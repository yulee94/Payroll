# Personal AI — 개발 메모

## 스트리밍 상태

**미구현 (스텁만 존재).** `services/ai_chat_stream.py`의 `stream_chat_with_agent`는 내부적으로 동기 `chat_with_agent`를 호출합니다.

향후 Tkinter 연동 시:

1. `OpenAI().responses.create(..., stream=True)`
2. 워커 스레드 → `queue.Queue` → `after()`로 `ScrolledText` 갱신
3. `ui/ai_assistant_dialog.py`의 `_send()`에 스트림 분기

자세한 설계: `docs/AI_AGENT.md`

## Responses vs Chat Completions

`services/ai_assistant.py`의 `_call_openai_with_fallback`:

1. `responses.create` (모델: `OPENAI_MODEL` / 사용자 설정 / `gpt-5.5`)
2. 실패 시 동일 모델로 Chat Completions
3. 그래도 실패 시 `gpt-4o-mini`로 1·2 반복

`AssistantResponse.api_mode`: `responses` | `chat_completions` | `local` | `blocked`
