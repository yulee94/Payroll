# Bitween ERP / 워크플로우

Bitween Workflow is the ERP work-cycle domain for electronic approval, execution tasks, reports, business trips, calendar/To-Do links, KPI reflection, and manager dashboards. Production delivery targets the Kubernetes-native Rust API and TypeScript frontend stack described in `docs/KUBERNETES_NATIVE_STACK.md`.

## Frontend routes

| Surface | Route / view intent |
|------|-----------|
| Platform home | Work queue, calendar, Daily To-Do, KPI and workflow summary cards |
| Workflow hub | Home / approval inbox / compose / execution tasks / reports / month close |
| Business trip lifecycle | Form box → business trip request, execution task, report, manager trip status |
| Linked surfaces | Calendar, Daily To-Do, business trip request, daily work log, business trip report, KPI hub |

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

REST API (`/api/workflow/...`) is currently represented by service functions and must be wrapped by the Rust HTTP layer for production.

## 출장 lifecycle (production scope)

출장은 문서 상태와 별도의 lifecycle 상태를 유지합니다. 결재문서, 실행업무, 업무일지/출장보고서, 캘린더/To-Do, KPI 실적반영이 같은 `trip_id`로 추적됩니다.

| 단계 | 상태 / 표면 | 구현 |
|------|-------------|------|
| 출장계획 | `draft → planned` | `출장신청서` 작성·상신 시 lifecycle 1건 생성/갱신 |
| 출장승인 | `approved` | 최종 승인 시 실행업무 자동 생성, 캘린더·To-Do source link 생성 |
| 출장실행 | `in_progress / diary_due / overdue` | 실행업무 완료 시 업무일지/보고 단계로 전이, 지연 평가는 Kubernetes CronJob 또는 명시적 관리자 작업으로 escalation |
| 업무일지/보고 | `일일업무일지`, `출장보고서` | 양식함 필드에 `trip_id` 연결, 업무일지는 진행 증빙으로 연결하고 실행업무 완료 후 승인된 출장보고서가 있을 때 lifecycle 완료 |
| 실적반영 | `blocked → ready → reflected` | 실행업무 완료와 승인된 동일 출장보고서가 모두 있는 건만 KPI 반영 가능, KPI 개인 실적 row로 idempotent 반영 |

관리자/상급자 조회는 `core/workflow/permissions.py`의 site/department/manager access matrix를 통과한 출장만 표시합니다. Workflow Hub 보고 탭의 **출장 현황**은 진행/완료/지연 섹션과 KPI 반영 상태를 표시합니다. Workspace/Platform surfaces show calendar and To-Do source links with labels such as `전자결재`, `결재`, `실행업무`, `출장 지연`. KPI Hub personal cards include reflected trip performance counts.

그룹 루트 DB에 여러 법인 workflow가 저장되더라도 출장 lifecycle은 `origin_tenant_id` / `legal_entity_id`로 법인 권한을 다시 검증합니다. 따라서 같은 그룹의 형제 법인 관리자는 명시적 그룹 HQ 권한이 없는 한 다른 법인의 출장 현황, 실행업무, 업무일지/출장보고서 side effect, KPI 반영을 볼 수 없습니다. 수기/보정 lifecycle API도 동일하게 실행업무 증빙 없이는 `diary_due/overdue`, 완료된 실행업무와 승인된 동일 출장보고서 없이는 `completed/ready/reflected` 상태를 만들거나 실적반영할 수 없습니다. 초안/상신 중인 보고서는 완료 증빙을 대체하지 않으며, 보고서 판별은 제목/요약이 아니라 payload의 `business_trip_artifact`, `artifact_type`, `gw_template_id`, `gw_form_name` 같은 안정적인 양식 metadata를 우선합니다.

Lifecycle row에는 운영 감사와 상급자 view에 필요한 durable evidence도 함께 저장합니다. 주요 필드: `traveler_user_id`, `traveler_name`, `plan_document_id`, `execution_task_id`, `planned_start/planned_end`, `actual_start/actual_end`, `diary_due_at`, `completed_at`, `overdue_at`, `kpi_record_id`, `escalation_level`, `last_escalated_at`, `escalation_target_user_ids`.


Rust migration checkpoint (2026-06-04): the pure lifecycle taxonomy, source normalization, migration/view-model shaping, source dedupe matching, and status-transition rule now live in `crates/workflow-core::business_trip`; supplied-profile lifecycle legal-scope, visibility, manage, administration, and overdue-evaluator predicates now live in `crates/workflow-core::business_trip_permissions`. Python still owns JSON persistence, `UserSession` adaptation, authorization profile lookup, document/task/report/KPI side effects, overdue escalation execution, notifications, calendar/To-Do links, and UI bridge behavior until those boundaries are ported behind parity tests.

## Data and persistence

Compatibility storage:

- `{app_data_dir}/workflow/{tenant_id}/database.json`
- Development fixture path: `workflow/{tenant}/database.json`
- Seed path: `core/workflow/seed.py`

Production target:

- Rust workflow service behind `/api/workflow/v1/*`.
- Database/object storage behind Rust repositories.
- Overdue evaluation and KPI reflection as Kubernetes CronJobs or idempotent workers.
- Secrets and AI credentials injected through Kubernetes Secrets or an external secret manager.

## 환경변수 (AI)

- `OPENAI_API_KEY` — AI 기안 도우미·임원 요약 (선택)
- `OPENAI_MODEL` — 기본 `gpt-5.5` 등 (`services/openai_client.py` 참고)
- 또는 Personal AI account settings (tenant/user scoped)

## Local compatibility checks

```powershell
python -m unittest tests.test_workflow -v
python -m unittest tests.test_business_trip_lifecycle tests.test_business_trip_workflow_integration tests.test_business_trip_followup_kpi_manager tests.test_business_trip_ui_surfaces -v
```

## 구현 완료

- 공통 문서 상태·유형·결재 단계 모델
- 문서 CRUD, 상신, 승인/반려/보완요청
- 승인 후 실행업무 자동 생성·완료 처리
- 출장 lifecycle: 출장신청서 → 승인/실행업무 → 지연 escalation → 업무일지 기록/출장보고서 승인 → KPI 실적반영
- 캘린더·To-Do source link idempotency
- 근태/구매/지출 payload 저장 (문서별 확장 테이블)
- 사업장·임원 대시보드 집계
- 관리자 출장 현황 대시보드 (진행/완료/지연/KPI 상태)
- 감사로그·알림 구조
- AI 기안 초안 (`services/workflow_ai.py`)
- 샘플 시드 (본사·밀양·부산·경남, 샘플 기안/구매/지출/연차)

## 향후 확장

- Rust HTTP REST wrapper (`/api/workflow/v1/...`)
- Production database migration and Kubernetes migration Jobs
- Attachment object storage
- Month-close lock/reopen APIs
- Comments and approval-line editing surfaces
- Accounting ERP and groupware integrations

## 주요 파일

| 영역 | 경로 |
|------|------|
| 상수 | `core/workflow/constants.py` |
| 저장소 | `core/workflow/store.py` |
| 권한 | `core/workflow/permissions.py` |
| 비즈니스 | `core/workflow/service.py` |
| 시드 | `core/workflow/seed.py` |
| AI | `services/workflow_ai.py` |
| Production UI target | `apps/bitween-platform-ui/`, `frontend/` |
| Production target | Rust workflow service under future `crates/` service crates |
