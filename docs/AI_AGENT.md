# Personal AI Agent (Bitween 급여 데스크톱)

Python 3 + Tkinter 데스크톱 앱용 ChatGPT 기반 사내 업무 비서입니다. API 키는 **서비스 레이어·사용자 설정 파일**에만 있으며 실행 파일·소스 번들에 포함하지 않습니다.

## 관련 파일

| 경로 | 역할 |
|------|------|
| `services/openai_client.py` | OpenAI SDK 클라이언트, 키 검증 |
| `services/openai_settings_store.py` | 계정별 API 키·모델 (workspace JSON) |
| `services/ai_assistant.py` | `ask_assistant`, `chat_with_agent`, Responses/폴백 |
| `services/ai_chat_stream.py` | 스트리밍 스텁 (TODO) |
| `services/personal_agent_prompt.py` | 시스템(developer) 프롬프트 |
| `services/ai_user_context.py` | getUserContext (세션·TODO DB 연동) |
| `services/work_ai_context.py` | 급여·명부·업무함 컨텍스트 |
| `services/ai_safety_policy.py` | 플랫폼 변경 차단·쓰기 경로 검증 |
| `services/payroll_ai_context.py` | 급여 스냅샷 조회 |
| `services/ai_agent_actions.py` | 보고·차트 등 에이전트 액션 |
| `services/ai_workspace_actions.py` | 할 일·일정 |
| `ui/ai_assistant_dialog.py` | 채팅 UI |
| `app_ui.py` | 사이드바 「✨ Personal AI」 |
| `tests/test_ai_chat.py` | Mock 단위 테스트 |
| `AI_README.md` | 스트리밍·개발 메모 |

## 설치

```bash
cd 급여프로그램
pip install -r requirements.txt
```

`requirements.txt`에 `openai>=1.0` 포함.

## 환경 변수 (선택)

`.env.example` 참고:

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | 전사/배포 PC 공용 키 (선택) |
| `OPENAI_MODEL` | 기본 `gpt-5.5` (env가 사용자 설정보다 우선) |

Windows (PowerShell):

```powershell
$env:OPENAI_API_KEY = "sk-..."
$env:OPENAI_MODEL = "gpt-5.5"
```

## API 키 위치 (우선순위)

1. **Personal AI → API 설정** — `%AppData%`/앱 데이터 아래  
   `workspace/{tenant_id}/users/{user_id}/openai_settings.json`
2. **`OPENAI_API_KEY` 환경변수**

키를 소스·Git·PyInstaller 번들에 넣지 마세요.

## 실행·테스트

```bash
python main.py
```

1. 로그인
2. 사이드바 **「✨ Personal AI」**
3. 질문 입력 후 전송 (Ctrl+Enter)

단위 테스트 (네트워크 불필요):

```bash
python -m unittest tests.test_ai_chat -v
```

스모크:

```bash
python -c "from services.ai_assistant import ask_assistant; print('ok', ask_assistant)"
python -c "from app_ui import PayrollDashboard; print('ok', PayrollDashboard)"
```

## API 동작

- **1차**: OpenAI **Responses API** (`client.responses.create`)
- **폴백**: Chat Completions (`/v1/chat/completions`), 모델 `gpt-4o-mini` 재시도
- API 키 없음: 로컬 급여·할 일 데이터만으로 답변 + API 등록 안내

`chat_with_agent(message, session, conversation_id)` →  
`{ "answer", "responseId", "conversationId" }`

## 보안

- `ai_safety_policy.py`: 플랫폼·권한·명부·급여 산출 변경 요청 차단
- AI 파일 쓰기: 개인 `workspace/.../ai_assets`, 월별보고 폴더만
- API 키·비밀번호 출력 금지 (프롬프트 + 요청 필터)

## 향후 DB 연동 (TODO)

- `ai_user_context.get_user_context` — 부서·직급·최근 업무 DB
- `ai_assistant` — `conversationId` 영구 저장·rate limit
- `ai_chat_stream.py` — Tkinter 스트리밍 UI

## 스트리밍

현재 비활성. `services/ai_chat_stream.py` 및 `AI_README.md` 참고.
