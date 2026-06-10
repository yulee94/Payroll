import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { spawn } from "node:child_process";
import http from "node:http";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appRoot = join(__dirname, "..");
const serverPath = join(appRoot, "preview", "server.js");
const packagePath = join(appRoot, "package.json");
const workflowPath = join(appRoot, "..", "..", ".github", "workflows", "tests.yml");
const runtimeVerifierPath = join(__dirname, "verify-runtime-data-mode.mjs");
const errors = [];

const serverSource = readFileSync(serverPath, "utf8");
const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
const workflowSource = readFileSync(workflowPath, "utf8");
const runtimeVerifierSource = readFileSync(runtimeVerifierPath, "utf8");

function requireText(source, text, message) {
  if (!source.includes(text)) errors.push(message);
}

function assertStaticSecurityContracts() {
  if (packageJson.scripts?.["verify:security-gates"] !== "node scripts/verify-security-gates.mjs") {
    errors.push("package.json must expose verify:security-gates for local and CI security evidence.");
  }
  requireText(workflowSource, "npm run verify:security-gates", ".github/workflows/tests.yml must run verify:security-gates in CI.");
  requireText(runtimeVerifierSource, "verify-security-gates.mjs", "verify-runtime-data-mode.mjs must guard that security gate verification remains wired.");
  requireText(serverSource, "requireSameOriginMutation", "preview/server.js must reject cross-origin mutable requests before storage side effects.");
  requireText(serverSource, "decodeRequestPath", "preview/server.js must safely decode malformed request paths before route dispatch.");
  requireText(serverSource, "request_path_invalid", "malformed request paths must return a stable fail-closed error code instead of crashing.");
  requireText(serverSource, "csrf_origin_rejected", "same-origin guard must return a stable origin rejection code.");
  requireText(serverSource, "csrf_fetch_site_rejected", "same-origin guard must use Fetch Metadata to reject cross-site mutation attempts.");
  requireText(serverSource, "enforceRateLimit", "preview/server.js must enforce route rate limits before body parsing/storage side effects.");
  requireText(serverSource, "rateLimitBuckets", "preview/server.js must keep bounded in-memory rate buckets for local review.");
  requireText(serverSource, "x-ratelimit-limit", "preview/server.js must emit standard rate limit evidence headers.");
  requireText(serverSource, "rate_limit_exceeded", "preview/server.js must return a stable rate-limit error code.");
  requireText(serverSource, "readBinaryBody(req)", "archive uploads must remain behind the bounded body reader after security gates.");
  requireText(serverSource, "__Host-bitween_session", "auth sign-out must clear a host-only session cookie name.");
  requireText(serverSource, "clearSessionCookieHeader", "auth sign-out must use one hardened session-cookie clear helper.");
  requireText(serverSource, "Max-Age=0", "auth sign-out must expire the session cookie immediately.");
  requireText(serverSource, "HttpOnly", "session cookies must be inaccessible to client-side scripts.");
  requireText(serverSource, "SameSite=Lax", "session cookies must use SameSite=Lax for CSRF resistance.");
  requireText(serverSource, "Secure", "session cookies must be HTTPS-only in production.");
}

function requestJson(port, method, path, body = "", headers = {}) {
  const payload = Buffer.isBuffer(body) ? body : Buffer.from(body, "utf8");
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: "127.0.0.1",
      method,
      path,
      port,
      timeout: 10000,
      headers: {
        "content-length": String(payload.length),
        ...headers,
      },
    }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        const text = Buffer.concat(chunks).toString("utf8");
        try {
          resolve({ body: text ? JSON.parse(text) : {}, headers: res.headers, statusCode: res.statusCode || 0 });
        } catch (error) {
          reject(new Error(`Invalid JSON from ${method} ${path}: ${error.message}; body=${text.slice(0, 160)}`));
        }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error(`Timed out requesting ${method} ${path}`)));
    req.end(payload);
  });
}

function requestText(port, path) {
  return new Promise((resolve, reject) => {
    const req = http.request({ hostname: "127.0.0.1", method: "GET", path, port, timeout: 10000 }, (res) => {
      res.resume();
      res.on("end", () => resolve({ headers: res.headers, statusCode: res.statusCode || 0 }));
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
      BITWEEN_AUTH_RATE_LIMIT_MAX: "2",
      BITWEEN_HTTP_TELEMETRY: "off",
      BITWEEN_MUTATION_RATE_LIMIT_MAX: "2",
      BITWEEN_RATE_LIMIT_WINDOW_MS: "60000",
      PORT: String(port),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let stderr = "";
  child.stderr.on("data", (chunk) => { stderr += chunk.toString("utf8"); });
  child.stdout.on("data", () => {});
  return { child, stderr: () => stderr };
}

async function waitForServer(port) {
  let lastError;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await requestText(port, "/");
      if (response.statusCode === 200) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw lastError || new Error("Preview server did not start.");
}

function assertResponse(response, expectedStatus, expectedError, label) {
  if (response.statusCode !== expectedStatus || response.body.error !== expectedError) {
    errors.push(`${label} expected ${expectedStatus}/${expectedError}; got ${JSON.stringify(response)}`);
  }
}

async function assertRuntimeSecurity() {
  const port = 5600 + (process.pid % 300);
  const server = launchServer(port);
  try {
    await waitForServer(port);
    const malformedPath = await requestJson(port, "GET", "/%E0%A4%A");
    assertResponse(malformedPath, 400, "request_path_invalid", "malformed percent-encoded path");

    const crossOrigin = await requestJson(port, "POST", "/api/auth/v1/signout", "", {
      origin: "https://attacker.example",
      "sec-fetch-site": "cross-site",
    });
    assertResponse(crossOrigin, 403, "csrf_origin_rejected", "cross-origin mutation");

    const crossSite = await requestJson(port, "POST", "/api/auth/v1/signout", "", {
      "sec-fetch-site": "same-site",
    });
    assertResponse(crossSite, 403, "csrf_fetch_site_rejected", "Fetch Metadata mutation");

    const sameOrigin = await requestJson(port, "POST", "/api/auth/v1/signout", "", {
      origin: `http://127.0.0.1:${port}`,
      "sec-fetch-site": "same-origin",
    });
    assertResponse(sameOrigin, 503, "auth_route_unconfigured", "same-origin signout pass-through");
    if (sameOrigin.headers["x-ratelimit-limit"] !== "2") {
      errors.push("same-origin mutable route must include rate limit headers.");
    }
    const setCookie = Array.isArray(sameOrigin.headers["set-cookie"])
      ? sameOrigin.headers["set-cookie"].join("; ")
      : String(sameOrigin.headers["set-cookie"] || "");
    for (const required of ["__Host-bitween_session=", "Max-Age=0", "Path=/", "HttpOnly", "SameSite=Lax", "Secure"]) {
      if (!setCookie.includes(required)) {
        errors.push(`same-origin signout must clear the hardened session cookie with ${required}; got ${setCookie || "<missing>"}`);
      }
    }
    if (/Domain=/i.test(setCookie)) {
      errors.push(`__Host- session cookie clear header must not set Domain; got ${setCookie}`);
    }

    const first = await requestJson(port, "GET", "/api/auth/v1/routes");
    const second = await requestJson(port, "GET", "/api/auth/v1/routes");
    const third = await requestJson(port, "GET", "/api/auth/v1/routes");
    if (first.statusCode !== 200 || second.statusCode !== 200) {
      errors.push(`auth route discovery should allow the first two requests: ${JSON.stringify([first, second])}`);
    }
    assertResponse(third, 429, "rate_limit_exceeded", "auth route rate limit");
    if (third.headers["x-ratelimit-limit"] !== "2" || third.headers["x-ratelimit-remaining"] !== "0") {
      errors.push("rate limited response must include limit and remaining headers.");
    }
  } finally {
    server.child.kill("SIGTERM");
  }
}

assertStaticSecurityContracts();
await assertRuntimeSecurity();

if (errors.length > 0) {
  console.error("Security gate verification failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("Security gate verification passed.");
