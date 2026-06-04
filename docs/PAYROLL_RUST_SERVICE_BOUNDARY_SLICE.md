# Spec: Payroll Rust service boundary and readiness slice

## Objective

Move the payroll API from pure DTO/validation helpers toward a production Rust
service boundary. This slice adds a framework-neutral Rust service facade for
payroll validation and health/readiness responses that a future HTTP framework,
Kubernetes probe, or Tauri command can call without depending on Python modules.

This is still not the full backend rewrite. Python remains compatibility storage
and payroll execution until Rust service routing, persistence, auth, and rollout
evidence exist.

## Tech stack

- Rust crate: `crates/payroll-api`
- Serialization: existing `serde` and `serde_json`
- No new HTTP/runtime dependency in this slice
- Buck2 target: `//crates/payroll-api:payroll_api_test`

## Commands

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
npm run typecheck --prefix frontend
python -m unittest tests.test_payroll_api_contract -v
```

Use `bash scripts/verify_rust_buck2_reindeer.sh` before merging when Buck2/Reindeer
inputs change or as a final Rust build-system gate.

## Project structure

- `crates/payroll-api/src/service.rs` — framework-neutral service facade,
  health response, readiness response, and service configuration.
- `crates/payroll-api/src/lib.rs` — public exports and endpoint constants.
- `frontend/src/contracts/payrollApi.ts` — TypeScript readiness/health DTOs.
- `services/payroll_api_contract.py` and `docs/PAYROLL_API_CONTRACT.md` —
  compatibility contract metadata and examples.
- Migration docs under `docs/` — checkpoint updates.

## Code style

Rust service code should keep infrastructure concerns explicit but dependency-free:

```rust
let service = PayrollApiService::new(ServiceConfig::default());
let readiness = service.readiness(vec![ReadinessCheck::ready("policy", "Policy loaded")]);
```

Conventions:

- Stable snake_case JSON fields for frontend/desktop clients.
- Health response is cheap and always framework-neutral.
- Readiness is aggregated from named checks; any non-ready required check makes
  the service not ready.
- No secrets, tenant runtime data, or payroll output paths in readiness payloads.
- No new dependencies for this slice.

## Testing strategy

- RED: service tests assert public service types/functions before implementation.
- GREEN: implement the smallest service facade with deterministic serialized JSON.
- Regression: run Cargo, Buck2, Python contract, and frontend type checks.

## Boundaries

- Always: keep Python compatibility behavior intact.
- Always: keep readiness payloads stable and safe to expose to UI/probe callers.
- Ask first: adding Axum/Actix/Tower, database clients, JWT/WebAuthn crates, or Kubernetes manifests.
- Never: claim production Rust backend ownership until auth, persistence, routing,
  and Kubernetes deployment evidence exist.

## Success criteria

- Rust exposes `PayrollApiService` with validation, health, and readiness methods.
- Health/readiness DTOs serialize to stable JSON documented in the API contract.
- TypeScript frontend contracts name the same DTOs.
- Existing Python contract tests still pass.
- Cargo and Buck2 tests pass.

## Implementation plan

### Task 1: Add Rust service/readiness RED tests

Acceptance:

- Tests fail because `PayrollApiService`, `ServiceConfig`, and readiness DTOs do
  not exist yet.

Verification:

- `cargo test -p bitween-payroll-api service::tests` fails for missing symbols.

### Task 2: Implement framework-neutral service boundary

Acceptance:

- `PayrollApiService::validate_run_payload` delegates to Rust validation.
- `health()` returns service/version/status/uptime shape.
- `readiness()` aggregates named checks with `ready`, `degraded`, and `not_ready`
  outcomes.

Verification:

- `cargo test -p bitween-payroll-api` passes.

### Task 3: Align contracts/docs and verify

Acceptance:

- TypeScript/Python/Markdown contract surfaces include `/healthz` and
  `/readiness` shapes.
- Migration docs identify the completed service-boundary slice and remaining
  production gaps.

Verification:

- Commands in the Commands section pass.
