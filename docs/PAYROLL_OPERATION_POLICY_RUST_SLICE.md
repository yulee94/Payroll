# Spec: Payroll operation policy Rust slice

## Objective

Keep payroll operation policy normalization in the Rust payroll backend contract.
The policy layer decides safe defaults and clamps before payroll execution,
PostgreSQL admission, or UI workflow actions consume payroll inputs.

G028 decommissioned the former repo-owned compatibility bridge; missing behavior
must be restored only through Rust/Buck2 services or TypeScript contract gates.

## Tech stack

- Rust crate: `crates/payroll-api`
- Serialization: `serde` and `serde_json`
- Build graph: Buck2 target `//crates/payroll-api:payroll_api_test`
- Parity source: Rust-owned fixtures and documented payroll policy invariants

## Commands

```sh
buck2 test //...
buck2 test //crates/payroll-api:payroll_api_test
buck2 build '//crates/payroll-api:payroll_api[check]'
cd apps/bitween-platform-ui
npm run verify:no-python-source
npm run verify:buck2-only
npm run typecheck
```

Use `bash scripts/verify_rust_buck2_reindeer.sh` before merging when Reindeer,
vendored Rust dependencies, or Buck2 inputs change.

## Project structure

- `crates/payroll-api/src/policy.rs` — Rust operation policy DTOs and
  normalization invariants.
- `crates/payroll-api/src/response.rs` — validation responses expose normalized
  policy data.
- `frontend/src/contracts/payrollApi.ts` — TypeScript contract fields consumed by
  product surfaces.
- `docs/PAYROLL_API_CONTRACT.md` — public payroll API and DTO contract.

## Code style

Rust policy normalization should be explicit and conservative:

```rust
let rounding_minutes = int_between(raw.rounding_minutes, DEFAULT_ROUNDING, 1, 60);
let missing_clock_policy = MissingClockPolicy::from_str(raw_policy).unwrap_or_default();
```

Conventions:

- Prefer typed enums over stringly typed policy branches.
- Preserve stable snake_case JSON fields for Rust and TypeScript contracts.
- Preserve unknown top-level policy fields in `extra` only when that does not
  weaken known invariant normalization.
- No new runtime dependencies for this slice.

## Testing strategy

- RED: add Rust tests that express documented payroll policy invariants:
  - invalid `input_basis` falls back to `hybrid`;
  - invalid/negative/out-of-range attendance numbers are clamped to documented
    defaults/ranges;
  - invalid `missing_clock_policy` falls back to `warn`;
  - default policy includes user-visible setup-guide, policy-note, and
    attendance defaults;
  - validation responses serialize the normalized policy.
- GREEN: implement the smallest Rust normalization API needed by those tests.
- Regression: run Buck2 tests plus TypeScript contract/product gates.

## Boundaries

- Always keep JSON fields stable for frontend/API consumers.
- Always document new policy fields before exposing them.
- Ask first before adding a new Rust HTTP framework, database, async runtime, or
  FFI bridge.
- Never reintroduce repo-owned Python; restore missing behavior through Rust or
  TypeScript contracts only.
- Never hand-edit Reindeer-generated `third-party/rust/BUCK` or vendored crates.

## Success criteria

- Rust exposes a normalized `OperationPolicy` for known fields.
- Rust validation responses include normalized default/clamped operation policy
  data.
- Buck2 tests for `crates/payroll-api` pass.
- TypeScript contracts and docs identify this as a completed policy-invariant
  slice while deeper production service work remains active.
