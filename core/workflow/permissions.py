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
    DOC_TYPE_BUSINESS_TRIP_REQUEST,
    STEP_PENDING,
    WF_ROLE_ADMIN,
    WF_ROLE_APPROVER,
    WF_ROLE_DEPT_MANAGER,
    WF_ROLE_EXECUTIVE,
    WF_ROLE_EXECUTOR,
    WF_ROLE_FINANCE,
    WF_ROLE_HR,
    WF_ROLE_SITE_MANAGER,
    WF_ROLE_VIEWER,
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


def _user_tenant_id(user: dict[str, Any] | UserSession) -> str:
    if isinstance(user, UserSession):
        return str(user.tenant_id or "").strip()
    return str(user.get("tenant_id") or user.get("origin_tenant_id") or "").strip()


def is_business_trip_legal_scope_allowed(
    user: dict[str, Any] | UserSession,
    trip: dict[str, Any],
    *,
    tenant_id: str,
) -> bool:
    """Separate legal-tenant authority from shared workflow-root storage.

    Workflow documents may be stored in a group root tenant for cross-entity
    approvals. Business-trip lifecycle rows remain legal-entity scoped:
    sibling tenant admins do not inherit read/write authority simply because
    they share the same workflow DB. The workflow root itself is treated as the
    explicit group-HQ scope.
    """
    storage_tenant = str(tenant_id or "").strip()
    row_storage_tenant = str(trip.get("tenant_id") or "").strip()
    if row_storage_tenant and row_storage_tenant != storage_tenant:
        return False
    origin_tenant = str(
        trip.get("origin_tenant_id")
        or trip.get("legal_tenant_id")
        or row_storage_tenant
        or storage_tenant
    ).strip()
    user_tenant = _user_tenant_id(user)
    if not user_tenant:
        return True
    if user_tenant == origin_tenant:
        return True
    return bool(storage_tenant and user_tenant == storage_tenant and storage_tenant != origin_tenant)


def _is_business_trip_related_document(document: dict[str, Any]) -> bool:
    if document.get("document_type") == DOC_TYPE_BUSINESS_TRIP_REQUEST:
        return True
    payload = document.get("content_json") if isinstance(document.get("content_json"), dict) else {}
    return bool(str(payload.get("trip_id") or "").strip())


def is_business_trip_document_legal_scope_allowed(
    user: dict[str, Any] | UserSession,
    document: dict[str, Any],
    *,
    tenant_id: str,
) -> bool:
    """Tenant/legal-entity gate for business-trip documents and artifacts.

    Business-trip request, work-log, and report documents live in the workflow
    document table, but their side effects are legal-tenant scoped. Being a
    sibling-tenant admin or an assigned approver in the same workflow-root DB is
    not enough to read or mutate another legal tenant's trip evidence.
    """
    if not _is_business_trip_related_document(document):
        return True
    storage_tenant = str(tenant_id or "").strip()
    payload = document.get("content_json") if isinstance(document.get("content_json"), dict) else {}
    origin_tenant = str(
        document.get("origin_tenant_id")
        or payload.get("origin_tenant_id")
        or payload.get("legal_tenant_id")
        or storage_tenant
    ).strip()
    return is_business_trip_legal_scope_allowed(
        user,
        {
            "tenant_id": storage_tenant,
            "origin_tenant_id": origin_tenant,
            "legal_entity_id": str(
                document.get("legal_entity_id") or payload.get("legal_entity_id") or ""
            ).strip(),
        },
        tenant_id=storage_tenant,
    )


def can_view_document(user: dict[str, Any] | UserSession, document: dict[str, Any], *, tenant_id: str) -> bool:
    if not is_business_trip_document_legal_scope_allowed(user, document, tenant_id=tenant_id):
        return False
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
    if not is_business_trip_document_legal_scope_allowed(user, document, tenant_id=tenant_id):
        return False
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
    if not is_business_trip_document_legal_scope_allowed(user, document, tenant_id=tenant_id):
        return False
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


def can_view_business_trip_lifecycle(
    user: dict[str, Any] | UserSession, trip: dict[str, Any], *, tenant_id: str
) -> bool:
    """Tenant-bound lifecycle visibility predicate for business trips.

    Viewer role is intentionally not global access. A user can see a trip only
    inside the requested tenant boundary and through admin/executive/finance,
    direct ownership, or manager site/department scope.
    """
    if not is_business_trip_legal_scope_allowed(user, trip, tenant_id=tenant_id):
        return False
    uid = _user_id(user)
    profile = get_user_profile(tenant_id, uid)
    roles = _workflow_roles(user, profile)
    if WF_ROLE_ADMIN in roles or WF_ROLE_EXECUTIVE in roles or WF_ROLE_FINANCE in roles:
        return True
    requester_id = str(trip.get("requester_id") or trip.get("traveler_user_id") or "")
    executor_id = str(trip.get("executor_id") or "")
    if uid in {requester_id, executor_id}:
        return True
    explicit_approvers = {str(v) for v in (trip.get("approver_ids") or trip.get("approval_user_ids") or [])}
    if WF_ROLE_APPROVER in roles and uid in explicit_approvers:
        return True
    if not profile:
        return False
    if requester_id:
        traveler_profile = get_user_profile(tenant_id, requester_id)
        if traveler_profile and str(traveler_profile.get("manager_user_id") or "") == uid:
            return True
    site_id = str(trip.get("site_id") or "")
    dept_id = str(trip.get("department_id") or trip.get("org_unit_id") or "")
    allowed_sites = {str(v) for v in (profile.get("site_ids") or [])}
    allowed_departments = {str(v) for v in (profile.get("department_ids") or profile.get("org_unit_ids") or [])}
    if site_id and site_id in allowed_sites and (WF_ROLE_SITE_MANAGER in roles or WF_ROLE_HR in roles):
        return True
    if dept_id and dept_id in allowed_departments and (
        WF_ROLE_DEPT_MANAGER in roles or WF_ROLE_SITE_MANAGER in roles or WF_ROLE_HR in roles
    ):
        return True
    if WF_ROLE_VIEWER in roles:
        scoped_sites = {str(v) for v in (profile.get("viewer_site_ids") or [])}
        scoped_departments = {str(v) for v in (profile.get("viewer_department_ids") or [])}
        if (site_id and site_id in scoped_sites) or (dept_id and dept_id in scoped_departments):
            return True
    return False

def can_manage_business_trip_lifecycle(
    user: dict[str, Any] | UserSession, trip: dict[str, Any], *, tenant_id: str
) -> bool:
    """Write predicate for business-trip lifecycle transitions.

    Read visibility is broader than mutation authority. Lifecycle changes are
    restricted to admins/executives/finance plus direct requester/executor owners
    within the tenant boundary.
    """
    if not is_business_trip_legal_scope_allowed(user, trip, tenant_id=tenant_id):
        return False
    uid = _user_id(user)
    profile = get_user_profile(tenant_id, uid)
    roles = _workflow_roles(user, profile)
    if WF_ROLE_ADMIN in roles or WF_ROLE_EXECUTIVE in roles or WF_ROLE_FINANCE in roles:
        return True
    requester_id = str(trip.get("requester_id") or trip.get("traveler_user_id") or "")
    executor_id = str(trip.get("executor_id") or "")
    return uid in {requester_id, executor_id}


def can_administer_business_trip_lifecycle(user: dict[str, Any] | UserSession, *, tenant_id: str) -> bool:
    """Tenant-wide mutation authority for repair jobs and batch evaluators."""
    uid = _user_id(user)
    profile = get_user_profile(tenant_id, uid)
    roles = _workflow_roles(user, profile)
    return WF_ROLE_ADMIN in roles or WF_ROLE_EXECUTIVE in roles or WF_ROLE_FINANCE in roles


def can_run_business_trip_overdue_evaluator(user: dict[str, Any] | UserSession, *, tenant_id: str) -> bool:
    """Whether a user may invoke overdue evaluation side effects at all."""
    uid = _user_id(user)
    profile = get_user_profile(tenant_id, uid)
    roles = _workflow_roles(user, profile)
    return any(
        role in roles
        for role in (
            WF_ROLE_ADMIN,
            WF_ROLE_EXECUTIVE,
            WF_ROLE_FINANCE,
            WF_ROLE_SITE_MANAGER,
            WF_ROLE_DEPT_MANAGER,
            WF_ROLE_HR,
        )
    )


def can_evaluate_business_trip_overdue(
    user: dict[str, Any] | UserSession, trip: dict[str, Any], *, tenant_id: str
) -> bool:
    """Scoped authority for overdue evaluation side effects.

    Direct travelers/executors can view their trips, but marking delayed tasks
    and escalating to managers is an operational control reserved for tenant
    admins/executives/finance or managers over the trip's site/department.
    """
    if not is_business_trip_legal_scope_allowed(user, trip, tenant_id=tenant_id):
        return False
    uid = _user_id(user)
    profile = get_user_profile(tenant_id, uid)
    roles = _workflow_roles(user, profile)
    if WF_ROLE_ADMIN in roles or WF_ROLE_EXECUTIVE in roles or WF_ROLE_FINANCE in roles:
        return True
    if not profile:
        return False
    site_id = str(trip.get("site_id") or "")
    dept_id = str(trip.get("department_id") or trip.get("org_unit_id") or "")
    allowed_sites = {str(v) for v in (profile.get("site_ids") or [])}
    allowed_departments = {str(v) for v in (profile.get("department_ids") or profile.get("org_unit_ids") or [])}
    if site_id and site_id in allowed_sites and (WF_ROLE_SITE_MANAGER in roles or WF_ROLE_HR in roles):
        return True
    return bool(
        dept_id
        and dept_id in allowed_departments
        and (WF_ROLE_DEPT_MANAGER in roles or WF_ROLE_SITE_MANAGER in roles or WF_ROLE_HR in roles)
    )
