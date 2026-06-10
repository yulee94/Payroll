# Bitween managed-Kubernetes release and rollback runbook

## Scope

This runbook covers the Bitween internal managed-Kubernetes release surface under
`deploy/kubernetes/base`. It protects the frontend shell, Rust API, PostgreSQL
migration job, self-hosted PostgreSQL, and self-hosted RustFS object storage.

## Promotion checks

1. Verify the exact Git commit, immutable image tags, and image digests are
   recorded in the release ticket.
2. Run the local gate: `npm run verify:kubernetes-manifests --prefix apps/bitween-platform-ui`.
3. Run the product gates: `npm run verify:data-mode --prefix apps/bitween-platform-ui`,
   `npm run verify:security-gates --prefix apps/bitween-platform-ui`, and
   `npm run verify:performance-gates --prefix apps/bitween-platform-ui`.
4. Run Buck2 Rust verification for the service images being promoted.
5. Confirm the external secret manager has reconciled managed Secrets named
   `bitween-runtime-secrets`, `bitween-postgres-auth`, and `bitween-rustfs-auth`.
6. Confirm PostgreSQL backup and point-in-time recovery status is healthy before
   the migration job runs.
7. Confirm RustFS bucket versioning and object-lock policy for archive originals
   and audit evidence before opening archive intake.
8. Run `kubectl diff -k deploy/kubernetes/base` and resolve any drift before
   applying the release.
9. Confirm ServiceMonitor targets are discovered and OpenTelemetry collector
   export is healthy for the API, frontend, and worker audit stream.
10. Confirm the current PostgreSQL/RustFS restore drill evidence is attached to
   the release ticket.

## Apply sequence

1. Apply the namespace and data-plane resources first: `kubectl apply -k deploy/kubernetes/base`.
2. Wait for PostgreSQL and RustFS readiness.
3. Run the migration job and store its logs in the audit evidence bucket.
4. Wait for `bitween-api` readiness, then `bitween-frontend` readiness.
5. Confirm the `cloud_native_audit_worker` CronJob completes once and emits its
   JSON report for log/audit pipeline capture.
6. Confirm Gateway API route status before inviting users into the release wave.

## Rollback sequence

1. Freeze new archive admissions and payroll execution in the Admin policy gate.
2. Roll back stateless workloads: `kubectl rollout undo deployment/bitween-api -n bitween-prod`
   and `kubectl rollout undo deployment/bitween-frontend -n bitween-prod`.
3. If a migration must be reversed, restore PostgreSQL through the audited
   point-in-time recovery marker captured before the migration job. Do not store
   binary database snapshots in Git.
4. Keep RustFS original objects immutable. Use object versioning to select the
   prior logical version and update PostgreSQL metadata through a reviewed
   rollback admission record.
5. Emit a rollback audit entry containing Git commit, image digests, migration
   version, PostgreSQL restore marker, RustFS object version ids, operator id,
   and user-facing impact window.
6. Re-run the same local and cluster gates before reopening business operations.

## Drift response

Any drift in Deployment probes, security context, NetworkPolicy, image tags,
Secrets handling, SLO manifests, ServiceMonitor targets, worker CronJobs,
tenant ResourceQuota/LimitRange, or rollback annotations is a release blocker.
The fix is committed to Git first, then applied through the same GitOps path.
