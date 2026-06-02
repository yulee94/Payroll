"""
core/hr/service.py - 인사 · 노무 (한국 일반 기업 HR)

근로기준법·노무 실무 기준: 명부, 연차, 근태, 근로계약, 증명서, 징계·상담, 입·퇴사.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from core.module_store import load_module_db, mutate_module_db, save_module_db
from core.session_service import session_tenant_id, get_session
from core.hr.onboarding_templates import ROLE_LABELS, steps_for_process
from core.hr import onboarding_notify as ob_notify
from core.hr import roster_sync as hr_roster_sync
from core.hr import traffic_signal as hr_signal
from core.hr.traffic_signal import SignalProfile

MODULE = "hr"

_EMPTY: dict[str, Any] = {
    "leave_records": [],
    "attendance": [],
    "contracts": [],
    "certificates": [],
    "labor_cases": [],
    "onboarding": [],
    "seeded": False,
}

# UI 탭 (명부는 EmployeeRosterPanel 별도)
RECORD_TAB_IDS = ("leave", "attendance", "contracts", "certificates", "labor", "onboarding")

ALL_TAB_IDS = ("roster", *RECORD_TAB_IDS, "recruitment", "severance", "signal", "compliance_docs", "health_checkup")

TAB_LABELS = {
    "roster": "직원 명부",
    "leave": "연차 · 휴가",
    "attendance": "근태",
    "contracts": "근로계약",
    "certificates": "증명서",
    "labor": "노무 · 징계",
    "onboarding": "입 · 퇴사",
    "recruitment": "채용",
    "severance": "퇴직금",
    "signal": "신호등",
    "compliance_docs": "법정 · 규정",
    "health_checkup": "건강검진",
}


def _tid() -> str:
    return session_tenant_id() or "default"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _today() -> str:
    return date.today().isoformat()


def _parse_date(s: str) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _build_tasks_from_template(
    process_type: str,
    target_date: str,
    tenant_id: str,
    case: dict[str, Any],
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for tpl in steps_for_process(process_type):
        uid, uname = ob_notify._role_user_id(tenant_id, tpl.assignee_role, case)
        due = ob_notify.due_date_from_target(target_date, tpl.due_offset_days)
        tasks.append(
            {
                "id": _new_id(),
                "code": tpl.code,
                "title": tpl.title,
                "document": tpl.document,
                "assignee_role": tpl.assignee_role,
                "assignee_user_id": uid,
                "assignee_name": uname or ROLE_LABELS.get(tpl.assignee_role, tpl.assignee_role),
                "due_date": due,
                "required": tpl.required,
                "critical": tpl.critical,
                "category": tpl.category,
                "legal_note": tpl.legal_note,
                "status": "대기",
                "completed_at": "",
                "reminder_sent": False,
                "note": "",
            }
        )
    return tasks


def _calc_case_progress(case: dict[str, Any]) -> dict[str, Any]:
    tasks = list(case.get("tasks") or [])
    required = [t for t in tasks if t.get("required", True)]
    done = sum(1 for t in required if t.get("status") == "완료")
    total = len(required) or 1
    overdue = 0
    today = date.today()
    for t in tasks:
        if t.get("status") == "완료":
            continue
        d = _parse_date(str(t.get("due_date") or ""))
        if d and d < today:
            t["status"] = "지연"
            overdue += 1
    case["progress_pct"] = int(done * 100 / total)
    case["overdue_count"] = overdue
    case["tasks_done"] = done
    case["tasks_total"] = len(required)
    pending_critical = [
        t for t in tasks if t.get("critical") and t.get("status") != "완료"
    ]
    if pending_critical and overdue:
        case["status"] = "지연"
    elif done >= total and total > 0:
        case["status"] = "완료"
    elif case.get("status") not in ("예정", "보류", "완료", "지연"):
        case["status"] = "진행중"
    return case


def _legacy_to_case(row: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    """구 flat 레코드 → 절차·체크리스트 케이스."""
    case = {
        "id": str(row.get("id") or _new_id()),
        "employee_name": str(row.get("employee_name") or ""),
        "process_type": str(row.get("process_type") or "입사"),
        "target_date": str(row.get("target_date") or _today()),
        "department": str(row.get("department") or ""),
        "site_name": str(row.get("site_name") or ""),
        "status": str(row.get("status") or "진행중"),
        "note": str(row.get("checklist") or row.get("note") or ""),
        "created_at": str(row.get("created_at") or _today()),
        "created_by": str(row.get("created_by") or ""),
        "manager_user_id": str(row.get("manager_user_id") or ""),
        "hr_user_id": "",
        "payroll_user_id": "",
    }
    ob_notify.resolve_case_assignees(tenant_id, case)
    case["tasks"] = _build_tasks_from_template(
        case["process_type"], case["target_date"], tenant_id, case
    )
    return _calc_case_progress(case)


def _migrate_onboarding_schema(db: dict[str, Any], tenant_id: str) -> bool:
    rows = list(db.get("onboarding") or [])
    if not rows:
        return False
    if rows and isinstance(rows[0].get("tasks"), list):
        return False
    db["onboarding"] = [_legacy_to_case(r, tenant_id) for r in rows]
    return True


def _ensure_onboarding_ready(db: dict[str, Any], tenant_id: str) -> None:
    if _migrate_onboarding_schema(db, tenant_id):
        save_module_db(MODULE, tenant_id, db)
    for i, case in enumerate(list(db.get("onboarding") or [])):
        updated = _calc_case_progress(dict(case))
        db["onboarding"][i] = updated


def ensure_seed(tenant_id: str | None = None) -> None:
    tid = tenant_id or _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    if db.get("seeded"):
        _ensure_onboarding_ready(db, tid)
        save_module_db(MODULE, tid, db)
        return
    d = date.today()
    y = d.year
    db["leave_records"] = [
        {
            "id": _new_id(),
            "employee_name": "김민수",
            "leave_type": "연차",
            "start_date": (d + timedelta(days=14)).isoformat(),
            "end_date": (d + timedelta(days=14)).isoformat(),
            "days": 1,
            "status": "승인",
            "balance_after": 12,
            "note": "전자결재 연동 예정",
        },
        {
            "id": _new_id(),
            "employee_name": "이영희",
            "leave_type": "반차",
            "start_date": d.isoformat(),
            "end_date": d.isoformat(),
            "days": 0.5,
            "status": "사용",
            "balance_after": 8.5,
            "note": "",
        },
    ]
    db["attendance"] = [
        {
            "id": _new_id(),
            "employee_name": "박철수",
            "date": (d - timedelta(days=1)).isoformat(),
            "type": "지각",
            "minutes": 25,
            "status": "확인",
            "note": "교통 지연",
        },
        {
            "id": _new_id(),
            "employee_name": "최지원",
            "date": d.isoformat(),
            "type": "출장",
            "minutes": 0,
            "status": "승인",
            "note": "부산 사업장",
        },
    ]
    db["contracts"] = [
        {
            "id": _new_id(),
            "employee_name": "정우진",
            "contract_type": "정규직",
            "start_date": f"{y}-03-01",
            "end_date": "",
            "department": "경영지원",
            "position": "대리",
            "status": "유효",
        },
        {
            "id": _new_id(),
            "employee_name": "한소희",
            "contract_type": "계약직",
            "start_date": f"{y}-01-15",
            "end_date": f"{y}-12-31",
            "department": "정비",
            "position": "사원",
            "status": "유효",
        },
    ]
    db["certificates"] = [
        {
            "id": _new_id(),
            "employee_name": "김민수",
            "cert_type": "재직증명서",
            "request_date": d.isoformat(),
            "issue_date": d.isoformat(),
            "purpose": "금융기관 제출",
            "status": "발급완료",
        },
        {
            "id": _new_id(),
            "employee_name": "이영희",
            "cert_type": "경력증명서",
            "request_date": (d - timedelta(days=2)).isoformat(),
            "issue_date": "",
            "purpose": "이직",
            "status": "대기",
        },
    ]
    db["labor_cases"] = [
        {
            "id": _new_id(),
            "employee_name": "박철수",
            "case_type": "경고",
            "occurred_date": (d - timedelta(days=30)).isoformat(),
            "summary": "안전수칙 위반 1회",
            "action": "서면 경고",
            "status": "종결",
        },
    ]
    db["onboarding"] = []
    tid = tenant_id or _tid()
    hire_case = {
        "id": _new_id(),
        "employee_name": "신입 A",
        "process_type": "입사",
        "target_date": (d + timedelta(days=7)).isoformat(),
        "department": "인사팀",
        "site_name": "서울 강남 본사",
        "status": "진행중",
        "note": "",
        "created_at": _today(),
        "created_by": "",
        "manager_user_id": "",
        "hr_user_id": "",
        "payroll_user_id": "",
    }
    ob_notify.resolve_case_assignees(tid, hire_case)
    hire_case["tasks"] = _build_tasks_from_template("입사", hire_case["target_date"], tid, hire_case)
    _calc_case_progress(hire_case)
    if hire_case.get("tasks"):
        hire_case["tasks"][0]["status"] = "완료"
        hire_case["tasks"][0]["completed_at"] = _today()

    resign_case = {
        "id": _new_id(),
        "employee_name": "퇴사 예정 B",
        "process_type": "퇴사",
        "target_date": (d + timedelta(days=14)).isoformat(),
        "department": "영업",
        "site_name": "부산 AMKR 현장",
        "status": "예정",
        "note": "",
        "created_at": _today(),
        "created_by": "",
        "manager_user_id": "",
        "hr_user_id": "",
        "payroll_user_id": "",
    }
    ob_notify.resolve_case_assignees(tid, resign_case)
    resign_case["tasks"] = _build_tasks_from_template("퇴사", resign_case["target_date"], tid, resign_case)
    _calc_case_progress(resign_case)
    db["onboarding"] = [hire_case, resign_case]
    db["seeded"] = True
    save_module_db(MODULE, tid, db)


def _db() -> dict[str, Any]:
    ensure_seed()
    tid = _tid()
    db = load_module_db(MODULE, tid, _EMPTY)
    _ensure_onboarding_ready(db, tid)
    return db


def list_onboarding_cases() -> list[dict[str, Any]]:
    db = _db()
    sync_overdue_reminders()
    return list(db.get("onboarding") or [])


def get_onboarding_case(case_id: str) -> dict[str, Any] | None:
    for case in list_onboarding_cases():
        if str(case.get("id")) == str(case_id):
            return case
    return None


def onboarding_summary_row(case: dict[str, Any]) -> dict[str, Any]:
    """목록용 요약 행."""
    tasks = list(case.get("tasks") or [])
    critical_pending = sum(
        1 for t in tasks if t.get("critical") and t.get("status") != "완료"
    )
    return {
        "id": case.get("id"),
        "employee_name": case.get("employee_name"),
        "process_type": case.get("process_type"),
        "target_date": case.get("target_date"),
        "department": case.get("department"),
        "site_name": case.get("site_name"),
        "progress": f"{case.get('progress_pct', 0)}%",
        "tasks_summary": f"{case.get('tasks_done', 0)}/{case.get('tasks_total', 0)}",
        "overdue_count": case.get("overdue_count", 0),
        "critical_pending": critical_pending,
        "status": case.get("status"),
    }


def create_onboarding_case(values: dict[str, str]) -> dict[str, Any]:
    tid = _tid()
    sess = get_session()
    actor = sess.user_id if sess else ""

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        pt = str(values.get("process_type") or "입사").strip()
        if pt not in ("입사", "퇴사"):
            pt = "입사" if "입" in pt else "퇴사"
        target = str(values.get("target_date") or _today())[:10]
        case: dict[str, Any] = {
            "id": _new_id(),
            "employee_name": str(values.get("employee_name") or "").strip(),
            "process_type": pt,
            "target_date": target,
            "department": str(values.get("department") or "").strip(),
            "site_name": str(values.get("site_name") or "").strip(),
            "resident_rrn": str(values.get("resident_rrn") or "").strip(),
            "status": str(values.get("status") or "진행중"),
            "note": str(values.get("note") or "").strip(),
            "created_at": _today(),
            "created_by": actor,
            "manager_user_id": str(values.get("manager_user_id") or ""),
            "hr_user_id": "",
            "payroll_user_id": "",
        }
        ob_notify.resolve_case_assignees(tid, case)
        case["tasks"] = _build_tasks_from_template(pt, target, tid, case)
        hr_signal.attach_signal_to_case(case, tid)
        _calc_case_progress(case)
        db.setdefault("onboarding", []).append(case)
        return case

    case = mutate_module_db(MODULE, tid, _EMPTY, mut)
    ob_notify.notify_case_created(tid, case, actor_user_id=actor)
    return case


def _apply_roster_sync(case: dict[str, Any], completed_task: dict[str, Any] | None) -> dict[str, Any] | None:
    """명부 반영 — roster 단계 완료 또는 케이스 전체 완료 시."""
    tid = _tid()
    if case.get("roster_synced"):
        return {"action": "skipped", "message": "이미 명부에 반영됨"}

    result: dict[str, Any] | None = None
    if completed_task:
        result = hr_roster_sync.sync_roster_for_task(case, completed_task)

    if result is None and case.get("status") == "완료":
        result = hr_roster_sync.ensure_case_roster_sync(case)

    if result and result.get("action") in ("created", "updated"):
        hr_roster_sync.mark_case_roster_synced(case, result)
        _sync_traffic_signal_employment(case, tid)
    elif result and result.get("action") == "not_found":
        case["roster_sync_pending"] = True
        case["roster_sync_message"] = result.get("message", "")

    return result


def _sync_traffic_signal_employment(case: dict[str, Any], tenant_id: str) -> None:
    key = hr_signal.resolve_rrn_for_case(case, tenant_id)
    if not key:
        return
    name = str(case.get("employee_name") or "")
    dept = str(case.get("department") or "")
    site = str(case.get("site_name") or "")
    target = str(case.get("target_date") or "")[:10]
    if case.get("process_type") == "입사":
        hr_signal.record_hire_event(
            rrn=key,
            tenant_id=tenant_id,
            employee_name=name,
            hire_date=target,
            department=dept,
            site_name=site,
        )
    elif case.get("process_type") == "퇴사":
        hr_signal.record_resign_event(
            rrn=key,
            tenant_id=tenant_id,
            employee_name=name,
            resign_date=target,
            department=dept,
            site_name=site,
        )


def register_case_resign_signal(
    case_id: str,
    *,
    severity: str,
    category: str,
    summary: str,
) -> tuple[dict[str, Any] | None, SignalProfile | None]:
    """퇴사 케이스 신호등 등록 후 케이스에 반영."""
    tid = _tid()
    case = get_onboarding_case(case_id)
    if not case:
        raise ValueError("케이스를 찾을 수 없습니다.")
    key = hr_signal.resolve_rrn_for_case(case, tid)
    if not key:
        raise ValueError("주민등록번호가 없습니다. 입·퇴사 등록 시 입력하거나 명부에 주민번호를 등록하세요.")
    prof = hr_signal.register_resign_signal(
        rrn=key,
        tenant_id=tid,
        employee_name=str(case.get("employee_name") or ""),
        severity=severity,  # type: ignore[arg-type]
        category=category,
        summary=summary,
        case_id=str(case.get("id") or ""),
        resign_date=str(case.get("target_date") or "")[:10],
        department=str(case.get("department") or ""),
        site_name=str(case.get("site_name") or ""),
    )

    def mut(db: dict[str, Any]) -> dict[str, Any] | None:
        for c in db.get("onboarding") or []:
            if str(c.get("id")) != str(case_id):
                continue
            c["signal_snapshot"] = {
                "status": prof.status if prof else severity,
                "status_label": prof.status_label if prof else severity,
                "rrn_masked": prof.rrn_masked if prof else "",
                "issue_count": len(prof.issues) if prof else 1,
                "found": True,
                "registered_at": _today(),
            }
            c["resident_rrn"] = key
            return c
        return None

    updated = mutate_module_db(MODULE, tid, _EMPTY, mut)
    return updated, prof


def lookup_signal_for_rrn(rrn: str) -> SignalProfile | None:
    return hr_signal.lookup_by_rrn(rrn)


def signal_summary_for_case(case: dict[str, Any]) -> str:
    return hr_signal.format_signal_for_case(case)


def update_case_resident_rrn(case_id: str, rrn: str) -> dict[str, Any] | None:
    """입·퇴사 케이스에 주민번호를 추가하고 신호등을 다시 조회합니다."""
    tid = _tid()
    key, err = hr_signal.validate_rrn_input(rrn)
    if err or not key:
        raise ValueError(err or "주민등록번호가 필요합니다.")

    def mut(db: dict[str, Any]) -> dict[str, Any] | None:
        for c in db.get("onboarding") or []:
            if str(c.get("id")) != str(case_id):
                continue
            c["resident_rrn"] = key
            hr_signal.attach_signal_to_case(c, tid)
            return c
        return None

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def complete_onboarding_task(
    case_id: str, task_id: str, *, note: str = ""
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    tid = _tid()
    sync_result: dict[str, Any] | None = None
    completed_task: dict[str, Any] | None = None

    def mut(db: dict[str, Any]) -> dict[str, Any] | None:
        nonlocal completed_task, sync_result
        for case in db.get("onboarding") or []:
            if str(case.get("id")) != str(case_id):
                continue
            for task in case.get("tasks") or []:
                if str(task.get("id")) != str(task_id):
                    continue
                task["status"] = "완료"
                task["completed_at"] = _today()
                if note:
                    task["note"] = note.strip()
                completed_task = dict(task)
            _calc_case_progress(case)
            if case.get("status") == "완료":
                ob_notify.notify_case_completed(tid, case)
            sync_result = _apply_roster_sync(case, completed_task)
            return case
        return None

    case = mutate_module_db(MODULE, tid, _EMPTY, mut)
    return case, sync_result


def sync_overdue_reminders() -> int:
    """지연 항목 알림 (1회)."""
    tid = _tid()

    def mut(db: dict[str, Any]) -> int:
        count = 0
        for case in db.get("onboarding") or []:
            _calc_case_progress(case)
            for task in case.get("tasks") or []:
                if task.get("status") != "지연":
                    continue
                if task.get("reminder_sent"):
                    continue
                ob_notify.notify_task_overdue(tid, case, task)
                task["reminder_sent"] = True
                count += 1
        return count

    return mutate_module_db(MODULE, tid, _EMPTY, mut)


def dashboard_kpis() -> list[tuple[str, str, str]]:
    ensure_seed()
    db = load_module_db(MODULE, _tid(), _EMPTY)
    pending_leave = sum(1 for r in db.get("leave_records") or [] if r.get("status") in ("대기", "신청"))
    active_contracts = sum(1 for r in db.get("contracts") or [] if r.get("status") == "유효")
    open_labor = sum(1 for r in db.get("labor_cases") or [] if r.get("status") != "종결")
    onboarding = sum(1 for r in db.get("onboarding") or [] if r.get("status") in ("진행중", "예정", "지연"))
    overdue = sum(int(r.get("overdue_count") or 0) for r in db.get("onboarding") or [])
    return [
        ("연차·휴가", str(len(db.get("leave_records") or [])), f"대기 {pending_leave}건"),
        ("근로계약", str(active_contracts), "유효 계약"),
        ("노무·징계", str(len(db.get("labor_cases") or [])), f"진행 {open_labor}건"),
        ("입·퇴사", str(len(db.get("onboarding") or [])), f"진행 {onboarding} · 지연 {overdue}"),
    ]


def list_records(tab_id: str) -> list[dict[str, Any]]:
    ensure_seed()
    if tab_id == "onboarding":
        return [onboarding_summary_row(c) for c in list_onboarding_cases()]
    db = load_module_db(MODULE, _tid(), _EMPTY)
    key = _tab_key(tab_id)
    return list(db.get(key) or [])


def _tab_key(tab_id: str) -> str:
    mapping = {
        "leave": "leave_records",
        "attendance": "attendance",
        "contracts": "contracts",
        "certificates": "certificates",
        "labor": "labor_cases",
        "onboarding": "onboarding",
    }
    if tab_id not in mapping:
        raise ValueError(f"알 수 없는 탭: {tab_id}")
    return mapping[tab_id]


def tab_columns(tab_id: str) -> tuple[tuple[str, str, int], ...]:
    specs: dict[str, tuple[tuple[str, str, int], ...]] = {
        "leave": (
            ("employee_name", "성명", 80),
            ("leave_type", "유형", 70),
            ("start_date", "시작", 90),
            ("end_date", "종료", 90),
            ("days", "일수", 50),
            ("status", "상태", 60),
            ("balance_after", "잔여", 50),
        ),
        "attendance": (
            ("employee_name", "성명", 80),
            ("date", "일자", 90),
            ("type", "구분", 70),
            ("minutes", "분", 50),
            ("status", "상태", 60),
            ("note", "비고", 160),
        ),
        "contracts": (
            ("employee_name", "성명", 80),
            ("contract_type", "유형", 70),
            ("job_group", "직군", 60),
            ("pay_type", "급여형태", 70),
            ("monthly_fixed_hours", "월고정(h)", 70),
            ("fixed_overtime_hours", "특근(h)", 60),
            ("fixed_extension_hours", "연장(h)", 60),
            ("department", "부서", 90),
            ("start_date", "시작", 90),
            ("status", "상태", 60),
        ),
        "certificates": (
            ("employee_name", "성명", 80),
            ("cert_type", "증명서", 100),
            ("request_date", "신청일", 90),
            ("issue_date", "발급일", 90),
            ("purpose", "용도", 120),
            ("status", "상태", 70),
        ),
        "labor": (
            ("employee_name", "성명", 80),
            ("case_type", "유형", 70),
            ("occurred_date", "발생일", 90),
            ("summary", "요약", 140),
            ("action", "조치", 100),
            ("status", "상태", 60),
        ),
        "onboarding": (
            ("employee_name", "성명", 80),
            ("process_type", "구분", 50),
            ("target_date", "예정일", 88),
            ("department", "부서", 80),
            ("progress", "진행", 50),
            ("tasks_summary", "체크", 50),
            ("overdue_count", "지연", 40),
            ("status", "상태", 60),
        ),
    }
    return specs.get(tab_id, (("id", "ID", 80),))


def form_fields(tab_id: str) -> tuple[tuple[str, str, bool], ...]:
    forms: dict[str, tuple[tuple[str, str, bool], ...]] = {
        "leave": (
            ("employee_name", "성명", True),
            ("leave_type", "유형(연차/반차/병가 등)", True),
            ("start_date", "시작일", True),
            ("end_date", "종료일", True),
            ("days", "일수", True),
            ("status", "상태", False),
            ("note", "비고", False),
        ),
        "attendance": (
            ("employee_name", "성명", True),
            ("date", "일자", True),
            ("type", "구분(출장/지각/조퇴 등)", True),
            ("minutes", "시간(분)", False),
            ("status", "상태", False),
            ("note", "비고", False),
        ),
        "contracts": (
            ("employee_name", "성명", True),
            ("contract_type", "계약유형", True),
            ("job_group", "직군(경비/미화/관리)", False),
            ("site_name", "사업장", False),
            ("pay_type", "급여형태(hourly/monthly_salary)", False),
            ("fixed_hours_mode", "고정근로시간(예/아니오)", False),
            ("monthly_fixed_hours", "월 고정근로시간", False),
            ("fixed_overtime_hours", "고정 특근시간", False),
            ("fixed_extension_hours", "고정 연장시간", False),
            ("department", "부서", True),
            ("position", "직위", False),
            ("start_date", "시작일", True),
            ("end_date", "종료일", False),
            ("status", "상태", False),
        ),
        "certificates": (
            ("employee_name", "성명", True),
            ("cert_type", "증명서 종류", True),
            ("request_date", "신청일", True),
            ("purpose", "용도", True),
            ("status", "상태", False),
        ),
        "labor": (
            ("employee_name", "성명", True),
            ("case_type", "유형(경고/견책/상담)", True),
            ("occurred_date", "발생일", True),
            ("summary", "요약", True),
            ("action", "조치", False),
            ("status", "상태", False),
        ),
        "onboarding": (
            ("employee_name", "성명", True),
            ("process_type", "입사 또는 퇴사", True),
            ("target_date", "예정일(YYYY-MM-DD)", True),
            ("resident_rrn", "주민등록번호(13자리)", False),
            ("department", "부서", True),
            ("site_name", "사업장", False),
            ("note", "비고", False),
        ),
    }
    return forms.get(tab_id, (("note", "내용", True),))


def add_record(tab_id: str, values: dict[str, str]) -> dict[str, Any]:
    ensure_seed()
    if tab_id == "onboarding":
        return create_onboarding_case(values)
    key = _tab_key(tab_id)

    def mut(db: dict[str, Any]) -> dict[str, Any]:
        row = {"id": _new_id(), **values}
        if tab_id == "leave" and not row.get("status"):
            row["status"] = "신청"
        if tab_id == "contracts":
            if not row.get("status"):
                row["status"] = "유효"
            from core.payroll.fixed_hours import normalize_contract_fixed_hours_fields

            normalize_contract_fixed_hours_fields(row)
        if tab_id == "certificates":
            row.setdefault("request_date", _today())
            row.setdefault("status", "대기")
        if tab_id == "attendance" and not row.get("status"):
            row["status"] = "확인"
        if tab_id == "labor" and not row.get("status"):
            row["status"] = "진행"
        db.setdefault(key, []).append(row)
        return row

    return mutate_module_db(MODULE, _tid(), _EMPTY, mut)
