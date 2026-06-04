# Bitween Payroll

Bitween Payroll은 급여·HR·전자결재·업무일지·출장 lifecycle·KPI를 하나의 사내 B2B 운영 플랫폼으로 연결하는 제품입니다. 생산 배포 목표는 **Kubernetes-native Rust backend + TypeScript frontend**입니다.

기존 Python 서비스는 Rust 전환 전까지 동작을 고정하는 호환 어댑터와 characterization source로만 유지합니다.

## 주요 기능

- 도급비 청구서, 근태, 청구서+근태 혼합 입력을 같은 급여 자동화 계약으로 처리
- 법인/테넌트 및 사업장별 급여 운영 기준 관리: 입력 방식, 지급일, 지문근태 반올림, 지각/조퇴 유예, 누락 출퇴근 처리
- 근로자 명부, 연차 사용대장, 월별 보고, 급여차이 보고 관리
- 법인/테넌트 기반 데이터 분리와 사용자 권한 관리
- 업무/전자결재 허브: 결재함, 기안, 승인/반려, 실행업무, 보고, 월마감
- 출장 lifecycle: 출장계획 → 출장승인/실행 → 업무일지/출장보고서 → KPI 실적반영 → 관리자 ongoing/completed/overdue view
- HR, 채용, KPI, 정비, 입찰, 회계, Personal AI 업무 보조 기능
- TypeScript frontend contracts and React Native platform shell for cross-platform UI delivery
- Rust payroll API contract crate as the first backend migration slice

## Production stack

Bitween production is designed to run as a Kubernetes-native stack:

| Layer | Target | Repository surface |
| --- | --- | --- |
| Frontend | TypeScript / React Native shell, web/mobile-ready | `apps/bitween-platform-ui/`, `frontend/` |
| Backend APIs | Idiomatic Rust services and domain crates | `crates/` and future Rust service crates |
| Compatibility | Python adapters and tests used only until Rust parity is proven | `services/`, `core/`, `tests/` |
| Runtime | Kubernetes Deployments/Services/Ingress, ConfigMaps/Secrets, CronJobs, probes, HPA | `docs/KUBERNETES_NATIVE_STACK.md` |
| Persistence | Production database/object storage behind Rust services; no local JSON store as production authority | API/domain docs |

Source-backed deployment direction is documented in `docs/KUBERNETES_NATIVE_STACK.md`. Kubernetes manifests or Helm/Kustomize overlays should be added under a dedicated deployment surface such as `deploy/kubernetes/` once Rust service images exist. The Rust backend rewrite backlog is documented in `docs/RUST_BACKEND_MIGRATION.md` and `.omx/backlog.md`.

## Local development

Recommended toolchain:

- Rust stable for backend domain/API crates
- Node.js 20+ for TypeScript contracts and platform UI
- Python 3.11+ only for compatibility adapters, migration characterization tests, and local tooling while Rust migration is in progress

```powershell
cargo test --workspace

cd frontend
npm install
npm run typecheck

cd ..\apps\bitween-platform-ui
npm install
npm run typecheck
```

Compatibility checks while the migration is incomplete:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m unittest tests.test_payroll_api_adapter tests.test_payroll_api_contract -v
```

## 개발 구조

| 경로 | 역할 |
| --- | --- |
| `crates/` | Rust backend domain/API/validation crates |
| `apps/bitween-platform-ui/` | TypeScript React Native platform UI shell and browser preview |
| `frontend/` | Shared TypeScript frontend contracts and DTO guards |
| `core/` | Compatibility domain modules and characterization source before Rust migration |
| `services/` | Compatibility service adapters before Rust migration |
| `tests/` | Compatibility, parity, and regression tests |
| `docs/` | Architecture, API, Kubernetes, migration, and integration documentation |

## 급여 자동화 구조

- `crates/payroll-api` provides Rust request parsing, validation, and response contracts for payroll API v1.
- `frontend/src/contracts/payrollApi.ts` provides frontend request/response DTOs using the same field names.
- `services/payroll_api_adapter.py` mirrors the contract for compatibility and characterization until the Rust service is authoritative.
- `services.payroll_api_adapter.validate_payroll_api_payload()` can validate a payload before running payroll generation.
- `services/payroll_api_contract.py` and `docs/PAYROLL_API_CONTRACT.md` freeze the HTTP wrapper contract.
- `services/payroll_readiness.py` exposes readiness snapshots used by current UI/API integration tests.
- `services/payroll_policy_store.py` stores and interprets affiliate/site payroll policies until moved behind Rust persistence.
- `services/attendance_import.py` and `services/attendance_invoice_bridge.py` transform external attendance files into payroll-compatible input rows.

## 테스트

Core compatibility suite:

```powershell
python -m unittest tests.test_attendance_import tests.test_payroll_api_adapter tests.test_payroll_api_contract tests.test_payroll_automation tests.test_payroll_operation_policy tests.test_payroll_readiness tests.test_payroll_ui_bridge tests.test_payroll_settings_ui_bridge tests.test_preview_grid_filter tests.test_workflow tests.test_org_access -v
```

Business trip/workflow suite:

```powershell
python -m unittest tests.test_business_trip_ui_surfaces tests.test_business_trip_followup_kpi_manager tests.test_business_trip_workflow_integration tests.test_business_trip_lifecycle tests.test_workflow_business_trip_contracts tests.test_workflow_forms tests.test_form_templates -v
```

Rust/TypeScript checks:

```powershell
cargo test --workspace
cd frontend && npm run typecheck
cd ../apps/bitween-platform-ui && npm run typecheck
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
git fetch origin --prune
git merge --ff-only origin/main
git checkout -b codex/my-feature
```

변경 후 테스트를 통과시키고 PR로 병합합니다. Rust backend, TypeScript frontend, Kubernetes deployment, documentation-only changes should remain reviewable as separate PRs unless a contract update requires a coordinated slice.

## 상용화 방향

상용화 기준은 Kubernetes-native 운영, Rust backend parity, TypeScript frontend delivery, tenant/legal-entity isolation, reproducible tests, observable runtime health, and safe data migration. Compatibility code is maintained only until each Rust slice is production-proven and explicitly decommissioned.
