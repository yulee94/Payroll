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
    DOC_STATUS_COMPLETED,
    DOC_STATUS_DRAFT,
    DOC_STATUS_IN_REVIEW,
    DOC_STATUS_REJECTED,
    DOC_STATUS_REQUESTED_CHANGES,
    DOC_STATUS_SUBMITTED,
    DOC_TYPE_ATTENDANCE,
    DOC_TYPE_EXPENSE,
    DOC_TYPE_GENERAL,
    DOC_TYPE_PURCHASE,
    STEP_APPROVED,
    STEP_PENDING,
    STEP_REJECTED,
    STEP_REQUESTED_CHANGES,
    TASK_PENDING,
    WF_ROLE_ADMIN,
    WF_ROLE_EXECUTIVE,
    WF_ROLE_FINANCE,
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
            executor_id = _spawn_execution_tasks(db, doc, actor_id=_uid(sess))
            from core.workflow.follow_up import sync_approval_complete_follow_up

            try:
                sync_approval_complete_follow_up(doc, session=sess, executor_id=executor_id or "")
            except Exception:
                pass
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


def _spawn_execution_tasks(db: dict[str, Any], doc: dict[str, Any], *, actor_id: str) -> str:
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
        "title": f"실행: {doc.get('title', '')}",
        "description": doc.get("summary", ""),
        "executor_id": executor_id or doc.get("requester_id", ""),
        "site_id": doc.get("site_id", ""),
        "department_id": doc.get("department_id", ""),
        "due_date": doc.get("due_date", ""),
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

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        for t in db.get("execution_tasks") or []:
            if t.get("id") != task_id:
                continue
            if not wf_perm.can_manage_execution_task(sess, t, tenant_id=tenant_id):
                raise PermissionError("실행업무를 완료할 권한이 없습니다.")
            t["status"] = "completed"
            t["completed_at"] = _now_iso()
            t["updated_at"] = _now_iso()
            doc_id = t.get("document_id", "")
            for d in db.get("documents") or []:
                if d.get("id") == doc_id:
                    d["status"] = DOC_STATUS_COMPLETED
                    d["completed_at"] = _now_iso()
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
