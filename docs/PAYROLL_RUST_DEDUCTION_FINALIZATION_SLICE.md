# Spec: Rust payroll deduction finalization slice

## Objective

Keep deterministic final payroll deduction and net-pay calculation in Rust for
already-supplied payroll row totals. The slice covers simplified tax lookup,
preset-tax precedence, local tax, identity-guarantee deduction handling,
total-deduction, and net-pay behavior after gross pay, insurance totals, and
optional roster-provided overrides are already resolved.

G028 decommissioned the former repo-owned compatibility bridge; missing behavior
must be restored only through Rust/Buck2 services or TypeScript contract gates.

## Tech Stack

- Rust crate: `crates/payroll-api` on Rust 2024 / Rust 1.96 with existing
  `serde`/`serde_json` only; no new runtime dependencies.
- Parity source: Rust-owned payroll fixtures and documented deduction/tax
  invariants.
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`,
  `frontend/src/contracts/payrollApi.ts`, and Rust API metadata.

## Commands

- Format/lint: `buck2 build '<target>[clippy.txt]'`
- Rust tests: `buck2 test //...`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`

## Project Structure

- `crates/payroll-api/src/deductions.rs` — tax table, DTOs, and pure final
  deduction/net-pay logic.
- `crates/payroll-api/src/service.rs` — service facade method for supplied-input
  deduction finalization.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports
  and Buck source list.
- `frontend/src/contracts/payrollApi.ts` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style

Rust deduction finalization stays pure and deterministic: callers supply numeric
payroll totals and optional preset tax values. Rust returns stable DTO fields
without reading settings, rosters, payroll workbooks, or tax-table files.

```rust
let result = finalize_payroll_deductions(PayrollDeductionInput::new(3_000_000, 300_000));
assert_eq!(result.net_pay, 2_469_000);
```

## Testing Strategy

- Add Rust unit tests for simplified tax bracket lookup, preset-income-tax with
  automatic local tax, preset local-tax override, high-income fallback formula,
  identity-guarantee deduction absolute-value handling, negative taxable floor
  behavior, serialization shape, and service delegation.
- Add TypeScript DTO definitions so frontend/server wrappers can rely on stable
  enum and field names.
- Keep workbook assembly, roster matching, and source-file sync in separate Rust
  service slices.

## Boundaries

- Always preserve simplified tax table brackets, high-income fallback formula,
  preset income-tax precedence, preset local-tax precedence, won/tens rounding,
  taxable pay as `gross - insurance`, identity-guarantee deduction absolute-value
  inclusion, and net-pay calculation.
- Ask first before moving workbook parsing/writing, roster matching,
  social-insurance resolution, employee tax-table storage, or final payroll record
  assembly into this slice.
- Never commit payroll outputs, employee rosters, tenant runtime data,
  credentials, local tax files, or generated runtime folders.

## Success Criteria

- Rust exposes `PayrollTaxMethod`, `PayrollDeductionInput`,
  `PayrollDeductionResult`, `lookup_simplified_income_tax`,
  `calculate_payroll_income_tax`, and `finalize_payroll_deductions`.
- `PayrollApiService` delegates supplied-input deduction finalization through a
  framework-neutral method.
- Buck2 and TypeScript contract gates pass locally or carry explicit blockers.
