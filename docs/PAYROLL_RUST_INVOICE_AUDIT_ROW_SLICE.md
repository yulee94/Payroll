# Spec: Rust payroll invoice-audit row slice

## Objective
Move the deterministic invoice-audit row calculation from Python compatibility code into Rust for already-supplied inputs. Rust should preserve `core.payroll.invoice_audit.audit_invoice_row` behavior after Python has resolved the workplace policy, optional ledger record, and optional fixed-hours profile.

Python may still load settings, match payroll ledger records, resolve employee fixed-hours profiles, and aggregate whole-invoice summaries in this slice. Rust must own the pure single-row audit calculation and flags once those inputs are supplied.

## Tech Stack
- Rust crate: `crates/payroll-api` with existing `serde`/`serde_json` only; no new runtime dependencies.
- Compatibility source: `core/payroll/invoice_audit.py` (`_estimate_break_hours`, `audit_invoice_row`).
- Existing Rust dependencies inside the crate: `workplace_hours` and `fixed_hours` modules.
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`.

## Commands
- Format: `cargo fmt --check`
- Rust tests: `cargo test --workspace`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- Python characterization/contract tests: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_invoice_audit tests.test_payroll_api_contract -v`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/payroll-api/src/invoice_audit.rs` — invoice audit DTOs, break-hour estimation, row audit flags, and fixed-hours composition.
- `crates/payroll-api/src/service.rs` — service facade method for auditing supplied invoice rows.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck inputs.
- `tests/test_invoice_audit.py` — Python characterization coverage for supplied-policy/record/profile parity.
- `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`, `tests/test_payroll_api_contract.py` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust invoice auditing stays pure and deterministic: callers supply an invoice row, workplace label, normalized policy, optional ledger record, and optional fixed-hours profile; Rust returns the audit row without reading files or stores.

```rust
let row = audit_invoice_row(invoice, "앰코", &policy, Some(&record), None);
assert_eq!(row.status, InvoiceAuditStatus::Warn);
assert!(row.flags.iter().any(|flag| flag.contains("기본급 불일치")));
```

## Testing Strategy
- Add Python characterization for supplied-policy audit behavior, record monthly-hour mismatch, break-hour estimation, and fixed-hours profile composition before Rust implementation.
- Add Rust unit tests with the same business cases plus serialization and service delegation.
- Keep tests outcome-focused on returned audit fields and Korean flags, not implementation details.

## Boundaries
- Always: preserve status/status_label, warning flag order, break-hour estimation, base-salary formula text, `_monthly_*`/fixed-hours composition, and Python-compatible rounding.
- Ask first: move settings lookup, record matching, batch audit summaries, workbook I/O, or employee fixed-hours resolution into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, or generated local runtime folders.

## Success Criteria
- Rust exposes `InvoiceAuditInvoice`, `InvoiceAuditRecord`, `InvoiceAuditRow`, `InvoiceAuditStatus`, `estimate_break_hours`, and `audit_invoice_row`.
- `PayrollApiService` delegates supplied-input invoice row auditing through a framework-neutral method.
- Rust reproduces supplied-policy workplace-hour auditing, fixed-hours profile audit flag composition, record monthly-hour mismatch checks, base salary mismatch checks, break-hour estimation, and formula text.
- Contracts/docs identify Rust as owner of single-row supplied-input invoice auditing while Python remains resolver/batch/workbook bridge.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add Python characterization for supplied-input invoice-audit parity.
- [x] Add failing Rust tests for audit warnings, break-hour estimation, fixed-hours composition, serialization, and service delegation.
- [x] Implement `invoice_audit.rs` without new dependencies.
- [x] Export the module, wire service facade, and update Buck inputs.
- [x] Update TypeScript/Python contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
