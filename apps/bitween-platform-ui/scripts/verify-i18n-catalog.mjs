import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const catalogPath = join(__dirname, "..", "src", "i18n", "catalog.json");
const catalog = JSON.parse(readFileSync(catalogPath, "utf8"));
const expectedLocales = ["ko-KR", "en-US", "zh-Hans-CN", "ja-JP"];
const errors = [];

const supportedLocales = Array.isArray(catalog.supportedLocales) ? catalog.supportedLocales : [];
if (JSON.stringify(supportedLocales) !== JSON.stringify(expectedLocales)) {
  errors.push(`supportedLocales must be exactly ${expectedLocales.join(", ")}`);
}

const requireLocalizedValues = (owner, values) => {
  if (!values || typeof values !== "object" || Array.isArray(values)) {
    errors.push(`${owner} must provide a values object`);
    return;
  }
  for (const locale of expectedLocales) {
    if (typeof values[locale] !== "string" || values[locale].trim().length === 0) {
      errors.push(`${owner} is missing a non-empty ${locale} value`);
    }
  }
  for (const locale of Object.keys(values)) {
    if (!expectedLocales.includes(locale)) {
      errors.push(`${owner} has unsupported locale ${locale}`);
    }
  }
};

const keys = new Set();
for (const [index, row] of (catalog.messages ?? []).entries()) {
  if (!row || typeof row.key !== "string" || row.key.trim().length === 0) {
    errors.push(`messages[${index}] must have a non-empty key`);
    continue;
  }
  if (keys.has(row.key)) {
    errors.push(`duplicate message key ${row.key}`);
  }
  keys.add(row.key);
  requireLocalizedValues(`message ${row.key}`, row.values);
}

const languageRows = new Map();
for (const [index, row] of (catalog.languageDisplayNames ?? []).entries()) {
  if (!row || typeof row.locale !== "string") {
    errors.push(`languageDisplayNames[${index}] must have a locale`);
    continue;
  }
  if (!expectedLocales.includes(row.locale)) {
    errors.push(`languageDisplayNames[${index}] has unsupported locale ${row.locale}`);
  }
  if (languageRows.has(row.locale)) {
    errors.push(`duplicate languageDisplayNames row ${row.locale}`);
  }
  languageRows.set(row.locale, row);
  requireLocalizedValues(`languageDisplayNames ${row.locale}`, row.values);
}
for (const locale of expectedLocales) {
  if (!languageRows.has(locale)) {
    errors.push(`languageDisplayNames is missing ${locale}`);
  }
}

const sourceFiles = [
  join(__dirname, "..", "App.tsx"),
  join(__dirname, "..", "src", "components.tsx"),
  join(__dirname, "..", "src", "data.ts"),
  join(__dirname, "..", "preview", "app.js"),
  join(__dirname, "..", "preview", "index.html"),
  join(__dirname, "..", "src", "screens.tsx"),
  join(__dirname, "..", "src", "theme.ts"),
  join(__dirname, "..", "src", "viewModel.ts")
];
const localizedGlyphPattern = /[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]/;
for (const sourceFile of sourceFiles) {
  const lines = readFileSync(sourceFile, "utf8").split(/\r?\n/);
  for (const [index, line] of lines.entries()) {
    if (localizedGlyphPattern.test(line)) {
      errors.push(`${sourceFile}:${index + 1} contains localized UI copy outside catalog.json`);
    }
  }
}

if (errors.length > 0) {
  console.error("i18n catalog verification failed:");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log(`i18n catalog verified: ${keys.size} messages across ${expectedLocales.length} locales with no localized copy outside the catalog`);
