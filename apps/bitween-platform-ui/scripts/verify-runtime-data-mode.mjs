import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appPath = join(__dirname, "..", "App.tsx");
const packagePath = join(__dirname, "..", "package.json");
const previewAppPath = join(__dirname, "..", "preview", "app.js");
const previewServerPath = join(__dirname, "..", "preview", "server.js");
const previewStylesPath = join(__dirname, "..", "preview", "styles.css");
const componentsPath = join(__dirname, "..", "src", "components.tsx");
const screensPath = join(__dirname, "..", "src", "screens.tsx");
const typesPath = join(__dirname, "..", "src", "types.ts");
const dataPath = join(__dirname, "..", "src", "data.ts");
const catalogPath = join(__dirname, "..", "src", "i18n", "catalog.json");

const appSource = readFileSync(appPath, "utf8");
const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
const previewAppSource = readFileSync(previewAppPath, "utf8");
const previewServerSource = readFileSync(previewServerPath, "utf8");
const previewStylesSource = readFileSync(previewStylesPath, "utf8");
const componentsSource = readFileSync(componentsPath, "utf8");
const screensSource = readFileSync(screensPath, "utf8");
const typesSource = readFileSync(typesPath, "utf8");
const dataSource = readFileSync(dataPath, "utf8");
const catalogSource = readFileSync(catalogPath, "utf8");
const errors = [];

const requireText = (source, text, message) => {
  if (!source.includes(text)) errors.push(message);
};
const rejectText = (source, text, message) => {
  if (source.includes(text)) errors.push(message);
};
const requirePattern = (source, pattern, message) => {
  if (!pattern.test(source)) errors.push(message);
};

if (packageJson.scripts?.preview !== "node preview/server.js 4174") {
  errors.push("package.json preview script must serve the local review URL on port 4174.");
}
if (packageJson.scripts?.["preview:4174"] !== "node preview/server.js 4174") {
  errors.push("package.json preview:4174 script must remain pinned to port 4174.");
}
if (packageJson.scripts?.["check:strict-config"] !== "node scripts/check-strict-config.js") {
  errors.push("package.json must keep the strict TypeScript guard script.");
}

requireText(previewServerSource, "no-store, no-cache, must-revalidate, max-age=0", "preview/server.js must disable browser caching for local UI review.");
requireText(previewServerSource, "styles.css?v=", "preview/server.js must version styles.css responses.");
requireText(previewServerSource, "app.js?v=", "preview/server.js must version app.js responses.");

requireText(typesSource, '"maintenanceRental"', "PlatformId must include maintenanceRental.");
requireText(dataSource, '{ id: "maintenanceRental", accent:', "Navigation definitions must include the maintenance/rental tab.");
requireText(dataSource, 'maintenanceRental: {', "Module definitions must include maintenance/rental dashboard data.");
requireText(dataSource, 'getPreviewAccounts', "Preview accounts must remain the role-based login source.");
requireText(appSource, 'useState<PreviewAccountId>("fieldWorker")', "App.tsx must keep role-based preview account selection.");
requireText(appSource, 'onLogin={login}', "App.tsx must pass account login handling to LoginScreen.");
requireText(appSource, 'modeLabel={session.modeLabel}', "AppShell must keep role/developer mode labeling.");
requireText(componentsSource, 'height: 46', "React Native sidebar nav buttons must keep a fixed 46px height.");
requireText(componentsSource, 'numberOfLines={1}', "React Native sidebar nav labels must stay one line.");

requireText(screensSource, 'maintenanceRentalIntegration', "screens.tsx must expose the maintenance/rental external bridge.");
requireText(screensSource, 'https://github.com/yulee94/maintenance_system', "screens.tsx bridge must point to the maintenance_system source until a deployment URL is configured.");
requireText(previewAppSource, 'maintenanceRentalIntegration', "preview/app.js must mirror the maintenance/rental external bridge.");
requireText(previewAppSource, 'data-external-url', "preview/app.js must open external maintenance/rental URLs through explicit external-url buttons.");
requireText(previewAppSource, 'devicePreviewPanel', "preview/app.js must expose the web/mobile side-by-side preview panel.");
requireText(previewAppSource, 'web-preview-frame', "preview/app.js must render the web-only preview frame.");
requireText(previewAppSource, 'mobile-preview-frame', "preview/app.js must render the phone-only preview frame.");
requireText(screensSource, 'DevicePreviewPanel', "screens.tsx must expose the web/mobile side-by-side preview panel.");
requireText(catalogSource, '"navigation.maintenanceRental.label"', "i18n catalog must include maintenance/rental navigation copy.");
requireText(catalogSource, '"preview.toast.externalOpened"', "i18n catalog must include external-link toast copy.");
requireText(catalogSource, '"screens.launcher.devicePreview.title"', "i18n catalog must include web/mobile side-by-side preview copy.");

rejectText(screensSource, "cossMonthlyFileDefinitions", "screens.tsx must not reintroduce the removed 1~5월 payroll intake checklist.");
rejectText(previewAppSource, "cossMonthlyFileIds", "preview/app.js must not reintroduce the removed 1~5월 payroll intake checklist.");
rejectText(catalogSource, "급여자료 입력 현황", "catalog must not expose the removed payroll input-status sidebar copy.");

requirePattern(previewStylesSource, /\.sidebar\s*\{[\s\S]*?height:\s*100vh;[\s\S]*?overflow:\s*hidden;[\s\S]*?\}/, "preview sidebar must keep fixed viewport height and hide outer overflow.");
requirePattern(previewStylesSource, /\.nav-button\s*\{[\s\S]*?height:\s*46px;[\s\S]*?max-height:\s*46px;[\s\S]*?min-height:\s*46px;[\s\S]*?width:\s*100%;[\s\S]*?\}/, "preview sidebar nav buttons must use a fixed 46px row height.");
requirePattern(previewStylesSource, /\.nav-button strong\s*\{[\s\S]*?text-overflow:\s*ellipsis;[\s\S]*?white-space:\s*nowrap;[\s\S]*?\}/, "preview sidebar nav labels must not wrap and resize rows.");
requirePattern(previewStylesSource, /\.nav\s*\{[\s\S]*?align-content:\s*start;[\s\S]*?grid-auto-rows:\s*46px;[\s\S]*?overflow-y:\s*auto;[\s\S]*?\}/, "preview sidebar nav must not stretch gaps between tabs.");
requireText(previewStylesSource, ".device-preview-grid", "preview styles must include the web/mobile side-by-side preview layout.");

if (errors.length > 0) {
  console.error("runtime data mode verification failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("Runtime data mode check passed.");
