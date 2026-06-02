"""
core/hr/severance.py - 퇴직금·중간정산 산출 (근로자퇴직급여 보장법)

평균임금 = 퇴직일 이전 3개월간 지급 임금 총액 / 그 기간의 총일수
퇴직금 = 평균임금(일) × 30 × (근속연수)  … 근속연수 = 근속일수 / 365
"""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable

from annual_leave_accrual import parse_hire_date
from core.module_store import load_module_db, mutate_module_db
from core.session_service import session_tenant_id
from roster_constants import norm_name_key

MODULE = "hr"

_EMPTY_SEVERANCE: dict[str, Any] = {
    "severance_interim": [],
}

# 4대보험 근로자 부담분 (표시용 — 퇴직금 산정 기준은 세전 총지급)
_INSURANCE_KEYS = (
    "national_pension",
    "health_insurance",
    "long_term_care",
    "employment_insurance",
)

# 임금 구성 항목 (급여 스냅샷 필드)
_WAGE_COMPONENT_KEYS: tuple[tuple[str, str], ...] = (
    ("base_salary", "기본급"),
    ("ot_pay", "연장수당"),
    ("shift_pay", "교대수당"),
    ("night_pay", "야간수당"),
    ("special_pay", "특근수당"),
    ("special_ext_pay", "특근연장"),
    ("position_pay", "직책수당"),
    ("shutdown_allowance", "휴업수당"),
    ("annual_pay", "상여·업무추진"),
    ("transport", "교통비"),
)


def _tid(tenant_id: str | None) -> str:
    return tenant_id or session_tenant_id() or "default"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _subtract_months(d: date, months: int) -> date:
    """날짜에서 months 개월 전 (말일 보정)."""
    year, month = d.year, d.month - months
    while month <= 0:
        month += 12
        year -= 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def three_month_window(resign_date: date) -> tuple[date, date, int]:
    """퇴직일 기준 3개월 구간 (시작·종료·총일수)."""
    period_end = resign_date
    period_start = _subtract_months(resign_date, 3) + timedelta(days=1)
    calendar_days = (period_end - period_start).days + 1
    return period_start, period_end, calendar_days


def _days_in_month_range(year: int, month: int, start: date, end: date) -> int:
    """해당 월에서 [start, end] 구간과 겹치는 일수."""
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    overlap_start = max(month_start, start)
    overlap_end = min(month_end, end)
    if overlap_start > overlap_end:
        return 0
    return (overlap_end - overlap_start).days + 1


def _period_from_ym(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _iter_months_in_range(start: date, end: date) -> list[tuple[str, int, int]]:
    """(YYYY-MM, year, month) 목록 — start~end 구간과 겹치는 월."""
    out: list[tuple[str, int, int]] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        if _days_in_month_range(y, m, start, end) > 0:
            out.append((_period_from_ym(y, m), y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _safe_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _employee_insurance_total(rec: dict[str, Any]) -> int:
    return sum(_safe_int(rec.get(k)) for k in _INSURANCE_KEYS)


def _wage_components(rec: dict[str, Any]) -> dict[str, int]:
    return {label: _safe_int(rec.get(key)) for key, label in _WAGE_COMPONENT_KEYS}


def _statutory_wage_from_record(rec: dict[str, Any]) -> int:
    """급여 스냅샷의 총지급(세전) — 퇴직금 평균임금 산정 기준."""
    gross = _safe_int(rec.get("gross_pay"))
    if gross > 0:
        return gross
    components = _wage_components(rec)
    return sum(components.values())


def _prorate_wage(full_wage: int, days_in_window: int, days_in_month: int) -> int:
    if days_in_month <= 0 or days_in_window <= 0:
        return 0
    if days_in_window >= days_in_month:
        return full_wage
    return round(full_wage * days_in_window / days_in_month)


@dataclass
class MonthlyWageRow:
    period: str
    period_label: str
    days_in_window: int
    days_in_month: int
    gross_wage: int
    prorated_wage: int
    components: dict[str, int] = field(default_factory=dict)
    insurance_employee: int = 0
    found: bool = True
    note: str = ""


@dataclass
class InterimSettlement:
    id: str
    employee_name: str
    date: str
    amount: int
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "employee_name": self.employee_name,
            "date": self.date,
            "amount": self.amount,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> InterimSettlement:
        return cls(
            id=str(raw.get("id") or _new_id()),
            employee_name=str(raw.get("employee_name") or raw.get("name") or ""),
            date=str(raw.get("date") or ""),
            amount=_safe_int(raw.get("amount")),
            reason=str(raw.get("reason") or ""),
        )


@dataclass
class ServicePeriod:
    days: int
    years: float
    display: str


@dataclass
class SeveranceResult:
    employee_name: str
    employee_key: str
    hire_date: date | None
    resign_date: date
    period_start: date
    period_end: date
    calendar_days: int
    monthly_rows: list[MonthlyWageRow]
    total_gross_3m: int
    total_insurance_3m: int
    average_daily_wage: float
    service: ServicePeriod
    statutory_severance: int
    interim_settlements: list[InterimSettlement]
    interim_total: int
    final_severance: int
    warnings: list[str] = field(default_factory=list)

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "employee_name": self.employee_name,
            "hire_date": self.hire_date.isoformat() if self.hire_date else "",
            "resign_date": self.resign_date.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "calendar_days": self.calendar_days,
            "total_gross_3m": self.total_gross_3m,
            "total_insurance_3m": self.total_insurance_3m,
            "average_daily_wage": round(self.average_daily_wage, 2),
            "service_days": self.service.days,
            "service_display": self.service.display,
            "statutory_severance": self.statutory_severance,
            "interim_total": self.interim_total,
            "final_severance": self.final_severance,
            "warnings": list(self.warnings),
        }


def calculate_service_period(hire_date: date, resign_date: date) -> ServicePeriod:
    if resign_date < hire_date:
        return ServicePeriod(days=0, years=0.0, display="0일")
    days = (resign_date - hire_date).days + 1
    years = days / 365.0
    y = days // 365
    rem = days % 365
    months = rem // 30
    rem_days = rem % 30
    parts: list[str] = []
    if y:
        parts.append(f"{y}년")
    if months:
        parts.append(f"{months}개월")
    if rem_days or not parts:
        parts.append(f"{rem_days}일")
    return ServicePeriod(days=days, years=years, display=" ".join(parts))


def _find_employee_record(
    records: list[dict[str, Any]],
    employee_name: str,
) -> dict[str, Any] | None:
    key = norm_name_key(employee_name)
    if not key:
        return None
    for rec in records:
        if norm_name_key(rec.get("name")) == key:
            return rec
    return None


def calculate_average_wage(
    employee_name: str,
    resign_date: date,
    *,
    tenant_id: str | None = None,
    load_payroll_fn: Callable[[str, str], list[dict[str, Any]]] | None = None,
) -> tuple[list[MonthlyWageRow], int, int, float, list[str]]:
    """
    퇴직 전 3개월 급여 스냅샷에서 평균임금(일) 산출.

    Returns: (월별 행, 3개월 임금 합, 3개월 보험 합, 평균일임금, 경고)
    """
    from payroll_archive import format_period_display

    tid = _tid(tenant_id)
    period_start, period_end, calendar_days = three_month_window(resign_date)
    warnings: list[str] = []

    if load_payroll_fn is None:
        from core.access_control import load_payroll_records_secured

        def _load(period: str, t: str) -> list[dict[str, Any]]:
            return load_payroll_records_secured(period, t)

        load_payroll_fn = _load

    monthly_rows: list[MonthlyWageRow] = []
    total_wage = 0
    total_insurance = 0

    for period, y, m in _iter_months_in_range(period_start, period_end):
        days_in_month = calendar.monthrange(y, m)[1]
        days_in_window = _days_in_month_range(y, m, period_start, period_end)
        label = format_period_display(period)

        records = load_payroll_fn(period, tid)
        rec = _find_employee_record(records, employee_name)
        if rec is None:
            monthly_rows.append(
                MonthlyWageRow(
                    period=period,
                    period_label=label,
                    days_in_window=days_in_window,
                    days_in_month=days_in_month,
                    gross_wage=0,
                    prorated_wage=0,
                    found=False,
                    note="해당 월 급여 데이터 없음",
                )
            )
            warnings.append(f"{label} 급여 기록 없음")
            continue

        full_gross = _statutory_wage_from_record(rec)
        prorated = _prorate_wage(full_gross, days_in_window, days_in_month)
        ins_full = _employee_insurance_total(rec)
        ins_prorated = _prorate_wage(ins_full, days_in_window, days_in_month)
        comps = _wage_components(rec)
        prorated_comps = {
            k: _prorate_wage(v, days_in_window, days_in_month) for k, v in comps.items()
        }

        note = ""
        if days_in_window < days_in_month:
            note = f"{days_in_window}/{days_in_month}일 비례"

        monthly_rows.append(
            MonthlyWageRow(
                period=period,
                period_label=label,
                days_in_window=days_in_window,
                days_in_month=days_in_month,
                gross_wage=full_gross,
                prorated_wage=prorated,
                components=prorated_comps,
                insurance_employee=ins_prorated,
                note=note,
            )
        )
        total_wage += prorated
        total_insurance += ins_prorated

    if calendar_days <= 0:
        return monthly_rows, 0, 0, 0.0, ["퇴직일 구간 오류"]

    avg_daily = total_wage / calendar_days
    if not any(r.found for r in monthly_rows):
        warnings.append("3개월 구간 내 급여 스냅샷이 없습니다. 급여 산출 후 다시 시도하세요.")

    return monthly_rows, total_wage, total_insurance, avg_daily, warnings


def list_interim_settlements(
    employee_name: str,
    *,
    tenant_id: str | None = None,
) -> list[InterimSettlement]:
    tid = _tid(tenant_id)
    key = norm_name_key(employee_name)
    db = load_module_db(MODULE, tid, _EMPTY_SEVERANCE)
    raw_list = db.get("severance_interim") or []
    out: list[InterimSettlement] = []
    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        item = InterimSettlement.from_dict(raw)
        if norm_name_key(item.employee_name) == key:
            out.append(item)
    out.sort(key=lambda x: x.date)
    return out


def save_interim_settlement(
    settlement: InterimSettlement,
    *,
    tenant_id: str | None = None,
) -> InterimSettlement:
    tid = _tid(tenant_id)
    key = norm_name_key(settlement.employee_name)

    def _mutate(db: dict[str, Any]) -> InterimSettlement:
        items = list(db.get("severance_interim") or [])
        updated = settlement
        if not updated.id:
            updated = InterimSettlement(
                id=_new_id(),
                employee_name=settlement.employee_name,
                date=settlement.date,
                amount=settlement.amount,
                reason=settlement.reason,
            )
        found = False
        new_items: list[dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            if str(raw.get("id")) == updated.id:
                new_items.append(updated.to_dict())
                found = True
            else:
                new_items.append(raw)
        if not found:
            new_items.append(updated.to_dict())
        db["severance_interim"] = new_items
        return updated

    return mutate_module_db(MODULE, tid, _EMPTY_SEVERANCE, _mutate)


def delete_interim_settlement(
    settlement_id: str,
    *,
    tenant_id: str | None = None,
) -> bool:
    tid = _tid(tenant_id)
    sid = str(settlement_id).strip()

    def _mutate(db: dict[str, Any]) -> bool:
        items = db.get("severance_interim") or []
        new_items = [x for x in items if isinstance(x, dict) and str(x.get("id")) != sid]
        removed = len(new_items) < len(items)
        db["severance_interim"] = new_items
        return removed

    return bool(mutate_module_db(MODULE, tid, _EMPTY_SEVERANCE, _mutate))


def calculate_severance(
    employee_name: str,
    resign_date: date,
    hire_date: date | None,
    interim_settlements: list[InterimSettlement] | None = None,
    *,
    tenant_id: str | None = None,
    load_payroll_fn: Callable[[str, str], list[dict[str, Any]]] | None = None,
) -> SeveranceResult:
    """퇴직금 산출 — 중간정산 차감 후 최종 퇴직금."""
    emp_key = norm_name_key(employee_name)
    period_start, period_end, calendar_days = three_month_window(resign_date)
    warnings: list[str] = []

    monthly_rows, total_gross, total_ins, avg_daily, wage_warnings = calculate_average_wage(
        employee_name,
        resign_date,
        tenant_id=tenant_id,
        load_payroll_fn=load_payroll_fn,
    )
    warnings.extend(wage_warnings)

    if hire_date is None:
        warnings.append("입사일 미확인 — 근속연수·퇴직금 산정이 부정확할 수 있습니다.")
        service = ServicePeriod(days=0, years=0.0, display="미확인")
        statutory = 0
    else:
        service = calculate_service_period(hire_date, resign_date)
        statutory = round(avg_daily * 30 * service.years)

    if interim_settlements is None:
        interim_settlements = list_interim_settlements(employee_name, tenant_id=tenant_id)

    interim_total = sum(i.amount for i in interim_settlements)
    final = max(0, statutory - interim_total)

    if interim_total > statutory and statutory > 0:
        warnings.append("중간정산 합계가 법정 퇴직금을 초과합니다.")

    return SeveranceResult(
        employee_name=employee_name,
        employee_key=emp_key,
        hire_date=hire_date,
        resign_date=resign_date,
        period_start=period_start,
        period_end=period_end,
        calendar_days=calendar_days,
        monthly_rows=monthly_rows,
        total_gross_3m=total_gross,
        total_insurance_3m=total_ins,
        average_daily_wage=avg_daily,
        service=service,
        statutory_severance=statutory,
        interim_settlements=interim_settlements,
        interim_total=interim_total,
        final_severance=final,
        warnings=warnings,
    )


def parse_resign_date(value: Any) -> date | None:
    return parse_hire_date(value)


def hire_date_from_roster(row: dict[str, Any]) -> date | None:
    """명부 행에서 입사일 — 최초입사일 우선."""
    for key in ("최초입사일", "입사일"):
        d = parse_hire_date(row.get(key))
        if d:
            return d
    return None


def resign_date_from_roster(row: dict[str, Any]) -> date | None:
    return parse_hire_date(row.get("퇴사일"))
