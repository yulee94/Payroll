"""
employment_succession.py - 계열사 간 고용승계·최초입사일·퇴직금 정산 이력

고용승계이력(JSON) 예:
[
  {"계열사": "A법인", "일자": "2010.01.15", "구분": "최초입사", "퇴직금정산": null},
  {"계열사": "B법인", "일자": "2018.06.01", "구분": "승계", "퇴직금정산": true}
]
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from annual_leave_accrual import parse_hire_date
from senior_internship import parse_roster_date_input

KIND_INITIAL = "최초입사"
KIND_SUCCESSION = "승계"

_DATE_PLACEHOLDER = "0000.00.00"


@dataclass
class SuccessionStep:
    affiliate: str
    date: str
    kind: str = KIND_INITIAL
    severance_settled: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "계열사": self.affiliate,
            "일자": self.date,
            "구분": self.kind,
            "퇴직금정산": self.severance_settled,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SuccessionStep | None:
        if not isinstance(raw, dict):
            return None
        aff = str(raw.get("계열사") or raw.get("affiliate") or "").strip()
        date_s = format_succession_date(raw.get("일자") or raw.get("date"))
        if not aff and not date_s:
            return None
        kind_raw = str(raw.get("구분") or raw.get("kind") or KIND_INITIAL).strip()
        kind = KIND_SUCCESSION if kind_raw in (KIND_SUCCESSION, "승계", "이동") else KIND_INITIAL
        sev = _parse_severance_flag(raw.get("퇴직금정산") if "퇴직금정산" in raw else raw.get("severance_settled"))
        return cls(affiliate=aff, date=date_s or _DATE_PLACEHOLDER, kind=kind, severance_settled=sev)


def format_succession_date(value: Any) -> str:
    if value is None or str(value).strip() == "":
        return _DATE_PLACEHOLDER
    parsed = parse_roster_date_input(str(value))
    if parsed:
        return parsed
    d = parse_hire_date(value)
    if d is None:
        t = str(value).strip()
        return t if t else _DATE_PLACEHOLDER
    return f"{d.year:04d}.{d.month:02d}.{d.day:02d}"


def _parse_severance_flag(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().upper()
    if text in ("Y", "YES", "O", "○", "정산", "완료", "TRUE", "1"):
        return True
    if text in ("N", "NO", "X", "×", "미정산", "FALSE", "0"):
        return False
    return None


def severance_display(flag: bool | None) -> str:
    if flag is True:
        return "O"
    if flag is False:
        return "X"
    return "—"


def parse_succession_history(rec: dict[str, Any]) -> list[SuccessionStep]:
    """명부 레코드 → 승계 단계 목록 (이력 없으면 입사일·계열사로 1단계 추정)."""
    raw = rec.get("고용승계이력")
    steps: list[SuccessionStep] = []

    if isinstance(raw, list):
        for item in raw:
            step = SuccessionStep.from_dict(item) if isinstance(item, dict) else None
            if step and (step.affiliate or step.date != _DATE_PLACEHOLDER):
                steps.append(step)
    elif isinstance(raw, str) and raw.strip():
        text = raw.strip()
        if text.startswith("["):
            try:
                data = json.loads(text)
                if isinstance(data, list):
                    for item in data:
                        step = SuccessionStep.from_dict(item) if isinstance(item, dict) else None
                        if step and (step.affiliate or step.date != _DATE_PLACEHOLDER):
                            steps.append(step)
            except json.JSONDecodeError:
                pass
        if not steps:
            steps = _parse_legacy_path_text(text)

    if not steps:
        aff = str(rec.get("계열사") or "").strip()
        hire = format_succession_date(rec.get("입사일") or rec.get("최초입사일"))
        if aff or hire != _DATE_PLACEHOLDER:
            steps.append(
                SuccessionStep(
                    affiliate=aff,
                    date=hire,
                    kind=KIND_INITIAL,
                    severance_settled=None,
                )
            )

    if steps and steps[0].kind != KIND_INITIAL:
        steps[0].kind = KIND_INITIAL
        steps[0].severance_settled = None

    return steps


def _parse_legacy_path_text(text: str) -> list[SuccessionStep]:
    """구분자 경로 텍스트: A|2010.01.01|최초;B|2018.06.01|승계|Y"""
    steps: list[SuccessionStep] = []
    for chunk in re.split(r"[;；\n]+", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [p.strip() for p in re.split(r"[|｜]", chunk)]
        if len(parts) < 2:
            continue
        aff = parts[0]
        date_s = format_succession_date(parts[1])
        kind = KIND_SUCCESSION if len(parts) > 2 and parts[2] in (KIND_SUCCESSION, "승계") else KIND_INITIAL
        sev = _parse_severance_flag(parts[3]) if len(parts) > 3 else None
        steps.append(SuccessionStep(affiliate=aff, date=date_s, kind=kind, severance_settled=sev))
    return steps


def serialize_succession_history(steps: list[SuccessionStep]) -> str:
    payload = [s.to_dict() for s in steps]
    return json.dumps(payload, ensure_ascii=False)


def group_first_hire_date(rec: dict[str, Any]) -> str:
    """그룹 최초 입사일 (YYYY.MM.DD)."""
    explicit = rec.get("최초입사일")
    if explicit is not None and str(explicit).strip():
        return format_succession_date(explicit)
    steps = parse_succession_history(rec)
    if steps:
        return steps[0].date
    return format_succession_date(rec.get("입사일"))


def format_step_segment(step: SuccessionStep, *, index: int) -> str:
    aff = step.affiliate or "(계열사미입력)"
    if step.kind == KIND_INITIAL or index == 0:
        return f"{aff} 최초입사일 {step.date}"
    sev = severance_display(step.severance_settled)
    return f"{aff} 승계일 {step.date} (퇴직금정산 {sev})"


def format_succession_path(rec: dict[str, Any]) -> str:
    steps = parse_succession_history(rec)
    if not steps:
        return ""
    if len(steps) == 1 and steps[0].kind == KIND_INITIAL:
        return format_step_segment(steps[0], index=0)
    return " → ".join(format_step_segment(s, index=i) for i, s in enumerate(steps))


def current_affiliate_succession_date(rec: dict[str, Any]) -> str:
    """현재 계열사 기준 승계일·입사일."""
    current = str(rec.get("계열사") or "").strip()
    steps = parse_succession_history(rec)
    if current:
        for step in reversed(steps):
            if step.affiliate == current:
                return step.date
    if steps:
        return steps[-1].date
    return format_succession_date(rec.get("입사일"))


def apply_succession_to_record(rec: dict[str, Any]) -> None:
    steps = parse_succession_history(rec)
    if steps:
        rec["고용승계이력"] = serialize_succession_history(steps)
        rec["최초입사일"] = steps[0].date
    rec["_group_first_hire_display"] = group_first_hire_date(rec)
    rec["_succession_path_display"] = format_succession_path(rec)
    rec["_current_succession_date"] = current_affiliate_succession_date(rec)


def save_succession_steps(rec: dict[str, Any], steps: list[SuccessionStep]) -> None:
    if not steps:
        rec.pop("고용승계이력", None)
        rec.pop("최초입사일", None)
    else:
        if steps[0].kind != KIND_INITIAL:
            steps[0].kind = KIND_INITIAL
            steps[0].severance_settled = None
        for i, step in enumerate(steps):
            if i > 0 and step.kind != KIND_SUCCESSION:
                step.kind = KIND_SUCCESSION
            if i == 0:
                step.severance_settled = None
        rec["고용승계이력"] = serialize_succession_history(steps)
        rec["최초입사일"] = steps[0].date
    apply_succession_to_record(rec)


def continuous_hire_date_for_leave(rec: dict[str, Any]):
    """연차 산정용 — 최초입사일(그룹) 우선."""
    d = parse_hire_date(rec.get("최초입사일"))
    if d is not None:
        return d
    steps = parse_succession_history(rec)
    if steps:
        return parse_hire_date(steps[0].date)
    return parse_hire_date(rec.get("입사일"))
