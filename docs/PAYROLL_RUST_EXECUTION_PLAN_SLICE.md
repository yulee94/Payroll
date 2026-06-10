# Spec: Rust payroll execution planning slice

## Objective
Move the next payroll backend decision from legacy compatibility code into the Rust service boundary: given a validated `PayrollRunRequest` plus a resolved `OperationPolicySnapshot`, Rust must produce a deterministic execution plan describing which source paths are required and which compatibility executor steps will run. This advances the backend-to-Rust migration without changing payroll output generation yet.

## Tech Stack
- Rust crate: `crates/payroll-api` (`serde`, `serde_json`, std types only; no new runtime dependencies)
- Historical source: pre-G028 compatibility source was removed; keep parity evidence in Rust tests, TypeScript contracts, and documented fixtures.
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`
- Build surfaces: Cargo workspace and `crates/payroll-api/BUCK`

## Commands
- Format: `buck2 build '<target>[clippy.txt]'`
- Rust tests: `buck2 test //...`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- G028 retired the former compatibility gate; use Buck2 Rust tests plus TypeScript gates from AGENTS.md.
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `buck2 build '<target>[clippy.txt]'`

## Project Structure
- `crates/payroll-api/src/execution_plan.rs` — Rust execution plan DTOs and planning rules
- `crates/payroll-api/src/service.rs` — service facade method for planning parsed requests
- `crates/payroll-api/src/lib.rs` — public exports
- `crates/payroll-api/BUCK` — Buck input list update
- `frontend/src/contracts/payrollApi.ts` — TypeScript execution plan DTOs
- `Rust-owned contract` / `Rust parity test` — Rust parity metadata and tests
- `docs/` — migration/contract checkpoint docs

## Code Style
Rust DTOs remain framework-neutral, serializable, and explicit about stable string values.

```rust
let plan = plan_payroll_execution(&request, OperationPolicySnapshot::new(policy, "site"));
assert_eq!(plan.input_type, PayrollInputType::Attendance);
assert_eq!(plan.steps[0].kind, PayrollExecutionStepKind::BuildAttendanceInvoice);
```

## Testing Strategy
- RED first: add Rust tests that assert the plan behavior before implementation compiles.
- Cover explicit input requests, auto policy resolution, mixed fallback behavior, normalized policy serialization, and service delegation.
- Keep Rust tests as characterization/contract checks; Rust execution remains the fallback executor.
- Keep TypeScript compile-only checks for contract shape alignment.

## Boundaries
- Always: preserve Rust execution behavior and public field names; normalize policies in Rust; keep output generation untouched.
- Ask first: add runtime dependencies, change HTTP framework assumptions, remove compatibility adapters, or change payroll output file semantics.
- Never: commit payroll output data, employee rosters, tenant runtime data, secrets, or generated local runtime folders.

## Success Criteria
- Rust exposes `PayrollExecutionPlan`, stable step/backend enums, and `plan_payroll_execution`.
- `PayrollApiService` can plan a parsed run request using a policy snapshot.
- Plans distinguish explicit invoice/attendance/mixed requests from auto policy-derived choices.
- Mixed requests without invoice but with attendance preserve legacy compatibility by planning an attendance fallback.
- G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.
- All listed verification commands pass locally or have an explicitly documented external blocker.

## Task Checklist
- [x] Add failing Rust tests for execution planning behavior and service delegation.
- [x] Implement `execution_plan.rs` with serializable DTOs and no new dependencies.
- [x] Export the module, wire service facade, and update Buck inputs.
- [x] Update TypeScript/Rust contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [ ] Run verification, self-review, commit, PR, review, merge, and resync. (Verification and self-review complete; PR/merge/resync pending.)
