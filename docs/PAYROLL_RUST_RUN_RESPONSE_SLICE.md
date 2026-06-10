# Spec: Payroll Rust run response envelope slice

## Objective

Move payroll run-result response shaping into Rust-owned, framework-neutral code
while Rust payroll execution remains a backlog item. This slice makes the
Rust service boundary responsible for turning a supplied run result into the
stable API success/error envelope used by frontend, desktop, future HTTP, and
Kubernetes callers.

This is not the Rust payroll executor or persistence layer. The compatibility
Rust payroll execution remains a backlog item, but the response envelope it
must match is now specified and tested in Rust.

## Tech Stack

- Rust crate: `crates/payroll-api`
- Serialization: existing `serde` and `serde_json`
- TypeScript contract: `frontend/src/contracts/payrollApi.ts`
- Rust parity metadata/tests: `Rust-owned contract` and
  `Rust parity test`
- No new HTTP, database, async runtime, object-storage, or payroll execution
  dependency in this slice

## Commands

```sh
buck2 build '<target>[clippy.txt]'
buck2 test //...
buck2 test //crates/payroll-api:payroll_api_test
# G028 retired the former compatibility gate; use Buck2 Rust tests plus TypeScript gates from AGENTS.md.
npm run typecheck --prefix frontend
git diff --check
```

## Project Structure

- `crates/payroll-api/src/run.rs` — Rust run result input DTO and API response
  envelope shaping.
- `crates/payroll-api/src/service.rs` — service facade method for formatting a
  supplied payroll run result.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports
  and build graph inputs.
- `frontend/src/contracts/payrollApi.ts` — TypeScript success/run-failure DTOs.
- `Rust-owned contract` and `docs/PAYROLL_API_CONTRACT.md` — stable
  contract examples and migration notes.
- `docs/RUST_BACKEND_MIGRATION.md` and `docs/BUILD_AND_RUNTIME_TRANSITION.md` —
  Rust migration checkpoint updates.

## Code Style

Keep the envelope deterministic and data-only:

```rust
let response = service.run_response(
    PayrollRunResult::success(scope, PayrollInputType::Mixed)
        .with_count(28)
        .with_path("ledger", "rustfs://bucket/payroll.xlsx"),
    "payroll-run-2026-05-acme-site-a",
);
```

Conventions:

- Stable snake_case JSON fields.
- `scope` is the external display string; `scope_key` is the internal
  compatibility key.
- `status` is `success` when `ok=true`, otherwise `error`.
- `will_run` is always `true` for execution results.
- `can_run` mirrors `ok` for execution results.
- `error_code` is empty on success and `payroll_run_failed` on run failure.
- `details` is an empty object for run-result envelopes.
- `request_id` is omitted when empty.
- Never serialize internal exception objects.

## Testing Strategy

- RED: add Rust run-response tests that reference missing `PayrollRunResult`,
  `PayrollRunResponse`, and service facade behavior.
- GREEN: implement the smallest Rust DTOs and serialization behavior that match
  documented `payroll_api_response(result, request_id=...)`.
- Regression: run Buck2 and Rust/TypeScript contract tests, frontend typecheck,
  and whitespace checks.

## Boundaries

- Always: preserve legacy compatibility adapter behavior while rollout is
  incomplete.
- Always: keep known operation policy fields normalized through existing Rust
  `OperationPolicy`.
- Always: treat run failure envelopes differently from validation errors:
  validation errors have `will_run=false`, run failures have `will_run=true` and
  `error_code=payroll_run_failed`.
- Ask first: adding payroll execution, persistence, object storage, an HTTP
  framework, async runtime, or new dependencies.
- Never: expose exception objects, payroll employee rosters from local runtime
  data, tenant secrets, or credentials.

## Success Criteria

- Rust exposes `PayrollRunResult`, `PayrollRunResponse`, and
  `run_response_from_result`.
- `PayrollApiService::run_response` returns the same stable documented envelope as the Rust contract
  `payroll_api_response` for success and execution failure cases.
- TypeScript contract distinguishes validation errors from run failures so
  `will_run` and `can_run` are typed correctly.
- Rust contract metadata includes a representative run-failure response and
  states that Rust owns run-result envelope shaping.
- Migration docs record this completed checkpoint and keep executor/persistence
  and Rust executor backlog as remaining work.
- Verification commands in this spec pass locally.

## Implementation Plan

### Task 1: Add Rust run-response RED tests

Acceptance:

- Tests assert success and run-failure envelope fields, request ID omission,
  normalized operation policy serialization, and service facade delegation.
- Tests fail before implementation because run-response types/functions do not
  exist.

Verification:

- `buck2 test //crates/payroll-api:payroll_api_test` fails for missing symbols.

### Task 2: Implement Rust run-response DTOs

Acceptance:

- DTOs serialize to the stable legacy-compatible envelope for success and run
  failure results.
- No exception field exists in the serialized response.
- `OperationPolicy` is normalized before serialization.

Verification:

- `buck2 test //crates/payroll-api:payroll_api_test` passes.

### Task 3: Add service facade and align contracts/docs

Acceptance:

- `PayrollApiService::run_response` delegates to Rust response shaping.
- TypeScript/Rust/Markdown contract surfaces document success, validation
  error, and run-failure response shapes.
- Migration docs identify this Rust checkpoint and remaining production gaps.

Verification:

- Commands in the Commands section pass.
