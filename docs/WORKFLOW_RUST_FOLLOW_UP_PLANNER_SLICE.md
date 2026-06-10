# Workflow Rust Follow-Up Planner Slice

## Objective
Move workflow submission/completion follow-up planning from `Rust-owned contract` into `crates/workflow-core` as pure Rust intent generation. This advances the backend-to-Rust objective while side effects and persistence must be restored through Rust-owned service boundaries.

## Tech Stack
- Rust 2024 / Rust 1.96 first-party backend crate: `crates/workflow-core`
- Historical source: pre-G028 compatibility source was removed; keep parity evidence in Rust tests, TypeScript contracts, and documented fixtures.
- Contract metadata: `Rust-owned contract`
- Tests: Rust unit tests plus Rust contract metadata tests

## Commands
- Targeted Rust RED/GREEN: `buck2 test //crates/workflow-core:workflow_core_test`
- G028 retired the former compatibility gate; use Buck2 Rust tests plus TypeScript gates from AGENTS.md.
- G028 retired the former compatibility gate; use Buck2 Rust tests plus TypeScript gates from AGENTS.md.
- Workspace Rust: `buck2 test //...`
- Buck2 parity: `buck2 test //crates/workflow-core:workflow_core_test`
- Formatting: `buck2 build '<target>[clippy.txt]'`
- Diff hygiene: `git diff --check`
- Bounded clippy: `buck2 build '<target>[clippy.txt]'`

## Project Structure
- `crates/workflow-core/src/workflow_follow_up.rs` owns pure follow-up DTOs and plan functions.
- `crates/workflow-core/src/lib.rs` exports the new module.
- `crates/workflow-core/BUCK` lists the new source for Buck2 parity.
- `Rust-owned contract` declares Rust migration contract metadata.
- `Rust parity test` locks contract-visible contract metadata.
- Migration docs track the checkpoint and Rust backlog boundary.

## Code Style
```rust
pub fn plan_submission_follow_up(input: &WorkflowSubmissionFollowUpInput) -> Vec<WorkflowFollowUpAction> {
    // pure intent generation only; no workspace_store, session, file, or notification side effects
}
```

Conventions:
- Keep planning deterministic and side-effect free.
- Preserve legacy-compatible title/default/fallback rules, approval-step numbering, duplicate approver suppression, cc skip rules, source keys, sources, and trip-id propagation.
- G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Testing Strategy
- RED first: Rust tests reference missing `workflow_follow_up` module functions/DTOs.
- Contract RED first: Rust/TypeScript contract test expects workflow follow-up Rust metadata.
- GREEN: targeted Rust and Rust tests pass.
- Regression: Rust follow-up/workflow tests, workspace Rust, Buck2 workflow target, diff check, and bounded clippy pass.

## Boundaries
- Always: preserve `sync_submission_follow_up` and `sync_approval_complete_follow_up` call-intent behavior for supplied document, tenant, requester, approval line, cc, and executor values.
- Always: keep these side effects outside pure Rust predicates until Rust services own `UserSession`, `DOC_TYPE_LABELS`, `content_json` extraction, `workspace_store.add_*`, idempotent store updates, workflow persistence, and UI rendering.
- Ask first: adding runtime dependencies, changing workspace-store persisted item shape, changing source-key format, changing CI config.
- Never: commit tenant runtime data, payroll outputs, API keys, cookies, or local session files.

## Success Criteria
- Rust exposes `WorkflowFollowUpDocument`, `WorkflowFollowUpApprovalStep`, `WorkflowFollowUpAction`, `WorkflowSubmissionFollowUpInput`, `WorkflowApprovalCompleteFollowUpInput`, `plan_submission_follow_up`, and `plan_approval_complete_follow_up`.
- Rust preserves legacy-compatible rules for:
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
- Rust contract metadata declares Rust-owned follow-up DTOs, entrypoints, action types, sources, and invariants.
- Local verification commands listed above pass before merge.

## Open Questions
G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Implementation Checklist
- [x] RED Rust tests fail for missing workflow follow-up DTOs/functions.
- [x] RED Rust/TypeScript contract test fails for missing workflow follow-up metadata.
- [x] Rust implementation passes targeted tests.
- [x] Contract metadata passes targeted Rust tests.
- [x] Existing Rust follow-up behavior remains green.
- [x] Migration docs updated.
- [x] Local gates pass.
- [ ] Review posted and PR merged/resynced.
