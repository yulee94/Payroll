# Workflow Rust Document Permissions Slice

## Objective
Move workflow document permission decisions for view, edit, submit, and approve into `crates/workflow-core` as pure Rust predicates. This advances the backend-to-Rust goal without moving storage, `UserSession` conversion, profile resolution, org-position permission lookup, document mutation, notifications, calendar/To-Do links, or UI bridge behavior.

## Tech Stack
- Rust 2024 / Rust 1.96 first-party backend crate: `crates/workflow-core`
- legacy compatibility and contract metadata: `Rust-owned contract`, `Rust-owned contract`, `tests/`
- Serialization: existing `serde` dependency already used by `bitween-workflow-core`

## Commands
- Targeted Rust RED/GREEN: `buck2 test //crates/workflow-core:workflow_core_test`
- G028 retired the former compatibility gate; use Buck2 Rust tests plus TypeScript gates from AGENTS.md.
- Workspace Rust: `buck2 test //...`
- Buck2 parity: `buck2 test //crates/workflow-core:workflow_core_test`
- Formatting: `buck2 build '<target>[clippy.txt]'`
- Diff hygiene: `git diff --check`
- Bounded clippy: `buck2 build '<target>[clippy.txt]'`

## Project Structure
- `crates/workflow-core/src/business_trip_permissions.rs` owns pure permission DTOs and predicates.
- `Rust-owned contract` declares Rust migration contract metadata consumed by Rust tests and API docs.
- `Rust parity test` locks contract-visible contract metadata.
- `docs/RUST_BACKEND_MIGRATION.md`, `docs/BUILD_AND_RUNTIME_TRANSITION.md`, and `docs/WORKFLOW_ERP.md` track migration checkpoints.

## Code Style
```rust
pub fn can_approve_document(input: &WorkflowDocumentPermissionInput) -> bool {
    if !workflow_permission_document_legal_scope_allowed(&input.principal, &input.document, &input.tenant_id) {
        return false;
    }
    // pure supplied DTO checks only; no profile/store/session lookups here
}
```

Conventions:
- Keep predicates side-effect free and deterministic.
- Accept resolved DTOs/booleans as inputs instead of reading stores or sessions.
- Preserve legacy compatibility names and denial semantics.
- Additive Rust DTO fields must have safe defaults.

## Testing Strategy
- RED first: Rust tests reference missing document permission DTOs/functions and must fail before implementation.
- Contract RED first: Rust/TypeScript contract test expects document permission entrypoints/invariants and must fail before metadata is updated.
- GREEN: targeted Rust and Rust tests pass.
- Regression: workspace Rust, Buck2 workflow target, diff check, and bounded clippy pass.

## Boundaries
- Always: preserve `core.workflow.permissions` observable behavior for supplied documents, profiles, approval steps, and org-approval capability.
- Always: keep resolver and mutator side effects in explicit Rust service backlog lanes for this slice.
- Ask first: adding runtime dependencies, changing persisted workflow document storage, changing approval-step status taxonomy, changing CI config.
- Never: commit tenant runtime data, payroll outputs, API keys, cookies, or local session files.

## Success Criteria
- Rust exposes `WorkflowApprovalStep`, `WorkflowDocumentPermissionInput`, `can_view_document`, `can_edit_document`, `can_submit_document`, and `can_approve_document`.
- Rust preserves business-trip document legal-scope gate before document permissions.
- Admin/executive/finance can view legal-scoped documents.
- Requesters can view their documents.
- Approval-step assignees can view documents and approve only the current pending step.
- Site managers/HR can view profile-scoped site documents.
- Edit and submit are requester-only and limited to `draft` or `requested_changes`; `approved` and `closed` are terminal.
- Approval is limited to `submitted` or `in_review`, requires a pending step, and allows only the current pending approver unless supplied org workflow-approval capability is true and the principal has admin/executive/finance workflow authority.
- Rust contract metadata declares the Rust-owned document permission entrypoints and invariants.
- Local verification commands listed above pass before merge.

## Open Questions
G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Implementation Checklist
- [x] RED Rust tests fail for missing document permission DTOs/functions.
- [x] RED Rust/TypeScript contract test fails for missing entrypoints/invariants.
- [x] Rust implementation passes targeted tests.
- [x] Contract metadata passes targeted Rust tests.
- [x] Migration docs updated.
- [x] Local gates pass.
- [ ] Review posted and PR merged/resynced.
