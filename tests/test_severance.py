"""
tests/test_severance.py - 퇴직금·중간정산 산출

실행:
  cd 급여프로그램
  python -m unittest tests.test_severance -v
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from core.hr import severance as sev
from core.hr.severance import InterimSettlement, calculate_severance, calculate_service_period


def _mock_payroll(records_by_period: dict[str, list[dict]]):
    def _load(period: str, _tenant: str) -> list[dict]:
        return records_by_period.get(period, [])

    return _load


class TestServicePeriod(unittest.TestCase):
    def test_one_year(self) -> None:
        hire = date(2020, 1, 1)
        resign = date(2020, 12, 31)
        sp = calculate_service_period(hire, resign)
        self.assertEqual(sp.days, 366)  # 2020 leap year
        self.assertAlmostEqual(sp.years, 366 / 365, places=4)

    def test_partial_year(self) -> None:
        hire = date(2023, 6, 1)
        resign = date(2024, 5, 31)
        sp = calculate_service_period(hire, resign)
        self.assertEqual(sp.days, 366)
        self.assertIn("년", sp.display)


class TestAverageWage(unittest.TestCase):
    def test_three_month_sum_and_average(self) -> None:
        resign = date(2026, 6, 15)
        payroll = {
            "2026-03": [{"name": "홍길동", "gross_pay": 3_000_000, "national_pension": 100_000,
                         "health_insurance": 100_000, "long_term_care": 10_000, "employment_insurance": 20_000}],
            "2026-04": [{"name": "홍길동", "gross_pay": 3_100_000, "national_pension": 100_000,
                         "health_insurance": 100_000, "long_term_care": 10_000, "employment_insurance": 20_000}],
            "2026-05": [{"name": "홍길동", "gross_pay": 3_200_000, "national_pension": 100_000,
                         "health_insurance": 100_000, "long_term_care": 10_000, "employment_insurance": 20_000}],
            "2026-06": [{"name": "홍길동", "gross_pay": 3_300_000, "national_pension": 100_000,
                         "health_insurance": 100_000, "long_term_care": 10_000, "employment_insurance": 20_000}],
        }
        rows, total, ins, avg, warnings = sev.calculate_average_wage(
            "홍길동",
            resign,
            tenant_id="test",
            load_payroll_fn=_mock_payroll(payroll),
        )
        self.assertEqual(len(rows), 4)
        self.assertGreater(total, 0)
        self.assertGreater(ins, 0)
        self.assertGreater(avg, 0)
        _, _, calendar_days = sev.three_month_window(resign)
        self.assertAlmostEqual(avg, total / calendar_days, places=2)

    def test_missing_month_warns(self) -> None:
        resign = date(2026, 6, 15)
        payroll = {
            "2026-04": [{"name": "김철수", "gross_pay": 2_000_000}],
            "2026-05": [{"name": "김철수", "gross_pay": 2_000_000}],
            "2026-06": [{"name": "김철수", "gross_pay": 2_000_000}],
        }
        _, _, _, _, warnings = sev.calculate_average_wage(
            "김철수",
            resign,
            tenant_id="test",
            load_payroll_fn=_mock_payroll(payroll),
        )
        self.assertTrue(any("없음" in w for w in warnings))


class TestSeveranceCalculation(unittest.TestCase):
    def test_statutory_formula(self) -> None:
        resign = date(2026, 6, 15)
        hire = date(2021, 6, 15)
        monthly_gross = 3_000_000
        payroll = {
            p: [{"name": "이영희", "gross_pay": monthly_gross,
                 "national_pension": 50_000, "health_insurance": 50_000,
                 "long_term_care": 5_000, "employment_insurance": 10_000}]
            for p in ("2026-03", "2026-04", "2026-05", "2026-06")
        }
        result = calculate_severance(
            "이영희",
            resign,
            hire,
            interim_settlements=[],
            tenant_id="test",
            load_payroll_fn=_mock_payroll(payroll),
        )
        expected = round(result.average_daily_wage * 30 * result.service.years)
        self.assertEqual(result.statutory_severance, expected)
        self.assertEqual(result.final_severance, expected)

    def test_interim_deduction(self) -> None:
        resign = date(2026, 6, 15)
        hire = date(2016, 1, 1)
        payroll = {
            p: [{"name": "박민수", "gross_pay": 4_000_000}]
            for p in ("2026-03", "2026-04", "2026-05", "2026-06")
        }
        interim = [
            InterimSettlement(id="i1", employee_name="박민수", date="2021-05-15", amount=5_000_000, reason="5년"),
            InterimSettlement(id="i2", employee_name="박민수", date="2024-05-15", amount=3_000_000, reason="추가"),
        ]
        result = calculate_severance(
            "박민수",
            resign,
            hire,
            interim_settlements=interim,
            tenant_id="test",
            load_payroll_fn=_mock_payroll(payroll),
        )
        self.assertEqual(result.interim_total, 8_000_000)
        self.assertEqual(result.final_severance, max(0, result.statutory_severance - 8_000_000))


class TestInterimStorage(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._root = Path(self._tmpdir)
        self._patcher = patch("core.paths.app_data_dir", return_value=self._root)
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_save_and_list(self) -> None:
        item = InterimSettlement(id="", employee_name="테스트", date="2024-01-01", amount=1_000_000, reason="중간")
        saved = sev.save_interim_settlement(item, tenant_id="t1")
        self.assertTrue(saved.id)
        listed = sev.list_interim_settlements("테스트", tenant_id="t1")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].amount, 1_000_000)

    def test_delete(self) -> None:
        item = sev.save_interim_settlement(
            InterimSettlement(id="", employee_name="삭제", date="2024-01-01", amount=500_000),
            tenant_id="t1",
        )
        self.assertTrue(sev.delete_interim_settlement(item.id, tenant_id="t1"))
        self.assertEqual(sev.list_interim_settlements("삭제", tenant_id="t1"), [])


if __name__ == "__main__":
    unittest.main()
