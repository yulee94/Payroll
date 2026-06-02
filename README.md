# Bitween Payroll

Bitween Payroll은 Python 3 + Tkinter 기반의 데스크톱 업무 플랫폼입니다. 현재 급여 산출을 중심으로 전자결재, HR, KPI, 회계, 입찰, 정비, Personal AI 기능을 하나의 사내 B2B 운영 도구로 확장하고 있습니다.

## 주요 기능

- 도급비 청구서 업로드 기반 급여대장, 급여명세서, 지급내역 자동 생성
- 근로자 명부, 연차 사용대장, 월별 보고, 급여차이 보고 관리
- 법인/테넌트 기반 데이터 분리와 사용자 권한 관리
- 업무/전자결재 허브: 결재함, 기안, 승인/반려, 실행업무, 월마감 MVP
- HR, 채용, KPI, 정비, 입찰, 회계 모듈 MVP
- OpenAI 기반 Personal AI 업무 보조 기능

## 실행 환경

- Windows 데스크톱
- Python 3.11 이상 권장
- 주요 의존성: `openpyxl`, `openai`, `windnd`, `matplotlib`

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## 개발 구조

| 경로 | 역할 |
| --- | --- |
| `main.py` | 앱 시작과 급여 산출 진입점 |
| `app_ui.py` | 메인 Tkinter 대시보드, 사이드바, 페이지 라우팅 |
| `ui/` | 화면 패널과 다이얼로그 |
| `core/` | 플랫폼, 권한, 테넌트, 워크플로우, 도메인 서비스 |
| `services/` | 급여, AI, 아카이브, 보고, 설정 등 응용 서비스 |
| `docs/` | 설계 문서와 연동 가이드 |
| `tests/` | 기능별 단위 테스트 |

## 테스트

네트워크가 필요 없는 핵심 테스트부터 돌립니다.

```powershell
python -m unittest tests.test_ai_chat tests.test_workflow tests.test_org_access tests.test_preview_grid_filter -v
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

변경 후 테스트를 통과시키고 PR로 병합합니다.

## 상용화 방향

현재는 데스크톱 MVP에서 상용 제품으로 전환하는 단계입니다. 우선순위는 보안, 성능, 데이터 분리, 테스트 자동화, 배포/업데이트 안정화입니다. 세부 로드맵은 `docs/COMMERCIALIZATION_READINESS.md`를 참고하세요.
