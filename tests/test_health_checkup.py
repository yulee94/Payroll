"""tests/test_health_checkup.py - 건강검진 대상 조회 · 결과지 업로드"""

from __future__ import annotations

import csv
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.hr import health_checkup as hc


class TestHealthCheckupImportLookup(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        root = Path(self._tmpdir)
        self._root_patcher = patch.object(hc, "_CHECKUP_ROOT", root)
        self._root_patcher.start()
        self.addCleanup(self._root_patcher.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_csv(self, rows: list[dict[str, str]], headers: list[str]) -> Path:
        path = Path(self._tmpdir) / "eligibility.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return path

    def test_import_and_lookup_by_employee_no(self) -> None:
        csv_path = self._write_csv(
            [
                {
                    "사번": "E001",
                    "성명": "홍길동",
                    "주민등록번호": "900101-1234567",
                    "검진유형": "일반",
                    "기간시작": "2026-01-01",
                    "기간종료": "2026-06-30",
                    "상태": "미수검",
                },
                {
                    "사번": "E002",
                    "성명": "김철수",
                    "주민등록번호": "850515-2000000",
                    "검진유형": "특수",
                    "기간시작": "2026-02-01",
                    "기간종료": "2026-08-31",
                    "특수검사": "소음,분진",
                    "상태": "미수검",
                },
            ],
            ["사번", "성명", "주민등록번호", "검진유형", "기간시작", "기간종료", "특수검사", "상태"],
        )
        summary = hc.import_eligibility_csv(csv_path, tenant_id="tenant_a")
        self.assertEqual(summary["imported_count"], 2)

        result = hc.lookup_eligibility("tenant_a", "E001")
        self.assertTrue(result.eligible)
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0]["checkup_type"], "general")
        self.assertEqual(result.records[0]["employee_name"], "홍길동")

        special = hc.lookup_eligibility("tenant_a", "8505152000000")
        self.assertTrue(special.eligible)
        self.assertEqual(special.records[0]["checkup_type"], "special")
        self.assertIn("소음", special.records[0]["special_exam_types"])

    def test_manual_add_and_lookup_by_rrn(self) -> None:
        hc.add_eligibility_manual(
            tenant_id="tenant_a",
            employee_no="A100",
            employee_name="이영희",
            rrn="670204-2447413",
            checkup_type="special",
            period_start="2026-03-01",
            period_end="2026-09-30",
            special_exam_types=["유기용제"],
        )
        result = hc.lookup_eligibility("tenant_a", "6702042447413")
        self.assertTrue(result.eligible)
        self.assertEqual(result.records[0]["employee_name"], "이영희")
        self.assertEqual(result.records[0]["special_exam_types"], ["유기용제"])

    def test_save_upload_marks_completed(self) -> None:
        rec = hc.add_eligibility_manual(
            tenant_id="tenant_a",
            employee_no="U01",
            employee_name="박수검",
            rrn="800101-1000000",
            period_start="2026-01-01",
            period_end="2026-12-31",
        )
        src = Path(self._tmpdir) / "result.pdf"
        src.write_bytes(b"%PDF-1.4 test")

        upload = hc.save_upload(
            source_file=src,
            eligibility_id=rec["id"],
            checkup_date="2026-04-15",
            tenant_id="tenant_a",
            uploaded_by="u1",
        )
        self.assertTrue(upload["original_filename"].endswith("result.pdf"))

        stored = hc.resolve_upload_path("tenant_a", upload["file_path"])
        self.assertTrue(stored.is_file())

        after = hc.lookup_eligibility("tenant_a", "U01")
        self.assertEqual(after.records[0]["status"], "completed")
        self.assertEqual(len(after.uploads), 1)

    def test_tenant_isolation(self) -> None:
        hc.add_eligibility_manual(
            tenant_id="tenant_a",
            employee_no="X1",
            employee_name="A사원",
        )
        hc.add_eligibility_manual(
            tenant_id="tenant_b",
            employee_no="X1",
            employee_name="B사원",
        )
        a = hc.lookup_eligibility("tenant_a", "X1")
        b = hc.lookup_eligibility("tenant_b", "X1")
        self.assertEqual(a.records[0]["employee_name"], "A사원")
        self.assertEqual(b.records[0]["employee_name"], "B사원")

    def test_provider_not_live(self) -> None:
        self.assertFalse(hc.get_provider().is_live())
        self.assertFalse(hc.is_api_connected("tenant_a"))

    def test_lookup_not_found(self) -> None:
        result = hc.lookup_eligibility("tenant_a", "UNKNOWN999")
        self.assertFalse(result.eligible)
        self.assertEqual(result.records, [])


if __name__ == "__main__":
    unittest.main()
