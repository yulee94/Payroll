# Buck2 + Reindeer Rust transition runbook

## Status

Started on 2026-06-04. This is the first production-safe slice of the full
Rust backend transition: Buck2 can now build and test the existing Rust payroll
API contract crate through Reindeer-managed third-party Rust dependencies.

Cargo build/check/test/clippy/run/bench are retired for product verification; Buck2 is canonical for build, check, test, and clippy evidence. Repo-owned legacy compatibility code was decommissioned in G028, so missing behavior must return through Rust/Buck2 or TypeScript contracts only.

## Source-backed basis

Official references checked for this implementation:

- Buck2 getting started and Rust tutorial path: https://buck2.build/docs/getting_started/
- Buck2 installation/source build guidance: https://buck2.build/docs/getting_started/install/
- Buck2 build-rule explicit input requirement: https://buck2.build/docs/concepts/build_rule/
- Buck2 Rust language support: https://buck2.build/docs/about/language_support/
- Buck2 `rust_library`, `rust_test`, and `rust_binary` rule attributes:
  - https://buck2.build/docs/prelude/rules/rust/rust_library/
  - https://buck2.build/docs/prelude/rules/rust/rust_test/
  - https://buck2.build/docs/prelude/rules/rust/rust_binary/
- Reindeer Cargo-to-Buck dependency generation: https://github.com/facebookincubator/reindeer
- Reindeer manual and fixup model: https://github.com/facebookincubator/reindeer/blob/main/docs/MANUAL.md

## Repository layout

| Path | Owner | Purpose |
| --- | --- | --- |
| `.buckconfig`, `.buckroot` | Build tooling | Buck2 root, cells, bundled prelude, default platform, Rust edition/remap settings. |
| `toolchains/BUCK` | Build tooling | Buck2 bundled demo/system toolchain bootstrap for local Rust validation. |
| `reindeer.toml` | Build tooling | Reindeer config for the Cargo workspace, vendored third-party Rust deps, generated Buck macros, and fail-fast fixup policy. |
| `third-party/rust/BUCK` | Reindeer generated | Buck2 rules for Cargo dependencies; never hand-edit. |
| `third-party/rust/vendor/` | Reindeer generated | Vendored crates so Buck2 does not need crates.io network access at build time. |
| `third-party/rust/fixups/` | Build tooling | Required Reindeer fixups for crates with build scripts or Cargo compile-time env needs. |
| `crates/payroll-api/BUCK` | Rust backend | First verified first-party Rust `rust_library` and `rust_test` targets. |
| `scripts/verify_rust_buck2_reindeer.sh` | Verification | Local verification entrypoint for Reindeer generated output plus Buck2 build/test and target-specific check parity. |

## Tool versions

- Rust baseline: edition `2024`, `rust-version = "1.96"`, and `rust-toolchain.toml` channel `1.96.0`.
- Local Buck2 verified version: `buck2 2b6f2339eb903743a21606ddb93ea669`.
- CI installs Reindeer from `facebookincubator/reindeer` at revision `d1638c7675fe31013f101f39cd18248f40b5ce6c` to keep generated Buck output deterministic.

## Update workflow

Run this workflow whenever Rust dependencies or first-party Rust targets change:

```sh
reindeer --config reindeer.toml vendor
reindeer --config reindeer.toml buckify
git diff -- third-party/rust/BUCK third-party/rust/vendor third-party/rust/fixups
buck2 build //crates/payroll-api:payroll_api
buck2 test //crates/payroll-api:payroll_api_test
buck2 build '//crates/payroll-api:payroll_api[check]'
buck2 build //crates/payroll-api:platform_live_view
buck2 build //crates/payroll-api:hr_employee_store //crates/payroll-api:archive_intake_store
buck2 test //crates/payroll-api:hr_employee_store_test //crates/payroll-api:archive_intake_store_test
```

Use explicit target-specific `[check]` / `[clippy.txt]` targets for Rust provider
checks. Unsupported recursive provider shortcuts are blocked by the verification
ratchet.

`reindeer.toml` sets `unresolved_fixup_error = true`. If Reindeer finds a crate
with a build script and no fixup, the transition is blocked until the build
script is reviewed and a crate-specific fixup records whether it runs under
Buck2.

## Current verified targets

| Target | Purpose | Verification |
| --- | --- | --- |
| `//crates/payroll-api:payroll_api` | Rust payroll API contract library | `buck2 build //crates/payroll-api:payroll_api` |
| `//crates/payroll-api:payroll_api_test` | Rust payroll API contract unit tests | `buck2 test //crates/payroll-api:payroll_api_test` |

## Production gates for the full Rust transition

A backend slice restoring historical behavior may ship only when all gates are met:

1. Historical behavior is locked with Rust tests, TypeScript contract checks, or documented fixtures.
2. Rust DTOs, policy invariants, tenant/legal-entity scoping, and error codes are documented.
3. Rust implementation has Buck2 tests.
4. Reindeer-generated dependency rules are up to date and build without missing fixups.
5. Kubernetes service/worker/job shape is documented before production rollout.
6. API authorization is enforced server-side with RBAC + ABAC; frontend and Tauri surfaces are capability hints only.
7. Repo-owned compatibility code remains decommissioned; do not restore it without a Rust/Buck2-backed migration record.

## Next Rust backend slices

1. Expand payroll API from validation contract into a service crate with health,
   readiness, typed configuration, audit/error envelopes, and Kubernetes probe
   semantics.
2. Port workflow/business-trip lifecycle state transitions into Rust behind
   characterization tests for trip plan -> trip execution -> work journal -> KPI
   reflection -> manager ongoing/completed views.
3. Port KPI and manager-dashboard read models with explicit tenant/legal-entity
   ABAC checks.
4. Port org hierarchy, roles, and service-account policy evaluation.
5. Restore missing historical backend behavior only through Rust services with Buck2 tests, production routing evidence, and TypeScript contract alignment.
