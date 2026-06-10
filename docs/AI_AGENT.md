# AI assistant policy surface

## Status

Current as of 2026-06-10 after G028.

Repo-owned AI assistant implementation is not Rust-backed. Any AI assistant
capability must be delivered through Rust service boundaries and TypeScript UI
contracts, with secrets supplied by Kubernetes Secrets or an external secret
manager.

## Production direction

Bitween AI assistance is a tenant/user-scoped work assistant for payroll,
업무 관리, reports, calendar/follow-ups, and KPI contexts. Production delivery
must route AI requests through the Kubernetes-native API/policy gateway.

| Surface | Owner | Requirement |
| --- | --- | --- |
| Policy gateway | Rust service | Tenant scope, user scope, ABAC/RBAC/PBAC authorization, rate limits, audit events, prompt/response redaction. |
| Provider adapter | Rust service | Provider credentials read from Secrets only; no frontend secret exposure. |
| UI | TypeScript shell | Korean-first catalog copy, explicit user action, no hidden mutation. |
| Storage | PostgreSQL/RustFS | Conversation metadata and audit references in PostgreSQL; files/evidence in RustFS when needed. |
| Operations | Kubernetes | NetworkPolicy, observability, SLOs, rollout and rollback evidence. |

## Security rules

- Do not put API keys, passwords, cookies, tokens, or tenant/user secrets in
  source, Git history, container images, logs, prompts, frontend bundles, or test
  fixtures.
- AI actions that could mutate payroll, HR, workflow, approval, archive,
  settings, or admin state must pass Rust-owned authorization and audit checks.
- Sensitive payroll/personnel data must be minimized, redacted where possible,
  scoped to tenant/legal entity/workplace, and logged only as safe audit
  metadata.
- No local compatibility assistant is an approved production path.

## Verification

AI-related product work must keep the standard product gates green:

```sh
cd apps/bitween-platform-ui
npm run verify:no-python-source
npm run verify:data-mode
npm run verify:security-gates
npm run verify:route-authorization
npm run verify:sensitive-data
npm run verify:sensitive-history
npm run typecheck
```

Rust AI gateway work must add target-specific Buck2 build/check/test/clippy
evidence for the Rust crate or binary that owns the behavior.

## Roadmap

- Rust AI policy gateway and tenant-scoped API routes.
- Provider adapter with Secret-managed credentials and redaction.
- Persistent conversation metadata, rate limits, audit events, and retention
  policy.
- Streaming endpoint for TypeScript frontend chat surfaces.
- Kubernetes observability and production rollback evidence.
