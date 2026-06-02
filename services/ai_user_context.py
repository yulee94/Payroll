"""
services/ai_user_context.py - Personal AI용 사용자·권한 컨텍스트
"""

from __future__ import annotations

from datetime import date
from typing import Any, TypedDict

from core.access_control import can_view_executive_payroll, session_role
from core.roles import role_label
from core.session_service import UserSession, require_session
from core.org_access import get_user_org_context, session_permissions
from core.org_positions import ORG_PLATFORM_LABELS, PLATFORM_TO_PERM
from core.org_store import get_unit
from core.tenant_data_scope import tenant_data_scope_label
from core.tenant_store import get_tenant
from services import workspace_store as ws


class UserContextDict(TypedDict):
    userId: str
    name: str
    department: str
    position: str
    permissions: list[str]
    recentTasks: list[str]
    companyRules: list[str]
    tenantId: str
    tenantName: str
    dataScope: str


def get_user_context(session: UserSession | None = None) -> UserContextDict:
    """
    로그인 세션 기반 사용자 컨텍스트.
    TODO(DB): users/departments 테이블에서 department, position, recentTasks 연동.
    현재는 세션·workspace_store(할 일·일정)만 사용합니다.
    """
    sess = session or require_session()
    tenant = get_tenant(sess.tenant_id)
    role = session_role(sess)

    perms: list[str] = [role_label(role)]
    if can_view_executive_payroll(role):
        perms.append("임원급여·경영보고 열람")
    else:
        perms.append("일반급여·명부(임원 제외)")

    ctx = get_user_org_context(sess.user_id)
    unit_rec = get_unit(sess.tenant_id, ctx["org_unit_id"]) if ctx["org_unit_id"] else None
    dept = unit_rec.name if unit_rec else (tenant.display_name if tenant else sess.tenant_id)
    pos_label = ctx["position_label"] or role_label(role)

    for plat_id, perm in PLATFORM_TO_PERM.items():
        if perm in session_permissions(sess):
            perms.append(ORG_PLATFORM_LABELS.get(plat_id, plat_id))

    todos = [t for t in ws.list_todos(sess) if not t.get("done")][:5]
    recent_tasks = [str(t.get("title") or "") for t in todos if t.get("title")]

    today = date.today()
    events = ws.list_calendar_events(today.year, today.month, sess)[:3]
    for ev in events:
        recent_tasks.append(f"일정 {ev.get('date', '')}: {ev.get('title', '')}")

    company_rules = [
        "본인 고객사(법인) 데이터만 조회·기안에 사용합니다.",
        "급여·인원 수치는 플랫폼 저장 데이터와 일치해야 합니다.",
        "임원 관련 정보는 재무팀·관리자 권한에서만 다룹니다.",
    ]

    return UserContextDict(
        userId=sess.user_id,
        name=sess.display_name,
        department=dept,
        position=pos_label,
        permissions=perms,
        recentTasks=recent_tasks,
        companyRules=company_rules,
        tenantId=sess.tenant_id,
        tenantName=(tenant.display_name if tenant else sess.tenant_id),
        dataScope=tenant_data_scope_label(sess.tenant_id),
    )


def format_user_context_block(ctx: UserContextDict) -> str:
    lines = [
        "=== 사용자 컨텍스트 ===",
        f"이름: {ctx['name']} (ID: {ctx['userId']})",
        f"소속(고객사): {ctx['tenantName']} · 데이터 범위: {ctx['dataScope']}",
        f"직급(권한): {ctx['position']}",
        f"허용 기능: {', '.join(ctx['permissions'])}",
    ]
    if ctx["recentTasks"]:
        lines.append("최근 할 일·일정: " + "; ".join(ctx["recentTasks"][:6]))
    lines.append("사내 규칙:")
    for rule in ctx["companyRules"]:
        lines.append(f"  · {rule}")
    return "\n".join(lines)
