"""
core/hr/onboarding_notify.py - 입·퇴사 담당자·책임자 알림·할 일 연동
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from core.hr.onboarding_templates import ROLE_LABELS
from core.user_store import find_user_by_username, get_user, list_users_for_tenant
from core.org_positions import POS_CEO, POS_DIRECTOR, POS_MANAGER, POS_TEAM_LEAD
from core.workflow.store import add_notification, with_db
from services import workspace_store as ws

NTYPE_ASSIGNED = "hr_onboarding_assigned"
NTYPE_OVERDUE = "hr_onboarding_overdue"
NTYPE_COMPLETE = "hr_onboarding_complete"
NTYPE_CASE_CREATED = "hr_onboarding_created"


def _role_user_id(tenant_id: str, role: str, case: dict[str, Any]) -> tuple[str, str]:
    """역할 → (user_id, 표시명)."""
    tid = str(tenant_id or "").strip()
    role = str(role or "").strip()

    if role == "hr":
        uid = str(case.get("hr_user_id") or "")
        if uid:
            u = get_user(uid)
            return uid, (u.display_name if u else ROLE_LABELS["hr"])
        u = find_user_by_username(tid, "coss_hr")
        return (u.user_id, u.display_name) if u else ("", ROLE_LABELS["hr"])

    if role == "payroll":
        uid = str(case.get("payroll_user_id") or "")
        if uid:
            u = get_user(uid)
            return uid, (u.display_name if u else ROLE_LABELS["payroll"])
        for uname in ("coss_finance", "coss_acct"):
            u = find_user_by_username(tid, uname)
            if u:
                return u.user_id, u.display_name
        return "", ROLE_LABELS["payroll"]

    if role in ("dept_manager", "safety", "admin"):
        uid = str(case.get("manager_user_id") or "")
        if uid:
            u = get_user(uid)
            return uid, (u.display_name if u else ROLE_LABELS.get(role, role))
        for u in list_users_for_tenant(tid):
            if u.position in (POS_MANAGER, POS_DIRECTOR, POS_TEAM_LEAD, POS_CEO):
                return u.user_id, u.display_name
        return "", ROLE_LABELS.get(role, role)

    return "", role


def resolve_case_assignees(tenant_id: str, case: dict[str, Any]) -> dict[str, Any]:
    """케이스에 hr/payroll/manager user_id 채우기."""
    tid = str(tenant_id or "").strip()
    hr_id, _ = _role_user_id(tid, "hr", case)
    pay_id, _ = _role_user_id(tid, "payroll", case)
    mgr_id, _ = _role_user_id(tid, "dept_manager", case)
    case["hr_user_id"] = hr_id
    case["payroll_user_id"] = pay_id
    if not case.get("manager_user_id"):
        case["manager_user_id"] = mgr_id
    return case


def _push_notification(
    tenant_id: str,
    user_id: str,
    *,
    ntype: str,
    title: str,
    message: str,
    case_id: str = "",
) -> None:
    if not user_id or not tenant_id:
        return

    def mut(db: dict[str, Any]) -> None:
        add_notification(
            db,
            user_id=user_id,
            ntype=ntype,
            title=title,
            message=message,
            related_task_id=case_id,
        )

    with_db(tenant_id)(mut)


def _push_todo(
    tenant_id: str,
    user_id: str,
    title: str,
    *,
    due_date: str = "",
    case_id: str = "",
    task_id: str = "",
) -> None:
    if not user_id or not tenant_id:
        return
    try:
        ws.add_todo_for_user(
            user_id,
            tenant_id,
            title,
            due_date=due_date,
            source="hr_onboarding",
            document_id=case_id,
            extra={"task_id": task_id},
        )
    except ValueError:
        pass


def _push_calendar(tenant_id: str, user_id: str, title: str, event_date: str, *, case_id: str = "") -> None:
    if not user_id or not tenant_id or not event_date:
        return
    try:
        ws.add_calendar_event_for_user(
            user_id,
            tenant_id,
            title,
            event_date,
            source="hr_onboarding",
            document_id=case_id,
        )
    except ValueError:
        pass


def notify_case_created(tenant_id: str, case: dict[str, Any], *, actor_user_id: str = "") -> None:
    """케이스 생성 시 HR·부서장·각 담당자에게 알림·할 일."""
    case_id = str(case.get("id") or "")
    name = str(case.get("employee_name") or "")
    pt = str(case.get("process_type") or "")
    target = str(case.get("target_date") or "")
    dept = str(case.get("department") or "")

    summary = f"{name} · {pt} · {target} · {dept}"
    notified: set[str] = set()

    hr_id = str(case.get("hr_user_id") or "")
    mgr_id = str(case.get("manager_user_id") or "")

    for uid, label in ((hr_id, "인사"), (mgr_id, "부서장")):
        if uid and uid not in notified:
            notified.add(uid)
            _push_notification(
                tenant_id,
                uid,
                ntype=NTYPE_CASE_CREATED,
                title=f"[입·퇴사] {pt} 절차 개시",
                message=f"{summary}\n체크리스트 {len(case.get('tasks') or [])}건이 생성되었습니다.",
                case_id=case_id,
            )
            _push_calendar(tenant_id, uid, f"[입·퇴사] {name} {pt}", target, case_id=case_id)

    for task in case.get("tasks") or []:
        if task.get("status") == "완료":
            continue
        _notify_task_assigned(tenant_id, case, task, first=True)


def _notify_task_assigned(tenant_id: str, case: dict[str, Any], task: dict[str, Any], *, first: bool = False) -> None:
    uid = str(task.get("assignee_user_id") or "")
    if not uid:
        return
    case_id = str(case.get("id") or "")
    name = str(case.get("employee_name") or "")
    pt = str(case.get("process_type") or "")
    title = str(task.get("title") or "")
    doc = str(task.get("document") or "")
    due = str(task.get("due_date") or "")
    critical = " ⚠ 법정" if task.get("critical") else ""

    msg = f"{name} ({pt})\n· {title}\n· 서류: {doc}\n· 마감: {due or '미정'}{critical}"
    _push_notification(
        tenant_id,
        uid,
        ntype=NTYPE_ASSIGNED,
        title=f"[입·퇴사] 담당 업무{critical}",
        message=msg,
        case_id=case_id,
    )
    todo_title = f"[입·퇴사] {title} — {name}"
    if doc:
        todo_title = f"{todo_title} ({doc})"
    _push_todo(tenant_id, uid, todo_title, due_date=due, case_id=case_id, task_id=str(task.get("id") or ""))


def notify_task_overdue(tenant_id: str, case: dict[str, Any], task: dict[str, Any]) -> None:
    uid = str(task.get("assignee_user_id") or "")
    hr_id = str(case.get("hr_user_id") or "")
    mgr_id = str(case.get("manager_user_id") or "")
    case_id = str(case.get("id") or "")
    name = str(case.get("employee_name") or "")
    title = str(task.get("title") or "")
    due = str(task.get("due_date") or "")

    msg = f"{name}\n· {title}\n· 마감: {due} (지연)\n즉시 처리 필요"
    if task.get("critical"):
        msg += "\n※ 법정 신고·4대보험 누락 위험"

    targets = {uid for uid in (uid, hr_id, mgr_id) if uid}
    for target in targets:
        _push_notification(
            tenant_id,
            target,
            ntype=NTYPE_OVERDUE,
            title=f"[입·퇴사] ⚠ 지연 — {title}",
            message=msg,
            case_id=case_id,
        )


def notify_case_completed(tenant_id: str, case: dict[str, Any]) -> None:
    case_id = str(case.get("id") or "")
    name = str(case.get("employee_name") or "")
    pt = str(case.get("process_type") or "")
    msg = f"{name} · {pt} 절차가 모두 완료되었습니다."
    for uid in {str(case.get("hr_user_id") or ""), str(case.get("manager_user_id") or "")}:
        if uid:
            _push_notification(
                tenant_id,
                uid,
                ntype=NTYPE_COMPLETE,
                title=f"[입·퇴사] {pt} 완료",
                message=msg,
                case_id=case_id,
            )


def due_date_from_target(target_date: str, offset_days: int) -> str:
    try:
        base = date.fromisoformat(str(target_date)[:10])
    except ValueError:
        return str(target_date or "")[:10]
    return (base + timedelta(days=int(offset_days))).isoformat()
