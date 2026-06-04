# Spec: Rust payroll attendance aggregation slice

## Objective
Move the next payroll-domain calculation from Python compatibility code into Rust: aggregate normalized attendance records into invoice-compatible payroll rows using the same rounding, late/early grace, grouping, and output-field rules currently characterized by `services.attendance_import`.

Python may still parse CSV/XLSX files and build workbook artifacts in this slice. Rust must own the pure backend aggregation rule once rows have been normalized.

## Tech Stack
- Rust crate: `crates/payroll-api` with existing `serde`/`serde_json` only; no new runtime dependencies.
- Compatibility source: `services/attendance_import.py` (`_aggregate_records`, `_round_hours`, grace handling, output row shape).
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`.

## Commands
- Format: `cargo fmt --check`
- Rust tests: `cargo test --workspace`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- Python characterization/contract tests: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_attendance_import tests.test_payroll_api_contract -v`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/payroll-api/src/attendance.rs` — attendance source DTOs and aggregation rules.
- `crates/payroll-api/src/service.rs` — service facade method for aggregation.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck inputs.
- `tests/test_attendance_import.py` — Python characterization coverage for grouping/grace parity.
- `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`, `tests/test_payroll_api_contract.py` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust aggregation stays pure and deterministic: caller supplies parsed records plus a normalized or raw attendance policy, Rust returns sorted invoice-compatible rows without reading files or writing workbooks.

```rust
let rows = aggregate_attendance_records(records, "Site A", &policy.attendance);
assert_eq!(rows[0].work_days, 8.0);
assert_eq!(rows[0].attendance_days, 2);
```

## Testing Strategy
- Add Python characterization for multi-row grouping and grace behavior before Rust implementation.
- Add Rust unit tests with the same business case plus rounding edge coverage.
- Keep tests outcome-focused on serialized fields and payroll row values, not implementation details.

## Boundaries
- Always: preserve Python-compatible invoice row field names, safe default zero values, sorted row order, and rounding/grace semantics.
- Ask first: add parsing dependencies, parse XLSX/CSV in Rust, change workbook generation, or remove Python compatibility paths.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, or generated local runtime folders.

## Success Criteria
- Rust exposes `AttendanceSourceRecord`, `AttendanceInvoiceRow`, and `aggregate_attendance_records`.
- `PayrollApiService` delegates attendance aggregation through a framework-neutral method.
- Rust aggregation groups by supplied or derived name key, applies late/early grace per source record, rounds payroll hours using Python-compatible half-even rounding, and emits invoice-compatible fields.
- Contracts/docs identify Rust as owner of attendance aggregation while Python remains file parser/workbook bridge.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add Python characterization for grouped attendance aggregation parity.
- [x] Add failing Rust tests for aggregation DTOs, grace handling, rounding, sorting, and service delegation.
- [x] Implement `attendance.rs` without new dependencies.
- [x] Export the module, wire service facade, and update Buck inputs.
- [x] Update TypeScript/Python contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
