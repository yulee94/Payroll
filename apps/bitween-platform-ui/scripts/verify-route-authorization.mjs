import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { spawn } from "node:child_process";
import http from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appRoot = join(__dirname, "..");
const serverPath = join(appRoot, "preview", "server.js");
const basePort = 4700 + (process.pid % 300);

function requestJson(port, method, path, body = "", headers = {}) {
  return new Promise((resolve, reject) => {
    const payload = Buffer.isBuffer(body) ? body : Buffer.from(body, "utf8");
    const req = http.request(
      {
        hostname: "127.0.0.1",
        method,
        path,
        port,
        timeout: 10000,
        headers: {
          "content-length": String(payload.length),
          ...headers
        }
      },
      (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          const text = Buffer.concat(chunks).toString("utf8");
          try {
            resolve({ body: text ? JSON.parse(text) : {}, statusCode: res.statusCode ?? 0 });
          } catch (error) {
            reject(new Error(`Invalid JSON from ${method} ${path}: ${error.message}; body=${text.slice(0, 200)}`));
          }
        });
      }
    );
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error(`Timed out requesting ${method} ${path}`)));
    req.end(payload);
  });
}

function launchServer(port, extraEnv = {}) {
  const child = spawn(process.execPath, [serverPath, String(port)], {
    cwd: appRoot,
    env: {
      ...process.env,
      ...extraEnv,
      PORT: String(port)
    },
    stdio: ["ignore", "pipe", "pipe"]
  });
  let stderr = "";
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString("utf8");
  });
  child.stdout.on("data", () => {});
  return { child, stderr: () => stderr };
}

async function waitForServer(port) {
  let lastError;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      await requestJson(port, "GET", "/api/auth/v1/routes");
      return;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  throw lastError ?? new Error("Server did not start");
}

async function withServer(port, env, fn) {
  const server = launchServer(port, env);
  try {
    await waitForServer(port);
    await fn();
  } finally {
    server.child.kill("SIGTERM");
  }
}

function withRustFsMock(fn) {
  const uploads = [];
  const server = http.createServer((req, res) => {
    if (req.method !== "PUT") {
      res.writeHead(404);
      res.end();
      return;
    }
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => {
      uploads.push({
        body: Buffer.concat(chunks),
        path: req.url || "",
        sha256: req.headers["x-amz-meta-bitween-sha256"] || ""
      });
      res.writeHead(200, { "content-type": "text/plain" });
      res.end("ok");
    });
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", async () => {
      try {
        const { port } = server.address();
        await fn({
          env: {
            BITWEEN_RUSTFS_ENDPOINT: `http://127.0.0.1:${port}`,
            BITWEEN_RUSTFS_ACCESS_KEY: "local-access-key",
            BITWEEN_RUSTFS_SECRET_KEY: "local-secret-key",
            BITWEEN_RUSTFS_BUCKET_ARCHIVE: "bitween-archive-originals",
            BITWEEN_RUSTFS_REGION: "us-east-1"
          },
          uploads
        });
        server.close(() => resolve());
      } catch (error) {
        server.close(() => reject(error));
      }
    });
  });
}

function localStoreEnv(tempDir) {
  return {
    BITWEEN_ALLOW_LOCAL_REVIEW_STORE: "true",
    BITWEEN_HR_EMPLOYEE_STORE: join(tempDir, "hr", "employees.json"),
    BITWEEN_ARCHIVE_INTAKE_STORE: join(tempDir, "archive", "intake.json"),
    BITWEEN_USER_PREFERENCE_STORE: join(tempDir, "settings", "preferences.json"),
    BITWEEN_WORKFLOW_TEMPLATE_STORE: join(tempDir, "workflow", "templates.json"),
    BITWEEN_TENANT_ID: "tenant-acme",
    BITWEEN_TENANT_NAME: "Acme",
    BITWEEN_PAYROLL_AFFILIATE: "Acme",
    BITWEEN_PAYROLL_WORKPLACE: "Seoul",
    BITWEEN_PAYROLL_PERIOD: "2026-06"
  };
}

function postgresDsnEnv(tempDir) {
  return {
    BITWEEN_POSTGRES_DSN: "postgres://bitween:bitween@127.0.0.1:5432/bitween",
    BITWEEN_POSTGRES_TENANT_ID: "tenant-acme",
    BITWEEN_POSTGRES_LEGAL_ENTITY_ID: "acme-corp",
    BITWEEN_POSTGRES_WORKPLACE_ID: "seoul",
    BITWEEN_HR_EMPLOYEE_STORE: join(tempDir, "hr", "employees.json"),
    BITWEEN_ARCHIVE_INTAKE_STORE: join(tempDir, "archive", "intake.json"),
    BITWEEN_USER_PREFERENCE_STORE: join(tempDir, "settings", "preferences.json"),
    BITWEEN_WORKFLOW_TEMPLATE_STORE: join(tempDir, "workflow", "templates.json"),
    BITWEEN_TENANT_ID: "tenant-acme",
    BITWEEN_TENANT_NAME: "Acme",
    BITWEEN_PAYROLL_AFFILIATE: "Acme",
    BITWEEN_PAYROLL_WORKPLACE: "Seoul",
    BITWEEN_PAYROLL_PERIOD: "2026-06"
  };
}

function verifiedSessionEnv(role = "hr_operator") {
  return {
    BITWEEN_AUTH_CONFIGURED: "true",
    BITWEEN_SESSION_JWT_VERIFIED: "true",
    BITWEEN_SESSION_JWT_ISSUER: "https://auth.example.com",
    BITWEEN_SESSION_JWT_AUDIENCE: "bitween-platform",
    BITWEEN_SESSION_JWT_SUBJECT: "user-live-ops",
    BITWEEN_SESSION_JWT_EXPIRES_AT_UNIX: "4102444800",
    BITWEEN_WEBAUTHN_USER_VERIFIED: "true",
    BITWEEN_SESSION_ACR_LEVEL: "elevated",
    BITWEEN_SESSION_ACR_EVENT_AT_UNIX: "1",
    BITWEEN_SESSION_ROLE: role,
    BITWEEN_SESSION_AUTHZ_POLICY_ID: "bitween.authz.rbac-abac-pbac.v1",
    BITWEEN_SESSION_AUTHZ_TENANT_ID: "tenant-acme",
    BITWEEN_SESSION_AUTHZ_LEGAL_ENTITY: "Acme",
    BITWEEN_SESSION_AUTHZ_WORKPLACE: "Seoul"
  };
}

function multipartBody(content = "name,amount\nAcme Member,1000\n", fileName = "payroll.csv") {
  const boundary = `bitween-${process.pid}`;
  const body = Buffer.from([
    `--${boundary}`,
    `Content-Disposition: form-data; name="file"; filename="${fileName}"`,
    "Content-Type: text/csv",
    "",
    content,
    `--${boundary}--`,
    ""
  ].join("\r\n"));
  return { body, headers: { "content-type": `multipart/form-data; boundary=${boundary}` } };
}

function assertDenied(response, route) {
  if (response.statusCode !== 403 || response.body.ok !== false || response.body.error !== "authorization_required") {
    throw new Error(`${route} must fail closed before storage/object side effects: ${JSON.stringify(response)}`);
  }
}

function assertNoLocalStoreSideEffects(tempDir, route) {
  for (const relativePath of [
    "hr/employees.json",
    "archive/intake.json",
    "settings/preferences.json",
    "workflow/templates.json"
  ]) {
    if (existsSync(join(tempDir, relativePath))) {
      throw new Error(`${route} created a local-review store side effect at ${relativePath}`);
    }
  }
}

function assertPostgresStoreUnavailable(response, route, errorCode) {
  if (response.statusCode !== 503 || response.body.error !== errorCode) {
    throw new Error(`${route} must use the configured Rust PostgreSQL adapter and fail closed if PostgreSQL is unavailable: ${JSON.stringify(response)}`);
  }
  if (!String(response.body.detail || "").includes("postgres://<redacted>")) {
    throw new Error(`${route} PostgreSQL adapter failures must redact the DSN: ${JSON.stringify(response)}`);
  }
}

async function verifyUnauthenticatedMutableRoutesFailClosed() {
  const tempDir = mkdtempSync(join(tmpdir(), "bitween-authz-deny-"));
  try {
    await withServer(basePort, localStoreEnv(tempDir), async () => {
      assertDenied(
        await requestJson(basePort, "GET", "/api/hr/v1/employees"),
        "GET /api/hr/v1/employees"
      );
      assertDenied(
        await requestJson(
          basePort,
          "POST",
          "/api/hr/v1/employees",
          JSON.stringify({ name: "Acme Operator", team: "HR", role: "Manager" }),
          { "content-type": "application/json" }
        ),
        "POST /api/hr/v1/employees"
      );
      assertDenied(
        await requestJson(
          basePort,
          "PATCH",
          "/api/hr/v1/employees/employee-1",
          JSON.stringify({ role: "Lead" }),
          { "content-type": "application/json" }
        ),
        "PATCH /api/hr/v1/employees/:id"
      );
      assertDenied(
        await requestJson(basePort, "DELETE", "/api/hr/v1/employees/employee-1"),
        "DELETE /api/hr/v1/employees/:id"
      );
      assertDenied(
        await requestJson(basePort, "GET", "/api/settings/v1/preferences"),
        "GET /api/settings/v1/preferences"
      );
      assertDenied(
        await requestJson(
          basePort,
          "PUT",
          "/api/settings/v1/preferences",
          JSON.stringify({ locale: "ko-KR", theme: "calm" }),
          { "content-type": "application/json" }
        ),
        "PUT /api/settings/v1/preferences"
      );
      assertDenied(
        await requestJson(basePort, "GET", "/api/archive/v1/intake"),
        "GET /api/archive/v1/intake"
      );
      const upload = multipartBody();
      assertDenied(
        await requestJson(basePort, "POST", "/api/archive/v1/intake", upload.body, upload.headers),
        "POST /api/archive/v1/intake"
      );
      assertDenied(
        await requestJson(
          basePort,
          "PATCH",
          "/api/archive/v1/intake/intake-1/issues",
          JSON.stringify({ issue_type: "guidance", code: "explain_column", column: "조직" }),
          { "content-type": "application/json" }
        ),
        "PATCH /api/archive/v1/intake/:id/issues"
      );
      assertDenied(
        await requestJson(
          basePort,
          "PATCH",
          "/api/archive/v1/intake/intake-1/field-mappings",
          JSON.stringify({
            sourceFingerprint: "sha256:test",
            mappings: []
          }),
          { "content-type": "application/json" }
        ),
        "PATCH /api/archive/v1/intake/:id/field-mappings"
      );
      assertDenied(
        await requestJson(basePort, "POST", "/api/archive/v1/intake/intake-1/admissions", "{}", { "content-type": "application/json" }),
        "POST /api/archive/v1/intake/:id/admissions"
      );
      assertDenied(
        await requestJson(
          basePort,
          "POST",
          "/api/archive/v1/intake/intake-1/rollbacks",
          JSON.stringify({ reason: "operator_requested" }),
          { "content-type": "application/json" }
        ),
        "POST /api/archive/v1/intake/:id/rollbacks"
      );
      assertDenied(
        await requestJson(
          basePort,
          "POST",
          "/api/archive/v1/intake/intake-1/source-syncs",
          "{}",
          { "content-type": "application/json" }
        ),
        "POST /api/archive/v1/intake/:id/source-syncs"
      );
      assertDenied(
        await requestJson(basePort, "GET", "/api/workflow/v1/templates"),
        "GET /api/workflow/v1/templates"
      );
      assertDenied(
        await requestJson(
          basePort,
          "POST",
          "/api/workflow/v1/templates/payroll-close/preflights",
          JSON.stringify({ actor_role: "payroll_manager" }),
          { "content-type": "application/json" }
        ),
        "POST /api/workflow/v1/templates/:id/preflights"
      );
      assertDenied(
        await requestJson(
          basePort,
          "POST",
          "/api/workflow/v1/templates/payroll-close/steps/close-attendance/validations",
          JSON.stringify({ next_step_ids: ["close-payroll-inputs"] }),
          { "content-type": "application/json" }
        ),
        "POST /api/workflow/v1/templates/:id/steps/:stepId/validations"
      );
      assertDenied(
        await requestJson(
          basePort,
          "POST",
          "/api/workflow/v1/templates/payroll-close/steps",
          JSON.stringify({ title: "Exception review", action: "Confirm missing item", owner: "payroll_manager", lane: "operation", node_type: "condition" }),
          { "content-type": "application/json" }
        ),
        "POST /api/workflow/v1/templates/:id/steps"
      );
      assertDenied(
        await requestJson(
          basePort,
          "PATCH",
          "/api/workflow/v1/templates/payroll-close/steps/close-attendance",
          JSON.stringify({ status: "completed" }),
          { "content-type": "application/json" }
        ),
        "PATCH /api/workflow/v1/templates/:id/steps/:stepId"
      );
      assertDenied(
        await requestJson(
          basePort,
          "DELETE",
          "/api/workflow/v1/templates/payroll-close/steps/close-attendance",
          JSON.stringify({}),
          { "content-type": "application/json" }
        ),
        "DELETE /api/workflow/v1/templates/:id/steps/:stepId"
      );
      assertDenied(
        await requestJson(
          basePort,
          "POST",
          "/api/workflow/v1/templates/payroll-close/steps/close-attendance/executions",
          JSON.stringify({ actor_role: "payroll_manager" }),
          { "content-type": "application/json" }
        ),
        "POST /api/workflow/v1/templates/:id/steps/:stepId/executions"
      );
      assertNoLocalStoreSideEffects(tempDir, "unauthenticated route checks");
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

async function verifyAuthorizedHrWriteSucceeds() {
  const tempDir = mkdtempSync(join(tmpdir(), "bitween-authz-allow-"));
  try {
    await withServer(basePort + 1, { ...localStoreEnv(tempDir), ...verifiedSessionEnv("hr_operator") }, async () => {
      const response = await requestJson(
        basePort + 1,
        "POST",
        "/api/hr/v1/employees",
        JSON.stringify({ name: "Acme Operator", team: "HR", role: "Manager" }),
        { "content-type": "application/json" }
      );
      if (response.statusCode !== 200 || response.body.schema !== "bitween.hr.employee-store.v1" || response.body.employees?.length !== 1) {
        throw new Error(`Authorized HR write should reach the Rust store: ${JSON.stringify(response)}`);
      }
      const list = await requestJson(basePort + 1, "GET", "/api/hr/v1/employees");
      if (list.statusCode !== 200 || list.body.schema !== "bitween.hr.employee-store.v1" || list.body.employees?.length !== 1) {
        throw new Error(`Authorized HR read should reach the Rust store: ${JSON.stringify(list)}`);
      }
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

async function verifyAuthorizedSettingsUpdateSucceeds() {
  const tempDir = mkdtempSync(join(tmpdir(), "bitween-authz-settings-"));
  try {
    await withServer(basePort + 2, { ...localStoreEnv(tempDir), ...verifiedSessionEnv("support_sre") }, async () => {
      const response = await requestJson(
        basePort + 2,
        "PUT",
        "/api/settings/v1/preferences",
        JSON.stringify({ locale: "ko-KR", theme: "calm" }),
        { "content-type": "application/json" }
      );
      if (response.statusCode !== 200 || response.body.schema !== "bitween.user-preferences.v1" || response.body.current?.locale !== "ko-KR") {
        throw new Error(`Authorized settings update should reach the Rust store: ${JSON.stringify(response)}`);
      }
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

async function verifyAuthorizedArchiveReadReachesRustStore() {
  const tempDir = mkdtempSync(join(tmpdir(), "bitween-authz-archive-"));
  try {
    await withServer(basePort + 3, { ...localStoreEnv(tempDir), ...verifiedSessionEnv("payroll_operator") }, async () => {
      const response = await requestJson(basePort + 3, "GET", "/api/archive/v1/intake");
      if (response.statusCode !== 200 || response.body.schema !== "bitween.archive.intake-store.v1") {
        throw new Error(`Authorized archive read should reach the Rust store: ${JSON.stringify(response)}`);
      }
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

async function verifyAuthorizedArchiveUploadSucceeds() {
  const tempDir = mkdtempSync(join(tmpdir(), "bitween-authz-upload-"));
  try {
    await withRustFsMock(async ({ env: rustFsEnv, uploads }) => {
      await withServer(basePort + 4, { ...localStoreEnv(tempDir), ...verifiedSessionEnv("payroll_operator"), ...rustFsEnv }, async () => {
        const upload = multipartBody();
        const response = await requestJson(basePort + 4, "POST", "/api/archive/v1/intake", upload.body, upload.headers);
        if (response.statusCode !== 200 || response.body.schema !== "bitween.archive.intake-store.v1" || response.body.intakes?.length !== 1) {
          throw new Error(`Authorized archive upload should reach RustFS and the Rust store: ${JSON.stringify(response)}`);
        }
        if (uploads.length !== 1 || !uploads[0].path.startsWith("/bitween-archive-originals/quarantine/") || !uploads[0].sha256) {
          throw new Error(`Authorized archive upload should PUT one quarantined RustFS object with checksum metadata: ${JSON.stringify(uploads)}`);
        }
      });
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

async function verifyAuthorizedArchiveFieldMappingReviewSucceeds() {
  const tempDir = mkdtempSync(join(tmpdir(), "bitween-authz-archive-review-"));
  try {
    await withRustFsMock(async ({ env: rustFsEnv }) => {
      await withServer(basePort + 7, { ...localStoreEnv(tempDir), ...verifiedSessionEnv("hr_operator"), BITWEEN_SESSION_ACR_LEVEL: "sensitive", ...rustFsEnv }, async () => {
        const upload = multipartBody(
          "이름,특이값\nAcme Member,People\n",
          "employee-roster.csv"
        );
        const uploaded = await requestJson(basePort + 7, "POST", "/api/archive/v1/intake", upload.body, upload.headers);
        const intake = uploaded.body.intakes?.[0];
        const issue = intake?.guidance_items?.find((item) => item.code === "confirm_missing_required_data" && item.column === "department");
        if (uploaded.statusCode !== 200 || !intake?.id || !issue) {
          throw new Error(`Authorized archive field mapping setup should create a required mapping issue: ${JSON.stringify(uploaded)}`);
        }

        const reviewed = await requestJson(
          basePort + 7,
          "PATCH",
          `/api/archive/v1/intake/${encodeURIComponent(intake.id)}/field-mappings`,
          JSON.stringify({
            sourceFingerprint: intake.source_fingerprint,
            mappings: [{
              sourceColumn: "특이값",
              targetTable: "hr_employee_staging",
              targetField: "department",
              status: "confirmed",
              ignoreReason: null
            }]
          }),
          { "content-type": "application/json" }
        );
        const reviewedIntake = reviewed.body.intakes?.find((item) => item.id === intake.id);
        const stillOpen = reviewedIntake?.guidance_items?.some((item) => item.code === issue.code && item.column === issue.column);
        const mapped = reviewedIntake?.field_mappings?.find((mapping) => mapping.source_column === "특이값");
        if (reviewed.statusCode !== 200 || stillOpen || mapped?.target_field !== "department" || mapped?.status !== "confirmed") {
          throw new Error(`Authorized archive field mapping review should resolve the required mapping through the Rust store: ${JSON.stringify(reviewed)}`);
        }
      });
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

async function verifyPostgresDsnUsesRustRepositoriesWithoutLocalSideEffects() {
  const tempDir = mkdtempSync(join(tmpdir(), "bitween-postgres-adapter-required-"));
  try {
    await withServer(basePort + 5, { ...postgresDsnEnv(tempDir), ...verifiedSessionEnv("platform_owner"), BITWEEN_SESSION_ACR_LEVEL: "sensitive" }, async () => {
      assertPostgresStoreUnavailable(
        await requestJson(basePort + 5, "GET", "/api/hr/v1/employees"),
        "GET /api/hr/v1/employees",
        "hr_employee_store_unavailable"
      );
      assertPostgresStoreUnavailable(
        await requestJson(basePort + 5, "GET", "/api/archive/v1/intake"),
        "GET /api/archive/v1/intake",
        "archive_intake_store_unavailable"
      );
      assertPostgresStoreUnavailable(
        await requestJson(
          basePort + 5,
          "PATCH",
          "/api/archive/v1/intake/00000000-0000-0000-0000-000000000001/issues",
          JSON.stringify({ issue_type: "guidance", code: "explain_column", column: "조직" }),
          { "content-type": "application/json" }
        ),
        "PATCH /api/archive/v1/intake/:id/issues",
        "archive_intake_store_unavailable"
      );
      assertPostgresStoreUnavailable(
        await requestJson(
          basePort + 5,
          "PATCH",
          "/api/archive/v1/intake/00000000-0000-0000-0000-000000000001/field-mappings",
          JSON.stringify({
            sourceFingerprint: "sha256:test",
            mappings: []
          }),
          { "content-type": "application/json" }
        ),
        "PATCH /api/archive/v1/intake/:id/field-mappings",
        "archive_intake_store_unavailable"
      );
      assertPostgresStoreUnavailable(
        await requestJson(
          basePort + 5,
          "POST",
          "/api/archive/v1/intake/00000000-0000-0000-0000-000000000001/admissions",
          "{}",
          { "content-type": "application/json" }
        ),
        "POST /api/archive/v1/intake/:id/admissions",
        "archive_intake_store_unavailable"
      );
      assertPostgresStoreUnavailable(
        await requestJson(
          basePort + 5,
          "POST",
          "/api/archive/v1/intake/00000000-0000-0000-0000-000000000001/rollbacks",
          JSON.stringify({ reason: "selected_recovery_point", recovery_point_id: "00000000-0000-0000-0000-000000000002" }),
          { "content-type": "application/json" }
        ),
        "POST /api/archive/v1/intake/:id/rollbacks",
        "archive_intake_store_unavailable"
      );
      assertPostgresStoreUnavailable(
        await requestJson(
          basePort + 5,
          "POST",
          "/api/archive/v1/intake/00000000-0000-0000-0000-000000000001/source-syncs",
          "{}",
          { "content-type": "application/json" }
        ),
        "POST /api/archive/v1/intake/:id/source-syncs",
        "archive_source_sync_store_unavailable"
      );
      assertPostgresStoreUnavailable(
        await requestJson(basePort + 5, "GET", "/api/settings/v1/preferences"),
        "GET /api/settings/v1/preferences",
        "user_preference_store_unavailable"
      );
      assertPostgresStoreUnavailable(
        await requestJson(basePort + 5, "GET", "/api/workflow/v1/templates"),
        "GET /api/workflow/v1/templates",
        "workflow_template_store_unavailable"
      );
      assertNoLocalStoreSideEffects(tempDir, "postgres DSN with Rust PostgreSQL adapters");
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

async function verifyAuthorizedWorkflowEditorSucceeds() {
  const tempDir = mkdtempSync(join(tmpdir(), "bitween-authz-workflow-"));
  try {
    await withServer(basePort + 6, { ...localStoreEnv(tempDir), ...verifiedSessionEnv("platform_owner"), BITWEEN_SESSION_ACR_LEVEL: "sensitive" }, async () => {
      const add = await requestJson(
        basePort + 6,
        "POST",
        "/api/workflow/v1/templates/payroll-close/steps",
        JSON.stringify({
          title: "Exception review",
          action: "Confirm missing item before payroll continues",
          owner: "payroll_manager",
          lane: "operation",
          node_type: "condition",
          after_step_id: "review-deductions",
          slo_minutes: 120,
          escalation_role: "payroll_manager",
          condition_expression: { rule: "deduction exception owner must be confirmed before calculation" },
          permission_scope: { data_class: "sensitive", tenant_required: "true", object_scope: "payroll_period" }
        }),
        { "content-type": "application/json" }
      );
      if (add.statusCode !== 200 || add.body.schema !== "bitween.workflow.template-store.v1") {
        throw new Error(`Authorized workflow add should reach the Rust store: ${JSON.stringify(add)}`);
      }
      const added = add.body.templates?.[0]?.steps?.find((step) => step.id === "exception-review");
      if (!added || added.next_step_ids?.[0] !== "run-calculation") {
        throw new Error(`Authorized workflow add should persist a connected graph step: ${JSON.stringify(add.body.templates?.[0]?.steps)}`);
      }

      const patch = await requestJson(
        basePort + 6,
        "PATCH",
        "/api/workflow/v1/templates/payroll-close/steps/exception-review",
        JSON.stringify({
          title: "Exception owner review",
          action: "Confirm owner and next action",
          status: "waiting",
          owner: "payroll_manager",
          lane: "operation",
          node_type: "condition",
          position_x: 58,
          position_y: 54,
          next_step_ids: ["run-calculation", "request-approval"],
          slo_minutes: 120,
          escalation_role: "payroll_manager",
          condition_expression: { rule: "deduction exception owner must be confirmed before calculation" },
          permission_scope: { data_class: "sensitive", tenant_required: "true", object_scope: "payroll_period" }
        }),
        { "content-type": "application/json" }
      );
      const updated = patch.body.templates?.[0]?.steps?.find((step) => step.id === "exception-review");
      if (patch.statusCode !== 200 || updated?.status !== "waiting" || updated?.title !== "Exception owner review" || updated?.next_step_ids?.length !== 2 || updated?.position_x !== 58) {
        throw new Error(`Authorized workflow patch should persist editor fields: ${JSON.stringify(patch)}`);
      }
      if (!patch.body.analytics?.some((item) => item.template_id === "payroll-close" && item.branch_count >= 1)) {
        throw new Error(`Authorized workflow patch should return graph analytics for branch wiring: ${JSON.stringify(patch.body.analytics)}`);
      }

      const validation = await requestJson(
        basePort + 6,
        "POST",
        "/api/workflow/v1/templates/payroll-close/steps/review-deductions/validations",
        JSON.stringify({
          actor_role: "payroll_manager",
          next_step_ids: ["run-calculation", "request-approval"]
        }),
        { "content-type": "application/json" }
      );
      if (validation.statusCode !== 200 || validation.body.schema !== "bitween.workflow.edit-validation.v1" || validation.body.status !== "accepted" || validation.body.would_persist !== true || validation.body.proposed_analytics?.branch_count < 1) {
        throw new Error(`Authorized workflow validation should dry-run accepted branch wiring: ${JSON.stringify(validation)}`);
      }

      const blockedValidation = await requestJson(
        basePort + 6,
        "POST",
        "/api/workflow/v1/templates/payroll-close/steps/request-approval/validations",
        JSON.stringify({
          actor_role: "payroll_manager",
          next_step_ids: ["close-attendance"]
        }),
        { "content-type": "application/json" }
      );
      if (blockedValidation.statusCode !== 200 || blockedValidation.body.status !== "blocked" || blockedValidation.body.would_persist !== false || !blockedValidation.body.issues?.some((issue) => issue.code === "cycle_detected")) {
        throw new Error(`Authorized workflow validation should block cycle-creating rewiring before persistence: ${JSON.stringify(blockedValidation)}`);
      }

      const preflight = await requestJson(
        basePort + 6,
        "POST",
        "/api/workflow/v1/templates/payroll-close/preflights",
        JSON.stringify({
          actor_role: "payroll_manager",
          scope_tenant: "Acme Corporation",
          scope_workplace: "Seoul",
          scope_period: "2026-06"
        }),
        { "content-type": "application/json" }
      );
      if (preflight.statusCode !== 200 || preflight.body.schema !== "bitween.workflow.preflight.v1" || !preflight.body.planned_step_ids?.includes("run-calculation") || !preflight.body.data_operations?.some((operation) => operation.operation_type === "payroll_calculation_plan")) {
        throw new Error(`Authorized workflow preflight should return a Rust-planned execution report: ${JSON.stringify(preflight)}`);
      }

      const execution = await requestJson(
        basePort + 6,
        "POST",
        "/api/workflow/v1/templates/payroll-close/steps/exception-review/executions",
        JSON.stringify({
          actor_role: "payroll_manager",
          scope_tenant: "Acme Corporation",
          scope_workplace: "Seoul",
          scope_period: "2026-06"
        }),
        { "content-type": "application/json" }
      );
      const executed = execution.body.templates?.[0]?.steps?.find((step) => step.id === "exception-review");
      const customOperation = execution.body.runtime_events?.[0]?.data_operations?.[0];
      const customRecord = execution.body.data_records?.find((record) => record.step_id === "exception-review");
      if (execution.statusCode !== 200 || executed?.status !== "completed" || execution.body.runtime_events?.[0]?.affected_step_ids?.length !== 2 || customOperation?.operation_type !== "custom_workflow_action" || customRecord?.record_type !== "custom_workflow_action") {
        throw new Error(`Authorized workflow execution should mutate graph state and record concrete data operation evidence: ${JSON.stringify(execution)}`);
      }

      const calculation = await requestJson(
        basePort + 6,
        "POST",
        "/api/workflow/v1/templates/payroll-close/steps/run-calculation/executions",
        JSON.stringify({
          actor_role: "payroll_manager",
          scope_tenant: "Acme Corporation",
          scope_workplace: "Seoul",
          scope_period: "2026-06"
        }),
        { "content-type": "application/json" }
      );
      const calculationOperation = calculation.body.runtime_events?.find((event) => event.step_id === "run-calculation")?.data_operations?.[0];
      const calculationRecord = calculation.body.data_records?.find((record) => record.step_id === "run-calculation" && record.record_type === "payroll_calculation_plan");
      if (calculation.statusCode !== 200 || calculationOperation?.operation_type !== "payroll_calculation_plan" || calculationOperation?.metadata?.scope_period !== "2026-06" || calculationRecord?.metadata?.scope_period !== "2026-06") {
        throw new Error(`Authorized workflow calculation execution should produce payroll planning evidence with business scope: ${JSON.stringify(calculation)}`);
      }

      const deleted = await requestJson(
        basePort + 6,
        "DELETE",
        "/api/workflow/v1/templates/payroll-close/steps/exception-review",
        JSON.stringify({}),
        { "content-type": "application/json" }
      );
      const stillPresent = deleted.body.templates?.[0]?.steps?.some((step) => step.id === "exception-review");
      if (deleted.statusCode !== 200 || stillPresent) {
        throw new Error(`Authorized workflow delete should remove the graph step: ${JSON.stringify(deleted)}`);
      }

      const rollback = await requestJson(
        basePort + 6,
        "POST",
        "/api/workflow/v1/templates/payroll-close/rollbacks",
        JSON.stringify({ version: 1 }),
        { "content-type": "application/json" }
      );
      const restoredException = rollback.body.templates?.[0]?.steps?.some((step) => step.id === "exception-review");
      const rollbackVersion = rollback.body.template_versions?.at?.(-1);
      if (rollback.statusCode !== 200 || restoredException || rollbackVersion?.rollback_of_version !== 1) {
        throw new Error(`Authorized workflow rollback should restore a prior persisted text graph version: ${JSON.stringify(rollback)}`);
      }
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
}

await verifyUnauthenticatedMutableRoutesFailClosed();
await verifyAuthorizedHrWriteSucceeds();
await verifyAuthorizedSettingsUpdateSucceeds();
await verifyAuthorizedArchiveReadReachesRustStore();
await verifyAuthorizedArchiveUploadSucceeds();
await verifyAuthorizedArchiveFieldMappingReviewSucceeds();
await verifyPostgresDsnUsesRustRepositoriesWithoutLocalSideEffects();
await verifyAuthorizedWorkflowEditorSucceeds();
console.log("Route authorization verification passed.");
