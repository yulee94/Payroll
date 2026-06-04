# Spec: Rust payroll deduction finalization slice

## Objective
Move the deterministic final payroll deduction and net-pay calculation rule from Python compatibility code into Rust for already-supplied payroll row totals. Rust should preserve the observable behavior of `tax.calculate_tax` and the final deduction block in `payroll_builder.build_payroll_records` after Python has resolved gross pay, insurance totals, identity-guarantee insurance deductions, and optional roster-provided tax overrides.

Python may still parse workbooks, match employee rosters, resolve social insurance, apply EDI/site/fixed-hour rules, and assemble final payroll records in this slice. Rust must own the pure calculation that turns supplied gross pay, insurance total, optional preset income/local tax, and identity-guarantee insurance deduction into taxable pay, income tax, local income tax, total deduction, and net pay.

## Tech Stack
- Rust crate: `crates/payroll-api` on Rust 2024 / Rust 1.96 with existing `serde`/`serde_json` only; no new runtime dependencies.
- Compatibility sources: `tax.py` (`lookup_simplified_tax`, `calculate_tax`) and `payroll_builder.py` final deduction block.
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`.

## Commands
- Format: `cargo fmt --check`
- Rust tests: `cargo test --workspace`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- Python contract/compatibility tests: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_payroll_api_contract -v`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/payroll-api/src/deductions.rs` — tax table, DTOs, and pure final deduction/net-pay logic.
- `crates/payroll-api/src/service.rs` — service facade method for supplied-input deduction finalization.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck source list.
- `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`, `tests/test_payroll_api_contract.py` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust deduction finalization stays pure and deterministic: callers supply numeric payroll totals and optional preset tax values. Rust returns stable DTO fields without reading settings, rosters, payroll workbooks, or tax-table files.

```rust
let result = finalize_payroll_deductions(PayrollDeductionInput::new(3_000_000, 300_000));
assert_eq!(result.net_pay, 2_469_000);
```

## Testing Strategy
- Add Rust unit tests for simplified tax bracket lookup, preset-income-tax with automatic local tax, preset local-tax override, high-income fallback formula, identity-guarantee deduction absolute-value handling, negative taxable floor behavior, serialization shape, and service delegation.
- Add Python contract tests and TypeScript DTO definitions so frontend/server wrappers can rely on stable enum and field names.
- Keep the Python compatibility tax/deduction behavior as the source of parity; this slice does not replace workbook assembly.

## Boundaries
- Always: preserve simplified tax table brackets, high-income fallback formula `(taxable - 1_500_000) * 0.03`, preset income-tax precedence, preset local-tax precedence, Python-compatible won/tens rounding, taxable pay as `gross - insurance`, identity-guarantee deduction absolute-value inclusion, and net-pay calculation.
- Ask first: move workbook parsing/writing, roster matching, social insurance resolution, employee tax-table storage, or final payroll record assembly into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, local tax files, or generated runtime folders.

## Success Criteria
- Rust exposes `PayrollTaxMethod`, `PayrollDeductionInput`, `PayrollDeductionResult`, `lookup_simplified_income_tax`, `calculate_payroll_income_tax`, and `finalize_payroll_deductions`.
- `PayrollApiService` delegates supplied-input deduction finalization through a framework-neutral method.
- Rust preserves Python-compatible simplified tax, preset tax override, total-deduction, and net-pay behavior.
- Contracts/docs identify Rust as owner of supplied-input final deduction/net-pay calculation while Python remains the workbook/roster/record assembly bridge.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add failing Rust tests for tax table/preset/fallback/deduction/serialization/service behavior.
- [x] Implement deduction DTOs and pure calculation logic without new dependencies.
- [x] Export the deduction API and wire service facade/Buck source list.
- [x] Update TypeScript/Python contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [x] Commit, PR, review, merge, and resync.
