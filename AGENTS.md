# AGENTS.md

Guidance for Codex and other coding agents working in this repository.

## Project Direction

Bitween is a payroll-first business platform. The current desktop app is Python
and Tkinter, while backend domain logic is moving toward idiomatic Rust and
frontend work can use TypeScript.

Keep the transition incremental:

- Python desktop compatibility stays intact unless the task explicitly removes it.
- Rust backend work belongs under `crates/`.
- TypeScript frontend work belongs under `frontend/`.
- Shared request and response contracts should keep stable field names across
  Python, Rust, and TypeScript.

## Scope Boundaries

Prefer narrow changes over broad rewrites.

- Payroll automation backend: `services/payroll_automation.py`,
  `services/payroll_api_adapter.py`, `services/payroll_api_contract.py`,
  `services/payroll_policy_store.py`, `core/payroll/`, and `crates/`.
- Frontend TypeScript: `frontend/`.
- Desktop UI: `ui/`, `app_ui.py`, and Tkinter bridge modules.
- Tests: keep Python tests in `tests/`; keep Rust tests in the relevant crate;
  keep TypeScript type checks under `frontend/`.

Do not mix unrelated backend, frontend, documentation, and workflow changes in
one PR unless the change is a small contract update that requires all of them.

## Atomic Commits

Each commit should represent one reviewable idea.

- One behavior change, one contract change, one test update, or one documentation
  update per commit.
- Include tests in the same commit as the behavior they verify.
- Keep generated files, local runtime data, and formatting-only churn out of
  feature commits.
- Use clear commit messages such as `Add payroll validation response contract`
  or `Add Rust payroll API request parser`.

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

Python:

```powershell
python -m unittest tests.test_payroll_api_adapter tests.test_payroll_api_contract -v
```

Focused payroll suite:

```powershell
python -m unittest tests.test_attendance_import tests.test_payroll_api_adapter tests.test_payroll_api_contract tests.test_payroll_automation tests.test_payroll_operation_policy tests.test_payroll_readiness tests.test_payroll_ui_bridge tests.test_payroll_settings_ui_bridge tests.test_preview_grid_filter tests.test_workflow tests.test_org_access -v
```

Rust:

```powershell
cargo test --workspace
```

TypeScript:

```powershell
cd frontend
npm install
npm run typecheck
```

## Data Safety

Never commit payroll outputs, employee rosters, tenant runtime data, API keys,
cookies, passwords, or local session files. Check `.gitignore` before adding new
runtime folders.
