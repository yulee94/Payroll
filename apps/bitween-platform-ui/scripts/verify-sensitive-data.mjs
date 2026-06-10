#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const root = spawnSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).stdout.trim();
if (!root) {
  console.error('verify-sensitive-data: not inside a git worktree');
  process.exit(1);
}

const scanHistory = process.argv.includes('--history');
const maxFindings = Number(process.env.BITWEEN_SENSITIVE_SCAN_MAX || '5000');
const reservedEmailDomains = /(?:example\.(?:com|org|net|invalid|test)|localhost)$/i;
const safeSecretValues = /^(?:REDACTED(?:_[A-Z0-9]+)*|REDACTED_TEST_SECRET|TEST_[A-Z0-9_]+|CHANGE_ME|EXAMPLE_[A-Z0-9_]+)$/;
const safePersonFixtureValues = /^(?:직원 [A-Z]|담당자|관리자|사용자|테스트 사용자|Acme(?: Corporation| Services)?|Bitween|Admin|Manager|Owner|Operator)$/i;

const skipPath = (p) =>
  /(^|\/)(\.git|node_modules|buck-out|dist|build|\.expo)(\/|$)/.test(p)
  || p.startsWith('third-party/rust/vendor/')
  || p.endsWith('package-lock.json');

const textExt = /\.(?:rs|tsx?|jsx?|mjs|cjs|json|md|yml|yaml|toml|lock|sh|ps1|py|txt|spec|css|html|sql|csv|tsv|example|iss)$/i;
const maybeText = (p) => textExt.test(p) || !path.extname(p);
const isScannerSource = (p) => p.endsWith('apps/bitween-platform-ui/scripts/verify-sensitive-data.mjs');

function luhn(candidate) {
  const digits = candidate.replace(/\D/g, '');
  if (digits.length < 13 || digits.length > 19) return false;
  let sum = 0;
  let doubleDigit = false;
  for (let i = digits.length - 1; i >= 0; i -= 1) {
    let n = Number(digits[i]);
    if (doubleDigit) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
    doubleDigit = !doubleDigit;
  }
  return sum % 10 === 0;
}

function secretLiteralFindings(line) {
  const findings = [];
  const assignment = /\b(password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|private[_-]?key)\b["']?\s*[:=]\s*["']([^"'\n]{6,})["']/gi;
  for (const match of line.matchAll(assignment)) {
    if (!safeSecretValues.test(match[2])) findings.push('secret_literal_assignment');
  }
  return findings;
}

function personNameFindings(line) {
  const findings = [];
  const keyValue = /["']((?:employee|applicant|worker|author|requester|approver|reviewer|manager|display|full|user|person)_name)["']\s*:\s*["']([^"'\n]{2,40})["']/gi;
  const assignment = /\b((?:employee|applicant|worker|author|requester|approver|reviewer|manager|display|full|user|person)_name)\s*=\s*["']([^"'\n]{2,40})["']/gi;
  for (const match of [...line.matchAll(keyValue), ...line.matchAll(assignment)]) {
    const value = match[2];
    if ((/[가-힣]{2,4}/.test(value) || /[A-Z][a-z]+\s+[A-Z][a-z]+/.test(value)) && !safePersonFixtureValues.test(value)) {
      findings.push('person_name_fixture');
    }
  }
  return findings;
}

let currentFilePath = '';
function lineFindings(line) {
  const findings = [];
  if (!isScannerSource(currentFilePath) && /\bCOSS\b|\bcoss\b|cossok\.com|coss_[a-z0-9_-]*/i.test(line)) findings.push('company_identifier');
  for (const match of line.matchAll(/[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})/gi)) {
    if (!reservedEmailDomains.test(match[1])) findings.push('email_address');
  }
  if (/\b\d{6}-[1-4]\d{6}\b/.test(line)) findings.push('korean_resident_registration_number');
  if (/(?:\+82[-\s]?10|010)[-\s]?\d{3,4}[-\s]?\d{4}\b/.test(line)) findings.push('phone_number');
  if (/(birth|dob|date_of_birth|birth_date|생년월일|출생일)\b[^\n]{0,80}\b(?:19|20)\d{2}[-./]\d{1,2}[-./]\d{1,2}/i.test(line)) findings.push('date_of_birth');
  for (const match of line.matchAll(/(?:\b\d[ -]?){13,19}\b/g)) {
    if (luhn(match[0])) findings.push('payment_card_like');
  }
  findings.push(...secretLiteralFindings(line));
  findings.push(...personNameFindings(line));
  return [...new Set(findings)];
}

function scanText(scope, filePath, text, findings) {
  text.split(/\r?\n/).forEach((line, index) => {
    for (const category of lineFindings(line)) {
      findings.push({ scope, path: filePath, line: index + 1, category });
    }
  });
}

function scanPath(scope, filePath, findings) {
  if (isScannerSource(filePath)) return;
  if (/coss/i.test(filePath)) {
    findings.push({ scope, path: filePath, line: 0, category: 'company_identifier_path' });
  }
}

function scanWorktree() {
  const output = spawnSync('git', ['ls-files', '-co', '--exclude-standard'], {
    cwd: root,
    encoding: 'utf8',
    maxBuffer: 1024 * 1024 * 64,
  });
  const findings = [];
  for (const filePath of output.stdout.trim().split(/\n/).filter(Boolean)) {
    if (skipPath(filePath)) continue;
    if (!fs.existsSync(path.join(root, filePath))) continue;
    scanPath('worktree', filePath, findings);
    if (!maybeText(filePath)) continue;
    let text;
    try {
      text = fs.readFileSync(path.join(root, filePath), 'utf8');
    } catch {
      continue;
    }
    if (text.includes('\0')) continue;
    currentFilePath = filePath;
    scanText('worktree', filePath, text, findings);
    currentFilePath = '';
  }
  return findings;
}

function scanGitHistory() {
  const revs = spawnSync('git', ['rev-list', '--all'], {
    cwd: root,
    encoding: 'utf8',
    maxBuffer: 1024 * 1024 * 64,
  }).stdout.trim().split(/\n/).filter(Boolean);
  const findings = [];
  if (!revs.length) return findings;

  const pathOutput = spawnSync('git', ['log', '--all', '--name-only', '--pretty=format:'], {
    cwd: root,
    encoding: 'utf8',
    maxBuffer: 1024 * 1024 * 64,
  });
  for (const filePath of new Set(pathOutput.stdout.trim().split(/\n/).filter(Boolean))) {
    if (!skipPath(filePath)) scanPath('history', filePath, findings);
  }

  const combinedPattern = [
    'COSS',
    'coss',
    'cossok\\.com',
    'coss_',
    '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}',
    '[0-9]{6}-[1-4][0-9]{6}',
    '(\\+82[-[:space:]]?10|010)[-[:space:]]?[0-9]{3,4}[-[:space:]]?[0-9]{4}',
    'birth|dob|date_of_birth|birth_date|생년월일|출생일',
    'password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|private[_-]?key',
    'employee_name|applicant_name|worker_name|author_name|requester_name|approver_name|reviewer_name|manager_name|display_name|full_name|user_name|person_name|성명|작성자|신청자|승인자|검토자',
    '([0-9][ -]?){13,19}',
  ].join('|');
  const grep = spawnSync(
    'git',
    [
      'grep',
      '-nI',
      '-E',
      combinedPattern,
      ...revs,
      '--',
      ':(exclude)third-party/rust/vendor/**',
      ':(exclude)**/node_modules/**',
      ':(exclude)**/package-lock.json',
      ':(exclude)buck-out/**',
      ':(exclude)**/dist/**',
      ':(exclude)**/build/**',
      ':(exclude)**/.expo/**',
    ],
    {
      cwd: root,
      encoding: 'utf8',
      maxBuffer: 1024 * 1024 * 256,
    },
  );
  for (const row of grep.stdout.split(/\n/).filter(Boolean)) {
    const first = row.indexOf(':');
    const second = row.indexOf(':', first + 1);
    const third = row.indexOf(':', second + 1);
    if (first === -1 || second === -1 || third === -1) continue;
    const scope = row.slice(0, first).slice(0, 12);
    const filePath = row.slice(first + 1, second);
    if (skipPath(filePath) || !maybeText(filePath)) continue;
    const line = Number(row.slice(second + 1, third));
    const text = row.slice(third + 1);
    currentFilePath = filePath;
    for (const category of lineFindings(text)) {
      findings.push({ scope, path: filePath, line, category });
    }
    currentFilePath = '';
    if (findings.length >= maxFindings) return findings;
  }
  return findings;
}

const findings = scanHistory ? scanGitHistory() : scanWorktree();
if (findings.length) {
  const summary = findings.reduce((acc, finding) => {
    acc[finding.category] = (acc[finding.category] || 0) + 1;
    return acc;
  }, {});
  console.error(`verify-sensitive-data failed (${scanHistory ? 'history' : 'worktree'}): ${findings.length} finding(s)`);
  console.error(JSON.stringify({ summary, findings: findings.slice(0, 200) }, null, 2));
  process.exit(1);
}

console.log(`verify-sensitive-data passed (${scanHistory ? 'history' : 'worktree'}): no high-signal sensitive data patterns found`);
