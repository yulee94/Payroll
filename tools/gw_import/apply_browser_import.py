#!/usr/bin/env python3
"""
apply_browser_import.py — COSS GW browser scrape → Bitween (gw_import + workflow + bulletin).

Reads gw_import/browser_min_screen.json (+ optional _drafts_parsed.json).
Re-runnable: skips rows already imported (gw_doc_id / gw_notice_key).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.paths import app_data_dir
from core.workflow.constants import DOC_STATUS_APPROVED
from core.workflow.store import _load_raw, _new_id, _now_iso, _save_raw, next_document_no
from core.gw_import.classify import DEFAULT_REQUESTER, infer_document_type
from core.gw_import.paths import dev_gw_import_dir, gw_details_dir
from core.gw_import.store import load_detail_cache

IMPORT_DIR = app_data_dir() / "gw_import"
BROWSER_FILE = IMPORT_DIR / "browser_min_screen.json"
DRAFTS_FILE = IMPORT_DIR / "_drafts_parsed.json"
BULLETIN_FILE = app_data_dir() / "bulletin" / "announcements.json"
TENANT_ID = "coss"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gw_keys_in_db(db: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for doc in db.get("documents") or []:
        if not isinstance(doc, dict):
            continue
        cj = doc.get("content_json") or {}
        if isinstance(cj, dict):
            gid = str(cj.get("gw_doc_id") or "").strip()
            if gid:
                found.add(f"id:{gid}")
            else:
                t = str(doc.get("title") or "").strip()
                if t:
                    found.add(f"title:{t}")
    return found


def _import_workflow_documents(
    db: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    list_kind: str,
) -> tuple[int, int]:
    existing = _gw_keys_in_db(db)
    added = 0
    skipped = 0
    for row in rows:
        gid = str(row.get("gw_doc_id") or "").strip()
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        dedupe = f"id:{gid}" if gid else f"title:{title}"
        if dedupe in existing:
            skipped += 1
            continue
        doc_id = _new_id()
        db.setdefault("documents", []).append(
            {
                "id": doc_id,
                "document_no": next_document_no(db),
                "document_type": infer_document_type(title),
                "title": title,
                "summary": title,
                "content": "",
                "status": DOC_STATUS_APPROVED,
                "site_id": "site_hq",
                "department_id": "dept_mgmt",
                "requester_id": DEFAULT_REQUESTER,
                "total_amount": 0,
                "currency": "KRW",
                "category": "",
                "requested_date": "",
                "due_date": "",
                "approved_at": _now_iso(),
                "rejected_at": "",
                "completed_at": "",
                "closed_at": "",
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "content_json": {
                    "gw_doc_id": gid,
                    "gw_drafter": row.get("drafter") or "",
                    "gw_list": list_kind,
                    "imported_from": "gw.cossok.com",
                    "imported_at": _utc_now(),
                },
            }
        )
        existing.add(dedupe)
        added += 1
    return added, skipped


def _bulletin_gw_keys(store: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for row in store.get("announcements") or []:
        if not isinstance(row, dict):
            continue
        k = str(row.get("gw_notice_key") or "").strip()
        if k:
            keys.add(k)
    return keys


def _import_bulletin(notices: list[dict[str, Any]]) -> tuple[int, int]:
    BULLETIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    if BULLETIN_FILE.is_file():
        store = json.loads(BULLETIN_FILE.read_text(encoding="utf-8"))
    else:
        store = {"version": 1, "announcements": []}
    existing = _bulletin_gw_keys(store)
    added = 0
    skipped = 0
    rows: list[dict[str, Any]] = list(store.get("announcements") or [])
    for n in notices:
        key = str(n.get("key") or n.get("title") or "").strip()
        title = str(n.get("title") or "").strip()
        if not title:
            continue
        if key in existing:
            skipped += 1
            continue
        body = str(n.get("body") or "").strip() or f"(COSS 그룹웨어에서 가져온 공지) {title}"
        rows.append(
            {
                "id": uuid.uuid4().hex[:12],
                "title": title,
                "body": body,
                "author_user_id": DEFAULT_REQUESTER,
                "author_name": "COSS GW Import",
                "author_tenant_id": TENANT_ID,
                "author_org": "(주)코스",
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "pinned": bool(n.get("pinned")),
                "visibility": {"all_group": True, "tenants": [], "sites": []},
                "gw_notice_key": key,
                "gw_import": True,
            }
        )
        existing.add(key)
        added += 1
    store["announcements"] = rows
    BULLETIN_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    return added, skipped


def _drafts_path() -> Path | None:
    for p in (DRAFTS_FILE, dev_gw_import_dir() / "_drafts_parsed.json"):
        if p.is_file():
            return p
    return None


def _load_extract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    drafts_path = _drafts_path()
    if drafts_path:
        drafts = json.loads(drafts_path.read_text(encoding="utf-8"))
        approval = data.setdefault("approval", {})
        approval["drafts_page1"] = drafts
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply COSS GW browser extract to Bitween")
    parser.add_argument("--input", type=Path, default=BROWSER_FILE)
    parser.add_argument("--tenant", default=TENANT_ID)
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Missing extract file: {args.input}", file=sys.stderr)
        return 1

    extract = _load_extract(args.input)
    tenant_id = str(extract.get("tenant_id") or args.tenant)

    approval = extract.get("approval") or {}
    doc_rows: list[dict[str, Any]] = []
    for key in ("drafts_page1", "circulate_home_widget"):
        block = approval.get(key)
        if isinstance(block, list):
            for row in block:
                if isinstance(row, dict):
                    doc_rows.append({**row, "_list": key})

    db = _load_raw(tenant_id)
    db_before = len(db.get("documents") or [])
    wf_added, wf_skipped = _import_workflow_documents(db, doc_rows, list_kind="browser")
    _save_raw(tenant_id, db)

    detail_merged = 0
    for row in doc_rows:
        gid = str(row.get("gw_doc_id") or "").strip()
        if not gid:
            continue
        detail = load_detail_cache(gid)
        if not detail:
            continue
        detail.setdefault("gw_list", row.get("_list") or "browser")
        try:
            from core.gw_import.importer import upsert_gw_document

            upsert_gw_document(tenant_id, detail, skip_if_complete=True)
            detail_merged += 1
        except Exception:
            pass

    board = extract.get("board") or {}
    notices = board.get("notices", [])
    if not isinstance(notices, list):
        notices = []
    for title in board.get("recent_posts") or []:
        t = str(title).strip()
        if not t:
            continue
        key = "gw-board-" + uuid.uuid5(uuid.NAMESPACE_URL, t).hex[:12]
        notices.append({"key": key, "title": t, "body": f"(COSS GW 게시판) {t}"})
    bul_added, bul_skipped = _import_bulletin(notices)

    manifest_path = IMPORT_DIR / "manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
    manifest.update(
        {
            "fetched_at": extract.get("fetched_at") or _utc_now(),
            "source": "gw.cossok.com",
            "import_mode": "browser_scrape",
            "tenant_id": tenant_id,
            "group": extract.get("group_name") or "COSS Group",
            "modules": {
                **(manifest.get("modules") or {}),
                "browser_screen": {
                    "workflow_docs_added": wf_added,
                    "workflow_docs_skipped": wf_skipped,
                    "detail_files_merged": detail_merged,
                    "details_dir": str(gw_details_dir()),
                    "bulletin_added": bul_added,
                    "bulletin_skipped": bul_skipped,
                    "documents_in_db": len(db.get("documents") or []),
                    "documents_before": db_before,
                },
            },
        }
    )
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "tenant_id": tenant_id,
        "workflow": {
            "added": wf_added,
            "skipped_duplicate": wf_skipped,
            "total_documents": len(db.get("documents") or []),
        },
        "bulletin": {"added": bul_added, "skipped_duplicate": bul_skipped},
        "manifest": str(manifest_path),
    }
    report_path = IMPORT_DIR / "import_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
