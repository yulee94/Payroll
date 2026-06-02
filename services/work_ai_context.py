"""
services/work_ai_context.py - 업무 전반 AI 컨텍스트 (의도 분류 + 로컬 데이터 조립)

구상 요약
----------
1. 질문 의도 분류 → 필요한 데이터 소스만 붙여 토큰·환각을 줄입니다.
2. 급여·명부·개인 업무함·플랫폼 안내를 분리하고, 사실(숫자·이름)은 로컬만 근거로 합니다.
3. ChatGPT는 설명·초안·절차·일반 업무 조언에 쓰고, 수치는 [로컬 컨텍스트]를 따릅니다.
4. 로그인 사용자의 개인 데이터(할 일·메일·메신저)만 세션으로 주입합니다.

의도 카테고리
-------------
- payroll      : 급여·실수령·공제·월별 합계
- roster       : 직원 명부·고용형태·시급·근무지
- schedule     : 캘린더·일정
- tasks        : Daily To-Do
- mail         : 내 메일함
- messenger    : 사내 메신저
- archive      : 월별 자료·처리 이력
- benefits     : 연령별 혜택·국가지원·법령 안내
- platform     : Bitween 메뉴·기능 사용법
- general      : 문서·메일 초안·업무 팁 (로컬 데이터 없음)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from core.brand_display import company_name_line, product_name_line
from core.platforms import PLATFORMS
from core.session_service import UserSession, require_session
from core.tenant_data_scope import (
    discover_scopes_for_tenant,
    enforce_session_tenant_access,
    filter_roster_rows_for_tenant,
    list_periods_for_tenant,
    tenant_data_scope_label,
)
from core.tenant_store import get_tenant
from payroll_archive import format_period_display
from roster_constants import find_fuzzy_name_key, norm_name_key
from core.access_control import (
    can_view_executive_payroll,
    load_roster_rows_secured,
    session_role,
)
from core.roles import role_label
from services.employee_roster_store import roster_exists, roster_updated_display
from services.payroll_ai_context import (
    build_payroll_context,
    extract_person_name,
    parse_period_from_text,
)
from services.age_benefit_advisor import (
    format_benefit_context_block,
    is_benefit_related_question,
    scan_roster_age_benefits,
    try_answer_age_benefit_question,
)
from services import workspace_store as ws

# --- 의도 키워드 ---
_INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("payroll", ("급여", "월급", "임금", "실수령", "총지급", "공제", "명세", "지급내역", "청구서")),
    ("roster", ("명부", "직원", "근로자", "입사", "퇴사", "고용형태", "시급", "사번", "인사")),
    ("schedule", ("일정", "캘린더", "스케줄", "약속", "회의", "미팅", "예약")),
    ("tasks", ("할 일", "할일", "todo", "to-do", "태스크", "업무 목록", "투두")),
    ("mail", ("메일", "이메일", "email", "편지함", "수신")),
    ("messenger", ("메신저", "채팅", "대화", "쪽지", "dm")),
    ("archive", ("자료함", "아카이브", "월별", "스냅샷", "보고", "전월대비")),
    ("report", ("기안", "초안", "임원보고", "경영보고", "요약보고", "월별보고", "보고서 작성")),
    ("document", ("양식", "템플릿", "엑셀양식", "급여대장양식", "명세서양식")),
    ("platform", ("bitween", "비트윈", "사용법", "메뉴", "기능", "플랫폼", "어디서", "어떻게")),
    (
        "benefits",
        (
            "혜택",
            "지원사업",
            "국가지원",
            "정부지원",
            "법령",
            "시니어",
            "인턴십",
            "65세",
            "60세",
            "만65",
            "만60",
            "청년",
            "중장년",
            "고령",
            "면제",
            "장려금",
            "고용지원",
        ),
    ),
)


@dataclass
class WorkContextResult:
    """AI에 넘길 업무 컨텍스트 묶음."""

    intents: list[str]
    context_text: str
    direct_answer: str | None = None
    sections: dict[str, str] = field(default_factory=dict)


def classify_work_intents(question: str) -> list[str]:
    t = str(question or "").lower()
    found: list[str] = []
    for intent, keywords in _INTENT_RULES:
        if any(kw in t for kw in keywords):
            found.append(intent)
    if not found:
        found.append("general")
    if "payroll" not in found and extract_person_name(question):
        found.insert(0, "payroll")
    return list(dict.fromkeys(found))


def _section_platform(*, compact: bool = False) -> str:
    lines = [
        f"=== {product_name_line()} / {company_name_line()} ===",
        "사이드바: 플랫폼 홈, 법인 관리, 급여(급여 산출·월별 자료함·요약·보고·설정), "
        "인사·노무(직원 명부·연차·근태·계약·증명서·입퇴사), "
        "채용·마당(채용공고·채용마당·지원·채널 홍보).",
        "플랫폼 홈: 오늘의 업무(로그인 후) — 캘린더, To-Do, 메신저, 메일, Personal AI.",
        "Personal AI: 대화로 할 일·일정 등록 가능 (예: 「할일에 보고서 작성 추가」, 「6월 10일 팀 회의 일정 등록」).",
    ]
    if not compact:
        for p in PLATFORMS:
            st = p.status_label or ("사용 가능" if p.enabled else "준비 중")
            lines.append(f"- {p.title}: {st} — {p.description[:80]}…")
    return "\n".join(lines)


def _section_archive(tenant_id: str) -> str:
    periods = list_periods_for_tenant(tenant_id)
    scopes = discover_scopes_for_tenant(tenant_id)
    lines = [
        "=== 급여 처리·자료함 (본인 법인만) ===",
        f"데이터 범위: {tenant_data_scope_label(tenant_id)}",
        f"저장된 급여월: {', '.join(format_period_display(p) for p in periods[:10]) or '없음'}",
        f"사업장·월 scope 수: {len(scopes)}",
        "급여 산출: 플랫폼 홈 → 급여 → 급여 산출에서 청구서(.xlsx) 업로드.",
        "월별 자료함·요약·보고: 동일 메뉴에서 해당 월 선택 후 이용.",
    ]
    return "\n".join(lines)


def _section_personal(sess: UserSession, intents: list[str]) -> str:
    lines = [f"=== {sess.display_name} 님 개인 업무함 (본인만) ==="]
    today = date.today()
    today_iso = today.isoformat()

    if "tasks" in intents:
        todos = [t for t in ws.list_todos(sess) if not t.get("done")]
        if todos:
            lines.append("[할 일]")
            for t in todos[:8]:
                due = f" (마감 {t['due_date']})" if t.get("due_date") else ""
                lines.append(f"  · {t.get('title', '')}{due}")
        else:
            lines.append("[할 일] 등록된 미완료 항목 없음")

    if "schedule" in intents:
        evs = ws.list_calendar_events(today.year, today.month, sess)
        upcoming = [e for e in evs if str(e.get("date", "")) >= today_iso][:6]
        lines.append(f"[이번 달 일정] {today_iso[:7]}")
        if upcoming:
            for e in upcoming:
                lines.append(f"  · {e.get('date', '')} {e.get('title', '')}")
        else:
            lines.append("  (등록된 일정 없음)")

    if "mail" in intents:
        unread = ws.unread_mail_count(sess)
        mails = ws.list_mail(sess, limit=3)
        lines.append(f"[메일] 읽지 않음 {unread}건")
        for m in mails:
            mark = "●" if not m.get("read") else "○"
            lines.append(f"  {mark} {m.get('subject', '')}")

    if "messenger" in intents:
        threads = ws.list_message_threads(sess)[:4]
        lines.append("[메신저 최근 대화]")
        if threads:
            for t in threads:
                u = f" ({t['unread']} 미읽음)" if t.get("unread") else ""
                lines.append(f"  · {t.get('other_label', '')}{u}: {(t.get('last_text') or '')[:50]}")
        else:
            lines.append("  (대화 없음)")

    bulletins = ws.list_company_bulletins(sess)
    if bulletins:
        lines.append("[회사 공지]")
        for b in bulletins[:3]:
            lines.append(f"  · {b.get('title', '')}")

    return "\n".join(lines)


def _section_roster(question: str, tenant_id: str) -> str:
    lines = [
        "=== 직원 명부 (본인 법인 소속만) ===",
        f"데이터 범위: {tenant_data_scope_label(tenant_id)}",
    ]
    if not roster_exists():
        lines.append("등록된 근로자 명부 파일이 없습니다. 인사 · 노무 → 직원 명부에서 등록하세요.")
        return "\n".join(lines)
    lines.append(f"최종 갱신: {roster_updated_display()}")
    rows = load_roster_rows_secured(tenant_id=tenant_id)
    lines.append(f"표시 가능 인원 {len(rows)}명 (임원 제외 시 일반 사용자)")

    name = extract_person_name(question)
    if name:
        key = norm_name_key(name)
        keys = {norm_name_key(r.get("성명") or r.get("name") or "") for r in rows}
        fuzzy = find_fuzzy_name_key(key, keys)
        matched = []
        for r in rows:
            rn = str(r.get("성명") or r.get("name") or "")
            nk = norm_name_key(rn)
            if fuzzy and nk == fuzzy:
                matched.append(r)
            elif nk == key or name in rn:
                matched.append(r)
        if matched:
            lines.append(f"[{name} 명부 정보]")
            for r in matched[:3]:
                lines.append(
                    f"  · {r.get('성명', r.get('name', ''))} | "
                    f"사번 {r.get('사번', '-')} | "
                    f"고용 {r.get('고용형태', '-')} | "
                    f"근무지 {r.get('근무지', '-')} | "
                    f"기본시급 {r.get('기본시급', '-')} | "
                    f"입사 {r.get('입사일', '-')}"
                )
        else:
            lines.append(f"'{name}' 을(를) 명부에서 찾지 못했습니다.")
    return "\n".join(lines)


def _try_local_work_answer(question: str, sess: UserSession, intents: list[str]) -> str | None:
    """API 없이 답할 수 있는 개인·플랫폼 질문."""
    benefit = try_answer_age_benefit_question(question, sess, tenant_id=sess.tenant_id)
    if benefit:
        return benefit

    t = question.strip()
    tl = t.lower()

    if any(k in tl for k in ("할 일", "할일", "todo")) and any(
        k in tl for k in ("뭐", "무엇", "알려", "목록", "오늘")
    ):
        todos = [x for x in ws.list_todos(sess) if not x.get("done")]
        if not todos:
            return "등록된 미완료 할 일이 없습니다. 플랫폼 홈 To-Do에서 추가할 수 있습니다."
        lines = ["미완료 할 일:"]
        for x in todos[:10]:
            due = f" (마감 {x['due_date']})" if x.get("due_date") else ""
            lines.append(f"· {x.get('title', '')}{due}")
        return "\n".join(lines)

    if any(k in tl for k in ("일정", "캘린더")) and any(k in tl for k in ("뭐", "알려", "목록", "이번")):
        today = date.today()
        evs = ws.list_calendar_events(today.year, today.month, sess)
        if not evs:
            return f"{today.year}년 {today.month}월에 등록된 일정이 없습니다."
        lines = [f"{today.year}년 {today.month}월 일정:"]
        for e in evs[:10]:
            lines.append(f"· {e.get('date', '')} {e.get('title', '')}")
        return "\n".join(lines)

    if "메일" in tl or "이메일" in tl:
        if any(k in tl for k in ("몇", "읽지", "안 읽", "미확인")):
            n = ws.unread_mail_count(sess)
            return f"읽지 않은 메일 {n}건입니다. 플랫폼 홈 → 내 메일함에서 확인하세요."

    if "메신저" in tl or "채팅" in tl:
        threads = ws.list_message_threads(sess)
        if not threads:
            return "최근 메신저 대화가 없습니다. 같은 고객사 동료에게만 메시지를 보낼 수 있습니다."
        lines = ["최근 대화:"]
        for th in threads[:5]:
            lines.append(f"· {th.get('other_label', '')}: {(th.get('last_text') or '')[:40]}")
        return "\n".join(lines)

    if "platform" in intents or "bitween" in tl or "사용법" in tl:
        if any(k in tl for k in ("급여", "산출", "청구서")):
            return (
                "급여 산출: 플랫폼 홈 → 「급여」 → 「급여 산출」에서 도급비 청구서(.xlsx)를 "
                "업로드하면 급여대장·명세서·지급내역이 생성됩니다. 처리 후 월별 자료함에서 파일을 열람할 수 있습니다."
            )
        if "명부" in tl:
            return (
                "직원 명부: 「인사 · 노무」 → 「직원 명부」에서 근로자 정보를 확인·수정합니다. "
                "저장 내용은 다음 청구서 업로드 시 급여 산출에 반영됩니다."
            )

    return None


def build_work_context(
    question: str,
    session: UserSession | None = None,
) -> WorkContextResult:
    """
    업무 질문에 맞춰 로컬 컨텍스트를 조립합니다.

    Returns:
        intents, LLM용 context_text, 즉답 가능 시 direct_answer
    """
    sess = enforce_session_tenant_access(session or require_session())
    intents = classify_work_intents(question)
    tenant = get_tenant(sess.tenant_id)
    tid = sess.tenant_id
    sections: dict[str, str] = {}

    sections["session"] = (
        f"=== 현재 세션 ===\n"
        f"사용자: {sess.display_name} ({sess.username})\n"
        f"고객사: {(tenant.display_name if tenant else tid)} ({tid})\n"
        f"열람 가능 법인: {tenant_data_scope_label(tid)}\n"
        f"권한: {role_label(session_role(sess))} ({'임원 데이터 포함' if can_view_executive_payroll(session_role(sess)) else '임원 데이터 제외'})\n"
        f"오늘: {date.today().isoformat()}\n"
        "※ 타 고객사·타 법인 급여·명부 데이터는 조회·제공 금지."
    )

    payroll_direct: str | None = None
    if "payroll" in intents or extract_person_name(question):
        payroll_ctx, payroll_direct = build_payroll_context(question, tid, session=sess)
        sections["payroll"] = payroll_ctx

    if "roster" in intents or extract_person_name(question):
        sections["roster"] = _section_roster(question, tid)

    personal_intents = {"tasks", "schedule", "mail", "messenger"}
    if personal_intents.intersection(intents):
        sections["personal"] = _section_personal(sess, intents)

    if "archive" in intents:
        sections["archive"] = _section_archive(tid)

    if "platform" in intents:
        sections["platform"] = _section_platform(compact=False)
    elif intents == ["general"]:
        sections["platform"] = _section_platform(compact=True)

    if "archive" not in sections and "payroll" in intents:
        sections["archive"] = _section_archive(tid)

    if "benefits" in intents or is_benefit_related_question(question):
        scan = scan_roster_age_benefits(tid, session=sess)
        sections["benefits"] = format_benefit_context_block(scan)

    direct = payroll_direct or _try_local_work_answer(question, sess, intents)

    parts = [
        "=== Bitween Personal AI — 로컬 업무 컨텍스트 ===",
        "아래 블록만 사실(금액·인원·일정) 근거로 사용하세요. 없는 내용은 추측하지 마세요.",
        "",
    ]
    order = ("session", "payroll", "roster", "benefits", "personal", "archive", "resources", "report_draft", "platform")
    for key in order:
        if key in sections:
            parts.append(sections[key])
            parts.append("")

    parts.append(
        "일반 업무(메일 초안, 회의 안건, 절차 설명)는 위 데이터를 참고할 수 있습니다. "
        "급여·명부 수치는 반드시 로컬 블록과 일치해야 하며, "
        "다른 법인·다른 고객사 데이터는 없는 것으로 처리하세요."
    )

    return WorkContextResult(
        intents=intents,
        context_text="\n".join(parts),
        direct_answer=direct,
        sections=sections,
    )
