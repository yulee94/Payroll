const tones = {
  ready: "tone-ready",
  attention: "tone-attention",
  blocked: "tone-blocked",
  neutral: "tone-neutral"
};

const demoAccount = {
  companyCode: "0000",
  password: "admin",
  userId: "admin"
};

const employeeNumber = "BW-0001";
const session = {
  roleLabel: "admin",
  tenantName: "Bitween Demo"
};
const companyLogoUri =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%231F3864'/%3E%3Cpath d='M18 18h18c7 0 11 4 11 9 0 4-2 7-6 8 5 1 8 5 8 10 0 6-5 10-13 10H18V18zm11 14h6c3 0 5-1 5-4s-2-4-5-4h-6v8zm0 17h7c4 0 6-2 6-5s-2-5-6-5h-7v10z' fill='white'/%3E%3C/svg%3E";

const navDefs = [
  ["home", "#64748B"],
  ["payroll", "#1F3864"],
  ["hr", "#0D9488"],
  ["attendance", "#0284C7"],
  ["recruit", "#9333EA"],
  ["travel", "#0F766E"],
  ["workflow", "#2563EB"],
  ["archive", "#475569"],
  ["ai", "#7C3AED"],
  ["admin", "#B45309"],
  ["settings", "#0F766E"]
].map(([id, accent]) => ({ id, accent }));

const sidebarThemeIds = ["steel", "graphite", "teal", "navy"];
const supportedLocales = ["ko-KR", "en-US", "zh-Hans-CN", "ja-JP"];

const metricDefs = [
  ["today", "attention"],
  ["ready", "ready"],
  ["blocked", "blocked"],
  ["docs", "neutral"]
].map(([id, tone]) => ({ id, tone }));

const readinessDefs = [
  ["roster", "attention"],
  ["policy", "neutral"],
  ["outputs", "ready"],
  ["api", "attention"]
].map(([id, tone]) => ({ id, tone }));

const payrollStepDefs = [
  ["settings", "01", "attention"],
  ["upload", "02", "neutral"],
  ["preview", "03", "ready"],
  ["archive", "04", "neutral"]
].map(([id, index, tone]) => ({ id, index, tone }));

const payrollIntegrationCheckDefs = [
  ["branch-docs", "attention"],
  ["edi", "attention"],
  ["mapping", "neutral"],
  ["policy", "ready"]
].map(([id, tone]) => ({ id, tone }));

const rowGroups = {
  payrollSettings: [
    ["payroll-setting-1", "neutral", "settings"],
    ["payroll-setting-2", "attention", "settings"],
    ["payroll-setting-3", "ready", "settings"]
  ],
  payrollIntegration: [
    ["payroll-integration-1", "attention", "admin"],
    ["payroll-integration-2", "neutral", "admin"],
    ["payroll-integration-3", "ready", "payroll"]
  ],
  preview: [
    ["preview-1", "ready", "archive"],
    ["preview-2", "neutral", "payroll"],
    ["preview-3", "attention", "archive"]
  ]
};

const workQueueDefs = [
  ["payroll-june", "attention", "payroll"],
  ["approval-pending", "neutral", "workflow"],
  ["travel-diary", "attention", "travel"],
  ["archive-preview", "ready", "archive"]
].map(([id, tone, target]) => ({ id, tone, target }));

const calendarEventDefs = [
  ["calendar-payroll", "2026.06.04", "10:00", "attention"],
  ["calendar-approval", "2026.06.04", "14:00", "neutral"],
  ["calendar-recruit", "2026.06.05", "09:30", "ready"],
  ["calendar-travel", "2026.06.05", "16:00", "attention"]
].map(([id, date, time, tone]) => ({ id, date, time, tone }));

const todayTodoDefs = [
  ["todo-payroll", "attention", false],
  ["todo-approval", "neutral", false],
  ["todo-travel", "attention", false],
  ["todo-archive", "ready", true]
].map(([id, tone, done]) => ({ id, tone, done }));

const attendanceLogDefs = [
  ["att-log-1", "09:02", "ready"],
  ["att-log-2", "13:40", "attention"],
  ["att-log-3", "--:--", "neutral"]
].map(([id, time, tone]) => ({ id, time, tone }));

const travelStageDefs = [
  ["travel-plan", "01", "neutral"],
  ["travel-run", "02", "attention"],
  ["travel-diary", "03", "attention"],
  ["travel-result", "04", "neutral"],
  ["travel-review", "05", "ready"]
].map(([id, index, tone]) => ({ id, index, tone }));

const adminPermissionDefs = [
  ["role-owner", "ready"],
  ["role-manager", "neutral"],
  ["role-employee", "attention"]
].map(([id, tone]) => ({ id, tone }));

const archiveFolderDefs = [
  ["folder-payroll", "ready", "payroll"],
  ["folder-attendance", "attention", "attendance"],
  ["folder-approval", "neutral", "workflow"],
  ["folder-travel", "ready", "travel"]
].map(([id, tone, target]) => ({ id, tone, target }));

const archiveDocumentDefs = [
  ["doc-payroll", "ready"],
  ["doc-attendance", "attention"],
  ["doc-travel", "neutral"]
].map(([id, tone]) => ({ id, tone }));

const aiRecommendationDefs = [
  ["ai-payroll-errors", "ready", "payroll"],
  ["ai-approval-comment", "attention", "workflow"],
  ["ai-archive-summary", "neutral", "archive"]
].map(([id, tone, target]) => ({ id, tone, target }));

const aiDraftDefs = [
  ["draft-summary", "ready"],
  ["draft-question", "attention"],
  ["draft-comment", "neutral"]
].map(([id, tone]) => ({ id, tone }));

const moduleDefs = {
  hr: {
    filters: ["all", "roster", "resume", "resignation", "certificate"],
    metrics: [["employees", "ready"], ["attendance", "attention"], ["certs", "neutral"]],
    rows: [["hr-1", "attention", "hr", ["roster"]], ["hr-2", "neutral", "hr", ["certificate"]], ["hr-3", "ready", "hr", ["resume", "resignation"]]],
    secondaryTarget: "payroll"
  },
  attendance: {
    filters: ["all", "checkIn", "checkOut", "attention"],
    metrics: [["checked-in", "ready"], ["pending", "attention"], ["weekly", "neutral"]],
    rows: [["attendance-1", "ready", "attendance", ["checkIn", "checkOut"]], ["attendance-2", "attention", "attendance", ["attention"]]],
    secondaryTarget: "hr"
  },
  recruit: {
    filters: ["all", "applicant", "career", "credential", "placement"],
    metrics: [["applicants", "ready"], ["qualified", "attention"], ["placement", "neutral"]],
    rows: [["recruit-1", "attention", "recruit", ["applicant", "career"]], ["recruit-2", "ready", "recruit", ["credential", "placement"]]],
    secondaryTarget: "hr"
  },
  travel: {
    filters: ["all", "plan", "run", "diary", "result", "review"],
    metrics: [["plans", "neutral"], ["diary", "attention"], ["completed", "ready"]],
    rows: [["travel-1", "attention", "travel", ["plan", "run", "diary"]], ["travel-2", "neutral", "travel", ["review", "result"]], ["travel-3", "ready", "travel", ["result"]]],
    secondaryTarget: "workflow"
  },
  workflow: {
    filters: ["all", "pending", "ongoing", "returned"],
    metrics: [["pending", "attention"], ["drafts", "neutral"], ["done", "ready"]],
    rows: [["wf-1", "attention", "workflow", ["pending"]], ["wf-2", "neutral", "workflow", ["ongoing"]]],
    secondaryTarget: "archive"
  },
  archive: {
    filters: ["all", "payroll", "contract", "report"],
    metrics: [["reports", "ready"], ["missing", "attention"], ["shared", "ready"]],
    rows: [["ar-1", "ready", "archive", ["payroll", "report"]], ["ar-2", "attention", "archive", ["report"]]],
    secondaryTarget: "payroll"
  },
  ai: {
    filters: ["all", "summary", "draft", "review"],
    metrics: [["prompts", "ready"], ["reviews", "attention"], ["policy", "neutral"]],
    rows: [["ai-1", "ready", "ai", ["summary"]], ["ai-2", "attention", "ai", ["draft", "review"]]],
    secondaryTarget: "settings"
  },
  admin: {
    filters: ["all", "permission", "branch", "subaccount", "audit"],
    metrics: [["branch", "ready"], ["users", "ready"], ["roles", "attention"], ["audit", "ready"]],
    rows: [["ad-1", "attention", "admin", ["subaccount", "permission"]], ["ad-2", "ready", "admin", ["branch"]], ["ad-3", "attention", "admin", ["permission", "audit"]]],
    secondaryTarget: "settings"
  },
  settings: {
    filters: ["all", "personal", "payroll", "notification"],
    metrics: [["profile", "ready"], ["payroll", "attention"], ["notice", "neutral"]],
    rows: [["st-1", "attention", "settings", ["payroll"]], ["st-2", "ready", "settings", ["personal"]]],
    secondaryTarget: "payroll"
  }
};

const state = {
  activeId: "home",
  authed: false,
  catalog: undefined,
  companyCode: "",
  filter: "all",
  loginFeedbackKey: "",
  password: "",
  selectedPayrollCardKey: "",
  selectedPayrollStepKey: "",
  selectedQueueKey: "",
  locale: "ko-KR",
  search: "",
  selectedRowKey: "",
  sidebarTheme: "steel",
  userId: ""
};

async function boot() {
  const response = await fetch("/catalog.json");
  state.catalog = await response.json();
  document.title = t("preview.documentTitle");
  render();
}

function t(key, params = {}) {
  const message = state.catalog?.messages?.find((row) => row.key === key);
  const template = message?.values?.[state.locale];
  if (!template) {
    throw new Error(`Missing i18n message ${key} for ${state.locale}`);
  }
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, name) => String(params[name] ?? match));
}

function languageName(locale) {
  const row = state.catalog?.languageDisplayNames?.find((item) => item.locale === locale);
  const label = row?.values?.[state.locale];
  if (!label) {
    throw new Error(`Missing language label ${locale} for ${state.locale}`);
  }
  return label;
}

function navigationItems() {
  return navDefs.map((item) => ({
    ...item,
    description: t(`navigation.${item.id}.description`),
    eyebrow: t(`navigation.${item.id}.eyebrow`),
    label: t(`navigation.${item.id}.label`)
  }));
}

function sidebarThemes() {
  return sidebarThemeIds.map((id) => ({
    id,
    description: t(`sidebarThemes.${id}.description`),
    label: t(`sidebarThemes.${id}.label`)
  }));
}

function platformMetrics() {
  return metricDefs.map((item) => ({
    ...item,
    helper: t(`platform.metrics.${item.id}.helper`),
    label: t(`platform.metrics.${item.id}.label`),
    value: t(`platform.metrics.${item.id}.value`)
  }));
}

function readinessCards() {
  return readinessDefs.map((item) => ({
    ...item,
    detail: t(`payroll.readiness.${item.id}.detail`),
    title: t(`payroll.readiness.${item.id}.title`),
    value: t(`payroll.readiness.${item.id}.value`)
  }));
}

function payrollSteps() {
  return payrollStepDefs.map((item) => ({
    ...item,
    detail: t(`payroll.steps.${item.id}.detail`),
    status: t(`payroll.steps.${item.id}.status`),
    title: t(`payroll.steps.${item.id}.title`)
  }));
}

function localizedRows(group) {
  return rowGroups[group].map(([id, tone, target]) => localizedRow(`rows.${group}.${id}`, id, tone, target));
}

function localizedRow(prefix, id, tone, target, filters = []) {
  return {
    category: t(`${prefix}.category`),
    filters,
    id,
    next: t(`${prefix}.nextStep`),
    owner: t(`${prefix}.owner`),
    status: t(`${prefix}.status`),
    target,
    tone
  };
}

function workQueue() {
  return workQueueDefs.map((item) => ({
    ...item,
    due: t(`workQueue.${item.id}.due`),
    meta: t(`workQueue.${item.id}.meta`),
    owner: t(`workQueue.${item.id}.owner`),
    status: t(`workQueue.${item.id}.status`),
    title: t(`workQueue.${item.id}.title`)
  }));
}

function calendarEvents() {
  return calendarEventDefs.map((item) => ({
    ...item,
    title: t(`calendarEvents.${item.id}.title`)
  }));
}

function todayTodos() {
  return todayTodoDefs.map((item) => ({
    ...item,
    owner: t(`todayTodos.${item.id}.owner`),
    timeLabel: t(`todayTodos.${item.id}.timeLabel`),
    title: t(`todayTodos.${item.id}.title`)
  }));
}

function moduleData(id) {
  const def = moduleDefs[id];
  if (!def) return undefined;
  return {
    id,
    emptyDescription: t(`modules.${id}.emptyDescription`),
    emptyTitle: t(`modules.${id}.emptyTitle`),
    filters: def.filters.map((filter) => ({ id: filter, label: t(`modules.${id}.filters.${filter}`) })),
    metrics: def.metrics.map(([metricId, tone]) => ({
      helper: t(`modules.${id}.metrics.${metricId}.helper`),
      id: metricId,
      label: t(`modules.${id}.metrics.${metricId}.label`),
      tone,
      value: t(`modules.${id}.metrics.${metricId}.value`)
    })),
    primaryAction: {
      description: t(`modules.${id}.primaryAction.description`),
      label: t(`modules.${id}.primaryAction.label`),
      target: id
    },
    rows: def.rows.map(([rowId, tone, target, filters]) =>
      localizedRow(`modules.${id}.rows.${rowId}`, rowId, tone, target, filters)
    ),
    secondaryAction: {
      description: t(`modules.${id}.secondaryAction.description`),
      label: t(`modules.${id}.secondaryAction.label`),
      target: def.secondaryTarget
    },
    subtitle: t(`modules.${id}.subtitle`),
    title: t(`modules.${id}.title`)
  };
}

function html(strings, ...values) {
  return strings.reduce((out, str, i) => out + str + (values[i] ?? ""), "");
}

function escapeText(value) {
  return String(value).replace(/[&<>"']/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[m]);
}

function badge(text, tone = "neutral") {
  return `<span class="badge ${tones[tone]}">${escapeText(text)}</span>`;
}

function button(label, target, variant = "secondary") {
  return `<button class="btn ${variant}" data-target="${target}">${escapeText(label)}</button>`;
}

function render() {
  if (!state.catalog) return;
  document.documentElement.lang = state.locale.split("-")[0];
  document.title = t("preview.documentTitle");
  document.getElementById("app").innerHTML = state.authed ? renderShell() : renderLogin();
  bindEvents();
}

function renderLogin() {
  return html`
    <section class="login-page">
      <div class="login-grid">
        <div class="login-hero">
          ${badge(t("screens.login.hero.badge"), "ready")}
          <div class="hero-copy">
            <div class="brand">Bitween</div>
            <h1 class="hero-title">${t("screens.login.hero.title")}</h1>
            <p class="hero-desc">${t("screens.login.hero.copy")}</p>
          </div>
          <div class="hero-pills">
            <span class="hero-pill">${t("screens.login.hero.status.roleMenu")}</span>
            <span class="hero-pill">${t("screens.login.hero.status.workflowStatus")}</span>
            <span class="hero-pill">${t("screens.login.hero.status.dataProtection")}</span>
          </div>
        </div>
        <form class="card login-card" id="login-form">
          ${sectionHead(t("screens.login.form.eyebrow"), t("screens.login.form.title"), t("screens.login.form.description"))}
          ${languageSelector()}
          ${field(t("screens.login.form.companyCode"), "company-code", demoAccount.companyCode, "text", state.companyCode)}
          ${field(t("screens.login.form.userId"), "user-id", demoAccount.userId, "text", state.userId)}
          ${field(t("screens.login.form.password"), "password", demoAccount.password, "password", state.password)}
          ${state.loginFeedbackKey ? `<div class="inline-warning">${badge(t("screens.login.feedback.badge"), "attention")}<span>${t(state.loginFeedbackKey)}</span></div>` : ""}
          <div class="login-actions">
            <button class="btn primary" type="submit">${t("screens.login.actions.enterHome")}</button>
            <button class="btn secondary" type="button" data-demo-login="true">${t("screens.login.actions.demo")}</button>
          </div>
          <div class="notice">${badge(t("screens.login.demo.badge"), "neutral")}<span class="helper">${t("screens.login.demo.summary")}</span></div>
        </form>
      </div>
    </section>
  `;
}

function languageSelector() {
  return `<section class="language-panel">
    <span class="helper">${t("settings.i18n.title")}</span>
    <div class="language-grid">${supportedLocales.map((locale) => `
      <button class="language-option ${state.locale === locale ? "selected" : ""}" type="button" data-language="${locale}">
        <strong>${languageName(locale)}</strong><span class="helper">${state.locale === locale ? t("settings.i18n.status.selected") : t("settings.i18n.status.available")}</span>
      </button>
    `).join("")}</div>
  </section>`;
}

function field(label, id, placeholder, type = "text", value = "") {
  return `<label class="field" for="${id}"><span>${escapeText(label)}</span><input id="${id}" type="${type}" value="${escapeText(value)}" placeholder="${escapeText(placeholder)}" /></label>`;
}

function renderShell() {
  const items = navigationItems();
  const active = items.find((item) => item.id === state.activeId) || items[0];
  const sessionLabel = `${session.tenantName} · ${t("session.roleLabel")} · ${demoAccount.companyCode}`;
  const demoModeLabel = `${t("preview.demoMode.title")}. ${t("preview.demoMode.description")}`;
  return html`
    <section class="shell sidebar-theme-${state.sidebarTheme}">
      <aside class="sidebar">
        <div class="brand-block">
          <img class="company-logo" src="${companyLogoUri}" alt="${t("shell.companyLogo")}" />
          <div><strong>Bitween</strong><span>${t("shell.brandSubtitle")}</span></div>
        </div>
        <div class="sidebar-options" aria-label="${t("shell.themePanel.aria")}">
          <span class="sidebar-options-title">${t("shell.themePanel.title")}</span>
          <div class="sidebar-theme-grid">
            ${sidebarThemes().map((theme) => `
              <button
                class="sidebar-theme-chip ${state.sidebarTheme === theme.id ? "active" : ""}"
                data-sidebar-theme="${theme.id}"
                aria-label="${escapeText(`${theme.label}. ${theme.description}`)}"
                aria-pressed="${state.sidebarTheme === theme.id ? "true" : "false"}"
                title="${escapeText(theme.description)}"
              >
                <span class="sidebar-swatch sidebar-swatch-${theme.id}"></span>
                <strong>${theme.label}</strong>
              </button>
            `).join("")}
          </div>
        </div>
        <nav class="nav" aria-label="${t("shell.navigation.aria")}">
            ${items.map((item) => `
            <button class="nav-button ${item.id === active.id ? "active" : ""}" data-target="${item.id}" aria-current="${item.id === active.id ? "page" : "false"}" style="${item.id === active.id ? `border-left-color:${item.accent}` : ""}">
              <strong>${item.label}</strong>
            </button>
          `).join("")}
        </nav>
      </aside>
      <div class="main">
        <header class="topbar">
          <div class="topbar-copy">
            <h1>${active.label}</h1>
          </div>
          <div class="top-actions">
            ${badge(sessionLabel, "neutral")}
            ${badge(t("shell.employeeNumber", { number: employeeNumber }), "neutral")}
            <button class="btn ghost compact-btn" data-logout="true">${t("shell.logout")}</button>
          </div>
        </header>
        <div class="demo-mode-banner" role="status" aria-label="${escapeText(demoModeLabel)}">
          ${badge(t("preview.demoMode.badge"), "attention")}
          <div>
            <strong>${t("preview.demoMode.title")}</strong>
            <span>${t("preview.demoMode.description")}</span>
          </div>
        </div>
        <div class="content">${renderScreen(active.id)}</div>
      </div>
    </section>
    <div class="toast" id="toast">${t("preview.toast.default")}</div>
  `;
}

function renderScreen(id) {
  if (id === "home") return renderHome();
  if (id === "payroll") return renderPayroll();
  return renderModule(id);
}

function renderHome() {
  const queueItems = workQueue();
  const selectedQueue = queueItems.find((row) => row.id === state.selectedQueueKey) || queueItems[0];
  const items = navigationItems();

  return html`
    <section class="card">
      ${sectionHead("", t("screens.launcher.platformStatus.title"), t("screens.launcher.platformStatus.description"), button(t("screens.launcher.platformStatus.action"), "payroll", "secondary"))}
      ${metrics(platformMetrics())}
    </section>
    <section class="planner-grid">
      <div class="card planner-card">
        ${sectionHead("", t("screens.calendar.title"), t("screens.calendar.description"))}
        <div class="calendar-day"><span>2026.06</span><strong>04</strong><em>${t("screens.calendar.weekday")}</em></div>
        <div class="planner-list">${calendarEvents().map((event) => `
          <div class="planner-item">${badge(event.time, event.tone)}<div><strong>${event.title}</strong><span class="helper">${event.date}</span></div></div>
        `).join("")}</div>
      </div>
      <div class="card planner-card">
        ${sectionHead("", t("screens.todo.title"), t("screens.todo.description"))}
        <div class="planner-list">${todayTodos().map((item) => `
          <div class="planner-item todo-item ${item.done ? "done" : ""}">${badge(item.timeLabel, item.tone)}<div><strong>${item.title}</strong><span class="helper">${item.owner}</span></div></div>
        `).join("")}</div>
      </div>
    </section>
    <section class="card">
      ${sectionHead("", t("screens.launcher.workQueue.title"), t("screens.launcher.workQueue.description"))}
      <div class="queue-grid">${queueItems.map((item) => `
        <button class="queue-card select-card ${state.selectedQueueKey === item.id ? "selected" : ""}" data-queue-key="${item.id}">
          <div class="queue-head">${badge(item.status, item.tone)}<span class="helper">${item.due}</span></div>
          <strong>${item.title}</strong>
          <span class="helper">${t("screens.launcher.workQueue.metaOwner", { meta: item.meta, owner: item.owner })}</span>
        </button>
      `).join("")}</div>
      ${selectedQueue ? queueDetail(selectedQueue) : ""}
    </section>
    <section class="card">
      ${sectionHead("", t("screens.launcher.shortcuts.title"), t("screens.launcher.shortcuts.description"))}
      <div class="launcher-grid">${items.filter((item) => item.id !== "home").map((item) => `
        <article class="launcher-card" style="border-top-color:${item.accent}">
          <span class="eyebrow">${item.eyebrow}</span>
          <strong>${item.label}</strong>
          <span class="helper">${item.description}</span>
          ${button(t("screens.actions.open"), item.id, "ghost")}
        </article>
      `).join("")}</div>
    </section>
  `;
}

function queueDetail(item) {
  return `<div class="detail-panel">
    <div class="detail-head"><div><span class="helper">${t("screens.workQueueDetail.selectedLabel")}</span><strong>${escapeText(item.title)}</strong></div>${badge(item.status, item.tone)}</div>
    <div class="detail-grid">
      <div class="detail-item"><span class="helper">${t("screens.workQueueDetail.owner")}</span><strong>${escapeText(item.owner)}</strong></div>
      <div class="detail-item"><span class="helper">${t("screens.workQueueDetail.due")}</span><strong>${escapeText(item.due)}</strong></div>
      <div class="detail-item"><span class="helper">${t("screens.workQueueDetail.area")}</span><span>${escapeText(item.meta)}</span></div>
    </div>
    <div class="action-row">${button(t("screens.workQueueDetail.actions.openRelated"), item.target, "secondary")}${button(t("screens.workQueueDetail.actions.confirmFlow"), state.activeId, "ghost")}</div>
  </div>`;
}

function renderPayroll() {
  const cards = readinessCards();
  const steps = payrollSteps();
  const selectedReadiness = cards.find((row) => row.id === state.selectedPayrollCardKey) || cards[0];
  const selectedStep = steps.find((row) => row.id === state.selectedPayrollStepKey) || steps[0];
  return html`
    <section class="card">
      ${sectionHead(t("screens.payroll.readiness.eyebrow"), t("screens.payroll.readiness.title"), t("screens.payroll.readiness.description"), button(t("screens.payroll.readiness.action"), "settings", "secondary"))}
      <div class="card-grid">${cards.map((item) => `
        <button class="mini-card readiness-card select-card ${state.selectedPayrollCardKey === item.id ? "selected" : ""}" data-payroll-card-key="${item.id}" style="border-top-color:${toneColor(item.tone)}">
          <span class="helper">${item.title}</span>
          <strong class="metric-value" style="color:${toneColor(item.tone)}">${item.value}</strong>
          <span>${item.detail}</span>
        </button>
      `).join("")}</div>
      ${selectedReadiness ? payrollReadinessDetail(selectedReadiness) : ""}
    </section>
    ${payrollIntegrationPanel()}
    <section class="card">
      ${sectionHead(t("screens.payroll.flow.eyebrow"), t("screens.payroll.flow.title"), t("screens.payroll.flow.description"), button(t("screens.payroll.flow.action"), "settings", "secondary"))}
      <div class="step-grid">${steps.map((item) => `
        <button class="step-card select-card ${state.selectedPayrollStepKey === item.id ? "selected" : ""}" data-payroll-step-key="${item.id}" style="border-top-color:${toneColor(item.tone)}">
          <span class="eyebrow">${item.index}</span>
          ${badge(item.status, item.tone)}
          <strong>${item.title}</strong>
          <span class="helper">${item.detail}</span>
        </button>
      `).join("")}</div>
      ${selectedStep ? payrollStepDetail(selectedStep) : ""}
      <div class="action-row">${button(t("screens.payroll.actions.keepPayroll"), "payroll", "primary")}${button(t("screens.payroll.actions.monthlyArchive"), "archive")}${button(t("screens.payroll.actions.prepareAiReview"), "ai", "ghost")}</div>
    </section>
    <section class="card">
      ${sectionHead(t("screens.launcher.settingsSummary.eyebrow"), t("screens.launcher.settingsSummary.title"), t("screens.launcher.settingsSummary.description"), button(t("screens.launcher.settingsSummary.action"), "settings", "secondary"))}
      ${table(localizedRows("payrollSettings"))}
    </section>
    <section class="card">
      ${sectionHead(t("screens.launcher.previewArchive.eyebrow"), t("screens.launcher.previewArchive.title"), t("screens.launcher.previewArchive.description"), button(t("screens.launcher.previewArchive.action"), "archive", "secondary"))}
      ${table(localizedRows("preview"))}
    </section>
  `;
}

function payrollIntegrationPanel() {
  return `<section class="card">
    ${sectionHead("", t("screens.payroll.integration.title"), t("screens.payroll.integration.description"), button(t("screens.payroll.integration.action"), "admin", "secondary"))}
    <div class="integration-grid">${payrollIntegrationCheckDefs.map((item) => `
      <article class="integration-card" style="border-top-color:${toneColor(item.tone)}">
        <span class="helper">${t(`screens.payroll.integrationChecks.${item.id}.label`)}</span>
        <strong class="metric-value" style="color:${toneColor(item.tone)}">${t(`screens.payroll.integrationChecks.${item.id}.value`)}</strong>
        <span>${t(`screens.payroll.integrationChecks.${item.id}.detail`)}</span>
      </article>
    `).join("")}</div>
    ${table(localizedRows("payrollIntegration"))}
    <div class="notice">${badge(t("screens.payroll.integration.notice.badge"), "neutral")}<span class="helper">${t("screens.payroll.integration.notice.description")}</span></div>
  </section>`;
}

function payrollReadinessDetail(item) {
  return `<div class="detail-panel">
    <div class="detail-head"><div><span class="helper">${t("screens.payroll.readinessDetail.label")}</span><strong>${escapeText(item.title)}</strong></div>${badge(item.value, item.tone)}</div>
    <span>${escapeText(item.detail)}</span>
    <div class="action-row">${button(t("screens.payroll.readinessDetail.actions.status"), "payroll", "secondary")}${button(t("screens.payroll.readinessDetail.actions.materials"), "archive", "ghost")}</div>
  </div>`;
}

function payrollStepDetail(item) {
  return `<div class="detail-panel">
    <div class="detail-head"><div><span class="helper">${t("screens.payroll.stepDetail.label")}</span><strong>${escapeText(item.title)}</strong></div>${badge(item.status, item.tone)}</div>
    <span>${escapeText(item.detail)}</span>
    <div class="action-row">${button(t("screens.payroll.stepDetail.actions.work"), "payroll", "secondary")}${button(t("screens.payroll.stepDetail.actions.help"), "ai", "ghost")}</div>
  </div>`;
}

function renderModule(id) {
  const data = moduleData(id);
  if (!data) return empty(t("screens.module.unavailable.title"), t("screens.module.unavailable.description"));
  const rows = filterRows(data.rows);
  const selectedRow = rows.find((row) => row.id === state.selectedRowKey) || rows[0];
  const filterLabel = data.filters.find((filter) => filter.id === state.filter)?.label || data.filters[0].label;
  return html`
    <section class="card">
      ${sectionHead("", data.title, "", button(data.primaryAction.label, data.primaryAction.target, "primary"))}
      ${metrics(data.metrics)}
    </section>
    ${id === "attendance" ? attendancePhonePanel() : ""}
    ${id === "travel" ? travelWorklogPanel() : ""}
    ${id === "admin" ? adminAccountPanel() : ""}
    ${id === "archive" ? archiveLibraryPanel() : ""}
    ${id === "ai" ? aiWorkspacePanel() : ""}
    ${id === "settings" ? i18nSettingsPanel() : ""}
    <section class="card">
      ${sectionHead("", t("screens.module.list.title"), t("screens.module.list.description"), button(data.secondaryAction.label, data.secondaryAction.target, "secondary"))}
      <div class="list-toolbar">
        <div class="filters">${data.filters.map((filter) => `<button class="filter-chip ${state.filter === filter.id ? "active" : ""}" data-filter="${filter.id}">${filter.label}</button>`).join("")}</div>
        <label class="search-box" for="work-search"><span>${t("screens.module.search.label")}</span><input id="work-search" type="search" value="${escapeText(state.search)}" placeholder="${t("screens.module.search.placeholder")}" /></label>
      </div>
      <div class="list-summary"><strong>${t("screens.module.list.count", { count: rows.length })}</strong><span class="helper">${state.search ? t("screens.module.list.filteredWithSearch", { filter: filterLabel, search: state.search }) : t("screens.module.list.filtered", { filter: filterLabel })}</span></div>
      ${table(rows, true)}
      ${selectedRow ? workDetail(selectedRow) : ""}
    </section>
    <div class="action-panels">
      <section class="card"><strong>${data.primaryAction.label}</strong><span class="helper">${data.primaryAction.description}</span>${button(t("screens.actions.move"), data.primaryAction.target, "ghost")}</section>
      <section class="card"><strong>${data.secondaryAction.label}</strong><span class="helper">${data.secondaryAction.description}</span>${button(t("screens.actions.move"), data.secondaryAction.target, "ghost")}</section>
    </div>
  `;
}

function sectionHead(eyebrow, title, desc, action = "") {
  return `<div class="section-head"><div class="section-title">${eyebrow ? `<span class="eyebrow">${eyebrow}</span>` : ""}<h2>${title}</h2>${desc ? `<p>${desc}</p>` : ""}</div>${action}</div>`;
}

function i18nSettingsPanel() {
  return `<section class="card">
    ${sectionHead("", t("settings.i18n.title"), t("settings.i18n.description"))}
    <div class="language-grid">${supportedLocales.map((locale) => `
      <button class="language-option ${state.locale === locale ? "selected" : ""}" data-language="${locale}">
        <strong>${languageName(locale)}</strong><span class="helper">${state.locale === locale ? t("settings.i18n.status.selected") : t("settings.i18n.status.available")}</span>
      </button>
    `).join("")}</div>
    <div class="language-summary-panel">${badge(t("settings.i18n.current.badge"), "ready")}<strong>${t("settings.i18n.current.title", { language: languageName(state.locale) })}</strong><span class="helper">${t("settings.i18n.current.description")}</span></div>
    <div class="notice">${badge(t("settings.i18n.catalogRule.title"), "neutral")}<span class="helper">${t("settings.i18n.catalogRule.description")}</span></div>
  </section>`;
}

function aiWorkspacePanel() {
  return `<section class="card">
    ${sectionHead("", t("screens.ai.title"), t("screens.ai.description"), button(t("screens.ai.action"), "settings", "secondary"))}
    <div class="ai-workspace-grid">
      <div class="ai-recommendation-list">${aiRecommendationDefs.map((item) => `
        <button class="ai-recommendation-item" data-target="${item.target}" style="border-left-color:${toneColor(item.tone)}">
          ${badge(t(`screens.ai.recommendations.${item.id}.status`), item.tone)}
          <div><strong>${t(`screens.ai.recommendations.${item.id}.title`)}</strong><span class="helper">${t(`screens.ai.recommendations.${item.id}.source`)}</span></div>
        </button>
      `).join("")}</div>
      <div class="ai-preview-pane">
        <span class="helper">${t("screens.ai.preview.label")}</span>
        <strong>${t("screens.ai.preview.title")}</strong>
        <div class="ai-draft-grid">${aiDraftDefs.map((item) => `
          <article class="ai-draft-card" style="border-top-color:${toneColor(item.tone)}">
            ${badge(t(`screens.ai.drafts.${item.id}.label`), item.tone)}
            <strong>${t(`screens.ai.drafts.${item.id}.title`)}</strong>
            <span class="helper">${t(`screens.ai.drafts.${item.id}.detail`)}</span>
          </article>
        `).join("")}</div>
        <div class="action-row">${button(t("screens.ai.preview.actions.payroll"), "payroll", "secondary")}${button(t("screens.ai.preview.actions.archive"), "archive", "ghost")}</div>
      </div>
    </div>
  </section>`;
}

function archiveLibraryPanel() {
  return `<section class="card">
    ${sectionHead("", t("screens.archive.title"), t("screens.archive.description"), button(t("screens.archive.action"), "payroll", "secondary"))}
    <div class="archive-folder-grid">${archiveFolderDefs.map((item) => `
      <button class="archive-folder-card" data-target="${item.target}" style="border-top-color:${toneColor(item.tone)}">
        ${badge(t(`screens.archive.folders.${item.id}.count`), item.tone)}
        <strong>${t(`screens.archive.folders.${item.id}.label`)}</strong>
        <span class="helper">${t(`screens.archive.folders.${item.id}.owner`)}</span>
      </button>
    `).join("")}</div>
    <div class="archive-preview-grid">
      <div class="archive-document-list">${archiveDocumentDefs.map((item) => `
        <article class="archive-document-item">${badge(t(`screens.archive.documents.${item.id}.status`), item.tone)}<div><strong>${t(`screens.archive.documents.${item.id}.title`)}</strong><span class="helper">${t("screens.archive.documents.meta", { type: t(`screens.archive.documents.${item.id}.type`), owner: t(`screens.archive.documents.${item.id}.owner`) })}</span></div></article>
      `).join("")}</div>
      <div class="archive-preview-pane">
        <span class="helper">${t("screens.archive.preview.label")}</span>
        <strong>${t("screens.archive.preview.title")}</strong>
        <div class="archive-meta-grid">
          <div class="detail-item"><span class="helper">${t("screens.archive.preview.securityScope.label")}</span><strong>${t("screens.archive.preview.securityScope.value")}</strong></div>
          <div class="detail-item"><span class="helper">${t("screens.archive.preview.status.label")}</span><strong>${t("screens.archive.preview.status.value")}</strong></div>
        </div>
        <div class="action-row">${button(t("screens.archive.preview.actions.payroll"), "payroll", "secondary")}${button(t("screens.archive.preview.actions.permissions"), "admin", "ghost")}</div>
      </div>
    </div>
  </section>`;
}

function adminAccountPanel() {
  return `<section class="card">
    ${sectionHead("", t("screens.admin.title"), t("screens.admin.description"))}
    <div class="admin-branch-grid">
      <article class="detail-item"><span class="helper">${t("screens.admin.branchAccount.label")}</span><strong>${t("screens.admin.branchAccount.value")}</strong><span>${t("screens.admin.branchAccount.detail")}</span></article>
      <article class="detail-item"><span class="helper">${t("screens.admin.subaccount.label")}</span><strong>${t("screens.admin.subaccount.value")}</strong><span>${t("screens.admin.subaccount.detail")}</span></article>
    </div>
    <div class="permission-matrix">${adminPermissionDefs.map((item) => `
      <article class="permission-row">
        <div class="permission-role">${badge(t(`screens.admin.permissions.${item.id}.role`), item.tone)}</div>
        <div class="permission-cell"><span class="helper">${t("screens.admin.permissions.columns.payroll")}</span><strong>${t(`screens.admin.permissions.${item.id}.payroll`)}</strong></div>
        <div class="permission-cell"><span class="helper">${t("screens.admin.permissions.columns.executive")}</span><strong>${t(`screens.admin.permissions.${item.id}.executive`)}</strong></div>
        <div class="permission-cell"><span class="helper">${t("screens.admin.permissions.columns.archive")}</span><strong>${t(`screens.admin.permissions.${item.id}.archive`)}</strong></div>
      </article>
    `).join("")}</div>
  </section>`;
}

function travelWorklogPanel() {
  return `<section class="card">
    ${sectionHead("", t("screens.travel.title"), t("screens.travel.description"))}
    <div class="travel-stage-grid">${travelStageDefs.map((item) => `
      <article class="travel-stage-card" style="border-top-color:${toneColor(item.tone)}">
        <span class="eyebrow">${item.index}</span>
        ${badge(t(`screens.travel.stages.${item.id}.status`), item.tone)}
        <strong>${t(`screens.travel.stages.${item.id}.label`)}</strong>
        <span class="helper">${t(`screens.travel.stages.${item.id}.detail`)}</span>
      </article>
    `).join("")}</div>
    <div class="travel-review-grid">
      <article class="detail-item"><span class="helper">${t("screens.travel.review.ongoing.label")}</span><strong>${t("screens.travel.review.ongoing.value")}</strong><span>${t("screens.travel.review.ongoing.detail")}</span></article>
      <article class="detail-item"><span class="helper">${t("screens.travel.review.completed.label")}</span><strong>${t("screens.travel.review.completed.value")}</strong><span>${t("screens.travel.review.completed.detail")}</span></article>
    </div>
  </section>`;
}

function attendancePhonePanel() {
  return `<section class="card">
    ${sectionHead("", t("screens.attendance.title"), t("screens.attendance.description"))}
    <div class="attendance-grid">
      <div class="phone-frame">
        <div class="phone-head"><span class="helper">${t("screens.attendance.phone.todayStatus")}</span>${badge(t("screens.attendance.phone.checkedIn"), "ready")}</div>
        <div class="phone-clock"><strong>09:02</strong><span class="helper">${t("screens.attendance.phone.location")}</span></div>
        <div class="punch-actions"><button class="punch primary">${t("screens.attendance.phone.checkIn")}</button><button class="punch secondary">${t("screens.attendance.phone.checkOut")}</button></div>
        <div class="location-notice"><strong>${t("screens.attendance.locationNotice.title")}</strong><span class="helper">${t("screens.attendance.locationNotice.description")}</span></div>
      </div>
      <div class="attendance-side">
        <div class="detail-item"><span class="helper">${t("screens.attendance.manager.label")}</span><strong>${t("screens.attendance.manager.value")}</strong><span>${t("screens.attendance.manager.detail")}</span></div>
        <div class="planner-list">${attendanceLogDefs.map((item) => `
          <div class="planner-item">${badge(t(`screens.attendance.logs.${item.id}.label`), item.tone)}<div><strong>${item.time}</strong><span class="helper">${t(`screens.attendance.logs.${item.id}.place`)}</span></div></div>
        `).join("")}</div>
      </div>
    </div>
  </section>`;
}

function metrics(items) {
  return `<div class="metric-grid">${items.map((item) => `
    <article class="metric-card" style="border-left-color:${toneColor(item.tone)}">
      <span class="helper">${item.label}</span>
      <strong class="metric-value" style="color:${toneColor(item.tone)}">${item.value}</strong>
      <span>${item.helper}</span>
    </article>
  `).join("")}</div>`;
}

function table(rows, selectable = false) {
  if (!rows.length) return empty(t("table.empty.title"), t("table.empty.description"));
  return `<div class="table">
    <div class="table-row header"><span>${t("table.columns.category")}</span><span>${t("table.columns.status")}</span><span>${t("table.columns.owner")}</span><span>${t("table.columns.nextStep")}</span></div>
    ${rows.map((row) => {
      const content = `<span><strong>${row.category}</strong></span><span>${badge(row.status, row.tone)}</span><span>${row.owner}</span><span>${row.next}</span>`;
      return selectable ? `
      <button class="table-row row-button ${state.selectedRowKey === row.id ? "selected" : ""}" data-row-key="${row.id}">
        ${content}
      </button>
    ` : `
      <div class="table-row">
        ${content}
      </div>
    `;
    }).join("")}
  </div>`;
}

function workDetail(row) {
  return `<div class="detail-panel">
    <div class="detail-head"><div><span class="helper">${t("screens.workDetail.selectedLabel")}</span><strong>${escapeText(row.category)}</strong></div>${badge(row.status, row.tone)}</div>
    <div class="detail-grid">
      <div class="detail-item"><span class="helper">${t("screens.workDetail.owner")}</span><strong>${escapeText(row.owner)}</strong></div>
      <div class="detail-item"><span class="helper">${t("screens.workDetail.nextStep")}</span><span>${escapeText(row.next)}</span></div>
    </div>
    <div class="action-row">${button(t("screens.workDetail.actions.openRelated"), row.target, "secondary")}${button(t("screens.workDetail.actions.confirmOwner"), state.activeId, "ghost")}</div>
  </div>`;
}

function filterRows(rows) {
  const query = state.search.trim().toLowerCase();
  return rows.filter((row) => {
    const filterMatch = state.filter === "all" || row.filters.includes(state.filter);
    const haystack = [row.category, row.status, row.owner, row.next].join(" ").toLowerCase();
    const queryMatch = !query || haystack.includes(query);
    return filterMatch && queryMatch;
  });
}

function empty(title, desc) {
  return `<div class="empty"><strong>${title}</strong><span class="helper">${desc}</span></div>`;
}

function toneColor(tone) {
  return {
    ready: "#047857",
    attention: "#B45309",
    blocked: "#B91C1C",
    neutral: "#667085"
  }[tone] || "#667085";
}

function bindEvents() {
  document.querySelectorAll("[data-target]").forEach((el) => {
    el.addEventListener("click", () => {
      state.authed = true;
      state.activeId = el.dataset.target;
      state.filter = "all";
      state.search = "";
      state.selectedRowKey = "";
      state.selectedPayrollCardKey = "";
      state.selectedPayrollStepKey = "";
      state.selectedQueueKey = "";
      state.loginFeedbackKey = "";
      render();
      const label = navigationItems().find((item) => item.id === state.activeId)?.label || t("screens.module.unavailable.title");
      toast(t("preview.toast.screenChanged", { screen: label }));
    });
  });

  document.querySelectorAll("[data-filter]").forEach((el) => {
    el.addEventListener("click", () => {
      state.filter = el.dataset.filter;
      state.selectedRowKey = "";
      render();
      const activeModule = moduleData(state.activeId);
      const filterLabel = activeModule?.filters.find((filter) => filter.id === state.filter)?.label || t("screens.filters.all");
      toast(t("preview.toast.filterSelected", { filter: filterLabel }));
    });
  });

  document.querySelectorAll("[data-row-key]").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedRowKey = el.dataset.rowKey;
      render();
      toast(t("preview.toast.workDetailOpened"));
    });
  });

  document.querySelectorAll("[data-sidebar-theme]").forEach((el) => {
    el.addEventListener("click", () => {
      state.sidebarTheme = el.dataset.sidebarTheme || "steel";
      render();
      toast(t("preview.toast.sidebarThemeApplied"));
    });
  });

  document.querySelectorAll("[data-language]").forEach((el) => {
    el.addEventListener("click", () => {
      state.locale = supportedLocales.includes(el.dataset.language) ? el.dataset.language : "ko-KR";
      state.filter = "all";
      render();
      toast(t("preview.toast.languageSelected"));
    });
  });

  document.querySelectorAll("[data-payroll-card-key]").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedPayrollCardKey = el.dataset.payrollCardKey;
      render();
      toast(t("preview.toast.payrollReadinessSelected"));
    });
  });

  document.querySelectorAll("[data-payroll-step-key]").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedPayrollStepKey = el.dataset.payrollStepKey;
      render();
      toast(t("preview.toast.payrollStepSelected"));
    });
  });

  document.querySelectorAll("[data-queue-key]").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedQueueKey = el.dataset.queueKey;
      render();
      toast(t("preview.toast.queueDetailOpened"));
    });
  });

  document.querySelectorAll("[data-logout]").forEach((el) => {
    el.addEventListener("click", () => {
      state.authed = false;
      state.activeId = "home";
      state.filter = "all";
      state.loginFeedbackKey = "";
      state.password = "";
      state.selectedPayrollCardKey = "";
      state.selectedPayrollStepKey = "";
      state.selectedQueueKey = "";
      state.search = "";
      state.selectedRowKey = "";
      render();
      toast(t("preview.toast.logout"));
    });
  });

  document.querySelectorAll("[data-demo-login]").forEach((el) => {
    el.addEventListener("click", () => {
      state.companyCode = demoAccount.companyCode;
      state.userId = demoAccount.userId;
      state.password = demoAccount.password;
      state.loginFeedbackKey = "";
      state.authed = true;
      state.activeId = "home";
      state.filter = "all";
      state.search = "";
      state.selectedPayrollCardKey = "";
      state.selectedPayrollStepKey = "";
      state.selectedQueueKey = "";
      state.selectedRowKey = "";
      render();
      toast(t("preview.toast.demoLogin"));
    });
  });

  const search = document.getElementById("work-search");
  if (search) {
    search.addEventListener("input", (event) => {
      const cursor = event.target.selectionStart;
      state.search = event.target.value;
      state.selectedRowKey = "";
      render();
      window.requestAnimationFrame(() => {
        const nextSearch = document.getElementById("work-search");
        if (nextSearch) {
          nextSearch.focus();
          nextSearch.setSelectionRange(cursor, cursor);
        }
      });
    });
  }

  const companyCode = document.getElementById("company-code");
  if (companyCode) {
    companyCode.addEventListener("input", (event) => {
      state.companyCode = event.target.value;
    });
  }

  const userId = document.getElementById("user-id");
  if (userId) {
    userId.addEventListener("input", (event) => {
      state.userId = event.target.value;
    });
  }

  const password = document.getElementById("password");
  if (password) {
    password.addEventListener("input", (event) => {
      state.password = event.target.value;
    });
  }

  const form = document.getElementById("login-form");
  if (form) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      state.companyCode = document.getElementById("company-code")?.value.trim() || "";
      state.userId = document.getElementById("user-id")?.value.trim() || "";
      state.password = document.getElementById("password")?.value.trim() || "";
      if (!state.companyCode || !state.userId || !state.password) {
        state.loginFeedbackKey = "screens.login.feedback.missingDemo";
        render();
        toast(t("preview.toast.checkLogin"));
        return;
      }
      if (
        state.companyCode !== demoAccount.companyCode ||
        state.userId !== demoAccount.userId ||
        state.password !== demoAccount.password
      ) {
        state.loginFeedbackKey = "screens.login.feedback.invalidDemo";
        render();
        toast(t("preview.toast.checkLogin"));
        return;
      }
      state.loginFeedbackKey = "";
      state.authed = true;
      state.activeId = "home";
      render();
      toast(t("preview.toast.home"));
    });
  }
}

function toast(text) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = text;
  el.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => el.classList.remove("show"), 1400);
}

if ("EventSource" in window) {
  const source = new EventSource("/events");
  source.addEventListener("reload", () => window.location.reload());
}

boot().catch((error) => {
  console.error(error);
  document.getElementById("app").innerHTML = `<pre>${escapeText(error.message)}</pre>`;
});
