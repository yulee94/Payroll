"""
services/ai_assistant.py - Personal AI Agent (OpenAI SDK + Bitween 업무 데이터)
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paths import app_data_dir
from core.session_service import UserSession, require_session
from core.tenant_data_scope import TenantDataAccessError, enforce_session_tenant_access
from services.ai_agent_actions import AgentActionResult, try_handle_agent_actions
from services.ai_safety_policy import assess_ai_request_safety, get_safety_rules_for_prompt
from services.ai_user_context import get_user_context
from services.ai_workspace_actions import try_handle_workspace_actions
from services.openai_client import (
    COMPAT_FALLBACK_MODEL,
    OpenAIKeyMissingError,
    create_openai_client,
)
from services.openai_errors import QUOTA_USER_MESSAGE, OpenAIQuotaError, is_quota_error
from services.openai_settings_store import load_openai_settings, resolve_openai_model
from services.personal_agent_prompt import build_personal_agent_system_prompt
from services.local_agent_dialogue import format_work_dialogue_reply, is_pure_casual_message, try_casual_reply
from services.work_ai_context import build_work_context, classify_work_intents

# TODO: rate limit (요청/분당), conversationId DB 영구 저장
_MAX_MESSAGE_LEN = 8000
_MAX_CONTEXT_CHARS = 7000
_OPENAI_HISTORY_LIMIT = 4
_OPENAI_TIMEOUT_SEC = 45

_AGENT_INTENTS = frozenset({"report", "document", "archive"})
_LOCAL_DIRECT_INTENTS = frozenset(
    {"payroll", "roster", "tasks", "schedule", "mail", "messenger", "platform", "benefits"}
)
_NARRATIVE_KW = (
    "초안",
    "작성",
    "써",
    "문장",
    "이메일",
    "메일 써",
    "정리해",
    "요약해",
    "설명해",
    "추천해",
    "아이디어",
    "방법",
    "어떻게",
    "왜",
    "비교",
    "계획",
    "안내 문구",
    "다듬",
    "검토해",
)

_logger = logging.getLogger(__name__)


@dataclass
class AssistantResponse:
    answer: str
    attachment_paths: list[str] = field(default_factory=list)
    conversation_id: str = ""
    response_id: str = ""
    api_mode: str = ""  # responses | chat_completions | local

    def __str__(self) -> str:
        return self.answer


def _trim_context(ctx: str, max_len: int = _MAX_CONTEXT_CHARS) -> str:
    text = str(ctx or "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 80].rstrip() + "\n\n...(컨텍스트 일부 생략 — 핵심 데이터는 상단에 있습니다.)"


def _needs_llm_narrative(question: str) -> bool:
    tl = str(question or "").lower()
    return any(k in tl for k in _NARRATIVE_KW)


def _needs_agent_actions(intents: list[str]) -> bool:
    return bool(_AGENT_INTENTS.intersection(intents))


def _prefer_local_direct_over_openai(question: str, intents: list[str], direct: str | None) -> bool:
    if not direct or _needs_llm_narrative(question):
        return False
    if "report" in intents or "document" in intents:
        return False
    if intents == ["general"]:
        return True
    return set(intents).issubset(_LOCAL_DIRECT_INTENTS)


def _is_action_only_message(question: str) -> bool:
    from services.ai_workspace_actions import _has_complete_intent, _has_write_intent

    text = str(question or "").strip()
    if not (_has_write_intent(text) or _has_complete_intent(text)):
        return False
    if _needs_llm_narrative(text):
        return False
    if any(k in text for k in ("그리고", "또", "알려", "?", "어때", "설명", "말해")):
        return False
    return len(text) <= 120


def _should_skip_openai_for_agent(agent_result: Any, question: str) -> bool:
    if not agent_result.changed:
        return False
    if _needs_llm_narrative(question):
        return False
    return bool(getattr(agent_result, "report_bundle", None) or getattr(agent_result, "search_result", None))


def _chat_history_path(sess: UserSession) -> Path:
    return (
        app_data_dir()
        / "workspace"
        / sess.tenant_id
        / "users"
        / sess.user_id
        / "ai_chat_history.json"
    )


def load_chat_history(session: UserSession | None = None, limit: int = 20) -> list[dict[str, str]]:
    sess = session or require_session()
    path = _chat_history_path(sess)
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        msgs = raw.get("messages") if isinstance(raw, dict) else []
        if not isinstance(msgs, list):
            return []
        out = []
        for m in msgs[-limit:]:
            if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content"):
                out.append({"role": str(m["role"]), "content": str(m["content"])})
        return out
    except (OSError, json.JSONDecodeError):
        return []


def save_chat_turn(
    user_text: str,
    assistant_text: str,
    session: UserSession | None = None,
) -> None:
    sess = session or require_session()
    path = _chat_history_path(sess)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw: dict[str, Any] = {}
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
    msgs: list[dict[str, str]] = list(raw.get("messages") or [])
    msgs.append({"role": "user", "content": user_text})
    msgs.append({"role": "assistant", "content": assistant_text})
    raw["messages"] = msgs[-40:]
    raw["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_chat_history(session: UserSession | None = None) -> None:
    sess = session or require_session()
    path = _chat_history_path(sess)
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass


def _build_developer_prompt(
    sess: UserSession,
    *,
    work_context: str,
    intents: list[str],
) -> str:
    user_ctx = get_user_context(sess)
    intent_note = f"[질문 유형: {', '.join(intents)}]\n"
    system_prompt = build_personal_agent_system_prompt(
        user_ctx,
        extra_rules=get_safety_rules_for_prompt(),
    )
    return (
        system_prompt
        + "\n\n"
        + intent_note
        + "[로컬 업무 컨텍스트]\n"
        + work_context
    )


def _extract_responses_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return str(text).strip()
    parts: list[str] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", None) or []:
            if getattr(content, "type", None) == "output_text":
                parts.append(str(getattr(content, "text", "") or ""))
    return "\n".join(p for p in parts if p).strip()


def _call_responses_api(
    *,
    api_key: str,
    model: str,
    instructions: str,
    user_message: str,
    history: list[dict[str, str]],
    previous_response_id: str | None = None,
) -> tuple[str, str]:
    """OpenAI Responses API (client.responses.create). Returns (answer, response_id)."""
    client = create_openai_client(api_key=api_key)
    input_payload: Any
    if history:
        input_payload = [
            *[{"role": m["role"], "content": m["content"]} for m in history],
            {"role": "user", "content": user_message},
        ]
    else:
        input_payload = user_message

    kwargs: dict[str, Any] = {
        "model": model,
        "instructions": instructions,
        "input": input_payload,
        "temperature": 0.35,
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    response = client.responses.create(**kwargs)
    answer = _extract_responses_text(response)
    if not answer:
        raise RuntimeError("OpenAI Responses API 응답 내용이 없습니다.")
    response_id = str(getattr(response, "id", "") or "")
    return answer, response_id


def _call_chat_completions(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    model: str,
    timeout: int = _OPENAI_TIMEOUT_SEC,
) -> tuple[str, str]:
    """
    Chat Completions 폴백 (urllib — Responses API 실패·구모델 호환 시).
    SDK responses.create 가 모델 미지원·네트워크 오류일 때 사용합니다.
    """
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": 0.35,
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("error", {}).get("message", err_body)
        except json.JSONDecodeError:
            msg = err_body or str(exc)
        raise RuntimeError(f"OpenAI API 오류 ({exc.code}): {msg}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"네트워크 오류: {exc.reason}") from exc

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenAI 응답이 비어 있습니다.")
    content = choices[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("OpenAI 응답 내용이 없습니다.")
    response_id = str(data.get("id") or "")
    return str(content).strip(), response_id


def _call_openai_with_fallback(
    *,
    api_key: str,
    model: str,
    instructions: str,
    user_message: str,
    history: list[dict[str, str]],
    previous_response_id: str | None = None,
) -> tuple[str, str, str]:
    """
    Chat Completions 우선 (응답 속도), 실패 시 Responses API 폴백.
    Returns (answer, response_id, api_mode).
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": instructions},
        *history,
        {"role": "user", "content": user_message},
    ]
    models_to_try = [model]
    if model != COMPAT_FALLBACK_MODEL:
        models_to_try.append(COMPAT_FALLBACK_MODEL)

    last_exc: Exception | None = None
    for attempt_model in models_to_try:
        try:
            answer, rid = _call_chat_completions(
                messages,
                api_key=api_key,
                model=attempt_model,
            )
            return answer, rid, "chat_completions"
        except Exception as exc:
            last_exc = exc
            if is_quota_error(exc):
                _logger.info("OpenAI quota exceeded on chat completions")
                break
            _logger.warning("Chat completions failed for model %s: %s", attempt_model, exc)

        try:
            answer, rid = _call_responses_api(
                api_key=api_key,
                model=attempt_model,
                instructions=instructions,
                user_message=user_message,
                history=history,
                previous_response_id=previous_response_id if attempt_model == model else None,
            )
            return answer, rid, "responses"
        except Exception as exc:
            last_exc = exc
            if is_quota_error(exc):
                _logger.info("OpenAI quota exceeded; skipping further API retries")
                break
            _logger.warning("Responses API failed (%s)", exc)

    if last_exc and is_quota_error(last_exc):
        raise OpenAIQuotaError(QUOTA_USER_MESSAGE) from last_exc
    raise RuntimeError(f"OpenAI 호출 실패: {last_exc}") from last_exc


def _answer_with_quota_fallback(
    q: str,
    sess: UserSession,
    *,
    exc: BaseException,
    agent_result: Any,
    workspace_result: Any,
    bundle: Any,
    conv_id: str,
    ctx: str,
) -> AssistantResponse:
    """한도 초과 시 로컬 데이터로 답변 + 결제 안내."""
    bundle.context_text = ctx
    local = _local_fallback_answer(
        q,
        sess,
        agent_result=agent_result,
        workspace_result=workspace_result,
        bundle=bundle,
        conv_id=conv_id,
    )
    note = QUOTA_USER_MESSAGE if isinstance(exc, OpenAIQuotaError) else str(exc)
    if note not in local.answer:
        local.answer = f"{note}\n\n---\n\n{local.answer}"
    local.api_mode = "local_quota_fallback"
    return local


def chat_with_agent(
    message: str,
    session: UserSession | None = None,
    conversation_id: str | None = None,
) -> dict[str, str]:
    """
    Personal AI Agent 단일 턴 (OpenAI).

    Returns:
        { "answer", "responseId", "conversationId" }
    """
    q = str(message or "").strip()
    if not q:
        raise ValueError("질문을 입력하세요.")
    if len(q) > _MAX_MESSAGE_LEN:
        raise ValueError(f"질문은 {_MAX_MESSAGE_LEN}자 이하로 입력하세요.")

    try:
        sess = enforce_session_tenant_access(session or require_session())
    except TenantDataAccessError as exc:
        raise PermissionError(str(exc)) from exc

    safety = assess_ai_request_safety(q)
    if safety.blocked:
        conv_id = conversation_id or f"{sess.user_id}-{sess.tenant_id}"
        return {
            "answer": safety.denial_text,
            "responseId": "",
            "conversationId": conv_id,
        }

    settings = load_openai_settings(sess)
    api_key = str(settings.get("api_key") or "")
    if not api_key or not settings.get("enabled", True):
        raise OpenAIKeyMissingError()

    model = resolve_openai_model(str(settings.get("model") or ""))
    conv_id = conversation_id or f"{sess.user_id}-{sess.tenant_id}"
    previous_response_id = conversation_id if conversation_id and conversation_id.startswith("resp_") else None

    bundle = build_work_context(q, sess)
    instructions = _build_developer_prompt(sess, work_context=bundle.context_text, intents=bundle.intents)
    history = load_chat_history(sess, limit=8)

    try:
        answer, response_id, _mode = _call_openai_with_fallback(
            api_key=api_key,
            model=model,
            instructions=instructions,
            user_message=q,
            history=history,
            previous_response_id=previous_response_id,
        )
    except OpenAIQuotaError:
        raise
    new_conv_id = response_id or conv_id
    return {
        "answer": answer,
        "responseId": response_id,
        "conversationId": new_conv_id,
    }


def _local_fallback_answer(
    q: str,
    sess: UserSession,
    *,
    agent_result: Any,
    workspace_result: Any,
    bundle: Any,
    conv_id: str,
    api_mode: str = "local",
) -> AssistantResponse:
    direct = bundle.direct_answer
    if not agent_result.changed and not workspace_result.changed:
        casual = try_casual_reply(q, sess)
        if casual:
            save_chat_turn(q, casual, sess)
            return AssistantResponse(answer=casual, conversation_id=conv_id, api_mode="local_casual")

    if agent_result.changed and agent_result.summary_lines:
        answer = "\n".join(f"✅ {m}" for m in agent_result.summary_lines)
        if agent_result.report_bundle:
            answer += "\n\n---\n\n" + agent_result.report_bundle.draft_text[:6000]
        if direct:
            answer += "\n\n" + direct
        answer += "\n\n플랫폼 홈·월별 보고 메뉴에서 자료를 확인할 수 있습니다."
    elif workspace_result.changed and workspace_result.summary_text:
        answer = workspace_result.summary_text
        if direct:
            answer += "\n\n" + direct
        answer += "\n\n플랫폼 홈 To-Do·캘린더에서 바로 확인할 수 있습니다."
    else:
        answer = format_work_dialogue_reply(q, sess, bundle)
    save_chat_turn(q, answer, sess)
    return AssistantResponse(answer=answer, conversation_id=conv_id, api_mode=api_mode)


def _local_fast_answer(
    q: str,
    sess: UserSession,
    *,
    agent_result: AgentActionResult,
    workspace_result: Any,
    bundle: Any,
    conv_id: str,
    api_mode: str,
    attachments: list[str],
) -> AssistantResponse:
    result = _local_fallback_answer(
        q,
        sess,
        agent_result=agent_result,
        workspace_result=workspace_result,
        bundle=bundle,
        conv_id=conv_id,
        api_mode=api_mode,
    )
    if attachments:
        result.attachment_paths = attachments
    return result


def predict_assistant_status(question: str, *, has_api_key: bool) -> str:
    """UI 상태 표시용 — OpenAI 호출 여부를 빠르게 추정."""
    q = str(question or "").strip()
    if not q:
        return "답변 생성 중…"
    if not has_api_key or is_pure_casual_message(q):
        return "로컬 답변 중…"
    intents = classify_work_intents(q)
    if _is_action_only_message(q):
        return "로컬 답변 중…"
    if _needs_agent_actions(intents) and not _needs_llm_narrative(q):
        return "로컬 답변 중…"
    if set(intents).issubset(_LOCAL_DIRECT_INTENTS) and not _needs_llm_narrative(q):
        return "로컬 답변 중…"
    return "ChatGPT 연결 중…"


def ask_assistant(
    question: str,
    session: UserSession | None = None,
    *,
    use_openai: bool = True,
    conversation_id: str | None = None,
) -> AssistantResponse:
    """
    Personal AI Agent 질의응답.
    API 키: 사용자 workspace 설정 우선, 없으면 OPENAI_API_KEY 환경변수.
    """
    q = str(question or "").strip()
    if not q:
        raise ValueError("질문을 입력하세요.")
    if len(q) > _MAX_MESSAGE_LEN:
        raise ValueError(f"질문은 {_MAX_MESSAGE_LEN}자 이하로 입력하세요.")

    try:
        sess = enforce_session_tenant_access(session or require_session())
    except TenantDataAccessError as exc:
        raise PermissionError(str(exc)) from exc

    safety = assess_ai_request_safety(q)
    if safety.blocked:
        conv_id = conversation_id or f"{sess.user_id}-{sess.tenant_id}"
        save_chat_turn(q, safety.denial_text, sess)
        return AssistantResponse(answer=safety.denial_text, conversation_id=conv_id, api_mode="blocked")

    settings = load_openai_settings(sess)
    api_key = str(settings.get("api_key") or "")
    model = resolve_openai_model(str(settings.get("model") or ""))
    conv_id = conversation_id or f"{sess.user_id}-{sess.tenant_id}"
    intents = classify_work_intents(q)

    if is_pure_casual_message(q):
        casual = try_casual_reply(q, sess)
        if casual:
            save_chat_turn(q, casual, sess)
            return AssistantResponse(answer=casual, conversation_id=conv_id, api_mode="local_casual")

    workspace_result = try_handle_workspace_actions(q, sess, use_llm=False)
    agent_result = (
        try_handle_agent_actions(q, sess) if _needs_agent_actions(intents) else AgentActionResult()
    )

    bundle = build_work_context(q, sess)
    ctx = bundle.context_text
    direct = bundle.direct_answer
    intents = bundle.intents

    appendix_parts: list[str] = []
    if workspace_result.summary_text:
        appendix_parts.append("[실행된 업무함 작업]\n" + workspace_result.summary_text)
    if agent_result.context_appendix:
        appendix_parts.append(agent_result.context_appendix)
    if appendix_parts:
        ctx = ctx + "\n\n" + "\n\n".join(appendix_parts)

    attachments = [str(p) for p in agent_result.attachment_paths if p.is_file()]
    bundle.context_text = ctx

    if not use_openai or not api_key or not settings.get("enabled", True):
        return _local_fallback_answer(
            q,
            sess,
            agent_result=agent_result,
            workspace_result=workspace_result,
            bundle=bundle,
            conv_id=conv_id,
        )

    if workspace_result.changed and _is_action_only_message(q):
        return _local_fast_answer(
            q,
            sess,
            agent_result=agent_result,
            workspace_result=workspace_result,
            bundle=bundle,
            conv_id=conv_id,
            api_mode="local_action",
            attachments=attachments,
        )

    if direct and _prefer_local_direct_over_openai(q, intents, direct):
        return _local_fast_answer(
            q,
            sess,
            agent_result=agent_result,
            workspace_result=workspace_result,
            bundle=bundle,
            conv_id=conv_id,
            api_mode="local_direct",
            attachments=attachments,
        )

    if _should_skip_openai_for_agent(agent_result, q):
        return _local_fast_answer(
            q,
            sess,
            agent_result=agent_result,
            workspace_result=workspace_result,
            bundle=bundle,
            conv_id=conv_id,
            api_mode="local_agent",
            attachments=attachments,
        )

    ctx = _trim_context(ctx)
    instructions = _build_developer_prompt(sess, work_context=ctx, intents=intents)
    history = load_chat_history(sess, limit=_OPENAI_HISTORY_LIMIT)
    previous_response_id = (
        conversation_id if conversation_id and str(conversation_id).startswith("resp_") else None
    )

    try:
        answer, response_id, api_mode = _call_openai_with_fallback(
            api_key=api_key,
            model=model,
            instructions=instructions,
            user_message=q,
            history=history,
            previous_response_id=previous_response_id,
        )
    except OpenAIKeyMissingError:
        raise
    except OpenAIQuotaError as exc:
        return _answer_with_quota_fallback(
            q,
            sess,
            exc=exc,
            agent_result=agent_result,
            workspace_result=workspace_result,
            bundle=bundle,
            conv_id=conv_id,
            ctx=ctx,
        )
    except Exception as exc:
        if is_quota_error(exc):
            return _answer_with_quota_fallback(
                q,
                sess,
                exc=exc,
                agent_result=agent_result,
                workspace_result=workspace_result,
                bundle=bundle,
                conv_id=conv_id,
                ctx=ctx,
            )
        raise RuntimeError(str(exc)) from exc

    footnotes: list[str] = []
    if workspace_result.summary_text and workspace_result.summary_text not in answer:
        footnotes.append(workspace_result.summary_text)
    if agent_result.summary_lines:
        agent_note = "\n".join(f"✅ {m}" for m in agent_result.summary_lines)
        if agent_note not in answer:
            footnotes.append(agent_note)
    if footnotes:
        answer = answer.rstrip() + "\n\n" + "\n".join(footnotes)

    save_chat_turn(q, answer, sess)
    return AssistantResponse(
        answer=answer,
        attachment_paths=attachments,
        conversation_id=response_id or conv_id,
        response_id=response_id,
        api_mode=api_mode,
    )
