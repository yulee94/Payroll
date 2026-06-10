#!/usr/bin/env node
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..", "..");
const retired = new Set(["build", "check", "test", "clippy", "run", "bench", "fmt", "doc", "nextest"]);
const allowed = new Set(["metadata", "install", "vendor"]);

function readPayload() {
  const raw = fs.readFileSync(0, "utf8").trim();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function commandFrom(payload) {
  const input = payload && typeof payload.tool_input === "object" && payload.tool_input !== null
    ? payload.tool_input
    : {};
  return String(input.command || input.cmd || payload.command || payload.cmd || "").trim();
}

function tokenizeShell(command) {
  const tokens = [];
  let current = "";
  let quote = "";
  let escaped = false;
  for (const ch of command) {
    if (escaped) {
      current += ch;
      escaped = false;
      continue;
    }
    if (ch === "\\") {
      escaped = true;
      continue;
    }
    if (quote) {
      if (ch === quote) quote = "";
      else current += ch;
      continue;
    }
    if (ch === "'" || ch === '"') {
      quote = ch;
      continue;
    }
    if (/\s/.test(ch)) {
      if (current) {
        tokens.push(current);
        current = "";
      }
      continue;
    }
    current += ch;
  }
  if (current) tokens.push(current);
  return tokens;
}

function splitCommands(tokens) {
  const commands = [];
  let segment = [];
  for (const token of tokens) {
    if (["&&", "||", ";", "|"].includes(token)) {
      if (segment.length) commands.push(segment);
      segment = [];
    } else {
      segment.push(token);
    }
  }
  if (segment.length) commands.push(segment);
  return commands;
}

function unwrapRunner(segment) {
  let i = 0;
  while (i < segment.length && /^[A-Z_][A-Z0-9_]*=.*/.test(segment[i])) i += 1;
  if (segment[i] === "env") {
    i += 1;
    while (i < segment.length && /^[A-Z_][A-Z0-9_]*=.*/.test(segment[i])) i += 1;
  }
  return segment.slice(i);
}

function cargoInvocation(command) {
  for (const rawSegment of splitCommands(tokenizeShell(command))) {
    const segment = unwrapRunner(rawSegment);
    if (!segment.length) continue;
    const exe = segment[0].split("/").pop();
    if (exe !== "cargo") continue;
    const subcommand = segment.find((token, index) => index > 0 && !token.startsWith("-"));
    if (!subcommand) return { blocked: true, subcommand: "<missing>" };
    if (allowed.has(subcommand)) return null;
    if (retired.has(subcommand)) return { blocked: true, subcommand };
    return { blocked: true, subcommand };
  }
  return null;
}

const payload = readPayload();
const input = payload && typeof payload.tool_input === "object" && payload.tool_input !== null
  ? payload.tool_input
  : {};
const cwd = path.resolve(String(input.cwd || input.workdir || payload.cwd || process.cwd()));
const command = commandFrom(payload);

if (!(cwd === root || cwd.startsWith(`${root}${path.sep}`)) || !command) process.exit(0);

const blocked = cargoInvocation(command);
if (!blocked) process.exit(0);

const message = [
  `🚫 BLOCKED: 'cargo ${blocked.subcommand}' is retired for this repository.`,
  "Buck2 is the canonical build & verify tool (founder 2026-05-29: stop using cargo; canonical monorepo pattern).",
  "Use instead:",
  "    buck2 build //...                 # build",
  "    buck2 test  //...                 # test",
  "    buck2 build '<target>[check]'     # type-check changed Rust targets",
  "    buck2 build '<target>[clippy.txt]' # clippy changed Rust targets",
  "Still allowed: cargo metadata / cargo install / cargo vendor for Buck/Reindeer inputs."
].join("\n");

console.log(JSON.stringify({
  decision: "block",
  reason: message,
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: message
  },
  systemMessage: message
}));
