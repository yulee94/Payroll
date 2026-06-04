# Workflow Rust business-trip overdue permissions slice

## Objective

Move the remaining pure business-trip lifecycle administration and overdue
permission decisions into `crates/workflow-core::business_trip_permissions` while
keeping the repository pinned to Rust 2024 / Rust 1.96.

This slice follows the supplied-profile boundary established by
`docs/WORKFLOW_RUST_BUSINESS_TRIP_PERMISSIONS_SLICE.md`: Rust owns pure decisions
once callers provide the principal, current user profile, trip row, and requested
workflow storage tenant. Python remains responsible for `UserSession` conversion,
`get_user_profile` lookup, workflow JSON persistence, overdue side effects,
notifications/escalations, document/task/report/KPI writes, calendar/To-Do
links, and UI bridge behavior.

## Compatibility invariants

- `can_administer_business_trip_lifecycle` allows only workflow
  admin/executive/finance after base-role expansion.
- `can_run_business_trip_overdue_evaluator` allows admin/executive/finance plus
  site manager, department manager, and HR roles; requester, executor, approver,
  and viewer alone cannot invoke evaluator side effects.
- `can_evaluate_business_trip_overdue` first applies the same business-trip
  legal-scope gate as visibility/manage predicates.
- Overdue evaluation is allowed for admin/executive/finance inside legal scope.
- Site manager and HR can evaluate trips only for scoped `site_id` values.
- Department manager, site manager, and HR can evaluate trips only for scoped
  `department_id` or `org_unit_id` values.
- Direct travelers/executors may view/manage their own rows where allowed by the
  lifecycle predicate, but that does not grant overdue-evaluation side-effect
  authority.
- Viewer and explicit approver grants do not imply overdue evaluator authority.

## Rust API shape

- Crate: `bitween-workflow-core`
- Module: `business_trip_permissions`
- New entrypoints:
  - `can_administer_business_trip_lifecycle`
  - `can_run_business_trip_overdue_evaluator`
  - `can_evaluate_business_trip_overdue`

## Validation plan

Start RED, then implement only enough to go GREEN, then run the local gate set.

```sh
cargo test -p bitween-workflow-core business_trip_permissions --lib
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_business_trip_contracts.BusinessTripLifecycleContractTests.test_contract_declares_rust_business_trip_overdue_permissions -v
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
RED/GREEN Rust permission tests and Python contract tests; readability preserves
the existing flat supplied-profile predicate style; architecture keeps Python as
profile resolver and overdue side-effect bridge; security keeps legal-scope
isolation and denies requester/executor/viewer/approver escalation into overdue
side-effect authority; performance remains bounded to small in-memory role and
scope membership checks.

## Checklist

- [x] RED Rust unit tests describe overdue/admin permission parity.
- [x] RED Python contract test names the Rust overdue permission boundary.
- [x] Rust 2024 / Rust 1.96 functions implement pure overdue/admin predicates.
- [x] Contract metadata and migration docs describe the new boundary.
- [x] Local cargo, Buck, Python, diff, and clippy gates pass.
- [x] Code review is recorded before merge.
