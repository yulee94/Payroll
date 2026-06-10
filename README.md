# Bitween Payroll

Bitween Payroll은 급여·HR·전자결재·업무 관리·자료함을 하나의 사내 B2B 운영 플랫폼으로 연결하는 제품입니다. 생산 배포 목표는 **Kubernetes-native Rust backend + TypeScript frontend**입니다.

Python 구현은 G028에서 decommission되었습니다. 새 Python 소스, 스크립트, 테스트, 라이브 배선은 금지합니다. 과거 동작 보존은 Rust Buck2 테스트, TypeScript 계약, 런타임 검증 게이트가 담당합니다.

## 주요 기능

- 급여 운영: 근태/급여 입력 마감, 공제 검토, 계산, 결재 요청, 지급 자료 준비, 증빙 보관
- HR 운영: 직원 등록·수정·퇴사, HR 변경이 급여 작업에 미치는 영향 표시
- 업무 관리: 편집 가능한 기업 업무 그래프, 단계·분기·담당·권한·SLO·실행 기록 관리
- 전자결재: 서명과 승인/반려가 필요한 결정 큐
- 자료함: 모든 파일 원본은 RustFS에 보관하고, HR/Payroll 데이터는 검토 후 PostgreSQL로 반영
- 설정/보안: Korean-first i18n, JWT/OIDC/WebAuthn/passkey, ABAC+RBAC+PBAC, 민감정보 보호

## Production stack

| Layer | Target | Repository surface |
| --- | --- | --- |
| Frontend | TypeScript / React Native shell, browser preview | `apps/bitween-platform-ui/`, `frontend/` |
| Backend APIs | Idiomatic Rust services and domain crates | `crates/` and future Rust service crates |
| Relational data | PostgreSQL with tenant/legal-entity/workplace isolation | `crates/payroll-api/migrations/` |
| Object storage | RustFS-compatible object storage for originals and evidence | `docs/ARCHIVE_INTAKE_CLOUD_NATIVE.md` |
| Runtime | Managed Kubernetes, GitOps-ready manifests, observability, rollback evidence | `deploy/kubernetes/`, `docs/KUBERNETES_NATIVE_STACK.md` |
| Legacy Python | Removed from repo-owned source | guarded by `npm run verify:no-python-source` |

## Local development

Recommended toolchain:

- Buck2 for Rust build/check/test/lint
- Node.js 22+ for TypeScript contracts and platform UI
- No Python runtime for repo-owned development paths

Rust verification:

```powershell
buck2 build //...
buck2 test //...
buck2 build '//crates/payroll-api:payroll_api[check]' '//crates/workflow-core:workflow_core[check]'
buck2 build '//crates/payroll-api:payroll_api[clippy.txt]'
```

Retired Cargo commands are blocked: `cargo build`, `cargo check`, `cargo test`, `cargo clippy`, `cargo run`, `cargo bench`, and similar Rust verification shortcuts. Use target-specific Buck2 `[check]` and `[clippy.txt]` targets for changed Rust crates; do not use unsupported recursive provider shortcuts for check/clippy. Allowed Cargo use is limited to `cargo metadata`, `cargo install`, and `cargo vendor` for Buck/Reindeer inputs.

TypeScript verification:

```powershell
cd frontend
npm install
npm run typecheck

cd ../apps/bitween-platform-ui
npm install
npm run verify:no-python-source
npm run verify:data-mode
npm run verify:i18n
npm run typecheck
```

## 개발 구조

| 경로 | 역할 |
| --- | --- |
| `crates/` | Rust backend domain/API/validation/service boundaries |
| `crates/payroll-api/migrations/` | PostgreSQL schema and migration contracts |
| `apps/bitween-platform-ui/` | TypeScript React Native platform UI shell and browser preview |
| `frontend/` | Shared TypeScript frontend contracts and DTO guards |
| `deploy/kubernetes/` | Managed-Kubernetes deployment, network policy, observability, rollback artifacts |
| `docs/` | Architecture, API, Kubernetes, security, archive, and migration documentation |

## 급여 자동화 구조

- `crates/payroll-api` owns request parsing, validation, payroll/domain calculations, platform view-models, auth/session verification, authorization decisions, PostgreSQL repository contracts, and RustFS archive intake boundaries.
- `frontend/src/contracts/payrollApi.ts` provides frontend request/response DTOs using the same stable field names.
- `apps/bitween-platform-ui/preview/server.js` is a thin local-review adapter that calls Rust/Buck2 targets and fails closed without explicit local-review or production storage configuration.
- `/api/platform/v1/view-model` is backed by Rust platform view data; operator UI must not expose technical readiness/source walls.

## 테스트

Core Rust/TypeScript gates:

```powershell
buck2 build //...
buck2 test //...
buck2 build '//crates/payroll-api:payroll_api[check]' '//crates/workflow-core:workflow_core[check]'
buck2 build '//crates/payroll-api:payroll_api[clippy.txt]'
cd frontend && npm run typecheck
cd ../apps/bitween-platform-ui
npm run verify:no-python-source
npm run verify:buck2-only
npm run verify:security-gates
npm run verify:auth-session
npm run verify:route-authorization
npm run verify:data-mode
npm run verify:i18n
npm run typecheck
```

## 민감 데이터 원칙

급여, 직원정보, 개인 API 키, 로그인 세션, 테넌트 런타임 데이터, 그룹웨어 쿠키/응답 원문은 GitHub에 커밋하지 않습니다. `.gitignore`는 운영 데이터 폴더와 명부성 Excel 파일을 제외하도록 설정되어 있습니다.

커밋 전 확인할 항목:

```powershell
git status --short
cd apps/bitween-platform-ui && npm run verify:sensitive-data
```

다음 항목이 보이면 커밋하지 않습니다.

- `employees/`, `output/`, `월별보고/`, `급여차이내역/`, `연차사용대장/`
- `session.json`, `tenants.json`, `employee_dump.json`
- `근로자명부*.xlsx`, 직원 명부/재직증명서/연차관리 Excel
- 실제 API 키, 비밀번호, 쿠키, 그룹웨어 세션 정보
