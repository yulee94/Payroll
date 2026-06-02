"""
services/local_agent_dialogue.py - API 없이 Personal AI 대화 (인사·일상·업무 요약)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from core.config import APP_CONFIG
from core.session_service import UserSession

if TYPE_CHECKING:
    from services.work_ai_context import WorkContextResult

_AGENT_NAME = "빗트윈"
_PRODUCT = APP_CONFIG.brand.product_name

# 업무 키워드가 있으면 인사 전용 응답 대신 업무 처리
_WORK_HINTS = (
    "급여",
    "명부",
    "월별",
    "보고",
    "기안",
    "결재",
    "전자결재",
    "할일",
    "할 일",
    "todo",
    "일정",
    "캘린더",
    "메일",
    "메신저",
    "양식",
    "산출",
    "청구",
    "연차",
    "근태",
    "구매",
    "지출",
    "실행",
    "문서",
    "상신",
    "승인",
    "반려",
    "임원",
    "사업장",
    "마감",
    "원장",
    "명세",
    "65세",
    "60세",
    "혜택",
    "지원사업",
    "시니어",
    "인턴십",
    "청년",
)


def _norm(text: str) -> str:
    t = str(text or "").strip().lower()
    t = re.sub(r"[!?.,~…\s]+", " ", t)
    return t.strip()


def _contains_work_intent(text: str) -> bool:
    tl = text.lower()
    return any(k in tl for k in _WORK_HINTS)


def is_pure_casual_message(text: str) -> bool:
    """짧은 인사·일상만 있는지 (업무 키워드 없음)."""
    raw = str(text or "").strip()
    if not raw or len(raw) > 80:
        return False
    if _contains_work_intent(raw):
        return False
    n = _norm(raw)
    casual_starts = (
        "안녕",
        "하이",
        "hello",
        "hi",
        "헬로",
        "반가",
        "만나서",
        "고마",
        "감사",
        "thanks",
        "thank",
        "잘가",
        "bye",
        "굿바",
        "good morning",
        "good night",
        "누구",
        "이름",
        "뭐야",
        "뭐해",
        "도움",
        "help",
        "기능",
        "할수",
        "할 수",
        "소개",
    )
    return any(n.startswith(c) or n == c or f" {c}" in f" {n}" for c in casual_starts)


def try_casual_reply(question: str, session: UserSession) -> str | None:
    """인사·감사·자기소개 등 오프라인 즉답."""
    if not is_pure_casual_message(question):
        return None

    n = _norm(question)
    name = (session.display_name or "님").strip()
    if name.endswith("님"):
        호칭 = name
    else:
        호칭 = f"{name}님"

    if any(x in n for x in ("안녕", "하이", "hello", "hi", "헬로", "반가", "만나서")):
        return (
            f"안녕하세요, {호칭}! 반가워요.\n\n"
            f"저는 {_PRODUCT} 플랫폼의 Personal AI Agent 「{_AGENT_NAME}」이에요. "
            f"사내 급여·인사·전자결재·업무함 데이터를 바탕으로 대화하며 도와드립니다.\n\n"
            "지금은 ChatGPT API 없이도 대화할 수 있어요. "
            "예를 들어 「할 일 알려줘」, 「이번 달 급여」, 「5월 월별보고 기안」처럼 말씀해 보세요."
        )

    if any(x in n for x in ("고마", "감사", "thanks", "thank")):
        return (
            f"천만에요, {호칭}! 도움이 되었다니 기뻐요.\n"
            f"다른 업무가 있으면 편하게 말씀해 주세요. {_AGENT_NAME}이 함께할게요."
        )

    if any(x in n for x in ("잘가", "bye", "굿바", "good night")):
        return f"좋은 하루 보내세요, {호칭}! 필요하실 때 다시 불러 주세요. — {_AGENT_NAME}"

    if any(x in n for x in ("누구", "이름", "소개", "뭐야", "뭐해")) or "agent" in n:
        return (
            f"저는 COSS Group {_PRODUCT}에 내장된 Personal AI Agent 「{_AGENT_NAME}」입니다.\n\n"
            "할 수 있는 일 (API 없이도 가능한 것):\n"
            "  · 급여·명부·월별 자료 조회 안내\n"
            "  · 연령별 혜택·국가지원 추천 (명부·한국 법령 참고)\n"
            "  · 할 일·일정·메일·메신저 현황\n"
            "  · 보고·기안 초안(텍스트), 할 일/일정 등록\n"
            "  · 플랫폼 메뉴·양식 위치 안내\n\n"
            "ChatGPT API를 연결하면 문장 다듬기·긴 보고 초안·AI 요약이 더 자연스러워집니다."
        )

    if any(x in n for x in ("도움", "help", "기능", "할수", "할 수")):
        return (
            f"{호칭}, 이렇게 요청해 보세요.\n\n"
            "  · 「안녕」 — 인사 (지금처럼 대화)\n"
            "  · 「미완료 할 일」 「이번 달 일정」\n"
            "  · 「○○ 급여 알려줘」 「명부에서 ○○ 찾아줘」\n"
            "  · 「연령별 혜택」 「홍길동 혜택」 「65세 보험」\n"
            "  · 「할일에 보고서 검토 추가」 「6월 10일 회의 일정」\n"
            "  · 「급여대장 양식 찾아줘」 「5월 월별보고 기안」\n\n"
            f"— {_AGENT_NAME} ({_PRODUCT})"
        )

  # 짧은 긍정/리액션
    if n in ("ok", "오케이", "ㅇㅇ", "응", "네", "예", "좋아", "굿", "good"):
        return f"네, {호칭}! 다음에 필요하신 업무를 말씀해 주세요."

    return (
        f"안녕하세요, {호칭}! 저는 {_AGENT_NAME}이에요.\n"
        "업무 관련 질문이나 「안녕」처럼 가볍게 말 걸어 주셔도 좋아요."
    )


def format_work_dialogue_reply(
    question: str,
    session: UserSession,
    bundle: "WorkContextResult",
) -> str:
    """업무 질문에 대한 대화형 로컬 답변 (컨텍스트 전체 덤프 대신)."""
    name = session.display_name or "사용자"
    intents = bundle.intents or ["general"]
    intent_labels = {
        "payroll": "급여",
        "roster": "직원 명부",
        "tasks": "할 일",
        "schedule": "일정",
        "mail": "메일",
        "messenger": "메신저",
        "archive": "월별 자료",
        "benefits": "연령별 혜택·국가지원",
        "platform": "플랫폼 이용",
        "general": "일반 업무",
    }
    areas = ", ".join(intent_labels.get(i, i) for i in intents[:4])

    lines = [
        f"{name}님, 말씀하신 내용을 {_PRODUCT}에 저장된 데이터로 확인했어요.",
        f"(인식한 영역: {areas})",
        "",
    ]

    if bundle.direct_answer:
        lines.append(bundle.direct_answer)
    else:
        # 섹션에서 짧게 발췌
        sec = bundle.sections or {}
        if sec.get("payroll"):
            snippet = _snippet(sec["payroll"], 1200)
            lines.append("[급여 데이터 요약]")
            lines.append(snippet)
        elif sec.get("personal"):
            lines.append(_snippet(sec["personal"], 800))
        elif sec.get("benefits"):
            lines.append("[연령별 혜택·국가지원]")
            lines.append(_snippet(sec["benefits"], 1200))
        elif sec.get("roster"):
            lines.append(_snippet(sec["roster"], 800))
        else:
            lines.append(
                "구체적인 월·이름·메뉴를 알려주시면 더 정확히 찾아드릴게요. "
                "예: 「2026년 5월 급여」, 「홍길동 명부」, 「결재 대기 문서」"
            )

    lines.append("")
    lines.append(
        f"※ 지금은 오프라인({_AGENT_NAME}) 모드입니다. "
        "Personal AI → API 설정에서 OpenAI를 연결하면 보고서·기안 문장을 더 풍부하게 다듬을 수 있어요."
    )
    return "\n".join(lines)


def _snippet(block: str, max_len: int) -> str:
    text = str(block or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "…"
