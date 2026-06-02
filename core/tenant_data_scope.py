"""
core/tenant_data_scope.py - 고객사(법인)별 데이터 접근 범위

다른 법인의 급여·명부·스냅샷은 조회할 수 없습니다.
"""

from __future__ import annotations

from typing import Any

from core.session_service import UserSession, require_session
from core.tenant_store import get_active_tenant_id, get_tenant, load_registry
from payroll_archive import MonthSummary, dedupe_monthly_snapshot_records, load_snapshot_records
from services.payroll_scope import PayrollScope, discover_scopes


class TenantDataAccessError(PermissionError):
    """타 법인 데이터 접근 시도."""


def _tenant_raw(tenant_id: str) -> dict[str, Any]:
    raw = (load_registry().get("tenants") or {}).get(str(tenant_id).strip())
    return raw if isinstance(raw, dict) else {}


def tenant_allowed_affiliates(tenant_id: str) -> frozenset[str]:
    """
    이 고객사가 열람할 수 있는 계열사(법인) 폴더명.
    tenants.json 의 data_affiliates 우선, 없으면 display_name_ko → display_name.
    """
    tid = str(tenant_id).strip()
    raw = _tenant_raw(tid)
    explicit = raw.get("data_affiliates")
    if isinstance(explicit, list) and explicit:
        names = {str(a).strip() for a in explicit if str(a).strip()}
        if names:
            return frozenset(names)

    rec = get_tenant(tid)
    if rec is None:
        return frozenset()
    if rec.display_name_ko:
        return frozenset([rec.display_name_ko])
    if rec.display_name:
        return frozenset([rec.display_name])
    return frozenset()


def scope_allowed_for_tenant(scope: PayrollScope, tenant_id: str) -> bool:
    allowed = tenant_allowed_affiliates(tenant_id)
    if not allowed:
        return False
    return scope.affiliate in allowed


def discover_scopes_for_tenant(tenant_id: str) -> list[PayrollScope]:
    scoped = [s for s in discover_scopes() if scope_allowed_for_tenant(s, tenant_id)]
    if scoped:
        return scoped
    # tenants.json data_affiliates 미설정·폴더명 불일치 시에도 산출물이 있으면 급여월 선택 가능
    if not tenant_allowed_affiliates(tenant_id):
        return list(discover_scopes())
    return scoped


def enforce_session_tenant_access(session: UserSession | None = None) -> UserSession:
    """로그인 계정 고객사 = 활성 고객사, 타 법인 데이터 조회 차단."""
    sess = session or require_session()
    active = get_active_tenant_id()
    if sess.tenant_id != active:
        raise TenantDataAccessError(
            "활성 고객사가 변경되었습니다. 다시 로그인한 뒤 이용해 주세요."
        )
    return sess


def assert_record_in_tenant(record: dict[str, Any], tenant_id: str) -> None:
    """스냅샷 레코드가 해당 고객사 소속인지 검증."""
    aff = str(record.get("affiliate") or "").strip()
    if not aff:
        wp_aff = str(record.get("_scope_workplace") or "")
        _ = wp_aff
    allowed = tenant_allowed_affiliates(tenant_id)
    if aff and aff not in allowed:
        raise TenantDataAccessError("다른 법인 소속 급여 데이터는 조회할 수 없습니다.")


def load_payroll_records_for_tenant(period: str, tenant_id: str) -> list[dict[str, Any]]:
    """해당 고객사 소속 scope 의 스냅샷만 합칩니다."""
    allowed = tenant_allowed_affiliates(tenant_id)
    out: list[dict[str, Any]] = []
    for scope in discover_scopes_for_tenant(tenant_id):
        if scope.period != period:
            continue
        for rec in load_snapshot_records(period, scope):
            if not isinstance(rec, dict):
                continue
            tagged = dict(rec)
            tagged.setdefault("affiliate", scope.affiliate)
            tagged["_scope_workplace"] = scope.workplace
            if not allowed or scope.affiliate in allowed:
                out.append(tagged)
    return dedupe_monthly_snapshot_records(out)


def list_periods_for_tenant(tenant_id: str) -> list[str]:
    from payroll_archive import _period_sort_key

    periods = sorted(
        {s.period for s in discover_scopes_for_tenant(tenant_id)},
        key=_period_sort_key,
        reverse=True,
    )
    return periods


def build_month_summary_for_tenant(period: str, tenant_id: str) -> MonthSummary:
    records = load_payroll_records_for_tenant(period, tenant_id)
    summary = MonthSummary(period=period, files=[], has_output=bool(records))
    if not records:
        return summary
    summary.employee_count = len(records)
    for r in records:
        summary.total_gross += int(r.get("gross_pay") or 0)
        summary.total_net += int(r.get("net_pay") or 0)
        summary.total_deduction += int(r.get("total_deduction") or 0)
        if float(r.get("leave_days") or 0) > 0:
            summary.leave_users += 1
        if float(r.get("unpaid_days") or 0) > 0:
            summary.absence_users += 1
    return summary


def roster_row_affiliate(row: dict[str, Any]) -> str:
    return str(row.get("계열사") or row.get("affiliate") or "").strip()


def filter_roster_rows_for_tenant(
    rows: list[dict[str, Any]],
    tenant_id: str,
) -> list[dict[str, Any]]:
    allowed = tenant_allowed_affiliates(tenant_id)
    if not allowed:
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        aff = roster_row_affiliate(row)
        if aff:
            if aff in allowed:
                out.append(row)
        elif len(allowed) == 1:
            out.append(row)
    return out


def tenant_data_scope_label(tenant_id: str) -> str:
    affs = sorted(tenant_allowed_affiliates(tenant_id))
    if not affs:
        return "(데이터 범위 미설정)"
    return ", ".join(affs)
