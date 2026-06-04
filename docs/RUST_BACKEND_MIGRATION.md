# Idiomatic Rust backend rewrite backlog

## Status

In progress. The Buck2/Reindeer foundation for the first Rust backend contract crate is in place; Python remains characterization-only until Rust parity is proven domain by domain. This is a production-quality rewrite track and is not an MVP shortcut.

## Goal

Rewrite backend code in idiomatic Rust while preserving the observable business behavior already covered by compatibility tests. The target runtime is the Kubernetes-native stack documented in `docs/KUBERNETES_NATIVE_STACK.md`, and first-party Rust backend work uses Rust 2024 with Rust 1.96.

## Current implementation checkpoint: Buck2/Reindeer foundation

Implemented on 2026-06-04:

- Added Buck2 repository configuration with bundled prelude/toolchain wiring.
- Added Reindeer-managed, vendored third-party Rust dependencies under `third-party/rust/`.
- Added first-party Buck2 targets for `crates/payroll-api`:
  - `//crates/payroll-api:payroll_api`
  - `//crates/payroll-api:payroll_api_test`
- Added Reindeer fixups for crates that require build-script execution or Cargo compile-time environment values.
- Added `scripts/verify_rust_buck2_reindeer.sh` as the local verification entrypoint.

Verification evidence for this checkpoint:

- `buck2 build //crates/payroll-api:payroll_api`
- `buck2 test //crates/payroll-api:payroll_api_test`
- `cargo test --workspace`

Runbook: `docs/BUCK2_REINDEER_RUST_TRANSITION.md`.

## Current implementation checkpoint: payroll operation policy invariants

Implemented on 2026-06-04 as the next backend behavior slice:

- Rust now owns the normalized payroll operation policy DTO for known fields in
  `crates/payroll-api/src/policy.rs`.
- The Rust policy model preserves Python-compatible safe defaults for payroll
  input basis, payday, setup-guide visibility, policy notes, and attendance
  settings.
- Attendance minute fields are clamped to the Python compatibility ranges:
  rounding and overtime rounding `1..=60`, late/early-leave grace `0..=240`.
- Missing clock handling is typed as `warn`, `ignore`, or `deduct`, with invalid
  values normalized to `warn`.
- Rust validation responses normalize the supplied operation policy before
  serializing it to frontend/API clients.

Verification evidence for this checkpoint:

- `cargo test -p bitween-payroll-api`
- `buck2 test //crates/payroll-api:payroll_api_test`
- Python compatibility tests for `tests.test_payroll_operation_policy` and
  `tests.test_payroll_api_adapter`

Slice spec: `docs/PAYROLL_OPERATION_POLICY_RUST_SLICE.md`.

## Current implementation checkpoint: Rust service boundary and probes

Implemented on 2026-06-04 as the first framework-neutral service-boundary
slice:

- `crates/payroll-api` now exposes `PayrollApiService`.
- `PayrollApiService::validate_run_payload` delegates request validation,
  input-method resolution, policy normalization, and response shaping to Rust.
- `PayrollApiService::health()` returns a stable probe-safe health payload with
  service name, version, environment, build SHA, and uptime.
- `PayrollApiService::readiness(checks)` aggregates named readiness checks into
  `ready`, `degraded`, or `not_ready` states without exposing secrets or payroll
  runtime data.
- TypeScript and Python contract metadata now include `/healthz` and
  `/readiness` DTO shapes.

Verification evidence for this checkpoint:

- `cargo test -p bitween-payroll-api`
- `buck2 test //crates/payroll-api:payroll_api_test`
- Python contract test for `tests.test_payroll_api_contract`
- `npm run typecheck --prefix frontend`

Slice spec: `docs/PAYROLL_RUST_SERVICE_BOUNDARY_SLICE.md`.

## Current implementation checkpoint: Rust payroll authorization invariants

Implemented on 2026-06-04 as the next service-boundary hardening slice:

- `crates/payroll-api` now exposes `PayrollPrincipal`, `PayrollAction`,
  `PayrollPermission`, and `PayrollAccessDecision`.
- `authorize_payroll_request` and `PayrollApiService::authorize_run_request`
  evaluate tenant/legal-entity match, role/position permissions, effective org
  unit platform filtering, and affiliate/workplace ABAC limits in Rust.
- Rust preserves the Python compatibility rule that CEO position bypasses team
  platform filtering while non-CEO admin/finance grants remain filtered by
  `effective_platform_ids`.
- TypeScript and Python contract metadata now include the authorization decision
  DTO and stable denial reason codes.

Verification evidence for this checkpoint:

- `cargo test -p bitween-payroll-api access::tests`
- `cargo test -p bitween-payroll-api service::tests`
- Python contract/org access tests for `tests.test_payroll_api_contract` and
  `tests.test_org_access`
- `npm run typecheck --prefix frontend`

Slice spec: `docs/PAYROLL_RUST_AUTHORIZATION_SLICE.md`.

## Current implementation checkpoint: Rust payroll run-response envelope

Implemented on 2026-06-04 as the next service-boundary behavior slice:

- `crates/payroll-api` now exposes `PayrollRunResult`,
  `PayrollRunResponse`, and `run_response_from_result`.
- `PayrollApiService::run_response` formats supplied execution results into the
  stable API success/error envelope previously shaped by the Python
  compatibility adapter.
- Rust preserves the contract distinction between validation errors
  (`will_run=false`) and execution failures (`will_run=true`,
  `error_code=payroll_run_failed`).
- Rust normalizes known `operation_policy` fields before serializing run-result
  responses and never exposes internal exception objects.
- TypeScript and Python contract metadata now include the run-failure DTO shape
  and the Rust response-shaping entrypoint.

Verification evidence for this checkpoint:

- `cargo test -p bitween-payroll-api run::tests`
- `cargo test -p bitween-payroll-api service::tests`
- Python adapter/contract tests for `tests.test_payroll_api_adapter` and
  `tests.test_payroll_api_contract`
- `npm run typecheck --prefix frontend`

Slice spec: `docs/PAYROLL_RUST_RUN_RESPONSE_SLICE.md`.


## Current implementation checkpoint: Rust payroll attendance aggregation

Implemented on 2026-06-04 as the next payroll-domain behavior slice:

- `crates/payroll-api` now exposes `AttendanceSourceRecord`,
  `AttendanceInvoiceRow`, and `aggregate_attendance_records`.
- `PayrollApiService::aggregate_attendance_records` turns normalized attendance
  records plus an `AttendancePolicy` into invoice-compatible payroll rows.
- Rust preserves Python compatibility grouping, per-record late/early grace
  handling, half-even hour rounding, sorted employee rows, and the
  `_attendance_days` / `_attendance_input` compatibility fields.
- Python remains responsible for CSV/XLSX parsing and workbook bridge output
  until those I/O-heavy slices are ported separately.
- TypeScript and Python contract metadata now include the attendance source and
  invoice-row DTO shapes.

Verification evidence for this checkpoint:

- `cargo fmt --check`
- `cargo test --workspace`
- `buck2 test //crates/payroll-api:payroll_api_test`
- `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_attendance_import tests.test_payroll_api_contract -v`
- `npm run typecheck --prefix frontend`
- `git diff --check`
- `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

Slice spec: `docs/PAYROLL_RUST_ATTENDANCE_AGGREGATION_SLICE.md`.


## Current implementation checkpoint: Rust payroll invoice audit batch

Implemented on 2026-06-04 as the next payroll audit behavior slice:

- `crates/payroll-api` now exposes `InvoiceAuditBatchItem`,
  `InvoiceAuditSummary`, `InvoiceAuditBatchResult`, and
  `audit_invoice_batch`.
- `PayrollApiService::audit_invoice_batch` evaluates a supplied batch of
  invoice-audit items without reading settings stores, matching ledgers,
  resolving fixed-hours profiles, parsing workbooks, or rendering UI text.
- Rust preserves Python compatibility row order, `summary.total/pass/warn`,
  `pass_count`, `warn_count`, batch workplace labeling, and row-auditor output.
- Python remains responsible for settings lookup, record matching,
  fixed-profile resolution, workbook I/O, and UI summary text until those
  resolver/I/O slices move to Rust behind parity tests.
- TypeScript and Python contract metadata now include invoice-audit batch item,
  summary, and result DTO shapes.

Verification evidence for this checkpoint:

- `cargo fmt --check`
- `cargo test --workspace`
- `buck2 test //crates/payroll-api:payroll_api_test`
- `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_invoice_audit tests.test_payroll_api_contract -v`
- `npm run typecheck --prefix frontend`
- `git diff --check`
- `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

Slice spec: `docs/PAYROLL_RUST_INVOICE_AUDIT_BATCH_SLICE.md`.





## Current implementation checkpoint: Rust payroll social-insurance calculation

Implemented on 2026-06-04 as the next payroll calculation behavior slice:

- `crates/payroll-api` now exposes `SocialInsuranceInput`,
  `SocialInsuranceResult`, `calculate_social_insurance`, and
  `calculate_employment_insurance`.
- `PayrollApiService::calculate_social_insurance` calculates supplied-input
  pension, health insurance, long-term care, employment insurance, total, and
  exemption state without reading employee masters, identities, KCOMWEL records,
  EDI files, settings, or workbooks.
- Rust preserves Python compatibility for pension floor/ceiling clamps, pension
  and health rates, long-term-care ratio, employment-insurance worker rate,
  positive preset precedence, exemption zeroing, won rounding, and employment
  insurance 10-won rounding.
- Python remains responsible for identity parsing, KCOMWEL age-65 decisions,
  EDI premium overrides, employee-master lookup, workbook parsing/writing, and
  payroll row mutation until those boundaries move behind parity tests.
- TypeScript and Python contract metadata now include social-insurance input and
  result DTO shapes.

Verification evidence for this checkpoint:

- `cargo fmt --check`
- `cargo test --workspace`
- `buck2 test //crates/payroll-api:payroll_api_test`
- `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_payroll_api_contract -v`
- `npm run typecheck --prefix frontend`
- `git diff --check`
- `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

Slice spec: `docs/PAYROLL_RUST_SOCIAL_INSURANCE_SLICE.md`.

## Current implementation checkpoint: Rust payroll deduction finalization

Implemented on 2026-06-04 as the next payroll output-generation behavior slice:

- `crates/payroll-api` now exposes `PayrollTaxMethod`,
  `PayrollDeductionInput`, `PayrollIncomeTaxResult`,
  `PayrollDeductionResult`, `lookup_simplified_income_tax`,
  `calculate_payroll_income_tax`, and `finalize_payroll_deductions`.
- `PayrollApiService::finalize_payroll_deductions` calculates supplied-input
  taxable pay, income tax, local income tax, tax total, identity-guarantee
  deduction contribution, total deduction, and net pay without reading
  workbooks, rosters, settings, social-insurance sources, or tax-table files.
- Rust preserves Python compatibility for the simplified income-tax brackets,
  high-income estimate formula, preset income-tax precedence, preset local-tax
  precedence, automatic local-tax rounding, identity-guarantee deduction absolute
  value, and net-pay calculation.
- Python remains responsible for workbook parsing/writing, employee roster
  matching, social-insurance resolution, EDI/site/fixed-hour application, and
  final payroll record assembly until those boundaries move behind parity tests.
- TypeScript and Python contract metadata now include deduction input, income-tax
  result, and final deduction result DTO shapes.

Verification evidence for this checkpoint:

- `cargo fmt --check`
- `cargo test --workspace`
- `buck2 test //crates/payroll-api:payroll_api_test`
- `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_payroll_api_contract -v`
- `npm run typecheck --prefix frontend`
- `git diff --check`
- `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

Slice spec: `docs/PAYROLL_RUST_DEDUCTION_FINALIZATION_SLICE.md`.

## Current implementation checkpoint: Rust payroll EI 65+ decision

Implemented on 2026-06-04 as the next payroll decision behavior slice:

- `crates/payroll-api` now exposes `Ei65EligibilityStatus`,
  `Ei65UnknownDefault`, `Ei65VerificationRecord`, `Ei65PayrollInput`,
  `Ei65PayrollResult`, `age_years_from_korean_identity`,
  `is_age_65_plus_for_period`, and `resolve_ei_65_for_payroll`.
- `PayrollApiService::resolve_ei_65_for_payroll` resolves the supplied-input
  Korean age-65+ employment-insurance payroll decision without reading KCOMWEL
  storage, tenant/site settings, live APIs, workbooks, EDI premiums, or payroll
  invoice rows.
- Rust preserves Python compatibility for valid-period month-end age checks,
  Korean RRN century/pivot parsing, `exempt`/`liable`/`unknown` status values,
  `skip`/`deduct` unknown defaults, management-number fallback, and the Korean
  unknown-warning wording.
- Python remains responsible for KCOMWEL CSV import/persistence, live provider
  calls, employee matching, site management-number lookup, EDI premium input
  resolution, payroll row mutation, and workbook I/O until those slices move to
  Rust behind parity tests.
- TypeScript and Python contract metadata now include EI 65+ supplied-input and
  result DTO shapes.

Verification evidence for this checkpoint:

- `cargo fmt --check`
- `cargo test --workspace`
- `buck2 test //crates/payroll-api:payroll_api_test`
- `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_employment_insurance_65 tests.test_payroll_employment_insurance tests.test_payroll_api_contract -v`
- `npm run typecheck --prefix frontend`
- `git diff --check`
- `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

Slice spec: `docs/PAYROLL_RUST_EI65_SLICE.md`.


## Current implementation checkpoint: Rust payroll EDI insurance premium application

Implemented on 2026-06-04 as the next payroll row-application behavior slice:

- `crates/payroll-api` now exposes `EdiPremiumSource`,
  `EdiInsuranceConfig`, `EdiInsurancePremiumRecord`,
  `EdiInsuranceInvoice`, `EdiInsuranceApplication`, and
  `apply_edi_premiums_to_invoice`.
- `PayrollApiService::apply_edi_premiums_to_invoice` applies a supplied latest
  EDI premium record to one invoice-compatible row without reading settings,
  EDI storage, live providers, rosters, site management-number stores, or
  workbooks.
- Rust preserves Python-compatible enabled/disabled and missing-record messages,
  EDI metadata fields, source values, long-term-care fallback rounding,
  age-exempt pension/health/LTC preservation, employment clearing/application,
  industrial-accident fields, and insurance-total recalculation.
- Python remains responsible for EDI CSV/Excel import, local EDI storage, future
  live provider calls, tenant/site config resolution, employee matching,
  site management-number resolution, and workbook I/O until those boundaries move
  behind parity tests.
- TypeScript and Python contract metadata now include EDI config, premium record,
  invoice, and application DTO shapes.

Verification evidence for this checkpoint:

- `cargo fmt --check`
- `cargo test --workspace`
- `buck2 test //crates/payroll-api:payroll_api_test`
- `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_edi_insurance tests.test_payroll_api_contract -v`
- `npm run typecheck --prefix frontend`
- `git diff --check`
- `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

Slice spec: `docs/PAYROLL_RUST_EDI_INSURANCE_SLICE.md`.

## Current implementation checkpoint: Rust payroll site-benefits application

Implemented on 2026-06-04 as the next payroll row-application behavior slice:

- `crates/payroll-api` now exposes `WorkersDayConfig`,
  `IdentityInsuranceConfig`, `SiteBenefitsConfig`, `SiteBenefitsInvoice`,
  `SiteBenefitsApplication`, and `apply_site_benefits_to_invoice`.
- `PayrollApiService::apply_site_benefits_to_invoice` applies supplied
  site-benefits config to one invoice-compatible row without reading settings,
  canonical workplace maps, identity-insurance ledgers, workbooks, or payroll
  totals.
- Rust preserves Python compatibility normalization, Workers' Day allowance
  rules, identity-guarantee insurance billing-month and already-applied
  suppression rules, source fields, and `_workers_day_source` /
  `_identity_insurance_source` compatibility keys.
- Python remains responsible for settings lookup, workplace canonicalization,
  identity-insurance ledger read/write, workbook I/O, and payroll subtotal/gross
  recalculation until those slices move to Rust behind parity tests.
- TypeScript and Python contract metadata now include site-benefits config,
  invoice, and application DTO shapes.

Verification evidence for this checkpoint:

- `cargo fmt --check`
- `cargo test --workspace`
- `buck2 test //crates/payroll-api:payroll_api_test`
- `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_site_benefits tests.test_payroll_api_contract -v`
- `npm run typecheck --prefix frontend`
- `git diff --check`
- `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

Slice spec: `docs/PAYROLL_RUST_SITE_BENEFITS_SLICE.md`.


## Current implementation checkpoint: Rust payroll invoice audit row

Implemented on 2026-06-04 as the next payroll audit behavior slice:

- `crates/payroll-api` now exposes `InvoiceAuditInvoice`,
  `InvoiceAuditRecord`, `InvoiceAuditRow`, `InvoiceAuditStatus`,
  `estimate_break_hours`, and `audit_invoice_row`.
- `PayrollApiService::audit_invoice_row` evaluates a supplied invoice row,
  workplace-hours policy, optional ledger record, and optional fixed-hours
  profile without reading settings stores, workbooks, or rosters.
- Rust preserves Python compatibility status labels, warning flag wording,
  break-hour estimation, base-salary formula text, fixed-hours flag composition,
  and ledger monthly-hour mismatch checks.
- Python remains responsible for settings lookup, record matching, fixed-profile
  resolution, workbook I/O, and UI text rendering until those slices move to
  Rust behind parity tests.
- TypeScript and Python contract metadata now include invoice-audit invoice,
  record, and row DTO shapes.

Verification evidence for this checkpoint:

- `cargo fmt --check`
- `cargo test --workspace`
- `buck2 test //crates/payroll-api:payroll_api_test`
- `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_invoice_audit tests.test_payroll_api_contract -v`
- `npm run typecheck --prefix frontend`
- `git diff --check`
- `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

Slice spec: `docs/PAYROLL_RUST_INVOICE_AUDIT_ROW_SLICE.md`.

## Current implementation checkpoint: Rust payroll workplace-hours application

Implemented on 2026-06-04 as the next payroll monthly-hours behavior slice:

- `crates/payroll-api` now exposes `WorkplaceHoursPolicy`,
  `WorkplaceHoursInvoice`, `WorkplaceMonthlyHoursResolution`,
  `WorkplaceMonthlyHoursApplication`, `resolve_monthly_work_hours`, and
  `apply_monthly_hours_to_invoice`.
- `PayrollApiService::apply_monthly_hours_to_invoice` applies a supplied
  workplace-hours policy to an invoice-compatible row without reading local
  tenant/site settings or org alias repositories.
- Rust preserves Python compatibility policy normalization, five mode values,
  209-hour fallback behavior, non-positive invoice-hour fallback behavior, and
  `_monthly_work_hours` / `_monthly_hours_source` metadata.
- Python remains responsible for settings persistence, site/tenant/global policy
  lookup, and canonical workplace aliases until those repository slices move to
  Rust.
- TypeScript and Python contract metadata now include workplace-hours policy,
  invoice, resolution, and application DTO shapes.

Verification evidence for this checkpoint:

- `cargo fmt --check`
- `cargo test --workspace`
- `buck2 test //crates/payroll-api:payroll_api_test`
- `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workplace_hours tests.test_payroll_api_contract -v`
- `npm run typecheck --prefix frontend`
- `git diff --check`
- `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

Slice spec: `docs/PAYROLL_RUST_WORKPLACE_HOURS_SLICE.md`.

## Current implementation checkpoint: Rust payroll fixed-hours application

Implemented on 2026-06-04 as the next payroll record-generation behavior slice:

- `crates/payroll-api` now exposes `FixedHoursProfile`,
  `FixedHoursInvoice`, `FixedHoursApplication`, and
  `apply_fixed_hours_to_invoice`.
- `PayrollApiService::apply_fixed_hours_to_invoice` applies a resolved
  fixed-hours profile to an invoice-compatible row without reading HR contracts,
  site templates, local settings, or roster files.
- Rust preserves Python compatibility metadata: original invoice hour fields are
  saved under `_invoice_*`, monthly hour source and fixed-hours profile metadata
  are emitted under `_monthly_*` and `_fixed_hours_*`, and audit flags keep the
  Korean labels used by payroll reviewers.
- Python remains responsible for resolving employee contracts, job-group
  templates, and settings snapshots until those repository/persistence slices
  are ported separately.
- TypeScript and Python contract metadata now include fixed-hours profile,
  invoice, and application DTO shapes.

Verification evidence for this checkpoint:

- `cargo fmt --check`
- `cargo test --workspace`
- `buck2 test //crates/payroll-api:payroll_api_test`
- `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_fixed_hours tests.test_payroll_api_contract -v`
- `npm run typecheck --prefix frontend`
- `git diff --check`
- `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

Slice spec: `docs/PAYROLL_RUST_FIXED_HOURS_SLICE.md`.

## Current implementation checkpoint: Rust payroll policy resolution

Implemented on 2026-06-04 as the next service-boundary behavior slice:

- `crates/payroll-api` now exposes `PayrollPolicySettings`,
  `OperationPolicySource`, `ResolvedOperationPolicy`, and
  `resolve_operation_policy`.
- Rust resolves supplied settings snapshots using site -> tenant -> global
  precedence and normalizes the selected `OperationPolicy` before response
  serialization.
- `PayrollApiService::validate_run_payload_with_policy_settings` validates a
  payroll payload using Rust policy resolution instead of a Python-resolved
  policy snapshot.
- Supplied workplace aliases can canonicalize site-policy lookup until Rust owns
  the org-config repository.
- TypeScript and Python contract metadata now name the Rust policy-resolution
  entrypoint, source values, and settings snapshot fields.

Verification evidence for this checkpoint:

- `cargo test -p bitween-payroll-api policy_resolution::tests`
- `cargo test -p bitween-payroll-api service::tests`
- Python policy/API contract tests for `tests.test_payroll_operation_policy` and
  `tests.test_payroll_api_contract`
- `npm run typecheck --prefix frontend`

Slice spec: `docs/PAYROLL_RUST_POLICY_RESOLUTION_SLICE.md`.


## Current implementation checkpoint: Rust payroll execution planning

Implemented on 2026-06-04 as the next service-boundary behavior slice:

- `crates/payroll-api` now exposes `PayrollExecutionPlan`,
  `PayrollExecutionStep`, `PayrollExecutionBackend`,
  `PayrollExecutionStepKind`, and `plan_payroll_execution`.
- `PayrollApiService::plan_run_request` turns a parsed request plus normalized
  operation-policy snapshot into deterministic invoice, attendance, or mixed
  execution steps.
- Rust preserves Python compatibility routing: explicit caller input types win,
  `auto` resolves from the policy snapshot, and mixed requests with only an
  attendance source plan an attendance fallback.
- Every plan currently names `python_compatibility` as the backend until Rust
  owns payroll output generation.
- TypeScript and Python contract metadata now include the execution-plan DTO,
  step kinds, backend value, and Rust service entrypoint.

Verification evidence for this checkpoint:

- `cargo test -p bitween-payroll-api execution_plan::tests`
- `cargo test -p bitween-payroll-api service::tests`
- Python payroll automation/API contract tests for `tests.test_payroll_automation`
  and `tests.test_payroll_api_contract`
- `npm run typecheck --prefix frontend`

Slice spec: `docs/PAYROLL_RUST_EXECUTION_PLAN_SLICE.md`.

## Required execution disciplines

- **Incremental implementation:** migrate thin vertical slices behind stable contracts; no big-bang rewrite.
- **Source-driven development:** before choosing or using Rust/Kubernetes libraries, verify current official docs and record the source in an ADR or implementation note.
- **Test-driven development:** write characterization tests for current behavior, then Rust contract/parity tests before implementation.
- **Doubt-driven development:** run adversarial review for architecture, migration boundaries, tenant isolation, concurrency, data migration, and security decisions.
- **Code review and quality:** every slice needs independent review across correctness, readability, architecture, security, and performance before merge.
- **Code simplification:** remove compatibility code only after parity is proven; avoid duplicating existing complexity in Rust.

## Migration phases

1. **Inventory and boundaries**
   - Map Python compatibility modules to domain capabilities.
   - Freeze external DTOs and state transitions.
   - Identify tenant/legal-entity authorization invariants.

2. **Contract and characterization tests**
   - Lock payroll, workflow, business-trip lifecycle, KPI, org/role, mobile attendance, and AI policy behavior.
   - Keep tests DAMP and outcome-focused.

3. **Rust architecture ADRs**
   - Choose HTTP framework, async runtime, persistence library, validation approach, error model, observability, and Kubernetes packaging with official-source citations.
   - Reject unsupported or undocumented patterns explicitly.

4. **First production slice**
   - Expand `crates/payroll-api` into the first service boundary or create a dedicated Rust API service crate.
   - Ship one endpoint family with Rust tests, TypeScript contract alignment, and compatibility parity.

5. **Workflow and trip lifecycle slice**
   - Port document state, execution tasks, business-trip lifecycle, overdue evaluation, escalation, report proof, and KPI reflection.
   - Preserve legal-tenant scoping and proof-gated transitions.

6. **Persistence and migration**
   - Move production state to a database/object-storage layer behind Rust repositories.
   - Run schema/data migrations as Kubernetes Jobs with audit evidence.

7. **Kubernetes productionization**
   - Add container builds, Deployments, Services, Ingress/Gateway route, ConfigMaps, Secrets, probes, HPA, CronJobs, and migration Jobs.
   - Store release manifests or Helm/Kustomize overlays under a dedicated deployment surface such as `deploy/kubernetes/`.
   - Verify readiness/liveness behavior and safe shutdown.

8. **Decommission compatibility code**
   - Prove zero production usage.
   - Remove compatibility adapters, tests, and docs in separate reviewable commits.

## Non-goals

- Do not start a broad Rust rewrite inside an unrelated feature gate.
- Do not treat local compatibility UI or JSON runtime stores as production deployment architecture.
- Do not add dependencies based on memory or popularity alone.
