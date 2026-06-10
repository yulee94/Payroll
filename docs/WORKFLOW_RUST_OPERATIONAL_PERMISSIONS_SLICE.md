# Workflow Rust operational permissions slice

## Objective

Move pure workflow operational permission decisions into
`crates/workflow-core::business_trip_permissions` while keeping the repository
pinned to Rust 2024 / Rust 1.96.

This slice covers supplied-profile predicates for site report visibility,
month-close authority, and execution-task management. Rust owns only
deterministic decisions once callers provide the principal, profile, site/task
identifiers, and tenant context. The remaining Rust service backlog owns
`UserSession` conversion, `get_user_profile`, workflow JSON persistence,
site/task storage lookups, close-month side effects, execution task mutation,
notifications, calendar/To-Do links, and UI bridge behavior.

## Compatibility invariants

- Admin, executive, and finance roles can view any site report.
- If no admin/executive/finance role is present, site-report visibility requires
  a supplied profile with matching `site_ids`.
- Month close is allowed for admin or finance only when the user can view the
  site report.
- Site managers can close month only for sites they can view.
- HR and viewer site visibility does not imply month-close authority.
- Execution-task management is allowed for admin or for the direct assigned
  executor.
- Executor role without direct assignment does not grant task management.

## Rust API shape

- Crate: `bitween-workflow-core`
- Module: `business_trip_permissions`
- New entrypoints:
  - `can_view_site_report`
  - `can_close_month`
  - `can_manage_execution_task`

## Validation plan

Start RED, then implement only enough to go GREEN, then run the local gate set.

```sh
buck2 test //crates/workflow-core:workflow_core_test
# G028 retired the former compatibility gate; use Buck2 Rust tests plus TypeScript gates from AGENTS.md.
buck2 build '<target>[clippy.txt]'
buck2 test //...
buck2 test //crates/workflow-core:workflow_core_test
# G028 retired the former compatibility gate; use Buck2 Rust tests plus TypeScript gates from AGENTS.md.
git diff --check
buck2 build '<target>[clippy.txt]'
```

Hosted GitHub Actions remain best-effort because the current account
billing/spending-limit blocker prevents hosted runners from starting before job
steps execute.

## Review record

2026-06-04 local five-axis review: no blockers. Correctness is covered by
RED/GREEN Rust operational permission tests and Rust/TypeScript contract tests;
readability keeps predicates flat and reuses existing role/profile helpers;
architecture keeps the Rust backlog as profile/task/site resolver and side-effect bridge;
security preserves admin/site/assignment boundaries and avoids broadening HR,
viewer, or unassigned executor authority; performance remains bounded to small
role and site membership checks.

## Checklist

- [x] RED Rust unit tests describe site report, month close, and execution-task parity.
- [x] RED Rust/TypeScript contract test names the Rust operational permission boundary.
- [x] Rust 2024 / Rust 1.96 functions implement pure operational predicates.
- [x] Contract metadata and migration docs describe the new boundary.
- [x] Buck2, diff, and product gates pass.
- [x] Code review is recorded before merge.
