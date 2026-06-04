# Kubernetes-native production stack

## Status

Accepted direction as of 2026-06-04.

Bitween production must run as a Kubernetes-native stack. Local compatibility runners and Python adapters are not production services; they exist only to preserve behavior until Rust services and TypeScript client surfaces have parity.

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
- Rust services own backend behavior in production.
- TypeScript frontend owns user-facing frontend delivery.
- API state is tenant/legal-entity scoped; group-root storage must never bypass legal-tenant authorization.
- Configuration uses ConfigMaps; credentials and API keys use Secrets or an external secret manager.
- All HTTP workloads expose dedicated startup/readiness/liveness endpoints.
- Horizontal scaling uses HPA only after resource requests, readiness behavior, and idempotency are verified.
- Scheduled lifecycle work runs as CronJobs or queue workers, not as ad-hoc local scripts.
- Production persistence is a database/object-storage layer behind Rust services. Local JSON stores are compatibility fixtures only.
- Migrations are explicit Jobs with rollback/restore instructions and audit logs.

## API routing

Planned service routes:

| Route | Owner | Notes |
| --- | --- | --- |
| `/api/payroll/v1/runs` | Rust payroll API | Run or validate payroll automation requests. |
| `/api/payroll/v1/runs/validate` | Rust payroll API | Validate without generating payroll outputs. |
| `/api/payroll/v1/readiness` | Rust payroll/readiness API | Tenant/site readiness cards for frontend dashboards. |
| `/api/workflow/v1/*` | Rust workflow API | Documents, inbox, forms, execution tasks, trip lifecycle. |
| `/api/kpi/v1/*` | Rust KPI API | Individual and manager performance records. |
| `/api/mobile/v1/*` | Rust mobile API | Device auth, attendance events, profile, leave, payroll preview. |
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
