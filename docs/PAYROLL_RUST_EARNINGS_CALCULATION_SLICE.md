# Spec: Rust payroll earnings calculation slice

## Objective
Move the deterministic supplied-input payroll earnings, gross-pay, non-taxable-pay, and taxable-pay calculation from Python compatibility code into Rust. Rust should preserve the observable behavior of the earnings half of `calculator.calculate_salary` plus helpers `calc_ordinary_hourly`, `calc_weekly_holiday_pay`, and `calc_overlap_premium` once callers supply normalized numeric payroll row inputs.

Python may still parse invoices, merge employee masters, normalize strings/cell values, calculate social insurance and taxes, finalize deductions, and assemble final payroll records in this slice. Rust owns only the pure calculation from supplied numeric earnings inputs to ordinary hourly wage, adjusted overtime hours, earnings breakdown, gross pay, non-taxable meal cap, and taxable pay.

## Tech Stack
- Rust crate: `crates/payroll-api` on Rust 2024 / Rust 1.96 with existing `serde`/`serde_json` only; no new runtime dependencies.
- Compatibility sources: `calculator.py` (`calc_ordinary_hourly`, `calc_weekly_holiday_pay`, `calc_overlap_premium`, earnings block in `calculate_salary`) and `utils.py` (`STANDARD_MONTHLY_HOURS`, `MEAL_ALLOWANCE_PER_DAY`, `is_likely_hours`, `round_won`).
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
- `crates/payroll-api/src/earnings.rs` — constants, DTOs, helpers, and pure earnings/gross/taxable calculation logic.
- `crates/payroll-api/src/service.rs` — service facade method for supplied-input earnings calculation.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck source list.
- `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`, `tests/test_payroll_api_contract.py` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust earnings calculation stays pure and deterministic: callers supply numeric values already parsed from Python compatibility code. Rust returns stable DTO fields without reading invoices, employee masters, settings, workbooks, social-insurance files, or tax tables.

```rust
let result = calculate_payroll_earnings(PayrollEarningsInput::new().with_base_salary(2_090_000.0));
assert_eq!(result.earnings.base_salary, 2_090_000);
```

## Testing Strategy
- Add Rust unit tests for ordinary-hourly precedence, weekly holiday pay proration, overlap premium, full earnings/gross/taxable calculation, raw-amount fallback behavior, meal non-taxable cap, serialization shape, and service delegation.
- Add Python contract tests and TypeScript DTO definitions so frontend/server wrappers can rely on stable field names.
- Keep Python compatibility behavior as parity source; this slice does not replace invoice parsing, employee master merging, insurance/tax/deduction calculation, or record assembly.

## Boundaries
- Always: preserve standard monthly hours `209`, meal allowance per day `5_500`, overtime premium `1.5`, night premium `0.5`, holiday premium `1.5`, overlap premium `0.5`, weekly holiday pay proration, raw amount fallback using `is_likely_hours`, Python-compatible won rounding, and meal non-taxable cap `200_000`.
- Ask first: move invoice parsing, employee master merge, social-insurance calculation orchestration, tax/deduction orchestration, workbook parsing/writing, or final payroll record assembly into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, local payroll files, or generated runtime folders.

## Success Criteria
- Rust exposes `PayrollEarningsInput`, `PayrollEarningsBreakdown`, `PayrollEarningsHours`, `PayrollEarningsResult`, `calculate_payroll_earnings`, `calculate_ordinary_hourly`, `calculate_weekly_holiday_pay`, `calculate_overlap_premium`, and `PayrollApiService::calculate_payroll_earnings(input)`.
- Rust preserves Python-compatible supplied-input earnings, gross-pay, non-taxable-pay, and taxable-pay behavior.
- Contracts/docs identify Rust as owner of supplied-input earnings calculation while Python remains the invoice/master/insurance/tax/deduction/record bridge.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add failing Rust tests for helper, earnings, raw fallback, serialization, and service behavior.
- [x] Implement earnings DTOs and pure calculation logic without new dependencies.
- [x] Export the earnings API and wire service facade/Buck source list.
- [x] Update TypeScript/Python contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
