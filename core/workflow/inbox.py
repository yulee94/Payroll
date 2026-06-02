"""
core/workflow/inbox.py - 시장 표준 그룹웨어형 결재함 (다우오피스·네이버웍스·잔디 패턴)

결재함 분류:
  to_approve   — 결재할 문서 (내 차례)
  in_progress  — 진행함 (내 기안·결재 진행 중)
  completed    — 완료함
  rejected     — 반려·취소함
  my_draft     — 임시저장·보완
  reference    — 참조함 (결재선·참조자)
  all          — 전체
"""

from __future__ import annotations

from typing import Any

from core.session_service import UserSession
from core.workflow import permissions as wf_perm
from core.workflow.constants import (
    DOC_STATUS_APPROVED,
    DOC_STATUS_CANCELLED,
    DOC_STATUS_CLOSED,
    DOC_STATUS_COMPLETED,
    DOC_STATUS_DRAFT,
    DOC_STATUS_IN_REVIEW,
    DOC_STATUS_REJECTED,
    DOC_STATUS_REQUESTED_CHANGES,
    DOC_STATUS_SUBMITTED,
)

# id → (라벨, 설명, 참고 서비스) — 상단은 COSS GW 결재 메뉴 순서에 맞춤
INBOX_DEFINITIONS: tuple[tuple[str, str, str, str], ...] = (
    ("to_approve", "결재할 문서", "내 결재 차례인 문서", "GW 결재할 문서"),
    ("my_draft", "기안함", "작성 중·보완 요청", "GW 기안"),
    ("circulate", "공람", "참조·공람으로 받은 문서", "GW 공람"),
    ("in_progress", "진행함", "내가 올린 문서·결재 진행 중", "GW 진행"),
    ("completed", "완료함", "승인·실행완료·마감", "완료함"),
    ("rejected", "반려함", "반려·취소된 문서", "반려함"),
    ("reference", "참조함", "결재선 참여·열람", "참조"),
    ("all", "전체", "열람 가능한 모든 문서", "통합 목록"),
)

# GW 결재함 상단 퀵 탭 (전체 / 대기 / 기안 / 공람)
GW_INBOX_QUICK_TABS: tuple[tuple[str, str], ...] = (
    ("all", "전체"),
    ("to_approve", "대기"),
    ("my_draft", "기안"),
    ("circulate", "공람"),
)

INBOX_IDS: tuple[str, ...] = tuple(row[0] for row in INBOX_DEFINITIONS)

INBOX_LABELS: dict[str, str] = {row[0]: row[1] for row in INBOX_DEFINITIONS}


def _uid(sess: UserSession) -> str:
    return sess.user_id


def _cc_users(doc: dict[str, Any]) -> set[str]:
    raw = doc.get("cc_user_ids") or doc.get("cc_users") or []
    return {str(x) for x in raw if x}


def _gw_list_kind(doc: dict[str, Any]) -> str:
    cj = doc.get("content_json") or {}
    if not isinstance(cj, dict):
        return ""
    return str(cj.get("gw_list") or "").lower()


def _is_gw_import(doc: dict[str, Any]) -> bool:
    cj = doc.get("content_json") or {}
    return isinstance(cj, dict) and bool(cj.get("imported_from") or cj.get("gw_doc_id"))


def matches_inbox(
    doc: dict[str, Any],
    inbox_id: str,
    *,
    session: UserSession,
    tenant_id: str,
) -> bool:
    """문서가 해당 결재함에 속하는지."""
    if inbox_id in ("", "all"):
        return True

    uid = _uid(session)
    status = doc.get("status") or ""
    is_mine = doc.get("requester_id") == uid
    can_approve = wf_perm.can_approve_document(session, doc, tenant_id=tenant_id)
    steps = doc.get("approval_steps") or []
    on_line = any(s.get("approver_id") == uid for s in steps)
    in_cc = uid in _cc_users(doc)

    if inbox_id == "to_approve":
        if _is_gw_import(doc):
            gl = _gw_list_kind(doc)
            if gl in ("pending", "to_approve", "inbox_scrape", "inbox"):
                return status in (DOC_STATUS_SUBMITTED, DOC_STATUS_IN_REVIEW)
        return can_approve and status in (DOC_STATUS_SUBMITTED, DOC_STATUS_IN_REVIEW)

    if inbox_id == "my_draft":
        if _is_gw_import(doc):
            gl = _gw_list_kind(doc)
            return gl in ("draft", "drafts", "my_draft", "drafts_page1", "기안", "browser")
        return is_mine and status in (DOC_STATUS_DRAFT, DOC_STATUS_REQUESTED_CHANGES)

    if inbox_id == "in_progress":
        if is_mine and status in (DOC_STATUS_SUBMITTED, DOC_STATUS_IN_REVIEW):
            return True
        if on_line and status in (DOC_STATUS_SUBMITTED, DOC_STATUS_IN_REVIEW):
            return True
        return False

    if inbox_id == "completed":
        if status in (DOC_STATUS_APPROVED, DOC_STATUS_COMPLETED, DOC_STATUS_CLOSED):
            return is_mine or on_line or in_cc
        return False

    if inbox_id == "rejected":
        return status in (DOC_STATUS_REJECTED, DOC_STATUS_CANCELLED) and (is_mine or on_line)

    if inbox_id == "circulate":
        if _is_gw_import(doc):
            gl = _gw_list_kind(doc)
            if gl in ("circulate", "circulate_home_widget", "공람", "reference"):
                return True
        if uid not in _cc_users(doc):
            return False
        if can_approve and status in (DOC_STATUS_SUBMITTED, DOC_STATUS_IN_REVIEW):
            return False
        return status not in (DOC_STATUS_DRAFT, DOC_STATUS_CANCELLED)

    if inbox_id == "reference":
        if in_cc:
            return False
        if on_line and not is_mine and status not in (DOC_STATUS_DRAFT,):
            return True
        return False

    # 레거시 필터 (기존 UI 호환)
    if inbox_id == "my_requests":
        return is_mine
    if inbox_id == "pending_approval":
        return matches_inbox(doc, "to_approve", session=session, tenant_id=tenant_id)

    return True


def filter_inbox(
    documents: list[dict[str, Any]],
    inbox_id: str,
    *,
    session: UserSession,
    tenant_id: str,
) -> list[dict[str, Any]]:
    return [
        d
        for d in documents
        if matches_inbox(d, inbox_id, session=session, tenant_id=tenant_id)
    ]


def count_by_inbox(
    documents: list[dict[str, Any]],
    *,
    session: UserSession,
    tenant_id: str,
) -> dict[str, int]:
    counts = {iid: 0 for iid in INBOX_IDS}
    for iid in INBOX_IDS:
        counts[iid] = len(filter_inbox(documents, iid, session=session, tenant_id=tenant_id))
    return counts
