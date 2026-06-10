# Workflow Rust Inbox Classification Slice

## Objective
Move workflow inbox classification (`to_approve`, `my_draft`, `circulate`, `in_progress`, `completed`, `rejected`, `reference`, legacy aliases, and `all`) into `crates/workflow-core` as pure Rust predicates. This advances the backend-to-Rust goal while side effects and persistence must be restored through Rust-owned service boundaries.

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
- `crates/workflow-core/src/workflow_inbox.rs` owns pure inbox classification DTOs and predicates.
- `crates/workflow-core/src/lib.rs` exports the new module.
- `crates/workflow-core/BUCK` lists the new Rust source for Buck2 parity.
- `Rust-owned contract` declares the Rust migration contract metadata.
- `Rust parity test` locks contract-visible contract metadata.
- Migration docs track the checkpoint and Rust backlog boundary.

## Code Style
```rust
pub fn matches_inbox(input: &WorkflowInboxMatchInput) -> bool {
    if input.inbox_id.trim().is_empty() || input.inbox_id == INBOX_ALL {
        return true;
    }
    // pure supplied DTO checks only; no profile/session/store reads here
}
```

Conventions:
- Keep classification deterministic and side-effect free.
- Accept supplied `can_approve_document` instead of calling permission logic.
- Preserve legacy-compatible status and GW import list semantics.
- Additive DTO fields use safe empty defaults.

## Testing Strategy
- RED first: Rust tests reference missing `workflow_inbox` module, DTOs, and `matches_inbox` function.
- Contract RED first: Rust/TypeScript contract test expects workflow inbox Rust metadata.
- GREEN: targeted Rust and Rust tests pass.
- Regression: Rust inbox behavior, workspace Rust, Buck2 workflow target, diff check, and bounded clippy pass.

## Boundaries
- Always: preserve `core.workflow.inbox.matches_inbox` observable classification for supplied document/user/can-approve state.
- Always: keep these side effects outside pure Rust predicates until Rust services own `UserSession`, `wf_perm.can_approve_document`, document dictionaries, labels, counts, filtering, persistence, and UI.
- Ask first: adding runtime dependencies, changing inbox IDs, changing persisted document shape, changing CI config.
- Never: commit tenant runtime data, payroll outputs, API keys, cookies, or local session files.

## Success Criteria
- Rust exposes `WorkflowInboxDocument`, `WorkflowInboxApprovalStep`, `WorkflowInboxMatchInput`, `matches_inbox`, `filter_inbox_ids`, and stable inbox ID constants.
- Rust preserves legacy-compatible rules for:
  - blank/`all` inbox inclusion;
  - direct supplied `can_approve_document` for `to_approve`;
  - GW imported pending/draft/circulate list overrides;
  - requester draft/requested-changes classification;
  - requester/approval-line in-progress classification;
  - completed visibility for requester/approval-line/cc users;
  - rejected visibility for requester/approval-line users;
  - circulate excluding draft/cancelled and active approval tasks;
  - reference excluding cc users and draft documents;
  - legacy `my_requests` and `pending_approval` aliases.
- Rust contract metadata declares Rust-owned inbox entrypoints and invariants.
- Local verification commands listed above pass before merge.

## Open Questions
G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Implementation Checklist
- [x] RED Rust tests fail for missing workflow inbox module/DTOs/functions.
- [x] RED Rust/TypeScript contract test fails for missing workflow inbox metadata.
- [x] Rust implementation passes targeted tests.
- [x] Contract metadata passes targeted Rust tests.
- [x] Existing Rust inbox behavior remains green.
- [x] Migration docs updated.
- [x] Local gates pass.
- [ ] Review posted and PR merged/resynced.
