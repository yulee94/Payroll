# Bitween Payroll

Bitween Payroll은 Python 3 + Tkinter 기반의 데스크톱 업무 플랫폼입니다. 현재는 급여 산출을 최우선으로 상용화 기반을 다지고 있으며, 이후 전자결재, HR, KPI, 회계, 입찰, 정비, Personal AI 기능을 하나의 사내 B2B 운영 도구로 확장합니다.

## 주요 기능

- 도급비 청구서 업로드 기반 급여대장, 급여명세서, 지급내역 자동 생성
- 청구서, 지문근태, 청구서+근태 혼합 입력을 같은 급여 자동화 서비스로 처리할 수 있는 API-ready 구조
- 법인/테넌트 및 사업장별 급여 운영 기준 관리: 입력 방식, 지급일, 지문근태 반올림, 지각/조퇴 유예, 누락 출퇴근 처리
- 근로자 명부, 연차 사용대장, 월별 보고, 급여차이 보고 관리
- 법인/테넌트 기반 데이터 분리와 사용자 권한 관리
- 업무/전자결재 허브: 결재함, 기안, 승인/반려, 실행업무, 월마감 MVP
- HR, 채용, KPI, 정비, 입찰, 회계 모듈 MVP
- OpenAI 기반 Personal AI 업무 보조 기능

## 실행 환경

- Windows 데스크톱
- Python 3.11 이상 권장
- Rust stable: 급여 API 검증/계약 코어 전환용
- Node.js 20 이상: TypeScript 프론트 계약/클라이언트 전환용
- 주요 의존성: `openpyxl`, `openai`, `windnd`, `matplotlib`, `requests`

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## 개발 구조

| 경로 | 역할 |
| --- | --- |
| `main.py` | 앱 시작과 기존 청구서 급여 산출 진입점 |
| `app_ui.py` | 메인 Tkinter 대시보드, 사이드바, 페이지 라우팅 |
| `ui/` | 화면 패널과 다이얼로그 |
| `core/` | 플랫폼, 권한, 테넌트, 워크플로우, 도메인 서비스 |
| `services/` | 급여 자동화, 설정, 근태 변환, AI, 아카이브, 보고 등 응용 서비스 |
| `crates/` | Rust 전환용 백엔드 도메인/계약 라이브러리 |
| `frontend/` | TypeScript 프론트 계약과 향후 웹 UI 작업 영역 |
| `tests/` | 기능별 단위 테스트 |

## 급여 자동화 구조

- `services/payroll_automation.py`가 청구서/근태/혼합 입력을 받는 공통 백엔드 진입점입니다.
- `services/payroll_api_adapter.py`가 JSON에 가까운 API 요청/응답 형태를 내부 급여 자동화 요청으로 변환합니다.
- `services.payroll_api_adapter.validate_payroll_api_payload()`로 산출 전 요청 검증만 수행할 수 있습니다.
- `crates/payroll-api`가 같은 요청/응답 계약을 Rust 타입과 검증 코어로 제공합니다.
- `frontend/src/contracts/payrollApi.ts`가 프론트엔드에서 사용하는 TypeScript 요청/응답 타입을 제공합니다.
- `services/payroll_api_contract.py`와 `docs/PAYROLL_API_CONTRACT.md`가 향후 HTTP 래퍼/외부 연동에서 사용할 요청·응답 계약을 고정합니다.
- `services/payroll_readiness.py`가 명부, 운영 기준, 산출 자료, API 계약 준비 상태를 UI/API 공통 스냅샷으로 제공합니다.
- `services/payroll_policy_store.py`가 법인 기본값과 사업장별 운영 기준을 저장하고 해석합니다.
- `services/attendance_import.py`와 `services/attendance_invoice_bridge.py`가 외부 근태 파일을 기존 급여 엔진이 읽을 수 있는 청구서형 데이터로 변환합니다.
- `services/payroll_ui_bridge.py`와 `services/payroll_settings_ui_bridge.py`가 데스크톱 UI를 새 자동화 서비스와 설정 UX에 연결합니다.
- `services/ui_performance.py`는 대시보드 화면을 필요한 순간에 만드는 방식으로 시작 체감 속도를 줄입니다.

## 테스트

PR 자동검사와 동일한 핵심 테스트부터 실행합니다.

```powershell
python -m unittest tests.test_attendance_import tests.test_payroll_api_adapter tests.test_payroll_api_contract tests.test_payroll_automation tests.test_payroll_operation_policy tests.test_payroll_readiness tests.test_payroll_ui_bridge tests.test_payroll_settings_ui_bridge tests.test_preview_grid_filter tests.test_workflow tests.test_org_access -v
```

Rust/TypeScript 전환 영역은 각 도구가 설치된 환경에서 실행합니다.

```powershell
cargo test --workspace
cd frontend
npm install
npm run typecheck
```

전체 테스트는 변경 범위가 넓을 때 실행합니다.

```powershell
python -m unittest discover tests -v
```

## 민감 데이터 원칙

급여, 직원정보, 개인 API 키, 로그인 세션, 테넌트 런타임 데이터, 그룹웨어 쿠키/응답 원문은 GitHub에 커밋하지 않습니다. `.gitignore`는 운영 데이터 폴더와 명부성 Excel 파일을 제외하도록 설정되어 있습니다.

커밋 전 확인할 항목:

```powershell
git status --short
```

다음 항목이 보이면 커밋하지 않습니다.

- `employees/`, `output/`, `월별보고/`, `급여차이내역/`, `연차사용대장/`
- `session.json`, `tenants.json`, `employee_dump.json`
- `근로자명부*.xlsx`, 직원 명부/재직증명서/연차관리 Excel
- 실제 API 키, 비밀번호, 쿠키, 그룹웨어 세션 정보

## 개발 흐름

`main`은 안정 브랜치로 유지하고, 기능 작업은 `codex/<topic>` 브랜치에서 진행합니다.

```powershell
git checkout main
git pull origin main
git checkout -b codex/my-feature
```

변경 후 테스트를 통과시키고 PR로 병합합니다. 다른 개발자와 동시에 작업할 때는 저장소 collaborator 초대, 초대 수락, 저장소 clone, 브랜치 분리까지 완료해야 같은 프로젝트를 안전하게 이어갈 수 있습니다.

## 상용화 방향

현재 단계는 데스크톱 MVP에서 상용 제품으로 전환하기 위한 급여 자동화 기반 구축입니다. 우선순위는 급여 산출 정확도, 설정 UX, 성능, 데이터 분리, 테스트 자동화, 배포/업데이트 안정화입니다. AI와 다른 Bitween 모듈은 급여 자동화의 입력/결과 구조가 안정된 뒤 순차적으로 연결합니다.
