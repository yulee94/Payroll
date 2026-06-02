"""
services/ai_workspace_actions.py - Personal AI 대화형 To-Do·캘린더 등록
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Literal

from core.session_service import UserSession, require_session
from services import workspace_store as ws
from services.openai_settings_store import DEFAULT_MODEL

ActionType = Literal["add_todo", "add_event", "complete_todo"]

_WRITE_VERBS = (
    "추가",
    "등록",
    "넣어",
    "잡아",
    "만들",
    "기록",
    "적어",
    "저장",
    "등록해",
    "추가해",
    "등록해줘",
    "추가해줘",
    "잡아줘",
    "넣어줘",
    "만들어",
    "만들어줘",
    "예약",
)
_COMPLETE_VERBS = ("완료", "체크", "끝", "했어", "처리했", "지워", "삭제")
_CALENDAR_KW = ("일정", "캘린더", "스케줄", "약속", "회의", "미팅", "schedule", "calendar", "event")
_TODO_KW = ("할일", "할 일", "todo", "to-do", "태스크", "투두")


@dataclass
class ParsedAction:
    action: ActionType
    title: str
    due_date: str = ""
    event_date: str = ""


@dataclass
class WorkspaceActionResult:
    actions: list[ParsedAction] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    changed: bool = False

    @property
    def summary_text(self) -> str:
        if not self.messages:
            return ""
        return "\n".join(f"✅ {m}" for m in self.messages)


def _has_write_intent(text: str) -> bool:
    t = text.lower()
    if any(v in text for v in _WRITE_VERBS):
        return True
    return "add" in t or "create" in t


def _has_complete_intent(text: str) -> bool:
    t = text.lower()
    if any(v in text for v in _COMPLETE_VERBS):
        return True
    return "done" in t or "complete" in t


def _is_calendar_intent(text: str) -> bool:
    tl = text.lower()
    has_cal = any(k in tl for k in _CALENDAR_KW)
    has_todo = any(k in tl for k in _TODO_KW)
    if has_cal and not has_todo:
        return True
    if has_todo and not has_cal:
        return False
    if re.search(r"(마감|까지|due)", tl):
        return False
    if parse_korean_date(text):
        return True
    return False


def parse_korean_date(text: str, *, ref: date | None = None) -> str | None:
    """한국어·숫자 날짜 표현 → YYYY-MM-DD."""
    ref = ref or date.today()
    t = str(text or "")

    if re.search(r"오늘", t):
        return ref.isoformat()
    if re.search(r"내일", t):
        return (ref + timedelta(days=1)).isoformat()
    if re.search(r"모레", t):
        return (ref + timedelta(days=2)).isoformat()

    weekday_map = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    m = re.search(r"(?:다음\s*주|다음주)\s*([월화수목금토일])요일", t)
    if m:
        target = weekday_map[m.group(1)]
        days_to_next_monday = (7 - ref.weekday()) % 7
        if days_to_next_monday == 0:
            days_to_next_monday = 7
        next_monday = ref + timedelta(days=days_to_next_monday)
        return (next_monday + timedelta(days=target)).isoformat()

    m = re.search(r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})", t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            pass

    m = re.search(r"(\d{1,2})월\s*(\d{1,2})일", t)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = ref.year
        try:
            d = date(year, month, day)
            if d < ref - timedelta(days=180):
                d = date(year + 1, month, day)
            return d.isoformat()
        except ValueError:
            pass

    m = re.search(r"(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        year = ref.year
        if m.group(3):
            y = int(m.group(3))
            year = y if y > 99 else 2000 + y
        try:
            if a > 12:
                d = date(year, b, a)
            else:
                d = date(year, a, b)
            return d.isoformat()
        except ValueError:
            pass

    return None


def _strip_date_phrases(text: str) -> str:
    out = text
    patterns = (
        r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",
        r"\d{1,2}월\s*\d{1,2}일",
        r"\d{1,2}[/.]\d{1,2}(?:[/.]\d{2,4})?",
        r"(?:다음\s*주|다음주)\s*[월화수목금토일]요일",
        r"오늘|내일|모레",
        r"(?:마감|까지)\s*[^\s,]+",
    )
    for pat in patterns:
        out = re.sub(pat, " ", out)
    return re.sub(r"\s+", " ", out).strip()


def _extract_todo_due_and_title(text: str) -> tuple[str, str]:
    """「내일까지 ○○」 형태에서 마감일과 본문 분리."""
    t = str(text or "").strip()
    due = ""

    m = re.match(
        r"^(내일|모레|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}월\s*\d{1,2}일|\d{1,2}[/.]\d{1,2})(?:까지)\s*(.+)$",
        t,
    )
    if m:
        due = parse_korean_date(m.group(1)) or ""
        return due, m.group(2).strip()

    m = re.match(r"^(.+?)\s*(내일|모레|\d{1,2}월\s*\d{1,2}일|\d{1,2}[/.]\d{1,2})(?:까지)\s*$", t)
    if m:
        due = parse_korean_date(m.group(2)) or ""
        return due, m.group(1).strip()

    m = re.search(r"(?:마감|까지)\s*([^\s,]+)", t)
    if m:
        due = parse_korean_date(m.group(1)) or parse_korean_date(t) or ""

    return due, t


def _clean_title(raw: str) -> str:
    title = str(raw or "").strip()
    title = re.sub(r"^[「『\"']|[」』\"']$", "", title)
    title = re.sub(
        r"^(?:할\s*일|todo|to-do|일정|캘린더|스케줄|약속|회의|미팅)\s*(?:으로|에|로)?\s*",
        "",
        title,
        flags=re.I,
    )
    title = re.sub(
        r"\s*(?:을|를|에|로|으로)?\s*(?:추가|등록|넣어|잡아|만들|저장|해줘|해 주세요|해주세요|등록해|추가해).*$",
        "",
        title,
    )
    title = _strip_date_phrases(title)
    title = re.sub(r"\s+", " ", title).strip(" ·,-")
    return title


def _parse_local_actions(question: str) -> list[ParsedAction]:
    text = str(question or "").strip()
    if not text:
        return []

    actions: list[ParsedAction] = []
    parsed_date = parse_korean_date(text)

    if _has_complete_intent(text) and any(k in text.lower() for k in _TODO_KW + ("할일",)):
        title = _clean_title(text)
        title = re.sub(r"(?:완료|체크|끝|했어|처리|지워|삭제).*$", "", title).strip()
        if title:
            actions.append(ParsedAction(action="complete_todo", title=title))
            return actions

    if not _has_write_intent(text):
        return []

    patterns_todo = (
        r"(?:할\s*일|todo|to-do)(?:에|로)?\s*[:\-]?\s*(.+?)\s*(?:추가|등록|넣|잡|만들)",
        r"(.+?)\s*(?:을|를)?\s*(?:할\s*일|todo|to-do)(?:에|로)?\s*(?:추가|등록|넣|잡|만들)",
        r"(?:할\s*일|todo)\s*(?:추가|등록)\s*[:\-]?\s*(.+)",
    )
    patterns_event = (
        r"(?:일정|캘린더|스케줄|약속|회의|미팅)(?:에|으로|로)?\s*[:\-]?\s*(.+?)\s*(?:추가|등록|넣|잡|만들|예약)",
        r"(.+?)\s*(?:을|를)?\s*(?:일정|캘린더|스케줄)(?:에|으로|로)?\s*(?:추가|등록|넣|잡|만들|예약)",
        r"(?:일정|캘린더)\s*(?:추가|등록)\s*[:\-]?\s*(.+)",
    )

    is_cal = _is_calendar_intent(text)
    patterns = patterns_event if is_cal else patterns_todo

    title = ""
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            raw = m.group(1).strip()
            if is_cal:
                title = _clean_title(raw)
            else:
                due_hint, body = _extract_todo_due_and_title(raw)
                title = _clean_title(body)
                if due_hint and not re.search(r"(?:마감|까지)", text):
                    pass
            if title:
                break

    if not title:
        generic = re.search(
            r"(?:추가|등록|넣어|잡아|만들|저장|예약)\s*[:\-]?\s*(.+)$",
            text,
        )
        if generic:
            title = _clean_title(generic.group(1))

    if not title and parsed_date:
        rest = _strip_date_phrases(text)
        for verb in _WRITE_VERBS:
            rest = rest.replace(verb, " ")
        title = _clean_title(rest)

    if not title:
        return []

    if is_cal:
        event_date = parsed_date or date.today().isoformat()
        actions.append(ParsedAction(action="add_event", title=title, event_date=event_date))
    else:
        due, _ = _extract_todo_due_and_title(text)
        if not due:
            m_due = re.search(r"(?:마감|까지)\s*([^\s,]+)", text)
            if m_due:
                due = parse_korean_date(m_due.group(1)) or ""
            elif parsed_date and any(k in text for k in ("마감", "까지", "due")):
                due = parsed_date
        actions.append(ParsedAction(action="add_todo", title=title, due_date=due))

    return actions


def _extract_actions_via_llm(
    question: str,
    *,
    api_key: str,
    model: str,
    ref: date,
) -> list[ParsedAction]:
    prompt = f"""사용자 메시지에서 개인 To-Do·캘린더 등록/완료 의도만 JSON 배열로 추출하세요.
오늘: {ref.isoformat()}
규칙:
- add_todo: title(필수), due_date(YYYY-MM-DD 또는 null)
- add_event: title(필수), date(YYYY-MM-DD, 없으면 오늘)
- complete_todo: title(완료할 할 일 제목)
- 등록·추가·잡아줘·넣어줘 등 쓰기 의도가 없으면 []
- JSON 배열만 출력 (설명 금지)

예: [{{"action":"add_todo","title":"보고서 작성","due_date":"2026-06-05"}}]

사용자: {question}"""

    body = json.dumps(
        {
            "model": model or DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
        return []

    content = str((data.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.I).strip()
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\[[\s\S]*\]", content)
        if not m:
            return []
        try:
            raw = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []

    if not isinstance(raw, list):
        return []

    out: list[ParsedAction] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "").strip()
        title = _clean_title(str(item.get("title") or ""))
        if not title:
            continue
        if action == "add_todo":
            due = str(item.get("due_date") or item.get("date") or "").strip()
            if due and due.lower() in ("null", "none"):
                due = ""
            if due and len(due) >= 10:
                due = due[:10]
            elif not due:
                due = parse_korean_date(question, ref=ref) or ""
                if due and _is_calendar_intent(question):
                    due = ""
            out.append(ParsedAction(action="add_todo", title=title, due_date=due))
        elif action == "add_event":
            ev_date = str(item.get("date") or item.get("event_date") or "").strip()
            if len(ev_date) < 10:
                ev_date = parse_korean_date(question, ref=ref) or ref.isoformat()
            else:
                ev_date = ev_date[:10]
            out.append(ParsedAction(action="add_event", title=title, event_date=ev_date))
        elif action == "complete_todo":
            out.append(ParsedAction(action="complete_todo", title=title))
    return out


def _execute_action(action: ParsedAction, sess: UserSession) -> str:
    if action.action == "add_todo":
        item = ws.add_todo(action.title, due_date=action.due_date, session=sess)
        due_note = f" (마감 {item['due_date']})" if item.get("due_date") else ""
        return f"할 일 등록: 「{item['title']}」{due_note}"

    if action.action == "add_event":
        ev = ws.add_calendar_event(
            action.title,
            action.event_date or date.today().isoformat(),
            session=sess,
        )
        return f"일정 등록: {ev['date']} 「{ev['title']}」"

    if action.action == "complete_todo":
        todos = [t for t in ws.list_todos(sess) if not t.get("done")]
        needle = action.title.lower()
        matched = None
        for t in todos:
            title = str(t.get("title") or "")
            if needle in title.lower() or title.lower() in needle:
                matched = t
                break
        if not matched:
            raise ValueError(f"할 일 「{action.title}」을(를) 찾지 못했습니다.")
        ws.toggle_todo(str(matched["id"]), session=sess)
        return f"할 일 완료 처리: 「{matched.get('title', '')}」"

    raise ValueError(f"지원하지 않는 작업: {action.action}")


def try_handle_workspace_actions(
    question: str,
    session: UserSession | None = None,
    *,
    api_key: str = "",
    model: str = "",
    use_llm: bool = True,
) -> WorkspaceActionResult:
    """
    대화에서 To-Do·캘린더 등록/완료를 실행합니다.
    로컬 패턴 우선, API 있으면 LLM 보조 추출.
    """
    sess = session or require_session()
    text = str(question or "").strip()
    result = WorkspaceActionResult()

    if not text:
        return result

    tl = text.lower()
    might_act = (
        _has_write_intent(text)
        or _has_complete_intent(text)
        or any(k in tl for k in _TODO_KW + _CALENDAR_KW)
    )
    if not might_act:
        return result

    parsed = _parse_local_actions(text)
    if not parsed and use_llm and api_key and (_has_write_intent(text) or _has_complete_intent(text)):
        parsed = _extract_actions_via_llm(
            text,
            api_key=api_key,
            model=model or DEFAULT_MODEL,
            ref=date.today(),
        )

    if not parsed:
        return result

    for action in parsed:
        try:
            msg = _execute_action(action, sess)
            result.messages.append(msg)
            result.actions.append(action)
            result.changed = True
        except ValueError as exc:
            result.messages.append(str(exc))
        except Exception as exc:
            result.messages.append(f"처리 실패: {exc}")

    return result
