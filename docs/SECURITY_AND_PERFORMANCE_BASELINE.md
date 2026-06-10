# Security, authorization, and performance baseline

## Status

Required baseline for the Buck2/Rust/Tauri/React Native transition.

## Source-backed references

- NIST SP 800-207 Zero Trust Architecture: https://www.nist.gov/publications/zero-trust-architecture-0
- NIST SP 800-162 ABAC definition and considerations: https://csrc.nist.gov/pubs/sp/800/162/upd2/final
- NIST RBAC project and ANSI/INCITS 359 background: https://csrc.nist.gov/Projects/Role-Based-Access-Control
- Kubernetes RBAC authorization: https://kubernetes.io/docs/reference/access-authn-authz/rbac/
- Kubernetes Horizontal Pod Autoscaling: https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/
- Core Web Vitals thresholds and measurement guidance: https://web.dev/articles/vitals
- Tauri capabilities: https://tauri.app/security/capabilities/
- IETF RFC 7519 JSON Web Token: https://datatracker.ietf.org/doc/html/rfc7519.html
- OWASP JWT Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
- W3C WebAuthn Level 3: https://www.w3.org/TR/webauthn-3/
- FIDO specifications overview: https://fidoalliance.org/specifications-overview/

## Authorization model: RBAC + ABAC

Bitween authorization must combine RBAC and ABAC:

| Layer | Purpose | Examples |
| --- | --- | --- |
| RBAC | Coarse-grained job responsibility and administrative capability | employee, manager, payroll operator, HR admin, workflow approver, executive, auditor, service account |
| ABAC | Contextual decision inputs evaluated per request | tenant/legal entity, workplace, department, document owner, approval line, trip status, device posture, time window, data sensitivity, environment, action |

### Required authorization contract

Every protected backend and desktop command must evaluate:

- **Subject:** authenticated user or service account, roles, group, department, manager chain, device/session posture.
- **Object:** resource type, tenant/legal entity, workplace, owner, sensitivity, lifecycle state.
- **Action:** read, create, approve, reject, execute, report, reflect KPI, export, administer.
- **Environment:** request origin, channel, network trust signal, time, workload identity, Kubernetes namespace/service account.

Access is denied unless both are true:

1. The subject has an RBAC role that permits the action family.
2. ABAC policy allows the exact subject/object/action/environment tuple.

### Backend enforcement points

- Rust API handlers validate identity, tenant, legal entity, and action before service logic.
- Domain services re-check authorization for state transitions; route-level checks are not enough.
- Repository queries must be tenant/legal-entity scoped and must not rely on frontend filtering.
- Background workers and CronJobs use service accounts with only the domain permissions required for their job.
- Tauri commands never bypass backend authorization for production business resources.

### Kubernetes enforcement points

- Use Kubernetes RBAC for service accounts, migration Jobs, CronJobs, and operators.
- Do not bind broad `cluster-admin` or secrets-reader roles to app workloads.
- Namespace-scoped Role/RoleBinding is preferred unless a ClusterRole is required and reviewed.
- Secrets access is isolated to workloads that need a specific secret.

## Zero Trust baseline

Zero Trust for Bitween means no implicit trust based on network location, desktop packaging, cluster membership, or internal service naming.

Required controls:

- Authenticate and authorize every request, including service-to-service traffic.
- Use least privilege for users, services, Jobs, CronJobs, and Tauri capabilities.
- Treat all external inputs, uploaded files, imported workbooks, groupware payloads, AI responses, and desktop IPC payloads as untrusted.
- Validate payloads at every boundary with typed schemas or Rust domain validators.
- Keep credentials in Kubernetes Secrets or an external secret manager; never in source, frontend bundles, or desktop static assets.
- Emit audit events for authorization decisions on sensitive actions such as payroll export, approval, report proof, KPI reflection, admin changes, and data migration.
- Redact sensitive data in logs and errors.
- Prefer short-lived tokens and explicit session/device posture checks for mobile and desktop clients.


## Authentication baseline: JWT + WebAuthn

### WebAuthn / passkeys

- WebAuthn/passkeys are the preferred phishing-resistant authentication mechanism for privileged roles and step-up verification.
- Registration and authentication ceremonies must be implemented in the Rust backend and TypeScript frontend with origin/RP validation.
- Private keys never leave authenticators; the server stores public credential metadata and audit state only.
- Recovery/offboarding is a required production design topic, not an afterthought.

### JWT

- JWT is a short-lived signed claims format for API boundaries, not a durable session database.
- Required validation: issuer, audience, signature algorithm, expiration, not-before, issued-at, subject, and token ID/revocation status where used.
- Claims may carry tenant/legal entity, role family, assurance level, and device/session posture, but the Rust policy engine must still evaluate RBAC + ABAC per request.
- Prefer asymmetric signing once multiple Rust services verify tokens independently.
- Browser storage should prefer secure httpOnly sameSite cookies; Tauri/mobile token storage requires an explicit secure-storage decision.

## Frontend and desktop security rules

- React Native screens are presentation and interaction surfaces, not authorization boundaries.
- UI may hide actions based on capability hints, but the backend must enforce the final decision.
- Tauri capabilities must be least-privilege and reviewed with each desktop command.
- Desktop local storage may cache non-sensitive settings only; production secrets and payroll data require explicit encrypted-storage and retention decisions.
- Tauri commands must have typed inputs/outputs and must validate all payloads before native operations.

## Performance baseline

### User-experience budgets

For web and Tauri-rendered frontend surfaces, use Core Web Vitals as the first user-facing performance baseline:

| Metric | Budget |
| --- | --- |
| LCP | 2.5 seconds or less at the 75th percentile |
| INP | 200 milliseconds or less at the 75th percentile |
| CLS | 0.1 or less at the 75th percentile |

### Backend and Kubernetes budgets

Initial budgets for Rust services before production traffic tuning:

- Define SLOs per endpoint family before enabling HPA.
- Expose request latency, error rate, saturation, queue depth, and worker lag metrics.
- Add readiness and liveness probes before scaling.
- Set resource requests before HPA because CPU utilization is calculated against requested resources.
- Use pagination or bounded query windows for lists, dashboards, reports, and manager views.
- Reject unbounded exports or run them as audited background jobs.

### Measurement workflow

1. Measure current behavior before optimizing.
2. Identify the actual bottleneck with traces, logs, metrics, or browser performance tooling.
3. Fix the narrow cause.
4. Re-measure and record evidence.
5. Add a regression guard where practical.

## Review gates

A PR in this transition track is not production-ready unless it states:

- Which RBAC roles and ABAC attributes protect the changed behavior.
- Which Zero Trust boundary was added or preserved.
- What performance budget applies and how it was measured or deferred.
- Which tests or checks prove the claim.
- What legacy compatibility path remains and when it can be deleted.
- Which Korean labor-law or labor-market policy facts were used, the official source/effective date for each fact, and whether the value is configuration-backed.
- Which UI/UX maturity gate applies for role workspaces, employee self-service, manager insights, compliance cockpit, lifecycle timelines, auditability, accessibility, Korean localization, and full single-language Korean/English/Chinese/Japanese review.
- Whether auth/security messages, WebAuthn/passkey flows, JWT/session errors, policy-denied states, and audit-facing copy are localized through stable codes and catalog arrays instead of hardcoded strings.
