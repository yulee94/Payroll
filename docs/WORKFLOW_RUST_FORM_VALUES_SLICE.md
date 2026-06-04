# Workflow Rust Form Values Slice

## Objective
Move workflow form value validation and document-field shaping from `core/workflow/forms.py` into `crates/workflow-core` as pure Rust functions. This advances the backend-to-Rust objective while keeping Python responsible for tenant-specific template lookup, config-store fallback, filesystem persistence, and UI rendering.

## Tech Stack
- Rust 2024 / Rust 1.96 first-party backend crate: `crates/workflow-core`
- Python compatibility source: `core/workflow/forms.py`
- Contract metadata: `services/workflow_api_contract.py`
- Tests: Rust unit tests plus Python contract metadata tests

## Commands
- Targeted Rust RED/GREEN: `cargo test -p bitween-workflow-core workflow_forms --lib`
- Targeted Python contract: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_form_contracts -v`
- Existing Python behavior: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_workflow_forms -v`
- Workspace Rust: `cargo test --workspace`
- Buck2 parity: `buck2 test //crates/workflow-core:workflow_core_test`
- Formatting: `cargo fmt --check`
- Diff hygiene: `git diff --check`
- Bounded clippy: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/workflow-core/src/workflow_forms.rs` owns pure form DTOs, built-in schema fallback, validation, field shaping, and attendance label mapping.
- `crates/workflow-core/src/lib.rs` exports the new module.
- `crates/workflow-core/BUCK` lists the new source for Buck2 parity.
- `services/workflow_api_contract.py` declares Rust migration contract metadata.
- `tests/test_workflow_form_contracts.py` locks Python-visible contract metadata.
- Migration docs track the checkpoint and Python boundary.

## Code Style
```rust
pub fn validate_form_values(schema: &[WorkflowFormFieldDef], values: &BTreeMap<String, String>) -> Vec<String> {
    // pure supplied DTO checks only; no tenant config/template filesystem lookup here
}
```

Conventions:
- Keep validation deterministic and side-effect free.
- Preserve Python-compatible trimming, comma-stripped integer parsing, Korean error messages, lexicographic period comparison, and summary/amount fallback order.
- Use supplied schemas for tenant/template-specific forms; built-in schema fallback only mirrors Python default constants.

## Testing Strategy
- RED first: Rust tests reference missing `workflow_forms` module functions/DTOs.
- Contract RED first: Python contract test expects workflow form Rust metadata.
- GREEN: targeted Rust and Python tests pass.
- Regression: existing Python workflow form/follow-up tests, workspace Rust, Buck2 workflow target, diff check, and bounded clippy pass.

## Boundaries
- Always: preserve `core.workflow.forms.validate_form_values`, `build_document_fields`, and `attendance_type_key` observable behavior for supplied values and built-in schemas.
- Always: keep Python as adapter for `get_form_schema` tenant/template/config lookup, form template persistence, workflow document persistence, service mutation, and UI rendering.
- Ask first: adding runtime dependencies, changing document type constants, changing persisted document shape, changing CI config.
- Never: commit tenant runtime data, payroll outputs, API keys, cookies, or local session files.

## Success Criteria
- Rust exposes `WorkflowFormFieldDef`, `WorkflowDocumentFields`, built-in schema constants/functions, `validate_form_values`, `validate_builtin_form_values`, `build_document_fields`, and `attendance_type_key`.
- Rust preserves Python-compatible rules for:
  - required field Korean error messages;
  - number validation with comma stripping;
  - closing month length check;
  - lexicographic period start/end ordering;
  - default general schema fallback for unknown document types;
  - summary fallback order (`summary`, `content`, `business_trip_purpose`, `purpose`, `reason`, then `item_summary` through join fallback);
  - amount fallback order (`total_amount`, then `estimated_amount`) with invalid values becoming zero;
  - payload string trimming and `document_type` injection;
  - attendance label-to-key mapping with `other` fallback.
- Python contract metadata declares Rust-owned form value entrypoints, DTOs, document types, and invariants.
- Local verification commands listed above pass before merge.

## Open Questions
None for this slice. Python remains the compatibility adapter until a later service-boundary slice wires Rust form validation/building into runtime calls.

## Implementation Checklist
- [x] RED Rust tests fail for missing workflow form DTOs/functions.
- [x] RED Python contract test fails for missing workflow form metadata.
- [x] Rust implementation passes targeted tests.
- [x] Contract metadata passes targeted Python tests.
- [x] Existing Python workflow form behavior remains green.
- [x] Migration docs updated.
- [x] Local gates pass.
- [ ] Review posted and PR merged/resynced.
