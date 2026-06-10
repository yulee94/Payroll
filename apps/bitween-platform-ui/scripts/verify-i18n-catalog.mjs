import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const catalogPath = join(__dirname, "..", "src", "i18n", "catalog.json");
const localizationTerminologyPath = join(__dirname, "..", "..", "..", "docs", "LOCALIZATION_TERMINOLOGY.md");
const catalog = JSON.parse(readFileSync(catalogPath, "utf8"));
const localizationTerminology = readFileSync(localizationTerminologyPath, "utf8");
const expectedLocales = ["ko-KR", "en-US", "zh-Hans-CN", "ja-JP"];
const errors = [];
const latinTokenPattern = /[A-Za-z][A-Za-z0-9_-]*/g;
const koreanGlyphPattern = /[\uac00-\ud7af]/;
const approvedKoreanLatinTokens = new Set(["Bitween", "Acme", "Corporation"]);
const bannedKoreanLoanwords = new Map([
  ["Workflow", "업무 관리"],
  ["workflow", "업무 관리"],
  ["워크플로", "업무 관리"],
  ["워크플로우", "업무 관리"],
  ["태스크", "할 일"],
  ["투두", "할 일"],
  ["오너", "담당자"],
  ["어사인", "배정"],
  ["리마인더", "알림"],
  ["딥다이브", "자세히 보기"],
  ["인사이트", "확인할 점"],
  ["대시보드", "현황"],
  ["프로필", "내 정보"],
  ["메시지", "쪽지"],
  ["세션", "접속"],
  ["토큰", "인증 확인"],
  ["브랜치", "법인 또는 사업장"],
  ["소스", "출처"],
  ["스키마", "자료 구조"],
  ["엔드포인트", "연결 주소"],
  ["백엔드", "서버"],
  ["런북", "지원 절차"],
  ["게이트", "확인 단계"],
  ["패널", "영역"],
  ["노드", "단계"],
  ["캔버스", "흐름도"],
  ["로직", "규칙"],
  ["블롭", "파일"],
  ["오브젝트", "파일"],
  ["스토리지", "보관함"],
  ["마일스톤", "주요 일정"],
  ["플랫폼", "업무 환경"],
  ["모듈", "업무 영역"],
  ["카드", "업무 항목"],
  ["템플릿", "양식"],
  ["테넌트", "고객사"],
  ["데이터", "자료"],
  ["아카이브", "자료함"],
  ["트리거", "시작점"],
  ["라우팅", "배정 또는 인계"],
  ["프리뷰", "화면 확인"],
  ["콘솔", "관리 화면"],
  ["필터", "조건"],
  ["업로드", "올리기"],
  ["미리보기", "확인"],
  ["라이브", "실제"]
]);

const stripInterpolationNames = (value) => value.replace(/\{[^}]+}/g, "");

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
const messageRows = new Map();
for (const [index, row] of (catalog.messages ?? []).entries()) {
  if (!row || typeof row.key !== "string" || row.key.trim().length === 0) {
    errors.push(`messages[${index}] must have a non-empty key`);
    continue;
  }
  if (keys.has(row.key)) {
    errors.push(`duplicate message key ${row.key}`);
  }
  keys.add(row.key);
  messageRows.set(row.key, row);
  requireLocalizedValues(`message ${row.key}`, row.values);

  const koreanValue = row.values?.["ko-KR"];
  if (typeof koreanValue === "string") {
    const visibleKoreanValue = stripInterpolationNames(koreanValue);
    for (const [bannedTerm, suggestedTerm] of bannedKoreanLoanwords) {
      if (visibleKoreanValue.includes(bannedTerm)) {
        errors.push(`message ${row.key} ko-KR uses lazy/non-contextual term "${bannedTerm}"; use culturally appropriate business wording such as "${suggestedTerm}"`);
      }
    }
    const latinTokens = [...visibleKoreanValue.matchAll(latinTokenPattern)]
      .map((match) => match[0])
      .filter((token) => !approvedKoreanLatinTokens.has(token));
    if (latinTokens.length > 0) {
      errors.push(`message ${row.key} ko-KR contains non-Korean visible token(s): ${[...new Set(latinTokens)].join(", ")}`);
    }
  }

  for (const locale of expectedLocales.filter((item) => item !== "ko-KR")) {
    const value = row.values?.[locale];
    if (typeof value === "string" && koreanGlyphPattern.test(value)) {
      errors.push(`message ${row.key} ${locale} contains Korean fallback text`);
    }
  }
}

const workflowLabel = messageRows.get("navigation.workflow.label")?.values?.["ko-KR"];
if (workflowLabel !== "업무 관리") {
  errors.push(`navigation.workflow.label ko-KR must be 업무 관리, got ${JSON.stringify(workflowLabel)}`);
}
const workflowEyebrow = messageRows.get("navigation.workflow.eyebrow")?.values?.["ko-KR"];
if (workflowEyebrow !== "업무 관리") {
  errors.push(`navigation.workflow.eyebrow ko-KR must be 업무 관리, got ${JSON.stringify(workflowEyebrow)}`);
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

for (const requiredTerm of [
  "Culture context is part of correctness",
  "Workflow module / workflow canvas",
  "업무 관리",
  "HR",
  "인사",
  "AI assistance",
  "업무 지원",
  "Dashboard",
  "현황",
  "Tenant",
  "고객사",
  "Data",
  "자료"
]) {
  if (!localizationTerminology.includes(requiredTerm)) {
    errors.push(`docs/LOCALIZATION_TERMINOLOGY.md must retain context-aware glossary term ${requiredTerm}`);
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
