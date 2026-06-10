import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const appRoot = join(__dirname, "..");
const repoRoot = join(appRoot, "..", "..");
const errors = [];

const paths = {
  contract: join(repoRoot, "docs", "OFFICE_PRODUCT_CONTRACT.md"),
  handoff: join(repoRoot, "HANDOFF.md"),
  packageJson: join(appRoot, "package.json"),
  workflow: join(repoRoot, ".github", "workflows", "tests.yml"),
  runtimeVerifier: join(__dirname, "verify-runtime-data-mode.mjs"),
  desktopReadme: join(repoRoot, "apps", "bitween-desktop-tauri", "README.md"),
};

function readRequired(path, label) {
  if (!existsSync(path)) {
    errors.push(`${label} is missing at ${path}`);
    return "";
  }
  return readFileSync(path, "utf8");
}

function requireText(source, text, message) {
  if (!source.includes(text)) errors.push(message);
}

function requirePattern(source, pattern, message) {
  if (!pattern.test(source)) errors.push(message);
}

function rejectPattern(source, pattern, message) {
  if (pattern.test(source)) errors.push(message);
}

const contractSource = readRequired(paths.contract, "Office product contract");
const handoffSource = readRequired(paths.handoff, "HANDOFF.md");
const packageSource = readRequired(paths.packageJson, "platform UI package.json");
const workflowSource = readRequired(paths.workflow, "CI workflow");
const runtimeVerifierSource = readRequired(paths.runtimeVerifier, "runtime verifier");
const desktopReadmeSource = readRequired(paths.desktopReadme, "desktop Tauri README");
let packageJson = {};
try {
  packageJson = packageSource ? JSON.parse(packageSource) : {};
} catch (error) {
  errors.push(`package.json is not valid JSON: ${error.message}`);
}

if (packageJson.scripts?.["verify:office-contract"] !== "node scripts/verify-office-contract.mjs") {
  errors.push("package.json must expose verify:office-contract.");
}
requireText(workflowSource, "npm run verify:office-contract", "CI must run the Office product contract verifier.");
requireText(runtimeVerifierSource, "verify-office-contract.mjs", "verify-runtime-data-mode.mjs must guard the Office contract verifier.");
requireText(desktopReadmeSource, "docs/OFFICE_PRODUCT_CONTRACT.md", "Tauri README must point desktop work at the Office product contract.");

requireText(contractSource, "# Office Product Contract", "Office contract must have a stable title.");
requireText(contractSource, "Status: future product, not exposed in navigation until live-wired", "Office contract must forbid placeholder navigation/UI exposure.");
requireText(contractSource, "Rust service crates", "Office contract must keep backend implementation in Rust service crates.");
requireText(contractSource, "React Native", "Office contract must keep the shared React Native frontend source of truth.");
requireText(contractSource, "Tauri", "Office contract must cover desktop/native packaging where applicable.");
requirePattern(contractSource, /documents[\s\S]*spreadsheets[\s\S]*slides/i, "Office contract must cover documents, spreadsheets, and slides together.");
requireText(contractSource, "real-time collaboration", "Office contract must require real-time collaboration.");
requireText(contractSource, "CRDT/operation-log", "Office contract must name the collaboration consistency boundary.");
requireText(contractSource, "PostgreSQL metadata", "Office contract must put relational metadata in PostgreSQL.");
requireText(contractSource, "RustFS blobs", "Office contract must put originals and binary blobs in RustFS.");
requireText(contractSource, "append-only audit", "Office contract must require append-only audit evidence.");
requireText(contractSource, "logical versions/deltas", "Office contract must require logical version/recovery deltas instead of binary snapshots.");
requireText(contractSource, "ABAC + RBAC + PBAC", "Office contract must require the existing authorization model.");
requireText(contractSource, "tenant/legal-entity/workplace", "Office contract must preserve tenant and workplace scope.");
requireText(contractSource, "Acme / Acme Corporation", "Office contract must preserve scrubbed fixture naming.");
requireText(contractSource, "~/Developer/oyatie/oya/office", "Office contract must cite the local Oyatie Office reference tree.");
requireText(contractSource, "registry/catalog/oya-workspace-collab-runtime-kernel.yaml", "Office contract must cite the Oyatie collab-runtime catalog reference.");
requireText(contractSource, "verification gates before visibility", "Office contract must require gates before any visible Office module is added.");
rejectPattern(contractSource, /binary snapshot duplication|binary snapshots in PostgreSQL/i, "Office contract must not allow binary snapshot duplication or PostgreSQL binary snapshots.");

requireText(handoffSource, "Office Product Contract", "HANDOFF.md must record the Office contract slice evidence.");
requireText(handoffSource, "verify:office-contract", "HANDOFF.md must record the Office verifier command.");

if (errors.length > 0) {
  console.error("Office contract verification failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("Office contract verification passed. Future Office product remains durable and hidden until live-wired.");
