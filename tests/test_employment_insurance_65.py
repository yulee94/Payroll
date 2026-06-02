"""tests/test_employment_insurance_65.py - 만 65세 고용보험 KCOMWEL 확인."""

from __future__ import annotations

import csv
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from core.payroll import employment_insurance_65 as ei65
from core.payroll_calc_rules import resolve_social_insurance
from utils import calc_employment_insurance


class TestEmploymentInsurance65(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        root = Path(self._tmpdir)
        self._root_patcher = patch.object(ei65, "_EI65_ROOT", root)
        self._root_patcher.start()
        self._tenant_patcher = patch.object(ei65, "session_tenant_id", return_value="t1")
        self._tenant_patcher.start()
        self.addCleanup(self._root_patcher.stop)
        self.addCleanup(self._tenant_patcher.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_age_detection_from_rrn(self) -> None:
        self.assertTrue(ei65.is_age_65_plus("500615-1", as_of=date(2026, 5, 31)))
        self.assertFalse(ei65.is_age_65_plus("650601-1", as_of=date(2026, 5, 31)))
        self.assertEqual(ei65.age_years_from_identity("600501-1", as_of=date(2026, 5, 31)), 66)

    def test_premium_zero_no_deduction(self) -> None:
        ei65.add_verification_manual(
            employee_name="김순자",
            premium_amount=0,
            management_no="1234567890",
        )
        inv = {"name": "김순자", "gross_pay": 3_000_000}
        resolve_social_insurance(
            inv,
            identity="500615-1",
            payroll_period="2026-05",
            emp_roster={"성명": "김순자", "사번": "E1"},
        )
        self.assertEqual(inv["national_pension"], 0)
        self.assertEqual(inv["health_insurance"], 0)
        self.assertEqual(inv["employment_insurance"], 0)
        self.assertEqual(inv["ei_65_status"], "exempt")

    def test_premium_positive_deduction(self) -> None:
        ei65.add_verification_manual(
            employee_name="박대표",
            premium_amount=15_000,
            management_no="9876543210",
        )
        gross = 4_000_000
        inv = {"name": "박대표", "gross_pay": gross}
        resolve_social_insurance(
            inv,
            identity="500615-1",
            payroll_period="2026-05",
            emp_roster={"성명": "박대표"},
        )
        expected_ei = calc_employment_insurance(gross)
        self.assertEqual(inv["employment_insurance"], expected_ei)
        self.assertEqual(inv["ei_65_status"], "liable")
        self.assertTrue(inv.get("ei_65_liable"))

    def test_unknown_status_warning_and_skip_default(self) -> None:
        ei65.set_unknown_default("skip")
        result = ei65.resolve_ei_65_for_payroll(
            identity="500615-1",
            payroll_period="2026-05",
            employee_name="미확인",
        )
        self.assertEqual(result.status, "unknown")
        self.assertFalse(result.deduct_employment_insurance)
        self.assertIn("미확인", result.warning)

        inv = {"name": "미확인", "gross_pay": 2_500_000}
        resolve_social_insurance(
            inv,
            identity="500615-1",
            payroll_period="2026-05",
            emp_roster={"성명": "미확인"},
        )
        self.assertEqual(inv["employment_insurance"], 0)
        self.assertIn("ei_65_warning", inv)

    def test_unknown_deduct_default(self) -> None:
        ei65.set_unknown_default("deduct")
        gross = 2_500_000
        inv = {"name": "미확인2", "gross_pay": gross}
        resolve_social_insurance(
            inv,
            identity="500615-1",
            payroll_period="2026-05",
            emp_roster={"성명": "미확인2"},
        )
        self.assertEqual(inv["employment_insurance"], calc_employment_insurance(gross))

    def test_csv_import(self) -> None:
        path = Path(self._tmpdir) / "kcomwel.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["관리번호", "성명", "부과고지보험료", "조회일"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "관리번호": "111",
                    "성명": "이순신",
                    "부과고지보험료": "0",
                    "조회일": "2026-05-01",
                }
            )
        summary = ei65.import_verifications_csv(path)
        self.assertEqual(summary["imported_count"], 1)
        rec = ei65.get_latest_verification(employee_name="이순신")
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertEqual(rec.status, "exempt")

    def test_list_65_plus_roster(self) -> None:
        roster = {
            "a": {"성명": "젊은이", "주민번호": "900101-1"},
            "b": {"성명": "어르신", "주민번호": "500615-1", "근무지": "한국앰코"},
        }
        rows = ei65.list_65_plus_roster_rows(
            roster,
            payroll_period="2026-05",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["employee_name"], "어르신")
        self.assertEqual(rows[0]["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
