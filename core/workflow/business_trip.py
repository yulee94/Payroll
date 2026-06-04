"""Business-trip lifecycle contracts for workflow foundation lanes.

This module freezes the lifecycle taxonomy and tenant-bound data shape used by
later form, follow-up, KPI, and UI lanes. It intentionally contains no UI or KPI
calculation behavior.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.workflow.constants import (
    KPI_REFLECTION_BLOCKED,
    KPI_REFLECTION_NOT_APPLICABLE,
    KPI_REFLECTION_READY,
    KPI_REFLECTION_REFLECTED,
    KPI_REFLECTION_STATUSES,
    TRIP_SOURCE_KIND_MANUAL,
    TRIP_SOURCE_KINDS,
    TRIP_STATUS_APPROVED,
    TRIP_STATUS_CANCELLED,
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_DIARY_DUE,
    TRIP_STATUS_DRAFT,
    TRIP_STATUS_IN_PROGRESS,
    TRIP_STATUS_OVERDUE,
    TRIP_STATUS_PLANNED,
    TRIP_STATUSES,
)
from core.workflow.store import _new_id, _now_iso

TRIP_VIEW_MODEL_KEYS: tuple[str, ...] = (
    "trip_id",
    "tenant_id",
    "status",
    "kpi_reflection_status",
    "title",
    "requester_id",
    "executor_id",
    "site_id",
    "department_id",
    "period_start",
    "period_end",
    "approved_document_id",
    "diary_document_id",
    "report_document_id",
    "source",
    "dedupe_key",
    "created_at",
    "updated_at",
)

TRIP_SOURCE_KEYS: tuple[str, ...] = ("kind", "document_id", "dedupe_key")

TRIP_STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    TRIP_STATUS_DRAFT: (TRIP_STATUS_PLANNED, TRIP_STATUS_CANCELLED),
    TRIP_STATUS_PLANNED: (TRIP_STATUS_APPROVED, TRIP_STATUS_CANCELLED),
    TRIP_STATUS_APPROVED: (TRIP_STATUS_IN_PROGRESS, TRIP_STATUS_CANCELLED),
    TRIP_STATUS_IN_PROGRESS: (TRIP_STATUS_DIARY_DUE, TRIP_STATUS_OVERDUE, TRIP_STATUS_COMPLETED),
    TRIP_STATUS_DIARY_DUE: (TRIP_STATUS_COMPLETED, TRIP_STATUS_OVERDUE),
    TRIP_STATUS_OVERDUE: (TRIP_STATUS_COMPLETED, TRIP_STATUS_CANCELLED),
    TRIP_STATUS_COMPLETED: (),
    TRIP_STATUS_CANCELLED: (),
}


def normalize_trip_status(status: str | None) -> str:
    value = str(status or "").strip()
    return value if value in TRIP_STATUSES else TRIP_STATUS_DRAFT


def normalize_kpi_reflection_status(status: str | None) -> str:
    value = str(status or "").strip()
    return value if value in KPI_REFLECTION_STATUSES else KPI_REFLECTION_BLOCKED


def normalize_trip_source(source: dict[str, Any] | None) -> dict[str, str]:
    raw = source if isinstance(source, dict) else {}
    kind = str(raw.get("kind") or TRIP_SOURCE_KIND_MANUAL).strip()
    if kind not in TRIP_SOURCE_KINDS:
        kind = TRIP_SOURCE_KIND_MANUAL
    document_id = str(raw.get("document_id") or "").strip()
    dedupe_key = str(raw.get("dedupe_key") or document_id or "").strip()
    return {"kind": kind, "document_id": document_id, "dedupe_key": dedupe_key}


def default_business_trip_record(default_tenant_id: str, **fields: Any) -> dict[str, Any]:
    source = normalize_trip_source(fields.get("source"))
    now = _now_iso()
    trip_id = str(fields.get("trip_id") or fields.get("id") or _new_id()).strip()
    record = {
        "id": trip_id,
        "trip_id": trip_id,
        "tenant_id": str(fields.get("tenant_id") or default_tenant_id or "").strip(),
        "status": normalize_trip_status(fields.get("status")),
        "kpi_reflection_status": normalize_kpi_reflection_status(fields.get("kpi_reflection_status")),
        "title": str(fields.get("title") or "").strip(),
        "requester_id": str(fields.get("requester_id") or "").strip(),
        "executor_id": str(fields.get("executor_id") or "").strip(),
        "site_id": str(fields.get("site_id") or "").strip(),
        "department_id": str(fields.get("department_id") or "").strip(),
        "period_start": str(fields.get("period_start") or "").strip(),
        "period_end": str(fields.get("period_end") or "").strip(),
        "approved_document_id": str(fields.get("approved_document_id") or "").strip(),
        "diary_document_id": str(fields.get("diary_document_id") or "").strip(),
        "report_document_id": str(fields.get("report_document_id") or "").strip(),
        "source": source,
        "dedupe_key": str(fields.get("dedupe_key") or source.get("dedupe_key") or trip_id).strip(),
        "created_at": str(fields.get("created_at") or now),
        "updated_at": str(fields.get("updated_at") or now),
    }
    return record


def migrate_business_trip_record(tenant_id: str, record: dict[str, Any]) -> dict[str, Any]:
    migrated = default_business_trip_record(tenant_id, **(record or {}))
    # Preserve unknown fields for forward compatibility while freezing required keys.
    extra = {k: deepcopy(v) for k, v in (record or {}).items() if k not in migrated}
    return {**extra, **migrated}


def migrate_business_trips(db: dict[str, Any], tenant_id: str) -> bool:
    rows = db.setdefault("business_trips", [])
    changed = False
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            changed = True
            continue
        migrated = migrate_business_trip_record(tenant_id, row)
        if migrated != row:
            changed = True
        normalized.append(migrated)
    if rows != normalized:
        db["business_trips"] = normalized
        changed = True
    db.setdefault("business_trip_seq", 0)
    return changed


def can_transition_trip_status(current: str, target: str) -> bool:
    return target in TRIP_STATUS_TRANSITIONS.get(normalize_trip_status(current), ())


def transition_trip_status(record: dict[str, Any], target: str) -> dict[str, Any]:
    current = normalize_trip_status(record.get("status"))
    target = normalize_trip_status(target)
    if target == current:
        return migrate_business_trip_record(str(record.get("tenant_id") or ""), record)
    if not can_transition_trip_status(current, target):
        raise ValueError(f"Invalid business trip status transition: {current} -> {target}")
    updated = migrate_business_trip_record(str(record.get("tenant_id") or ""), record)
    updated["status"] = target
    updated["updated_at"] = _now_iso()
    if target == TRIP_STATUS_COMPLETED and updated.get("kpi_reflection_status") == KPI_REFLECTION_BLOCKED:
        updated["kpi_reflection_status"] = KPI_REFLECTION_READY
    if target in (TRIP_STATUS_CANCELLED,):
        updated["kpi_reflection_status"] = KPI_REFLECTION_NOT_APPLICABLE
    return updated


def business_trip_view_model(record: dict[str, Any]) -> dict[str, Any]:
    migrated = migrate_business_trip_record(str(record.get("tenant_id") or ""), record)
    return {key: deepcopy(migrated.get(key, "")) for key in TRIP_VIEW_MODEL_KEYS}


def find_business_trip_by_source(db: dict[str, Any], *, source: dict[str, Any]) -> dict[str, Any] | None:
    normalized = normalize_trip_source(source)
    dedupe_key = normalized.get("dedupe_key") or ""
    document_id = normalized.get("document_id") or ""
    for row in db.get("business_trips") or []:
        row_source = normalize_trip_source(row.get("source"))
        if dedupe_key and (row.get("dedupe_key") == dedupe_key or row_source.get("dedupe_key") == dedupe_key):
            return row
        if document_id and row_source.get("document_id") == document_id:
            return row
    return None
