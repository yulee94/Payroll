# Workflow Rust Inbox Classification Slice

## Objective
Move workflow inbox classification (`to_approve`, `my_draft`, `circulate`, `in_progress`, `completed`, `rejected`, `reference`, legacy aliases, and `all`) into `crates/workflow-core` as pure Rust predicates. This advances the backend-to-Rust goal while keeping Python responsible for session adaptation, document hydration, permission resolution, persistence, and UI labels.

## Tech Stack
- Rust 2024 / Rust 1.96 first-party backend crate: `crates/workflow-core`
- Python compatibility source: `core/workflow/inbox.py`
- Contract metadata: `services/workflow_api_contract.py`
- Tests: Rust unit tests plus Python contract metadata tests

## Commands
- Targeted Rust RED/GREEN: `cargo test -p bitween-workflow-core workflow_inbox --lib`
- Targeted Python contract: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_inbox_contracts -v`
- Existing Python behavior: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_inbox_gw -v`
- Workspace Rust: `cargo test --workspace`
- Buck2 parity: `buck2 test //crates/workflow-core:workflow_core_test`
- Formatting: `cargo fmt --check`
- Diff hygiene: `git diff --check`
- Bounded clippy: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/workflow-core/src/workflow_inbox.rs` owns pure inbox classification DTOs and predicates.
- `crates/workflow-core/src/lib.rs` exports the new module.
- `crates/workflow-core/BUCK` lists the new Rust source for Buck2 parity.
- `services/workflow_api_contract.py` declares the Rust migration contract metadata.
- `tests/test_workflow_inbox_contracts.py` locks Python-visible contract metadata.
- Migration docs track the checkpoint and Python boundary.

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
- Preserve Python-compatible status and GW import list semantics.
- Additive DTO fields use safe empty defaults.

## Testing Strategy
- RED first: Rust tests reference missing `workflow_inbox` module, DTOs, and `matches_inbox` function.
- Contract RED first: Python contract test expects workflow inbox Rust metadata.
- GREEN: targeted Rust and Python tests pass.
- Regression: existing Python inbox behavior, workspace Rust, Buck2 workflow target, diff check, and bounded clippy pass.

## Boundaries
- Always: preserve `core.workflow.inbox.matches_inbox` observable classification for supplied document/user/can-approve state.
- Always: keep Python as adapter for `UserSession`, `wf_perm.can_approve_document`, document dictionaries, labels, counts, filtering, persistence, and UI.
- Ask first: adding runtime dependencies, changing inbox IDs, changing persisted document shape, changing CI config.
- Never: commit tenant runtime data, payroll outputs, API keys, cookies, or local session files.

## Success Criteria
- Rust exposes `WorkflowInboxDocument`, `WorkflowInboxApprovalStep`, `WorkflowInboxMatchInput`, `matches_inbox`, `filter_inbox_ids`, and stable inbox ID constants.
- Rust preserves Python-compatible rules for:
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
- Python contract metadata declares Rust-owned inbox entrypoints and invariants.
- Local verification commands listed above pass before merge.

## Open Questions
None for this slice. Python remains the compatibility adapter until a later service-boundary slice wires Rust inbox classification into runtime calls.

## Implementation Checklist
- [x] RED Rust tests fail for missing workflow inbox module/DTOs/functions.
- [x] RED Python contract test fails for missing workflow inbox metadata.
- [x] Rust implementation passes targeted tests.
- [x] Contract metadata passes targeted Python tests.
- [x] Existing Python inbox behavior remains green.
- [x] Migration docs updated.
- [x] Local gates pass.
- [ ] Review posted and PR merged/resynced.
