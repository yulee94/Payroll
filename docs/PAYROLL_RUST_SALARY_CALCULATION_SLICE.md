# Spec: Rust payroll salary calculation slice

## Objective
Move the deterministic supplied-input `calculator.calculate_salary` orchestration into Rust. Rust should compose the already-ported earnings calculation, social-insurance calculation, and Python-compatible income-tax calculation to return a complete salary result for one normalized employee row.

Python may still parse invoices, merge employee masters, normalize strings/cell values, determine age/KCOMWEL or EDI overrides, write workbooks, and assemble final payroll records in this slice. Rust owns only the pure calculation from supplied normalized numeric payroll inputs to earnings, insurance/tax deductions, total deductions, and net pay.

## Tech Stack
- Rust crate: `crates/payroll-api` on Rust 2024 / Rust 1.96 with existing `serde`/`serde_json` only; no new runtime dependencies.
- Compatibility source: `calculator.py::calculate_salary`, plus the Rust-owned `earnings`, `social_insurance`, and `deductions` helper modules.
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`.

## Commands
- Format: `cargo fmt --check`
- Rust tests: `cargo test --workspace`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- Python contract tests: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_payroll_api_contract -v`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/payroll-api/src/salary.rs` — supplied-input salary DTOs, Python-compatible income-tax helper, and pure salary calculation orchestration.
- `crates/payroll-api/src/service.rs` — service facade method for supplied-input salary calculation.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck source list.
- `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`, `tests/test_payroll_api_contract.py` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust salary calculation stays pure and deterministic: callers supply already-normalized values, and Rust returns stable DTO fields without reading invoices, employee masters, settings, workbooks, EDI files, or tax-table files.

```rust
let result = calculate_payroll_salary(PayrollSalaryInput::new().with_name("홍길동"));
assert_eq!(result.name, "홍길동");
```

## Testing Strategy
- Add Rust unit tests for the full Python parity example, raw amount fallback example, preset insurance/tax example, JSON serialization shape, and service delegation.
- Add Python contract tests and TypeScript DTO definitions so frontend/server wrappers can rely on stable field names.
- Keep Python compatibility behavior as parity source; this slice does not replace invoice parsing, employee master merging, age/EDI resolution, workbook I/O, or final payroll record assembly.

## Boundaries
- Always: preserve `calculator.calculate_salary` observable supplied-input fields, earnings output, insurance deduction values, income/local tax rounding, total deductions, net pay, uppercase `tax_method`, Python-compatible won rounding, and stable labels (`name`, `emp_no`, `department`, `account_no`).
- Ask first: move invoice parsing, employee master merge, age/KCOMWEL lookup, EDI premium resolution, workbook parsing/writing, or final payroll record assembly into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, local payroll files, or generated runtime folders.

## Success Criteria
- Rust exposes `PayrollSalaryInput`, `PayrollSalaryDeductions`, `PayrollSalaryTaxMethod`, `PayrollSalaryResult`, `calculate_payroll_salary`, and `PayrollApiService::calculate_payroll_salary(input)`.
- Rust preserves Python-compatible supplied-input salary calculation behavior for earnings, insurance deductions, income/local tax, total deductions, and net pay.
- Contracts/docs identify Rust as owner of supplied-input salary calculation while Python remains the invoice/master/age/EDI/workbook/final-record bridge.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add failing Rust tests for supplied salary, raw fallback, preset insurance/tax, serialization, and service behavior.
- [x] Implement salary DTOs and pure orchestration without new dependencies.
- [x] Export the salary API and wire service facade/Buck source list.
- [x] Update TypeScript/Python contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
