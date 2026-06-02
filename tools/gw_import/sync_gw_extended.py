#!/usr/bin/env python3
"""COSS GW 양식함·결재함·메일 메타 → Bitween 동기화."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.paths import app_data_dir
from core.workflow.form_templates import merge_gw_templates
from tools.gw_import.apply_browser_import import (
    BROWSER_FILE,
    IMPORT_DIR,
    TENANT_ID,
    _import_workflow_documents,
)
from core.workflow.constants import DOC_STATUS_APPROVED, DOC_STATUS_IN_REVIEW
from core.workflow.store import _load_raw, _save_raw

EXTENDED_FILE = IMPORT_DIR / "gw_scrape_extended.json"
FORM_BRACKET = re.compile(r"\[([^\]]+)\]")


def _extra_form_names() -> list[str]:
    names: set[str] = set()
    if BROWSER_FILE.is_file():
        data = json.loads(BROWSER_FILE.read_text(encoding="utf-8"))
        for n in data.get("form_templates") or []:
            if isinstance(n, str) and n.strip():
                names.add(n.strip())
    if EXTENDED_FILE.is_file():
        ext = json.loads(EXTENDED_FILE.read_text(encoding="utf-8"))
        for line in ext.get("document_samples") or []:
            if not isinstance(line, dict):
                continue
            raw = str(line.get("line") or "")
            for m in FORM_BRACKET.finditer(raw):
                nm = m.group(1).strip()
                if nm and nm not in ("승인", "기안"):
                    names.add(nm)
    return sorted(names)


def _parse_inbox_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not EXTENDED_FILE.is_file():
        return rows
    ext = json.loads(EXTENDED_FILE.read_text(encoding="utf-8"))
    for line in ext.get("document_samples") or []:
        if not isinstance(line, dict):
            continue
        raw = str(line.get("line") or "").strip().strip('"')
        m = FORM_BRACKET.search(raw)
        form_name = m.group(1) if m else ""
        title = raw
        if "]" in raw:
            title = raw.split("]", 1)[-1].split("새창")[0].strip()
        if not title:
            continue
        status = DOC_STATUS_APPROVED if "[승인]" in raw or "승인" in form_name else DOC_STATUS_IN_REVIEW
        rows.append(
            {
                "title": title[:200],
                "gw_form_name": form_name.replace("[승인]", "").strip(),
                "gw_list": "inbox_scrape",
                "status_hint": status,
            }
        )
    return rows[:60]


def _import_inbox_samples(tenant_id: str) -> tuple[int, int]:
    db = _load_raw(tenant_id)
    doc_rows = []
    for row in _parse_inbox_rows():
        title = str(row.get("title") or "")
        doc_rows.append(
            {
                "title": title,
                "gw_doc_id": "",
                "drafter": "",
                "_list": str(row.get("gw_list") or "inbox"),
            }
        )
    added, skipped = _import_workflow_documents(db, doc_rows, list_kind="inbox_scrape")
    _save_raw(tenant_id, db)
    return added, skipped


def _save_mail_metadata(tenant_id: str) -> int:
    if not EXTENDED_FILE.is_file():
        return 0
    ext = json.loads(EXTENDED_FILE.read_text(encoding="utf-8"))
    folders = ext.get("mail_folders") or []
    out = IMPORT_DIR / "mail_folders.json"
    out.write_text(
        json.dumps(
            {"tenant_id": tenant_id, "folders": folders, "source": "gw.cossok.com"},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return len(folders)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync COSS GW forms, inbox, mail metadata")
    parser.add_argument("--tenant", default=TENANT_ID)
    args = parser.parse_args()
    tenant_id = args.tenant

    extra = _extra_form_names()
    inbox_summary = {}
    mail_folders = []
    if EXTENDED_FILE.is_file():
        ext = json.loads(EXTENDED_FILE.read_text(encoding="utf-8"))
        inbox_summary = ext.get("inbox_counts_hint") or {}
        mail_folders = ext.get("mail_folders") or []

    form_stats = merge_gw_templates(
        tenant_id,
        extra,
        inbox_summary=inbox_summary,
        mail_folders=mail_folders,
    )

    wf_added, wf_skipped = _import_inbox_samples(tenant_id)

    mail_count = _save_mail_metadata(tenant_id)

    report = {
        "tenant_id": tenant_id,
        "forms": form_stats,
        "extra_form_names": len(extra),
        "inbox_documents": {"added": wf_added, "skipped": wf_skipped},
        "mail_folders_saved": mail_count,
        "form_templates_path": str(app_data_dir() / "workflow" / tenant_id / "form_templates.json"),
    }
    path = IMPORT_DIR / "sync_extended_report.json"
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
