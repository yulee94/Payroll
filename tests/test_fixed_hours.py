"""
tests/test_fixed_hours.py - 근로계약·사업장 직군별 고정 근로시간
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.payroll.fixed_hours import (
    FIXED_HOURS_SOURCE_CONTRACT,
    FIXED_HOURS_SOURCE_TEMPLATE,
    PAY_TYPE_MONTHLY_SALARY,
    apply_fixed_hours_to_invoice,
    contract_to_fixed_hours_profile,
    infer_job_group_from_roster,
    normalize_contract_fixed_hours_fields,
    resolve_employee_fixed_hours,
    resolve_job_group_template,
)
from core.payroll.invoice_audit import audit_invoice_row
from payroll_builder import _apply_roster_hourly_and_recalc
from services.payroll_settings_store import (
    save_job_group_fixed_hours_template,
    save_site_security_cleaning_flag,
)


class FixedHoursTests(unittest.TestCase):
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
            patch("services.payroll_settings_store.get_active_tenant_id", return_value="t_fixed"),
            patch("core.payroll.fixed_hours.get_active_tenant_id", return_value="t_fixed", create=True),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_contract_normalize_salaried(self) -> None:
        row = {
            "employee_name": "김관리",
            "fixed_hours_mode": "예",
            "monthly_fixed_hours": "209",
            "fixed_overtime_hours": "10",
            "fixed_extension_hours": "20",
            "pay_type": "연봉직",
            "job_group": "관리",
        }
        normalize_contract_fixed_hours_fields(row)
        prof = contract_to_fixed_hours_profile(row)
        self.assertTrue(prof["fixed_hours_mode"])
        self.assertEqual(prof["pay_type"], PAY_TYPE_MONTHLY_SALARY)
        self.assertEqual(prof["fixed_overtime_hours"], 10.0)
        self.assertEqual(prof["fixed_extension_hours"], 20.0)

    def test_site_template_inheritance(self) -> None:
        save_site_security_cleaning_flag("강남경비", True)
        save_job_group_fixed_hours_template(
            "강남경비",
            "경비",
            monthly_fixed_hours=200,
            fixed_overtime_hours=8,
            fixed_extension_hours=12,
            pay_type="hourly",
        )
        prof = resolve_employee_fixed_hours(
            employee_name="이경비",
            workplace="강남경비",
            job_group="경비",
            contracts=[],
        )
        self.assertIsNotNone(prof)
        assert prof is not None
        self.assertEqual(prof["source_label"], FIXED_HOURS_SOURCE_TEMPLATE)
        self.assertEqual(prof["monthly_fixed_hours"], 200.0)
        self.assertEqual(prof["fixed_overtime_hours"], 8.0)
        self.assertEqual(prof["fixed_extension_hours"], 12.0)

    def test_contract_overrides_template(self) -> None:
        save_job_group_fixed_hours_template(
            "강남경비",
            "경비",
            monthly_fixed_hours=200,
            pay_type="hourly",
        )
        contracts = [
            {
                "id": "c1",
                "employee_name": "박경비",
                "status": "유효",
                "fixed_hours_mode": True,
                "monthly_fixed_hours": 180,
                "fixed_overtime_hours": 5,
                "fixed_extension_hours": 15,
                "pay_type": "hourly",
                "job_group": "경비",
            }
        ]
        prof = resolve_employee_fixed_hours(
            employee_name="박경비",
            workplace="강남경비",
            contracts=contracts,
        )
        self.assertIsNotNone(prof)
        assert prof is not None
        self.assertEqual(prof["source_label"], FIXED_HOURS_SOURCE_CONTRACT)
        self.assertEqual(prof["monthly_fixed_hours"], 180.0)

    def test_payroll_uses_fixed_not_invoice_hours(self) -> None:
        inv = {
            "name": "최연봉",
            "work_days": 150,
            "base_days": 150,
            "ot_hours": 5,
            "special_hours": 3,
            "base_hourly": 10000,
            "base_salary": 1500000,
        }
        emp = {
            "성명": "최연봉",
            "근무지": "강남경비",
            "업무": "경비",
            "기본시급": 10000,
            "통상시급": 12000,
        }
        contracts = [
            {
                "employee_name": "최연봉",
                "status": "유효",
                "fixed_hours_mode": True,
                "monthly_fixed_hours": 209,
                "fixed_overtime_hours": 10,
                "fixed_extension_hours": 20,
                "pay_type": "monthly_salary",
                "job_group": "경비",
            }
        ]

        with patch("core.payroll.fixed_hours.load_hr_contracts", return_value=contracts):
            _apply_roster_hourly_and_recalc(inv, emp)

        self.assertTrue(inv.get("_fixed_hours_mode"))
        self.assertEqual(inv["_monthly_work_hours"], 209.0)
        self.assertEqual(inv["base_salary"], 2090000)
        self.assertEqual(inv["ot_hours"], 20.0)
        self.assertEqual(inv["special_hours"], 10.0)
        self.assertEqual(inv["ot_pay"], round(12000 * 20 * 1.5))
        self.assertEqual(inv["special_pay"], round(12000 * 10 * 1.5))

    def test_infer_job_group_from_roster(self) -> None:
        self.assertEqual(infer_job_group_from_roster({"업무": "야간경비"}), "경비")
        self.assertEqual(infer_job_group_from_roster({"업무": "환경미화"}), "미화")
        self.assertEqual(infer_job_group_from_roster({"고용형태": "정규직(연봉)"}), "관리")

    def test_audit_shows_contract_fixed_label(self) -> None:
        inv = {
            "name": "홍길동",
            "base_days": 150,
            "work_days": 150,
            "base_hourly": 10000,
            "base_salary": 2090000,
        }
        contracts = [
            {
                "employee_name": "홍길동",
                "status": "유효",
                "fixed_hours_mode": True,
                "monthly_fixed_hours": 209,
                "job_group": "경비",
            }
        ]
        with patch("core.payroll.fixed_hours.load_hr_contracts", return_value=contracts):
            row = audit_invoice_row(inv, workplace="강남경비")
        self.assertTrue(row.get("fixed_hours_mode"))
        self.assertIn("근로계약서", row.get("fixed_hours_source", ""))
        self.assertTrue(any("근로계약서" in f for f in row.get("flags", [])))

    def test_apply_fixed_preserves_invoice_for_validation(self) -> None:
        inv = {"work_days": 180, "ot_hours": 3, "special_hours": 2}
        prof = {
            "fixed_hours_mode": True,
            "monthly_fixed_hours": 209,
            "fixed_overtime_hours": 10,
            "fixed_extension_hours": 15,
            "source_label": FIXED_HOURS_SOURCE_CONTRACT,
        }
        apply_fixed_hours_to_invoice(inv, prof)
        self.assertEqual(inv["_invoice_work_days"], 180)
        self.assertEqual(inv["_invoice_ot_hours"], 3)
        self.assertEqual(inv["ot_hours"], 15)
        self.assertEqual(inv["special_hours"], 10)

    def test_resolve_template_requires_security_cleaning_flag(self) -> None:
        tpl = resolve_job_group_template("경비", {"security_cleaning": False, "job_group_templates": {}})
        self.assertIsNone(tpl)


if __name__ == "__main__":
    unittest.main()
