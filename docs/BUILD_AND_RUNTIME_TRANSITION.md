# Build and runtime transition authority

## Status

Current as of 2026-06-10 after G028.

This document replaces the earlier transition log. The old plan mixed legacy
compatibility commands, retired build paths, and future decommission language.
That state is no longer authoritative.

## Current invariant

- Backend product implementation is Rust under `crates/` and future Rust service
  crates.
- Frontend implementation is TypeScript under `apps/bitween-platform-ui/` and
  `frontend/`.
- Repo-owned Python source, tests, scripts, adapters, local tools, stubs, and
  dependency manifests are decommissioned.
- Missing historical behavior must return through Rust/Buck2 services/tests or
  TypeScript contracts only.
- Buck2 is the canonical Rust build, check, test, and clippy surface. Retired
  Cargo build/check/test/clippy/run/bench commands are blocked by the local
  PreToolUse guard and CI verification.
- PostgreSQL is the relational system of record; RustFS is the object/blob store.
- Managed Kubernetes release artifacts live under `deploy/kubernetes/` and are
  verified through static product gates before promotion.

## Active verification

Run the smallest relevant set first, then the full gate before claiming a
production-ready slice:

```sh
cd apps/bitween-platform-ui
npm run verify:no-python-source
npm run verify:buck2-only
npm run verify:data-mode
npm run verify:security-gates
npm run verify:auth-session
npm run verify:auth-routes
npm run verify:route-authorization
npm run verify:signed-out-auth-ux
npm run verify:i18n
npm run typecheck
npm run verify:performance-gates
npm run verify:kubernetes-manifests
npm run verify:sensitive-data
npm run verify:sensitive-history
npm audit --omit=dev --audit-level=moderate
```

Rust verification uses Buck2 only:

```sh
buck2 build //...
buck2 test //...
buck2 build '<target>[check]'
buck2 build '<target>[clippy.txt]'
```

Use target-specific `[check]` and `[clippy.txt]` providers for changed Rust
crates/binaries; the current Buck2 parser in this workspace does not accept the
old recursive provider examples.

## Runtime direction

| Area | Current production direction |
| --- | --- |
| Backend | Rust services/domain crates built and tested by Buck2. |
| Frontend | React Native/TypeScript shell with catalog-backed i18n. |
| Auth | Rust-owned JWT/JWKS/OIDC validation, WebAuthn assertion verification, session step-up, revocation/audit, ABAC/RBAC/PBAC checks. |
| Data | PostgreSQL migrations and repository contracts with tenant/legal/workplace scope. |
| Objects | RustFS object lifecycle with checksum, quarantine, sensitivity label, review, admission, versioning, and rollback metadata. |
| Operations | Kubernetes manifests, NetworkPolicy, SLOs, runbooks, audit worker, migration Job, and rollback evidence under `deploy/kubernetes/`. |
| CI | No-Python, Buck2-only, security, auth, route authorization, i18n, TypeScript, performance, Kubernetes, sensitive-data, npm-audit, and Buck2 Rust gates. |

## Historical transition handling

Pre-G028 transition checkpoints remain useful only as historical evidence of
what behavior was migrated. They are not instructions to restore old adapters or
run old compatibility gates. When a historical behavior gap is found:

1. Write or extend a Rust/TypeScript contract for the behavior.
2. Add Buck2 Rust tests or TypeScript verifier coverage.
3. Wire production paths through Rust service boundaries, PostgreSQL, RustFS, and
   authorization checks.
4. Update docs and `HANDOFF.md` with the new Rust/TypeScript evidence.
5. Keep the no-Python and Buck2-only gates green.

## Stop condition

A transition slice is complete only when the relevant Rust/TypeScript product
surface is live wired, no stubs or placeholder paths are introduced, no sensitive
data is committed, target-specific Buck2 gates pass, product Node gates pass,
and local/CI documentation points to the current Rust/TypeScript path.
