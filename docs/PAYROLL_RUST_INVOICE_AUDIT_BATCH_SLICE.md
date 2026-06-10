# Spec: Rust payroll invoice-audit batch slice

## Objective
Move deterministic invoice-audit batch summarization from legacy compatibility code into Rust for already-supplied row inputs. Rust should preserve the observable `audit_invoice_payroll` result shape once a Rust service has resolved the workplace policy, matched ledger records, and resolved optional fixed-hours profiles for each invoice row.

G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Tech Stack
- Rust crate: `crates/payroll-api` with existing `serde`/`serde_json` only; no new runtime dependencies.
- Historical source: pre-G028 compatibility source was removed; keep parity evidence in Rust tests, TypeScript contracts, and documented fixtures.
- Existing Rust dependency inside the crate: `invoice_audit::audit_invoice_row`.
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
- `crates/payroll-api/src/invoice_audit.rs` — batch DTOs and `audit_invoice_batch` built on the Rust row auditor.
- `crates/payroll-api/src/service.rs` — service facade method for auditing supplied invoice batches.
- `crates/payroll-api/src/lib.rs` — public exports.
- Former Python invoice-audit batch characterization has been decommissioned; parity now lives in `crates/payroll-api/src/invoice_audit.rs` Rust tests.
- `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`, `Rust parity test` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust batch auditing stays pure and deterministic: callers supply per-row `InvoiceAuditBatchItem`s with invoice, workplace, policy, optional record, and optional fixed-hours profile; Rust returns the rows and counts without reading settings, rosters, or files.

```rust
let result = audit_invoice_batch(items, "앰코");
assert_eq!(result.summary.warn, 1);
assert_eq!(result.rows[0].name, "A");
```

## Testing Strategy
- Rust parity coverage for batch result shape, row order, pass/warn counts, workplace label, and summary text has been retired after Rust parity landed.
- Add Rust unit tests for batch pass/warn counting, default workplace fallback, row order, serialization, and service delegation.
- Keep tests outcome-focused on summary shape and row outputs, not implementation details.

## Boundaries
- Always: preserve row order, `summary.total/pass/warn`, top-level `pass_count`/`warn_count`, and workplace label semantics.
- Ask first: move settings lookup, ledger record matching, fixed-hours profile resolution, workbook I/O, or UI text rendering into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, or generated local runtime folders.

## Success Criteria
- Rust exposes `InvoiceAuditBatchItem`, `InvoiceAuditSummary`, `InvoiceAuditBatchResult`, and `audit_invoice_batch`.
- `PayrollApiService` delegates supplied-input invoice batch auditing through a framework-neutral method.
- Rust preserves legacy-compatible batch summary shape, counts, row order, default workplace fallback, and serialized fields.
- G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Retire Rust parity coverage for supplied-input invoice-audit batch parity after Rust coverage.
- [x] Add failing Rust tests for batch counts, row order, serialization, and service delegation.
- [x] Implement batch DTOs and `audit_invoice_batch` without new dependencies.
- [x] Export the batch API and wire service facade.
- [x] Update TypeScript/Rust contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [x] Commit, PR, review, merge, and resync.
