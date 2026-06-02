"""
core/mobile/payroll_source.py - 출퇴근 기반 급여 소스 (청구서 업로드 대체)

기존 payroll_builder.build_payroll_records 는 invoice_rows 를 입력으로 받습니다.
모바일 근태 집계 결과를 동일 형태의 dict 로 변환해 연결합니다.
"""

from __future__ import annotations

from typing import Any

from core.mobile.models import AttendanceEvent, PeriodWorkSummary
from core.mobile import store, sync
from roster_constants import norm_name_key

# 급여 산출 소스 식별자 (payroll_settings·아카이브 메타 확장용)
PAYROLL_SOURCE_ATTENDANCE = "attendance_mobile"
PAYROLL_SOURCE_INVOICE = "invoice_xlsx"


def aggregate_period_hours(
    period: str,
    *,
    tenant_id: str | None = None,
    site_name: str = "",
    hours_per_day: float = 8.0,
) -> list[PeriodWorkSummary]:
    """
    verified 출퇴근 이벤트 → 월별·사업장별 근무시간 집계.

    clock_in/out 쌍이 있으면 실제 분 단위, 없으면 출근 1건 = 1일(8h)로 환산.
    """
    events = store.list_events(tenant_id=tenant_id, period=period, status="verified")
    if site_name:
        events = [e for e in events if e.site_name == site_name]

    paired = sync.pair_work_minutes(events)
    paired_ids = {e.id for e in paired}

    buckets: dict[tuple[str, str], PeriodWorkSummary] = {}

    for ev in events:
        key = (ev.employee_name, ev.site_name)
        if key not in buckets:
            buckets[key] = PeriodWorkSummary(
                employee_name=ev.employee_name,
                period=period,
                site_name=ev.site_name,
                source=PAYROLL_SOURCE_ATTENDANCE,
            )
        buckets[key].event_ids.append(ev.id)

    for ev in paired:
        key = (ev.employee_name, ev.site_name)
        b = buckets[key]
        hours = ev.work_minutes / 60.0
        b.work_hours += hours
        b.work_days += hours / hours_per_day if hours_per_day > 0 else 0

    # 퇴근 없이 출근만 있는 날 — 1일 환산
    clock_in_days: dict[tuple[str, str, str], AttendanceEvent] = {}
    for ev in events:
        if ev.event_type != "clock_in":
            continue
        day = ev.event_at[:10]
        clock_in_days[(ev.employee_name, ev.site_name, day)] = ev

    for (name, site, day), ev_in in clock_in_days.items():
        has_pair = any(
            e.employee_name == name and e.site_name == site and e.id in paired_ids and e.event_at[:10] == day
            for e in paired
        )
        if has_pair:
            continue
        key = (name, site)
        b = buckets[key]
        b.work_days += 1.0
        b.work_hours += hours_per_day

    summaries = list(buckets.values())
    for s in summaries:
        store.upsert_period_summary(s, tenant_id)
    return summaries


def summaries_to_invoice_rows(
    summaries: list[PeriodWorkSummary],
    *,
    affiliate: str = "",
) -> list[dict[str, Any]]:
    """
    payroll_builder.build_payroll_records 가 기대하는 invoice_row 형태로 변환.

    청구서 I·J열에 해당: base_days(기준일/시간), work_hours(근무시간).
    """
    rows: list[dict[str, Any]] = []
    for s in summaries:
        rows.append(
            {
                "name": s.employee_name,
                "workplace": s.site_name,
                "affiliate": affiliate,
                "base_days": s.work_hours,
                "work_hours": s.work_hours,
                "base_salary": 0,
                "meal_days": int(s.work_days),
                "_payroll_source": PAYROLL_SOURCE_ATTENDANCE,
                "_attendance_period": s.period,
                "_attendance_event_ids": list(s.event_ids),
            }
        )
    return rows


def build_attendance_payroll_inputs(
    period: str,
    *,
    tenant_id: str | None = None,
    site_name: str = "",
    affiliate: str = "",
) -> tuple[list[dict[str, Any]], list[PeriodWorkSummary]]:
    """모바일 근태 → 급여 산출용 invoice_rows + 집계 요약."""
    summaries = aggregate_period_hours(period, tenant_id=tenant_id, site_name=site_name)
    if not summaries:
        stored = store.list_period_summaries(period, tenant_id=tenant_id, site_name=site_name)
        summaries = stored
    rows = summaries_to_invoice_rows(summaries, affiliate=affiliate)
    return rows, summaries


def merge_with_roster_names(
    invoice_rows: list[dict[str, Any]],
    roster_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """명부에 없는 이름 경고 (main.py 청구서 검증과 동일 패턴)."""
    roster_keys = {norm_name_key(r.get("성명")) for r in roster_rows}
    warnings: list[str] = []
    for row in invoice_rows:
        key = norm_name_key(row.get("name"))
        if key and key not in roster_keys:
            warnings.append(f"근태 기록 '{row.get('name')}' — 명부에 없음")
    return invoice_rows, warnings
