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
