"""Workflow API/Rust migration contract metadata."""

from __future__ import annotations

from typing import Any

from core.workflow import constants as c
from core.workflow.business_trip import TRIP_SOURCE_KEYS, TRIP_VIEW_MODEL_KEYS


def workflow_business_trip_lifecycle_example() -> dict[str, Any]:
    """Return the Rust-owned pure business-trip lifecycle contract shape."""
    return {
        "rust_crate": "bitween-workflow-core",
        "rust_module": "business_trip",
        "rust_entrypoints": [
            "normalize_trip_status",
            "normalize_kpi_reflection_status",
            "normalize_trip_source",
            "migrate_business_trip_record",
            "business_trip_view_model",
            "business_trip_source_matches",
            "can_transition_trip_status",
            "transition_trip_status",
        ],
        "python_compatibility_source": "core.workflow.business_trip",
        "python_boundary": (
            "Python compatibility code may still own workflow JSON persistence, document/task/report/KPI side effects, "
            "authorization profile lookup, overdue escalation, notifications, calendar/To-Do links, and UI bridges."
        ),
        "trip_statuses": list(c.TRIP_STATUSES),
        "kpi_reflection_statuses": list(c.KPI_REFLECTION_STATUSES),
        "source_kinds": list(c.TRIP_SOURCE_KINDS),
        "source_keys": list(TRIP_SOURCE_KEYS),
        "view_model_keys": list(TRIP_VIEW_MODEL_KEYS),
        "transition_edges": [
            "draft -> planned",
            "draft -> cancelled",
            "planned -> approved",
            "planned -> cancelled",
            "approved -> in_progress",
            "approved -> cancelled",
            "in_progress -> diary_due",
            "in_progress -> overdue",
            "diary_due -> completed",
            "diary_due -> overdue",
            "overdue -> completed",
            "overdue -> cancelled",
        ],
        "example_legacy_input": {
            "id": "legacy-1",
            "tenant_id": "",
            "status": "unknown-status",
            "source": {"kind": "bad", "document_id": "DOC-7"},
            "legacy_note": "kept",
        },
        "example_migrated_result": {
            "id": "legacy-1",
            "trip_id": "legacy-1",
            "tenant_id": "tenant-a",
            "origin_tenant_id": "tenant-a",
            "status": c.TRIP_STATUS_DRAFT,
            "kpi_reflection_status": c.KPI_REFLECTION_BLOCKED,
            "source": {"kind": c.TRIP_SOURCE_KIND_MANUAL, "document_id": "DOC-7", "dedupe_key": "DOC-7"},
            "dedupe_key": "DOC-7",
            "legacy_note": "kept",
        },
        "transition_timestamp_effects": {
            "in_progress": ["updated_at", "actual_start when missing"],
            "diary_due": ["updated_at", "actual_start when missing", "actual_end when missing", "diary_due_at when missing"],
            "overdue": ["updated_at", "overdue_at when missing"],
            "completed": ["updated_at", "actual_end/completed_at when KPI is blocked", "kpi_reflection_status ready when KPI is blocked"],
            "cancelled": ["updated_at", "kpi_reflection_status not_applicable"],
        },
        "invariants": [
            "invalid trip statuses normalize to draft",
            "invalid KPI reflection statuses normalize to blocked",
            "cancelled trips always use not_applicable KPI reflection status",
            "non-completed trips cannot keep ready/reflected KPI reflection statuses",
            "source kind falls back to manual and dedupe_key falls back to document_id",
            "migration preserves unknown fields while freezing required lifecycle keys",
            "view_model_keys remain stable for UI and API wrappers",
            "invalid status transitions are rejected instead of silently mutating lifecycle rows",
        ],
    }


def workflow_business_trip_permissions_example() -> dict[str, Any]:
    """Return the Rust-owned supplied-profile business-trip permission contract."""
    return {
        "rust_crate": "bitween-workflow-core",
        "rust_module": "business_trip_permissions",
        "rust_entrypoints": [
            "workflow_roles",
            "is_business_trip_legal_scope_allowed",
            "is_business_trip_document_legal_scope_allowed",
            "is_business_trip_related_document",
            "can_view_business_trip_lifecycle",
            "can_manage_business_trip_lifecycle",
            "can_evaluate_business_trip_overdue",
            "can_run_business_trip_overdue_evaluator",
            "can_administer_business_trip_lifecycle",
            "can_manage_execution_task",
            "can_close_month",
            "can_view_site_report",
        ],
        "python_compatibility_source": "core.workflow.permissions",
        "python_boundary": (
            "Python compatibility code may still own UserSession conversion, get_user_profile lookup, "
            "workflow JSON persistence, document/task/report/KPI side effects, overdue evaluation, "
            "notifications, calendar/To-Do links, and UI bridges. Rust permission predicates expect "
            "supplied principal, trip, user profile, and optional requester/traveler profile DTOs."
        ),
        "role_values": [
            c.WF_ROLE_ADMIN,
            c.WF_ROLE_EXECUTIVE,
            c.WF_ROLE_SITE_MANAGER,
            c.WF_ROLE_DEPT_MANAGER,
            c.WF_ROLE_APPROVER,
            c.WF_ROLE_REQUESTER,
            c.WF_ROLE_EXECUTOR,
            c.WF_ROLE_FINANCE,
            c.WF_ROLE_HR,
            c.WF_ROLE_VIEWER,
        ],
        "role_expansions": [
            "admin -> admin/executive/approver/finance/hr",
            "finance -> finance/approver/executive",
            "empty workflow role set -> requester",
        ],
        "permission_dtos": [
            "BusinessTripPrincipal",
            "BusinessTripProfile",
            "BusinessTripPermissionTrip",
            "BusinessTripPermissionInput",
            "BusinessTripPermissionDocument",
        ],
        "legal_scope_invariants": [
            "row tenant_id must match requested workflow storage tenant when present",
            "missing principal tenant_id preserves legacy legal-scope compatibility",
            "origin/legal tenant users pass the legal-scope gate",
            "workflow-root tenant users can pass when storage tenant differs from origin/legal tenant",
            "sibling legal-tenant admins are rejected through shared workflow-root storage",
        ],
        "visibility_invariants": [
            "Admin/executive/finance can view within legal scope",
            "Requester or executor can view within legal scope",
            "traveler_user_id is used as owner fallback when requester_id is absent",
            "Explicit approver can view only when approver role is present",
            "Supplied requester manager can view",
            "Site manager/HR can view scoped site trips",
            "Department manager/site manager/HR can view scoped department trips",
            "Viewer role is scoped-only access",
        ],
        "manage_invariants": [
            "Manage authority is narrower than visibility",
            "Admin/executive/finance can manage within legal scope",
            "Requester or executor can manage within legal scope",
            "Manager, site, department, viewer, and approver grants do not imply manage authority",
        ],
        "administer_invariants": [
            "Tenant-wide administration is limited to admin/executive/finance",
            "Site, department, HR, requester, executor, approver, and viewer roles are not tenant-wide administrators",
        ],
        "overdue_invariants": [
            "Overdue evaluator invocation is limited to admin/executive/finance/site_manager/department_manager/hr",
            "Overdue evaluation applies legal-scope isolation",
            "Admin/executive/finance can evaluate any legally scoped trip",
            "Site manager/HR evaluation is site scoped",
            "Department manager/site manager/HR evaluation is department scoped",
            "Requester/executor ownership does not imply overdue evaluation authority",
            "Viewer and explicit approver grants do not imply overdue evaluation authority",
        ],
        "document_scope_invariants": [
            "BUSINESS_TRIP_REQUEST documents are business-trip related",
            "content trip_id marks a document as business-trip related",
            "Non-business-trip documents pass unchanged",
            "document origin_tenant_id wins over content tenant fields",
            "content origin_tenant_id wins over content legal_tenant_id",
            "related documents use the requested workflow storage tenant as row tenant",
            "missing principal tenant preserves legacy document-scope compatibility",
            "sibling legal-tenant principals fail related-document scope",
        ],
        "operational_invariants": [
            "Admin/executive/finance can view any site report",
            "Non-admin site report visibility requires matching supplied profile site_ids",
            "Admin/finance can close month only when they can view the site report",
            "Site managers can close month only for visible sites",
            "HR and viewer site visibility does not imply month-close authority",
            "Admin can manage any execution task",
            "Assigned executor can manage their execution task",
            "Executor role without assignment does not grant task management",
        ],
    }


def workflow_api_contract() -> dict[str, Any]:
    """Return workflow API contract metadata for Rust migration slices."""
    return {
        "business_trip_lifecycle": workflow_business_trip_lifecycle_example(),
        "business_trip_permissions": workflow_business_trip_permissions_example(),
        "response": {
            "business_trip_lifecycle_entrypoint": "bitween_workflow_core::business_trip::transition_trip_status(record, target, now_iso)",
            "business_trip_permissions_entrypoint": "bitween_workflow_core::business_trip_permissions::can_view_business_trip_lifecycle(input)",
        },
    }
