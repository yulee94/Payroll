# Spec: Rust payroll site-benefits application slice

## Objective
Move the deterministic site-benefits application rules from Python compatibility code into Rust for already-supplied inputs. Rust should preserve the observable behavior of `core.payroll.site_benefits.normalize_*`, `calc_workers_day_allowance`, and the pure portion of `apply_site_benefits_to_invoice` once Python has resolved site/tenant/global settings and checked whether identity insurance was already applied for the year.

Python may still load settings, canonicalize workplace aliases, inspect/persist identity-insurance ledgers, parse workbooks, and recalculate payroll totals in this slice. Rust must own normalization of supplied benefit configs plus the pure calculation/application of Workers' Day allowance and identity-guarantee insurance deduction fields on one supplied invoice row.

## Tech Stack
- Rust crate: `crates/payroll-api` with existing `serde`/`serde_json` only; no new runtime dependencies.
- Compatibility source: `core/payroll/site_benefits.py` (`normalize_workers_day_config`, `normalize_identity_insurance_config`, `calc_workers_day_allowance`, `apply_site_benefits_to_invoice`).
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`.

## Commands
- Format: `cargo fmt --check`
- Rust tests: `cargo test --workspace`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- Python characterization/contract tests: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_site_benefits tests.test_payroll_api_contract -v`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/payroll-api/src/site_benefits.rs` — config DTOs, invoice DTO, and pure application logic.
- `crates/payroll-api/src/service.rs` — service facade method for applying supplied site benefits.
- `crates/payroll-api/src/lib.rs` — public exports.
- `tests/test_site_benefits.py` — Python characterization for pure supplied-config parity.
- `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`, `tests/test_payroll_api_contract.py` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust site-benefit application stays pure and deterministic: callers supply invoice row, resolved workers-day config, resolved identity-insurance config, source labels, period, and whether identity insurance was already applied; Rust returns the updated invoice plus applied amounts and source labels without reading or writing settings/ledgers.

```rust
let result = apply_site_benefits_to_invoice(invoice, config, "2026-05");
assert_eq!(result.invoice.workers_day_allowance, 10_000);
assert_eq!(result.invoice.identity_guarantee_insurance_deduction, -20_000);
```

## Testing Strategy
- Add Python characterization for supplied-config application parity and non-May/default/already-applied behavior.
- Add Rust unit tests for config normalization, Workers' Day invoice/default behavior, identity-insurance month/already-applied behavior, serialization shape, and service delegation.
- Keep tests outcome-focused on applied amounts, source fields, and serialized compatibility keys.

## Boundaries
- Always: preserve positive amount clamping, May-only fixed Workers' Day default behavior, billing-month-only identity-insurance deduction, already-applied suppression, and compatibility field names.
- Ask first: move site/tenant/global setting lookup, canonical workplace alias lookup, identity-insurance ledger read/write, payroll subtotal/gross recalculation, or workbook I/O into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, or generated local runtime folders.

## Success Criteria
- Rust exposes `WorkersDayConfig`, `IdentityInsuranceConfig`, `SiteBenefitsConfig`, `SiteBenefitsInvoice`, `SiteBenefitsApplication`, and `apply_site_benefits_to_invoice`.
- `PayrollApiService` delegates supplied-config site-benefits application through a framework-neutral method.
- Rust preserves Python-compatible normalization, amount calculation, source labels, updated invoice fields, and serialized DTO field names.
- Contracts/docs identify Rust as owner of supplied-config site-benefits application while Python remains settings/ledger/workbook bridge.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add Python characterization for supplied-config site-benefits application parity.
- [x] Add failing Rust tests for normalization, application, serialization, and service delegation.
- [x] Implement site-benefits DTOs and `apply_site_benefits_to_invoice` without new dependencies.
- [x] Export the site-benefits API and wire service facade.
- [x] Update TypeScript/Python contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [x] Commit, PR, review, merge, and resync.
