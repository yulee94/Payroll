"""
tests/test_invoice_audit.py - 청구서 급여 자동검열
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.payroll.invoice_audit import audit_invoice_payroll, audit_invoice_row
from core.payroll.fixed_hours import (
    FIXED_HOURS_SOURCE_CONTRACT,
    PAY_TYPE_MONTHLY_SALARY,
)
from services.payroll_settings_store import save_workplace_hours_policy
from services.workplace_hours import MODE_FIXED, MODE_INVOICE_WORK


class InvoiceAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._root = Path(self._tmpdir.name)
        self._global_path = self._root / "config" / "payroll_settings.json"
        self._global_path.parent.mkdir(parents=True)
        self._global_path.write_text(
            json.dumps(
                {
                    "default_workplace_hours_policy": {"mode": "fixed", "hours": 209},
                    "workplace_hours_policies": {},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self._patches = [
            patch("services.payroll_settings_store.GLOBAL_SETTINGS_PATH", self._global_path),
            patch("services.payroll_settings_store.app_data_dir", return_value=self._root),
            patch("services.payroll_settings_store.get_active_tenant_id", return_value="t_audit"),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_pass_when_base_salary_matches(self) -> None:
        save_workplace_hours_policy("앰코", mode=MODE_FIXED, hours=209)
        inv = {
            "name": "홍길동",
            "base_days": 209,
            "work_days": 200,
            "base_hourly": 10000,
            "base_salary": 2090000,
        }
        row = audit_invoice_row(inv, workplace="앰코")
        self.assertEqual(row["status"], "pass")
        self.assertEqual(row["applied_monthly_hours"], 209.0)
        self.assertEqual(row["calc_base_salary"], 2090000)

    def test_warn_missing_invoice_work_hours(self) -> None:
        save_workplace_hours_policy("앰코", mode=MODE_INVOICE_WORK, hours=209)
        inv = {"name": "김철수", "base_days": 209, "work_days": 0, "base_hourly": 9000}
        row = audit_invoice_row(inv, workplace="앰코")
        self.assertEqual(row["status"], "warn")
        self.assertTrue(any("근무시간" in f for f in row["flags"]))

    def test_audit_batch_summary(self) -> None:
        save_workplace_hours_policy("앰코", mode=MODE_FIXED, hours=209)
        invoices = [
            {
                "name": "A",
                "base_days": 209,
                "work_days": 209,
                "base_hourly": 10000,
                "base_salary": 2090000,
            },
            {
                "name": "B",
                "base_days": 209,
                "work_days": 209,
                "base_hourly": 10000,
                "base_salary": 1000,
            },
        ]
        result = audit_invoice_payroll(invoices, workplace="앰코")
        self.assertEqual(result["summary"]["total"], 2)
        self.assertEqual(result["warn_count"], 1)
        self.assertEqual(result["pass_count"], 1)

    def test_supplied_policy_record_mismatch_for_rust_parity(self) -> None:
        inv = {
            "name": "박감사",
            "base_days": 209,
            "work_days": 200,
            "base_salary": 2_000_000,
        }
        record = {"name": "박감사", "base_hourly": 10_000, "_monthly_work_hours": 208}

        row = audit_invoice_row(
            inv,
            workplace="앰코",
            policy={"mode": MODE_FIXED, "hours": 209},
            record=record,
        )

        self.assertEqual(row["status"], "warn")
        self.assertEqual(row["status_label"], "확인")
        self.assertEqual(row["applied_monthly_hours"], 209.0)
        self.assertEqual(row["calc_base_salary"], 2_090_000)
        self.assertEqual(
            row["formula"], "기본시급 10,000원 × 209시간 = 2,090,000원"
        )
        self.assertIn(
            "기본급 불일치: 산출 2,090,000원 vs 청구서 2,000,000원",
            row["flags"],
        )
        self.assertIn("대장 적용시간(208h)과 재검열(209h) 상이", row["flags"])
        self.assertEqual(row["break_hours"], 9.0)

    def test_fixed_profile_audit_composes_flags_for_rust_parity(self) -> None:
        inv = {
            "name": "최연봉",
            "base_days": 150,
            "work_days": 150,
            "ot_hours": 5,
            "special_hours": 3,
            "special_ext_hours": 2,
            "base_hourly": 10_000,
            "base_salary": 2_090_000,
        }
        profile = {
            "fixed_hours_mode": True,
            "monthly_fixed_hours": 209,
            "daily_fixed_hours": 0,
            "fixed_overtime_hours": 10,
            "fixed_extension_hours": 20,
            "pay_type": PAY_TYPE_MONTHLY_SALARY,
            "job_group": "경비",
            "source": "contract",
            "source_label": FIXED_HOURS_SOURCE_CONTRACT,
            "contract_id": "c1",
        }

        with patch(
            "core.payroll.invoice_audit.resolve_employee_fixed_hours",
            return_value=profile,
        ):
            row = audit_invoice_row(
                inv,
                workplace="강남경비",
                policy={"mode": MODE_FIXED, "hours": 209},
            )

        self.assertEqual(row["status"], "warn")
        self.assertTrue(row["fixed_hours_mode"])
        self.assertEqual(row["fixed_hours_source"], FIXED_HOURS_SOURCE_CONTRACT)
        self.assertEqual(row["hours_source"], FIXED_HOURS_SOURCE_CONTRACT)
        self.assertEqual(row["applied_monthly_hours"], 209.0)
        self.assertEqual(row["calc_base_salary"], 2_090_000)
        self.assertEqual(
            row["flags"][:5],
            [
                "근로계약서 기준 고정 (경비)",
                "급여형태: 연봉직",
                "청구서 연장(5h) ≠ 계약 고정(20h)",
                "청구서 특근(3h) ≠ 계약 고정(10h)",
                "청구서 근무시간(150h) ≠ 계약 월시간(209h)",
            ],
        )

    def test_break_hours_from_policy(self) -> None:
        save_workplace_hours_policy(
            "앰코",
            mode=MODE_FIXED,
            hours=209,
            daily_hours=8,
            break_minutes=60,
        )
        inv = {"name": "이영희", "base_days": 209, "work_days": 20, "base_hourly": 0}
        row = audit_invoice_row(inv, workplace="앰코")
        self.assertAlmostEqual(row["break_hours"] or 0, 20.0, places=2)


if __name__ == "__main__":
    unittest.main()
