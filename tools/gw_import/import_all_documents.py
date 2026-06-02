#!/usr/bin/env python3
"""
import_all_documents.py — Batch import COSS GW documents (body + attachments) into Bitween.

Order: pending → in_progress → completed → circulate → draft lists (from scrape JSON).
Uses detail cache: app_data/gw_import/details/{gw_doc_id}.json
Checkpoint: app_data/gw_import/import_checkpoint.json

Usage:
  cd 급여프로그램
  python tools/gw_import/import_all_documents.py
  python tools/gw_import/import_all_documents.py --tenant coss --limit 50
  python tools/gw_import/import_all_documents.py --import-details-only
  python tools/gw_import/import_all_documents.py --resume

After browser scrape per document:
  python tools/gw_import/scrape_document_detail.py --gw-doc-id ... --snapshot ...
  python tools/gw_import/import_all_documents.py --resume
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.gw_import.importer import count_fully_imported, import_detail_file, upsert_gw_document
from core.gw_import.lists import collect_list_rows, default_batch_lists
from core.gw_import.paths import gw_details_dir
from core.gw_import.store import load_checkpoint, mark_completed, save_checkpoint
from core.paths import app_data_dir
from tools.gw_import.apply_browser_import import IMPORT_DIR, _import_workflow_documents
from core.workflow.store import _load_raw, _save_raw

TENANT_DEFAULT = "coss"
RATE_LIMIT_SEC = 0.15


def _bootstrap_list_metadata(tenant_id: str, rows: list[dict[str, object]]) -> tuple[int, int]:
    """Ensure list rows exist (titles) before full body merge."""
    if not rows:
        return 0, 0
    db = _load_raw(tenant_id)
    doc_rows = [{**r, "_list": r.get("gw_list") or "import"} for r in rows if r.get("title")]
    added, skipped = _import_workflow_documents(db, doc_rows, list_kind="batch")
    _save_raw(tenant_id, db)
    return added, skipped


def _synthetic_detail_from_row(row: dict[str, object]) -> dict[str, object]:
    gid = str(row.get("gw_doc_id") or "").strip()
    title = str(row.get("title") or "").strip()
    text = f"(COSS 그룹웨어에서 가져온 문서)\n\n{title}"
    if row.get("drafter"):
        text += f"\n\n기안자: {row.get('drafter')}"
    aw = row.get("approval_workflow_json")
    if isinstance(aw, dict) and aw.get("steps"):
        text += "\n\n— 결재선 —\n"
        for i, s in enumerate(aw["steps"], 1):
            if isinstance(s, dict):
                text += f"  {i}. {s.get('name')} ({s.get('role')})\n"
    return {
        "gw_doc_id": gid,
        "title": title,
        "drafter": row.get("drafter") or "",
        "gw_list": row.get("gw_list") or "",
        "content_text": text,
        "content_html": "",
        "attachments": [],
        "approval_workflow_json": aw if isinstance(aw, dict) else {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch GW document import into Bitween")
    parser.add_argument("--tenant", default=TENANT_DEFAULT)
    parser.add_argument("--limit", type=int, default=0, help="Max documents per run (0=all)")
    parser.add_argument("--resume", action="store_true", help="Skip ids in checkpoint")
    parser.add_argument("--reset-checkpoint", action="store_true")
    parser.add_argument("--import-details-only", action="store_true", help="Only import files in details/")
    parser.add_argument("--lists", default=",".join(default_batch_lists()))
    parser.add_argument("--min-body", action="store_true", help="Import list rows with synthetic body if no detail file")
    parser.add_argument(
        "--force-remerge",
        action="store_true",
        help="Re-apply detail JSON even if checkpoint/import thinks complete",
    )
    parser.add_argument("--rate", type=float, default=RATE_LIMIT_SEC)
    args = parser.parse_args()

    tenant_id = args.tenant
    cp = load_checkpoint()
    if args.reset_checkpoint:
        cp = {
            "started_at": "",
            "updated_at": "",
            "completed_ids": [],
            "errors": [],
            "stats": {"imported": 0, "skipped": 0, "failed": 0},
        }
        save_checkpoint(cp)

    completed = set(cp.get("completed_ids") or [])
    stats = {"imported": 0, "skipped": 0, "failed": 0, "no_detail": 0}

    if args.import_details_only:
        detail_files = sorted(gw_details_dir().glob("*.json"))
        rows = [{"gw_doc_id": p.stem} for p in detail_files]
    else:
        list_kinds = [x.strip() for x in args.lists.split(",") if x.strip()]
        rows = collect_list_rows(lists=tuple(list_kinds))
        _bootstrap_list_metadata(tenant_id, rows)

    processed = 0
    for row in rows:
        gid = str(row.get("gw_doc_id") or "").strip()
        if not gid:
            continue
        if args.resume and not args.force_remerge and gid in completed:
            stats["skipped"] += 1
            continue
        if args.limit and processed >= args.limit:
            break

        detail_path = gw_details_dir() / f"{gid}.json"
        try:
            if detail_path.is_file():
                _, created, skipped = import_detail_file(
                    tenant_id,
                    detail_path,
                    skip_if_complete=not args.force_remerge,
                )
            elif args.min_body:
                detail = _synthetic_detail_from_row(row)
                _, created, skipped = upsert_gw_document(tenant_id, detail)
            else:
                stats["no_detail"] += 1
                continue

            if skipped:
                stats["skipped"] += 1
            else:
                stats["imported"] += 1
            mark_completed(gid, imported=not skipped, skipped=skipped)
            completed.add(gid)
            processed += 1
            if args.rate > 0:
                time.sleep(args.rate)
        except Exception as exc:
            stats["failed"] += 1
            mark_completed(gid, error=str(exc))

    counts = count_fully_imported(tenant_id)
    report = {
        "tenant_id": tenant_id,
        "run_stats": stats,
        "fully_imported": counts,
        "checkpoint": str(app_data_dir() / "gw_import" / "import_checkpoint.json"),
        "details_dir": str(gw_details_dir()),
        "attachments_dir": str(app_data_dir() / "gw_import" / "attachments"),
    }
    out = IMPORT_DIR / "full_import_report.json"
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
