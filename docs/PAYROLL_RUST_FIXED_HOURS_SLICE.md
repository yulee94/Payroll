# Spec: Rust payroll fixed-hours application slice

## Objective
Move the next payroll record-generation rule from Python compatibility code into Rust: applying a resolved fixed-hours profile to an invoice-compatible payroll row. Rust should preserve the Python behavior from `core.payroll.fixed_hours.apply_fixed_hours_to_invoice` and `fixed_hours_audit_flags` once the caller supplies the profile.

Python may still load HR contracts, site templates, payroll settings, and employee rosters in this slice. Rust must own the pure deterministic transformation and audit flag semantics after profile resolution.

## Tech Stack
- Rust crate: `crates/payroll-api` with existing `serde`/`serde_json` only; no new runtime dependencies.
- Compatibility source: `core/payroll/fixed_hours.py` (`normalize_fixed_hours_profile`, `apply_fixed_hours_to_invoice`, `fixed_hours_audit_flags`).
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`.

## Commands
- Format: `cargo fmt --check`
- Rust tests: `cargo test --workspace`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- Python characterization/contract tests: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_fixed_hours tests.test_payroll_api_contract -v`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/payroll-api/src/fixed_hours.rs` — fixed-hours DTOs, profile normalization, invoice application, and audit flags.
- `crates/payroll-api/src/service.rs` — service facade method for applying resolved fixed-hours profiles.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck inputs.
- `tests/test_fixed_hours.py` — Python characterization coverage for resolved-profile application parity.
- `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`, `tests/test_payroll_api_contract.py` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust fixed-hours application stays pure and deterministic: caller supplies an invoice row, a resolved profile, and an optional workplace override; Rust returns the transformed row plus audit flags without reading local settings or HR contract stores.

```rust
let result = apply_fixed_hours_to_invoice(invoice, &profile, "강남경비");
assert!(result.applied);
assert_eq!(result.invoice.monthly_work_hours, 209.0);
assert_eq!(result.invoice.ot_hours, 20.0);
```

## Testing Strategy
- Add/keep Python characterization for resolved-profile fixed-hours application before Rust implementation.
- Add Rust unit tests with the same business cases plus normalization, preserve-reference-hours, and audit-flag coverage.
- Keep tests outcome-focused on transformed payroll fields and serialized compatibility keys, not implementation details.

## Boundaries
- Always: preserve invoice original values under `_invoice_*`, monthly-hour source metadata, fixed-hours mode/source/pay-type/job-group metadata, and audit warning semantics.
- Ask first: move HR contract loading, site template resolution, payroll settings persistence, or roster matching into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, or generated local runtime folders.

## Success Criteria
- Rust exposes `FixedHoursProfile`, `FixedHoursInvoice`, `FixedHoursApplication`, and `apply_fixed_hours_to_invoice`.
- `PayrollApiService` delegates fixed-hours application through a framework-neutral method.
- Rust normalizes fixed-hours profiles, applies monthly hours and fixed overtime/special hours, preserves original invoice values, respects `_preserve_reference_hours`, and emits Python-compatible audit flags.
- Contracts/docs identify Rust as owner of fixed-hours application while Python remains profile resolver/settings bridge.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add Python characterization for resolved-profile fixed-hours application parity.
- [x] Add failing Rust tests for profile normalization, invoice application, preservation, audit flags, and service delegation.
- [x] Implement `fixed_hours.rs` without new dependencies.
- [x] Export the module, wire service facade, and update Buck inputs.
- [x] Update TypeScript/Python contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
