# Personal AI Agent

Bitween Personal AI is a tenant/user-scoped work assistant for payroll, workflow, reports, To-Do/calendar, and KPI contexts. Production delivery should route AI requests through the Kubernetes-native API/policy gateway while keeping API keys in service-layer settings or Secrets only.

## Related files

| Path | Role |
|------|------|
| `services/openai_client.py` | OpenAI SDK client and key validation compatibility adapter |
| `services/openai_settings_store.py` | User/tenant API key and model settings |
| `services/ai_assistant.py` | `ask_assistant`, `chat_with_agent`, Responses fallback |
| `services/ai_chat_stream.py` | Streaming compatibility stub |
| `services/personal_agent_prompt.py` | System/developer prompt |
| `services/ai_user_context.py` | User context (session and To-Do DB integration) |
| `services/work_ai_context.py` | Payroll, roster, workflow inbox context |
| `services/ai_safety_policy.py` | Platform mutation blocking and write-path validation |
| `services/payroll_ai_context.py` | Payroll snapshot lookup |
| `services/ai_agent_actions.py` | Report/chart actions |
| `services/ai_workspace_actions.py` | To-Do/calendar actions |
| `tests/test_ai_chat.py` | Mock unit tests |
| `AI_README.md` | Streaming and development notes |

## Installation for compatibility tests

```bash
pip install -r requirements.txt
```

`requirements.txt` includes `openai>=1.0`.

## Environment variables

`.env.example` documents optional local variables:

| Variable | Description |
|------|------|
| `OPENAI_API_KEY` | Shared development key, optional |
| `OPENAI_MODEL` | Default model such as `gpt-5.5` |

Production Kubernetes deployments must inject credentials through Secrets or an external secret manager, not through source files or frontend bundles.

## API key priority

1. Personal AI account settings under tenant/user app data.
2. `OPENAI_API_KEY` environment variable.
3. Kubernetes Secret or external secret manager for production service deployments.

Do not put keys in source, Git, container images, or frontend bundles.

## Tests

```bash
python -m unittest tests.test_ai_chat -v
python -c "from services.ai_assistant import ask_assistant; print('ok', ask_assistant)"
```

## API behavior

- Primary: OpenAI Responses API (`client.responses.create`).
- Fallback: Chat Completions (`/v1/chat/completions`) and lower-cost retry model when configured.
- No API key: local payroll/work context only, plus API registration guidance.

`chat_with_agent(message, session, conversation_id)` returns:

```json
{ "answer": "...", "responseId": "...", "conversationId": "..." }
```

## Security

- `ai_safety_policy.py` blocks platform/permission/roster/payroll mutation requests outside approved actions.
- AI file writes are limited to personal `workspace/.../ai_assets` and report output folders.
- API keys, passwords, cookies, and secrets must not be emitted in prompts, logs, responses, or frontend assets.

## Roadmap

- Rust AI policy gateway and tenant-scoped API routes.
- Persistent `conversationId`, rate limits, and audit events.
- Streaming endpoint for TypeScript frontend chat surfaces.
- Kubernetes Secret integration and production observability.
