import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appPath = join(__dirname, "..", "App.tsx");
const screensPath = join(__dirname, "..", "src", "screens.tsx");
const viewModelPath = join(__dirname, "..", "src", "viewModel.ts");
const appSource = readFileSync(appPath, "utf8");
const screensSource = readFileSync(screensPath, "utf8");
const viewModelSource = readFileSync(viewModelPath, "utf8");
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
