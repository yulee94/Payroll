import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..", "..", "..");
const deployRoot = join(root, "deploy", "kubernetes");
const baseRoot = join(deployRoot, "base");
const sloRoot = join(deployRoot, "slo");
const runbookPath = join(deployRoot, "runbooks", "release-rollback.md");
const packagePath = join(__dirname, "..", "package.json");
const workflowPath = join(root, ".github", "workflows", "tests.yml");
const runtimeVerifierPath = join(__dirname, "verify-runtime-data-mode.mjs");

const errors = [];
const requiredBaseFiles = [
  "kustomization.yaml",
  "namespace.yaml",
  "serviceaccounts.yaml",
  "configmap.yaml",
  "services.yaml",
  "api-deployment.yaml",
  "frontend-deployment.yaml",
  "postgres-statefulset.yaml",
  "rustfs-statefulset.yaml",
  "postgres-migrate-job.yaml",
  "worker-cronjobs.yaml",
  "observability.yaml",
  "gateway-httproute.yaml",
  "tenant-isolation.yaml",
  "networkpolicies.yaml",
  "poddisruptionbudgets.yaml",
];
const requiredSloFiles = [
  "bitween-api.availability.openslo.yaml",
  "bitween-frontend.availability.openslo.yaml",
];
const scrubbedTenantPattern = new RegExp(
  [`CO${"SS"}`, `tenant-${"co"}${"ss"}`, "Seoul\\s*·\\s*2026-06"].join("|"),
  "i",
);

function readText(path) {
  return readFileSync(path, "utf8");
}

function requireText(source, text, message) {
  if (!source.includes(text)) errors.push(message);
}

function rejectPattern(source, pattern, message) {
  if (pattern.test(source)) errors.push(message);
}

function requirePattern(source, pattern, message) {
  if (!pattern.test(source)) errors.push(message);
}

function fileExists(path) {
  try {
    return statSync(path).isFile();
  } catch {
    return false;
  }
}

function listFiles(startPath, files = []) {
  const stat = statSync(startPath);
  if (stat.isDirectory()) {
    for (const entry of readdirSync(startPath)) listFiles(join(startPath, entry), files);
    return files;
  }
  if (stat.isFile()) files.push(startPath);
  return files;
}

function assertAllFilesPresent() {
  for (const file of requiredBaseFiles) {
    const path = join(baseRoot, file);
    if (!fileExists(path)) errors.push(`Missing Kubernetes base file: ${relative(root, path)}`);
  }
  for (const file of requiredSloFiles) {
    const path = join(sloRoot, file);
    if (!fileExists(path)) errors.push(`Missing OpenSLO file: ${relative(root, path)}`);
  }
  if (!fileExists(runbookPath)) errors.push(`Missing rollback runbook: ${relative(root, runbookPath)}`);
}

function assertNoUnsafeText() {
  const forbidden = /\b(TODO|TBD|FIXME|placeholder|changeme|example|sample|demo|mock|rustfsadmin|password:)\b/i;
  for (const file of listFiles(deployRoot)) {
    if (![".yaml", ".yml", ".md"].includes(extname(file))) continue;
    const source = readText(file);
    const rel = relative(root, file);
    rejectPattern(source, forbidden, `${rel} contains unsafe release text or known default credentials.`);
    rejectPattern(source, /image:\s*[^\n]*:latest\b/i, `${rel} uses an unpinned latest image tag.`);
    rejectPattern(source, /kind:\s*Secret\b/, `${rel} must not commit Kubernetes Secret objects; use externally managed Secrets.`);
    rejectPattern(source, new RegExp(["Min", "IO"].join(""), "i"), `${rel} must not reference the retired object-store choice.`);
    rejectPattern(source, scrubbedTenantPattern, `${rel} contains scrubbed tenant/personnel seed data.`);
  }
}

function assertKustomize() {
  const source = readText(join(baseRoot, "kustomization.yaml"));
  requireText(source, "kind: Kustomization", "Kubernetes base must be a Kustomize base.");
  for (const file of requiredBaseFiles.filter((file) => file !== "kustomization.yaml")) {
    requireText(source, `- ${file}`, `kustomization.yaml must include ${file}.`);
  }
  requireText(source, "images:", "Kustomize base must declare image transform entries for release pinning.");
  requireText(source, "ghcr.io/bitween/payroll-api", "Kustomize images must include the Rust API image.");
  requireText(source, "ghcr.io/bitween/platform-ui", "Kustomize images must include the frontend image.");
  requireText(source, "rustfs/rustfs", "Kustomize images must include RustFS.");
  requireText(source, "docker.io/library/postgres", "Kustomize images must include PostgreSQL.");
}

function assertNamespaceAndConfig() {
  const namespace = readText(join(baseRoot, "namespace.yaml"));
  requireText(namespace, "pod-security.kubernetes.io/enforce: restricted", "Namespace must enforce restricted Pod Security Admission.");
  const config = readText(join(baseRoot, "configmap.yaml"));
  requireText(config, "BITWEEN_DEFAULT_LOCALE: ko-KR", "Runtime ConfigMap must keep Korean-first locale.");
  requireText(config, "BITWEEN_PUBLIC_TENANT_NAME: Acme Corporation", "Runtime ConfigMap must use Acme Corporation as the neutral default tenant name.");
  requireText(config, "BITWEEN_AUTH_REQUIRED: \"true\"", "Runtime ConfigMap must require auth in production.");
  requireText(config, "BITWEEN_POSTGRES_TLS_POLICY: verify-full", "Runtime ConfigMap must wire the Rust PostgreSQL TLS policy expected by runtime binaries.");
  requireText(config, "BITWEEN_POSTGRES_TENANT_ID: tenant-acme", "Runtime ConfigMap must provide the PostgreSQL tenant scope expected by Rust stores.");
  requireText(config, "BITWEEN_POSTGRES_LEGAL_ENTITY_ID: acme-corp", "Runtime ConfigMap must provide the PostgreSQL legal-entity scope expected by Rust stores.");
  requireText(config, "BITWEEN_POSTGRES_WORKPLACE_ID: seoul", "Runtime ConfigMap must provide the PostgreSQL workplace scope expected by Rust stores.");
  requireText(config, "BITWEEN_RUSTFS_ENDPOINT:", "Runtime ConfigMap must wire RustFS endpoint for archive/object storage.");
  requireText(config, "BITWEEN_RUSTFS_BUCKET: bitween-archive-originals", "Runtime ConfigMap must wire the RustFS archive bucket expected by runtime upload/source-sync paths.");
  requireText(config, "BITWEEN_RUSTFS_BUCKET_ARCHIVE: bitween-archive-originals", "Runtime ConfigMap must keep the semantic RustFS archive bucket alias.");
  requireText(config, "BITWEEN_RUSTFS_BUCKET_EVIDENCE: bitween-audit-evidence", "Runtime ConfigMap must wire the RustFS evidence bucket.");
  requireText(config, "BITWEEN_AUDIT_EXPORT_BUCKET: bitween-audit-evidence", "Runtime ConfigMap must wire the audit export bucket consumed by the cloud-native audit worker.");
  requireText(config, "BITWEEN_AUDIT_EVENT_STREAM: postgres+otel", "Runtime ConfigMap must declare PostgreSQL plus OpenTelemetry audit event sinks.");
  requireText(config, "BITWEEN_OTEL_SERVICE_NAMESPACE: bitween", "Runtime ConfigMap must declare the OpenTelemetry service namespace.");
  requireText(config, "BITWEEN_OTEL_EXPORTER_OTLP_ENDPOINT:", "Runtime ConfigMap must wire the OpenTelemetry OTLP endpoint.");
}

function assertWorkload(path, name, { stateful = false, http = true } = {}) {
  const source = readText(path);
  const rel = relative(root, path);
  requireText(source, `name: ${name}`, `${rel} must name ${name}.`);
  requireText(source, "automountServiceAccountToken: false", `${rel} must disable default service-account token mounting.`);
  requireText(source, "runAsNonRoot: true", `${rel} must run as non-root.`);
  requireText(source, "seccompProfile:", `${rel} must use a seccomp profile.`);
  requireText(source, "type: RuntimeDefault", `${rel} must use RuntimeDefault seccomp.`);
  requireText(source, "allowPrivilegeEscalation: false", `${rel} must disable privilege escalation.`);
  requireText(source, "drop: [\"ALL\"]", `${rel} must drop all Linux capabilities.`);
  requireText(source, "resources:", `${rel} must declare resource requests and limits.`);
  requireText(source, "requests:", `${rel} must declare resource requests.`);
  requireText(source, "limits:", `${rel} must declare resource limits.`);
  requireText(source, "startupProbe:", `${rel} must declare a startup probe.`);
  requireText(source, "readinessProbe:", `${rel} must declare a readiness probe.`);
  requireText(source, "livenessProbe:", `${rel} must declare a liveness probe.`);
  requireText(source, "preStop:", `${rel} must include graceful preStop handling.`);
  requireText(source, "terminationGracePeriodSeconds:", `${rel} must declare termination grace.`);
  if (!stateful) {
    requireText(source, "readOnlyRootFilesystem: true", `${rel} stateless containers must use read-only root filesystems.`);
    requireText(source, "replicas: 2", `${rel} stateless deployments must start with at least two replicas.`);
    requireText(source, "maxUnavailable: 0", `${rel} rolling update must keep capacity available.`);
  } else {
    requireText(source, "volumeClaimTemplates:", `${rel} stateful workloads must declare persistent volume claims.`);
  }
  if (http) requirePattern(source, /httpGet:\n\s+path:/, `${rel} must use HTTP health probes where applicable.`);
  rejectPattern(source, /privileged:\s*true/, `${rel} must not run privileged containers.`);
  rejectPattern(source, /hostNetwork:\s*true/, `${rel} must not use hostNetwork.`);
}

function assertWorkloads() {
  assertWorkload(join(baseRoot, "api-deployment.yaml"), "bitween-api");
  const api = readText(join(baseRoot, "api-deployment.yaml"));
  requireText(api, "secretKeyRef:", "API deployment must pull sensitive values from Secrets only.");
  requireText(api, "BITWEEN_POSTGRES_DSN", "API deployment must wire the PostgreSQL DSN env var consumed by Rust stores.");
  requireText(api, "key: postgres-dsn", "API deployment must source PostgreSQL DSN from the external runtime Secret.");
  rejectPattern(api, /BITWEEN_DATABASE_URL/, "API deployment must not use a stale PostgreSQL env name that Rust stores do not consume.");
  requireText(api, "BITWEEN_RUSTFS_ACCESS_KEY", "API deployment must wire RustFS credentials by Secret reference.");
  requireText(api, "bitween.io/slo-bundle", "API deployment must link SLO evidence.");

  assertWorkload(join(baseRoot, "frontend-deployment.yaml"), "bitween-frontend");
  const frontend = readText(join(baseRoot, "frontend-deployment.yaml"));
  requireText(frontend, "BITWEEN_API_BASE_URL", "Frontend deployment must route to the API surface explicitly.");
  requireText(frontend, "bitween.io/slo-bundle", "Frontend deployment must link SLO evidence.");

  assertWorkload(join(baseRoot, "postgres-statefulset.yaml"), "bitween-postgres", { stateful: true, http: false });
  const postgres = readText(join(baseRoot, "postgres-statefulset.yaml"));
  requireText(postgres, "pg_isready", "PostgreSQL StatefulSet must probe with pg_isready.");
  requireText(postgres, "bitween.io/backup-policy: point-in-time-recovery", "PostgreSQL StatefulSet must require PITR backup policy evidence.");

  assertWorkload(join(baseRoot, "rustfs-statefulset.yaml"), "bitween-rustfs", { stateful: true });
  const rustfs = readText(join(baseRoot, "rustfs-statefulset.yaml"));
  requireText(rustfs, "rustfs/rustfs:1.0.0-beta.7", "RustFS StatefulSet must pin the selected beta release instead of latest.");
  requireText(rustfs, "RUSTFS_ACCESS_KEY", "RustFS StatefulSet must source access key from a Secret.");
  requireText(rustfs, "RUSTFS_SECRET_KEY", "RustFS StatefulSet must source secret key from a Secret.");
  requireText(rustfs, "RUSTFS_CONSOLE_ENABLE", "RustFS StatefulSet must explicitly control console exposure.");
  requireText(rustfs, "value: \"false\"", "RustFS console must stay disabled in the app namespace.");
}

function assertJobGatewayNetworkAndPdb() {
  const job = readText(join(baseRoot, "postgres-migrate-job.yaml"));
  requireText(job, "kind: Job", "PostgreSQL migration must be a Kubernetes Job.");
  requireText(job, "restartPolicy: Never", "Migration Job must not run as a long-lived process.");
  requireText(job, "backoffLimit: 1", "Migration Job must have a bounded retry policy.");
  requireText(job, "postgres_migrate", "Migration Job must execute the Rust postgres_migrate binary.");
  requireText(job, "bitween.io/rollback-runbook", "Migration Job must link rollback evidence.");
  requireText(job, "secretKeyRef:", "Migration Job must source database DSN from Secret.");
  requireText(job, "BITWEEN_POSTGRES_DSN", "Migration Job must wire the PostgreSQL DSN env var consumed by postgres_migrate.");
  requireText(job, "key: postgres-dsn", "Migration Job must source PostgreSQL DSN from the external runtime Secret.");
  rejectPattern(job, /BITWEEN_DATABASE_URL/, "Migration Job must not use a stale PostgreSQL env name that postgres_migrate does not consume.");

  const route = readText(join(baseRoot, "gateway-httproute.yaml"));
  requireText(route, "kind: HTTPRoute", "Gateway surface must use Gateway API HTTPRoute.");
  requireText(route, "bitween-edge", "HTTPRoute must attach to the managed edge Gateway.");
  requireText(route, "bitween-api", "HTTPRoute must route API traffic to bitween-api.");
  requireText(route, "bitween-frontend", "HTTPRoute must route shell traffic to bitween-frontend.");

  const network = readText(join(baseRoot, "networkpolicies.yaml"));
  requireText(network, "name: bitween-default-deny", "NetworkPolicy must include default-deny isolation.");
  requireText(network, "podSelector: {}", "Default-deny NetworkPolicy must select all pods.");
  requireText(network, "bitween-api-traffic", "NetworkPolicy must scope API traffic.");
  requireText(network, "bitween-data-plane", "NetworkPolicy must scope PostgreSQL/RustFS data-plane traffic.");
  requireText(network, "bitween-worker-egress", "NetworkPolicy must scope worker traffic.");
  requireText(network, "bitween-cloud-native-audit-worker", "NetworkPolicy must include the cloud-native audit worker.");
  requireText(network, "kubernetes.io/metadata.name: kube-system", "NetworkPolicy must explicitly allow DNS egress.");

  const pdb = readText(join(baseRoot, "poddisruptionbudgets.yaml"));
  for (const name of ["bitween-api", "bitween-frontend", "bitween-postgres", "bitween-rustfs"]) {
    requireText(pdb, `name: ${name}`, `PodDisruptionBudget must cover ${name}.`);
  }
}

function assertWorkerCronJobs() {
  const worker = readText(join(baseRoot, "worker-cronjobs.yaml"));
  requireText(worker, "kind: CronJob", "Worker manifest must declare Kubernetes CronJob resources.");
  requireText(worker, "name: bitween-cloud-native-audit-worker", "Worker CronJob must include the cloud-native audit worker.");
  requireText(worker, "schedule: \"*/30 * * * *\"", "Cloud-native audit worker must run on a bounded production cadence.");
  requireText(worker, "timeZone: Asia/Seoul", "Cloud-native audit worker schedule must use the Korea operations timezone.");
  requireText(worker, "concurrencyPolicy: Forbid", "Cloud-native audit worker must prevent overlapping runs.");
  requireText(worker, "startingDeadlineSeconds: 300", "Cloud-native audit worker must have a bounded start deadline.");
  requireText(worker, "successfulJobsHistoryLimit: 3", "Cloud-native audit worker must retain successful run evidence.");
  requireText(worker, "failedJobsHistoryLimit: 5", "Cloud-native audit worker must retain failed run evidence.");
  requireText(worker, "backoffLimit: 1", "Cloud-native audit worker must have a bounded retry policy.");
  requireText(worker, "cloud_native_audit_worker", "Cloud-native audit worker must execute the Rust/Buck2 binary.");
  requireText(worker, "serviceAccountName: bitween-worker", "Cloud-native audit worker must use the worker service account.");
  requireText(worker, "automountServiceAccountToken: false", "Cloud-native audit worker must not mount default service-account tokens.");
  requireText(worker, "restartPolicy: Never", "Cloud-native audit worker must be a bounded job run.");
  requireText(worker, "runAsNonRoot: true", "Cloud-native audit worker must run as non-root.");
  requireText(worker, "type: RuntimeDefault", "Cloud-native audit worker must use RuntimeDefault seccomp.");
  requireText(worker, "allowPrivilegeEscalation: false", "Cloud-native audit worker must disable privilege escalation.");
  requireText(worker, "readOnlyRootFilesystem: true", "Cloud-native audit worker must use a read-only root filesystem.");
  requireText(worker, "drop: [\"ALL\"]", "Cloud-native audit worker must drop all Linux capabilities.");
  requireText(worker, "resources:", "Cloud-native audit worker must declare resources.");
  requireText(worker, "requests:", "Cloud-native audit worker must declare resource requests.");
  requireText(worker, "limits:", "Cloud-native audit worker must declare resource limits.");
  requireText(worker, "BITWEEN_POSTGRES_DSN", "Cloud-native audit worker must receive PostgreSQL DSN by Secret reference.");
  requireText(worker, "key: postgres-dsn", "Cloud-native audit worker must source PostgreSQL DSN from the external runtime Secret.");
  requireText(worker, "BITWEEN_RUSTFS_ACCESS_KEY", "Cloud-native audit worker must receive RustFS access key by Secret reference.");
  requireText(worker, "BITWEEN_RUSTFS_SECRET_KEY", "Cloud-native audit worker must receive RustFS secret key by Secret reference.");
  requireText(worker, "BITWEEN_OTEL_SERVICE_NAME", "Cloud-native audit worker must set its OpenTelemetry service name.");
  requireText(worker, "bitween.io/audit-event-schema: bitween.audit-event.v1", "Cloud-native audit worker must declare its audit event schema.");
  requireText(worker, "service.name,http.response.status_code", "Cloud-native audit worker must record OpenTelemetry semantic-convention evidence.");

  const serviceAccounts = readText(join(baseRoot, "serviceaccounts.yaml"));
  requireText(serviceAccounts, "name: bitween-worker", "ServiceAccount manifest must include the worker identity.");
}

function assertObservabilityAndTenantIsolation() {
  const observability = readText(join(baseRoot, "observability.yaml"));
  requireText(observability, "apiVersion: monitoring.coreos.com/v1", "Observability manifest must use Prometheus Operator ServiceMonitor resources.");
  requireText(observability, "kind: ServiceMonitor", "Observability manifest must declare ServiceMonitor resources.");
  requireText(observability, "name: bitween-api", "ServiceMonitor must cover the Rust API.");
  requireText(observability, "name: bitween-frontend", "ServiceMonitor must cover the frontend shell.");
  requireText(observability, "path: /metrics", "ServiceMonitor endpoints must scrape /metrics.");
  requireText(observability, "interval: 30s", "ServiceMonitor endpoints must set an explicit interval.");
  requireText(observability, "targetLabel: service_namespace", "ServiceMonitor relabeling must expose the OpenTelemetry service namespace.");
  requireText(observability, "replacement: bitween", "ServiceMonitor relabeling must use the Bitween service namespace.");
  requireText(observability, "targetLabel: data_classification", "ServiceMonitor relabeling must preserve data classification.");

  const tenant = readText(join(baseRoot, "tenant-isolation.yaml"));
  requireText(tenant, "kind: ResourceQuota", "Tenant isolation manifest must include ResourceQuota.");
  requireText(tenant, "kind: LimitRange", "Tenant isolation manifest must include LimitRange.");
  requireText(tenant, "kind: Role", "Tenant isolation manifest must include a read-only release operator Role.");
  requireText(tenant, "kind: RoleBinding", "Tenant isolation manifest must bind the release operator Role.");
  requireText(tenant, "bitween.io/tenant-scope: tenant-acme", "Tenant isolation resources must carry the tenant scope.");
  requireText(tenant, "persistentvolumeclaims: \"8\"", "Tenant ResourceQuota must bound persistent-volume claims.");
  requireText(tenant, "pods: \"32\"", "Tenant ResourceQuota must bound pod count.");
  requireText(tenant, "bitween-release-operators", "Tenant RoleBinding must use the release operator group.");
}

function assertSloAndRunbook() {
  for (const file of requiredSloFiles) {
    const source = readText(join(sloRoot, file));
    const rel = `deploy/kubernetes/slo/${file}`;
    requireText(source, "apiVersion: openslo/v1", `${rel} must use OpenSLO v1.`);
    requireText(source, "kind: SLO", `${rel} must declare kind SLO.`);
    requireText(source, "data_classes:", `${rel} must label data classes.`);
    requireText(source, "pack: internal-korea", `${rel} must declare internal Korea pack context.`);
    requireText(source, "objectives:", `${rel} must declare SLO objectives.`);
    requireText(source, "isRolling: true", `${rel} must use a rolling time window.`);
    requirePattern(source, /target:\s*0\.99[0-9]/, `${rel} must set a production-grade availability target.`);
    requireText(source, "http_response_status_code", `${rel} must use OpenTelemetry-aligned HTTP status attributes.`);
  }
  const runbook = readText(runbookPath);
  requireText(runbook, "kubectl apply -k deploy/kubernetes/base", "Runbook must include the GitOps apply path.");
  requireText(runbook, "kubectl diff -k deploy/kubernetes/base", "Runbook must include a server-side drift preview path.");
  requireText(runbook, "kubectl rollout undo deployment/bitween-api", "Runbook must include API rollback command.");
  requireText(runbook, "point-in-time recovery", "Runbook must use PostgreSQL PITR rather than Git binary snapshots.");
  requireText(runbook, "object versioning", "Runbook must use RustFS object versioning for object rollback.");
  requireText(runbook, "Do not store\n   binary database snapshots in Git", "Runbook must forbid binary database snapshots in Git.");
  requireText(runbook, "cloud_native_audit_worker", "Runbook must include cloud-native audit worker evidence capture.");
  requireText(runbook, "ServiceMonitor", "Runbook must include ServiceMonitor evidence checks.");
  requireText(runbook, "OpenTelemetry", "Runbook must include OpenTelemetry evidence checks.");
  requireText(runbook, "image digests", "Runbook must require image digest evidence before promotion.");
  requireText(runbook, "external secret manager", "Runbook must verify the external secret manager contract.");
  requireText(runbook, "restore drill", "Runbook must require PostgreSQL/RustFS restore drill evidence.");
  requireText(runbook, "Drift response", "Runbook must define drift response.");
}

function assertVerifierWiring() {
  const packageJson = JSON.parse(readText(packagePath));
  if (packageJson.scripts?.["verify:kubernetes-manifests"] !== "node scripts/verify-kubernetes-manifests.mjs") {
    errors.push("package.json must expose verify:kubernetes-manifests.");
  }
  const workflow = readText(workflowPath);
  requireText(workflow, "npm run verify:kubernetes-manifests", "CI must run verify:kubernetes-manifests with platform UI gates.");
  requireText(workflow, "buck2 build //crates/payroll-api:cloud_native_audit_worker", "CI must build the cloud-native audit worker with Buck2.");
  requireText(workflow, "buck2 build '//crates/payroll-api:cloud_native_audit_worker[check]'", "CI must type-check the cloud-native audit worker with Buck2.");
  requireText(workflow, "buck2 build '//crates/payroll-api:cloud_native_audit_worker[clippy.txt]'", "CI must lint the cloud-native audit worker with Buck2.");
  requireText(workflow, "buck2 test //crates/payroll-api:cloud_native_audit_worker_test", "CI must test the cloud-native audit worker with Buck2.");
  const runtimeVerifier = readText(runtimeVerifierPath);
  requireText(runtimeVerifier, "verify-kubernetes-manifests.mjs", "Runtime verifier must guard Kubernetes manifest verification wiring.");
}

assertAllFilesPresent();
assertNoUnsafeText();
assertKustomize();
assertNamespaceAndConfig();
assertWorkloads();
assertJobGatewayNetworkAndPdb();
assertWorkerCronJobs();
assertObservabilityAndTenantIsolation();
assertSloAndRunbook();
assertVerifierWiring();

if (errors.length > 0) {
  console.error("Kubernetes manifest verification failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("Kubernetes manifest verification passed.");
