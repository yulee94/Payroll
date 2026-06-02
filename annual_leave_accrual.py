"""
annual_leave_accrual.py - 입사일 기준 연차 발생·다음 발생일 산정

근로기준법 제60조(연차 유급휴가) 요약 반영:
- 1년 미만: 1개월 개근 시 1일 (최대 11일, 입사 후 1년까지)
- 1년 이상 개근 80% 이상: 15일
- 3년 이상 근속: 2년마다 1일 가산 (최대 25일)

※ 출근률 80% 미만·최초 1년 11일 상한 등은 명부·근태 확인 후 조정이 필요할 수 있습니다.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

_HIRE_DATE_RE = re.compile(
    r"^(\d{2,4})[.\-/](\d{1,2})[.\-/](\d{1,2})$"
)


@dataclass(frozen=True)
class LeaveAccrualResult:
    accrued: float
    annual_grant: float
    basis: str
    next_accrual_date: date | None
    next_accrual_days: float
    service_years: int
    is_first_year_monthly: bool


def parse_hire_date(value: Any) -> date | None:
    """입사일 — datetime·YYYY-MM-DD·YY.MM.DD 등."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    m = _HIRE_DATE_RE.match(text)
    if m:
        y_raw, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y_raw < 100:
            year = 2000 + y_raw if y_raw < 50 else 1900 + y_raw
        else:
            year = y_raw
        try:
            return date(year, mo, d)
        except ValueError:
            return None

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def period_end_date(period_label: str) -> date:
    try:
        y, m = period_label.split("-")
        year, month = int(y), int(m)
        last = calendar.monthrange(year, month)[1]
        return date(year, month, last)
    except (ValueError, AttributeError):
        today = date.today()
        last = calendar.monthrange(today.year, today.month)[1]
        return date(today.year, today.month, last)


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def years_of_service_at(hire: date, as_of: date) -> int:
    if as_of < hire:
        return 0
    years = as_of.year - hire.year
    if (as_of.month, as_of.day) < (hire.month, hire.day):
        years -= 1
    return max(0, years)


def last_anniversary_on_or_before(hire: date, as_of: date) -> date:
    years = years_of_service_at(hire, as_of)
    return add_years(hire, years)


def statutory_annual_grant_days(years_at_anniversary: int) -> int:
    """입사 기념일 시점 근속 연수 기준 연간 부여 일수."""
    if years_at_anniversary < 1:
        return 0
    days = 15
    if years_at_anniversary >= 3:
        days += min((years_at_anniversary - 1) // 2, 10)
    return min(days, 25)


def completed_employment_months(hire: date, as_of: date) -> int:
    """입사월 포함, 기준일이 속한 월까지의 근무 월 수."""
    if as_of < hire:
        return 0
    return (as_of.year - hire.year) * 12 + (as_of.month - hire.month) + 1


def first_year_monthly_accrued(hire: date, as_of: date) -> float:
    first_anniversary = add_years(hire, 1)
    if as_of >= first_anniversary:
        return 0.0
    months = completed_employment_months(hire, as_of)
    return float(min(max(0, months), 11))


def compute_leave_accrual(hire: date, period_label: str) -> LeaveAccrualResult:
    """급여월 말일 기준 누적 발생 연차."""
    as_of = period_end_date(period_label)
    if as_of < hire:
        return LeaveAccrualResult(
            accrued=0.0,
            annual_grant=0.0,
            basis="기준일 이전 입사",
            next_accrual_date=hire,
            next_accrual_days=0.0,
            service_years=0,
            is_first_year_monthly=False,
        )

    first_anniversary = add_years(hire, 1)
    service_years = years_of_service_at(hire, as_of)

    if as_of < first_anniversary:
        accrued = first_year_monthly_accrued(hire, as_of)
        next_month = as_of.month + 1
        next_year = as_of.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        next_day = min(hire.day, calendar.monthrange(next_year, next_month)[1])
        next_date = date(next_year, next_month, next_day)
        if next_date > first_anniversary:
            next_date = first_anniversary
            next_days = float(statutory_annual_grant_days(1))
        else:
            next_days = 1.0
        return LeaveAccrualResult(
            accrued=accrued,
            annual_grant=accrued,
            basis=f"1년 미만 월할 ({completed_employment_months(hire, as_of)}개월)",
            next_accrual_date=next_date,
            next_accrual_days=next_days,
            service_years=0,
            is_first_year_monthly=True,
        )

    grant = statutory_annual_grant_days(service_years)
    anni = last_anniversary_on_or_before(hire, as_of)
    next_anni = add_years(anni, 1)
    next_years = years_of_service_at(hire, next_anni)
    next_days = float(statutory_annual_grant_days(next_years))

    return LeaveAccrualResult(
        accrued=float(grant),
        annual_grant=float(grant),
        basis=f"{service_years}년차 (입사 {hire:%Y-%m-%d}, {anni:%m/%d} 부여 {grant}일)",
        next_accrual_date=next_anni,
        next_accrual_days=next_days,
        service_years=service_years,
        is_first_year_monthly=False,
    )


def format_next_accrual_display(result: LeaveAccrualResult) -> str:
    if result.next_accrual_date is None:
        return "-"
    d = result.next_accrual_date
    days = result.next_accrual_days
    days_s = str(int(days)) if days == int(days) else f"{days:g}"
    if result.is_first_year_monthly and days <= 1.01:
        return f"{d:%Y-%m-%d} (+{days_s}일)"
    return f"{d:%Y-%m-%d} ({days_s}일)"


def apply_hire_date_leave_to_record(
    rec: dict[str, Any],
    period_label: str,
    *,
    sheet_leave: dict[str, Any] | None = None,
) -> bool:
    """
    명부 레코드에 입사일 기준 연차를 반영합니다.

    사용 일수는 연차 시트 월별 데이터(sheet_leave)를 우선합니다.
    Returns True if hire-date logic was applied.
    """
    from employment_succession import continuous_hire_date_for_leave

    hire = continuous_hire_date_for_leave(rec)
    if hire is None:
        return False

    accrual = compute_leave_accrual(hire, period_label)
    used = 0.0
    monthly: dict[str, float] = {}
    if sheet_leave:
        used = max(0.0, float(sheet_leave.get("사용연차") or 0))
        raw_monthly = sheet_leave.get("_monthly_leave_usage")
        if isinstance(raw_monthly, dict):
            monthly = dict(raw_monthly)

    remaining = accrual.accrued - used
    over = remaining < 0

    rec["발생연차"] = accrual.accrued
    rec["예상발생연차"] = accrual.next_accrual_days
    rec["사용연차"] = used
    rec["잔여연차"] = remaining if not over else 0.0
    rec["잔여연차_raw"] = "-" if over else remaining
    rec["_잔여연차_초과"] = over
    rec["_monthly_leave_usage"] = monthly
    rec["_hire_based_leave"] = True
    rec["_leave_accrual_basis"] = accrual.basis
    rec["_next_accrual_date"] = (
        accrual.next_accrual_date.isoformat() if accrual.next_accrual_date else ""
    )
    rec["_next_accrual_display"] = format_next_accrual_display(accrual)
    rec["_leave_period_hint"] = period_label
    rec["_service_years"] = accrual.service_years
    for col_name in ("발생연차", "사용연차", "잔여연차"):
        rec[f"_{col_name}_수식"] = False
    return True
