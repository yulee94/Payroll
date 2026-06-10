# Python Decommission Inventory

Status: decommissioned
Completed: 2026-06-10

Target end state is now enforced: no repo-owned Python source, stubs, bytecode caches, tests, local tools, UI panels, services, or compatibility adapters remain in the source tree. New Python implementation is prohibited.

## Current source count

Repo-owned Python source count: 0

Generated Buck2 output under `buck-out/` is not source of record and is ignored by the decommission gate. If Buck2 materializes Python helper files for its own toolchain, those files remain generated build output, not Bitween implementation.

## Removed legacy surfaces

- Root legacy desktop/payroll modules such as payroll builders, invoice parsers, validators, roster helpers, and Tkinter entrypoints.
- `auth/`, `core/`, `integrations/`, `services/`, `ui/`, and `tools/` Python trees.
- Python compatibility and characterization tests under `tests/`.
- Python release/local-helper scripts under `scripts/`.
- Third-party vendored Python helper scripts that were not required by Buck2-built Rust targets.

## Replacement evidence

Production-useful surfaces are now owned by:

1. Rust domain/API/service boundaries under `crates/payroll-api` and future Rust crates.
2. PostgreSQL migrations and schema contracts under `crates/payroll-api/migrations/`.
3. RustFS object lifecycle contracts and archive source-sync/admission/rollback paths.
4. TypeScript frontend contracts under `frontend/` and the unified shell under `apps/bitween-platform-ui/`.
5. Buck2 build/check/test/clippy targets for Rust verification.
6. Node-based product gates for UI, i18n, security, sensitive data, auth, route authorization, performance, Kubernetes manifests, and no-Python enforcement.

## Enforcement

Run:

```powershell
cd apps/bitween-platform-ui
npm run verify:no-python-source
```

`verify:no-python-source` fails if repo-owned `.py`, `.pyi`, or `__pycache__` paths reappear, if CI reintroduces Python setup/test commands, or if top-level docs instruct users or agents to run removed Python compatibility paths. `npm run verify:data-mode` and CI guard that this decommission gate remains wired.

## Future policy

- Do not add Python implementation, tests, local tools, stubs, or placeholder adapters.
- If a future external tool requires Python internally, keep it outside repo-owned source and document it as generated/vendor/toolchain output, not Bitween product code.
- Any missing behavior discovered after decommission must be restored in Rust or TypeScript with Buck2/Node verification, not by reviving Python compatibility code.
