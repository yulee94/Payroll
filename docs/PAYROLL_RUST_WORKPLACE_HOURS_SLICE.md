# Spec: Rust payroll workplace-hours application slice

## Objective
Move the payroll monthly-work-hours calculation for a supplied workplace-hours policy from legacy compatibility code into Rust. Rust should preserve the deterministic behavior of `Rust-owned contract`, `resolve_monthly_work_hours`, and `apply_monthly_hours_to_invoice` after a Rust service has resolved the relevant settings snapshot.

G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Tech Stack
- Rust crate: `crates/payroll-api` with existing `serde`/`serde_json` only; no new runtime dependencies.
- Historical source: pre-G028 compatibility source was removed; keep parity evidence in Rust tests, TypeScript contracts, and documented fixtures.
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`.

## Commands
- Format: `buck2 build '<target>[clippy.txt]'`
- Rust tests: `buck2 test //...`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- Rust parity tests after Rust parity decommission: `buck2 test //crates/payroll-api:payroll_api_test`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `buck2 build '<target>[clippy.txt]'`

## Project Structure
- `crates/payroll-api/src/workplace_hours.rs` — workplace-hours DTOs, policy normalization, resolution, and invoice metadata application.
- `crates/payroll-api/src/service.rs` — service facade methods for resolving/applying supplied workplace-hours policies.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck inputs.
- Former Python workplace-hours characterization has been decommissioned; parity now lives in `crates/payroll-api/src/workplace_hours.rs` Rust tests.
- `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`, `Rust parity test` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust workplace-hours application stays pure and deterministic: callers supply a policy and invoice row; Rust returns the selected hours/source and the invoice row with `_monthly_work_hours` and `_monthly_hours_source` populated.

```rust
let result = apply_monthly_hours_to_invoice(invoice, "청구장", &policy);
assert_eq!(result.hours, 195.0);
assert_eq!(result.invoice.monthly_work_hours, Some(195.0));
```

## Testing Strategy
- Rust parity coverage for supplied-policy normalization and source-label behavior has been retired after Rust parity landed.
- Add Rust unit tests with the same business cases plus invalid-policy fallback, negative invoice-hour clamping, serialization, and service delegation.
- Keep tests outcome-focused on selected hours/source labels and serialized compatibility keys, not implementation details.

## Boundaries
- Always: preserve legacy-compatible mode names, default 209-hour fallback, positive invoice-hour selection rules, source-label wording, and `_monthly_*` invoice metadata.
- Ask first: move settings-store persistence, canonical workplace alias repository, payroll calculation/audit flags, or UI settings lists into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, or generated local runtime folders.

## Success Criteria
- Rust exposes `WorkplaceHoursPolicy`, `WorkplaceHoursInvoice`, `WorkplaceMonthlyHoursResolution`, `WorkplaceMonthlyHoursApplication`, `resolve_monthly_work_hours`, and `apply_monthly_hours_to_invoice`.
- `PayrollApiService` delegates workplace-hours resolution/application through framework-neutral methods.
- Rust normalizes supplied workplace-hours policies, applies all five legacy-compatible modes, clamps missing/negative invoice hours to fallback behavior, and emits the expected Korean source labels.
- G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Retire Rust parity coverage for supplied-policy workplace-hours parity after Rust coverage.
- [x] Add failing Rust tests for policy normalization, mode resolution, invoice metadata application, serialization, and service delegation.
- [x] Implement `workplace_hours.rs` without new dependencies.
- [x] Export the module, wire service facade, and update Buck inputs.
- [x] Update TypeScript/Rust contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
