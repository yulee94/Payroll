# AGENTS.md

Guidance for Codex and other coding agents working in this repository.

## Project Direction

Bitween is a payroll-first business platform whose **production target is a
Kubernetes-native stack**:

- Backend domain, API, validation, workflow, and integration logic moves to
  idiomatic Rust under `crates/` and future Rust service crates.
- Frontend work is TypeScript-first under `apps/bitween-platform-ui/` and
  `frontend/`.
- Existing Python modules are compatibility adapters, characterization sources,
  migration fixtures, or local tooling until each backend slice is rewritten in
  Rust. Do not document compatibility adapters as the user-facing client.
- Deployment assumptions belong in `docs/KUBERNETES_NATIVE_STACK.md`; API and
  DTO assumptions belong in the relevant contract docs.

Keep the transition incremental and production-safe:

- Preserve legacy compatibility behavior until the Rust replacement has parity
  tests and an explicit decommission step.
- Use stable field names across Rust services and TypeScript contracts.
- Prefer vertical slices that can be tested, reviewed, and reverted.
- Do not add a new runtime dependency without a source-backed decision record.

## Scope Boundaries

Prefer narrow changes over broad rewrites.

- Rust backend: `crates/` plus future service crates for workflow, payroll,
  tenant/org, KPI, mobile attendance, and integrations.
- TypeScript frontend: `apps/bitween-platform-ui/` and `frontend/`.
- Compatibility adapters and characterization sources: `services/`, `core/`,
  existing Python entrypoints, and tests that lock current behavior before Rust
  migration.
- Tests: keep Rust tests in the relevant crate; keep TypeScript type checks under
  `frontend/` or `apps/bitween-platform-ui/`; keep compatibility/characterization
  tests in `tests/` until the covered behavior is migrated.

Do not mix unrelated backend, frontend, documentation, and workflow changes in
one PR unless the change is a small contract update that requires all of them.

## Atomic Commits

Each commit should represent one reviewable idea.

- One behavior change, one contract change, one test update, or one documentation
  update per commit.
- Include tests in the same commit as the behavior they verify.
- Keep generated files, local runtime data, and formatting-only churn out of
  feature commits.
- Commit messages must follow the Lore protocol from the top-level orchestration
  instructions.

## Scoped Pull Requests

Each PR should be easy to review and safe to merge.

- Base PRs on `main` unless the work is intentionally stacked.
- If stacked, name the dependency in the PR body and keep the dependent PR draft
  until its base PR is merged.
- Keep PR titles literal and narrow.
- Put backend, frontend, and documentation-only work in separate PRs when they
  can be reviewed independently.
- Avoid using a PR as a parking lot for ongoing work.

## Validation

Run the smallest relevant test set first.

Rust:

```powershell
cargo test --workspace
```

TypeScript contracts/frontends:

```powershell
cd frontend
npm install
npm run typecheck

cd ../apps/bitween-platform-ui
npm install
npm run typecheck
```

Compatibility characterization tests:

```powershell
python -m unittest tests.test_payroll_api_adapter tests.test_payroll_api_contract -v
python -m unittest tests.test_attendance_import tests.test_payroll_api_adapter tests.test_payroll_api_contract tests.test_payroll_automation tests.test_payroll_operation_policy tests.test_payroll_readiness tests.test_payroll_ui_bridge tests.test_payroll_settings_ui_bridge tests.test_preview_grid_filter tests.test_workflow tests.test_org_access -v
```

## Data Safety

Never commit payroll outputs, employee rosters, tenant runtime data, API keys,
cookies, passwords, or local session files. Check `.gitignore` before adding new
runtime folders.
