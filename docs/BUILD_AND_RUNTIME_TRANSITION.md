# Buck2, Rust backend, Python cleanup, React Native, and Tauri transition plan

## Overview

This plan starts the next production track after the merged business-trip lifecycle PR. The target is a Kubernetes-native Rust backend, a Buck2-aware monorepo build graph, a React Native / TypeScript frontend source of truth, a Tauri desktop client for Windows/macOS/Linux, RBAC + ABAC authorization, Zero Trust boundaries, JWT/WebAuthn authentication, performance budgets, industry-leader maturity inspired by SAP, Remote People, and Workday, fully single-language i18n for Korean/English/Chinese/Japanese, Korean labor-market/labor-law localization, and staged Python decommissioning after Rust parity.

See `docs/decisions/ADR-001-buck2-rust-tauri-react-native-transition.md` for the accepted architecture decision and source links. Security/performance gates are in `docs/SECURITY_AND_PERFORMANCE_BASELINE.md`; SAP/Korean SME benchmark guidance is in `docs/SAP_KOREAN_SME_BENCHMARK.md`.

## Current baseline

| Area | Current state | Target state |
| --- | --- | --- |
| Backend | Python compatibility modules plus `crates/payroll-api` Rust contract crate on Rust 2024 / Rust 1.96 | Idiomatic Rust services/domain crates deployed on Kubernetes |
| Build | Cargo, npm, Python unittest commands, plus first Buck2/Reindeer Rust target for `crates/payroll-api` | Buck2 target graph for Rust, frontend export, desktop package, and CI target selection; Cargo/npm retained until Buck2 parity |
| Frontend | Expo / React Native / React Native Web app under `apps/bitween-platform-ui/` | Same React Native source exported for web, Kubernetes frontend, and Tauri desktop |
| Desktop | No production desktop surface | `apps/bitween-desktop-tauri/` wraps the React Native Web export and adds audited Tauri commands |
| Python | Production behavior still expressed by compatibility modules | Characterization-only evidence source; backend production ownership moves to Rust service/domain crates and Python is removed slice by slice after parity |
| Runtime | Kubernetes direction documented | Kubernetes manifests/images/jobs added after Rust service boundaries exist |
| Authorization | Python/Rust compatibility checks and org roles are still transitional | RBAC role families plus ABAC per-request policy checks in Rust services, workers, CronJobs, and desktop command boundaries |
| Security posture | Compatibility code preserves behavior | Zero Trust: every request authenticated, authorized, least-privilege, audited, and validated at the boundary |
| Authentication | Compatibility login/session patterns | WebAuthn/passkeys for privileged/default sign-in direction plus short-lived JWT API claims validated by Rust services |
| Product benchmark | Payroll/workflow platform direction | SAP/Remote People/Workday-inspired feature richness, role-specific UX, employee self-service, manager insights, real-time analytics, compliance cockpit, guided configuration, adapted to Korean SME compliance and adoption constraints |
| I18n/localization | Mixed Korean/English product copy in current docs/UI surfaces | Fully single-language Korean, English, Chinese, and Japanese UI modes with no missing-key fallback in production |
| Performance | Local tests/typechecks only | Core Web Vitals budgets for frontend/desktop; Rust service SLOs and Kubernetes metrics before autoscaling |

## Dependency graph

```text
Characterization tests
    │
    ├── Industry maturity + Korean SME benchmark + auth architecture
    │       │
    │       ├── SAP/Remote People/Workday maturity backlog
    │       ├── Guided setup and Korean labor-law policy registry
    │       ├── Full single-language i18n contract
    │       └── JWT/WebAuthn contract and tests
    │
    ├── RBAC/ABAC policy model + Zero Trust boundary map
    │       │
    │       └── Authorization/security regression tests
    │
    ├── Stable API/domain contracts
    │       │
    │       ├── Rust service/domain slices
    │       │       │
    │       │       ├── Kubernetes service/worker/job packaging
    │       │       └── Buck2 Rust targets
    │       │
    │       └── TypeScript DTOs and frontend adapters
    │               │
    │               ├── Expo web export
    │               └── Tauri desktop wrapper
    │
    └── Python decommission evidence
```


## Phase 0: Security, authorization, and performance gates

### Task 0: Freeze RBAC + ABAC and Zero Trust baseline

**Description:** Define the authorization and security posture before new Rust service, Tauri, or Buck2 rollout work can claim production readiness.

**Acceptance criteria:**

- [ ] Role families and ABAC attributes are documented for payroll, workflow, business trip, KPI, org/roles, mobile, AI, desktop, and service accounts.
- [ ] SAP/Remote People/Workday maturity priorities, Korean/English/Chinese/Japanese i18n, Korean labor-market/labor-law localization, and JWT/WebAuthn authentication requirements are documented.
- [ ] Every future Rust service slice identifies policy enforcement points at API, domain, repository, worker, CronJob, and Kubernetes service-account layers.
- [ ] Frontend and Tauri surfaces are documented as capability hints/clients, not authorization boundaries.
- [ ] Initial performance budgets are documented for frontend/desktop and Rust API services.
- [ ] UI/UX maturity gates cover role workspaces, employee self-service, manager insight hubs, compliance cockpit, lifecycle timelines, audit trails, accessibility, realistic Korean copy, and full single-language review for Korean/English/Chinese/Japanese.

**Verification:**

- [ ] Documentation review confirms each protected action names RBAC role families and ABAC attributes.
- [ ] Future implementation PRs add policy/auth regression tests before behavior changes.

**Dependencies:** None

**Files likely touched:**

- `docs/SECURITY_AND_PERFORMANCE_BASELINE.md`
- `docs/SAP_KOREAN_SME_BENCHMARK.md`
- `docs/BUILD_AND_RUNTIME_TRANSITION.md`
- future Rust policy modules and tests

**Estimated scope:** Small

### Task 0.1: Define Korean labor-law policy registry and UI maturity gates

**Description:** Convert the industry maturity benchmark into implementation-ready product gates before UI or backend feature slices claim production quality.

**Acceptance criteria:**

- [ ] Korean Labor Standards Act, minimum wage, work-family/equal-employment, four major social insurance, and e-tax/NTS policy areas have source/effective-date metadata requirements.
- [ ] Yearly legal thresholds, including minimum wage, are configuration-backed and not hardcoded into UI components.
- [ ] UI/UX review checklist covers Workday-like manager insights, Remote People-like self-service/compliance, SAP-like integrated process content, and Korean SME setup defaults.
- [ ] Legal-rule explanations are product policy summaries with official-source links and are not presented as legal advice.
- [ ] Performance and accessibility requirements are attached to rich dashboards before production release.

**Verification:**

- [ ] Documentation review confirms every legal threshold has a source/effective-date field.
- [ ] Future implementation PRs include policy-registry tests and UI maturity review evidence.

**Dependencies:** Task 0

**Files likely touched:**

- `docs/SAP_KOREAN_SME_BENCHMARK.md`
- `docs/FRONTEND_UI_GUIDE.md`
- `docs/I18N_LOCALIZATION.md`
- future policy registry docs, Rust policy modules, and frontend view models

**Estimated scope:** Small

### Task 0.2: Freeze full single-language i18n contract

**Description:** Define the localization architecture before React Native, Tauri, auth, legal-policy, and manager-dashboard slices expand user-facing copy.

**Acceptance criteria:**

- [ ] Supported locale tags are `ko-KR`, `en-US`, `zh-Hans-CN`, and `ja-JP`.
- [ ] Language selection precedence is documented for user profile, tenant policy, explicit selector, device/browser locale, and Korean default.
- [ ] UI copy is pulled from catalog arrays, not hardcoded in components.
- [ ] Production UI has no missing translation-key fallback or mixed-language screen states.
- [ ] Backend error/status codes remain stable and are localized by frontend/desktop clients.
- [ ] Legal/policy copy has source URL, source language, effective date, review date, and owner metadata.
- [ ] Tauri desktop shell copy follows the same localization source of truth as the React Native UI.

**Verification:**

- [ ] React Native implementation PRs run `npm run verify:i18n --prefix apps/bitween-platform-ui`, which checks translation completeness and rejects localized source copy outside the catalog.
- [ ] Future UI PRs run visual/manual review in Korean, English, Chinese, and Japanese.

**Dependencies:** Task 0 and Task 0.1

**Files likely touched:**

- `docs/I18N_LOCALIZATION.md`
- `docs/FRONTEND_UI_GUIDE.md`
- `apps/bitween-platform-ui/src/i18n/`

**Estimated scope:** Medium

## Phase 1: Build and runtime foundations

### Task 1: Inventory Buck2 target graph

**Description:** Map existing Cargo, npm, Expo, and Python checks into candidate Buck2 targets without changing the active build path.

**Acceptance criteria:**

- [ ] Candidate targets cover `crates/payroll-api`, `frontend`, `apps/bitween-platform-ui`, security/policy tests, and characterization tests.
- [x] Third-party Rust dependency handling uses Reindeer-generated, vendored Buck2 rules under `third-party/rust/`.
- [x] Buck2 package boundaries avoid symlinked sources; first-party Rust sources and Reindeer vendored inputs are declared in Buck targets.

**Verification:**

- [x] `cargo test --workspace`
- [ ] `npm run typecheck --prefix frontend`
- [ ] `npm run typecheck --prefix apps/bitween-platform-ui`
- [ ] Relevant Python characterization suite remains green.

**Dependencies:** None

**Files likely touched:**

- `docs/BUILD_AND_RUNTIME_TRANSITION.md`
- future `.buckconfig`, `BUCK`, and `third-party/` rule-generation files only after target design is reviewed

**Estimated scope:** Medium

### Task 2: Add first verified Buck2 Rust target

**Description:** Add Buck2 config for the smallest Rust target that can be verified against the existing Cargo build.

**Acceptance criteria:**

- [x] Buck2 builds/checks the selected Rust crate and test target.
- [x] Cargo remains an authoritative compatibility gate until Buck2 parity expands beyond the first Rust target.
- [x] First-party source files and Reindeer-managed dependencies are declared as Buck2 inputs for `crates/payroll-api`.

**Verification:**

- [x] `buck2 build //crates/payroll-api:payroll_api`
- [x] `cargo test --workspace`

**Dependencies:** Task 1

**Files likely touched:**

- `.buckconfig`
- `BUCK`
- `crates/payroll-api/BUCK`
- optional third-party generated Buck rules

**Estimated scope:** Medium

## Implementation checkpoint: Buck2/Reindeer Rust foundation

Completed on 2026-06-04 as the first build-system implementation slice:

- Buck2 root configuration and bundled toolchain cell are present.
- Reindeer manages vendored third-party Rust dependencies in `third-party/rust/`.
- `crates/payroll-api` has verified Buck2 `rust_library` and `rust_test` targets.
- Reindeer fixups are required (`unresolved_fixup_error = true`) for build scripts and Cargo compile-time env usage.
- The runbook is `docs/BUCK2_REINDEER_RUST_TRANSITION.md`.

Verified commands:

```sh
buck2 build //crates/payroll-api:payroll_api
buck2 test //crates/payroll-api:payroll_api_test
cargo test --workspace
```

## Phase 2: Rust backend transition

### Task 3: Freeze the next backend service contract

**Description:** Select the next Rust backend slice after payroll validation: likely workflow/business-trip lifecycle, KPI reflection, org/roles, or mobile attendance based on risk and existing tests.

**Acceptance criteria:**

- [x] Public request/response DTOs are documented for payroll validation and operation policy normalization.
- [x] Tenant/legal-entity authorization invariants, RBAC role families, and ABAC attributes are explicit in Rust service-boundary contracts.
- [x] Existing Python behavior has characterization tests before Rust code is added for payroll operation policy normalization.

**Verification:**

- [x] Targeted Python characterization tests pass for payroll operation policy and API adapter behavior.
- [x] Rust contract tests fail first for missing implementation, then pass after the slice lands.

**Dependencies:** Task 1

**Files likely touched:**

- `docs/PAYROLL_API_CONTRACT.md` or a new domain contract doc
- `crates/`
- `frontend/src/contracts/`
- `tests/`

**Estimated scope:** Medium

### Task 4: Ship the first production Rust service boundary

**Description:** Expand beyond pure contract validation into a service boundary with typed errors, observability hooks, health endpoints, and Kubernetes-ready configuration.

**Acceptance criteria:**

- [x] Rust owns the selected behavior behind a stable API facade for validation, policy normalization, policy resolution precedence, attendance aggregation, workplace-hours application, invoice audit row/batch evaluation, supplied-input earnings/gross/taxable-pay calculation, supplied-input salary calculation, final deduction/net-pay calculation, employment-insurance 65+ decisions, EDI insurance premium application, site-benefits application, fixed-hours application, execution planning, business-trip lifecycle normalization/transitions, authorization, run-result response shaping, health, and readiness.
- [ ] Python adapter is retained only as compatibility fallback while rollout is incomplete.
- [x] Health/readiness behavior is defined in framework-neutral Rust DTOs and API contracts.
- [x] Run-result success/error envelope behavior is defined in framework-neutral Rust DTOs and API contracts.
- [x] Tenant/site/global operation-policy resolution behavior is defined in framework-neutral Rust DTOs and API contracts for supplied settings snapshots.
- [x] Payroll execution routing/planning behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the compatibility executor.
- [x] Business-trip lifecycle normalization and status-transition behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the workflow persistence/document/task/report/KPI side-effect bridge.
- [x] Business-trip lifecycle legal-scope, visibility, and manage permission predicates are defined in framework-neutral Rust DTOs and API contracts while Python remains the profile resolver and side-effect bridge.
- [x] Business-trip lifecycle administration and overdue-evaluator permission predicates are defined in framework-neutral Rust DTOs and API contracts while Python remains the profile resolver and side-effect bridge.
- [x] Business-trip document relatedness and legal-scope predicates are defined in framework-neutral Rust DTOs and API contracts while Python remains the document/content resolver and side-effect bridge.
- [x] Workflow document view/edit/submit/approve permission predicates are defined in framework-neutral Rust DTOs and API contracts while Python remains the profile/org-capability resolver and approval mutation bridge.
- [x] Workflow site-report, month-close, and execution-task management permission predicates are defined in framework-neutral Rust DTOs and API contracts while Python remains the profile/task/site resolver and side-effect bridge.
- [x] Attendance-to-invoice aggregation behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the file parser/workbook bridge.
- [x] Workplace monthly-hours policy application behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the settings/canonical-workplace resolver.
- [x] Invoice audit row and batch behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the settings/ledger/fixed-profile resolver and workbook/UI bridge.
- [x] Supplied-input earnings, gross-pay, non-taxable-pay, and taxable-pay calculation behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the invoice/master/insurance/tax/deduction/final-record bridge.
- [x] Supplied-input one-employee salary calculation behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the invoice/master/age/EDI/workbook/final-record bridge.
- [x] Final deduction and net-pay calculation behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the workbook/roster/social-insurance/final-record bridge.
- [x] Employment-insurance 65+ payroll decision behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the KCOMWEL/settings/payroll-row/workbook bridge.
- [x] EDI insurance premium application behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the EDI import/storage/provider/settings/roster/workbook bridge.
- [x] Site-benefits payroll row application behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the settings/ledger/workbook/totals bridge.
- [x] Fixed-hours payroll row application behavior is defined in framework-neutral Rust DTOs and API contracts while Python remains the HR contract/settings resolver.
- [ ] Service-account permissions and initial latency/error budgets are defined for Kubernetes.

**Verification:**

- [x] Rust unit/integration tests pass.
- [x] Contract parity tests pass against Python compatibility fixtures for the contract metadata slice.
- [x] TypeScript payroll API DTO typecheck passes for the validation, policy-resolution, authorization, probe, and run-result envelope shapes.
- [x] TypeScript contract typecheck passes.

**Dependencies:** Task 3

**Files likely touched:**

- `crates/`
- `docs/KUBERNETES_NATIVE_STACK.md`
- `frontend/`
- `tests/`

**Estimated scope:** Medium

## Implementation checkpoint: payroll operation policy Rust invariants

Completed on 2026-06-04 as the first backend behavior-invariant slice after the
Buck2/Reindeer foundation:

- `crates/payroll-api` now has a typed `OperationPolicy` and `AttendancePolicy`
  matching the Python compatibility policy shape.
- Rust normalizes invalid input basis values to `hybrid`, clamps attendance
  minute settings to Python-compatible safe ranges, and types missing-clock
  handling as `warn`, `ignore`, or `deduct`.
- Rust validation responses serialize normalized policy fields before frontend or
  future HTTP clients consume them.
- The TypeScript contract in `frontend/src/contracts/payrollApi.ts` names the
  full normalized policy shape.
- Slice spec: `docs/PAYROLL_OPERATION_POLICY_RUST_SLICE.md`.

Verified commands:

```sh
cargo test -p bitween-payroll-api
buck2 test //crates/payroll-api:payroll_api_test
python -m unittest tests.test_payroll_operation_policy tests.test_payroll_api_adapter -v
npm run typecheck --prefix frontend
```

## Implementation checkpoint: Rust payroll authorization invariants

Completed on 2026-06-04 as a service-boundary hardening slice:

- `crates/payroll-api` owns payroll action authorization decisions through
  `authorize_payroll_request` and `PayrollApiService::authorize_run_request`.
- Trusted server/session/JWT wrappers supply `PayrollPrincipal`; frontend labels
  are explicitly not authorization input.
- Rust checks tenant match, action permission, role/position families, effective
  org-unit platform filtering, and affiliate/workplace ABAC scope limits.
- Contract docs and TypeScript/Python metadata name stable denial reason codes
  for future HTTP/Tauri/mobile wrappers.
- Slice spec: `docs/PAYROLL_RUST_AUTHORIZATION_SLICE.md`.

Verified commands:

```sh
cargo test -p bitween-payroll-api access::tests
cargo test -p bitween-payroll-api service::tests
python -m unittest tests.test_org_access tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
```

## Implementation checkpoint: Rust service boundary and probes

Completed on 2026-06-04 as the first framework-neutral service-boundary slice:

- `crates/payroll-api` exposes `PayrollApiService`.
- `PayrollApiService::validate_run_payload` is the Rust service facade for
  validation-only payroll run requests.
- `PayrollApiService::health()` returns a stable `/api/payroll/v1/healthz`
  payload with service, version, environment, build SHA, and uptime fields.
- `PayrollApiService::readiness(checks)` aggregates named readiness checks for
  `/api/payroll/v1/readiness` without exposing secrets or payroll output paths.
- Frontend/Python contract metadata names the health/readiness DTOs so future
  HTTP, Tauri, or Kubernetes wrappers call the Rust-owned shapes.
- Slice spec: `docs/PAYROLL_RUST_SERVICE_BOUNDARY_SLICE.md`.

Verified commands:

```sh
cargo test -p bitween-payroll-api
buck2 test //crates/payroll-api:payroll_api_test
python -m unittest tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
```



## Implementation checkpoint: Rust payroll attendance aggregation

Completed on 2026-06-04 as a payroll-domain behavior slice:

- `crates/payroll-api` owns attendance source-record aggregation through
  `aggregate_attendance_records` and
  `PayrollApiService::aggregate_attendance_records`.
- Rust groups normalized attendance records, applies per-record late/early grace
  minutes, performs Python-compatible half-even hour rounding, and emits
  invoice-compatible payroll rows.
- Python remains the parser/workbook bridge for CSV/XLSX uploads until those I/O
  surfaces are migrated behind parity tests.
- Contract docs and TypeScript/Python metadata name the source-record and
  invoice-row DTOs, including `_attendance_days` and `_attendance_input`.
- Slice spec: `docs/PAYROLL_RUST_ATTENDANCE_AGGREGATION_SLICE.md`.

Verified commands:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_attendance_import tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```


## Implementation checkpoint: Rust payroll invoice audit batch

Completed on 2026-06-04 as a payroll audit behavior slice:

- `crates/payroll-api` owns supplied-input invoice audit batch summarization
  through `audit_invoice_batch`, `InvoiceAuditBatchItem`,
  `InvoiceAuditSummary`, `InvoiceAuditBatchResult`, and
  `PayrollApiService::audit_invoice_batch`.
- Rust preserves supplied row order, Python-compatible summary counts, top-level
  pass/warn counts, batch workplace labels, and row-auditor output.
- Python remains the resolver/UI bridge for settings lookup, ledger record
  matching, fixed-hours profile resolution, workbook I/O, and summary text
  rendering.
- Contract docs and TypeScript/Python metadata name the invoice-audit batch
  item, summary, and result DTOs.
- Slice spec: `docs/PAYROLL_RUST_INVOICE_AUDIT_BATCH_SLICE.md`.

Verified commands:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_invoice_audit tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```

Task 4 acceptance status:

- [x] Supplied-input invoice audit batch summarization is Rust-owned behind
      parity tests.



## Implementation checkpoint: Rust payroll deduction finalization

Completed on 2026-06-04 as a payroll output-generation behavior slice:

- `crates/payroll-api` owns supplied-input final deduction and net-pay
  calculation through `finalize_payroll_deductions`,
  `calculate_payroll_income_tax`, `lookup_simplified_income_tax`,
  `PayrollTaxMethod`, `PayrollDeductionInput`, `PayrollIncomeTaxResult`,
  `PayrollDeductionResult`, and
  `PayrollApiService::finalize_payroll_deductions`.
- Rust applies Python-compatible simplified tax brackets, high-income estimate
  fallback, preset income/local tax overrides, local tax rounding,
  identity-guarantee deduction absolute-value handling, total deduction, and net
  pay calculation.
- Python remains the workbook, roster, social-insurance, EDI/site/fixed-hour, and
  final-record assembly bridge.
- Contract docs and TypeScript/Python metadata name the deduction input,
  income-tax result, and final deduction result DTOs.
- Slice spec: `docs/PAYROLL_RUST_DEDUCTION_FINALIZATION_SLICE.md`.

Verified commands:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```

Task 4 acceptance status:

- [x] Supplied-input final deduction/net-pay calculation is Rust-owned behind
      parity tests.

## Implementation checkpoint: Rust payroll earnings calculation

Completed on 2026-06-04 as a payroll calculation behavior slice:

- `crates/payroll-api` owns supplied-input payroll earnings calculation through
  `calculate_payroll_earnings`, helper functions for ordinary hourly,
  weekly-holiday pay, overlap premium, `PayrollEarningsInput`,
  `PayrollEarningsHours`, `PayrollEarningsBreakdown`,
  `PayrollEarningsResult`, and
  `PayrollApiService::calculate_payroll_earnings`.
- Rust applies Python-compatible 209-hour ordinary-rate calculation, premium
  factors, weekly-holiday proration, raw amount fallback heuristics, base-salary
  fallback, meal non-taxable cap, and won rounding.
- Python remains the invoice parser, employee master merger, cell normalizer,
  insurance/tax/deduction orchestrator, workbook bridge, and final-record
  assembly layer.
- Contract docs and TypeScript/Python metadata name the earnings input, hours,
  breakdown, and result DTOs.
- Slice spec: `docs/PAYROLL_RUST_EARNINGS_CALCULATION_SLICE.md`.

Verified commands:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```

Task 4 acceptance status:

- [x] Supplied-input earnings/gross/non-taxable/taxable-pay calculation is
      Rust-owned behind parity tests.

## Implementation checkpoint: Rust payroll salary calculation

Completed on 2026-06-04 as a payroll calculation behavior slice:

- `crates/payroll-api` owns supplied-input one-employee salary calculation
  through `calculate_payroll_salary`, `PayrollSalaryInput`,
  `PayrollSalaryDeductions`, `PayrollSalaryTaxMethod`,
  `PayrollSalaryResult`, and
  `PayrollApiService::calculate_payroll_salary`.
- Rust composes earnings and social-insurance Rust modules with
  calculator-compatible income/local tax handling to produce deductions, total
  deductions, and net pay.
- Python remains the invoice parser, employee master merger, cell normalizer,
  age/KCOMWEL/EDI resolver, workbook bridge, and final-record assembly layer.
- Contract docs and TypeScript/Python metadata name the salary input,
  deductions, tax-method, and result DTOs.
- Slice spec: `docs/PAYROLL_RUST_SALARY_CALCULATION_SLICE.md`.

Verified commands:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```

Task 4 acceptance status:

- [x] Supplied-input salary calculation is Rust-owned behind parity tests.

## Implementation checkpoint: Rust payroll EI 65+ decision

Completed on 2026-06-04 as a payroll decision behavior slice:

- `crates/payroll-api` owns supplied-input EI 65+ payroll decisions through
  `resolve_ei_65_for_payroll`, age helpers, decision DTOs, and
  `PayrollApiService::resolve_ei_65_for_payroll`.
- Rust handles valid-period month-end age checks, Korean RRN century/pivot
  parsing, supplied KCOMWEL premium interpretation, unknown-default skip/deduct
  handling, management-number fallback, and Korean warning text.
- Python remains the KCOMWEL import/storage/live-provider, employee matching,
  site settings, EDI premium input resolution, payroll-row mutation, and workbook bridge.
- Contract docs and TypeScript/Python metadata name the EI 65+ input,
  verification, and result DTOs.
- Slice spec: `docs/PAYROLL_RUST_EI65_SLICE.md`.

Verified commands:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_employment_insurance_65 tests.test_payroll_employment_insurance tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```

Task 4 acceptance status:

- [x] Supplied-input EI 65+ payroll decision is Rust-owned behind parity tests.


## Implementation checkpoint: Rust payroll EDI insurance premium application

Completed on 2026-06-04 as a payroll row-application behavior slice:

- `crates/payroll-api` owns supplied-record EDI premium application through
  `apply_edi_premiums_to_invoice`, `EdiPremiumSource`,
  `EdiInsuranceConfig`, `EdiInsurancePremiumRecord`, `EdiInsuranceInvoice`,
  `EdiInsuranceApplication`, and
  `PayrollApiService::apply_edi_premiums_to_invoice`.
- Rust applies Python-compatible enabled/disabled behavior, missing-record
  handling, source normalization, EDI metadata, age-exempt preservation,
  long-term-care fallback rounding, employment premium clearing/application,
  industrial-accident split fields, and insurance-total recalculation.
- Python remains the EDI import/storage/live-provider, tenant/site setting,
  employee matching, site management-number, roster, and workbook bridge.
- Contract docs and TypeScript/Python metadata name the EDI config, premium
  record, invoice, and application DTOs.
- Slice spec: `docs/PAYROLL_RUST_EDI_INSURANCE_SLICE.md`.

Verified commands:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_edi_insurance tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```

Task 4 acceptance status:

- [x] Supplied-record EDI insurance premium application is Rust-owned behind
      parity tests.

## Implementation checkpoint: Rust payroll site-benefits application

Completed on 2026-06-04 as a payroll row-application behavior slice:

- `crates/payroll-api` owns supplied-config site-benefits application through
  `apply_site_benefits_to_invoice`, `WorkersDayConfig`,
  `IdentityInsuranceConfig`, `SiteBenefitsConfig`, `SiteBenefitsInvoice`,
  `SiteBenefitsApplication`, and
  `PayrollApiService::apply_site_benefits_to_invoice`.
- Rust normalizes benefit configs, applies Workers' Day invoice/default amount
  rules, applies identity-guarantee insurance billing-month and already-applied
  suppression rules, and emits source fields plus compatibility invoice keys.
- Python remains the resolver/ledger/workbook/totals bridge for
  site/tenant/global settings, workplace canonicalization, identity-insurance
  ledger read/write, workbook I/O, and payroll subtotal/gross recalculation.
- Contract docs and TypeScript/Python metadata name the site-benefits config,
  invoice, and application DTOs.
- Slice spec: `docs/PAYROLL_RUST_SITE_BENEFITS_SLICE.md`.

Verified commands:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_site_benefits tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```

Task 4 acceptance status:

- [x] Supplied-config site-benefits row application is Rust-owned behind parity
      tests.

## Implementation checkpoint: Rust payroll invoice audit row

Completed on 2026-06-04 as a payroll audit behavior slice:

- `crates/payroll-api` owns supplied-input invoice audit row evaluation through
  `audit_invoice_row`, `estimate_break_hours`, and
  `PayrollApiService::audit_invoice_row`.
- Rust composes workplace-hours and fixed-hours Rust rules, emits Python-compatible
  warning flags/status labels, estimates break hours, and calculates base-salary
  formula output for a single supplied row.
- Python remains the resolver bridge for settings, ledger record matching,
  fixed-hours profile resolution, workbook I/O, and UI text rendering.
- Contract docs and TypeScript/Python metadata name the invoice-audit invoice,
  record, and row DTOs.
- Slice spec: `docs/PAYROLL_RUST_INVOICE_AUDIT_ROW_SLICE.md`.

Verified commands:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_invoice_audit tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```

## Implementation checkpoint: Rust payroll workplace-hours application

Completed on 2026-06-04 as a payroll monthly-hours behavior slice:

- `crates/payroll-api` owns supplied-policy workplace monthly-hours application
  through `resolve_monthly_work_hours`, `apply_monthly_hours_to_invoice`, and
  `PayrollApiService::apply_monthly_hours_to_invoice`.
- Rust normalizes workplace-hours policies, applies the five Python-compatible
  mode values, clamps missing/negative invoice hours before selection, and emits
  `_monthly_work_hours` plus `_monthly_hours_source` metadata.
- Python remains the resolver bridge for tenant/site/global settings and
  canonical workplace aliases until those repositories move to Rust.
- Contract docs and TypeScript/Python metadata name the workplace-hours policy,
  invoice, resolution, and application DTOs.
- Slice spec: `docs/PAYROLL_RUST_WORKPLACE_HOURS_SLICE.md`.

Verified commands:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workplace_hours tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```

## Implementation checkpoint: Rust payroll fixed-hours application

Completed on 2026-06-04 as a payroll record-generation behavior slice:

- `crates/payroll-api` owns fixed-hours profile application through
  `apply_fixed_hours_to_invoice` and
  `PayrollApiService::apply_fixed_hours_to_invoice`.
- Rust normalizes resolved fixed-hours profiles, preserves original invoice hour
  fields, applies monthly fixed hours and fixed overtime/special hours, and
  emits Python-compatible audit flags.
- Python remains the resolver bridge for HR contracts, site job-group templates,
  roster matching, and local payroll settings until those repositories move to
  Rust.
- Contract docs and TypeScript/Python metadata name the fixed-hours profile,
  invoice, and application DTOs.
- Slice spec: `docs/PAYROLL_RUST_FIXED_HOURS_SLICE.md`.

Verified commands:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_fixed_hours tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```


## Implementation checkpoint: Rust workflow document permissions core

Completed on 2026-06-04 as a workflow document authorization slice:

- `crates/workflow-core::business_trip_permissions` owns pure supplied
  workflow-document view, edit, submit, and approve predicates.
- Rust preserves the business-trip document legal-scope gate, admin/executive/
  finance document visibility, requester visibility, approval-step visibility,
  site-manager/HR site-scoped visibility, requester-only edit/submit for
  `draft` and `requested_changes`, terminal `approved`/`closed` edit denial,
  current-pending-step approval, and supplied org workflow-approval override
  only for admin/executive/finance workflow authority.
- Python remains the `UserSession` adapter, workflow profile resolver,
  document/content resolver, org-position workflow-approval capability resolver,
  workflow store, approval mutation owner, document/task/report/KPI side-effect
  owner, notification/calendar/To-Do producer, and UI bridge.
- Slice spec: `docs/WORKFLOW_RUST_DOCUMENT_PERMISSIONS_SLICE.md`.

Verified commands:

```sh
cargo test -p bitween-workflow-core business_trip_permissions --lib
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_document_permissions_contracts -v
```

Task 5 acceptance status:

- [x] Workflow document permission predicates are Rust-owned behind parity
      contract tests.

## Implementation checkpoint: Rust workflow operational permissions core

Completed on 2026-06-04 as a workflow operational authorization slice:

- `crates/workflow-core::business_trip_permissions` owns pure supplied-profile
  site-report visibility, month-close authority, and execution-task management
  predicates.
- Rust preserves admin/executive/finance report visibility, supplied profile
  `site_ids` report visibility, admin/finance/site-manager month-close checks
  through report visibility, direct executor task management, and executor-role
  without assignment denial.
- Python remains the `UserSession` adapter, workflow profile resolver, workflow
  store, site/task resolver, close-month side-effect owner, execution-task
  mutation owner, notification/calendar/To-Do producer, and UI bridge.
- Slice spec: `docs/WORKFLOW_RUST_OPERATIONAL_PERMISSIONS_SLICE.md`.

Verified commands:

```sh
cargo test -p bitween-workflow-core business_trip_permissions --lib
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_permissions_contracts -v
```

Task 5 acceptance status:

- [x] Workflow operational permission predicates are Rust-owned behind parity
      contract tests.

## Implementation checkpoint: Rust business-trip document legal-scope core

Completed on 2026-06-04 as a workflow document authorization slice:

- `crates/workflow-core::business_trip_permissions` owns pure business-trip
  document relatedness and document legal-scope predicates for supplied
  principal/document DTOs.
- Rust preserves `BUSINESS_TRIP_REQUEST` and payload `trip_id` relatedness,
  unrelated-document pass-through, origin/legal tenant fallback order, workflow
  storage-tenant row scoping, workflow-root access, and sibling legal-tenant
  denial.
- Python remains the `UserSession` adapter, document JSON/content resolver,
  workflow store, profile resolver, approval mutation owner, document/task/
  report/KPI side-effect owner, notification/calendar/To-Do producer, and UI
  bridge.
- Slice spec: `docs/WORKFLOW_RUST_BUSINESS_TRIP_DOCUMENT_SCOPE_SLICE.md`.

Verified commands:

```sh
cargo test -p bitween-workflow-core business_trip_permissions --lib
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_business_trip_contracts.BusinessTripLifecycleContractTests.test_contract_declares_rust_business_trip_document_scope -v
```

Task 5 acceptance status:

- [x] Business-trip document legal-scope predicates are Rust-owned behind parity
      contract tests.

## Implementation checkpoint: Rust business-trip overdue permission core

Completed on 2026-06-04 as a follow-up supplied-profile workflow authorization slice:

- `crates/workflow-core::business_trip_permissions` owns pure tenant-wide
  administration, overdue-evaluator invocation, and scoped overdue-evaluation
  predicates for supplied principal/profile/trip DTOs.
- Rust preserves admin/executive/finance tenant-wide authority, manager/HR
  evaluator invocation, legal-scope isolation, site/department scoped overdue
  evaluation, and the exclusion of direct requester/executor/viewer/approver
  grants from overdue side-effect authority.
- Python remains the `UserSession` adapter, workflow profile resolver, workflow
  JSON store, overdue escalation side-effect owner, document/task/report/KPI
  writer, notification/calendar/To-Do producer, and UI bridge.
- Slice spec: `docs/WORKFLOW_RUST_BUSINESS_TRIP_OVERDUE_PERMISSIONS_SLICE.md`.

Verified commands:

```sh
cargo test -p bitween-workflow-core business_trip_permissions --lib
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_business_trip_contracts.BusinessTripLifecycleContractTests.test_contract_declares_rust_business_trip_overdue_permissions -v
```

Task 5 acceptance status:

- [x] Business-trip lifecycle administration and overdue permission predicates
      are Rust-owned behind parity contract tests.

## Implementation checkpoint: Rust business-trip permission core

Completed on 2026-06-04 as a supplied-profile workflow authorization slice:

- `crates/workflow-core::business_trip_permissions` owns pure business-trip
  lifecycle legal-scope, visibility, and manage predicates for supplied
  principal/trip/profile DTOs.
- Rust preserves the workflow role matrix for admin/finance expansion, direct
  requester/executor ownership, explicit approver visibility, requester manager
  visibility, site/department scoped manager visibility, viewer scoped-only
  visibility, and narrower manage authority.
- Python remains the `UserSession` adapter, workflow profile resolver, workflow
  JSON store, document/task/report/KPI side-effect owner, overdue evaluator,
  notification/calendar/To-Do producer, and UI bridge.
- Slice spec: `docs/WORKFLOW_RUST_BUSINESS_TRIP_PERMISSIONS_SLICE.md`.

Verified commands:

```sh
cargo test -p bitween-workflow-core business_trip_permissions --lib
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_business_trip_contracts.BusinessTripLifecycleContractTests.test_contract_declares_rust_business_trip_permissions -v
```

Task 5 acceptance status:

- [x] Business-trip lifecycle permission predicates are Rust-owned behind parity
      contract tests.

## Implementation checkpoint: Rust business-trip lifecycle core

Completed on 2026-06-04 as the first workflow-domain Rust backend slice:

- `crates/workflow-core` owns pure business-trip lifecycle constants, source
  normalization, migration/view-model shaping, source matching, transition
  validation, and transition timestamp/KPI effects.
- Rust preserves compatibility with `core.workflow.business_trip` for status
  strings/order, KPI reflection values, source kinds, dedupe fallback, unknown
  field preservation, invalid transition rejection, cancellation, and completed
  KPI-ready behavior.
- Python remains the workflow JSON store, document approval sync, execution task
  and report prerequisite checker, overdue escalation worker, KPI reflection
  writer, authorization profile resolver, notification/calendar/To-Do producer,
  and UI bridge.
- Slice spec: `docs/WORKFLOW_RUST_BUSINESS_TRIP_LIFECYCLE_SLICE.md`.

Verified commands:

```sh
cargo test -p bitween-workflow-core business_trip --lib
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_business_trip_contracts.BusinessTripLifecycleContractTests.test_contract_declares_rust_business_trip_lifecycle -v
```

Task 5 acceptance status:

- [x] Business-trip lifecycle normalization and transitions are Rust-owned behind
      parity tests.

## Implementation checkpoint: Rust payroll execution planning

Completed on 2026-06-04 as a service-boundary behavior slice:

- `crates/payroll-api` owns execution planning through `plan_payroll_execution`
  and `PayrollApiService::plan_run_request`.
- Rust plans invoice, attendance, and mixed compatibility execution steps from a
  parsed request and normalized operation-policy snapshot.
- Python remains the compatibility executor, explicitly named as
  `python_compatibility`, until payroll output generation moves to Rust.
- Contract docs and TypeScript/Python metadata name the step kinds, backend
  value, source paths, missing source paths, and compatibility executor.
- Slice spec: `docs/PAYROLL_RUST_EXECUTION_PLAN_SLICE.md`.

Verified commands:

```sh
cargo test -p bitween-payroll-api execution_plan::tests
cargo test -p bitween-payroll-api service::tests
python -m unittest tests.test_payroll_automation tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
```

## Phase 3: React Native and Tauri desktop transition

### Task 5: Treat Expo web export as the desktop frontend artifact

**Description:** Add a production export path for the React Native platform UI so Tauri can bundle static web assets instead of creating a separate desktop UI.

**Acceptance criteria:**

- [ ] `apps/bitween-platform-ui` has an explicit web export command.
- [ ] Tauri desktop docs point at the exported web artifact.
- [ ] Desktop-specific capability gaps are tracked as backend/desktop contract requests, not UI forks.
- [ ] Desktop UI states expose permissions/access clearly without implying client-side authorization.

**Verification:**

- [ ] `npm run typecheck --prefix apps/bitween-platform-ui`
- [ ] `npm run export:web --prefix apps/bitween-platform-ui` once Expo dependencies are installed in the local/CI environment.

**Dependencies:** None

**Files likely touched:**

- `apps/bitween-platform-ui/package.json`
- `apps/bitween-platform-ui/README.md`
- `apps/bitween-desktop-tauri/README.md`

**Estimated scope:** Small

### Task 5.1: Maintain the UI catalog-array baseline

**Description:** Keep the React Native app and dependency-free preview catalog-array driven so Korean, English, Chinese, and Japanese can each render as a fully single-language UI. This PR establishes the baseline; future UI slices must extend it instead of adding inline copy.

**Acceptance criteria:**

- [ ] `src/data.ts`, `src/screens.tsx`, `src/components.tsx`, `src/theme.ts`, `src/viewModel.ts`, and `preview/app.js` use stable ids/tones/targets/sample data and do not introduce localized user-facing copy outside the catalog.
- [ ] Existing navigation, dashboard, table, form, auth, permission, empty/error/loading, toast, and action copy is represented as catalog-array rows or localized domain data arrays.
- [ ] Translation completeness and localized-source-copy checks cover every production key for `ko-KR`, `en-US`, `zh-Hans-CN`, and `ja-JP`.
- [ ] Backend error/status codes are displayed through localized frontend copy.
- [ ] Japanese is included in the settings language selector and all future language reviews.

**Verification:**

- [ ] `npm run verify:i18n --prefix apps/bitween-platform-ui`
- [ ] `npm run typecheck --prefix apps/bitween-platform-ui`
- [ ] Manual/visual review of the same screen in Korean, English, Chinese, and Japanese.

**Dependencies:** Task 0.2 and Task 5

**Files likely touched:**

- `apps/bitween-platform-ui/src/i18n/`
- `apps/bitween-platform-ui/src/data.ts`
- `apps/bitween-platform-ui/src/screens.tsx`
- `apps/bitween-platform-ui/src/components.tsx`
- future lint/check scripts

**Estimated scope:** Medium

### Task 6: Scaffold Tauri desktop shell

**Description:** Add a Tauri app surface that bundles the React Native Web export and exposes only typed desktop commands.

**Acceptance criteria:**

- [ ] Tauri `src-tauri/` is a Rust workspace member or clearly isolated desktop crate.
- [ ] Tauri commands use typed request/response structures, declare least-privilege capabilities, validate inputs, and do not duplicate business logic.
- [ ] Capabilities/permissions are least-privilege and reviewed.
- [ ] Desktop app calls Kubernetes APIs for production business behavior.

**Verification:**

- [ ] `cargo test --workspace`
- [ ] Tauri build/dev command for the desktop shell
- [ ] TypeScript typecheck for the platform UI

**Dependencies:** Task 5

**Files likely touched:**

- `apps/bitween-desktop-tauri/`
- `Cargo.toml`
- `apps/bitween-platform-ui/`

**Estimated scope:** Medium

## Phase 4: Python cleanup

### Task 7: Build Python decommission inventory

**Description:** Classify Python modules as compatibility behavior, migration tooling, tests, data fixtures, or removable dead code.

**Acceptance criteria:**

- [ ] Each Python module category has an owner Rust target or a documented deletion gate.
- [ ] No production path depends on Python after the corresponding Rust slice is accepted.
- [ ] Generated caches and local runtime data are not committed.

**Verification:**

- [ ] Python characterization tests pass before and after each deletion.
- [ ] Rust parity tests cover the removed behavior.
- [ ] `python -m compileall -q` passes for remaining compatibility modules until deletion.

**Dependencies:** Task 3 or Task 4 for each domain slice

**Files likely touched:**

- `core/`
- `services/`
- root-level Python compatibility modules
- `tests/`
- docs explaining decommission evidence

**Estimated scope:** Medium per slice

### Task 8: Remove Python compatibility slice by slice

**Description:** Delete Python compatibility code only when Rust owns the behavior and tests prove parity.

**Acceptance criteria:**

- [ ] Deletion commit names the Rust replacement and parity tests.
- [ ] Docs no longer instruct production users to run removed Python paths.
- [ ] CI no longer runs obsolete tests after replacement tests are active.

**Verification:**

- [ ] Rust tests pass.
- [ ] TypeScript typecheck passes.
- [ ] Remaining Python tests pass or are intentionally removed with replacement evidence.

**Dependencies:** Task 7 and the corresponding Rust slice

**Files likely touched:** Domain-specific compatibility modules and tests

**Estimated scope:** Small/Medium per slice

## Checkpoints

### Checkpoint A: Tooling plan accepted

- [ ] SAP/Remote People/Workday maturity benchmark, Korean/English/Chinese/Japanese i18n, Korean labor-market/labor-law localization, JWT/WebAuthn, RBAC + ABAC, and Zero Trust baseline reviewed.
- [ ] Buck2 target inventory reviewed.
- [ ] Cargo/npm/Python checks remain green.
- [ ] No unverified Buck2 config is promoted to CI.

### Checkpoint B: First Rust service slice accepted

- [ ] Rust owns one behavior slice beyond pure validation.
- [ ] Kubernetes health/config requirements are documented.
- [ ] Python remains only as a controlled compatibility fallback for that slice.

### Checkpoint C: Desktop shell accepted

- [ ] React Native Web export is the UI artifact.
- [ ] Tauri command surface is typed, least-privilege, validated, and audited.
- [ ] Desktop does not fork business workflows from the Kubernetes API.

### Checkpoint D: Python cleanup loop accepted

- [ ] Decommission inventory is complete.
- [ ] First Python slice is removed only after Rust parity evidence.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Buck2 dependency graph diverges from Cargo/npm | High | Keep Cargo/npm authoritative until Buck2 target parity is proven. |
| Rust rewrite duplicates Python complexity | High | Use characterization tests and simplify boundaries before porting. |
| Tauri becomes a second backend | High | Restrict Tauri commands to desktop capabilities; business APIs stay in Kubernetes Rust services. |
| Client-side authorization is mistaken for enforcement | High | UI uses capability hints only; Rust backend enforces RBAC + ABAC per request. |
| Missing performance evidence delays production rollout | Medium | Record budgets and measurements before HPA, desktop release, or frontend export promotion. |
| React Native Web export lacks desktop UX affordances | Medium | Use platform-specific files only where necessary and keep shared components default. |
| UI ships with mixed-language fallback copy | High | Add translation completeness gates and review every production UI slice in Korean, English, Chinese, and Japanese. |
| Python deletion removes behavior evidence | High | Delete only after Rust parity and zero-production-use evidence. |
| Kubernetes deployment work begins before service images exist | Medium | Add manifests after service crates and container builds exist. |

## Stop condition for this planning PR

This PR is complete when the architecture decision, task breakdown, and first frontend export hook are committed, current checks still pass, and a draft PR is opened from the synced `origin/main` base.


### Payroll social-insurance calculation Rust slice — completed 2026-06-04

`crates/payroll-api` now owns supplied-input social-insurance calculation through
`PayrollApiService::calculate_social_insurance`. Python compatibility code still
parses identities, determines age/KCOMWEL eligibility, applies EDI overrides,
looks up roster/master values, and mutates workbooks/payroll rows until those
boundaries move behind parity tests.

Verification:

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```
