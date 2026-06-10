import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appPath = join(__dirname, "..", "App.tsx");
const packagePath = join(__dirname, "..", "package.json");
const previewAppPath = join(__dirname, "..", "preview", "app.js");
const previewServerPath = join(__dirname, "..", "preview", "server.js");
const previewStylesPath = join(__dirname, "..", "preview", "styles.css");
const authRouteScriptPath = join(__dirname, "verify-auth-routes.mjs");
const routeAuthorizationScriptPath = join(__dirname, "verify-route-authorization.mjs");
const signedOutAuthUxScriptPath = join(__dirname, "verify-signed-out-auth-ux.mjs");
const archiveIntakeStoriesScriptPath = join(__dirname, "verify-archive-intake-stories.mjs");
const noPythonSourceScriptPath = join(__dirname, "verify-no-python-source.mjs");
const buck2OnlyScriptPath = join(__dirname, "verify-buck2-only.mjs");
const performanceGateScriptPath = join(__dirname, "verify-performance-gates.mjs");
const securityGateScriptPath = join(__dirname, "verify-security-gates.mjs");
const kubernetesManifestScriptPath = join(__dirname, "verify-kubernetes-manifests.mjs");
const authSessionScriptPath = join(__dirname, "verify-auth-session.mjs");
const officeContractScriptPath = join(__dirname, "verify-office-contract.mjs");
const sourceComponentsPath = join(__dirname, "..", "src", "components.tsx");
const sourceDataPath = join(__dirname, "..", "src", "data.ts");
const sourceScreensPath = join(__dirname, "..", "src", "screens.tsx");
const sourceThemePath = join(__dirname, "..", "src", "theme.ts");
const sourceTypesPath = join(__dirname, "..", "src", "types.ts");
const sourceViewModelPath = join(__dirname, "..", "src", "viewModel.ts");
const sourceCatalogPath = join(__dirname, "..", "src", "i18n", "catalog.json");
const contractPath = join(__dirname, "..", "..", "..", "frontend", "src", "contracts", "payrollApi.ts");
const rustLibPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "lib.rs");
const rustApiContractPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "api_contract.rs");
const rustAuthPolicyPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "auth_policy.rs");
const rustPlatformViewPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "platform_view.rs");
const rustLiveBinPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "bin", "platform_live_view.rs");
const rustAuthSessionPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "auth_session.rs");
const rustAuthSessionSchemaPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "auth_session_schema.rs");
const rustAuthSessionBinPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "bin", "auth_session_validate.rs");
const rustAuthzDecisionBinPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "bin", "authz_decision.rs");
const rustHrEmployeeStorePath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "bin", "hr_employee_store.rs");
const rustArchiveIntakeStorePath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "bin", "archive_intake_store.rs");
const rustUserPreferenceStorePath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "bin", "user_preference_store.rs");
const rustWorkflowTemplateStorePath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "bin", "workflow_template_store.rs");
const rustPostgresMigratePath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "bin", "postgres_migrate.rs");
const rustCloudNativeAuditWorkerPath = join(
  __dirname,
  "..",
  "..",
  "..",
  "crates",
  "payroll-api",
  "src",
  "bin",
  "cloud_native_audit_worker.rs",
);
const rustArchiveIntakeSchemaPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "archive_intake_schema.rs");
const rustArchiveRollbackSchemaPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "archive_rollback_schema.rs");
const rustWorkflowTemplateSchemaPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "workflow_template_schema.rs");
const rustHrEmployeeSchemaPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "hr_employee_schema.rs");
const rustPayrollAttendanceSchemaPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "payroll_attendance_schema.rs");
const rustUserPreferenceSchemaPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "user_preference_schema.rs");
const rustPostgresRepositoryPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "src", "postgres_repository.rs");
const archivePostgresMigrationPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "migrations", "001_archive_intake.sql");
const workflowPostgresMigrationPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "migrations", "002_workflow_templates.sql");
const hrEmployeePostgresMigrationPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "migrations", "003_hr_employee.sql");
const userPreferencePostgresMigrationPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "migrations", "004_user_preferences.sql");
const payrollAttendancePostgresMigrationPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "migrations", "005_payroll_attendance_intake.sql");
const archiveRollbackPostgresMigrationPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "migrations", "006_archive_admission_rollback.sql");
const authSessionPostgresMigrationPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "migrations", "007_auth_session_security.sql");
const authSecurityContractPath = join(__dirname, "..", "..", "..", "docs", "AUTH_SECURITY_CONTRACT.md");
const officeProductContractPath = join(__dirname, "..", "..", "..", "docs", "OFFICE_PRODUCT_CONTRACT.md");
const productionFastPathPath = join(__dirname, "..", "..", "..", "docs", "PRODUCTION_DELIVERY_FAST_PATH.md");
const kubernetesNativeStackPath = join(__dirname, "..", "..", "..", "docs", "KUBERNETES_NATIVE_STACK.md");
const postgresAdapterDecisionPath = join(__dirname, "..", "..", "..", "docs", "POSTGRES_REPOSITORY_ADAPTER_DECISION.md");
const rootCargoLockPath = join(__dirname, "..", "..", "..", "Cargo.lock");
const payrollCargoTomlPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "Cargo.toml");
const payrollBuckPath = join(__dirname, "..", "..", "..", "crates", "payroll-api", "BUCK");
const thirdPartyRustBuckPath = join(__dirname, "..", "..", "..", "third-party", "rust", "BUCK");
const getrandomFixupPath = join(__dirname, "..", "..", "..", "third-party", "rust", "fixups", "getrandom", "fixups.toml");
const libcFixupPath = join(__dirname, "..", "..", "..", "third-party", "rust", "fixups", "libc", "fixups.toml");
const mioFixupPath = join(__dirname, "..", "..", "..", "third-party", "rust", "fixups", "mio", "fixups.toml");
const parkingLotCoreFixupPath = join(
  __dirname,
  "..",
  "..",
  "..",
  "third-party",
  "rust",
  "fixups",
  "parking_lot_core",
  "fixups.toml",
);
const tokioFixupPath = join(__dirname, "..", "..", "..", "third-party", "rust", "fixups", "tokio", "fixups.toml");
const tokioUtilFixupPath = join(
  __dirname,
  "..",
  "..",
  "..",
  "third-party",
  "rust",
  "fixups",
  "tokio-util",
  "fixups.toml",
);
const rustlsFixupPath = join(__dirname, "..", "..", "..", "third-party", "rust", "fixups", "rustls", "fixups.toml");
const ringFixupPath = join(__dirname, "..", "..", "..", "third-party", "rust", "fixups", "ring", "fixups.toml");
const postgresProtocolPasswordPath = join(
  __dirname,
  "..",
  "..",
  "..",
  "third-party",
  "rust",
  "vendor",
  "postgres-protocol-0.6.11",
  "src",
  "password",
  "mod.rs",
);
const tokioUnixPipePath = join(
  __dirname,
  "..",
  "..",
  "..",
  "third-party",
  "rust",
  "vendor",
  "tokio-1.52.3",
  "src",
  "net",
  "unix",
  "pipe.rs",
);
const wasmEncoderReencodePath = join(
  __dirname,
  "..",
  "..",
  "..",
  "third-party",
  "rust",
  "vendor",
  "wasm-encoder-0.244.0",
  "src",
  "reencode.rs",
);
const githubWorkflowPath = join(__dirname, "..", "..", "..", ".github", "workflows", "tests.yml");
const codexCargoGuardPath = join(__dirname, "..", "..", "..", ".codex", "hooks", "buck2-cargo-guard.js");

const appSource = readFileSync(appPath, "utf8");
const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
const previewAppSource = readFileSync(previewAppPath, "utf8");
const previewServerSource = readFileSync(previewServerPath, "utf8");
const previewStylesSource = readFileSync(previewStylesPath, "utf8");
const authRouteScriptSource = readFileSync(authRouteScriptPath, "utf8");
const routeAuthorizationScriptSource = readFileSync(routeAuthorizationScriptPath, "utf8");
const signedOutAuthUxScriptSource = readFileSync(signedOutAuthUxScriptPath, "utf8");
const archiveIntakeStoriesScriptSource = readFileSync(archiveIntakeStoriesScriptPath, "utf8");
const noPythonSourceScriptSource = readFileSync(noPythonSourceScriptPath, "utf8");
const buck2OnlyScriptSource = readFileSync(buck2OnlyScriptPath, "utf8");
const performanceGateScriptSource = readFileSync(performanceGateScriptPath, "utf8");
const securityGateScriptSource = readFileSync(securityGateScriptPath, "utf8");
const kubernetesManifestScriptSource = readFileSync(kubernetesManifestScriptPath, "utf8");
const authSessionScriptSource = readFileSync(authSessionScriptPath, "utf8");
const officeContractScriptSource = readFileSync(officeContractScriptPath, "utf8");
const sourceComponentsSource = readFileSync(sourceComponentsPath, "utf8");
const sourceDataSource = readFileSync(sourceDataPath, "utf8");
const sourceScreensSource = readFileSync(sourceScreensPath, "utf8");
const sourceThemeSource = readFileSync(sourceThemePath, "utf8");
const sourceTypesSource = readFileSync(sourceTypesPath, "utf8");
const sourceViewModelSource = readFileSync(sourceViewModelPath, "utf8");
const sourceCatalogSource = readFileSync(sourceCatalogPath, "utf8");
const contractSource = readFileSync(contractPath, "utf8");
const rustLibSource = readFileSync(rustLibPath, "utf8");
const rustApiContractSource = readFileSync(rustApiContractPath, "utf8");
const rustAuthPolicySource = readFileSync(rustAuthPolicyPath, "utf8");
const rustPlatformViewSource = readFileSync(rustPlatformViewPath, "utf8");
const rustLiveBinSource = readFileSync(rustLiveBinPath, "utf8");
const rustAuthSessionSource = readFileSync(rustAuthSessionPath, "utf8");
const rustAuthSessionSchemaSource = readFileSync(rustAuthSessionSchemaPath, "utf8");
const rustAuthSessionBinSource = readFileSync(rustAuthSessionBinPath, "utf8");
const rustAuthzDecisionBinSource = readFileSync(rustAuthzDecisionBinPath, "utf8");
const rustHrEmployeeStoreSource = readFileSync(rustHrEmployeeStorePath, "utf8");
const rustArchiveIntakeStoreSource = readFileSync(rustArchiveIntakeStorePath, "utf8");
const rustUserPreferenceStoreSource = readFileSync(rustUserPreferenceStorePath, "utf8");
const rustWorkflowTemplateStoreSource = readFileSync(rustWorkflowTemplateStorePath, "utf8");
const rustPostgresMigrateSource = readFileSync(rustPostgresMigratePath, "utf8");
const rustCloudNativeAuditWorkerSource = readFileSync(rustCloudNativeAuditWorkerPath, "utf8");
const rustArchiveIntakeSchemaSource = readFileSync(rustArchiveIntakeSchemaPath, "utf8");
const rustArchiveRollbackSchemaSource = readFileSync(rustArchiveRollbackSchemaPath, "utf8");
const rustWorkflowTemplateSchemaSource = readFileSync(rustWorkflowTemplateSchemaPath, "utf8");
const rustHrEmployeeSchemaSource = readFileSync(rustHrEmployeeSchemaPath, "utf8");
const rustPayrollAttendanceSchemaSource = readFileSync(rustPayrollAttendanceSchemaPath, "utf8");
const rustUserPreferenceSchemaSource = readFileSync(rustUserPreferenceSchemaPath, "utf8");
const rustPostgresRepositorySource = readFileSync(rustPostgresRepositoryPath, "utf8");
const archivePostgresMigrationSource = readFileSync(archivePostgresMigrationPath, "utf8");
const workflowPostgresMigrationSource = readFileSync(workflowPostgresMigrationPath, "utf8");
const hrEmployeePostgresMigrationSource = readFileSync(hrEmployeePostgresMigrationPath, "utf8");
const userPreferencePostgresMigrationSource = readFileSync(userPreferencePostgresMigrationPath, "utf8");
const payrollAttendancePostgresMigrationSource = readFileSync(payrollAttendancePostgresMigrationPath, "utf8");
const archiveRollbackPostgresMigrationSource = readFileSync(archiveRollbackPostgresMigrationPath, "utf8");
const authSessionPostgresMigrationSource = readFileSync(authSessionPostgresMigrationPath, "utf8");
const authSecurityContractSource = readFileSync(authSecurityContractPath, "utf8");
const officeProductContractSource = readFileSync(officeProductContractPath, "utf8");
const productionFastPathSource = readFileSync(productionFastPathPath, "utf8");
const kubernetesNativeStackSource = readFileSync(kubernetesNativeStackPath, "utf8");
const postgresAdapterDecisionSource = readFileSync(postgresAdapterDecisionPath, "utf8");
const rootCargoLockSource = readFileSync(rootCargoLockPath, "utf8");
const payrollCargoTomlSource = readFileSync(payrollCargoTomlPath, "utf8");
const payrollBuckSource = readFileSync(payrollBuckPath, "utf8");
const thirdPartyRustBuckSource = readFileSync(thirdPartyRustBuckPath, "utf8");
const getrandomFixupSource = readFileSync(getrandomFixupPath, "utf8");
const libcFixupSource = readFileSync(libcFixupPath, "utf8");
const mioFixupSource = readFileSync(mioFixupPath, "utf8");
const parkingLotCoreFixupSource = readFileSync(parkingLotCoreFixupPath, "utf8");
const tokioFixupSource = readFileSync(tokioFixupPath, "utf8");
const tokioUtilFixupSource = readFileSync(tokioUtilFixupPath, "utf8");
const rustlsFixupSource = readFileSync(rustlsFixupPath, "utf8");
const ringFixupSource = readFileSync(ringFixupPath, "utf8");
const postgresProtocolPasswordSource = readFileSync(postgresProtocolPasswordPath, "utf8");
const tokioUnixPipeSource = readFileSync(tokioUnixPipePath, "utf8");
const wasmEncoderReencodeSource = readFileSync(wasmEncoderReencodePath, "utf8");
const githubWorkflowSource = readFileSync(githubWorkflowPath, "utf8");
const codexCargoGuardSource = readFileSync(codexCargoGuardPath, "utf8");
const errors = [];
const retiredObjectStoreName = "Min" + "IO";
const previewStylesOutsideRoot = previewStylesSource.replace(/:root\s*\{[\s\S]*?\}\s*/, "");

const requireText = (source, text, message) => {
  if (!source.includes(text)) errors.push(message);
};
const rejectText = (source, text, message) => {
  if (source.includes(text)) errors.push(message);
};
const requirePattern = (source, pattern, message) => {
  if (!pattern.test(source)) errors.push(message);
};
const rejectPattern = (source, pattern, message) => {
  if (pattern.test(source)) errors.push(message);
};
const functionBody = (source, name) => {
  const start = source.indexOf(`function ${name}`);
  if (start === -1) return "";
  const brace = source.indexOf("{", start);
  if (brace === -1) return "";
  let depth = 0;
  for (let index = brace; index < source.length; index += 1) {
    if (source[index] === "{") depth += 1;
    if (source[index] === "}") {
      depth -= 1;
      if (depth === 0) return source.slice(start, index + 1);
    }
  }
  return source.slice(start);
};

if (packageJson.scripts?.preview !== "node preview/server.js 4174") {
  errors.push("package.json preview script must serve the Rust live local review URL on port 4174.");
}
if (packageJson.scripts?.["preview:4174"] !== "node preview/server.js 4174") {
  errors.push("package.json preview:4174 script must remain pinned to port 4174.");
}
if (packageJson.scripts?.demo) {
  errors.push("package.json must not expose demo as a first-class runtime path.");
}
if (packageJson.scripts?.["check:strict-config"] !== "node scripts/check-strict-config.js") {
  errors.push("package.json must keep the strict TypeScript guard script.");
}
if (packageJson.scripts?.["verify:buck2-only"] !== "node scripts/verify-buck2-only.mjs") {
  errors.push("package.json must keep the Buck2-only cargo enforcement verification script.");
}
if (packageJson.scripts?.["verify:performance-gates"] !== "node scripts/verify-performance-gates.mjs") {
  errors.push("package.json must keep the performance/telemetry gate verification script.");
}
if (packageJson.scripts?.["verify:security-gates"] !== "node scripts/verify-security-gates.mjs") {
  errors.push("package.json must keep the same-origin/rate-limit security gate verification script.");
}
if (packageJson.scripts?.["verify:kubernetes-manifests"] !== "node scripts/verify-kubernetes-manifests.mjs") {
  errors.push("package.json must keep the Kubernetes manifest verification script.");
}
if (packageJson.scripts?.["verify:auth-routes"] !== "node scripts/verify-auth-routes.mjs") {
  errors.push("package.json must keep the auth route smoke verification script.");
}
if (packageJson.scripts?.["verify:route-authorization"] !== "node scripts/verify-route-authorization.mjs") {
  errors.push("package.json must keep the route authorization verification script.");
}
if (packageJson.scripts?.["verify:signed-out-auth-ux"] !== "node scripts/verify-signed-out-auth-ux.mjs") {
  errors.push("package.json must keep the signed-out auth UX verification script.");
}
if (packageJson.scripts?.["verify:no-python-source"] !== "node scripts/verify-no-python-source.mjs") {
  errors.push("package.json must keep the no-Python source decommission verification script.");
}
if (packageJson.scripts?.["verify:auth-session"] !== "node scripts/verify-auth-session.mjs") {
  errors.push("package.json must keep the Rust JWT/JWKS auth session verification script.");
}
if (packageJson.scripts?.["verify:office-contract"] !== "node scripts/verify-office-contract.mjs") {
  errors.push("package.json must keep the Office product contract verification script.");
}
if (packageJson.scripts?.["verify:sensitive-data"] !== "node scripts/verify-sensitive-data.mjs") {
  errors.push("package.json must keep the sensitive data worktree verification script.");
}
if (packageJson.scripts?.["verify:sensitive-history"] !== "node scripts/verify-sensitive-data.mjs --history") {
  errors.push("package.json must keep the sensitive data history verification script.");
}
if (!packageJson.dependencies?.["lucide-react-native"] || !packageJson.dependencies?.["react-native-svg"]) {
  errors.push("package.json must use Lucide icons through lucide-react-native/react-native-svg.");
}
if (packageJson.overrides?.uuid !== "^11.1.1") {
  errors.push("package.json must keep the uuid ^11.1.1 override until Expo's xcode transitive dependency path is upstream-patched.");
}

requireText(githubWorkflowSource, "npm run verify:buck2-only", ".github/workflows/tests.yml must run Buck2-only cargo enforcement before platform UI verification.");
requireText(githubWorkflowSource, "npm run verify:no-python-source", ".github/workflows/tests.yml must run no-Python source verification before platform UI verification.");
requireText(githubWorkflowSource, "npm run verify:performance-gates", ".github/workflows/tests.yml must run performance/telemetry gates before platform UI verification.");
requireText(githubWorkflowSource, "npm run verify:security-gates", ".github/workflows/tests.yml must run same-origin/rate-limit security gates before auth route verification.");
requireText(githubWorkflowSource, "npm run verify:kubernetes-manifests", ".github/workflows/tests.yml must run Kubernetes manifest verification before auth route verification.");
requireText(githubWorkflowSource, "npm run verify:auth-session", ".github/workflows/tests.yml must run Rust JWT/JWKS auth-session verification before auth route verification.");
requireText(githubWorkflowSource, "npm run verify:office-contract", ".github/workflows/tests.yml must run Office product contract verification before platform UI verification.");
requireText(githubWorkflowSource, "buck2 build //crates/payroll-api:auth_session_validate", ".github/workflows/tests.yml must build the Rust auth session validator.");
requireText(githubWorkflowSource, "buck2 build '//crates/payroll-api:auth_session_validate[check]'", ".github/workflows/tests.yml must check the Rust auth session validator.");
requireText(githubWorkflowSource, "buck2 build '//crates/payroll-api:auth_session_validate[clippy.txt]'", ".github/workflows/tests.yml must run Buck2 clippy for the Rust auth session validator.");
requireText(githubWorkflowSource, "buck2 test //crates/payroll-api:auth_session_validate_test", ".github/workflows/tests.yml must test the Rust auth session validator.");
requireText(githubWorkflowSource, "buck2 build //crates/payroll-api:workflow_template_store", ".github/workflows/tests.yml must build the live workflow template store target.");
requireText(githubWorkflowSource, "buck2 build //crates/payroll-api:postgres_migrate", ".github/workflows/tests.yml must build the live PostgreSQL migration target.");
requireText(githubWorkflowSource, "buck2 build //crates/payroll-api:cloud_native_audit_worker", ".github/workflows/tests.yml must build the cloud-native audit worker target.");
requireText(githubWorkflowSource, "buck2 build '//crates/payroll-api:workflow_template_store[check]'", ".github/workflows/tests.yml must check the live workflow template store target.");
requireText(githubWorkflowSource, "buck2 build '//crates/payroll-api:postgres_migrate[check]'", ".github/workflows/tests.yml must check the live PostgreSQL migration target.");
requireText(githubWorkflowSource, "buck2 build '//crates/payroll-api:cloud_native_audit_worker[check]'", ".github/workflows/tests.yml must check the cloud-native audit worker target.");
requireText(githubWorkflowSource, "buck2 build '//crates/payroll-api:workflow_template_store[clippy.txt]'", ".github/workflows/tests.yml must run Buck2 clippy for the workflow template store target.");
requireText(githubWorkflowSource, "buck2 build '//crates/payroll-api:postgres_migrate[clippy.txt]'", ".github/workflows/tests.yml must run Buck2 clippy for the PostgreSQL migration target.");
requireText(githubWorkflowSource, "buck2 build '//crates/payroll-api:cloud_native_audit_worker[clippy.txt]'", ".github/workflows/tests.yml must run Buck2 clippy for the cloud-native audit worker target.");
requireText(githubWorkflowSource, "buck2 test //crates/payroll-api:workflow_template_store_test", ".github/workflows/tests.yml must test the workflow template store target.");
requireText(githubWorkflowSource, "buck2 test //crates/payroll-api:postgres_migrate_test", ".github/workflows/tests.yml must test the PostgreSQL migration target.");
requireText(githubWorkflowSource, "buck2 test //crates/payroll-api:cloud_native_audit_worker_test", ".github/workflows/tests.yml must test the cloud-native audit worker target.");
requireText(buck2OnlyScriptSource, "Buck2-only verification passed.", "verify-buck2-only.mjs must emit a stable pass message for CI evidence.");
requireText(buck2OnlyScriptSource, "retiredCargoSubcommands", "verify-buck2-only.mjs must maintain the retired cargo subcommand list.");
requireText(buck2OnlyScriptSource, "cargo \" + \"test //crates/payroll-api:payroll_api_test", "verify-buck2-only.mjs must prove the retired test subcommand is blocked by the PreToolUse guard.");
requireText(buck2OnlyScriptSource, "cargo install --locked --git", "verify-buck2-only.mjs must prove Reindeer cargo install remains allowed.");
requireText(performanceGateScriptSource, "Performance gate verification passed.", "verify-performance-gates.mjs must emit a stable pass message for CI evidence.");
requireText(performanceGateScriptSource, "server-timing", "verify-performance-gates.mjs must assert Server-Timing latency evidence.");
requireText(performanceGateScriptSource, "routeLatencyBudgetMs", "verify-performance-gates.mjs must enforce a route latency budget.");
requireText(performanceGateScriptSource, "appJsMaxBytes", "verify-performance-gates.mjs must enforce a shell JavaScript size budget.");
requireText(performanceGateScriptSource, "maxExtractedXmlBytes", "verify-performance-gates.mjs must guard large archive spreadsheet extraction constraints.");
requireText(securityGateScriptSource, "Security gate verification passed.", "verify-security-gates.mjs must emit a stable pass message for CI evidence.");
requireText(securityGateScriptSource, "csrf_origin_rejected", "verify-security-gates.mjs must assert cross-origin mutation rejection.");
requireText(securityGateScriptSource, "csrf_fetch_site_rejected", "verify-security-gates.mjs must assert Fetch Metadata mutation rejection.");
requireText(securityGateScriptSource, "rate_limit_exceeded", "verify-security-gates.mjs must assert route rate-limit rejection.");
requireText(securityGateScriptSource, "request_path_invalid", "verify-security-gates.mjs must assert malformed percent-encoded paths fail closed.");
requireText(securityGateScriptSource, "x-ratelimit-limit", "verify-security-gates.mjs must assert rate limit evidence headers.");
requireText(kubernetesManifestScriptSource, "Kubernetes manifest verification passed.", "verify-kubernetes-manifests.mjs must emit a stable pass message for CI evidence.");
requireText(kubernetesManifestScriptSource, "pod-security.kubernetes.io/enforce: restricted", "verify-kubernetes-manifests.mjs must guard restricted Pod Security Admission.");
requireText(kubernetesManifestScriptSource, "bitween-default-deny", "verify-kubernetes-manifests.mjs must guard default-deny NetworkPolicy.");
requireText(kubernetesManifestScriptSource, "OpenSLO", "verify-kubernetes-manifests.mjs must guard SLO manifests.");
requireText(kubernetesManifestScriptSource, "rustfs/rustfs:1.0.0-beta.7", "verify-kubernetes-manifests.mjs must guard the RustFS release pin.");
requireText(kubernetesManifestScriptSource, "BITWEEN_POSTGRES_DSN", "verify-kubernetes-manifests.mjs must guard the Rust PostgreSQL DSN env contract.");
requireText(kubernetesManifestScriptSource, "BITWEEN_POSTGRES_TENANT_ID", "verify-kubernetes-manifests.mjs must guard the Rust PostgreSQL tenant scope env contract.");
requireText(kubernetesManifestScriptSource, "BITWEEN_RUSTFS_BUCKET: bitween-archive-originals", "verify-kubernetes-manifests.mjs must guard the RustFS archive bucket env contract.");
requireText(kubernetesManifestScriptSource, "worker-cronjobs.yaml", "verify-kubernetes-manifests.mjs must guard worker CronJobs.");
requireText(kubernetesManifestScriptSource, "cloud_native_audit_worker", "verify-kubernetes-manifests.mjs must guard the cloud-native audit worker binary wiring.");
requireText(kubernetesManifestScriptSource, "ServiceMonitor", "verify-kubernetes-manifests.mjs must guard observability ServiceMonitors.");
requireText(kubernetesManifestScriptSource, "ResourceQuota", "verify-kubernetes-manifests.mjs must guard tenant ResourceQuota.");
requireText(kubernetesManifestScriptSource, "BITWEEN_AUDIT_EVENT_STREAM: postgres+otel", "verify-kubernetes-manifests.mjs must guard audit event stream wiring.");
requireText(authSessionScriptSource, "Auth session verification passed.", "verify-auth-session.mjs must emit a stable pass message for CI evidence.");
requireText(authSessionScriptSource, "auth_session_validate", "verify-auth-session.mjs must exercise the Rust JWT/JWKS validator.");
requireText(authSessionScriptSource, "jwt_signature_invalid", "verify-auth-session.mjs must assert invalid JWT signature fail-closed behavior.");
requireText(authSessionScriptSource, "BITWEEN_AUTH_OIDC_CONFIGURATION_JSON", "verify-auth-session.mjs must exercise server-side OIDC discovery metadata validation.");
requireText(authSessionScriptSource, "BITWEEN_AUTH_EXPECTED_JWKS_URI", "verify-auth-session.mjs must pin the expected JWKS URI when discovery metadata is configured.");
requireText(authSessionScriptSource, "oidc_issuer_mismatch", "verify-auth-session.mjs must prove OIDC discovery issuer mismatch fails closed.");
requireText(authSessionScriptSource, "BITWEEN_AUTH_SESSION_SECURITY_MODE", "verify-auth-session.mjs must exercise the PostgreSQL auth-session security mode.");
requireText(authSessionScriptSource, "auth_session_security_store_required", "verify-auth-session.mjs must prove PostgreSQL security mode fails closed without a DSN.");
requireText(authSessionScriptSource, "/api/platform/v1/view-model", "verify-auth-session.mjs must prove the preview shell consumes Rust-verified session facts.");
requireText(officeContractScriptSource, "Office contract verification passed.", "verify-office-contract.mjs must emit a stable pass message for CI evidence.");
requireText(officeProductContractSource, "Status: future product, not exposed in navigation until live-wired", "Office product contract must keep Office hidden until live-wired.");
requireText(officeProductContractSource, "Rust service crates", "Office product contract must keep the Office backend in Rust.");
requireText(officeProductContractSource, "PostgreSQL metadata", "Office product contract must keep Office relational metadata in PostgreSQL.");
requireText(officeProductContractSource, "RustFS blobs", "Office product contract must keep Office binary/object storage in RustFS.");
requireText(officeProductContractSource, "verification gates before visibility", "Office product contract must require verification gates before visible Office UI.");
requireText(codexCargoGuardSource, "decision: \"block\"", ".codex/hooks/buck2-cargo-guard.js must emit a block decision for retired cargo commands.");
requireText(codexCargoGuardSource, "hookEventName: \"PreToolUse\"", ".codex/hooks/buck2-cargo-guard.js must run as a PreToolUse permission gate.");
requireText(codexCargoGuardSource, "permissionDecision: \"deny\"", ".codex/hooks/buck2-cargo-guard.js must deny retired cargo commands.");
requireText(codexCargoGuardSource, "buck2 build //...", ".codex/hooks/buck2-cargo-guard.js must point agents to Buck2 replacements.");
requireText(codexCargoGuardSource, "'<target>[check]'", ".codex/hooks/buck2-cargo-guard.js must point type-checking to supported target-specific Buck2 check targets.");
requireText(codexCargoGuardSource, "'<target>[clippy.txt]'", ".codex/hooks/buck2-cargo-guard.js must point linting to supported target-specific Buck2 clippy targets.");
rejectText(codexCargoGuardSource, "buck2 build //...[check]", ".codex/hooks/buck2-cargo-guard.js must not recommend unsupported recursive Buck2 check patterns.");
rejectText(codexCargoGuardSource, "buck2 build //...[clippy]", ".codex/hooks/buck2-cargo-guard.js must not recommend unsupported recursive Buck2 clippy patterns.");
requireText(buck2OnlyScriptSource, "scanUnsupportedRecursiveBuck2Usage", "verify-buck2-only.mjs must scan repo-owned scripts/docs for unsupported recursive Buck2 provider patterns.");
requireText(buck2OnlyScriptSource, "unsupportedRecursiveBuck2Pattern", "verify-buck2-only.mjs must carry an explicit unsupported recursive Buck2 pattern ratchet.");

requireText(previewServerSource, "no-store, no-cache, must-revalidate, max-age=0", "preview/server.js must disable browser caching for local UI review.");
requireText(previewServerSource, "securityHeaders", "preview/server.js must centralize HTTP security headers for every live preview response.");
requireText(previewServerSource, "content-security-policy", "preview/server.js must send a content security policy.");
requireText(previewServerSource, "frame-ancestors 'none'", "preview/server.js CSP must block embedding.");
requireText(previewServerSource, "x-frame-options", "preview/server.js must include a legacy frame-blocking header.");
requireText(previewServerSource, "x-content-type-options", "preview/server.js must block MIME sniffing.");
requireText(previewServerSource, "referrer-policy", "preview/server.js must avoid leaking referrer data.");
requireText(previewServerSource, "permissions-policy", "preview/server.js must deny unused browser permissions.");
requireText(previewServerSource, "cross-origin-opener-policy", "preview/server.js must isolate the live preview browsing context.");
requireText(previewServerSource, "eventStreamHeaders", "preview/server.js must apply security headers to live reload event streams.");
requireText(previewServerSource, "styles.css?v=", "preview/server.js must version styles.css responses.");
requireText(previewServerSource, "app.js?v=", "preview/server.js must version app.js responses.");
requireText(previewServerSource, "decodeRequestPath", "preview/server.js must safely handle malformed URL paths before route dispatch.");
requireText(previewServerSource, "request_path_invalid", "preview/server.js must return a stable malformed-path error instead of crashing.");
requireText(previewServerSource, '"/api/platform/v1/view-model"', "preview/server.js must expose the Rust platform view-model endpoint.");
requireText(previewServerSource, '"/api/auth/v1/signin"', "preview/server.js must expose a real configured sign-in route endpoint.");
requireText(previewServerSource, '"/api/auth/v1/signup"', "preview/server.js must expose a real configured sign-up/access route endpoint.");
requireText(previewServerSource, '"/api/auth/v1/signout"', "preview/server.js must expose a real configured sign-out route endpoint.");
requireText(previewServerSource, '"/api/onboarding/v1/start"', "preview/server.js must expose a real configured onboarding route endpoint.");
requireText(previewServerSource, '"/api/auth/v1/routes"', "preview/server.js must expose auth route status so signed-out users are not sent into dead-end buttons.");
requireText(previewServerSource, '"/api/workflow/v1/templates"', "preview/server.js must expose a live workflow template route for persisted workflow editing.");
requireText(previewServerSource, '"add-step"', "preview/server.js must expose persisted workflow step creation.");
requireText(previewServerSource, '"delete-step"', "preview/server.js must expose persisted workflow step deletion.");
requireText(previewServerSource, '"execute-step"', "preview/server.js must expose persisted workflow step execution.");
requireText(previewServerSource, '"rollback-template"', "preview/server.js must expose persisted workflow version rollback.");
requireText(previewServerSource, '"preflight-template"', "preview/server.js must expose Rust workflow preflight planning.");
requireText(previewServerSource, '"validate-step-update"', "preview/server.js must expose Rust workflow dry-run edit validation.");
requireText(previewServerSource, "/validations", "preview/server.js must route workflow edit validation before graph mutation.");
requireText(previewServerSource, "bitween.auth-routes.v1", "preview/server.js must return a stable auth route status schema.");
requireText(previewServerSource, "BITWEEN_AUTH_SIGNIN_URL", "preview/server.js must fail closed unless a sign-in route is configured.");
requireText(previewServerSource, "BITWEEN_AUTH_SIGNUP_URL", "preview/server.js must fail closed unless a sign-up/access route is configured.");
requireText(previewServerSource, "BITWEEN_AUTH_SIGNOUT_URL", "preview/server.js must fail closed unless a sign-out route is configured.");
requireText(previewServerSource, "BITWEEN_ONBOARDING_START_URL", "preview/server.js must fail closed unless an onboarding route is configured.");
requireText(previewServerSource, "auth_route_unconfigured", "preview/server.js auth actions must fail closed instead of creating browser-local sessions.");
requireText(previewServerSource, "requireSameOriginMutation", "preview/server.js must reject cross-origin mutable requests before any storage side effect.");
requireText(previewServerSource, "csrf_origin_rejected", "preview/server.js must return a stable CSRF origin rejection code.");
requireText(previewServerSource, "csrf_fetch_site_rejected", "preview/server.js must return a stable Fetch Metadata rejection code.");
requireText(previewServerSource, "enforceRateLimit", "preview/server.js must rate-limit auth and mutable API routes before body parsing/storage side effects.");
requireText(previewServerSource, "rate_limit_exceeded", "preview/server.js must return a stable rate-limit error code.");
requireText(previewServerSource, "x-ratelimit-limit", "preview/server.js must emit rate-limit evidence headers.");
requireText(previewServerSource, '"//crates/payroll-api:auth_session_validate"', "preview/server.js must call the Rust JWT/JWKS session verifier when session token configuration is present.");
requireText(previewServerSource, "authSessionEnvForRustTargets", "preview/server.js must derive Rust target session facts from the verifier instead of browser state.");
requireText(previewServerSource, "deniedAuthSessionEnv", "preview/server.js must force unauthenticated Rust target env facts when JWT verification fails.");
requireText(previewServerSource, '"//crates/payroll-api:authz_decision"', "preview/server.js must call the Rust authorization decision target before live reads/writes.");
requireText(previewServerSource, "requireAuthorizedOperation", "preview/server.js must gate sensitive live routes through Rust authorization.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"hr_employee_read\"\)[\s\S]*?runHrEmployeeStore\(\[\"list\"\]/, "preview/server.js must authorize HR employee reads before storage access.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"hr_employee_write\"\)[\s\S]*?runHrEmployeeStore\(\[\"add\"\]/, "preview/server.js must authorize HR employee creation before storage writes.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"archive_read\"\)[\s\S]*?runArchiveIntakeStore\(\[\"list\"\]/, "preview/server.js must authorize 자료함 reads before storage access.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"archive_upload\"\)[\s\S]*?storeArchiveObjectInRustFs/, "preview/server.js must authorize 자료함 upload before RustFS object storage writes.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"archive_review\"\)[\s\S]*?runArchiveIntakeStore\(\[\"resolve\"/, "preview/server.js must authorize 자료함 issue review before resolving human-review work.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"archive_admit\"\)[\s\S]*?runArchiveIntakeStore\(\[\"admit\"/, "preview/server.js must authorize 자료함 canonical admission before writing reviewed rows into business tables.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"archive_rollback\"\)[\s\S]*?runArchiveIntakeStore\(\[\"rollback\"/, "preview/server.js must authorize 자료함 recovery rollback before reversing admitted business rows.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"archive_sync\"\)[\s\S]*?syncArchiveSourceVersions/, "preview/server.js must authorize source-file sync before generating derived RustFS workbook versions.");
requirePattern(previewServerSource, /syncArchiveSourceVersions[\s\S]*?runArchiveIntakeStore\(\[\"source-sync-plan\"[\s\S]*?putRustFsObject[\s\S]*?runArchiveIntakeStore\(\[\"source-sync-complete\"/, "preview/server.js must live-wire source sync through Rust plan, RustFS PUT, and Rust completion.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"read_workspace\"\)[\s\S]*?runUserPreferenceStore\(\[\"get\"\]/, "preview/server.js must authorize settings preference reads before storage access.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"user_preference_update\"\)[\s\S]*?runUserPreferenceStore\(\[\"update\"\]/, "preview/server.js must authorize settings updates before preference writes.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"workflow_template_read\"\)[\s\S]*?runWorkflowTemplateStore\(\[\"get\"\]/, "preview/server.js must authorize workflow template reads before store access.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"workflow_template_write\"\)[\s\S]*?runWorkflowTemplateStore\(\s*\[[\s\S]*?\"update-step\"/, "preview/server.js must authorize workflow template edits before persisted updates.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"workflow_template_write\"\)[\s\S]*?runWorkflowTemplateStore\(\s*\[[\s\S]*?\"add-step\"/, "preview/server.js must authorize workflow step creation before persisted updates.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"workflow_template_write\"\)[\s\S]*?runWorkflowTemplateStore\(\s*\[[\s\S]*?\"delete-step\"/, "preview/server.js must authorize workflow step deletion before persisted updates.");
requirePattern(previewServerSource, /requireAuthorizedOperation\(\"workflow_step_execute\"\)[\s\S]*?runWorkflowTemplateStore\(\s*\[[\s\S]*?\"execute-step\"/, "preview/server.js must authorize workflow step execution before persisted runtime mutation.");
requirePattern(previewServerSource, /requireAuthorizedOperation\("workflow_template_write"\)[\s\S]*?runWorkflowTemplateStore\(\s*\[[\s\S]*?"rollback-template"/, "preview/server.js must authorize workflow version rollback before persisted graph mutation.");
requirePattern(previewServerSource, /requireAuthorizedOperation\("workflow_template_read"\)[\s\S]*?runWorkflowTemplateStore\(\s*\[[\s\S]*?"preflight-template"/, "preview/server.js must authorize workflow preflight before exposing execution planning.");
requirePattern(previewServerSource, /requireAuthorizedOperation\("workflow_template_write"\)[\s\S]*?runWorkflowTemplateStore\(\s*\[[\s\S]*?"validate-step-update"/, "preview/server.js must authorize workflow dry-run validation before returning edit analysis.");
requireText(previewServerSource, "authorization_required", "preview/server.js must return a controlled authorization_required error when Rust denies an action.");
requireText(authRouteScriptSource, "/api/auth/v1/routes", "verify-auth-routes.mjs must smoke test the auth route status contract.");
requireText(authRouteScriptSource, "/api/auth/v1/signin", "verify-auth-routes.mjs must smoke test the sign-in route.");
requireText(authRouteScriptSource, "/api/auth/v1/signup", "verify-auth-routes.mjs must smoke test the sign-up/access route.");
requireText(authRouteScriptSource, "/api/auth/v1/signout", "verify-auth-routes.mjs must smoke test the sign-out route.");
requireText(authRouteScriptSource, "/api/onboarding/v1/start", "verify-auth-routes.mjs must smoke test the onboarding route.");
requireText(authRouteScriptSource, "auth_route_unconfigured", "verify-auth-routes.mjs must assert missing auth routes fail closed.");
requireText(authRouteScriptSource, "verifyInsecureRoutesFailClosed", "verify-auth-routes.mjs must assert non-HTTPS identity routes fail closed.");
requireText(authRouteScriptSource, "verifyDisallowedRouteOriginFailsClosed", "verify-auth-routes.mjs must assert identity route origins outside the expected issuer fail closed.");
requireText(previewServerSource, "BITWEEN_AUTH_ALLOWED_ORIGINS", "preview/server.js must support explicit auth route origin allow-lists.");
requireText(previewServerSource, "BITWEEN_ONBOARDING_ALLOWED_ORIGINS", "preview/server.js must support explicit onboarding route origin allow-lists.");
requireText(routeAuthorizationScriptSource, "authorization_required", "verify-route-authorization.mjs must assert sensitive routes fail closed when Rust authz denies.");
requireText(routeAuthorizationScriptSource, "assertNoLocalStoreSideEffects", "verify-route-authorization.mjs must prove denied writes do not create local-review store side effects.");
requireText(routeAuthorizationScriptSource, "withRustFsMock", "verify-route-authorization.mjs must prove authorized 자료함 uploads reach a live RustFS-compatible PUT path.");
requireText(routeAuthorizationScriptSource, "BITWEEN_RUSTFS_BUCKET_ARCHIVE", "verify-route-authorization.mjs must exercise the Kubernetes RustFS archive bucket env contract.");
requireText(routeAuthorizationScriptSource, "PATCH", "verify-route-authorization.mjs must cover HR employee updates.");
requireText(routeAuthorizationScriptSource, "DELETE", "verify-route-authorization.mjs must cover HR employee deletion.");
requireText(routeAuthorizationScriptSource, "/api/hr/v1/employees", "verify-route-authorization.mjs must cover HR employee reads/writes.");
requireText(routeAuthorizationScriptSource, "/api/archive/v1/intake", "verify-route-authorization.mjs must cover 자료함 reads/intake before RustFS side effects.");
requireText(routeAuthorizationScriptSource, "verifyAuthorizedArchiveFieldMappingReviewSucceeds", "verify-route-authorization.mjs must cover authorized 자료함 field-mapping issue review.");
requireText(routeAuthorizationScriptSource, "/api/archive/v1/intake/intake-1/rollbacks", "verify-route-authorization.mjs must cover 자료함 rollback authorization before business-row recovery.");
requireText(routeAuthorizationScriptSource, "/api/workflow/v1/templates/payroll-close/rollbacks", "verify-route-authorization.mjs must cover 업무 관리 graph rollback authorization before persisted graph recovery.");
requireText(routeAuthorizationScriptSource, "/api/workflow/v1/templates/payroll-close/preflights", "verify-route-authorization.mjs must cover 업무 관리 preflight authorization before execution planning.");
requireText(routeAuthorizationScriptSource, "/api/settings/v1/preferences", "verify-route-authorization.mjs must cover settings reads/writes.");
requireText(routeAuthorizationScriptSource, "BITWEEN_SESSION_AUTHZ_POLICY_ID", "verify-route-authorization.mjs must use live Rust ABAC/RBAC/PBAC env facts for allowed actions.");
requireText(signedOutAuthUxScriptSource, "회사 계정 연결 필요", "verify-signed-out-auth-ux.mjs must assert the concise Korean setup state renders.");
requireText(signedOutAuthUxScriptSource, "data-auth-action=\\\"signin\\\"", "verify-signed-out-auth-ux.mjs must assert configured sign-in remains clickable.");
requireText(signedOutAuthUxScriptSource, "회사 인증 주소가 설정되지 않았습니다", "verify-signed-out-auth-ux.mjs must guard against the dead-end missing-address copy.");
requireText(signedOutAuthUxScriptSource, "Signed-out auth UX verification passed.", "verify-signed-out-auth-ux.mjs must emit a stable pass message.");
requireText(previewServerSource, '"buck2"', "preview/server.js must execute the Buck2 Rust target, not a script stub.");
requireText(previewServerSource, '"//crates/payroll-api:platform_live_view"', "preview/server.js must call the bitween-payroll-api Buck2 live view target.");
requireText(previewServerSource, '"//crates/payroll-api:hr_employee_store"', "preview/server.js must call the Rust/Buck2 HR employee store target for HR changes.");
requireText(previewServerSource, '"//crates/payroll-api:archive_intake_store"', "preview/server.js must call the Rust/Buck2 archive intake store target for 자료함 changes.");
requireText(previewServerSource, '"/api/hr/v1/employees"', "preview/server.js must expose live HR employee endpoints.");
requireText(previewServerSource, '"/api/archive/v1/intake"', "preview/server.js must expose live 자료함 intake endpoints.");
requireText(previewServerSource, "/issues", "preview/server.js must expose an archive issue-review endpoint instead of passive review labels only.");
requireText(previewServerSource, '"/api/settings/v1/preferences"', "preview/server.js must expose live settings preference endpoints.");
requireText(previewServerSource, "BITWEEN_RUSTFS_ENDPOINT", "preview/server.js must fail closed unless RustFS object storage is configured.");
requireText(previewServerSource, "configuredRustFsBucket", "preview/server.js must centralize RustFS archive bucket configuration.");
requireText(previewServerSource, "BITWEEN_RUSTFS_BUCKET_ARCHIVE", "preview/server.js must accept the semantic RustFS archive bucket env var used by Kubernetes.");
requireText(previewServerSource, "rustfs_archive_bucket_invalid", "preview/server.js must reject invalid RustFS bucket names before object writes.");
requireText(previewServerSource, "requireRelationalStoreAvailable", "preview/server.js must fail closed when PostgreSQL-backed relational storage is not configured.");
requireText(previewServerSource, "BITWEEN_ALLOW_LOCAL_REVIEW_STORE", "preview/server.js may only use local file persistence behind an explicit hermetic review flag.");
requireText(previewServerSource, "storeArchiveObjectInRustFs", "preview/server.js must store 자료함 originals in RustFS before classification.");
requireText(previewServerSource, "putRustFsObject", "preview/server.js must use a live S3-compatible RustFS PUT path, not local fake blob storage.");
requireText(previewServerSource, '"//crates/payroll-api:user_preference_store"', "preview/server.js must call the Rust/Buck2 user preference store target for settings changes.");
requireText(previewServerSource, "postgresDsnConfigured", "preview/server.js must explicitly distinguish configured PostgreSQL DSN from hermetic local-review storage.");
rejectText(previewServerSource, "postgres_repository_adapter_required", "preview/server.js must not reject a configured PostgreSQL DSN after the Rust workflow repository adapter is linked.");
requireText(previewServerSource, "extractXlsxSample", "preview/server.js must attempt spreadsheet extraction for Excel intake.");
requireText(previewServerSource, "maxExtractedXmlBytes", "preview/server.js must cap spreadsheet XML extraction to reduce archive intake zip-bomb risk.");
requireText(previewServerSource, "archiveIntakeInputsForFile", "preview/server.js must fan out archive uploads into extracted review records when safe.");
requireText(previewServerSource, "extractZipIntakeSamples", "preview/server.js must safely extract tabular files from ZIP archive uploads.");
requireText(previewServerSource, "isSafeZipEntryName", "preview/server.js must reject unsafe ZIP member names before treating them as review items.");
requireText(previewServerSource, "maxZipTotalExtractedBytes", "preview/server.js must bound total ZIP extraction to reduce zip-bomb risk.");
requireText(archiveIntakeStoriesScriptSource, "verifyZipBundleExtractsSafeInnerFiles", "archive intake story verifier must exercise safe ZIP uploads with inner tabular files.");
requireText(archiveIntakeStoriesScriptSource, "verifyArchiveUiActualUsageStories", "archive intake verifier must exercise actual UI usage stories for normal, edge, and malicious uploads.");
requireText(previewAppSource, "applyArchiveMutationResponse", "preview/app.js must preserve the archive review queue when an upload or review mutation fails.");
requireText(sourceCatalogSource, "압축 파일 내부 표 파일", "Korean archive intake UX copy must explain that compressed inner tabular files are split for review.");
requireText(previewServerSource, "content_sha256", "preview/server.js must pass a checksum into the Rust archive intake store.");
rejectText(previewServerSource.toLowerCase(), "python", "preview/server.js must not invoke Python.");
requireText(noPythonSourceScriptSource, "Python source/stub remains", "verify-no-python-source.mjs must reject repo-owned Python source/stub files.");
requireText(noPythonSourceScriptSource, "Python dependency/tooling manifest remains", "verify-no-python-source.mjs must reject Python dependency/tooling manifests.");
requireText(noPythonSourceScriptSource, "setup.cfg", "verify-no-python-source.mjs must reject Python packaging config files.");
requireText(noPythonSourceScriptSource, "tox.ini", "verify-no-python-source.mjs must reject Python test/tooling config files.");
requireText(noPythonSourceScriptSource, "pytest.ini", "verify-no-python-source.mjs must reject Python test config files.");
requireText(noPythonSourceScriptSource, "uv.lock", "verify-no-python-source.mjs must reject Python package manager lockfiles.");
requireText(noPythonSourceScriptSource, "pdm.lock", "verify-no-python-source.mjs must reject Python package manager lockfiles.");
requireText(noPythonSourceScriptSource, "pyrightconfig.json", "verify-no-python-source.mjs must reject Python type-checker config files.");
requireText(noPythonSourceScriptSource, "workflowSources", "verify-no-python-source.mjs must scan every GitHub Actions workflow for Python setup/test commands.");
requireText(noPythonSourceScriptSource, "setup-python", "verify-no-python-source.mjs must reject CI Python setup after decommission.");
requireText(noPythonSourceScriptSource, "python(?:3", "verify-no-python-source.mjs must reject python3 workflow command variants.");
requireText(noPythonSourceScriptSource, "\\bpy\\s+-m", "verify-no-python-source.mjs must reject py -m workflow command variants.");
requireText(noPythonSourceScriptSource, "pip(?:3", "verify-no-python-source.mjs must reject pip3 workflow command variants.");
requireText(noPythonSourceScriptSource, "\\bpip(?:3(?:\\.\\d+)?)?\\s+install", "verify-no-python-source.mjs must reject active docs that install Python packages.");
requireText(noPythonSourceScriptSource, "\\b(?:python(?:3(?:\\.\\d+)?)?|py)\\s+-(?:m|c)", "verify-no-python-source.mjs must reject active docs that run Python module/eval commands.");
requireText(noPythonSourceScriptSource, "\\b(?:pytest|unittest)\\b", "verify-no-python-source.mjs must reject active docs that run Python test runners.");
requireText(noPythonSourceScriptSource, "\\brequirements[^/\\s`'\"]*\\.txt\\b", "verify-no-python-source.mjs must reject active docs that reference removed Python manifests.");
requireText(noPythonSourceScriptSource, "\\b[\\w./-]+\\.py\\b", "verify-no-python-source.mjs must reject any active docs that reference removed Python source/test paths.");
requireText(noPythonSourceScriptSource, "Existing Python remains compatibility/characterization inventory", "verify-no-python-source.mjs must reject stale Python compatibility inventory docs.");
requireText(noPythonSourceScriptSource, "Repo-owned Python source count: 0", "verify-no-python-source.mjs must require zero-source decommission evidence.");
requireText(noPythonSourceScriptSource, "activeDocCommandPatterns", "verify-no-python-source.mjs must reject stale active Python/Buck2 doc commands.");
requireText(noPythonSourceScriptSource, "staleDocNarrativePatterns", "verify-no-python-source.mjs must reject docs that describe repo-owned Python as an active bridge.");
requireText(noPythonSourceScriptSource, "Python may still", "verify-no-python-source.mjs must reject stale docs that keep Python as an active bridge.");
requireText(noPythonSourceScriptSource, "Python still owns", "verify-no-python-source.mjs must reject stale docs that keep Python as an active owner.");
requireText(noPythonSourceScriptSource, "Python contract tests?", "verify-no-python-source.mjs must reject stale docs that require Python contract tests.");
requireText(noPythonSourceScriptSource, "DESIGN.md", "verify-no-python-source.mjs must scan top-level design authority docs.");
requireText(noPythonSourceScriptSource, "apps/bitween-platform-ui/README.md", "verify-no-python-source.mjs must scan app-level active docs.");
requireText(noPythonSourceScriptSource, "Python responsible", "verify-no-python-source.mjs must reject docs that keep Python responsible for behavior.");
requireText(noPythonSourceScriptSource, "buck2 build\\s+['\"]?\\/\\/\\.\\.\\.\\[(?:check|clippy)\\]", "verify-no-python-source.mjs must reject unsupported recursive Buck2 doc commands.");
requireText(noPythonSourceScriptSource, "buck2 build \\/\\/\\.\\.\\.\\s+--filter\\s+lint", "verify-no-python-source.mjs must reject retired Buck2 lint-filter doc commands.");
rejectText(previewServerSource.toLowerCase(), "demo-only", "preview/server.js must not label the live path demo-only.");
rejectText(previewServerSource, retiredObjectStoreName, "preview/server.js must use RustFS naming and configuration, not the retired object-store candidate.");
rejectText(previewServerSource, 'process.env.BITWEEN_RUSTFS_BUCKET || "bitween-archive"', "preview/server.js must not silently default RustFS writes to an implicit bucket.");

requireText(previewAppSource, 'fetch("/api/platform/v1/view-model")', "preview/app.js must fetch the Rust platform view-model endpoint.");
requireText(previewAppSource, 'fetch("/api/hr/v1/employees")', "preview/app.js must fetch the live HR employee endpoint.");
requireText(previewAppSource, "state.liveView", "preview/app.js must render from the live Rust payload state.");
requireText(previewAppSource, "syncSessionFromLive", "preview/app.js must derive auth state from the Rust live session payload.");
requireText(previewAppSource, "state.liveView?.session?.authenticated", "preview/app.js must use Rust-owned session.authenticated, not a local auth stub.");
requireText(previewAppSource, "startAuthFlow", "preview/app.js must route sign-in/sign-up/onboarding/sign-out through configured live endpoints.");
requireText(previewAppSource, 'fetch("/api/auth/v1/routes")', "preview/app.js must preflight auth route availability instead of showing an unconfigured-address dead end.");
requireText(previewAppSource, "authRouteConfigured", "preview/app.js must disable unavailable auth actions before the user clicks them.");
requireText(previewAppSource, '"/api/auth/v1/signin"', "preview/app.js must start sign-in through the live auth endpoint.");
requireText(previewAppSource, '"/api/auth/v1/signup"', "preview/app.js must start sign-up/access through the live auth endpoint.");
requireText(previewAppSource, '"/api/auth/v1/signout"', "preview/app.js must start sign-out through the live auth endpoint.");
requireText(previewAppSource, '"/api/onboarding/v1/start"', "preview/app.js must start onboarding through the live onboarding endpoint.");
requireText(previewAppSource, "payrollWorkstream", "preview/app.js must render the role workflow from the Rust workstream payload.");
requireText(previewAppSource, "homeWorkBuckets", "preview/app.js must render the operator cockpit buckets instead of readiness walls.");
requireText(previewAppSource, "schedule:", "preview/app.js Home must include a schedule bucket for upcoming work.");
requireText(previewAppSource, "prep:", "preview/app.js Home must include a preparation bucket for upcoming payroll/archive work.");
requireText(previewAppSource, "workflowCanvas", "preview/app.js must render the corporate workflow canvas.");
requireText(previewAppSource, "workflowMiniMap", "preview/app.js must render a data-driven workflow overview map.");
requireText(previewAppSource, "workflowBuilderLayout", "preview/app.js must render a mature workflow builder layout with palette, canvas, and inspector.");
requireText(previewAppSource, "workflowPalette", "preview/app.js must expose a node palette for persisted workflow step creation.");
requireText(previewAppSource, "data-workflow-palette-add", "preview/app.js must add palette steps through the live workflow route.");
requireText(previewAppSource, "data-workflow-auto-layout", "preview/app.js must expose persisted auto-arrange controls for workflow maps.");
requireText(previewAppSource, "autoLayoutWorkflow", "preview/app.js must persist automatic workflow layout changes.");
requireText(previewAppSource, "connectWorkflowSteps", "preview/app.js must support click-to-connect persisted workflow wiring.");
requireText(previewAppSource, "disconnectWorkflowSteps", "preview/app.js must support persisted workflow rewire/removal.");
requireText(previewAppSource, "data-workflow-connect-from", "preview/app.js must expose source handles for persisted workflow connections.");
requireText(previewAppSource, "data-workflow-connect-to", "preview/app.js must expose target handles for persisted workflow connections.");
requireText(previewAppSource, "workflow-node-handle", "preview/app.js must render visible connection handles, not only form checkboxes.");
requireText(previewAppSource, "workflowEdgeControls", "preview/app.js must show and remove persisted outgoing workflow connections.");
requireText(previewAppSource, "workflowCanvasLines(nodes, edges)", "preview/app.js must render workflow connectors from live node/edge data, not a decorative path.");
rejectText(previewAppSource, "nodes.slice(0, -1).map", "preview/app.js must not fabricate fallback workflow edges when the persisted graph has no wiring.");
requireText(previewAppSource, "data-workflow-editor", "preview/app.js must expose a real persisted workflow editor form.");
requireText(previewAppSource, "mutateWorkflowStep(", "preview/app.js must persist workflow editor changes through the live workflow endpoint.");
requireText(previewAppSource, "data-workflow-add-step", "preview/app.js must expose a persisted workflow step creation form.");
requireText(previewAppSource, "addWorkflowStep(", "preview/app.js must persist workflow step creation through the live workflow endpoint.");
requireText(previewAppSource, "data-workflow-delete-step", "preview/app.js must expose persisted workflow step deletion.");
requireText(previewAppSource, "deleteWorkflowStep(", "preview/app.js must persist workflow step deletion through the live workflow endpoint.");
requireText(previewAppSource, "data-workflow-execute-step", "preview/app.js must expose real workflow action execution controls.");
requireText(previewAppSource, "executeWorkflowStep(", "preview/app.js must execute workflow actions through the live workflow endpoint.");
requireText(previewAppSource, "scope_tenant", "preview/app.js must pass business scope into workflow execution, not just toggle a visual status.");
requireText(previewAppSource, "workflowRuntimePanel", "preview/app.js must surface executed workflow action evidence to the operator.");
requireText(previewAppSource, "workflowDataRecordsForNode", "preview/app.js must surface persisted workflow data-record updates, not just event logs.");
requireText(previewAppSource, "workflowOperationTypeText", "preview/app.js must translate workflow action outcomes through the catalog.");
requireText(previewAppSource, "workflowVersionHistory", "preview/app.js must show text version history for workflow rollback.");
requireText(previewAppSource, "data-workflow-rollback-version", "preview/app.js must expose persisted workflow rollback controls.");
requireText(previewAppSource, "workflowPreflightPanel", "preview/app.js must show live workflow preflight results before execution.");
requireText(previewAppSource, "data-workflow-preflight", "preview/app.js must expose a workflow preflight control wired to the Rust endpoint.");
requireText(previewAppSource, "preflightWorkflowTemplate(", "preview/app.js must run workflow preflight through the live workflow endpoint.");
requireText(previewAppSource, "workflowEditValidationPanel", "preview/app.js must show live workflow edit validation instead of saving unsafe wiring silently.");
requireText(previewAppSource, "validateWorkflowStepEdit(", "preview/app.js must dry-run workflow edge edits before persisting them.");
requireText(previewAppSource, "/validations", "preview/app.js must call the workflow validation route before connector mutations.");
requireText(previewAppSource, "store.template_versions", "preview/app.js must load workflow version history from the Rust store.");
requireText(previewAppSource, "data-workflow-move-step", "preview/app.js must expose persisted workflow reorganization controls.");
requireText(previewAppSource, "handleWorkflowNodePointerDown", "preview/app.js must support moving workflow nodes directly on the canvas.");
requireText(previewAppSource, "workflowAnalyticsPanel", "preview/app.js must render real workflow graph analytics from the Rust store.");
requireText(previewAppSource, "workflowOperationalSteps", "preview/app.js must derive operator work lists from the editable workflow graph.");
requireText(previewAppSource, "editableWorkflowSteps", "preview/app.js must expose edited workflow steps to HR/Payroll/Approval/Archive surfaces.");
requirePattern(previewAppSource, /function workflowSteps\(target\) \{\s+const steps = editableWorkflowSteps\(\);/, "preview/app.js workflow surfaces must filter the edited graph, not the original payroll sequence.");
requireText(previewAppSource, "const steps = [...editableWorkflowSteps(), ...liveQueueStepItems()];", "preview/app.js home work buckets must include edited workflow graph steps.");
requireText(previewAppSource, "for (const nextId of node.nextStepIds || [])", "preview/app.js edited workflow work lists must follow persisted graph edges.");
requireText(previewAppSource, "next_step_ids", "preview/app.js must persist workflow edge wiring, not just visual cards.");
requireText(previewAppSource, "getAll(\"next_step_ids\")", "preview/app.js must support multi-branch workflow edge wiring.");
requireText(previewAppSource, "after_step_id", "preview/app.js must persist workflow placement/reordering through the workflow store.");
requireText(previewAppSource, "workflowOwnerOptions", "preview/app.js workflow editor must expose owner role editing.");
requireText(previewAppSource, "workflowLaneOptions", "preview/app.js workflow editor must expose lane editing.");
requireText(previewAppSource, "workflowNodeTypeOptions", "preview/app.js workflow editor must expose step-type editing.");
requireText(previewAppSource, "slo_minutes", "preview/app.js workflow editor must persist completion targets through the live workflow endpoint.");
requireText(previewAppSource, "escalation_role", "preview/app.js workflow editor must persist escalation roles through the live workflow endpoint.");
requireText(previewAppSource, "condition_expression", "preview/app.js workflow editor must persist branch conditions through the live workflow endpoint.");
requireText(previewAppSource, "permission_scope", "preview/app.js workflow editor must persist protected-object access scope through the live workflow endpoint.");
requireText(previewAppSource, "workflowPermissionScopeFromForm", "preview/app.js workflow editor must translate form input into workflow permission scope metadata.");
requireText(previewAppSource, "renderApproval", "preview/app.js must split 전자결재 into an approval-only surface.");
requireText(previewAppSource, '"approval"', "preview/app.js must include a first-class approval route.");
requireText(previewAppSource, "workflowTemplateNodes", "preview/app.js workflow canvas must visualize workflow logic nodes, not numbered sequence cards.");
requireText(previewAppSource, "data-open-tutorial", "preview/app.js must expose screen-aware guided onboarding from the top bar.");
requireText(previewAppSource, "tutorialAnchorLabelKeys", "preview/app.js guided onboarding must name the current UI region from catalog-backed labels.");
requireText(previewAppSource, "tutorialActiveAnchor", "preview/app.js guided onboarding must calculate the current UI region to highlight.");
requireText(previewAppSource, "tutorialAnchorClass", "preview/app.js guided onboarding must bind walkthrough steps to actual screen regions.");
requireText(previewAppSource, 'data-tutorial-anchor="topbar-help"', "preview/app.js top bar help must be an anchored walkthrough target.");
requireText(previewAppSource, 'data-tutorial-target="${escapeAttribute(step.anchor)}"', "preview/app.js tutorial overlay must identify the active UI target.");
requireText(previewAppSource, 'workflow-canvas ${state.workflowConnectFromId ? "connecting" : ""}${tutorialAnchorClass("workflow-canvas")}', "preview/app.js workflow tutorial must highlight the editable workflow canvas.");
requireText(previewStylesSource, ".tutorial-anchor-active", "preview/styles.css must visually highlight active guided walkthrough regions.");
requireText(previewStylesSource, ".tutorial-target-pill", "preview/styles.css must style the contextual tutorial target label.");
requireText(previewAppSource, "renderSettings", "preview/app.js must keep settings reachable from the top bar.");
requireText(previewAppSource, "workspaceSettingsPanel", "preview/app.js Settings must include profile/workspace preferences, not only theme/language.");
requireText(previewAppSource, "data-preference-key", "preview/app.js Settings workspace preferences must persist through the live settings route.");
requireText(previewAppSource, 'data-open-settings="true" role="menuitem"', "preview/app.js profile menu must open Settings from the top bar profile action.");
rejectText(previewAppSource, "shell.themePanel", "preview/app.js must not reference retired sidebar theme-panel i18n keys.");
rejectPattern(previewAppSource, /const navDefs = \[[\s\S]*?\["settings"/, "preview/app.js must not place Settings in the left navigation definitions.");
requireText(previewAppSource, "topbarCountBadge(notificationItems().length)", "preview/app.js topbar notifications must show live item counts.");
requireText(previewAppSource, "workflowNotificationItems", "preview/app.js topbar notifications must include live workflow runtime/data-record evidence.");
requireText(previewAppSource, "workflowMessageItems", "preview/app.js topbar messages must include live workflow handoff evidence.");
requireText(previewAppSource, "state.workflowRuntimeEvents", "preview/app.js topbar workflow items must derive from Rust workflow runtime events.");
requireText(previewAppSource, "state.workflowDataRecords", "preview/app.js topbar workflow items must derive from Rust workflow data records.");
requireText(previewAppSource, 'fetch("/api/settings/v1/preferences")', "preview/app.js must fetch the live settings preference endpoint.");
requireText(previewAppSource, "mutateUserPreferences", "preview/app.js must persist settings changes through the live preference endpoint.");
requireText(previewAppSource, "topbarActionPanel", "preview/app.js must expose live-derived notification/message panels.");
requireText(previewAppSource, "liveQueueStepItems", "preview/app.js home buckets must merge live work_queue items with payroll workstream steps.");
requireText(previewAppSource, "data-home-work-target", "preview/app.js home work rows must open the relevant business surface, not only update invisible selection state.");
requireText(previewAppSource, "lucidePaths", "preview/app.js must use the Lucide icon adapter in the dependency-free preview.");
requireText(previewAppSource, "mutateHrEmployee", "preview/app.js must live-wire HR add/update/remove actions.");
requireText(previewAppSource, "employeeLifecycleSummary", "preview/app.js HR must frame employee lifecycle status, not only a raw table.");
requireText(previewAppSource, "payrollStageSummary", "preview/app.js Payroll must frame close/run/output work stages.");
requireText(previewAppSource, "adminSetupGroups", "preview/app.js Admin must group setup/security/operation work instead of a generic wall.");
requireText(previewAppSource, "data-intake-file", "preview/app.js must expose 자료함 import/intake workflow entry.");
requireText(previewAppSource, "FormData", "preview/app.js must upload the real selected file, not JSON/base64 placeholder content.");
requireText(previewAppSource, "data-intake-resolve", "preview/app.js must expose live issue-review actions for eligible 자료함 guidance/anomaly items.");
requireText(previewAppSource, "resolveArchiveIssue", "preview/app.js must resolve archive issues through the server route, not browser-only state.");
requireText(previewAppSource, "data-intake-admit", "preview/app.js must expose live canonical-admission actions for reviewed 자료함 rows.");
requireText(previewAppSource, "admitArchiveIntake", "preview/app.js must admit reviewed archive rows through the server route, not browser-only state.");
requireText(previewAppSource, "data-intake-rollback", "preview/app.js must expose recovery rollback actions for admitted 자료함 rows.");
requireText(previewAppSource, "rollbackArchiveIntake", "preview/app.js must rollback admitted archive rows through the server route, not browser-only state.");
requireText(previewAppSource, "archiveVersionList", "preview/app.js must render source versions, recovery points, and source-file sync status from Rust.");
requireText(previewAppSource, "source_versions", "preview/app.js must show immutable RustFS source versions without storing binary snapshots in PostgreSQL.");
requireText(previewAppSource, "recovery_points", "preview/app.js must show row-level recovery points for selected rollback.");
requireText(previewAppSource, "source_sync_items", "preview/app.js must show source workbook sync state from PostgreSQL.");
requireText(previewAppSource, "data-intake-source-sync", "preview/app.js must expose live source-file sync for pending source-sync rows.");
requireText(previewAppSource, "syncArchiveSource", "preview/app.js must sync source files through the server route, not browser-only state.");
requireText(previewAppSource, '"hr_attendance_staging"', "preview/app.js must allow reviewed HR attendance staging rows to reach the canonical admission route.");
requireText(previewAppSource, '"payroll_input_staging"', "preview/app.js must allow reviewed payroll staging rows to reach the canonical admission route.");
requireText(previewAppSource, "archiveIntakeList", "preview/app.js must render the live 자료함 intake queue.");
requireText(previewAppSource, "archiveGuidanceList", "preview/app.js must surface human mapping/anomaly guidance from Rust.");
requireText(previewAppSource, "const palette =", "preview/app.js must draw runtime accent/tone colors from a central preview palette adapter.");
requireText(previewAppSource, "var(--palette-", "preview/app.js must use CSS palette variables instead of ad-hoc hex accents.");
rejectPattern(previewAppSource, /#[0-9A-Fa-f]{3,8}\b/, "preview/app.js must not contain ad-hoc hex colors; use palette variables.");
rejectText(previewAppSource, "enterpriseMaturity", "preview/app.js must not render enterprise maturity walls to operators.");
rejectText(previewAppSource, "renderLiveEnterpriseSurface", "preview/app.js must not route workflow/archive/admin to a generic maturity wall.");
rejectText(previewAppSource, "readinessCards", "preview/app.js must not render technical payroll readiness cards.");
rejectText(previewAppSource, "payrollReadinessDetail", "preview/app.js must not render technical readiness detail panels.");
rejectText(previewAppSource, "selectedPayrollCardKey", "preview/app.js must not keep stale readiness-card selection state.");
rejectText(previewAppSource, "Hermetic 개발", "preview/app.js must not expose development diagnostics in the user UI.");
requireText(sourceDataSource, "dateWithOffset", "src/data.ts must derive Home schedule dates from the current date instead of stale hardcoded dates.");
requireText(sourceDataSource, "formatScheduleDate", "src/data.ts must format schedule dates per locale.");
requireText(sourceScreensSource, "calendarDisplayParts", "src/screens.tsx must render the current calendar header dynamically.");
rejectText(sourceDataSource, "2026.06.04", "src/data.ts must not hardcode the stale Home schedule date 2026.06.04.");
rejectText(sourceScreensSource, "2026.06.04", "src/screens.tsx must not hardcode the stale Home schedule date 2026.06.04.");
rejectText(sourceCatalogSource, "2026년 6월 4일", "catalog.json must not describe Home schedule using the stale date 2026년 6월 4일.");
rejectText(previewAppSource, "Buck2 전용", "preview/app.js must not expose build-tool details in the user UI.");
rejectText(previewAppSource, "previewAccounts", "preview/app.js must not contain hardcoded preview accounts.");
rejectText(previewAppSource, "data-demo-login", "preview/app.js must not expose demo login controls.");
rejectText(previewAppSource, "authed: true", "preview/app.js must fail closed without a Rust-authenticated session.");
rejectText(previewAppSource, "modeLabel", "preview/app.js must not carry technical session mode labels into operator state.");
rejectText(previewAppSource, "sessionSignedOut", "preview/app.js must not create browser-local session override state.");
rejectText(previewAppSource, "data-refresh-session", "preview/app.js must not locally refresh/recreate authentication state.");
rejectText(previewAppSource, "data-return-session", "preview/app.js must not locally reauthenticate a signed-out session.");
rejectText(previewAppSource, "state.authed = true", "preview/app.js must not locally set authenticated state.");
rejectText(previewAppSource, 'accept=".xlsx', "preview/app.js 자료함 intake must accept any file, not only spreadsheets.");
rejectText(previewAppSource, "String(index + 1).padStart", "preview/app.js must not render numbered workflow sequence cards.");
rejectText(previewAppSource, "stepCards(", "preview/app.js must not use generic numbered/card-grid workflow placeholders.");
rejectText(previewAppSource, "data-step-status", "preview/app.js must not expose non-persistent fake workflow status editing.");
rejectText(previewAppSource, "workflow.canvas.edit", "preview/app.js must not show stub workflow edit controls without live persistence.");
requireText(previewAppSource, "/api/workflow/v1/templates", "preview/app.js must load persisted workflow templates from the live route.");
requireText(previewAppSource, "mutateWorkflowStepStatus", "preview/app.js must persist workflow status edits through the live route.");
requireText(previewAppSource, "data-workflow-status", "preview/app.js must expose workflow status controls only when wired to persisted route mutation.");
rejectText(previewAppSource, "login-form", "preview/app.js must not render a credential stub form in the live path.");
rejectText(previewAppSource, "password", "preview/app.js must not include hardcoded password handling in the live path.");
rejectText(previewAppSource.toLowerCase(), "mock", "preview/app.js must not describe live data as mock.");
rejectText(previewAppSource.toLowerCase(), "demo", "preview/app.js must not describe the live path as demo.");

const tutorialCloseButtonCount = (previewAppSource.match(/class="icon-btn tutorial-close"/g) || []).length;
if (tutorialCloseButtonCount !== 1) {
  errors.push("preview/app.js guided tutorial must render exactly one close button.");
}

for (const surface of ["renderHome", "renderHr", "renderPayroll", "renderWorkflow", "renderArchive"]) {
  const body = functionBody(previewAppSource, surface);
  rejectText(body, "liveSourcePanel", `${surface} must not show technical live source diagnostics.`);
  rejectText(body, "view.source", `${surface} must not show Rust/source internals to operators.`);
  rejectText(body, "readiness", `${surface} must not show technical readiness internals.`);
}
const settingsBody = functionBody(previewAppSource, "renderSettings");
rejectText(settingsBody, "liveSourcePanel", "renderSettings must not show technical source diagnostics to operators.");
rejectText(previewAppSource, "function liveSourcePanel", "preview/app.js must not include a visible technical source diagnostics panel.");

requireText(contractSource, 'export type PayrollExecutionBackend = "rust_native";', "TypeScript payroll contract must expose rust_native backend.");
requireText(contractSource, "executor: string;", "TypeScript payroll execution plan must expose executor, not compatibility_executor.");
rejectText(contractSource, "python_compatibility", "TypeScript payroll contract must not expose python_compatibility.");
rejectText(contractSource, "compatibility_executor", "TypeScript payroll contract must not expose compatibility_executor.");

requireText(rustLibSource, "pub mod platform_view;", "Rust payroll API must export the platform live view module.");
requireText(rustLibSource, "pub mod auth_policy;", "Rust payroll API must export the auth policy module.");
requireText(rustLibSource, "pub mod api_contract;", "Rust payroll API must export the API contract spine module.");
requireText(rustLibSource, "api_endpoint_contracts", "Rust payroll API must export the API endpoint contract registry.");
requireText(rustLibSource, "evaluate_authorization", "Rust payroll API must export the ABAC/RBAC/PBAC authorization evaluator.");
requireText(rustApiContractSource, 'API_CONTRACT_SCHEMA: &str = "bitween.api-contract-spine.v1"', "Rust API contract spine must declare a stable schema.");
requireText(rustApiContractSource, "ApiEndpointContract", "Rust API contract spine must expose endpoint contract records.");
requireText(rustApiContractSource, "API_IMPLEMENTATION_LIVE_RUST_ROUTE", "Rust API contract spine must distinguish live Rust routes.");
requireText(rustApiContractSource, "API_IMPLEMENTATION_LIVE_RUST_SERVICE", "Rust API contract spine must distinguish live Rust service contracts.");
requireText(rustApiContractSource, "API_IMPLEMENTATION_CONFIGURED_IDENTITY_ROUTE", "Rust API contract spine must distinguish configured identity routes.");
requireText(rustApiContractSource, "API_IMPLEMENTATION_CONTRACT_LOCKED_PENDING_ROUTE", "Rust API contract spine must honestly mark pending production routes.");
for (const moduleName of ["platform", "hr", "payroll", "workflow", "approval", "archive", "settings", "auth", "admin"]) {
  requireText(rustApiContractSource, `module: "${moduleName}"`, `Rust API contract spine must cover the ${moduleName} module.`);
}
for (const path of [
  "/api/platform/v1/view-model",
  "/api/hr/v1/employees",
  "/api/payroll/v1/runs",
  "/api/payroll/v1/runs/validate",
  "/api/workflow/v1/templates",
  "/api/workflow/v1/templates/{template_id}/steps",
  "/api/workflow/v1/templates/{template_id}/steps/{step_id}/validations",
  "/api/approval/v1/requests",
  "/api/archive/v1/intake",
  "/api/archive/v1/intake/{intake_id}/admissions",
  "/api/archive/v1/intake/{intake_id}/rollbacks",
  "/api/archive/v1/intake/{intake_id}/source-syncs",
  "/api/settings/v1/preferences",
  "/api/auth/v1/routes",
  "/api/auth/v1/signin",
  "/api/auth/v1/signup",
  "/api/onboarding/v1/start",
  "/api/auth/v1/signout",
  "/api/admin/v1/tenants/{tenant_id}/access"
]) {
  requireText(rustApiContractSource, `path: "${path}"`, `Rust API contract spine must include ${path}.`);
}
for (const lifecycleTag of [
  "rustfs_original_object",
  "checksum_sha256",
  "quarantine",
  "human_review",
  "canonical_admission",
  "row_level_recovery",
  "source_file_sync"
]) {
  requireText(rustApiContractSource, lifecycleTag, `Rust API contract spine must preserve RustFS lifecycle tag ${lifecycleTag}.`);
}
for (const schema of [
  "bitween.payroll.run-response.v1",
  "bitween.payroll.validation-response.v1",
  "bitween.approval.queue.v1",
  "bitween.approval.signature-receipt.v1",
  "bitween.admin.access-policy.v1"
]) {
  requireText(rustApiContractSource, schema, `Rust API contract spine must publish response schema ${schema}.`);
}
requireText(rustApiContractSource, "AuthSensitiveOperation::parse", "Rust API contract spine tests must prove non-public operations are backed by the Rust ABAC/RBAC/PBAC policy.");
requireText(rustApiContractSource, "PostgreSQL", "Rust API contract spine must declare PostgreSQL ownership for business write contracts.");
requireText(rustApiContractSource, "api_contract_uses_only_controlled_implementation_states", "Rust API contract spine must test controlled implementation state wording.");
requireText(rustApiContractSource, "response_schema: HR_EMPLOYEE_STORE_SCHEMA", "Rust API contract spine must reuse the HR store response schema constant instead of duplicating schema strings.");
requireText(rustApiContractSource, "response_schema: WORKFLOW_TEMPLATE_STORE_SCHEMA", "Rust API contract spine must reuse the workflow store response schema constant instead of duplicating schema strings.");
requireText(rustApiContractSource, "response_schema: WORKFLOW_PREFLIGHT_SCHEMA", "Rust API contract spine must reuse the workflow preflight response schema constant instead of duplicating schema strings.");
requireText(rustApiContractSource, "response_schema: WORKFLOW_EDIT_VALIDATION_SCHEMA", "Rust API contract spine must reuse the workflow edit-validation response schema constant instead of duplicating schema strings.");
requireText(rustApiContractSource, "response_schema: ARCHIVE_INTAKE_STORE_SCHEMA", "Rust API contract spine must reuse the archive intake response schema constant instead of duplicating schema strings.");
requireText(rustApiContractSource, "response_schema: ARCHIVE_SOURCE_SYNC_PLAN_SCHEMA", "Rust API contract spine must reuse the archive source-sync response schema constant instead of duplicating schema strings.");
requireText(rustApiContractSource, "response_schema: USER_PREFERENCE_STORE_SCHEMA", "Rust API contract spine must reuse the settings response schema constant instead of duplicating schema strings.");
requireText(rustApiContractSource, "response_schema: AUTH_ROUTES_SCHEMA", "Rust API contract spine must reuse the auth route-status schema constant instead of duplicating schema strings.");
requireText(rustApiContractSource, "response_schema: AUTH_ROUTE_ACTION_SCHEMA", "Rust API contract spine must reuse the auth route-action schema constant instead of duplicating schema strings.");
requireText(payrollBuckSource, "src/api_contract.rs", "crates/payroll-api/BUCK must include the Rust API contract spine source.");
requireText(rustAuthPolicySource, "AUTHZ_POLICY_ID", "Rust auth policy must declare a stable PBAC policy id.");
requireText(rustAuthPolicySource, "AuthzRole", "Rust auth policy must model RBAC roles.");
requireText(rustAuthPolicySource, "AuthzRequest", "Rust auth policy must model an authorization request.");
requireText(rustAuthPolicySource, "AuthzDecision", "Rust auth policy must model a fail-closed authorization decision.");
requireText(rustAuthPolicySource, "AuthDataClass", "Rust auth policy must model ABAC data classification.");
requireText(rustAuthPolicySource, "WorkflowTemplateRead", "Rust auth policy must model workflow template read as a first-class operation.");
requireText(rustAuthPolicySource, "WorkflowTemplateWrite", "Rust auth policy must model workflow template write as a first-class operation.");
requireText(rustAuthPolicySource, "WorkflowStepExecute", "Rust auth policy must model workflow step execution as a first-class operation.");
requireText(rustAuthSessionSource, "AUTH_ROUTES_SCHEMA", "Rust auth session boundary must export the auth route-status response schema constant.");
requireText(rustAuthSessionSource, "AUTH_ROUTE_ACTION_SCHEMA", "Rust auth session boundary must export the auth route-action response schema constant.");
requireText(rustWorkflowTemplateStoreSource, "WORKFLOW_TEMPLATE_STORE_SCHEMA", "Rust workflow template store must declare a stable schema.");
requireText(rustWorkflowTemplateStoreSource, "audit_events", "Rust workflow template store must record audit events for workflow edits.");
requireText(rustWorkflowTemplateStoreSource, "runtime_events", "Rust workflow template store must record runtime events for executed workflow actions.");
requireText(rustWorkflowTemplateStoreSource, "WorkflowDataOperation", "Rust workflow template store must record concrete data operations for executed workflow actions.");
requireText(rustWorkflowTemplateStoreSource, "data_operations_for_step", "Rust workflow executions must map workflow steps to concrete domain data operations.");
requireText(rustWorkflowTemplateStoreSource, "WorkflowDataRecord", "Rust workflow template store must persist workflow data records changed by executed actions.");
requireText(rustWorkflowTemplateStoreSource, "apply_data_operations", "Rust workflow executions must upsert data records, not only append runtime events.");
requireText(rustWorkflowTemplateStoreSource, "payroll_calculation_plan", "Rust workflow execution must produce payroll calculation planning evidence for calculation steps.");
requireText(rustWorkflowTemplateStoreSource, "WorkflowTemplateAnalytics", "Rust workflow template store must calculate graph analytics for workflow editing.");
requireText(rustWorkflowTemplateStoreSource, "WorkflowEditValidationReport", "Rust workflow template store must return structured dry-run edit validation reports.");
requireText(rustWorkflowTemplateStoreSource, "reject_blocking_graph_issues", "Rust workflow template store must block cycle-creating graph edits before persistence.");
requireText(rustWorkflowTemplateStoreSource, "validate-step-update", "Rust workflow template store must expose a dry-run validation action for workflow edge edits.");
requireText(rustWorkflowTemplateStoreSource, "WorkflowTemplateVersionRecord", "Rust workflow template store must preserve text graph versions for rollback.");
requireText(rustWorkflowTemplateStoreSource, "template_versions", "Rust workflow template store must expose workflow version history to the UI.");
requireText(rustWorkflowTemplateStoreSource, "rollback_template", "Rust workflow template store must support restoring a previous workflow graph version.");
requireText(rustWorkflowTemplateStoreSource, "rollback_of_version", "Rust workflow version history must retain rollback lineage without binary snapshots.");
requireText(rustWorkflowTemplateStoreSource, "BITWEEN_WORKFLOW_TEMPLATE_STORE", "Rust workflow template store must support explicit hermetic local review path.");
requireText(rustWorkflowTemplateStoreSource, "PostgreSQL relational workflow template storage is required", "Rust workflow template store must fail closed without PostgreSQL/local-review storage.");
requireText(rustWorkflowTemplateStoreSource, "BITWEEN_POSTGRES_DSN", "Rust workflow template store must use PostgreSQL when a DSN is configured.");
requireText(rustWorkflowTemplateStoreSource, "connect_client_session", "Rust workflow template store must connect through the live PostgreSQL client session.");
requireText(rustWorkflowTemplateStoreSource, "required_postgres_migrations", "Rust workflow template store must apply required migrations before reads or writes.");
requireText(rustWorkflowTemplateStoreSource, "load_postgres_store", "Rust workflow template store must read workflow templates from PostgreSQL.");
requireText(rustWorkflowTemplateStoreSource, "save_postgres_store", "Rust workflow template store must write edited workflow templates to PostgreSQL.");
requireText(rustWorkflowTemplateStoreSource, "load_postgres_template_versions", "Rust workflow template store must load workflow version history from PostgreSQL.");
requireText(rustWorkflowTemplateStoreSource, "bitween_workflow.workflow_data_record", "Rust workflow template store must persist executed workflow data records to PostgreSQL.");
requireText(rustWorkflowTemplateSchemaSource, "WORKFLOW_TEMPLATE_STORE_SCHEMA", "Rust workflow template schema module must export the live workflow response schema constant.");
requireText(rustWorkflowTemplateSchemaSource, "WORKFLOW_PREFLIGHT_SCHEMA", "Rust workflow template schema module must export the preflight response schema constant.");
requireText(rustWorkflowTemplateSchemaSource, "WORKFLOW_EDIT_VALIDATION_SCHEMA", "Rust workflow template schema module must export the edit-validation response schema constant.");
requireText(rustPostgresMigrateSource, "bitween.postgres-migrate.v1", "Rust PostgreSQL migration job must expose a stable response schema.");
requireText(rustPostgresMigrateSource, "BITWEEN_POSTGRES_DSN", "Rust PostgreSQL migration job must read the explicit PostgreSQL DSN.");
requireText(rustPostgresMigrateSource, "BITWEEN_POSTGRES_TLS_POLICY", "Rust PostgreSQL migration job must read the explicit TLS policy.");
requireText(rustPostgresMigrateSource, "BITWEEN_POSTGRES_TENANT_ID", "Rust PostgreSQL migration job must require tenant scope.");
requireText(rustPostgresMigrateSource, "BITWEEN_POSTGRES_LEGAL_ENTITY_ID", "Rust PostgreSQL migration job must require legal-entity scope.");
requireText(rustPostgresMigrateSource, "BITWEEN_POSTGRES_WORKPLACE_ID", "Rust PostgreSQL migration job must require workplace scope.");
requireText(rustPostgresMigrateSource, "connect_client_session", "Rust PostgreSQL migration job must use the real PostgreSQL client session.");
requireText(rustPostgresMigrateSource, "apply_required_migrations", "Rust PostgreSQL migration job must apply the controlled migration set.");
requireText(rustPostgresMigrateSource, "required_postgres_migrations", "Rust PostgreSQL migration job must use the required migration list.");
requireText(rustPostgresMigrateSource, "postgres://<redacted>", "Rust PostgreSQL migration job must redact DSNs in all responses.");
requireText(rustPostgresMigrateSource, "postgres_tenant_scope_required", "Rust PostgreSQL migration job must fail closed without tenant scope.");
requireText(rustPostgresMigrateSource, "postgres_legal_entity_scope_required", "Rust PostgreSQL migration job must fail closed without legal-entity scope.");
requireText(rustPostgresMigrateSource, "postgres_workplace_scope_required", "Rust PostgreSQL migration job must fail closed without workplace scope.");
requireText(rustCloudNativeAuditWorkerSource, "bitween.cloud-native-audit-worker.v1", "Rust cloud-native audit worker must expose a stable response schema.");
requireText(rustCloudNativeAuditWorkerSource, "bitween.audit-event.v1", "Rust cloud-native audit worker must expose the audit event schema.");
requireText(rustCloudNativeAuditWorkerSource, "BITWEEN_POSTGRES_DSN", "Rust cloud-native audit worker must inspect the PostgreSQL DSN contract.");
requireText(rustCloudNativeAuditWorkerSource, "BITWEEN_POSTGRES_TLS_POLICY", "Rust cloud-native audit worker must inspect the PostgreSQL TLS contract.");
requireText(rustCloudNativeAuditWorkerSource, "BITWEEN_POSTGRES_TENANT_ID", "Rust cloud-native audit worker must inspect tenant scope.");
requireText(rustCloudNativeAuditWorkerSource, "BITWEEN_RUSTFS_ENDPOINT", "Rust cloud-native audit worker must inspect RustFS endpoint wiring.");
requireText(rustCloudNativeAuditWorkerSource, "BITWEEN_RUSTFS_BUCKET_EVIDENCE", "Rust cloud-native audit worker must inspect RustFS evidence bucket wiring.");
requireText(rustCloudNativeAuditWorkerSource, "BITWEEN_AUDIT_EVENT_STREAM", "Rust cloud-native audit worker must inspect audit event stream wiring.");
requireText(rustCloudNativeAuditWorkerSource, "BITWEEN_OTEL_EXPORTER_OTLP_ENDPOINT", "Rust cloud-native audit worker must inspect OpenTelemetry OTLP wiring.");
requireText(rustCloudNativeAuditWorkerSource, "postgres://<redacted>", "Rust cloud-native audit worker must redact PostgreSQL DSNs in all responses.");
requireText(rustCloudNativeAuditWorkerSource, "required environment value is absent", "Rust cloud-native audit worker must fail closed with actionable missing-env evidence.");
requireText(payrollBuckSource, 'name = "postgres_migrate"', "crates/payroll-api/BUCK must build the PostgreSQL migration job binary.");
requireText(payrollBuckSource, 'name = "postgres_migrate_test"', "crates/payroll-api/BUCK must test the PostgreSQL migration job fail-closed behavior.");
requireText(payrollBuckSource, "src/bin/postgres_migrate.rs", "crates/payroll-api/BUCK must include the PostgreSQL migration job source.");
requireText(payrollBuckSource, 'name = "cloud_native_audit_worker"', "crates/payroll-api/BUCK must build the cloud-native audit worker binary.");
requireText(payrollBuckSource, 'name = "cloud_native_audit_worker_test"', "crates/payroll-api/BUCK must test the cloud-native audit worker fail-closed behavior.");
requireText(payrollBuckSource, "src/bin/cloud_native_audit_worker.rs", "crates/payroll-api/BUCK must include the cloud-native audit worker source.");
requireText(rustWorkflowTemplateSchemaSource, '"bitween_workflow.workflow_data_record"', "Rust workflow PostgreSQL contract must include persisted workflow data records.");
requireText(workflowPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_data_record", "Workflow PostgreSQL migration must create a data-record table for executed workflow actions.");
requireText(workflowPostgresMigrationSource, "scope_hash char(64) NOT NULL CHECK", "Workflow data records must be idempotently scoped by a stable scope hash.");
requireText(workflowPostgresMigrationSource, "business_scope jsonb NOT NULL DEFAULT '{}'::jsonb", "Workflow data records must persist business scope for PostgreSQL admission.");
requireText(workflowPostgresMigrationSource, "'payroll_calculation_plan'", "Workflow data-record schema must support payroll calculation planning evidence.");
requireText(workflowPostgresMigrationSource, "workflow_data_record_tenant_isolation", "Workflow data-record table must enforce tenant RLS.");
requireText(rustAuthPolicySource, "actor_legal_entity", "Rust auth policy must carry legal-entity ABAC scope.");
requireText(rustAuthPolicySource, "resource_legal_entity", "Rust auth policy must compare resource legal-entity ABAC scope.");
requireText(rustAuthPolicySource, "AuthWorkflowState", "Rust auth policy must model PBAC workflow state.");
requireText(rustAuthPolicySource, "evaluate_authorization", "Rust auth policy must evaluate ABAC, RBAC, PBAC, and step-up together.");
requireText(rustAuthPolicySource, "rbac_denied", "Rust auth policy must produce RBAC denial reasons without leaking claims.");
requireText(rustAuthPolicySource, "abac_scope_denied", "Rust auth policy must deny tenant/workplace scope mismatches.");
requireText(rustAuthPolicySource, "pbac_workflow_denied", "Rust auth policy must deny policy/workflow state mismatches.");
requireText(rustAuthPolicySource, "[\"pbac\", \"rbac\", \"abac\", \"acr_step_up\"]", "Rust auth policy decisions must record the active authorization control families.");
requireText(rustPlatformViewSource, "PLATFORM_VIEW_SCHEMA", "Rust platform live view must declare a stable schema.");
requireText(rustPlatformViewSource, "PAYROLL_RUST_NATIVE_EXECUTOR", "Rust platform live view must identify the Rust executor.");
requireText(rustPlatformViewSource, "PayrollWorkstreamView", "Rust platform live view must expose a workflow workstream, not only readiness cards.");
requireText(rustPlatformViewSource, '"hr"', "Rust platform live view must keep HR as a distinct workflow surface.");
requireText(rustPlatformViewSource, 'id: "approval"', "Rust platform live view must expose approval as a separate navigation surface from workflow.");
requireText(rustPlatformViewSource, 'label: "Workflow"', "Rust platform live view workflow surface must mean workflow logic/canvas, not approvals.");
requireText(rustPlatformViewSource, "session_jwt_verified", "Rust platform live view must require verified JWT/session claims before marking a session authenticated.");
requireText(rustPlatformViewSource, "BITWEEN_SESSION_JWT_VERIFIED", "Rust platform live view must make authentication explicit and Rust-owned.");
requireText(rustPlatformViewSource, "BITWEEN_SESSION_JWT_ISSUER", "Rust platform live view must require a verified JWT issuer claim.");
requireText(rustPlatformViewSource, "BITWEEN_SESSION_JWT_AUDIENCE", "Rust platform live view must require a verified JWT audience claim.");
requireText(rustPlatformViewSource, "BITWEEN_SESSION_JWT_SUBJECT", "Rust platform live view must require a verified JWT subject claim.");
requireText(rustPlatformViewSource, "BITWEEN_SESSION_JWT_EXPIRES_AT_UNIX", "Rust platform live view must require a bounded JWT expiration.");
requireText(rustPlatformViewSource, "BITWEEN_WEBAUTHN_USER_VERIFIED", "Rust platform live view must require WebAuthn/passkey user verification for authenticated shell access.");
requireText(rustPlatformViewSource, "session_webauthn_user_verified", "Rust platform live view must track WebAuthn user verification explicitly.");
requireText(rustPlatformViewSource, "BITWEEN_SESSION_ACR_LEVEL", "Rust platform live view must require a controlled ACR level after identity verification.");
requireText(rustPlatformViewSource, "BITWEEN_SESSION_ACR_EVENT_AT_UNIX", "Rust platform live view must require a bounded ACR grant timestamp.");
requireText(rustPlatformViewSource, "BITWEEN_SESSION_AUTHZ_POLICY_ID", "Rust platform live view must require a trusted PBAC policy id for sensitive authorization.");
requireText(rustPlatformViewSource, "BITWEEN_SESSION_AUTHZ_TENANT_ID", "Rust platform live view must carry tenant ABAC authorization attributes from the identity gateway.");
requireText(rustPlatformViewSource, "BITWEEN_SESSION_AUTHZ_LEGAL_ENTITY", "Rust platform live view must carry legal-entity ABAC authorization attributes from the identity gateway.");
requireText(rustPlatformViewSource, "BITWEEN_SESSION_AUTHZ_WORKPLACE", "Rust platform live view must carry workplace ABAC authorization attributes from the identity gateway.");
requireText(rustPlatformViewSource, "session_acr_valid", "Rust platform live view must validate ACR freshness before authentication succeeds.");
requireText(rustPlatformViewSource, "session_authorizes_operation", "Rust platform live view must expose a full ABAC/RBAC/PBAC authorization gate for sensitive operations.");
requireText(rustPlatformViewSource, "session_authorization_request", "Rust platform live view must convert live session facts into Rust authorization requests.");
requireText(rustPlatformViewSource, "evaluate_authorization", "Rust platform live view must call the Rust authorization policy evaluator, not frontend labels.");
requirePattern(rustPlatformViewSource, /self\.auth_provider_configured[\s\S]*&&\s*self\.session_jwt_verified[\s\S]*&&\s*!self\.session_jwt_issuer\.is_empty\(\)[\s\S]*&&\s*!self\.session_jwt_audience\.is_empty\(\)[\s\S]*&&\s*!self\.session_jwt_subject\.is_empty\(\)[\s\S]*&&\s*self\.session_jwt_expires_at_unix\s*>\s*generated_at_unix\(\)[\s\S]*&&\s*self\.session_webauthn_user_verified/, "Rust platform live view must not authenticate without provider, verified JWT registered claims, valid expiration, and WebAuthn user verification.");
requirePattern(rustPlatformViewSource, /payroll_work_step\(\s*"request-approval"[\s\S]*?"approval"\s*,\s*\)/, "Rust payroll workstream must route approval requests to the approval surface.");
requireText(rustPlatformViewSource, 'id: "confirm-payroll-close"', "Rust platform live work queue must use business-language payroll close actions.");
requireText(rustPlatformViewSource, 'id: "set-payroll-scope"', "Rust platform live work queue must expose payroll scope work in business language.");
requireText(rustPlatformViewSource, 'id: "complete-access-setup"', "Rust platform live work queue must expose access setup work in business language.");
rejectText(rustPlatformViewSource, '"run-readiness-validation"', "Rust platform live work queue must not expose readiness action IDs to operators.");
rejectText(rustPlatformViewSource, '"review-payroll-readiness"', "Rust platform live work queue must not expose readiness action IDs to operators.");
rejectText(rustPlatformViewSource, "Run payroll readiness validation", "Rust platform live work queue must not expose readiness titles to operators.");
rejectText(rustPlatformViewSource, "Review payroll readiness", "Rust platform live work queue must not expose readiness titles to operators.");
requireText(rustLiveBinSource, "build_platform_live_view", "Rust live binary must emit the platform live view.");
requireText(rustAuthzDecisionBinSource, "bitween.authz-decision.v1", "Rust authorization decision binary must expose a stable schema.");
requireText(rustAuthzDecisionBinSource, "AuthSensitiveOperation::parse", "Rust authorization decision binary must parse controlled operation ids.");
requireText(rustAuthzDecisionBinSource, "session_is_authenticated", "Rust authorization decision binary must deny before policy checks when the session is not authenticated.");
requireText(rustAuthzDecisionBinSource, "session_authorization_decision", "Rust authorization decision binary must delegate ABAC/RBAC/PBAC decisions to the Rust policy module.");
requireText(rustAuthzDecisionBinSource, "session_not_authenticated", "Rust authorization decision binary must return a controlled unauthenticated denial reason.");
requireText(rustHrEmployeeStoreSource, "HR_EMPLOYEE_STORE_SCHEMA", "Rust HR employee store must use the exported HR response schema constant.");
requireText(rustHrEmployeeStoreSource, "EmployeeRecord", "Rust HR employee store must own employee records for the live HR surface.");
requireText(rustHrEmployeeStoreSource, "PostgreSQL relational employee storage is required", "Rust HR employee store must fail closed instead of silently writing local JSON.");
requireText(rustHrEmployeeStoreSource, "BITWEEN_ALLOW_LOCAL_REVIEW_STORE", "Rust HR employee local file persistence must be explicit hermetic review mode only.");
requireText(rustHrEmployeeStoreSource, "BITWEEN_POSTGRES_DSN", "Rust HR employee store must use PostgreSQL when a DSN is configured.");
requireText(rustHrEmployeeStoreSource, "connect_client_session", "Rust HR employee store must connect through the live PostgreSQL client session.");
requireText(rustHrEmployeeStoreSource, "required_postgres_migrations", "Rust HR employee store must apply required migrations before reads or writes.");
requireText(rustHrEmployeeStoreSource, "bitween_hr.employee", "Rust HR employee store must read and write the PostgreSQL HR employee table.");
requireText(rustHrEmployeeSchemaSource, "bitween.hr.postgres.v1", "Rust HR employee schema module must expose a PostgreSQL contract version.");
requireText(rustHrEmployeeSchemaSource, "HR_EMPLOYEE_STORE_SCHEMA", "Rust HR employee schema module must export the live response schema constant.");
requireText(rustHrEmployeeSchemaSource, "003_hr_employee.sql", "Rust HR employee schema module must include the PostgreSQL migration.");
requireText(hrEmployeePostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_hr.employee", "HR employee PostgreSQL migration must create the employee table.");
requireText(hrEmployeePostgresMigrationSource, "ALTER TABLE bitween_hr.employee ENABLE ROW LEVEL SECURITY", "HR employee PostgreSQL migration must enable RLS.");
requireText(userPreferencePostgresMigrationSource, "current_setting('bitween.tenant_id', true)", "User preference PostgreSQL migration must enforce tenant isolation using session tenant settings.");
requireText(rustArchiveIntakeStoreSource, "ARCHIVE_INTAKE_STORE_SCHEMA", "Rust archive intake store must use the exported archive response schema constant.");
requireText(rustArchiveIntakeStoreSource, "GuidanceItem", "Rust archive intake store must create human guidance backlog items for ambiguous data.");
requireText(rustArchiveIntakeStoreSource, "AnomalyItem", "Rust archive intake store must create anomaly items for faulty or unsafe data.");
requireText(rustArchiveIntakeStoreSource, "postgres_ready", "Rust archive intake store must distinguish reviewed relational-staging readiness.");
requireText(rustArchiveIntakeStoreSource, "object_uri", "Rust archive intake store must require a RustFS object URI before saving intake metadata.");
requireText(rustArchiveIntakeStoreSource, "object_bucket", "Rust archive intake store must persist the RustFS object bucket.");
requireText(rustArchiveIntakeStoreSource, "object_key", "Rust archive intake store must persist the RustFS object key.");
requireText(rustArchiveIntakeStoreSource, "content_sha256", "Rust archive intake store must persist a checksum for the RustFS object.");
requireText(rustArchiveIntakeStoreSource, "content_sample_sha256", "Rust archive intake store must persist content-sample checksum evidence.");
requireText(rustArchiveIntakeStoreSource, "content_sample_row_count", "Rust archive intake store must persist bounded content-sample row counts.");
requireText(rustArchiveIntakeStoreSource, "redacted_content_sample_excerpt", "Rust archive intake store must store redacted bounded sample excerpts in PostgreSQL only.");
requireText(rustArchiveIntakeStoreSource, "redacted_content_sample_excerpt(&sample_text)", "Rust archive intake store must derive redacted sample evidence from extracted file content.");
requireText(rustArchiveIntakeStoreSource, "extraction_status_for", "Rust archive intake store must classify sample extraction state for review/admission.");
requireText(rustArchiveIntakeStoreSource, "ArchiveExtractionStatus", "Rust archive intake store must expose a typed extraction status instead of free-form strings.");
requireText(rustArchiveIntakeStoreSource, "PostgreSQL relational archive intake storage is required", "Rust archive intake store must fail closed instead of silently writing local JSON.");
requireText(rustArchiveIntakeStoreSource, "BITWEEN_ALLOW_LOCAL_REVIEW_STORE", "Rust archive intake local file persistence must be explicit hermetic review mode only.");
requireText(rustArchiveIntakeStoreSource, "BITWEEN_POSTGRES_DSN", "Rust archive intake store must use PostgreSQL when a DSN is configured.");
requireText(rustArchiveIntakeStoreSource, "connect_client_session", "Rust archive intake store must connect through the live PostgreSQL client session.");
requireText(rustArchiveIntakeStoreSource, "required_postgres_migrations", "Rust archive intake store must apply required migrations before reads or writes.");
requireText(rustArchiveIntakeStoreSource, "bitween_archive.archive_intake", "Rust archive intake store must read and write the PostgreSQL archive intake table.");
requireText(rustArchiveIntakeStoreSource, "bitween_archive.archive_intake_issue", "Rust archive intake store must persist guidance/anomaly issues in PostgreSQL.");
requireText(rustArchiveIntakeStoreSource, "resolve_postgres_intake_issue", "Rust archive intake store must own live PostgreSQL issue resolution, not a UI-only acknowledgement.");
requireText(rustArchiveIntakeStoreSource, "status = 'resolved'", "Rust archive intake issue resolution must persist resolved issue status.");
requireText(rustArchiveIntakeStoreSource, "status = 'open'", "Rust archive intake store must return and recompute readiness from open review issues only.");
requireText(rustArchiveIntakeStoreSource, "admit_postgres_intake", "Rust archive intake store must own live PostgreSQL admission from staging into canonical business tables.");
requireText(rustArchiveIntakeStoreSource, "admit_postgres_hr_employee_staging", "Rust archive intake store must upsert reviewed HR staging rows into the canonical HR employee table.");
requireText(rustArchiveIntakeStoreSource, "admit_postgres_hr_attendance_staging", "Rust archive intake store must upsert reviewed HR attendance staging rows into the canonical attendance table.");
requireText(rustArchiveIntakeStoreSource, "admit_postgres_payroll_input_staging", "Rust archive intake store must upsert reviewed payroll staging rows into the canonical payroll input table.");
requireText(rustArchiveIntakeStoreSource, "archive_admission_audit", "Rust archive intake store must write admission audit evidence for canonical table changes.");
requireText(rustArchiveIntakeStoreSource, "rollback_postgres_intake", "Rust archive intake store must own live PostgreSQL recovery rollback from canonical business tables.");
requireText(rustArchiveIntakeStoreSource, "archive_admission_recovery_point", "Rust archive intake store must capture row-level recovery points before canonical admissions.");
requireText(rustArchiveIntakeStoreSource, "archive_source_sync", "Rust archive intake store must queue source workbook synchronization metadata after admission/rollback.");
requireText(rustArchiveIntakeStoreSource, "ARCHIVE_SOURCE_SYNC_PLAN_SCHEMA", "Rust archive intake store must expose a stable source-sync plan contract.");
requireText(rustArchiveIntakeStoreSource, "source-sync-plan", "Rust archive intake store must plan source workbook sync artifacts from PostgreSQL.");
requireText(rustArchiveIntakeStoreSource, "source-sync-complete", "Rust archive intake store must mark source sync complete only after RustFS upload metadata is supplied.");
requireText(rustArchiveIntakeStoreSource, "source-sync-fail", "Rust archive intake store must persist failed RustFS source-sync attempts instead of pretending success.");
requireText(rustArchiveIntakeStoreSource, "source_sync_bucket_from_parts", "Rust archive source sync must validate explicit RustFS bucket configuration.");
requireText(rustArchiveIntakeStoreSource, "archive_source_sync_rustfs_bucket_required", "Rust archive source sync must fail closed when no RustFS archive bucket is configured.");
requireText(rustArchiveIntakeStoreSource, "source_sync_workbook_xml", "Rust archive intake store must generate an Excel-compatible source sync artifact from PostgreSQL row state.");
requireText(rustArchiveIntakeStoreSource, "load_postgres_source_versions", "Rust archive intake store must return immutable RustFS object-version metadata.");
requireText(rustArchiveIntakeStoreSource, "load_postgres_recovery_points", "Rust archive intake store must return available row-level recovery points.");
requireText(rustArchiveIntakeStoreSource, "before_payload", "Rust archive rollback must keep only row-level JSON before-payload metadata for recovery.");
requireText(rustArchiveIntakeStoreSource, "after_payload", "Rust archive rollback must keep row-level JSON after-payload metadata for audit.");
requireText(rustArchiveIntakeStoreSource, "\"binary_snapshot_stored\": false", "Rust archive source-sync metadata must explicitly record that PostgreSQL stores no binary snapshots.");
requireText(rustArchiveIntakeStoreSource, "recovery_status = 'restored'", "Rust archive rollback must mark consumed recovery points as restored.");
rejectText(rustArchiveIntakeStoreSource.toLowerCase(), "bytea", "Rust archive intake store must not store binary snapshots in PostgreSQL.");
requireText(rustArchiveIntakeStoreSource, "bitween_hr.attendance_record", "Rust archive intake store must write admitted attendance rows into the canonical HR attendance table.");
requireText(rustArchiveIntakeStoreSource, "bitween_payroll.payroll_input", "Rust archive intake store must write admitted payroll rows into the canonical payroll input table.");
requireText(rustUserPreferenceStoreSource, "bitween.user-preferences.v1", "Rust user preference store must expose a stable schema for live settings.");
requireText(rustUserPreferenceStoreSource, "USER_PREFERENCE_STORE_SCHEMA", "Rust user preference store must use the exported settings response schema constant.");
requireText(rustUserPreferenceStoreSource, "DEFAULT_LOCALE: &str = \"ko-KR\"", "Rust user preference store must default to Korean-first locale.");
requireText(rustUserPreferenceStoreSource, "PostgreSQL relational user preference storage is required", "Rust user preference store must fail closed instead of silently writing local settings JSON.");
requireText(rustUserPreferenceStoreSource, "BITWEEN_ALLOW_LOCAL_REVIEW_STORE", "Rust user preference local file persistence must be explicit hermetic review mode only.");
requireText(rustUserPreferenceStoreSource, "BITWEEN_POSTGRES_DSN", "Rust user preference store must use PostgreSQL when a DSN is configured.");
requireText(rustUserPreferenceStoreSource, "connect_client_session", "Rust user preference store must connect through the live PostgreSQL client session.");
requireText(rustUserPreferenceStoreSource, "required_postgres_migrations", "Rust user preference store must apply required migrations before reads or writes.");
requireText(rustUserPreferenceStoreSource, "bitween_settings.user_preference", "Rust user preference store must read and write the PostgreSQL settings table.");
requireText(rustUserPreferenceStoreSource, "postgres_user_subject_required", "Rust user preference store must require an authenticated subject for PostgreSQL settings.");
requireText(rustUserPreferenceSchemaSource, "bitween.settings.postgres.v1", "Rust user preference schema module must expose a PostgreSQL contract version.");
requireText(rustUserPreferenceSchemaSource, "USER_PREFERENCE_STORE_SCHEMA", "Rust user preference schema module must export the live settings response schema constant.");
requireText(rustUserPreferenceSchemaSource, "004_user_preferences.sql", "Rust user preference schema module must include the PostgreSQL migration.");
requireText(userPreferencePostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_settings.user_preference", "User preference PostgreSQL migration must create the settings table.");
requireText(userPreferencePostgresMigrationSource, "locale text NOT NULL DEFAULT 'ko-KR'", "User preference PostgreSQL migration must default to Korean-first locale.");
requireText(userPreferencePostgresMigrationSource, "ALTER TABLE bitween_settings.user_preference ENABLE ROW LEVEL SECURITY", "User preference PostgreSQL migration must enable RLS.");
requireText(rustPayrollAttendanceSchemaSource, "bitween.payroll-attendance.postgres.v1", "Rust payroll/attendance schema module must expose a canonical PostgreSQL contract version.");
requireText(rustPayrollAttendanceSchemaSource, "005_payroll_attendance_intake.sql", "Rust payroll/attendance schema module must include the canonical admission migration.");
requireText(payrollAttendancePostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_hr.attendance_record", "Payroll/attendance PostgreSQL migration must create canonical attendance records.");
requireText(payrollAttendancePostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_payroll.payroll_input", "Payroll/attendance PostgreSQL migration must create canonical payroll inputs.");
requireText(payrollAttendancePostgresMigrationSource, "source_intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake", "Canonical payroll/attendance records must keep source intake lineage.");
requireText(payrollAttendancePostgresMigrationSource, "source_row_hash char(64) NOT NULL", "Canonical payroll/attendance records must keep source row hashes.");
requireText(payrollAttendancePostgresMigrationSource, "ALTER TABLE bitween_hr.attendance_record ENABLE ROW LEVEL SECURITY", "Canonical attendance table must enable RLS.");
requireText(payrollAttendancePostgresMigrationSource, "ALTER TABLE bitween_payroll.payroll_input ENABLE ROW LEVEL SECURITY", "Canonical payroll input table must enable RLS.");
requireText(payrollAttendancePostgresMigrationSource, "current_setting('bitween.legal_entity_id', true)", "Canonical payroll/attendance RLS must enforce legal-entity scope.");
requireText(payrollAttendancePostgresMigrationSource, "current_setting('bitween.workplace_id', true)", "Canonical payroll/attendance RLS must enforce workplace scope.");
requireText(rustArchiveIntakeSchemaSource, "bitween.archive.postgres.v1", "Rust archive intake schema module must expose a PostgreSQL contract version.");
requireText(rustArchiveIntakeSchemaSource, "ARCHIVE_INTAKE_STORE_SCHEMA", "Rust archive intake schema module must export the live response schema constant.");
requireText(rustArchiveIntakeSchemaSource, "ARCHIVE_SOURCE_SYNC_PLAN_SCHEMA", "Rust archive intake schema module must export the source-sync response schema constant.");
requireText(rustArchiveIntakeSchemaSource, "001_archive_intake.sql", "Rust archive intake schema module must include the PostgreSQL migration.");
requireText(rustArchiveRollbackSchemaSource, "bitween.archive-rollback.postgres.v1", "Rust archive rollback schema module must expose a PostgreSQL contract version.");
requireText(rustArchiveRollbackSchemaSource, "006_archive_admission_rollback.sql", "Rust archive rollback schema module must include the recovery/rollback migration.");
requireText(rustArchiveRollbackSchemaSource, "archive_admission_recovery_point", "Rust archive rollback schema module must declare row-level recovery points.");
requireText(rustArchiveRollbackSchemaSource, "archive_source_sync", "Rust archive rollback schema module must declare source workbook sync metadata.");
requireText(rustArchiveRollbackSchemaSource, '!sql.to_ascii_lowercase().contains("bytea")', "Rust archive rollback schema tests must guard against binary PostgreSQL snapshots.");
requireText(rustLibSource, "pub mod workflow_template_schema", "Rust payroll API must export the workflow template PostgreSQL schema module.");
requireText(rustLibSource, "pub mod user_preference_schema", "Rust payroll API must export the user preference PostgreSQL schema module.");
requireText(rustLibSource, "pub mod payroll_attendance_schema", "Rust payroll API must export the payroll/attendance canonical PostgreSQL schema module.");
requireText(rustLibSource, "pub mod archive_rollback_schema", "Rust payroll API must export the archive rollback/recovery PostgreSQL schema module.");
requireText(rustLibSource, "pub mod auth_session_schema", "Rust payroll API must export the auth-session PostgreSQL schema module.");
requireText(rustWorkflowTemplateSchemaSource, "bitween.workflow.postgres.v1", "Rust workflow template schema module must expose a PostgreSQL contract version.");
requireText(rustWorkflowTemplateSchemaSource, "002_workflow_templates.sql", "Rust workflow template schema module must include the PostgreSQL migration.");
requireText(rustWorkflowTemplateSchemaSource, "workflow_template_postgres_contract", "Rust workflow template schema module must expose a stable contract function.");
requireText(rustLibSource, "pub mod postgres_repository;", "Rust payroll API must export the PostgreSQL repository boundary module.");
requireText(rustLibSource, "PostgresRepositoryConfig", "Rust payroll API must export the PostgreSQL repository config contract.");
requireText(rustLibSource, "PostgresTlsPolicy", "Rust payroll API must export the PostgreSQL TLS policy contract.");
requireText(rustLibSource, "postgres_repository_status", "Rust payroll API must export PostgreSQL repository status without leaking secrets.");
requireText(rustPostgresRepositorySource, "PostgresRepositoryConfig", "Rust PostgreSQL repository boundary must own DSN/TLS configuration.");
requireText(rustPostgresRepositorySource, "PostgresTlsPolicy", "Rust PostgreSQL repository boundary must model allowed TLS policies.");
requireText(rustPostgresRepositorySource, "postgres_no_tls_rejected", "Rust PostgreSQL repository boundary must reject production NoTls.");
requireText(rustPostgresRepositorySource, "postgres://<redacted>", "Rust PostgreSQL repository boundary must redact DSNs before status/log exposure.");
requireText(rustPostgresRepositorySource, "implicit_migrations_allowed: bool", "Rust PostgreSQL repository boundary must make implicit migrations an explicit false policy.");
requireText(rustPostgresRepositorySource, "tenant_session_setting_sql", "Rust PostgreSQL repository boundary must expose tenant session-setting SQL for RLS.");
requireText(rustPostgresRepositorySource, "SELECT set_config('bitween.tenant_id', $1, false)", "Rust PostgreSQL repository boundary must parameterize tenant session settings at session scope for RLS.");
requireText(rustPostgresRepositorySource, "tenant_session_setting_batch_sql", "Rust PostgreSQL repository boundary must expose executable tenant session-setting SQL.");
requireText(rustPostgresRepositorySource, "PostgresTenantScope", "Rust PostgreSQL repository boundary must model tenant/legal-entity/workplace scope.");
requireText(rustPostgresRepositorySource, "postgres_scope_required", "Rust PostgreSQL repository boundary must reject blank tenant scope values.");
requireText(rustPostgresRepositorySource, "PostgresClientSession", "Rust PostgreSQL repository boundary must expose a live client session type.");
requireText(rustPostgresRepositorySource, "PostgresConnectionFailure", "Rust PostgreSQL repository boundary must expose sanitized connection failures.");
requireText(rustPostgresRepositorySource, "PostgresMigration", "Rust PostgreSQL repository boundary must model controlled schema migrations.");
requireText(rustPostgresRepositorySource, "PostgresMigrationReceipt", "Rust PostgreSQL repository boundary must return auditable migration receipts.");
requireText(rustPostgresRepositorySource, "PostgresMigrationStatus", "Rust PostgreSQL repository boundary must distinguish applied and already-applied migrations.");
requireText(rustPostgresRepositorySource, "required_postgres_migrations", "Rust PostgreSQL repository boundary must enumerate required production migrations.");
requireText(rustPostgresRepositorySource, "ARCHIVE_INTAKE_POSTGRES_MIGRATION_SQL", "Rust PostgreSQL migration runner must include archive intake migration SQL.");
requireText(rustPostgresRepositorySource, "WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_SQL", "Rust PostgreSQL migration runner must include workflow template migration SQL.");
requireText(rustPostgresRepositorySource, "PAYROLL_ATTENDANCE_POSTGRES_MIGRATION_SQL", "Rust PostgreSQL migration runner must include canonical payroll/attendance migration SQL.");
requireText(rustPostgresRepositorySource, "ARCHIVE_ROLLBACK_POSTGRES_MIGRATION_SQL", "Rust PostgreSQL migration runner must include archive recovery/rollback migration SQL.");
requireText(rustPostgresRepositorySource, "AUTH_SESSION_POSTGRES_MIGRATION_SQL", "Rust PostgreSQL migration runner must include auth-session revocation/audit migration SQL.");
requireText(rustPostgresRepositorySource, "required_postgres_migrations() -> [PostgresMigration; 7]", "Rust PostgreSQL migration runner must include all seven required production migrations.");
requireText(rustPostgresRepositorySource, "postgres_migration_registry_sql", "Rust PostgreSQL migration runner must create an idempotent migration registry.");
requireText(rustPostgresRepositorySource, "schema_migration", "Rust PostgreSQL migration runner must persist migration registry rows.");
requireText(rustPostgresRepositorySource, "checksum_sha256", "Rust PostgreSQL migration runner must record SHA-256 migration checksums.");
requireText(rustPostgresRepositorySource, "Sha256::digest", "Rust PostgreSQL migration runner must compute SHA-256 checksums in Rust.");
requireText(rustPostgresRepositorySource, "apply_required_migrations", "Rust PostgreSQL client session must expose migration application.");
requireText(rustPostgresRepositorySource, "postgres_migration_checksum_mismatch", "Rust PostgreSQL migration runner must fail closed on checksum drift.");
requireText(rustPostgresRepositorySource, "postgres_migration_apply_failed", "Rust PostgreSQL migration runner must return sanitized migration apply failures.");
requireText(rustPostgresRepositorySource, "postgres_migration_record_failed", "Rust PostgreSQL migration runner must return sanitized registry record failures.");
requireText(rustPostgresRepositorySource, "PostgresDriverConfig", "Rust PostgreSQL repository boundary must expose driver validation metadata.");
requireText(rustPostgresRepositorySource, "validate_driver_config", "Rust PostgreSQL repository boundary must validate DSNs through the selected driver.");
requireText(rustPostgresRepositorySource, ".parse::<tokio_postgres::Config>()", "Rust PostgreSQL repository boundary must validate DSNs with tokio-postgres without connecting.");
requireText(rustPostgresRepositorySource, 'driver_crate: "tokio-postgres"', "Rust PostgreSQL repository boundary must identify the selected driver crate.");
requireText(rustPostgresRepositorySource, 'required_tls_connector_crate: "tokio-postgres-rustls"', "Rust PostgreSQL repository boundary must keep the required TLS connector explicit.");
requireText(rustPostgresRepositorySource, "PostgresTlsConnectorProfile", "Rust PostgreSQL repository boundary must expose TLS connector profile metadata.");
requireText(rustPostgresRepositorySource, "build_tls_connector", "Rust PostgreSQL repository boundary must construct the production TLS connector without network side effects.");
requireText(rustPostgresRepositorySource, "tokio_postgres_rustls::MakeRustlsConnect::new", "Rust PostgreSQL repository boundary must use tokio-postgres-rustls for TLS connection construction.");
requireText(rustPostgresRepositorySource, "rustls::ClientConfig::builder()", "Rust PostgreSQL repository boundary must construct a rustls client config.");
requireText(rustPostgresRepositorySource, "webpki_roots::TLS_SERVER_ROOTS", "Rust PostgreSQL repository boundary must load webpki root anchors.");
requireText(rustPostgresRepositorySource, "postgres_tls_connector_requires_verify_full", "Rust PostgreSQL repository boundary must reject TLS connector construction unless verify-full is active.");
requireText(rustPostgresRepositorySource, 'crypto_provider: "ring"', "Rust PostgreSQL repository boundary must record the selected rustls crypto provider.");
requireText(rustPostgresRepositorySource, 'root_store: "webpki-roots"', "Rust PostgreSQL repository boundary must record the selected root store.");
requireText(rustPostgresRepositorySource, "permits_no_tls: false", "Rust PostgreSQL repository boundary must record that production TLS connector does not permit no-TLS.");
requireText(rustPostgresRepositorySource, "connect_client_session", "Rust PostgreSQL repository boundary must provide a real tokio-postgres connection/session entrypoint.");
requireText(rustPostgresRepositorySource, "tokio_postgres::connect", "Rust PostgreSQL repository boundary must use the selected PostgreSQL driver for live connections.");
requireText(rustPostgresRepositorySource, "tokio::spawn", "Rust PostgreSQL repository boundary must drive the tokio-postgres connection future.");
requireText(rustPostgresRepositorySource, "postgres_connect_failed", "Rust PostgreSQL repository boundary must map connection errors to sanitized stable codes.");
requireText(rustPostgresRepositorySource, "postgres_tenant_session_failed", "Rust PostgreSQL repository boundary must map tenant session failures to sanitized stable codes.");
requireText(rustPostgresRepositorySource, "postgres_connection_task_failed", "Rust PostgreSQL repository boundary must map background connection task failures without logging DSNs.");
rejectText(rustPostgresRepositorySource, "NoTls", "Rust PostgreSQL repository boundary must not encode a production NoTls path.");
requireText(rustAuthSessionSource, "AUTH_SESSION_SCHEMA", "Rust auth session verifier must expose a stable session verification schema.");
requireText(rustAuthSessionSource, "AUTH_OIDC_DISCOVERY_SCHEMA", "Rust auth session verifier must expose a stable OIDC discovery metadata schema.");
requireText(rustAuthSessionSource, "OidcDiscoveryVerifierConfig", "Rust auth session verifier must model expected OIDC discovery metadata.");
requireText(rustAuthSessionSource, "validate_oidc_discovery", "Rust auth session verifier must validate OIDC discovery metadata before trusting provider config.");
requireText(rustAuthSessionSource, "oidc_issuer_mismatch", "Rust OIDC discovery validator must fail closed on issuer mismatch.");
requireText(rustAuthSessionSource, "oidc_jwks_uri_untrusted", "Rust OIDC discovery validator must require an HTTPS JWKS URI.");
requireText(rustAuthSessionSource, "oidc_rs256_unsupported", "Rust OIDC discovery validator must require RS256 signing algorithm support.");
requireText(rustAuthSessionSource, "AUTH_SESSION_ALLOWED_ALGORITHM", "Rust auth session verifier must keep explicit JWT algorithm allow-listing.");
requireText(rustAuthSessionSource, "RsaPublicKeyComponents", "Rust auth session verifier must verify RS256 JWT signatures against JWKS RSA key material.");
requireText(rustAuthSessionSource, "jwt_alg_untrusted", "Rust auth session verifier must reject untrusted JWT algorithms.");
requireText(rustAuthSessionSource, "jwt_signature_invalid", "Rust auth session verifier must reject invalid JWT signatures.");
requireText(rustAuthSessionSource, "jwt_audience_mismatch", "Rust auth session verifier must enforce expected JWT audience.");
requireText(rustAuthSessionSource, "webauthn_user_verification_missing", "Rust auth session verifier must require WebAuthn/passkey user verification evidence.");
requireText(rustAuthSessionSource, "AUTH_WEBAUTHN_ASSERTION_SCHEMA", "Rust auth session verifier must expose a stable WebAuthn assertion verification schema.");
requireText(rustAuthSessionSource, "WebAuthnAssertionVerifierConfig", "Rust auth session verifier must model WebAuthn relying-party assertion configuration.");
requireText(rustAuthSessionSource, "verify_webauthn_assertion", "Rust auth session verifier must validate WebAuthn/passkey assertions server-side.");
requireText(rustAuthSessionSource, "webauthn_challenge_mismatch", "Rust WebAuthn verifier must fail closed on challenge mismatch.");
requireText(rustAuthSessionSource, "webauthn_origin_mismatch", "Rust WebAuthn verifier must fail closed on origin mismatch.");
requireText(rustAuthSessionSource, "webauthn_rp_id_hash_mismatch", "Rust WebAuthn verifier must bind assertions to the configured RP ID.");
requireText(rustAuthSessionSource, "webauthn_user_not_verified", "Rust WebAuthn verifier must require the UV flag.");
requireText(rustAuthSessionSource, "webauthn_sign_count_replayed", "Rust WebAuthn verifier must reject replayed nonzero signature counters.");
requireText(rustAuthSessionSource, "ECDSA_P256_SHA256_ASN1", "Rust WebAuthn verifier must verify ES256 authenticator signatures.");
requireText(rustAuthSessionSource, "jwt_id_sha256", "Rust auth session verifier must hash JWT IDs instead of echoing replay identifiers.");
requireText(rustAuthSessionBinSource, "BITWEEN_SESSION_JWT", "Rust auth session validator binary must read the JWT from a server-side environment boundary.");
requireText(rustAuthSessionBinSource, "BITWEEN_AUTH_JWKS_JSON", "Rust auth session validator binary must read JWKS JSON from server-side configuration.");
requireText(rustAuthSessionBinSource, "BITWEEN_AUTH_OIDC_CONFIGURATION_JSON", "Rust auth session validator binary must validate OIDC discovery metadata when configured.");
requireText(rustAuthSessionBinSource, "BITWEEN_AUTH_EXPECTED_JWKS_URI", "Rust auth session validator binary must support expected JWKS URI pinning.");
requireText(rustAuthSessionBinSource, "enforce_oidc_discovery_if_configured", "Rust auth session validator binary must fail closed on invalid OIDC discovery metadata.");
requireText(rustAuthSessionBinSource, "BITWEEN_WEBAUTHN_ASSERTION_JSON", "Rust auth session validator binary must support server-side WebAuthn assertion verification when assertion evidence is supplied.");
requireText(rustAuthSessionBinSource, "enforce_webauthn_assertion_if_configured", "Rust auth session validator binary must fail closed on invalid WebAuthn assertion evidence.");
requireText(rustAuthSessionBinSource, "BITWEEN_AUTH_SESSION_SECURITY_MODE", "Rust auth session validator binary must support explicit PostgreSQL revocation/audit mode.");
requireText(rustAuthSessionBinSource, "auth_session_security_store_required", "Rust auth session validator binary must fail closed when PostgreSQL security mode lacks a DSN.");
requireText(rustAuthSessionBinSource, "auth_session_security_store_unavailable", "Rust auth session validator binary must fail closed when PostgreSQL security store is unavailable.");
requireText(rustAuthSessionBinSource, "jwt_revoked", "Rust auth session validator binary must deny hashed JWT IDs found in the revocation table.");
requireText(rustAuthSessionBinSource, "auth_session_event_audit_failed", "Rust auth session validator binary must fail closed when session event audit cannot be written.");
requireText(rustAuthSessionBinSource, "hex_sha256(&verification.subject)", "Rust auth session validator binary must hash subjects before audit storage.");
requireText(rustAuthSessionBinSource, "auth_session_revocation_lookup_sql", "Rust auth session validator binary must use the shared parameterized revocation lookup contract.");
requireText(rustAuthSessionBinSource, "auth_session_event_insert_sql", "Rust auth session validator binary must use the shared parameterized audit insert contract.");
requireText(rustAuthSessionBinSource, "std::process::exit(2)", "Rust auth session validator binary must exit non-zero when verification fails.");
requireText(rustAuthSessionSchemaSource, "AUTH_SESSION_POSTGRES_SCHEMA_VERSION", "Rust auth session PostgreSQL schema module must expose a stable schema version.");
requireText(rustAuthSessionSchemaSource, "007_auth_session_security.sql", "Rust auth session PostgreSQL schema module must include the controlled migration.");
requireText(rustAuthSessionSchemaSource, "bitween_auth.jwt_revocation", "Rust auth session PostgreSQL schema module must declare the JWT revocation table.");
requireText(rustAuthSessionSchemaSource, "bitween_auth.session_event_audit", "Rust auth session PostgreSQL schema module must declare the session event audit table.");
requireText(rustAuthSessionSchemaSource, "auth_session_revocation_lookup_sql", "Rust auth session PostgreSQL schema module must expose parameterized revocation lookup SQL.");
requireText(rustAuthSessionSchemaSource, "auth_session_event_insert_sql", "Rust auth session PostgreSQL schema module must expose parameterized audit insert SQL.");
requireText(rustAuthSessionSchemaSource, '!AUTH_SESSION_POSTGRES_MIGRATION_SQL.to_ascii_lowercase().contains("raw_token")', "Rust auth session schema tests must guard against raw-token storage.");
requireText(authSessionPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_auth.jwt_revocation", "Auth session PostgreSQL migration must create a hashed JWT revocation table.");
requireText(authSessionPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_auth.session_event_audit", "Auth session PostgreSQL migration must create a session verification audit table.");
requireText(authSessionPostgresMigrationSource, "jwt_id_sha256 char(64)", "Auth session PostgreSQL migration must persist hashed JWT IDs only.");
requireText(authSessionPostgresMigrationSource, "subject_sha256 char(64)", "Auth session PostgreSQL migration must persist hashed subject IDs only.");
requireText(authSessionPostgresMigrationSource, "ALTER TABLE bitween_auth.jwt_revocation ENABLE ROW LEVEL SECURITY", "Auth session PostgreSQL migration must enforce tenant RLS on revocations.");
requireText(authSessionPostgresMigrationSource, "ALTER TABLE bitween_auth.session_event_audit ENABLE ROW LEVEL SECURITY", "Auth session PostgreSQL migration must enforce tenant RLS on audit rows.");
requireText(authSessionPostgresMigrationSource, "current_setting('bitween.tenant_id', true)", "Auth session PostgreSQL migration must isolate rows using tenant session settings.");
rejectText(authSessionPostgresMigrationSource.toLowerCase(), "raw_token", "Auth session PostgreSQL migration must never store raw tokens.");
rejectText(authSessionPostgresMigrationSource.toLowerCase(), "access_token", "Auth session PostgreSQL migration must never store access tokens.");
requireText(rustLibSource, "PostgresClientSession", "Rust payroll API must export the PostgreSQL client session type.");
requireText(rustLibSource, "validate_oidc_discovery", "Rust payroll API must export the OIDC discovery validation contract.");
requireText(rustLibSource, "PostgresConnectionFailure", "Rust payroll API must export sanitized PostgreSQL connection failures.");
requireText(rustLibSource, "PostgresMigration", "Rust payroll API must export PostgreSQL migration descriptors.");
requireText(rustLibSource, "PostgresMigrationReceipt", "Rust payroll API must export PostgreSQL migration receipts.");
requireText(rustLibSource, "PostgresMigrationStatus", "Rust payroll API must export PostgreSQL migration statuses.");
requireText(rustLibSource, "required_postgres_migrations", "Rust payroll API must export required PostgreSQL migration enumeration.");
requireText(rustLibSource, "PostgresTenantScope", "Rust payroll API must export the PostgreSQL tenant scope type.");
requireText(rustLibSource, "PostgresTlsConnector", "Rust payroll API must export the PostgreSQL TLS connector type.");
requireText(rustLibSource, "PostgresTlsConnectorProfile", "Rust payroll API must export the PostgreSQL TLS connector profile.");
requireText(payrollCargoTomlSource, 'rustls = { version = "0.23"', "crates/payroll-api/Cargo.toml must declare rustls for production PostgreSQL TLS.");
requireText(payrollCargoTomlSource, 'sha2 = "0.11"', "crates/payroll-api/Cargo.toml must declare sha2 for migration checksums.");
requireText(payrollCargoTomlSource, 'tokio = { version = "1"', "crates/payroll-api/Cargo.toml must declare tokio for the live PostgreSQL connection session.");
requireText(payrollCargoTomlSource, 'tokio-postgres = "0.7"', "crates/payroll-api/Cargo.toml must declare the selected tokio-postgres dependency.");
requireText(payrollCargoTomlSource, 'tokio-postgres-rustls = { version = "0.14"', "crates/payroll-api/Cargo.toml must declare the tokio-postgres-rustls TLS connector.");
requireText(payrollCargoTomlSource, 'webpki-roots = "1"', "crates/payroll-api/Cargo.toml must declare webpki root anchors for rustls.");
requireText(rootCargoLockSource, 'name = "ring"', "Cargo.lock must lock the selected ring crypto provider.");
requireText(rootCargoLockSource, 'name = "rustls"', "Cargo.lock must lock the selected rustls dependency.");
requireText(rootCargoLockSource, 'name = "sha2"', "Cargo.lock must lock sha2 for migration checksums.");
requireText(rootCargoLockSource, 'name = "tokio"', "Cargo.lock must lock tokio for the live PostgreSQL connection session.");
requireText(rootCargoLockSource, 'name = "tokio-postgres"', "Cargo.lock must lock the selected tokio-postgres dependency.");
requireText(rootCargoLockSource, 'name = "tokio-postgres-rustls"', "Cargo.lock must lock the selected tokio-postgres-rustls dependency.");
requireText(rootCargoLockSource, 'name = "webpki-roots"', "Cargo.lock must lock the selected webpki-roots dependency.");
requireText(payrollBuckSource, "//third-party/rust:rustls", "crates/payroll-api/BUCK must depend on the Reindeer-generated rustls target.");
requireText(payrollBuckSource, "//third-party/rust:sha2", "crates/payroll-api/BUCK must depend on the Reindeer-generated sha2 target.");
requireText(payrollBuckSource, "//third-party/rust:tokio", "crates/payroll-api/BUCK must depend on the Reindeer-generated tokio target.");
requireText(payrollBuckSource, "//third-party/rust:tokio-postgres", "crates/payroll-api/BUCK must depend on the Reindeer-generated tokio-postgres target.");
requireText(payrollBuckSource, "//third-party/rust:tokio-postgres-rustls", "crates/payroll-api/BUCK must depend on the Reindeer-generated tokio-postgres-rustls target.");
requireText(payrollBuckSource, "//third-party/rust:webpki-roots", "crates/payroll-api/BUCK must depend on the Reindeer-generated webpki-roots target.");
requireText(payrollBuckSource, "src/auth_session_schema.rs", "crates/payroll-api/BUCK must include the auth-session PostgreSQL schema module.");
requireText(payrollBuckSource, "migrations/007_auth_session_security.sql", "crates/payroll-api/BUCK must include the auth-session revocation/audit migration.");
requireText(payrollBuckSource, 'name = "auth_session_validate"', "crates/payroll-api/BUCK must build the Rust auth session validator.");
requireText(payrollBuckSource, 'name = "auth_session_validate_test"', "crates/payroll-api/BUCK must test the Rust auth session validator.");
requireText(thirdPartyRustBuckSource, 'package_name = "ring"', "third-party/rust/BUCK must include ring build-script package metadata.");
requireText(thirdPartyRustBuckSource, 'name = "rustls"', "third-party/rust/BUCK must expose a public rustls alias.");
requireText(thirdPartyRustBuckSource, 'name = "sha2"', "third-party/rust/BUCK must expose a public sha2 alias.");
requireText(thirdPartyRustBuckSource, 'name = "tokio"', "third-party/rust/BUCK must expose a public tokio alias.");
requireText(thirdPartyRustBuckSource, 'name = "tokio-postgres"', "third-party/rust/BUCK must expose a public tokio-postgres alias.");
requireText(thirdPartyRustBuckSource, 'name = "tokio-postgres-rustls"', "third-party/rust/BUCK must expose a public tokio-postgres-rustls alias.");
requireText(thirdPartyRustBuckSource, 'name = "webpki-roots"', "third-party/rust/BUCK must expose a public webpki-roots alias.");
requireText(thirdPartyRustBuckSource, 'name = "ring-0.17"', "third-party/rust/BUCK must generate the locked ring rule.");
requireText(thirdPartyRustBuckSource, 'name = "rustls-0.23"', "third-party/rust/BUCK must generate the locked rustls rule.");
requireText(thirdPartyRustBuckSource, 'name = "sha2-0.11"', "third-party/rust/BUCK must generate the locked sha2 rule.");
requireText(thirdPartyRustBuckSource, 'name = "tokio-1"', "third-party/rust/BUCK must generate the locked tokio rule.");
requireText(thirdPartyRustBuckSource, 'name = "tokio-postgres-0.7"', "third-party/rust/BUCK must generate the locked tokio-postgres rule.");
requireText(thirdPartyRustBuckSource, 'name = "tokio-postgres-rustls-0.14"', "third-party/rust/BUCK must generate the locked tokio-postgres-rustls rule.");
requireText(thirdPartyRustBuckSource, 'name = "webpki-roots-1"', "third-party/rust/BUCK must generate the locked webpki-roots rule.");
requireText(thirdPartyRustBuckSource, "vendor/ring-0.17.", "third-party/rust/BUCK must build ring from vendored sources.");
requireText(thirdPartyRustBuckSource, "vendor/rustls-0.23.", "third-party/rust/BUCK must build rustls from vendored sources.");
requireText(thirdPartyRustBuckSource, "vendor/sha2-0.11.", "third-party/rust/BUCK must build sha2 from vendored sources.");
requireText(thirdPartyRustBuckSource, "vendor/tokio-1.", "third-party/rust/BUCK must build tokio from vendored sources.");
requireText(thirdPartyRustBuckSource, "vendor/tokio-postgres-0.7.", "third-party/rust/BUCK must build tokio-postgres from vendored sources.");
requireText(thirdPartyRustBuckSource, "vendor/tokio-postgres-rustls-0.14.", "third-party/rust/BUCK must build tokio-postgres-rustls from vendored sources.");
requireText(thirdPartyRustBuckSource, "vendor/webpki-roots-1.", "third-party/rust/BUCK must build webpki-roots from vendored sources.");
requireText(thirdPartyRustBuckSource, 'name = "ring-0.17-build-script-run"', "third-party/rust/BUCK must run ring's build script for native crypto objects.");
requireText(thirdPartyRustBuckSource, "rustc_link_lib = True", "third-party/rust/BUCK must preserve ring build-script native link libraries.");
requireText(thirdPartyRustBuckSource, "rustc_link_search = True", "third-party/rust/BUCK must preserve ring build-script native link search paths.");
requireText(getrandomFixupSource, "buildscript.run = true", "getrandom Reindeer fixup must run the build script for hermetic Buck metadata.");
requireText(getrandomFixupSource, 'extra_srcs = ["README.md"]', "getrandom Reindeer fixup must include README.md used by the crate source.");
requireText(libcFixupSource, "buildscript.run = true", "libc Reindeer fixup must run the build script for hermetic Buck metadata.");
requireText(parkingLotCoreFixupSource, "buildscript.run = true", "parking_lot_core Reindeer fixup must run the build script for hermetic Buck metadata.");
requireText(mioFixupSource, "precise_srcs = false", "mio Reindeer fixup must include cfg-gated platform sources.");
requireText(tokioFixupSource, "precise_srcs = false", "tokio Reindeer fixup must include cfg-gated runtime/platform sources.");
requireText(tokioUtilFixupSource, "precise_srcs = false", "tokio-util Reindeer fixup must include cfg-gated codec/tracing sources.");
requireText(rustlsFixupSource, "buildscript.run = true", "rustls Reindeer fixup must run the build script for hermetic cfg metadata.");
requireText(rustlsFixupSource, "precise_srcs = false", "rustls Reindeer fixup must include cfg-gated source trees.");
requireText(ringFixupSource, "[buildscript.run]", "ring Reindeer fixup must run the native crypto build script under Buck.");
requireText(ringFixupSource, "rustc_link_lib = true", "ring Reindeer fixup must preserve native link libraries emitted by the build script.");
requireText(ringFixupSource, "rustc_link_search = true", "ring Reindeer fixup must preserve native link search paths emitted by the build script.");
requireText(ringFixupSource, 'CARGO_MANIFEST_LINKS = "ring_core_0_17_14_"', "ring Reindeer fixup must provide Cargo links metadata expected by ring.");
requireText(ringFixupSource, 'CC_aarch64_apple_darwin = "/usr/bin/clang"', "ring Reindeer fixup must pin the Apple clang path used by the hermetic Buck build-script action.");
requireText(
  postgresProtocolPasswordSource,
  "backend compatibility",
  "postgres-protocol vendor SASLprep fallback comment must carry explicit upstream compatibility rationale.",
);
requireText(
  tokioUnixPipeSource,
  "Compatibility rationale: upstream Tokio exposes this expert-mode option",
  "tokio FIFO-check skip option must carry explicit upstream compatibility rationale.",
);
requireText(
  wasmEncoderReencodeSource,
  "parsing because code section entries are already handled",
  "wasm-encoder payload skip comment must carry explicit design rationale.",
);
requireText(archivePostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_archive.archive_intake", "PostgreSQL migration must create archive intake metadata table.");
requireText(archivePostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_archive.hr_employee_staging", "PostgreSQL migration must create HR staging table.");
requireText(archivePostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_archive.payroll_input_staging", "PostgreSQL migration must create payroll staging table.");
requireText(archivePostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_archive.archive_admission_audit", "PostgreSQL migration must create canonical admission audit evidence.");
requireText(archivePostgresMigrationSource, "object_uri text NOT NULL CHECK (object_uri LIKE 'rustfs://%')", "PostgreSQL migration must enforce RustFS object URIs.");
requireText(archivePostgresMigrationSource, "content_sha256 char(64) NOT NULL", "PostgreSQL migration must persist object checksums.");
requireText(archivePostgresMigrationSource, "content_sample_sha256 char(64) NOT NULL", "PostgreSQL migration must persist a content-sample checksum for extraction evidence.");
requireText(archivePostgresMigrationSource, "content_sample_row_count bigint NOT NULL DEFAULT 0", "PostgreSQL migration must persist bounded sample row counts for intake review.");
requireText(archivePostgresMigrationSource, "redacted_content_sample_excerpt text NOT NULL DEFAULT ''", "PostgreSQL migration must persist only redacted bounded content samples, not raw file snapshots.");
requireText(archivePostgresMigrationSource, "char_length(redacted_content_sample_excerpt) <= 8192", "PostgreSQL content sample excerpts must be bounded.");
requireText(archivePostgresMigrationSource, "extraction_status text NOT NULL DEFAULT 'not_readable'", "PostgreSQL migration must persist sample extraction status.");
requireText(archivePostgresMigrationSource, "ENABLE ROW LEVEL SECURITY", "PostgreSQL migration must enable tenant row-level security.");
requireText(archiveRollbackPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_archive.archive_admission_recovery_point", "PostgreSQL rollback migration must create row-level recovery points instead of binary snapshots.");
requireText(archiveRollbackPostgresMigrationSource, "before_payload jsonb NOT NULL DEFAULT '{}'::jsonb", "PostgreSQL rollback migration must preserve previous row state as JSON metadata.");
requireText(archiveRollbackPostgresMigrationSource, "after_payload jsonb NOT NULL", "PostgreSQL rollback migration must preserve admitted row state as JSON metadata.");
requireText(archiveRollbackPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_archive.archive_source_sync", "PostgreSQL rollback migration must create source workbook sync metadata.");
requireText(archiveRollbackPostgresMigrationSource, "source_object_uri text NOT NULL CHECK (source_object_uri LIKE 'rustfs://%')", "PostgreSQL rollback migration must link back to immutable RustFS source objects.");
requireText(archiveRollbackPostgresMigrationSource, "generated_object_uri text CHECK", "PostgreSQL rollback migration must reference derived RustFS workbook versions without storing binaries.");
requireText(archiveRollbackPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_archive.archive_admission_rollback", "PostgreSQL rollback migration must create rollback audit evidence.");
requireText(archiveRollbackPostgresMigrationSource, "ALTER TABLE bitween_archive.archive_admission_recovery_point ENABLE ROW LEVEL SECURITY", "PostgreSQL recovery points must enforce tenant RLS.");
requireText(archiveRollbackPostgresMigrationSource, "ALTER TABLE bitween_archive.archive_source_sync ENABLE ROW LEVEL SECURITY", "PostgreSQL source-sync metadata must enforce tenant RLS.");
rejectText(archiveRollbackPostgresMigrationSource.toLowerCase(), "bytea", "PostgreSQL rollback migration must not store binary snapshots.");
requireText(workflowPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_template", "PostgreSQL workflow migration must create workflow template metadata.");
requireText(workflowPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_template_version", "PostgreSQL workflow migration must version workflow graph publications.");
requireText(workflowPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_node", "PostgreSQL workflow migration must create editable workflow graph nodes.");
requireText(workflowPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_edge", "PostgreSQL workflow migration must create editable workflow graph edges.");
requireText(workflowPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_publish_check", "PostgreSQL workflow migration must gate publish readiness.");
requireText(workflowPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_audit_event", "PostgreSQL workflow migration must persist workflow audit events.");
requireText(workflowPostgresMigrationSource, "CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_runtime_instance", "PostgreSQL workflow migration must persist runtime workflow instances.");
requireText(workflowPostgresMigrationSource, "ENABLE ROW LEVEL SECURITY", "PostgreSQL workflow migration must enable tenant row-level security.");
requireText(workflowPostgresMigrationSource, "current_setting('bitween.tenant_id', true)", "PostgreSQL workflow migration must enforce tenant isolation using session tenant settings.");
requireText(workflowPostgresMigrationSource, "slo_minutes integer", "PostgreSQL workflow migration must model SLO timers.");
requireText(workflowPostgresMigrationSource, "escalation_role text", "PostgreSQL workflow migration must model escalation ownership.");
requireText(workflowPostgresMigrationSource, "condition_expression jsonb", "PostgreSQL workflow migration must model editable branch conditions.");
requireText(workflowPostgresMigrationSource, "permission_scope jsonb", "PostgreSQL workflow migration must model workflow access scope metadata.");
requireText(rustWorkflowTemplateStoreSource, "slo_minutes: Option<u16>", "Rust workflow template store must persist optional SLO timers.");
requireText(rustWorkflowTemplateStoreSource, "escalation_role: Option<String>", "Rust workflow template store must persist optional escalation roles.");
requireText(rustWorkflowTemplateStoreSource, "condition_expression: BTreeMap<String, String>", "Rust workflow template store must persist branch condition metadata.");
requireText(rustWorkflowTemplateStoreSource, "permission_scope: BTreeMap<String, String>", "Rust workflow template store must persist permission scope metadata.");
requireText(rustWorkflowTemplateStoreSource, "missing_slo", "Rust workflow analytics must flag workflow steps missing SLO controls.");
requireText(rustWorkflowTemplateStoreSource, "missing_permission_scope", "Rust workflow analytics must flag workflow steps missing permission scope controls.");
rejectText(rustPlatformViewSource, "services.payroll", "Rust platform live view must not reference Python services.");
rejectText(rustArchiveIntakeStoreSource, retiredObjectStoreName, "Rust archive intake store must use RustFS naming, not the retired object-store candidate.");
rejectText(rustArchiveIntakeStoreSource.toLowerCase(), "min" + "io://", "Rust archive intake store tests must not use retired object-store URIs.");
rejectText(rustUserPreferenceStoreSource, retiredObjectStoreName, "Rust user preference store must not use retired object-store naming.");
rejectText(archivePostgresMigrationSource, retiredObjectStoreName, "PostgreSQL archive migration must not use the retired object-store candidate.");
rejectText(workflowPostgresMigrationSource, retiredObjectStoreName, "PostgreSQL workflow migration must not use the retired object-store candidate.");
rejectText(userPreferencePostgresMigrationSource, retiredObjectStoreName, "PostgreSQL user preference migration must not use the retired object-store candidate.");
rejectText(payrollAttendancePostgresMigrationSource, retiredObjectStoreName, "PostgreSQL payroll/attendance migration must not use the retired object-store candidate.");
rejectText(archiveRollbackPostgresMigrationSource, retiredObjectStoreName, "PostgreSQL rollback/source-sync migration must not use the retired object-store candidate.");
rejectText(authSessionPostgresMigrationSource, retiredObjectStoreName, "PostgreSQL auth-session migration must not use the retired object-store candidate.");
rejectText(rustHrEmployeeStoreSource, 'PathBuf::from("hr/employees.json")', "Rust HR employee store must not silently default to local JSON persistence.");
rejectText(rustArchiveIntakeStoreSource, 'PathBuf::from("archive/intake.json")', "Rust archive intake store must not silently default to local JSON persistence.");
requireText(rustArchiveIntakeStoreSource, "insert_postgres_staging_rows", "Rust archive intake store must translate ready HR/payroll/archive samples into PostgreSQL staging rows, not only metadata.");
requireText(rustArchiveIntakeStoreSource, "bitween_archive.hr_employee_staging", "Rust archive intake store must write HR employee staging rows when mapping is ready.");
requireText(rustArchiveIntakeStoreSource, "bitween_archive.hr_attendance_staging", "Rust archive intake store must write HR attendance staging rows when mapping is ready.");
requireText(rustArchiveIntakeStoreSource, "bitween_archive.payroll_input_staging", "Rust archive intake store must write payroll input staging rows when mapping is ready.");
requireText(rustArchiveIntakeStoreSource, "staged_rows_for_record", "Rust archive intake store must keep sample-to-staging translation unit tested.");
requireText(rustAuthPolicySource, "ArchiveReview", "Rust authorization policy must include 자료함 review as a distinct sensitive operation.");
requireText(rustAuthPolicySource, "ArchiveAdmit", "Rust authorization policy must include 자료함 canonical admission as a distinct manager-gated sensitive operation.");
requireText(rustAuthPolicySource, "ArchiveRollback", "Rust authorization policy must include 자료함 rollback/recovery as a distinct manager-gated sensitive operation.");
requireText(rustAuthPolicySource, "ArchiveSync", "Rust authorization policy must include source-file synchronization as a distinct manager-gated sensitive operation.");
requireText(authSecurityContractSource, "archive_review", "Auth/security docs must record the 자료함 review authorization operation.");
requireText(authSecurityContractSource, "archive_admit", "Auth/security docs must record the 자료함 canonical admission authorization operation.");
requireText(authSecurityContractSource, "archive_rollback", "Auth/security docs must record the 자료함 rollback authorization operation.");
requireText(authSecurityContractSource, "archive_sync", "Auth/security docs must record the source-file synchronization authorization operation.");

requireText(authSecurityContractSource, "https://datatracker.ietf.org/doc/html/rfc7519", "docs/AUTH_SECURITY_CONTRACT.md must cite the JWT RFC.");
requireText(authSecurityContractSource, "https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html", "docs/AUTH_SECURITY_CONTRACT.md must cite OWASP JWT guidance.");
requireText(authSecurityContractSource, "https://www.w3.org/TR/webauthn-3/", "docs/AUTH_SECURITY_CONTRACT.md must cite W3C WebAuthn.");
requireText(authSecurityContractSource, "https://fidoalliance.org/passkeys/", "docs/AUTH_SECURITY_CONTRACT.md must cite FIDO passkey guidance.");
requireText(authSecurityContractSource, "https://pages.nist.gov/800-63-4/sp800-63b.html", "docs/AUTH_SECURITY_CONTRACT.md must cite NIST authentication guidance.");
requireText(authSecurityContractSource, "https://csrc.nist.gov/pubs/sp/800/162/upd2/final", "docs/AUTH_SECURITY_CONTRACT.md must cite NIST ABAC guidance.");
requireText(authSecurityContractSource, "https://csrc.nist.gov/projects/role-based-access-control", "docs/AUTH_SECURITY_CONTRACT.md must cite NIST RBAC guidance.");
requireText(authSecurityContractSource, "https://csrc.nist.gov/glossary/term/policy_based_access_control", "docs/AUTH_SECURITY_CONTRACT.md must cite NIST PBAC guidance.");
requireText(authSecurityContractSource, "https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html", "docs/AUTH_SECURITY_CONTRACT.md must cite OWASP authorization guidance.");
requireText(authSecurityContractSource, "JWT possession is never authorization", "docs/AUTH_SECURITY_CONTRACT.md must keep JWT separate from authorization.");
requireText(authSecurityContractSource, "ABAC + RBAC + PBAC", "docs/AUTH_SECURITY_CONTRACT.md must require combined authorization controls.");
requireText(authSecurityContractSource, "WebAuthn/passkey user verification", "docs/AUTH_SECURITY_CONTRACT.md must require WebAuthn/passkey user verification.");
requireText(authSecurityContractSource, "auth_session_validate", "docs/AUTH_SECURITY_CONTRACT.md must document the Rust JWT/JWKS session validator boundary.");
requireText(authSecurityContractSource, "RS256 JWT signatures", "docs/AUTH_SECURITY_CONTRACT.md must document the current JWT signature verification slice.");
requireText(authSecurityContractSource, "hashes JWT IDs", "docs/AUTH_SECURITY_CONTRACT.md must document replay identifier hashing instead of raw JWT ID echoing.");
requireText(authSecurityContractSource, "Rust WebAuthn assertion verification slice", "docs/AUTH_SECURITY_CONTRACT.md must document the Rust WebAuthn assertion verification slice.");
requireText(authSecurityContractSource, "BITWEEN_WEBAUTHN_ASSERTION_JSON", "docs/AUTH_SECURITY_CONTRACT.md must document the WebAuthn assertion env boundary.");
requireText(authSecurityContractSource, "webauthn_sign_count_replayed", "docs/AUTH_SECURITY_CONTRACT.md must document replay-counter rejection.");
requireText(authSecurityContractSource, "server-side assertion boundary", "docs/AUTH_SECURITY_CONTRACT.md must describe the verified server-side WebAuthn assertion boundary.");
requireText(authSecurityContractSource, "auth_route_unconfigured", "docs/AUTH_SECURITY_CONTRACT.md must document fail-closed auth route behavior.");

requireText(productionFastPathSource, "Production delivery fast path", "docs/PRODUCTION_DELIVERY_FAST_PATH.md must remain the production fast-path contract.");
requireText(productionFastPathSource, "Kubernetes-native target", "Production fast path must preserve the Kubernetes-native target.");
requireText(productionFastPathSource, "PostgreSQL is the production relational system of record", "Production fast path must preserve PostgreSQL as relational system of record.");
requireText(productionFastPathSource, "RustFS is the production object/blob store", "Production fast path must preserve RustFS as object/blob store.");
requireText(productionFastPathSource, "JWT", "Production fast path must preserve real JWT authentication requirements.");
requireText(productionFastPathSource, "WebAuthn", "Production fast path must preserve WebAuthn/passkey requirements.");
requireText(productionFastPathSource, "ABAC + RBAC + PBAC", "Production fast path must preserve combined authorization requirements.");
requireText(productionFastPathSource, "Operator screens must not display Rust, Buck2, source-path, schema, backend", "Production fast path must reject technical operator walls.");
requireText(productionFastPathSource, "internal product operated on managed Kubernetes", "Production fast path must keep the internal managed-Kubernetes scope assumption.");
requireText(productionFastPathSource, "not an external hyperscale cloud product", "Production fast path must downscope Oyatie's external hyperscale/cloud-provider ceremonies for Bitween.");
requireText(productionFastPathSource, "wave-gated preview → stable → production progression", "Production fast path must adopt Oyatie-style wave gates in a Bitween-sized form.");
requireText(productionFastPathSource, "avoid public-cloud marketplace, multi-region fan-out, and hyperscaler-maturity claims", "Production fast path must explicitly avoid external-product ceremony that does not fit Bitween.");
requireText(productionFastPathSource, "accepts any file", "Production fast path must preserve any-file 자료함 intake.");
requireText(productionFastPathSource, "no repo-owned Python source left", "Production fast path must record completed Python decommission.");
requireText(productionFastPathSource, "npm run verify:no-python-source", "Production fast path must name the no-Python source enforcement gate.");
requireText(productionFastPathSource, "https://github.com/cncf/toc/blob/main/DEFINITION.md", "Production fast path must retain CNCF source-backed constraint.");
requireText(productionFastPathSource, "https://kubernetes.io/docs/concepts/security/multi-tenancy/", "Production fast path must retain Kubernetes multi-tenancy source-backed constraint.");
requireText(productionFastPathSource, "https://owasp.org/www-project-application-security-verification-standard/", "Production fast path must retain OWASP ASVS source-backed constraint.");
requireText(productionFastPathSource, "https://opentelemetry.io/docs/concepts/semantic-conventions/", "Production fast path must retain OpenTelemetry source-backed constraint.");
requireText(kubernetesNativeStackSource, "managed-Kubernetes product path", "Kubernetes stack doc must record the managed-Kubernetes product path.");
requireText(kubernetesNativeStackSource, "not an external hyperscale cloud product", "Kubernetes stack doc must downscope external hyperscale cloud-provider posture.");
requireText(kubernetesNativeStackSource, "| Runtime operation | Managed Kubernetes first |", "Kubernetes stack doc must make managed Kubernetes the first production runtime.");
requireText(kubernetesNativeStackSource, "cloud_native_audit_worker", "Kubernetes stack doc must document the cloud-native audit worker runtime boundary.");
requireText(kubernetesNativeStackSource, "ServiceMonitor", "Kubernetes stack doc must document observability ServiceMonitor wiring.");
requireText(kubernetesNativeStackSource, "ResourceQuota", "Kubernetes stack doc must document tenant ResourceQuota isolation.");
requireText(kubernetesNativeStackSource, "image digests", "Kubernetes stack doc must require promotion image digest evidence.");
rejectText(kubernetesNativeStackSource, ".example", "Kubernetes stack doc must not publish placeholder hostnames.");
rejectText(kubernetesNativeStackSource, "Kubernetes as scale-up path", "Kubernetes stack doc must not defer Kubernetes to a later scale-up path.");
requireText(postgresAdapterDecisionSource, "Decision: use tokio-postgres with a TLS-capable connector boundary", "PostgreSQL adapter decision must select a source-backed Rust driver path.");
requireText(postgresAdapterDecisionSource, "tokio-postgres-rustls", "PostgreSQL adapter decision must include a rustls-capable TLS path.");
requireText(postgresAdapterDecisionSource, "NoTls must not be used for production database traffic", "PostgreSQL adapter decision must reject production NoTls usage.");
requireText(postgresAdapterDecisionSource, "sqlx is deferred", "PostgreSQL adapter decision must explain why SQLx is not the first adapter slice.");
requireText(postgresAdapterDecisionSource, "PostgresRepositoryConfig::validate_driver_config", "PostgreSQL adapter decision must document the current driver validation checkpoint.");
requireText(postgresAdapterDecisionSource, "PostgresRepositoryConfig::connect_client_session", "PostgreSQL adapter decision must document the current connection/session checkpoint.");
requireText(postgresAdapterDecisionSource, "PostgresTenantScope", "PostgreSQL adapter decision must document tenant scope enforcement before repository reads/writes.");
requireText(postgresAdapterDecisionSource, "postgres://<redacted>", "PostgreSQL adapter decision must document sanitized connection/session errors.");
requireText(postgresAdapterDecisionSource, "PostgreSQL writes remain fail-closed", "PostgreSQL adapter decision must not overclaim production write enablement.");
requireText(postgresAdapterDecisionSource, "https://docs.rs/tokio-postgres/latest/tokio_postgres/", "PostgreSQL adapter decision must cite tokio-postgres docs.");
requireText(postgresAdapterDecisionSource, "https://docs.rs/tokio-postgres-rustls/latest/tokio_postgres_rustls/", "PostgreSQL adapter decision must cite tokio-postgres-rustls docs.");
requireText(postgresAdapterDecisionSource, "https://docs.rs/postgres/latest/postgres/", "PostgreSQL adapter decision must cite postgres sync-wrapper docs.");
requireText(postgresAdapterDecisionSource, "https://docs.rs/sqlx/latest/sqlx/macro.query.html", "PostgreSQL adapter decision must cite SQLx query macro/offline tradeoff docs.");

requirePattern(previewStylesSource, /\.sidebar\s*\{[\s\S]*?height:\s*100vh;[\s\S]*?overflow:\s*hidden;[\s\S]*?\}/, "preview sidebar must keep fixed viewport height and hide outer overflow.");
requirePattern(previewStylesSource, /\.nav-button\s*\{[\s\S]*?height:\s*46px;[\s\S]*?max-height:\s*46px;[\s\S]*?min-height:\s*46px;[\s\S]*?width:\s*100%;[\s\S]*?\}/, "preview sidebar nav buttons must use a fixed 46px row height.");
requirePattern(previewStylesSource, /\.nav-button strong\s*\{[\s\S]*?text-overflow:\s*ellipsis;[\s\S]*?white-space:\s*nowrap;[\s\S]*?\}/, "preview sidebar nav labels must not wrap and resize rows.");

if (appSource.includes("previewPlatformViewModel")) {
  errors.push("App.tsx still imports the preview view model; migrate Expo runtime to a live adapter before production release.");
}
requireText(appSource, "EXPO_PUBLIC_BITWEEN_AUTH_SIGNIN_URL", "App.tsx must route sign-in through a configured provider URL.");
requireText(appSource, "EXPO_PUBLIC_BITWEEN_AUTH_SIGNUP_URL", "App.tsx must route sign-up/access through a configured provider URL.");
requireText(appSource, "EXPO_PUBLIC_BITWEEN_AUTH_SIGNOUT_URL", "App.tsx must route sign-out through a configured provider URL.");
requireText(appSource, "EXPO_PUBLIC_BITWEEN_ONBOARDING_START_URL", "App.tsx must route onboarding through a configured provider URL.");
requireText(appSource, "<AuthGate", "App.tsx must render a real auth gate instead of entering the app without authentication.");
rejectText(appSource, 'logoutLabel="Reset"', "App.tsx must not hardcode a reset button as sign-out.");
rejectText(appSource, "employeeNumberLabel", "App.tsx must not expose employee/session diagnostics in the top bar.");
rejectText(appSource, "modeLabel", "App.tsx must not expose technical session mode in the top bar.");
rejectText(appSource, "developerMode", "App.tsx must not expose development mode in the operator shell.");
rejectText(appSource, "sessionLabel", "App.tsx must not expose a dense technical session label in the top bar.");
requireText(sourceViewModelSource, 't(locale, "session.displayName")', "src/viewModel.ts must localize fallback display names instead of hardcoding English operator text.");
requireText(sourceViewModelSource, 't(locale, "session.roleLabel")', "src/viewModel.ts must localize fallback role labels instead of exposing technical role ids.");
requireText(sourceViewModelSource, 't(locale, "session.employeeNumber.pending")', "src/viewModel.ts must localize pending employee-number text instead of exposing implementation diagnostics.");
rejectText(sourceViewModelSource, "operations_observer", "src/viewModel.ts must not expose technical fallback role ids in the operator shell.");
rejectText(sourceViewModelSource, "Acme Operator", "src/viewModel.ts must not expose mixed-language fallback person labels.");
rejectText(sourceViewModelSource, "read-only", "src/viewModel.ts must not expose technical read-only fallback session text.");
requireText(sourceComponentsSource, "lucide-react-native", "src/components.tsx must use Lucide icons instead of ad-hoc SVG icons.");
requireText(sourceComponentsSource, "function TopbarAction", "src/components.tsx must render top bar icon actions through a shared component.");
requireText(sourceComponentsSource, "function TopbarPanel", "src/components.tsx must render notification/message panels instead of routing icon clicks directly away.");
requireText(sourceComponentsSource, "function ProfileMenu", "src/components.tsx must keep profile actions and sign-out behind the profile icon.");
requireText(sourceComponentsSource, "helpStepIndex", "src/components.tsx must provide an interactive contextual help walkthrough, not a static help paragraph.");
requireText(sourceComponentsSource, "AuthGate", "src/components.tsx must expose an auth gate with sign-in/sign-up/onboarding actions.");
requireText(sourceThemeSource, "export const pantoneBasis", "src/theme.ts must define the Pantone-based basis palette.");
requireText(sourceThemeSource, "cloudDancer", "src/theme.ts must anchor surfaces on a Cloud Dancer-inspired Pantone basis.");
requireText(sourceThemeSource, "export const platformAccents", "src/theme.ts must expose platform accent colors from the central palette.");
requireText(sourceThemeSource, "whiteOverlay", "src/theme.ts must keep translucent surfaces in palette tokens.");
requireText(sourceDataSource, "platformAccents.", "src/data.ts navigation accents must come from theme platformAccents.");
requireText(sourceDataSource, "contractDueWindow", "src/data.ts must derive due-window screen contract fields for every module row.");
requireText(sourceDataSource, "contractBlockers", "src/data.ts must derive blocker screen contract fields for every module row.");
requireText(sourceDataSource, "contractPermission", "src/data.ts must derive permission screen contract fields for every module row.");
requireText(sourceDataSource, "contractLiveState", "src/data.ts must derive live-state screen contract fields for every module row.");
requireText(sourceScreensSource, "settings.theme.title", "src/screens.tsx must expose theme selection from Settings.");
requireText(sourceScreensSource, "getSidebarThemes(locale)", "src/screens.tsx must draw Settings theme options from theme tokens.");
requireText(sourceScreensSource, "workDetail.dueWindow", "src/screens.tsx must show due-window fields in module work detail.");
requireText(sourceScreensSource, "workDetail.blockers", "src/screens.tsx must show blocker fields in module work detail.");
requireText(sourceScreensSource, "workDetail.permission", "src/screens.tsx must show permission fields in module work detail.");
requireText(sourceScreensSource, "workDetail.liveState", "src/screens.tsx must show live/fail-closed state fields in module work detail.");
requireText(sourceTypesSource, "readonly dueWindow: string", "src/types.ts ModuleRow/PayrollStep must include due-window contracts.");
requireText(sourceTypesSource, "readonly blockers: string", "src/types.ts ModuleRow/PayrollStep must include blocker contracts.");
requireText(sourceTypesSource, "readonly permission: string", "src/types.ts ModuleRow/PayrollStep must include permission contracts.");
requireText(sourceTypesSource, "readonly liveState: string", "src/types.ts ModuleRow/PayrollStep must include live-state contracts.");
rejectPattern(sourceDataSource, /#[0-9A-Fa-f]{3,8}\b/, "src/data.ts must not define ad-hoc hex colors; use src/theme.ts palette tokens.");
rejectPattern(sourceComponentsSource, /#[0-9A-Fa-f]{3,8}\b|rgba?\(/, "src/components.tsx must not define ad-hoc literal colors; use src/theme.ts palette tokens.");
rejectText(sourceComponentsSource, "getSidebarThemes", "src/components.tsx sidebar must not render theme selection; theme selection belongs in Settings.");
rejectText(sourceComponentsSource, "themePanel", "src/components.tsx sidebar must not keep a theme panel.");
requireText(previewStylesSource, "--pantone-cloud-dancer", "preview/styles.css must expose Pantone-based root palette tokens.");
rejectPattern(previewStylesOutsideRoot, /#[0-9A-Fa-f]{3,8}\b|rgba?\(/, "preview/styles.css must keep literal colors in the root palette only; component rules should use variables.");
rejectText(sourceScreensSource, "LoginScreen", "src/screens.tsx must not ship a demo credential login screen.");
requireText(sourceTypesSource, '| "approval"', "src/types.ts must expose approval as a first-class platform id.");
requireText(sourceDataSource, '{ id: "approval"', "src/data.ts must keep approval as its own navigation item.");
rejectText(sourceDataSource, '{ id: "settings", accent:', "src/data.ts must not keep Settings in the left navigation definitions.");
requireText(sourceDataSource, 'approval: localizeModule("approval"', "src/data.ts must expose a separate approval module dashboard.");
requireText(sourceScreensSource, "function WorkflowCanvasPanel", "src/screens.tsx must render Workflow as workflow logic/canvas, not approvals.");
requireText(sourceScreensSource, "function ApprovalPanel", "src/screens.tsx must render 전자결재 as a separate approval-only surface.");
requireText(sourceScreensSource, "function PayrollWorkPanel", "src/screens.tsx must show payroll work, not technical readiness cards.");
requireText(sourceScreensSource, "payroll.work.title", "src/screens.tsx payroll surface must use business payroll work copy.");
rejectText(sourceScreensSource, "PayrollReadiness", "src/screens.tsx must not render payroll readiness cards.");
rejectText(sourceScreensSource, "PayrollReadinessDetail", "src/screens.tsx must not render payroll readiness detail panels.");
rejectText(sourceScreensSource, "stepIndex", "src/screens.tsx payroll flow must not show numbered step cards.");
rejectText(sourceScreensSource, "String(index + 1).padStart", "src/screens.tsx must not render numbered workflow cards.");
rejectText(sourceDataSource, "getReadinessCards", "src/data.ts must not expose payroll readiness card data to the operator UI.");
rejectText(sourceDataSource, "payroll.readiness", "src/data.ts must not keep payroll readiness catalog wiring.");
rejectText(sourceScreensSource, "WorkflowApprovalPanel", "src/screens.tsx must not keep approvals under a WorkflowApprovalPanel.");
rejectText(sourceScreensSource, "workflowApproval", "src/screens.tsx must not keep workflow/approval-coupled component names.");
rejectPattern(sourceScreensSource, /const approvalSummaryDefinitions = \[[^\]]*target: "admin"/, "src/screens.tsx approval cards must not route signing decisions to Admin.");
rejectPattern(sourceScreensSource, /const approvalSummaryDefinitions = \[[^\]]*target: "ai"/, "src/screens.tsx approval cards must not route signing decisions to AI/work assistance.");
requirePattern(sourceScreensSource, /const hrPeopleReviewDefinitions = \[[^\]]*target: "payroll"/, "src/screens.tsx HR surface must expose a live navigation path to payroll impact without merging HR and Payroll.");
rejectText(sourceDataSource, '{ id: "approval-pending", target: "workflow"', "approval work queue items must route to approval, not workflow.");
rejectText(sourceDataSource, 'id: "calendar-approval", target: "workflow"', "approval calendar events must route to approval, not workflow.");
rejectText(sourceDataSource, '{ completed: false, id: "todo-approval", target: "workflow"', "approval todos must route to approval, not workflow.");
rejectText(sourceDataSource, "PreviewAccount", "src/data.ts must not ship preview account definitions.");
rejectText(sourceDataSource, "password:", "src/data.ts must not ship hardcoded passwords.");
rejectText(sourceCatalogSource, "screens.login.demo", "catalog.json must not include demo login copy.");
rejectText(sourceCatalogSource, "preview.toast.demoLogin", "catalog.json must not include demo login toast copy.");
rejectText(sourceCatalogSource, "shell.status.demoCompany", "catalog.json must not include demo company shell status copy.");
rejectPattern(sourceCatalogSource, /readiness/i, "catalog.json must not include readiness copy for operator UI.");
rejectText(sourceCatalogSource, "shell.status.", "catalog.json must not keep technical shell status footer copy.");
rejectText(sourceCatalogSource, "preview.source.", "catalog.json must not include user-facing technical source diagnostics copy.");
rejectText(sourceCatalogSource, "회사 인증 주소가 설정되지 않았습니다.", "catalog.json must not show a dead-end missing auth address toast to operators.");
rejectText(sourceCatalogSource, "Hermetic 개발", "catalog.json must not include user-facing hermetic diagnostics copy.");
rejectText(sourceCatalogSource, "Buck2 전용", "catalog.json must not include user-facing build-tool diagnostics copy.");
rejectText(sourceCatalogSource, "Buck2", "catalog.json must not expose build-tool names in operator copy.");
rejectText(sourceCatalogSource, "RustFS", "catalog.json must not expose object-store implementation names in operator copy.");
rejectText(sourceCatalogSource, "PostgreSQL", "catalog.json must not expose database implementation names in operator copy.");
rejectText(sourceCatalogSource, "rust_native", "catalog.json must not expose backend enum values in operator copy.");
rejectText(sourceCatalogSource, "backend/API", "catalog.json must not expose backend/API contract gaps in operator copy.");
rejectText(sourceCatalogSource, "backend API", "catalog.json must not expose backend API contract gaps in operator copy.");
rejectText(sourceCatalogSource, "API 계약", "catalog.json must not expose API contract gaps in operator copy.");
rejectText(sourceCatalogSource, "실제 저장 없이", "catalog.json must not tell operators that a visible settings surface is unsaved.");
rejectText(sourceCatalogSource, "화면 안내만", "catalog.json must not describe production surfaces as guidance-only placeholders.");
rejectText(sourceCatalogSource, "실제 인사 자료를 저장하지 않고", "catalog.json must not describe HR as a non-live placeholder.");
rejectText(sourceCatalogSource, "실제 지원자 자료를 저장하지 않고", "catalog.json must not describe recruiting as a non-live placeholder.");
requireText(sourceCatalogSource, "단계 편집", "catalog.json must expose persisted workflow editing copy after live route wiring.");
rejectText(sourceCatalogSource, "완료 또는 다시 열기", "catalog.json must not advertise fake workflow status editing.");
requireText(sourceCatalogSource, '"key": "screens.hrPeople.cards.payrollImpact.title"', "catalog.json must describe the HR-to-payroll impact workflow.");
rejectText(sourceCatalogSource, retiredObjectStoreName, "catalog.json must not include retired object-store copy; 자료함 uses RustFS-backed object storage.");
requireText(sourceCatalogSource, '"key": "navigation.workflow.label"', "catalog.json must keep a Workflow navigation label.");
requireText(sourceCatalogSource, '"ko-KR": "업무 관리"', "catalog.json must label workflow as 업무 관리 in Korean.");
rejectText(sourceCatalogSource, "워크플로", "catalog.json must not use lazy workflow loanword copy in Korean operator UI.");
rejectText(sourceCatalogSource, "워크플로우", "catalog.json must not use lazy workflow loanword copy in Korean operator UI.");
requireText(sourceCatalogSource, '"key": "navigation.approval.label"', "catalog.json must keep a separate approval navigation label.");
requireText(sourceCatalogSource, '"ko-KR": "전자결재"', "catalog.json must label approval as 전자결재 in Korean.");
rejectText(sourceCatalogSource, "preview.archive.intake.steps.", "catalog.json must not keep numbered archive intake step copy.");
rejectText(sourceCatalogSource, "preview.workflow.canvas.edit", "catalog.json must not include visible fake workflow edit copy.");
rejectText(sourceCatalogSource, "shell.themePanel", "catalog.json must not keep sidebar theme-selection copy; theme selection belongs in Settings.");

if (errors.length > 0) {
  console.error("runtime data mode verification failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("Runtime data mode check passed.");
