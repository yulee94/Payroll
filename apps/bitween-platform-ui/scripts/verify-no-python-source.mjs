import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appRoot = join(__dirname, "..");
const repoRoot = join(appRoot, "..", "..");
const errors = [];
const ignoredDirs = new Set([".git", "buck-out", "node_modules"]);
const ignoredPathParts = new Set(["node_modules"]);
const stalePythonInventoryPhrase = "Existing Python remains compatibility/characterization inventory";
const activeDocCommandPatterns = [
  {
    pattern: /\b(?:python(?:3(?:\.\d+)?)?|py)\s+-(?:m|c)\b/i,
    label: "removed Python module/eval command",
  },
  {
    pattern: /\bpip(?:3(?:\.\d+)?)?\s+install\b/i,
    label: "removed Python package install command",
  },
  {
    pattern: /\b(?:pytest|unittest)\b/i,
    label: "removed Python test-runner command",
  },
  {
    pattern: /\b[\w./-]+\.py\b/i,
    label: "removed Python source/test path",
  },
  {
    pattern: /\brequirements[^/\s`'"]*\.txt\b/i,
    label: "removed Python dependency manifest reference",
  },
  {
    pattern: /buck2 build\s+['"]?\/\/\.\.\.\[(?:check|clippy)\]/i,
    label: "unsupported recursive Buck2 check/clippy target",
  },
  {
    pattern: /buck2 build \/\/\.\.\.\s+--filter\s+lint/i,
    label: "retired Buck2 lint filter example",
  },
];
const staleDocNarrativePatterns = [
  /Python may still/i,
  /Python remains (?:responsible|only as|the|a|an|compatibility|characterization|parser|resolver|adapter|bridge)/i,
  /while Python remains/i,
  /Python remains responsible/i,
  /Python remains only as/i,
  /Existing Python behavior/i,
  /Decommission Python compatibility modules/i,
  /Local compatibility runners and Python adapters/i,
  /A backend slice can replace Python/i,
  /current compatibility behavior/i,
  /Python compatibility modules/i,
  /Python responsible/i,
  /keeping Python responsible/i,
  /still Python-backed/i,
  /retained Python fallback/i,
  /Python still owns/i,
  /Python still (?:parses|supplies|imports|resolves|performs)/i,
  /Python contract tests?/i,
  /Python characterization/i,
  /Python-visible/i,
  /Python fallback/i,
  /current Python adapter/i,
  /Python-owned/i,
  /Python as (?:adapter|resolver|executor)/i,
  /compatibility code remains responsible/i,
  /adapter may still call Python/i,
  /Python persistence gap/i,
  /Cargo\/npm retained/i,
  /removed pre-G028 compatibility module/i,
  /removed pre-G028 compatibility test/i,
];
const pythonManifestNames = new Set([
  ".mypy.ini",
  ".pylintrc",
  ".python-version",
  ".ruff.toml",
  "MANIFEST.in",
  "Pipfile",
  "Pipfile.lock",
  "constraints.txt",
  "hatch.toml",
  "mypy.ini",
  "pdm.lock",
  "pdm.toml",
  "poetry.lock",
  "poetry.toml",
  "pyproject.toml",
  "pyrightconfig.json",
  "pytest.ini",
  "ruff.toml",
  "setup.cfg",
  "setup.py",
  "tox.ini",
  "uv.lock",
  "uv.toml",
]);

function walk(dir) {
  for (const entry of readdirSync(dir)) {
    if (ignoredDirs.has(entry)) continue;
    const fullPath = join(dir, entry);
    const rel = relative(repoRoot, fullPath).replaceAll("\\\\", "/");
    if ([...ignoredPathParts].some((part) => rel.split("/").includes(part))) continue;
    const stats = statSync(fullPath);
    if (stats.isDirectory()) {
      if (entry === "__pycache__") {
        errors.push(`Python bytecode cache directory remains: ${rel}`);
        continue;
      }
      walk(fullPath);
      continue;
    }
    if (entry.endsWith(".py") || entry.endsWith(".pyi")) {
      errors.push(`Python source/stub remains: ${rel}`);
    }
    if (pythonManifestNames.has(entry) || /^requirements[^/]*\.txt$/i.test(entry)) {
      errors.push(`Python dependency/tooling manifest remains: ${rel}`);
    }
  }
}

function collectMarkdownFiles(dir, results = []) {
  for (const entry of readdirSync(dir)) {
    if (ignoredDirs.has(entry)) continue;
    const fullPath = join(dir, entry);
    const rel = relative(repoRoot, fullPath).replaceAll("\\\\", "/");
    if ([...ignoredPathParts].some((part) => rel.split("/").includes(part))) continue;
    const stats = statSync(fullPath);
    if (stats.isDirectory()) {
      collectMarkdownFiles(fullPath, results);
    } else if (entry.endsWith(".md")) {
      results.push(fullPath);
    }
  }
  return results;
}

function requireText(source, text, message) {
  if (!source.includes(text)) errors.push(message);
}

function rejectPattern(source, pattern, message) {
  if (pattern.test(source)) errors.push(message);
}

walk(repoRoot);

const workflowSource = readFileSync(join(repoRoot, ".github", "workflows", "tests.yml"), "utf8");
const workflowSources = readdirSync(join(repoRoot, ".github", "workflows"))
  .filter((name) => name.endsWith(".yml") || name.endsWith(".yaml"))
  .map((name) => [name, readFileSync(join(repoRoot, ".github", "workflows", name), "utf8")]);
const packageJson = JSON.parse(readFileSync(join(appRoot, "package.json"), "utf8"));
const runtimeVerifierSource = readFileSync(join(__dirname, "verify-runtime-data-mode.mjs"), "utf8");
const agentsSource = readFileSync(join(repoRoot, "AGENTS.md"), "utf8");
const readmeSource = readFileSync(join(repoRoot, "README.md"), "utf8");
const aiReadmeSource = readFileSync(join(repoRoot, "AI_README.md"), "utf8");
const decommissionSource = readFileSync(join(repoRoot, "docs", "PYTHON_DECOMMISSION_INVENTORY.md"), "utf8");
const fastPathSource = readFileSync(join(repoRoot, "docs", "PRODUCTION_DELIVERY_FAST_PATH.md"), "utf8");
const handoffSource = readFileSync(join(repoRoot, "HANDOFF.md"), "utf8");
const activeMarkdownSources = [
  "AGENTS.md",
  "README.md",
  "AI_README.md",
  "DESIGN.md",
  "HANDOFF.md",
  "apps/bitween-platform-ui/README.md",
  ...collectMarkdownFiles(join(appRoot, "docs")).map((path) => relative(repoRoot, path).replaceAll("\\\\", "/")),
];
const docMarkdownSources = collectMarkdownFiles(join(repoRoot, "docs")).map((path) => [
  relative(repoRoot, path).replaceAll("\\\\", "/"),
  readFileSync(path, "utf8"),
]);
for (const markdownPath of activeMarkdownSources) {
  if (markdownPath === "docs/PYTHON_DECOMMISSION_INVENTORY.md") continue;
  docMarkdownSources.push([markdownPath, readFileSync(join(repoRoot, markdownPath), "utf8")]);
}

if (packageJson.scripts?.["verify:no-python-source"] !== "node scripts/verify-no-python-source.mjs") {
  errors.push("package.json must expose verify:no-python-source.");
}
requireText(workflowSource, "npm run verify:no-python-source", "CI must run verify:no-python-source before product gates.");
requireText(runtimeVerifierSource, "verify-no-python-source.mjs", "verify-runtime-data-mode.mjs must guard the no-Python source verifier.");
requireText(decommissionSource, "Status: decommissioned", "Python decommission inventory must record the decommissioned state.");
requireText(decommissionSource, "Repo-owned Python source count: 0", "Python decommission inventory must record zero repo-owned Python source files.");
requireText(decommissionSource, "verify:no-python-source", "Python decommission inventory must name the enforcement gate.");
for (const [workflowName, source] of workflowSources) {
  rejectPattern(source, /setup-python|python-version|\bpython(?:3(?:\.\d+)?)?\s+-m|\bpy\s+-m|\bpip(?:3(?:\.\d+)?)?\s+install|\bpytest\b|\bunittest\b/i, `${workflowName} must not install or run Python after G028 decommission.`);
}
rejectPattern(agentsSource, /python -m|Compatibility characterization tests|Existing Python modules/i, "AGENTS.md must not instruct agents to use Python compatibility tests or modules.");
rejectPattern(readmeSource, /python -m|pip install|services\/[\w/-]+\.py|tests\/[\w/-]+\.py|Python 3/i, "README.md must not instruct users to run removed Python compatibility paths.");
rejectPattern(aiReadmeSource, /services\/[\w/-]+\.py|python -m|python -c|compatibility callers use synchronous/i, "AI_README.md must not reference removed Python AI compatibility paths.");
rejectPattern(fastPathSource, new RegExp(stalePythonInventoryPhrase, "i"), "Production fast-path doc must not describe Python as active compatibility inventory after G028.");
rejectPattern(handoffSource, /Existing Python migration\/decommission is tracked as future work|Complete Python decommission after production SaaS workflow surfaces|Replace any remaining compatibility Python tests\/tools/i, "HANDOFF.md must not describe Python decommission as future work after G028.");
for (const [docPath, source] of docMarkdownSources) {
  for (const { pattern, label } of activeDocCommandPatterns) {
    rejectPattern(source, pattern, `${docPath} must not contain active ${label} after G028.`);
  }
  if (docPath !== "docs/PYTHON_DECOMMISSION_INVENTORY.md") {
    for (const pattern of staleDocNarrativePatterns) {
      rejectPattern(source, pattern, `${docPath} must not describe repo-owned Python as an active compatibility path after G028.`);
    }
  }
}

if (errors.length > 0) {
  console.error("No-Python source verification failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("No-Python source verification passed: repo-owned Python sources are decommissioned.");
