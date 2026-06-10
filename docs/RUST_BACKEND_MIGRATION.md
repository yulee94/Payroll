# Idiomatic Rust backend backlog

## Status

G028 decommissioned all repo-owned Python implementation, tests, scripts, and
compatibility adapters. Backend behavior now returns only through Rust services,
Buck2 verification, TypeScript contracts, and Kubernetes-native deployment
artifacts.

## Goal

Ship the Bitween backend as idiomatic Rust services for managed Kubernetes while
preserving payroll, HR, archive, approval, workflow, tenant, and security
behavior through explicit Rust parity fixtures and product-level contract gates.
The production assumptions remain documented in `docs/KUBERNETES_NATIVE_STACK.md`.

## Current verified foundation

- Buck2 is the canonical Rust build/test/check path.
- Reindeer vendors third-party Rust dependencies under `third-party/rust/` with
  fixups reviewed as part of the build graph.
- `crates/payroll-api` exposes Rust DTOs, service facades, authorization policy,
  live store binaries, PostgreSQL schema contracts, and cloud-native worker
  entrypoints.
- `crates/workflow-core` owns the Rust workflow graph model used by the editable
  업무 관리 canvas/editor.
- TypeScript contracts under `frontend/` and `apps/bitween-platform-ui/` consume
  stable Rust-shaped DTOs.
- CI/local product gates reject repo-owned Python reintroduction, retired Cargo
  verification commands, stale active Python docs, unsupported recursive Buck2
  provider examples, sensitive-data leaks, and non-hermetic browser/session
  fallbacks.

## Required backend patterns

1. Build every Rust slice with Buck2 targets and tests.
2. Keep PostgreSQL as the relational system of record for canonical business
   state, audit rows, version history, admission staging, and policy-backed
   workflow execution state.
3. Keep RustFS as the object/blob store for originals, attachments, generated
   export artifacts, and file-version references.
4. Store version history as text/structured metadata plus object references; do
   not store binary snapshots in PostgreSQL.
5. Enforce JWT/OIDC, WebAuthn/passkey evidence, ACR step-up, and ABAC/RBAC/PBAC
   decisions before sensitive workflow, payroll, HR, archive, approval, tenant,
   or settings mutations.
6. Fail closed when PostgreSQL, RustFS, auth policy, or session verification is
   unavailable.
7. Keep Korean-first and locale-aware copy in catalog-backed frontend surfaces;
   do not leak technical readiness internals to payroll/HR operators.
8. Preserve tenant/legal-entity/workplace isolation in Rust DTOs, queries,
   schemas, telemetry, audit events, and user-facing workflows.

## Completed Rust slices

- Buck2/Reindeer foundation and first-party Rust target graph.
- Payroll operation policy normalization and run-response contracts.
- Payroll service boundary, health/readiness DTOs, and platform live-view model.
- Payroll authorization with ABAC/RBAC/PBAC-sensitive operation decisions.
- Attendance aggregation, fixed-hours, workplace-hours, site-benefits,
  social-insurance, EI-65, EDI, invoice-audit, earnings, deductions, salary, and
  execution-plan contracts covered by Rust parity tests.
- Workflow/business-trip/document/follow-up/form/inbox/permission contracts under
  Rust workflow modules and the editable 업무 관리 UI surface.
- PostgreSQL schema contracts for archive intake/admission/rollback/source sync,
  workflow templates/version history/runtime execution/data records, HR employee
  records, user preferences, payroll/attendance intake, and auth-session
  security.
- Rust store binaries for HR employee, archive intake, user preference, workflow
  template, auth-session validation, authorization decisions, PostgreSQL
  migrations, and cloud-native audits.
- Preview shell routes that delegate sensitive operations to Rust/Buck2 binaries
  and fail closed without configured PostgreSQL/RustFS or explicit hermetic local
  review mode.

## Remaining production backlog

1. Add hermetic PostgreSQL and RustFS integration fixtures that can run in CI or a
   controlled local environment without depending on developer-global services.
2. Replace local-review file persistence paths with production PostgreSQL/RustFS
   wiring for every mutable route, then remove the local review flag.
3. Add networked OIDC discovery/JWKS retrieval, cache rotation, revocation
   propagation, and session-audit retention/export controls.
4. Add WebAuthn/passkey registration, enrollment, recovery, offboarding, and
   browser ceremony adapters around the verified server-side assertion boundary.
5. Add deployment attestation, workload identity, secret rotation, backup/restore
   drills, admission-policy checks, and managed-Kubernetes rollout evidence.
6. Complete end-to-end archive intake: upload to RustFS, extract/validate HR or
   payroll data, stage anomalies for human guidance, admit reviewed rows to
   PostgreSQL, sync approved state back to linked source files where appropriate,
   and support graceful rollback to previous text/metadata versions.
7. Complete visual workflow execution analytics: persisted runtime instances,
   SLO timers, escalation routing, data-operation audit, replay/rollback controls,
   and operator-facing metrics.
8. Replace dependency/host-tool assumptions that rely on local Apple toolchains
   with repository-owned Buck toolchain configuration before production CI
   standardization.

## Verification commands

Run the smallest relevant subset first, then the full product gate before a
release candidate:

```sh
buck2 build //...
buck2 test //...
buck2 build '//crates/payroll-api:payroll_api[check]' '//crates/payroll-api:platform_live_view[check]' '//crates/workflow-core:workflow_core[check]'
cd apps/bitween-platform-ui
npm run verify:no-python-source
npm run verify:buck2-only
npm run verify:data-mode
npm run verify:security-gates
npm run verify:auth-session
npm run verify:route-authorization
npm run verify:i18n
npm run typecheck
npm run verify:sensitive-data
npm run verify:sensitive-history
```
