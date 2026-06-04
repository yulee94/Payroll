# Workflow Rust business-trip document legal-scope slice

## Objective

Move the pure business-trip document relatedness and legal-scope decisions into
`crates/workflow-core::business_trip_permissions` while keeping the repository
pinned to Rust 2024 / Rust 1.96.

This slice extends the supplied-profile permission boundary: Rust owns whether a
workflow document is business-trip related and whether its legal tenant is inside
the caller's allowed business-trip scope once callers supply a principal,
document DTO, and requested workflow storage tenant. Python remains responsible
for `UserSession` conversion, JSON document storage, content extraction from
`content_json`, profile lookup, approval workflow mutation, task/report/KPI side
effects, notifications, calendar/To-Do links, and UI bridge behavior.

## Compatibility invariants

- A workflow document is business-trip related when `document_type` is
  `BUSINESS_TRIP_REQUEST` or when extracted content contains a non-empty
  `trip_id`.
- Non-business-trip documents pass the business-trip legal-scope gate unchanged.
- Related documents derive origin/legal tenant from document `origin_tenant_id`,
  extracted content `origin_tenant_id`, extracted content `legal_tenant_id`, or
  the requested workflow storage tenant, in that order.
- Related documents use the requested workflow storage tenant as the row storage
  tenant, matching the Python compatibility shim.
- Missing principal tenant remains legacy-compatible and passes the legal-scope
  gate.
- Origin/legal tenant principals pass; explicit workflow-root principals pass
  when storage tenant differs from origin; sibling legal-tenant principals fail.

## Rust API shape

- Crate: `bitween-workflow-core`
- Module: `business_trip_permissions`
- New DTO:
  - `BusinessTripPermissionDocument`
- New entrypoints:
  - `is_business_trip_related_document`
  - `is_business_trip_document_legal_scope_allowed`

## Validation plan

Start RED, then implement only enough to go GREEN, then run the local gate set.

```sh
cargo test -p bitween-workflow-core business_trip_permissions --lib
/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_business_trip_contracts.BusinessTripLifecycleContractTests.test_contract_declares_rust_business_trip_document_scope -v
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
RED/GREEN Rust document relatedness/legal-scope tests and Python contract tests;
readability keeps the DTO and predicates flat beside existing permission code;
architecture keeps Python as document/content resolver and side-effect bridge;
security preserves legal-tenant isolation while allowing unrelated documents to
pass unchanged; performance remains bounded to string normalization and one
small in-memory scope check.

## Checklist

- [x] RED Rust unit tests describe document relatedness and legal-scope parity.
- [x] RED Python contract test names the Rust document-scope boundary.
- [x] Rust 2024 / Rust 1.96 DTO/functions implement pure document-scope predicates.
- [x] Contract metadata and migration docs describe the new boundary.
- [x] Local cargo, Buck, Python, diff, and clippy gates pass.
- [x] Code review is recorded before merge.
