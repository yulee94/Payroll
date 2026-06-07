"""개인별 HR 문서 권한 정책.

The app currently has coarse roles (staff/finance/admin), org positions, and
platform access.  This module maps Issue #76's HR-document roles onto those
existing primitives without changing payroll/HR permissions globally.
"""

from __future__ import annotations

from typing import Any

from core.org_positions import POS_CEO, POS_DIRECTOR, POS_EXECUTIVE, POS_MANAGER, POS_TEAM_LEAD
from core.roles import ROLE_ADMIN, ROLE_FINANCE, normalize_role
from core.session_service import UserSession, get_session
from core.user_store import get_user

PAYROLL_TYPE_KEYWORDS = ("급여", "연봉", "원천징수", "갑근세", "소득", "payslip", "withholding", "payroll", "salary")
SENSITIVE_TYPE_KEYWORDS = ("신분", "주민", "비자", "체류", "외국인", "개인정보", "계좌", "identity", "visa", "privacy")


def _sess(session: UserSession | None = None) -> UserSession | None:
    return session or get_session()


def _is_admin(session: UserSession | None = None) -> bool:
    sess = _sess(session)
    return bool(sess and normalize_role(sess.role) == ROLE_ADMIN)


def _is_finance(session: UserSession | None = None) -> bool:
    sess = _sess(session)
    return bool(sess and normalize_role(sess.role) == ROLE_FINANCE)


def _can_manage_org(session: UserSession | None = None) -> bool:
    """Lazy org-admin check.

    Recent payroll/workflow modules can make ``core.org_access`` import optional
    Excel/payroll dependencies.  HR document permissions should still import and
    run in minimal test/runtime environments without those extras.
    """

    sess = _sess(session)
    if not sess:
        return False
    if _is_admin(sess):
        return True
    try:
        from core.org_access import can_manage_org

        return bool(can_manage_org(sess))
    except Exception:
        return False


def _can_access_hr_platform(session: UserSession | None = None) -> bool:
    sess = _sess(session)
    if not sess:
        return False
    if _is_admin(sess):
        return True
    try:
        from core.org_access import can_access_platform

        return bool(can_access_platform("hr", session=sess))
    except Exception:
        # Fallback keeps direct-manager HR document visibility usable when the
        # optional payroll Excel stack is not installed.
        return True


def _position(user_id: str) -> str:
    rec = get_user(user_id)
    return rec.position if rec else ""


def _is_team_leader(session: UserSession | None = None) -> bool:
    sess = _sess(session)
    if not sess:
        return False
    return _position(sess.user_id) in {POS_CEO, POS_EXECUTIVE, POS_DIRECTOR, POS_MANAGER, POS_TEAM_LEAD}


def _is_direct_manager(employee_user_id: str, session: UserSession | None = None) -> bool:
    sess = _sess(session)
    if not sess or not employee_user_id:
        return False
    rec = get_user(employee_user_id)
    return bool(rec and rec.manager_user_id == sess.user_id)


def _type_text(doc_or_type: dict[str, Any] | str) -> str:
    if isinstance(doc_or_type, dict):
        parts = [
            str(doc_or_type.get("document_type") or ""),
            str(doc_or_type.get("document_type_label") or ""),
            str(doc_or_type.get("document_name") or ""),
        ]
        return " ".join(parts).casefold()
    return str(doc_or_type or "").casefold()


def is_payroll_document(doc_or_type: dict[str, Any] | str) -> bool:
    text = _type_text(doc_or_type)
    return any(k.casefold() in text for k in PAYROLL_TYPE_KEYWORDS)


def is_sensitive_document(doc_or_type: dict[str, Any] | str) -> bool:
    text = _type_text(doc_or_type)
    return any(k.casefold() in text for k in SENSITIVE_TYPE_KEYWORDS)


def can_manage_employee_documents(session: UserSession | None = None) -> bool:
    """HR 관리자/최고관리자: 전체 문서 관리 가능."""

    sess = _sess(session)
    if not sess:
        return False
    return _is_admin(sess) or _can_manage_org(sess)


def can_approve_document_requests(session: UserSession | None = None) -> bool:
    return can_manage_employee_documents(session)


def can_generate_for_employee(employee_user_id: str = "", session: UserSession | None = None) -> bool:
    """Compatibility permission for certificate-generation self-service."""

    sess = _sess(session)
    if not sess:
        return False
    return can_manage_employee_documents(sess) or _is_finance(sess) or (employee_user_id and employee_user_id == sess.user_id)


def can_view_employee_documents(
    employee_user_id: str = "",
    *,
    session: UserSession | None = None,
    document: dict[str, Any] | None = None,
) -> bool:
    """Employee self-view, HR admin full-view, payroll limited-view, manager partial-view."""

    sess = _sess(session)
    if not sess:
        return False
    if can_manage_employee_documents(sess):
        return True
    if employee_user_id and employee_user_id == sess.user_id:
        return True
    if document and is_payroll_document(document):
        return _is_finance(sess)
    if document and is_sensitive_document(document):
        return False
    if employee_user_id and _is_direct_manager(employee_user_id, sess):
        return _is_team_leader(sess) and _can_access_hr_platform(sess)
    return False


def can_upload_employee_document(
    employee_user_id: str = "",
    *,
    session: UserSession | None = None,
    doc_type_policy: dict[str, Any] | None = None,
) -> bool:
    sess = _sess(session)
    if not sess:
        return False
    if can_manage_employee_documents(sess):
        return True
    if _is_finance(sess) and doc_type_policy and doc_type_policy.get("payroll_related"):
        return True
    if employee_user_id and employee_user_id == sess.user_id:
        return bool((doc_type_policy or {}).get("employee_upload_allowed", False))
    return False


def can_download_document(document: dict[str, Any], *, session: UserSession | None = None) -> bool:
    sess = _sess(session)
    if not sess:
        return False
    if str(document.get("status") or "") in {"검토 필요", "반려"} and not can_manage_employee_documents(sess):
        return False
    if can_manage_employee_documents(sess):
        return True
    if is_payroll_document(document):
        return _is_finance(sess)
    if is_sensitive_document(document) and str(document.get("employee_user_id") or "") != sess.user_id:
        return False
    return can_view_employee_documents(str(document.get("employee_user_id") or ""), session=sess, document=document)
