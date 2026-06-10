import { spawn } from "node:child_process";
import http from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appRoot = join(__dirname, "..");
const serverPath = join(appRoot, "preview", "server.js");
const basePort = 4300 + (process.pid % 400);

const configuredRoutes = {
  "/api/auth/v1/signin": "https://auth.example.com/signin",
  "/api/auth/v1/signup": "https://auth.example.com/request-access",
  "/api/onboarding/v1/start": "https://onboarding.example.com/start"
};
const configuredPostRoutes = {
  "/api/auth/v1/signout": "https://auth.example.com/signout"
};

function requestJson(port, method, path) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        hostname: "127.0.0.1",
        method,
        path,
        port,
        timeout: 2000
      },
      (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          const body = Buffer.concat(chunks).toString("utf8");
          try {
            resolve({ body: body ? JSON.parse(body) : {}, statusCode: res.statusCode ?? 0 });
          } catch (error) {
            reject(new Error(`Invalid JSON from ${method} ${path}: ${error.message}`));
          }
        });
      }
    );
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy(new Error(`Timed out requesting ${method} ${path}`));
    });
    req.end();
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
  for (let attempt = 0; attempt < 20; attempt += 1) {
    try {
      await requestJson(port, "GET", "/api/auth/v1/signin");
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

async function verifyConfiguredRoutes() {
  const port = basePort;
  await withServer(
    port,
    {
      BITWEEN_AUTH_SIGNIN_URL: configuredRoutes["/api/auth/v1/signin"],
      BITWEEN_AUTH_SIGNUP_URL: configuredRoutes["/api/auth/v1/signup"],
      BITWEEN_AUTH_SIGNOUT_URL: configuredPostRoutes["/api/auth/v1/signout"],
      BITWEEN_ONBOARDING_START_URL: configuredRoutes["/api/onboarding/v1/start"]
    },
    async () => {
      for (const [path, expectedUrl] of Object.entries(configuredRoutes)) {
        const response = await requestJson(port, "GET", path);
        if (response.statusCode !== 200 || response.body.url !== expectedUrl || response.body.ok !== true) {
          throw new Error(`Configured route failed for ${path}: ${JSON.stringify(response)}`);
        }
      }
      for (const [path, expectedUrl] of Object.entries(configuredPostRoutes)) {
        const response = await requestJson(port, "POST", path);
        if (response.statusCode !== 200 || response.body.url !== expectedUrl || response.body.ok !== true) {
          throw new Error(`Configured route failed for ${path}: ${JSON.stringify(response)}`);
        }
      }
      const status = await requestJson(port, "GET", "/api/auth/v1/routes");
      if (
        status.statusCode !== 200 ||
        status.body.schema !== "bitween.auth-routes.v1" ||
        status.body.configured !== true ||
        status.body.routes?.signin?.configured !== true ||
        status.body.routes?.signup?.configured !== true ||
        status.body.routes?.onboarding?.configured !== true ||
        status.body.routes?.signout?.configured !== true
      ) {
        throw new Error(`Configured route status failed: ${JSON.stringify(status)}`);
      }
    }
  );
}

async function verifyMissingRoutesFailClosed() {
  const port = basePort + 1;
  await withServer(port, {}, async () => {
    const status = await requestJson(port, "GET", "/api/auth/v1/routes");
    if (status.statusCode !== 200 || status.body.configured !== false || !status.body.missing?.includes("signin")) {
      throw new Error(`Missing auth route status must be actionable: ${JSON.stringify(status)}`);
    }
    const response = await requestJson(port, "GET", "/api/auth/v1/signin");
    if (response.statusCode !== 503 || response.body.ok !== false || response.body.error !== "auth_route_unconfigured") {
      throw new Error(`Missing auth route must fail closed: ${JSON.stringify(response)}`);
    }
  });
}

async function verifyInsecureRoutesFailClosed() {
  const port = basePort + 2;
  await withServer(
    port,
    {
      BITWEEN_AUTH_SIGNIN_URL: "http://auth.example.com/signin",
      BITWEEN_AUTH_SIGNUP_URL: configuredRoutes["/api/auth/v1/signup"],
      BITWEEN_AUTH_SIGNOUT_URL: configuredPostRoutes["/api/auth/v1/signout"],
      BITWEEN_ONBOARDING_START_URL: configuredRoutes["/api/onboarding/v1/start"]
    },
    async () => {
      const status = await requestJson(port, "GET", "/api/auth/v1/routes");
      if (status.statusCode !== 200 || status.body.configured !== false || status.body.routes?.signin?.configured !== false) {
        throw new Error(`Insecure auth route must be treated as unconfigured: ${JSON.stringify(status)}`);
      }
      const response = await requestJson(port, "GET", "/api/auth/v1/signin");
      if (response.statusCode !== 503 || response.body.ok !== false || response.body.error !== "auth_route_unconfigured") {
        throw new Error(`Insecure auth route must fail closed: ${JSON.stringify(response)}`);
      }
    }
  );
}

async function verifyDisallowedRouteOriginFailsClosed() {
  const port = basePort + 3;
  await withServer(
    port,
    {
      BITWEEN_AUTH_EXPECTED_ISSUER: "https://auth.example.com",
      BITWEEN_AUTH_SIGNIN_URL: "https://attacker.example/signin",
      BITWEEN_AUTH_SIGNUP_URL: configuredRoutes["/api/auth/v1/signup"],
      BITWEEN_AUTH_SIGNOUT_URL: configuredPostRoutes["/api/auth/v1/signout"],
      BITWEEN_ONBOARDING_START_URL: configuredRoutes["/api/onboarding/v1/start"]
    },
    async () => {
      const status = await requestJson(port, "GET", "/api/auth/v1/routes");
      if (status.statusCode !== 200 || status.body.configured !== false || status.body.routes?.signin?.configured !== false) {
        throw new Error(`Auth route origin outside expected issuer must be treated as unconfigured: ${JSON.stringify(status)}`);
      }
      const response = await requestJson(port, "GET", "/api/auth/v1/signin");
      if (response.statusCode !== 503 || response.body.ok !== false || response.body.error !== "auth_route_unconfigured") {
        throw new Error(`Auth route origin outside expected issuer must fail closed: ${JSON.stringify(response)}`);
      }
    }
  );
}

await verifyConfiguredRoutes();
await verifyMissingRoutesFailClosed();
await verifyInsecureRoutesFailClosed();
await verifyDisallowedRouteOriginFailsClosed();
console.log("Auth route verification passed.");
