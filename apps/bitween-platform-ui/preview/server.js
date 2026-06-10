const http = require("node:http");
const https = require("node:https");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const zlib = require("node:zlib");

const root = __dirname;
const repoRoot = path.resolve(root, "..", "..", "..");
const port = Number(process.env.PORT || process.argv[2] || 4174);
const maxUploadBytes = 50 * 1024 * 1024;
const maxExtractedXmlBytes = 2 * 1024 * 1024;
const maxZipEntries = 512;
const maxZipMemberBytes = 8 * 1024 * 1024;
const maxZipTotalExtractedBytes = 16 * 1024 * 1024;
const maxZipTextSampleBytes = 64 * 1024;
const routeLatencyBudgetMs = Number(process.env.BITWEEN_ROUTE_LATENCY_BUDGET_MS || 1500);
const rateLimitWindowMs = Number(process.env.BITWEEN_RATE_LIMIT_WINDOW_MS || 60_000);
const defaultMutableRateLimitMax = Number(process.env.BITWEEN_MUTATION_RATE_LIMIT_MAX || 60);
const authRateLimitMax = Number(process.env.BITWEEN_AUTH_RATE_LIMIT_MAX || 30);
const clients = new Set();
const rateLimitBuckets = new Map();
const sessionCookieName = "__Host-bitween_session";
const sessionEnvKeys = [
  "BITWEEN_AUTH_CONFIGURED",
  "BITWEEN_SESSION_JWT_VERIFIED",
  "BITWEEN_SESSION_JWT_ISSUER",
  "BITWEEN_SESSION_JWT_AUDIENCE",
  "BITWEEN_SESSION_JWT_SUBJECT",
  "BITWEEN_SESSION_JWT_EXPIRES_AT_UNIX",
  "BITWEEN_WEBAUTHN_USER_VERIFIED",
  "BITWEEN_SESSION_ACR_LEVEL",
  "BITWEEN_SESSION_ACR_EVENT_AT_UNIX",
  "BITWEEN_SESSION_ROLE",
  "BITWEEN_SESSION_AUTHZ_POLICY_ID",
  "BITWEEN_SESSION_AUTHZ_TENANT_ID",
  "BITWEEN_SESSION_AUTHZ_LEGAL_ENTITY",
  "BITWEEN_SESSION_AUTHZ_WORKPLACE"
];
const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".js": "text/javascript; charset=utf-8"
};

const securityHeaders = {
  "content-security-policy": [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "connect-src 'self'",
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'"
  ].join("; "),
  "cross-origin-opener-policy": "same-origin",
  "cross-origin-resource-policy": "same-origin",
  "origin-agent-cluster": "?1",
  "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), bluetooth=()",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY"
};

const noCacheHeaders = {
  ...securityHeaders,
  "cache-control": "no-store, no-cache, must-revalidate, max-age=0",
  "pragma": "no-cache"
};

const eventStreamHeaders = {
  ...securityHeaders,
  "cache-control": "no-cache",
  "connection": "keep-alive",
  "content-type": "text/event-stream"
};

const telemetryRoutePatterns = [
  [/^\/api\/archive\/v1\/intake\/[^/]+\/field-mappings$/, "/api/archive/v1/intake/{intake_id}/field-mappings"],
  [/^\/api\/archive\/v1\/intake\/[^/]+\/issues$/, "/api/archive/v1/intake/{intake_id}/issues"],
  [/^\/api\/archive\/v1\/intake\/[^/]+\/admissions$/, "/api/archive/v1/intake/{intake_id}/admissions"],
  [/^\/api\/archive\/v1\/intake\/[^/]+\/rollbacks$/, "/api/archive/v1/intake/{intake_id}/rollbacks"],
  [/^\/api\/archive\/v1\/intake\/[^/]+\/source-syncs$/, "/api/archive/v1/intake/{intake_id}/source-syncs"],
  [/^\/api\/hr\/v1\/employees\/[^/]+$/, "/api/hr/v1/employees/{employee_id}"],
  [/^\/api\/workflow\/v1\/templates\/[^/]+\/preflights$/, "/api/workflow/v1/templates/{template_id}/preflights"],
  [/^\/api\/workflow\/v1\/templates\/[^/]+\/rollbacks$/, "/api/workflow/v1/templates/{template_id}/rollbacks"],
  [/^\/api\/workflow\/v1\/templates\/[^/]+\/steps\/[^/]+\/validations$/, "/api/workflow/v1/templates/{template_id}/steps/{step_id}/validations"],
  [/^\/api\/workflow\/v1\/templates\/[^/]+\/steps\/[^/]+\/executions$/, "/api/workflow/v1/templates/{template_id}/steps/{step_id}/executions"],
  [/^\/api\/workflow\/v1\/templates\/[^/]+\/steps\/[^/]+$/, "/api/workflow/v1/templates/{template_id}/steps/{step_id}"],
  [/^\/api\/workflow\/v1\/templates\/[^/]+\/steps$/, "/api/workflow/v1/templates/{template_id}/steps"]
];

function telemetryRouteName(urlPath) {
  if (urlPath === "/" || urlPath === "/index.html") return "/";
  if (["/app.js", "/styles.css", "/catalog.json", "/events"].includes(urlPath)) return urlPath;
  for (const [pattern, route] of telemetryRoutePatterns) {
    if (pattern.test(urlPath)) return route;
  }
  if (urlPath.startsWith("/api/")) return urlPath;
  return "/{asset}";
}

function requestDurationMs(startedAt) {
  return Number(process.hrtime.bigint() - startedAt) / 1_000_000;
}

function logHttpTelemetry(req, route, statusCode, durationMs) {
  if (String(process.env.BITWEEN_HTTP_TELEMETRY || "on").toLowerCase() === "off") return;
  console.log(JSON.stringify({
    schema: "bitween.telemetry.http.v1",
    "http.request.method": req.method || "GET",
    "http.response.status_code": Number(statusCode) || 0,
    "http.route": route,
    "bitween.route_latency_budget_ms": routeLatencyBudgetMs,
    duration_ms: Number(durationMs.toFixed(1))
  }));
}

function instrumentHttpRequest(req, res, urlPath) {
  const startedAt = process.hrtime.bigint();
  const route = telemetryRouteName(urlPath);
  const originalWriteHead = res.writeHead;
  let recorded = false;
  res.writeHead = function writeHeadWithTelemetry(statusCode, ...args) {
    if (!recorded) {
      recorded = true;
      const durationMs = requestDurationMs(startedAt);
      res.setHeader("server-timing", `bitween;dur=${durationMs.toFixed(1)};desc="http.route"`);
      res.setHeader("x-bitween-route", route);
      res.setHeader("x-bitween-route-budget-ms", String(routeLatencyBudgetMs));
      logHttpTelemetry(req, route, statusCode, durationMs);
    }
    return originalWriteHead.call(this, statusCode, ...args);
  };
}

function assetVersion(fileName) {
  try {
    return String(fs.statSync(path.join(root, fileName)).mtimeMs);
  } catch {
    return String(Date.now());
  }
}

function sendIndex(res) {
  fs.readFile(path.join(root, "index.html"), "utf8", (err, html) => {
    if (err) {
      res.writeHead(404, { ...noCacheHeaders, "content-type": "text/plain; charset=utf-8" });
      res.end("Not found");
      return;
    }
    const versioned = html
      .replace("./styles.css", `./styles.css?v=${assetVersion("styles.css")}`)
      .replace("./app.js", `./app.js?v=${assetVersion("app.js")}`);
    res.writeHead(200, { ...noCacheHeaders, "content-type": types[".html"] });
    res.end(versioned);
  });
}

function sendFile(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { ...noCacheHeaders, "content-type": "text/plain; charset=utf-8" });
      res.end("Not found");
      return;
    }
    res.writeHead(200, { ...noCacheHeaders, "content-type": types[path.extname(filePath)] || "application/octet-stream" });
    res.end(data);
  });
}

function sendRustPlatformView(res) {
  const result = spawnSync(
    "buck2",
    ["run", "//crates/payroll-api:platform_live_view"],
    {
      cwd: repoRoot,
      encoding: "utf8",
      env: rustTargetEnv(),
      timeout: 15000
    }
  );

  if (result.error || result.status !== 0) {
    const detail = result.error ? result.error.message : result.stderr.trim();
    res.writeHead(503, { ...noCacheHeaders, "content-type": types[".json"] });
    res.end(JSON.stringify({
      ok: false,
      error: "rust_platform_view_unavailable",
      detail,
      owner: "bitween-payroll-api"
    }));
    return;
  }

  res.writeHead(200, { ...noCacheHeaders, "content-type": types[".json"] });
  res.end(result.stdout);
}

function runHrEmployeeStore(args, input) {
  return spawnSync(
    "buck2",
    ["run", "//crates/payroll-api:hr_employee_store", "--", ...args],
    {
      cwd: repoRoot,
      encoding: "utf8",
      env: rustTargetEnv(),
      input,
      timeout: 15000
    }
  );
}

function runArchiveIntakeStore(args, input) {
  return spawnSync(
    "buck2",
    ["run", "//crates/payroll-api:archive_intake_store", "--", ...args],
    {
      cwd: repoRoot,
      encoding: "utf8",
      env: rustTargetEnv(),
      input,
      timeout: 15000
    }
  );
}

function runUserPreferenceStore(args, input) {
  return spawnSync(
    "buck2",
    ["run", "//crates/payroll-api:user_preference_store", "--", ...args],
    {
      cwd: repoRoot,
      encoding: "utf8",
      env: rustTargetEnv(),
      input,
      timeout: 15000
    }
  );
}

function runWorkflowTemplateStore(args, input) {
  return spawnSync(
    "buck2",
    ["run", "//crates/payroll-api:workflow_template_store", "--", ...args],
    {
      cwd: repoRoot,
      encoding: "utf8",
      env: rustTargetEnv(),
      input,
      timeout: 15000
    }
  );
}

function runAuthorizationDecision(operation) {
  return spawnSync(
    "buck2",
    ["run", "//crates/payroll-api:authz_decision", "--", operation],
    {
      cwd: repoRoot,
      encoding: "utf8",
      env: rustTargetEnv(),
      timeout: 15000
    }
  );
}

function runAuthSessionValidate() {
  return spawnSync(
    "buck2",
    ["run", "//crates/payroll-api:auth_session_validate"],
    {
      cwd: repoRoot,
      encoding: "utf8",
      env: process.env,
      timeout: 15000
    }
  );
}

function authSessionValidationConfigured() {
  return [
    "BITWEEN_SESSION_JWT",
    "BITWEEN_AUTH_JWKS_JSON",
    "BITWEEN_AUTH_EXPECTED_ISSUER",
    "BITWEEN_AUTH_EXPECTED_AUDIENCE"
  ].some((name) => Boolean(String(process.env[name] || "").trim()));
}

function deniedAuthSessionEnv(reason) {
  return {
    ...process.env,
    BITWEEN_AUTH_CONFIGURED: "true",
    BITWEEN_SESSION_JWT_VERIFIED: "false",
    BITWEEN_SESSION_JWT_ISSUER: "",
    BITWEEN_SESSION_JWT_AUDIENCE: "",
    BITWEEN_SESSION_JWT_SUBJECT: "",
    BITWEEN_SESSION_JWT_EXPIRES_AT_UNIX: "0",
    BITWEEN_WEBAUTHN_USER_VERIFIED: "false",
    BITWEEN_SESSION_ACR_LEVEL: "",
    BITWEEN_SESSION_ACR_EVENT_AT_UNIX: "0",
    BITWEEN_SESSION_ROLE: "",
    BITWEEN_SESSION_AUTHZ_POLICY_ID: "",
    BITWEEN_SESSION_AUTHZ_TENANT_ID: "",
    BITWEEN_SESSION_AUTHZ_LEGAL_ENTITY: "",
    BITWEEN_SESSION_AUTHZ_WORKPLACE: "",
    BITWEEN_SESSION_AUTH_FAILURE_REASON: reason || "jwt_session_unverified"
  };
}

function verifiedAuthSessionEnv(verification) {
  return {
    ...process.env,
    BITWEEN_AUTH_CONFIGURED: "true",
    BITWEEN_SESSION_JWT_VERIFIED: "true",
    BITWEEN_SESSION_JWT_ISSUER: verification.issuer,
    BITWEEN_SESSION_JWT_AUDIENCE: verification.audience,
    BITWEEN_SESSION_JWT_SUBJECT: verification.subject,
    BITWEEN_SESSION_JWT_EXPIRES_AT_UNIX: String(verification.expires_at_unix),
    BITWEEN_WEBAUTHN_USER_VERIFIED: String(verification.webauthn_user_verified === true),
    BITWEEN_SESSION_ACR_LEVEL: verification.acr_level,
    BITWEEN_SESSION_ACR_EVENT_AT_UNIX: String(verification.acr_event_at_unix),
    BITWEEN_SESSION_ROLE: verification.role,
    BITWEEN_SESSION_AUTHZ_POLICY_ID: verification.authz_policy_id,
    BITWEEN_SESSION_AUTHZ_TENANT_ID: verification.authorized_tenant_id,
    BITWEEN_SESSION_AUTHZ_LEGAL_ENTITY: verification.authorized_legal_entity,
    BITWEEN_SESSION_AUTHZ_WORKPLACE: verification.authorized_workplace,
    BITWEEN_SESSION_AUTH_FAILURE_REASON: ""
  };
}

function authSessionEnvForRustTargets() {
  if (!authSessionValidationConfigured()) return process.env;
  const result = runAuthSessionValidate();
  let verification;
  try {
    verification = JSON.parse(result.stdout || "{}");
  } catch {
    return deniedAuthSessionEnv("auth_session_invalid_json");
  }
  if (result.error || result.status !== 0 || verification.verified !== true) {
    return deniedAuthSessionEnv(verification.reason || "jwt_session_unverified");
  }
  return verifiedAuthSessionEnv(verification);
}

function rustTargetEnv() {
  const env = authSessionEnvForRustTargets();
  for (const key of sessionEnvKeys) {
    if (env[key] === undefined) return env;
  }
  return env;
}

function sendStoreResult(res, result, errorCode) {
  if (result.error || result.status !== 0) {
    const detail = result.error ? result.error.message : result.stderr.trim();
    res.writeHead(503, { ...noCacheHeaders, "content-type": types[".json"] });
    res.end(JSON.stringify({
      ok: false,
      error: errorCode,
      detail,
      owner: "bitween-payroll-api"
    }));
    return;
  }
  res.writeHead(200, { ...noCacheHeaders, "content-type": types[".json"] });
  res.end(result.stdout);
}

function parseStoreJsonResult(result, errorCode) {
  if (result.error || result.status !== 0) {
    const detail = result.error ? result.error.message : result.stderr.trim();
    const error = new Error(detail || errorCode);
    error.statusCode = 503;
    error.code = errorCode;
    throw error;
  }
  try {
    return JSON.parse(result.stdout);
  } catch (parseError) {
    const error = new Error(`Rust store returned invalid JSON: ${parseError.message}`);
    error.statusCode = 503;
    error.code = errorCode;
    throw error;
  }
}

function writeJson(res, statusCode, body) {
  res.writeHead(statusCode, { ...noCacheHeaders, "content-type": types[".json"] });
  res.end(JSON.stringify(body));
}

function requestError(statusCode, code, message) {
  const error = new Error(message);
  error.statusCode = statusCode;
  error.code = code;
  return error;
}

function decodeRequestPath(rawUrl) {
  const rawPath = String(rawUrl || "/").split("?")[0] || "/";
  try {
    return { ok: true, urlPath: decodeURIComponent(rawPath) };
  } catch {
    return {
      ok: false,
      urlPath: rawPath,
      error: requestError(400, "request_path_invalid", "요청 경로 형식이 올바르지 않습니다.")
    };
  }
}

function requireAuthorizedOperation(operation) {
  const result = runAuthorizationDecision(operation);
  if (result.error || result.status !== 0) {
    const detail = result.error ? result.error.message : result.stderr.trim();
    const error = new Error(detail || "Rust authorization decision is unavailable.");
    error.statusCode = 503;
    error.code = "authorization_decision_unavailable";
    throw error;
  }
  let decision;
  try {
    decision = JSON.parse(result.stdout);
  } catch {
    const error = new Error("Rust authorization decision returned invalid JSON.");
    error.statusCode = 503;
    error.code = "authorization_decision_unavailable";
    throw error;
  }
  if (!decision.ok || decision.allowed !== true) {
    const error = new Error("Action requires a verified session and authorized business scope.");
    error.statusCode = 403;
    error.code = "authorization_required";
    error.reason = decision.reason || "authorization_denied";
    throw error;
  }
}

function localReviewStoreEnabled() {
  return ["1", "true", "yes", "on"].includes(String(process.env.BITWEEN_ALLOW_LOCAL_REVIEW_STORE || "").trim().toLowerCase());
}

function postgresDsnConfigured() {
  return Boolean(String(process.env.BITWEEN_POSTGRES_DSN || "").trim());
}

function configuredRustFsBucket() {
  return String(process.env.BITWEEN_RUSTFS_BUCKET || process.env.BITWEEN_RUSTFS_BUCKET_ARCHIVE || "").trim();
}

function requireRelationalStoreAvailable() {
  if (localReviewStoreEnabled()) return;
  if (postgresDsnConfigured()) return;
  const error = new Error(
    "PostgreSQL relational storage is required for live HR/archive/settings/workflow write paths. Set BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true only for hermetic local review while the production PostgreSQL adapter is being linked."
  );
  error.statusCode = 503;
  error.code = "postgres_relational_store_required";
  throw error;
}

function configuredOrigins(names) {
  const origins = new Set();
  for (const name of names) {
    const values = String(process.env[name] || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
    for (const value of values) {
      try {
        const parsed = new URL(value);
        if (parsed.protocol === "https:" && !parsed.username && !parsed.password && !parsed.hash) {
          origins.add(parsed.origin);
        }
      } catch {
        // Invalid allow-list entries are ignored so the route remains fail-closed when no valid origin is present.
      }
    }
  }
  return origins;
}

function authRouteAllowedOrigins(action) {
  if (action === "onboarding") {
    return configuredOrigins(["BITWEEN_ONBOARDING_ALLOWED_ORIGINS"]);
  }
  return configuredOrigins(["BITWEEN_AUTH_EXPECTED_ISSUER", "BITWEEN_AUTH_ALLOWED_ORIGINS"]);
}

function configuredUrl(name, action) {
  const value = String(process.env[name] || "").trim();
  if (!value) return "";
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "https:") return "";
    if (parsed.username || parsed.password || parsed.hash) return "";
    const allowedOrigins = authRouteAllowedOrigins(action);
    if (allowedOrigins.size > 0 && !allowedOrigins.has(parsed.origin)) return "";
    return parsed.toString();
  } catch {
    return "";
  }
}

function authRoute(action) {
  const envNames = {
    onboarding: "BITWEEN_ONBOARDING_START_URL",
    signin: "BITWEEN_AUTH_SIGNIN_URL",
    signout: "BITWEEN_AUTH_SIGNOUT_URL",
    signup: "BITWEEN_AUTH_SIGNUP_URL"
  };
  return configuredUrl(envNames[action], action);
}

function authRouteStatus() {
  const actions = ["signin", "signup", "onboarding", "signout"];
  const routes = Object.fromEntries(actions.map((action) => {
    const url = authRoute(action);
    return [action, {
      action,
      configured: Boolean(url),
      source: url ? "environment" : "missing"
    }];
  }));
  return {
    ok: true,
    schema: "bitween.auth-routes.v1",
    configured: actions.every((action) => routes[action].configured),
    routes,
    missing: actions.filter((action) => !routes[action].configured)
  };
}

function isMutationMethod(method) {
  return ["DELETE", "PATCH", "POST", "PUT"].includes(method);
}

function requestHost(req) {
  return String(req.headers.host || `127.0.0.1:${port}`).toLowerCase();
}

function originHost(value) {
  if (!value) return "";
  try {
    return new URL(String(value)).host.toLowerCase();
  } catch {
    return "";
  }
}

function requireSameOriginMutation(req) {
  if (!isMutationMethod(req.method || "")) return;
  const host = requestHost(req);
  const origin = originHost(req.headers.origin);
  if (origin && origin !== host) {
    const error = new Error("Cross-origin mutations are not allowed.");
    error.statusCode = 403;
    error.code = "csrf_origin_rejected";
    throw error;
  }
  const fetchSite = String(req.headers["sec-fetch-site"] || "").toLowerCase();
  if (fetchSite && !["none", "same-origin"].includes(fetchSite)) {
    const error = new Error("Cross-site mutations are not allowed.");
    error.statusCode = 403;
    error.code = "csrf_fetch_site_rejected";
    throw error;
  }
}

function rateLimitPolicy(req, urlPath) {
  if (urlPath.startsWith("/api/auth/") || urlPath.startsWith("/api/onboarding/")) {
    return { limit: authRateLimitMax, name: "auth" };
  }
  if (urlPath.startsWith("/api/") && isMutationMethod(req.method || "")) {
    return { limit: defaultMutableRateLimitMax, name: "mutation" };
  }
  return null;
}

function clientRateLimitKey(req, route, policy) {
  const address = req.socket?.remoteAddress || "unknown";
  return `${policy.name}:${address}:${route}`;
}

function enforceRateLimit(req, res, urlPath) {
  const policy = rateLimitPolicy(req, urlPath);
  if (!policy) return;
  const route = telemetryRouteName(urlPath);
  const now = Date.now();
  const key = clientRateLimitKey(req, route, policy);
  const current = rateLimitBuckets.get(key);
  const bucket = current && current.resetAt > now
    ? current
    : { count: 0, resetAt: now + rateLimitWindowMs };
  bucket.count += 1;
  rateLimitBuckets.set(key, bucket);
  const remaining = Math.max(0, policy.limit - bucket.count);
  res.setHeader("x-ratelimit-limit", String(policy.limit));
  res.setHeader("x-ratelimit-remaining", String(remaining));
  res.setHeader("x-ratelimit-reset", String(Math.ceil(bucket.resetAt / 1000)));
  if (bucket.count > policy.limit) {
    const error = new Error("Too many requests for this route.");
    error.statusCode = 429;
    error.code = "rate_limit_exceeded";
    throw error;
  }
  if (rateLimitBuckets.size > 10_000) {
    for (const [bucketKey, value] of rateLimitBuckets.entries()) {
      if (value.resetAt <= now) rateLimitBuckets.delete(bucketKey);
    }
  }
}

function sendAuthRouteStatus(res) {
  res.writeHead(200, { ...noCacheHeaders, "content-type": types[".json"] });
  res.end(JSON.stringify(authRouteStatus()));
}

function clearSessionCookieHeader() {
  return `${sessionCookieName}=; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; HttpOnly; SameSite=Lax; Secure`;
}

function authRouteHeaders(action) {
  const headers = { ...noCacheHeaders, "content-type": types[".json"] };
  if (action === "signout") {
    headers["set-cookie"] = clearSessionCookieHeader();
  }
  return headers;
}

function sendAuthRoute(res, action) {
  const url = authRoute(action);
  if (!url) {
    res.writeHead(503, authRouteHeaders(action));
    res.end(JSON.stringify({
      ok: false,
      error: "auth_route_unconfigured",
      detail: "Production identity/onboarding route is not configured for this environment.",
      owner: "identity-gateway"
    }));
    return;
  }
  res.writeHead(200, authRouteHeaders(action));
  res.end(JSON.stringify({
    ok: true,
    action,
    url
  }));
}

async function handleAuthRoutes(req, res, urlPath) {
  if (req.method === "GET" && urlPath === "/api/auth/v1/routes") {
    sendAuthRouteStatus(res);
    return true;
  }
  if (req.method === "GET" && urlPath === "/api/auth/v1/signin") {
    sendAuthRoute(res, "signin");
    return true;
  }
  if (req.method === "GET" && urlPath === "/api/auth/v1/signup") {
    sendAuthRoute(res, "signup");
    return true;
  }
  if (req.method === "GET" && urlPath === "/api/onboarding/v1/start") {
    sendAuthRoute(res, "onboarding");
    return true;
  }
  if (req.method === "POST" && urlPath === "/api/auth/v1/signout") {
    sendAuthRoute(res, "signout");
    return true;
  }
  return false;
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 1024 * 1024) {
        reject(new Error("Request body too large"));
        req.destroy();
      }
    });
    req.on("end", () => resolve(body || "{}"));
    req.on("error", reject);
  });
}

function readBinaryBody(req, maxBytes = maxUploadBytes) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    req.on("data", (chunk) => {
      total += chunk.length;
      if (total > maxBytes) {
        reject(new Error("Request body too large"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function parseMultipartFile(req, body) {
  const contentType = req.headers["content-type"] || "";
  const boundaryMatch = contentType.match(/boundary=(?:"([^"]+)"|([^;]+))/i);
  if (!boundaryMatch) {
    throw new Error("Missing multipart boundary");
  }
  const boundary = Buffer.from(`--${boundaryMatch[1] || boundaryMatch[2]}`);
  let offset = body.indexOf(boundary);
  while (offset !== -1) {
    offset += boundary.length;
    if (body[offset] === 45 && body[offset + 1] === 45) break;
    if (body[offset] === 13 && body[offset + 1] === 10) offset += 2;
    const headerEnd = body.indexOf(Buffer.from("\r\n\r\n"), offset);
    if (headerEnd === -1) break;
    const headers = body.slice(offset, headerEnd).toString("utf8");
    const next = body.indexOf(boundary, headerEnd + 4);
    if (next === -1) break;
    let dataEnd = next;
    if (body[dataEnd - 2] === 13 && body[dataEnd - 1] === 10) dataEnd -= 2;
    const data = body.slice(headerEnd + 4, dataEnd);
    const disposition = headers.match(/content-disposition:\s*form-data;([^\r\n]+)/i)?.[1] || "";
    const name = disposition.match(/name="([^"]+)"/i)?.[1] || "";
    const filename = disposition.match(/filename="([^"]*)"/i)?.[1] || "";
    if (name === "file" && filename) {
      return {
        data,
        fileName: path.basename(filename.replace(/\\/g, "/")),
        contentType: headers.match(/content-type:\s*([^\r\n]+)/i)?.[1]?.trim() || "application/octet-stream"
      };
    }
    offset = next;
  }
  throw new Error("Missing uploaded file");
}

function rustFsConfig() {
  const endpoint = process.env.BITWEEN_RUSTFS_ENDPOINT;
  const accessKey = process.env.BITWEEN_RUSTFS_ACCESS_KEY;
  const secretKey = process.env.BITWEEN_RUSTFS_SECRET_KEY;
  const bucket = configuredRustFsBucket();
  if (!endpoint || !accessKey || !secretKey || !bucket) {
    const error = new Error("RustFS object storage is not configured.");
    error.statusCode = 503;
    error.code = "rustfs_object_store_unavailable";
    throw error;
  }
  if (!/^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$/.test(bucket)) {
    const error = new Error("RustFS archive bucket name is invalid.");
    error.statusCode = 503;
    error.code = "rustfs_archive_bucket_invalid";
    throw error;
  }
  return {
    accessKey,
    bucket,
    endpoint: new URL(endpoint),
    region: process.env.BITWEEN_RUSTFS_REGION || "us-east-1",
    secretKey
  };
}

function objectKeyFor(fileName) {
  const day = new Date().toISOString().slice(0, 10);
  const ext = path.extname(fileName).replace(/[^a-zA-Z0-9.]/g, "").slice(0, 16).toLowerCase();
  return `quarantine/${day}/${crypto.randomUUID()}${ext}`;
}

function hashSha256(data, encoding = "hex") {
  return crypto.createHash("sha256").update(data).digest(encoding);
}

function hmacSha256(key, data, encoding) {
  return crypto.createHmac("sha256", key).update(data).digest(encoding);
}

function signingKey(secretKey, dateStamp, region) {
  const kDate = hmacSha256(Buffer.from(`AWS4${secretKey}`, "utf8"), dateStamp);
  const kRegion = hmacSha256(kDate, region);
  const kService = hmacSha256(kRegion, "s3");
  return hmacSha256(kService, "aws4_request");
}

function amzDateParts(date) {
  const iso = date.toISOString().replace(/[:-]|\.\d{3}/g, "");
  return {
    amzDate: iso,
    dateStamp: iso.slice(0, 8)
  };
}

function encodeS3Key(key) {
  return key.split("/").map(encodeURIComponent).join("/");
}

function putRustFsObject(config, key, data, contentType) {
  const endpointPath = config.endpoint.pathname.replace(/\/$/, "");
  const canonicalUri = `${endpointPath}/${config.bucket}/${encodeS3Key(key)}`.replace(/\/+/g, "/");
  const requestPath = `${canonicalUri}${config.endpoint.search || ""}`;
  const payloadHash = hashSha256(data);
  const { amzDate, dateStamp } = amzDateParts(new Date());
  const host = config.endpoint.host;
  const headers = {
    "content-length": String(data.length),
    "content-type": contentType || "application/octet-stream",
    "host": host,
    "x-amz-content-sha256": payloadHash,
    "x-amz-date": amzDate,
    "x-amz-meta-bitween-sha256": payloadHash
  };
  const signedHeaders = Object.keys(headers).sort().join(";");
  const canonicalHeaders = Object.keys(headers)
    .sort()
    .map((name) => `${name}:${headers[name]}\n`)
    .join("");
  const canonicalRequest = [
    "PUT",
    canonicalUri,
    "",
    canonicalHeaders,
    signedHeaders,
    payloadHash
  ].join("\n");
  const credentialScope = `${dateStamp}/${config.region}/s3/aws4_request`;
  const stringToSign = [
    "AWS4-HMAC-SHA256",
    amzDate,
    credentialScope,
    hashSha256(canonicalRequest)
  ].join("\n");
  const signature = hmacSha256(signingKey(config.secretKey, dateStamp, config.region), stringToSign, "hex");
  const authorization = `AWS4-HMAC-SHA256 Credential=${config.accessKey}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${signature}`;

  return new Promise((resolve, reject) => {
    const client = config.endpoint.protocol === "https:" ? https : http;
    const req = client.request({
      method: "PUT",
      hostname: config.endpoint.hostname,
      port: config.endpoint.port || (config.endpoint.protocol === "https:" ? 443 : 80),
      path: requestPath,
      headers: { ...headers, authorization }
    }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve();
          return;
        }
        const error = new Error(Buffer.concat(chunks).toString("utf8") || `RustFS upload failed with ${res.statusCode}`);
        error.statusCode = 503;
        error.code = "rustfs_upload_failed";
        reject(error);
      });
    });
    req.on("error", reject);
    req.end(data);
  });
}

async function storeArchiveObjectInRustFs(file) {
  const config = rustFsConfig();
  const key = objectKeyFor(file.fileName);
  await putRustFsObject(config, key, file.data, file.contentType);
  return `rustfs://${config.bucket}/${key}`;
}

async function syncArchiveSourceVersions(intakeId) {
  const plan = parseStoreJsonResult(
    runArchiveIntakeStore(["source-sync-plan", intakeId]),
    "archive_source_sync_store_unavailable"
  );
  const items = plan.sync_items || [];
  if (!items.length) {
    return { planned: 0, synced: [] };
  }
  const config = rustFsConfig();
  const synced = [];
  for (const item of items) {
    const body = Buffer.from(String(item.body_text || ""), "utf8");
    try {
      await putRustFsObject(config, item.object_key, body, item.content_type);
      const generatedObjectUri = `rustfs://${config.bucket}/${item.object_key}`;
      parseStoreJsonResult(
        runArchiveIntakeStore(["source-sync-complete"], JSON.stringify({
          content_sha256: item.content_sha256,
          file_size_bytes: body.length,
          generated_object_uri: generatedObjectUri,
          sync_item_id: item.sync_item_id
        })),
        "archive_source_sync_complete_failed"
      );
      synced.push(generatedObjectUri);
    } catch (error) {
      runArchiveIntakeStore(["source-sync-fail"], JSON.stringify({
        error: error.message || "RustFS source sync upload failed",
        sync_item_id: item.sync_item_id
      }));
      throw error;
    }
  }
  return { planned: items.length, synced };
}

function extractSampleText(file) {
  const ext = path.extname(file.fileName).slice(1).toLowerCase();
  if (["csv", "tsv", "txt"].includes(ext) || file.contentType.startsWith("text/")) {
    return file.data.slice(0, 64 * 1024).toString("utf8");
  }
  if (ext === "xlsx") {
    return extractXlsxSample(file.data);
  }
  return "";
}

function archiveIntakeInputsForFile(file, blobUri) {
  const contentSha256 = hashSha256(file.data);
  const shared = {
    blob_uri: blobUri,
    content_sha256: contentSha256,
    file_size_bytes: file.data.length,
    object_uri: blobUri
  };
  if (!isZipUpload(file)) {
    return [{
      ...shared,
      file_name: file.fileName,
      file_type: file.contentType,
      sample_text: extractSampleText(file)
    }];
  }
  const extracted = extractZipIntakeSamples(file);
  if (!extracted.length) {
    return [{
      ...shared,
      file_name: file.fileName,
      file_type: file.contentType || "application/zip",
      sample_text: ""
    }];
  }
  return extracted.map((entry) => ({
    ...shared,
    file_name: `${file.fileName}/${entry.name}`,
    file_type: entry.contentType,
    sample_text: entry.sampleText
  }));
}

function isZipUpload(file) {
  const ext = path.extname(file.fileName).slice(1).toLowerCase();
  const contentType = String(file.contentType || "").toLowerCase();
  return ext === "zip" || ["application/zip", "application/x-zip-compressed", "multipart/x-zip"].includes(contentType);
}

function extractZipIntakeSamples(file) {
  const entries = zipEntries(file.data);
  if ((entries.zipEntryCount || entries.size) > maxZipEntries) {
    const error = new Error("압축 파일 안의 항목이 너무 많아 안전하게 읽을 수 없습니다.");
    error.statusCode = 400;
    error.code = "archive_zip_too_many_entries";
    throw error;
  }
  const samples = [];
  let totalExtracted = 0;
  for (const entry of entries.values()) {
    const safeName = isSafeZipEntryName(entry.name);
    if (!safeName || entry.isDirectory || entry.isEncrypted || isZipSymlink(entry)) continue;
    const ext = path.extname(safeName).slice(1).toLowerCase();
    if (!["csv", "tsv", "txt", "xlsx"].includes(ext)) continue;
    if (entry.uncompressedSize > maxZipMemberBytes) continue;
    if (totalExtracted + entry.uncompressedSize > maxZipTotalExtractedBytes) break;
    const data = readZipEntryBuffer(
      file.data,
      entry,
      Math.min(maxZipMemberBytes, maxZipTotalExtractedBytes - totalExtracted)
    );
    if (!data) continue;
    totalExtracted += data.length;
    const sampleText = sampleTextForEntry(safeName, data);
    if (!sampleText.trim()) continue;
    samples.push({
      contentType: contentTypeForArchiveEntry(safeName),
      name: safeName,
      sampleText
    });
  }
  return samples;
}

function isSafeZipEntryName(name) {
  const raw = String(name || "");
  if (!raw || raw.length > 240 || /[\u0000-\u001f]/.test(raw)) return "";
  const normalized = raw.replace(/\\/g, "/").replace(/\/+/g, "/");
  if (normalized.startsWith("/") || /^[A-Za-z]:/.test(normalized)) return "";
  const parts = normalized.split("/").filter(Boolean);
  if (!parts.length) return "";
  if (parts[0] === "__MACOSX") return "";
  if (parts.some((part) => {
    return part === "." || part === ".." || part.length > 120 || /[<>:"|?*]/.test(part);
  })) {
    return "";
  }
  return parts.join("/");
}

function isZipSymlink(entry) {
  const unixMode = (entry.externalAttributes >>> 16) & 0xffff;
  return (unixMode & 0o170000) === 0o120000;
}

function sampleTextForEntry(fileName, data) {
  const ext = path.extname(fileName).slice(1).toLowerCase();
  if (["csv", "tsv", "txt"].includes(ext)) {
    return data.slice(0, maxZipTextSampleBytes).toString("utf8");
  }
  if (ext === "xlsx") {
    return extractXlsxSample(data);
  }
  return "";
}

function contentTypeForArchiveEntry(fileName) {
  const ext = path.extname(fileName).slice(1).toLowerCase();
  if (ext === "csv") return "text/csv; charset=utf-8";
  if (ext === "tsv") return "text/tab-separated-values; charset=utf-8";
  if (ext === "txt") return "text/plain; charset=utf-8";
  if (ext === "xlsx") return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  return "application/octet-stream";
}

function extractXlsxSample(buffer) {
  try {
    const entries = zipEntries(buffer);
    const sharedStrings = parseSharedStrings(readZipEntry(buffer, entries.get("xl/sharedStrings.xml")) || "");
    const candidates = workbookSheetPaths(entries, buffer)
      .map((sheetPath) => {
        const sheet = readZipEntry(buffer, entries.get(sheetPath)) || "";
        return bestSheetSample(parseSheetRows(sheet, sharedStrings));
      })
      .filter((candidate) => candidate.score > 0);
    const best = candidates.sort((left, right) => right.score - left.score || left.headerIndex - right.headerIndex)[0];
    return best ? best.rows.map((row) => row.map(csvCell).join(",")).join("\n") : "";
  } catch {
    return "";
  }
}

function workbookSheetPaths(entries, buffer) {
  const workbook = readZipEntry(buffer, entries.get("xl/workbook.xml")) || "";
  const rels = readZipEntry(buffer, entries.get("xl/_rels/workbook.xml.rels")) || "";
  const relTargets = new Map(Array.from(rels.matchAll(/<Relationship\b([^>]*)\/?>/g)).map((match) => {
    const attrs = xmlAttrs(match[1]);
    const target = attrs.Target || attrs.target || "";
    const pathName = target.startsWith("/") ? target.slice(1) : `xl/${target.replace(/^\.\//, "")}`;
    return [attrs.Id || attrs.id, pathName.replace(/\/+/g, "/")];
  }));
  const listed = Array.from(workbook.matchAll(/<sheet\b([^>]*)\/?>/g))
    .map((match) => {
      const attrs = xmlAttrs(match[1]);
      const relId = attrs["r:id"] || attrs.id;
      return relTargets.get(relId);
    })
    .filter((pathName) => pathName && entries.has(pathName));
  if (listed.length) return listed;
  return Array.from(entries.keys())
    .filter((name) => /^xl\/worksheets\/sheet\d+\.xml$/.test(name))
    .sort((left, right) => left.localeCompare(right, undefined, { numeric: true }));
}

function xmlAttrs(value) {
  return Object.fromEntries(Array.from(String(value || "").matchAll(/([\w:.-]+)=["']([^"']*)["']/g)).map((match) => [
    match[1],
    xmlDecode(match[2])
  ]));
}

function bestSheetSample(rows) {
  let best = { score: 0, headerIndex: 0, rows: [] };
  rows.slice(0, 40).forEach((row, index) => {
    const normalized = normalizeSheetRow(row);
    const score = headerRowScore(normalized);
    if (score > best.score) {
      const sampleRows = rows
        .slice(index + 1, index + 21)
        .map(normalizeSheetRow)
        .filter((candidate) => candidate.some((cell) => cleanPreviewText(cell)));
      best = {
        score,
        headerIndex: index,
        rows: [normalized, ...sampleRows].filter((candidate) => candidate.length)
      };
    }
  });
  return best;
}

function normalizeSheetRow(row) {
  const last = Array.from(row || []).reduce((index, value, current) => {
    return cleanPreviewText(value) ? current : index;
  }, -1);
  return Array.from({ length: Math.min(last + 1, 80) }, (_, index) => cleanPreviewText(row?.[index] || ""));
}

function headerRowScore(row) {
  const nonEmpty = row.filter(Boolean);
  if (nonEmpty.length < 2) return 0;
  const aliases = [
    "no", "순", "번호", "사번", "직원번호", "사원번호", "성명", "성 명", "이름", "직원명",
    "소속", "부서", "조직", "근무지", "업무", "직무", "직책", "기본시급", "통상시급",
    "급여", "지급액", "지급총액", "공제", "공제총액", "입사일", "퇴사일", "근무일",
    "주민번호", "휴대폰", "email", "e-mail", "은행", "계좌"
  ];
  const aliasKeys = aliases.map(headerKey);
  const aliasScore = nonEmpty.reduce((score, cell) => {
    const key = headerKey(cell);
    return score + (aliasKeys.some((alias) => key === alias || key.includes(alias)) ? 5 : 0);
  }, 0);
  const textScore = nonEmpty.filter((cell) => /[A-Za-z가-힣]/.test(cell) && !/^\d+([.,]\d+)*$/.test(cell)).length;
  const numericPenalty = nonEmpty.filter((cell) => /^\d+([.,]\d+)*$/.test(cell)).length;
  return aliasScore + textScore + Math.min(nonEmpty.length, 12) - numericPenalty * 2;
}

function headerKey(value) {
  return cleanPreviewText(value)
    .toLowerCase()
    .replace(/[^0-9a-z가-힣]/g, "");
}

function cleanPreviewText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function zipEntries(buffer) {
  const entries = new Map();
  const eocdSignature = 0x06054b50;
  let eocd = -1;
  for (let index = buffer.length - 22; index >= Math.max(0, buffer.length - 65558); index -= 1) {
    if (buffer.readUInt32LE(index) === eocdSignature) {
      eocd = index;
      break;
    }
  }
  if (eocd === -1) return entries;
  const totalEntries = buffer.readUInt16LE(eocd + 10);
  entries.zipEntryCount = totalEntries;
  let offset = buffer.readUInt32LE(eocd + 16);
  for (let count = 0; count < Math.min(totalEntries, maxZipEntries) && offset + 46 <= buffer.length; count += 1) {
    if (buffer.readUInt32LE(offset) !== 0x02014b50) break;
    const flags = buffer.readUInt16LE(offset + 8);
    const method = buffer.readUInt16LE(offset + 10);
    const compressedSize = buffer.readUInt32LE(offset + 20);
    const uncompressedSize = buffer.readUInt32LE(offset + 24);
    const fileNameLength = buffer.readUInt16LE(offset + 28);
    const extraLength = buffer.readUInt16LE(offset + 30);
    const commentLength = buffer.readUInt16LE(offset + 32);
    const externalAttributes = buffer.readUInt32LE(offset + 38);
    const localHeaderOffset = buffer.readUInt32LE(offset + 42);
    const name = buffer.slice(offset + 46, offset + 46 + fileNameLength).toString("utf8");
    entries.set(name, {
      compressedSize,
      externalAttributes,
      isDirectory: name.endsWith("/"),
      isEncrypted: Boolean(flags & 1),
      flags,
      localHeaderOffset,
      method,
      name,
      uncompressedSize
    });
    offset += 46 + fileNameLength + extraLength + commentLength;
  }
  return entries;
}

function readZipEntryBuffer(buffer, entry, maxOutputLength) {
  if (!entry || entry.isEncrypted || entry.uncompressedSize > maxOutputLength) return undefined;
  if (entry.localHeaderOffset < 0 || entry.localHeaderOffset + 30 > buffer.length) return undefined;
  if (buffer.readUInt32LE(entry.localHeaderOffset) !== 0x04034b50) return undefined;
  const nameLength = buffer.readUInt16LE(entry.localHeaderOffset + 26);
  const extraLength = buffer.readUInt16LE(entry.localHeaderOffset + 28);
  const dataStart = entry.localHeaderOffset + 30 + nameLength + extraLength;
  const dataEnd = dataStart + entry.compressedSize;
  if (dataStart < 0 || dataEnd > buffer.length || dataEnd < dataStart) return undefined;
  const compressed = buffer.slice(dataStart, dataEnd);
  try {
    if (entry.method === 0) {
      return compressed.length <= maxOutputLength ? compressed : undefined;
    }
    if (entry.method === 8) {
      return zlib.inflateRawSync(compressed, { maxOutputLength });
    }
  } catch {
    return undefined;
  }
  return undefined;
}

function readZipEntry(buffer, entry) {
  return readZipEntryBuffer(buffer, entry, maxExtractedXmlBytes)?.toString("utf8") || "";
}

function parseSharedStrings(xml) {
  return Array.from(xml.matchAll(/<si[\s\S]*?<\/si>/g)).map((match) => {
    return Array.from(match[0].matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g))
      .map((text) => xmlDecode(text[1]))
      .join("");
  });
}

function parseSheetRows(xml, sharedStrings) {
  return Array.from(xml.matchAll(/<row[^>]*>([\s\S]*?)<\/row>/g)).map((rowMatch) => {
    const row = [];
    for (const cellMatch of rowMatch[1].matchAll(/<c([^>]*)>([\s\S]*?)<\/c>/g)) {
      const attrs = cellMatch[1];
      const cell = cellMatch[2];
      const ref = attrs.match(/\sr="([A-Z]+)\d+"/)?.[1] || "A";
      const type = attrs.match(/\st="([^"]+)"/)?.[1] || "";
      const value = cell.match(/<v>([\s\S]*?)<\/v>/)?.[1] || "";
      const inline = cell.match(/<t[^>]*>([\s\S]*?)<\/t>/)?.[1] || "";
      row[columnIndex(ref)] = type === "s" ? (sharedStrings[Number(value)] || "") : xmlDecode(inline || value);
    }
    return row.map((value) => value || "");
  });
}

function columnIndex(letters) {
  return letters.split("").reduce((total, ch) => total * 26 + ch.charCodeAt(0) - 64, 0) - 1;
}

function xmlDecode(value) {
  return value
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, "\"")
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&");
}

function csvCell(value) {
  const text = String(value || "");
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

async function handleHrEmployees(req, res, urlPath) {
  if (req.method === "GET" && urlPath === "/api/hr/v1/employees") {
    requireAuthorizedOperation("hr_employee_read");
    requireRelationalStoreAvailable();
    sendStoreResult(res, runHrEmployeeStore(["list"]), "hr_employee_store_unavailable");
    return true;
  }

  if (req.method === "POST" && urlPath === "/api/hr/v1/employees") {
    requireAuthorizedOperation("hr_employee_write");
    requireRelationalStoreAvailable();
    sendStoreResult(res, runHrEmployeeStore(["add"], await readJsonBody(req)), "hr_employee_store_unavailable");
    return true;
  }

  const match = urlPath.match(/^\/api\/hr\/v1\/employees\/([^/]+)$/);
  if (match && req.method === "PATCH") {
    requireAuthorizedOperation("hr_employee_write");
    requireRelationalStoreAvailable();
    sendStoreResult(res, runHrEmployeeStore(["update", match[1]], await readJsonBody(req)), "hr_employee_store_unavailable");
    return true;
  }
  if (match && req.method === "DELETE") {
    requireAuthorizedOperation("hr_employee_write");
    requireRelationalStoreAvailable();
    sendStoreResult(res, runHrEmployeeStore(["remove", match[1]]), "hr_employee_store_unavailable");
    return true;
  }
  return false;
}

async function handleArchiveIntake(req, res, urlPath) {
  if (req.method === "GET" && urlPath === "/api/archive/v1/intake") {
    requireAuthorizedOperation("archive_read");
    requireRelationalStoreAvailable();
    sendStoreResult(res, runArchiveIntakeStore(["list"]), "archive_intake_store_unavailable");
    return true;
  }
  if (req.method === "POST" && urlPath === "/api/archive/v1/intake") {
    try {
      requireAuthorizedOperation("archive_upload");
      requireRelationalStoreAvailable();
      const file = parseMultipartFile(req, await readBinaryBody(req));
      const blobUri = await storeArchiveObjectInRustFs(file);
      const intakeInputs = archiveIntakeInputsForFile(file, blobUri);
      let store;
      for (const intakeInput of intakeInputs) {
        store = parseStoreJsonResult(
          runArchiveIntakeStore(["add"], JSON.stringify(intakeInput)),
          "archive_intake_store_unavailable"
        );
      }
      res.writeHead(200, { ...noCacheHeaders, "content-type": types[".json"] });
      res.end(JSON.stringify(store));
    } catch (error) {
      res.writeHead(error.statusCode || 400, { ...noCacheHeaders, "content-type": types[".json"] });
      res.end(JSON.stringify({
        ok: false,
        error: error.code || "archive_intake_failed",
        detail: error.message,
        reason: error.reason
      }));
    }
    return true;
  }
  const issueMatch = urlPath.match(/^\/api\/archive\/v1\/intake\/([^/]+)\/issues$/);
  if (issueMatch && req.method === "PATCH") {
    try {
      requireAuthorizedOperation("archive_review");
      requireRelationalStoreAvailable();
      sendStoreResult(
        res,
        runArchiveIntakeStore(["resolve", decodeURIComponent(issueMatch[1])], await readJsonBody(req)),
        "archive_intake_store_unavailable"
      );
    } catch (error) {
      res.writeHead(error.statusCode || 400, { ...noCacheHeaders, "content-type": types[".json"] });
      res.end(JSON.stringify({
        ok: false,
        error: error.code || "archive_issue_resolution_failed",
        detail: error.message,
        reason: error.reason
      }));
    }
    return true;
  }
  const fieldMappingMatch = urlPath.match(/^\/api\/archive\/v1\/intake\/([^/]+)\/field-mappings$/);
  if (fieldMappingMatch && req.method === "PATCH") {
    try {
      requireAuthorizedOperation("archive_review");
      requireRelationalStoreAvailable();
      sendStoreResult(
        res,
        runArchiveIntakeStore(["map-fields", decodeURIComponent(fieldMappingMatch[1])], await readJsonBody(req)),
        "archive_intake_store_unavailable"
      );
    } catch (error) {
      res.writeHead(error.statusCode || 400, { ...noCacheHeaders, "content-type": types[".json"] });
      res.end(JSON.stringify({
        ok: false,
        error: error.code || "archive_field_mapping_failed",
        detail: error.message,
        reason: error.reason
      }));
    }
    return true;
  }
  const admissionMatch = urlPath.match(/^\/api\/archive\/v1\/intake\/([^/]+)\/admissions$/);
  if (admissionMatch && req.method === "POST") {
    try {
      requireAuthorizedOperation("archive_admit");
      requireRelationalStoreAvailable();
      sendStoreResult(
        res,
        runArchiveIntakeStore(["admit", decodeURIComponent(admissionMatch[1])], "{}"),
        "archive_intake_store_unavailable"
      );
    } catch (error) {
      res.writeHead(error.statusCode || 400, { ...noCacheHeaders, "content-type": types[".json"] });
      res.end(JSON.stringify({
        ok: false,
        error: error.code || "archive_admission_failed",
        detail: error.message,
        reason: error.reason
      }));
    }
    return true;
  }
  const rollbackMatch = urlPath.match(/^\/api\/archive\/v1\/intake\/([^/]+)\/rollbacks$/);
  if (rollbackMatch && req.method === "POST") {
    try {
      requireAuthorizedOperation("archive_rollback");
      requireRelationalStoreAvailable();
      sendStoreResult(
        res,
        runArchiveIntakeStore(["rollback", decodeURIComponent(rollbackMatch[1])], await readJsonBody(req)),
        "archive_intake_store_unavailable"
      );
    } catch (error) {
      res.writeHead(error.statusCode || 400, { ...noCacheHeaders, "content-type": types[".json"] });
      res.end(JSON.stringify({
        ok: false,
        error: error.code || "archive_rollback_failed",
        detail: error.message,
        reason: error.reason
      }));
    }
    return true;
  }
  const sourceSyncMatch = urlPath.match(/^\/api\/archive\/v1\/intake\/([^/]+)\/source-syncs$/);
  if (sourceSyncMatch && req.method === "POST") {
    try {
      requireAuthorizedOperation("archive_sync");
      requireRelationalStoreAvailable();
      await syncArchiveSourceVersions(decodeURIComponent(sourceSyncMatch[1]));
      sendStoreResult(res, runArchiveIntakeStore(["list"]), "archive_intake_store_unavailable");
    } catch (error) {
      writeJson(res, error.statusCode || 400, {
        ok: false,
        error: error.code || "archive_source_sync_failed",
        detail: error.message,
        reason: error.reason
      });
    }
    return true;
  }
  return false;
}

async function handleUserPreferences(req, res, urlPath) {
  if (urlPath !== "/api/settings/v1/preferences") return false;
  if (req.method === "GET") {
    requireAuthorizedOperation("read_workspace");
    requireRelationalStoreAvailable();
    sendStoreResult(res, runUserPreferenceStore(["get"]), "user_preference_store_unavailable");
    return true;
  }
  if (req.method === "PUT") {
    requireAuthorizedOperation("user_preference_update");
    requireRelationalStoreAvailable();
    sendStoreResult(
      res,
      runUserPreferenceStore(["update"], await readJsonBody(req)),
      "user_preference_store_unavailable"
    );
    return true;
  }
  res.writeHead(405, { ...noCacheHeaders, "content-type": types[".json"] });
  res.end(JSON.stringify({
    ok: false,
    error: "unsupported_user_preference_method"
  }));
  return true;
}

async function handleWorkflowTemplates(req, res, urlPath) {
  if (req.method === "GET" && urlPath === "/api/workflow/v1/templates") {
    requireAuthorizedOperation("workflow_template_read");
    requireRelationalStoreAvailable();
    sendStoreResult(res, runWorkflowTemplateStore(["get"]), "workflow_template_store_unavailable");
    return true;
  }

  const collectionMatch = urlPath.match(/^\/api\/workflow\/v1\/templates\/([^/]+)\/steps$/);
  if (collectionMatch && req.method === "POST") {
    requireAuthorizedOperation("workflow_template_write");
    requireRelationalStoreAvailable();
    sendStoreResult(
      res,
      runWorkflowTemplateStore(
        ["add-step", decodeURIComponent(collectionMatch[1])],
        await readJsonBody(req)
      ),
      "workflow_template_store_unavailable"
    );
    return true;
  }

  const rollbackMatch = urlPath.match(/^\/api\/workflow\/v1\/templates\/([^/]+)\/rollbacks$/);
  if (rollbackMatch && req.method === "POST") {
    requireAuthorizedOperation("workflow_template_write");
    requireRelationalStoreAvailable();
    const body = await readJsonBody(req);
    let payload;
    try {
      payload = JSON.parse(body || "{}");
    } catch (_error) {
      const error = new Error("A workflow rollback request must be valid JSON.");
      error.statusCode = 400;
      error.code = "workflow_rollback_invalid_json";
      throw error;
    }
    const version = Number(payload.version);
    if (!Number.isInteger(version) || version < 1) {
      const error = new Error("A workflow rollback requires a saved version number.");
      error.statusCode = 400;
      error.code = "workflow_rollback_version_required";
      throw error;
    }
    sendStoreResult(
      res,
      runWorkflowTemplateStore(
        ["rollback-template", decodeURIComponent(rollbackMatch[1]), String(version)],
        body
      ),
      "workflow_template_store_unavailable"
    );
    return true;
  }

  const preflightMatch = urlPath.match(/^\/api\/workflow\/v1\/templates\/([^/]+)\/preflights$/);
  if (preflightMatch && req.method === "POST") {
    requireAuthorizedOperation("workflow_template_read");
    requireRelationalStoreAvailable();
    sendStoreResult(
      res,
      runWorkflowTemplateStore(
        ["preflight-template", decodeURIComponent(preflightMatch[1])],
        await readJsonBody(req)
      ),
      "workflow_template_store_unavailable"
    );
    return true;
  }

  const validationMatch = urlPath.match(/^\/api\/workflow\/v1\/templates\/([^/]+)\/steps\/([^/]+)\/validations$/);
  if (validationMatch && req.method === "POST") {
    requireAuthorizedOperation("workflow_template_write");
    requireRelationalStoreAvailable();
    sendStoreResult(
      res,
      runWorkflowTemplateStore(
        ["validate-step-update", decodeURIComponent(validationMatch[1]), decodeURIComponent(validationMatch[2])],
        await readJsonBody(req)
      ),
      "workflow_template_store_unavailable"
    );
    return true;
  }

  const executionMatch = urlPath.match(/^\/api\/workflow\/v1\/templates\/([^/]+)\/steps\/([^/]+)\/executions$/);
  if (executionMatch && req.method === "POST") {
    requireAuthorizedOperation("workflow_step_execute");
    requireRelationalStoreAvailable();
    sendStoreResult(
      res,
      runWorkflowTemplateStore(
        ["execute-step", decodeURIComponent(executionMatch[1]), decodeURIComponent(executionMatch[2])],
        await readJsonBody(req)
      ),
      "workflow_template_store_unavailable"
    );
    return true;
  }

  const match = urlPath.match(/^\/api\/workflow\/v1\/templates\/([^/]+)\/steps\/([^/]+)$/);
  if (match && req.method === "PATCH") {
    requireAuthorizedOperation("workflow_template_write");
    requireRelationalStoreAvailable();
    sendStoreResult(
      res,
      runWorkflowTemplateStore(
        ["update-step", decodeURIComponent(match[1]), decodeURIComponent(match[2])],
        await readJsonBody(req)
      ),
      "workflow_template_store_unavailable"
    );
    return true;
  }

  if (match && req.method === "DELETE") {
    requireAuthorizedOperation("workflow_template_write");
    requireRelationalStoreAvailable();
    sendStoreResult(
      res,
      runWorkflowTemplateStore(
        ["delete-step", decodeURIComponent(match[1]), decodeURIComponent(match[2])],
        await readJsonBody(req)
      ),
      "workflow_template_store_unavailable"
    );
    return true;
  }

  return false;
}

const server = http.createServer(async (req, res) => {
  const decodedPath = decodeRequestPath(req.url);
  const urlPath = decodedPath.urlPath;
  instrumentHttpRequest(req, res, urlPath);
  if (!decodedPath.ok) {
    writeJson(res, decodedPath.error.statusCode, {
      ok: false,
      error: decodedPath.error.code,
      detail: decodedPath.error.message
    });
    return;
  }
  try {
    requireSameOriginMutation(req);
    enforceRateLimit(req, res, urlPath);
  } catch (error) {
    writeJson(res, error.statusCode || 400, {
      ok: false,
      error: error.code || "request_security_rejected",
      detail: error.message
    });
    return;
  }
  if (req.url === "/events") {
    res.writeHead(200, eventStreamHeaders);
    res.write("\n");
    clients.add(res);
    req.on("close", () => clients.delete(res));
    return;
  }

  if (urlPath === "/api/platform/v1/view-model") {
    sendRustPlatformView(res);
    return;
  }
  try {
    if (await handleAuthRoutes(req, res, urlPath)) return;
    if (await handleHrEmployees(req, res, urlPath)) return;
    if (await handleArchiveIntake(req, res, urlPath)) return;
    if (await handleUserPreferences(req, res, urlPath)) return;
    if (await handleWorkflowTemplates(req, res, urlPath)) return;
  } catch (error) {
    res.writeHead(error.statusCode || 400, { ...noCacheHeaders, "content-type": types[".json"] });
    res.end(JSON.stringify({
      ok: false,
      error: error.code || "invalid_live_store_request",
      detail: error.message,
      reason: error.reason
    }));
    return;
  }
  if (urlPath === "/catalog.json") {
    sendFile(res, path.join(root, "..", "src", "i18n", "catalog.json"));
    return;
  }
  if (urlPath === "/" || urlPath === "/index.html") {
    sendIndex(res);
    return;
  }
  const safePath = urlPath;
  const filePath = path.normalize(path.join(root, safePath));
  if (!filePath.startsWith(root)) {
    res.writeHead(403, { ...noCacheHeaders, "content-type": "text/plain; charset=utf-8" });
    res.end("Forbidden");
    return;
  }
  sendFile(res, filePath);
});

for (const filePath of [
  path.join(root, "index.html"),
  path.join(root, "styles.css"),
  path.join(root, "app.js"),
  path.join(root, "..", "src", "i18n", "catalog.json")
]) {
  fs.watch(filePath, { persistent: false }, () => {
    for (const client of clients) client.write("event: reload\ndata: now\n\n");
  });
}

server.listen(port, "127.0.0.1", () => {
  console.log(`Bitween Rust live UI running at http://127.0.0.1:${port}`);
});
