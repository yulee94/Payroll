# Idiomatic Rust backend rewrite backlog

## Status

In progress. The Buck2/Reindeer foundation for the first Rust backend contract crate is in place; Python remains characterization-only until Rust parity is proven domain by domain. This is a production-quality rewrite track and is not an MVP shortcut.

## Goal

Rewrite backend code in idiomatic Rust while preserving the observable business behavior already covered by compatibility tests. The target runtime is the Kubernetes-native stack documented in `docs/KUBERNETES_NATIVE_STACK.md`.

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
