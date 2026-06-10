# Workflow Rust Form Values Slice

## Objective
Move workflow form value validation and document-field shaping from `Rust-owned contract` into `crates/workflow-core` as pure Rust functions. This advances the backend-to-Rust objective while side effects and persistence must be restored through Rust-owned service boundaries.

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
- `crates/workflow-core/src/workflow_forms.rs` owns pure form DTOs, built-in schema fallback, validation, field shaping, and attendance label mapping.
- `crates/workflow-core/src/lib.rs` exports the new module.
- `crates/workflow-core/BUCK` lists the new source for Buck2 parity.
- `Rust-owned contract` declares Rust migration contract metadata.
- `Rust parity test` locks contract-visible contract metadata.
- Migration docs track the checkpoint and Rust backlog boundary.

## Code Style
```rust
pub fn validate_form_values(schema: &[WorkflowFormFieldDef], values: &BTreeMap<String, String>) -> Vec<String> {
    // pure supplied DTO checks only; no tenant config/template filesystem lookup here
}
```

Conventions:
- Keep validation deterministic and side-effect free.
- Preserve legacy-compatible trimming, comma-stripped integer parsing, Korean error messages, lexicographic period comparison, and summary/amount fallback order.
- Use supplied schemas for tenant/template-specific forms; built-in schema fallback only mirrors documented default constants.

## Testing Strategy
- RED first: Rust tests reference missing `workflow_forms` module functions/DTOs.
- Contract RED first: Rust/TypeScript contract test expects workflow form Rust metadata.
- GREEN: targeted Rust and Rust tests pass.
- Regression: Rust workflow form/follow-up tests, workspace Rust, Buck2 workflow target, diff check, and bounded clippy pass.

## Boundaries
- Always: preserve `core.workflow.forms.validate_form_values`, `build_document_fields`, and `attendance_type_key` observable behavior for supplied values and built-in schemas.
- Always: keep these side effects outside pure Rust predicates until Rust services own `get_form_schema` tenant/template/config lookup, form template persistence, workflow document persistence, service mutation, and UI rendering.
- Ask first: adding runtime dependencies, changing document type constants, changing persisted document shape, changing CI config.
- Never: commit tenant runtime data, payroll outputs, API keys, cookies, or local session files.

## Success Criteria
- Rust exposes `WorkflowFormFieldDef`, `WorkflowDocumentFields`, built-in schema constants/functions, `validate_form_values`, `validate_builtin_form_values`, `build_document_fields`, and `attendance_type_key`.
- Rust preserves legacy-compatible rules for:
  - required field Korean error messages;
  - number validation with comma stripping;
  - closing month length check;
  - lexicographic period start/end ordering;
  - default general schema fallback for unknown document types;
  - summary fallback order (`summary`, `content`, `business_trip_purpose`, `purpose`, `reason`, then `item_summary` through join fallback);
  - amount fallback order (`total_amount`, then `estimated_amount`) with invalid values becoming zero;
  - payload string trimming and `document_type` injection;
  - attendance label-to-key mapping with `other` fallback.
- Rust contract metadata declares Rust-owned form value entrypoints, DTOs, document types, and invariants.
- Local verification commands listed above pass before merge.

## Open Questions
G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Implementation Checklist
- [x] RED Rust tests fail for missing workflow form DTOs/functions.
- [x] RED Rust/TypeScript contract test fails for missing workflow form metadata.
- [x] Rust implementation passes targeted tests.
- [x] Contract metadata passes targeted Rust tests.
- [x] Existing Rust workflow form behavior remains green.
- [x] Migration docs updated.
- [x] Local gates pass.
- [ ] Review posted and PR merged/resynced.
