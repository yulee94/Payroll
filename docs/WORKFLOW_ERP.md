# Bitween ERP / 워크플로우 MVP

Python 3 + Tkinter 데스크톱 앱에 확장 가능한 **전자결재·업무 허브** MVP가 추가되었습니다.  
(프롬프트의 Next.js/Prisma 경로는 별도 `packages/payroll-engine` 스캐폴드용이며, **운영 UI는 급여프로그램**입니다.)

## 접속 경로 (데스크톱)

| 화면 | 이동 방법 |
|------|-----------|
| 플랫폼 홈 | 사이드바 **플랫폼 홈** → 카드 **업무 · 전자결재** |
| 워크플로우 허브 | 사이드바 **업무 · 전자결재** (탭: 홈 / 결재함 / 작성 / 실행업무 / 보고 / 월마감) |

## 결재함 (시장 표준 MVP)

다우오피스·네이버웍스·잔디·SAP Concur와 유사한 분류 (`core/workflow/inbox.py`):

| 함 | 설명 |
|----|------|
| 결재할 문서 | 내 결재 차례 |
| 진행함 | 내 기안·결재 진행 중 |
| 완료함 | 승인·실행완료·마감 |
| 반려함 | 반려·취소 |
| 임시저장 | 작성 중·보완 요청 |
| 참조함 | 결재선·참조자 |
| 전체 | 열람 가능 문서 전체 |

REST API (`/api/workflow/...`)는 **서비스 함수**로 구현되어 있으며, 향후 HTTP 서버 레이어를 붙일 수 있습니다.

## 데이터 저장

- 경로: `{app_data_dir}/workflow/{tenant_id}/database.json`
- 개발: `급여프로그램/workflow/{tenant}/database.json`
- 설치본: `%LOCALAPPDATA%\Bitween\Payroll\workflow\{tenant}\database.json`
- **마이그레이션**: 최초 로그인 후 워크플로우 화면 진입 시 샘플 데이터 자동 시드 (`core/workflow/seed.py`)

## 환경변수 (AI)

- `OPENAI_API_KEY` — AI 기안 도우미·임원 요약 (선택)
- `OPENAI_MODEL` — 기본 `gpt-5.5` 등 (`services/openai_client.py` 참고)
- 또는 **Personal AI → API 설정** (계정별 저장)

## 실행

```powershell
cd c:\Users\MY\Desktop\payroll\급여프로그램
pip install -r requirements.txt
python main.py
```

로그인 후 **업무 · 전자결재** 메뉴 이용.

## 테스트

```powershell
python -m unittest tests.test_workflow -v
```

## 구현 완료 (MVP)

- 공통 문서 상태·유형·결재 단계 모델
- 문서 CRUD, 상신, 승인/반려/보완요청
- 승인 후 실행업무 자동 생성·완료 처리
- 근태/구매/지출 payload 저장 (문서별 확장 테이블)
- 사업장·임원 대시보드 집계
- 감사로그·알림 구조
- AI 기안 초안 (`services/workflow_ai.py`)
- 샘플 시드 (본사·밀양·부산·경남, 샘플 기안/구매/지출/연차)

## TODO (확장)

- HTTP REST 래퍼 (`/api/workflow/...`)
- 첨부파일 실제 업로드 (metadata만 설계됨)
- 월마감 잠금·재오픈 API
- 댓글 UI, 결재라인 편집 UI
- 회계 ERP·그룹웨어 연동
- Prisma/PostgreSQL 이전 (다중 사용자 동시성)

## 주요 파일

| 영역 | 경로 |
|------|------|
| 상수 | `core/workflow/constants.py` |
| 저장소 | `core/workflow/store.py` |
| 권한 | `core/workflow/permissions.py` |
| 비즈니스 | `core/workflow/service.py` |
| 시드 | `core/workflow/seed.py` |
| AI | `services/workflow_ai.py` |
| UI | `ui/workflow_hub_panel.py` |
| 플랫폼 등록 | `core/platforms.py`, `app_ui.py` |
