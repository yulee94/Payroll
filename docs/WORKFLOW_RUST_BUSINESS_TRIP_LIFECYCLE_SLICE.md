# Spec: Rust business-trip lifecycle slice

## Objective
G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Tech Stack
- Rust crate: `crates/workflow-core` on Rust 2024 / Rust 1.96.
- Existing dependencies only: `serde` and `serde_json` already used in the workspace.
- Rust parity source: `core.workflow.business_trip` and `core.workflow.constants`.
- Contract/doc surfaces: `docs/WORKFLOW_ERP.md`, `docs/RUST_BACKEND_MIGRATION.md`, `docs/BUILD_AND_RUNTIME_TRANSITION.md`, and a Rust contract metadata module for tests.

## Commands
- Format: `buck2 build '<target>[clippy.txt]'`
- Rust tests: `buck2 test //crates/workflow-core:workflow_core_test`
- Workspace tests: `buck2 test //...`
- Buck target: `buck2 test //crates/workflow-core:workflow_core_test`
- G028 retired the former compatibility gate; use Buck2 Rust tests plus TypeScript gates from AGENTS.md.
- Diff hygiene: `git diff --check`
- Bounded lint gate: `buck2 build '<target>[clippy.txt]'`

## Project Structure
- `crates/workflow-core/src/business_trip.rs` — lifecycle constants, normalization helpers, migration/view-model helpers, and status transition logic.
- `crates/workflow-core/src/lib.rs`, `crates/workflow-core/Cargo.toml`, `crates/workflow-core/BUCK` — Rust crate and Buck target.
- Root `Cargo.toml` and `BUCK` — workspace and target aliases.
- `Rust-owned contract` and `Rust parity test` — contract metadata and Rust-side assertions.
- `docs/` — migration and workflow checkpoint docs.

## Code Style
Rust lifecycle code stays pure and deterministic: callers provide already-loaded record JSON plus `now_iso` / `fallback_trip_id`, and Rust returns stable JSON-compatible records without reading stores, documents, tasks, KPI state, users, calendars, or notifications.

```rust
let transitioned = transition_trip_status(&trip, "diary_due", "2026-06-04T09:00:00Z")?;
assert_eq!(transitioned["status"], "diary_due");
```

## Testing Strategy
- Add Rust unit tests for status taxonomy, source normalization, legacy migration shape, invalid transition rejection, timestamp field effects, cancellation KPI behavior, and view-model key order.
- Add Rust contract metadata assertions so compatibility tests expose the Rust lifecycle entrypoints and remaining Rust backlog boundaries.
- Keep Rust workflow integration tests green; this slice does not replace store, service, permission, document artifact, KPI reflection, escalation, or UI behavior.

## Boundaries
- Always: preserve status strings/order, KPI reflection strings/order, source kind strings/order, transition adjacency, default invalid-status fallback to `draft`, invalid KPI fallback to `blocked`, source normalization, dedupe fallback, timestamp field side effects, cancellation `not_applicable`, completed `ready`, unknown-field preservation during migration, and view-model key order.
- Ask first: move persistence, authorization/profile lookup, document approval sync, execution task checks, overdue escalation, KPI reflection, calendar/To-Do side effects, notifications, or frontend workflow UI behavior into Rust.
- Never: add runtime dependencies, commit tenant workflow DB data, credentials, local runtime stores, or generated build artifacts.

## Success Criteria
- Rust exposes business-trip lifecycle constants and pure functions for normalization, migration/view-model shaping, source matching, transition validation, and status transition.
- Rust tests prove parity with the documented business-trip lifecycle contract for the selected pure rules.
- G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add failing Rust tests and Rust/TypeScript contract assertions.
- [x] Implement Rust workflow-core crate and lifecycle functions without new dependencies.
- [x] Wire Cargo workspace and Buck target aliases.
- [x] Update Rust contract metadata and migration/workflow docs.
- [x] Run local verification and self-review.
- [ ] Commit, PR, review, merge, and resync.
