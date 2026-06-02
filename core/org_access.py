"""
core/org_access.py - 조직·직위 기반 데이터·플랫폼 접근 제어
"""

from __future__ import annotations

from typing import Any

from core.access_control import can_manage_user_roles, can_view_executive_payroll, session_role
from core.org_positions import (
    ORG_PLATFORM_LABELS,
    PERM_ACCOUNTING,
    PERM_ACCOUNTING_CLOSE,
    PERM_BIDDING,
    PERM_MAINTENANCE,
    PERM_ORG_MANAGE,
    PERM_PAYROLL,
    PERM_PAYROLL_EXEC,
    PERM_PAYROLL_SETTINGS,
    PERM_TENANT_ADMIN,
    PERM_USER_ROLES,
    PERM_WORKFLOW,
    PERM_WORKFLOW_APPROVE,
    PLATFORM_TO_PERM,
    POS_CEO,
    normalize_position,
    permissions_for_position,
    position_label,
)
from core.org_store import descendant_unit_ids, effective_platform_ids_for_unit, get_unit
from core.roles import ROLE_ADMIN, ROLE_FINANCE, normalize_role
from core.session_service import UserSession, get_session, require_session
from core.user_store import UserRecord, get_user


def get_user_org_context(user_id: str) -> dict[str, str]:
    rec = get_user(user_id)
    if not rec:
        return {
            "org_unit_id": "",
            "position": "",
            "position_label": "",
            "manager_user_id": "",
        }
    pos = normalize_position(rec.position)
    return {
        "org_unit_id": rec.org_unit_id,
        "position": pos,
        "position_label": position_label(pos),
        "manager_user_id": rec.manager_user_id,
    }


def _effective_permissions(rec: UserRecord | None) -> frozenset[str]:
    if rec is None:
        return frozenset()
    pos = normalize_position(rec.position)
    perms = set(permissions_for_position(pos))

    # 레거시 역할 보강
    role = normalize_role(rec.role)
    if role == ROLE_ADMIN:
        perms.update(permissions_for_position(POS_CEO))
    elif role == ROLE_FINANCE:
        perms.update({PERM_PAYROLL, PERM_PAYROLL_EXEC, PERM_WORKFLOW, PERM_WORKFLOW_APPROVE})

    if rec.org_unit_id:
        team_platforms = effective_platform_ids_for_unit(rec.tenant_id, rec.org_unit_id)
        for plat_id in ("payroll", "hr", "recruitment", "kpi", "workflow", "maintenance", "bidding", "accounting"):
            perm = PLATFORM_TO_PERM.get(plat_id)
            if perm and plat_id not in team_platforms and pos != POS_CEO:
                perms.discard(perm)
                if plat_id == "payroll":
                    perms.discard(PERM_PAYROLL_EXEC)
                    perms.discard(PERM_PAYROLL_SETTINGS)
                if plat_id == "accounting":
                    perms.discard(PERM_ACCOUNTING_CLOSE)

    return frozenset(perms)


def user_permissions(user_id: str) -> frozenset[str]:
    return _effective_permissions(get_user(user_id))


def session_permissions(session: UserSession | None = None) -> frozenset[str]:
    sess = session or get_session()
    if sess is None:
        return frozenset()
    return user_permissions(sess.user_id)


def has_permission(perm: str, *, session: UserSession | None = None) -> bool:
    return perm in session_permissions(session)


def can_manage_org(session: UserSession | None = None) -> bool:
    return has_permission(PERM_ORG_MANAGE, session=session) or can_manage_user_roles(session_role(session))


def can_access_platform(platform_id: str, *, session: UserSession | None = None) -> bool:
    perm = PLATFORM_TO_PERM.get(str(platform_id).strip())
    if not perm:
        return True
    return has_permission(perm, session=session)


def can_access_payroll_settings(session: UserSession | None = None) -> bool:
    return has_permission(PERM_PAYROLL_SETTINGS, session=session)


def can_approve_workflow(session: UserSession | None = None) -> bool:
    return has_permission(PERM_WORKFLOW_APPROVE, session=session)


def can_view_accounting_close(session: UserSession | None = None) -> bool:
    return has_permission(PERM_ACCOUNTING_CLOSE, session=session)


def can_manage_tenant_settings(session: UserSession | None = None) -> bool:
    return has_permission(PERM_TENANT_ADMIN, session=session)


def can_create_subordinate_in_unit(
    manager_user_id: str,
    target_unit_id: str,
) -> bool:
    mgr = get_user(manager_user_id)
    if mgr is None:
        return False
    if can_manage_org(UserSession.from_record(mgr)):
        return True
    ctx = get_user_org_context(manager_user_id)
    my_unit = ctx["org_unit_id"]
    if not my_unit:
        return False
    scope = descendant_unit_ids(mgr.tenant_id, my_unit, include_self=True)
    return str(target_unit_id).strip() in scope


def require_org_management(session: UserSession | None = None) -> UserSession:
    sess = require_session() if session is None else session
    if not can_manage_org(sess):
        raise PermissionError("조직·계정 관리는 대표이사 또는 조직 관리자만 가능합니다.")
    return sess


def require_platform_access(platform_id: str, session: UserSession | None = None) -> UserSession:
    sess = require_session() if session is None else session
    if not can_access_platform(platform_id, session=sess):
        label = ORG_PLATFORM_LABELS.get(platform_id, platform_id)
        raise PermissionError(f"「{label}」에 대한 접근 권한이 없습니다. 소속 팀·직위를 확인하세요.")
    return sess


def list_accessible_platform_ids(session: UserSession | None = None) -> frozenset[str]:
    perms = session_permissions(session)
    out: set[str] = set()
    for plat_id, perm in PLATFORM_TO_PERM.items():
        if perm in perms:
            out.add(plat_id)
    return frozenset(out)


def org_summary_for_user(user_id: str) -> dict[str, str]:
    rec = get_user(user_id)
    if rec is None:
        return {}
    ctx = get_user_org_context(user_id)
    unit = get_unit(rec.tenant_id, ctx["org_unit_id"]) if ctx["org_unit_id"] else None
    mgr = get_user(ctx["manager_user_id"]) if ctx["manager_user_id"] else None
    perms = user_permissions(user_id)
    platforms = [
        ORG_PLATFORM_LABELS[p]
        for p in ("payroll", "workflow", "maintenance", "bidding", "accounting")
        if PLATFORM_TO_PERM.get(p) in perms
    ]
    return {
        "display_name": rec.display_name,
        "username": rec.username,
        "role": rec.role,
        "org_unit": unit.name if unit else "(미배치)",
        "position": ctx["position_label"],
        "manager": mgr.display_name if mgr else "",
        "platforms": ", ".join(platforms) if platforms else "(없음)",
        "executive_payroll": "가능" if can_view_executive_payroll(rec.role) or PERM_PAYROLL_EXEC in perms else "불가",
    }
