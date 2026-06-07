import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appPath = join(__dirname, "..", "App.tsx");
const packagePath = join(__dirname, "..", "package.json");
const previewAppPath = join(__dirname, "..", "preview", "app.js");
const previewServerPath = join(__dirname, "..", "preview", "server.js");
const screensPath = join(__dirname, "..", "src", "screens.tsx");
const viewModelPath = join(__dirname, "..", "src", "viewModel.ts");
const appSource = readFileSync(appPath, "utf8");
const packageSource = readFileSync(packagePath, "utf8");
const previewAppSource = readFileSync(previewAppPath, "utf8");
const previewServerSource = readFileSync(previewServerPath, "utf8");
const screensSource = readFileSync(screensPath, "utf8");
const viewModelSource = readFileSync(viewModelPath, "utf8");
const packageJson = JSON.parse(packageSource);
const errors = [];

if (!appSource.includes("createEmptyPlatformViewModel")) {
  errors.push("App.tsx must default to an empty non-demo platform view model when no real adapter is wired.");
}

if (!appSource.includes("isDemoDataMode")) {
  errors.push("App.tsx must use an explicit demo mode flag before showing preview data.");
}

if (/useMemo\(\s*\(\)\s*=>\s*getPreviewPlatformViewModel/.test(appSource)) {
  errors.push("App.tsx must not use preview/dummy data as the default view model.");
}

if (!appSource.includes("demoDataEnabled ? getPreviewPlatformViewModel(locale) : createEmptyPlatformViewModel(locale)")) {
  errors.push("App.tsx must keep preview/dummy data behind the explicit demo mode flag.");
}

if (!/\{demoDataEnabled\s*\?\s*\([\s\S]*?preview\.demoMode\.badge[\s\S]*?preview\.demoMode\.title[\s\S]*?preview\.demoMode\.description/.test(appSource)) {
  errors.push("App.tsx must show a visible demo-mode banner when demo data is explicitly enabled.");
}

if (!/accessibilityLabel=\{`\$\{t\(locale, "preview\.demoMode\.title"\)\}\. \$\{t\(locale, "preview\.demoMode\.description"\)\}`\}/.test(appSource)) {
  errors.push("App.tsx demo-mode banner must expose an accessibility label.");
}

if (!appSource.includes('accessibilityRole="summary"')) {
  errors.push("App.tsx demo-mode banner must use a summary accessibility role.");
}

if (packageJson.scripts?.demo !== "node scripts/run-demo-preview.mjs") {
  errors.push("package.json demo script must start the explicit demo preview wrapper.");
}

if (packageJson.scripts?.preview !== "node scripts/run-demo-preview.mjs") {
  errors.push("package.json preview script must route through the explicit demo preview wrapper.");
}

if (!previewServerSource.includes("demo-only preview")) {
  errors.push("preview/server.js startup log must identify the route as demo-only.");
}

if (!/class="demo-mode-banner" role="status" aria-label="\$\{escapeText\(demoModeLabel\)\}"/.test(previewAppSource)) {
  errors.push("preview/app.js demo banner must expose a status role and escaped aria-label.");
}

if (!/id="toast" role="status" aria-live="polite" aria-atomic="true"/.test(previewAppSource)) {
  errors.push("preview/app.js toast must expose a polite atomic status live region.");
}

if (!/el\.setAttribute\("aria-label", text\)/.test(previewAppSource)) {
  errors.push("preview/app.js toast updates must mirror the visible text to aria-label.");
}

if (!screensSource.includes('accessibilityRole="alert"')) {
  errors.push("screens.tsx login feedback must expose alert accessibility role.");
}

if (!/class="inline-warning" role="alert" aria-live="assertive" aria-atomic="true"/.test(previewAppSource)) {
  errors.push("preview/app.js login feedback must expose assertive atomic alert semantics.");
}

if (!/data-language="\$\{locale\}" aria-pressed="\$\{state\.locale === locale \? "true" : "false"\}"/.test(previewAppSource)) {
  errors.push("preview/app.js language buttons must expose pressed state.");
}

if (!screensSource.includes("cossStatutoryBasisDefinitions")) {
  errors.push("screens.tsx demo payroll preview must expose statutory deduction basis checks.");
}

if (!previewAppSource.includes("cossStatutoryBasisDefs")) {
  errors.push("preview/app.js demo payroll preview must mirror statutory deduction basis checks.");
}

if (!screensSource.includes("cossMonthlyFileDefinitions")) {
  errors.push("screens.tsx demo payroll preview must expose the monthly COSS file intake checklist.");
}

if (!previewAppSource.includes("cossMonthlyFileIds")) {
  errors.push("preview/app.js demo payroll preview must mirror the monthly COSS file intake checklist.");
}

if (!screensSource.includes("cossPreviewGuardDefinitions")) {
  errors.push("screens.tsx demo payroll preview must expose the COSS preview data guard.");
}

if (!previewAppSource.includes("cossPreviewGuardDefs")) {
  errors.push("preview/app.js demo payroll preview must mirror the COSS preview data guard.");
}

if (!screensSource.includes("PayrollExecutiveComparePanel")) {
  errors.push("screens.tsx demo payroll preview must expose the executive billing/payroll comparison panel.");
}

if (!previewAppSource.includes("payrollExecutiveComparePanel")) {
  errors.push("preview/app.js demo payroll preview must mirror the executive billing/payroll comparison panel.");
}

if (!screensSource.includes('"payroll.actions.openHrRoster"') || !screensSource.includes('"payroll.actions.siteRules"')) {
  errors.push("screens.tsx payroll actions must include HR roster and workplace-rule entry points.");
}

if (!previewAppSource.includes('"screens.payroll.actions.openHrRoster"') || !previewAppSource.includes('"screens.payroll.actions.siteRules"')) {
  errors.push("preview/app.js payroll actions must include HR roster and workplace-rule entry points.");
}

if (!previewAppSource.includes("${themePanel()}")) {
  errors.push("preview/app.js must move theme controls into the top action area.");
}

if (/function renderHome\(\)[\s\S]*?screens\.launcher\.shortcuts\.title[\s\S]*?function queueDetail/.test(previewAppSource)) {
  errors.push("preview/app.js platform home must not render platform shortcuts.");
}

if (!appSource.includes('"session.emptyCompanyCodeLabel"')) {
  errors.push("App.tsx must replace empty company-code placeholders with a non-demo disconnected label.");
}

if (!appSource.includes('"shell.employeeNumber.empty"')) {
  errors.push("App.tsx must replace empty employee-number placeholders with a non-demo disconnected label.");
}

const emptyModelSource = viewModelSource.split("export const getPreviewSession")[0] ?? "";
if (emptyModelSource.includes('"session.roleLabel"')) {
  errors.push("createEmptyPlatformViewModel must not use the demo session role label.");
}

if (!emptyModelSource.includes('"session.emptyRoleLabel"')) {
  errors.push("createEmptyPlatformViewModel must use the non-demo empty session role label.");
}

if (/from\s+["']\.\/data["']/.test(screensSource)) {
  errors.push("screens.tsx must render passed view-model data instead of importing preview/mock data directly.");
}

const demoLoginGuards = [
  {
    label: "demo login action",
    pattern: /\{demoMode\s*\?\s*<ActionButton[^>]+onPress=\{handleDemoLogin\}/
  },
  {
    label: "demo account notice",
    pattern: /\{demoMode\s*\?\s*\(\s*<View[^>]+style=\{styles\.inlineNotice\}>[\s\S]*?login\.demo\.badge/
  },
  {
    label: "demo company-code placeholder",
    pattern: /placeholder=\{demoMode\s*\?\s*demoAccount\.companyCode\s*:\s*""\}/
  },
  {
    label: "demo user-id placeholder",
    pattern: /placeholder=\{demoMode\s*\?\s*demoAccount\.userId\s*:\s*""\}/
  },
  {
    label: "demo password placeholder",
    pattern: /placeholder=\{demoMode\s*\?\s*demoAccount\.password\s*:\s*""\}/
  }
];
for (const guard of demoLoginGuards) {
  if (!guard.pattern.test(screensSource)) {
    errors.push(`Login ${guard.label} must remain gated behind demoMode.`);
  }
}

const demoOnlyPanels = [
  "AttendancePhonePanel",
  "TravelWorklogPanel",
  "AdminAccountPanel",
  "ArchiveLibraryPanel",
  "AiWorkspacePanel"
];
for (const panel of demoOnlyPanels) {
  const gatedPattern = new RegExp(`demoMode\\s*&&\\s*active\\.id\\s*===\\s*["'][a-z]+["']\\s*\\?\\s*<${panel}\\b`);
  if (!gatedPattern.test(screensSource)) {
    errors.push(`${panel} must remain gated behind demoMode before rendering static demo panels.`);
  }
}

if (errors.length > 0) {
  console.error("runtime data mode verification failed:");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log("runtime data mode verified: dummy data stays behind explicit demo mode");
