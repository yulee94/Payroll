#!/usr/bin/env python3
"""
batch_full_scrape.py — Full COSS GW document body + attachment import.

Modes:
  --api          HTTP selectApprovalView + file download (needs GW_USER/GW_PASS or --cookies-file)
  --ingest-dir   Parse saved browser snapshots/HTML under gw_import/snapshots/
  --report       Stats only

Progress: gw_import/full_scrape_progress.log
Checkpoint: gw_import/full_scrape_checkpoint.json
Errors: gw_import/scrape_errors.json

Do NOT commit gw_import/session_cookies.json or credentials.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.gw_import.detail_parser import load_detail_file
from core.gw_import.gw_document_api import (
    detail_from_approval_view,
    download_attachments,
    fetch_approval_view,
    gw_popup_url,
    is_synthetic_body,
    load_cookies_into_session,
    needs_full_scrape,
)
from core.gw_import.paths import dev_gw_import_dir, gw_details_dir, gw_import_root
from core.gw_import.store import load_detail_cache, save_detail_cache

GW_DOC_VIEW_URL = (
    "https://gw.cossok.com/gw/biz/eap/approval/eapApprMain.do"
    "?mode=view&apprId={gw_doc_id}"
)

RATE_LIMIT_SEC = 0.35


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    line = f"[{_utc_now()}] {msg}"
    print(line)
    log_path = gw_import_root() / "full_scrape_progress.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _checkpoint_path() -> Path:
    return gw_import_root() / "full_scrape_checkpoint.json"


def _errors_path() -> Path:
    return gw_import_root() / "scrape_errors.json"


def load_checkpoint() -> dict:
    p = _checkpoint_path()
    if not p.is_file():
        return {"completed": [], "failed": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("completed", [])
            data.setdefault("failed", [])
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"completed": [], "failed": []}


def save_checkpoint(cp: dict) -> None:
    cp["updated_at"] = _utc_now()
    _checkpoint_path().write_text(json.dumps(cp, ensure_ascii=False, indent=2), encoding="utf-8")


def append_error(gw_doc_id: str, error: str, *, mode: str = "") -> None:
    path = _errors_path()
    rows: list = []
    if path.is_file():
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            rows = []
    if not isinstance(rows, list):
        rows = []
    rows.append({"gw_doc_id": gw_doc_id, "error": error, "mode": mode, "at": _utc_now()})
    path.write_text(json.dumps(rows[-500:], ensure_ascii=False, indent=2), encoding="utf-8")


def collect_gw_doc_ids() -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()

    db_path = _ROOT / "workflow" / "coss" / "database.json"
    if db_path.is_file():
        db = json.loads(db_path.read_text(encoding="utf-8"))
        for doc in db.get("documents") or []:
            cj = doc.get("content_json") or {}
            gid = str(cj.get("gw_doc_id") or "").strip()
            if gid and gid not in seen:
                seen.add(gid)
                ids.append(gid)

    pending = dev_gw_import_dir() / "pending_detail_scrape.json"
    if pending.is_file():
        for row in json.loads(pending.read_text(encoding="utf-8")):
            if isinstance(row, dict):
                gid = str(row.get("gw_doc_id") or "").strip()
                if gid and gid not in seen:
                    seen.add(gid)
                    ids.append(gid)

    for p in sorted(gw_details_dir().glob("*.json")):
        gid = p.stem
        if gid and gid not in seen:
            seen.add(gid)
            ids.append(gid)

    return ids


def _session_from_args(args: argparse.Namespace):
    import requests

    from tools.gw_import.gw_client import GwClient

    session = requests.Session()
    if args.cookies_file:
        load_cookies_into_session(session, Path(args.cookies_file))
        return session
    client = GwClient(session=session)
    client.login(user=args.gw_user, password=args.gw_pass)
    return session


def run_api_scrape(args: argparse.Namespace) -> dict:
    try:
        session = _session_from_args(args)
    except Exception as exc:
        _log(f"LOGIN FAILED: {exc}")
        return {"ok": 0, "failed": 0, "skipped": 0, "login_error": str(exc)}

    cp = load_checkpoint()
    done = set(cp.get("completed") or [])
    stats = {"ok": 0, "failed": 0, "skipped": 0, "partial": 0}

    for gid in collect_gw_doc_ids():
        if args.resume and gid in done:
            stats["skipped"] += 1
            continue
        if args.limit and stats["ok"] + stats["failed"] + stats["partial"] >= args.limit:
            break

        cached = load_detail_cache(gid)
        if cached and not needs_full_scrape(cached) and not args.force:
            stats["skipped"] += 1
            continue

        try:
            res = fetch_approval_view(session, gid)
            detail = detail_from_approval_view(res, gid)
            if detail.get("attachments"):
                detail = download_attachments(session, detail)
            save_detail_cache(detail)
            has_html = len(str(detail.get("content_html") or "")) > 80
            has_att = bool(detail.get("attachments"))
            if has_html:
                stats["ok"] += 1
                _log(f"OK {gid} html={len(detail.get('content_html') or '')} att={len(detail.get('attachments') or [])}")
            elif has_att:
                stats["partial"] += 1
                _log(f"PARTIAL {gid} (attachments only, iframe/API may lack body)")
            else:
                stats["failed"] += 1
                append_error(gid, "empty body and attachments", mode="api")
                _log(f"EMPTY {gid}")
            done.add(gid)
            cp["completed"] = sorted(done)
            save_checkpoint(cp)
        except Exception as exc:
            stats["failed"] += 1
            append_error(gid, str(exc), mode="api")
            _log(f"FAIL {gid}: {exc}")
            failed = cp.setdefault("failed", [])
            if gid not in failed:
                failed.append(gid)
            save_checkpoint(cp)

        if args.rate > 0:
            time.sleep(args.rate)

    return stats


_GW_ID_FILE = re.compile(r"^([0-9a-f]{18,})\.(log|html|htm|yaml|yml)$", re.I)


def run_ingest_dir(args: argparse.Namespace) -> dict:
    snap_dir = Path(args.ingest_dir) if args.ingest_dir else dev_gw_import_dir() / "snapshots"
    stats = {"ok": 0, "failed": 0, "skipped": 0}
    if not snap_dir.is_dir():
        _log(f"No snapshot dir: {snap_dir}")
        return stats

    for path in sorted(snap_dir.iterdir()):
        m = _GW_ID_FILE.match(path.name)
        if not m:
            continue
        gid = m.group(1)
        if args.limit and stats["ok"] + stats["failed"] >= args.limit:
            break
        try:
            detail = load_detail_file(path)
            if gid and not detail.get("gw_doc_id"):
                detail["gw_doc_id"] = gid
            detail.setdefault("gw_url", gw_popup_url(gid))
            save_detail_cache(detail)
            stats["ok"] += 1
            _log(f"INGEST {gid} from {path.name}")
        except Exception as exc:
            stats["failed"] += 1
            append_error(gid, str(exc), mode="ingest")
            _log(f"INGEST FAIL {path.name}: {exc}")
    return stats


def run_report() -> dict:
    ids = collect_gw_doc_ids()
    html_n = att_n = thin_n = 0
    for gid in ids:
        d = load_detail_cache(gid) or {}
        ch = str(d.get("content_html") or "")
        if len(ch) > 80:
            html_n += 1
        if d.get("attachments"):
            att_n += 1
        if is_synthetic_body(d):
            thin_n += 1
    report = {
        "at": _utc_now(),
        "total_gw_doc_ids": len(ids),
        "detail_with_html": html_n,
        "detail_with_attachments": att_n,
        "detail_synthetic_thin": thin_n,
        "popup_url_template": gw_popup_url("{gw_doc_id}"),
        "view_url_template": GW_DOC_VIEW_URL,
        "manual": (
            "Iframe blocks browser a11y tree. Use eapApprViewPopup.do?apprId=ID, "
            "save HTML (Print/PC저장), or --api with session_cookies.json"
        ),
    }
    out = gw_import_root() / "full_scrape_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(json.dumps(report, ensure_ascii=False))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch full GW document scrape")
    parser.add_argument("--api", action="store_true", help="Fetch via GW HTTP API")
    parser.add_argument("--ingest", action="store_true", help="Ingest snapshot/HTML files")
    parser.add_argument("--ingest-dir", default="", help="Snapshot directory (default: gw_import/snapshots)")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--cookies-file", type=Path, default=None, help="Exported browser cookies JSON")
    parser.add_argument("--gw-user", default="", help="Or set GW_USER env")
    parser.add_argument("--gw-pass", default="", help="Or set GW_PASS env")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if detail looks complete")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--rate", type=float, default=RATE_LIMIT_SEC)
    args = parser.parse_args()

    import os

    if not args.gw_user:
        args.gw_user = os.environ.get("GW_USER", "")
    if not args.gw_pass:
        args.gw_pass = os.environ.get("GW_PASS", "")
    if not args.cookies_file:
        for cand in (
            gw_import_root() / "session_cookies.json",
            dev_gw_import_dir() / "session_cookies.json",
        ):
            if cand.is_file():
                args.cookies_file = cand
                break

    if args.report:
        run_report()
        return 0
    if args.api:
        stats = run_api_scrape(args)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        run_report()
        return 0 if not stats.get("login_error") else 1
    if args.ingest:
        stats = run_ingest_dir(args)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        run_report()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
