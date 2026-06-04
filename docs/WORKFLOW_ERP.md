# Bitween ERP / 워크플로우

Python 3 + Tkinter 데스크톱 앱에 확장 가능한 **전자결재·업무 허브**가 추가되었습니다.
(프롬프트의 Next.js/Prisma 경로는 별도 `packages/payroll-engine` 스캐폴드용이며, **운영 UI는 급여프로그램**입니다.)

## 접속 경로 (데스크톱)

| 화면 | 이동 방법 |
|------|-----------|
| 플랫폼 홈 | 사이드바 **플랫폼 홈** → 카드 **업무 · 전자결재** |
| 워크플로우 허브 | 사이드바 **업무 · 전자결재** (탭: 홈 / 결재함 / 작성 / 실행업무 / 보고 / 월마감) |
| 출장 lifecycle | 워크플로우 **양식함 → 출장 신청**, **실행업무**, **보고 → 출장 현황** |
| 연동 표면 | 플랫폼 홈 **캘린더 / Daily To-Do**, KPI 허브 **개인 KPI** |

## 결재함 (시장 표준)

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

## 출장 lifecycle (production scope)

출장은 문서 상태와 별도의 lifecycle 상태를 유지합니다. 결재문서, 실행업무, 업무일지/출장보고서,
캘린더/To-Do, KPI 실적반영이 같은 `trip_id`로 추적됩니다.

| 단계 | 상태 / 표면 | 구현 |
|------|-------------|------|
| 출장계획 | `draft → planned` | `출장신청서` 작성·상신 시 lifecycle 1건 생성/갱신 |
| 출장승인 | `approved` | 최종 승인 시 실행업무 자동 생성, 캘린더·To-Do source link 생성 |
| 출장실행 | `in_progress / diary_due / overdue` | 실행업무 완료 시 업무일지/보고 단계로 전이, 지연 평가는 권한 있는 관리자 명령으로 escalation |
| 업무일지/보고 | `일일업무일지`, `출장보고서` | 양식함 필드에 `trip_id` 연결, 실행업무 완료 후 출장보고서 승인 시 lifecycle 완료 |
| 실적반영 | `blocked → ready → reflected` | 실행업무 완료와 승인된 출장보고서가 모두 있는 건만 KPI 반영 가능, KPI 개인 실적 row로 idempotent 반영 |

관리자/상급자 조회는 `core/workflow/permissions.py`의 site/department/manager access matrix를 통과한
출장만 표시합니다. Workflow Hub 보고 탭의 **출장 현황**은 진행/완료/지연 섹션과 KPI 반영 상태를 표시합니다.
Workspace Hub는 workflow에서 생성된 캘린더/To-Do 항목에 `전자결재`, `결재`, `실행업무`, `출장 지연`
라벨을 붙입니다. KPI Hub의 개인 KPI 카드에는 출장 실적 반영 건수가 표시됩니다.
그룹 루트 DB에 여러 법인 workflow가 저장되더라도 출장 lifecycle은 `origin_tenant_id` / `legal_entity_id`로
법인 권한을 다시 검증합니다. 따라서 같은 그룹의 형제 법인 관리자는 명시적 그룹 HQ 권한이 없는 한
다른 법인의 출장 현황, 실행업무, 출장보고서 side effect, KPI 반영을 볼 수 없습니다.
수기/보정 lifecycle API도 동일하게 실행업무 증빙 없이는 `diary_due/overdue`, 완료된 실행업무와 승인된
동일 출장보고서 없이는 `completed/ready/reflected` 상태를 만들거나 실적반영할 수 없습니다.

Lifecycle row에는 운영 감사와 상급자 view에 필요한 durable evidence도 함께 저장합니다.
주요 필드: `traveler_user_id`, `traveler_name`, `plan_document_id`, `execution_task_id`,
`planned_start/planned_end`, `actual_start/actual_end`, `diary_due_at`, `completed_at`, `overdue_at`,
`kpi_record_id`, `escalation_level`, `last_escalated_at`, `escalation_target_user_ids`.

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
python -m unittest tests.test_business_trip_lifecycle tests.test_business_trip_workflow_integration tests.test_business_trip_followup_kpi_manager tests.test_business_trip_ui_surfaces -v
```

## 구현 완료

- 공통 문서 상태·유형·결재 단계 모델
- 문서 CRUD, 상신, 승인/반려/보완요청
- 승인 후 실행업무 자동 생성·완료 처리
- 출장 lifecycle: 출장신청서 → 승인/실행업무 → 지연 escalation → KPI 실적반영
- 캘린더·To-Do source link idempotency
- 근태/구매/지출 payload 저장 (문서별 확장 테이블)
- 사업장·임원 대시보드 집계
- 관리자 출장 현황 대시보드 (진행/완료/지연/KPI 상태)
- 감사로그·알림 구조
- AI 기안 초안 (`services/workflow_ai.py`)
- 샘플 시드 (본사·밀양·부산·경남, 샘플 기안/구매/지출/연차)

## 향후 확장

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
