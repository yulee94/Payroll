"""연차사용대장 일별 표식 헬퍼 테스트."""

from __future__ import annotations

import unittest

from leave_calendar_marks import (
    LeaveMarkKind,
    aggregate_leave_usage_rows,
    build_day_marks,
    days_in_month,
    format_usage_dates_summary,
    parse_usage_memo,
    render_compact_calendar,
    render_month_mark_row,
    symbol_for_day,
)


class TestLeaveCalendarMarks(unittest.TestCase):
    def test_days_in_month_february_leap(self) -> None:
        self.assertEqual(days_in_month("2024-02"), 29)
        self.assertEqual(days_in_month("2025-02"), 28)

    def test_parse_full_and_half_from_memo(self) -> None:
        memo = "05월 01일 사용, 05월 02일 사용, 05월 반차(0.5일) 사용"
        marks = parse_usage_memo(memo, default_month=5)
        self.assertEqual(marks[1], LeaveMarkKind.FULL)
        self.assertEqual(marks[2], LeaveMarkKind.FULL)
        self.assertIn(LeaveMarkKind.HALF, marks.values())

    def test_parse_absence_memo(self) -> None:
        memo = "05월 03일 결근/무급, 05월 04일 결근/무급"
        marks = parse_usage_memo(memo, default_month=5, absence=True)
        self.assertEqual(marks[3], LeaveMarkKind.ABSENCE)
        self.assertEqual(marks[4], LeaveMarkKind.ABSENCE)

    def test_build_from_leave_dates(self) -> None:
        marks = build_day_marks(
            "2026-05",
            leave_dates=[3, 7, 15],
            leave_days=3.0,
        )
        self.assertEqual(marks[3], LeaveMarkKind.FULL)
        self.assertEqual(marks[7], LeaveMarkKind.FULL)
        self.assertEqual(marks[15], LeaveMarkKind.FULL)
        self.assertEqual(symbol_for_day(marks, 1), "·")

    def test_sequential_fill_when_no_dates(self) -> None:
        marks = build_day_marks("2026-01", leave_days=2.0)
        row = render_month_mark_row("2026-01", marks)
        self.assertTrue(row.startswith("●●"))
        self.assertEqual(len(row), days_in_month("2026-01"))

    def test_render_compact_calendar(self) -> None:
        marks = build_day_marks(
            "2026-05",
            leave_memo="05월 10일 사용",
            leave_days=1.0,
        )
        text = render_compact_calendar("2026-05", marks)
        self.assertTrue(text.startswith("05월 "))
        self.assertIn("●", text)

    def test_half_day_only_memo(self) -> None:
        marks = build_day_marks(
            "2026-05",
            leave_memo="05월 반차(0.5일) 사용",
            leave_days=0.5,
        )
        self.assertIn(LeaveMarkKind.HALF, marks.values())

    def test_format_usage_dates_summary(self) -> None:
        marks = build_day_marks(
            "2026-05",
            leave_memo="05월 01일 사용, 05월 12일 사용, 05월 반차(0.5일) 사용",
            leave_days=2.5,
        )
        summary = format_usage_dates_summary("2026-05", marks)
        self.assertIn("5/1(●)", summary)
        self.assertIn("5/12(●)", summary)
        self.assertIn("◐", summary)

    def test_aggregate_leave_usage_rows_by_employee(self) -> None:
        rows = [
            {
                "name": "홍길동",
                "workplace": "본사",
                "month_leave": 1.0,
                "leave_memo": "05월 01일 사용",
                "leave_sheet_leave_dates": [1],
            },
            {
                "name": "홍길동",
                "workplace": "본사",
                "month_leave": 1.0,
                "leave_memo": "05월 12일 사용",
                "leave_sheet_leave_dates": [12],
            },
            {
                "name": "김철수",
                "workplace": "본사",
                "month_leave": 0.5,
                "leave_memo": "05월 반차(0.5일) 사용",
            },
        ]
        agg = aggregate_leave_usage_rows(rows, "2026-05")
        self.assertEqual(len(agg), 2)
        by_name = {r["name"]: r for r in agg}
        self.assertEqual(by_name["홍길동"]["month_leave"], 2.0)
        self.assertIn("5/1(●)", by_name["홍길동"]["dates_summary"])
        self.assertIn("5/12(●)", by_name["홍길동"]["dates_summary"])
        self.assertEqual(by_name["김철수"]["month_leave"], 0.5)
        self.assertIn("◐", by_name["김철수"]["dates_summary"])


if __name__ == "__main__":
    unittest.main()
