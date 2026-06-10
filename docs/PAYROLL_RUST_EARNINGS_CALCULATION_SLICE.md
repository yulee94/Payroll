# Spec: Rust payroll earnings calculation slice

## Objective

Keep deterministic supplied-input payroll earnings, gross-pay, non-taxable-pay,
and taxable-pay calculation in Rust. Callers supply normalized numeric payroll
row inputs; Rust returns stable earnings DTOs used by the payroll service and
frontend contracts.

G028 decommissioned the former repo-owned compatibility bridge; missing behavior
must be restored only through Rust/Buck2 services or TypeScript contract gates.

## Tech Stack

- Rust crate: `crates/payroll-api` on Rust 2024 / Rust 1.96 with existing
  `serde`/`serde_json` only; no new runtime dependencies.
- Parity source: Rust-owned payroll fixtures and documented earnings invariants.
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`,
  `frontend/src/contracts/payrollApi.ts`, and Rust API metadata.

## Commands

- Format/lint: `buck2 build '<target>[clippy.txt]'`
- Rust tests: `buck2 test //...`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`

## Project Structure

- `crates/payroll-api/src/earnings.rs` — constants, DTOs, helpers, and pure
  earnings/gross/taxable calculation logic.
- `crates/payroll-api/src/service.rs` — service facade method for supplied-input
  earnings calculation.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports
  and Buck source list.
- `frontend/src/contracts/payrollApi.ts` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style

Rust earnings calculation stays pure and deterministic: callers supply numeric
values already admitted through reviewed intake. Rust returns stable DTO fields
without reading invoices, employee masters, settings, workbooks,
social-insurance files, or tax tables.

```rust
let result = calculate_payroll_earnings(PayrollEarningsInput::new().with_base_salary(2_090_000.0));
assert_eq!(result.earnings.base_salary, 2_090_000);
```

## Testing Strategy

- Add Rust unit tests for ordinary-hourly precedence, weekly holiday pay
  proration, overlap premium, full earnings/gross/taxable calculation,
  raw-amount fallback behavior, meal non-taxable cap, serialization shape, and
  service delegation.
- Add TypeScript DTO definitions so frontend/server wrappers can rely on stable
  field names.
- Keep invoice parsing, employee master merging, insurance/tax/deduction
  orchestration, and record assembly in separate Rust service slices.

## Boundaries

- Always preserve standard monthly hours `209`, meal allowance per day `5_500`,
  overtime premium `1.5`, night premium `0.5`, holiday premium `1.5`, overlap
  premium `0.5`, weekly holiday pay proration, raw amount fallback,
  won rounding, and meal non-taxable cap `200_000`.
- Ask first before moving invoice parsing, employee master merge,
  social-insurance orchestration, tax/deduction orchestration, workbook
  parsing/writing, or final payroll record assembly into this slice.
- Never commit payroll outputs, employee rosters, tenant runtime data,
  credentials, local payroll files, or generated runtime folders.

## Success Criteria

- Rust exposes `PayrollEarningsInput`, `PayrollEarningsBreakdown`,
  `PayrollEarningsHours`, `PayrollEarningsResult`, `calculate_payroll_earnings`,
  `calculate_ordinary_hourly`, `calculate_weekly_holiday_pay`,
  `calculate_overlap_premium`, and `PayrollApiService::calculate_payroll_earnings(input)`.
- Buck2 and TypeScript contract gates pass locally or carry explicit blockers.
