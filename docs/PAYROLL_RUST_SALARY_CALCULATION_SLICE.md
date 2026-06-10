# Spec: Rust payroll salary calculation slice

## Objective
Move the deterministic supplied-input `calculator.calculate_salary` orchestration into Rust. Rust should compose the already-ported earnings calculation, social-insurance calculation, and legacy-compatible income-tax calculation to return a complete salary result for one normalized employee row.

G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Tech Stack
- Rust crate: `crates/payroll-api` on Rust 2024 / Rust 1.96 with existing `serde`/`serde_json` only; no new runtime dependencies.
- Historical source: pre-G028 compatibility source was removed; keep parity evidence in Rust tests, TypeScript contracts, and documented fixtures.
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`.

## Commands
- Format: `buck2 build '<target>[clippy.txt]'`
- Rust tests: `buck2 test //...`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- G028 retired the former compatibility gate; use Buck2 Rust tests plus TypeScript gates from AGENTS.md.
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `buck2 build '<target>[clippy.txt]'`

## Project Structure
- `crates/payroll-api/src/salary.rs` — supplied-input salary DTOs, legacy-compatible income-tax helper, and pure salary calculation orchestration.
- `crates/payroll-api/src/service.rs` — service facade method for supplied-input salary calculation.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck source list.
- `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`, `Rust parity test` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust salary calculation stays pure and deterministic: callers supply already-normalized values, and Rust returns stable DTO fields without reading invoices, employee masters, settings, workbooks, EDI files, or tax-table files.

```rust
let result = calculate_payroll_salary(PayrollSalaryInput::new().with_name("홍길동"));
assert_eq!(result.name, "홍길동");
```

## Testing Strategy
- Add Rust unit tests for the full Rust parity example, raw amount fallback example, preset insurance/tax example, JSON serialization shape, and service delegation.
- Add Rust/TypeScript contract tests and TypeScript DTO definitions so frontend/server wrappers can rely on stable field names.
- Keep legacy compatibility behavior as parity source; this slice does not replace invoice parsing, employee master merging, age/EDI resolution, workbook I/O, or final payroll record assembly.

## Boundaries
- Always: preserve `calculator.calculate_salary` observable supplied-input fields, earnings output, insurance deduction values, income/local tax rounding, total deductions, net pay, uppercase `tax_method`, legacy-compatible won rounding, and stable labels (`name`, `emp_no`, `department`, `account_no`).
- Ask first: move invoice parsing, employee master merge, age/KCOMWEL lookup, EDI premium resolution, workbook parsing/writing, or final payroll record assembly into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, local payroll files, or generated runtime folders.

## Success Criteria
- Rust exposes `PayrollSalaryInput`, `PayrollSalaryDeductions`, `PayrollSalaryTaxMethod`, `PayrollSalaryResult`, `calculate_payroll_salary`, and `PayrollApiService::calculate_payroll_salary(input)`.
- Rust preserves legacy-compatible supplied-input salary calculation behavior for earnings, insurance deductions, income/local tax, total deductions, and net pay.
- G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add failing Rust tests for supplied salary, raw fallback, preset insurance/tax, serialization, and service behavior.
- [x] Implement salary DTOs and pure orchestration without new dependencies.
- [x] Export the salary API and wire service facade/Buck source list.
- [x] Update TypeScript/Rust contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
