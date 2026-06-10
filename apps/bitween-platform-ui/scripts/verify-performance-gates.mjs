import { readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { spawn } from "node:child_process";
import http from "node:http";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appRoot = join(__dirname, "..");
const previewRoot = join(appRoot, "preview");
const serverPath = join(previewRoot, "server.js");
const packagePath = join(appRoot, "package.json");
const workflowPath = join(appRoot, "..", "..", ".github", "workflows", "tests.yml");
const runtimeVerifierPath = join(__dirname, "verify-runtime-data-mode.mjs");

const routeLatencyBudgetMs = 1500;
const budgets = {
  appJsMaxBytes: 160 * 1024,
  catalogMaxBytes: 480 * 1024,
  indexHtmlMaxBytes: 8 * 1024,
  stylesCssMaxBytes: 80 * 1024,
};
const errors = [];

const serverSource = readFileSync(serverPath, "utf8");
const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
const workflowSource = readFileSync(workflowPath, "utf8");
const runtimeVerifierSource = readFileSync(runtimeVerifierPath, "utf8");

function requireText(source, text, message) {
  if (!source.includes(text)) errors.push(message);
}

function assertFileBudget(relativePath, maxBytes, label) {
  const size = statSync(join(appRoot, relativePath)).size;
  if (size > maxBytes) {
    errors.push(`${label} exceeds the shell budget: ${size} bytes > ${maxBytes} bytes.`);
  }
}

function assertStaticContracts() {
  if (packageJson.scripts?.["verify:performance-gates"] !== "node scripts/verify-performance-gates.mjs") {
    errors.push("package.json must expose verify:performance-gates for local and CI performance guard evidence.");
  }
  requireText(workflowSource, "npm run verify:performance-gates", ".github/workflows/tests.yml must run verify:performance-gates in CI.");
  requireText(runtimeVerifierSource, "verify-performance-gates.mjs", "verify-runtime-data-mode.mjs must guard that performance verification remains wired.");
  requireText(serverSource, "routeLatencyBudgetMs", "preview/server.js must declare a route latency budget.");
  requireText(serverSource, "server-timing", "preview/server.js must expose Server-Timing route latency evidence.");
  requireText(serverSource, "x-bitween-route", "preview/server.js must expose sanitized route templates for latency smoke checks.");
  requireText(serverSource, "bitween.telemetry.http.v1", "preview/server.js must emit a stable HTTP telemetry schema.");
  requireText(serverSource, "http.request.method", "HTTP telemetry must use OpenTelemetry semantic field names for request method.");
  requireText(serverSource, "http.response.status_code", "HTTP telemetry must use OpenTelemetry semantic field names for response status.");
  requireText(serverSource, "http.route", "HTTP telemetry must use OpenTelemetry semantic field names for sanitized route templates.");
  requireText(serverSource, "maxUploadBytes = 50 * 1024 * 1024", "archive intake must cap uploaded files for local review.");
  requireText(serverSource, "maxExtractedXmlBytes = 2 * 1024 * 1024", "archive intake must cap extracted spreadsheet XML.");
  requireText(serverSource, "maxOutputLength", "archive intake zip inflation must use a bounded output length.");
  requireText(serverSource, "readZipEntryBuffer", "archive intake must route ZIP entry extraction through a bounded buffer reader.");
  requireText(serverSource, "readBinaryBody(req)", "archive intake must read uploads through the bounded binary body reader.");
}

function request(port, path) {
  const startedAt = process.hrtime.bigint();
  return new Promise((resolve, reject) => {
    const req = http.request({ hostname: "127.0.0.1", method: "GET", path, port, timeout: 10000 }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => resolve({
        body: Buffer.concat(chunks),
        elapsedMs: Number(process.hrtime.bigint() - startedAt) / 1_000_000,
        headers: res.headers,
        statusCode: res.statusCode || 0,
      }));
    });
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error(`Timed out requesting ${path}`)));
    req.end();
  });
}

function launchServer(port) {
  const child = spawn(process.execPath, [serverPath, String(port)], {
    cwd: appRoot,
    env: {
      ...process.env,
      BITWEEN_HTTP_TELEMETRY: "off",
      BITWEEN_ROUTE_LATENCY_BUDGET_MS: String(routeLatencyBudgetMs),
      PORT: String(port),
    },
    stdio: ["ignore", "pipe", "pipe"],
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
      const response = await request(port, "/api/auth/v1/routes");
      if (response.statusCode === 200) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw lastError || new Error("Preview server did not start.");
}

function parseServerTiming(value) {
  const match = String(value || "").match(/bitween;dur=([0-9.]+)/);
  return match ? Number(match[1]) : Number.NaN;
}

async function assertRouteTiming(port, path, expectedRoute) {
  const response = await request(port, path);
  if (response.statusCode !== 200) {
    errors.push(`${path} returned ${response.statusCode}, expected 200 for latency smoke.`);
    return;
  }
  const timingMs = parseServerTiming(response.headers["server-timing"]);
  if (!Number.isFinite(timingMs)) {
    errors.push(`${path} must include a parseable Server-Timing bitween duration.`);
  } else if (timingMs > routeLatencyBudgetMs) {
    errors.push(`${path} exceeded route latency budget: ${timingMs}ms > ${routeLatencyBudgetMs}ms.`);
  }
  if (response.elapsedMs > routeLatencyBudgetMs * 2) {
    errors.push(`${path} wall-clock latency is too high for local smoke: ${response.elapsedMs.toFixed(1)}ms.`);
  }
  if (response.headers["x-bitween-route"] !== expectedRoute) {
    errors.push(`${path} must expose sanitized route ${expectedRoute}; got ${response.headers["x-bitween-route"] || "<missing>"}.`);
  }
  if (response.headers["x-bitween-route-budget-ms"] !== String(routeLatencyBudgetMs)) {
    errors.push(`${path} must expose the route latency budget header.`);
  }
}

async function assertRuntimeRouteBudgets() {
  const port = 5000 + (process.pid % 500);
  const server = launchServer(port);
  try {
    await waitForServer(port);
    await assertRouteTiming(port, "/", "/");
    await assertRouteTiming(port, "/app.js", "/app.js");
    await assertRouteTiming(port, "/styles.css", "/styles.css");
    await assertRouteTiming(port, "/api/auth/v1/routes", "/api/auth/v1/routes");
  } finally {
    server.child.kill("SIGTERM");
  }
}

assertStaticContracts();
assertFileBudget("preview/app.js", budgets.appJsMaxBytes, "preview app.js");
assertFileBudget("preview/styles.css", budgets.stylesCssMaxBytes, "preview styles.css");
assertFileBudget("preview/index.html", budgets.indexHtmlMaxBytes, "preview index.html");
assertFileBudget("src/i18n/catalog.json", budgets.catalogMaxBytes, "i18n catalog.json");
await assertRuntimeRouteBudgets();

if (errors.length > 0) {
  console.error("Performance gate verification failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("Performance gate verification passed.");
