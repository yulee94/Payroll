"""
core/workflow/permissions.py - 워크플로우 권한 검사
"""

from __future__ import annotations

from typing import Any

from core.roles import ROLE_ADMIN, ROLE_FINANCE, normalize_role
from core.session_service import UserSession
from core.workflow.constants import (
    DOC_STATUS_APPROVED,
    DOC_STATUS_CLOSED,
    DOC_STATUS_DRAFT,
    DOC_STATUS_IN_REVIEW,
    DOC_STATUS_REQUESTED_CHANGES,
    DOC_STATUS_SUBMITTED,
    STEP_PENDING,
    WF_ROLE_ADMIN,
    WF_ROLE_APPROVER,
    WF_ROLE_EXECUTIVE,
    WF_ROLE_EXECUTOR,
    WF_ROLE_FINANCE,
    WF_ROLE_HR,
    WF_ROLE_SITE_MANAGER,
)
from core.workflow.store import get_user_profile


def _workflow_roles(user: dict[str, Any] | UserSession, profile: dict[str, Any] | None) -> set[str]:
    roles: set[str] = set()
    if profile:
        for r in profile.get("workflow_roles") or []:
            roles.add(str(r))
    base = normalize_role(user.get("role") if isinstance(user, dict) else getattr(user, "role", ""))
    if base == ROLE_ADMIN:
        roles.update({WF_ROLE_ADMIN, WF_ROLE_EXECUTIVE, WF_ROLE_APPROVER, WF_ROLE_FINANCE, WF_ROLE_HR})
    elif base == ROLE_FINANCE:
        roles.update({WF_ROLE_FINANCE, WF_ROLE_APPROVER, WF_ROLE_EXECUTIVE})
    if not roles:
        roles.add("requester")
    return roles


def _user_id(user: dict[str, Any] | UserSession) -> str:
    if isinstance(user, UserSession):
        return user.user_id
    return str(user.get("user_id") or user.get("id") or "")


def can_view_document(user: dict[str, Any] | UserSession, document: dict[str, Any], *, tenant_id: str) -> bool:
    uid = _user_id(user)
    profile = get_user_profile(tenant_id, uid)
    roles = _workflow_roles(user, profile)
    if WF_ROLE_ADMIN in roles or WF_ROLE_EXECUTIVE in roles or WF_ROLE_FINANCE in roles:
        return True
    if document.get("requester_id") == uid:
        return True
    for step in document.get("approval_steps") or []:
        if step.get("approver_id") == uid:
            return True
    site_id = document.get("site_id")
    if site_id and profile:
        allowed_sites = profile.get("site_ids") or []
        if site_id in allowed_sites and (WF_ROLE_SITE_MANAGER in roles or WF_ROLE_HR in roles):
            return True
    return False


def can_edit_document(user: dict[str, Any] | UserSession, document: dict[str, Any], *, tenant_id: str) -> bool:
    if document.get("status") in (DOC_STATUS_CLOSED, DOC_STATUS_APPROVED):
        return False
    uid = _user_id(user)
    if document.get("requester_id") != uid:
        return False
    return document.get("status") in (
        DOC_STATUS_DRAFT,
        DOC_STATUS_REQUESTED_CHANGES,
    )


def can_submit_document(user: dict[str, Any] | UserSession, document: dict[str, Any], *, tenant_id: str) -> bool:
    return can_edit_document(user, document, tenant_id=tenant_id)


def can_approve_document(user: dict[str, Any] | UserSession, document: dict[str, Any], *, tenant_id: str) -> bool:
    if document.get("status") not in (DOC_STATUS_SUBMITTED, DOC_STATUS_IN_REVIEW):
        return False
    uid = _user_id(user)
    steps = document.get("approval_steps") or []
    current = next((s for s in steps if s.get("status") == STEP_PENDING), None)
    if not current:
        return False
    if str(current.get("approver_id") or "") == uid:
        return True
    profile = get_user_profile(tenant_id, uid)
    roles = _workflow_roles(user, profile)
    try:
        from core.org_access import can_approve_workflow

        if can_approve_workflow(session=user if isinstance(user, UserSession) else None):
            if WF_ROLE_ADMIN in roles or WF_ROLE_EXECUTIVE in roles or WF_ROLE_FINANCE in roles:
                return True
    except Exception:
        pass
    return False


def can_view_site_report(user: dict[str, Any] | UserSession, site_id: str, *, tenant_id: str) -> bool:
    uid = _user_id(user)
    profile = get_user_profile(tenant_id, uid)
    roles = _workflow_roles(user, profile)
    if WF_ROLE_ADMIN in roles or WF_ROLE_EXECUTIVE in roles or WF_ROLE_FINANCE in roles:
        return True
    if not profile:
        return False
    return site_id in (profile.get("site_ids") or [])


def can_close_month(user: dict[str, Any] | UserSession, site_id: str, *, tenant_id: str) -> bool:
    profile = get_user_profile(tenant_id, _user_id(user))
    roles = _workflow_roles(user, profile)
    if WF_ROLE_ADMIN in roles or WF_ROLE_FINANCE in roles:
        return can_view_site_report(user, site_id, tenant_id=tenant_id)
    return WF_ROLE_SITE_MANAGER in roles and can_view_site_report(user, site_id, tenant_id=tenant_id)


def can_manage_execution_task(
    user: dict[str, Any] | UserSession, task: dict[str, Any], *, tenant_id: str
) -> bool:
    uid = _user_id(user)
    profile = get_user_profile(tenant_id, uid)
    roles = _workflow_roles(user, profile)
    if WF_ROLE_ADMIN in roles:
        return True
    if task.get("executor_id") == uid:
        return True
    return WF_ROLE_EXECUTOR in roles and task.get("executor_id") == uid
