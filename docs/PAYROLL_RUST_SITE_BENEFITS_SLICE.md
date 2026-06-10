# Spec: Rust payroll site-benefits application slice

## Objective
Move the deterministic site-benefits application rules from legacy compatibility code into Rust for already-supplied inputs. Rust should preserve the observable behavior of `core.payroll.site_benefits.normalize_*`, `calc_workers_day_allowance`, and the pure portion of `apply_site_benefits_to_invoice` once a Rust service has resolved site/tenant/global settings and checked whether identity insurance was already applied for the year.

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
- `crates/payroll-api/src/site_benefits.rs` — config DTOs, invoice DTO, and pure application logic.
- `crates/payroll-api/src/service.rs` — service facade method for applying supplied site benefits.
- `crates/payroll-api/src/lib.rs` — public exports.
- `Rust parity test` — Rust parity coverage for pure supplied-config parity.
- `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`, `Rust parity test` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust site-benefit application stays pure and deterministic: callers supply invoice row, resolved workers-day config, resolved identity-insurance config, source labels, period, and whether identity insurance was already applied; Rust returns the updated invoice plus applied amounts and source labels without reading or writing settings/ledgers.

```rust
let result = apply_site_benefits_to_invoice(invoice, config, "2026-05");
assert_eq!(result.invoice.workers_day_allowance, 10_000);
assert_eq!(result.invoice.identity_guarantee_insurance_deduction, -20_000);
```

## Testing Strategy
- Add Rust parity coverage for supplied-config application parity and non-May/default/already-applied behavior.
- Add Rust unit tests for config normalization, Workers' Day invoice/default behavior, identity-insurance month/already-applied behavior, serialization shape, and service delegation.
- Keep tests outcome-focused on applied amounts, source fields, and serialized compatibility keys.

## Boundaries
- Always: preserve positive amount clamping, May-only fixed Workers' Day default behavior, billing-month-only identity-insurance deduction, already-applied suppression, and compatibility field names.
- Ask first: move site/tenant/global setting lookup, canonical workplace alias lookup, identity-insurance ledger read/write, payroll subtotal/gross recalculation, or workbook I/O into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, or generated local runtime folders.

## Success Criteria
- Rust exposes `WorkersDayConfig`, `IdentityInsuranceConfig`, `SiteBenefitsConfig`, `SiteBenefitsInvoice`, `SiteBenefitsApplication`, and `apply_site_benefits_to_invoice`.
- `PayrollApiService` delegates supplied-config site-benefits application through a framework-neutral method.
- Rust preserves legacy-compatible normalization, amount calculation, source labels, updated invoice fields, and serialized DTO field names.
- G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add Rust parity coverage for supplied-config site-benefits application parity.
- [x] Add failing Rust tests for normalization, application, serialization, and service delegation.
- [x] Implement site-benefits DTOs and `apply_site_benefits_to_invoice` without new dependencies.
- [x] Export the site-benefits API and wire service facade.
- [x] Update TypeScript/Rust contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [x] Commit, PR, review, merge, and resync.
