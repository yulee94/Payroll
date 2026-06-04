# Spec: Rust business-trip lifecycle slice

## Objective
Move the deterministic business-trip lifecycle taxonomy, normalization, source/dedupe normalization, view-model key order, and status-transition rules from Python compatibility code into Rust. Rust should own the pure lifecycle domain contract once callers supply the current timestamp and fallback IDs; Python may still own JSON file persistence, document/work-task/report/KPI side effects, authorization lookup, notifications, and UI bridge behavior in this slice.

## Tech Stack
- Rust crate: `crates/workflow-core` on Rust 2024 / Rust 1.96.
- Existing dependencies only: `serde` and `serde_json` already used in the workspace.
- Python characterization source: `core.workflow.business_trip` and `core.workflow.constants`.
- Contract/doc surfaces: `docs/WORKFLOW_ERP.md`, `docs/RUST_BACKEND_MIGRATION.md`, `docs/BUILD_AND_RUNTIME_TRANSITION.md`, and a Python contract metadata module for tests.

## Commands
- Format: `cargo fmt --check`
- Rust tests: `cargo test -p bitween-workflow-core business_trip --lib`
- Workspace tests: `cargo test --workspace`
- Buck target: `buck2 test //crates/workflow-core:workflow_core_test`
- Python contract tests: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_business_trip_contracts -v`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/workflow-core/src/business_trip.rs` — lifecycle constants, normalization helpers, migration/view-model helpers, and status transition logic.
- `crates/workflow-core/src/lib.rs`, `crates/workflow-core/Cargo.toml`, `crates/workflow-core/BUCK` — Rust crate and Buck target.
- Root `Cargo.toml` and `BUCK` — workspace and target aliases.
- `services/workflow_api_contract.py` and `tests/test_workflow_business_trip_contracts.py` — contract metadata and Python-side assertions.
- `docs/` — migration and workflow checkpoint docs.

## Code Style
Rust lifecycle code stays pure and deterministic: callers provide already-loaded record JSON plus `now_iso` / `fallback_trip_id`, and Rust returns stable JSON-compatible records without reading stores, documents, tasks, KPI state, users, calendars, or notifications.

```rust
let transitioned = transition_trip_status(&trip, "diary_due", "2026-06-04T09:00:00Z")?;
assert_eq!(transitioned["status"], "diary_due");
```

## Testing Strategy
- Add Rust unit tests for status taxonomy, source normalization, legacy migration shape, invalid transition rejection, timestamp field effects, cancellation KPI behavior, and view-model key order.
- Add Python contract metadata assertions so compatibility tests expose the Rust lifecycle entrypoints and remaining Python boundaries.
- Keep existing Python integration tests green; this slice does not replace store, service, permission, document artifact, KPI reflection, escalation, or UI behavior.

## Boundaries
- Always: preserve status strings/order, KPI reflection strings/order, source kind strings/order, transition adjacency, default invalid-status fallback to `draft`, invalid KPI fallback to `blocked`, source normalization, dedupe fallback, timestamp field side effects, cancellation `not_applicable`, completed `ready`, unknown-field preservation during migration, and view-model key order.
- Ask first: move persistence, authorization/profile lookup, document approval sync, execution task checks, overdue escalation, KPI reflection, calendar/To-Do side effects, notifications, or frontend workflow UI behavior into Rust.
- Never: add runtime dependencies, commit tenant workflow DB data, credentials, local runtime stores, or generated build artifacts.

## Success Criteria
- Rust exposes business-trip lifecycle constants and pure functions for normalization, migration/view-model shaping, source matching, transition validation, and status transition.
- Rust tests prove parity with the Python business-trip lifecycle contract for the selected pure rules.
- Python contract metadata and docs identify Rust as owner of the pure business-trip lifecycle domain while Python remains the persistence/service/side-effect bridge.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add failing Rust tests and Python contract assertions.
- [x] Implement Rust workflow-core crate and lifecycle functions without new dependencies.
- [x] Wire Cargo workspace and Buck target aliases.
- [x] Update Python contract metadata and migration/workflow docs.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
