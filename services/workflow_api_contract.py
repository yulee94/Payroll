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


def workflow_api_contract() -> dict[str, Any]:
    """Return workflow API contract metadata for Rust migration slices."""
    return {
        "business_trip_lifecycle": workflow_business_trip_lifecycle_example(),
        "response": {
            "business_trip_lifecycle_entrypoint": "bitween_workflow_core::business_trip::transition_trip_status(record, target, now_iso)",
        },
    }
