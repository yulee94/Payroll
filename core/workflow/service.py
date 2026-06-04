"""
core/workflow/service.py - 문서·결재·실행업무·보고·마감 비즈니스 로직
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import date
from typing import Any

from core.session_service import UserSession, require_session
from core.workflow import permissions as wf_perm
from core.workflow.constants import (
    DOC_STATUS_APPROVED,
    DOC_STATUS_CANCELLED,
    DOC_STATUS_COMPLETED,
    DOC_STATUS_DRAFT,
    DOC_STATUS_IN_REVIEW,
    DOC_STATUS_REJECTED,
    DOC_STATUS_REQUESTED_CHANGES,
    DOC_STATUS_SUBMITTED,
    DOC_TYPE_ATTENDANCE,
    DOC_TYPE_BUSINESS_TRIP_REQUEST,
    DOC_TYPE_EXPENSE,
    DOC_TYPE_GENERAL,
    DOC_TYPE_PURCHASE,
    KPI_REFLECTION_BLOCKED,
    KPI_REFLECTION_NOT_APPLICABLE,
    KPI_REFLECTION_READY,
    KPI_REFLECTION_REFLECTED,
    STEP_APPROVED,
    STEP_PENDING,
    STEP_REJECTED,
    STEP_REQUESTED_CHANGES,
    TASK_COMPLETED,
    TASK_CANCELLED,
    TASK_DELAYED,
    TASK_PENDING,
    TRIP_SOURCE_KIND_WORKFLOW,
    TRIP_STATUS_APPROVED,
    TRIP_STATUS_CANCELLED,
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_DIARY_DUE,
    TRIP_STATUS_DRAFT,
    TRIP_STATUS_IN_PROGRESS,
    TRIP_STATUS_OVERDUE,
    TRIP_STATUS_PLANNED,
    TRIP_STATUS_LABELS,
    WF_ROLE_ADMIN,
    WF_ROLE_DEPT_MANAGER,
    WF_ROLE_EXECUTIVE,
    WF_ROLE_FINANCE,
    WF_ROLE_HR,
    WF_ROLE_SITE_MANAGER,
)
from core.workflow.inbox import count_by_inbox, filter_inbox
from core.workflow.store import (
    _load_raw,
    _new_id,
    _now_iso,
    add_notification,
    append_audit,
    get_user_profile,
    next_document_no,
    with_db,
)
from core.group_store import get_workflow_tenant_id


def _resolve_tenant(tenant_id: str) -> str:
    return get_workflow_tenant_id(tenant_id)


def _uid(sess: UserSession) -> str:
    return sess.user_id


def _is_business_trip_document(doc: dict[str, Any]) -> bool:
    return doc.get("document_type") == DOC_TYPE_BUSINESS_TRIP_REQUEST


def _business_trip_source_for_document(doc: dict[str, Any]) -> dict[str, str]:
    document_id = str(doc.get("id") or "").strip()
    payload = doc.get("content_json") if isinstance(doc.get("content_json"), dict) else {}
    explicit_dedupe = str(payload.get("trip_dedupe_key") or "").strip()
    dedupe_key = ""
    if explicit_dedupe:
        dedupe_key = explicit_dedupe if explicit_dedupe.startswith("business-trip:") else f"business-trip:{explicit_dedupe}"
    elif document_id:
        dedupe_key = f"business-trip:{document_id}"
    return {
        "kind": TRIP_SOURCE_KIND_WORKFLOW,
        "document_id": document_id,
        "dedupe_key": dedupe_key,
    }


def _business_trip_fields_from_document(
    tenant_id: str,
    doc: dict[str, Any],
    *,
    status: str | None = None,
    trip_id: str = "",
) -> dict[str, Any]:
    payload = doc.get("content_json") if isinstance(doc.get("content_json"), dict) else {}
    source = _business_trip_source_for_document(doc)
    title = str(doc.get("title") or payload.get("title") or "").strip()
    return {
        "trip_id": trip_id or str(payload.get("trip_id") or "").strip(),
        "tenant_id": tenant_id,
        "status": status or TRIP_STATUS_DRAFT,
        "title": title,
        "requester_id": str(doc.get("requester_id") or payload.get("traveler_user_id") or "").strip(),
        "executor_id": str(payload.get("recommended_executor_id") or payload.get("executor_id") or "").strip(),
        "site_id": str(doc.get("site_id") or payload.get("site_id") or "").strip(),
        "department_id": str(doc.get("department_id") or payload.get("department_id") or "").strip(),
        "period_start": str(doc.get("period_start") or payload.get("period_start") or "").strip(),
        "period_end": str(doc.get("period_end") or payload.get("period_end") or "").strip(),
        "approved_document_id": str(doc.get("id") or "").strip(),
        "source": source,
        "dedupe_key": source["dedupe_key"],
    }


def _link_document_to_trip(doc: dict[str, Any], trip: dict[str, Any]) -> None:
    payload = doc.setdefault("content_json", {})
    if not isinstance(payload, dict):
        payload = {}
        doc["content_json"] = payload
    payload["trip_id"] = trip.get("trip_id") or trip.get("id") or ""
    payload["business_trip_source"] = deepcopy(trip.get("source") or _business_trip_source_for_document(doc))
    doc["updated_at"] = _now_iso()


def _trip_artifact_kind_from_document(doc: dict[str, Any]) -> str:
    """Classify non-request documents that are explicitly linked to a trip."""
    if _is_business_trip_document(doc):
        return ""
    payload = doc.get("content_json") if isinstance(doc.get("content_json"), dict) else {}
    if not str(payload.get("trip_id") or "").strip():
        return ""
    raw = " ".join(
        str(v or "")
        for v in (
            payload.get("business_trip_artifact"),
            payload.get("artifact_type"),
            payload.get("template_name"),
            payload.get("template_id"),
            doc.get("title"),
            doc.get("summary"),
        )
    ).lower()
    if "출장보고" in raw or "trip_report" in raw or str(payload.get("source_document_id") or "").strip():
        return "report"
    if "업무일지" in raw or "diary" in raw or "daily" in raw:
        return "diary"
    return ""


def _sync_business_trip_artifact_for_document(
    db: dict[str, Any],
    tenant_id: str,
    doc: dict[str, Any],
    *,
    actor_id: str,
    audit_action: str,
    complete_report: bool = False,
) -> dict[str, Any] | None:
    """Link diary/report documents to an existing lifecycle and gate completion."""
    artifact_kind = _trip_artifact_kind_from_document(doc)
    if not artifact_kind:
        return None
    payload = doc.get("content_json") if isinstance(doc.get("content_json"), dict) else {}
    trip_id = str(payload.get("trip_id") or "").strip()
    trip = _business_trip_by_id(db, trip_id)
    if not trip:
        raise LookupError("연계 출장 lifecycle을 찾을 수 없습니다.")
    if str(trip.get("tenant_id") or "").strip() != str(tenant_id or "").strip():
        raise PermissionError("다른 테넌트의 출장 lifecycle에는 연결할 수 없습니다.")

    from core.workflow.business_trip import transition_trip_status

    before = deepcopy(trip)
    if artifact_kind == "diary":
        trip["diary_document_id"] = str(doc.get("id") or "")
    elif artifact_kind == "report":
        trip["report_document_id"] = str(doc.get("id") or "")
        if complete_report:
            if trip.get("status") == TRIP_STATUS_APPROVED:
                trip.update(transition_trip_status(trip, TRIP_STATUS_IN_PROGRESS))
            if trip.get("status") == TRIP_STATUS_IN_PROGRESS:
                trip.update(transition_trip_status(trip, TRIP_STATUS_DIARY_DUE))
            if trip.get("status") in (TRIP_STATUS_DIARY_DUE, TRIP_STATUS_OVERDUE):
                trip.update(transition_trip_status(trip, TRIP_STATUS_COMPLETED))
    trip["updated_at"] = _now_iso()
    if trip == before:
        return trip
    append_audit(
        db,
        actor_id=actor_id,
        action=audit_action,
        entity_type="BusinessTripLifecycle",
        entity_id=str(trip.get("trip_id") or trip_id),
        before=before,
        after=trip,
    )
    return trip


def _sync_business_trip_lifecycle_for_document(
    db: dict[str, Any],
    tenant_id: str,
    doc: dict[str, Any],
    *,
    target_status: str,
    actor_id: str,
    audit_action: str,
) -> dict[str, Any] | None:
    """Create/update one lifecycle row for a business-trip workflow document.

    The lifecycle status intentionally remains separate from document status and
    KPI reflection status; only the business-trip row is transitioned here.
    """
    if not _is_business_trip_document(doc):
        return None

    from core.workflow.business_trip import (
        default_business_trip_record,
        find_business_trip_by_source,
        migrate_business_trip_record,
        transition_trip_status,
    )

    source = _business_trip_source_for_document(doc)
    rows = db.setdefault("business_trips", [])
    payload_trip_id = ""
    content_json = doc.get("content_json")
    if isinstance(content_json, dict):
        payload_trip_id = str(content_json.get("trip_id") or "").strip()
    existing = find_business_trip_by_source(db, source=source)
    if existing is None and payload_trip_id:
        existing = next((row for row in rows if row.get("trip_id") == payload_trip_id or row.get("id") == payload_trip_id), None)

    if existing is None:
        record = default_business_trip_record(
            tenant_id,
            **_business_trip_fields_from_document(tenant_id, doc, status=target_status or TRIP_STATUS_DRAFT),
        )
        rows.append(record)
        _link_document_to_trip(doc, record)
        append_audit(
            db,
            actor_id=actor_id,
            action=audit_action,
            entity_type="BusinessTripLifecycle",
            entity_id=record["trip_id"],
            after=record,
        )
        return record

    before = deepcopy(existing)
    updated = migrate_business_trip_record(
        tenant_id,
        {
            **existing,
            **_business_trip_fields_from_document(
                tenant_id,
                doc,
                status=existing.get("status") or TRIP_STATUS_DRAFT,
                trip_id=str(existing.get("trip_id") or existing.get("id") or ""),
            ),
        },
    )
    if target_status and target_status != updated.get("status"):
        updated = transition_trip_status(updated, target_status)
    existing.clear()
    existing.update(updated)
    _link_document_to_trip(doc, updated)
    append_audit(
        db,
        actor_id=actor_id,
        action=audit_action,
        entity_type="BusinessTripLifecycle",
        entity_id=updated["trip_id"],
        before=before,
        after=updated,
    )
    return updated


def _complete_business_trip_lifecycle_for_task(
    db: dict[str, Any],
    tenant_id: str,
    doc: dict[str, Any],
    task: dict[str, Any],
    *,
    actor_id: str,
) -> None:
    if not _is_business_trip_document(doc):
        return
    trip_id = str(task.get("trip_id") or "").strip()
    if not trip_id and isinstance(doc.get("content_json"), dict):
        trip_id = str(doc["content_json"].get("trip_id") or "").strip()
    if not trip_id:
        trip = _sync_business_trip_lifecycle_for_document(
            db,
            tenant_id,
            doc,
            target_status=TRIP_STATUS_APPROVED,
            actor_id=actor_id,
            audit_action="business_trip_lifecycle_relinked_from_task",
        )
        trip_id = str((trip or {}).get("trip_id") or "")
    if not trip_id:
        return

    from core.workflow.business_trip import transition_trip_status

    for row in db.get("business_trips") or []:
        if row.get("trip_id") != trip_id and row.get("id") != trip_id:
            continue
        before = deepcopy(row)
        updated = row
        if row.get("status") == TRIP_STATUS_APPROVED:
            updated = transition_trip_status(updated, TRIP_STATUS_IN_PROGRESS)
        if updated.get("status") == TRIP_STATUS_IN_PROGRESS:
            updated = transition_trip_status(updated, TRIP_STATUS_DIARY_DUE)
        if updated == before:
            return
        row.clear()
        row.update(updated)
        append_audit(
            db,
            actor_id=actor_id,
            action="business_trip_lifecycle_diary_due_from_task",
            entity_type="BusinessTripLifecycle",
            entity_id=str(row.get("trip_id") or trip_id),
            before=before,
            after=row,
        )
        return


def _business_trip_by_id(db: dict[str, Any], trip_id: str) -> dict[str, Any] | None:
    trip_id = str(trip_id or "").strip()
    if not trip_id:
        return None
    return next(
        (
            row
            for row in db.get("business_trips") or []
            if row.get("trip_id") == trip_id or row.get("id") == trip_id
        ),
        None,
    )


def _today_str(value: str | date | None = None) -> str:
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or "").strip()[:10]
    return text or date.today().isoformat()


def _add_notification_once(
    db: dict[str, Any],
    *,
    user_id: str,
    ntype: str,
    title: str,
    message: str,
    related_document_id: str = "",
    related_task_id: str = "",
) -> bool:
    user_id = str(user_id or "").strip()
    if not user_id:
        return False
    for note in db.get("notifications") or []:
        if (
            note.get("user_id") == user_id
            and note.get("type") == ntype
            and note.get("related_document_id") == related_document_id
            and note.get("related_task_id") == related_task_id
            and note.get("title") == title
        ):
            return False
    add_notification(
        db,
        user_id=user_id,
        ntype=ntype,
        title=title,
        message=message,
        related_document_id=related_document_id,
        related_task_id=related_task_id,
    )
    return True


def _business_trip_escalation_user_ids(db: dict[str, Any], trip: dict[str, Any], task: dict[str, Any]) -> list[str]:
    """Return direct owners plus manager/escalation roles for overdue trips."""
    ordered: list[str] = []

    def add(uid: Any) -> None:
        text = str(uid or "").strip()
        if text and text not in ordered:
            ordered.append(text)

    requester_id = str(trip.get("requester_id") or "")
    executor_id = str(task.get("executor_id") or trip.get("executor_id") or "")
    add(requester_id)
    add(executor_id)

    profiles = [p for p in db.get("user_profiles") or [] if isinstance(p, dict)]
    by_uid = {str(p.get("user_id") or ""): p for p in profiles}
    for uid in (requester_id, executor_id):
        add((by_uid.get(uid) or {}).get("manager_user_id"))

    site_id = str(trip.get("site_id") or task.get("site_id") or "")
    dept_id = str(trip.get("department_id") or task.get("department_id") or "")
    for profile in profiles:
        roles = {str(v) for v in profile.get("workflow_roles") or []}
        profile_site_ids = {str(v) for v in profile.get("site_ids") or []}
        profile_department_ids = {str(v) for v in profile.get("department_ids") or profile.get("org_unit_ids") or []}
        if site_id and site_id in profile_site_ids and (
            WF_ROLE_SITE_MANAGER in roles or WF_ROLE_HR in roles
        ):
            add(profile.get("user_id"))
        if dept_id and dept_id in profile_department_ids and (
            WF_ROLE_DEPT_MANAGER in roles or WF_ROLE_SITE_MANAGER in roles or WF_ROLE_HR in roles
        ):
            add(profile.get("user_id"))
    return ordered


def _overdue_trip_update(row: dict[str, Any]) -> dict[str, Any]:
    """Move an active trip into overdue through legal state-machine hops."""
    from core.workflow.business_trip import transition_trip_status

    status = row.get("status")
    updated = row
    if status == TRIP_STATUS_APPROVED:
        updated = transition_trip_status(updated, TRIP_STATUS_IN_PROGRESS)
        status = updated.get("status")
    if status in (TRIP_STATUS_IN_PROGRESS, TRIP_STATUS_DIARY_DUE):
        updated = transition_trip_status(updated, TRIP_STATUS_OVERDUE)
    return updated


def _attach_steps(db: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    doc_id = doc.get("id")
    steps = sorted(
        [s for s in db.get("approval_steps") or [] if s.get("document_id") == doc_id],
        key=lambda s: int(s.get("step_order") or 0),
    )
    out = dict(doc)
    out["approval_steps"] = steps
    return out


def list_documents(
    tenant_id: str,
    *,
    session: UserSession | None = None,
    status: str | None = None,
    document_type: str | None = None,
    site_id: str | None = None,
    inbox: str | None = None,
) -> list[dict[str, Any]]:
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()
    db = _load_raw(tenant_id)
    docs = [_attach_steps(db, d) for d in db.get("documents") or []]
    visible = [d for d in docs if wf_perm.can_view_document(sess, d, tenant_id=tenant_id)]
    if status:
        visible = [d for d in visible if d.get("status") == status]
    if document_type:
        visible = [d for d in visible if d.get("document_type") == document_type]
    if site_id:
        visible = [d for d in visible if d.get("site_id") == site_id]
    if inbox:
        visible = filter_inbox(visible, inbox, session=sess, tenant_id=tenant_id)
    return sorted(visible, key=lambda d: d.get("updated_at") or "", reverse=True)


def inbox_counts(tenant_id: str, *, session: UserSession | None = None) -> dict[str, int]:
    """결재함별 건수 (홈·사이드바 뱃지용)."""
    sess = session or require_session()
    docs = list_documents(tenant_id, session=sess, inbox="all")
    return count_by_inbox(docs, session=sess, tenant_id=tenant_id)


def get_document(tenant_id: str, document_id: str, *, session: UserSession | None = None) -> dict[str, Any]:
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()
    db = _load_raw(tenant_id)
    for d in db.get("documents") or []:
        if d.get("id") == document_id:
            doc = _attach_steps(db, d)
            if not wf_perm.can_view_document(sess, doc, tenant_id=tenant_id):
                raise PermissionError("문서를 조회할 권한이 없습니다.")
            doc["comments"] = [c for c in db.get("comments") or [] if c.get("document_id") == document_id]
            doc["execution_tasks"] = [
                t for t in db.get("execution_tasks") or [] if t.get("document_id") == document_id
            ]
            doc["payload"] = _load_payload(db, doc)
            return doc
    raise LookupError("문서를 찾을 수 없습니다.")


def _load_payload(db: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    doc_id = doc.get("id")
    dtype = doc.get("document_type")
    if dtype == DOC_TYPE_ATTENDANCE:
        for r in db.get("attendance_requests") or []:
            if r.get("document_id") == doc_id:
                return r
    if dtype == DOC_TYPE_PURCHASE:
        items = [i for i in db.get("purchase_request_items") or [] if i.get("document_id") == doc_id]
        for r in db.get("purchase_requests") or []:
            if r.get("document_id") == doc_id:
                return {**r, "items": items}
    if dtype == DOC_TYPE_EXPENSE:
        for r in db.get("expense_reports") or []:
            if r.get("document_id") == doc_id:
                return r
    return doc.get("content_json") or {}


def create_document(
    tenant_id: str,
    *,
    document_type: str,
    title: str,
    summary: str = "",
    content: str = "",
    site_id: str = "",
    department_id: str = "",
    total_amount: int = 0,
    category: str = "",
    due_date: str = "",
    period_start: str = "",
    period_end: str = "",
    cc_user_ids: list[str] | None = None,
    payload: dict[str, Any] | None = None,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or require_session()
    origin_tid = sess.tenant_id
    wf_tid = _resolve_tenant(tenant_id or origin_tid)
    from core.group_store import get_group_for_tenant
    from core.workflow.config_store import get_entity_for_tenant

    grp = get_group_for_tenant(origin_tid)
    entity_id = ""
    if grp:
        ent = get_entity_for_tenant(grp.group_id, origin_tid)
        if ent:
            entity_id = str(ent.get("entity_id") or "")

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        doc_id = _new_id()
        doc = {
            "id": doc_id,
            "document_no": next_document_no(db),
            "document_type": document_type,
            "title": title.strip(),
            "summary": summary.strip(),
            "content": content.strip(),
            "status": DOC_STATUS_DRAFT,
            "site_id": site_id,
            "department_id": department_id,
            "requester_id": _uid(sess),
            "origin_tenant_id": origin_tid,
            "legal_entity_id": entity_id,
            "total_amount": int(total_amount or 0),
            "currency": "KRW",
            "category": category,
            "requested_date": date.today().isoformat(),
            "due_date": due_date,
            "period_start": period_start or due_date or date.today().isoformat(),
            "period_end": period_end or due_date or period_start or date.today().isoformat(),
            "approved_at": "",
            "rejected_at": "",
            "completed_at": "",
            "closed_at": "",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "content_json": payload or {},
            "cc_user_ids": list(cc_user_ids or []),
        }
        db.setdefault("documents", []).append(doc)
        _save_typed_payload(db, doc, payload or {})
        append_audit(
            db,
            actor_id=_uid(sess),
            action="document_created",
            entity_type="WorkflowDocument",
            entity_id=doc_id,
            after=doc,
        )
        _sync_business_trip_lifecycle_for_document(
            db,
            wf_tid,
            doc,
            target_status=TRIP_STATUS_DRAFT,
            actor_id=_uid(sess),
            audit_action="business_trip_lifecycle_created_from_document",
        )
        _sync_business_trip_artifact_for_document(
            db,
            wf_tid,
            doc,
            actor_id=_uid(sess),
            audit_action="business_trip_artifact_linked_from_document",
        )
        return doc

    doc = with_db(wf_tid)(mut)
    return get_document(wf_tid, doc["id"], session=sess)


def update_document(
    tenant_id: str,
    document_id: str,
    *,
    fields: dict[str, Any],
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or require_session()

    def mut(db: dict[str, Any]) -> None:
        for d in db.get("documents") or []:
            if d.get("id") != document_id:
                continue
            if not wf_perm.can_edit_document(sess, _attach_steps(db, d), tenant_id=tenant_id):
                raise PermissionError("문서를 수정할 권한이 없습니다.")
            before = deepcopy(d)
            for k, v in fields.items():
                if k in (
                    "title",
                    "summary",
                    "content",
                    "site_id",
                    "department_id",
                    "total_amount",
                    "category",
                    "due_date",
                    "period_start",
                    "period_end",
                    "cc_user_ids",
                ):
                    d[k] = v
            if "payload" in fields:
                d["content_json"] = fields["payload"]
                _save_typed_payload(db, d, fields["payload"])
            d["updated_at"] = _now_iso()
            append_audit(
                db,
                actor_id=_uid(sess),
                action="document_updated",
                entity_type="WorkflowDocument",
                entity_id=document_id,
                before=before,
                after=d,
            )
            _sync_business_trip_lifecycle_for_document(
                db,
                tenant_id,
                d,
                target_status="",
                actor_id=_uid(sess),
                audit_action="business_trip_lifecycle_updated_from_document",
            )
            _sync_business_trip_artifact_for_document(
                db,
                tenant_id,
                d,
                actor_id=_uid(sess),
                audit_action="business_trip_artifact_linked_from_update",
            )
            return
        raise LookupError("문서를 찾을 수 없습니다.")

    with_db(tenant_id)(mut)
    return get_document(tenant_id, document_id, session=sess)


def _save_typed_payload(db: dict[str, Any], doc: dict[str, Any], payload: dict[str, Any]) -> None:
    doc_id = doc.get("id")
    dtype = doc.get("document_type")
    payload = dict(payload or {})
    payload["document_id"] = doc_id
    if dtype == DOC_TYPE_ATTENDANCE:
        rows = db.setdefault("attendance_requests", [])
        rows[:] = [r for r in rows if r.get("document_id") != doc_id]
        rows.append({**payload, "id": payload.get("id") or _new_id()})
    elif dtype == DOC_TYPE_PURCHASE:
        prs = db.setdefault("purchase_requests", [])
        prs[:] = [r for r in prs if r.get("document_id") != doc_id]
        prs.append({**payload, "id": payload.get("id") or _new_id()})
        items = payload.pop("items", []) if "items" in payload else payload.get("items", [])
        db["purchase_request_items"] = [
            i for i in db.get("purchase_request_items") or [] if i.get("document_id") != doc_id
        ]
        total = 0
        for it in items or []:
            qty = int(it.get("quantity") or 0)
            price = int(it.get("unit_price") or 0)
            line = qty * price
            total += line
            db["purchase_request_items"].append(
                {
                    "id": _new_id(),
                    "document_id": doc_id,
                    "item_name": it.get("item_name", ""),
                    "quantity": qty,
                    "unit_price": price,
                    "total_amount": line,
                }
            )
        doc["total_amount"] = total
    elif dtype == DOC_TYPE_EXPENSE:
        ers = db.setdefault("expense_reports", [])
        ers[:] = [r for r in ers if r.get("document_id") != doc_id]
        ers.append({**payload, "id": payload.get("id") or _new_id()})
        doc["total_amount"] = int(payload.get("total_amount") or payload.get("amount") or 0)


def submit_document(
    tenant_id: str,
    document_id: str,
    approval_line: list[dict[str, Any]],
    *,
    session: UserSession | None = None,
    cc_user_ids: list[str] | None = None,
) -> dict[str, Any]:
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()
    if not approval_line:
        raise ValueError("결재라인이 필요합니다.")
    for i, step in enumerate(approval_line, start=1):
        if not str(step.get("approver_id") or "").strip():
            raise ValueError(f"결재 {i}단계 결재자를 지정하세요.")

    def mut(db: dict[str, Any]) -> None:
        doc = None
        for d in db.get("documents") or []:
            if d.get("id") == document_id:
                doc = d
                break
        if not doc:
            raise LookupError("문서를 찾을 수 없습니다.")
        if not wf_perm.can_submit_document(sess, _attach_steps(db, doc), tenant_id=tenant_id):
            raise PermissionError("상신할 수 없습니다.")
        db["approval_steps"] = [s for s in db.get("approval_steps") or [] if s.get("document_id") != document_id]
        for i, step in enumerate(approval_line, start=1):
            db["approval_steps"].append(
                {
                    "id": _new_id(),
                    "document_id": document_id,
                    "step_order": i,
                    "approver_id": step.get("approver_id", ""),
                    "approver_role": step.get("approver_role", ""),
                    "approver_tenant_id": step.get("approver_tenant_id", tenant_id),
                    "status": STEP_PENDING if i == 1 else STEP_PENDING,
                    "approved_at": "",
                    "rejected_at": "",
                    "comment": "",
                }
            )
        doc["status"] = DOC_STATUS_IN_REVIEW
        doc["updated_at"] = _now_iso()
        if cc_user_ids is not None:
            doc["cc_user_ids"] = list(cc_user_ids)
        first = approval_line[0]
        add_notification(
            db,
            user_id=first.get("approver_id", ""),
            ntype="approval_requested",
            title=f"결재 요청: {doc.get('title', '')}",
            message=doc.get("summary", ""),
            related_document_id=document_id,
        )
        append_audit(db, actor_id=_uid(sess), action="document_submitted", entity_type="WorkflowDocument", entity_id=document_id)
        _sync_business_trip_lifecycle_for_document(
            db,
            tenant_id,
            doc,
            target_status=TRIP_STATUS_PLANNED,
            actor_id=_uid(sess),
            audit_action="business_trip_lifecycle_planned_from_submit",
        )
        _sync_business_trip_artifact_for_document(
            db,
            tenant_id,
            doc,
            actor_id=_uid(sess),
            audit_action="business_trip_artifact_linked_from_submit",
        )

    with_db(tenant_id)(mut)
    doc = get_document(tenant_id, document_id, session=sess)
    from core.workflow.follow_up import sync_submission_follow_up

    try:
        sync_submission_follow_up(
            doc,
            approval_line,
            session=sess,
            cc_user_ids=doc.get("cc_user_ids") or [],
        )
    except Exception:
        pass
    return doc


def approve_document(
    tenant_id: str,
    document_id: str,
    *,
    comment: str = "",
    session: UserSession | None = None,
) -> dict[str, Any]:
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()

    def mut(db: dict[str, Any]) -> None:
        doc = next((d for d in db.get("documents") or [] if d.get("id") == document_id), None)
        if not doc:
            raise LookupError("문서를 찾을 수 없습니다.")
        attached = _attach_steps(db, doc)
        if not wf_perm.can_approve_document(sess, attached, tenant_id=tenant_id):
            raise PermissionError("결재할 권한이 없습니다.")
        steps = attached["approval_steps"]
        current = next((s for s in steps if s.get("status") == STEP_PENDING), None)
        if not current:
            raise ValueError("대기 중인 결재 단계가 없습니다.")
        current["status"] = STEP_APPROVED
        current["approved_at"] = _now_iso()
        current["comment"] = comment
        pending = [s for s in steps if s.get("status") == STEP_PENDING and s.get("id") != current.get("id")]
        if pending:
            doc["status"] = DOC_STATUS_IN_REVIEW
            nxt = pending[0]
            add_notification(
                db,
                user_id=nxt.get("approver_id", ""),
                ntype="approval_requested",
                title=f"결재 요청: {doc.get('title', '')}",
                message="",
                related_document_id=document_id,
            )
        else:
            doc["status"] = DOC_STATUS_APPROVED
            doc["approved_at"] = _now_iso()
            trip = _sync_business_trip_lifecycle_for_document(
                db,
                tenant_id,
                doc,
                target_status=TRIP_STATUS_APPROVED,
                actor_id=_uid(sess),
                audit_action="business_trip_lifecycle_approved_from_document",
            )
            executor_id = _spawn_execution_tasks(
                db,
                doc,
                actor_id=_uid(sess),
                trip_id=str((trip or {}).get("trip_id") or ""),
            )
            from core.workflow.follow_up import sync_approval_complete_follow_up

            try:
                sync_approval_complete_follow_up(doc, session=sess, executor_id=executor_id or "")
            except Exception:
                pass
            _sync_business_trip_artifact_for_document(
                db,
                tenant_id,
                doc,
                actor_id=_uid(sess),
                audit_action="business_trip_artifact_completed_from_approval",
                complete_report=True,
            )
        doc["updated_at"] = _now_iso()
        append_audit(db, actor_id=_uid(sess), action="document_approved", entity_type="WorkflowDocument", entity_id=document_id)

    with_db(tenant_id)(mut)
    return get_document(tenant_id, document_id, session=sess)


def reject_document(
    tenant_id: str,
    document_id: str,
    *,
    comment: str = "",
    session: UserSession | None = None,
) -> dict[str, Any]:
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()

    def mut(db: dict[str, Any]) -> None:
        doc = next((d for d in db.get("documents") or [] if d.get("id") == document_id), None)
        if not doc:
            raise LookupError("문서를 찾을 수 없습니다.")
        if not wf_perm.can_approve_document(sess, _attach_steps(db, doc), tenant_id=tenant_id):
            raise PermissionError("반려할 권한이 없습니다.")
        for s in db.get("approval_steps") or []:
            if s.get("document_id") == document_id and s.get("status") == STEP_PENDING:
                s["status"] = STEP_REJECTED
                s["rejected_at"] = _now_iso()
                s["comment"] = comment
        doc["status"] = DOC_STATUS_REJECTED
        doc["rejected_at"] = _now_iso()
        doc["updated_at"] = _now_iso()
        add_notification(
            db,
            user_id=doc.get("requester_id", ""),
            ntype="rejected",
            title=f"반려: {doc.get('title', '')}",
            message=comment,
            related_document_id=document_id,
        )
        append_audit(db, actor_id=_uid(sess), action="document_rejected", entity_type="WorkflowDocument", entity_id=document_id)
        _sync_business_trip_lifecycle_for_document(
            db,
            tenant_id,
            doc,
            target_status=TRIP_STATUS_CANCELLED,
            actor_id=_uid(sess),
            audit_action="business_trip_lifecycle_cancelled_from_reject",
        )

    with_db(tenant_id)(mut)
    return get_document(tenant_id, document_id, session=sess)


def cancel_document(
    tenant_id: str,
    document_id: str,
    *,
    comment: str = "",
    session: UserSession | None = None,
) -> dict[str, Any]:
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()

    def mut(db: dict[str, Any]) -> None:
        doc = next((d for d in db.get("documents") or [] if d.get("id") == document_id), None)
        if not doc:
            raise LookupError("문서를 찾을 수 없습니다.")
        if not wf_perm.can_edit_document(sess, _attach_steps(db, doc), tenant_id=tenant_id):
            raise PermissionError("문서를 취소할 권한이 없습니다.")
        before = deepcopy(doc)
        doc["status"] = DOC_STATUS_CANCELLED
        doc["closed_at"] = _now_iso()
        doc["updated_at"] = _now_iso()
        if comment:
            db.setdefault("comments", []).append(
                {
                    "id": _new_id(),
                    "document_id": document_id,
                    "author_id": _uid(sess),
                    "comment": comment,
                    "created_at": _now_iso(),
                }
            )
        append_audit(
            db,
            actor_id=_uid(sess),
            action="document_cancelled",
            entity_type="WorkflowDocument",
            entity_id=document_id,
            before=before,
            after=doc,
        )
        _sync_business_trip_lifecycle_for_document(
            db,
            tenant_id,
            doc,
            target_status=TRIP_STATUS_CANCELLED,
            actor_id=_uid(sess),
            audit_action="business_trip_lifecycle_cancelled_from_document",
        )

    with_db(tenant_id)(mut)
    return get_document(tenant_id, document_id, session=sess)


def request_changes(
    tenant_id: str,
    document_id: str,
    *,
    comment: str = "",
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or require_session()

    def mut(db: dict[str, Any]) -> None:
        doc = next((d for d in db.get("documents") or [] if d.get("id") == document_id), None)
        if not doc:
            raise LookupError("문서를 찾을 수 없습니다.")
        if not wf_perm.can_approve_document(sess, _attach_steps(db, doc), tenant_id=tenant_id):
            raise PermissionError("보완 요청 권한이 없습니다.")
        for s in db.get("approval_steps") or []:
            if s.get("document_id") == document_id and s.get("status") == STEP_PENDING:
                s["status"] = STEP_REQUESTED_CHANGES
                s["comment"] = comment
        doc["status"] = DOC_STATUS_REQUESTED_CHANGES
        doc["updated_at"] = _now_iso()
        add_notification(
            db,
            user_id=doc.get("requester_id", ""),
            ntype="change_requested",
            title=f"보완 요청: {doc.get('title', '')}",
            message=comment,
            related_document_id=document_id,
        )
        append_audit(db, actor_id=_uid(sess), action="document_change_requested", entity_type="WorkflowDocument", entity_id=document_id)

    with_db(tenant_id)(mut)
    return get_document(tenant_id, document_id, session=sess)


def _spawn_execution_tasks(db: dict[str, Any], doc: dict[str, Any], *, actor_id: str, trip_id: str = "") -> str:
    """승인 후 기본 실행업무 생성. executor_id 반환."""
    doc_id = doc.get("id")
    dtype = doc.get("document_type")
    executor_id = doc.get("content_json", {}).get("recommended_executor_id", "")
    if not executor_id:
        profiles = db.get("user_profiles") or []
        for p in profiles:
            roles = p.get("workflow_roles") or []
            if dtype == DOC_TYPE_PURCHASE and "purchasing" in roles:
                executor_id = p.get("user_id", "")
                break
        if not executor_id and profiles:
            executor_id = profiles[0].get("user_id", "")
    task = {
        "id": _new_id(),
        "document_id": doc_id,
        "trip_id": trip_id,
        "title": f"실행: {doc.get('title', '')}",
        "description": doc.get("summary", ""),
        "executor_id": executor_id or doc.get("requester_id", ""),
        "site_id": doc.get("site_id", ""),
        "department_id": doc.get("department_id", ""),
        "due_date": doc.get("due_date") or doc.get("period_end") or doc.get("period_start") or "",
        "priority": "normal",
        "status": TASK_PENDING,
        "ai_recommended_action": "",
        "completed_at": "",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    db.setdefault("execution_tasks", []).append(task)
    add_notification(
        db,
        user_id=task["executor_id"],
        ntype="execution_task_assigned",
        title=task["title"],
        message=task["description"],
        related_document_id=doc_id,
        related_task_id=task["id"],
    )
    append_audit(db, actor_id=actor_id, action="execution_task_created", entity_type="ExecutionTask", entity_id=task["id"])
    return str(task.get("executor_id") or "")


def list_execution_tasks(
    tenant_id: str,
    *,
    session: UserSession | None = None,
    mine_only: bool = False,
    status: str | None = None,
) -> list[dict[str, Any]]:
    sess = session or require_session()
    db = _load_raw(tenant_id)
    tasks = list(db.get("execution_tasks") or [])
    profile = get_user_profile(tenant_id, _uid(sess))
    roles = wf_perm._workflow_roles(sess, profile)  # noqa: SLF001
    if mine_only or not (WF_ROLE_ADMIN in roles or WF_ROLE_EXECUTIVE in roles or WF_ROLE_FINANCE in roles):
        tasks = [t for t in tasks if t.get("executor_id") == _uid(sess)]
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    return sorted(tasks, key=lambda t: t.get("due_date") or "", reverse=False)


def complete_execution_task(
    tenant_id: str,
    task_id: str,
    *,
    session: UserSession | None = None,
) -> dict[str, Any]:
    sess = session or require_session()
    tenant_id = _resolve_tenant(tenant_id)
    if _resolve_tenant(sess.tenant_id) != tenant_id:
        raise PermissionError("실행업무를 완료할 권한이 없습니다.")

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        for t in db.get("execution_tasks") or []:
            if t.get("id") != task_id:
                continue
            if not wf_perm.can_manage_execution_task(sess, t, tenant_id=tenant_id):
                raise PermissionError("실행업무를 완료할 권한이 없습니다.")
            if t.get("status") == TASK_COMPLETED:
                return t
            t["status"] = TASK_COMPLETED
            t["completed_at"] = _now_iso()
            t["updated_at"] = _now_iso()
            doc_id = t.get("document_id", "")
            for d in db.get("documents") or []:
                if d.get("id") == doc_id:
                    d["status"] = DOC_STATUS_COMPLETED
                    d["completed_at"] = _now_iso()
                    d["updated_at"] = _now_iso()
                    _complete_business_trip_lifecycle_for_task(db, tenant_id, d, t, actor_id=_uid(sess))
            append_audit(db, actor_id=_uid(sess), action="execution_task_completed", entity_type="ExecutionTask", entity_id=task_id)
            return t
        raise LookupError("실행업무를 찾을 수 없습니다.")

    return with_db(tenant_id)(mut)


def site_summary(tenant_id: str, month: str, *, session: UserSession | None = None) -> dict[str, Any]:
    sess = session or require_session()
    db = _load_raw(tenant_id)
    docs = db.get("documents") or []
    tasks = db.get("execution_tasks") or []
    sites = [s for s in db.get("sites") or [] if wf_perm.can_view_site_report(sess, s.get("id", ""), tenant_id=tenant_id)]
    result_sites = []
    for site in sites:
        sid = site.get("id", "")
        site_docs = [d for d in docs if d.get("site_id") == sid]
        purchase = sum(
            int(d.get("total_amount") or 0)
            for d in site_docs
            if d.get("document_type") == DOC_TYPE_PURCHASE and d.get("status") == DOC_STATUS_APPROVED
        )
        expense = sum(
            int(d.get("total_amount") or 0)
            for d in site_docs
            if d.get("document_type") == DOC_TYPE_EXPENSE and d.get("status") == DOC_STATUS_APPROVED
        )
        result_sites.append(
            {
                "site_id": sid,
                "site_name": site.get("name", ""),
                "pending_approvals": len(
                    [d for d in site_docs if d.get("status") in (DOC_STATUS_SUBMITTED, DOC_STATUS_IN_REVIEW)]
                ),
                "approved_count": len([d for d in site_docs if d.get("status") == DOC_STATUS_APPROVED]),
                "rejected_count": len([d for d in site_docs if d.get("status") == DOC_STATUS_REJECTED]),
                "purchase_amount": purchase,
                "expense_amount": expense,
                "delayed_tasks": len(
                    [
                        t
                        for t in tasks
                        if t.get("site_id") == sid and t.get("status") in (TASK_PENDING, "in_progress")
                        and (t.get("due_date") or "") < date.today().isoformat()
                    ]
                ),
            }
        )
    return {"month": month, "sites": result_sites}


def executive_summary(tenant_id: str, month: str, *, session: UserSession | None = None) -> dict[str, Any]:
    site = site_summary(tenant_id, month, session=session)
    total_expense = sum(s.get("expense_amount", 0) for s in site.get("sites", []))
    total_purchase = sum(s.get("purchase_amount", 0) for s in site.get("sites", []))
    pending = sum(s.get("pending_approvals", 0) for s in site.get("sites", []))
    delayed = sum(s.get("delayed_tasks", 0) for s in site.get("sites", []))
    return {
        "month": month,
        "sites": site.get("sites", []),
        "total_expense": total_expense,
        "total_purchase": total_purchase,
        "monthly_change": 0,
        "pending_approvals": pending,
        "delayed_tasks": delayed,
        "profit_and_loss": {},
        "ai_summary": "",
        "risks": [],
    }


def ensure_tenant_seeded(tenant_id: str) -> bool:
    from core.workflow.seed import seed_tenant_if_empty

    return seed_tenant_if_empty(tenant_id)


def list_business_trips(
    tenant_id: str,
    *,
    session: UserSession | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """List tenant-bound business-trip lifecycle view models."""
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()
    db = _load_raw(tenant_id)
    from core.workflow.business_trip import business_trip_view_model, normalize_trip_status

    rows = [
        business_trip_view_model(row)
        for row in db.get("business_trips") or []
        if wf_perm.can_view_business_trip_lifecycle(sess, row, tenant_id=tenant_id)
    ]
    if status:
        expected = normalize_trip_status(status)
        rows = [row for row in rows if row.get("status") == expected]
    return sorted(rows, key=lambda row: row.get("updated_at") or "", reverse=True)


def get_business_trip(
    tenant_id: str, trip_id: str, *, session: UserSession | None = None
) -> dict[str, Any]:
    """Return a single tenant-bound business-trip lifecycle view model."""
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()
    db = _load_raw(tenant_id)
    from core.workflow.business_trip import business_trip_view_model

    for row in db.get("business_trips") or []:
        if row.get("trip_id") == trip_id or row.get("id") == trip_id:
            if not wf_perm.can_view_business_trip_lifecycle(sess, row, tenant_id=tenant_id):
                raise PermissionError("출장 lifecycle을 조회할 권한이 없습니다.")
            return business_trip_view_model(row)
    raise LookupError("출장 lifecycle을 찾을 수 없습니다.")


def upsert_business_trip_lifecycle(
    tenant_id: str,
    *,
    fields: dict[str, Any],
    session: UserSession | None = None,
) -> dict[str, Any]:
    """Create/update the foundation lifecycle record idempotently by source/dedupe key."""
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        from core.workflow.business_trip import (
            default_business_trip_record,
            find_business_trip_by_source,
            migrate_business_trip_record,
        )

        payload = dict(fields or {})
        payload["tenant_id"] = tenant_id
        payload.setdefault("requester_id", _uid(sess))
        existing = find_business_trip_by_source(db, source=payload.get("source") or {})
        rows = db.setdefault("business_trips", [])
        if existing is None and payload.get("trip_id"):
            existing = next((row for row in rows if row.get("trip_id") == payload.get("trip_id")), None)
        if existing is None:
            record = default_business_trip_record(tenant_id, **payload)
            rows.append(record)
            append_audit(
                db,
                actor_id=_uid(sess),
                action="business_trip_lifecycle_created",
                entity_type="BusinessTripLifecycle",
                entity_id=record["trip_id"],
                after=record,
            )
            return record
        before = deepcopy(existing)
        updated = migrate_business_trip_record(tenant_id, {**existing, **payload})
        existing.clear()
        existing.update(updated)
        append_audit(
            db,
            actor_id=_uid(sess),
            action="business_trip_lifecycle_updated",
            entity_type="BusinessTripLifecycle",
            entity_id=updated["trip_id"],
            before=before,
            after=updated,
        )
        return updated

    record = with_db(tenant_id)(mut)
    return get_business_trip(tenant_id, record["trip_id"], session=sess)


def transition_business_trip_lifecycle(
    tenant_id: str,
    trip_id: str,
    status: str,
    *,
    session: UserSession | None = None,
) -> dict[str, Any]:
    """Advance a business-trip lifecycle through the frozen state machine."""
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()
    if _resolve_tenant(sess.tenant_id) != tenant_id:
        raise PermissionError("출장 lifecycle을 변경할 권한이 없습니다.")
    if not wf_perm.can_administer_business_trip_lifecycle(sess, tenant_id=tenant_id):
        raise PermissionError("출장 lifecycle을 변경할 권한이 없습니다.")

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        from core.workflow.business_trip import transition_trip_status

        for row in db.get("business_trips") or []:
            if row.get("trip_id") != trip_id and row.get("id") != trip_id:
                continue
            if status == TRIP_STATUS_COMPLETED and not str(row.get("report_document_id") or "").strip():
                raise ValueError("출장보고서 연결 후 완료 전이가 가능합니다.")
            before = deepcopy(row)
            updated = transition_trip_status(row, status)
            if updated == before:
                return updated
            row.clear()
            row.update(updated)
            append_audit(
                db,
                actor_id=_uid(sess),
                action="business_trip_lifecycle_status_changed",
                entity_type="BusinessTripLifecycle",
                entity_id=updated["trip_id"],
                before=before,
                after=updated,
            )
            return updated
        raise LookupError("출장 lifecycle을 찾을 수 없습니다.")

    record = with_db(tenant_id)(mut)
    return get_business_trip(tenant_id, record["trip_id"], session=sess)


def evaluate_business_trip_overdues(
    tenant_id: str,
    *,
    session: UserSession | None = None,
    today: str | date | None = None,
) -> dict[str, Any]:
    """Mark overdue business-trip execution tasks and escalate once per task/user."""
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()
    if _resolve_tenant(sess.tenant_id) != tenant_id:
        raise PermissionError("출장 지연 평가 권한이 없습니다.")
    if not wf_perm.can_run_business_trip_overdue_evaluator(sess, tenant_id=tenant_id):
        raise PermissionError("출장 지연 평가 권한이 없습니다.")
    as_of = _today_str(today)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        summary = {
            "as_of": as_of,
            "delayed_tasks": 0,
            "overdue_trips": 0,
            "escalations": 0,
            "task_ids": [],
            "trip_ids": [],
        }
        for task in db.get("execution_tasks") or []:
            due = str(task.get("due_date") or "").strip()[:10]
            if not due or due >= as_of:
                continue
            if task.get("status") in (TASK_COMPLETED, TASK_CANCELLED, TASK_DELAYED):
                continue
            trip = _business_trip_by_id(db, str(task.get("trip_id") or ""))
            if not trip:
                continue
            if not wf_perm.can_evaluate_business_trip_overdue(sess, trip, tenant_id=tenant_id):
                continue
            if trip.get("status") in (TRIP_STATUS_COMPLETED, TRIP_STATUS_CANCELLED):
                continue
            before_task = deepcopy(task)
            task["status"] = TASK_DELAYED
            task["delayed_at"] = _now_iso()
            task["updated_at"] = _now_iso()
            append_audit(
                db,
                actor_id=_uid(sess),
                action="execution_task_marked_delayed",
                entity_type="ExecutionTask",
                entity_id=str(task.get("id") or ""),
                before=before_task,
                after=task,
            )
            summary["delayed_tasks"] += 1
            summary["task_ids"].append(task.get("id") or "")

            before_trip = deepcopy(trip)
            updated_trip = _overdue_trip_update(trip)
            if updated_trip != before_trip:
                trip.clear()
                trip.update(updated_trip)
                append_audit(
                    db,
                    actor_id=_uid(sess),
                    action="business_trip_lifecycle_overdue_from_evaluator",
                    entity_type="BusinessTripLifecycle",
                    entity_id=str(trip.get("trip_id") or ""),
                    before=before_trip,
                    after=trip,
                )
                summary["overdue_trips"] += 1
                summary["trip_ids"].append(trip.get("trip_id") or "")

            from services import workspace_store as ws

            title = f"출장 지연 확인: {trip.get('title') or task.get('title') or ''}".strip()
            message = f"기한 {due}까지 완료되지 않은 출장 실행업무입니다."
            for uid in _business_trip_escalation_user_ids(db, trip, task):
                if _add_notification_once(
                    db,
                    user_id=uid,
                    ntype="business_trip_overdue_escalation",
                    title=title,
                    message=message,
                    related_document_id=str(task.get("document_id") or trip.get("approved_document_id") or ""),
                    related_task_id=str(task.get("id") or ""),
                ):
                    summary["escalations"] += 1
                ws.add_todo_for_user(
                    uid,
                    tenant_id,
                    title,
                    due_date=as_of,
                    source="business_trip_overdue",
                    document_id=str(task.get("document_id") or trip.get("approved_document_id") or ""),
                    extra={
                        "source_key": f"business_trip_overdue:{task.get('id')}:{uid}",
                        "trip_id": str(trip.get("trip_id") or ""),
                        "task_id": str(task.get("id") or ""),
                        "escalation": True,
                    },
                )
        return summary

    return with_db(tenant_id)(mut)


def list_business_trip_kpi_reflections(
    tenant_id: str,
    *,
    session: UserSession | None = None,
    kpi_reflection_status: str | None = None,
) -> list[dict[str, Any]]:
    """Query visible business trips through the KPI reflection state adapter."""
    rows = list_business_trips(tenant_id, session=session)
    if kpi_reflection_status:
        rows = [row for row in rows if row.get("kpi_reflection_status") == kpi_reflection_status]

    out: list[dict[str, Any]] = []
    for row in rows:
        kpi_status = row.get("kpi_reflection_status") or KPI_REFLECTION_BLOCKED
        blocking_reason = ""
        if kpi_status == KPI_REFLECTION_BLOCKED:
            blocking_reason = "출장 실행 완료 후 실적 반영 가능"
        elif kpi_status == KPI_REFLECTION_NOT_APPLICABLE:
            blocking_reason = "취소 또는 반려된 출장은 실적 반영 대상이 아님"
        out.append(
            {
                "trip_id": row.get("trip_id", ""),
                "title": row.get("title", ""),
                "status": row.get("status", ""),
                "kpi_reflection_status": kpi_status,
                "blocking_reason": blocking_reason,
                "ready": kpi_status == KPI_REFLECTION_READY,
                "reflected": kpi_status == KPI_REFLECTION_REFLECTED,
                "executor_id": row.get("executor_id", ""),
                "requester_id": row.get("requester_id", ""),
                "site_id": row.get("site_id", ""),
                "department_id": row.get("department_id", ""),
                "approved_document_id": row.get("approved_document_id", ""),
            }
        )
    return out


def reflect_business_trip_kpi(
    tenant_id: str,
    trip_id: str,
    *,
    session: UserSession | None = None,
) -> dict[str, Any]:
    """Reflect a READY business trip into KPI and mark it REFLECTED idempotently."""
    tenant_id = _resolve_tenant(tenant_id)
    sess = session or require_session()

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        from core.kpi import service as kpi_svc
        from core.workflow.business_trip import business_trip_view_model

        row = _business_trip_by_id(db, trip_id)
        if not row:
            raise LookupError("출장 lifecycle을 찾을 수 없습니다.")
        if not wf_perm.can_manage_business_trip_lifecycle(sess, row, tenant_id=tenant_id):
            raise PermissionError("출장 실적을 반영할 권한이 없습니다.")
        status = row.get("kpi_reflection_status") or KPI_REFLECTION_BLOCKED
        if status == KPI_REFLECTION_NOT_APPLICABLE:
            raise ValueError("취소 또는 반려된 출장은 실적 반영 대상이 아닙니다.")
        if status == KPI_REFLECTION_BLOCKED:
            raise ValueError("출장 실행 완료 후 실적 반영이 가능합니다.")
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        if source.get("kind") == TRIP_SOURCE_KIND_WORKFLOW and not str(row.get("report_document_id") or "").strip():
            raise ValueError("출장보고서 연결 후 실적 반영이 가능합니다.")
        kpi_record = kpi_svc.upsert_business_trip_reflection(tenant_id, row)
        if status != KPI_REFLECTION_REFLECTED:
            before = deepcopy(row)
            row["kpi_reflection_status"] = KPI_REFLECTION_REFLECTED
            row["kpi_reflected_at"] = _now_iso()
            row["updated_at"] = _now_iso()
            append_audit(
                db,
                actor_id=_uid(sess),
                action="business_trip_kpi_reflected",
                entity_type="BusinessTripLifecycle",
                entity_id=str(row.get("trip_id") or trip_id),
                before=before,
                after=row,
            )
        return {**business_trip_view_model(row), "kpi_record": kpi_record}

    return with_db(tenant_id)(mut)


def business_trip_manager_dashboard(
    tenant_id: str,
    *,
    session: UserSession | None = None,
) -> dict[str, Any]:
    """Return manager-scoped ongoing/completed/overdue business-trip view models."""
    rows = list_business_trips(tenant_id, session=session)
    ongoing_statuses = {TRIP_STATUS_PLANNED, TRIP_STATUS_APPROVED, TRIP_STATUS_IN_PROGRESS, TRIP_STATUS_DIARY_DUE}
    kpi_summary = {
        KPI_REFLECTION_BLOCKED: 0,
        KPI_REFLECTION_READY: 0,
        KPI_REFLECTION_REFLECTED: 0,
        KPI_REFLECTION_NOT_APPLICABLE: 0,
    }
    view_rows: list[dict[str, Any]] = []
    for row in rows:
        status = row.get("status", "")
        kpi_status = row.get("kpi_reflection_status") or KPI_REFLECTION_BLOCKED
        if kpi_status in kpi_summary:
            kpi_summary[kpi_status] += 1
        view_rows.append(
            {
                **row,
                "status_label": TRIP_STATUS_LABELS.get(status, status),
                "is_overdue": status == TRIP_STATUS_OVERDUE,
                "is_completed": status == TRIP_STATUS_COMPLETED,
                "kpi_ready": kpi_status == KPI_REFLECTION_READY,
            }
        )
    sections = {
        "ongoing": [row for row in view_rows if row.get("status") in ongoing_statuses],
        "completed": [row for row in view_rows if row.get("status") == TRIP_STATUS_COMPLETED],
        "overdue": [row for row in view_rows if row.get("status") == TRIP_STATUS_OVERDUE],
    }
    return {
        "trips": view_rows,
        "sections": sections,
        "counts": {
            "total": len(rows),
            "ongoing": len(sections["ongoing"]),
            "completed": len(sections["completed"]),
            "overdue": len(sections["overdue"]),
        },
        "kpi_summary": kpi_summary,
    }
