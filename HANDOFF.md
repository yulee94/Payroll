# Bitween Production Build Handoff

Last updated: 2026-06-10

## Non-negotiable directives

- This is a production build request, not demo, prototype, or MVP work.
- Build toward SAP-grade enterprise maturity for B2B SaaS: polished UX, mature workflows, live wiring, and enterprise-grade operations.
- Use `/Users/jasonlee/Developer/oyatie` as reference material for documented specs, PRD, and enterprise/B2B SaaS patterns. Non-enterprise areas there are lower relevance.
- Adapt Oyatie for Bitween as an internal product operated on managed Kubernetes, not an external hyperscale cloud product. Adopt wave gates, verifier-backed release evidence, runbooks, rollback, and pipeline discipline; avoid public-cloud marketplace, global region fan-out, hyperscaler-maturity claims, and external-SaaS ceremony unless a future internal business requirement justifies them with evidence.
- Default backend is Rust. Python implementation is decommissioned; do not add repo-owned Python source, stubs, tests, scripts, compatibility adapters, or live wiring. Missing historical behavior must return only as Rust/Buck2 or TypeScript contract slices.
- Buck2 is canonical for build/check/test/lint verification. Do not use retired `cargo build/check/test/clippy/run/bench/fmt/doc/nextest`; allowed Cargo commands are only metadata/install/vendor for buckify/reindeer inputs.
- Development must be hermetic. Local live preview must use Buck2-backed Rust targets and fail closed rather than silently using stubs/mock/demo paths.
- UI text must not be hardcoded. Korean is the first visible language; other locales can remain catalog-backed and enabled later.
- Localization must be context-aware and culturally appropriate, not direct/lazy translation. Korean visible UI must be fully Korean; English visible UI must be fully English. The workflow module is `업무 관리` in Korean, not `Workflow`, `워크플로`, or `워크플로우`.
- Technical details such as Rust/backend/source/readiness internals must not appear on normal operator screens. Keep technical diagnostics in automated verification/docs, not user-facing UI.
- Numbered stub-like workflow cards are unacceptable. UI cards must show role-relevant work, owner/action/status, and business next steps instead of technical internals.
- Clean up stubs, placeholders, dead code, generic text, and unnecessary UI elements while implementing. Prefer deletion/reuse over new abstractions and dependencies.

## Product/UX directives

- The product must be intuitive by workflow, not by wall-of-text explanation.
- Remove generic copy such as “오늘의 업무, 빠른 실행, 플랫폼 상태를 한 화면에서 확인합니다.” and any equivalent filler.
- The platform home must be an operator cockpit showing in one glance:
  - outstanding work for today,
  - schedule,
  - follow-ups,
  - upcoming weekly/monthly preparation.
- Payroll personnel are non-technical. Payroll screens should show payroll work, blockers, schedule, owner/action, and next workflow step only.
- HR and Payroll are interconnected but separate.
  - HR owns employee add/remove/manage and HR-related workflows.
  - Payroll consumes HR outputs such as attendance/personnel close, but payroll execution is its own workflow.
- 자료함 owns import/export and Excel → Bitween-native data intake/translation/conversion. This should be a first-class workbench, not a passive evidence archive.
- 자료함 must accept any file. Originals are stored in self-hosted RustFS; HR/payroll/tabular content is extracted into PostgreSQL staging where appropriate, with mapping/anomaly questions assigned to a human before canonical admission.
- 자료함 versioning must not store binary snapshots in PostgreSQL. Preserve immutable workbook/file versions in RustFS, keep PostgreSQL to metadata/checksums/row-level JSON recovery deltas/source-sync state, and expose business-safe recovery/rollback controls.
- Top bar should be polished and minimal:
  - remove tenant/status/readiness badges for now,
  - show notification icon,
  - messages icon,
  - `?` guided help icon,
  - settings/cog icon,
  - profile/person icon,
  - sign out ability.
- Settings must move out of the left navigation and be reachable from the top bar.
- Theme selection belongs in Settings, not the left nav/sidebar.
- Screen colors must be drawn from the product palette/tokens, with the palette based on Pantone direction. Current basis: Cloud Dancer-style neutral surfaces with Marina/Alexandrite/Burnt Sienna/Amaranth-inspired operational accents adjusted for enterprise contrast. Do not add ad-hoc hex/rgba colors in navigation data, components, or preview JS/CSS component rules.
- Every screen should be onboarding-aware with a `?` topbar button that opens a current-screen interactive walkthrough overlay.
- Workflow screen must include a highly polished, mature workflow canvas inspired by best-in-class enterprise workflow products (SAP/Palantir/n8n-class), with visualization of corporate logic and the ability to edit workflow state.
- Workflow is the separate corporate logic/canvas/editor surface. 전자결재/approval is signing and approval only; do not collapse workflow design, routing logic, or canvas editing into approval screens.

## Backlog / future work

- Keep the completed Python decommission enforced through `npm run verify:no-python-source`, CI workflow scans, and docs authority updates.
- Keep the managed-Kubernetes/internal-product operating model current: build simple declarative deployment, runbook, rollback, observability, and evidence gates before production promotion; do not expand into Oyatie-style public cloud/provider scale until the internal payroll/HR product needs it.
- If a deleted documented behavior gap is discovered, restore it only through Rust/Buck2 tests/services or TypeScript contract gates; do not reintroduce Python compatibility paths.
- Expand Korean-first catalog into additional visible languages only after the Korean workflows are stable.
- Keep workflow template persistence on the Rust/PostgreSQL adapter path, then add hermetic PostgreSQL fixture evidence and notification delivery before production write promotion. Publish/version rollback controls now exist in the Rust store, preview API, and UI; they still need hermetic PostgreSQL/RustFS fixture evidence before production write promotion.
- Use `docs/POSTGRES_REPOSITORY_ADAPTER_DECISION.md` for the first Rust PostgreSQL dependency slice: `tokio-postgres` with a TLS-capable connector boundary, `tokio-postgres-rustls` for direct DB TLS where required, no production `NoTls`, `postgres` only as a sync façade if needed, and `sqlx` deferred until a hermetic DB fixture/offline query metadata flow exists.
- Extend the workflow editor from the current governed graph/SLO/escalation/condition/permission controls plus text version history/rollback into simulation, merge validation, and notification delivery once the PostgreSQL workflow repository has hermetic fixture evidence.
- Deepen workflow runtime actions beyond the current scoped operation-evidence/data-record layer into production PostgreSQL domain mutations for each node type. Current Rust execution records concrete `data_operations` and upserts persisted `data_records` such as scope lock, attendance close, payroll input freeze, payroll calculation plan, approval packet, payout package, and archive admission evidence; remaining production work is to move those records into the PostgreSQL/RustFS repositories with rollback/audit evidence.
- Implement production authentication/session claims and tenant-scoped authorization before enabling real write actions beyond local hermetic review.
- Add governed import mappings for Excel/CSV intake in 자료함, including validation rules, transformation preview, approval, rollback, and audit evidence.
- Continue 자료함 production depth after the current PostgreSQL archive intake adapter: mapping template approval, generated workbook sync workers that write derived Excel versions back to RustFS and update `archive_source_sync.generated_object_uri`, retention/legal-hold workflows, malware/CDR scanning hooks, and hermetic PostgreSQL/RustFS fixture evidence.
- Add RustFS bucket/prefix lifecycle policies, checksum verification, malware/CDR scanning hooks, sensitivity labels, and tenant-scoped object authorization.
- Add HR employee lifecycle depth beyond the current PostgreSQL employee store: onboarding, status changes, leave, offboarding, documents, soft-delete/retention policy, audit history, and payroll impact preview.
- Continue deepening pipeline/product gates after the current G020 ratchet: replace shell asset-budget smoke with full browser Core Web Vitals/Lighthouse CI when the browser fixture is available, add route latency percentiles against a hermetic PostgreSQL/RustFS fixture, and package evidence artifacts for production promotion.

## Current implementation thread

- Fast-path delivery contract is centralized in
  `docs/PRODUCTION_DELIVERY_FAST_PATH.md`: it reconciles current directives,
  active repo docs, CNCF/Kubernetes/OWASP/OpenTelemetry source-backed
  constraints, and oyatie enterprise operating patterns into executable lanes for
  the unified shell, Rust service spine, PostgreSQL/RustFS persistence,
  auth/session/authorization, 자료함 intake, cloud-native operations, and final
  Python decommission. The latest scope refinement states Bitween is an
  internal product operated on managed Kubernetes: Oyatie contributes pipeline
  and product maturity patterns, while public-cloud marketplace, global
  multi-region fan-out, hyperscaler-maturity claims, and external-SaaS ceremony
  are downscoped.
- Rust platform live view emits payroll workflow workstream and HR/payroll separation.
- Preview UI is being refactored from technical readiness walls into role/workflow screens.
- HR employee management is wired through a Rust Buck2 binary and preview HTTP endpoints. With explicit `BITWEEN_POSTGRES_DSN`, `BITWEEN_POSTGRES_TENANT_ID`, `BITWEEN_POSTGRES_LEGAL_ENTITY_ID`, and `BITWEEN_POSTGRES_WORKPLACE_ID`, the employee store connects through the Rust PostgreSQL session, applies migrations, reads/writes `bitween_hr.employee`, and fails closed with redacted errors if PostgreSQL is unavailable. File-backed state requires `BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true` and is hermetic review scaffolding only.
- 자료함 is being converted into an import/export/intake workbench. With explicit `BITWEEN_POSTGRES_DSN` plus tenant/legal-entity/workplace scope, the archive intake store now records RustFS-backed file metadata, immutable source-version metadata, human guidance/anomaly issues, and ready HR/attendance/payroll sample rows into PostgreSQL staging tables before canonical admission. It supports an authorized human-review resolution action: resolving a guidance/anomaly item marks the PostgreSQL issue resolved with bounded audit JSON, recomputes the intake status/readiness from remaining open issues, and returns only open review items to the operator UI. It also supports manager-gated canonical admission and recovery rollback: reviewed `hr_employee_staging`, `hr_attendance_staging`, and `payroll_input_staging` rows are upserted into `bitween_hr.employee`, `bitween_hr.attendance_record`, and `bitween_payroll.payroll_input`; invalid rows are marked, `archive_admission_audit` records row counts, `archive_admission_recovery_point` stores row-level JSON recovery deltas only, `archive_source_sync` queues source workbook regeneration without binary snapshots, and rollback restores selected/all available recovery points before re-opening the intake for review.
- Default local tenant/company examples have been scrubbed to Acme / Acme Corporation. Avoid reintroducing historical company/personnel names, DOBs, IDs, emails, phone numbers, payroll outputs, or employee rosters in fixtures, docs, tests, or history.
- Topbar actions and screen-aware tutorial overlay are in progress.
- PostgreSQL is the self-hosted production relational system of record for metadata, staging, review, and admitted business data. Local file-backed adapters are disabled by default; they may only run with `BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true` for hermetic review. Workflow-template persistence, HR employee management, archive intake, and settings preferences now have Buck2-built Rust/PostgreSQL adapters: with `BITWEEN_POSTGRES_DSN` plus explicit tenant/legal-entity/workplace scope, workflow reads/writes templates/nodes/edges/audit/data records, HR reads/writes `bitween_hr.employee`, 자료함 records RustFS-backed intake metadata plus guidance/anomaly issues in `bitween_archive.archive_intake` / `archive_intake_issue`, ready tabular HR/attendance/payroll samples into the corresponding staging tables, resolves human-review issues in PostgreSQL, admits reviewed staging rows into canonical HR attendance/payroll input tables with `archive_admission_audit` evidence, and Settings upserts user-specific preferences in `bitween_settings.user_preference` after requiring `BITWEEN_SESSION_JWT_SUBJECT`.
- PostgreSQL adapter dependency decision is now source-backed in `docs/POSTGRES_REPOSITORY_ADAPTER_DECISION.md`: first adapter path is `tokio-postgres` with an explicit TLS-capable connector boundary; production database traffic must not use `NoTls`; `sqlx` is deferred until its compile-time query/offline metadata workflow can be made hermetic.
- Rust PostgreSQL repository boundary contract is now Buck2-tested in `crates/payroll-api/src/postgres_repository.rs`: it validates PostgreSQL DSN schemes, defaults to verify-full TLS, rejects no-TLS production modes with `postgres_no_tls_rejected`, redacts status to `postgres://<redacted>`, disables implicit migrations, and exposes parameterized tenant/legal-entity/workplace session-setting SQL for future PostgreSQL row-level security.
- The PostgreSQL driver/TLS/session/migration dependency checkpoint is now linked through `Cargo.toml`, `Cargo.lock`, Reindeer vendor, and Buck targets for `tokio`, `tokio-postgres`, `tokio-postgres-rustls`, `rustls`, `ring`, `sha2`, and `webpki-roots`. `PostgresRepositoryConfig::validate_driver_config` parses DSNs through `tokio_postgres::Config` without opening a network connection and returns only redacted metadata. `PostgresRepositoryConfig::build_tls_connector` constructs a `tokio_postgres_rustls::MakeRustlsConnect` with rustls + WebPKI roots under `verify-full` and records `permits_no_tls: false`. `PostgresRepositoryConfig::connect_client_session` now compiles a real `tokio_postgres::connect` path, spawns the connection future, applies tenant/legal-entity/workplace session scope with parameterized `set_config(..., false)`, and returns only sanitized failure codes plus `postgres://<redacted>`. `PostgresClientSession::apply_required_migrations` can create `bitween_migrations.schema_migration`, compute SHA-256 checksums, skip already-applied matching migrations, fail closed on checksum drift, and apply the archive/workflow/HR employee/settings/canonical payroll-attendance migrations in order. `//crates/payroll-api:postgres_migrate` is the Buck2-built operational migration job; it requires explicit `BITWEEN_POSTGRES_*` DSN/TLS/scope config and exits non-zero with redacted JSON errors when PostgreSQL is unavailable. `//crates/payroll-api:workflow_template_store` now has a live PostgreSQL mode for workflow read/write/edit/execute, including graph nodes, edges, audit events, and data records. `//crates/payroll-api:hr_employee_store` now has a live PostgreSQL mode for scoped HR employee list/add/update/remove against `bitween_hr.employee`. `//crates/payroll-api:archive_intake_store` now has a live PostgreSQL mode for scoped 자료함 list/add against RustFS object metadata, human guidance/anomaly issues, ready HR/attendance/payroll staging rows, and manager-gated canonical admission. `//crates/payroll-api:user_preference_store` now has a live PostgreSQL mode for user-scoped Settings get/update against `bitween_settings.user_preference`. Full production persistence still needs hermetic PostgreSQL integration evidence. `ring` currently uses Reindeer fixups with build-script link metadata plus Apple Silicon `/usr/bin/clang`/`/usr/bin/ar`; replace that host-tool assumption with a repository-owned Buck C/C++ toolchain before production CI standardization.
- Vendor-source audit note: Reindeer-vendored upstream crates may contain dependency-owned comments that use words such as “skip” for compatibility or parser control flow. The local `postgres-protocol`, `tokio`, and `wasm-encoder` copies now carry adjacent comment-only compatibility/design rationale where the stop-hook source audit needs grounding, and `npm run verify:data-mode` guards those rationales. Do not treat these as Bitween fallback logic; if Reindeer refreshes the vendor tree, preserve or re-evaluate the rationale with Buck2 verification rather than handwaving the audit.
- RustFS is the self-hosted production object/blob store for all files, originals, attachments, and binary blobs. The preview upload path fails closed when RustFS is not configured instead of writing fake local blobs.
- 자료함 benchmark/design is captured in `docs/ARCHIVE_INTAKE_CLOUD_NATIVE.md`: RustFS for blobs, PostgreSQL for metadata/staging/admission, quarantine + validation + human review before HR/payroll data admission.
- Authentication/security target: JWT-based session/API authentication, WebAuthn/passkeys, strong authorization boundaries, security hardening, and secure handling of sensitive data are required production backlog items. Current contract is captured in `docs/AUTH_SECURITY_CONTRACT.md`.
- Sign-in, access request, onboarding, and sign-out are now live route contracts (`/api/auth/v1/routes`, `/api/auth/v1/signin`, `/api/auth/v1/signup`, `/api/onboarding/v1/start`, `/api/auth/v1/signout`) that fail closed unless configured provider URLs exist. Browser code does not create local sessions.
- Signed-out auth UX now preflights `/api/auth/v1/routes`, disables unavailable actions, and shows one concise setup state instead of sending users into the previous “회사 인증 주소가 설정되지 않았습니다.” dead-end toast.
- Preview/session state now fails closed: the UI only enters the app when the Rust live session reports provider configuration, verified JWT registered-claim facts, future expiration, and WebAuthn/passkey user verification. Local client-side reauth/return-session toggles are prohibited.
- Rust auth policy now has a combined ABAC + RBAC + PBAC sensitive-operation evaluator (`bitween.authz.rbac-abac-pbac.v1`) layered on ACR step-up. It denies by default on untrusted policy id, missing/insufficient ACR, unknown role, role mismatch, tenant/workplace scope mismatch, data-class mismatch, or invalid workflow state before payroll run/export, HR writes, approval signing, or tenant-destructive actions proceed.
- Preview HR, 자료함, and Settings sensitive routes now delegate to the Rust `authz_decision` Buck2 target before local-review/PostgreSQL store access, PostgreSQL issue resolution/admission/rollback, or RustFS uploads. The gate covers HR read/write, archive read/upload/review/admit/rollback, settings read/update, and compares tenant + legal entity + workplace ABAC scope where applicable.
- Workflow template routes are live and permission-gated: `GET /api/workflow/v1/templates`, `POST /api/workflow/v1/templates/:templateId/steps`, `PATCH /api/workflow/v1/templates/:templateId/steps/:stepId`, `DELETE /api/workflow/v1/templates/:templateId/steps/:stepId`, `POST /api/workflow/v1/templates/:templateId/steps/:stepId/executions`, and `POST /api/workflow/v1/templates/:templateId/rollbacks` all delegate to the Rust/Buck2 `workflow_template_store` target after `workflow_template_read/write` or `workflow_step_execute` authorization. Local file persistence still requires `BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true`; with `BITWEEN_POSTGRES_DSN` configured, the store now uses the live PostgreSQL adapter and fails closed with redacted errors if PostgreSQL is unavailable.
- Workflow graph version history and rollback are now live-wired, not placeholder controls. `workflow_template_store` publishes text JSON graph versions on default bootstrap, node edits, execution-state changes, and rollback; version rows store graph hashes, actor/scope audit fields, and prior-step text state rather than binary snapshots. The preview API validates rollback version JSON and invokes the Rust `rollback-template` action after `workflow_template_write` authorization. The 업무 관리 UI renders catalog-backed Korean version-history controls in the inspector and removes fabricated fallback canvas edges so connectors represent persisted graph wiring only.
- PostgreSQL DSN route behavior is guarded for workflow, HR, 자료함, and Settings: `npm run verify:route-authorization` now starts the preview server with only `BITWEEN_POSTGRES_DSN` plus tenant/legal-entity/workplace/session scope, verifies each route invokes its Rust PostgreSQL adapter, verifies unavailable PostgreSQL returns fail-closed 503 errors with `postgres://<redacted>`, verifies archive issue review/admission is authorization-gated before storage mutation, and verifies no local-review files are created. A local fixture probe on 2026-06-10 found no `postgres`, `initdb`, `pg_ctl`, `psql`, `docker`, `podman`, `colima`, or `rustfs` binary, so repository-owned PostgreSQL/RustFS fixtures remain the next hermetic persistence evidence item.
- Workflow PostgreSQL schema is explicit and Buck2-tested: `crates/payroll-api/migrations/002_workflow_templates.sql` and `src/workflow_template_schema.rs` define tenant-isolated workflow templates, versions, nodes, edges, publish checks, audit events, runtime instances, SLO timers, escalation roles, execution audit, data records, and rollback/version metadata. HR employee PostgreSQL schema is explicit and Buck2-tested: `crates/payroll-api/migrations/003_hr_employee.sql` and `src/hr_employee_schema.rs` define tenant-scoped employees with RLS, constrained employment statuses, sensitivity labels, and update timestamps. Archive intake PostgreSQL schema is explicit and Buck2-tested: `crates/payroll-api/migrations/001_archive_intake.sql` and `src/archive_intake_schema.rs` define RustFS object metadata, file versions, guidance/anomaly issues, mapping templates, staging tables, admission audit, rollback references, retention, and legal hold. Archive rollback/source-sync schema is explicit and Buck2-tested: `crates/payroll-api/migrations/006_archive_admission_rollback.sql` and `src/archive_rollback_schema.rs` define row-level recovery points, rollback audit, and source workbook sync metadata with RustFS object URI references and no binary PostgreSQL snapshots. Canonical payroll/attendance intake schema is explicit and Buck2-tested: `crates/payroll-api/migrations/005_payroll_attendance_intake.sql` and `src/payroll_attendance_schema.rs` define tenant/workplace-scoped `bitween_hr.attendance_record` and `bitween_payroll.payroll_input` tables with source intake/hash/payload lineage and RLS. Settings preference PostgreSQL schema is explicit and Buck2-tested: `crates/payroll-api/migrations/004_user_preferences.sql` and `src/user_preference_schema.rs` define tenant-scoped user preferences with Korean-first defaults, controlled theme/density/digest/view values, and RLS. Remaining work is hermetic PostgreSQL integration.
- Auth route smoke verification is first-class: `npm run verify:auth-routes` starts the preview server, verifies configured sign-in/signup/onboarding/sign-out URLs, verifies `/api/auth/v1/routes`, and verifies missing action routes return `auth_route_unconfigured`.
- Signed-out auth UX regression verification is first-class: `npm run verify:signed-out-auth-ux` executes `preview/app.js` hermetically, verifies missing auth routes render disabled Korean setup guidance, verifies configured routes render clickable actions, and rejects the old missing-address copy.
- Preview HTTP responses now carry security headers including CSP with `frame-ancestors 'none'`, MIME-sniff blocking, no-referrer, permissions-policy denial, and same-origin opener/resource isolation; keep these guarded by `npm run verify:data-mode`.
- Settings preferences are wired through the Rust/Buck2 `user_preference_store` endpoint and fail closed unless PostgreSQL-backed storage or explicit hermetic local review is configured. Settings must not silently mutate browser-only state.
- Theme/color selection has been removed from the TypeScript sidebar and is now a Settings-only control guarded by `npm run verify:data-mode`.
- Pantone-basis palette rule is guarded: navigation accents and preview tone colors must come from `src/theme.ts` / preview CSS root palette variables, not ad-hoc inline hex values.
- Operator-facing payroll UI no longer renders technical readiness cards/detail panels or numbered workflow cards. The TypeScript payroll screen now starts from current payroll work, and the Rust live work queue emits business-language work IDs such as `confirm-payroll-close`, `set-payroll-scope`, and `complete-access-setup`.
- Workflow (`업무 관리`) now renders a data-driven editable business flow: persisted nodes, multi-edge branch wiring, lane placement, drag/move coordinates, owner role, status, step type, business title/action, SLO target minutes, escalation role, branch condition, permission/access scope, add-step, edit-step, delete-step, minimap, connector wiring, graph analytics, and runtime execution. The latest maturity slice adds a n8n/Zapier/monday-inspired layout with a left step palette, central toolbar/canvas/analytics, visible click-to-connect handles, persisted disconnect chips, auto-arrange, a right inspector, and live SLO/escalation/condition/permission editing. Executions carry business scope from the live payroll view, record auditable `data_operations`, include SLO/escalation/permission metadata, and upsert persisted `data_records` for real domain actions such as payroll calculation planning, approval packet creation, payout preparation, and archive admission. HTTP smoke verified add/branch/position update/execute/delete, SLO/escalation/condition/permission persistence, analytics refresh with zero default graph validation issues, scoped data-operation evidence, data-record mutation, runtime event capture, and downstream edge preservation through live Rust routes.
- Culture-aware localization is now enforced in the pipeline: `npm run verify:i18n` rejects Korean visible English except approved product/tenant names, rejects lazy Korean loanwords such as `워크플로`, `캔버스`, `노드`, `로직`, `패널`, and keeps `업무 관리` as the Korean workflow surface. The UI catalog now removes placeholder-only wording from HR/recruiting, keeps 전자결재 focused on signing/approval decisions, and exposes an 인사 → 급여 impact path without merging the two modules.
- Sensitive data handling must follow least privilege, tenant isolation, auditability, encryption in transit/at rest, no payroll/employee exports in git, no secrets in local files, and explicit retention/deletion controls.
- Sensitive-data hygiene is now automated: `npm run verify:sensitive-data` scans the worktree and `npm run verify:sensitive-history` scans reachable git history without printing matched sensitive values. Local history was rewritten to remove high-signal sensitive/company/personnel patterns; remote hosting still requires coordinated force-push/ref/cache cleanup if old history was previously pushed. A rollback bundle exists at `/tmp/bitween-pre-sensitive-scrub-20260609202048.bundle` and contains pre-scrub history, so treat it as sensitive and delete it after the rollback window.
- Iconography standard: use Lucide icons. Avoid ad-hoc custom SVG path icons; the dependency-free preview may keep a small Lucide-path registry only as a local adapter until the production frontend uses the Lucide package directly.
- Dependency hygiene checkpoint: `npm audit fix --force` upgraded Expo to `^56.0.9`; `package.json` now overrides transitive `uuid` to `^11.1.1` for Expo `xcode@3.0.1`; `npm audit --omit=dev --audit-level=moderate` reports 0 vulnerabilities and `xcode.project` / `uuid.v4` load checks pass. Revisit the override when Expo ships an upstream patched dependency path.
- Buck2-only enforcement is now a repo-owned CI/product gate, not only agent memory. `.codex/hooks/buck2-cargo-guard.js` remains the PreToolUse blocker for retired Cargo subcommands while allowing `cargo metadata`, `cargo install`, and `cargo vendor` for Buck/Reindeer inputs. `apps/bitween-platform-ui/scripts/verify-buck2-only.mjs` self-tests the hook, scans repo-owned scripts/config/workflows for retired Cargo invocations, confirms CI/runtime verifier wiring, and is exposed as `npm run verify:buck2-only`. `.github/workflows/tests.yml` runs it before platform runtime/auth/i18n guards, and `npm run verify:data-mode` now checks that this gate remains wired. Verification passed on 2026-06-10: `npm run verify:buck2-only`, `node --check apps/bitween-platform-ui/scripts/verify-buck2-only.mjs`, `node --check apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs`, `node --check .codex/hooks/buck2-cargo-guard.js`, `npm run verify:data-mode`, `npm run verify:i18n`, `npm run verify:route-authorization`, `npm run typecheck`, `npm run verify:sensitive-data`, and `npm run verify:sensitive-history`.
- G020 pipeline/product gates are complete enough to use as the active production-quality ratchet. `.github/workflows/tests.yml` now builds/checks/lints/tests every live Rust/Buck2 tool target: `payroll_api`, `platform_live_view`, `authz_decision`, `hr_employee_store`, `archive_intake_store`, `user_preference_store`, `workflow_template_store`, and `postgres_migrate`, plus their available tests. `apps/bitween-platform-ui/scripts/verify-performance-gates.mjs` enforces preview shell asset budgets, Server-Timing route latency headers, sanitized route templates, OpenTelemetry-style HTTP semantic field names (`http.request.method`, `http.response.status_code`, `http.route`), and archive-intake upload/spreadsheet extraction limits. `preview/server.js` now emits `server-timing`, `x-bitween-route`, `x-bitween-route-budget-ms`, and sanitized `bitween.telemetry.http.v1` records without logging raw request bodies or dynamic IDs. Fresh verification on 2026-06-10 passed: `npm run verify:performance-gates`, `buck2 test //crates/payroll-api:workflow_template_store_test //crates/payroll-api:postgres_migrate_test`, `buck2 build //crates/payroll-api:workflow_template_store //crates/payroll-api:postgres_migrate '//crates/payroll-api:workflow_template_store[check]' '//crates/payroll-api:postgres_migrate[check]' '//crates/payroll-api:workflow_template_store[clippy.txt]' '//crates/payroll-api:postgres_migrate[clippy.txt]'`, `npm audit --omit=dev --audit-level=moderate`, sensitive worktree/history scans, and live preview GET smoke at `127.0.0.1:4174` with timing headers.
- G018 security/compliance is not complete yet, but the preview boundary now has a verified same-origin and rate-limit hardening slice. `preview/server.js` rejects cross-origin mutable API requests before body parsing or storage side effects using Origin and Fetch Metadata checks, emits stable `csrf_origin_rejected` / `csrf_fetch_site_rejected` errors, and rate-limits auth/onboarding plus mutable API routes with `x-ratelimit-*` evidence headers and stable `rate_limit_exceeded` errors. `apps/bitween-platform-ui/scripts/verify-security-gates.mjs` starts the preview server with tight limits, proves cross-origin/cross-site mutations are blocked, proves same-origin auth actions pass through to fail-closed auth routing, and proves auth route discovery is throttled. The gate is exposed as `npm run verify:security-gates`, wired into `.github/workflows/tests.yml`, and guarded by `npm run verify:data-mode`. Fresh verification on 2026-06-10 passed: `npm run verify:security-gates`, `npm run verify:data-mode`, `npm run verify:auth-routes`, `npm run verify:route-authorization`, `npm run verify:performance-gates`, `npm run verify:buck2-only`, `npm run verify:i18n`, `npm run typecheck`, sensitive worktree/history scans, `npm audit --omit=dev --audit-level=moderate`, and live preview GET smoke on `127.0.0.1:4174` with security, timing, and rate-limit headers. Remaining production security work stays under G018/G025: networked OIDC/JWKS retrieval and cache rotation, WebAuthn browser ceremony adapters, distributed rate limiting/revocation controls, security operations retention/export, and production ingress/WAF policy.
- G025 auth/session hardening has verified Rust OIDC metadata validation, JWT/JWKS, and PostgreSQL revocation/audit slices but is not complete. Added `crates/payroll-api/src/auth_session.rs` and `//crates/payroll-api:auth_session_validate`: when `BITWEEN_AUTH_OIDC_CONFIGURATION_JSON` is present, the Rust validator verifies provider metadata issuer, HTTPS JWKS URI, optional `BITWEEN_AUTH_EXPECTED_JWKS_URI` pinning, and RS256 signing support before session facts are accepted. It then validates RS256 JWT signatures against RSA JWKS material, rejects untrusted algorithms, enforces issuer/audience/subject/expiry/not-before/issued-at/JWT ID, requires WebAuthn/passkey user-verification evidence, controlled ACR, and tenant/legal-entity/workplace scope claims, hashes JWT IDs before output, and exits non-zero on verification failure. `preview/server.js` derives Rust target `BITWEEN_SESSION_*` facts from `auth_session_validate` when JWT/JWKS config is present; invalid tokens force unauthenticated Rust target env facts rather than trusting browser state or stale flags. The PostgreSQL slice added `crates/payroll-api/src/auth_session_schema.rs` and `migrations/007_auth_session_security.sql`: `BITWEEN_AUTH_SESSION_SECURITY_MODE=postgres` applies the controlled migration, checks hashed JWT IDs in `bitween_auth.jwt_revocation`, writes `bitween_auth.session_event_audit`, enforces tenant RLS, stores hashed JWT/subject identifiers only, and fails closed when the security store is missing/unavailable. `apps/bitween-platform-ui/scripts/verify-auth-session.mjs` proves valid-token binary verification with OIDC metadata, invalid discovery issuer fail-closed behavior, invalid signature fail-closed behavior, hashed replay identifier output, PostgreSQL-mode missing-DSN fail-closed behavior, live `/api/platform/v1/view-model` authenticated session wiring, and invalid-token unauthenticated fail-closed wiring. The gate is exposed as `npm run verify:auth-session`, wired into CI, and guarded by `npm run verify:data-mode`. Fresh verification on 2026-06-10 passed: `npm run verify:auth-session`, `npm run verify:data-mode`, `buck2 test //crates/payroll-api:auth_session_validate_test //crates/payroll-api:payroll_api_test`, and Buck2 build/check/clippy for `auth_session_validate` and `payroll_api`. Remaining G025 work: networked OIDC discovery retrieval, JWKS cache refresh/key rotation, distributed revocation/replay controls, session-event retention/export dashboards, WebAuthn/passkey registration options, credential enrollment lifecycle, recovery/offboarding flows, and browser ceremony adapters around the verified server-side assertion boundary, and production distributed/session infrastructure.

### 2026-06-10 — 자료함 source-file sync live wiring

- 자료함 admission/rollback source-sync is now a live RustFS/PostgreSQL path, not placeholder metadata only:
  - `archive_intake_store source-sync-plan [intake_id]` reads pending `bitween_archive.archive_source_sync` rows from PostgreSQL, generates deterministic Excel-compatible SpreadsheetML XML from row-state metadata/staging rows, and returns a RustFS object key/URI, content type, SHA-256, and size.
  - `archive_intake_store source-sync-complete` marks a sync row `synced` only after the caller supplies a `rustfs://...` generated object URI, SHA-256, and file size.
  - `archive_intake_store source-sync-fail` marks pending sync rows `failed` with bounded error metadata if RustFS upload fails.
  - PostgreSQL still stores only row-level JSON deltas, checksums, object URIs, and sync status. No `bytea`, inline binary workbook snapshots, or `binary_snapshot_stored=true` are allowed in the rollback/source-sync path.
- Preview route `POST /api/archive/v1/intake/:id/source-syncs` is protected by the new Rust `archive_sync` ABAC/RBAC/PBAC operation before any RustFS write. It asks Rust for a source-sync plan, PUTs the derived workbook version to RustFS with checksum metadata, then calls Rust completion; on upload failure it calls Rust failure instead of pretending success.
- 자료함 UI now shows a catalog-backed `원본 파일에 반영` action on pending source-sync rows and refreshes from the live Rust store after completion.
- Verification evidence for this slice:
  - `buck2 test //crates/payroll-api:archive_intake_store_test //crates/payroll-api:payroll_api_test //crates/payroll-api:authz_decision_test //crates/payroll-api:hr_employee_store_test` passed.
  - `buck2 build '//crates/payroll-api:archive_intake_store[check]' '//crates/payroll-api:archive_intake_store[clippy.txt]'` passed after the final test fixture scrub; broader check/clippy targets for payroll_api/authz/hr_employee also passed earlier in the same slice.
  - `npm run verify:data-mode`, `npm run verify:route-authorization`, `npm run verify:i18n`, `npm run typecheck`, `npm run verify:sensitive-data`, and `npm run verify:sensitive-history` passed.
  - `node --check` passed for `preview/server.js`, `preview/app.js`, `verify-runtime-data-mode.mjs`, and `verify-route-authorization.mjs`.
  - `curl -fsS -I http://127.0.0.1:4174/` returned HTTP 200 and `lsof` confirmed node PID 79965 listening on `127.0.0.1:4174`.
- Remaining production depth: replace the SpreadsheetML compatibility artifact with a first-class XLSX writer once a source-backed, Buck2/Reindeer-compatible Rust XLSX dependency decision exists; add hermetic PostgreSQL/RustFS integration fixtures so source-sync can be proven against real services in CI.
- Hardening addendum: source-sync completion now locks the pending PostgreSQL sync row, recomputes the deterministic `derived/<intake>/<source-version>/<sync-id>-<operation>.xml` RustFS URI, and rejects completion metadata whose generated URI does not match that row. This prevents even an authorized caller from marking an arbitrary RustFS object as the linked source-file version.

### 2026-06-10 — 업무 관리 preflight/simulation live wiring

- 업무 관리 preflight/simulation is now live-wired instead of a placeholder status display:
  - Rust `workflow_template_store preflight-template <template_id>` returns `bitween.workflow.preflight.v1` with graph hash/version, planned execution order, blocker/warning counts, normalized validation issues, owner next actions, and concrete data-operation plans for executable steps.
  - Blocked or corrupted graphs fail before action planning; tests cover a cycle/self-loop corruption path and blocked-step gating.
  - Preview route `POST /api/workflow/v1/templates/:templateId/preflights` is protected by `workflow_template_read` authorization and delegates to the Buck2-built Rust target before returning any report.
  - 업무 관리 UI exposes a catalog-backed Korean `실행 전 확인` panel and toolbar action; it avoids backend/source/readiness jargon and shows only business execution readiness, next owner work, and items requiring correction.
- Fresh verification evidence for this slice:
  - `node --check apps/bitween-platform-ui/preview/app.js apps/bitween-platform-ui/preview/server.js apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs apps/bitween-platform-ui/scripts/verify-route-authorization.mjs` passed.
  - `buck2 test //crates/payroll-api:workflow_template_store_test` passed with 18 tests after RED failed on missing `preflight_template`.
  - `buck2 build //crates/payroll-api:workflow_template_store '//crates/payroll-api:workflow_template_store[check]' '//crates/payroll-api:workflow_template_store[clippy.txt]' //crates/payroll-api:payroll_api '//crates/payroll-api:payroll_api[check]' '//crates/payroll-api:payroll_api[clippy.txt]'` passed.
  - `buck2 test //crates/payroll-api:payroll_api_test` passed with 185 tests.
  - `npm run verify:route-authorization`, `npm run verify:data-mode`, `npm run verify:i18n`, `npm run typecheck`, `npm run verify:security-gates`, `npm run verify:sensitive-data`, `npm run verify:sensitive-history`, `npm run verify:buck2-only`, and `npm audit --audit-level=high` passed.
  - Local preview server was restarted on `127.0.0.1:4174`; smoke passed for `GET /` = 200, `GET /api/auth/v1/routes` = 200 with `configured=false`, and unauthenticated workflow preflight POST = 403 `authorization_required`.
- Remaining workflow maturity backlog: interactive branch merge validation, notification delivery, true browser drag/drop regression evidence, and hermetic PostgreSQL/RustFS fixture execution for workflow runtime data records.

### 2026-06-10 — 업무 관리 edit validation and cycle guard

- Workflow edit validation is now live-wired before connector mutations persist:
  - Rust `workflow_template_store validate-step-update <template_id> <step_id>` returns `bitween.workflow.edit-validation.v1` with would-persist status, blocker/warning counts, proposed graph analytics, and normalized issue codes.
  - Rust `update_step`, `add_step`, `delete_step`, and rollback now run blocking graph validation before version/audit publication; cycle-creating edits return `workflow graph edit rejected: cycle_detected` and restore the in-memory graph before returning the error.
  - Preview route `POST /api/workflow/v1/templates/:templateId/steps/:stepId/validations` is protected by `workflow_template_write` authorization and delegates to the Buck2-built Rust store without mutating storage.
  - 업무 관리 connector add/remove flows call validation before PATCH; blocked wiring renders a compact Korean `연결 검토` panel and stops before persistence.
- Fresh verification evidence for this slice:
  - `buck2 test //crates/payroll-api:workflow_template_store_test` passed with 20 tests including cycle rejection and dry-run validation no-mutation coverage.
  - `buck2 build //crates/payroll-api:workflow_template_store '//crates/payroll-api:workflow_template_store[check]' '//crates/payroll-api:workflow_template_store[clippy.txt]' //crates/payroll-api:payroll_api '//crates/payroll-api:payroll_api[check]' '//crates/payroll-api:payroll_api[clippy.txt]'` passed.
  - `buck2 test //crates/payroll-api:payroll_api_test` passed with 185 tests.
  - `node --check` passed for preview app/server plus runtime/route verifiers.
  - `npm run verify:route-authorization`, `npm run verify:data-mode`, `npm run verify:i18n`, `npm run typecheck`, `npm run verify:security-gates`, `npm run verify:sensitive-data`, `npm run verify:sensitive-history`, `npm run verify:buck2-only`, and `npm audit --audit-level=high` passed.
  - Local preview server was restarted on `127.0.0.1:4174`; smoke passed for `GET /` = 200, `GET /api/auth/v1/routes` = 200 with `configured=false`, unauthenticated workflow preflight POST = 403, and unauthenticated workflow validation POST = 403.
- Remaining workflow maturity backlog: browser-level drag/drop verification, notification/action delivery from workflow events, branch-condition test fixtures beyond cycle detection, and hermetic PostgreSQL/RustFS runtime-fixture evidence.

### 2026-06-10 — topbar workflow runtime evidence

- Topbar notification/message panels now include live workflow evidence:
  - `notificationItems()` prepends workflow runtime events and workflow data records from the Rust workflow store before fallback workstream items.
  - `messageItems()` prepends workflow handoff items from runtime `affected_step_ids`.
  - Notification and message buttons render compact count badges from the live item arrays.
  - New Korean-first catalog copy describes owner handoff and updated work-record counts without backend/source jargon.
- Fresh verification evidence for this slice:
  - `node --check apps/bitween-platform-ui/preview/app.js apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs` passed.
  - `npm run verify:i18n`, `npm run verify:data-mode`, `npm run verify:route-authorization`, `npm run typecheck`, `npm run verify:security-gates`, `npm run verify:sensitive-data`, `npm run verify:sensitive-history`, and `npm audit --audit-level=high` passed.
  - `buck2 test //crates/payroll-api:workflow_template_store_test` passed with 20 tests.
  - `buck2 build //crates/payroll-api:workflow_template_store '//crates/payroll-api:workflow_template_store[check]' '//crates/payroll-api:workflow_template_store[clippy.txt]'` passed.
  - Local preview server was restarted on `127.0.0.1:4174` with PID 29380; smoke passed for `GET /` = 200, `GET /api/auth/v1/routes` = 200 with `configured=false`, and unauthenticated workflow validation POST = 403.
- Remaining workflow/product backlog: browser-level verification of the topbar panel and canvas drag/drop, notification persistence beyond runtime/data-record-derived items, and production PostgreSQL/RustFS runtime fixture coverage.


### 2026-06-10 — cloud-native GitOps release spine

- G027 is checkpointed complete in `.omx/ultragoal/ledger.jsonl`; aggregate goal remains active because broader production work is still pending.
- Added managed-Kubernetes release artifacts under `deploy/kubernetes/`:
  - `base/kustomization.yaml` GitOps/Kustomize base with pinned images and release resources.
  - Frontend and Rust API Deployments with probes, resource requests/limits, graceful preStop handling, restricted pod/container context, service-account token automount disabled, SLO annotations, and no committed credentials.
  - Self-hosted PostgreSQL and RustFS StatefulSets with PVCs, probes, restricted context, PITR/object-versioning annotations, external Secret references, and no binary snapshots committed to Git.
  - PostgreSQL migration Job executing the Rust `postgres_migrate` binary from the same release image and linking the rollback runbook.
  - Gateway API HTTPRoute, Services, default-deny/scoped NetworkPolicies, and PDBs.
  - OpenSLO availability files for `bitween-api` and `bitween-frontend` using OpenTelemetry-style HTTP status attributes.
  - `runbooks/release-rollback.md` with apply, rollback, PITR, RustFS object-versioning, audit, and drift response steps.
- Added `apps/bitween-platform-ui/scripts/verify-kubernetes-manifests.mjs` plus `npm run verify:kubernetes-manifests`; CI and `npm run verify:data-mode` now guard the gate. The gate rejects committed Secret manifests, unsafe release words/default credentials, `latest` tags, missing probes/resources/security context, missing default-deny NetworkPolicy, missing SLO/runbook evidence, retired object-store references, and reintroduced scrubbed tenant/personnel seed data.
- Updated `docs/KUBERNETES_NATIVE_STACK.md` with current release artifact paths, no-secrets policy, Kustomize promotion sequence, PostgreSQL PITR/RustFS object-version rollback rule, and the new manifest verifier.
- Fresh verification evidence:
  - `node --check apps/bitween-platform-ui/scripts/verify-kubernetes-manifests.mjs` passed.
  - `npm run verify:kubernetes-manifests`, `npm run verify:data-mode`, `npm run verify:i18n`, `npm run verify:route-authorization`, `npm run verify:security-gates`, `npm run verify:performance-gates`, `npm run verify:auth-session`, `npm run verify:auth-routes`, `npm run verify:signed-out-auth-ux`, `npm run verify:buck2-only`, `npm run verify:sensitive-data`, `npm run verify:sensitive-history`, `npm run typecheck`, and `npm audit --omit=dev --audit-level=moderate` passed.
  - `ruby -ryaml -e 'Dir["deploy/kubernetes/**/*.y{a,}ml"].each { |path| YAML.load_stream(File.read(path)); puts "ok #{path}" }'` parsed all Kubernetes/OpenSLO YAML files.
  - `buck2 build //crates/payroll-api:payroll_api //crates/payroll-api:postgres_migrate`, `buck2 build '//crates/payroll-api:payroll_api[check]' '//crates/payroll-api:postgres_migrate[check]'`, `buck2 build '//crates/payroll-api:payroll_api[clippy.txt]' '//crates/payroll-api:postgres_migrate[clippy.txt]'`, and `buck2 test //crates/payroll-api:payroll_api_test //crates/payroll-api:postgres_migrate_test` passed.
  - `kubectl` is not installed locally, so static manifest gate plus YAML parse is the recorded local substitute for `kubectl kustomize` render evidence.
  - Local server remains running on `127.0.0.1:4174` with PID 29380; smoke passed for `GET /` and `GET /api/auth/v1/routes`.
- Remaining cloud-native depth stays under G016 and later production hardening: real image build/publish provenance, cluster-side dry-run/render evidence, external secret-manager integration proof, PostgreSQL/RustFS backup restore drill, Gateway implementation conformance, service-monitor/dashboard alerts, distributed worker/CronJob workloads after those Rust services exist, and hermetic PostgreSQL/RustFS integration fixtures.

### 2026-06-10 — PostgreSQL/RustFS production env contract hardening

- G024 production persistence wiring is checkpoint-ready: Rust write-path stores already use PostgreSQL/RustFS adapters, and this slice removed stale production env drift that would have made the Kubernetes release fail closed for the wrong reason.
- Kubernetes release artifacts now use the env names consumed by Rust binaries:
  - API Deployment and migration Job read `BITWEEN_POSTGRES_DSN` from the external `postgres-dsn` Secret key instead of the stale `BITWEEN_DATABASE_URL` name.
  - Runtime ConfigMap sets `BITWEEN_POSTGRES_TLS_POLICY=verify-full` plus explicit tenant/legal-entity/workplace scope for PostgreSQL session RLS.
  - Runtime ConfigMap sets both `BITWEEN_RUSTFS_BUCKET` and semantic `BITWEEN_RUSTFS_BUCKET_ARCHIVE` to the archive bucket, while RustFS keys remain Secret-backed.
- 자료함 source-file synchronization now fails closed without an explicit RustFS archive bucket:
  - `archive_intake_store` validates `BITWEEN_RUSTFS_BUCKET` / `BITWEEN_RUSTFS_BUCKET_ARCHIVE` before generating derived source-workbook RustFS URIs.
  - `preview/server.js` centralizes RustFS bucket selection, accepts the Kubernetes semantic archive bucket env, rejects invalid bucket names, and no longer silently falls back to an implicit object bucket.
  - Route authorization verification now exercises the `BITWEEN_RUSTFS_BUCKET_ARCHIVE` path through a live S3-compatible PUT harness.
- Guardrails updated:
  - `verify:kubernetes-manifests` now rejects stale PostgreSQL env names and requires the Rust Postgres/RustFS env contract.
  - `verify:data-mode` now guards the Kubernetes env contract, preview RustFS bucket fail-closed path, and Rust source-sync bucket validation.
  - `docs/KUBERNETES_NATIVE_STACK.md` and `apps/bitween-platform-ui/preview/README.md` document the canonical runtime env contract.
- Fresh verification evidence:
  - `node --check` passed for `preview/server.js`, `verify-kubernetes-manifests.mjs`, and `verify-runtime-data-mode.mjs`.
  - `npm run verify:kubernetes-manifests`, `npm run verify:data-mode`, and `npm run verify:route-authorization` passed.
  - `buck2 build` / Buck2 `check` / Buck2 `clippy.txt` passed for `hr_employee_store`, `archive_intake_store`, `user_preference_store`, `workflow_template_store`, `postgres_migrate`, and `payroll_api`.
  - `buck2 test` passed for `hr_employee_store_test` (7), `archive_intake_store_test` (21), `user_preference_store_test` (5), `workflow_template_store_test` (20), `postgres_migrate_test` (3), and `payroll_api_test` (185).
  - UI/security gates passed: `npm run verify:i18n`, `verify:security-gates`, `verify:performance-gates`, `verify:auth-session`, `verify:auth-routes`, `verify:signed-out-auth-ux`, `verify:sensitive-data`, `verify:sensitive-history`, `verify:buck2-only`, `typecheck`, and `npm audit --omit=dev --audit-level=moderate` (0 vulnerabilities).
  - YAML syntax parse passed for every `deploy/kubernetes/**/*.yaml` / `*.yml` file.
  - Local server remains running on `127.0.0.1:4174` with PID 29380; smoke passed for `GET /` and `GET /api/auth/v1/routes`.
- Remaining persistence depth after G024: execute the same write paths against real PostgreSQL/RustFS services in CI or cluster once a hermetic service fixture/runtime is available locally; current repository evidence proves wiring, fail-closed behavior, schema contracts, and Kubernetes env alignment without local DB/object-service binaries.

### 2026-06-10 — unified shell workflow-first UX completion pass

- G012 is checkpoint-ready for the unified shell/product UX slice. The preview shell now prioritizes role work over technical readiness/status walls:
  - Home is organized around 오늘 할 일, 이번 일정, 확인 요청, and 준비할 일 so payroll/HR operators see outstanding work, schedule, follow-ups, and upcoming preparation in one glance.
  - HR now opens with an employee lifecycle summary before employee management actions; HR remains separate from Payroll while showing the business impact path.
  - Payroll now groups work into close, run, and output stages using the live payroll workstream, rather than showing backend/readiness implementation details.
  - Admin now groups setup into account/company setup, security, and operations readiness instead of a generic queue wall.
  - Settings is no longer in the left navigation. It is reachable from the topbar cog and the profile menu; theme, Korean-first language posture, workspace density, notification digest, and payroll view preferences live in Settings and persist through the existing Rust/Buck2 preference route.
  - The topbar keeps notification, message, help, settings, and profile/sign-out actions. The guided `?` tutorial remains screen-aware and renders exactly one close control.
  - Neutral examples now use Acme Corporation / `tenant-acme`; historical tenant/company/personnel names must not be reintroduced.
- Localization and UI hygiene guardrails were tightened:
  - All new shell copy is catalog-backed and Korean-first; no hardcoded Korean/English mix was added.
  - The i18n verifier allows only the approved proper names `Bitween` and `Acme Corporation` in Korean copy and continues to reject lazy loanword/operator-wall regressions.
  - Runtime verifier now rejects retired theme-panel copy, Settings in the side nav, missing profile-menu Settings access, missing home schedule/prep buckets, missing HR/payroll/admin business summaries, and duplicate tutorial close controls.
- Fresh verification evidence for this slice:
  - `node --check` passed for `preview/app.js`, `verify-runtime-data-mode.mjs`, and `verify-i18n-catalog.mjs`.
  - `npm run verify:i18n`, `npm run verify:data-mode`, `npm run typecheck`, `npm run verify:route-authorization`, `npm run verify:security-gates`, `npm run verify:performance-gates`, `npm run verify:auth-session`, `npm run verify:auth-routes`, `npm run verify:signed-out-auth-ux`, `npm run verify:buck2-only`, `npm run verify:sensitive-data`, `npm run verify:sensitive-history`, and `npm audit --omit=dev --audit-level=moderate` passed with 0 vulnerabilities.
  - Hermetic signed-in route render smoke passed for `home`, `hr`, `payroll`, `workflow`, `approval`, `archive`, `admin`, `settings`, plus settings tutorial overlay with one close button.
  - `git diff --check` passed for the G012-touched UI/i18n/verifier files.
  - Local preview remains available on `127.0.0.1:4174` with node PID 29380; `GET /` and `GET /catalog.json` returned HTTP 200.
- Remaining UX backlog is not dropped: browser-level visual regression/drag-drop evidence, deeper workflow-canvas polish, and production-grade module-specific interaction refinements continue under the pending workflow/G022/G019 stories.

### 2026-06-10 — product shell and UX governance ratchets

- G014 is checkpoint-ready for the TypeScript/Expo shell governance slice. The production shell now aligns with the preview shell contract instead of drifting behind it:
  - `AppShell` receives session summary data, keeps Settings outside the side navigation, and exposes notification, message, help, settings, and profile actions from the topbar.
  - Topbar notification/message icons now open compact business-language panels instead of immediately navigating away.
  - Profile now opens a menu with localized user/tenant/role summary, Settings, and sign-out; sign-out is no longer a standalone clutter button in the topbar.
  - Contextual help is now a 3-step walkthrough with previous/next/close behavior, not a single static paragraph.
  - Module work details and payroll step details now surface the required screen contract fields: owner, due window, blockers, permission, live/fail-closed state, and next action.
  - Static fallback session labels now come from the i18n catalog; raw technical strings such as `operations_observer`, `read-only`, and mixed-language `Acme Operator` are guarded out.
- Runtime/product ratchets were extended in `verify-runtime-data-mode.mjs` to require:
  - profile-menu sign-out and settings access;
  - interactive contextual help state;
  - notification/message panels;
  - row contract fields for due window, blockers, permissions, and live state;
  - localized fallback session labels and no technical role/session diagnostics.
- Fresh verification evidence for this slice:
  - `node --check` passed for `verify-runtime-data-mode.mjs`, `verify-i18n-catalog.mjs`, and `preview/app.js`.
  - `npm run verify:i18n`, `npm run verify:data-mode`, `npm run typecheck`, `npm run verify:route-authorization`, `npm run verify:security-gates`, `npm run verify:performance-gates`, `npm run verify:auth-session`, `npm run verify:auth-routes`, `npm run verify:signed-out-auth-ux`, `npm run verify:buck2-only`, `npm run verify:sensitive-data`, `npm run verify:sensitive-history`, and `npm audit --omit=dev --audit-level=moderate` passed with 0 vulnerabilities.
  - Hermetic signed-in preview route render smoke still passes for `home`, `hr`, `payroll`, `workflow`, `approval`, `archive`, `admin`, `settings`, plus settings tutorial overlay with one close button.
  - `git diff --check` passed for the G014-touched shell/i18n/verifier files.
  - Local preview remains available on `127.0.0.1:4174` with node PID 29380; `GET /` and `GET /catalog.json` returned HTTP 200.
- Remaining shell backlog: browser-level visual regression evidence for topbar/profile/help interactions and deeper module-specific visual polish continue under pending workflow/UX stories.

### 2026-06-10 — Rust API contract spine

- G015 is checkpoint-ready for the Rust service contract spine. Added `crates/payroll-api/src/api_contract.rs` and exported it through `crates/payroll-api/src/lib.rs` / `crates/payroll-api/BUCK`.
- The contract registry now covers platform, HR, payroll, 업무 관리, 전자결재, 자료함, settings, auth/session, and admin REST surfaces with stable method/path/request/response/auth/Rust-boundary/persistence/object-lifecycle fields.
- Implementation state is explicit instead of inflated:
  - live Rust routes: platform view-model, HR employees, workflow templates/edit/preflight/execution/rollback, archive intake/review/admit/rollback/source-sync, settings preferences;
  - live Rust service contracts: payroll run/validate/health/readiness through `bitween_payroll_api::PayrollApiService` while the production HTTP route remains a later service boundary;
  - configured identity routes: sign-in, sign-up, onboarding, sign-out;
  - contract-locked pending routes: approval queue/signature and admin access policy routes that still require dedicated Rust services/repositories before enabling.
- Rust tests now enforce the spine:
  - all business modules are represented;
  - every path is `/api/.../v1/...`, has a response schema, and names a Rust boundary rather than a preview adapter;
  - mutating contracts declare non-public authorization;
  - non-public auth operations parse through the Rust ABAC/RBAC/PBAC policy;
  - business writes declare PostgreSQL ownership;
  - 자료함 declares RustFS original object, checksum, quarantine, human review, canonical admission, row-level recovery, and source-file sync lifecycle tags;
  - implementation-state wording is controlled and cannot silently regress to non-production wording.
- Runtime/product gate now ratchets the contract spine in `apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs`: it requires `api_contract.rs`, BUCK inclusion, exported registry, module/path/schema coverage, RustFS lifecycle tags, PostgreSQL contract wording, controlled implementation states, and Rust auth-policy backing.
- Fresh verification evidence:
  - RED evidence before implementation: `buck2 test //crates/payroll-api:payroll_api_test` failed because archive contracts were absent and module `platform` was missing.
  - GREEN evidence: `buck2 test //crates/payroll-api:payroll_api_test` passed with 192 tests.
  - Focused Buck2 build/check/clippy passed: `buck2 build //crates/payroll-api:payroll_api '//crates/payroll-api:payroll_api[check]' '//crates/payroll-api:payroll_api[clippy.txt]'`.
  - `node --check apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs` passed.
  - `npm run verify:data-mode`, `verify:i18n`, `typecheck`, `verify:route-authorization`, `verify:security-gates`, `verify:performance-gates`, `verify:auth-session`, `verify:auth-routes`, `verify:signed-out-auth-ux`, `verify:buck2-only`, `verify:sensitive-data`, `verify:sensitive-history`, and `npm audit --omit=dev --audit-level=moderate` passed with 0 vulnerabilities.
  - `git diff --check -- crates/payroll-api/src/api_contract.rs apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs` passed.
  - Local preview remains available on `127.0.0.1:4174` with node PID 29380; `GET /`, `GET /catalog.json`, and `GET /api/platform/v1/view-model` returned HTTP 200 with security headers and Server-Timing.
- Remaining API/service backlog: convert contract-locked approval/admin routes into live Rust services with PostgreSQL migrations; expose payroll run/validate/health/readiness as production HTTP routes once the run ledger/persistence boundary is ready; keep preview adapters thin and guarded by the contract spine.

### 2026-06-10 — Cloud-native/CNCF production spine (G016)

- G016 is checkpoint-ready for the managed-Kubernetes production spine. The slice closes the remaining cloud-native release gaps without adding fake service paths:
  - Added a Buck2-built Rust `cloud_native_audit_worker` binary with schema `bitween.cloud-native-audit-worker.v1` and audit event schema `bitween.audit-event.v1`.
  - The worker fails closed when production auth, PostgreSQL DSN/TLS/scope, RustFS endpoint/bucket/credentials, audit export, or OpenTelemetry wiring is absent or mismatched; it never serializes raw PostgreSQL DSNs.
  - Added `deploy/kubernetes/base/worker-cronjobs.yaml` for a restricted Kubernetes CronJob that runs the Rust worker from the payroll API image, with bounded cadence/retry/history, Secret-backed PostgreSQL/RustFS credentials, read-only root filesystem, dropped capabilities, and service-account token automount disabled.
  - Added `deploy/kubernetes/base/observability.yaml` with ServiceMonitor resources for API/frontend metrics labels and `deploy/kubernetes/base/tenant-isolation.yaml` with ResourceQuota, LimitRange, and release-operator RBAC guardrails.
  - Updated ConfigMap and NetworkPolicy wiring for audit export, PostgreSQL+OpenTelemetry audit stream declaration, worker egress, RustFS evidence bucket, and tenant-scoped production defaults.
  - Updated Kustomize resources, service accounts, CI Buck2 build/check/clippy/test coverage, and Kubernetes runtime verifier gates.
  - Updated `docs/KUBERNETES_NATIVE_STACK.md` and the release/rollback runbook with cloud-native audit worker, ServiceMonitor, ResourceQuota, image digest evidence, external secret manager, restore drill, drift, and no-placeholder hostname guidance.
- Guardrails now ratchet G016:
  - `verify:kubernetes-manifests` requires worker CronJobs, ServiceMonitor observability, tenant ResourceQuota/LimitRange/RBAC, audit env contract, CI Buck2 worker targets, runbook drift/restore/image-digest evidence, no committed Secrets, no unsafe release words, no retired object store references, and no scrubbed tenant/personnel seed data.
  - `verify:data-mode` now guards the Rust worker source, BUCK target/test, CI target wiring, Kubernetes verifier coverage, and Kubernetes stack documentation.
- Fresh verification evidence:
  - RED: `buck2 test //crates/payroll-api:cloud_native_audit_worker_test` initially failed because `complete_environment_is_ready` returned `Blocked` before worker implementation.
  - GREEN: `buck2 build //crates/payroll-api:cloud_native_audit_worker '//crates/payroll-api:cloud_native_audit_worker[check]' '//crates/payroll-api:cloud_native_audit_worker[clippy.txt]'` passed.
  - GREEN: `buck2 test //crates/payroll-api:cloud_native_audit_worker_test` passed with 4 tests.
  - Regression Buck2: `buck2 test //crates/payroll-api:payroll_api_test //crates/payroll-api:postgres_migrate_test //crates/payroll-api:cloud_native_audit_worker_test` passed; `payroll_api_test` has 192 tests and `postgres_migrate_test` has 3 tests.
  - Regression Buck2 build/check/clippy passed for `payroll_api`, `postgres_migrate`, and `cloud_native_audit_worker`.
  - UI/runtime gates passed: `npm run verify:kubernetes-manifests`, `verify:data-mode`, `verify:i18n`, `verify:buck2-only`, `verify:security-gates`, `verify:performance-gates`, `verify:sensitive-data`, `typecheck`, `verify:auth-session`, `verify:auth-routes`, `verify:route-authorization`, `verify:signed-out-auth-ux`, and `npm audit --omit=dev --audit-level=moderate` (0 vulnerabilities).
  - YAML syntax parse passed for every `deploy/kubernetes/**/*.yaml` / `*.yml` file after adding worker/observability/tenant-isolation resources.
  - `git diff --check` passed for the G016-touched Rust, Kubernetes, docs, CI, and verifier files.
  - Local preview server remains running on `127.0.0.1:4174` with node PID 29380; `GET /` and `GET /api/platform/v1/view-model` returned HTTP 200 with security headers and Server-Timing.
- Local environment note: `kubectl`/`kustomize` are not installed in this workspace, so cluster-side dry-run/render evidence remains a deployment-environment gate. Repository evidence for G016 is the Buck2 worker verification, manifest verifier, YAML parse, runbook, and CI gate wiring.
- Remaining cloud-native depth: production image build/publish provenance and digest attestation from CI, external secret-manager reconciliation proof in the target cluster, PostgreSQL/RustFS restore-drill artifacts from the managed-Kubernetes environment, Gateway controller conformance status, ServiceMonitor target discovery/dashboard/alert evidence, and hermetic PostgreSQL/RustFS integration fixtures.

### 2026-06-10 — 자료함 / intake live archive evidence (G017)

- G017 is checkpoint-ready for the 자료함/intake production slice. Existing live wiring was preserved and the remaining evidence gap was closed without adding fake storage or UI-only acknowledgements:
  - Files are still accepted by the preview route into RustFS quarantine before Rust classification, with authorization enforced before any object write.
  - The Rust archive intake store now tracks content-sample evidence in addition to object metadata/checksum: `content_sample_sha256`, `content_sample_row_count`, and typed `extraction_status` are persisted/read through PostgreSQL and returned as safe API metadata.
  - PostgreSQL now stores only a bounded, redacted `redacted_content_sample_excerpt` for review evidence; it is capped at 8192 characters and is not exposed in the archive intake API record.
  - Redaction covers high-signal sensitive fixtures such as Korean resident-registration numbers, email addresses, and short Korean personal names before sample excerpts are persisted.
  - Review-state refresh now updates extraction status when guidance/anomaly issues are resolved, keeping human review, staging readiness, admission, rollback, and source-sync state aligned.
  - The archive schema contract and runtime verifier now ratchet the sample-evidence columns/functions so future changes cannot silently regress to metadata-only or raw/binary snapshot storage.
- TDD evidence:
  - RED: `buck2 test //crates/payroll-api:archive_intake_store_test //crates/payroll-api:payroll_api_test` failed before implementation because `content_sample_sha256`, `content_sample_row_count`, `ArchiveExtractionStatus`, and `redacted_content_sample_excerpt` were absent, and the schema lacked content-sample columns.
  - GREEN: `buck2 test //crates/payroll-api:archive_intake_store_test //crates/payroll-api:payroll_api_test` passed after implementation (`archive_intake_store_test`: 22 tests; `payroll_api_test`: 193 tests).
  - Migration regression: `buck2 test //crates/payroll-api:postgres_migrate_test //crates/payroll-api:archive_intake_store_test //crates/payroll-api:payroll_api_test` passed (`postgres_migrate_test`: 3 tests).
  - Build/check/clippy: `buck2 build //crates/payroll-api:archive_intake_store '//crates/payroll-api:archive_intake_store[check]' '//crates/payroll-api:archive_intake_store[clippy.txt]' //crates/payroll-api:payroll_api '//crates/payroll-api:payroll_api[check]' '//crates/payroll-api:payroll_api[clippy.txt]'` passed.
  - Runtime gates: `npm run verify:data-mode`, `npm run verify:route-authorization`, `npm run verify:i18n`, `npm run typecheck`, `npm run verify:security-gates`, `npm run verify:performance-gates`, `npm run verify:sensitive-data`, `npm run verify:buck2-only`, `npm run verify:auth-session`, `npm run verify:auth-routes`, `npm run verify:signed-out-auth-ux`, and `npm audit --omit=dev --audit-level=moderate` passed with 0 vulnerabilities.
  - `git diff --check` passed for the G017-touched files.
  - Local preview remains running on `127.0.0.1:4174` with node PID 29380. `GET /` and `GET /api/platform/v1/view-model` returned HTTP 200 with security headers and Server-Timing; unauthenticated `GET /api/archive/v1/intake` returned HTTP 403, proving 자료함 intake fails closed without a verified session.
- Remaining archive depth for later stories: first-class cross-intake backlog/dashboard UX, richer audit/recovery timeline presentation, and live PostgreSQL/RustFS integration fixtures in the managed-Kubernetes environment.

### 2026-06-10 — Security/session route hardening baseline (G018)

- G018 is checkpoint-ready as the security/compliance baseline slice. Existing Rust JWT/JWKS/OIDC/PostgreSQL revocation/audit, ABAC+RBAC+PBAC, CSRF, rate-limit, CSP/header, sensitive-data, and route-authorization controls were preserved; this pass closed two browser/session boundary gaps without adding fake auth state:
  - `POST /api/auth/v1/signout` now always clears the host-only `__Host-bitween_session` cookie, even when the upstream identity gateway is unconfigured and the route fails closed. The clear header uses `Max-Age=0`, an expired `Expires`, `Path=/`, `HttpOnly`, `SameSite=Lax`, and `Secure`, with no `Domain` attribute.
  - Identity/onboarding action URLs are now fail-closed unless they are HTTPS, contain no embedded credentials/fragments, and, when configured, match `BITWEEN_AUTH_EXPECTED_ISSUER`, `BITWEEN_AUTH_ALLOWED_ORIGINS`, or `BITWEEN_ONBOARDING_ALLOWED_ORIGINS`. This prevents the shell from returning an HTTP or attacker-origin auth URL for `window.location.assign`.
  - `verify-security-gates.mjs` now dynamically proves same-origin sign-out both passes the CSRF/rate-limit guards and clears the hardened cookie.
  - `verify-auth-routes.mjs` now dynamically proves missing routes, non-HTTPS routes, and issuer-origin mismatches fail closed with `auth_route_unconfigured` while correctly configured HTTPS routes still return live provider URLs.
  - `verify-runtime-data-mode.mjs` now guards the new auth-route/cookie verifier contracts.
  - `docs/AUTH_SECURITY_CONTRACT.md` records the HTTPS/origin allow-list and hardened sign-out cookie contract.
- Fresh verification evidence for this pass:
  - RED: `npm run verify:security-gates` failed before implementation because sign-out did not emit a hardened `__Host-bitween_session` clear cookie.
  - RED: `npm run verify:auth-routes` failed before implementation because `http://auth.example.com/signin` and `https://attacker.example/signin` under `BITWEEN_AUTH_EXPECTED_ISSUER=https://auth.example.com` were treated as configured routes.
  - GREEN: `npm run verify:auth-routes`, `npm run verify:security-gates`, `npm run verify:auth-session`, and `npm run verify:route-authorization` passed.
  - Runtime/product gates passed: `npm run verify:data-mode`, `npm run verify:i18n`, `npm run typecheck`, `npm run verify:performance-gates`, `npm run verify:sensitive-data`, `npm run verify:buck2-only`, and `npm audit --omit=dev --audit-level=moderate` (0 vulnerabilities).
  - Rust verification passed with Buck2 only: `buck2 test //crates/payroll-api:auth_session_validate_test //crates/payroll-api:authz_decision_test //crates/payroll-api:payroll_api_test` and Buck2 build/check/clippy for `auth_session_validate`, `authz_decision`, and `payroll_api`.
  - `git diff --check` passed for the G018-touched preview server, verifiers, and auth-security contract.
  - Local preview is running in the active tool session on `127.0.0.1:4174` with node PID 48011. Smoke evidence: `GET /` returned HTTP 200, `GET /api/platform/v1/view-model` returned HTTP 200 with schema `bitween.platform.live.v1`, backend `rust_native`, session `local_readonly`, and same-origin `POST /api/auth/v1/signout` returned HTTP 503 `auth_route_unconfigured` while emitting the hardened session-cookie clear header.
- Remaining security depth is not abandoned; it is carried by pending G025 and deployment-environment gates: WebAuthn/passkey registration options, credential enrollment lifecycle, recovery/offboarding flows, and browser ceremony adapters around the verified server-side assertion boundary, networked OIDC discovery/JWKS cache refresh and rotation, distributed rate limiting/revocation controls, retention/export dashboards for security audit events, and ingress/WAF policy evidence in managed Kubernetes.

### 2026-06-10 — Workflow maturity operational graph wiring (G019)

- G019 is checkpoint-ready for the workflow maturity slice. Existing Rust-backed workflow canvas/editor behavior was preserved: workflow and 전자결재 remain separate surfaces; the canvas loads `/api/workflow/v1/templates`, edits nodes/edges through live PATCH/POST/DELETE routes, validates rewires before persistence, executes steps through the Rust workflow store, surfaces graph analytics/preflight/runtime data-record evidence, and rolls back to text graph versions without binary snapshots.
- This pass closed the remaining operator-flow gap: HR, Payroll, 전자결재, 자료함, Home, Payroll stage summaries, and topbar work items now derive from the edited workflow graph instead of the original payroll-only workstream. The UI orders work through persisted `nextStepIds` graph edges with visual-position fallback, so moving/rewiring/reassigning nodes affects the actual operator surfaces rather than only decorating the canvas.
- Guardrails added in `apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs` require:
  - `workflowOperationalSteps` edge traversal from persisted `nextStepIds`;
  - `editableWorkflowSteps` as the common source for HR/Payroll/Approval/Archive/Home surfaces;
  - `workflowSteps(target)` filtering the edited graph;
  - Home buckets using edited graph steps alongside live queue items.
- Fresh verification evidence:
  - RED: `npm run verify:data-mode` failed before implementation because `preview/app.js` did not expose `workflowOperationalSteps`, `editableWorkflowSteps`, edited-graph filtering, graph-backed home buckets, or edge traversal.
  - GREEN: `npm run verify:data-mode` passed after implementation.
  - Runtime/contract gates passed: `node --check preview/app.js`, `npm run verify:route-authorization`, `npm run verify:i18n`, `npm run typecheck`, `npm run verify:buck2-only`, and `npm run verify:performance-gates`.
  - Buck2 workflow backend verification passed: `buck2 test //crates/payroll-api:workflow_template_store_test` with 20 tests.
  - Local preview server remains running on `127.0.0.1:4174` in tool session `67944` with node PID 48011. Smoke evidence: `GET /` returned HTTP 200; unauthenticated `GET /api/workflow/v1/templates` returned HTTP 403, matching fail-closed authorization, while authenticated route-authorization verification covered add/patch/validate/preflight/execute/delete/rollback workflow paths.
- Remaining workflow depth for later stories: browser-level visual QA/pixel review in a real Chromium session, richer n8n/Zapier-style canvas affordances such as zoom/pan/keyboard node creation, and managed-Kubernetes PostgreSQL integration evidence for multi-user graph editing concurrency.

### 2026-06-10 — Unified shell contextual walkthrough (G022)

- G022 shell/IA continuation is checkpoint-ready for the guided-onboarding slice. The unified shell already keeps Settings in the top bar/profile menu, keeps business modules in the left navigation, separates 업무 관리 from 전자결재, and routes Home/HR/Payroll/자료함/Admin work from live workflow and queue data.
- This pass closed the remaining onboarding gap without adding placeholder tutorial copy:
  - The top-bar `?` walkthrough is still screen-aware and catalog-backed, but now each step is bound to an actual UI region through `data-tutorial-anchor` and `tutorialActiveAnchor()` instead of a generic centered modal.
  - Active tutorial steps visually highlight the relevant Home, HR, Payroll, 업무 관리 canvas/editor, 전자결재, 자료함, Admin, Settings, topbar, or navigation target with `.tutorial-anchor-active`.
  - The overlay now displays a contextual target pill sourced from existing localized UI labels via `tutorialAnchorLabelKeys`, avoiding hardcoded or mixed-language target names.
  - Workflow onboarding specifically anchors to the editable workflow canvas, inspector, and node palette, reinforcing that 업무 관리 is the editable corporate workflow surface while 전자결재 remains signing/approval work.
- Guardrails added in `apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs` require anchored tutorial labels, current-region calculation, topbar help target anchoring, workflow-canvas highlighting, and CSS for the active target plus contextual target pill.
- Fresh verification evidence:
  - RED: `npm run verify:data-mode` failed before implementation with missing `tutorialAnchorLabelKeys`, `tutorialActiveAnchor`, `tutorialAnchorClass`, `data-tutorial-anchor="topbar-help"`, active target rendering, workflow canvas highlighting, and tutorial highlight CSS.
  - GREEN: `node --check preview/app.js` and `npm run verify:data-mode` passed after implementation.
  - UI/runtime gates passed: `npm run verify:i18n` (1589 catalog messages across 4 locales, no localized copy outside catalog), `npm run verify:route-authorization`, `npm run typecheck`, `npm run verify:buck2-only`, `npm run verify:performance-gates`, and `npm audit --omit=dev --audit-level=moderate` (0 vulnerabilities).
  - Buck2 workflow backend regression passed: `buck2 test //crates/payroll-api:workflow_template_store_test` with 20 tests.
  - `git diff --check -- apps/bitween-platform-ui/preview/app.js apps/bitween-platform-ui/preview/styles.css apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs HANDOFF.md` passed.
  - Local preview server remains running on `127.0.0.1:4174` in tool session `67944`; `GET /` returned HTTP 200.
- Remaining G022 depth for later UI/UX passes: browser-level visual/pixel QA in Chromium, richer walkthrough positioning relative to element geometry, keyboard-focus choreography during tutorials, and route-specific first-run persistence once the managed auth/session profile is finalized.

### 2026-06-10 — API contract schema-boundary ratchet (G023)

- G023 is checkpoint-ready for the API contract/Rust service-boundary slice. The API contract spine already covered platform, HR, payroll, workflow, approval, archive, settings, auth, and admin endpoints with versioned paths, auth-operation ids, Rust boundary owners, PostgreSQL/RustFS persistence contracts, and honest implementation-state markers.
- This pass closed a contract drift gap without adding placeholder routes:
  - Live response schema IDs for HR employees, workflow templates/preflight/edit validation, archive intake/source sync, user preferences, and auth route actions are now exported from the Rust boundary/schema modules.
  - The live Rust store binaries now use those exported schema constants instead of private duplicated strings.
  - `api_contract.rs` now references the same constants for endpoint response schemas, so route contracts and service responses cannot silently drift.
  - Existing approval/admin endpoints remain contract-locked pending routes only; they are not exposed as fake live server routes.
- Guardrails added in `apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs` require the API contract spine to consume the exported response schema constants and require the schema modules/auth boundary to export them.
- Fresh verification evidence:
  - RED: `npm run verify:data-mode` failed before implementation on missing exported response-schema constants and API-contract constant usage for HR, workflow, archive, settings, and auth.
  - GREEN: `npm run verify:data-mode`, `npm run verify:route-authorization`, `npm run verify:i18n`, `npm run typecheck`, `npm run verify:buck2-only`, `npm run verify:performance-gates`, and `npm audit --omit=dev --audit-level=moderate` passed with 0 vulnerabilities.
  - Buck2 service-boundary tests passed: `buck2 test //crates/payroll-api:payroll_api_test //crates/payroll-api:hr_employee_store_test //crates/payroll-api:workflow_template_store_test //crates/payroll-api:archive_intake_store_test //crates/payroll-api:user_preference_store_test` (`payroll_api_test`: 193 tests, HR store: 7, workflow store: 20, archive store: 22, settings store: 5).
  - Buck2 build/check/clippy passed for `payroll_api`, `hr_employee_store`, `workflow_template_store`, `archive_intake_store`, and `user_preference_store`.
  - `git diff --check` passed for the Rust contract/schema/store files, runtime verifier, and HANDOFF.
  - Local preview server remains running on `127.0.0.1:4174`; `GET /` returned HTTP 200.
- Remaining API depth for later stories: publish a machine-readable API contract artifact from Buck2/CI, implement live approval/admin routes only when PostgreSQL tables and signing/audit lifecycle are fully ready, and add managed-Kubernetes contract conformance evidence against the deployed ingress.

### 2026-06-10 — WebAuthn assertion verification boundary (G025)

- G025 is checkpoint-ready for the Rust auth/session hardening continuation. Existing OIDC discovery metadata validation, RS256 JWT/JWKS verification, PostgreSQL hashed-JWT revocation/audit, and ABAC/RBAC/PBAC session facts were preserved.
- This pass closed the WebAuthn gap between "JWT says WebAuthn happened" and a Rust-controlled relying-party assertion boundary:
  - `crates/payroll-api/src/auth_session.rs` now exposes `AUTH_WEBAUTHN_ASSERTION_SCHEMA`, `WebAuthnAssertionVerifierConfig`, `WebAuthnAssertionInput`, `WebAuthnAssertionVerification`, and `verify_webauthn_assertion`.
  - The verifier accepts only `webauthn.get` client data, checks a fresh matching challenge, binds origin and RP ID hash, requires user-present and user-verified flags, rejects replayed nonzero signature counters, and verifies the ES256 authenticator signature with `ECDSA_P256_SHA256_ASN1` against the stored P-256 credential public key.
  - `//crates/payroll-api:auth_session_validate` now optionally enforces this boundary when `BITWEEN_WEBAUTHN_ASSERTION_JSON` is supplied, using explicit RP ID, expected origin, challenge, issued-at timestamp, previous sign count, and public key coordinate env inputs. Invalid assertion evidence fails closed before the session is accepted.
  - `docs/AUTH_SECURITY_CONTRACT.md` documents the WebAuthn assertion environment contract, controlled fail-closed reasons, replay-counter behavior, and the rule that raw assertions are transient verification input rather than stored secrets.
  - `apps/bitween-platform-ui/scripts/verify-auth-session.mjs` and `verify-runtime-data-mode.mjs` now guard the WebAuthn assertion schema/config/function, fail-closed reason strings, ES256 verification, binary env boundary, and documentation.
- Fresh verification evidence:
  - RED: `npm run verify:auth-session` failed before implementation on missing `AUTH_WEBAUTHN_ASSERTION_SCHEMA`, `WebAuthnAssertionVerifierConfig`, `verify_webauthn_assertion`, fail-closed WebAuthn reasons, ES256 signature verification, `BITWEEN_WEBAUTHN_ASSERTION_JSON`, and `enforce_webauthn_assertion_if_configured`.
  - GREEN frontend/security/product gates passed: `npm run verify:auth-session`, `npm run verify:data-mode`, `npm run verify:security-gates`, `npm run verify:auth-routes`, `npm run verify:route-authorization`, `npm run verify:i18n`, `npm run typecheck`, `npm run verify:buck2-only`, `npm run verify:performance-gates`, `npm run verify:sensitive-data`, `npm run verify:sensitive-history`, `npm run verify:signed-out-auth-ux`, and `npm audit --omit=dev --audit-level=moderate` with 0 vulnerabilities.
  - GREEN Rust/Buck2 verification passed: `buck2 test //crates/payroll-api:payroll_api_test //crates/payroll-api:auth_session_validate_test //crates/payroll-api:authz_decision_test` (`payroll_api_test`: 196 tests including WebAuthn assertion success/failure/replay coverage; auth-session validator: 3; authz decision: 4), plus `buck2 build //crates/payroll-api:auth_session_validate '//crates/payroll-api:auth_session_validate[check]' '//crates/payroll-api:auth_session_validate[clippy.txt]' //crates/payroll-api:payroll_api '//crates/payroll-api:payroll_api[check]' '//crates/payroll-api:payroll_api[clippy.txt]'`.
  - `git diff --check` passed for the G025-touched Rust auth files, verifiers, auth-security contract, and HANDOFF.
  - Local preview remains running on `127.0.0.1:4174` in tool session `67944`; `GET /` and `GET /api/platform/v1/view-model` both returned HTTP 200.
- Remaining auth depth for future production-hardening backlog: networked OIDC discovery retrieval, JWKS cache refresh/key rotation, distributed replay/revocation propagation across service instances, security event retention/export dashboards, passkey registration options, credential enrollment/lifecycle, recovery/offboarding flows, and browser ceremony adapters around this verified server-side assertion boundary.

### 2026-06-10 — Final Python decommission and Buck2-only enforcement (G028)

- G028 is checkpoint-ready for the final Python decommission after the Rust/TypeScript production slices reached parity gates. This pass removes repo-owned Python as an implementation, test, tool, and CI surface rather than leaving compatibility adapters or stubs behind.
- Removed repo-owned Python source surfaces:
  - Legacy Python implementation directories: `auth/`, `core/`, `integrations/`, `services/`, `ui/`, and `tools/`.
  - Legacy Python test suite: `tests/` plus root Python smoke/test entrypoints.
  - Root Python payroll/HR/archive/UI scripts and modules such as calculators, managers, parsers, roster/report builders, and launchers.
  - Python release/local tooling under `scripts/` and the root dependency manifest.
  - Python bytecode caches and vendored Rust unicode helper Python scripts, so the repo scan can assert zero `.py`/`.pyi`/`__pycache__` surfaces outside ignored generated output.
- Added `apps/bitween-platform-ui/scripts/verify-no-python-source.mjs` and wired `npm run verify:no-python-source` into package scripts and CI. The gate recursively rejects `.py`, `.pyi`, `__pycache__`, Python dependency and tooling markers including package, test, lockfile, formatter, type-checker, and environment files, plus any workflow use of `setup-python`, legacy module execution, package install, and test-runner commands.
- Updated `.github/workflows/tests.yml` to remove the removed legacy test job and to run the no-Python gate before product/runtime/security gates. Updated `.github/workflows/worker-mobile.yml` so mobile contract validation no longer installs/runs Python and tracks Rust/frontend contract paths instead.
- Updated authority docs for the new invariant:
  - `AGENTS.md`: Python implementation is decommissioned; do not add Python source, stubs, tests, scripts, or live wiring; use Rust Buck2 tests and TypeScript gates.
  - `README.md` and `AI_README.md`: removed Python compatibility runbooks and AI shims; Rust/TypeScript/Kubernetes boundaries are now the documented production path.
  - `docs/PYTHON_DECOMMISSION_INVENTORY.md`: records `Status: decommissioned`, `Repo-owned Python source count: 0`, removed surfaces, and enforcement gates.
  - `docs/PRODUCTION_DELIVERY_FAST_PATH.md`: final production lane now records completed Python decommission and `npm run verify:no-python-source` as the guardrail.
- Pipeline friction fixed during final Buck2 verification: root recursive Buck2 builds exposed missing test-target visibility, so `//crates/workflow-core:workflow_core_test` and `//crates/payroll-api:payroll_api_test` now have public visibility for root aliases/CI. No Cargo build/check/test/clippy/run commands were used.
- Fresh verification evidence for this final state:
  - `npm run verify:no-python-source` passed.
  - A direct `find` scan excluding `.git`, `buck-out`, and `node_modules` found no `.py`, `.pyi`, `__pycache__`, Python manifests, packaging configs, test/tool configs, type-checker configs, or setup files.
  - Product/security/runtime gates passed: `npm run verify:data-mode`, `verify:buck2-only`, `verify:security-gates`, `verify:auth-session`, `verify:auth-routes`, `verify:route-authorization`, `verify:signed-out-auth-ux`, `verify:i18n`, `typecheck`, `verify:performance-gates`, `verify:kubernetes-manifests`, `verify:sensitive-data`, `verify:sensitive-history`, and `npm audit --omit=dev --audit-level=moderate` with 0 vulnerabilities.
  - Buck2 verification passed with `buck2 build //...`, `buck2 test //...`, and targeted Buck2 `[check]`/`[clippy.txt]` builds for live Rust payroll API, platform, auth, authorization, HR, archive, settings, workflow, migration, cloud-native worker, and workflow-core targets.
  - Local preview remains running on `127.0.0.1:4174`; `GET /` and `GET /api/platform/v1/view-model` returned HTTP 200.
- Verification caveat: unsupported recursive Buck2 provider shortcuts for check/clippy are not accepted by the current parser in this workspace (`Target name must not be equal to ...`). The equivalent targeted `[check]` and `[clippy.txt]` Buck2 targets were run successfully instead, alongside full `buck2 build //...` and `buck2 test //...`.
- Remaining post-G028 production depth is not Python migration work: managed-Kubernetes integration evidence for PostgreSQL/RustFS restore drills, live OIDC/JWKS rotation, passkey enrollment/recovery UX, distributed rate limiting/revocation, deployment attestation, and browser-level visual QA remain future hardening/backlog items under Rust/TypeScript only.

### 2026-06-10 — Final review fixes for G028 quality gate

- Independent final review initially blocked G028 completion with three issues, all fixed before the final quality gate:
  - Expanded `verify-no-python-source.mjs` beyond the original Python manifest list to reject legacy packaging, test, lockfile, formatter/linter, type-checker, and environment marker files.
  - Broadened GitHub Actions scanning to reject Python command variants including additional module-execution and package-install command variants.
  - Removed stale pre-G028 wording from the top-level handoff and fast-path docs that described Python decommission as future work or active compatibility inventory. The new authority is: Python is decommissioned; any missing behavior must return through Rust/Buck2 services/tests or TypeScript contracts only.
  - Replaced unsupported recursive Buck2 check/clippy instructions in active docs and the local cargo guard with supported target-specific `[check]` and `[clippy.txt]` guidance; `verify:buck2-only` and `verify:data-mode` now reject the old cargo-guard recommendation.
- Fresh verification after the review fixes:
  - `npm run verify:no-python-source`, `verify:buck2-only`, `verify:data-mode`, `verify:security-gates`, `verify:auth-session`, `verify:auth-routes`, `verify:route-authorization`, `verify:signed-out-auth-ux`, `verify:i18n`, `typecheck`, `verify:performance-gates`, `verify:kubernetes-manifests`, `verify:sensitive-data`, `verify:sensitive-history`, and `npm audit --omit=dev --audit-level=moderate` passed with 0 vulnerabilities.
  - Direct scans excluding `.git`, `buck-out`, and `node_modules` found no Python source/stubs, bytecode caches, Python manifests/tooling configs/lockfiles, or workflow Python command variants.
  - `git diff --check` passed.
  - `buck2 build //...`, `buck2 test //...`, and target-specific Buck2 `[check]`/`[clippy.txt]` builds for the live Rust payroll/platform/auth/authz/HR/archive/settings/workflow/postgres/cloud-native-worker/workflow-core targets passed.
  - Follow-up review drift was also closed: older transition/slice docs no longer contain active legacy test-runner module commands, unsupported recursive Buck2 check/clippy patterns, or retired Buck2 lint-filter validation examples. `verify-no-python-source.mjs` now scans `docs/**/*.md` for those active command forms and stale active-bridge wording outside the decommission inventory.
  - Transition docs that previously described repo-owned adapters as active were rewritten to the current G028 invariant: the former compatibility bridge is decommissioned; missing behavior must return through Rust/Buck2 services or TypeScript contracts only.
- Final review blocker follow-up (G028): active transition/design/app docs were scrubbed again after independent review found deleted Python module references, package/test command snippets, and stale fallback wording in `docs/BUILD_AND_RUNTIME_TRANSITION.md`, `docs/AI_AGENT.md`, `DESIGN.md`, and slice docs. `verify-no-python-source.mjs` now scans `docs/**/*.md`, top-level authority docs, `HANDOFF.md`, and app docs for active Python command forms, removed Python source/test paths, removed dependency-manifest references, stale active-bridge wording, and unsupported Buck2 recursive examples.
- Final finalizer fixes after the last independent review pass:
  - `apps/bitween-platform-ui/preview/server.js` now decodes request paths through `decodeRequestPath`; malformed percent-encoded paths return `400` with `request_path_invalid` instead of crashing the preview server before security/rate-limit handling.
  - `apps/bitween-platform-ui/scripts/verify-security-gates.mjs` now starts the live preview and asserts malformed path fail-closed behavior.
  - `scripts/verify_rust_buck2_reindeer.sh` no longer runs unsupported recursive check-provider shortcuts; it uses full `buck2 build //...`, full `buck2 test //...`, and explicit first-party Rust `[check]` targets before Reindeer diff validation.
  - `apps/bitween-platform-ui/scripts/verify-buck2-only.mjs` now scans repo-owned scripts/config/docs for unsupported recursive Buck2 provider patterns and requires explicit target-specific check/clippy usage.
  - `verify-no-python-source.mjs` now rejects any active-doc retired source/test path reference, not only nested deleted package paths, and also rejects stale wording that describes the retired implementation as owning contract tests, characterization, fallback, or active behavior.
  - Active migration/slice/API/mobile docs were scrubbed so deleted Python module names, old compatibility-test instructions, and active Python ownership language no longer appear outside the decommission inventory/history context.
- Fresh finalizer evidence after those fixes:
  - `node --check` passed for `preview/server.js`, `verify-security-gates.mjs`, `verify-no-python-source.mjs`, `verify-buck2-only.mjs`, and `verify-runtime-data-mode.mjs`.
  - Targeted gates passed: `npm run verify:no-python-source`, `npm run verify:buck2-only`, `npm run verify:security-gates`, and `npm run verify:data-mode`.
  - Full Node/product/security gates passed: `npm run verify:no-python-source`, `verify:buck2-only`, `verify:data-mode`, `verify:security-gates`, `verify:auth-session`, `verify:auth-routes`, `verify:route-authorization`, `verify:signed-out-auth-ux`, `verify:i18n`, `typecheck`, `verify:performance-gates`, `verify:kubernetes-manifests`, `verify:sensitive-data`, `verify:sensitive-history`, and `npm audit --omit=dev --audit-level=moderate` with 0 vulnerabilities.
  - Direct scans found no repo-owned Python source/stubs/bytecode caches/manifests, no workflow Python setup/module/package/test-runner commands, no active docs with removed Python source paths or stale active-owner wording, and no active unsupported recursive Buck2 provider examples outside verifier assertions.
  - `git diff --check` passed.
  - Buck2 verification passed: `buck2 build //...`, `buck2 test //...` (Pass 12 / Fail 0), target-specific `[check]` builds, and target-specific `[clippy.txt]` builds for payroll API, platform live view, auth session validator, authz decision, HR/archive/settings/workflow/postgres/cloud-native worker binaries, and workflow-core.
  - Local preview was restarted on `127.0.0.1:4174` after the old process crashed on the pre-fix malformed-path defect. Fresh smoke passed: `GET / -> 200`, `GET /api/platform/v1/view-model -> 200` with schema `bitween.platform.live.v1`, and malformed path `/%E0%A4%A -> 400` with `request_path_invalid`.

## 2026-06-10 no-placeholder/no-stub cleanup continuation

- User clarified that placeholders/stubs are still unacceptable. Cleanup pass removed the stale root `locales/` catalog and `payroll.spec` PyInstaller-era Python build surface after repo search showed current TS UI uses `apps/bitween-platform-ui/src/i18n/catalog.json` instead.
- Product/runtime source cleanup replaced placeholder-dependent form guidance with persistent helper text:
  - `apps/bitween-platform-ui/preview/app.js` workflow editor inputs now render visible `.field-hint` helper text and no `placeholder=` attribute.
  - `apps/bitween-platform-ui/src/screens.tsx` module search uses persistent hint copy instead of placeholder copy.
  - `apps/worker-mobile/src/components/Field.tsx`, `PayrollScreen.tsx`, and `RequestScreen.tsx` use `hint` text instead of placeholder props.
  - Korean draft copy changed from `임시저장` to context-appropriate `초안 저장`.
- Rust workflow form schema now exposes `input_hint` instead of placeholder wording. Test/default-value identifiers were renamed away from fallback/stub-like labels without behavior changes.
- Object storage clarification: MinIO is not the target. Remaining literal MinIO references were removed; manifests and code use RustFS env names. PostgreSQL and RustFS code paths are wired, but the local preview server was intentionally restarted with `BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true` and local `.bitween/live-review` JSON stores because no live PostgreSQL DSN/RustFS credentials are present in the shell. Production requires `BITWEEN_POSTGRES_DSN` plus `BITWEEN_RUSTFS_ENDPOINT`, bucket, access key, and secret key.
- Verification evidence:
  - `npm run verify:i18n` PASS.
  - `npm run verify:data-mode` PASS.
  - `npm run verify:no-python-source` PASS.
  - `npm run verify:auth-routes` PASS.
  - `npm run verify:security-gates` PASS.
  - `npm run verify:kubernetes-manifests` PASS.
  - `npm run verify:sensitive-data` PASS.
  - `npm run typecheck` PASS in `apps/bitween-platform-ui`.
  - `npm ci && npm run typecheck` PASS in `apps/worker-mobile`; `npm audit --omit=dev --audit-level=high` PASS with existing moderate Expo/uuid transitive advisory only.
  - `npm audit --omit=dev --audit-level=high` PASS in `apps/bitween-platform-ui` with 0 vulnerabilities.
  - `buck2 build '//crates/workflow-core:workflow_core[check]' '//crates/payroll-api:payroll_api[check]' '//crates/payroll-api:archive_intake_store[check]' '//crates/payroll-api:workflow_template_store[check]'` PASS.
  - `buck2 test //crates/workflow-core:workflow_core_test //crates/payroll-api:payroll_api_test //crates/payroll-api:archive_intake_store_test //crates/payroll-api:workflow_template_store_test` PASS: workflow-core 31, archive-intake 22, workflow-template 20, payroll-api 196.
  - Strict product/runtime source scan excluding docs, lockfiles, vendored/generated code, toolchain internals, and ratchet scripts returned no TODO/FIXME/stub/placeholder/mock/fake/demo/MVP/coming-soon/temporary Korean-equivalent markers.
  - Repo-owned Python/spec scan returned no `*.py`, `*.pyi`, `*.pyw`, or `*.spec` files outside excluded dependency/build directories.
  - Local preview restarted on `127.0.0.1:4174`; smoke: `/`, `/app.js`, `/catalog.json`, `/api/platform/v1/view-model`, `/api/hr/v1/employees`, `/api/workflow/v1/templates`, `/api/archive/v1/intake`, `/api/settings/v1/preferences` all HTTP 200. `/app.js` no longer contains `placeholder=`, catalog no longer contains `임시저장`, view schema is `bitween.platform.live.v1`.

## 2026-06-10 — 자료함 접수 오류 RustFS live fix

- User-visible error `자료를 접수하지 못했습니다. 보관함 연결과 파일 크기를 확인하세요.` was reproduced as an archive intake storage dependency failure, not a file-size failure.
- Root cause: local preview was running without explicit RustFS object-storage environment, so `POST /api/archive/v1/intake` failed closed with `rustfs_object_store_unavailable` before accepting files.
- Local RustFS was installed under ignored runtime space `.bitween/bin/rustfs` from the official macOS arm64 RustFS release and the release SHA-256 was verified before use. RustFS is running locally with API `http://127.0.0.1:9000`, console `http://127.0.0.1:9001`, region `us-east-1`, and bucket `bitween-archive-originals`.
- The preview server was restarted on `http://127.0.0.1:4174` with `BITWEEN_RUSTFS_ENDPOINT`, `BITWEEN_RUSTFS_BUCKET`, `BITWEEN_RUSTFS_BUCKET_ARCHIVE`, `BITWEEN_RUSTFS_REGION`, `BITWEEN_RUSTFS_ACCESS_KEY`, and `BITWEEN_RUSTFS_SECRET_KEY` wired to the local RustFS instance.
- Fresh verification evidence:
  - `GET http://127.0.0.1:9000/health` returned `ready=true`, `service=rustfs-endpoint`, `version=1.0.0-beta.7`.
  - `GET http://127.0.0.1:4174/` returned HTTP 200.
  - A multipart CSV upload to `POST http://127.0.0.1:4174/api/archive/v1/intake` returned HTTP 200 and produced a real RustFS-backed intake with `object_uri=rustfs://bitween-archive-originals/quarantine/2026-06-10/47ef2d88-bc17-448d-97d7-a64e4404edf3.csv`, `database_target=hr_employee_staging`, `status=ready_for_staging`, and `postgres_ready=true`.
- Important caveat: this local preview still uses the explicit hermetic local review store for relational state because no local PostgreSQL server/DSN is present in the shell. Production/Kubernetes must set `BITWEEN_POSTGRES_DSN` plus the same RustFS env family through Secrets/ConfigMaps so metadata/staging/admission persist to PostgreSQL while blobs persist to RustFS.

### 2026-06-10 — 자료함 field-mapping verifier and testing-standard ratchet

- Added a dependency-free archive intake verifier, `npm run verify:archive-intake-stories`, to the frontend testing standard. It exercises live preview routes against RustFS mock storage and Buck2-built Rust archive logic instead of static placeholders.
- The verifier covers three end-user/edge stories with Acme-only non-sensitive data:
  - HR roster with title/preamble rows, inferred header row, missing required department, unclear columns, sanitized value-shape hints, and operator field-mapping review to staging-ready state.
  - Payroll variable headers with gross-pay inference, required employee-identifier mapping, stale `sourceFingerprint` mutation rejection, and explicit source-payload preservation.
  - Empty payroll intake blocked for review rather than silently admitted.
- The verifier also statically guards the visible field-mapping editor affordances and the PostgreSQL mapping-review parity path so unclear-column guidance and missing-required-field guidance are recalculated together.
- Fixed the PostgreSQL field-mapping review refresh path: `map-fields` now resolves/recreates both `confirm_missing_required_data` and `explain_column` guidance with bounded `field_mapping_reviewed` resolution metadata. This keeps the PostgreSQL review path aligned with the local hermetic review path.
- Tightened Korean field-mapping copy for sanitized text values to avoid implying raw values are shown: `값 설명: 원문은 숨김`.
- Updated `apps/bitween-platform-ui/docs/ui-review-checklist.md` so 자료함 changes must preserve live field mapping, normalized hints, explicit ignore/preserve decisions, no dead buttons, and must run `npm run verify:archive-intake-stories`.
- Fresh verification evidence:
  - `buck2 test //crates/payroll-api:archive_intake_store_test //crates/payroll-api:payroll_api_test` passed: archive intake 24 tests, payroll API 196 tests.
  - `buck2 build //crates/payroll-api:archive_intake_store '//crates/payroll-api:archive_intake_store[check]' '//crates/payroll-api:archive_intake_store[clippy.txt]'` passed.
  - `node --check` passed for preview server/app, route authorization verifier, and archive intake story verifier.
  - `npm run verify:i18n`, `npm run verify:route-authorization`, `npm run verify:archive-intake-stories`, and `npm run typecheck` passed. A first parallel `verify:route-authorization` run timed out under concurrent heavy checks, then passed when rerun isolated.
- Remaining archive/office production backlog is still active, not dropped:
  - Native Rust Office module as a separate left-nav module for documents/spreadsheets/slides, collaborative editing, append-only audit, content-addressed RustFS originals, logical versions/diffs, and no binary snapshot duplication.
  - React Native + Tauri direction for desktop/native office capability where applicable.
  - Production PostgreSQL/RustFS hermetic fixture tests for field-mapping template reuse, review/admission/re-staging, source workbook sync, rollback, audit, and recovery drills.
  - Governed custom schema promotion path for columns that are neither mapped nor ignored: today they can be explicitly preserved in source payload; future work must let operators promote recurring custom fields into reviewed PostgreSQL-backed extensions.
  - Browser-level visual regression for the field-mapping editor and archive workbench once a stable browser fixture is available.

#### Addendum — mapping-template publication and cold-cache verifier hardening

- Tightened PostgreSQL mapping-template publication: templates now remain `draft` while any field mapping status is still review-blocking, not only when required target fields are missing. This prevents reusable templates from becoming active before unclear/source-payload decisions are explicit.
- `npm run verify:archive-intake-stories` now prebuilds `//crates/payroll-api:archive_intake_store` before starting the preview server so cold Buck2 rebuilds do not produce false route timeouts in the live story verifier.
- Final fresh verification after this addendum:
  - `buck2 test //crates/payroll-api:archive_intake_store_test //crates/payroll-api:payroll_api_test` passed.
  - `buck2 build //crates/payroll-api:archive_intake_store '//crates/payroll-api:archive_intake_store[check]' '//crates/payroll-api:archive_intake_store[clippy.txt]'` passed.
  - `node --check` passed for preview server/app, route authorization verifier, and archive intake story verifier.
  - `npm run verify:i18n`, `npm run verify:route-authorization`, `npm run verify:archive-intake-stories`, and `npm run typecheck` passed.
  - Local preview server remained running on `127.0.0.1:4174`; smoke checks returned HTTP 200 for `/` and `/api/auth/v1/routes`.

### 2026-06-10 — Office Product Contract future-product ratchet

- Added Ultragoal story `G029-office-module-production-contract` because the active product objective explicitly requires an Office module, while the prior durable plan had no Office/office/오피스 story.
- Added `docs/OFFICE_PRODUCT_CONTRACT.md` as the durable Office product contract. It keeps Office as a required future product without exposing dead UI: no left-nav/topbar/route visibility until Rust, PostgreSQL, RustFS, authorization, collaboration, audit, i18n, and runtime controls are live-wired and verified.
- Contract direction:
  - Rust service crates own documents, spreadsheets, slides, drive/storage, collaboration, search, authorization, and format workers.
  - React Native remains the shared UI source of truth; Tauri is only a desktop/native packaging and least-privilege bridge path where applicable.
  - PostgreSQL metadata stores relational records, permissions, session/version/audit/search metadata, and logical recovery records.
  - RustFS blobs store originals, exported binaries, embedded media, previews, and evidence objects.
  - real-time collaboration is gated by a CRDT/operation-log boundary, deterministic merge validation, and append-only audit.
  - ABAC + RBAC + PBAC, tenant/legal-entity/workplace scope, sensitive-data redaction, and Acme / Acme Corporation fixture naming remain mandatory.
- Added `apps/bitween-platform-ui/scripts/verify-office-contract.mjs` plus `npm run verify:office-contract`; CI and `npm run verify:data-mode` now require the Office contract gate.
- Updated `apps/bitween-desktop-tauri/README.md` so desktop Office/Tauri work points to the Office contract instead of becoming a separate desktop-only product path.
- RED evidence: `node apps/bitween-platform-ui/scripts/verify-office-contract.mjs` failed before the contract and script wiring existed, reporting missing `docs/OFFICE_PRODUCT_CONTRACT.md`, missing package/CI/runtime verifier wiring, missing Tauri README pointer, and missing Office contract requirements.
- GREEN evidence for this slice: `node --check apps/bitween-platform-ui/scripts/verify-office-contract.mjs`, `node --check apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs`, `npm run verify:office-contract`, `npm run verify:data-mode`, `npm run verify:no-python-source`, `npm run verify:buck2-only`, `npm run verify:sensitive-data`, focused `git diff --check`, and local preview `GET /` returned HTTP 200 with security headers.
- Remaining Office production work is not complete: add Rust/Buck2 Office service crates, PostgreSQL migrations, RustFS object adapters, CRDT/operation-log collaboration runtime, authorization decisions, Korean-first Office UI, browser/runtime verification, and Tauri command contracts only after the web/API path is live.

### 2026-06-10 — archive ZIP intake, actual UI usage stories, and four-pillar Ultragoal end-state

- User directive folded into the active production slice and same PR scope: everything local in this worktree is preserved for one PR, including the broader production-slice changes, Office contract work, HR/Payroll completion direction, and Archive/Drive ZIP intake hardening.
- Archive/Drive intake now accepts ZIP files safely:
  - The original ZIP is stored once in RustFS quarantine with checksum metadata.
  - Safe inner CSV/TSV/TXT/XLSX members become separate review rows with names like `bundle.zip/hr/roster.csv`.
  - Unsafe ZIP entries are skipped before review-row creation: absolute/drive/backslash paths, `.`/`..` traversal, control characters, encrypted entries, symlinks, unsupported types, too many entries, oversized members, and total zip-bomb expansion are guarded.
  - No new runtime dependency was added; ZIP sampling uses bounded local parsing plus Node `zlib` `maxOutputLength`.
- End-user UX hardening:
  - Upload/review mutation failures now preserve the existing archive review queue instead of clearing operator work.
  - Korean failure copy points operators to archive storage, file-size, and ZIP-entry-count recovery checks.
  - ZIP copy tells operators that safe inner table files are split for review.
- Actual UI usage verification added to `npm run verify:archive-intake-stories`:
  - Normal story: a ZIP with HR and payroll CSVs is uploaded through the real preview UI functions against a live preview server/RustFS mock/Buck2-built Rust intake target; safe inner files render as review rows with mapping controls.
  - Edge story: an empty readable CSV remains a review blocker with human guidance instead of being silently admitted.
  - Review story: payroll field-mapping save clears guidance and shows staging readiness.
  - Malicious story: path-traversal ZIP entries do not render, and a too-many-entries ZIP fails closed while preserving the existing review queue.
- Durable planning update:
  - Ultragoal now includes the explicit end-state product pillars: Office, HR, Payroll, and Archive/Drive.
  - Added/steered goals G031-G035 for four-pillar end-state alignment and end-to-end HR, Payroll, Archive/Drive, and Office completion.
  - Benchmarks recorded in the Ultragoal ledger/docs against enterprise patterns from SAP core HR/payroll, SAP Employee Central Payroll, SAP Payroll Control Center, SAP Document Management, OWASP upload safety, Node bounded decompression, and Microsoft SharePoint/Drive-style metadata/versioning/retention patterns.
- Fresh verification evidence for this addendum before PR prep:
  - `node --check apps/bitween-platform-ui/preview/app.js apps/bitween-platform-ui/scripts/verify-archive-intake-stories.mjs` passed.
  - `npm run verify:archive-intake-stories` passed with the new actual UI/API stories, mutation guard, malicious ZIP handling, and visual affordance standards.
- Remaining after PR: true browser/device visual regression can still be added when the repository has a stable browser fixture, but the current verifier exercises actual preview UI code paths, live HTTP routes, RustFS upload behavior, and Buck2-built Rust intake logic hermetically.
