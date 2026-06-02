"""앱 표시명·창 제목 (Bitween · 활성 고객사)."""

from __future__ import annotations

from core.config import APP_CONFIG
from core.org_access import get_user_org_context
from core.org_store import get_root_unit_id, get_unit
from core.session_service import UserSession, get_session
from core.tenant_store import get_active_tenant, get_tenant

_brand = APP_CONFIG.brand


def app_window_title(*, suffix: str = "") -> str:
    base = f"{_brand.product_icon} {_brand.product_name}"
    if suffix:
        return f"{base} — {suffix}"
    return base


def product_name_line() -> str:
    return f"{_brand.product_icon}  {_brand.product_name}"


def company_name_line() -> str:
    """화면에 표시할 운영 회사명 (테넌트)."""
    return get_active_tenant().display_name


def company_name_ko_line() -> str:
    ko = get_active_tenant().display_name_ko
    return ko or ""


def launcher_tagline() -> str:
    return _brand.product_tagline


def active_tenant_login_id() -> str:
    return get_active_tenant().login_id


def _legal_entity_label(tenant_id: str) -> str:
    """테넌트·그룹 법인명 (예: (주)코스)."""
    tid = str(tenant_id or "").strip()
    if not tid:
        return ""
    try:
        from core.group_store import get_group_for_tenant
        from core.workflow.config_store import get_entity_for_tenant

        grp = get_group_for_tenant(tid)
        if grp:
            ent = get_entity_for_tenant(grp.group_id, tid)
            if ent:
                name = str(ent.get("name_ko") or ent.get("name") or "").strip()
                if name:
                    return name
    except Exception:
        pass
    rec = get_tenant(tid)
    if rec:
        return (rec.display_name_ko or rec.display_name or "").strip()
    return ""


def sidebar_user_identity_line(session: UserSession | None = None) -> str:
    """
    로그인 사용자 표시 (예: (주)코스 경영지원팀 홍길동 팀장·과장).
    미로그인 시 빈 문자열.
    """
    sess = session or get_session()
    if sess is None:
        return ""

    tid = sess.tenant_id
    ctx = get_user_org_context(sess.user_id)
    parts: list[str] = []

    entity = _legal_entity_label(tid)
    if entity:
        parts.append(entity)

    unit_id = str(ctx.get("org_unit_id") or "").strip()
    if unit_id:
        unit = get_unit(tid, unit_id)
        root_id = get_root_unit_id(tid) or ""
        if unit and unit.name and (not root_id or unit.unit_id != root_id):
            parts.append(unit.name.strip())

    name = str(sess.display_name or "").strip()
    pos = str(ctx.get("position_label") or "").strip()
    if name and pos:
        parts.append(f"{name} {pos}")
    elif name:
        parts.append(name)

    return " ".join(p for p in parts if p)
