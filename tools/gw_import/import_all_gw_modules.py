#!/usr/bin/env python3
"""
import_all_gw_modules.py — Full COSS GW → Bitween migration orchestrator.

Modules: approval lists, bulletin/board, mail metadata, work logs, org, forms probe.
Writes gw_import/migration_gap_report.json and appends to gw_import/full_migration.log

Auth (never commit):
  GW_USER + GW_PASS, or gw_import/session_cookies.json

Usage (from 급여프로그램/):
  python tools/gw_import/import_all_gw_modules.py --inventory-only
  python tools/gw_import/import_all_gw_modules.py --fetch-lists --max-pages 50
  python tools/gw_import/import_all_gw_modules.py --import --force-remerge
  python tools/gw_import/import_all_gw_modules.py --all
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.gw_import.gw_approval_list_api import APPR_BOX_BY_LIST_KIND, paginate_approval_list
from core.gw_import.gw_document_api import load_cookies_into_session
from core.gw_import.paths import dev_gw_import_dir, gw_details_dir, gw_import_root
from core.paths import app_data_dir
from tools.gw_import.apply_browser_import import BROWSER_FILE, BULLETIN_FILE, TENANT_ID

LOG_FILE = dev_gw_import_dir() / "full_migration.log"
GAP_REPORT = dev_gw_import_dir() / "migration_gap_report.json"
INVENTORY_FILE = dev_gw_import_dir() / "browser_menu_inventory.json"
LISTS_DIR = dev_gw_import_dir() / "lists"
WORKLOG_FILE = dev_gw_import_dir() / "work_logs.json"
BOARD_POSTS_FILE = dev_gw_import_dir() / "board_posts.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    line = f"[{_utc_now()}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _session_from_env_or_cookies(cookies_file: Path | None):
    import os

    import requests

    from tools.gw_import.gw_client import GwClient

    session = requests.Session()
    if cookies_file and cookies_file.is_file():
        load_cookies_into_session(session, cookies_file)
        return session, "cookies"
    uid = os.environ.get("GW_USER", "").strip()
    pwd = os.environ.get("GW_PASS", "")
    if uid and pwd:
        client = GwClient(session=session)
        client.login(user=uid, password=pwd)
        return session, "login"
    return None, ""


def _default_gw_inventory() -> dict[str, Any]:
    browser = _read_json(BROWSER_FILE if BROWSER_FILE.is_file() else dev_gw_import_dir() / "browser_min_screen.json", {})
    ext = _read_json(dev_gw_import_dir() / "gw_scrape_extended.json", {})
    counters = browser.get("counters") or {}
    hints = ext.get("inbox_counts_hint") or {}
    mail = ext.get("mail_folders") or []
    return {
        "fetched_at": _utc_now(),
        "source": "browser_min_screen+gw_scrape_extended",
        "approval": {
            "pending": hints.get("pending_approval") or counters.get("pending_approval"),
            "in_progress": hints.get("in_progress"),
            "circulate": hints.get("circulate") or counters.get("circulate_total"),
            "pending_home_widget": counters.get("pending_approval"),
        },
        "mail": {
            "unread": counters.get("unread_mail"),
            "folders": mail,
        },
        "board": {
            "recent_posts": counters.get("recent_board_posts"),
            "notices": counters.get("recent_notices"),
            "unread_notices": counters.get("unread_notices"),
        },
        "work_logs": {
            "unread_documents_widget": counters.get("unread_memo"),
            "home_widget_samples": len((browser.get("board") or {}).get("unread_work_reports") or []),
        },
        "org": {
            "org_tree_nodes": (_read_json(dev_gw_import_dir() / "org_tree.json", {}) or {}).get("counts", {}).get(
                "total_nodes"
            ),
        },
        "forms": {
            "browser_templates": len(browser.get("form_templates") or []),
        },
    }


def merge_browser_inventory(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    inv = _default_gw_inventory()
    if extra:
        for k, v in extra.items():
            if isinstance(v, dict) and isinstance(inv.get(k), dict):
                inv[k] = {**inv[k], **v}
            else:
                inv[k] = v
    if INVENTORY_FILE.is_file():
        prev = _read_json(INVENTORY_FILE, {})
        if isinstance(prev, dict):
            inv["previous_inventory_at"] = prev.get("fetched_at")
    _write_json(INVENTORY_FILE, inv)
    return inv


def _bitween_counts(tenant_id: str) -> dict[str, Any]:
    wf_path = _ROOT / "workflow" / tenant_id / "database.json"
    wf = _read_json(wf_path, {"documents": []})
    docs = wf.get("documents") or []
    with_gid = sum(
        1
        for d in docs
        if isinstance(d, dict) and str((d.get("content_json") or {}).get("gw_doc_id") or "").strip()
    )
    details = list(gw_details_dir().glob("*.json"))
    html_n = 0
    att_n = 0
    for p in details:
        d = _read_json(p, {})
        if len(str(d.get("content_html") or "")) > 80:
            html_n += 1
        if d.get("attachments"):
            att_n += 1
    bul_path = BULLETIN_FILE if BULLETIN_FILE.is_file() else _ROOT / "bulletin" / "announcements.json"
    bul = _read_json(bul_path, {"announcements": []})
    announcements = bul.get("announcements") or []
    gw_notices = sum(1 for a in announcements if isinstance(a, dict) and a.get("gw_notice_key"))
    board_posts = _read_json(BOARD_POSTS_FILE, {"posts": []})
    work_logs = _read_json(WORKLOG_FILE, {"items": []})
    mail_meta = _read_json(app_data_dir() / "gw_import" / "mail_folders.json", {})
    org = _read_json(dev_gw_import_dir() / "org_tree.json", {})
    org_count = 0
    if isinstance(org, dict):
        org_count = (org.get("counts") or {}).get("total_nodes") or len(org.get("flat_nodes") or [])
    list_files = list(LISTS_DIR.glob("*.json")) if LISTS_DIR.is_dir() else []
    list_ids: set[str] = set()
    for lf in list_files:
        data = _read_json(lf, {})
        for row in data.get("rows") or []:
            if isinstance(row, dict):
                gid = str(row.get("gw_doc_id") or "").strip()
                if gid:
                    list_ids.add(gid)
    return {
        "workflow_documents": len(docs),
        "workflow_with_gw_doc_id": with_gid,
        "detail_json_files": len(details),
        "detail_with_html": html_n,
        "detail_with_attachments": att_n,
        "bulletin_announcements": len(announcements),
        "bulletin_gw_notices": gw_notices,
        "board_posts_stored": len(board_posts.get("posts") or []),
        "work_log_items_stored": len(work_logs.get("items") or []),
        "mail_folders_stored": len(mail_meta.get("folders") or []),
        "org_nodes": org_count,
        "approval_list_index_ids": len(list_ids),
        "list_kind_files": [p.stem for p in list_files],
    }


def build_gap_report(tenant_id: str, *, gw_inv: dict[str, Any] | None = None) -> dict[str, Any]:
    gw = gw_inv or _read_json(INVENTORY_FILE) or _default_gw_inventory()
    bt = _bitween_counts(tenant_id)
    appr_gw = gw.get("approval") or {}
    board_gw = gw.get("board") or {}
    gaps: list[dict[str, str]] = []

    circulate = int(appr_gw.get("circulate") or 0)
    wf_docs = int(bt.get("workflow_documents") or 0)
    list_ids = int(bt.get("approval_list_index_ids") or 0)
    if circulate and max(wf_docs, list_ids) < circulate:
        gaps.append(
            {
                "module": "approval_circulate",
                "gw_count": str(circulate),
                "bitween_count": str(max(wf_docs, list_ids)),
                "note": "공람/결재 대량 미수집 — --fetch-lists + session_cookies.json 필요",
            }
        )
    if int(bt.get("detail_with_html") or 0) < int(bt.get("detail_json_files") or 0):
        gaps.append(
            {
                "module": "approval_body",
                "gw_count": str(bt.get("detail_json_files")),
                "bitween_count": str(bt.get("detail_with_html")),
                "note": "본문 HTML 미수집 — batch_full_scrape.py --api --resume",
            }
        )
    recent_posts = int(board_gw.get("recent_posts") or 0)
    if recent_posts and int(bt.get("board_posts_stored") or 0) < recent_posts:
        gaps.append(
            {
                "module": "board_posts",
                "gw_count": str(recent_posts),
                "bitween_count": str(bt.get("board_posts_stored")),
                "note": "게시글 본문·첨부 미수집 — 게시판 API/브라우저 페이징 필요",
            }
        )
    notices = int(board_gw.get("notices") or 0)
    if notices and int(bt.get("bulletin_gw_notices") or 0) < notices:
        gaps.append(
            {
                "module": "notices",
                "gw_count": str(notices),
                "bitween_count": str(bt.get("bulletin_gw_notices")),
                "note": "공지 일부만 import — 게시판 전체 페이징 필요",
            }
        )

    report = {
        "generated_at": _utc_now(),
        "tenant_id": tenant_id,
        "gw_inventory": gw,
        "bitween": bt,
        "gaps": gaps,
        "auth": {
            "cookies_file": str(dev_gw_import_dir() / "session_cookies.json"),
            "has_cookies": (dev_gw_import_dir() / "session_cookies.json").is_file()
            or (gw_import_root() / "session_cookies.json").is_file(),
            "has_gw_user": bool(__import__("os").environ.get("GW_USER")),
        },
        "next_steps": [
            "Export browser cookies → gw_import/session_cookies.json (gitignore)",
            "python tools/gw_import/import_all_gw_modules.py --fetch-lists",
            "python tools/gw_import/batch_full_scrape.py --api --resume",
            "python tools/gw_import/import_all_gw_modules.py --import --force-remerge",
        ],
    }
    _write_json(GAP_REPORT, report)
    return report


def import_board_and_worklogs_from_browser() -> dict[str, int]:
    """Import bulletin notices + stash board/worklog titles from browser extract."""
    src = BROWSER_FILE if BROWSER_FILE.is_file() else dev_gw_import_dir() / "browser_min_screen.json"
    data = _read_json(src, {})
    board = data.get("board") or {}
    posts: list[dict[str, Any]] = []
    for title in board.get("recent_posts") or []:
        t = str(title).strip()
        if t:
            posts.append({"title": t, "body": "", "source": "gw_home_widget"})
    for n in board.get("notices") or []:
        if isinstance(n, dict) and n.get("title"):
            posts.append(
                {
                    "title": str(n["title"]),
                    "body": str(n.get("body") or ""),
                    "gw_notice_key": str(n.get("key") or ""),
                    "source": "gw_notice",
                }
            )
    _write_json(
        BOARD_POSTS_FILE,
        {"fetched_at": _utc_now(), "posts": posts, "total": len(posts)},
    )
    work_items: list[dict[str, Any]] = []
    for title in board.get("unread_work_reports") or []:
        t = str(title).strip()
        if t:
            work_items.append({"title": t, "body": "", "source": "gw_home_widget"})
    _write_json(
        WORKLOG_FILE,
        {"fetched_at": _utc_now(), "items": work_items, "total": len(work_items)},
    )
    return {"board_posts": len(posts), "work_logs": len(work_items)}


def fetch_all_approval_lists(
    session,
    *,
    list_kinds: tuple[str, ...],
    page_size: int = 30,
    max_pages: int = 0,
) -> dict[str, Any]:
    LISTS_DIR.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {}
    all_ids: list[str] = []
    for kind in list_kinds:
        try:
            rows, total = paginate_approval_list(
                session,
                kind,
                page_size=page_size,
                max_pages=max_pages,
            )
            _write_json(
                LISTS_DIR / f"{kind}.json",
                {
                    "fetched_at": _utc_now(),
                    "list_kind": kind,
                    "appr_box_id": APPR_BOX_BY_LIST_KIND.get(kind, kind),
                    "gw_total": total,
                    "rows": rows,
                },
            )
            summary[kind] = {"gw_total": total, "fetched": len(rows)}
            for r in rows:
                gid = str(r.get("gw_doc_id") or "").strip()
                if gid:
                    all_ids.append(gid)
            _log(f"LIST {kind}: fetched={len(rows)} gw_total={total}")
        except Exception as exc:
            summary[kind] = {"error": str(exc)}
            _log(f"LIST {kind} FAILED: {exc}")
    pending_path = dev_gw_import_dir() / "pending_detail_scrape.json"
    uniq: dict[str, dict] = {}
    for gid in all_ids:
        if gid:
            uniq[gid] = {"gw_doc_id": gid, "title": "", "source": "list_api"}
    if uniq:
        _write_json(pending_path, list(uniq.values()))
    summary["unique_gw_doc_ids"] = len(uniq)
    return summary


def run_import_pipeline(tenant_id: str, *, force_remerge: bool) -> dict[str, Any]:
    results: dict[str, Any] = {}
    py = sys.executable

    def _run(cmd: list[str], label: str) -> None:
        _log(f"RUN {label}: {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
        results[label] = {"returncode": proc.returncode, "stdout_tail": (proc.stdout or "")[-2000:]}
        if proc.returncode != 0:
            _log(f"FAIL {label}: {(proc.stderr or '')[-500:]}")

    board_stats = import_board_and_worklogs_from_browser()
    results["board_worklog_stash"] = board_stats

    browser_src = BROWSER_FILE if BROWSER_FILE.is_file() else dev_gw_import_dir() / "browser_min_screen.json"
    _run([py, "tools/gw_import/apply_browser_import.py", "--input", str(browser_src), "--tenant", tenant_id], "apply_browser_import")
    _run([py, "tools/gw_import/sync_gw_extended.py", "--tenant", tenant_id], "sync_gw_extended")

    cookie_path = dev_gw_import_dir() / "session_cookies.json"
    if cookie_path.is_file() or __import__("os").environ.get("GW_USER"):
        scrape_cmd = [py, "tools/gw_import/batch_full_scrape.py", "--api", "--resume"]
        if cookie_path.is_file():
            scrape_cmd.extend(["--cookies-file", str(cookie_path)])
        _run(scrape_cmd, "batch_full_scrape")
    else:
        results["batch_full_scrape"] = {"skipped": "no session_cookies.json or GW_USER"}
        _log("SKIP batch_full_scrape: no auth")

    imp_cmd = [py, "tools/gw_import/import_all_documents.py", "--tenant", tenant_id, "--resume"]
    if force_remerge:
        imp_cmd.append("--force-remerge")
    _run(imp_cmd, "import_all_documents")

    results["gap_report"] = build_gap_report(tenant_id)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="COSS GW full module migration")
    parser.add_argument("--tenant", default=TENANT_ID)
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--gap-report", action="store_true")
    parser.add_argument("--fetch-lists", action="store_true")
    parser.add_argument("--import", dest="do_import", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--force-remerge", action="store_true")
    parser.add_argument("--cookies-file", type=Path, default=None)
    parser.add_argument("--page-size", type=int, default=30)
    parser.add_argument("--max-pages", type=int, default=0, help="0 = all pages per inbox")
    parser.add_argument(
        "--lists",
        default=",".join(
            (
                "pending",
                "in_progress",
                "completed",
                "circulate",
                "draft_progress",
            )
        ),
    )
    args = parser.parse_args()

    _log("=== import_all_gw_modules start ===")
    merge_browser_inventory()

    if args.inventory_only or args.gap_report or not (args.fetch_lists or args.do_import or args.all):
        report = build_gap_report(args.tenant)
        print(f"Gap report: {GAP_REPORT}")
        if not (args.fetch_lists or args.do_import or args.all):
            return 0

    cookies = args.cookies_file
    if not cookies:
        for cand in (dev_gw_import_dir() / "session_cookies.json", gw_import_root() / "session_cookies.json"):
            if cand.is_file():
                cookies = cand
                break

    if args.fetch_lists or args.all:
        session, mode = _session_from_env_or_cookies(cookies)
        if not session:
            _log("SKIP --fetch-lists: no GW_USER/GW_PASS or session_cookies.json")
        else:
            kinds = tuple(k.strip() for k in args.lists.split(",") if k.strip())
            summary = fetch_all_approval_lists(
                session,
                list_kinds=kinds,
                page_size=args.page_size,
                max_pages=args.max_pages,
            )
            _write_json(dev_gw_import_dir() / "list_fetch_summary.json", summary)
            _write_json(dev_gw_import_dir() / "list_fetch_summary.json", summary)
            print(f"List fetch summary: {dev_gw_import_dir() / 'list_fetch_summary.json'}")

    if args.do_import or args.all:
        results = run_import_pipeline(args.tenant, force_remerge=args.force_remerge)
        out_path = dev_gw_import_dir() / "orchestrator_results.json"
        _write_json(out_path, results)
        print(f"Wrote {out_path}")

    build_gap_report(args.tenant)
    _log("=== import_all_gw_modules done ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
