# Spec: Payroll Rust service boundary and readiness slice

## Objective

Keep the payroll API on a production Rust service boundary. The boundary exposes
framework-neutral validation, health, readiness, authorization, and DTO shapes
that HTTP services, Kubernetes probes, preview routes, and frontend contracts can
consume without repo-owned Python.

G028 decommissioned the former repo-owned compatibility bridge; missing behavior
must be restored only through Rust/Buck2 services or TypeScript contract gates.

## Tech stack

- Rust crate: `crates/payroll-api`
- Serialization: `serde` and `serde_json`
- No new HTTP/runtime dependency in this slice
- Buck2 target: `//crates/payroll-api:payroll_api_test`

## Commands

```sh
buck2 build '<target>[clippy.txt]'
buck2 test //...
buck2 test //crates/payroll-api:payroll_api_test
npm run typecheck --prefix frontend
cd apps/bitween-platform-ui
npm run verify:no-python-source
npm run verify:buck2-only
```

Use `bash scripts/verify_rust_buck2_reindeer.sh` before merging when Buck2 or
Reindeer inputs change.

## Project structure

- `crates/payroll-api/src/service.rs` — framework-neutral service facade,
  health response, readiness response, and service configuration.
- `crates/payroll-api/src/lib.rs` — public exports and endpoint constants.
- `frontend/src/contracts/payrollApi.ts` — TypeScript readiness/health DTOs.
- `docs/PAYROLL_API_CONTRACT.md` — API response and endpoint contract.
- Migration docs under `docs/` — checkpoint updates.

## Code style

Rust service code should keep infrastructure concerns explicit but dependency-free:

```rust
let service = PayrollApiService::new(ServiceConfig::default());
let readiness = service.readiness(vec![ReadinessCheck::ready("policy", "Policy loaded")]);
```

Conventions:

- Stable snake_case JSON fields for frontend clients.
- Health response is cheap and probe-safe.
- Readiness aggregates named checks; any non-ready required check makes the
  service not ready.
- No secrets, tenant runtime data, or payroll output paths in readiness payloads.
- No new dependencies for this slice.

## Testing strategy

- RED: service tests assert public service types/functions before implementation.
- GREEN: implement the smallest service facade with deterministic serialized JSON.
- Regression: run Buck2 tests plus TypeScript contract gates.

## Boundaries

- Always keep readiness payloads stable and safe to expose to UI/probe callers.
- Always fail closed when auth, PostgreSQL, RustFS, or policy gates are missing.
- Ask first before adding Axum/Actix/Tower, database clients, JWT/WebAuthn crates,
  or new Kubernetes service shapes.
- Never claim production ownership for routes without auth, persistence, routing,
  observability, and rollout evidence.

## Success criteria

- Rust exposes `PayrollApiService` with validation, health, and readiness methods.
- Health/readiness DTOs serialize to stable JSON documented in the API contract.
- TypeScript frontend contracts name the same DTOs.
- Buck2 tests pass.
