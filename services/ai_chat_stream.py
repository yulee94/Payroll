"""
services/ai_chat_stream.py - Personal AI 스트리밍 (향후 Tkinter 연동)

현재: 동기 ask_assistant / chat_with_agent 만 구현.
스트리밍은 OpenAI Responses API stream 이벤트를 UI 스레드에 넘기는 작업이 필요합니다.

TODO (Tkinter):
  1. client.responses.create(..., stream=True) 로 이벤트 수신
  2. 백그라운드 스레드에서 chunk 수집 → queue.Queue
  3. root.after(50, drain_queue) 로 ScrolledText에 점진 삽입
  4. ai_assistant_dialog._send() 에 stream=True 옵션 분기

참고: docs/AI_AGENT.md, AI_README.md
"""

from __future__ import annotations

from typing import Any, Callable, Iterator

from core.session_service import UserSession

StreamChunkCallback = Callable[[str], None]


def stream_chat_with_agent(
    message: str,
    session: UserSession | None = None,
    *,
    conversation_id: str | None = None,
    on_chunk: StreamChunkCallback | None = None,
) -> dict[str, str]:
    """
    스트리밍 스텁: 전체 응답을 한 번에 반환 (비스트리밍과 동일).

    on_chunk 가 있으면 완성된 answer 를 한 번만 호출합니다.
    """
    from services.ai_assistant import chat_with_agent

    result = chat_with_agent(message, session, conversation_id=conversation_id)
    answer = result.get("answer", "")
    if on_chunk and answer:
        on_chunk(answer)
    return result


def iter_response_stream_events(_raw_stream: Any) -> Iterator[str]:
    """TODO: OpenAI stream 이벤트 → 텍스트 델타."""
    yield from ()
