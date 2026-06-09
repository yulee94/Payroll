# Kubernetes-native production stack

## Status

Accepted direction as of 2026-06-04.

Bitween production must run as a Kubernetes-native stack. Local compatibility runners and Python adapters are not production services; they exist only to preserve behavior until Rust services and TypeScript client surfaces have parity.


## Preferred launch architecture

The current launch recommendation is:

| Area | Recommendation | Notes |
| --- | --- | --- |
| Server region | AWS Seoul or NAVER Cloud Korea | Keep one Korea-region central cloud first, with nationwide branches connecting over HTTPS/VPN/Zero Trust. |
| Backend | Docker-based API server | Keep API, Admin web, batch/worker containers separated. |
| Runtime operation | Managed Container first, Kubernetes as scale-up path | Use ECS Fargate/NCP managed container or similar for MVP; move to Kubernetes/EKS/NKS when service count and team capacity justify it. |
| Database | PostgreSQL Multi-AZ | Automatic backups, encryption, connection restrictions, read replica when reporting load grows. |
| Files | S3/Object Storage | Store uploaded HR, invoice, attendance, and report objects outside the DB. |
| Security | WAF + VPN/Zero Trust + MFA + audit logs | Admin pages require MFA and/or IP restriction; DB must not be publicly exposed. |
| Deployment | GitHub/GitLab CI/CD + Terraform | Git push → tests → image build → staging → approval → zero-downtime production deploy. |
| Mobile | React Native employee app | Flutter remains acceptable, but this repo now carries the React Native worker app scaffold. |
| Push | FCM + APNs | Device-token records are stored by `user_id`, `branch_id`, `device_id`, `platform`, version, and activity time. |
| Release | Employee app private first | Use TestFlight, Play Internal/Closed Testing, MDM, or private distribution before any customer public release. |

This staged approach does not change the long-term Kubernetes-native target. It keeps the MVP operable for a small team while preserving a clean migration path to Kubernetes when scale demands it.

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
| `bitween-overdue-evaluator` | CronJob | Periodic business-trip overdue evaluation and escalation. |
| `bitween-kpi-reflector` | CronJob or queue worker | Idempotent KPI reflection for approved lifecycle evidence. |
| `bitween-migrations` | Job | Schema and data migrations, run before rollout or as a controlled release step. |
| `bitween-observability` | ServiceMonitor/metrics integration where available | Health, metrics, logs, and audit evidence. |

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
- Migrations are explicit Jobs with rollback/restore instructions and audit logs.

## API surfaces and routing

Production API traffic is separated first by gateway/API surface, then by
versioned resource paths. The React Native employee app must not share the web
admin API surface.

| Surface | Gateway/service target | Exposure | Version rule |
| --- | --- | --- | --- |
| Web Admin API | `admin-api.bitween.example` | Admin web only, MFA/IP controls | `/api/admin/v1/*` |
| Mobile App API | `mobile-api.bitween.example` | iOS/Android employee app, token + device binding | `/api/v{n}/*`, e.g. `/api/v1/login`, `/api/v1/branches`, `/api/v1/tasks`, `/api/v2/tasks` |
| Public Customer API | `public-api.bitween.example` | External customer/partner integrations, rate-limited | `/api/public/v1/*` |
| Internal Admin API | `internal-api.bitween.local` | Private subnet operations/batch/security only | `/api/internal/v1/*` |

Planned service routes:

| Route | Owner | Notes |
| --- | --- | --- |
| `/api/payroll/v1/runs` | Rust payroll API | Run or validate payroll automation requests. |
| `/api/payroll/v1/runs/validate` | Rust payroll API | Validate without generating payroll outputs. |
| `/api/payroll/v1/healthz` | Rust payroll API | Probe-safe health payload from `PayrollApiService::health()`. |
| `/api/payroll/v1/readiness` | Rust payroll/readiness API | Tenant/site readiness cards for frontend dashboards. |
| `/api/workflow/v1/*` | Rust workflow API | Documents, inbox, forms, execution tasks, trip lifecycle. |
| `/api/kpi/v1/*` | Rust KPI API | Individual and manager performance records. |
| `/api/v1/*` on Mobile App API | Rust mobile API | Device auth, attendance events, branch list, tasks, profile, leave, payroll preview. |
| `/api/v2/tasks` on Mobile App API | Rust mobile API | Versioned task payload evolution without breaking existing app releases. |
| `/api/ai/v1/*` | Rust policy gateway + provider adapter | AI requests with tenant/user safety policy and secret isolation. |

## Rollout model

1. Maintain Kubernetes release manifests under a dedicated deployment surface such as `deploy/kubernetes/` once the Rust service images exist.
2. Build images for frontend, API, worker, migration, and scheduled jobs.
3. Run migration Job against staging data.
4. Deploy Rust API and workers behind Services.
5. Expose frontend through Ingress or Gateway API.
6. Enable readiness-gated rollout and HPA in staging.
7. Run parity suites against current compatibility behavior.
8. Promote with canary or rolling update.
9. Decommission compatibility adapters only after zero-production-use evidence.

## Backlog linkage

The Rust rewrite is tracked in `docs/RUST_BACKEND_MIGRATION.md` and `.omx/backlog.md`. Every backend slice must be source-driven, test-first, doubt-reviewed, code-reviewed, and simplified before decommissioning the compatibility path.
