# Spec: Rust payroll execution planning slice

## Objective
Move the next payroll backend decision from Python compatibility code into the Rust service boundary: given a validated `PayrollRunRequest` plus a resolved `OperationPolicySnapshot`, Rust must produce a deterministic execution plan describing which source paths are required and which compatibility executor steps will run. This advances the backend-to-Rust migration without changing payroll output generation yet.

## Tech Stack
- Rust crate: `crates/payroll-api` (`serde`, `serde_json`, std types only; no new runtime dependencies)
- Compatibility source: `services/payroll_automation.py` routing behavior
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`
- Build surfaces: Cargo workspace and `crates/payroll-api/BUCK`

## Commands
- Format: `cargo fmt --check`
- Rust tests: `cargo test --workspace`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- Python characterization/contract tests: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_payroll_automation tests.test_payroll_api_contract tests.test_payroll_api_adapter -v`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/payroll-api/src/execution_plan.rs` — Rust execution plan DTOs and planning rules
- `crates/payroll-api/src/service.rs` — service facade method for planning parsed requests
- `crates/payroll-api/src/lib.rs` — public exports
- `crates/payroll-api/BUCK` — Buck input list update
- `frontend/src/contracts/payrollApi.ts` — TypeScript execution plan DTOs
- `services/payroll_api_contract.py` / `tests/test_payroll_api_contract.py` — compatibility metadata and tests
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
- Keep Python tests as characterization/contract checks; Python execution remains the fallback executor.
- Keep TypeScript compile-only checks for contract shape alignment.

## Boundaries
- Always: preserve Python execution behavior and public field names; normalize policies in Rust; keep output generation untouched.
- Ask first: add runtime dependencies, change HTTP framework assumptions, remove compatibility adapters, or change payroll output file semantics.
- Never: commit payroll output data, employee rosters, tenant runtime data, secrets, or generated local runtime folders.

## Success Criteria
- Rust exposes `PayrollExecutionPlan`, stable step/backend enums, and `plan_payroll_execution`.
- `PayrollApiService` can plan a parsed run request using a policy snapshot.
- Plans distinguish explicit invoice/attendance/mixed requests from auto policy-derived choices.
- Mixed requests without invoice but with attendance preserve Python compatibility by planning an attendance fallback.
- Contracts/docs identify Rust as the owner of execution routing/planning while Python remains the compatibility executor.
- All listed verification commands pass locally or have an explicitly documented external blocker.

## Task Checklist
- [x] Add failing Rust tests for execution planning behavior and service delegation.
- [x] Implement `execution_plan.rs` with serializable DTOs and no new dependencies.
- [x] Export the module, wire service facade, and update Buck inputs.
- [x] Update TypeScript/Python contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [ ] Run verification, self-review, commit, PR, review, merge, and resync. (Verification and self-review complete; PR/merge/resync pending.)
