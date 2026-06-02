"""연령별 혜택·국가지원 추천·질문 라우팅."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import unittest

from services.age_benefit_advisor import (
    format_benefit_answer_for_person,
    is_benefit_related_question,
    scan_roster_age_benefits,
    try_answer_age_benefit_question,
)
from services.korean_age_benefits import programs_for_age


class TestProgramsForAge(unittest.TestCase):
    def test_age_66_includes_insurance_exempt(self) -> None:
        titles = {p.id for p in programs_for_age(66)}
        self.assertIn("insurance_exempt_65", titles)
        self.assertIn("senior_internship_60", titles)

    def test_age_62_pension_window(self) -> None:
        titles = {p.id for p in programs_for_age(62)}
        self.assertIn("pension_workplace_60", titles)
        self.assertNotIn("insurance_exempt_65", titles)

    def test_age_25_youth_programs(self) -> None:
        titles = {p.id for p in programs_for_age(25)}
        self.assertIn("youth_tomorrow", titles)
        self.assertNotIn("insurance_exempt_65", titles)


class TestBenefitQuestionRouting(unittest.TestCase):
    def test_keyword_detection(self) -> None:
        self.assertTrue(is_benefit_related_question("65세 4대보험 면제 알려줘"))
        self.assertFalse(is_benefit_related_question("5월 급여 합계"))

    @patch("services.age_benefit_advisor.load_roster_rows_secured")
    @patch("services.age_benefit_advisor.enforce_session_tenant_access")
    def test_scan_finds_senior(self, mock_enforce, mock_rows) -> None:
        from core.session_service import UserSession

        sess = UserSession(
            user_id="u1",
            tenant_id="t1",
            username="u",
            display_name="담당",
            role="admin",
        )
        mock_enforce.return_value = sess
        mock_rows.return_value = [
            {
                "성명": "김철수",
                "주민번호": "600501-1",
                "부서": "총무",
            },
        ]
        scan = scan_roster_age_benefits("t1", session=sess, as_of=date(2026, 5, 31))
        self.assertTrue(scan.has_recommendations)
        self.assertEqual(scan.matches[0].name, "김철수")
        self.assertGreaterEqual(scan.matches[0].age, 65)

    @patch("services.age_benefit_advisor.format_benefit_answer_for_person")
    @patch("services.age_benefit_advisor.is_benefit_related_question", return_value=True)
    def test_person_question_routes(self, _kw, mock_person) -> None:
        from core.session_service import UserSession

        sess = UserSession(
            user_id="u1",
            tenant_id="t1",
            username="u",
            display_name="담당",
            role="admin",
        )
        mock_person.return_value = "상세 답변"
        ans = try_answer_age_benefit_question("홍길동 혜택 알려줘", sess)
        self.assertEqual(ans, "상세 답변")
        mock_person.assert_called_once()

    @patch("services.age_benefit_advisor.load_roster_rows_secured")
    @patch("services.age_benefit_advisor.enforce_session_tenant_access")
    def test_format_person_detail(self, mock_enforce, mock_rows) -> None:
        from core.session_service import UserSession

        sess = UserSession(
            user_id="u1",
            tenant_id="t1",
            username="u",
            display_name="담당",
            role="admin",
        )
        mock_enforce.return_value = sess
        mock_rows.return_value = [
            {"성명": "이영희", "주민번호": "650601-2", "부서": "인사"},
        ]
        text = format_benefit_answer_for_person(
            "이영희",
            "t1",
            session=sess,
            as_of=date(2026, 5, 31),
        )
        self.assertIsNotNone(text)
        assert text is not None
        self.assertIn("이영희", text)
        self.assertIn("만 60세", text)


if __name__ == "__main__":
    unittest.main()
