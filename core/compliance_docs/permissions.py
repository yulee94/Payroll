"""법정·규정 문서함 접근 권한."""

from __future__ import annotations

from core.access_control import can_manage_user_roles, session_role
from core.org_access import has_permission
from core.org_positions import PERM_HR, PERM_ORG_MANAGE, PERM_TENANT_ADMIN
from core.session_service import UserSession, get_session, require_session
from core.tenant_data_scope import enforce_session_tenant_access


def can_view_compliance_docs(session: UserSession | None = None) -> bool:
    """법인 소속 로그인 사용자는 열람 가능."""
    sess = session or get_session()
    if sess is None:
        return False
    try:
        enforce_session_tenant_access(sess)
    except PermissionError:
        return False
    return True


def can_manage_compliance_docs(session: UserSession | None = None) -> bool:
    """업로드·관리: 테넌트 관리자, 조직 관리자, HR 권한, 시스템 관리자."""
    sess = session or get_session()
    if sess is None:
        return False
    if not can_view_compliance_docs(sess):
        return False
    if has_permission(PERM_TENANT_ADMIN, session=sess):
        return True
    if has_permission(PERM_ORG_MANAGE, session=sess):
        return True
    if can_manage_user_roles(session_role(sess)):
        return True
    if has_permission(PERM_HR, session=sess):
        return True
    return False


def require_view_compliance_docs(session: UserSession | None = None) -> UserSession:
    sess = require_session() if session is None else session
    if not can_view_compliance_docs(sess):
        raise PermissionError("법정·규정 문서함 열람 권한이 없습니다.")
    return enforce_session_tenant_access(sess)


def require_manage_compliance_docs(session: UserSession | None = None) -> UserSession:
    sess = require_view_compliance_docs(session)
    if not can_manage_compliance_docs(sess):
        raise PermissionError("문서 업로드·관리는 HR 담당자 또는 관리자만 가능합니다.")
    return sess
