import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join, relative, resolve, sep } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appRoot = resolve(__dirname, "..");
const root = resolve(__dirname, "..", "..", "..");
const packagePath = join(appRoot, "package.json");
const workflowPath = join(root, ".github", "workflows", "tests.yml");
const hookPath = join(root, ".codex", "hooks", "buck2-cargo-guard.js");
const runtimeVerifierPath = join(__dirname, "verify-runtime-data-mode.mjs");

const retiredCargoSubcommands = ["build", "check", "test", "clippy", "run", "bench", "fmt", "doc", "nextest"];
const allowedCargoSubcommands = ["metadata", "install", "vendor"];
const errors = [];

const readText = (path) => readFileSync(path, "utf8");
const packageJson = JSON.parse(readText(packagePath));
const workflowSource = readText(workflowPath);
const hookSource = readText(hookPath);
const runtimeVerifierSource = readText(runtimeVerifierPath);

function requireText(source, text, message) {
  if (!source.includes(text)) errors.push(message);
}

function requirePattern(source, pattern, message) {
  if (!pattern.test(source)) errors.push(message);
}

function rejectPattern(source, pattern, message) {
  if (pattern.test(source)) errors.push(message);
}

function parseHookOutput(output) {
  const trimmed = String(output || "").trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed);
  } catch (error) {
    errors.push(`Buck2 cargo guard emitted non-JSON output: ${error.message}`);
    return null;
  }
}

function runHook(command, cwd = root) {
  return spawnSync("node", [hookPath], {
    cwd: root,
    input: JSON.stringify({
      tool_name: "functions.exec_command",
      tool_input: { command, cwd },
    }),
    encoding: "utf8",
  });
}

function assertHookBlocks(command, expectedSubcommand) {
  const result = runHook(command);
  if (result.status !== 0) {
    errors.push(`Buck2 cargo guard exited non-zero for ${command}: ${result.stderr || result.stdout}`);
    return;
  }
  const payload = parseHookOutput(result.stdout);
  if (!payload) {
    errors.push(`Buck2 cargo guard did not block retired command: ${command}`);
    return;
  }
  if (payload.decision !== "block") errors.push(`Buck2 cargo guard did not return decision:block for ${command}.`);
  if (payload.hookSpecificOutput?.hookEventName !== "PreToolUse") {
    errors.push(`Buck2 cargo guard did not mark ${command} as a PreToolUse decision.`);
  }
  if (payload.hookSpecificOutput?.permissionDecision !== "deny") {
    errors.push(`Buck2 cargo guard did not deny ${command}.`);
  }
  if (!String(payload.reason || "").includes(`cargo ${expectedSubcommand}`)) {
    errors.push(`Buck2 cargo guard reason for ${command} did not name cargo ${expectedSubcommand}.`);
  }
  if (!String(payload.reason || "").includes("buck2 test")) {
    errors.push(`Buck2 cargo guard reason for ${command} did not provide Buck2 test guidance.`);
  }
}

function assertHookAllows(command, cwd = root) {
  const result = runHook(command, cwd);
  if (result.status !== 0) {
    errors.push(`Buck2 cargo guard exited non-zero for allowed command ${command}: ${result.stderr || result.stdout}`);
    return;
  }
  if (String(result.stdout || "").trim()) {
    errors.push(`Buck2 cargo guard unexpectedly blocked allowed command: ${command}`);
  }
}

function validateHookBehavior() {
  assertHookBlocks("cargo " + "test //crates/payroll-api:payroll_api_test", "test");
  assertHookBlocks("RUSTFLAGS=-Dwarnings cargo clippy --all-targets", "clippy");
  assertHookBlocks("env RUST_BACKTRACE=1 cargo build", "build");
  assertHookBlocks("buck2 test //... && cargo run --bin payroll_api", "run");
  assertHookAllows("cargo metadata --locked");
  assertHookAllows("cargo install --locked --git https://github.com/facebookincubator/reindeer reindeer");
  assertHookAllows("cargo vendor third-party/rust/vendor");
  assertHookAllows("buck2 test //...");
  assertHookAllows("cargo test", "/tmp");
}

function validateStaticWiring() {
  if (packageJson.scripts?.["verify:buck2-only"] !== "node scripts/verify-buck2-only.mjs") {
    errors.push("package.json must expose verify:buck2-only for local and CI Buck2-only enforcement.");
  }
  requireText(workflowSource, "npm run verify:buck2-only", ".github/workflows/tests.yml must run verify:buck2-only in CI before product checks.");
  requireText(runtimeVerifierSource, "verify-buck2-only.mjs", "verify-runtime-data-mode.mjs must guard that Buck2-only verification remains wired.");
  requireText(runtimeVerifierSource, "buck2-cargo-guard.js", "verify-runtime-data-mode.mjs must guard that the Codex PreToolUse cargo blocker remains present.");
  requireText(hookSource, "decision: \"block\"", "Codex cargo guard must emit a blocking decision.");
  requireText(hookSource, "hookEventName: \"PreToolUse\"", "Codex cargo guard must be a PreToolUse permission gate.");
  requireText(hookSource, "permissionDecision: \"deny\"", "Codex cargo guard must deny retired cargo commands.");
  requireText(hookSource, "buck2 build //...", "Codex cargo guard must point agents to Buck2 build/check/test replacements.");
  requireText(hookSource, "'<target>[check]'", "Codex cargo guard must point type-checking to supported target-specific Buck2 check targets.");
  requireText(hookSource, "'<target>[clippy.txt]'", "Codex cargo guard must point linting to supported target-specific Buck2 clippy targets.");
  rejectPattern(hookSource, /\/\/\.\.\.\[(check|clippy)\]/, "Codex cargo guard must not recommend unsupported recursive Buck2 check/clippy patterns.");
  for (const subcommand of retiredCargoSubcommands) {
    requirePattern(hookSource, new RegExp(`\\b${subcommand}\\b`), `Codex cargo guard must list retired cargo ${subcommand}.`);
  }
  for (const subcommand of allowedCargoSubcommands) {
    requirePattern(hookSource, new RegExp(`\\b${subcommand}\\b`), `Codex cargo guard must list allowed cargo ${subcommand}.`);
  }
}

const skipDirectories = new Set([
  ".git",
  ".buckd",
  ".cargo",
  ".omx",
  "buck-out",
  "node_modules",
  "target",
]);
const skippedRelativePrefixes = [
  `third-party${sep}rust${sep}vendor${sep}`,
  `apps${sep}bitween-platform-ui${sep}node_modules${sep}`,
  `frontend${sep}node_modules${sep}`,
];
const skippedRelativeFiles = new Set([
  `apps${sep}bitween-platform-ui${sep}scripts${sep}verify-buck2-only.mjs`,
]);
const scannedExtensions = new Set([
  "",
  ".bazel",
  ".buckconfig",
  ".bzl",
  ".cjs",
  ".env",
  ".json",
  ".js",
  ".jsx",
  ".md",
  ".mjs",
  ".rs",
  ".sh",
  ".toml",
  ".ts",
  ".tsx",
  ".txt",
  ".yaml",
  ".yml",
]);

function shouldSkipPath(path) {
  const rel = relative(root, path);
  if (!rel || rel.startsWith("..")) return false;
  if (skippedRelativeFiles.has(rel)) return true;
  return skippedRelativePrefixes.some((prefix) => rel.startsWith(prefix));
}

function listScannableFiles(startPath, files = []) {
  if (shouldSkipPath(startPath)) return files;
  const stat = statSync(startPath);
  if (stat.isDirectory()) {
    const basename = startPath.split(sep).pop();
    if (skipDirectories.has(basename)) return files;
    for (const entry of readdirSync(startPath)) listScannableFiles(join(startPath, entry), files);
    return files;
  }
  if (!stat.isFile()) return files;
  if (stat.size > 2_000_000) return files;
  if (!scannedExtensions.has(extname(startPath))) return files;
  files.push(startPath);
  return files;
}

const retiredCommandPattern = /\bcargo\s+(?:(?:\+[^\s]+|--?[A-Za-z0-9-]+(?:=[^\s]+)?)\s+)*(build|check|test|clippy|run|bench|fmt|doc|nextest)\b/g;
const retiredSlashListPattern = /\bcargo\s+(build|check|test|clippy|run|bench|fmt|doc|nextest)(?:\/(?:build|check|test|clippy|run|bench|fmt|doc|nextest))+\b/gi;
const directiveContextPattern = /\b(retired|do not use|blocked|canonical|buck2|allowed|reindeer|migration|transition|decommission|forbid|instead|only)\b/i;
const unsupportedRecursiveBuck2Pattern = /\bbuck2\s+build\s+(?:(?:'|")?\/\/\.\.\.\[(?:check|clippy)(?:\.txt)?\](?:'|")?|\/\/\.\.\.\s+--filter\s+lint)\b/gi;
const unsupportedBuck2DirectiveContextPattern = /\b(unsupported|not accepted|must not|do not use|blocked|reject|rejects|guard|guards|not recommend|retired|forbid|instead|only)\b/i;

function isDocumentationFile(path) {
  return extname(path).toLowerCase() === ".md";
}

function lineHasRetiredCargo(line) {
  retiredCommandPattern.lastIndex = 0;
  retiredSlashListPattern.lastIndex = 0;
  return retiredCommandPattern.test(line) || retiredSlashListPattern.test(line);
}

function scanRetiredCargoUsage() {
  for (const path of listScannableFiles(root)) {
    const rel = relative(root, path);
    const buffer = readFileSync(path);
    if (buffer.includes(0)) continue;
    const source = buffer.toString("utf8");
    const lines = source.split(/\r?\n/);
    lines.forEach((line, index) => {
      if (!lineHasRetiredCargo(line)) return;
      if (isDocumentationFile(path)) {
        const context = [lines[index - 1] || "", line, lines[index + 1] || ""].join(" ");
        if (directiveContextPattern.test(context)) return;
      }
      errors.push(`${rel}:${index + 1} uses a retired cargo command; use Buck2 or allowed cargo metadata/install/vendor only.`);
    });
  }
}

function scanUnsupportedRecursiveBuck2Usage() {
  for (const path of listScannableFiles(root)) {
    const rel = relative(root, path);
    const buffer = readFileSync(path);
    if (buffer.includes(0)) continue;
    const source = buffer.toString("utf8");
    const lines = source.split(/\r?\n/);
    lines.forEach((line, index) => {
      unsupportedRecursiveBuck2Pattern.lastIndex = 0;
      if (!unsupportedRecursiveBuck2Pattern.test(line)) return;
      const context = [lines[index - 1] || "", line, lines[index + 1] || ""].join(" ");
      if (unsupportedBuck2DirectiveContextPattern.test(context)) return;
      errors.push(`${rel}:${index + 1} uses an unsupported recursive Buck2 provider pattern; use explicit target-specific [check]/[clippy.txt] targets.`);
    });
  }
}

validateStaticWiring();
validateHookBehavior();
scanRetiredCargoUsage();
scanUnsupportedRecursiveBuck2Usage();

if (errors.length > 0) {
  console.error("Buck2-only verification failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("Buck2-only verification passed.");
