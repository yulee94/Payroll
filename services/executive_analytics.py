"""
services/executive_analytics.py - 임원 대시보드용 집계·추이 데이터
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from payroll_archive import (
    MonthSummary,
    _period_sort_key,
    build_month_summary,
    format_period_display,
    format_ytd_range_label,
    list_payroll_periods,
    load_snapshot_records,
)
from payroll_comparison import prev_period_label
from services.org_registry import enrich_records, resolve_workplace


def site_label(rec: dict[str, Any]) -> str:
    """사업장(근무지) 우선, 없으면 소속(부서)."""
    return resolve_workplace(rec)


@dataclass
class SiteMetrics:
    name: str
    headcount: int = 0
    gross: int = 0
    net: int = 0
    deduction: int = 0
    leave_users: int = 0
    absence_users: int = 0


@dataclass
class PeriodTrendPoint:
    period: str
    label: str
    headcount: int
    gross: int
    net: int


@dataclass
class MonthGrossDelta:
    """당해 연도 월별 총급여 및 전월 대비 증감."""

    period: str
    label: str
    gross: int
    delta: int


@dataclass
class ExecutiveAnalytics:
    period: str
    period_label: str
    summary: MonthSummary
    records: list[dict[str, Any]]
    # 인도급 관리 KPI
    headcount_delta: int = 0
    gross_delta: int = 0
    ot_total: int = 0  # 연장근로(연장수당)
    ot_delta: int = 0
    special_total: int = 0  # 특근수당(+특근연장 포함)
    special_delta: int = 0
    sites: list[SiteMetrics] = field(default_factory=list)
    trends: list[PeriodTrendPoint] = field(default_factory=list)
    ytd_label: str = ""
    ytd_months: list[PeriodTrendPoint] = field(default_factory=list)
    ytd_gross_deltas: list[MonthGrossDelta] = field(default_factory=list)
    ytd_total_gross: int = 0
    prior_period: str = ""
    prior_summary: MonthSummary | None = None
    top_employees: list[dict[str, Any]] = field(default_factory=list)


def aggregate_by_site(records: list[dict[str, Any]]) -> list[SiteMetrics]:
    buckets: dict[str, SiteMetrics] = {}
    for r in records:
        key = site_label(r)
        if key not in buckets:
            buckets[key] = SiteMetrics(name=key)
        m = buckets[key]
        m.headcount += 1
        m.gross += int(r.get("gross_pay") or 0)
        m.net += int(r.get("net_pay") or 0)
        m.deduction += int(r.get("total_deduction") or 0)
        if float(r.get("leave_days") or 0) > 0:
            m.leave_users += 1
        if float(r.get("unpaid_days") or 0) > 0:
            m.absence_users += 1
    return sorted(buckets.values(), key=lambda s: s.gross, reverse=True)


def months_in_calendar_year_through(current_period: str) -> list[str]:
    """당해 1월 ~ 선택 월까지, 산출 데이터가 있는 급여월(YYYY-MM) 목록."""
    try:
        year_s, month_s = current_period.split("-")
        year, end_month = int(year_s), int(month_s)
    except ValueError:
        return []

    found: set[str] = set()
    from services.payroll_scope import discover_scopes

    for scope in discover_scopes():
        p = scope.period
        try:
            py, pm = p.split("-")
            if int(py) != year or int(pm) > end_month:
                continue
        except ValueError:
            continue
        ms = build_month_summary(p)
        if ms.has_output:
            found.add(p)

    if not found:
        for key in list_payroll_periods():
            if "\x1f" in key:
                from services.payroll_scope import PayrollScope

                scope = PayrollScope.try_parse_key(key)
                p = scope.period if scope else ""
            else:
                p = key
            if not p:
                continue
            try:
                py, pm = p.split("-")
                if int(py) != year or int(pm) > end_month:
                    continue
            except ValueError:
                continue
            if build_month_summary(p).has_output:
                found.add(p)

    return sorted(found, key=_period_sort_key)


def load_year_to_date_series(current_period: str) -> tuple[str, list[PeriodTrendPoint], list[MonthGrossDelta], int]:
    """연간(1월~당월) 총급여 추이·전월 대비 차이."""
    periods = months_in_calendar_year_through(current_period)
    points: list[PeriodTrendPoint] = []
    deltas: list[MonthGrossDelta] = []
    prev_gross: int | None = None
    total = 0

    for p in periods:
        ms = build_month_summary(p)
        if not ms.has_output:
            continue
        try:
            _y, m_s = p.split("-")
            month_label = f"{int(m_s)}월"
        except ValueError:
            month_label = p
        points.append(
            PeriodTrendPoint(
                period=p,
                label=month_label,
                headcount=ms.employee_count,
                gross=ms.total_gross,
                net=ms.total_net,
            )
        )
        delta = 0 if prev_gross is None else ms.total_gross - prev_gross
        deltas.append(MonthGrossDelta(period=p, label=month_label, gross=ms.total_gross, delta=delta))
        total += ms.total_gross
        prev_gross = ms.total_gross

    return format_ytd_range_label(periods), points, deltas, total


def load_period_trends(current_period: str, max_months: int = 6) -> list[PeriodTrendPoint]:
    periods = list_payroll_periods()
    if current_period in periods:
        idx = periods.index(current_period)
        slice_periods = periods[idx : idx + max_months]
    else:
        slice_periods = periods[:max_months]
    slice_periods = list(reversed(slice_periods))
    points: list[PeriodTrendPoint] = []
    seen_months: set[str] = set()
    for p in slice_periods:
        from services.payroll_scope import PayrollScope

        scope = PayrollScope.try_parse_key(p)
        month = scope.period if scope else str(p).split("\x1f")[-1] if "\x1f" in str(p) else p
        if month in seen_months:
            continue
        seen_months.add(month)
        ms = build_month_summary(month)
        if not ms.has_output:
            continue
        points.append(
            PeriodTrendPoint(
                period=month,
                label=format_period_display(month).replace("년 ", "년\n"),
                headcount=ms.employee_count,
                gross=ms.total_gross,
                net=ms.total_net,
            )
        )
    return points


def build_executive_analytics(
    period: str,
    summary: MonthSummary | None = None,
    records: list[dict[str, Any]] | None = None,
) -> ExecutiveAnalytics:
    recs = records if records is not None else enrich_records(load_snapshot_records(period))
    ms = summary or build_month_summary(period)
    prior = prev_period_label(period)
    prior_ms = build_month_summary(prior)
    if not prior_ms.has_output:
        prior_ms = None

    def _sum(recs_: list[dict[str, Any]], *keys: str) -> int:
        total = 0
        for r in recs_:
            for k in keys:
                total += int(r.get(k) or 0)
        return total

    prior_recs: list[dict[str, Any]] = []
    if prior_ms:
        prior_recs = enrich_records(load_snapshot_records(prior))

    ot_total = _sum(recs, "ot_pay")
    ot_prior = _sum(prior_recs, "ot_pay") if prior_recs else 0
    special_total = _sum(recs, "special_pay", "special_ext_pay")
    special_prior = _sum(prior_recs, "special_pay", "special_ext_pay") if prior_recs else 0

    top = sorted(recs, key=lambda r: int(r.get("gross_pay") or 0), reverse=True)[:8]
    ytd_label, ytd_months, ytd_deltas, ytd_total = load_year_to_date_series(period)

    return ExecutiveAnalytics(
        period=period,
        period_label=format_period_display(period),
        summary=ms,
        records=recs,
        headcount_delta=(ms.employee_count - (prior_ms.employee_count if prior_ms else 0)),
        gross_delta=(ms.total_gross - (prior_ms.total_gross if prior_ms else 0)),
        ot_total=ot_total,
        ot_delta=(ot_total - ot_prior),
        special_total=special_total,
        special_delta=(special_total - special_prior),
        sites=aggregate_by_site(recs),
        trends=load_period_trends(period),
        ytd_label=ytd_label,
        ytd_months=ytd_months,
        ytd_gross_deltas=ytd_deltas,
        ytd_total_gross=ytd_total,
        prior_period=prior if prior_ms else "",
        prior_summary=prior_ms,
        top_employees=top,
    )
