# Workflow Rust business-trip permissions slice

## Objective

Move the pure, supplied-profile business-trip lifecycle permission decisions into
`crates/workflow-core` while keeping the repository pinned to Rust 2024 / Rust
1.96.

This slice is intentionally narrow: Rust owns deterministic tenant/legal scope,
visibility, and manage predicates once callers provide the principal, trip row,
current user workflow profile, and optional requester/traveler profile. Python
compatibility code remains responsible for `UserSession` conversion,
`get_user_profile` lookup, workflow JSON storage, document/task/report/KPI side
effects, overdue evaluation, notifications, calendar/To-Do links, and UI bridge
behavior.

## Compatibility invariants

- `tenant_id` on the row must match the requested workflow storage tenant when
  present.
- A user with no tenant remains compatible with legacy session behavior and can
  pass the legal-scope gate.
- A user in the origin/legal tenant can access the trip through the normal role
  and ownership matrix.
- A user in the workflow storage tenant can access a different origin tenant only
  when the storage tenant is explicitly different from the origin tenant.
- Sibling legal-tenant admins do not gain access through shared workflow-root
  storage.
- Base `admin` expands to workflow admin, executive, approver, finance, and HR.
- Base `finance` expands to workflow finance, approver, and executive.
- Empty workflow-role sets fall back to requester.
- Visibility includes admin/executive/finance, direct requester (or
  traveler_user_id when requester_id is absent), executor, explicit approver,
  supplied requester manager, site manager/HR site
  scope, department manager/site manager/HR department scope, and viewer scoped
  site/department grants.
- Viewer is not global access.
- Manage authority is narrower than visibility: admin/executive/finance or
  direct requester (or traveler_user_id when requester_id is absent)/executor
  only.

## Rust API shape

- Crate: `bitween-workflow-core`
- Module: `business_trip_permissions`
- Entrypoints:
  - `workflow_roles`
  - `is_business_trip_legal_scope_allowed`
  - `can_view_business_trip_lifecycle`
  - `can_manage_business_trip_lifecycle`
- DTOs:
  - `BusinessTripPrincipal`
  - `BusinessTripProfile`
  - `BusinessTripPermissionTrip`
  - `BusinessTripPermissionInput`

## Validation plan

Start RED, then implement only enough to go GREEN, then run the local gate set.

```sh
cargo test -p bitween-workflow-core business_trip_permissions --lib
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_business_trip_contracts.BusinessTripLifecycleContractTests.test_contract_declares_rust_business_trip_permissions -v
cargo fmt --check
cargo test --workspace
buck2 test //crates/workflow-core:workflow_core_test
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_business_trip_contracts -v
git diff --check
cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant
```

Hosted GitHub Actions remain best-effort because the current account
billing/spending-limit blocker prevents hosted runners from starting before job
steps execute.

## Review record

2026-06-04 local five-axis review: no blockers. Correctness is covered by
RED/GREEN Rust permission tests and Python contract tests; readability keeps the
module flat and DTO-driven; architecture preserves Python as resolver and
side-effect bridge; security keeps sibling legal-tenant admins out of shared
workflow-root data and keeps viewer scoped-only; performance is bounded to
small in-memory role/id set checks.

## Checklist

- [x] RED Rust unit tests describe permission parity.
- [x] RED Python contract test names the Rust permission boundary.
- [x] Rust 2024 / Rust 1.96 module implements pure permission predicates.
- [x] BUCK and public crate exports include the new module.
- [x] Contract metadata and migration docs describe the new boundary.
- [x] Local cargo, Buck, Python, diff, and clippy gates pass.
- [x] Code review is recorded before merge.
