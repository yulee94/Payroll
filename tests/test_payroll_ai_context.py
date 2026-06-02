"""
tests/test_payroll_ai_context.py - 급여 AI 컨텍스트 (사업장·기간 매칭)

실행:
  cd 급여프로그램
  python -m unittest tests.test_payroll_ai_context -v
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from services.payroll_ai_context import (
    build_payroll_context,
    extract_person_name,
    extract_workplace_from_text,
    parse_period_from_text,
)


class TestParsePeriod(unittest.TestCase):
    def test_month_only_prefers_current_year(self) -> None:
        available = ["2026-05", "2025-05"]
        self.assertEqual(parse_period_from_text("5월 급여", available), "2026-05")

    def test_year_month_explicit(self) -> None:
        available = ["2026-05", "2025-05"]
        self.assertEqual(parse_period_from_text("2026년 5월 엠코", available), "2026-05")


class TestWorkplaceExtraction(unittest.TestCase):
    def test_emco_short_name(self) -> None:
        wp = extract_workplace_from_text("5월 엠코 총급여", "coss")
        self.assertEqual(wp, "한국앰코")

    def test_emco_reordered_query(self) -> None:
        wp = extract_workplace_from_text("엠코 5월 급여", "coss")
        self.assertEqual(wp, "한국앰코")

    def test_amkor_variant(self) -> None:
        wp = extract_workplace_from_text("앰코 5월", "coss")
        self.assertEqual(wp, "한국앰코")

    def test_full_workplace_name(self) -> None:
        wp = extract_workplace_from_text("한국앰코생산 4월 급여", "coss")
        self.assertEqual(wp, "한국앰코")


class TestPersonNameExclusion(unittest.TestCase):
    def test_emco_not_person_when_workplace_conflict(self) -> None:
        from services.payroll_ai_context import _person_name_conflicts_with_workplace

        self.assertTrue(_person_name_conflicts_with_workplace("엠코", "한국앰코"))
        self.assertFalse(_person_name_conflicts_with_workplace("김철수", "한국앰코"))

    def test_real_person_still_extracted(self) -> None:
        self.assertEqual(extract_person_name("5월 김철수 급여"), "김철수")


class TestBuildPayrollContextSiteScope(unittest.TestCase):
    @patch("services.payroll_ai_context.load_payroll_records_secured")
    @patch("services.payroll_ai_context.list_available_periods")
    @patch("services.payroll_ai_context.tenant_data_scope_label", return_value="(주)코스")
    def test_may_emco_summary(
        self,
        _label,
        mock_periods,
        mock_load,
    ) -> None:
        mock_periods.return_value = ["2026-05", "2026-04"]
        mock_load.return_value = [
            {
                "name": "홍길동",
                "gross_pay": 3_000_000,
                "net_pay": 2_500_000,
                "total_deduction": 500_000,
                "base_salary": 2_000_000,
                "ot_pay": 0,
                "special_pay": 0,
                "transport": 0,
                "affiliate": "(주)코스",
                "workplace": "한국앰코스페셜티카톤즈",
                "_scope_workplace": "한국앰코",
            },
            {
                "name": "김영희",
                "gross_pay": 2_000_000,
                "net_pay": 1_700_000,
                "total_deduction": 300_000,
                "base_salary": 1_500_000,
                "ot_pay": 0,
                "special_pay": 0,
                "transport": 0,
                "affiliate": "(주)코스",
                "workplace": "한국앰코스페셜티카톤즈",
                "_scope_workplace": "한국앰코",
            },
            {
                "name": "타법인",
                "gross_pay": 9_000_000,
                "net_pay": 8_000_000,
                "total_deduction": 1_000_000,
                "affiliate": "ELSO",
                "workplace": "다른사업장",
                "_scope_workplace": "다른사업장",
            },
        ]

        ctx, direct = build_payroll_context("5월 엠코 총급여", "coss")

        self.assertIn("인식한 사업장: 한국앰코", ctx)
        self.assertIn("2026년 05월 · 한국앰코 요약", ctx)
        self.assertIn("인원 2명", ctx)
        self.assertIn("5,000,000원", ctx)
        self.assertNotIn("'엠코' 을(를) 찾지 못했습니다", ctx)
        self.assertIsNotNone(direct)
        assert direct is not None
        self.assertIn("한국앰코", direct)
        self.assertIn("5,000,000원", direct)


if __name__ == "__main__":
    unittest.main()
