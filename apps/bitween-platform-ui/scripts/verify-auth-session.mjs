import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import http from "node:http";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appRoot = join(__dirname, "..");
const repoRoot = join(appRoot, "..", "..");
const serverPath = join(appRoot, "preview", "server.js");
const packagePath = join(appRoot, "package.json");
const workflowPath = join(repoRoot, ".github", "workflows", "tests.yml");
const runtimeVerifierPath = join(__dirname, "verify-runtime-data-mode.mjs");
const rustAuthSessionPath = join(repoRoot, "crates", "payroll-api", "src", "auth_session.rs");
const rustAuthSessionSchemaPath = join(repoRoot, "crates", "payroll-api", "src", "auth_session_schema.rs");
const rustAuthSessionBinPath = join(repoRoot, "crates", "payroll-api", "src", "bin", "auth_session_validate.rs");
const rustAuthSessionMigrationPath = join(repoRoot, "crates", "payroll-api", "migrations", "007_auth_session_security.sql");
const authSecurityContractPath = join(repoRoot, "docs", "AUTH_SECURITY_CONTRACT.md");
const buckPath = join(repoRoot, "crates", "payroll-api", "BUCK");
const serverSource = readFileSync(serverPath, "utf8");
const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
const workflowSource = readFileSync(workflowPath, "utf8");
const runtimeVerifierSource = readFileSync(runtimeVerifierPath, "utf8");
const rustAuthSessionSource = readFileSync(rustAuthSessionPath, "utf8");
const rustAuthSessionSchemaSource = readFileSync(rustAuthSessionSchemaPath, "utf8");
const rustAuthSessionBinSource = readFileSync(rustAuthSessionBinPath, "utf8");
const rustAuthSessionMigrationSource = readFileSync(rustAuthSessionMigrationPath, "utf8");
const authSecurityContractSource = readFileSync(authSecurityContractPath, "utf8");
const buckSource = readFileSync(buckPath, "utf8");
const errors = [];

const testJwt = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InRlc3Qta2V5LTEifQ.eyJpc3MiOiJodHRwczovL2F1dGguYWNtZS5leGFtcGxlIiwic3ViIjoidXNlci1saXZlLW9wcyIsImF1ZCI6ImJpdHdlZW4tcGxhdGZvcm0iLCJleHAiOjQxMDI0NDQ4MDAsIm5iZiI6MTcwMDAwMDAwMCwiaWF0IjoxNzAwMDAwMDAwLCJqdGkiOiJzZXNzaW9uLXRva2VuLTAwMSIsImFjciI6InNlbnNpdGl2ZSIsImF1dGhfdGltZSI6MTcwMDAwMDAwMCwiYW1yIjpbInB3ZCIsIndlYmF1dGhuIl0sImJpdHdlZW5fcm9sZSI6InBheXJvbGxfbWFuYWdlciIsImJpdHdlZW5fdGVuYW50X2lkIjoidGVuYW50LWFjbWUiLCJiaXR3ZWVuX2xlZ2FsX2VudGl0eSI6IkFjbWUiLCJiaXR3ZWVuX3dvcmtwbGFjZSI6IlNlb3VsIn0.C5cBG8-5NUAfjf2zzua4IvNtYSLs11eHTF96G1kwSSDxfsBNCBw731oJAbxGmnlzZi9RVZTH0bjC2sf5ldqIb5T0g2z3KyH7V1DeMg0uZERm7J4evWaJ3VnHh5RYEgO06mM7zD9XBU7hS4-_32Ol1wQ4KPuoH9wfTc9798YKTlIIm_hYgH42IUoB_Snws2GgdVJ-CwnCKwZubIJ_bdPj8c6UXREaxlz6Up5Z8Xfgfbtrt5ENnAmCe4NX6Uy605ukwzVUSK7pep7wD-u6UAB0k2SbSAEz-oL_6CiYJcHLx5CVHl4BceaB_coaGL4mdOw-nflOelaL8GPDN-jhS5NiJw";
const testJwks = JSON.stringify({ keys: [{ kty: "RSA", n: "mwaczqZWd1GkBo8DQtJAEjFd4v4XGkBQt1KI7Flawe0lW9omwfolE6dut3Rrff4qhI3ncSjIOlf8NZ4EMmkH5wL6ktdRj0MWpDvSj7ZPAi1RvdKL6KrUGxpMtQymivPn2dd37KtaxZB4vbXYMU8vPJki3tjpI3bGNePRvmd8eYP2h5QmDXZFcqZJZ3oBIzKxH7NFjgZUetysXNvZLKqvLdnez_uCD83KoqV81l97IMJCHFBmoTnO3wyD0QXnBvNbyW7Sat8ekgx9PHuv8AhWjze9di4dy7n-Im2fN7Mry0afvFCpxmqj-vqVru8igUw13ngqq9vxjQ047zs5SWMMgQ", e: "AQAB", kid: "test-key-1", alg: "RS256", use: "sig" }] });
const testJwksUri = "https://auth.acme.example/.well-known/jwks.json";
const testOidcDiscovery = JSON.stringify({
  issuer: "https://auth.acme.example",
  jwks_uri: testJwksUri,
  response_types_supported: ["code"],
  subject_types_supported: ["public"],
  id_token_signing_alg_values_supported: ["RS256"],
});

function requireText(source, text, message) {
  if (!source.includes(text)) errors.push(message);
}

function assertStaticContracts() {
  if (packageJson.scripts?.["verify:auth-session"] !== "node scripts/verify-auth-session.mjs") {
    errors.push("package.json must expose verify:auth-session for Rust JWT/JWKS evidence.");
  }
  requireText(workflowSource, "npm run verify:auth-session", ".github/workflows/tests.yml must run verify:auth-session in CI.");
  requireText(runtimeVerifierSource, "verify-auth-session.mjs", "verify-runtime-data-mode.mjs must guard auth-session verification wiring.");
  requireText(buckSource, 'name = "auth_session_validate"', "crates/payroll-api/BUCK must build the auth_session_validate binary.");
  requireText(buckSource, 'name = "auth_session_validate_test"', "crates/payroll-api/BUCK must test the auth_session_validate binary.");
  requireText(workflowSource, "buck2 build //crates/payroll-api:auth_session_validate", "CI must build the Rust auth session validator.");
  requireText(workflowSource, "buck2 test //crates/payroll-api:auth_session_validate_test", "CI must test the Rust auth session validator.");
  requireText(serverSource, '"//crates/payroll-api:auth_session_validate"', "preview/server.js must call the Rust auth_session_validate target.");
  requireText(serverSource, "authSessionEnvForRustTargets", "preview/server.js must derive Rust target session env from the verifier.");
  requireText(serverSource, "deniedAuthSessionEnv", "preview/server.js must force an unauthenticated session when JWT validation fails.");
  requireText(serverSource, "BITWEEN_DEV_AUTH_BYPASS", "preview/server.js dev auth bypass must be gated behind an explicit opt-in env var.");
  requireText(serverSource, "isProductionSignal", "preview/server.js must detect production from the deployment's real signals to disable the dev auth bypass.");
  requireText(serverSource, "BITWEEN_RUNTIME_MODE", "preview/server.js production guard must honor BITWEEN_RUNTIME_MODE, the deployed production marker.");
  requireText(serverSource, "BITWEEN_AUTH_REQUIRED", "preview/server.js production guard must honor BITWEEN_AUTH_REQUIRED, the deployed production marker.");
  requireText(serverSource, "Refusing to start", "preview/server.js must refuse to boot when the dev auth bypass is requested in production.");
  requireText(serverSource, "devAuthBypassActive = devAuthBypassRequested && !isProductionEnv", "preview/server.js dev auth bypass must only activate outside production.");
  requireText(rustAuthSessionSource, "AUTH_SESSION_SCHEMA", "Rust auth session verifier must expose a stable schema.");
  requireText(rustAuthSessionSource, "AUTH_OIDC_DISCOVERY_SCHEMA", "Rust auth session verifier must expose a stable OIDC discovery schema.");
  requireText(rustAuthSessionSource, "validate_oidc_discovery", "Rust auth session verifier must validate OIDC discovery metadata.");
  requireText(rustAuthSessionSource, "oidc_rs256_unsupported", "Rust OIDC discovery validation must reject providers that do not advertise RS256.");
  requireText(rustAuthSessionSource, "oidc_jwks_uri_untrusted", "Rust OIDC discovery validation must reject non-HTTPS JWKS URIs.");
  requireText(rustAuthSessionSource, "AUTH_SESSION_ALLOWED_ALGORITHM", "Rust auth session verifier must keep an explicit algorithm allow-list.");
  requireText(rustAuthSessionSource, "RsaPublicKeyComponents", "Rust auth session verifier must verify RS256 signatures against JWKS RSA components.");
  requireText(rustAuthSessionSource, "jwt_alg_untrusted", "Rust auth session verifier must reject untrusted JWT algorithms.");
  requireText(rustAuthSessionSource, "jwt_signature_invalid", "Rust auth session verifier must reject invalid signatures.");
  requireText(rustAuthSessionSource, "jwt_audience_mismatch", "Rust auth session verifier must enforce expected audience.");
  requireText(rustAuthSessionSource, "webauthn_user_verification_missing", "Rust auth session verifier must require passkey/WebAuthn user verification evidence.");
  requireText(rustAuthSessionSource, "AUTH_WEBAUTHN_ASSERTION_SCHEMA", "Rust auth session verifier must expose a stable WebAuthn assertion verification schema.");
  requireText(rustAuthSessionSource, "WebAuthnAssertionVerifierConfig", "Rust auth session verifier must model WebAuthn relying-party assertion configuration.");
  requireText(rustAuthSessionSource, "verify_webauthn_assertion", "Rust auth session verifier must validate WebAuthn/passkey assertions server-side.");
  requireText(rustAuthSessionSource, "webauthn_challenge_mismatch", "Rust WebAuthn verifier must fail closed on challenge mismatch.");
  requireText(rustAuthSessionSource, "webauthn_origin_mismatch", "Rust WebAuthn verifier must fail closed on origin mismatch.");
  requireText(rustAuthSessionSource, "webauthn_rp_id_hash_mismatch", "Rust WebAuthn verifier must bind assertions to the configured RP ID.");
  requireText(rustAuthSessionSource, "webauthn_user_not_verified", "Rust WebAuthn verifier must require the UV flag.");
  requireText(rustAuthSessionSource, "webauthn_sign_count_replayed", "Rust WebAuthn verifier must reject replayed nonzero signature counters.");
  requireText(rustAuthSessionSource, "ECDSA_P256_SHA256_ASN1", "Rust WebAuthn verifier must verify ES256 authenticator signatures.");
  requireText(rustAuthSessionBinSource, "BITWEEN_SESSION_JWT", "auth_session_validate must read the token from an environment boundary without logging it.");
  requireText(rustAuthSessionBinSource, "BITWEEN_AUTH_JWKS_JSON", "auth_session_validate must read JWKS JSON from configuration.");
  requireText(rustAuthSessionBinSource, "BITWEEN_AUTH_OIDC_CONFIGURATION_JSON", "auth_session_validate must validate OIDC discovery metadata when configured.");
  requireText(rustAuthSessionBinSource, "BITWEEN_AUTH_EXPECTED_JWKS_URI", "auth_session_validate must support expected JWKS URI pinning.");
  requireText(rustAuthSessionBinSource, "enforce_oidc_discovery_if_configured", "auth_session_validate must fail closed on invalid OIDC discovery metadata.");
  requireText(rustAuthSessionBinSource, "BITWEEN_WEBAUTHN_ASSERTION_JSON", "auth_session_validate must support server-side WebAuthn assertion verification when assertion evidence is supplied.");
  requireText(rustAuthSessionBinSource, "enforce_webauthn_assertion_if_configured", "auth_session_validate must fail closed on invalid WebAuthn assertion evidence.");
  requireText(rustAuthSessionBinSource, "BITWEEN_AUTH_SESSION_SECURITY_MODE", "auth_session_validate must support an explicit PostgreSQL security-store mode.");
  requireText(rustAuthSessionBinSource, "auth_session_security_store_required", "auth_session_validate must fail closed when PostgreSQL security mode lacks a DSN.");
  requireText(rustAuthSessionBinSource, "jwt_revoked", "auth_session_validate must reject revoked hashed JWT IDs from PostgreSQL.");
  requireText(rustAuthSessionBinSource, "auth_session_event_audit_failed", "auth_session_validate must fail closed when session audit cannot be written.");
  requireText(rustAuthSessionBinSource, "auth_session_revocation_lookup_sql", "auth_session_validate must use the shared revocation SQL contract.");
  requireText(rustAuthSessionBinSource, "auth_session_event_insert_sql", "auth_session_validate must use the shared session audit SQL contract.");
  requireText(rustAuthSessionBinSource, "hex_sha256(&verification.subject)", "auth_session_validate must hash subjects before session audit writes.");
  requireText(rustAuthSessionSchemaSource, "AUTH_SESSION_POSTGRES_SCHEMA_VERSION", "Rust auth session PostgreSQL contract must expose a stable schema version.");
  requireText(rustAuthSessionSchemaSource, "bitween_auth.jwt_revocation", "Rust auth session PostgreSQL contract must declare the revocation table.");
  requireText(rustAuthSessionSchemaSource, "bitween_auth.session_event_audit", "Rust auth session PostgreSQL contract must declare the audit table.");
  requireText(rustAuthSessionSchemaSource, "auth_session_revocation_lookup_sql", "Rust auth session PostgreSQL contract must expose parameterized revocation SQL.");
  requireText(rustAuthSessionSchemaSource, "auth_session_event_insert_sql", "Rust auth session PostgreSQL contract must expose parameterized audit SQL.");
  requireText(rustAuthSessionMigrationSource, "ALTER TABLE bitween_auth.jwt_revocation ENABLE ROW LEVEL SECURITY", "Auth session migration must enforce tenant RLS on revocations.");
  requireText(rustAuthSessionMigrationSource, "ALTER TABLE bitween_auth.session_event_audit ENABLE ROW LEVEL SECURITY", "Auth session migration must enforce tenant RLS on session audit.");
  requireText(rustAuthSessionMigrationSource, "jwt_id_sha256 char(64)", "Auth session migration must persist hashed JWT IDs only.");
  requireText(rustAuthSessionMigrationSource, "subject_sha256 char(64)", "Auth session migration must persist hashed subject IDs only.");
  requireText(buckSource, "migrations/007_auth_session_security.sql", "crates/payroll-api/BUCK must include the auth session security migration.");
  requireText(buckSource, "src/auth_session_schema.rs", "crates/payroll-api/BUCK must include the auth session PostgreSQL contract source.");
  requireText(buckSource, "//third-party/rust:sha2", "auth_session_validate Buck target must depend on sha2 for subject hashing.");
  requireText(buckSource, "//third-party/rust:tokio", "auth_session_validate Buck target must depend on tokio for PostgreSQL security-store enforcement.");
  requireText(authSecurityContractSource, "Rust WebAuthn assertion verification slice", "docs/AUTH_SECURITY_CONTRACT.md must document the Rust WebAuthn assertion verification slice.");
  requireText(authSecurityContractSource, "BITWEEN_WEBAUTHN_ASSERTION_JSON", "docs/AUTH_SECURITY_CONTRACT.md must document the WebAuthn assertion env boundary.");
  requireText(authSecurityContractSource, "webauthn_sign_count_replayed", "docs/AUTH_SECURITY_CONTRACT.md must document replay-counter rejection.");
  requireText(authSecurityContractSource, "server-side assertion boundary", "docs/AUTH_SECURITY_CONTRACT.md must describe the verified server-side WebAuthn assertion boundary.");
}

function authEnv(token = testJwt) {
  return {
    BITWEEN_AUTH_EXPECTED_AUDIENCE: "bitween-platform",
    BITWEEN_AUTH_EXPECTED_ISSUER: "https://auth.acme.example",
    BITWEEN_AUTH_EXPECTED_JWKS_URI: testJwksUri,
    BITWEEN_AUTH_JWKS_JSON: testJwks,
    BITWEEN_AUTH_OIDC_CONFIGURATION_JSON: testOidcDiscovery,
    BITWEEN_AUTH_SIGNIN_URL: "https://auth.acme.example/signin",
    BITWEEN_AUTH_SIGNOUT_URL: "https://auth.acme.example/signout",
    BITWEEN_AUTH_SIGNUP_URL: "https://auth.acme.example/request-access",
    BITWEEN_HTTP_TELEMETRY: "off",
    BITWEEN_ONBOARDING_START_URL: "https://onboarding.acme.example/start",
    BITWEEN_SESSION_JWT: token,
    BITWEEN_SESSION_NOW_UNIX: "1800000000",
  };
}

function parseJsonOutput(label, result) {
  try {
    return JSON.parse(result.stdout || "{}");
  } catch (error) {
    errors.push(`${label} returned invalid JSON: ${error.message}; stderr=${result.stderr.slice(0, 240)}`);
    return {};
  }
}

function assertBinaryValidation() {
  const ok = spawnSync("buck2", ["run", "//crates/payroll-api:auth_session_validate"], {
    cwd: repoRoot,
    encoding: "utf8",
    env: { ...process.env, ...authEnv() },
    timeout: 30000,
  });
  const verification = parseJsonOutput("auth_session_validate valid token", ok);
  if (ok.status !== 0 || verification.verified !== true || verification.reason !== "verified") {
    errors.push(`valid auth_session_validate run should verify the token: ${JSON.stringify({ status: ok.status, verification, stderr: ok.stderr.slice(0, 240) })}`);
  }
  if (verification.subject !== "user-live-ops" || verification.role !== "payroll_manager" || verification.acr_level !== "sensitive") {
    errors.push("auth_session_validate must emit stable sanitized session facts for Rust targets.");
  }
  if (typeof verification.jwt_id_sha256 !== "string" || verification.jwt_id_sha256.length !== 64) {
    errors.push("auth_session_validate must hash JWT IDs instead of echoing raw replay identifiers.");
  }

  const invalidToken = `${testJwt.slice(0, -1)}A`;
  const denied = spawnSync("buck2", ["run", "//crates/payroll-api:auth_session_validate"], {
    cwd: repoRoot,
    encoding: "utf8",
    env: { ...process.env, ...authEnv(invalidToken) },
    timeout: 30000,
  });
  const deniedVerification = parseJsonOutput("auth_session_validate invalid token", denied);
  if (denied.status === 0 || deniedVerification.verified !== false || deniedVerification.reason !== "jwt_signature_invalid") {
    errors.push(`invalid auth_session_validate run must fail closed on signature: ${JSON.stringify({ status: denied.status, deniedVerification, stderr: denied.stderr.slice(0, 240) })}`);
  }
  if (deniedVerification.subject || deniedVerification.jwt_id_sha256) {
    errors.push("invalid auth_session_validate output must not leak subject or raw replay identifier facts.");
  }

  const wrongIssuerDiscovery = JSON.stringify({
    ...JSON.parse(testOidcDiscovery),
    issuer: "https://wrong-issuer.example",
  });
  const badDiscovery = spawnSync("buck2", ["run", "//crates/payroll-api:auth_session_validate"], {
    cwd: repoRoot,
    encoding: "utf8",
    env: {
      ...process.env,
      ...authEnv(),
      BITWEEN_AUTH_OIDC_CONFIGURATION_JSON: wrongIssuerDiscovery,
    },
    timeout: 30000,
  });
  const badDiscoveryVerification = parseJsonOutput("auth_session_validate invalid OIDC discovery", badDiscovery);
  if (
    badDiscovery.status === 0 ||
    badDiscoveryVerification.verified !== false ||
    badDiscoveryVerification.reason !== "oidc_issuer_mismatch"
  ) {
    errors.push(`auth_session_validate must fail closed on OIDC discovery issuer mismatch: ${JSON.stringify({
      status: badDiscovery.status,
      verification: badDiscoveryVerification,
      stderr: badDiscovery.stderr.slice(0, 240),
    })}`);
  }

  const missingSecurityStore = spawnSync("buck2", ["run", "//crates/payroll-api:auth_session_validate"], {
    cwd: repoRoot,
    encoding: "utf8",
    env: {
      ...process.env,
      ...authEnv(),
      BITWEEN_AUTH_SESSION_SECURITY_MODE: "postgres",
      BITWEEN_POSTGRES_DSN: "",
    },
    timeout: 30000,
  });
  const missingSecurityStoreVerification = parseJsonOutput("auth_session_validate missing PostgreSQL security store", missingSecurityStore);
  if (
    missingSecurityStore.status === 0 ||
    missingSecurityStoreVerification.verified !== false ||
    missingSecurityStoreVerification.reason !== "auth_session_security_store_required"
  ) {
    errors.push(`PostgreSQL auth-session security mode must fail closed without a DSN: ${JSON.stringify({
      status: missingSecurityStore.status,
      verification: missingSecurityStoreVerification,
      stderr: missingSecurityStore.stderr.slice(0, 240),
    })}`);
  }
}

function requestJson(port, path) {
  return new Promise((resolve, reject) => {
    const req = http.request({ hostname: "127.0.0.1", method: "GET", path, port, timeout: 30000 }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        const text = Buffer.concat(chunks).toString("utf8");
        try {
          resolve({ body: text ? JSON.parse(text) : {}, headers: res.headers, statusCode: res.statusCode || 0 });
        } catch (error) {
          reject(new Error(`Invalid JSON from ${path}: ${error.message}; body=${text.slice(0, 160)}`));
        }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error(`Timed out requesting ${path}`)));
    req.end();
  });
}

function launchServer(port, extraEnv) {
  const child = spawn(process.execPath, [serverPath, String(port)], {
    cwd: appRoot,
    env: { ...process.env, ...extraEnv, PORT: String(port) },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let stderr = "";
  child.stderr.on("data", (chunk) => { stderr += chunk.toString("utf8"); });
  child.stdout.on("data", () => {});
  return { child, stderr: () => stderr };
}

async function waitForServer(port) {
  let lastError;
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await requestJson(port, "/api/auth/v1/routes");
      if (response.statusCode === 200) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw lastError || new Error("Preview server did not start.");
}

async function withServer(port, env, fn) {
  const server = launchServer(port, env);
  try {
    await waitForServer(port);
    await fn(server);
  } finally {
    server.child.kill("SIGTERM");
  }
}

async function assertPreviewSessionWiring() {
  const port = 5900 + (process.pid % 200);
  await withServer(port, authEnv(), async () => {
    const response = await requestJson(port, "/api/platform/v1/view-model");
    if (response.statusCode !== 200) errors.push(`verified session view returned ${response.statusCode}`);
    if (response.body?.session?.authenticated !== true || response.body?.session?.role !== "payroll_manager") {
      errors.push(`verified JWT/JWKS session must authenticate the Rust live payload: ${JSON.stringify(response.body?.session)}`);
    }
  });

  const invalidPort = port + 1;
  await withServer(invalidPort, authEnv(`${testJwt.slice(0, -1)}A`), async () => {
    const response = await requestJson(invalidPort, "/api/platform/v1/view-model");
    if (response.statusCode !== 200) errors.push(`invalid session view returned ${response.statusCode}`);
    if (response.body?.session?.authenticated !== false || response.body?.session?.mode !== "auth_required") {
      errors.push(`invalid JWT/JWKS session must fail closed in the Rust live payload: ${JSON.stringify(response.body?.session)}`);
    }
  });

  // Dev auth bypass authenticates with NO JWT configured (local testing only).
  const bypassPort = port + 2;
  await withServer(bypassPort, { BITWEEN_DEV_AUTH_BYPASS: "1", BITWEEN_HTTP_TELEMETRY: "off" }, async () => {
    const response = await requestJson(bypassPort, "/api/platform/v1/view-model");
    if (response.body?.session?.authenticated !== true || response.body?.session?.role !== "platform_owner") {
      errors.push(`dev auth bypass must authenticate a platform_owner session without a JWT: ${JSON.stringify(response.body?.session)}`);
    }
  });
}

async function assertDevBypassRefusesProduction() {
  // The critical safety property: production can never bypass auth. The server
  // must exit non-zero and never bind a socket when the bypass is requested
  // alongside ANY production signal the deployment actually sets — not just
  // NODE_ENV (which the k8s configmap does not set) but the authoritative
  // BITWEEN_RUNTIME_MODE and BITWEEN_AUTH_REQUIRED markers.
  const productionSignals = [
    { label: "NODE_ENV=production", env: { NODE_ENV: "production" } },
    { label: "BITWEEN_RUNTIME_MODE=production", env: { BITWEEN_RUNTIME_MODE: "production" } },
    { label: "BITWEEN_AUTH_REQUIRED=true", env: { BITWEEN_AUTH_REQUIRED: "true" } },
  ];
  let offset = 7;
  for (const signal of productionSignals) {
    const port = 5900 + ((process.pid + offset) % 200);
    offset += 1;
    const { child, stderr } = launchServer(port, {
      BITWEEN_DEV_AUTH_BYPASS: "1",
      BITWEEN_HTTP_TELEMETRY: "off",
      ...signal.env,
    });
    const exitCode = await new Promise((resolve) => {
      child.once("exit", (code) => resolve(code));
      setTimeout(() => { try { child.kill("SIGKILL"); } catch {} resolve("timeout"); }, 10000);
    });
    if (exitCode !== 1) {
      errors.push(`dev auth bypass under ${signal.label} must refuse to boot (exit 1), got: ${exitCode}`);
    }
    if (!stderr().includes("Refusing to start")) {
      errors.push(`dev auth bypass under ${signal.label} must log a clear refusal to start.`);
    }
  }
}

assertStaticContracts();
assertBinaryValidation();
await assertPreviewSessionWiring();
await assertDevBypassRefusesProduction();

if (errors.length > 0) {
  console.error("Auth session verification failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("Auth session verification passed.");
