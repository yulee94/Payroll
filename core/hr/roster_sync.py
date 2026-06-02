"""
core/hr/roster_sync.py - 입·퇴사 절차 → 근로자 명부 자동 반영
"""

from __future__ import annotations

from typing import Any

from core.access_control import load_roster_rows_secured
from core.session_service import get_session
from employment_type import TYPE_REGULAR_HOURLY
from roster_constants import norm_name_key
from senior_internship import parse_roster_date_input
from services.employee_roster_store import load_roster_rows, save_roster_rows

TASK_HIRE_ROSTER = "hire_roster"
TASK_RESIGN_ROSTER = "resign_roster"


def _load_rows() -> list[dict[str, Any]]:
    sess = get_session()
    if sess:
        return list(load_roster_rows_secured(session=sess))
    return load_roster_rows(force=True)


def _format_roster_date(iso_or_text: str) -> str:
    parsed = parse_roster_date_input(str(iso_or_text or ""))
    if parsed:
        return parsed
    raw = str(iso_or_text or "").strip()[:10]
    if len(raw) == 10 and raw[4] == "-":
        return f"{raw[:4]}.{raw[5:7]}.{raw[8:10]}"
    return raw


def _find_row_index(rows: list[dict[str, Any]], name: str) -> int | None:
    key = norm_name_key(name)
    if not key:
        return None
    for i, row in enumerate(rows):
        if norm_name_key(row.get("성명")) == key:
            return i
    return None


def apply_hire_to_roster(case: dict[str, Any]) -> dict[str, Any]:
    """입사 → 명부 신규 등록 또는 입사일·근무지 갱신."""
    name = str(case.get("employee_name") or "").strip()
    if not name:
        return {"action": "error", "message": "성명이 없습니다."}

    hire_date = _format_roster_date(str(case.get("target_date") or ""))
    dept = str(case.get("department") or "").strip()
    site = str(case.get("site_name") or "").strip()
    rows = _load_rows()
    idx = _find_row_index(rows, name)

    if idx is not None:
        row = rows[idx]
        row["입사일"] = hire_date
        if not str(row.get("최초입사일") or "").strip():
            row["최초입사일"] = hire_date
        if site:
            row["근무지"] = site
        elif dept:
            row["근무지"] = dept
        if dept:
            row["업무"] = dept
        row["퇴사일"] = ""
        action = "updated"
    else:
        rows.append(
            {
                "성명": name,
                "입사일": hire_date,
                "최초입사일": hire_date,
                "근무지": site or dept,
                "업무": dept,
                "고용형태": TYPE_REGULAR_HOURLY,
                "퇴사일": "",
                "비고": f"입·퇴사 절차 자동등록",
            }
        )
        action = "created"

    count = save_roster_rows(rows, note=f"입사 명부 반영: {name}")
    return {
        "action": action,
        "process_type": "입사",
        "employee_name": name,
        "hire_date": hire_date,
        "saved_count": count,
        "message": f"명부에 입사 정보가 반영되었습니다. ({name}, 입사일 {hire_date})",
    }


def apply_resign_to_roster(case: dict[str, Any]) -> dict[str, Any]:
    """퇴사 → 명부 퇴사일 반영."""
    name = str(case.get("employee_name") or "").strip()
    if not name:
        return {"action": "error", "message": "성명이 없습니다."}

    resign_date = _format_roster_date(str(case.get("target_date") or ""))
    rows = _load_rows()
    idx = _find_row_index(rows, name)
    if idx is None:
        return {
            "action": "not_found",
            "process_type": "퇴사",
            "employee_name": name,
            "message": f"명부에서 '{name}' 을(를) 찾을 수 없습니다. 명부에 등록 후 다시 시도하세요.",
        }

    row = rows[idx]
    row["퇴사일"] = resign_date
    note = str(row.get("비고") or "").strip()
    tag = f"퇴사({resign_date})"
    if tag not in note:
        row["비고"] = f"{note} {tag}".strip() if note else tag

    count = save_roster_rows(rows, note=f"퇴사 명부 반영: {name}")
    return {
        "action": "updated",
        "process_type": "퇴사",
        "employee_name": name,
        "resign_date": resign_date,
        "saved_count": count,
        "message": f"명부에 퇴사일이 반영되었습니다. ({name}, 퇴사일 {resign_date})",
    }


def sync_roster_for_task(case: dict[str, Any], task: dict[str, Any]) -> dict[str, Any] | None:
    code = str(task.get("code") or "")
    if code == TASK_HIRE_ROSTER:
        return apply_hire_to_roster(case)
    if code == TASK_RESIGN_ROSTER:
        return apply_resign_to_roster(case)
    return None


def ensure_case_roster_sync(case: dict[str, Any]) -> dict[str, Any] | None:
    """케이스 완료 시 명부 미반영이면 유형별 자동 반영."""
    if case.get("roster_synced"):
        return {"action": "skipped", "message": "이미 명부에 반영됨"}

    pt = str(case.get("process_type") or "")
    if pt == "입사":
        return apply_hire_to_roster(case)
    if pt == "퇴사":
        return apply_resign_to_roster(case)
    return None


def mark_case_roster_synced(case: dict[str, Any], result: dict[str, Any]) -> None:
    from datetime import date

    case["roster_synced"] = True
    case["roster_sync_at"] = date.today().isoformat()
    case["roster_sync_action"] = result.get("action")
    case["roster_sync_message"] = result.get("message", "")
