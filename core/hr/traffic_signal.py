"""
core/hr/traffic_signal.py - Bitween 법인 간 HR 신호등 (주민등록번호 기준)

퇴사 후에도 레지스트리에 유지되어 타 법인(테넌트) 채용 시 참고합니다.
동명이인은 주민등록번호로만 매칭합니다.
"""

from __future__ import annotations

import json
import re
import threading
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from core.paths import app_data_dir
from core.tenant_store import get_tenant

SignalColor = Literal["green", "yellow", "red"]

_REGISTRY_PATH = app_data_dir() / "hr_signal" / "registry.json"
_lock = threading.Lock()

STATUS_LABELS: dict[str, str] = {
    "green": "양호",
    "yellow": "주의",
    "red": "위험",
}

SEVERITY_ORDER = {"red": 3, "yellow": 2, "green": 1}


@dataclass
class SignalIssue:
    id: str
    tenant_id: str
    tenant_name: str
    process_type: str
    category: str
    summary: str
    severity: SignalColor
    recorded_at: str
    case_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "process_type": self.process_type,
            "category": self.category,
            "summary": self.summary,
            "severity": self.severity,
            "recorded_at": self.recorded_at,
            "case_id": self.case_id,
        }


@dataclass
class EmploymentHistoryEntry:
    tenant_id: str
    tenant_name: str
    employee_name: str
    hire_date: str
    resign_date: str
    department: str
    site_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "employee_name": self.employee_name,
            "hire_date": self.hire_date,
            "resign_date": self.resign_date,
            "department": self.department,
            "site_name": self.site_name,
        }


@dataclass
class SignalProfile:
    rrn_key: str
    rrn_masked: str
    names: list[str]
    status: SignalColor
    status_label: str
    issues: list[SignalIssue] = field(default_factory=list)
    employment_history: list[EmploymentHistoryEntry] = field(default_factory=list)
    active_employment: bool = False
    updated_at: str = ""
    found: bool = True

    @property
    def display_emoji(self) -> str:
        return {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(self.status, "⚪")

    def summary_lines(self) -> list[str]:
        lines = [
            f"{self.display_emoji} 신호등: {self.status_label} ({self.rrn_masked})",
            f"등록 이름: {', '.join(self.names[:5]) or '-'}",
        ]
        if self.employment_history:
            last = self.employment_history[-1]
            lines.append(
                f"최근 재직: {last.tenant_name} · {last.employee_name} "
                f"({last.hire_date or '?'} ~ {last.resign_date or '재직'})"
            )
        if self.issues:
            lines.append(f"이력 {len(self.issues)}건 — 최근: {self.issues[-1].summary[:80]}")
        elif not self.found:
            lines.append("Bitween 신호등 레지스트리에 기록 없음 (최초 채용 또는 미등록)")
        return lines


def normalize_rrn(value: Any) -> str | None:
    """13자리 주민등록번호 숫자만 추출. 유효하지 않으면 None."""
    if value is None:
        return None
    digits = re.sub(r"[^\d]", "", str(value).strip())
    if len(digits) != 13:
        return None
    return digits


def mask_rrn(digits: str) -> str:
    d = normalize_rrn(digits) or digits
    if len(d) < 7:
        return "***"
    return f"{d[:6]}-{d[6:7]}******"


def validate_rrn_input(value: str) -> tuple[str | None, str | None]:
    key = normalize_rrn(value)
    if not key:
        return None, "주민등록번호 13자리를 입력하세요. (동명이인 구분용)"
    return key, None


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _empty_registry() -> dict[str, Any]:
    return {"version": 1, "persons": {}}


def _load_registry() -> dict[str, Any]:
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _REGISTRY_PATH.is_file():
        return _empty_registry()
    try:
        raw = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw.setdefault("persons", {})
            return raw
    except (OSError, json.JSONDecodeError):
        pass
    return _empty_registry()


def _save_registry(data: dict[str, Any]) -> None:
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _tenant_display(tenant_id: str) -> str:
    t = get_tenant(tenant_id)
    if t:
        return t.display_name_ko or t.display_name or tenant_id
    return tenant_id


def _worst_status(severities: list[SignalColor]) -> SignalColor:
    if not severities:
        return "green"
    return max(severities, key=lambda s: SEVERITY_ORDER.get(s, 0))


def _parse_profile(key: str, raw: dict[str, Any]) -> SignalProfile:
    issues = [
        SignalIssue(
            id=str(i.get("id") or ""),
            tenant_id=str(i.get("tenant_id") or ""),
            tenant_name=str(i.get("tenant_name") or ""),
            process_type=str(i.get("process_type") or ""),
            category=str(i.get("category") or ""),
            summary=str(i.get("summary") or ""),
            severity=str(i.get("severity") or "yellow"),  # type: ignore[arg-type]
            recorded_at=str(i.get("recorded_at") or ""),
            case_id=str(i.get("case_id") or ""),
        )
        for i in raw.get("issues") or []
        if isinstance(i, dict)
    ]
    history = [
        EmploymentHistoryEntry(
            tenant_id=str(h.get("tenant_id") or ""),
            tenant_name=str(h.get("tenant_name") or ""),
            employee_name=str(h.get("employee_name") or ""),
            hire_date=str(h.get("hire_date") or ""),
            resign_date=str(h.get("resign_date") or ""),
            department=str(h.get("department") or ""),
            site_name=str(h.get("site_name") or ""),
        )
        for h in raw.get("employment_history") or []
        if isinstance(h, dict)
    ]
    status = str(raw.get("status") or "green")
    if status not in STATUS_LABELS:
        status = _worst_status([i.severity for i in issues] or ["green"])
    return SignalProfile(
        rrn_key=key,
        rrn_masked=str(raw.get("rrn_masked") or mask_rrn(key)),
        names=list(raw.get("names") or []),
        status=status,  # type: ignore[arg-type]
        status_label=STATUS_LABELS.get(status, status),
        issues=issues,
        employment_history=history,
        active_employment=bool(raw.get("active_employment")),
        updated_at=str(raw.get("updated_at") or ""),
        found=True,
    )


def lookup_by_rrn(rrn: Any) -> SignalProfile | None:
    key, err = validate_rrn_input(str(rrn or ""))
    if err or not key:
        return None
    with _lock:
        reg = _load_registry()
        raw = (reg.get("persons") or {}).get(key)
    if not isinstance(raw, dict):
        return SignalProfile(
            rrn_key=key,
            rrn_masked=mask_rrn(key),
            names=[],
            status="green",
            status_label="기록 없음",
            found=False,
        )
    return _parse_profile(key, raw)


def lookup_for_hire(*, rrn: Any, employee_name: str = "") -> SignalProfile | None:
    """입사 전 조회 — 없으면 green/기록 없음 프로필 반환."""
    prof = lookup_by_rrn(rrn)
    if prof is None:
        return None
    name = str(employee_name or "").strip()
    if name and prof.found and name not in prof.names:
        prof = deepcopy(prof)
        prof.summary_lines  # keep dataclass
        # 이름 불일치 경고는 UI에서 — 동명이인은 RRN이 기준
    return prof


def find_rrn_for_employee_name(employee_name: str, *, tenant_id: str) -> str | None:
    """명부에서 성명으로 주민번호 찾기 (동명이인이면 None)."""
    name = str(employee_name or "").strip()
    if not name:
        return None
    try:
        from core.access_control import load_roster_rows_secured

        rows = load_roster_rows_secured(tenant_id=tenant_id)
    except Exception:
        return None
    matched: list[str] = []
    for row in rows:
        rn = str(row.get("성명") or row.get("name") or "").strip()
        if rn != name:
            continue
        key = normalize_rrn(row.get("주민번호"))
        if key:
            matched.append(key)
    unique = list(dict.fromkeys(matched))
    if len(unique) == 1:
        return unique[0]
    return None


def resolve_rrn_for_case(case: dict[str, Any], tenant_id: str) -> str | None:
    explicit = normalize_rrn(case.get("resident_rrn"))
    if explicit:
        return explicit
    return find_rrn_for_employee_name(str(case.get("employee_name") or ""), tenant_id=tenant_id)


def _ensure_person(reg: dict[str, Any], key: str) -> dict[str, Any]:
    persons: dict[str, Any] = reg.setdefault("persons", {})
    if key not in persons:
        persons[key] = {
            "rrn_masked": mask_rrn(key),
            "names": [],
            "status": "green",
            "issues": [],
            "employment_history": [],
            "active_employment": False,
            "updated_at": _now_iso(),
        }
    return persons[key]


def _add_name(person: dict[str, Any], name: str) -> None:
    n = str(name or "").strip()
    if not n:
        return
    names: list[str] = list(person.get("names") or [])
    if n not in names:
        names.append(n)
    person["names"] = names[-10:]


def record_hire_event(
    *,
    rrn: Any,
    tenant_id: str,
    employee_name: str,
    hire_date: str,
    department: str = "",
    site_name: str = "",
) -> SignalProfile | None:
    key, err = validate_rrn_input(str(rrn or ""))
    if err or not key:
        return None
    tname = _tenant_display(tenant_id)
    with _lock:
        reg = _load_registry()
        person = _ensure_person(reg, key)
        _add_name(person, employee_name)
        history: list[dict[str, Any]] = list(person.get("employment_history") or [])
        history.append(
            {
                "tenant_id": tenant_id,
                "tenant_name": tname,
                "employee_name": employee_name,
                "hire_date": str(hire_date or "")[:10],
                "resign_date": "",
                "department": department,
                "site_name": site_name,
            }
        )
        person["employment_history"] = history[-20:]
        person["active_employment"] = True
        person["updated_at"] = _now_iso()
        _save_registry(reg)
    return _parse_profile(key, person)


def record_resign_event(
    *,
    rrn: Any,
    tenant_id: str,
    employee_name: str,
    resign_date: str,
    department: str = "",
    site_name: str = "",
) -> SignalProfile | None:
    key, err = validate_rrn_input(str(rrn or ""))
    if err or not key:
        return None
    with _lock:
        reg = _load_registry()
        person = _ensure_person(reg, key)
        _add_name(person, employee_name)
        history: list[dict[str, Any]] = list(person.get("employment_history") or [])
        updated = False
        for entry in reversed(history):
            if entry.get("tenant_id") == tenant_id and not entry.get("resign_date"):
                entry["resign_date"] = str(resign_date or "")[:10]
                entry["employee_name"] = employee_name or entry.get("employee_name", "")
                updated = True
                break
        if not updated:
            history.append(
                {
                    "tenant_id": tenant_id,
                    "tenant_name": _tenant_display(tenant_id),
                    "employee_name": employee_name,
                    "hire_date": "",
                    "resign_date": str(resign_date or "")[:10],
                    "department": department,
                    "site_name": site_name,
                }
            )
        person["employment_history"] = history[-20:]
        person["active_employment"] = False
        person["updated_at"] = _now_iso()
        _save_registry(reg)
    return _parse_profile(key, person)


def register_resign_signal(
    *,
    rrn: Any,
    tenant_id: str,
    employee_name: str,
    severity: SignalColor,
    category: str,
    summary: str,
    case_id: str = "",
    resign_date: str = "",
    department: str = "",
    site_name: str = "",
) -> SignalProfile | None:
    """퇴사 시 신호등 등록 — 타 법인 공유용."""
    key, err = validate_rrn_input(str(rrn or ""))
    if err or not key:
        raise ValueError(err or "주민등록번호가 필요합니다.")
    if severity not in STATUS_LABELS:
        raise ValueError("신호등은 green/yellow/red 중 하나여야 합니다.")
    summary = str(summary or "").strip()
    if not summary:
        raise ValueError("판정 사유를 입력하세요.")

    tname = _tenant_display(tenant_id)
    issue = {
        "id": uuid.uuid4().hex[:12],
        "tenant_id": tenant_id,
        "tenant_name": tname,
        "process_type": "퇴사",
        "category": str(category or "퇴사").strip(),
        "summary": summary,
        "severity": severity,
        "recorded_at": _now_iso()[:10],
        "case_id": case_id,
    }

    with _lock:
        reg = _load_registry()
        person = _ensure_person(reg, key)
        _add_name(person, employee_name)
        issues: list[dict[str, Any]] = list(person.get("issues") or [])
        issues.append(issue)
        person["issues"] = issues[-30:]
        person["status"] = _worst_status([str(i.get("severity") or "green") for i in issues])  # type: ignore[arg-type]
        person["updated_at"] = _now_iso()
        if resign_date:
            history: list[dict[str, Any]] = list(person.get("employment_history") or [])
            for entry in reversed(history):
                if entry.get("tenant_id") == tenant_id and not entry.get("resign_date"):
                    entry["resign_date"] = resign_date[:10]
                    break
            person["employment_history"] = history
        person["active_employment"] = False
        _save_registry(reg)
    return _parse_profile(key, person)


def attach_signal_to_case(case: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    """입·퇴사 케이스 생성 시 신호등 스냅샷 부착."""
    key = resolve_rrn_for_case(case, tenant_id)
    snapshot: dict[str, Any] = {"rrn_key": key or "", "checked_at": _now_iso()}
    if key:
        prof = lookup_by_rrn(key)
        if prof:
            snapshot.update(
                {
                    "status": prof.status,
                    "status_label": prof.status_label,
                    "rrn_masked": prof.rrn_masked,
                    "issue_count": len(prof.issues),
                    "found": prof.found,
                    "summary": prof.issues[-1].summary if prof.issues else "",
                }
            )
        case["resident_rrn"] = key
    else:
        snapshot["status"] = "unknown"
        snapshot["status_label"] = "주민번호 미확인"
        snapshot["rrn_masked"] = ""
    case["signal_snapshot"] = snapshot
    return case


def format_signal_for_case(case: dict[str, Any]) -> str:
    snap = case.get("signal_snapshot") or {}
    if not snap:
        return ""
    emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴", "unknown": "⚪"}.get(
        str(snap.get("status") or "unknown"), "⚪"
    )
    label = snap.get("status_label") or "미조회"
    masked = snap.get("rrn_masked") or ""
    line = f"{emoji} Bitween 신호등: {label}"
    if masked:
        line += f" ({masked})"
    if snap.get("issue_count"):
        line += f" · 이력 {snap['issue_count']}건"
    if snap.get("summary"):
        line += f"\n   └ {snap['summary']}"
    if snap.get("status") == "unknown":
        line += "\n   └ 주민등록번호를 입력하거나 명부에 등록 후 다시 조회하세요."
    return line
