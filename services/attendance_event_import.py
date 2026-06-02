"""
services/attendance_event_import.py - 카드 출퇴근 근태 xlsx (베스텍 밀양 등)

열 매핑 (1-based, 헤더 1행):
  A 카드번호, B 발생시각, C 이름, D 상태, E 근무조, F 장치명, G 출입(발열/마스크)

상태: 출근(얼굴) / 퇴근(얼굴)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl

from roster_constants import norm_name_key

COL_CARD = 1
COL_TIMESTAMP = 2
COL_NAME = 3
COL_STATUS = 4
COL_SHIFT = 5
COL_DEVICE = 6

CLOCK_IN_MARKERS = ("출근",)
CLOCK_OUT_MARKERS = ("퇴근",)


@dataclass
class AttendanceDaySummary:
    employee_name: str
    day: str
    clock_in: datetime | None = None
    clock_out: datetime | None = None
    work_minutes: float = 0.0
    work_hours: float = 0.0
    incomplete: bool = False


@dataclass
class AttendanceMonthSummary:
    employee_name: str
    period: str
    work_days: float = 0.0
    work_hours: float = 0.0
    days: list[AttendanceDaySummary] = field(default_factory=list)


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _is_clock_in(status: str) -> bool:
    s = str(status or "")
    return any(m in s for m in CLOCK_IN_MARKERS)


def _is_clock_out(status: str) -> bool:
    s = str(status or "")
    return any(m in s for m in CLOCK_OUT_MARKERS)


def load_attendance_events(path: Path) -> list[dict[str, Any]]:
    """원시 이벤트 목록."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    events: list[dict[str, Any]] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or len(row) < 4:
            continue
        name = row[COL_NAME - 1]
        if not name:
            continue
        ts = _parse_timestamp(row[COL_TIMESTAMP - 1])
        if ts is None:
            continue
        events.append(
            {
                "card": row[COL_CARD - 1],
                "at": ts,
                "name": str(name).strip(),
                "status": str(row[COL_STATUS - 1] or "").strip(),
                "shift": str(row[COL_SHIFT - 1] or "").strip(),
                "device": str(row[COL_DEVICE - 1] or "").strip(),
            }
        )
    wb.close()
    return events


def aggregate_attendance_month(
    path: Path,
    *,
    period: str,
    break_minutes: float = 0.0,
    cap_hours_per_day: float | None = None,
) -> dict[str, AttendanceMonthSummary]:
    """
    출퇴근 이벤트 → 직원별 월 집계.

    같은 날 첫 출근·마지막 퇴근으로 근무시간 산정. 퇴근만 있으면 incomplete.
    """
    by_emp_day: dict[tuple[str, str], AttendanceDaySummary] = {}
    for ev in load_attendance_events(path):
        name = ev["name"]
        day = ev["at"].strftime("%Y-%m-%d")
        key = (name, day)
        if key not in by_emp_day:
            by_emp_day[key] = AttendanceDaySummary(employee_name=name, day=day)
        day_sum = by_emp_day[key]
        if _is_clock_in(ev["status"]):
            if day_sum.clock_in is None or ev["at"] < day_sum.clock_in:
                day_sum.clock_in = ev["at"]
        elif _is_clock_out(ev["status"]):
            if day_sum.clock_out is None or ev["at"] > day_sum.clock_out:
                day_sum.clock_out = ev["at"]

    month_buckets: dict[str, AttendanceMonthSummary] = {}
    for (name, _day), day_sum in sorted(by_emp_day.items()):
        if day_sum.clock_in and day_sum.clock_out and day_sum.clock_out > day_sum.clock_in:
            minutes = (day_sum.clock_out - day_sum.clock_in).total_seconds() / 60.0
            minutes = max(0.0, minutes - break_minutes)
            day_sum.work_minutes = minutes
            day_sum.work_hours = minutes / 60.0
            if cap_hours_per_day is not None and cap_hours_per_day > 0:
                day_sum.work_hours = min(day_sum.work_hours, cap_hours_per_day)
        else:
            day_sum.incomplete = True
            if day_sum.clock_in and not day_sum.clock_out:
                day_sum.work_hours = 0.0
            elif day_sum.clock_out and not day_sum.clock_in:
                day_sum.incomplete = True

        if name not in month_buckets:
            month_buckets[name] = AttendanceMonthSummary(
                employee_name=name, period=period
            )
        bucket = month_buckets[name]
        bucket.days.append(day_sum)
        if day_sum.work_hours > 0:
            bucket.work_hours += day_sum.work_hours
            bucket.work_days += 1.0

    return month_buckets


def attendance_to_invoice_overrides(
    summaries: dict[str, AttendanceMonthSummary],
    *,
    use_as_monthly_hours: bool = False,
) -> dict[str, dict[str, Any]]:
    """
    명부·청구서 invoice_row 에 덮어쓸 근태 필드.

    기본(use_as_monthly_hours=False): 급여 산정용 work_days/base_days 는 건드리지 않고
    `_attendance_*` 메타만 기록(밀양 209h 고정 정책과 충돌 방지).

    use_as_monthly_hours=True: 사업장 정책이 실근로시간 반영일 때만 base/work 에 실시간 적용.
    """
    out: dict[str, dict[str, Any]] = {}
    for name, s in summaries.items():
        key = norm_name_key(name)
        patch: dict[str, Any] = {
            "_attendance_work_hours": round(s.work_hours, 4),
            "_attendance_work_days": round(s.work_days, 4),
            "_attendance_source": "event_xlsx",
        }
        if use_as_monthly_hours:
            patch["work_days"] = round(s.work_hours, 4)
            patch["base_days"] = round(s.work_hours, 4)
        out[key] = patch
    return out


def column_mapping_doc() -> str:
    return (
        "| 엑셀열 | 필드 | 비고 |\n"
        "|--------|------|------|\n"
        "| A | 카드번호 | |\n"
        "| B | 발생시각 | YYYY-MM-DD HH:MM:SS |\n"
        "| C | 이름 | 직원 성명 |\n"
        "| D | 상태 | 출근(얼굴), 퇴근(얼굴) |\n"
        "| E | 근무조 | |\n"
        "| F | 장치명 | 사무동, 공장(출근) 등 |\n"
        "| G | 출입(발열/마스크) | |\n"
    )
