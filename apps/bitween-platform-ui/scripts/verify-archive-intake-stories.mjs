import { existsSync, readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { spawn, spawnSync } from "node:child_process";
import http from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import zlib from "node:zlib";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appRoot = join(__dirname, "..");
const repoRoot = join(appRoot, "..", "..");
const serverPath = join(appRoot, "preview", "server.js");
const basePort = 5000 + (process.pid % 400);

function requestJson(port, method, path, body = "", headers = {}) {
  return new Promise((resolve, reject) => {
    const payload = Buffer.isBuffer(body) ? body : Buffer.from(body, "utf8");
    const req = http.request(
      {
        hostname: "127.0.0.1",
        method,
        path,
        port,
        timeout: 30000,
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
            reject(new Error(`Invalid JSON from ${method} ${path}: ${error.message}; body=${text.slice(0, 240)}`));
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
  for (let attempt = 0; attempt < 50; attempt += 1) {
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

function verifiedSessionEnv(role = "hr_operator") {
  return {
    BITWEEN_AUTH_CONFIGURED: "true",
    BITWEEN_SESSION_JWT_VERIFIED: "true",
    BITWEEN_SESSION_JWT_ISSUER: "https://auth.example.com",
    BITWEEN_SESSION_JWT_AUDIENCE: "bitween-platform",
    BITWEEN_SESSION_JWT_SUBJECT: "user-archive-reviewer",
    BITWEEN_SESSION_JWT_EXPIRES_AT_UNIX: "4102444800",
    BITWEEN_WEBAUTHN_USER_VERIFIED: "true",
    BITWEEN_SESSION_ACR_LEVEL: "sensitive",
    BITWEEN_SESSION_ACR_EVENT_AT_UNIX: "1",
    BITWEEN_SESSION_ROLE: role,
    BITWEEN_SESSION_AUTHZ_POLICY_ID: "bitween.authz.rbac-abac-pbac.v1",
    BITWEEN_SESSION_AUTHZ_TENANT_ID: "tenant-acme",
    BITWEEN_SESSION_AUTHZ_LEGAL_ENTITY: "Acme",
    BITWEEN_SESSION_AUTHZ_WORKPLACE: "Seoul"
  };
}

function multipartBody(content, fileName, contentType = "text/csv") {
  const boundary = `bitween-${process.pid}-${Math.random().toString(16).slice(2)}`;
  const payload = Buffer.isBuffer(content) ? content : Buffer.from(String(content), "utf8");
  const head = Buffer.from([
    `--${boundary}`,
    `Content-Disposition: form-data; name="file"; filename="${fileName}"`,
    `Content-Type: ${contentType}`,
    "",
    ""
  ].join("\r\n"), "utf8");
  const tail = Buffer.from(`\r\n--${boundary}--\r\n`, "utf8");
  const body = Buffer.concat([head, payload, tail]);
  return { body, headers: { "content-type": `multipart/form-data; boundary=${boundary}` } };
}

const crc32Table = Array.from({ length: 256 }, (_, index) => {
  let value = index;
  for (let bit = 0; bit < 8; bit += 1) {
    value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
  }
  return value >>> 0;
});

function crc32(buffer) {
  let value = 0xffffffff;
  for (const byte of buffer) {
    value = crc32Table[(value ^ byte) & 0xff] ^ (value >>> 8);
  }
  return (value ^ 0xffffffff) >>> 0;
}

function buildZip(entries) {
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const entry of entries) {
    const name = Buffer.from(entry.name, "utf8");
    const source = Buffer.isBuffer(entry.body) ? entry.body : Buffer.from(String(entry.body), "utf8");
    const compressed = entry.deflate ? zlib.deflateRawSync(source) : source;
    const method = entry.deflate ? 8 : 0;
    const checksum = crc32(source);
    const localHeader = Buffer.alloc(30);
    localHeader.writeUInt32LE(0x04034b50, 0);
    localHeader.writeUInt16LE(20, 4);
    localHeader.writeUInt16LE(0, 6);
    localHeader.writeUInt16LE(method, 8);
    localHeader.writeUInt32LE(0, 10);
    localHeader.writeUInt32LE(checksum, 14);
    localHeader.writeUInt32LE(compressed.length, 18);
    localHeader.writeUInt32LE(source.length, 22);
    localHeader.writeUInt16LE(name.length, 26);
    localHeader.writeUInt16LE(0, 28);
    localParts.push(localHeader, name, compressed);

    const centralHeader = Buffer.alloc(46);
    centralHeader.writeUInt32LE(0x02014b50, 0);
    centralHeader.writeUInt16LE(20, 4);
    centralHeader.writeUInt16LE(20, 6);
    centralHeader.writeUInt16LE(0, 8);
    centralHeader.writeUInt16LE(method, 10);
    centralHeader.writeUInt32LE(0, 12);
    centralHeader.writeUInt32LE(checksum, 16);
    centralHeader.writeUInt32LE(compressed.length, 20);
    centralHeader.writeUInt32LE(source.length, 24);
    centralHeader.writeUInt16LE(name.length, 28);
    centralHeader.writeUInt16LE(0, 30);
    centralHeader.writeUInt16LE(0, 32);
    centralHeader.writeUInt16LE(0, 34);
    centralHeader.writeUInt16LE(0, 36);
    centralHeader.writeUInt32LE(0, 38);
    centralHeader.writeUInt32LE(offset, 42);
    centralParts.push(centralHeader, name);
    offset += localHeader.length + name.length + compressed.length;
  }
  const centralDirectory = Buffer.concat(centralParts);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(centralDirectory.length, 12);
  end.writeUInt32LE(offset, 16);
  end.writeUInt16LE(0, 20);
  return Buffer.concat([...localParts, centralDirectory, end]);
}

function requireIntake(response, label, fileName) {
  const intakes = response.body.intakes || [];
  const intake = fileName
    ? intakes.find((item) => item.original_file_name === fileName)
    : intakes[0];
  if (response.statusCode !== 200 || response.body.schema !== "bitween.archive.intake-store.v1" || !intake?.id) {
    throw new Error(`${label} should return a live archive intake store response: ${JSON.stringify(response)}`);
  }
  return intake;
}

function issueCodes(intake) {
  return new Set((intake.guidance_items || []).map((item) => `${item.code}:${item.column || ""}`));
}

function mappingFor(intake, sourceColumn) {
  return (intake.field_mappings || []).find((mapping) => mapping.source_column === sourceColumn);
}

async function patchMappings(port, intake, mappings) {
  return requestJson(
    port,
    "PATCH",
    `/api/archive/v1/intake/${encodeURIComponent(intake.id)}/field-mappings`,
    JSON.stringify({ sourceFingerprint: intake.source_fingerprint, mappings }),
    { "content-type": "application/json" }
  );
}

async function verifyHrPreambleAndCustomMapping(port) {
  const upload = multipartBody(
    [
      "근로자 명부",
      "작성일,2026-06-10",
      "이름,특이값,메모",
      "ACME-SAMPLE-EMPLOYEE,People,Followup"
    ].join("\n"),
    "acme-hr-preamble.csv"
  );
  const uploaded = await requestJson(port, "POST", "/api/archive/v1/intake", upload.body, upload.headers);
  const intake = requireIntake(uploaded, "HR preamble story", "acme-hr-preamble.csv");
  const issues = issueCodes(intake);
  if (intake.database_target !== "hr_employee_staging") {
    throw new Error(`HR preamble story should target hr_employee_staging, got ${intake.database_target}`);
  }
  for (const expected of ["confirm_missing_required_data:department", "explain_column:특이값", "explain_column:메모"]) {
    if (!issues.has(expected)) {
      throw new Error(`HR preamble story missing ${expected}: ${JSON.stringify(intake.guidance_items)}`);
    }
  }
  if (mappingFor(intake, "근로자 명부") || mappingFor(intake, "작성일")) {
    throw new Error(`Preamble rows must not become mapped columns: ${JSON.stringify(intake.field_mappings)}`);
  }
  const memo = mappingFor(intake, "메모");
  if (!memo || memo.target_field !== "source_payload" || memo.status !== "preserved" || memo.value_shape !== "identifier") {
    throw new Error(`Unclear HR columns should be preserved with sanitized value-shape hints: ${JSON.stringify(memo)}`);
  }

  const reviewed = await patchMappings(port, intake, [
    { sourceColumn: "특이값", targetTable: "hr_employee_staging", targetField: "department", status: "confirmed" },
    { sourceColumn: "메모", targetTable: "hr_employee_staging", targetField: "source_payload", status: "confirmed" }
  ]);
  const reviewedIntake = reviewed.body.intakes?.find((item) => item.id === intake.id);
  if (reviewed.statusCode !== 200 || !reviewedIntake?.postgres_ready || reviewedIntake.guidance_items?.length !== 0) {
    throw new Error(`HR mapping review should clear guidance and prepare staging: ${JSON.stringify(reviewed)}`);
  }
}

async function verifyPayrollHeaderVarianceAndFailClosedMutation(port) {
  const upload = multipartBody(
    [
      "급여 입력",
      "직원키,지급액,비고",
      "ACME-SAMPLE-001,3000000,June payroll"
    ].join("\n"),
    "acme-payroll-headers.csv"
  );
  const uploaded = await requestJson(port, "POST", "/api/archive/v1/intake", upload.body, upload.headers);
  const intake = requireIntake(uploaded, "Payroll header variance story", "acme-payroll-headers.csv");
  if (intake.database_target !== "payroll_input_staging") {
    throw new Error(`Payroll story should target payroll_input_staging, got ${intake.database_target}`);
  }
  const pay = mappingFor(intake, "지급액");
  if (!pay || pay.target_field !== "gross_pay" || pay.value_shape !== "numeric_normalized") {
    throw new Error(`Payroll amount should map to gross pay with a numeric normalization hint: ${JSON.stringify(pay)}`);
  }
  if (!issueCodes(intake).has("confirm_missing_required_data:employee_external_id")) {
    throw new Error(`Payroll story should require an explicit employee identifier mapping: ${JSON.stringify(intake.guidance_items)}`);
  }

  const stale = await requestJson(
    port,
    "PATCH",
    `/api/archive/v1/intake/${encodeURIComponent(intake.id)}/field-mappings`,
    JSON.stringify({
      sourceFingerprint: "sha256:stale",
      mappings: [{ sourceColumn: "직원키", targetTable: "payroll_input_staging", targetField: "employee_external_id", status: "confirmed" }]
    }),
    { "content-type": "application/json" }
  );
  if (stale.statusCode === 200 || stale.body.ok !== false) {
    throw new Error(`Stale source-fingerprint mapping mutation must fail closed: ${JSON.stringify(stale)}`);
  }

  const reviewed = await patchMappings(port, intake, [
    { sourceColumn: "직원키", targetTable: "payroll_input_staging", targetField: "employee_external_id", status: "confirmed" },
    { sourceColumn: "비고", targetTable: "payroll_input_staging", targetField: "source_payload", status: "confirmed" }
  ]);
  const reviewedIntake = reviewed.body.intakes?.find((item) => item.id === intake.id);
  if (reviewed.statusCode !== 200 || !reviewedIntake?.postgres_ready || reviewedIntake.guidance_items?.length !== 0) {
    throw new Error(`Payroll mapping review should clear guidance and prepare staging: ${JSON.stringify(reviewed)}`);
  }
}

async function verifyEmptyReadableFileBlocksAdmission(port) {
  const upload = multipartBody("급여 입력\n", "payroll-empty.csv");
  const uploaded = await requestJson(port, "POST", "/api/archive/v1/intake", upload.body, upload.headers);
  const intake = requireIntake(uploaded, "Empty readable file story", "payroll-empty.csv");
  if (intake.postgres_ready || intake.status !== "needs_guidance") {
    throw new Error(`Empty readable file should block admission and require review: ${JSON.stringify(intake)}`);
  }
}

async function verifyZipBundleExtractsSafeInnerFiles(port) {
  const zip = buildZip([
    {
      name: "hr/acme-zip-hr.csv",
      deflate: true,
      body: [
        "근로자 명부",
        "작성일,2026-06-10",
        "이름,부서,메모",
        "ACME-ZIP-HR-001,People,ZIP upload"
      ].join("\n")
    },
    {
      name: "payroll/acme-zip-payroll.csv",
      body: [
        "급여 입력",
        "직원키,지급액,공제",
        "ACME-ZIP-HR-001,3000000,200000"
      ].join("\n")
    },
    {
      name: "../escape.csv",
      body: "이름,부서\nSHOULD-NOT-APPEAR,Security\n"
    }
  ]);
  const upload = multipartBody(zip, "acme-upload-bundle.zip", "application/zip");
  const uploaded = await requestJson(port, "POST", "/api/archive/v1/intake", upload.body, upload.headers);
  const hr = requireIntake(uploaded, "ZIP HR inner file story", "acme-upload-bundle.zip/hr/acme-zip-hr.csv");
  const payroll = requireIntake(uploaded, "ZIP payroll inner file story", "acme-upload-bundle.zip/payroll/acme-zip-payroll.csv");
  const names = (uploaded.body.intakes || []).map((item) => item.original_file_name);
  if (names.some((name) => String(name).includes("escape"))) {
    throw new Error(`Unsafe ZIP path traversal entries must not become intake rows: ${JSON.stringify(names)}`);
  }
  if (hr.object_uri !== payroll.object_uri || !hr.object_uri?.includes("/quarantine/") || !hr.object_uri?.endsWith(".zip")) {
    throw new Error(`ZIP inner records should share the quarantined original ZIP object: ${JSON.stringify({ hr, payroll })}`);
  }
  if (hr.database_target !== "hr_employee_staging" || mappingFor(hr, "이름")?.target_field !== "display_name" || mappingFor(hr, "부서")?.target_field !== "department") {
    throw new Error(`ZIP HR CSV should be extracted, classified, and mapped for review: ${JSON.stringify(hr)}`);
  }
  if (payroll.database_target !== "payroll_input_staging" || mappingFor(payroll, "지급액")?.target_field !== "gross_pay") {
    throw new Error(`ZIP payroll CSV should be extracted, classified, and mapped for review: ${JSON.stringify(payroll)}`);
  }
}

function createPreviewDomHarness() {
  const app = {
    _innerHTML: "",
    get innerHTML() {
      return this._innerHTML;
    },
    set innerHTML(value) {
      this._innerHTML = String(value || "");
    }
  };
  const toast = {
    classList: {
      add() {},
      remove() {}
    },
    textContent: ""
  };
  const document = {
    documentElement: { lang: "" },
    title: "",
    getElementById(id) {
      if (id === "app") return app;
      if (id === "toast") return toast;
      return null;
    },
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    }
  };
  return { app, document, toast };
}

function createMappingForm(intake, overrides = {}) {
  const rows = (intake.field_mappings || []).map((mapping) => ({
    dataset: { sourceColumn: mapping.source_column || "" },
    querySelector(selector) {
      if (selector !== "[data-field-target]") return null;
      return { value: overrides[mapping.source_column] || mapping.target_field || "source_payload" };
    }
  }));
  return {
    querySelectorAll(selector) {
      return selector === "[data-field-mapping-row]" ? rows : [];
    }
  };
}

async function loadPreviewAppInHarness(port) {
  const { app, document, toast } = createPreviewDomHarness();
  const source = readFileSync(join(appRoot, "preview", "app.js"), "utf8");
  const instrumented = source.replace(
    "\nboot().catch((error) => {",
    "\nglobalThis.__bitweenPreview = { state, render, addArchiveIntake, updateArchiveFieldMappings };\nglobalThis.__bitweenBoot = boot().catch((error) => {"
  );
  if (!instrumented.includes("__bitweenPreview")) {
    throw new Error("Preview app instrumentation failed; cannot run archive UI usage stories.");
  }
  const context = {
    Blob,
    console,
    EventSource: undefined,
    File,
    FormData,
    setTimeout,
    clearTimeout,
    document,
    fetch(input, init) {
      const path = String(input);
      const url = path.startsWith("http://") || path.startsWith("https://")
        ? path
        : `http://127.0.0.1:${port}${path.startsWith("/") ? path : `/${path}`}`;
      return fetch(url, init);
    },
    window: {
      clearTimeout,
      location: {
        assign() {},
        reload() {}
      },
      setTimeout
    }
  };
  context.globalThis = context;
  context.window.window = context.window;
  vm.runInNewContext(instrumented, context, {
    filename: "preview/app.js",
    timeout: 30000
  });
  await context.__bitweenBoot;
  return { app, context, toast };
}

async function verifyArchiveUiActualUsageStories(port) {
  const { app, context, toast } = await loadPreviewAppInHarness(port);
  const preview = context.__bitweenPreview;
  preview.state.activeId = "archive";
  preview.render();
  if (!app.innerHTML.includes("data-intake-file") || !app.innerHTML.includes("압축 파일") || !app.innerHTML.includes("내부 표 파일")) {
    throw new Error("Archive UI must expose the actual file input and clear ZIP inner-file expectations before upload.");
  }

  const normalZip = new File([buildZip([
    {
      name: "hr/acme-ui-hr.csv",
      deflate: true,
      body: "이름,부서,메모\nACME-UI-HR-001,People,normal zip upload\n"
    },
    {
      name: "payroll/acme-ui-payroll.csv",
      body: "급여 입력\n직원키,지급액,공제\nACME-UI-HR-001,3000000,200000\n"
    },
    {
      name: "../malicious.csv",
      body: "이름,부서\nSHOULD-NOT-RENDER,Security\n"
    }
  ])], "acme-ui-upload.zip", { type: "application/zip" });
  await preview.addArchiveIntake(normalZip);
  const namesAfterNormal = preview.state.archiveIntakes.map((item) => item.original_file_name || item.file_name || "");
  if (!namesAfterNormal.includes("acme-ui-upload.zip/hr/acme-ui-hr.csv") || !namesAfterNormal.includes("acme-ui-upload.zip/payroll/acme-ui-payroll.csv")) {
    throw new Error(`Actual UI ZIP upload should render safe inner HR/payroll review rows: ${JSON.stringify(namesAfterNormal)}`);
  }
  if (app.innerHTML.includes("SHOULD-NOT-RENDER") || namesAfterNormal.some((name) => name.includes("malicious"))) {
    throw new Error("Actual UI ZIP upload must not render path traversal members or their contents.");
  }
  if (!app.innerHTML.includes("data-intake-field-mapping-form") || !app.innerHTML.includes("archive-field-map-row")) {
    throw new Error("Actual UI ZIP upload should show mapping review controls, not a blind success wall.");
  }
  if (!toast.textContent.includes("추가")) {
    throw new Error(`Actual UI normal upload should produce a recoverable success toast, got: ${toast.textContent}`);
  }

  const emptyFile = new File(["급여 입력\n"], "acme-ui-empty.csv", { type: "text/csv" });
  await preview.addArchiveIntake(emptyFile);
  const emptyIntake = preview.state.archiveIntakes.find((item) => item.original_file_name === "acme-ui-empty.csv");
  if (!emptyIntake || emptyIntake.postgres_ready || !app.innerHTML.includes("읽을 수 있는 표 구조가 필요합니다")) {
    throw new Error(`Actual UI edge-case upload should preserve the empty file as a review blocker: ${JSON.stringify(emptyIntake)}`);
  }

  const payrollIntake = preview.state.archiveIntakes.find((item) => item.original_file_name === "acme-ui-upload.zip/payroll/acme-ui-payroll.csv");
  if (!payrollIntake) {
    throw new Error(`Actual UI payroll ZIP intake missing before mapping save: ${JSON.stringify(preview.state.archiveIntakes)}`);
  }
  await preview.updateArchiveFieldMappings(payrollIntake.id, createMappingForm(payrollIntake, {
    "직원키": "employee_external_id",
    "지급액": "gross_pay",
    "공제": "deduction_total"
  }));
  const reviewedPayroll = preview.state.archiveIntakes.find((item) => item.id === payrollIntake.id);
  if (!reviewedPayroll?.postgres_ready || reviewedPayroll.guidance_items?.length) {
    throw new Error(`Actual UI mapping save should clear payroll guidance and show staging readiness: ${JSON.stringify({
      reviewedPayroll,
      archiveError: preview.state.archiveError,
      payrollMappingsBeforeSave: payrollIntake.field_mappings,
      intakes: preview.state.archiveIntakes.map((item) => ({ id: item.id, name: item.original_file_name, status: item.status }))
    })}`);
  }

  const countBeforeMalicious = preview.state.archiveIntakes.length;
  const maliciousZip = new File([buildZip(Array.from({ length: 513 }, (_, index) => ({
    name: `payload-${index}.csv`,
    body: "이름,부서\nACME,People\n"
  })))], "too-many-entries.zip", { type: "application/zip" });
  await preview.addArchiveIntake(maliciousZip);
  if (preview.state.archiveIntakes.length !== countBeforeMalicious) {
    throw new Error("Actual UI malicious ZIP failure must preserve the existing review queue for operator recovery.");
  }
  if (!preview.state.archiveError || !app.innerHTML.includes("압축 파일 내부 항목 수")) {
    throw new Error(`Actual UI malicious ZIP failure should show a business-readable recovery message: ${JSON.stringify(preview.state.archiveError)}`);
  }
}

function verifyPostgresMappingIssueRefreshParity() {
  const sourcePath = join(repoRoot, "crates", "payroll-api", "src", "bin", "archive_intake_store.rs");
  const source = readFileSync(sourcePath, "utf8");
  const refreshStart = source.indexOf("async fn refresh_postgres_");
  const refreshEnd = source.indexOf("async fn refresh_postgres_intake_review_state", refreshStart);
  const refreshBody = refreshStart >= 0 && refreshEnd > refreshStart ? source.slice(refreshStart, refreshEnd) : "";
  if (!refreshBody.includes("confirm_missing_required_data") || !refreshBody.includes("explain_column")) {
    throw new Error("PostgreSQL field-mapping review must recalculate both missing required-field guidance and unclear-column guidance, not only one class of issue.");
  }
  if (!refreshBody.includes("field_mapping_reviewed")) {
    throw new Error("PostgreSQL field-mapping issue refresh must leave a bounded review resolution marker.");
  }
  const upsertStart = source.indexOf("async fn upsert_postgres_mapping_template");
  const upsertEnd = source.indexOf("async fn refresh_postgres_mapping_issues", upsertStart);
  const upsertBody = upsertStart >= 0 && upsertEnd > upsertStart ? source.slice(upsertStart, upsertEnd) : "";
  if (!upsertBody.includes("is_review_blocking")) {
    throw new Error("PostgreSQL mapping templates must stay draft while any unresolved/unclear field mapping remains review-blocking.");
  }
}

function verifyVisualAffordanceStandards() {
  const app = readFileSync(join(appRoot, "preview", "app.js"), "utf8");
  const styles = readFileSync(join(appRoot, "preview", "styles.css"), "utf8");
  const catalog = readFileSync(join(appRoot, "src", "i18n", "catalog.json"), "utf8");
  for (const required of ["archiveMappingEditor", "data-intake-field-mapping-form", "archiveValueShapeText", "/field-mappings"]) {
    if (!app.includes(required)) {
      throw new Error(`Archive mapping UI is missing ${required}`);
    }
  }
  for (const required of [".archive-field-mapping", ".archive-field-map-grid", ".archive-field-map-row"]) {
    if (!styles.includes(required)) {
      throw new Error(`Archive mapping layout is missing ${required}`);
    }
  }
  for (const required of ["값 정리: 숫자 형식", "값 보호: 민감 식별자", "값 설명: 원문은 숨김"]) {
    if (!catalog.includes(required)) {
      throw new Error(`Korean catalog is missing context-aware sanitized value-shape copy: ${required}`);
    }
  }
  for (const required of ["압축 파일", "내부 표 파일"]) {
    if (!catalog.includes(required)) {
      throw new Error(`Korean archive intake UX copy must set ZIP expectations clearly: ${required}`);
    }
  }
  for (const required of ["extractZipIntakeSamples", "isSafeZipEntryName", "maxZipTotalExtractedBytes"]) {
    if (!readFileSync(serverPath, "utf8").includes(required)) {
      throw new Error(`Preview archive intake must include bounded ZIP extraction guard: ${required}`);
    }
  }
}

function prebuildArchiveStoreTarget() {
  const result = spawnSync("buck2", ["build", "//crates/payroll-api:archive_intake_store"], {
    cwd: repoRoot,
    encoding: "utf8",
    timeout: 60000
  });
  if (result.error || result.status !== 0) {
    const detail = result.error ? result.error.message : `${result.stderr || result.stdout}`.trim();
    throw new Error(`Buck2 archive intake target prebuild failed before live story verification: ${detail}`);
  }
}

async function main() {
  verifyPostgresMappingIssueRefreshParity();
  verifyVisualAffordanceStandards();
  prebuildArchiveStoreTarget();
  const tempDir = mkdtempSync(join(tmpdir(), "bitween-archive-stories-"));
  try {
    await withRustFsMock(async ({ env: rustFsEnv, uploads }) => {
      await withServer(basePort, { ...localStoreEnv(tempDir), ...verifiedSessionEnv("hr_operator"), ...rustFsEnv }, async () => {
        await verifyHrPreambleAndCustomMapping(basePort);
        await verifyPayrollHeaderVarianceAndFailClosedMutation(basePort);
        await verifyEmptyReadableFileBlocksAdmission(basePort);
        await verifyZipBundleExtractsSafeInnerFiles(basePort);
        await verifyArchiveUiActualUsageStories(basePort);
        if (uploads.length < 7 || uploads.some((upload) => !upload.path.startsWith("/bitween-archive-originals/quarantine/") || !upload.sha256)) {
          throw new Error(`Every archive story should store the original in RustFS quarantine with checksum metadata: ${JSON.stringify(uploads)}`);
        }
      });
    });
  } finally {
    rmSync(tempDir, { force: true, recursive: true });
  }
  for (const relativePath of ["archive/intake.json", "hr/employees.json"]) {
    if (existsSync(join(tempDir, relativePath))) {
      throw new Error(`Temporary local review store was not removed: ${relativePath}`);
    }
  }
  console.log("Archive intake API and actual UI usage stories, mutation guard, malicious ZIP handling, and visual affordance standards passed.");
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
