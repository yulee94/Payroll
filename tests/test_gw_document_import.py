"""Tests for COSS GW full document import (parser, paths, importer)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE = _ROOT / "fixtures" / "gw_import" / "document_detail_sample.json"
_ATT_FIXTURE = _ROOT / "fixtures" / "gw_import" / "attachments" / "729a5d49019e000012" / "sample_receipt.txt"


class TestGwDetailParser(unittest.TestCase):
    def test_parse_fixture_json(self) -> None:
        from core.gw_import.detail_parser import load_detail_file, parse_detail_payload

        detail = load_detail_file(_FIXTURE)
        self.assertEqual(detail["gw_doc_id"], "729a5d49019e000012")
        self.assertIn("소모품", detail["title"])
        self.assertTrue(detail.get("content_text"))

    def test_parse_inbox_sample_line(self) -> None:
        from core.gw_import.detail_parser import parse_inbox_sample_line

        line = (
            '"[지출결의서] 테스트 문서 2026.06.01 새창 손화나(기안) ▶ 전성진(결재)"'
        )
        row = parse_inbox_sample_line(line)
        self.assertEqual(row["form_name"], "지출결의서")
        self.assertIn("테스트", row["title"])
        self.assertEqual(len(row["approval_workflow_json"]["steps"]), 2)


class TestGwImporter(unittest.TestCase):
    def test_upsert_and_attachment_path(self) -> None:
        from core.gw_import.detail_parser import load_detail_file
        from core.gw_import.importer import upsert_gw_document
        import core.paths as core_paths
        import core.workflow.store as wf_store

        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "Bitween" / "Payroll"
            gw_root = data_root / "gw_import"
            gw_root.mkdir(parents=True)
            (gw_root / "attachments" / "729a5d49019e000012").mkdir(parents=True)
            shutil_copy = _ATT_FIXTURE.read_text(encoding="utf-8")
            (gw_root / "attachments" / "729a5d49019e000012" / "sample_receipt.txt").write_text(
                shutil_copy, encoding="utf-8"
            )

            orig = core_paths.app_data_dir
            orig_wf_root = wf_store.WORKFLOW_ROOT
            core_paths.app_data_dir = lambda: data_root  # type: ignore[method-assign]
            wf_store.WORKFLOW_ROOT = data_root / "workflow"

            detail = load_detail_file(_FIXTURE)
            detail["attachments"] = [
                {
                    "name": "sample_receipt.txt",
                    "path": str(gw_root / "attachments" / "729a5d49019e000012" / "sample_receipt.txt"),
                    "size": 10,
                }
            ]
            tenant = "test_gw_import"
            wf_dir = data_root / "workflow" / tenant
            wf_dir.mkdir(parents=True)
            wf_dir.joinpath("database.json").write_text(
                json.dumps({"version": 1, "documents": [], "document_seq": 0}, ensure_ascii=False),
                encoding="utf-8",
            )

            doc_id, created, skipped = upsert_gw_document(tenant, detail, skip_if_complete=False)
            self.assertTrue(created)
            self.assertFalse(skipped)

            db = json.loads((wf_dir / "database.json").read_text(encoding="utf-8"))
            doc = next(d for d in db["documents"] if d["id"] == doc_id)
            cj = doc.get("content_json") or {}
            self.assertTrue(cj.get("gw_readonly"))
            self.assertTrue(cj.get("attachments"))
            rel = cj["attachments"][0]["path"]
            full = data_root / "gw_import" / rel.replace("/", "\\")
            self.assertTrue(full.is_file(), msg=str(full))

            core_paths.app_data_dir = orig  # type: ignore[method-assign]
            wf_store.WORKFLOW_ROOT = orig_wf_root


if __name__ == "__main__":
    unittest.main()
