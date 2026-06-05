# Workflow Rust Follow-Up Planner Slice

## Objective
Move workflow submission/completion follow-up planning from `core/workflow/follow_up.py` into `crates/workflow-core` as pure Rust intent generation. This advances the backend-to-Rust objective while keeping Python responsible for executing workspace-store calendar/To-Do side effects, session adaptation, document hydration, and persistence.

## Tech Stack
- Rust 2024 / Rust 1.96 first-party backend crate: `crates/workflow-core`
- Python compatibility source: `core/workflow/follow_up.py`
- Contract metadata: `services/workflow_api_contract.py`
- Tests: Rust unit tests plus Python contract metadata tests

## Commands
- Targeted Rust RED/GREEN: `cargo test -p bitween-workflow-core workflow_follow_up --lib`
- Targeted Python contract: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_follow_up_contracts -v`
- Existing Python behavior: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_business_trip_followup_kpi_manager tests.test_workflow_forms -v`
- Workspace Rust: `cargo test --workspace`
- Buck2 parity: `buck2 test //crates/workflow-core:workflow_core_test`
- Formatting: `cargo fmt --check`
- Diff hygiene: `git diff --check`
- Bounded clippy: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/workflow-core/src/workflow_follow_up.rs` owns pure follow-up DTOs and plan functions.
- `crates/workflow-core/src/lib.rs` exports the new module.
- `crates/workflow-core/BUCK` lists the new source for Buck2 parity.
- `services/workflow_api_contract.py` declares Rust migration contract metadata.
- `tests/test_workflow_follow_up_contracts.py` locks Python-visible contract metadata.
- Migration docs track the checkpoint and Python boundary.

## Code Style
```rust
pub fn plan_submission_follow_up(input: &WorkflowSubmissionFollowUpInput) -> Vec<WorkflowFollowUpAction> {
    // pure intent generation only; no workspace_store, session, file, or notification side effects
}
```

Conventions:
- Keep planning deterministic and side-effect free.
- Preserve Python-compatible title/default/fallback rules, approval-step numbering, duplicate approver suppression, cc skip rules, source keys, sources, and trip-id propagation.
- Use supplied document type labels and trip IDs; Python remains responsible for dictionary/content_json extraction and `DOC_TYPE_LABELS` lookup.

## Testing Strategy
- RED first: Rust tests reference missing `workflow_follow_up` module functions/DTOs.
- Contract RED first: Python contract test expects workflow follow-up Rust metadata.
- GREEN: targeted Rust and Python tests pass.
- Regression: existing Python follow-up/workflow tests, workspace Rust, Buck2 workflow target, diff check, and bounded clippy pass.

## Boundaries
- Always: preserve `sync_submission_follow_up` and `sync_approval_complete_follow_up` call-intent behavior for supplied document, tenant, requester, approval line, cc, and executor values.
- Always: keep Python as adapter/executor for `UserSession`, `DOC_TYPE_LABELS`, `content_json` extraction, `workspace_store.add_*`, idempotent store updates, workflow persistence, and UI rendering.
- Ask first: adding runtime dependencies, changing workspace-store persisted item shape, changing source-key format, changing CI config.
- Never: commit tenant runtime data, payroll outputs, API keys, cookies, or local session files.

## Success Criteria
- Rust exposes `WorkflowFollowUpDocument`, `WorkflowFollowUpApprovalStep`, `WorkflowFollowUpAction`, `WorkflowSubmissionFollowUpInput`, `WorkflowApprovalCompleteFollowUpInput`, `plan_submission_follow_up`, and `plan_approval_complete_follow_up`.
- Rust preserves Python-compatible rules for:
  - document title defaulting to `문서`;
  - document type label defaulting to `문서` when not supplied;
  - requester fallback to session user for submission planning;
  - `period_start`/`requested_date`, `period_end`/`due_date`/`period_start`, and due fallback ordering;
  - requester calendar plus requester To-Do source keys;
  - approval-line To-Do/calendar numbering from original enumerate position;
  - blank/duplicate approval-step suppression after trimming approver IDs;
  - cc To-Do suppression for blank IDs, approvers, and requester;
  - approval-complete requester confirmation To-Do;
  - approval-complete executor To-Do/calendar only when executor is supplied and differs from requester;
  - trip-id propagation into all To-Do actions.
- Python contract metadata declares Rust-owned follow-up DTOs, entrypoints, action types, sources, and invariants.
- Local verification commands listed above pass before merge.

## Open Questions
None for this slice. Python remains the compatibility side-effect bridge until a later service-boundary slice executes Rust-planned follow-up intents from runtime calls.

## Implementation Checklist
- [x] RED Rust tests fail for missing workflow follow-up DTOs/functions.
- [x] RED Python contract test fails for missing workflow follow-up metadata.
- [x] Rust implementation passes targeted tests.
- [x] Contract metadata passes targeted Python tests.
- [x] Existing Python follow-up behavior remains green.
- [x] Migration docs updated.
- [x] Local gates pass.
- [ ] Review posted and PR merged/resynced.
