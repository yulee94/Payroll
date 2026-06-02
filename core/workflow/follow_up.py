"""
core/workflow/follow_up.py - 기안 상신 시 캘린더·To-Do·실행업무 팔로우업
"""

from __future__ import annotations

from typing import Any

from core.session_service import UserSession
from core.workflow.constants import DOC_TYPE_LABELS
from services import workspace_store as ws


def sync_submission_follow_up(
    doc: dict[str, Any],
    approval_line: list[dict[str, Any]],
    *,
    session: UserSession,
    cc_user_ids: list[str] | None = None,
) -> None:
    """
    상신 시 관련자 캘린더·할 일 생성.
    - 기안자: 업무 기간 일정 + 결재 진행 To-Do
    - 결재자: 결재 To-Do (마감=period_end 또는 due_date)
    - 참조: 열람 To-Do
    """
    title = str(doc.get("title") or "문서")
    doc_no = str(doc.get("document_no") or "")
    doc_id = str(doc.get("id") or "")
    dtype = str(doc.get("document_type") or "")
    dtype_label = DOC_TYPE_LABELS.get(dtype, "문서")
    period_start = str(doc.get("period_start") or doc.get("requested_date") or "")
    period_end = str(doc.get("period_end") or doc.get("due_date") or period_start)
    due = period_end or period_start

    cal_title = f"[{dtype_label}] {title}"
    if period_start and period_end and period_start != period_end:
        cal_title = f"{cal_title} ({period_start}~{period_end})"

    requester_id = str(doc.get("requester_id") or session.user_id)
    tenant_id = session.tenant_id

    ws.add_calendar_event_for_user(
        requester_id,
        tenant_id,
        cal_title,
        period_start or due,
        end_date=period_end,
        source="workflow",
        document_id=doc_id,
    )
    ws.add_todo_for_user(
        requester_id,
        tenant_id,
        f"결재 진행: {title} ({doc_no})",
        due_date=due,
        source="workflow",
        document_id=doc_id,
    )

    seen: set[str] = set()
    for i, step in enumerate(approval_line, start=1):
        uid = str(step.get("approver_id") or "").strip()
        if not uid or uid in seen:
            continue
        seen.add(uid)
        role = step.get("approver_role", "")
        ws.add_todo_for_user(
            uid,
            tenant_id,
            f"결재 {i}단계: {title} ({doc_no})",
            due_date=due,
            source="workflow_approval",
            document_id=doc_id,
            extra={"role": role},
        )
        ws.add_calendar_event_for_user(
            uid,
            tenant_id,
            f"결재: {title}",
            due or period_start,
            end_date=period_end,
            source="workflow_approval",
            document_id=doc_id,
        )

    for uid in cc_user_ids or []:
        uid = str(uid).strip()
        if not uid or uid in seen or uid == requester_id:
            continue
        ws.add_todo_for_user(
            uid,
            tenant_id,
            f"참조: {title} ({doc_no})",
            due_date=due,
            source="workflow_cc",
            document_id=doc_id,
        )


def sync_approval_complete_follow_up(
    doc: dict[str, Any],
    *,
    session: UserSession,
    executor_id: str = "",
) -> None:
    """최종 승인 후 실행 담당자 To-Do·일정."""
    title = str(doc.get("title") or "문서")
    doc_id = str(doc.get("id") or "")
    period_end = str(doc.get("period_end") or doc.get("due_date") or "")
    tenant_id = session.tenant_id
    requester_id = str(doc.get("requester_id") or "")

    ws.add_todo_for_user(
        requester_id,
        tenant_id,
        f"실행·완료 확인: {title}",
        due_date=period_end,
        source="workflow_execution",
        document_id=doc_id,
    )

    if executor_id and executor_id != requester_id:
        ws.add_todo_for_user(
            executor_id,
            tenant_id,
            f"실행: {title}",
            due_date=period_end,
            source="workflow_execution",
            document_id=doc_id,
        )
        ws.add_calendar_event_for_user(
            executor_id,
            tenant_id,
            f"실행: {title}",
            period_end or doc.get("period_start", ""),
            source="workflow_execution",
            document_id=doc_id,
        )
