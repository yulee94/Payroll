# Kubernetes-native production stack

## Status

Accepted direction as of 2026-06-04; refined 2026-06-10 for the internal
managed-Kubernetes product path.

Bitween production must run as a Kubernetes-native stack on managed Kubernetes.
It is an internal enterprise product, not an external hyperscale cloud product:
operate it with strong security, auditability, runbooks, rollout discipline, and
rollback evidence, but do not import public-cloud marketplace or global
multi-region provider ceremony into the current path. Local compatibility runners and repo-owned adapters were decommissioned in G028; missing behavior must return through Rust services and TypeScript client surfaces with parity evidence.


## Preferred launch architecture

The current launch recommendation is:

| Area | Recommendation | Notes |
| --- | --- | --- |
| Server region | AWS Seoul, NAVER Cloud Korea, or the selected managed-Kubernetes provider region | Keep one Korea-region central cluster first, with nationwide branches connecting over HTTPS/VPN/Zero Trust. |
| Backend | Docker-based API server | Keep API, Admin web, batch/worker containers separated. |
| Runtime operation | Managed Kubernetes first | Use a managed Kubernetes service as the production runtime. Keep the first cluster simple: ingress/gateway, Rust API/workers/jobs, PostgreSQL, RustFS, identity integration, secrets, observability, and audit events. |
| Database | Self-hosted PostgreSQL, HA/Multi-AZ where supported | Relational system of record for metadata, staging, review, admitted business data, HR/payroll canonical rows, 자료함 metadata, mapping, admission audit, backups, encryption, connection restrictions, and read replica when reporting load grows. |
| Files | Self-hosted RustFS object/blob storage | Store all files, originals, attachments, and blobs for HR, invoices, attendance, reports, and arbitrary 자료함 objects outside PostgreSQL while keeping metadata/admission state relational. |
| Security | WAF + VPN/Zero Trust + MFA + audit logs | Admin pages require MFA and/or IP restriction; DB must not be publicly exposed. |
| Deployment | GitHub/GitLab CI/CD + Terraform | Git push → tests → image build → staging → approval → zero-downtime production deploy. |
| Mobile | React Native employee app | Flutter remains acceptable, but this repo now carries the React Native worker app scaffold. |
| Push | FCM + APNs | Device-token records are stored by `user_id`, `branch_id`, `device_id`, `platform`, version, and activity time. |
| Release | Employee app private first | Use TestFlight, Play Internal/Closed Testing, MDM, or private distribution before any customer public release. |

This staged approach keeps the first production pilot operable for a small team
inside the managed-Kubernetes target. Scaling work should add evidence-backed
service separation, HPA, queue workers, and runbooks only when the internal
product needs them.

## Source-backed Kubernetes basis

This document is based on current official Kubernetes documentation for:

- Deployments: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- Services: https://kubernetes.io/docs/concepts/services-networking/service/
- Ingress: https://kubernetes.io/docs/concepts/services-networking/ingress/
- Gateway API: https://kubernetes.io/docs/concepts/services-networking/gateway/
- ConfigMaps: https://kubernetes.io/docs/concepts/configuration/configmap/
- Secrets: https://kubernetes.io/docs/concepts/configuration/secret/
- Probes: https://kubernetes.io/docs/concepts/workloads/pods/probes/
- HorizontalPodAutoscaler: https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/
- Jobs: https://kubernetes.io/docs/concepts/workloads/controllers/job/
- CronJobs: https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/

## Target topology

| Component | Kubernetes resource | Runtime intent |
| --- | --- | --- |
| `bitween-frontend` | Deployment + Service + Ingress/Gateway route | Serves the TypeScript frontend shell and static assets. |
| `bitween-api` | Deployment + Service | Rust HTTP API for payroll, workflow, org, KPI, mobile, AI policy, and integration contracts. |
| `bitween-worker` | Deployment | Rust background worker for workflow side effects, notifications, report generation, and idempotent follow-up processing. |
| `bitween-archive-intake` | Deployment + queue consumer | Rust worker that reads RustFS object-created/intake events, profiles files safely, stages HR/payroll data in PostgreSQL, and creates human review questions for anomalies or unknown mappings. |
| `bitween-postgres` | StatefulSet or managed-equivalent PostgreSQL release | Self-hosted relational store for tenant-scoped app state, staging, admission, audit, and workflow metadata. |
| `bitween-rustfs` | StatefulSet + Service | Self-hosted S3-compatible object storage for 자료함 originals and binary evidence. |
| `cloud_native_audit_worker` | CronJob | Rust operational worker that fails closed when PostgreSQL, RustFS, tenant scope, audit export, or OpenTelemetry wiring is absent. |
| `bitween-overdue-evaluator` | CronJob | Periodic business-trip overdue evaluation and escalation. |
| `bitween-kpi-reflector` | CronJob or queue worker | Idempotent KPI reflection for approved lifecycle evidence. |
| `bitween-migrations` | Job | Schema and data migrations, run before rollout or as a controlled release step. |
| `bitween-observability` | ServiceMonitor/metrics integration where available | Health, metrics, logs, OpenTelemetry evidence, and audit evidence. |
| `bitween-tenant-boundary` | ResourceQuota + LimitRange + RoleBinding | Namespace-level tenant guardrails paired with PostgreSQL RLS and Rust ABAC/RBAC/PBAC checks. |

## Production invariants

- Kubernetes manifests or Helm/Kustomize overlays are release artifacts, not optional local notes.
- Rust services own backend behavior in production and build against the repository Rust 2024 / Rust 1.96 baseline.
- TypeScript frontend owns user-facing frontend delivery.
- API state is tenant/legal-entity scoped; group-root storage must never bypass legal-tenant authorization.
- Payroll action authorization is Rust service-owned: request tenants must match trusted principals, action permissions must pass role/position plus effective org-unit platform filtering, and frontend labels are not authorization input.
- Configuration uses ConfigMaps; credentials and API keys use Secrets or an external secret manager.
- All HTTP workloads expose dedicated startup/readiness/liveness endpoints.
- Horizontal scaling uses HPA only after resource requests, readiness behavior, and idempotency are verified.
- Scheduled lifecycle work runs as CronJobs or queue workers, not as ad-hoc local scripts.
- Production persistence is a database/object-storage layer behind Rust services. Local JSON stores are compatibility fixtures only.
- All uploaded files, originals, attachments, and binary blobs live in RustFS; searchable metadata, relational staging, review tasks, and admitted HR/payroll rows live in PostgreSQL.
- Workflow is a separate corporate logic/canvas/editor surface; 전자결재/approval is signing/approval only and must not own workflow routing or canvas editing.
- User-facing workflow UIs must show role-relevant work, not numbered filler cards or Rust/source/storage internals.
- Migrations are explicit Jobs with rollback/restore instructions and audit logs.

## Runtime environment contract

Rust stores consume one canonical production contract across the API Deployment,
migration Job, and local preview harness:

- `BITWEEN_POSTGRES_DSN` comes from an external Secret and is never committed.
- `BITWEEN_POSTGRES_TLS_POLICY=verify-full` is the default production TLS mode.
- `BITWEEN_POSTGRES_TENANT_ID`, `BITWEEN_POSTGRES_LEGAL_ENTITY_ID`, and
  `BITWEEN_POSTGRES_WORKPLACE_ID` scope every PostgreSQL session before reads or
  writes.
- `BITWEEN_RUSTFS_ENDPOINT`, `BITWEEN_RUSTFS_BUCKET`, and
  `BITWEEN_RUSTFS_BUCKET_ARCHIVE` identify the self-hosted RustFS object store
  and archive bucket; access and secret keys come only from Secrets.
- Runtime code must fail closed when these values are absent instead of
  silently writing to local files or implicit object buckets.

## API surfaces and routing

Production API traffic is separated first by gateway/API surface, then by
versioned resource paths. The React Native employee app must not share the web
admin API surface.

| Surface | Gateway/service target | Exposure | Version rule |
| --- | --- | --- | --- |
| Web Admin API | `admin-api.bitween.acme.internal` | Admin web only, MFA/IP controls | `/api/admin/v1/*` |
| Mobile App API | `mobile-api.bitween.acme.internal` | iOS/Android employee app, token + device binding | `/api/v{n}/*`, e.g. `/api/v1/login`, `/api/v1/branches`, `/api/v1/tasks`, `/api/v2/tasks` |
| Partner API | `partner-api.bitween.acme.internal` | Approved partner integrations, rate-limited | `/api/public/v1/*` |
| Internal Admin API | `internal-api.bitween.local` | Private subnet operations/batch/security only | `/api/internal/v1/*` |

Planned service routes:

| Route | Owner | Notes |
| --- | --- | --- |
| `/api/payroll/v1/runs` | Rust payroll API | Run or validate payroll automation requests. |
| `/api/payroll/v1/runs/validate` | Rust payroll API | Validate without generating payroll outputs. |
| `/api/payroll/v1/healthz` | Rust payroll API | Probe-safe health payload from `PayrollApiService::health()`. |
| `/api/payroll/v1/readiness` | Rust payroll/readiness API | Tenant/site readiness cards for frontend dashboards. |
| `/api/workflow/v1/*` | Rust workflow API | Documents, inbox, forms, execution tasks, trip lifecycle. |
| `/api/archive/v1/intake` | Rust archive/intake API | Accept files, write originals to RustFS, create PostgreSQL intake/staging/review records, and expose business-language mapping/anomaly tasks. |
| `/api/kpi/v1/*` | Rust KPI API | Individual and manager performance records. |
| `/api/v1/*` on Mobile App API | Rust mobile API | Device auth, attendance events, branch list, tasks, profile, leave, payroll preview. |
| `/api/v2/tasks` on Mobile App API | Rust mobile API | Versioned task payload evolution without breaking existing app releases. |
| `/api/ai/v1/*` | Rust policy gateway + provider adapter | AI requests with tenant/user safety policy and secret isolation. |

## Rollout model

1. Maintain release artifacts under `deploy/kubernetes/`. The current base is a
   managed-Kubernetes GitOps base for the frontend shell, Rust API, PostgreSQL
   migration Job, self-hosted PostgreSQL, and self-hosted RustFS.
2. Build immutable images for the frontend, API, migration binary, and worker
   binaries. Release tickets record image digests; release overlays update image
   tags through Kustomize image transforms.
3. Provide credentials through an external secret manager or pre-created
   Kubernetes Secrets. The repository must not commit Secret objects or secret
   values.
4. Run `npm run verify:kubernetes-manifests --prefix apps/bitween-platform-ui`
   before promotion. The gate rejects unsafe image tags, missing probes, missing
   resources, weak security context, missing NetworkPolicy, missing SLO files,
   missing rollback evidence, missing worker CronJobs, missing ServiceMonitor
   wiring, missing ResourceQuota/LimitRange tenant guardrails, committed Secrets,
   and known object-store default credentials.
5. Run the PostgreSQL migration Job against staging data and capture its logs in
   audit evidence storage.
6. Deploy the Rust API and frontend behind Services and the managed Gateway API
   edge route.
7. Confirm `cloud_native_audit_worker` emits a ready report for PostgreSQL,
   RustFS, tenant scope, audit export, and OpenTelemetry wiring.
8. Keep self-hosted PostgreSQL protected by point-in-time recovery and keep
   RustFS originals protected by object versioning. Rollback uses metadata and
   storage-version references, not binary database snapshots committed to Git.
9. Enable HPA only after resource requests, readiness behavior, SLO evidence, and
   idempotency have been validated for the specific service.
10. Run Rust and TypeScript parity suites against documented behavior and fixtures.
11. Promote with readiness-gated rolling update and a recorded rollback marker.
12. Keep compatibility adapters decommissioned; any restored behavior must be Rust-owned with zero-regression evidence.

## Current release artifacts

| Artifact | Purpose |
| --- | --- |
| `deploy/kubernetes/base/kustomization.yaml` | Kustomize base and image pinning surface. |
| `deploy/kubernetes/base/*-deployment.yaml` | Frontend and Rust API rolling deployments with probes, resources, graceful shutdown, and restricted container context. |
| `deploy/kubernetes/base/*-statefulset.yaml` | Self-hosted PostgreSQL and RustFS stateful data-plane definitions with PVCs, probes, restricted pod context, and no committed credentials. |
| `deploy/kubernetes/base/postgres-migrate-job.yaml` | Controlled Rust `postgres_migrate` release Job. |
| `deploy/kubernetes/base/worker-cronjobs.yaml` | Controlled Rust `cloud_native_audit_worker` CronJob for audit, storage, tenant-scope, and telemetry wiring checks. |
| `deploy/kubernetes/base/observability.yaml` | ServiceMonitor resources for API/frontend metrics and OpenTelemetry-aligned labels. |
| `deploy/kubernetes/base/tenant-isolation.yaml` | ResourceQuota, LimitRange, and release-operator RBAC guardrails for the tenant namespace. |
| `deploy/kubernetes/base/networkpolicies.yaml` | Namespace default-deny plus scoped frontend, API, PostgreSQL, RustFS, DNS, and observability traffic. |
| `deploy/kubernetes/slo/*.openslo.yaml` | Promotion SLO evidence for request-serving surfaces. |
| `deploy/kubernetes/runbooks/release-rollback.md` | Apply, rollback, drift, PITR, RustFS object-version, and audit evidence procedure. |

RustFS is pinned to a post-alpha.79 line because public vulnerability records
show pre-alpha.79 releases included fixed security issues. Keep RustFS release
updates source-reviewed before changing the image pin.

## Backlog linkage

The Rust rewrite is tracked in `docs/RUST_BACKEND_MIGRATION.md` and `.omx/backlog.md`. Every backend slice must be source-driven, test-first, doubt-reviewed, code-reviewed, and simplified before decommissioning the compatibility path.
