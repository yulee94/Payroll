# Spec: Payroll Rust operation-policy resolution slice

## Objective

Move payroll operation-policy resolution precedence into Rust for supplied tenant
G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.
compatibility rollout, but Rust should own the deterministic choice of which
normalized policy applies to a payroll request: site override first, then tenant
default, then built-in global default.

This slice closes the current gap where Rust resolves a policy snapshot before
calling the Rust validation service. It does not add filesystem persistence,
settings UI writes, database repositories, or an HTTP framework.

## Tech Stack

- Rust crate: `crates/payroll-api`
- Serialization: existing `serde` and `serde_json`
- TypeScript contract: `frontend/src/contracts/payrollApi.ts`
- Rust parity metadata/tests: `Rust-owned contract` and
  `Rust parity test`
- No new dependencies

## Commands

```sh
buck2 build '<target>[clippy.txt]'
buck2 test //...
buck2 test //crates/payroll-api:payroll_api_test
# G028 retired the former compatibility gate; use Buck2 Rust tests plus TypeScript gates from AGENTS.md.
npm run typecheck --prefix frontend
git diff --check
```

## Project Structure

- `crates/payroll-api/src/policy_resolution.rs` — Rust settings snapshot,
  site/tenant/global precedence, source typing, and resolution DTO.
- `crates/payroll-api/src/response.rs` — validation helper that resolves policy
  from settings before creating the validation response.
- `crates/payroll-api/src/service.rs` — service facade method for validating a
  payload using Rust policy resolution.
- `frontend/src/contracts/payrollApi.ts` — TypeScript source/decision DTOs.
- `Rust-owned contract`, tests, and docs — contract metadata and
  migration checkpoint updates.

## Code Style

Keep policy resolution dependency-free and snapshot-based:

```rust
let settings = PayrollPolicySettings::default()
    .with_tenant_policy(OperationPolicy::new(PayrollInputBasis::Attendance))
    .with_site_policy("Site A", OperationPolicy::new(PayrollInputBasis::Invoice));

let resolved = resolve_operation_policy("Site A", &settings);
assert_eq!(resolved.source, OperationPolicySource::Site);
```

Conventions:

- Stable source strings: `site`, `tenant`, `global`.
- Normalize the chosen policy before returning or serializing it.
- `has_site_override` is true only when the chosen source is `site`.
- Workplaces are trimmed; alias/canonical matching is supported only from the
  supplied snapshot until Rust owns org configuration.
- Empty/missing workplace cannot select a site override and falls back to tenant
  or global policy.

## Testing Strategy

- RED: add Rust tests that reference missing policy-resolution types and service
  facade behavior.
- GREEN: implement the smallest Rust resolver matching documented precedence for
  supplied settings snapshots.
- Regression: run Buck2 and Rust/TypeScript policy/API contract tests, frontend
  typecheck, and whitespace checks.

## Boundaries

- Always: preserve existing settings persistence and compatibility tests.
- Always: keep validation response behavior stable while moving policy selection
  into Rust.
- Always: make source precedence explicit and serializable.
- Ask first: adding database/filesystem settings repositories, org-config file
  parsing, HTTP framework wiring, or a new dependency.
- Never: remove settings/policy compatibility backlog until Rust persistence
  and rollout parity are proven.

## Success Criteria

- Rust exposes `PayrollPolicySettings`, `OperationPolicySource`,
  `ResolvedOperationPolicy`, and `resolve_operation_policy`.
- Rust resolves site override > tenant policy > global default and normalizes the
  selected `OperationPolicy`.
- Rust can validate a payroll payload using a supplied policy settings snapshot
  via `validate_payroll_api_payload_with_policy_settings` and
  `PayrollApiService::validate_run_payload_with_policy_settings`.
- TypeScript/Rust/Markdown contracts describe the Rust policy-resolution
  entrypoint, source values, and precedence.
- Rust policy contract tests still pass.
- Verification commands in this spec pass locally.

## Implementation Plan

### Task 1: Add RED tests

Acceptance:

- Rust tests fail because policy-resolution types/functions and service method do
  not exist.

Verification:

- `buck2 test //crates/payroll-api:payroll_api_test` fails for missing
  symbols.

### Task 2: Implement Rust resolver and service helper

Acceptance:

- Site overrides win over tenant defaults when the canonical/alias workplace
  matches.
- Tenant policy wins over global default when no site override exists.
- Global default is used when no site or tenant policy exists.
- Validation responses created through the service helper include the resolved
  normalized policy and `operation_policy_source`.

Verification:

- `buck2 test //crates/payroll-api:payroll_api_test`
  passes.

### Task 3: Align contracts/docs and verify

Acceptance:

- TypeScript/Rust/Markdown surfaces name the Rust resolver and policy source
  values.
- Migration docs record the checkpoint and remaining persistence gap.

Verification:

- Commands in the Commands section pass.
