# Spec: Rust payroll workplace-hours application slice

## Objective
Move the payroll monthly-work-hours calculation for a supplied workplace-hours policy from Python compatibility code into Rust. Rust should preserve the deterministic behavior of `services.workplace_hours.normalize_policy`, `resolve_monthly_work_hours`, and `apply_monthly_hours_to_invoice` after Python has resolved the relevant settings snapshot.

Python may still load tenant/site/global settings, canonical workplace aliases, and UI labels in this slice. Rust must own the pure calculation and invoice metadata application once a caller supplies the invoice row, workplace label, and policy.

## Tech Stack
- Rust crate: `crates/payroll-api` with existing `serde`/`serde_json` only; no new runtime dependencies.
- Compatibility source: `services/workplace_hours.py` (`normalize_policy`, `resolve_monthly_work_hours`, `apply_monthly_hours_to_invoice`).
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`.

## Commands
- Format: `cargo fmt --check`
- Rust tests: `cargo test --workspace`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- Python characterization/contract tests: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workplace_hours tests.test_payroll_api_contract -v`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/payroll-api/src/workplace_hours.rs` — workplace-hours DTOs, policy normalization, resolution, and invoice metadata application.
- `crates/payroll-api/src/service.rs` — service facade methods for resolving/applying supplied workplace-hours policies.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck inputs.
- `tests/test_workplace_hours.py` — Python characterization coverage for supplied-policy parity.
- `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`, `tests/test_payroll_api_contract.py` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust workplace-hours application stays pure and deterministic: callers supply a policy and invoice row; Rust returns the selected hours/source and the invoice row with `_monthly_work_hours` and `_monthly_hours_source` populated.

```rust
let result = apply_monthly_hours_to_invoice(invoice, "청구장", &policy);
assert_eq!(result.hours, 195.0);
assert_eq!(result.invoice.monthly_work_hours, Some(195.0));
```

## Testing Strategy
- Add Python characterization for supplied-policy normalization and source-label behavior before Rust implementation.
- Add Rust unit tests with the same business cases plus invalid-policy fallback, negative invoice-hour clamping, serialization, and service delegation.
- Keep tests outcome-focused on selected hours/source labels and serialized compatibility keys, not implementation details.

## Boundaries
- Always: preserve Python-compatible mode names, default 209-hour fallback, positive invoice-hour selection rules, source-label wording, and `_monthly_*` invoice metadata.
- Ask first: move settings-store persistence, canonical workplace alias repository, payroll calculation/audit flags, or UI settings lists into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, or generated local runtime folders.

## Success Criteria
- Rust exposes `WorkplaceHoursPolicy`, `WorkplaceHoursInvoice`, `WorkplaceMonthlyHoursResolution`, `WorkplaceMonthlyHoursApplication`, `resolve_monthly_work_hours`, and `apply_monthly_hours_to_invoice`.
- `PayrollApiService` delegates workplace-hours resolution/application through framework-neutral methods.
- Rust normalizes supplied workplace-hours policies, applies all five Python-compatible modes, clamps missing/negative invoice hours to fallback behavior, and emits the expected Korean source labels.
- Contracts/docs identify Rust as owner of supplied-policy workplace-hours application while Python remains settings/canonical-workplace resolver.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add Python characterization for supplied-policy workplace-hours parity.
- [x] Add failing Rust tests for policy normalization, mode resolution, invoice metadata application, serialization, and service delegation.
- [x] Implement `workplace_hours.rs` without new dependencies.
- [x] Export the module, wire service facade, and update Buck inputs.
- [x] Update TypeScript/Python contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
