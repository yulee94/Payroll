# Spec: Payroll operation policy Rust slice

## Objective

Move the payroll operation policy normalization invariants from Python compatibility
logic into the Rust payroll backend contract crate. This is the next incremental
backend-to-Rust slice after the Buck2/Reindeer foundation: Rust should own the
safe defaults and clamps that decide how payroll input is interpreted before a
future Rust service executes payroll runs.

This slice does **not** remove Python compatibility code or introduce a new HTTP
framework. Python remains the characterization source until Rust parity is wired
through a service boundary and rollout evidence proves it can be decommissioned.

## Tech stack

- Rust crate: `crates/payroll-api`
- Serialization: existing `serde` and `serde_json`
- Build graph: Cargo plus existing Buck2 target `//crates/payroll-api:payroll_api_test`
- Characterization source: `services/payroll_policy_store.py`

## Commands

```sh
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
python3 -m venv /tmp/payroll-policy-venv
. /tmp/payroll-policy-venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m unittest tests.test_payroll_operation_policy tests.test_payroll_api_adapter -v
```

Use `bash scripts/verify_rust_buck2_reindeer.sh` before merging if Reindeer or
Buck2 inputs change.

## Project structure

- `crates/payroll-api/src/policy.rs` — Rust operation policy DTOs and normalization invariants.
- `crates/payroll-api/src/response.rs` — validation response should expose normalized policy data.
- `services/payroll_policy_store.py` — Python characterization source retained for compatibility.
- `tests/test_payroll_operation_policy.py` — Python behavior tests retained as parity guard.
- `docs/BUILD_AND_RUNTIME_TRANSITION.md` and `docs/RUST_BACKEND_MIGRATION.md` — migration status/checkpoint updates.

## Code style

Rust policy normalization should be explicit and conservative:

```rust
let rounding_minutes = int_between(raw.rounding_minutes, DEFAULT_ROUNDING, 1, 60);
let missing_clock_policy = MissingClockPolicy::from_str(raw_policy).unwrap_or_default();
```

Conventions:

- Prefer typed enums over stringly-typed policy branches.
- Preserve stable snake_case JSON fields used by Python and TypeScript contracts.
- Preserve unknown top-level policy fields in `extra` only when that does not weaken known invariant normalization.
- No new dependencies for this slice.

## Testing strategy

- RED: add Rust tests that express the current Python normalization behavior:
  - invalid `input_basis` falls back to `hybrid`;
  - invalid/negative/out-of-range attendance numbers are clamped to the Python defaults/ranges;
  - invalid `missing_clock_policy` falls back to `warn`;
  - default policy includes the same user-visible fields as Python (`show_setup_guide`, `policy_note`, attendance defaults);
  - validation responses serialize the normalized policy, not a partially typed placeholder.
- GREEN: implement the smallest Rust normalization API needed by those tests.
- Regression: run existing Python policy/API tests and Rust Cargo/Buck tests.

## Boundaries

- Always: preserve Python compatibility behavior while Rust parity is added.
- Always: keep Rust JSON field names stable for TypeScript/frontend consumers.
- Ask first: adding a new Rust HTTP framework, database, async runtime, or FFI bridge.
- Never: delete Python compatibility modules without zero-production-use evidence.
- Never: hand-edit Reindeer-generated `third-party/rust/BUCK` or vendored crates.

## Success criteria

- Rust exposes a normalized `OperationPolicy` equivalent to Python's `normalize_payroll_operation_policy` for known fields.
- Rust validation responses include normalized default/clamped operation policy data.
- Existing Python characterization tests still pass.
- Cargo and Buck2 tests for `crates/payroll-api` pass.
- Migration docs identify this as a completed policy-invariant slice, while full backend-to-Rust remains active.

## Implementation plan

### Task 1: Add Rust parity tests

Acceptance:

- Tests fail before implementation because current Rust policy lacks full Python-equivalent fields/clamps.

Verification:

- `cargo test -p bitween-payroll-api` fails for missing normalization behavior.

### Task 2: Implement Rust normalization

Acceptance:

- `OperationPolicy::normalize` accepts raw JSON/dto input and returns typed, clamped defaults.
- Response serialization uses stable Python-compatible fields.

Verification:

- `cargo test -p bitween-payroll-api` passes.

### Task 3: Verify compatibility and update docs

Acceptance:

- Python focused policy/API tests pass unchanged.
- Buck2 Rust tests pass.
- Migration docs record the completed Rust policy-invariant slice and next service-boundary step.

Verification:

- Commands in the Commands section pass or documented gaps are explicit.
