# AGENTS.md

Guidance for Codex and other coding agents working in this repository.

## Project Direction

Bitween is a payroll-first business platform whose **production target is a
Kubernetes-native stack**:

- Backend domain, API, validation, workflow, and integration logic moves to
  idiomatic Rust under `crates/` and future Rust service crates.
- Frontend work is TypeScript-first under `apps/bitween-platform-ui/` and
  `frontend/`.
- Python implementation has been decommissioned. Do not add new Python source,
  stubs, tests, scripts, or live wiring. Historical behavior is preserved by
  Rust Buck2 tests and TypeScript contract gates.
- Deployment assumptions belong in `docs/KUBERNETES_NATIVE_STACK.md`; API and
  DTO assumptions belong in the relevant contract docs.

Keep the transition incremental and production-safe:

- Preserve legacy behavior through Rust parity tests and explicit contract
  fixtures; do not reintroduce Python compatibility adapters.
- Use stable field names across Rust services and TypeScript contracts.
- Prefer vertical slices that can be tested, reviewed, and reverted.
- Do not add a new runtime dependency without a source-backed decision record.

## Scope Boundaries

Prefer narrow changes over broad rewrites.

- Rust backend: `crates/` plus future service crates for workflow, payroll,
  tenant/org, KPI, mobile attendance, and integrations.
- TypeScript frontend: `apps/bitween-platform-ui/` and `frontend/`.
- Tests: keep Rust tests in the relevant crate; keep TypeScript type checks under
  `frontend/` or `apps/bitween-platform-ui/`; Python tests are retired.

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
buck2 build //...
buck2 test //...
buck2 build '//crates/payroll-api:payroll_api[check]' '//crates/workflow-core:workflow_core[check]'
buck2 build '//crates/payroll-api:payroll_api[clippy.txt]'
```

`cargo build`, `cargo check`, `cargo test`, `cargo clippy`, `cargo run`, and
`cargo bench` are retired for this repository. Use Buck2 for build/check/test
verification. Use target-specific Buck2 `[check]` and `[clippy.txt]` targets
for changed Rust crates; do not use unsupported recursive provider shortcuts for
check/clippy. `cargo metadata`, `cargo install`, and `cargo vendor` remain
allowed only for Buck/Reindeer inputs.

TypeScript contracts/frontends:

```powershell
cd frontend
npm install
npm run typecheck

cd ../apps/bitween-platform-ui
npm install
npm run typecheck
```

Python decommission gate:

```powershell
cd apps/bitween-platform-ui
npm run verify:no-python-source
```

## Data Safety

Never commit payroll outputs, employee rosters, tenant runtime data, API keys,
cookies, passwords, or local session files. Check `.gitignore` before adding new
runtime folders.
