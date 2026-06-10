# Spec: Rust payroll social-insurance calculation slice

## Objective

Keep deterministic supplied-input Korean social-insurance calculation in Rust.
Callers supply taxable pay, optional preset pension/health values, and an
already-resolved insurance-exempt flag; Rust returns stable insurance DTOs used by
the payroll service and frontend contracts.

G028 decommissioned the former repo-owned compatibility bridge; missing behavior
must be restored only through Rust/Buck2 services or TypeScript contract gates.

## Tech Stack

- Rust crate: `crates/payroll-api` on Rust 2024 / Rust 1.96 with existing
  `serde`/`serde_json` only; no new runtime dependencies.
- Parity source: Rust-owned payroll fixtures and documented social-insurance
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

- `crates/payroll-api/src/social_insurance.rs` — constants, DTOs, and pure
  social-insurance calculation logic.
- `crates/payroll-api/src/service.rs` — service facade method for supplied-input
  social-insurance calculation.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports
  and Buck source list.
- `frontend/src/contracts/payrollApi.ts` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style

Rust social-insurance calculation stays pure and deterministic: callers supply
numeric payroll inputs and pre-resolved exemption status. Rust returns stable DTO
fields without reading employee masters, identities, EDI files, settings, or
workbooks.

```rust
let result = calculate_social_insurance(SocialInsuranceInput::new(3_000_000.0));
assert_eq!(result.total, 282_122);
```

## Testing Strategy

- Add Rust unit tests for base-rate calculation, pension floor/ceiling clamps,
  preset pension/health precedence, exemption zeroing, won/tens rounding,
  serialization shape, and service delegation.
- Add TypeScript DTO definitions so frontend/server wrappers can rely on stable
  field names.
- Keep identity, KCOMWEL age-65 decisions, EDI premium import/override,
  employee-master lookup, workbook parsing/writing, and final payroll record
  mutation in separate Rust service slices.

## Boundaries

- Always preserve pension rate `0.045`, health rate `0.03545`, long-term-care
  ratio `0.1295`, employment-insurance worker rate `0.009`, pension floor
  `390_000`, pension ceiling `6_170_000`, positive preset precedence, won
  rounding, employment-insurance tens rounding, and exemption zeroing.
- Ask first before moving identity parsing, KCOMWEL decisions, EDI premium
  import/override, employee-master lookup, workbook parsing/writing, or final
  payroll record mutation into this slice.
- Never commit payroll outputs, employee rosters, tenant runtime data,
  credentials, local tax/insurance files, or generated runtime folders.

## Success Criteria

- Rust exposes `SocialInsuranceInput`, `SocialInsuranceResult`,
  `calculate_social_insurance`, `calculate_employment_insurance`, and
  `PayrollApiService::calculate_social_insurance(input)`.
- Buck2 and TypeScript contract gates pass locally or carry explicit blockers.
