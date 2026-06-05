import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appPath = join(__dirname, "..", "App.tsx");
const appSource = readFileSync(appPath, "utf8");
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

if (errors.length > 0) {
  console.error("runtime data mode verification failed:");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log("runtime data mode verified: App.tsx keeps dummy data behind explicit demo mode");
