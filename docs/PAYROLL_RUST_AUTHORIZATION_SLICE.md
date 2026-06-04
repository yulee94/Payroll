# Spec: Payroll Rust authorization invariants slice

## Objective

Move payroll API authorization decisions into Rust-owned, framework-neutral code
before selecting an HTTP framework. This slice defines tenant/legal-entity,
RBAC, and ABAC invariants for payroll validation/run/settings actions so future
HTTP, Tauri, mobile, and Kubernetes wrappers call one Rust decision point instead
of duplicating Python compatibility checks.

This is still not full authentication. The caller/session/JWT layer remains a
future wrapper concern; this slice only evaluates a supplied principal and parsed
payroll request.

## Tech Stack

- Rust crate: `crates/payroll-api`
- Serialization: existing `serde` and `serde_json`
- No new auth, JWT, HTTP, database, or policy engine dependency
- Compatibility source: `core/org_access.py`, `core/org_positions.py`, and
  `tests/test_org_access.py`

## Commands

```sh
cargo fmt --check
cargo test --workspace
buck2 test //crates/payroll-api:payroll_api_test
python -m unittest tests.test_org_access tests.test_payroll_api_contract -v
npm run typecheck --prefix frontend
```

## Project Structure

- `crates/payroll-api/src/access.rs` — Rust payroll authorization roles,
  positions, permissions, principal attributes, and access decisions.
- `crates/payroll-api/src/service.rs` — service facade method for authorizing a
  parsed payroll request.
- `frontend/src/contracts/payrollApi.ts` — TypeScript DTOs for authorization
  actions and decision responses.
- `services/payroll_api_contract.py` and `docs/PAYROLL_API_CONTRACT.md` — stable
  contract metadata and examples.
- Migration docs under `docs/` — checkpoint and remaining gap updates.

## Code Style

Keep authorization explicit and dependency-free:

```rust
let principal = PayrollPrincipal::new("user-1", "coss")
    .with_role(PayrollRole::Finance)
    .with_position(PayrollPosition::Manager)
    .with_org_unit("finance")
    .with_effective_platforms(["payroll", "accounting"]);

let decision = service.authorize_run_request(&request, &principal, PayrollAction::Run);
```

Conventions:

- Stable snake_case JSON fields.
- `reason_code` is empty on allow and stable on deny.
- Tenant mismatch is denied before permission checks.
- RBAC comes from role + position families.
- ABAC uses tenant, affiliate, workplace, org unit, and effective platform
  attributes supplied by the caller/session layer.
- CEO position bypasses team platform filtering to match Python compatibility;
  non-CEO admin/finance roles are still filtered by effective unit platforms.

## Testing Strategy

- RED: Rust authorization tests assert the public decision types/functions before
  implementation.
- GREEN: implement the smallest Rust model matching Python platform scoping.
- Regression: run Cargo, Buck2, Python org access/contract tests, and frontend
  typecheck.

## Boundaries

- Always: keep Python compatibility behavior intact.
- Always: deny cross-tenant payroll requests when request tenant and principal
  tenant differ.
- Always: require payroll platform permission after role/position plus effective
  unit platform filtering.
- Ask first: adding JWT/WebAuthn/OIDC crates, policy engines, database-backed
  role repositories, or HTTP middleware.
- Never: treat frontend role labels as authorization; wrappers must supply a
  trusted principal from server-side/session/JWT state.

## Success Criteria

- Rust exposes `PayrollPrincipal`, `PayrollAction`, `PayrollPermission`, and
  `PayrollAccessDecision`.
- Rust service facade can authorize a parsed `PayrollRunRequest`.
- Finance manager in a payroll-enabled unit can run payroll; maintenance member
  cannot access payroll; non-CEO admin outside payroll platform is still denied;
  CEO is allowed across platforms.
- Tenant mismatch and workplace ABAC restrictions deny with stable reason codes.
- TypeScript/Python/Markdown contract surfaces describe the same decision shape.
- Cargo, Buck2, Python, and TypeScript verification commands pass locally.

## Implementation Plan

### Task 1: Add Rust authorization RED tests

Acceptance:

- Tests fail because authorization public types and service method do not exist.

Verification:

- `cargo test -p bitween-payroll-api access::tests` fails for missing symbols.

### Task 2: Implement Rust authorization model

Acceptance:

- Roles, positions, permissions, tenant checks, platform filtering, and ABAC
  scope checks produce deterministic decisions.
- `PayrollApiService::authorize_run_request` delegates to the Rust access model.

Verification:

- `cargo test -p bitween-payroll-api access::tests` passes.

### Task 3: Align contracts/docs and verify

Acceptance:

- TypeScript/Python/Markdown contract surfaces include the authorization decision
  DTO and invariant notes.
- Migration docs identify this authorization checkpoint and remaining production
  auth work.

Verification:

- Commands in the Commands section pass.
