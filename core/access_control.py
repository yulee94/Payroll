"""
core/access_control.py - 임원 급여·명부 접근 제어 (재무팀 / 관리자)
"""

from __future__ import annotations

from typing import Any

from core.executive_policy import (
    is_executive_payroll_record,
    is_executive_roster_row,
    refresh_executive_name_index,
)
from roster_constants import norm_name_key
from core.roles import ROLE_ADMIN, ROLE_FINANCE, normalize_role, role_label
from core.config import APP_CONFIG
from core.session_service import UserSession, get_session, session_tenant_id
from core.tenant_data_scope import (
    build_month_summary_for_tenant,
    enforce_session_tenant_access,
    filter_roster_rows_for_tenant,
    load_payroll_records_for_tenant,
    list_periods_for_tenant,
)
from core.user_store import get_user, list_users_for_tenant, update_user_role
from services.employee_roster_store import load_roster_rows

_executive_keys_cache: frozenset[str] | None = None


class AccessDenied(PermissionError):
    pass


def can_view_executive_payroll(role: str | None) -> bool:
    r = normalize_role(role)
    return r in (ROLE_FINANCE, ROLE_ADMIN)


def can_manage_user_roles(role: str | None) -> bool:
    return normalize_role(role) == ROLE_ADMIN


def can_view_executive_reports(role: str | None) -> bool:
    """월별 경영 보고·임원용 대시보드."""
    return can_view_executive_payroll(role)


def session_role(session: UserSession | None = None) -> str:
    sess = session or get_session()
    if sess is None:
        return ""
    if getattr(sess, "role", None):
        return normalize_role(sess.role)
    rec = get_user(sess.user_id)
    return normalize_role(rec.role if rec else "")


def _executive_name_keys() -> frozenset[str]:
    global _executive_keys_cache
    if _executive_keys_cache is None:
        rows = load_roster_rows()
        _executive_keys_cache = refresh_executive_name_index(rows)
    return _executive_keys_cache


def invalidate_executive_index() -> None:
    global _executive_keys_cache
    _executive_keys_cache = None


def filter_executive_payroll_records(
    records: list[dict[str, Any]],
    *,
    role: str | None = None,
    session: UserSession | None = None,
) -> list[dict[str, Any]]:
    r = role if role is not None else session_role(session)
    if can_view_executive_payroll(r):
        return list(records)
    keys = _executive_name_keys()
    out: list[dict[str, Any]] = []
    for rec in records:
        if is_executive_payroll_record(rec):
            continue
        name = str(rec.get("name") or "")
        if name and norm_name_key(name) in keys:
            continue
        out.append(rec)
    return out


def filter_executive_roster_rows(
    rows: list[dict[str, Any]],
    *,
    role: str | None = None,
    session: UserSession | None = None,
) -> list[dict[str, Any]]:
    r = role if role is not None else session_role(session)
    if can_view_executive_payroll(r):
        return list(rows)
    return [row for row in rows if not is_executive_roster_row(row)]


def load_payroll_records_secured(
    period: str,
    tenant_id: str,
    *,
    session: UserSession | None = None,
) -> list[dict[str, Any]]:
    raw = load_payroll_records_for_tenant(period, tenant_id)
    return filter_executive_payroll_records(raw, session=session)


def load_records_for_period_secured(
    period_or_key: str,
    *,
    session: UserSession | None = None,
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    """법인·임원 필터 적용 급여 레코드."""
    import re

    from payroll_archive import load_snapshot_records
    from services.org_registry import enrich_records
    from services.payroll_scope import PayrollScope

    tid = tenant_id
    if session:
        sess = enforce_session_tenant_access(session)
        tid = sess.tenant_id
    elif not tid:
        tid = session_tenant_id()
        if not tid and not APP_CONFIG.require_login:
            from core.tenant_store import get_active_tenant_id

            tid = get_active_tenant_id()

    if not tid:
        return []

    if not period_or_key:
        return []

    if "\x1f" not in str(period_or_key) and re.match(r"^\d{4}-\d{2}$", period_or_key):
        return load_payroll_records_secured(period_or_key, tid, session=session)

    scope = PayrollScope.try_parse_key(period_or_key)
    period = scope.period if scope else period_or_key
    if scope and tid:
        from core.tenant_data_scope import scope_allowed_for_tenant

        if not scope_allowed_for_tenant(scope, tid):
            return []
        recs = enrich_records(load_snapshot_records(period, scope))
        return filter_executive_payroll_records(recs, session=session)

    return load_payroll_records_secured(period, tid, session=session)


def build_month_summary_secured(
    period: str,
    tenant_id: str,
    *,
    session: UserSession | None = None,
) -> Any:
    from payroll_archive import MonthSummary

    records = load_payroll_records_secured(period, tenant_id, session=session)
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


def load_roster_rows_secured(
    *,
    session: UserSession | None = None,
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    tid = tenant_id
    if session:
        tid = enforce_session_tenant_access(session).tenant_id
    elif not tid:
        tid = session_tenant_id()
        if not tid and not APP_CONFIG.require_login:
            from core.tenant_store import get_active_tenant_id

            tid = get_active_tenant_id()
    if not tid:
        return []
    rows = filter_roster_rows_for_tenant(load_roster_rows(), tid)
    return filter_executive_roster_rows(rows, session=session)


# 급여대장·명세서·지급내역 Excel에는 임원이 포함되어 일반 사용자 목록에서 제외
_SENSITIVE_ARCHIVE_FILE_KINDS = frozenset({"payroll"})


def filter_archive_entries_for_role(
    entries: list[Any],
    *,
    session: UserSession | None = None,
) -> list[Any]:
    if can_view_executive_payroll(session_role(session)):
        return list(entries)
    return [e for e in entries if getattr(e, "kind", "") not in _SENSITIVE_ARCHIVE_FILE_KINDS]


def require_executive_payroll_access(session: UserSession | None = None) -> UserSession:
    sess = enforce_session_tenant_access(session or get_session())
    if not can_view_executive_payroll(session_role(sess)):
        raise AccessDenied(
            "임원 급여·경영 보고는 재무팀 또는 관리자 권한이 필요합니다. "
            "권한 변경은 관리자에게 요청하세요."
        )
    return sess


def require_role_management(session: UserSession | None = None) -> UserSession:
    sess = enforce_session_tenant_access(session or get_session())
    if not can_manage_user_roles(session_role(sess)):
        raise AccessDenied("사용자 권한 설정은 관리자만 가능합니다.")
    return sess


def set_user_role_for_tenant(
    target_user_id: str,
    role: str,
    *,
    session: UserSession | None = None,
) -> None:
    sess = require_role_management(session)
    target = get_user(target_user_id)
    if target is None or target.tenant_id != sess.tenant_id:
        raise AccessDenied("같은 고객사 사용자만 권한을 변경할 수 있습니다.")
    update_user_role(target_user_id, role)


def list_tenant_users_with_roles(tenant_id: str) -> list[dict[str, str]]:
    from core.org_access import org_summary_for_user

    out = []
    for u in list_users_for_tenant(tenant_id):
        summary = org_summary_for_user(u.user_id)
        out.append(
            {
                "user_id": u.user_id,
                "username": u.username,
                "display_name": u.display_name,
                "role": normalize_role(u.role),
                "role_label": role_label(u.role),
                "org_unit": summary.get("org_unit", ""),
                "position": summary.get("position", ""),
                "platforms": summary.get("platforms", ""),
            }
        )
    return out
