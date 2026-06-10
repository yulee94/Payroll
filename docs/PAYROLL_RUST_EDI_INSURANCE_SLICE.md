# Spec: Rust payroll EDI insurance premium application slice

## Objective
Move the deterministic EDI insurance-premium application rule from legacy compatibility code into Rust for already-supplied inputs. Rust should preserve the observable behavior of `core.payroll.edi_insurance.apply_edi_premiums_to_inv` after a Rust service has resolved whether EDI premiums are enabled and supplied an optional latest premium record for the employee/payroll period.

G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Tech Stack
- Rust crate: `crates/payroll-api` with existing `serde`/`serde_json` only; no new runtime dependencies.
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
- `crates/payroll-api/src/edi_insurance.rs` — EDI premium DTOs, invoice DTO, config DTO, and pure supplied-record application logic.
- `crates/payroll-api/src/service.rs` — service facade method for supplied-input EDI premium application.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck source list.
- `Rust parity test` — Rust parity coverage for compatibility behavior.
- `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`, `Rust parity test` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust EDI application stays pure and deterministic: callers supply invoice row, config, optional premium record, and payroll period. Rust returns the updated invoice plus applied status/message without reading settings, storage, EDI provider APIs, rosters, or workbooks.

```rust
let result = apply_edi_premiums_to_invoice(invoice, Some(&record), &config, "2026-06");
assert!(result.applied);
assert_eq!(result.invoice.edi_premium_badge, "EDI 조회");
```

## Testing Strategy
- Add Rust unit tests for disabled config, missing record, normal application, long-term-care fallback from EDI health premium, age-exempt pension/health/LTC preservation, employment clearing for zero EDI premium, industrial-accident fields, serialization shape, and service delegation.
- Keep Rust parity tests green to prove the compatibility adapter still behaves the same while Rust takes ownership of the supplied-input domain rule.
- Add Rust/TypeScript contract tests and TypeScript DTO definitions so frontend/server wrappers can rely on stable enum and field names.

## Boundaries
- Always: preserve legacy-compatible enabled/disabled messages, no-record message, EDI metadata fields, badge text, source values, positive-only pension/health/LTC overrides, LTC fallback as `round(health * 0.1295)`, age-exempt pension/health/LTC preservation, employment premium application/clearing behavior, industrial-accident fields, and insurance-total recalculation.
- Ask first: move EDI CSV/Excel import, local storage, live EDI provider/API calls, tenant/site settings lookup, site management-number resolution, employee matching, EI65 post-processing, or workbook I/O into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime EDI data, credentials/certificates, local EDI cache files, or generated runtime folders.

## Success Criteria
- Rust exposes `EdiPremiumSource`, `EdiInsuranceConfig`, `EdiInsurancePremiumRecord`, `EdiInsuranceInvoice`, `EdiInsuranceApplication`, and `apply_edi_premiums_to_invoice`.
- `PayrollApiService` delegates supplied-input EDI premium application through a framework-neutral method.
- Rust preserves legacy-compatible premium application, metadata fields, age-exempt handling, LTC fallback rounding, and serialized DTO field names.
- G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add failing Rust tests for disabled/missing/application/age-exempt/serialization/service behavior.
- [x] Implement EDI DTOs and pure application logic without new dependencies.
- [x] Export the EDI API and wire service facade/Buck source list.
- [x] Update TypeScript/Rust contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [x] Commit, PR, review, merge, and resync.
