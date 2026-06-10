# Spec: Rust payroll invoice-audit row slice

## Objective
Move the deterministic invoice-audit row calculation from legacy compatibility code into Rust for already-supplied inputs. Rust should preserve `core.payroll.invoice_audit.audit_invoice_row` behavior after a Rust service has resolved the workplace policy, optional ledger record, and optional fixed-hours profile.

G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Tech Stack
- Rust crate: `crates/payroll-api` with existing `serde`/`serde_json` only; no new runtime dependencies.
- Historical source: pre-G028 compatibility source was removed; keep parity evidence in Rust tests, TypeScript contracts, and documented fixtures.
- Existing Rust dependencies inside the crate: `workplace_hours` and `fixed_hours` modules.
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
- `crates/payroll-api/src/invoice_audit.rs` — invoice audit DTOs, break-hour estimation, row audit flags, and fixed-hours composition.
- `crates/payroll-api/src/service.rs` — service facade method for auditing supplied invoice rows.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck inputs.
- Former Python invoice-audit characterization has been decommissioned; parity now lives in `crates/payroll-api/src/invoice_audit.rs` Rust tests.
- `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`, `Rust parity test` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust invoice auditing stays pure and deterministic: callers supply an invoice row, workplace label, normalized policy, optional ledger record, and optional fixed-hours profile; Rust returns the audit row without reading files or stores.

```rust
let row = audit_invoice_row(invoice, "앰코", &policy, Some(&record), None);
assert_eq!(row.status, InvoiceAuditStatus::Warn);
assert!(row.flags.iter().any(|flag| flag.contains("기본급 불일치")));
```

## Testing Strategy
- Rust parity coverage for supplied-policy audit behavior, record monthly-hour mismatch, break-hour estimation, and fixed-hours profile composition has been retired after Rust parity landed.
- Add Rust unit tests with the same business cases plus serialization and service delegation.
- Keep tests outcome-focused on returned audit fields and Korean flags, not implementation details.

## Boundaries
- Always: preserve status/status_label, warning flag order, break-hour estimation, base-salary formula text, `_monthly_*`/fixed-hours composition, and legacy-compatible rounding.
- Ask first: move settings lookup, record matching, batch audit summaries, workbook I/O, or employee fixed-hours resolution into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, or generated local runtime folders.

## Success Criteria
- Rust exposes `InvoiceAuditInvoice`, `InvoiceAuditRecord`, `InvoiceAuditRow`, `InvoiceAuditStatus`, `estimate_break_hours`, and `audit_invoice_row`.
- `PayrollApiService` delegates supplied-input invoice row auditing through a framework-neutral method.
- Rust reproduces supplied-policy workplace-hour auditing, fixed-hours profile audit flag composition, record monthly-hour mismatch checks, base salary mismatch checks, break-hour estimation, and formula text.
- G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Retire Rust parity coverage for supplied-input invoice-audit parity after Rust coverage.
- [x] Add failing Rust tests for audit warnings, break-hour estimation, fixed-hours composition, serialization, and service delegation.
- [x] Implement `invoice_audit.rs` without new dependencies.
- [x] Export the module, wire service facade, and update Buck inputs.
- [x] Update TypeScript/Rust contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
