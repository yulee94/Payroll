const fs = require("node:fs");
const path = require("node:path");

const appRoot = path.resolve(__dirname, "..");
const packageJsonPath = path.join(appRoot, "package.json");
const tsconfigPath = path.join(appRoot, "tsconfig.json");

const requiredCompilerOptions = {
  noImplicitOverride: true,
  noImplicitReturns: true,
  noUncheckedIndexedAccess: true,
  strict: true
};

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function fail(message) {
  console.error(message);
  process.exitCode = 1;
}

const tsconfig = readJson(tsconfigPath);
const packageJson = readJson(packageJsonPath);
const compilerOptions = tsconfig.compilerOptions ?? {};

for (const [option, expected] of Object.entries(requiredCompilerOptions)) {
  if (compilerOptions[option] !== expected) {
    fail(`Expected compilerOptions.${option} to be ${String(expected)}.`);
  }
}

if (packageJson.scripts?.typecheck !== "tsc --noEmit") {
  fail('Expected package.json scripts.typecheck to be "tsc --noEmit".');
}

if (process.exitCode) {
  process.exit();
}

console.log("Bitween frontend strict TypeScript guard passed.");
