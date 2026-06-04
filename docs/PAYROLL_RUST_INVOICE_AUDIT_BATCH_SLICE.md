# Spec: Rust payroll invoice-audit batch slice

## Objective
Move deterministic invoice-audit batch summarization from Python compatibility code into Rust for already-supplied row inputs. Rust should preserve the observable `audit_invoice_payroll` result shape once Python has resolved the workplace policy, matched ledger records, and resolved optional fixed-hours profiles for each invoice row.

Python may still load settings, match records by name, resolve fixed-hours profiles, parse workbooks, and render UI text in this slice. Rust must own the pure batch loop that evaluates supplied row inputs, preserves row order, and returns `summary`, `pass_count`, `warn_count`, and audited rows.

## Tech Stack
- Rust crate: `crates/payroll-api` with existing `serde`/`serde_json` only; no new runtime dependencies.
- Compatibility source: `core/payroll/invoice_audit.py` (`audit_invoice_payroll`, summary shape).
- Existing Rust dependency inside the crate: `invoice_audit::audit_invoice_row`.
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
- `crates/payroll-api/src/invoice_audit.rs` — batch DTOs and `audit_invoice_batch` built on the Rust row auditor.
- `crates/payroll-api/src/service.rs` — service facade method for auditing supplied invoice batches.
- `crates/payroll-api/src/lib.rs` — public exports.
- `tests/test_invoice_audit.py` — Python characterization coverage for batch summary parity.
- `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`, `tests/test_payroll_api_contract.py` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust batch auditing stays pure and deterministic: callers supply per-row `InvoiceAuditBatchItem`s with invoice, workplace, policy, optional record, and optional fixed-hours profile; Rust returns the rows and counts without reading settings, rosters, or files.

```rust
let result = audit_invoice_batch(items, "앰코");
assert_eq!(result.summary.warn, 1);
assert_eq!(result.rows[0].name, "A");
```

## Testing Strategy
- Add Python characterization for batch result shape, row order, pass/warn counts, workplace label, and summary text before Rust implementation.
- Add Rust unit tests for batch pass/warn counting, default workplace fallback, row order, serialization, and service delegation.
- Keep tests outcome-focused on summary shape and row outputs, not implementation details.

## Boundaries
- Always: preserve row order, `summary.total/pass/warn`, top-level `pass_count`/`warn_count`, and workplace label semantics.
- Ask first: move settings lookup, ledger record matching, fixed-hours profile resolution, workbook I/O, or UI text rendering into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, or generated local runtime folders.

## Success Criteria
- Rust exposes `InvoiceAuditBatchItem`, `InvoiceAuditSummary`, `InvoiceAuditBatchResult`, and `audit_invoice_batch`.
- `PayrollApiService` delegates supplied-input invoice batch auditing through a framework-neutral method.
- Rust preserves Python-compatible batch summary shape, counts, row order, default workplace fallback, and serialized fields.
- Contracts/docs identify Rust as owner of supplied-input invoice-audit batch summarization while Python remains resolver/workbook/UI bridge.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add Python characterization for supplied-input invoice-audit batch parity.
- [x] Add failing Rust tests for batch counts, row order, serialization, and service delegation.
- [x] Implement batch DTOs and `audit_invoice_batch` without new dependencies.
- [x] Export the batch API and wire service facade.
- [x] Update TypeScript/Python contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [x] Commit, PR, review, merge, and resync.
