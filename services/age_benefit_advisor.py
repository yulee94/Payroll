"""
services/age_benefit_advisor.py - 명부 기반 연령별 혜택·국가지원 추천·확인 질문
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from core.access_control import load_roster_rows_secured
from core.session_service import UserSession, require_session
from core.tenant_data_scope import enforce_session_tenant_access
from insurance import is_insurance_exempt
from roster_constants import find_fuzzy_name_key, norm_name_key
from senior_internship import (
    classify_senior_internship_job,
    is_senior_internship_program_eligible,
    normalize_senior_internship_status,
    senior_internship_mark,
)
from services.korean_age_benefits import AgeBenefitProgram, programs_for_age
from services.payroll_ai_context import extract_person_name
from utils import age_years_at, parse_birth_date_from_korean_rrn

_BENEFIT_KEYWORDS = (
    "혜택",
    "지원",
    "지원사업",
    "국가지원",
    "정부지원",
    "법령",
    "고용법",
    "노동법",
    "4대보험",
    "면제",
    "시니어",
    "인턴십",
    "청년",
    "중장년",
    "고령",
    "65세",
    "60세",
    "만65",
    "만60",
    "연금",
    "장려금",
    "추천",
    "해당",
    "프로그램",
    "공제",
)

_DISCLAIMER = (
    "※ 아래는 한국 법령·정책을 참고한 안내이며, 최종 자격·신청은 "
    "고용노동부·국민연금공단·복지부·관할 지자체 공식 공고를 확인하세요."
)


@dataclass
class EmployeeBenefitMatch:
    name: str
    age: int
    dept: str
    programs: list[AgeBenefitProgram] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)


@dataclass
class AgeBenefitScanResult:
    as_of: date
    matches: list[EmployeeBenefitMatch] = field(default_factory=list)
    skipped_no_birth: int = 0

    @property
    def has_recommendations(self) -> bool:
        return bool(self.matches)


def is_benefit_related_question(text: str) -> bool:
    t = str(text or "").lower()
    return any(k in t for k in _BENEFIT_KEYWORDS)


def _employee_notes(rec: dict[str, Any], *, as_of: date) -> list[str]:
    notes: list[str] = []
    rrn = rec.get("주민번호")
    if is_insurance_exempt(rrn, as_of=as_of):
        notes.append("급여 산출: 만 65세 이상 → 4대보험 공제 0원 적용 대상")

    birth = parse_birth_date_from_korean_rrn(rrn, as_of=as_of)
    if birth and age_years_at(birth, as_of) >= 60:
        excluded, reason = classify_senior_internship_job(rec)
        if excluded:
            notes.append(f"시니어 인턴십: 단순노무 제외 ({reason or '직종'})")
        elif is_senior_internship_program_eligible(rec, as_of=as_of):
            mark = senior_internship_mark(rec, as_of=as_of)
            st = normalize_senior_internship_status(rec.get("시니어인턴십상태"))
            if st in ("", "O") or mark in ("O", ""):
                notes.append("시니어 인턴십: 지원·진행 검토 가능 (명부 O/△/X 관리)")
            elif st == "X":
                notes.append("시니어 인턴십: 지원 완료(X)로 기록됨")

    disability = str(rec.get("장애") or rec.get("중증장애") or "").strip()
    if disability and disability not in ("-", "0", "N", "아니오", "무"):
        notes.append("장애인 고용·지원 프로그램 검토 가능 (명부 장애 정보 있음)")

    return notes


def _collect_questions(programs: list[AgeBenefitProgram], notes: list[str]) -> list[str]:
    qs: list[str] = []
    seen: set[str] = set()
    for p in programs:
        for q in p.ask_questions:
            if q not in seen:
                seen.add(q)
                qs.append(q)
    if any("시니어" in n for n in notes):
        q = "시니어 인턴십 지원일·재직충족일을 명부에 입력하셨나요?"
        if q not in seen:
            qs.append(q)
    return qs[:6]


def scan_roster_age_benefits(
    tenant_id: str,
    *,
    session: UserSession | None = None,
    as_of: date | None = None,
    limit: int = 12,
) -> AgeBenefitScanResult:
    """근로자 명부를 스캔해 연령별 혜택·지원 대상을 찾습니다."""
    sess = enforce_session_tenant_access(session or require_session())
    as_of = as_of or date.today()
    rows = load_roster_rows_secured(session=sess)
    result = AgeBenefitScanResult(as_of=as_of)

    for rec in rows:
        rrn = rec.get("주민번호")
        birth = parse_birth_date_from_korean_rrn(rrn, as_of=as_of)
        if birth is None:
            result.skipped_no_birth += 1
            continue
        age = age_years_at(birth, as_of)
        programs = programs_for_age(age)
        if not programs:
            continue
        notes = _employee_notes(rec, as_of=as_of)
        if age >= 65 or age >= 60 or notes:
            match = EmployeeBenefitMatch(
                name=str(rec.get("성명") or rec.get("name") or "").strip(),
                age=age,
                dept=str(rec.get("부서") or rec.get("dept") or rec.get("근무지") or "").strip(),
                programs=programs,
                notes=notes,
                questions=_collect_questions(programs, notes),
            )
            result.matches.append(match)

    result.matches.sort(key=lambda m: (-m.age, m.name))
    if limit > 0:
        result.matches = result.matches[:limit]
    return result


def format_benefit_context_block(scan: AgeBenefitScanResult) -> str:
    """LLM 컨텍스트용 텍스트."""
    lines = [
        "=== 연령별 혜택·국가지원 (근로자명부·한국 법령 참고) ===",
        f"기준일: {scan.as_of.isoformat()} (만 나이)",
        _DISCLAIMER,
        "",
    ]
    if not scan.matches:
        lines.append("명부에서 연령·혜택 안내 대상 직원을 찾지 못했습니다.")
        if scan.skipped_no_birth:
            lines.append(f"주민번호 미기재 {scan.skipped_no_birth}명 — 연령 판단 불가.")
        return "\n".join(lines)

    for m in scan.matches:
        lines.append(f"[{m.name}] 만 {m.age}세" + (f" · {m.dept}" if m.dept else ""))
        for p in m.programs[:4]:
            laws = " · ".join(p.law_refs[:2])
            lines.append(f"  · {p.title} ({laws}): {p.summary[:120]}…")
        for n in m.notes[:3]:
            lines.append(f"  ※ {n}")
        for q in m.questions[:2]:
            lines.append(f"  ? {q}")
        lines.append("")

    if scan.skipped_no_birth:
        lines.append(f"주민번호 없음: {scan.skipped_no_birth}명 (연령별 안내 제외)")
    return "\n".join(lines)


def format_proactive_benefit_message(
    scan: AgeBenefitScanResult,
    *,
    session: UserSession | None = None,
) -> str | None:
    """Personal AI 대화 시작 시 자동 추천·질문."""
    if not scan.has_recommendations:
        return None
    sess = session or get_session_safe()
    name = (sess.display_name if sess else "") or "담당자"
    lines = [
        f"{name}님, 근로자 명부를 바탕으로 연령별 혜택·국가지원을 점검했습니다.",
        "",
        "📋 추천 확인 대상",
    ]
    for m in scan.matches[:5]:
        titles = ", ".join(p.title for p in m.programs[:2])
        lines.append(f"  · {m.name} (만 {m.age}세): {titles}")
        if m.questions:
            lines.append(f"    → {m.questions[0]}")
    lines.extend(
        [
            "",
            "「김OO 혜택」, 「65세 보험」, 「시니어 인턴십」처럼 물어보시면 "
            "법령 근거와 HR 조치를 자세히 안내해 드립니다.",
            "",
            _DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def get_session_safe() -> UserSession | None:
    try:
        from core.session_service import get_session

        return get_session()
    except Exception:
        return None


def _find_roster_row(rows: list[dict], name: str) -> dict | None:
    key = norm_name_key(name)
    if not key:
        return None
    for rec in rows:
        n = str(rec.get("성명") or rec.get("name") or "")
        if norm_name_key(n) == key:
            return rec
    fuzzy = find_fuzzy_name_key(key, [str(r.get("성명") or "") for r in rows])
    if fuzzy:
        for rec in rows:
            if norm_name_key(str(rec.get("성명") or "")) == fuzzy:
                return rec
    return None


def format_benefit_answer_for_person(
    name: str,
    tenant_id: str,
    *,
    session: UserSession | None = None,
    as_of: date | None = None,
) -> str | None:
    """특정 직원 연령별 혜택 상세."""
    sess = enforce_session_tenant_access(session or require_session())
    as_of = as_of or date.today()
    rows = load_roster_rows_secured(session=sess)
    rec = _find_roster_row(rows, name)
    if rec is None:
        return f"명부에서 「{name}」을(를) 찾지 못했습니다. 성명을 확인해 주세요."

    rrn = rec.get("주민번호")
    birth = parse_birth_date_from_korean_rrn(rrn, as_of=as_of)
    if birth is None:
        return f"{name}님 명부에 주민번호가 없어 만 나이를 계산할 수 없습니다. 명부에 입력 후 다시 요청해 주세요."

    age = age_years_at(birth, as_of)
    programs = programs_for_age(age)
    notes = _employee_notes(rec, as_of=as_of)

    lines = [
        f"【{name}】 만 {age}세 (기준일 {as_of.isoformat()})",
        "",
    ]
    if not programs:
        lines.append("현재 연령대에 매칭되는 표준 안내 프로그램이 없습니다.")
    else:
        lines.append("적용·검토 가능한 항목:")
        for p in programs:
            lines.append(f"\n▶ {p.title}")
            lines.append(f"  근거: {', '.join(p.law_refs)}")
            lines.append(f"  {p.summary}")
            if p.hr_actions:
                lines.append("  HR 조치:")
                for a in p.hr_actions[:3]:
                    lines.append(f"    · {a}")
    if notes:
        lines.append("\nBitween·명부 상태:")
        for n in notes:
            lines.append(f"  · {n}")
    qs = _collect_questions(programs, notes)
    if qs:
        lines.append("\n확인해 주세요:")
        for i, q in enumerate(qs[:4], 1):
            lines.append(f"  {i}. {q}")
    lines.append(f"\n{_DISCLAIMER}")
    return "\n".join(lines)


def try_answer_age_benefit_question(
    question: str,
    session: UserSession,
    *,
    tenant_id: str | None = None,
) -> str | None:
    """연령·혜택·지원 관련 질문 즉답."""
    if not is_benefit_related_question(question):
        return None

    tid = tenant_id or session.tenant_id
    person = extract_person_name(question)
    if person:
        return format_benefit_answer_for_person(person, tid, session=session)

    scan = scan_roster_age_benefits(tid, session=session, limit=8)
    if not scan.has_recommendations:
        return (
            "명부에서 연령별 혜택 안내 대상을 찾지 못했습니다.\n"
            "주민번호가 입력된 60세·65세 이상·청년 해당 직원이 있는지 명부를 확인해 주세요.\n\n"
            + _DISCLAIMER
        )

    lines = [
        "근로자 명부 기준 연령별 혜택·국가지원 요약입니다.",
        "",
        format_benefit_context_block(scan),
        "",
        "특정 직원은 「홍길동 혜택」처럼 이름을 넣어 물어봐 주세요.",
    ]
    return "\n".join(lines)
