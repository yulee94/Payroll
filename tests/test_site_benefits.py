"""
tests/test_site_benefits.py - 사업장별 특수 급여 항목
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.payroll.site_benefits import (
    _header_matches_workers_day,
    apply_site_benefits_to_invoice,
    calc_identity_guarantee_insurance_deduction,
    calc_workers_day_allowance,
    find_workers_day_column,
    identity_insurance_already_applied,
    resolve_site_benefits,
)
from payroll_builder import build_payroll_records, _apply_site_benefits_and_recalc_gross
from services.payroll_settings_store import (
    save_site_benefits_config,
    save_tenant_site_benefits_defaults,
)


class SiteBenefitsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._root = Path(self._tmpdir.name)
        self._global_path = self._root / "config" / "payroll_settings.json"
        self._global_path.parent.mkdir(parents=True)
        self._global_path.write_text(
            json.dumps(
                {
                    "default_workplace_hours_policy": {"mode": "fixed", "hours": 209},
                    "site_benefits_defaults": {
                        "workers_day_allowance": {
                            "enabled": False,
                            "default_amount": 0,
                            "auto_from_invoice": True,
                        },
                        "identity_guarantee_insurance": {
                            "enabled": False,
                            "annual_amount": 0,
                            "billing_month": 3,
                        },
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self._patches = [
            patch(
                "services.payroll_settings_store.GLOBAL_SETTINGS_PATH",
                self._global_path,
            ),
            patch(
                "services.payroll_settings_store.app_data_dir",
                return_value=self._root,
            ),
            patch(
                "services.payroll_settings_store.get_active_tenant_id",
                return_value="t_benefits",
            ),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_resolve_site_to_tenant_fallback(self) -> None:
        save_tenant_site_benefits_defaults(
            workers_day={"enabled": True, "default_amount": 10000, "auto_from_invoice": True},
            identity_insurance={"enabled": True, "annual_amount": 50000, "billing_month": 3},
        )
        resolved = resolve_site_benefits("테스트사업장")
        self.assertTrue(resolved["workers_day_allowance"]["enabled"])
        self.assertEqual(resolved["workers_day_source"], "tenant")
        self.assertEqual(resolved["identity_guarantee_insurance"]["annual_amount"], 50000)

    def test_site_override(self) -> None:
        save_tenant_site_benefits_defaults(
            workers_day={"enabled": True, "default_amount": 10000, "auto_from_invoice": True},
        )
        save_site_benefits_config(
            "한국앰코",
            workers_day={"enabled": True, "default_amount": 15000, "auto_from_invoice": False},
        )
        resolved = resolve_site_benefits("한국앰코")
        self.assertEqual(resolved["workers_day_source"], "site")
        self.assertFalse(resolved["workers_day_allowance"]["auto_from_invoice"])
        self.assertEqual(resolved["workers_day_allowance"]["default_amount"], 15000)

    def test_workers_day_from_invoice(self) -> None:
        save_site_benefits_config(
            "한국앰코",
            workers_day={"enabled": True, "default_amount": 0, "auto_from_invoice": True},
        )
        inv = {"name": "홍길동", "workers_day_pay": 20000, "base_salary": 2_000_000}
        amt = calc_workers_day_allowance(
            inv,
            resolve_site_benefits("한국앰코")["workers_day_allowance"],
            payroll_period="2026-05",
        )
        self.assertEqual(amt, 20000)

    def test_workers_day_default_in_may(self) -> None:
        cfg = {"enabled": True, "default_amount": 12000, "auto_from_invoice": False}
        self.assertEqual(calc_workers_day_allowance({}, cfg, payroll_period="2026-05"), 12000)
        self.assertEqual(calc_workers_day_allowance({}, cfg, payroll_period="2026-04"), 0)

    def test_identity_insurance_once_per_year(self) -> None:
        save_site_benefits_config(
            "한국앰코",
            identity_insurance={"enabled": True, "annual_amount": 30000, "billing_month": 3},
        )
        cfg = resolve_site_benefits("한국앰코")["identity_guarantee_insurance"]
        ded1 = calc_identity_guarantee_insurance_deduction(
            cfg,
            payroll_period="2026-03",
            workplace="한국앰코",
            employee_name="김철수",
        )
        self.assertEqual(ded1, -30000)
        apply_site_benefits_to_invoice(
            {"name": "김철수"},
            workplace="한국앰코",
            payroll_period="2026-03",
        )
        ded2 = calc_identity_guarantee_insurance_deduction(
            cfg,
            payroll_period="2026-03",
            workplace="한국앰코",
            employee_name="김철수",
        )
        self.assertEqual(ded2, 0)
        self.assertTrue(
            identity_insurance_already_applied(
                "한국앰코", "김철수", "2026-04"
            )
        )

    def test_apply_recalc_gross(self) -> None:
        save_site_benefits_config(
            "한국앰코",
            workers_day={"enabled": True, "default_amount": 0, "auto_from_invoice": True},
        )
        inv = {
            "name": "이영희",
            "base_salary": 2_000_000,
            "base_deduction": 0,
            "ot_pay": 0,
            "shift_pay": 0,
            "night_pay": 0,
            "special_pay": 0,
            "special_ext_pay": 0,
            "position_pay": 0,
            "transport": 100_000,
            "workers_day_pay": 15000,
        }
        _apply_site_benefits_and_recalc_gross(
            inv, workplace="한국앰코", payroll_period="2026-05"
        )
        self.assertEqual(inv["workers_day_allowance"], 15000)
        self.assertEqual(inv["subtotal"], 2_015_000)
        self.assertEqual(inv["gross_pay"], 2_115_000)

    def test_supplied_config_application_shape_for_rust_parity(self) -> None:
        save_site_benefits_config(
            "한국앰코",
            workers_day={"enabled": True, "default_amount": 12000, "auto_from_invoice": False},
            identity_insurance={"enabled": True, "annual_amount": 20000, "billing_month": 5},
        )
        inv = {
            "name": "박민수",
            "workplace": "한국앰코",
            "base_salary": 2_090_000,
            "workers_day_pay": 99999,
        }

        applied = apply_site_benefits_to_invoice(
            inv,
            workplace="한국앰코",
            payroll_period="2026-05",
            prior_records=[],
            persist_ledger=False,
        )

        self.assertEqual(
            applied,
            {
                "workers_day_allowance": 12000,
                "identity_guarantee_insurance_deduction": -20000,
                "workers_day_source": "site",
                "identity_insurance_source": "site",
            },
        )
        self.assertEqual(inv["workers_day_allowance"], 12000)
        self.assertEqual(inv["identity_guarantee_insurance_deduction"], -20000)
        self.assertEqual(inv["_workers_day_source"], "site")
        self.assertEqual(inv["_identity_insurance_source"], "site")

        already_applied = calc_identity_guarantee_insurance_deduction(
            {"enabled": True, "annual_amount": 20000, "billing_month": 5},
            payroll_period="2026-05",
            workplace="한국앰코",
            employee_name="박민수",
            prior_records=[
                {
                    "name": "박민수",
                    "workplace": "한국앰코",
                    "identity_guarantee_insurance_deduction": -20000,
                }
            ],
        )
        self.assertEqual(already_applied, 0)

    def test_build_payroll_records_includes_benefits(self) -> None:
        save_site_benefits_config(
            "한국앰코",
            workers_day={"enabled": True, "default_amount": 0, "auto_from_invoice": True},
            identity_insurance={"enabled": True, "annual_amount": 20000, "billing_month": 5},
        )
        inv = {
            "name": "박민수",
            "dept": "",
            "base_hourly": 10000,
            "ordinary_hourly": 12000,
            "base_days": 209,
            "work_days": 209,
            "unpaid_days": 0,
            "leave_days": 0,
            "ot_hours": 0,
            "shift_hours": 0,
            "night_hours": 0,
            "special_hours": 0,
            "special_ext_hours": 0,
            "early_leave_hours": 0,
            "base_salary": 2_090_000,
            "base_deduction": 0,
            "ot_pay": 0,
            "night_pay": 0,
            "special_pay": 0,
            "special_ext_pay": 0,
            "position_pay": 0,
            "shift_pay": 0,
            "annual_pay": 0,
            "transport": 0,
            "subtotal": 2_090_000,
            "gross_pay": 2_090_000,
            "workers_day_pay": 10000,
            "health_insurance": 0,
            "long_term_care": 0,
            "national_pension": 0,
            "employment_insurance": 0,
            "insurance_total": 0,
        }
        roster = {
            "박민수": {
                "성명": "박민수",
                "근무지": "한국앰코",
                "기본시급": 10000,
                "통상시급": 12000,
            }
        }
        records, _warnings = build_payroll_records(
            [inv],
            {},
            {},
            employee_roster=roster,
            payroll_period="2026-05",
        )
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["workers_day_allowance"], 10000)
        self.assertEqual(rec["identity_guarantee_insurance_deduction"], -20000)
        self.assertGreaterEqual(rec["gross_pay"], 2_090_000 + 10000)
        self.assertGreaterEqual(rec["total_deduction"], 20000)

    def test_header_matches_workers_day(self) -> None:
        self.assertTrue(_header_matches_workers_day("근로자의 날"))
        self.assertTrue(_header_matches_workers_day("근로자의날수당"))
        self.assertFalse(_header_matches_workers_day("교통비"))

    def test_find_workers_day_column(self) -> None:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.cell(3, 30, "근로자의 날")
        col = find_workers_day_column(ws)
        self.assertEqual(col, 30)
        wb.close()


if __name__ == "__main__":
    unittest.main()
