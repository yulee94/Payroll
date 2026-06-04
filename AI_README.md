# Personal AI — development memo

## Streaming status

Streaming is not implemented yet. `services/ai_chat_stream.py` currently delegates to synchronous `chat_with_agent`.

Future TypeScript/platform chat integration:

1. Call the Rust/Kubernetes AI policy gateway.
2. Stream provider responses through an approved server endpoint.
3. Update the frontend chat surface incrementally with cancellation and error states.
4. Keep API keys in service settings, Kubernetes Secrets, or an external secret manager only.

Detailed design: `docs/AI_AGENT.md`

## Responses vs Chat Completions

`services/ai_assistant.py` compatibility behavior:

1. `responses.create` (model: `OPENAI_MODEL` / user setting / `gpt-5.5`)
2. Fallback to Chat Completions on the same model
3. Retry with lower-cost fallback model if configured

`AssistantResponse.api_mode`: `responses` | `chat_completions` | `local` | `blocked`
