# Production delivery fast path

Status: active delivery contract, 2026-06-09.

This document is the single fast-path spine for shipping Bitween as a
production-grade enterprise B2B SaaS shell. It reconciles current founder
directives, active repo contracts, official cloud/security guidance, and
enterprise patterns from `/Users/jasonlee/Developer/oyatie`. Older documents are
evidence only when they conflict with this contract or newer user directives.

## Non-negotiable product outcome

Bitween must ship as a unified Korean-first enterprise shell where the end-state
pillars are **Office**, **HR**, **Payroll**, and **Archive/Drive**. Each module
must help a real operator complete work end to end:

1. **Office** shows today’s outstanding work, schedules, follow-ups, requests,
   workflow handoffs, and weekly/monthly preparation from the Home, Workflow,
   전자결재, Admin, and Settings surfaces.
2. **HR** owns employee lifecycle work end to end: add, remove, update,
   documents, onboarding/offboarding, and payroll-impact handoff.
3. **Payroll** owns payroll close/run/output work end to end and consumes
   HR/attendance readiness without exposing technical readiness/source details
   to payroll operators.
4. **Workflow** is the visual editable corporate workflow canvas.
5. **전자결재** is only signing, approval, rejection, delegation, and evidence of
   decision.
6. **Archive/Drive (자료함)** accepts any file, stores the original in RustFS,
   treats ZIP as a governed container, stages extracted business data in
   PostgreSQL, raises mapping/anomaly questions for humans, and admits data only
   after review while preserving drive-like metadata, versions, permissions,
   retention, and sharing boundaries.
7. **Admin** handles tenant/security/platform setup.
8. **Settings** is top-bar only and owns language, theme, profile, workspace,
   and accessibility preferences.

Operator screens must not display Rust, Buck2, source-path, schema, backend,
readiness, or “maturity evidence” diagnostics. Those belong in verification,
runbooks, observability, and admin-only operational surfaces.

## Product scale assumption

Bitween is an **internal product operated on managed Kubernetes**. It must be
secure, reliable, auditable, and easy to operate, but it is not an external hyperscale cloud product. Use Oyatie to learn pipeline discipline and product
maturity, not to import public-provider breadth or unnecessary ceremony.

Practical consequences:

- Keep a wave-gated preview → stable → production progression with explicit
  evidence, owner sign-off, rollback, and runbook coverage before promotion.
- Keep CI/CD lanes, local verifiers, source-backed decisions, sensitive-data
  scans, and fail-closed runtime gates as product surfaces.
- Prefer simple managed-Kubernetes topology: ingress/API boundary, Rust
  services/workers, PostgreSQL, RustFS, identity provider integration, secrets,
  observability, and audit events.
- Do avoid public-cloud marketplace, multi-region fan-out, and hyperscaler-maturity claims unless a future internal business requirement
  explicitly needs them and has fresh evidence.
- Avoid silent fallbacks, manual repeatable operations, and direct provider
  lock-in in product code; use adapter seams where external infrastructure
  choices can change.

## Architecture spine

### Runtime

- Kubernetes-native target, concretely a managed-Kubernetes target for Bitween,
  with declarative delivery, immutable images,
  service-level isolation, probes, resource requests, audit events, and rollback
  evidence.
- Rust owns backend domain/API/validation/workflow/integration logic under
  `crates/` and future Rust services.
- TypeScript owns the unified frontend shell under
  `apps/bitween-platform-ui/` and shared contracts under `frontend/`.
- PostgreSQL is the production relational system of record for metadata,
  staging, mappings, review tasks, admitted HR/payroll rows, audit references,
  retention, legal hold, and rollback references.
- RustFS is the production object/blob store for originals, attachments,
  generated evidence, and arbitrary 자료함 objects.
- Python implementation is decommissioned. Missing historical behavior must be
  restored only through Rust/Buck2 backend slices or TypeScript contract gates;
  do not reintroduce legacy compatibility adapters, tests, tools, or live wiring.

### Security

- Authentication is real: configured sign-in, sign-up/access request,
  onboarding, and sign-out route contracts must fail closed when identity
  provider routes are missing.
- JWT verification must validate registered claims and token trust before the
  frontend enters the authenticated shell.
- WebAuthn/passkeys are the preferred phishing-resistant step-up path for
  privileged work.
- Authorization is deny-by-default ABAC + RBAC + PBAC using tenant, legal
  entity, workplace, role, operation, resource type, data classification,
  workflow state, and assurance level.
- Sensitive route authorization must happen before PostgreSQL/RustFS/local
  review side effects.

### Delivery pipeline as product

Every production slice must improve or preserve the build pipeline itself:

- Rust verification uses Buck2 only:
  - `buck2 build //...`
  - `buck2 test //...`
  - target-specific Buck2 `[check]` and `[clippy.txt]` targets for changed Rust
    crates; for example:
    `buck2 build '//crates/payroll-api:payroll_api[check]'`
- Retired Cargo build/check/test/clippy/run/bench/fmt/doc/nextest commands are
  blocked by the PreToolUse guard; only `cargo metadata`, `cargo install`, and
  `cargo vendor` are allowed for Buck/Reindeer inputs.
- TypeScript uses `npm run typecheck`, `npm run verify:i18n`,
  `npm run verify:data-mode`, auth route smoke checks, authorization route smoke
  checks, signed-out auth UX checks, and `npm audit --omit=dev`.
- Static verifiers must reject user-facing technical walls, stub/demo/mock live
  paths, local browser auth, hardcoded visible strings, ad-hoc colors, ad-hoc
  icons, and Python-forward production wiring.
- Friction or repeated failures become verifier checks, runbook items, or
  backlog stories.

## Source-backed constraints

- CNCF defines cloud native around scalable applications in dynamic public,
  private, and hybrid environments using containers, service meshes,
  microservices, immutable infrastructure, and declarative APIs:
  https://github.com/cncf/toc/blob/main/DEFINITION.md
- Kubernetes multi-tenancy guidance highlights SaaS/multi-customer tenancy,
  control-plane/data-plane isolation, namespace scoping, RBAC, quotas, network
  policies, and noisy-neighbor controls:
  https://kubernetes.io/docs/concepts/security/multi-tenancy/
- OWASP ASVS 5.0 provides a measurable basis for testing web application
  security controls and secure-development requirements:
  https://owasp.org/www-project-application-security-verification-standard/
- OpenTelemetry semantic conventions provide common names for traces, metrics,
  logs, profiles, and resources so observability stays portable:
  https://opentelemetry.io/docs/concepts/semantic-conventions/

## Oyatie reference patterns to adopt

Use oyatie as a maturity reference, not a product-scope copy:

- conformance ratchets as product invariants,
- GitOps/IaC discipline with traceable apply evidence,
- tenant/workplace/legal-entity isolation and blast-radius control,
- policy-gated privileged transitions,
- audit-chain evidence packs,
- SLO-gated promotion,
- runbook and ownership catalogs,
- drift detection,
- performance baselines tied to repeatable workloads and failure modes,
- release-readiness checklists and wave gates sized for an internal product,
- clear anti-pattern tracking for silent fallback, manual repeatable operations,
  unsupported maturity claims, and provider lock-in.

Oyatie patterns to downscope for Bitween:

- public cloud/IaaS marketplace surfaces,
- external developer marketplace and public-provider billing breadth,
- global region fan-out or cell rebalancing as a day-one concern,
- hyperscaler-maturity marketing claims,
- consumer/public SaaS launch ceremony that does not improve internal payroll,
  HR, archive, approval, workflow, or admin operations.

## Executable shipping lanes

### Lane 1 — shell usefulness and UX quality

Acceptance:

- Home, HR, Payroll, Workflow, Approval, Archive, Admin, Settings render
  distinct workflow surfaces.
- Settings is not in left navigation; top bar has notifications, messages,
  contextual help, settings, profile, and sign-out.
- Visible copy is catalog-backed and Korean-first.
- Localization is context-aware, not direct translation: Korean operator copy
  must use culturally natural business terms such as `업무 관리` for the workflow
  module, `인사` for HR, `급여` for payroll, `전자결재` for approvals, and
  `자료함` for archive/intake.
- Operators see business work, owner, due window, blockers, and next action —
  not technical readiness/source diagnostics.
- Workflow canvas visualizes editable corporate logic and remains separate from
  approval signing. It must support moving/reorganizing steps, multi-edge
  rewiring, saved customization, SLO targets, escalation roles, branch conditions, permission/access scope, graph analytics, and runtime action execution;
  decorative-only connectors or static numbered cards are not acceptable. Runtime
  execution must produce auditable business operation evidence and persisted
  workflow data-record updates, not just visual status changes.

### Lane 2 — Rust service and contract spine

Acceptance:

- Platform view-model, HR, payroll, workflow, approval, archive, settings,
  auth/session, and admin contracts use stable DTO names.
- Live preview/server adapters call Buck2 Rust targets for business decisions
  and fail closed when production backing services are unavailable.
- Workflow graph contracts include versioned templates, nodes, edges,
  publication checks, runtime instances, SLO/escalation metadata, graph
  analytics, runtime execution events, scoped data-operation outcomes, persisted
  workflow data records, SLO/escalation/condition/permission validation, and audit events before production workflow writes are
  enabled.
- Workflow editor UX must stay production-grade: palette-based step creation,
  click-to-connect/rewire handles, persisted disconnect controls, auto-arrange,
  SLO/escalation/condition/permission editing, graph analytics, and selected-step inspection must remain live-wired through
  Rust routes rather than decorative canvas elements.
- No new Rust implementation is added.

### Lane 3 — PostgreSQL and RustFS production persistence

Acceptance:

- PostgreSQL migrations define metadata/staging/review/admission/audit schemas
  before write paths are enabled.
- PostgreSQL workflow migrations define editable corporate workflow templates,
  graph nodes/edges, publish gates, runtime instances, audit events, and tenant
  row-level security before workflow writes are promoted from hermetic local
  review.
- RustFS object lifecycle records checksum, tenant, sensitivity, quarantine,
  review, admission, rollback, retention, and legal-hold facts.
- Local file stores are explicitly hermetic review scaffolding only behind
  `BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true`.

### Lane 4 — auth, session, and authorization hardening

Acceptance:

- Auth routes are configured route contracts, not fake browser sessions.
- JWT/WebAuthn session facts gate app entry.
- ABAC + RBAC + PBAC gates protect HR, payroll, approval, archive, settings,
  admin, and export operations before side effects.
- Security headers, sensitive-data redaction, no-secrets checks, audit events,
  and denial UX are covered by verifiers.

### Lane 5 — 자료함 intake and human-guided admission

Acceptance:

- Any file can be uploaded.
- Original bytes are stored in RustFS first.
- Extracted Excel/CSV/HR/payroll samples are staged in PostgreSQL.
- Missing data, anomalies, ambiguous columns/rows, and likely faulty inputs
  become assigned human guidance tasks.
- Admission is reviewed, auditable, reversible, and tenant-scoped.

### Lane 6 — cloud-native operations

Acceptance:

- Deployment artifacts are declarative/GitOps-ready for the managed-Kubernetes
  environment Bitween actually runs on.
- Services expose liveness/readiness, structured logs, audit events, and
  OpenTelemetry-aligned attributes.
- Multi-tenant isolation is documented across namespace/network/storage/app
  policy and app-level tenant/legal-entity/workplace boundaries.
- SLOs, runbooks, rollback, and drift/conformance gates exist before production
  promotion.
- Public-cloud marketplace, global multi-region expansion, and hyperscaler
  maturity claims remain explicitly out of scope for the current internal
  product path.

### Lane 7 — Python decommission after product maturity

Acceptance:

- legacy compatibility slices have been removed after product workflow and Rust
  parity gates went green.
- Production paths do not import or execute Python.
- Final state has no repo-owned Python source left and is enforced by
  `npm run verify:no-python-source`.

## Stop condition for the fast path

The fast path is shippable only when the unified shell is role-useful, the
critical write paths are live-wired through Rust with PostgreSQL/RustFS-backed
contracts, auth/session/authorization gates fail closed, cloud-native operations
are declared and verifiable, and Buck2/frontend/security checks pass without
stub/demo/mock exceptions.
