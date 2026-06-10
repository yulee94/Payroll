# Design

## Source of truth
- Status: Active production build contract
- Last refreshed: 2026-06-09
- Primary product surfaces: Bitween enterprise payroll platform shell, operator home cockpit, HR employee management, payroll close workflow, workflow canvas, 자료함 intake/export workbench, admin/settings support surfaces, Rust-owned live runtime.
- Evidence reviewed:
  - `README.md`
  - `docs/FRONTEND_UI_GUIDE.md`
  - `apps/bitween-platform-ui/README.md`
  - `apps/bitween-platform-ui/docs/ui-review-checklist.md`
  - `apps/bitween-platform-ui/docs/backend-contract-requests.md`
  - `apps/bitween-platform-ui/App.tsx`
  - `apps/bitween-platform-ui/src/components.tsx`
  - `apps/bitween-platform-ui/src/screens.tsx`
  - `apps/bitween-platform-ui/src/data.ts`
  - `apps/bitween-platform-ui/src/viewModel.ts`
  - `apps/bitween-platform-ui/preview/*`
  - `crates/payroll-api/src/platform_view.rs` (Rust-owned live readiness source)
  - `crates/payroll-api/src/api_contract.rs`
  - `crates/payroll-api/src/service.rs`
  - `crates/payroll-api/src/execution_plan.rs`
  - oyatie reference: `docs/PRD.md`, `docs/PRD-OYATIE-FROM-SCRATCH-CANONICAL.md`, `docs/user-stories/b2b-work-surfaces.md`, `docs/gtm/tenant-prospect-to-active-stages.md`, `docs/decisions/ADR-0061-application-b2b-unified-shell.md`, `docs/decisions/ADR-0190-scim-2-provisioning-enterprise-tenants.md`, `docs/architecture/enterprise-software-coverage-matrix-2026-05-21.md`.
  - oyatie operating-bar reference: `docs/SLO-CATALOG.md`, `docs/QA-TEST-STRATEGY.md`, `docs/RELEASE-MANAGEMENT.md`, `docs/RACI-OWNERSHIP.md`, `docs/COMPLIANCE-MATRIX.md`, `docs/SECURITY-PROGRAM.md`, `docs/RUNBOOKS-INDEX.md`.
  - 자료함 cloud-native intake benchmark: `docs/ARCHIVE_INTAKE_CLOUD_NATIVE.md`.

## Brand
- Personality: calm, precise, accountable, enterprise-ready, Korean SME payroll-first.
- Trust signals: tenant/legal-entity scope, owner/action/status clarity, workflow state, audit trail language, permission boundaries, secure sensitive-data handling.
- Avoid: decorative dashboards, fake productivity metrics, dead buttons, demo account copy in production paths, mixed-language UI, unbacked legal advice, vendor-suite mimicry without Bitween purpose.

## Product goals
- Goals:
  - Make today’s outstanding work, schedule, follow-ups, and weekly/monthly preparation obvious within 10 seconds.
      - Show the next safe action for each role: HR manages employees and source inputs, payroll runs the close workflow, approvers review decisions, 자료함 stores files, translates business data, routes exceptions, and preserves evidence, admin fixes setup blockers.
  - Replace mock-only data with read-only live outputs from Rust-owned contract boundaries.
  - Preserve production direction: Rust backend contracts plus TypeScript frontend. Repo-owned Python is decommissioned; missing historical behavior must return through Rust/Buck2 services or TypeScript contracts only.
- Non-goals:
  - No static demo/prototype as the main product path.
  - No payroll/tax formula rewrites from UI work.
  - No invented backend data to make screens look full.
  - No new runtime dependency without a decision record.
- Success signals:
  - Startup path is live-wired and does not rely on demo/mock/stub data.
  - Operator screens hide Rust/source/readiness internals and show role-relevant work only.
  - Numbered stub-like workflow cards never ship; cards must represent real role work, owners, actions, and business state.
  - Top bar exposes notifications, messages, `?` guided walkthrough, settings, profile, and sign-out.
  - UI actions either hit Rust/Buck2-backed local endpoints or fail closed with evidence.
  - Tests fail if the production path imports hardcoded preview account data, shows technical walls to operators, or introduces non-Rust backend wiring.

## Enterprise maturity contract
- Product bar: SAP-grade maturity means each visible surface must prove tenant boundary, permission boundary, workflow/owner loop, compliance/evidence posture, support path, and source-checkable contract evidence without exposing implementation details to non-technical operators.
- Oyatie reference applied to Bitween:
  - One B2B entry shell, not fragmented product portals.
  - Internal product assumption: Bitween runs on managed Kubernetes and should
    adopt Oyatie's pipeline/product discipline without importing external
    hyperscale cloud-provider scope.
  - Tenant/legal-entity/workplace/period scope is mandatory context for payroll actions.
  - Product surfaces must be discovered/rendered from live capability or readiness manifests; do not hardcode surface sprawl to make the UI feel complete.
  - Workflow and ontology are the cross-surface substrates: payroll blockers become owner-assigned, replayable work; payroll objects need stable tenant-filtered contracts.
  - Audit/evidence completeness is part of the product, not a back-office afterthought.
- Oyatie patterns to adapt, not copy:
  - Keep wave-gated preview → stable → production promotion, release evidence,
    runbooks, rollback, sensitive-data scans, and verifier-backed CI lanes.
  - Downscope public-cloud marketplace, external developer ecosystem,
    multi-region fan-out, global cell rebalancing, and hyperscaler-maturity
    claims until there is a Bitween-specific internal operating need.
- Capability-tier checklist for every production surface:
  1. Permit set.
  2. Ontology projection.
  3. Workflow template.
  4. UX shell manifest.
  5. Compliance pack overlay.
  6. Observability and audit stream.
  7. FinOps cost dimension.
  8. Migration/import declaration.
  9. Support runbook reference.
- Current priority: the Rust live view-model must expose workflow state and owner/action boundaries so the UI can show what is due today, blocked, waiting, completed, and owner-owned without invented data.
- Future-work placement: import/parity gaps stay governed backlog lanes, but repo-owned Python remains decommissioned and cannot return as an implementation path.

## Personas and jobs
- Primary personas:
  - Finance operator: runs/validates monthly payroll, needs close workflow state, warnings, output evidence, and accounting handoff state.
  - HR operator/admin: adds/removes/manages employees, employment status, roster, leave, onboarding/offboarding, and HR source inputs that feed payroll.
  - Executive/branch manager: reviews readiness risk, exceptions, overdue approvals, and audit posture.
  - Worker/mobile employee: sees attendance, leave, pay/self-service status through restricted role surfaces.
  - IT/security admin: manages tenant, roles, SSO/provisioning readiness, and audit/compliance evidence.
- User jobs:
  - “What work must I finish today, this week, and this month?”
  - “Can we run payroll for this legal entity/site/period?”
  - “What blocks payroll and who owns the fix?”
  - “Which employee, HR, or attendance inputs affect payroll?”
  - “Which files need to be archived, translated to Bitween-native data, validated, admitted to PostgreSQL, exported, or kept as evidence?”
  - “Which approvals, attendance exceptions, and roster gaps must be resolved?”
  - “Can this user/tenant perform this action?”
- Key contexts of use: month-end close, payroll exception triage, HR onboarding/offboarding, employee management, attendance corrections, Excel/CSV intake, Korean labor/social-insurance readiness, executive risk review, legacy characterization-to-Rust migration verification.

## Information architecture
- Primary navigation:
  - Home: operator cockpit for today’s work, schedule, follow-ups, and weekly/monthly preparation.
  - HR: employee add/remove/manage, lifecycle status, HR workflows, and source inputs feeding payroll.
  - Payroll: period/scope → payroll close steps → calculation/validation → output handoff.
  - Workflow: separate corporate logic/canvas/editor surface for HR → Payroll → Archive routing, ownership, branch wiring, analytics, runtime actions, and state edits.
  - 전자결재/Approval: signing/approval only; it does not own workflow design, routing logic, or canvas editing.
  - Archive/자료함: any-file archive, RustFS object/blob storage for all files/originals/attachments/blobs, HR/payroll data translation, validation, exception review, PostgreSQL admission, output/evidence storage.
  - Admin: tenant/legal entity/site policy, permissions, setup blockers.
  - Settings: theme, Korean-first language controls, workspace/session preferences.
- Core routes/screens:
  - Live runtime sign-in/session state.
  - Payroll operations cockpit.
  - HR employee management panel.
  - Workflow canvas, graph analytics, runtime execution controls, and selected-step panel.
  - 자료함 intake/export panel.
  - Scope/period selector.
  - Audit/evidence list.
- Content hierarchy:
  1. Current work and schedule relevance.
  2. Owner/action/status for the selected workflow step.
  3. Tenant/scope/period only where it affects the action.
  4. Supporting outputs, audit details, or diagnostics only in the role-appropriate surface.

## Design principles
- Principle 1: Every screen must answer “what is this for?” and “what should I do next?” before showing secondary analytics.
- Principle 2: Live truth beats visual fullness. Empty/degraded states are valid production states when data is missing; do not fill screens with generic text.
- Principle 3: Payroll is evidence-gated. Execution and outputs must show status, owner, and audit/evidence implications; implementation source stays in automated verification/docs.
- Principle 4: Tenant/legal-entity/site scoping is visible at the point of action.
- Principle 5: Capability-tier composition over suite clutter. Surfaces compose HR, workflow, archive, admin, and payroll jobs without copying Workday/SAP navigation wholesale.
- Principle 6: Onboarding must be interactive and contextual. The `?` button opens a current-screen walkthrough instead of permanent instructional clutter.
- Principle 7: Enterprise operating evidence is UI content only where it helps the role complete work. SLO, runbook, compliance, owner, and audit status should be visible near the action they govern or in diagnostics.
- Tradeoffs: Dense B2B data is acceptable when headers, grouping, and next actions remain scannable; avoid consumer-style empty cards that hide operational state.

## Visual language
- Color: restrained navy/steel base, semantic green/amber/red for readiness; color never carries state alone.
- Typography: system sans, strong section titles, compact helper text, tabular numeric treatment where possible.
- Spacing/layout rhythm: 8px base rhythm, denser tables for desktop, card summaries for mobile.
- Layout quality gate: choose horizontal flow for process/canvas relationships, vertical lists for actionable queues, two-column bento rhythm for home cockpit, and avoid uniform card grids when hierarchy requires emphasis.
- Shape/radius/elevation: low-radius, low-shadow enterprise cards; borders over heavy elevation.
- Motion: minimal; respect reduced motion; use state changes rather than decorative animation.
- Imagery/iconography: no decorative hero art on production screens; icons only clarify actions/status.

## Components
- Existing components to reuse: `AppShell`, `Sidebar`, `SectionHeader`, `Card`, `Badge`, `ActionButton`, `MetricGrid`, `DataTable`, `EmptyState`, `FilterBar`.
- New/changed components:
  - Topbar action cluster with notifications, messages, help, settings, profile/sign-out.
  - Operator home cockpit buckets.
  - HR employee management table/form/detail.
  - Editable workflow canvas with drag/move positioning, palette-based step creation, click-to-connect and disconnect controls, auto-arrange, multi-edge rewiring, SLO targets, escalation roles, branch conditions, permission/access scope, graph analytics, scoped runtime action execution, data-operation evidence, persisted data-record updates, and selected-step inspector.
  - 자료함 import/export/intake workbench.
  - Settings workspace preference panel.
- Variants and states:
  - ready, pending/degraded, attention, blocked/error.
  - live, unavailable, unauthorized, loading, empty, contract-missing.
  - primary action, secondary navigation, disabled with reason.
- Token/component ownership: extend `src/theme.ts` and existing component primitives before adding new design-system layers.

## Accessibility
- Target standard: WCAG 2.2 AA for production UI decisions.
- Keyboard/focus behavior: all actionable rows/buttons reachable and visibly focused; no hover-only controls.
- Contrast/readability: status badges meet contrast targets; dense tables remain readable at 100% zoom and high contrast mode.
- Screen-reader semantics: sections have meaningful headings; badges include state text; disabled actions include reason text.
- Reduced motion and sensory considerations: avoid animated dashboards; no flashing or auto-advancing content.

## Responsive behavior
- Supported breakpoints/devices: 360px worker/mobile width, 768px tablet, 1186px+ desktop operations cockpit.
- Layout adaptations:
  - Desktop: side nav + cockpit grid + detail panel.
  - Tablet: compact nav + stacked work queues.
  - Mobile: task-first cards and large tap targets.
- Touch/hover differences: all hover affordances must have touch-visible equivalents.

## Interaction states
- Loading: show role-appropriate loading state; technical endpoint details belong in automated verification/docs.
- Empty: state the source checked and next setup step.
- Error: show recoverable message and owner/path where safe; implementation source belongs in automated verification/docs.
- Success: include evidence/source and timestamp when available.
- Disabled: explain missing permission, missing backend contract, or missing data prerequisite.
- Offline/slow network: preserve last known read-only state only when explicitly timestamped; do not imply freshness.

## Content voice
- Tone: direct, operational, respectful; no marketing filler inside work surfaces.
- Terminology:
  - “Live workflow” means data came from a Rust service/contract boundary.
  - “Demo” is reserved for explicit demo-only scripts and must not appear in production startup copy.
  - Use tenant, legal entity, workplace/site, payroll period, readiness, blocker, evidence, audit trail consistently.
- Microcopy rules:
  - Buttons use verbs tied to actual behavior.
  - If an action is not wired, do not render it as an enabled button.
  - Errors name what failed and what can be done next.
  - No generic “today/work/status at a glance” filler. The home cockpit must show concrete work, schedule, follow-ups, and upcoming preparation.

## Implementation constraints
- Framework/styling system: React Native/Expo TypeScript app and dependency-free static preview for no-install browser review; production logic must be shared via Rust-generated/read-only JSON contracts where possible.
- Design-token constraints: use `src/theme.ts` tokens and preview CSS variables consistently. The palette is Pantone-based: Cloud Dancer-style neutral surfaces plus Marina/Alexandrite/Burnt Sienna/Amaranth-inspired operational accents adjusted for enterprise contrast. Navigation accents, status/tone colors, translucent surfaces, and preview runtime colors must be drawn from palette tokens; do not add ad-hoc hex or rgba values in data/components/preview JS or CSS component rules.
- Performance constraints: production cockpit should be useful after first payload; static local preview should remain dependency-free.
- Backend constraints: default backend is Rust; PostgreSQL is the production relational system of record for metadata, staging, review, and admitted business data. Do not add new Python implementation or Python-backed live wiring. Local file-backed review adapters are disabled by default, require `BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true` for hermetic review, and must migrate to Rust/PostgreSQL before production write paths.
- 자료함 persistence constraints: all files/originals/attachments/blobs go to self-hosted RustFS; metadata, mappings, review tasks, staging rows, admission audit, and canonical HR/payroll rows go to self-hosted PostgreSQL. Unknown or non-tabular files may remain archive blobs; HR/payroll/tabular files require review before canonical relational admission.
- Security constraints: production auth must use JWT/session hardening, WebAuthn/passkeys, tenant-scoped authorization, hardened HTTP response headers/CSP, secure handling of sensitive employee/payroll data, no secrets or payroll/personnel exports in git, encryption in transit/at rest, retention/deletion controls, and auditable access. Keep the operative contract in `docs/AUTH_SECURITY_CONTRACT.md`.
- Auth UX constraint: never locally mark a session authenticated from the browser. The shell enters authenticated screens only when the Rust live session reports provider configuration, verified JWT registered-claim facts, future expiration, and WebAuthn/passkey user verification. Sign-in, access request, onboarding, and sign-out buttons only start configured provider routes and fail closed if those routes are missing.
- Settings UX constraint: Settings is opened from the top bar/settings affordance, not the left navigation. Theme/color selection belongs only in Settings, not in the sidebar. Preference changes must persist through a live Rust-backed preference endpoint or fail visibly; do not silently change browser-only state.
- Payroll UX constraint: payroll operators see current payroll work, owners, due windows, blockers, and next actions. Do not expose technical readiness cards/detail panels, backend diagnostics, or numbered sequence-card placeholders in operator payroll/workflow surfaces.
- Workflow execution constraint: workflow wiring must perform audited business operations, not only redraw connectors or toggle status. The current live Rust store records scoped operation evidence and upserts workflow data records for payroll calculation planning, approval packet generation, payout preparation, and archive admission; production promotion requires those records to become PostgreSQL/RustFS-backed mutations with rollback evidence.
- Test/screenshot expectations:
  - `npm run verify:i18n`
  - `npm run verify:data-mode`
  - `npm run check:strict-config`
  - `node --check preview/app.js`
  - Rust tests covering live payload generation.
  - No-production-Python/no-stub static checks for UI/server wiring.
  - Static checks that operator screens do not render Rust/source/readiness/maturity walls.

## Open questions
- [ ] Production API transport: choose Rust HTTP service framework and deployment surface when service images are ready; current local live wiring uses the Buck2 `//crates/payroll-api:platform_live_view` target without introducing new dependencies.
- [ ] Auth/SSO production provider: align with enterprise SSO/SCIM plan before real tenant login replaces local session display.
- [ ] Source of legal/labor-law content: define source-of-truth documents and effective-date policy before rendering compliance guidance as advice.
- [ ] Production runbooks/SLO rows: define payroll-specific SLO, support, incident, and release gates before enabling write-path payroll execution.
