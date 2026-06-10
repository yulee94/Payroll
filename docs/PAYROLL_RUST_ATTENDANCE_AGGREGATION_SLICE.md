# Spec: Rust payroll attendance aggregation slice

## Objective
Move the next payroll-domain calculation from legacy compatibility code into Rust: aggregate normalized attendance records into invoice-compatible payroll rows using the same rounding, late/early grace, grouping, and output-field rules currently characterized by `Rust-owned contract`.

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
- `crates/payroll-api/src/attendance.rs` — attendance source DTOs and aggregation rules.
- `crates/payroll-api/src/service.rs` — service facade method for aggregation.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck inputs.
- `Rust parity test` — Rust parity coverage for grouping/grace parity.
- `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`, `Rust parity test` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust aggregation stays pure and deterministic: caller supplies parsed records plus a normalized or raw attendance policy, Rust returns sorted invoice-compatible rows without reading files or writing workbooks.

```rust
let rows = aggregate_attendance_records(records, "Site A", &policy.attendance);
assert_eq!(rows[0].work_days, 8.0);
assert_eq!(rows[0].attendance_days, 2);
```

## Testing Strategy
- Add Rust parity coverage for multi-row grouping and grace behavior before Rust implementation.
- Add Rust unit tests with the same business case plus rounding edge coverage.
- Keep tests outcome-focused on serialized fields and payroll row values, not implementation details.

## Boundaries
- Always: preserve legacy-compatible invoice row field names, safe default zero values, sorted row order, and rounding/grace semantics.
- Ask first: add parsing dependencies, parse XLSX/CSV in Rust, change workbook generation, or remove legacy compatibility paths.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, or generated local runtime folders.

## Success Criteria
- Rust exposes `AttendanceSourceRecord`, `AttendanceInvoiceRow`, and `aggregate_attendance_records`.
- `PayrollApiService` delegates attendance aggregation through a framework-neutral method.
- Rust aggregation groups by supplied or derived name key, applies late/early grace per source record, rounds payroll hours using legacy-compatible half-even rounding, and emits invoice-compatible fields.
- G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add Rust parity coverage for grouped attendance aggregation parity.
- [x] Add failing Rust tests for aggregation DTOs, grace handling, rounding, sorting, and service delegation.
- [x] Implement `attendance.rs` without new dependencies.
- [x] Export the module, wire service facade, and update Buck inputs.
- [x] Update TypeScript/Rust contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
