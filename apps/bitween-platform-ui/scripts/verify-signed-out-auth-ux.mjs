import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appRoot = join(__dirname, "..");
const catalog = JSON.parse(readFileSync(join(appRoot, "src", "i18n", "catalog.json"), "utf8"));
const appSource = readFileSync(join(appRoot, "preview", "app.js"), "utf8");

function response(ok, body, status = ok ? 200 : 503) {
  return {
    ok,
    status,
    async json() {
      return body;
    }
  };
}

function liveView(authenticated = false) {
  return {
    schema: "bitween.platform.live.v1",
    session: {
      authenticated,
      tenant_id: "tenant-acme",
      tenant_name: "Acme"
    },
    navigation: [
      { id: "home" },
      { id: "hr" },
      { id: "payroll" },
      { id: "workflow" },
      { id: "approval" },
      { id: "archive" },
      { id: "admin" }
    ],
    work_queue: [],
    calendar: [],
    payroll_workstream: { steps: [] }
  };
}

function authRouteStatus(configured) {
  const routes = Object.fromEntries(["signin", "signup", "onboarding", "signout"].map((action) => [
    action,
    { action, configured, source: configured ? "environment" : "missing" }
  ]));
  return {
    ok: true,
    schema: "bitween.auth-routes.v1",
    configured,
    missing: configured ? [] : Object.keys(routes),
    routes
  };
}

async function renderSignedOut(configured) {
  let html = "";
  const appElement = {
    get innerHTML() {
      return html;
    },
    set innerHTML(value) {
      html = String(value);
    }
  };
  const document = {
    documentElement: {
      lang: "",
    },
    title: "",
    getElementById(id) {
      if (id === "app") return appElement;
      if (id === "toast") return { classList: { add() {}, remove() {} }, textContent: "" };
      return null;
    },
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    }
  };
  const context = {
    console,
    document,
    EventSource: undefined,
    FormData: class FormData {},
    window: {
      clearTimeout,
      location: {
        assign() {
          throw new Error("Signed-out verification must not navigate.");
        },
        reload() {}
      },
      setTimeout
    },
    fetch: async (url) => {
      if (url === "/catalog.json") return response(true, catalog);
      if (url === "/api/platform/v1/view-model") return response(true, liveView(false));
      if (url === "/api/hr/v1/employees") return response(true, { employees: [] });
      if (url === "/api/archive/v1/intake") return response(true, { intakes: [] });
      if (url === "/api/settings/v1/preferences") return response(true, { current: { locale: "ko-KR" } });
      if (url === "/api/auth/v1/routes") return response(true, authRouteStatus(configured));
      return response(false, { error: "unexpected_url", url });
    },
    setTimeout,
    clearTimeout
  };
  vm.runInNewContext(appSource, context, { filename: "preview/app.js" });
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if (html.includes("signed-out-panel")) return html;
    await delay(10);
  }
  throw new Error("Signed-out preview did not render.");
}

function assertIncludes(html, text, message) {
  if (!html.includes(text)) throw new Error(message);
}

function assertExcludes(html, text, message) {
  if (html.includes(text)) throw new Error(message);
}

const missingHtml = await renderSignedOut(false);
assertIncludes(missingHtml, "회사 계정 연결 필요", "Missing auth routes must show concise setup guidance.");
assertIncludes(missingHtml, "관리자가 로그인, 가입 요청, 온보딩 경로를 연결하면 시작할 수 있습니다.", "Missing auth route guidance must be operator-actionable.");
assertIncludes(missingHtml, "disabled", "Missing auth route buttons must render disabled.");
assertExcludes(missingHtml, "회사 인증 주소가 설정되지 않았습니다", "Signed-out UX must not expose the dead-end missing-address copy.");
assertExcludes(missingHtml, "data-auth-action=\"signin\"", "Missing sign-in route must not be clickable.");
assertExcludes(missingHtml, "data-auth-action=\"signup\"", "Missing sign-up route must not be clickable.");
assertExcludes(missingHtml, "data-auth-action=\"onboarding\"", "Missing onboarding route must not be clickable.");

const configuredHtml = await renderSignedOut(true);
assertExcludes(configuredHtml, "회사 계정 연결 필요", "Configured auth routes must not show setup guidance.");
assertIncludes(configuredHtml, "data-auth-action=\"signin\"", "Configured sign-in route must be clickable.");
assertIncludes(configuredHtml, "data-auth-action=\"signup\"", "Configured sign-up route must be clickable.");
assertIncludes(configuredHtml, "data-auth-action=\"onboarding\"", "Configured onboarding route must be clickable.");

console.log("Signed-out auth UX verification passed.");
