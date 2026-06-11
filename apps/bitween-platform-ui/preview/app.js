const tones = {
  ready: "tone-ready",
  attention: "tone-attention",
  blocked: "tone-blocked",
  neutral: "tone-neutral"
};

const palette = {
  accent: "var(--accent)",
  approval: "var(--palette-blue)",
  archive: "var(--palette-slate-strong)",
  danger: "var(--danger)",
  home: "var(--palette-slate)",
  hr: "var(--palette-teal-strong)",
  muted: "var(--muted)",
  success: "var(--success)",
  teal: "var(--palette-teal)",
  warning: "var(--warning)",
  workflow: "var(--palette-purple)"
};

const liveNavigationFallback = ["home", "hr", "payroll", "workflow", "approval", "archive", "admin"];
const companyLogoUri =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%231F3864'/%3E%3Cpath d='M18 18h18c7 0 11 4 11 9 0 4-2 7-6 8 5 1 8 5 8 10 0 6-5 10-13 10H18V18zm11 14h6c3 0 5-1 5-4s-2-4-5-4h-6v8zm0 17h7c4 0 6-2 6-5s-2-5-6-5h-7v10z' fill='white'/%3E%3C/svg%3E";

const navDefs = [
  ["home", palette.home],
  ["hr", palette.hr],
  ["payroll", palette.accent],
  ["workflow", palette.workflow],
  ["approval", palette.approval],
  ["archive", palette.archive],
  ["admin", palette.warning]
].map(([id, accent]) => ({ id, accent }));

const sidebarThemeIds = ["steel", "graphite", "teal", "navy"];
const supportedLocales = ["ko-KR", "en-US", "zh-Hans-CN", "ja-JP"];
const visibleLocaleIds = ["ko-KR"];
const defaultPreferences = {
  locale: "ko-KR",
  notification_digest: "role_work",
  payroll_standard_view: "before_run",
  sidebar_theme: "steel",
  workspace_density: "work_dense"
};
const authEndpoints = {
  onboarding: "/api/onboarding/v1/start",
  signin: "/api/auth/v1/signin",
  signout: "/api/auth/v1/signout",
  signup: "/api/auth/v1/signup"
};

const state = {
  activeId: "home",
  archiveError: undefined,
  archiveIntakes: [],
  authRoutes: undefined,
  authed: false,
  catalog: undefined,
  hrEmployees: [],
  hrError: undefined,
  liveError: undefined,
  liveView: undefined,
  locale: "ko-KR",
  payrollReconciliation: undefined,
  payrollReconciliationError: undefined,
  profileMenuOpen: false,
  selectedEmployeeId: "",
  selectedAdminKey: "",
  selectedWorkStepKey: "",
  settingsError: undefined,
  sidebarTheme: defaultPreferences.sidebar_theme,
  topbarPanel: "",
  tutorialOpen: false,
  tutorialStepIndex: 0,
  userPreferences: { ...defaultPreferences },
  workflowAuditEvents: [],
  workflowAnalytics: [],
  workflowConnectFromId: "",
  workflowDataRecords: [],
  workflowDragSuppressId: "",
  workflowEditValidationError: undefined,
  workflowEditValidationReports: [],
  workflowError: undefined,
  workflowPreflightError: undefined,
  workflowPreflightReports: [],
  workflowRuntimeEvents: [],
  workflowTemplates: [],
  workflowTemplateVersions: []
};

async function boot() {
  const [catalogResponse, liveResponse, hrResponse, archiveResponse, preferencesResponse, authRoutesResponse, workflowResponse] = await Promise.all([
    fetch("/catalog.json"),
    fetch("/api/platform/v1/view-model"),
    fetch("/api/hr/v1/employees"),
    fetch("/api/archive/v1/intake"),
    fetch("/api/settings/v1/preferences"),
    fetch("/api/auth/v1/routes"),
    fetch("/api/workflow/v1/templates")
  ]);
  state.catalog = await catalogResponse.json();
  if (liveResponse.ok) {
    state.liveView = await liveResponse.json();
    state.liveError = undefined;
  } else {
    state.liveView = undefined;
    state.liveError = await liveResponse.json().catch(() => ({
      error: "live_view_unavailable",
      detail: t("preview.live.unavailable")
    }));
  }
  syncSessionFromLive();
  await applyHrResponse(hrResponse);
  await applyArchiveResponse(archiveResponse);
  await applyPreferenceResponse(preferencesResponse);
  await applyAuthRoutesResponse(authRoutesResponse);
  await applyWorkflowResponse(workflowResponse);
  await loadPayrollReconciliation();
  document.title = t("preview.documentTitle");
  render();
}

async function refreshLiveView() {
  try {
    const response = await fetch("/api/platform/v1/view-model");
    if (!response.ok) {
      throw await response.json().catch(() => ({
        detail: t("preview.live.unavailable")
      }));
    }
    state.liveView = await response.json();
    state.liveError = undefined;
    syncSessionFromLive();
  } catch (error) {
    state.liveView = undefined;
    state.liveError = {
      error: "live_view_unavailable",
      detail: error?.detail || error?.message || t("preview.live.unavailable")
    };
    syncSessionFromLive();
  }
  await loadHrEmployees();
  await loadArchiveIntakes();
  await loadUserPreferences();
  await loadAuthRoutes();
  await loadWorkflowTemplates();
  await loadPayrollReconciliation();
  render();
}

function syncSessionFromLive() {
  state.authed = Boolean(state.liveView?.session?.authenticated);
}

async function loadHrEmployees() {
  const response = await fetch("/api/hr/v1/employees");
  await applyHrResponse(response);
}

async function applyHrResponse(response) {
  if (response.ok) {
    const store = await response.json();
    state.hrEmployees = store.employees || [];
    state.hrError = undefined;
    if (!state.selectedEmployeeId && state.hrEmployees[0]) {
      state.selectedEmployeeId = state.hrEmployees[0].id;
    }
  } else {
    state.hrEmployees = [];
    state.hrError = await response.json().catch(() => ({
      detail: t("preview.hr.toast.failed")
    }));
  }
}

async function loadArchiveIntakes() {
  const response = await fetch("/api/archive/v1/intake");
  await applyArchiveResponse(response);
}

function payrollReconciliationPeriod() {
  return state.liveView?.payroll?.scope?.period || "";
}

async function loadPayrollReconciliation() {
  const period = payrollReconciliationPeriod();
  if (!period) {
    state.payrollReconciliation = undefined;
    state.payrollReconciliationError = undefined;
    return;
  }
  const response = await fetch(`/api/payroll/v1/run?period=${encodeURIComponent(period)}`);
  await applyPayrollReconciliationResponse(response);
}

async function applyPayrollReconciliationResponse(response) {
  if (response.ok) {
    state.payrollReconciliation = await response.json();
    state.payrollReconciliationError = undefined;
  } else {
    state.payrollReconciliation = undefined;
    state.payrollReconciliationError = await response.json().catch(() => ({
      detail: t("preview.payroll.reconciliation.failed")
    }));
  }
}

async function loadUserPreferences() {
  const response = await fetch("/api/settings/v1/preferences");
  await applyPreferenceResponse(response);
}

async function loadAuthRoutes() {
  const response = await fetch("/api/auth/v1/routes");
  await applyAuthRoutesResponse(response);
}

async function loadWorkflowTemplates() {
  const response = await fetch("/api/workflow/v1/templates");
  await applyWorkflowResponse(response);
}

async function applyAuthRoutesResponse(response) {
  if (response.ok) {
    state.authRoutes = await response.json();
  } else {
    state.authRoutes = {
      configured: false,
      missing: Object.keys(authEndpoints),
      routes: {}
    };
  }
}

async function applyArchiveResponse(response) {
  if (response.ok) {
    const store = await response.json();
    state.archiveIntakes = store.intakes || [];
    state.archiveError = undefined;
  } else {
    state.archiveIntakes = [];
    state.archiveError = await response.json().catch(() => ({
      detail: t("preview.archive.intake.failed")
    }));
  }
}

async function applyArchiveMutationResponse(response, fallbackDetailKey = "preview.archive.intake.failed") {
  if (response.ok) {
    await applyArchiveResponse(response);
    return true;
  }
  state.archiveError = await response.json().catch(() => ({
    detail: t(fallbackDetailKey)
  }));
  return false;
}

async function applyWorkflowResponse(response) {
  if (response.ok) {
    const store = await response.json();
    state.workflowTemplates = store.templates || [];
    state.workflowAuditEvents = store.audit_events || [];
    state.workflowRuntimeEvents = store.runtime_events || [];
    state.workflowDataRecords = store.data_records || [];
    state.workflowAnalytics = store.analytics || [];
    state.workflowTemplateVersions = store.template_versions || [];
    state.workflowError = undefined;
  } else {
    state.workflowTemplates = [];
    state.workflowAuditEvents = [];
    state.workflowRuntimeEvents = [];
    state.workflowDataRecords = [];
    state.workflowAnalytics = [];
    state.workflowTemplateVersions = [];
    state.workflowError = await response.json().catch(() => ({
      detail: t("preview.workflow.store.failed")
    }));
  }
}

async function applyPreferenceResponse(response) {
  if (response.ok) {
    const store = await response.json();
    applyUserPreferences(store.current || {});
    state.settingsError = undefined;
  } else {
    state.settingsError = await response.json().catch(() => ({
      detail: t("preview.settings.preferences.failed")
    }));
  }
}

function applyUserPreferences(preferences) {
  state.userPreferences = {
    ...defaultPreferences,
    ...preferences
  };
  state.sidebarTheme = sidebarThemeIds.includes(state.userPreferences.sidebar_theme)
    ? state.userPreferences.sidebar_theme
    : defaultPreferences.sidebar_theme;
  state.locale = visibleLocaleIds.includes(state.userPreferences.locale)
    ? state.userPreferences.locale
    : defaultPreferences.locale;
}

async function addArchiveIntake(file) {
  const body = new FormData();
  body.append("file", file, file.name);
  const response = await fetch("/api/archive/v1/intake", {
    method: "POST",
    body
  });
  const ok = await applyArchiveMutationResponse(response, "preview.archive.intake.failed");
  render();
  if (!ok) {
    toast(t("preview.archive.intake.failed"));
    return;
  }
  toast(t("preview.archive.intake.toast"));
}

async function resolveArchiveIssue({ intakeId, issueType, code, column }) {
  if (!intakeId || !issueType || !code) return;
  const response = await fetch(`/api/archive/v1/intake/${encodeURIComponent(intakeId)}/issues`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      issue_type: issueType,
      code,
      column: column || "",
      decision: "confirmed_by_operator"
    })
  });
  const ok = await applyArchiveMutationResponse(response, "preview.archive.intake.issue.failed");
  render();
  if (!ok) {
    toast(t("preview.archive.intake.issue.failed"));
    return;
  }
  toast(t("preview.archive.intake.issue.resolved"));
}

async function updateArchiveFieldMappings(intakeId, form) {
  const intake = state.archiveIntakes.find((item) => item.id === intakeId);
  if (!intake || !form) return;
  const mappings = Array.from(form.querySelectorAll("[data-field-mapping-row]")).map((row) => {
    const targetField = row.querySelector("[data-field-target]")?.value || "source_payload";
    return {
      sourceColumn: row.dataset.sourceColumn || "",
      targetTable: intake.database_target,
      targetField,
      status: targetField === "ignored" ? "ignored" : "confirmed",
      ignoreReason: targetField === "ignored" ? "operator_excluded_column" : null
    };
  }).filter((mapping) => mapping.sourceColumn);
  const response = await fetch(`/api/archive/v1/intake/${encodeURIComponent(intakeId)}/field-mappings`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      sourceFingerprint: intake.source_fingerprint,
      mappings
    })
  });
  const ok = await applyArchiveMutationResponse(response, "preview.archive.intake.mapping.failed");
  render();
  if (!ok) {
    toast(t("preview.archive.intake.mapping.failed"));
    return;
  }
  toast(t("preview.archive.intake.mapping.saved"));
}

async function admitArchiveIntake(intakeId) {
  if (!intakeId) return;
  const response = await fetch(`/api/archive/v1/intake/${encodeURIComponent(intakeId)}/admissions`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{}"
  });
  const ok = await applyArchiveMutationResponse(response, "preview.archive.intake.admission.failed");
  render();
  if (!ok) {
    toast(t("preview.archive.intake.admission.failed"));
    return;
  }
  toast(t("preview.archive.intake.admission.saved"));
}

async function rollbackArchiveIntake(intakeId, recoveryPointId = "") {
  if (!intakeId) return;
  const response = await fetch(`/api/archive/v1/intake/${encodeURIComponent(intakeId)}/rollbacks`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      reason: recoveryPointId ? "selected_recovery_point" : "operator_requested",
      recovery_point_id: recoveryPointId || undefined
    })
  });
  const ok = await applyArchiveMutationResponse(response, "preview.archive.intake.rollback.failed");
  render();
  if (!ok) {
    toast(t("preview.archive.intake.rollback.failed"));
    return;
  }
  toast(t("preview.archive.intake.rollback.saved"));
}

async function syncArchiveSource(intakeId) {
  if (!intakeId) return;
  const response = await fetch(`/api/archive/v1/intake/${encodeURIComponent(intakeId)}/source-syncs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{}"
  });
  const ok = await applyArchiveMutationResponse(response, "preview.archive.intake.version.syncFailed");
  render();
  if (!ok) {
    toast(t("preview.archive.intake.version.syncFailed"));
    return;
  }
  toast(t("preview.archive.intake.version.syncSaved"));
}

async function mutateUserPreferences(patch) {
  const nextPreferences = {
    ...state.userPreferences,
    ...patch
  };
  const response = await fetch("/api/settings/v1/preferences", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(nextPreferences)
  });
  await applyPreferenceResponse(response);
  render();
  if (!response.ok) {
    toast(t("preview.settings.preferences.failed"));
    return;
  }
  toast(t("preview.settings.preferences.saved"));
}

async function mutateWorkflowStepStatus(templateId, stepId, status) {
  return mutateWorkflowStep(templateId, stepId, { status });
}

async function persistWorkflowStep(templateId, stepId, patch) {
  const response = await fetch(`/api/workflow/v1/templates/${encodeURIComponent(templateId)}/steps/${encodeURIComponent(stepId)}`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      actor_role: state.liveView?.session?.role || "platform_owner",
      ...patch
    })
  });
  await applyWorkflowResponse(response);
  return response;
}

async function validateWorkflowStepEdit(templateId, stepId, patch) {
  const response = await fetch(`/api/workflow/v1/templates/${encodeURIComponent(templateId)}/steps/${encodeURIComponent(stepId)}/validations`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      actor_role: state.liveView?.session?.role || "platform_owner",
      ...patch
    })
  });
  if (response.ok) {
    const report = await response.json();
    state.workflowEditValidationReports = [
      report,
      ...state.workflowEditValidationReports.filter((item) => !(item.template_id === report.template_id && item.step_id === report.step_id))
    ];
    state.workflowEditValidationError = undefined;
    return report;
  }
  state.workflowEditValidationError = await response.json().catch(() => ({
    detail: t("preview.workflow.validation.failed")
  }));
  return undefined;
}

async function mutateWorkflowStep(templateId, stepId, patch) {
  const response = await persistWorkflowStep(templateId, stepId, patch);
  render();
  if (!response.ok) {
    toast(state.workflowError?.detail || t("preview.workflow.store.failed"));
    return;
  }
  toast(t("preview.workflow.store.saved"));
}

async function connectWorkflowSteps(templateId, fromStepId, toStepId) {
  if (!fromStepId || !toStepId) return;
  if (fromStepId === toStepId) {
    state.workflowConnectFromId = "";
    render();
    toast(t("preview.workflow.connect.self"));
    return;
  }
  const fromNode = workflowTemplateNodes().find((node) => node.id === fromStepId);
  if (!fromNode) {
    state.workflowConnectFromId = "";
    render();
    toast(t("preview.workflow.store.failed"));
    return;
  }
  const nextStepIds = Array.from(new Set([...(fromNode.nextStepIds || []), toStepId]));
  if ((fromNode.nextStepIds || []).includes(toStepId)) {
    state.workflowConnectFromId = "";
    render();
    toast(t("preview.workflow.connect.exists"));
    return;
  }
  state.workflowConnectFromId = "";
  const validation = await validateWorkflowStepEdit(templateId, fromStepId, { next_step_ids: nextStepIds });
  if (!validation || validation.status === "blocked" || validation.would_persist === false) {
    render();
    toast(state.workflowEditValidationError?.detail || t("preview.workflow.validation.blocked"));
    return;
  }
  const response = await persistWorkflowStep(templateId, fromStepId, { next_step_ids: nextStepIds });
  render();
  if (!response.ok) {
    toast(state.workflowError?.detail || t("preview.workflow.store.failed"));
    return;
  }
  toast(t("preview.workflow.connect.saved"));
}

async function disconnectWorkflowSteps(templateId, fromStepId, toStepId) {
  const fromNode = workflowTemplateNodes().find((node) => node.id === fromStepId);
  if (!fromNode) return;
  const nextStepIds = (fromNode.nextStepIds || []).filter((id) => id !== toStepId);
  const validation = await validateWorkflowStepEdit(templateId, fromStepId, { next_step_ids: nextStepIds });
  if (!validation || validation.status === "blocked" || validation.would_persist === false) {
    render();
    toast(state.workflowEditValidationError?.detail || t("preview.workflow.validation.blocked"));
    return;
  }
  const response = await persistWorkflowStep(templateId, fromStepId, { next_step_ids: nextStepIds });
  render();
  if (!response.ok) {
    toast(state.workflowError?.detail || t("preview.workflow.store.failed"));
    return;
  }
  toast(t("preview.workflow.connect.removed"));
}

async function addWorkflowStep(templateId, input) {
  const response = await fetch(`/api/workflow/v1/templates/${encodeURIComponent(templateId)}/steps`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      actor_role: state.liveView?.session?.role || "platform_owner",
      ...input
    })
  });
  await applyWorkflowResponse(response);
  render();
  if (!response.ok) {
    toast(state.workflowError?.detail || t("preview.workflow.store.failed"));
    return;
  }
  toast(t("preview.workflow.store.saved"));
}

async function deleteWorkflowStep(templateId, stepId) {
  const response = await fetch(`/api/workflow/v1/templates/${encodeURIComponent(templateId)}/steps/${encodeURIComponent(stepId)}`, {
    method: "DELETE",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      actor_role: state.liveView?.session?.role || "platform_owner"
    })
  });
  await applyWorkflowResponse(response);
  state.selectedWorkStepKey = workflowTemplateNodes()[0]?.id || "";
  render();
  if (!response.ok) {
    toast(state.workflowError?.detail || t("preview.workflow.store.failed"));
    return;
  }
  toast(t("preview.workflow.store.saved"));
}

async function executeWorkflowStep(templateId, stepId) {
  const scope = state.liveView?.payroll?.scope || {};
  const response = await fetch(`/api/workflow/v1/templates/${encodeURIComponent(templateId)}/steps/${encodeURIComponent(stepId)}/executions`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      actor_role: state.liveView?.session?.role || "platform_owner",
      scope_tenant: scope.tenant_name || "",
      scope_workplace: scope.workplace || "",
      scope_period: scope.period || ""
    })
  });
  await applyWorkflowResponse(response);
  render();
  if (!response.ok) {
    toast(state.workflowError?.detail || t("preview.workflow.store.failed"));
    return;
  }
  toast(t("preview.workflow.execute.saved"));
}

async function rollbackWorkflowTemplate(templateId, version) {
  const response = await fetch(`/api/workflow/v1/templates/${encodeURIComponent(templateId)}/rollbacks`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      actor_role: state.liveView?.session?.role || "platform_owner",
      version: Number(version)
    })
  });
  await applyWorkflowResponse(response);
  state.selectedWorkStepKey = workflowTemplateNodes()[0]?.id || "";
  render();
  if (!response.ok) {
    toast(state.workflowError?.detail || t("preview.workflow.store.failed"));
    return;
  }
  toast(t("preview.workflow.rollback.saved"));
}

async function preflightWorkflowTemplate(templateId) {
  const scope = state.liveView?.payroll?.scope || {};
  const response = await fetch(`/api/workflow/v1/templates/${encodeURIComponent(templateId)}/preflights`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      actor_role: state.liveView?.session?.role || "platform_owner",
      scope_tenant: scope.tenant_name || "",
      scope_workplace: scope.workplace || "",
      scope_period: scope.period || ""
    })
  });
  if (response.ok) {
    const report = await response.json();
    state.workflowPreflightReports = [
      report,
      ...state.workflowPreflightReports.filter((item) => item.template_id !== report.template_id)
    ];
    state.workflowPreflightError = undefined;
  } else {
    state.workflowPreflightError = await response.json().catch(() => ({
      detail: t("preview.workflow.preflight.failed")
    }));
  }
  render();
  if (!response.ok) {
    toast(state.workflowPreflightError?.detail || t("preview.workflow.preflight.failed"));
    return;
  }
  toast(t("preview.workflow.preflight.saved"));
}

async function moveWorkflowStep(templateId, stepId, x, y) {
  const positionX = clampWorkflowPercent(x);
  const positionY = clampWorkflowPercent(y);
  await mutateWorkflowStep(templateId, stepId, {
    position_x: positionX,
    position_y: positionY,
    lane: workflowLaneFromPositionX(positionX)
  });
}

async function autoLayoutWorkflow(templateId) {
  const laneRows = new Map();
  const nodes = workflowTemplateNodes().map((node) => {
    const lane = node.lane || workflowLaneFromPositionX(node.positionX);
    const row = laneRows.get(lane) || 0;
    laneRows.set(lane, row + 1);
    return {
      ...node,
      positionX: workflowLanePositionX(lane),
      positionY: clampWorkflowPercent(16 + row * 14)
    };
  });
  for (const node of nodes) {
    const response = await persistWorkflowStep(templateId, node.id, {
      lane: node.lane,
      position_x: node.positionX,
      position_y: node.positionY
    });
    if (!response.ok) {
      render();
      toast(state.workflowError?.detail || t("preview.workflow.store.failed"));
      return;
    }
  }
  render();
  toast(t("preview.workflow.layout.saved"));
}

async function addWorkflowPaletteStep(templateId, kind, afterStepId) {
  const input = workflowPaletteInput(kind, afterStepId);
  if (!input) return;
  await addWorkflowStep(templateId, input);
}

async function startAuthFlow(action) {
  const endpoint = authEndpoints[action];
  if (!endpoint) return;
  if (!authRouteConfigured(action)) {
    toast(t("preview.auth.actionUnavailable"));
    return;
  }
  const response = await fetch(endpoint, {
    method: action === "signout" ? "POST" : "GET"
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.url) {
    await loadAuthRoutes();
    render();
    toast(t("preview.auth.actionUnavailable"));
    return;
  }
  toast(t("preview.auth.opening"));
  window.location.assign(payload.url);
}

function authRouteConfigured(action) {
  return Boolean(state.authRoutes?.routes?.[action]?.configured);
}

function authButton(action, variant, labelKey) {
  const disabled = !authRouteConfigured(action);
  return `<button class="btn ${variant}" ${disabled ? "disabled aria-disabled=\"true\"" : `data-auth-action="${action}"`}>${t(labelKey)}</button>`;
}

async function mutateHrEmployee(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: body ? { "content-type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });
  await applyHrResponse(response);
  render();
  if (!response.ok) {
    toast(state.hrError?.detail || t("preview.hr.toast.failed"));
    return;
  }
  toast(t("preview.hr.toast.saved"));
}

function t(key, params = {}) {
  const message = state.catalog?.messages?.find((row) => row.key === key);
  const template = message?.values?.[state.locale];
  if (!template) {
    throw new Error(`Missing i18n message ${key} for ${state.locale}`);
  }
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, name) => String(params[name] ?? match));
}

function messageExists(key) {
  return Boolean(state.catalog?.messages?.some((row) => row.key === key));
}

function catalogText(key, defaultText) {
  return messageExists(key) ? t(key) : defaultText;
}

function catalogId(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function statusText(value) {
  return catalogText(`preview.status.${catalogId(value)}`, value);
}

function ownerText(value) {
  return catalogText(`preview.owner.${catalogId(value)}`, value);
}

function workTitle(item) {
  return catalogText(`preview.work.${item.id}.title`, t("preview.work.default.title"));
}

function workNextStep(item) {
  return catalogText(`preview.work.${item.id}.next`, t("preview.work.default.next"));
}

function stepTitle(step) {
  if (step.title) return step.title;
  return catalogText(`preview.payrollWork.${step.id}.title`, step.id);
}

function stepAction(step) {
  if (step.action && !messageExists(`preview.payrollWork.${step.id}.action`)) return step.action;
  return catalogText(`preview.payrollWork.${step.id}.action`, step.action || step.id);
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

function settingsItem() {
  return {
    accent: palette.teal,
    description: t("navigation.settings.description"),
    eyebrow: t("navigation.settings.eyebrow"),
    id: "settings",
    label: t("navigation.settings.label")
  };
}

function activeItem(items) {
  if (state.activeId === "settings") return settingsItem();
  return items.find((item) => item.id === state.activeId) || items[0];
}

function selectedAccount() {
  const session = state.liveView?.session || {};
  const navigationIds = state.liveView?.navigation
    ?.map((item) => item.id)
    .filter((id) => navDefs.some((nav) => nav.id === id));
  const tenantConfigured = session.tenant_id && session.tenant_id !== "unconfigured";
  const tenantNameConfigured = session.tenant_name && !/not configured|unconfigured/i.test(session.tenant_name);
  return {
    companyCode: tenantConfigured ? session.tenant_id : "tenant-acme",
    defaultRoute: "home",
    displayName: t("preview.profile.displayName"),
    id: "liveOperations",
    navigationIds: navigationIds?.length ? navigationIds : liveNavigationFallback,
    tenantName: tenantNameConfigured ? session.tenant_name : t("preview.profile.defaultTenantName"),
    userId: "live-user"
  };
}

function visibleNavigationItems() {
  const account = selectedAccount();
  return navigationItems().filter((item) => account.navigationIds.includes(item.id));
}

function sidebarThemes() {
  return sidebarThemeIds.map((id) => ({
    id,
    description: t(`sidebarThemes.${id}.description`),
    label: t(`sidebarThemes.${id}.label`)
  }));
}

function workQueue() {
  const items = state.liveView?.work_queue || [];
  if (items.length === 0 && state.liveError) {
    return [{
      due: t("preview.queue.due.now"),
      id: "live-unavailable",
      meta: t("preview.queue.source.unavailable"),
      owner: t("preview.queue.engineering"),
      status: t("preview.status.blocked"),
      target: "admin",
      title: t("preview.queue.source.unavailable"),
      tone: "blocked"
    }];
  }
  return items.map((item) => ({
    due: t("preview.queue.due.now"),
    id: item.id,
    meta: workNextStep(item),
    owner: ownerText(item.owner),
    status: statusText(item.status),
    target: item.target,
    title: workTitle(item),
    tone: item.tone
  }));
}

function liveQueueStepItems() {
  return workQueue().map((item) => ({
    action: item.meta,
    id: `queue-${item.id}`,
    owner: item.owner,
    status: item.tone === "blocked" ? "blocked" : item.tone === "attention" ? "ready" : "waiting",
    target: item.target,
    title: item.title,
    tone: item.tone
  }));
}

function payrollWorkstream() {
  const workstream = state.liveView?.payroll?.workstream;
  if (workstream?.steps?.length) {
    return workstream;
  }
  return {
    current_step_id: "connect-live-view",
    period_label: t("preview.home.scopeMissing"),
    status: "blocked",
    tone: "blocked",
    steps: [{
      action: "connect-live-view",
      id: "connect-live-view",
      owner: "payroll-admin",
      status: "blocked",
      target: "admin",
      tone: "blocked"
    }]
  };
}

function workflowVisualOrder(left, right) {
  return (Number(left.positionY || 0) - Number(right.positionY || 0))
    || (Number(left.positionX || 0) - Number(right.positionX || 0))
    || String(left.id || "").localeCompare(String(right.id || ""));
}

function workflowOperationalSteps() {
  const nodes = workflowTemplateNodes();
  if (!nodes.length) return payrollWorkstream().steps;

  const byId = new Map(nodes.map((node) => [node.id, node]));
  const incoming = new Map(nodes.map((node) => [node.id, 0]));
  for (const node of nodes) {
    for (const nextId of node.nextStepIds || []) {
      if (incoming.has(nextId)) {
        incoming.set(nextId, incoming.get(nextId) + 1);
      }
    }
  }

  const ready = nodes
    .filter((node) => incoming.get(node.id) === 0)
    .sort(workflowVisualOrder);
  const ordered = [];
  const seen = new Set();

  while (ready.length) {
    const node = ready.shift();
    if (!node || seen.has(node.id)) continue;
    seen.add(node.id);
    ordered.push(node);

    for (const nextId of node.nextStepIds || []) {
      if (!incoming.has(nextId)) continue;
      incoming.set(nextId, Math.max(0, incoming.get(nextId) - 1));
      if (incoming.get(nextId) === 0 && byId.has(nextId)) {
        ready.push(byId.get(nextId));
        ready.sort(workflowVisualOrder);
      }
    }
  }

  const remaining = nodes
    .filter((node) => !seen.has(node.id))
    .sort(workflowVisualOrder);
  return [...ordered, ...remaining];
}

function editableWorkflowSteps() {
  return workflowOperationalSteps();
}

function workflowSteps(target) {
  const steps = editableWorkflowSteps();
  return target ? steps.filter((step) => step.target === target) : steps;
}

function currentWorkflowStep() {
  const steps = editableWorkflowSteps();
  return steps.find((step) => step.status !== "completed") || steps[steps.length - 1];
}

function selectedWorkflowStep(target) {
  const steps = workflowSteps(target);
  return steps.find((step) => step.id === state.selectedWorkStepKey) || steps[0] || currentWorkflowStep();
}

function homeWorkBuckets() {
  const steps = [...editableWorkflowSteps(), ...liveQueueStepItems()];
  const openSteps = steps.filter((step) => step.status !== "completed");
  const activeSteps = openSteps.filter((step) => step.status === "ready" || step.status === "blocked");
  const waitingSteps = openSteps.filter((step) => step.status === "waiting");
  const followUps = openSteps
    .filter((step) => step.tone === "blocked")
    .filter((step, index, rows) => rows.findIndex((row) => row.id === step.id) === index);
  const scheduleSteps = waitingSteps.filter((step) => ["hr", "payroll", "approval"].includes(step.target));
  const prepSteps = openSteps.filter((step) => ["payroll", "archive"].includes(step.target));

  return {
    today: activeSteps.length ? activeSteps.slice(0, 3) : openSteps.slice(0, 1),
    schedule: (scheduleSteps.length ? scheduleSteps : waitingSteps).slice(0, 4),
    followUps: followUps.slice(0, 3),
    prep: (prepSteps.length ? prepSteps : openSteps).slice(0, 4)
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

function escapeAttribute(value) {
  return escapeText(value);
}

function badge(text, tone = "neutral") {
  return `<span class="badge ${tones[tone] || tones.neutral}">${escapeText(text)}</span>`;
}

function button(label, target, variant = "secondary") {
  return `<button class="btn ${variant}" data-target="${target}">${escapeText(label)}</button>`;
}

function icon(name) {
  const lucidePaths = {
    "bell": "<path d=\"M10.268 21a2 2 0 0 0 3.464 0\"/><path d=\"M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326\"/>",
    "circle-help": "<circle cx=\"12\" cy=\"12\" r=\"10\"/><path d=\"M9.09 9a3 3 0 1 1 5.83 1c-.6 1.7-2.92 2-2.92 4\"/><path d=\"M12 17h.01\"/>",
    "message-circle": "<path d=\"M7.9 20A9 9 0 1 0 4 16.1L2 22Z\"/><path d=\"M8 12h.01\"/><path d=\"M12 12h.01\"/><path d=\"M16 12h.01\"/>",
    "building-2": "<path d=\"M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18\"/><path d=\"M6 12H4a2 2 0 0 0-2 2v8h20v-8a2 2 0 0 0-2-2h-2\"/><path d=\"M10 6h4\"/><path d=\"M10 10h4\"/><path d=\"M10 14h4\"/><path d=\"M10 18h4\"/>",
    "settings": "<path d=\"M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.32-1.915\"/><circle cx=\"12\" cy=\"12\" r=\"3\"/>",
    "user": "<path d=\"M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2\"/><circle cx=\"12\" cy=\"7\" r=\"4\"/>",
    "log-out": "<path d=\"m16 17 5-5-5-5\"/><path d=\"M21 12H9\"/><path d=\"M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4\"/>",
    "workflow": "<rect width=\"8\" height=\"8\" x=\"3\" y=\"3\" rx=\"2\"/><path d=\"M7 11v4a2 2 0 0 0 2 2h4\"/><rect width=\"8\" height=\"8\" x=\"13\" y=\"13\" rx=\"2\"/>",
    "git-branch": "<line x1=\"6\" x2=\"6\" y1=\"3\" y2=\"15\"/><circle cx=\"18\" cy=\"6\" r=\"3\"/><circle cx=\"6\" cy=\"18\" r=\"3\"/><path d=\"M18 9a9 9 0 0 1-9 9\"/>",
    "route": "<circle cx=\"6\" cy=\"19\" r=\"3\"/><path d=\"M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15\"/><circle cx=\"18\" cy=\"5\" r=\"3\"/>",
    "clock": "<circle cx=\"12\" cy=\"12\" r=\"10\"/><polyline points=\"12 6 12 12 16 14\"/>",
    "shield-check": "<path d=\"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.68 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z\"/><path d=\"m9 12 2 2 4-4\"/>",
    "file-check-2": "<path d=\"M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z\"/><path d=\"M14 2v4a2 2 0 0 0 2 2h4\"/><path d=\"m9 15 2 2 4-4\"/>",
    "upload-cloud": "<path d=\"M12 13v8\"/><path d=\"m8 17 4-4 4 4\"/><path d=\"M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3\"/>",
    "file-search": "<path d=\"M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h4\"/><path d=\"M14 2v6h6\"/><circle cx=\"15\" cy=\"15\" r=\"3\"/><path d=\"m17.5 17.5 3.5 3.5\"/>",
    "shield-alert": "<path d=\"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.68 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z\"/><path d=\"M12 8v4\"/><path d=\"M12 16h.01\"/>",
    "archive": "<rect width=\"20\" height=\"5\" x=\"2\" y=\"3\" rx=\"1\"/><path d=\"M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8\"/><path d=\"M10 12h4\"/>",
    "signature": "<path d=\"m21 17-2.2 2.2a1 1 0 0 1-1.4 0L16 17.8a1 1 0 0 0-1.4 0l-.7.7a1 1 0 0 1-1.4 0L11 17\"/><path d=\"M3 20c3-7 5-12 8-15 1.5-1.5 4-.5 3 2-1 3-5 8-7 10-1 1-2 1-3 0\"/>",
    "circle-dot": "<circle cx=\"12\" cy=\"12\" r=\"10\"/><circle cx=\"12\" cy=\"12\" r=\"1\"/>",
    "check-circle-2": "<circle cx=\"12\" cy=\"12\" r=\"10\"/><path d=\"m9 12 2 2 4-4\"/>",
    "alert-triangle": "<path d=\"m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3\"/><path d=\"M12 9v4\"/><path d=\"M12 17h.01\"/>",
    "plus-circle": "<circle cx=\"12\" cy=\"12\" r=\"10\"/><path d=\"M8 12h8\"/><path d=\"M12 8v8\"/>"
  };
  return `<svg aria-hidden="true" class="icon lucide lucide-${name}" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 24 24">${lucidePaths[name] || lucidePaths.user}</svg>`;
}

function handleWorkflowNodePointerDown(event) {
  if (event.button !== 0) return;
  if (event.target?.closest?.("button,input,select,textarea,a,label")) return;
  const nodeEl = event.currentTarget;
  const canvas = nodeEl.closest("[data-workflow-canvas]");
  if (!canvas) return;
  const stepId = nodeEl.dataset.workflowNodeId;
  const templateId = nodeEl.dataset.workflowTemplateId || "payroll-close";
  const rect = canvas.getBoundingClientRect();
  let moved = false;
  let latestX = Number.parseFloat(nodeEl.style.getPropertyValue("--node-x")) || 50;
  let latestY = Number.parseFloat(nodeEl.style.getPropertyValue("--node-y")) || 50;

  const updatePosition = (pointerEvent) => {
    const x = ((pointerEvent.clientX - rect.left) / rect.width) * 100;
    const y = ((pointerEvent.clientY - rect.top) / rect.height) * 100;
    latestX = clampWorkflowPercent(x);
    latestY = clampWorkflowPercent(y);
    nodeEl.style.setProperty("--node-x", latestX);
    nodeEl.style.setProperty("--node-y", latestY);
  };

  const onMove = (pointerEvent) => {
    moved = true;
    updatePosition(pointerEvent);
  };

  const onUp = async (pointerEvent) => {
    nodeEl.releasePointerCapture?.(pointerEvent.pointerId);
    nodeEl.removeEventListener("pointermove", onMove);
    nodeEl.removeEventListener("pointerup", onUp);
    nodeEl.removeEventListener("pointercancel", onCancel);
    if (!moved) return;
    state.workflowDragSuppressId = stepId;
    await moveWorkflowStep(templateId, stepId, latestX, latestY);
  };

  const onCancel = (pointerEvent) => {
    nodeEl.releasePointerCapture?.(pointerEvent.pointerId);
    nodeEl.removeEventListener("pointermove", onMove);
    nodeEl.removeEventListener("pointerup", onUp);
    nodeEl.removeEventListener("pointercancel", onCancel);
  };

  nodeEl.setPointerCapture?.(event.pointerId);
  nodeEl.addEventListener("pointermove", onMove);
  nodeEl.addEventListener("pointerup", onUp);
  nodeEl.addEventListener("pointercancel", onCancel);
}

function render() {
  if (!state.catalog) return;
  document.documentElement.lang = state.locale.split("-")[0];
  document.title = t("preview.documentTitle");
  const skipLink = document.querySelector("[data-skip-link]");
  if (skipLink) {
    skipLink.textContent = t("preview.skipLink");
    skipLink.setAttribute("aria-label", t("preview.skipLink"));
  }
  document.getElementById("app").innerHTML = renderShell();
  bindEvents();
}

function languageSettingsPanel() {
  return `<section class="card${tutorialAnchorClass("settings-language")}" data-tutorial-anchor="settings-language">
    ${sectionHead("", t("preview.settings.language.title"), "")}
    <div class="language-grid">${visibleLocaleIds.map((locale) => `
      <button class="language-option ${state.locale === locale ? "selected" : ""}" type="button" data-language="${locale}">
        <strong>${languageName(locale)}</strong><span class="helper">${t("preview.settings.koreanFirst.detail")}</span>
      </button>
    `).join("")}</div>
  </section>`;
}

function themeSettingsPanel() {
  const themes = sidebarThemes();
  const activeSidebarTheme = themes.find((theme) => theme.id === state.sidebarTheme) || themes[0];
  return `<section class="card${tutorialAnchorClass("settings-theme")}" data-tutorial-anchor="settings-theme">
    ${sectionHead("", t("preview.settings.theme.title"), "", badge(t("preview.settings.theme.current", { theme: activeSidebarTheme.label }), "neutral"))}
    <div class="sidebar-theme-grid settings-theme-grid">
      ${themes.map((theme) => `
        <button
          aria-label="${escapeText(t("preview.settings.theme.optionLabel", { label: theme.label, description: theme.description }))}"
          aria-pressed="${state.sidebarTheme === theme.id ? "true" : "false"}"
          class="sidebar-theme-chip ${state.sidebarTheme === theme.id ? "active" : ""}"
          data-sidebar-theme="${theme.id}"
          title="${escapeText(theme.description)}"
        >
          <span class="sidebar-swatch sidebar-swatch-${theme.id}"></span>
          <strong>${escapeText(theme.label)}</strong>
        </button>
      `).join("")}
    </div>
  </section>`;
}

function workspaceSettingsPanel() {
  const account = selectedAccount();
  const preferences = state.userPreferences || defaultPreferences;
  return `<section class="card settings-overview-card${tutorialAnchorClass("settings-workspace")}" data-tutorial-anchor="settings-workspace">
    ${sectionHead("", t("preview.settings.workspace.title"), "")}
    <div class="settings-status-grid">
      <article class="settings-status-item">
        <span class="helper">${t("preview.settings.session")}</span>
        <strong>${escapeText(account.displayName)}</strong>
        <small>${t("preview.settings.sessionActive")}</small>
      </article>
      <article class="settings-status-item">
        <span class="helper">${t("preview.settings.workspace.tenant")}</span>
        <strong>${escapeText(account.tenantName)}</strong>
        <small>${escapeText(account.companyCode)}</small>
      </article>
      <article class="settings-status-item">
        <span class="helper">${t("preview.settings.languagePolicy")}</span>
        <strong>${escapeText(languageName(state.locale))}</strong>
        <small>${t("preview.settings.koreanFirst.detail")}</small>
      </article>
    </div>
    <div class="settings-preference-grid">
      ${preferenceChoiceGroup("workspace_density", preferences.workspace_density, ["work_dense", "comfortable"])}
      ${preferenceChoiceGroup("notification_digest", preferences.notification_digest, ["role_work", "urgent_only"])}
      ${preferenceChoiceGroup("payroll_standard_view", preferences.payroll_standard_view, ["before_run", "always_visible"])}
    </div>
  </section>`;
}

function preferenceChoiceGroup(key, activeValue, values) {
  return `<fieldset class="preference-choice-group">
    <legend>${t(`preview.settings.preference.${catalogId(key)}.title`)}</legend>
    <div class="preference-choice-list">
      ${values.map((value) => `
        <button
          aria-pressed="${activeValue === value ? "true" : "false"}"
          class="preference-choice ${activeValue === value ? "selected" : ""}"
          data-preference-key="${escapeAttribute(key)}"
          data-preference-value="${escapeAttribute(value)}"
          type="button"
        >
          <strong>${t(`preview.settings.preference.${catalogId(value)}.label`)}</strong>
          <span>${t(`preview.settings.preference.${catalogId(value)}.detail`)}</span>
        </button>
      `).join("")}
    </div>
  </fieldset>`;
}

function renderShell() {
  if (!state.authed) return renderSignedOut();
  const items = visibleNavigationItems();
  const active = activeItem(items);
  return html`
    <section class="shell sidebar-theme-${state.sidebarTheme}">
      <aside class="sidebar">
        <div class="brand-block">
          <img class="company-logo" src="${companyLogoUri}" alt="${t("shell.companyLogo")}" />
          <div><strong>Bitween</strong><span>${t("shell.brandSubtitle")}</span></div>
        </div>
        <nav class="nav" aria-label="${t("shell.navigation.aria")}">
          ${items.map((item) => `
            <button aria-current="${item.id === active.id ? "page" : "false"}" class="nav-button ${item.id === active.id ? "active" : ""}${tutorialAnchorClass(`nav-${item.id}`)}" data-target="${item.id}" data-tutorial-anchor="nav-${item.id}" style="${item.id === active.id ? `border-left-color:${item.accent}` : ""}">
              <strong>${item.label}</strong>
            </button>
          `).join("")}
        </nav>
      </aside>
      <div class="main">
        <header class="topbar">
          <div class="topbar-copy">
            <span class="topbar-eyebrow">${active.eyebrow}</span>
            <h1>${active.label}</h1>
          </div>
          <div class="top-actions">
            <button class="icon-btn ${state.topbarPanel === "notifications" ? "active" : ""}" data-topbar-panel="notifications" aria-label="${t("preview.topbar.notifications")}">${icon("bell")}${topbarCountBadge(notificationItems().length)}</button>
            <button class="icon-btn ${state.topbarPanel === "messages" ? "active" : ""}" data-topbar-panel="messages" aria-label="${t("preview.topbar.messages")}">${icon("message-circle")}${topbarCountBadge(messageItems().length)}</button>
            <button class="icon-btn ${state.tutorialOpen ? "active" : ""}${tutorialAnchorClass("topbar-help")}" data-open-tutorial="true" data-tutorial-anchor="topbar-help" aria-label="${t("preview.topbar.help")}">${icon("circle-help")}</button>
            <button class="icon-btn ${state.activeId === "settings" ? "active" : ""}${tutorialAnchorClass("topbar-settings")}" data-open-settings="true" data-tutorial-anchor="topbar-settings" aria-label="${t("preview.topbar.settings")}">${icon("settings")}</button>
            ${state.topbarPanel ? topbarActionPanel(state.topbarPanel) : ""}
            <div class="profile-actions">
              <button class="icon-btn" data-profile-toggle="true" aria-expanded="${state.profileMenuOpen ? "true" : "false"}" aria-label="${t("preview.topbar.profile")}">${icon("user")}</button>
              ${state.profileMenuOpen ? profileMenu() : ""}
            </div>
          </div>
        </header>
        <div class="content" id="main-content" tabindex="-1">${renderScreen(active.id)}</div>
      </div>
    </section>
    ${state.tutorialOpen ? tutorialOverlay(active.id) : ""}
    <div aria-atomic="true" aria-live="polite" class="toast" id="toast" role="status">${t("preview.toast.default")}</div>
  `;
}

function renderSignedOut() {
  const needsAuthSetup = !authRouteConfigured("signin");
  return html`
    <section class="signed-out shell sidebar-theme-${state.sidebarTheme}">
      <main class="signed-out-panel card">
        <img class="company-logo large" src="${companyLogoUri}" alt="${t("shell.companyLogo")}" />
        <h1>${t("preview.signout.title")}</h1>
        <p>${t("preview.signout.detail")}</p>
        ${needsAuthSetup ? `<div class="auth-setup-hint" role="status"><strong>${t("preview.auth.setupTitle")}</strong><span>${t("preview.auth.setupDetail")}</span></div>` : ""}
        <div class="auth-actions">
          ${authButton("signin", "primary", "preview.auth.signin")}
          ${authButton("signup", "secondary", "preview.auth.signup")}
          ${authButton("onboarding", "ghost", "preview.auth.onboarding")}
        </div>
      </main>
    </section>
    <div aria-atomic="true" aria-live="polite" class="toast" id="toast" role="status">${t("preview.toast.default")}</div>
  `;
}

function profileMenu() {
  const account = selectedAccount();
  return `<div class="profile-menu" role="menu">
    <div class="profile-summary"><strong>${escapeText(account.displayName)}</strong><span>${escapeText(account.tenantName)}</span></div>
    <button class="profile-menu-item" data-open-settings="true" role="menuitem">${icon("settings")}<span>${t("preview.profile.settings")}</span></button>
    <button class="profile-menu-item" data-auth-action="signout" role="menuitem">${icon("log-out")}<span>${t("shell.logout")}</span></button>
  </div>`;
}

function topbarActionPanel(type) {
  const items = type === "notifications" ? notificationItems() : messageItems();
  const title = type === "notifications" ? t("preview.topbarPanel.notifications.title") : t("preview.topbarPanel.messages.title");
  const emptyText = type === "notifications" ? t("preview.topbarPanel.notifications.empty") : t("preview.topbarPanel.messages.empty");
  return `<div class="topbar-panel" role="dialog" aria-label="${escapeText(title)}">
    <strong>${escapeText(title)}</strong>
    ${items.length ? `<div class="topbar-panel-list">${items.map((item) => `
      <button class="topbar-panel-row" data-work-step-key="${item.id}" style="--tone:${toneColor(item.tone)}">
        <span>${badge(statusText(item.status), item.tone)}</span>
        <span><strong>${escapeText(item.title)}</strong><small>${escapeText(item.detail)}</small></span>
      </button>
    `).join("")}</div>` : `<div class="topbar-panel-empty">${escapeText(emptyText)}</div>`}
  </div>`;
}

function topbarCountBadge(count) {
  const value = Number(count || 0);
  return value > 0 ? `<span class="topbar-count" aria-hidden="true">${Math.min(value, 9)}</span>` : "";
}

function notificationItems() {
  const workflowItems = workflowNotificationItems();
  const payrollItems = editableWorkflowSteps()
    .filter((step) => step.status !== "completed" && (step.status === "ready" || step.tone === "blocked"))
    .slice(0, 4)
    .map((step) => ({
      detail: stepAction(step),
      id: step.id,
      status: step.status,
      title: stepTitle(step),
      tone: step.tone
    }));
  return [...workflowItems, ...payrollItems].slice(0, 6);
}

function workflowNotificationItems() {
  const runtimeItems = [...(state.workflowRuntimeEvents || [])]
    .slice(-4)
    .reverse()
    .map((event) => {
      const node = workflowTemplateNodes().find((step) => step.id === event.step_id) || { id: event.step_id };
      return {
        detail: t("preview.topbarPanel.notifications.workflowDetail", {
          owner: ownerText(event.actor_role),
          count: Array.isArray(event.affected_step_ids) ? event.affected_step_ids.length : 0
        }),
        id: event.step_id,
        status: "needs_attention",
        title: stepTitle(node),
        tone: "attention"
      };
    });
  const recordItems = [...(state.workflowDataRecords || [])]
    .slice(-4)
    .reverse()
    .map((record) => ({
      detail: t("preview.topbarPanel.notifications.dataRecord", {
        count: Number(record.record_count || 0)
      }),
      id: record.step_id,
      status: record.status === "completed" ? "completed" : "ready",
      title: workflowOperationTypeText(record.record_type),
      tone: record.status === "completed" ? "ready" : "attention"
    }));
  return [...runtimeItems, ...recordItems].slice(0, 4);
}

function messageItems() {
  const workflowItems = workflowMessageItems();
  const payrollItems = editableWorkflowSteps()
    .filter((step) => step.status !== "completed" && ["hr", "payroll", "workflow", "archive"].includes(step.target))
    .slice(0, 4)
    .map((step) => ({
      detail: t("preview.topbarPanel.messages.handoff", {
        owner: ownerText(step.owner),
        area: catalogText(`navigation.${step.target}.label`, step.target)
      }),
      id: step.id,
      status: step.status,
      title: stepTitle(step),
      tone: step.tone
    }));
  return [...workflowItems, ...payrollItems].slice(0, 6);
}

function workflowMessageItems() {
  return [...(state.workflowRuntimeEvents || [])]
    .slice(-4)
    .reverse()
    .filter((event) => Array.isArray(event.affected_step_ids) && event.affected_step_ids.length)
    .map((event) => {
      const node = workflowTemplateNodes().find((step) => step.id === event.step_id) || { id: event.step_id };
      return {
        detail: t("preview.topbarPanel.messages.workflowHandoff", {
          count: event.affected_step_ids.length
        }),
        id: event.affected_step_ids[0] || event.step_id,
        status: "needs_attention",
        title: stepTitle(node),
        tone: "attention"
      };
    });
}

function renderScreen(id) {
  if (id === "home") return renderHome();
  if (id === "hr") return renderHr();
  if (id === "payroll") return renderPayroll();
  if (id === "workflow") return renderWorkflow();
  if (id === "approval") return renderApproval();
  if (id === "archive") return renderArchive();
  if (id === "admin") return renderAdmin();
  if (id === "settings") return renderSettings();
  return empty(t("screens.module.unavailable.title"), t("screens.module.unavailable.description"));
}

function renderHome() {
  const workstream = payrollWorkstream();
  const buckets = homeWorkBuckets();
  const current = buckets.today[0] || currentWorkflowStep();
  return html`
    <section class="card operator-day-card${tutorialAnchorClass("home-primary")}" data-tutorial-anchor="home-primary">
      ${sectionHead("", t("preview.home.todayTitle"), "", button(t("preview.home.openWorkflow"), current.target || "workflow", "secondary"))}
      <div class="operator-day-grid">
        <article class="operator-focus" style="border-left-color:${toneColor(current.tone)}">
          ${badge(statusText(current.status), current.tone)}
          <h3>${escapeText(stepTitle(current))}</h3>
          <p>${escapeText(stepAction(current))}</p>
          <span class="helper">${escapeText(ownerText(current.owner))}</span>
        </article>
        <article class="operator-period">
          <span>${t("preview.home.period")}</span>
          <strong>${escapeText(workstream.period_label)}</strong>
        </article>
      </div>
    </section>
    <section class="home-board${tutorialAnchorClass("home-board")}" data-tutorial-anchor="home-board">
      ${homeBucket(t("preview.home.outstandingTitle"), buckets.today, t("preview.home.outstandingEmpty"), "today")}
      ${homeBucket(t("preview.home.scheduleTitle"), buckets.schedule, t("preview.home.scheduleEmpty"), "schedule")}
      ${homeBucket(t("preview.home.followUpsTitle"), buckets.followUps, t("preview.home.followUpsEmpty"), "follow")}
      ${homeBucket(t("preview.home.prepTitle"), buckets.prep, t("preview.home.prepEmpty"), "prep")}
    </section>
  `;
}

function renderHr() {
  const steps = workflowSteps("hr");
  const selected = selectedWorkflowStep("hr");
  const selectedEmployee = state.hrEmployees.find((employee) => employee.id === state.selectedEmployeeId) || state.hrEmployees[0];
  return html`
    <section class="card hr-management-card${tutorialAnchorClass("hr-people")}" data-tutorial-anchor="hr-people">
      ${sectionHead("", t("preview.hr.people.title"), "")}
      ${employeeLifecycleSummary()}
      <form class="employee-form" data-hr-employee-form="true">
        <label><span>${t("preview.hr.form.name")}</span><input name="name" autocomplete="name" required /></label>
        <label><span>${t("preview.hr.form.team")}</span><input name="team" required /></label>
        <label><span>${t("preview.hr.form.role")}</span><input name="role" required /></label>
        <button class="btn primary" type="submit">${t("preview.hr.actions.addEmployee")}</button>
      </form>
      ${state.hrError ? `<div class="notice warning">${escapeText(state.hrError.detail || t("preview.hr.toast.failed"))}</div>` : ""}
      ${employeeTable()}
      ${selectedEmployee ? employeeDetail(selectedEmployee) : empty(t("preview.hr.empty.title"), t("preview.hr.empty.detail"))}
    </section>
    <section class="card${tutorialAnchorClass("hr-workflow")}" data-tutorial-anchor="hr-workflow">
      ${sectionHead("", t("preview.hr.title"), "")}
      ${workSurfacePanel(steps, selected, "hr")}
    </section>
  `;
}

function renderPayroll() {
  const scope = state.liveView?.payroll?.scope;
  const allSteps = editableWorkflowSteps();
  const steps = workflowSteps("payroll");
  const selected = selectedWorkflowStep("payroll");
  return html`
    <section class="card${tutorialAnchorClass("payroll-scope")}" data-tutorial-anchor="payroll-scope">
      ${sectionHead("", t("preview.payroll.scope.title"), "")}
      <div class="detail-grid">
        <div class="detail-item"><span class="helper">${t("preview.payroll.scope.tenant")}</span><strong>${escapeText(scope?.tenant_name || t("preview.payroll.scope.notConfigured"))}</strong></div>
        <div class="detail-item"><span class="helper">${t("preview.payroll.scope.affiliate")}</span><strong>${escapeText(scope?.affiliate || t("preview.payroll.scope.notConfigured"))}</strong></div>
        <div class="detail-item"><span class="helper">${t("preview.payroll.scope.workplace")}</span><strong>${escapeText(scope?.workplace || t("preview.payroll.scope.notConfigured"))}</strong></div>
        <div class="detail-item"><span class="helper">${t("preview.payroll.scope.period")}</span><strong>${escapeText(scope?.period || t("preview.payroll.scope.notConfigured"))}</strong></div>
      </div>
    </section>
    <section class="card${tutorialAnchorClass("payroll-actions")}" data-tutorial-anchor="payroll-actions">
      ${sectionHead("", t("preview.payroll.actions.title"), "")}
      ${payrollStageSummary(allSteps)}
      ${workSurfacePanel(steps, selected, "payroll")}
    </section>
    <section class="card payroll-reconciliation-card">
      ${sectionHead("", t("preview.payroll.reconciliation.title"), t("preview.payroll.reconciliation.detail"))}
      ${payrollReconciliationPanel()}
    </section>
  `;
}

function formatWon(value) {
  const amount = Number(value) || 0;
  return new Intl.NumberFormat(state.locale).format(Math.round(amount));
}

function payrollReconciliationPanel() {
  if (state.payrollReconciliationError) {
    return `<div class="notice warning">${escapeText(state.payrollReconciliationError.detail || t("preview.payroll.reconciliation.failed"))}</div>`;
  }
  const report = state.payrollReconciliation;
  if (!report || !Array.isArray(report.workers) || report.workers.length === 0) {
    return empty(t("preview.payroll.reconciliation.empty.title"), t("preview.payroll.reconciliation.empty.detail"));
  }
  const totals = report.totals || {};
  const aggregateBadge = totals.all_net_match
    ? badge(t("preview.payroll.reconciliation.badge.pass"), "ready")
    : badge(t("preview.payroll.reconciliation.badge.variance"), "blocked");
  const summary = `
    <div class="payroll-reconciliation-summary">
      <div class="detail-grid">
        <div class="detail-item"><span class="helper">${t("preview.payroll.reconciliation.summary.period")}</span><strong>${escapeText(report.period || "")}</strong></div>
        <div class="detail-item"><span class="helper">${t("preview.payroll.reconciliation.summary.workers")}</span><strong>${t("preview.payroll.reconciliation.summary.matchCount", { matched: totals.net_match_count ?? 0, total: totals.workers ?? 0 })}</strong></div>
        <div class="detail-item"><span class="helper">${t("preview.payroll.reconciliation.summary.gross")}</span><strong>${formatWon(totals.gross)}</strong></div>
        <div class="detail-item"><span class="helper">${t("preview.payroll.reconciliation.summary.deductions")}</span><strong>${formatWon(totals.total_deductions)}</strong></div>
        <div class="detail-item"><span class="helper">${t("preview.payroll.reconciliation.summary.net")}</span><strong>${formatWon(totals.net)}</strong></div>
        <div class="detail-item"><span class="helper">${t("preview.payroll.reconciliation.summary.status")}</span>${aggregateBadge}</div>
      </div>
    </div>`;
  const rows = report.workers.map((worker) => {
    const matchBadge = worker.net_match
      ? badge(t("preview.payroll.reconciliation.row.match"), "ready")
      : badge(t("preview.payroll.reconciliation.row.delta", { delta: formatWon((worker.computed_net ?? 0) - (worker.source_net ?? 0)) }), "blocked");
    const name = worker.name || worker.employee_key || "";
    return `
      <div class="payroll-reconciliation-row" role="row">
        <span class="payroll-reconciliation-name"><strong>${escapeText(name)}</strong></span>
        <span class="payroll-reconciliation-amount">${formatWon(worker.gross)}</span>
        <span class="payroll-reconciliation-amount">${formatWon(worker.source_deductions)}</span>
        <span class="payroll-reconciliation-amount">${formatWon(worker.source_net)}</span>
        <span class="payroll-reconciliation-status">${matchBadge}</span>
      </div>`;
  }).join("");
  return `
    ${summary}
    <div class="payroll-reconciliation-table" role="table" aria-label="${t("preview.payroll.reconciliation.title")}">
      <div class="payroll-reconciliation-row payroll-reconciliation-head" role="row">
        <span>${t("preview.payroll.reconciliation.column.name")}</span>
        <span class="payroll-reconciliation-amount">${t("preview.payroll.reconciliation.column.gross")}</span>
        <span class="payroll-reconciliation-amount">${t("preview.payroll.reconciliation.column.deductions")}</span>
        <span class="payroll-reconciliation-amount">${t("preview.payroll.reconciliation.column.net")}</span>
        <span class="payroll-reconciliation-status">${t("preview.payroll.reconciliation.column.status")}</span>
      </div>
      ${rows}
    </div>`;
}

function renderWorkflow() {
  const nodes = workflowTemplateNodes();
  const selected = nodes.find((node) => node.id === state.selectedWorkStepKey) || nodes[0];
  return html`
    <section class="card workflow-builder-card">
      ${sectionHead("", t("preview.workflow.canvas.title"), t("preview.workflow.canvas.detail"))}
      ${state.workflowError ? `<div class="notice warning">${t("preview.workflow.store.failed")}</div>` : ""}
      ${workflowTemplateLibrary()}
      ${workflowBuilderLayout(nodes, selected)}
    </section>
  `;
}

function renderApproval() {
  const steps = workflowSteps("approval");
  const selected = selectedWorkflowStep("approval");
  return html`
    <section class="card approval-workbench-card">
      ${sectionHead("", t("preview.approval.title"), t("preview.approval.detail"))}
      ${approvalQueue(steps, selected)}
    </section>
  `;
}

function renderArchive() {
  const steps = workflowSteps("archive");
  const selected = selectedWorkflowStep("archive");
  return html`
    <section class="card intake-workbench-card${tutorialAnchorClass("archive-intake")}" data-tutorial-anchor="archive-intake">
      ${sectionHead("", t("preview.archive.intake.title"), "")}
      <div class="intake-dropzone" data-intake-dropzone="true">
        <strong>${t("preview.archive.intake.dropTitle")}</strong>
        <span>${t("preview.archive.intake.dropDetail")}</span>
        <input type="file" data-intake-file="true" />
      </div>
      ${state.archiveError ? `<div class="notice warning">${t("preview.archive.intake.failed")}</div>` : ""}
      ${archiveIntakeSummary()}
      ${archiveIntakeFlow()}
      ${archiveIntakeList()}
    </section>
    <section class="card${tutorialAnchorClass("archive-work")}" data-tutorial-anchor="archive-work">
      ${sectionHead("", t("preview.archive.title"), "")}
      ${workSurfacePanel(steps, selected, "archive")}
    </section>
  `;
}

function archiveIntakeList() {
  if (!state.archiveIntakes.length) {
    return empty(t("preview.archive.intake.empty.title"), t("preview.archive.intake.empty.detail"));
  }
  return `<div class="intake-list" aria-label="${t("preview.archive.intake.queue")}">
    ${state.archiveIntakes.map((intake) => `
      <article class="intake-row">
        <span><strong>${escapeText(intake.stored_file_name || intake.original_file_name || intake.file_name)}</strong><small>${escapeText(archiveFileMeta(intake))}</small></span>
        ${badge(archiveStatusText(intake.status), archiveStatusTone(intake.status))}
        <span class="intake-next"><small>${archiveDatabaseTargetText(intake.database_target)}</small><strong>${archiveNextActionText(intake.next_action)}</strong>${archiveAdmissionAction(intake)}</span>
        ${archiveMappingEditor(intake)}
        ${archiveGuidanceList(intake)}
        ${archiveVersionList(intake)}
      </article>
    `).join("")}
  </div>`;
}

function archiveIntakeSummary() {
  const intakes = state.archiveIntakes || [];
  const needsReview = intakes.filter((intake) => {
    const guidanceCount = (intake.guidance_items || []).length + (intake.anomalies || []).length;
    return guidanceCount > 0 || ["needs_guidance", "needs_review"].includes(intake.status);
  }).length;
  const ready = intakes.filter((intake) => intake.postgres_ready || intake.status === "ready_for_staging").length;
  const stored = intakes.filter((intake) => ["admitted", "archived", "accepted"].includes(intake.status)).length;
  return `<div class="intake-summary-grid" aria-label="${t("preview.archive.intake.summary.aria")}">
    ${archiveSummaryCard("review", needsReview, "blocked")}
    ${archiveSummaryCard("ready", ready, "ready")}
    ${archiveSummaryCard("stored", stored, "neutral")}
  </div>`;
}

function archiveSummaryCard(key, count, tone) {
  return `<article class="intake-summary-card" style="--tone:${toneColor(tone)}">
    <span>${t(`preview.archive.intake.summary.${key}.title`)}</span>
    <strong>${t("preview.archive.intake.summary.count", { count })}</strong>
    <small>${t(`preview.archive.intake.summary.${key}.detail`)}</small>
  </article>`;
}

function archiveMappingEditor(intake) {
  const mappings = intake.field_mappings || [];
  const targets = archiveTargetFields(intake.database_target);
  if (!mappings.length || !targets.length) return "";
  const unresolved = mappings.filter((mapping) => ["needs_review", "preserved"].includes(mapping.status)).length;
  const requiredOpen = (intake.guidance_items || []).some((item) => item.code === "confirm_missing_required_data");
  return `<form class="archive-field-mapping" data-intake-field-mapping-form="${escapeAttribute(intake.id)}">
    <div class="archive-field-mapping-head">
      <span>
        <strong>${t("preview.archive.intake.mapping.title")}</strong>
        <small>${t("preview.archive.intake.mapping.detail", {
          count: mappings.length,
          unresolved
        })}</small>
      </span>
      ${requiredOpen ? badge(t("preview.archive.intake.mapping.requiredOpen"), "blocked") : badge(t("preview.archive.intake.mapping.ready"), "ready")}
    </div>
    <div class="archive-field-map-grid" role="table" aria-label="${t("preview.archive.intake.mapping.aria")}">
      ${mappings.map((mapping) => archiveMappingRow(mapping, targets)).join("")}
    </div>
    <div class="archive-field-mapping-actions">
      <small>${t("preview.archive.intake.mapping.privacy")}</small>
      <button type="submit" class="primary-mini">${t("preview.archive.intake.mapping.save")}</button>
    </div>
  </form>`;
}

function archiveMappingRow(mapping, targets) {
  const selected = mapping.target_field || "source_payload";
  return `<label class="archive-field-map-row" data-field-mapping-row="true" data-source-column="${escapeAttribute(mapping.source_column || "")}">
    <span>
      <strong>${escapeText(mapping.source_column || t("preview.archive.intake.column.unspecified"))}</strong>
      <small>${archiveMappingStatusText(mapping.status)} · ${t("preview.archive.intake.mapping.confidence", { confidence: mapping.confidence ?? 0 })}</small>
      ${mapping.value_shape ? `<small>${archiveValueShapeText(mapping.value_shape)}</small>` : ""}
    </span>
    <select data-field-target="true" aria-label="${t("preview.archive.intake.mapping.targetAria", { column: mapping.source_column || "" })}">
      ${targets.map((field) => `<option value="${escapeAttribute(field)}" ${field === selected ? "selected" : ""}>${archiveTargetFieldText(field)}</option>`).join("")}
    </select>
  </label>`;
}

function renderAdmin() {
  const adminItems = workQueue().filter((item) => item.target === "admin");
  const selected = adminItems.find((item) => item.id === state.selectedAdminKey) || adminItems[0];
  return html`
    <section class="card${tutorialAnchorClass("admin-setup")}" data-tutorial-anchor="admin-setup">
      ${sectionHead("", t("preview.admin.title"), "")}
      ${adminItems.length ? adminCards(adminItems) : empty(t("preview.admin.ready.title"), t("preview.admin.ready.detail"))}
      ${selected ? adminDetail(selected) : ""}
    </section>
  `;
}

function renderSettings() {
  return html`
    ${state.settingsError ? `<div class="notice warning">${t("preview.settings.preferences.failed")}</div>` : ""}
    ${workspaceSettingsPanel()}
    ${themeSettingsPanel()}
    ${languageSettingsPanel()}
  `;
}

function homeBucket(title, steps, emptyText, timeframe) {
  return `<section class="card home-bucket">
    ${sectionHead("", title, "")}
    ${steps.length ? `<div class="home-work-list">${steps.map((step) => `
      <button class="home-work-row" data-home-work-target="${step.target}" data-work-step-key="${step.id}" style="--tone:${toneColor(step.tone)}">
        <span class="home-work-time">${t(`preview.home.timeframe.${timeframe}`)}</span>
        <span class="home-work-main"><strong>${escapeText(stepTitle(step))}</strong><small>${escapeText(stepAction(step))}</small></span>
        ${badge(statusText(step.status), step.tone)}
      </button>
    `).join("")}</div>` : `<div class="home-empty">${escapeText(emptyText)}</div>`}
  </section>`;
}

function tutorialOverlay(screenId) {
  const steps = tutorialSteps(screenId);
  const safeIndex = Math.min(state.tutorialStepIndex, steps.length - 1);
  const step = steps[safeIndex];
  return `<div class="tutorial-backdrop" role="dialog" aria-modal="true" aria-labelledby="tutorial-title">
    <section class="tutorial-card">
      <div class="tutorial-card-head">
        <span class="eyebrow">${t("preview.tutorial.eyebrow")}</span>
        <button class="icon-btn tutorial-close" data-close-tutorial="true" aria-label="${t("preview.tutorial.close")}">×</button>
      </div>
      <div class="tutorial-target-pill" data-tutorial-target="${escapeAttribute(step.anchor)}">
        ${icon("circle-dot")}
        <span>${escapeText(step.target)}</span>
      </div>
      <h2 id="tutorial-title">${escapeText(step.title)}</h2>
      <p>${escapeText(step.detail)}</p>
      <div class="tutorial-progress" aria-label="${t("preview.tutorial.progress", { current: safeIndex + 1, total: steps.length })}">
        ${steps.map((_, index) => `<span class="${index === safeIndex ? "active" : ""}"></span>`).join("")}
      </div>
      <div class="action-row">
        <button class="btn ghost" data-tutorial-prev="true" ${safeIndex === 0 ? "disabled" : ""}>${t("preview.tutorial.previous")}</button>
        <button class="btn primary" data-tutorial-next="true">${safeIndex === steps.length - 1 ? t("preview.tutorial.done") : t("preview.tutorial.next")}</button>
      </div>
    </section>
  </div>`;
}

function tutorialSteps(screenId) {
  const id = messageExists(`preview.tutorial.${screenId}.step1.title`) ? screenId : "home";
  const anchors = tutorialAnchorSequence(id);
  return [1, 2, 3].map((index) => {
    const anchor = anchors[index - 1] || anchors[0] || "home-primary";
    return {
      title: t(`preview.tutorial.${id}.step${index}.title`),
      detail: t(`preview.tutorial.${id}.step${index}.detail`),
      anchor,
      target: tutorialTargetLabel(anchor)
    };
  });
}

const tutorialAnchorLabelKeys = new Map([
  ["home-primary", "preview.home.todayTitle"],
  ["home-board", "preview.home.outstandingTitle"],
  ["topbar-help", "preview.topbar.help"],
  ["topbar-settings", "preview.topbar.settings"],
  ["nav-workflow", "navigation.workflow.label"],
  ["hr-people", "preview.hr.people.title"],
  ["hr-workflow", "preview.hr.title"],
  ["payroll-scope", "preview.payroll.scope.title"],
  ["payroll-actions", "preview.payroll.actions.title"],
  ["workflow-canvas", "preview.workflow.canvas.title"],
  ["workflow-inspector", "preview.workflow.detail.title"],
  ["workflow-palette", "preview.workflow.palette.title"],
  ["approval-list", "preview.approval.title"],
  ["approval-detail", "preview.approval.document"],
  ["archive-intake", "preview.archive.intake.title"],
  ["archive-work", "preview.archive.title"],
  ["admin-setup", "preview.admin.title"],
  ["admin-detail", "preview.admin.detail.selected"],
  ["settings-workspace", "preview.settings.workspace.title"],
  ["settings-theme", "preview.settings.theme.title"],
  ["settings-language", "preview.settings.language.title"]
]);

function tutorialAnchorSequence(screenId) {
  const anchorsByScreen = {
    home: ["home-primary", "home-board", "topbar-help"],
    hr: ["hr-people", "hr-workflow", "topbar-help"],
    payroll: ["payroll-scope", "payroll-actions", "topbar-help"],
    workflow: ["workflow-canvas", "workflow-inspector", "workflow-palette"],
    approval: ["approval-list", "approval-detail", "nav-workflow"],
    archive: ["archive-intake", "archive-work", "topbar-help"],
    admin: ["admin-setup", "admin-detail", "topbar-settings"],
    settings: ["settings-workspace", "settings-theme", "settings-language"]
  };
  return anchorsByScreen[screenId] || anchorsByScreen.home;
}

function tutorialTargetLabel(anchor) {
  const key = tutorialAnchorLabelKeys.get(anchor);
  return key && messageExists(key) ? t(key) : t("preview.tutorial.eyebrow");
}

function tutorialActiveAnchor(screenId = state.activeId) {
  if (!state.tutorialOpen) return "";
  const steps = tutorialSteps(screenId);
  const safeIndex = Math.min(state.tutorialStepIndex, steps.length - 1);
  return steps[safeIndex]?.anchor || "";
}

function tutorialAnchorClass(anchor) {
  return tutorialActiveAnchor() === anchor ? " tutorial-anchor-active" : "";
}

function workSurfacePanel(steps, selected, emptyTarget) {
  if (!steps.length) return empty(t(`preview.${emptyTarget}.empty.title`), t(`preview.${emptyTarget}.empty.detail`));
  return `<div class="work-surface-layout">
    ${workActionList(steps, selected)}
    ${selected ? workStepDetail(selected) : ""}
  </div>`;
}

function workActionList(steps, selected) {
  return `<div class="work-action-list">
    ${steps.map((step) => `
      <button aria-pressed="${selected?.id === step.id}" class="work-action-row ${selected?.id === step.id ? "selected" : ""}" data-work-step-key="${step.id}" style="--tone:${toneColor(step.tone)}">
        <span class="work-action-icon">${icon(workStepIcon(step))}</span>
        <span class="work-action-main"><strong>${escapeText(stepTitle(step))}</strong><small>${escapeText(stepAction(step))}</small></span>
        ${badge(statusText(step.status), step.tone)}
      </button>
    `).join("")}
  </div>`;
}

function workStepDetail(step) {
  return `<div class="detail-panel">
    <div class="detail-head"><div><span class="helper">${t("preview.workDetail.selected")}</span><strong>${escapeText(stepTitle(step))}</strong></div>${badge(statusText(step.status), step.tone)}</div>
    <div class="detail-grid">
      <div class="detail-item"><span class="helper">${t("screens.workQueueDetail.owner")}</span><strong>${escapeText(ownerText(step.owner))}</strong></div>
      <div class="detail-item"><span class="helper">${t("preview.workDetail.nextAction")}</span><strong>${escapeText(stepAction(step))}</strong></div>
      <div class="detail-item"><span class="helper">${t("preview.workDetail.area")}</span><strong>${escapeText(catalogText(`navigation.${step.target}.label`, step.target))}</strong></div>
    </div>
    <div class="action-row">${button(t("preview.workDetail.openArea"), step.target, "secondary")}</div>
  </div>`;
}

function workStepIcon(step) {
  return {
    "set-payroll-scope": "route",
    "configure-access": "shield-check",
    "close-attendance": "user",
    "close-payroll-inputs": "file-check-2",
    "review-deductions": "file-search",
    "run-calculation": "workflow",
    "request-approval": "signature",
    "prepare-payout": "file-check-2",
    "archive-payroll-evidence": "archive"
  }[step.id] || "circle-dot";
}

function employeeLifecycleSummary() {
  const counts = state.hrEmployees.reduce((acc, employee) => {
    acc[employee.status] = (acc[employee.status] || 0) + 1;
    return acc;
  }, {});
  const statuses = ["active", "on_leave", "offboarding"];
  return `<div class="employee-lifecycle-grid" aria-label="${t("preview.hr.lifecycle.title")}">
    ${statuses.map((status) => `<article class="employee-lifecycle-card" style="--tone:${toneColor(employeeStatusTone(status))}">
      <span>${employeeStatusText(status)}</span>
      <strong>${t("preview.hr.lifecycle.count", { count: counts[status] || 0 })}</strong>
    </article>`).join("")}
  </div>`;
}

function payrollStageSummary(steps) {
  const stages = [
    ["close", ["close-attendance", "close-payroll-inputs", "review-deductions"]],
    ["run", ["run-calculation", "request-approval"]],
    ["output", ["prepare-payout", "archive-payroll-evidence"]]
  ];
  return `<div class="payroll-stage-grid" aria-label="${t("preview.payroll.stage.title")}">
    ${stages.map(([stageId, stepIds]) => {
      const stageSteps = steps.filter((step) => stepIds.includes(step.id));
      const nextStep = stageSteps.find((step) => step.status !== "completed") || stageSteps[0];
      const completed = stageSteps.filter((step) => step.status === "completed").length;
      const tone = stageSteps.some((step) => step.tone === "blocked")
        ? "blocked"
        : stageSteps.some((step) => step.tone === "attention")
          ? "attention"
          : completed === stageSteps.length && stageSteps.length
            ? "ready"
            : "neutral";
      return `<article class="payroll-stage-card" style="--tone:${toneColor(tone)}">
        <span>${t(`preview.payroll.stage.${stageId}`)}</span>
        <strong>${t("preview.payroll.stage.count", { completed, total: stageSteps.length })}</strong>
        <small>${nextStep ? escapeText(stepTitle(nextStep)) : t("preview.payroll.stage.empty")}</small>
      </article>`;
    }).join("")}
  </div>`;
}

function approvalQueue(steps, selected) {
  if (!steps.length) return empty(t("preview.approval.empty.title"), t("preview.approval.empty.detail"));
  return `<div class="approval-layout">
    <div class="approval-list${tutorialAnchorClass("approval-list")}" data-tutorial-anchor="approval-list">
      ${steps.map((step) => `
        <button aria-pressed="${selected?.id === step.id}" class="approval-row ${selected?.id === step.id ? "selected" : ""}" data-work-step-key="${step.id}" style="--tone:${toneColor(step.tone)}">
          <span class="work-action-icon">${icon("signature")}</span>
          <span class="work-action-main"><strong>${escapeText(stepTitle(step))}</strong><small>${escapeText(stepAction(step))}</small></span>
          ${badge(statusText(step.status), step.tone)}
        </button>
      `).join("")}
    </div>
    ${selected ? approvalDetail(selected) : ""}
  </div>`;
}

function approvalDetail(step) {
  return `<div class="detail-panel approval-detail${tutorialAnchorClass("approval-detail")}" data-tutorial-anchor="approval-detail">
    <div class="detail-head"><div><span class="helper">${t("preview.approval.document")}</span><strong>${escapeText(stepTitle(step))}</strong></div>${badge(statusText(step.status), step.tone)}</div>
    <div class="approval-chain" aria-label="${t("preview.approval.chain")}">
      <span>${icon("file-check-2")}${t("preview.approval.chain.reviewed")}</span>
      <span>${icon("signature")}${escapeText(ownerText(step.owner))}</span>
      <span>${icon("archive")}${t("navigation.archive.label")}</span>
    </div>
    <p class="helper">${escapeText(stepAction(step))}</p>
  </div>`;
}

function archiveIntakeFlow() {
  return `<div class="intake-flow" aria-label="${t("preview.archive.intake.flowAria")}">
    ${[
      ["upload-cloud", "store"],
      ["file-search", "read"],
      ["shield-alert", "review"],
      ["archive", "admit"]
    ].map(([iconName, key]) => `
      <article class="intake-flow-step">
        <span class="work-action-icon">${icon(iconName)}</span>
        <strong>${t(`preview.archive.intake.flow.${key}.title`)}</strong>
        <small>${t(`preview.archive.intake.flow.${key}.detail`)}</small>
      </article>
    `).join("")}
  </div>`;
}

function workflowBuilderLayout(nodes, selected) {
  const templateId = selected?.templateId || workflowTemplate()?.id || "payroll-close";
  return `<div class="workflow-builder-layout">
    ${workflowPalette(templateId, nodes, selected)}
    <div class="workflow-canvas-workspace">
      ${workflowBuilderToolbar(templateId, nodes)}
      ${workflowPreflightPanel(templateId)}
      ${workflowEditValidationPanel(templateId)}
      ${workflowAnalyticsPanel(templateId)}
      ${workflowCanvas(nodes, selected)}
    </div>
    <aside class="workflow-inspector${tutorialAnchorClass("workflow-inspector")}" data-tutorial-anchor="workflow-inspector" aria-label="${t("preview.workflow.detail.title")}">
      ${selected ? workflowNodeInspector(selected) : empty(t("preview.workflow.empty.title"), t("preview.workflow.empty.detail"))}
      ${workflowVersionHistory(templateId)}
    </aside>
  </div>`;
}

function workflowBuilderToolbar(templateId, nodes) {
  return `<div class="workflow-toolbar" aria-label="${t("preview.workflow.toolbar.aria")}">
    <div>
      <strong>${t("preview.workflow.toolbar.title")}</strong>
      <span class="helper">${state.workflowConnectFromId
        ? t("preview.workflow.connect.active", { step: workflowPlacementText(state.workflowConnectFromId, nodes) })
        : t("preview.workflow.toolbar.detail")}</span>
    </div>
    <div class="action-row">
      ${state.workflowConnectFromId
        ? `<button class="btn ghost" type="button" data-workflow-cancel-connect="true">${t("preview.workflow.connect.cancel")}</button>`
        : ""}
      <button class="btn secondary" type="button" data-workflow-preflight="true" data-workflow-template-id="${escapeText(templateId)}">${t("preview.workflow.preflight.button")}</button>
      <button class="btn secondary" type="button" data-workflow-auto-layout="true" data-workflow-template-id="${escapeText(templateId)}">${t("preview.workflow.layout.auto")}</button>
    </div>
  </div>`;
}

function workflowPalette(templateId, nodes, selected) {
  const afterId = selected?.id || nodes[nodes.length - 1]?.id || "";
  return `<aside class="workflow-palette${tutorialAnchorClass("workflow-palette")}" data-tutorial-anchor="workflow-palette" aria-label="${t("preview.workflow.palette.aria")}">
    <div class="workflow-palette-head">
      <span class="eyebrow">${t("preview.workflow.palette.eyebrow")}</span>
      <strong>${t("preview.workflow.palette.title")}</strong>
      <small>${t("preview.workflow.palette.detail")}</small>
    </div>
    <div class="workflow-palette-list">
      ${workflowPaletteKinds.map((kind) => workflowPaletteButton(templateId, kind, afterId)).join("")}
    </div>
    ${workflowAddStepForm(selected, nodes)}
  </aside>`;
}

function workflowPaletteButton(templateId, kind, afterId) {
  const item = workflowPaletteDefinition(kind);
  return `<button class="workflow-palette-item" type="button" data-workflow-palette-add="true" data-workflow-template-id="${escapeText(templateId)}" data-workflow-palette-kind="${escapeText(kind)}" data-workflow-after-step-id="${escapeText(afterId)}">
    <span class="work-action-icon">${icon(item.icon)}</span>
    <span><strong>${t(item.titleKey)}</strong><small>${t(item.detailKey)}</small></span>
  </button>`;
}

function workflowTemplateNodes() {
  const template = workflowTemplate();
  const baseSteps = new Map(payrollWorkstream().steps.map((step) => [step.id, step]));
  const templateSteps = template?.steps?.length ? template.steps : payrollWorkstream().steps;
  return templateSteps
    .map((override, index) => {
      const base = baseSteps.get(override.id) || {};
      const lane = override.lane || workflowLaneForStep(base);
      const nodeType = override.node_type || workflowNodeTypeForStep({ ...base, lane });
      return {
        ...base,
        id: override.id || base.id,
        title: override.title || base.title,
        action: override.action || base.action,
        owner: override.owner || base.owner || "platform_owner",
        status: override.status || base.status || "waiting",
        tone: override.tone || base.tone || toneFromStatus(override.status || base.status),
        target: base.target || workflowTargetForLane(lane),
        lane,
        nodeType,
        enabled: override.enabled !== false,
        nextStepIds: Array.isArray(override.next_step_ids) ? override.next_step_ids : [],
        sloMinutes: Number.isFinite(override.slo_minutes) ? override.slo_minutes : null,
        escalationRole: override.escalation_role || "",
        conditionExpression: override.condition_expression && typeof override.condition_expression === "object" ? override.condition_expression : {},
        permissionScope: override.permission_scope && typeof override.permission_scope === "object" ? override.permission_scope : {},
        positionX: Number.isFinite(override.position_x) && override.position_x ? override.position_x : workflowLanePositionX(lane),
        positionY: Number.isFinite(override.position_y) && override.position_y ? override.position_y : (index + 1) * 10,
        templateId: template?.id || "payroll-close"
      };
    })
    .filter((node) => node.id && node.enabled)
    .sort((left, right) => (left.positionY - right.positionY) || (left.positionX - right.positionX) || left.id.localeCompare(right.id));
}

function workflowTemplate() {
  return state.workflowTemplates.find((template) => template.id === "payroll-close") || state.workflowTemplates[0];
}

const workflowOwnerOptions = [
  "hr_operator",
  "hr_manager",
  "payroll_operator",
  "payroll_manager",
  "approval_signer",
  "archive_operator",
  "it_security_admin",
  "platform_owner"
];

const workflowStatusOptions = ["waiting", "needs_attention", "completed", "blocked"];
const workflowLaneOptions = ["source", "rule", "operation", "approval", "record"];
const workflowNodeTypeOptions = ["trigger", "condition", "action", "approval", "record"];
const workflowPermissionClassOptions = ["sensitive", "confidential", "internal"];
const workflowObjectScopeOptions = ["payroll_period", "hr_attendance", "approval_packet", "payroll_evidence", "workflow_runtime"];
const workflowPaletteKinds = ["condition", "action", "approval", "record"];

function workflowPaletteDefinition(kind) {
  return {
    condition: {
      actionKey: "preview.workflow.palette.condition.action",
      detailKey: "preview.workflow.palette.condition.detail",
      icon: "git-branch",
      lane: "rule",
      nodeType: "condition",
      owner: "payroll_manager",
      permissionObjectScope: "payroll_period",
      ruleKey: "preview.workflow.palette.condition.rule",
      sloMinutes: 180,
      titleKey: "preview.workflow.palette.condition.title"
    },
    action: {
      actionKey: "preview.workflow.palette.action.action",
      detailKey: "preview.workflow.palette.action.detail",
      icon: "workflow",
      lane: "operation",
      nodeType: "action",
      owner: "payroll_manager",
      permissionObjectScope: "payroll_period",
      sloMinutes: 180,
      titleKey: "preview.workflow.palette.action.title"
    },
    approval: {
      actionKey: "preview.workflow.palette.approval.action",
      detailKey: "preview.workflow.palette.approval.detail",
      icon: "signature",
      lane: "approval",
      nodeType: "approval",
      owner: "approval_signer",
      permissionObjectScope: "approval_packet",
      sloMinutes: 240,
      titleKey: "preview.workflow.palette.approval.title"
    },
    record: {
      actionKey: "preview.workflow.palette.record.action",
      detailKey: "preview.workflow.palette.record.detail",
      icon: "archive",
      lane: "record",
      nodeType: "record",
      owner: "archive_operator",
      permissionObjectScope: "payroll_evidence",
      sloMinutes: 480,
      titleKey: "preview.workflow.palette.record.title"
    }
  }[kind] || null;
}

function workflowPaletteInput(kind, afterStepId) {
  const item = workflowPaletteDefinition(kind);
  if (!item) return undefined;
  return {
    action: t(item.actionKey),
    after_step_id: afterStepId || "",
    condition_expression: item.ruleKey ? { rule: t(item.ruleKey) } : {},
    escalation_role: workflowDefaultEscalationRole(item.owner),
    lane: item.lane,
    node_type: item.nodeType,
    owner: item.owner,
    permission_scope: workflowPermissionScopeInput("sensitive", item.permissionObjectScope),
    slo_minutes: item.sloMinutes,
    title: t(item.titleKey)
  };
}

function workflowDefaultEscalationRole(owner) {
  return {
    archive_operator: "payroll_manager",
    approval_signer: "payroll_manager",
    hr_operator: "hr_manager",
    it_security_admin: "platform_owner",
    payroll_operator: "payroll_manager"
  }[owner] || owner || "platform_owner";
}

function toneFromStatus(status) {
  if (status === "blocked") return "blocked";
  if (status === "completed" || status === "ready") return "ready";
  if (status === "waiting") return "neutral";
  return "attention";
}

function workflowLaneForStep(step) {
  if (step?.lane) return step.lane;
  if (["set-payroll-scope", "configure-access"].includes(step.id)) return "rule";
  if (step.target === "hr") return "source";
  if (step.target === "payroll") return "operation";
  if (step.target === "approval") return "approval";
  if (step.target === "archive") return "record";
  return "operation";
}

function workflowNodeTypeForStep(step) {
  if (step?.nodeType) return step.nodeType;
  if (step?.node_type) return step.node_type;
  return {
    source: "trigger",
    rule: "condition",
    operation: "action",
    approval: "approval",
    record: "record"
  }[workflowLaneForStep(step)];
}

function workflowTargetForLane(lane) {
  return {
    source: "hr",
    rule: "workflow",
    operation: "payroll",
    approval: "approval",
    record: "archive"
  }[lane] || "workflow";
}

function workflowLanePositionX(lane) {
  return {
    source: 10,
    rule: 30,
    operation: 50,
    approval: 70,
    record: 90
  }[lane] || 50;
}

function workflowLaneFromPositionX(x) {
  const position = Number(x);
  if (position < 20) return "source";
  if (position < 40) return "rule";
  if (position < 60) return "operation";
  if (position < 80) return "approval";
  return "record";
}

function clampWorkflowPercent(value) {
  return Math.max(5, Math.min(95, Math.round(Number(value) || 50)));
}

function workflowTemplateLibrary() {
  const steps = workflowTemplateNodes();
  const blocked = steps.filter((step) => step.tone === "blocked").length;
  const waiting = steps.filter((step) => step.status === "waiting").length;
  return `<div class="workflow-template-library">
    <article class="workflow-template-card active">
      <span class="work-action-icon">${icon("workflow")}</span>
      <strong>${t("preview.workflow.templates.payrollClose.title")}</strong>
      <small>${t("preview.workflow.templates.payrollClose.detail")}</small>
      ${badge(blocked ? t("preview.workflow.templates.needsAttention") : t("preview.workflow.templates.ready"), blocked ? "blocked" : "ready")}
    </article>
    <div class="workflow-map-summary" aria-label="${t("preview.workflow.summary.aria")}">
      <span>${icon("route")}${t("preview.workflow.summary.steps", { count: steps.length })}</span>
      <span>${icon("clock")}${t("preview.workflow.summary.waiting", { count: waiting })}</span>
      <span>${icon("shield-check")}${t("preview.workflow.summary.saved")}</span>
    </div>
  </div>`;
}

function workflowAnalyticsPanel(templateId) {
  const analytics = state.workflowAnalytics?.find((item) => item.template_id === templateId);
  if (!analytics) return "";
  const validationTone = analytics.cycle_detected || analytics.disconnected_step_ids?.length ? "blocked" : "ready";
  return `<div class="workflow-analytics-panel" aria-label="${t("preview.workflow.analytics.aria")}">
    <article>${badge(t("preview.workflow.analytics.steps"), "neutral")}<strong>${Number(analytics.step_count || 0)}</strong></article>
    <article>${badge(t("preview.workflow.analytics.edges"), "neutral")}<strong>${Number(analytics.edge_count || 0)}</strong></article>
    <article>${badge(t("preview.workflow.analytics.branches"), analytics.branch_count ? "attention" : "ready")}<strong>${Number(analytics.branch_count || 0)}</strong></article>
    <article>${badge(t("preview.workflow.analytics.longestPath"), "neutral")}<strong>${Number(analytics.longest_path_steps || 0)}</strong></article>
    <article>${badge(t("preview.workflow.analytics.validation"), validationTone)}<strong>${validationTone === "ready" ? t("preview.workflow.analytics.validationOk") : t("preview.workflow.analytics.validationNeedsReview")}</strong></article>
  </div>`;
}

function workflowPreflightPanel(templateId) {
  const report = state.workflowPreflightReports.find((item) => item.template_id === templateId);
  if (!report && !state.workflowPreflightError) {
    return `<div class="workflow-preflight-panel empty" aria-label="${t("preview.workflow.preflight.aria")}">
      <span class="work-action-icon">${icon("shield-check")}</span>
      <div>
        <strong>${t("preview.workflow.preflight.empty.title")}</strong>
        <small>${t("preview.workflow.preflight.empty.detail")}</small>
      </div>
    </div>`;
  }
  if (state.workflowPreflightError) {
    return `<div class="workflow-preflight-panel blocked" aria-label="${t("preview.workflow.preflight.aria")}">
      <span class="work-action-icon">${icon("alert-triangle")}</span>
      <div>
        <strong>${t("preview.workflow.preflight.failed")}</strong>
        <small>${escapeText(state.workflowPreflightError.detail || t("preview.workflow.store.failed"))}</small>
      </div>
    </div>`;
  }
  const statusTone = preflightStatusTone(report.status);
  const nextActions = Array.isArray(report.next_actions) ? report.next_actions.slice(0, 3) : [];
  const issues = Array.isArray(report.issues) ? report.issues.slice(0, 4) : [];
  return `<div class="workflow-preflight-panel ${statusTone}" aria-label="${t("preview.workflow.preflight.aria")}">
    <div class="workflow-preflight-summary">
      ${badge(t(preflightStatusKey(report.status)), statusTone)}
      <strong>${t("preview.workflow.preflight.title")}</strong>
      <small>${t("preview.workflow.preflight.summary", {
        blockers: Number(report.blocker_count || 0),
        warnings: Number(report.warning_count || 0),
        steps: Array.isArray(report.planned_step_ids) ? report.planned_step_ids.length : 0
      })}</small>
    </div>
    <div class="workflow-preflight-actions">
      ${nextActions.length
        ? nextActions.map((action) => workflowPreflightNextAction(action)).join("")
        : `<span>${t("preview.workflow.preflight.noNextAction")}</span>`}
    </div>
    ${issues.length
      ? `<div class="workflow-preflight-issues">${issues.map((issue) => badge(preflightIssueText(issue), issue.severity === "error" ? "blocked" : "attention")).join("")}</div>`
      : ""}
  </div>`;
}

function workflowPreflightNextAction(action) {
  const node = workflowTemplateNodes().find((candidate) => candidate.id === action.step_id) || { id: action.step_id };
  return `<article>
    <strong>${stepTitle(node)}</strong>
    <small>${ownerText(action.owner)} · ${preflightReasonText(action.reason)} · ${preflightDueWindowText(action.due_window)}</small>
  </article>`;
}

function workflowEditValidationPanel(templateId) {
  const report = state.workflowEditValidationReports.find((item) => item.template_id === templateId);
  if (!report && !state.workflowEditValidationError) return "";
  if (state.workflowEditValidationError) {
    return `<div class="workflow-preflight-panel blocked" aria-label="${t("preview.workflow.validation.aria")}">
      <span class="work-action-icon">${icon("triangle-alert")}</span>
      <div>
        <strong>${t("preview.workflow.validation.failed")}</strong>
        <small>${escapeText(state.workflowEditValidationError.detail || t("preview.workflow.validation.failed"))}</small>
      </div>
    </div>`;
  }
  const tone = report.status === "blocked" ? "blocked" : (report.status === "accepted" ? "ready" : "attention");
  const node = workflowTemplateNodes().find((candidate) => candidate.id === report.step_id);
  const issues = Array.isArray(report.issues) ? report.issues.filter((issue) => issue.severity === "error").slice(0, 3) : [];
  return `<div class="workflow-preflight-panel ${tone}" aria-label="${t("preview.workflow.validation.aria")}">
    <div class="workflow-preflight-summary">
      ${badge(t(validationStatusKey(report.status)), tone)}
      <strong>${t("preview.workflow.validation.title")}</strong>
      <small>${t("preview.workflow.validation.summary", {
        step: node ? stepTitle(node) : report.step_id,
        blockers: Number(report.blocker_count || 0),
        warnings: Number(report.warning_count || 0)
      })}</small>
    </div>
    ${issues.length
      ? `<div class="workflow-preflight-issues">${issues.map((issue) => badge(preflightIssueText(issue), "blocked")).join("")}</div>`
      : ""}
  </div>`;
}

function validationStatusKey(status) {
  return {
    accepted: "preview.workflow.validation.status.accepted",
    blocked: "preview.workflow.validation.status.blocked",
    needs_review: "preview.workflow.validation.status.needs_review"
  }[status] || "preview.workflow.validation.status.needs_review";
}

function preflightStatusTone(status) {
  if (status === "blocked") return "blocked";
  if (status === "ready") return "ready";
  return "attention";
}

function preflightStatusKey(status) {
  return {
    blocked: "preview.workflow.preflight.status.blocked",
    needs_review: "preview.workflow.preflight.status.needs_review",
    ready: "preview.workflow.preflight.status.ready"
  }[status] || "preview.workflow.preflight.status.needs_review";
}

function preflightIssueText(issue) {
  const code = issue?.code || "needs_review";
  const key = {
    blocked_step: "preview.workflow.preflight.issue.blocked_step",
    cycle_detected: "preview.workflow.preflight.issue.cycle_detected",
    disconnected_step: "preview.workflow.preflight.issue.disconnected_step",
    missing_condition_expression: "preview.workflow.preflight.issue.missing_condition_expression",
    missing_escalation_role: "preview.workflow.preflight.issue.missing_escalation_role",
    missing_permission_scope: "preview.workflow.preflight.issue.missing_permission_scope",
    missing_slo: "preview.workflow.preflight.issue.missing_slo",
    needs_review: "preview.workflow.preflight.issue.needs_review"
  }[code] || "preview.workflow.preflight.issue.needs_review";
  const step = issue?.step_id ? workflowTemplateNodes().find((node) => node.id === issue.step_id) : undefined;
  return step ? t(key, { step: stepTitle(step) }) : t(key);
}

function preflightReasonText(reason) {
  const key = {
    owner_review: "preview.workflow.preflight.reason.owner_review",
    ready_to_start: "preview.workflow.preflight.reason.ready_to_start",
    remove_blocker: "preview.workflow.preflight.reason.remove_blocker"
  }[reason] || "preview.workflow.preflight.reason.ready_to_start";
  return t(key);
}

function preflightDueWindowText(value) {
  if (!value || value === "not_set") return t("preview.workflow.preflight.due.notSet");
  const minutes = Number(String(value).replace(/m$/, ""));
  if (!Number.isFinite(minutes)) return t("preview.workflow.preflight.due.notSet");
  if (minutes >= 1440 && minutes % 1440 === 0) {
    return t("preview.workflow.preflight.due.days", { count: minutes / 1440 });
  }
  if (minutes >= 60 && minutes % 60 === 0) {
    return t("preview.workflow.preflight.due.hours", { count: minutes / 60 });
  }
  return t("preview.workflow.preflight.due.minutes", { count: minutes });
}

function workflowAddStepForm(selected, nodes) {
  const templateId = selected?.templateId || workflowTemplate()?.id || "payroll-close";
  return `<details class="workflow-add-step" data-workflow-add-panel="true">
    <summary>${icon("plus-circle")}${t("preview.workflow.add.title")}</summary>
    <form class="workflow-editor-form" data-workflow-add-step="true" data-workflow-template-id="${escapeText(templateId)}">
      <div class="workflow-editor-grid">
        ${workflowInput("title", "preview.workflow.edit.titleField", "", true, t("preview.workflow.add.titleHint"))}
        ${workflowInput("action", "preview.workflow.edit.actionField", "", true, t("preview.workflow.add.actionHint"))}
        ${workflowSelect("owner", selected?.owner || "payroll_manager", workflowOwnerOptions, "preview.workflow.edit.ownerField", ownerText)}
        ${workflowSelect("lane", selected?.lane || "operation", workflowLaneOptions, "preview.workflow.edit.laneField", (value) => t(`preview.workflow.lanes.${value}`))}
        ${workflowSelect("node_type", selected?.nodeType || "action", workflowNodeTypeOptions, "preview.workflow.edit.typeField", (value) => t(`preview.workflow.nodeType.${value}`))}
        ${workflowSelect("after_step_id", selected?.id || nodes[0]?.id || "", workflowPlacementOptions(nodes), "preview.workflow.edit.afterField", (value) => workflowPlacementText(value, nodes))}
        ${workflowNumberInput("slo_minutes", "preview.workflow.edit.sloMinutes", 180, false)}
        ${workflowOptionalSelect("escalation_role", selected?.escalationRole || workflowDefaultEscalationRole(selected?.owner || "payroll_manager"), workflowOwnerOptions, "preview.workflow.edit.escalationRole", ownerText)}
        ${workflowInput("condition_rule", "preview.workflow.edit.conditionRule", "", false, t("preview.workflow.edit.conditionHint"))}
        ${workflowSelect("permission_data_class", "sensitive", workflowPermissionClassOptions, "preview.workflow.edit.permissionDataClass", workflowPermissionClassText)}
      </div>
      <button class="btn primary" type="submit">${t("preview.workflow.add.save")}</button>
    </form>
  </details>`;
}

function workflowCanvas(nodes, selected) {
  const lanes = [
    ["source", t("preview.workflow.lanes.source")],
    ["rule", t("preview.workflow.lanes.rule")],
    ["operation", t("preview.workflow.lanes.operation")],
    ["approval", t("navigation.approval.label")],
    ["record", t("navigation.archive.label")]
  ];
  const edges = workflowTemplateEdges(nodes);
  return `<div class="workflow-canvas ${state.workflowConnectFromId ? "connecting" : ""}${tutorialAnchorClass("workflow-canvas")}" data-workflow-canvas="true" data-tutorial-anchor="workflow-canvas" aria-label="${t("preview.workflow.canvas.aria")}">
    ${workflowCanvasLines(nodes, edges)}
    ${workflowMiniMap(nodes, edges, selected)}
    <div class="workflow-lanes-background" aria-hidden="true">
      ${lanes.map(([lane, label]) => `<section class="workflow-lane workflow-lane-${lane}">
        <div class="workflow-lane-title">${escapeText(label)}</div>
      </section>`).join("")}
    </div>
    <div class="workflow-graph-layer">
      ${nodes.map((node) => workflowNode(node, selected?.id === node.id)).join("")}
    </div>
  </div>`;
}

function workflowTemplateEdges(nodes) {
  const visibleIds = new Set(nodes.map((node) => node.id));
  const stepEdges = nodes.flatMap((node) =>
    (node.nextStepIds || []).map((nextId) => ({
      from: node.id,
      to: nextId
    }))
  );
  return stepEdges.filter((edge) => visibleIds.has(edge.from) && visibleIds.has(edge.to));
}

function workflowCanvasPosition(node, nodes) {
  if (!node) return { x: 50, y: 50 };
  return {
    x: Number.isFinite(node.positionX) ? node.positionX : workflowLanePositionX(node.lane),
    y: Number.isFinite(node.positionY) ? node.positionY : 50
  };
}

function workflowCanvasLines(nodes, edges) {
  return `<svg class="workflow-canvas-lines" preserveAspectRatio="none" viewBox="0 0 100 100" aria-hidden="true">
    ${edges.map((edge) => {
      const from = workflowCanvasPosition(nodes.find((node) => node.id === edge.from), nodes);
      const to = workflowCanvasPosition(nodes.find((node) => node.id === edge.to), nodes);
      const mid = (from.x + to.x) / 2;
      return `<path d="M${from.x} ${from.y} C${mid} ${from.y} ${mid} ${to.y} ${to.x} ${to.y}" />`;
    }).join("")}
  </svg>`;
}

function workflowMiniMap(nodes, edges, selected) {
  return `<div class="workflow-minimap" aria-label="${t("preview.workflow.minimap.aria")}">
    <svg viewBox="0 0 100 100" role="img" aria-label="${t("preview.workflow.minimap.aria")}">
      ${edges.map((edge) => {
        const from = workflowCanvasPosition(nodes.find((node) => node.id === edge.from), nodes);
        const to = workflowCanvasPosition(nodes.find((node) => node.id === edge.to), nodes);
        return `<line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" />`;
      }).join("")}
      ${nodes.map((node) => {
        const point = workflowCanvasPosition(node, nodes);
        return `<circle class="${selected?.id === node.id ? "selected" : ""}" cx="${point.x}" cy="${point.y}" r="3" />`;
      }).join("")}
    </svg>
  </div>`;
}

function workflowNode(node, selected) {
  const templateId = node.templateId || "payroll-close";
  const position = workflowCanvasPosition(node);
  const isConnectSource = state.workflowConnectFromId === node.id;
  return `<article class="workflow-node ${selected ? "selected" : ""} ${isConnectSource ? "connect-source" : ""}" data-workflow-node-id="${node.id}" data-workflow-template-id="${templateId}" style="--tone:${toneColor(node.tone)};--node-x:${position.x};--node-y:${position.y};">
    <button class="workflow-node-handle workflow-node-handle-in" type="button" data-workflow-connect-to="true" data-workflow-template-id="${templateId}" data-workflow-step-id="${node.id}" aria-label="${t("preview.workflow.connect.to", { step: stepTitle(node) })}"></button>
    <button class="workflow-node-select" type="button" data-work-step-key="${node.id}" aria-pressed="${selected}">
      <span class="work-action-icon">${icon(workStepIcon(node))}</span>
      <span class="workflow-node-type">${t(`preview.workflow.nodeType.${node.nodeType}`)}</span>
      <span class="workflow-node-status">${badge(statusText(node.status), node.tone)}</span>
      <strong>${escapeText(stepTitle(node))}</strong>
      <small>${escapeText(ownerText(node.owner))}</small>
    </button>
    <div class="workflow-node-actions">
      <button class="workflow-node-action" type="button" data-workflow-connect-from="true" data-workflow-template-id="${templateId}" data-workflow-step-id="${node.id}" aria-label="${t("preview.workflow.connect.from", { step: stepTitle(node) })}">${icon("route")}</button>
      <button class="workflow-node-action" type="button" data-workflow-execute-step="true" data-workflow-template-id="${templateId}" data-workflow-step-id="${node.id}" aria-label="${t("preview.workflow.execute.button")}">${icon("check-circle-2")}</button>
    </div>
    <button class="workflow-node-handle workflow-node-handle-out" type="button" data-workflow-connect-from="true" data-workflow-template-id="${templateId}" data-workflow-step-id="${node.id}" aria-label="${t("preview.workflow.connect.from", { step: stepTitle(node) })}"></button>
  </article>`;
}

function workflowNodeInspector(node) {
  return `<div class="detail-panel">
    <div class="detail-head"><div><span class="helper">${t("preview.workflow.detail.selected")}</span><strong>${escapeText(stepTitle(node))}</strong></div>${badge(statusText(node.status), node.tone)}</div>
    <div class="detail-grid">
      <div class="detail-item"><span class="helper">${t("preview.workflow.detail.nodeType")}</span><strong>${t(`preview.workflow.nodeType.${node.nodeType}`)}</strong></div>
      <div class="detail-item"><span class="helper">${t("screens.workQueueDetail.owner")}</span><strong>${escapeText(ownerText(node.owner))}</strong></div>
      <div class="detail-item"><span class="helper">${t("preview.workflow.detail.slo")}</span><strong>${escapeText(workflowSloText(node.sloMinutes))}</strong></div>
      <div class="detail-item"><span class="helper">${t("preview.workflow.detail.escalation")}</span><strong>${escapeText(workflowEscalationText(node))}</strong></div>
      <div class="detail-item"><span class="helper">${t("preview.workflow.detail.permission")}</span><strong>${escapeText(workflowPermissionText(node))}</strong></div>
      <div class="detail-item"><span class="helper">${t("preview.workflow.detail.condition")}</span><strong>${escapeText(workflowConditionText(node))}</strong></div>
      <div class="detail-item"><span class="helper">${t("preview.workflow.detail.action")}</span><strong>${escapeText(stepAction(node))}</strong></div>
    </div>
    <div class="workflow-edit-controls" aria-label="${t("preview.workflow.edit.status")}">
      <span class="helper">${t("preview.workflow.edit.title")}</span>
      <div class="action-row">
        ${workflowStatusButton(node, "waiting", "preview.workflow.edit.markWaiting")}
        ${workflowStatusButton(node, "needs_attention", "preview.workflow.edit.markNeedsAttention")}
        ${workflowStatusButton(node, "completed", "preview.workflow.edit.markCompleted")}
        ${workflowStatusButton(node, "blocked", "preview.workflow.edit.markBlocked")}
      </div>
    </div>
    <div class="workflow-edit-controls" aria-label="${t("preview.workflow.move.title")}">
      <span class="helper">${t("preview.workflow.move.title")}</span>
      <div class="action-row">
        ${workflowMoveButton(node, -10, 0, "preview.workflow.move.left")}
        ${workflowMoveButton(node, 10, 0, "preview.workflow.move.right")}
        ${workflowMoveButton(node, 0, -10, "preview.workflow.move.up")}
        ${workflowMoveButton(node, 0, 10, "preview.workflow.move.down")}
      </div>
    </div>
    ${workflowEdgeControls(node, workflowTemplateNodes())}
    ${workflowRuntimePanel(node)}
    <form class="workflow-editor-form" data-workflow-editor="true" data-workflow-template-id="${node.templateId || "payroll-close"}" data-workflow-step-id="${node.id}">
      <div class="workflow-editor-grid">
        ${workflowInput("title", "preview.workflow.edit.titleField", stepTitle(node), true)}
        ${workflowInput("action", "preview.workflow.edit.actionField", stepAction(node), true)}
        ${workflowSelect("status", node.status, workflowStatusOptions, "preview.workflow.edit.statusField", statusText)}
        ${workflowSelect("owner", node.owner, workflowOwnerOptions, "preview.workflow.edit.ownerField", ownerText)}
        ${workflowSelect("lane", node.lane, workflowLaneOptions, "preview.workflow.edit.laneField", (value) => t(`preview.workflow.lanes.${value}`))}
        ${workflowSelect("node_type", node.nodeType, workflowNodeTypeOptions, "preview.workflow.edit.typeField", (value) => t(`preview.workflow.nodeType.${value}`))}
        ${workflowSelect("after_step_id", workflowPreviousStepId(node), workflowPlacementOptions(workflowTemplateNodes(), node.id), "preview.workflow.edit.afterField", (value) => workflowPlacementText(value, workflowTemplateNodes()))}
        ${workflowNumberInput("slo_minutes", "preview.workflow.edit.sloMinutes", node.sloMinutes || "", false)}
        ${workflowOptionalSelect("escalation_role", node.escalationRole || "", workflowOwnerOptions, "preview.workflow.edit.escalationRole", ownerText)}
        ${workflowInput("condition_rule", "preview.workflow.edit.conditionRule", workflowConditionInputValue(node), false, t("preview.workflow.edit.conditionHint"))}
        ${workflowSelect("permission_data_class", workflowPermissionDataClass(node) || "sensitive", workflowPermissionClassOptions, "preview.workflow.edit.permissionDataClass", workflowPermissionClassText)}
        ${workflowSelect("permission_object_scope", workflowPermissionObjectScope(node) || "payroll_period", workflowObjectScopeOptions, "preview.workflow.edit.permissionObjectScope", workflowObjectScopeText)}
        ${workflowInput("position_x", "preview.workflow.edit.positionX", node.positionX, true)}
        ${workflowInput("position_y", "preview.workflow.edit.positionY", node.positionY, true)}
      </div>
      ${workflowMultiNextControls(node, workflowTemplateNodes())}
      <div class="action-row">
        <button class="btn primary" type="submit">${t("preview.workflow.edit.save")}</button>
        <button class="btn secondary" type="button" data-workflow-execute-step="true" data-workflow-template-id="${node.templateId || "payroll-close"}" data-workflow-step-id="${node.id}">${t("preview.workflow.execute.button")}</button>
        <button class="btn danger" type="button" data-workflow-delete-step="true" data-workflow-template-id="${node.templateId || "payroll-close"}" data-workflow-step-id="${node.id}">${t("preview.workflow.edit.delete")}</button>
      </div>
    </form>
  </div>`;
}

function workflowRuntimePanel(node) {
  const events = workflowRuntimeEventsForNode(node.id);
  if (!events.length) {
    return `<div class="workflow-runtime-panel empty-runtime"><strong>${t("preview.workflow.runtime.title")}</strong><span class="helper">${t("preview.workflow.runtime.empty")}</span></div>`;
  }
  const event = events[0];
  const operations = Array.isArray(event.data_operations) ? event.data_operations : [];
  const records = workflowDataRecordsForNode(node.id);
  return `<div class="workflow-runtime-panel" aria-label="${t("preview.workflow.runtime.aria")}">
    <div class="runtime-head"><strong>${t("preview.workflow.runtime.title")}</strong>${badge(statusText(event.status_after || "completed"), "ready")}</div>
    ${operations.length ? `<div class="runtime-operation-list">${operations.map((operation) => `
      <article class="runtime-operation">
        <span>${badge(workflowOperationStatusText(operation.status), operation.status === "planned" || operation.status === "queued" ? "attention" : "ready")}</span>
        <strong>${escapeText(workflowOperationTypeText(operation.operation_type))}</strong>
        <small>${escapeText(workflowOperationMeta(operation))}</small>
      </article>
    `).join("")}</div>` : `<span class="helper">${t("preview.workflow.runtime.empty")}</span>`}
    ${records.length ? `<span class="helper">${t("preview.workflow.runtime.dataRecord", { count: records.length })}</span>` : ""}
  </div>`;
}

function workflowVersionHistory(templateId) {
  const template = workflowTemplate();
  const currentVersion = Number(template?.version || 0);
  const versions = (state.workflowTemplateVersions || [])
    .filter((record) => record.template_id === templateId)
    .sort((left, right) => Number(right.version || 0) - Number(left.version || 0))
    .slice(0, 6);
  if (!versions.length) {
    return `<section class="workflow-history-panel"><strong>${t("preview.workflow.history.title")}</strong><span class="helper">${t("preview.workflow.history.empty")}</span></section>`;
  }
  return `<section class="workflow-history-panel" aria-label="${t("preview.workflow.history.aria")}">
    <div class="runtime-head"><strong>${t("preview.workflow.history.title")}</strong>${badge(t("preview.workflow.history.count", { count: versions.length }), "neutral")}</div>
    <div class="workflow-history-list">
      ${versions.map((record) => {
        const version = Number(record.version || 0);
        const isCurrent = version === currentVersion;
        return `<article class="workflow-history-item ${isCurrent ? "current" : ""}">
          <div>
            <strong>${t("preview.workflow.history.version", { version })}</strong>
            <small>${workflowChangeSummaryText(record.change_summary)} · ${t("preview.workflow.history.stepCount", { count: Array.isArray(record.steps) ? record.steps.length : 0 })}</small>
          </div>
          ${isCurrent
            ? badge(t("preview.workflow.history.current"), "ready")
            : `<button class="btn ghost" type="button" data-workflow-rollback-version="${version}" data-workflow-template-id="${escapeText(templateId)}">${t("preview.workflow.rollback.button")}</button>`}
        </article>`;
      }).join("")}
    </div>
  </section>`;
}

function workflowChangeSummaryText(value) {
  return value
    ? catalogText(`preview.workflow.history.change.${catalogId(value)}`, t("preview.workflow.history.change.updated"))
    : t("preview.workflow.history.change.updated");
}

function workflowRuntimeEventsForNode(stepId) {
  return (state.workflowRuntimeEvents || [])
    .filter((event) => event.step_id === stepId)
    .sort((left, right) => Number(right.updated_at_unix || 0) - Number(left.updated_at_unix || 0));
}

function workflowDataRecordsForNode(stepId) {
  return (state.workflowDataRecords || [])
    .filter((record) => record.step_id === stepId)
    .sort((left, right) => Number(right.updated_at_unix || 0) - Number(left.updated_at_unix || 0));
}

function workflowOperationTypeText(type) {
  return catalogText(`preview.workflow.operation.${catalogId(type)}`, type);
}

function workflowOperationStatusText(status) {
  return catalogText(`preview.workflow.operationStatus.${catalogId(status)}`, status);
}

function workflowOperationMeta(operation) {
  const metadata = operation.metadata || {};
  const parts = [
    metadata.scope_period ? t("preview.workflow.runtime.period", { period: metadata.scope_period }) : "",
    metadata.scope_workplace ? t("preview.workflow.runtime.workplace", { workplace: metadata.scope_workplace }) : "",
    operation.record_count ? t("preview.workflow.runtime.records", { count: operation.record_count }) : ""
  ].filter(Boolean);
  return parts.join(" · ") || t("preview.workflow.runtime.recorded");
}

function workflowSloText(minutes) {
  return minutes ? t("preview.workflow.slo.minutes", { minutes }) : t("preview.workflow.slo.none");
}

function workflowEscalationText(node) {
  return node.escalationRole ? ownerText(node.escalationRole) : t("preview.workflow.edit.none");
}

function workflowConditionRule(node) {
  return node?.conditionExpression?.rule || "";
}

function workflowConditionInputValue(node) {
  return workflowConditionRule(node) || (messageExists(`preview.workflow.condition.${node?.id}`) ? t(`preview.workflow.condition.${node.id}`) : "");
}

function workflowConditionText(node) {
  return workflowConditionRule(node) || (messageExists(`preview.workflow.condition.${node?.id}`) ? t(`preview.workflow.condition.${node.id}`) : t("preview.workflow.edit.none"));
}

function workflowPermissionDataClass(node) {
  return node?.permissionScope?.data_class || "";
}

function workflowPermissionObjectScope(node) {
  return node?.permissionScope?.object_scope || "";
}

function workflowObjectScopeText(value) {
  return catalogText(`preview.workflow.objectScope.${catalogId(value)}`, value);
}

function workflowPermissionClassText(value) {
  return t(`preview.workflow.permission.${value}`);
}

function workflowPermissionText(node) {
  const dataClass = workflowPermissionDataClass(node);
  const objectScope = workflowPermissionObjectScope(node);
  return [dataClass ? workflowPermissionClassText(dataClass) : "", objectScope ? workflowObjectScopeText(objectScope) : ""]
    .filter(Boolean)
    .join(" · ") || t("preview.workflow.edit.none");
}

function workflowSloFromForm(formData) {
  const raw = String(formData.get("slo_minutes") || "").trim();
  if (!raw) return null;
  const numeric = Math.round(Number(raw));
  if (!Number.isFinite(numeric)) return null;
  return Math.max(1, Math.min(10080, numeric));
}

function workflowConditionFromForm(formData) {
  const rule = String(formData.get("condition_rule") || "").trim();
  return rule ? { rule } : {};
}

function workflowPermissionScopeFromForm(formData) {
  return workflowPermissionScopeInput(
    String(formData.get("permission_data_class") || "").trim(),
    String(formData.get("permission_object_scope") || "").trim()
  );
}

function workflowPermissionScopeInput(dataClass, objectScope = "payroll_period") {
  const scope = {};
  if (dataClass) {
    scope.data_class = dataClass;
    scope.tenant_required = "true";
  }
  if (objectScope) scope.object_scope = objectScope;
  return scope;
}

function workflowOptionalFormValue(value) {
  const text = String(value || "").trim();
  return text || null;
}

function workflowInput(name, labelKey, value, required = false, hint = "") {
  const hintId = hint ? `workflow-input-${escapeText(name)}-hint` : "";
  return `<label class="field">
    <span>${t(labelKey)}</span>
    <input name="${escapeText(name)}" value="${escapeText(value || "")}" ${hintId ? `aria-describedby="${hintId}"` : ""} ${required ? "required" : ""} />
    ${hint ? `<small id="${hintId}" class="field-hint">${escapeText(hint)}</small>` : ""}
  </label>`;
}

function workflowNumberInput(name, labelKey, value, required = false) {
  return `<label class="field">
    <span>${t(labelKey)}</span>
    <input name="${escapeText(name)}" type="number" min="1" max="10080" step="1" value="${escapeText(value || "")}" ${required ? "required" : ""} />
  </label>`;
}

function workflowSelect(name, value, options, labelKey, labelForValue) {
  return `<label class="field">
    <span>${t(labelKey)}</span>
    <select name="${escapeText(name)}">
      ${options.map((option) => `<option value="${escapeText(option)}" ${option === value ? "selected" : ""}>${escapeText(labelForValue(option))}</option>`).join("")}
    </select>
  </label>`;
}

function workflowOptionalSelect(name, value, options, labelKey, labelForValue) {
  return `<label class="field">
    <span>${t(labelKey)}</span>
    <select name="${escapeText(name)}">
      <option value="" ${value ? "" : "selected"}>${t("preview.workflow.edit.none")}</option>
      ${options.map((option) => `<option value="${escapeText(option)}" ${option === value ? "selected" : ""}>${escapeText(labelForValue(option))}</option>`).join("")}
    </select>
  </label>`;
}

function workflowPlacementOptions(nodes, excludeId) {
  return nodes
    .filter((node) => node.id !== excludeId)
    .map((node) => node.id);
}

function workflowNextOptions(nodes, excludeId) {
  return ["", ...workflowPlacementOptions(nodes, excludeId)];
}

function workflowPlacementText(value, nodes) {
  return stepTitle(nodes.find((node) => node.id === value) || { id: value });
}

function workflowNextText(value, nodes) {
  if (!value) return t("preview.workflow.edit.noNext");
  return workflowPlacementText(value, nodes);
}

function workflowMultiNextControls(node, nodes) {
  const selected = new Set(node.nextStepIds || []);
  const options = workflowPlacementOptions(nodes, node.id);
  return `<fieldset class="workflow-next-field">
    <legend>${t("preview.workflow.edit.nextField")}</legend>
    <span class="helper">${t("preview.workflow.edit.multiNextHelp")}</span>
    <div class="workflow-next-options">
      ${options.map((id) => `<label class="field-check">
        <input type="checkbox" name="next_step_ids" value="${escapeText(id)}" ${selected.has(id) ? "checked" : ""} />
        <span>${escapeText(workflowPlacementText(id, nodes))}</span>
      </label>`).join("")}
    </div>
  </fieldset>`;
}

function workflowEdgeControls(node, nodes) {
  const connected = (node.nextStepIds || [])
    .map((id) => nodes.find((candidate) => candidate.id === id))
    .filter(Boolean);
  return `<div class="workflow-edge-controls">
    <div class="runtime-head">
      <strong>${t("preview.workflow.connect.title")}</strong>
      <button class="btn ghost" type="button" data-workflow-connect-from="true" data-workflow-template-id="${node.templateId || "payroll-close"}" data-workflow-step-id="${node.id}">${t("preview.workflow.connect.start")}</button>
    </div>
    ${connected.length ? `<div class="workflow-edge-list">${connected.map((target) => `
      <span class="workflow-edge-chip">${icon("route")}${escapeText(stepTitle(target))}
        <button type="button" data-workflow-disconnect="true" data-workflow-template-id="${node.templateId || "payroll-close"}" data-workflow-step-id="${node.id}" data-workflow-next-step-id="${target.id}" aria-label="${t("preview.workflow.connect.remove", { step: stepTitle(target) })}">×</button>
      </span>
    `).join("")}</div>` : `<span class="helper">${t("preview.workflow.connect.empty")}</span>`}
  </div>`;
}

function workflowPreviousStepId(node) {
  const nodes = workflowTemplateNodes();
  const parent = nodes.find((candidate) => (candidate.nextStepIds || []).includes(node.id));
  return parent?.id || nodes.find((candidate) => candidate.id !== node.id)?.id || "";
}

function workflowStatusButton(node, status, labelKey) {
  return `<button class="btn ghost" data-workflow-status="${status}" data-workflow-template-id="${node.templateId || "payroll-close"}" data-workflow-step-id="${node.id}">${t(labelKey)}</button>`;
}

function workflowMoveButton(node, deltaX, deltaY, labelKey) {
  return `<button class="btn ghost" data-workflow-move-step="true" data-workflow-template-id="${node.templateId || "payroll-close"}" data-workflow-step-id="${node.id}" data-workflow-move-x="${deltaX}" data-workflow-move-y="${deltaY}">${t(labelKey)}</button>`;
}

function adminCards(items) {
  const selectedKey = state.selectedAdminKey || items[0]?.id || "";
  return `<div class="admin-setup-grid">${adminSetupGroups(items).map((group) => `
    <button aria-pressed="${group.items.some((item) => selectedKey === item.id)}" class="admin-setup-card select-card ${group.items.some((item) => selectedKey === item.id) ? "selected" : ""}" data-admin-key="${group.primary?.id || ""}" style="--tone:${toneColor(group.tone)}">
      <span class="work-action-icon">${icon(group.icon)}</span>
      <span class="admin-setup-main"><strong>${t(`preview.admin.group.${group.id}.title`)}</strong><small>${group.primary ? escapeText(group.primary.title) : t(`preview.admin.group.${group.id}.ready`)}</small></span>
      ${badge(group.primary?.status || t("preview.admin.ready.title"), group.tone)}
    </button>
  `).join("")}</div>`;
}

function adminSetupGroups(items) {
  const groups = [
    {
      icon: "building-2",
      id: "setup",
      items: items.filter((item) => /scope|payroll/i.test(item.id))
    },
    {
      icon: "shield-check",
      id: "security",
      items: items.filter((item) => /access|auth|sign/i.test(item.id))
    },
    {
      icon: "settings",
      id: "operations",
      items: []
    }
  ];
  const claimedIds = new Set(groups.flatMap((group) => group.items.map((item) => item.id)));
  groups[2].items = items.filter((item) => !claimedIds.has(item.id));
  return groups.map((group) => {
    const primary = group.items.find((item) => item.tone === "blocked") || group.items[0];
    return {
      ...group,
      primary,
      tone: primary?.tone || "ready"
    };
  });
}

function adminDetail(item) {
  return `<div class="detail-panel${tutorialAnchorClass("admin-detail")}" data-tutorial-anchor="admin-detail">
    <div class="detail-head"><div><span class="helper">${t("preview.admin.detail.selected")}</span><strong>${escapeText(item.title)}</strong></div>${badge(item.status, item.tone)}</div>
    <div class="detail-grid">
      <div class="detail-item"><span class="helper">${t("screens.workQueueDetail.owner")}</span><strong>${escapeText(item.owner)}</strong></div>
      <div class="detail-item"><span class="helper">${t("preview.workflow.detail.action")}</span><strong>${escapeText(item.meta)}</strong></div>
    </div>
  </div>`;
}

function employeeTable() {
  if (!state.hrEmployees.length) return "";
  return `<div class="employee-table" role="table" aria-label="${t("preview.hr.people.title")}">
    ${state.hrEmployees.map((employee) => `
      <button class="employee-row ${state.selectedEmployeeId === employee.id ? "selected" : ""}" data-employee-id="${employee.id}" role="row">
        <span><strong>${escapeText(employee.name)}</strong><small>${escapeText(employee.team)}</small></span>
        <span>${escapeText(employee.role)}</span>
        ${badge(employeeStatusText(employee.status), employeeStatusTone(employee.status))}
      </button>
    `).join("")}
  </div>`;
}

function employeeDetail(employee) {
  return `<div class="detail-panel employee-detail">
    <div class="detail-head"><div><span class="helper">${t("preview.hr.people.selected")}</span><strong>${escapeText(employee.name)}</strong></div>${badge(employeeStatusText(employee.status), employeeStatusTone(employee.status))}</div>
    <div class="detail-grid">
      <div class="detail-item"><span class="helper">${t("preview.hr.form.team")}</span><strong>${escapeText(employee.team)}</strong></div>
      <div class="detail-item"><span class="helper">${t("preview.hr.form.role")}</span><strong>${escapeText(employee.role)}</strong></div>
    </div>
    <div class="action-row">
      ${["active", "on_leave", "offboarding"].map((status) => `<button class="btn ghost" data-employee-status="${status}" data-employee-id="${employee.id}">${employeeStatusText(status)}</button>`).join("")}
      <button class="btn danger" data-remove-employee="${employee.id}">${t("preview.hr.actions.removeEmployee")}</button>
    </div>
  </div>`;
}

function employeeStatusText(status) {
  return catalogText(`preview.hr.status.${catalogId(status)}`, status);
}

function employeeStatusTone(status) {
  return {
    active: "ready",
    on_leave: "attention",
    offboarding: "blocked"
  }[status] || "neutral";
}

function archiveStatusText(status) {
  return catalogText(`preview.archive.intake.status.${catalogId(status)}`, status);
}

function archiveNextActionText(action) {
  return catalogText(`preview.archive.intake.action.${catalogId(action)}`, action);
}

function archiveFamilyText(family) {
  return catalogText(`preview.archive.intake.family.${catalogId(family)}`, family);
}

function archiveDatabaseTargetText(target) {
  return catalogText(`preview.archive.intake.target.${catalogId(target)}`, target || "");
}

function archiveGuidanceText(item) {
  return catalogText(`preview.archive.intake.guidance.${catalogId(item.code)}`, item.code).replace("{column}", item.column || t("preview.archive.intake.column.unspecified"));
}

function archiveAnomalyText(item) {
  return catalogText(`preview.archive.intake.anomaly.${catalogId(item.code)}`, item.code);
}

function archiveFileMeta(intake) {
  return t("preview.archive.intake.fileMeta", {
    family: archiveFamilyText(intake.family),
    size: fileSizeLabel(intake.file_size_bytes)
  });
}

function archiveGuidanceList(intake) {
  const items = [
    ...(intake.guidance_items || []).map((item) => ({ ...item, kind: "guidance" })),
    ...(intake.anomalies || []).map((item) => ({ ...item, kind: "anomaly" }))
  ];
  if (!items.length) return "";
  return `<div class="intake-guidance-list">
    ${items.slice(0, 4).map((item) => `
      <span class="intake-issue-chip">
        <span>${escapeText(item.kind === "guidance" ? archiveGuidanceText(item) : archiveAnomalyText(item))}</span>
        ${archiveIssueAction(intake, item)}
      </span>
    `).join("")}
  </div>`;
}

function archiveIssueAction(intake, item) {
  if (["choose_business_area", "upload_readable_sheet"].includes(item.code)) {
    return `<small>${t("preview.archive.intake.issue.needsInput")}</small>`;
  }
  return `<button type="button" class="text-button compact" data-intake-resolve="true" data-intake-id="${escapeAttribute(intake.id)}" data-issue-type="${escapeAttribute(item.kind)}" data-issue-code="${escapeAttribute(item.code)}" data-issue-column="${escapeAttribute(item.column || "")}">${t("preview.archive.intake.issue.resolve")}</button>`;
}

function archiveVersionList(intake) {
  const sourceVersions = intake.source_versions || [];
  const recoveryPoints = (intake.recovery_points || []).filter((point) => point.recovery_status === "available");
  const syncItems = intake.source_sync_items || [];
  if (!sourceVersions.length && !recoveryPoints.length && !syncItems.length) return "";
  return `<div class="intake-version-list" aria-label="${t("preview.archive.intake.version.aria")}">
    ${sourceVersions.slice(0, 2).map((version) => `
      <span class="intake-issue-chip">
        <span>${t("preview.archive.intake.version.source", {
          version: version.version,
          size: fileSizeLabel(version.file_size_bytes)
        })}</span>
      </span>
    `).join("")}
    ${recoveryPoints.slice(0, 3).map((point) => `
      <span class="intake-issue-chip">
        <span>${t("preview.archive.intake.version.point", {
          action: archiveRecoveryActionText(point.action),
          key: point.business_key
        })}</span>
        <button type="button" class="text-button compact" data-intake-rollback="true" data-intake-id="${escapeAttribute(intake.id)}" data-recovery-point-id="${escapeAttribute(point.id)}">${t("preview.archive.intake.version.restore")}</button>
      </span>
    `).join("")}
    ${syncItems.slice(0, 2).map((item) => `
      <span class="intake-issue-chip">
        <span>${t("preview.archive.intake.version.sync", {
          operation: archiveSyncOperationText(item.operation),
          status: archiveSyncStatusText(item.status)
        })}</span>
        ${item.status === "pending" ? `<button type="button" class="text-button compact" data-intake-source-sync="true" data-intake-id="${escapeAttribute(intake.id)}">${t("preview.archive.intake.version.syncAction")}</button>` : ""}
      </span>
    `).join("")}
  </div>`;
}

function archiveRecoveryActionText(action) {
  return catalogText(`preview.archive.intake.version.action.${catalogId(action)}`, action || "");
}

function archiveSyncOperationText(operation) {
  return catalogText(`preview.archive.intake.version.operation.${catalogId(operation)}`, operation || "");
}

function archiveSyncStatusText(status) {
  return catalogText(`preview.archive.intake.version.status.${catalogId(status)}`, status || "");
}

function archiveMappingStatusText(status) {
  return catalogText(`preview.archive.intake.mapping.status.${catalogId(status)}`, status || "");
}

function archiveValueShapeText(shape) {
  return catalogText(`preview.archive.intake.mapping.shape.${catalogId(shape)}`, shape || "");
}

function archiveTargetFieldText(field) {
  return catalogText(`preview.archive.intake.mapping.field.${catalogId(field)}`, field || "");
}

function archiveTargetFields(target) {
  const common = ["source_payload", "ignored"];
  const fields = {
    hr_employee_staging: [
      "employee_external_id", "display_name", "department", "workplace", "job_duty", "role_title",
      "base_hourly_rate", "regular_hourly_rate", "allowance", "national_pension", "health_insurance",
      "income_tax", "annual_leave_accrued", "annual_leave_used", "annual_leave_balance",
      "resident_registration_number", "hire_date", "insurance_start_date", "termination_date",
      "insurance_end_date", "address", "mobile_phone", "email", "severance_interim_settlement",
      "bank_name", "bank_account", "certification", "source_row_number", "employment_status"
    ],
    hr_attendance_staging: [
      "employee_external_id", "display_name", "work_date", "work_hours", "attendance_status"
    ],
    payroll_input_staging: [
      "employee_external_id", "display_name", "department", "workplace", "hire_date", "termination_date",
      "base_hourly_rate", "regular_hourly_rate", "base_pay", "gross_pay", "deduction_total",
      "overtime_hours", "shift_hours", "night_hours", "holiday_hours", "position_allowance",
      "labor_cost", "supply_amount", "vat", "source_row_number"
    ]
  }[target] || [];
  return [...fields, ...common];
}

function archiveAdmissionAction(intake) {
  const admissibleTargets = ["hr_employee_staging", "hr_attendance_staging", "payroll_input_staging"];
  if (!admissibleTargets.includes(intake.database_target)) {
    return "";
  }
  if (intake.status === "ready_for_staging" && intake.postgres_ready) {
    return `<button type="button" class="primary-mini" data-intake-admit="true" data-intake-id="${escapeAttribute(intake.id)}">${t("preview.archive.intake.admission.action")}</button>`;
  }
  if (["admitted", "rejected"].includes(intake.status)) {
    return `<button type="button" class="primary-mini danger" data-intake-rollback="true" data-intake-id="${escapeAttribute(intake.id)}">${t("preview.archive.intake.rollback.action")}</button>`;
  }
  return "";
}

function archiveStatusTone(status) {
  return {
    accepted: "ready",
    admitted: "ready",
    archived: "ready",
    needs_review: "blocked",
    needs_guidance: "blocked",
    ready_for_staging: "ready",
    received: "attention",
    rejected: "blocked",
    translating: "attention"
  }[status] || "neutral";
}

function fileSizeLabel(bytes) {
  const size = Number(bytes || 0);
  if (size >= 1024 * 1024) return t("preview.archive.intake.fileSize.mb", { size: (size / (1024 * 1024)).toFixed(1) });
  if (size >= 1024) return t("preview.archive.intake.fileSize.kb", { size: Math.ceil(size / 1024) });
  return t("preview.archive.intake.fileSize.bytes", { size });
}

function sectionHead(eyebrow, title, desc, action = "") {
  return `<div class="section-head"><div class="section-title">${eyebrow ? `<span class="eyebrow">${eyebrow}</span>` : ""}<h2>${title}</h2>${desc ? `<p>${desc}</p>` : ""}</div>${action}</div>`;
}

function empty(title, desc) {
  return `<div aria-live="polite" class="empty" role="status"><strong>${title}</strong><span class="helper">${desc}</span></div>`;
}

function toneColor(tone) {
  return {
    ready: palette.success,
    attention: palette.warning,
    blocked: palette.danger,
    neutral: palette.muted
  }[tone] || palette.muted;
}

function bindEvents() {
  document.querySelectorAll("[data-target]").forEach((el) => {
    el.addEventListener("click", () => {
      const target = el.dataset.target;
      const account = selectedAccount();
      state.activeId = account.navigationIds.includes(target) || target === "settings" ? target : account.defaultRoute;
      state.profileMenuOpen = false;
      state.topbarPanel = "";
      render();
      const label = state.activeId === "settings"
        ? t("navigation.settings.label")
        : visibleNavigationItems().find((item) => item.id === state.activeId)?.label || t("screens.module.unavailable.title");
      toast(t("preview.toast.screenChanged", { screen: label }));
    });
  });

  document.querySelectorAll("[data-open-settings]").forEach((el) => {
    el.addEventListener("click", () => {
      state.activeId = "settings";
      state.profileMenuOpen = false;
      state.topbarPanel = "";
      render();
      toast(t("preview.toast.screenChanged", { screen: t("navigation.settings.label") }));
    });
  });

  document.querySelectorAll("[data-topbar-panel]").forEach((el) => {
    el.addEventListener("click", () => {
      state.topbarPanel = state.topbarPanel === el.dataset.topbarPanel ? "" : el.dataset.topbarPanel;
      state.profileMenuOpen = false;
      state.tutorialOpen = false;
      render();
    });
  });

  document.querySelectorAll("[data-open-tutorial]").forEach((el) => {
    el.addEventListener("click", () => {
      state.tutorialOpen = true;
      state.tutorialStepIndex = 0;
      state.profileMenuOpen = false;
      state.topbarPanel = "";
      render();
    });
  });

  document.querySelectorAll("[data-close-tutorial]").forEach((el) => {
    el.addEventListener("click", () => {
      state.tutorialOpen = false;
      render();
    });
  });

  document.querySelectorAll("[data-tutorial-prev]").forEach((el) => {
    el.addEventListener("click", () => {
      state.tutorialStepIndex = Math.max(0, state.tutorialStepIndex - 1);
      render();
    });
  });

  document.querySelectorAll("[data-tutorial-next]").forEach((el) => {
    el.addEventListener("click", () => {
      const total = tutorialSteps(state.activeId).length;
      if (state.tutorialStepIndex >= total - 1) {
        state.tutorialOpen = false;
      } else {
        state.tutorialStepIndex += 1;
      }
      render();
    });
  });

  document.querySelectorAll("[data-profile-toggle]").forEach((el) => {
    el.addEventListener("click", () => {
      state.profileMenuOpen = !state.profileMenuOpen;
      state.topbarPanel = "";
      render();
    });
  });

  document.querySelectorAll("[data-auth-action]").forEach((el) => {
    el.addEventListener("click", async () => {
      state.profileMenuOpen = false;
      await startAuthFlow(el.dataset.authAction);
    });
  });

  document.querySelectorAll("[data-sidebar-theme]").forEach((el) => {
    el.addEventListener("click", async () => {
      const sidebarTheme = sidebarThemeIds.includes(el.dataset.sidebarTheme)
        ? el.dataset.sidebarTheme
        : defaultPreferences.sidebar_theme;
      await mutateUserPreferences({ sidebar_theme: sidebarTheme });
    });
  });

  document.querySelectorAll("[data-language]").forEach((el) => {
    el.addEventListener("click", async () => {
      const locale = supportedLocales.includes(el.dataset.language)
        ? el.dataset.language
        : defaultPreferences.locale;
      await mutateUserPreferences({ locale });
    });
  });

  document.querySelectorAll("[data-preference-key]").forEach((el) => {
    el.addEventListener("click", async () => {
      const key = el.dataset.preferenceKey;
      if (!Object.prototype.hasOwnProperty.call(defaultPreferences, key)) return;
      await mutateUserPreferences({ [key]: el.dataset.preferenceValue });
    });
  });

  document.querySelectorAll("[data-hr-employee-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      await mutateHrEmployee("POST", "/api/hr/v1/employees", {
        name: formData.get("name"),
        team: formData.get("team"),
        role: formData.get("role"),
        status: "active"
      });
    });
  });

  document.querySelectorAll("[data-employee-id]").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedEmployeeId = el.dataset.employeeId;
      render();
      toast(t("preview.hr.toast.selected"));
    });
  });

  document.querySelectorAll("[data-employee-status]").forEach((el) => {
    el.addEventListener("click", async () => {
      state.selectedEmployeeId = el.dataset.employeeId;
      await mutateHrEmployee("PATCH", `/api/hr/v1/employees/${encodeURIComponent(el.dataset.employeeId)}`, {
        status: el.dataset.employeeStatus
      });
    });
  });

  document.querySelectorAll("[data-remove-employee]").forEach((el) => {
    el.addEventListener("click", async () => {
      await mutateHrEmployee("DELETE", `/api/hr/v1/employees/${encodeURIComponent(el.dataset.removeEmployee)}`);
      state.selectedEmployeeId = state.hrEmployees[0]?.id || "";
    });
  });

  document.querySelectorAll("[data-intake-file]").forEach((el) => {
    el.addEventListener("change", async () => {
      const file = el.files?.[0];
      if (!file) return;
      await addArchiveIntake(file);
    });
  });

  document.querySelectorAll("[data-intake-resolve]").forEach((el) => {
    el.addEventListener("click", async () => {
      await resolveArchiveIssue({
        intakeId: el.dataset.intakeId,
        issueType: el.dataset.issueType,
        code: el.dataset.issueCode,
        column: el.dataset.issueColumn
      });
    });
  });

  document.querySelectorAll("[data-intake-field-mapping-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      await updateArchiveFieldMappings(form.dataset.intakeFieldMappingForm, form);
    });
  });

  document.querySelectorAll("[data-intake-admit]").forEach((el) => {
    el.addEventListener("click", async () => {
      await admitArchiveIntake(el.dataset.intakeId);
    });
  });

  document.querySelectorAll("[data-intake-rollback]").forEach((el) => {
    el.addEventListener("click", async () => {
      await rollbackArchiveIntake(el.dataset.intakeId, el.dataset.recoveryPointId || "");
    });
  });

  document.querySelectorAll("[data-intake-source-sync]").forEach((el) => {
    el.addEventListener("click", async () => {
      await syncArchiveSource(el.dataset.intakeId);
    });
  });

  document.querySelectorAll("[data-work-step-key]").forEach((el) => {
    el.addEventListener("click", () => {
      if (el.dataset.homeWorkTarget) return;
      if (state.workflowDragSuppressId === el.dataset.workStepKey) {
        state.workflowDragSuppressId = "";
        return;
      }
      state.selectedWorkStepKey = el.dataset.workStepKey;
      render();
      toast(t("preview.toast.workflowStepSelected"));
    });
  });

  document.querySelectorAll("[data-workflow-node-id]").forEach((el) => {
    el.addEventListener("pointerdown", handleWorkflowNodePointerDown);
  });

  document.querySelectorAll("[data-workflow-connect-from]").forEach((el) => {
    el.addEventListener("click", (event) => {
      event.stopPropagation();
      state.workflowConnectFromId = el.dataset.workflowStepId;
      render();
      toast(t("preview.workflow.connect.started"));
    });
  });

  document.querySelectorAll("[data-workflow-connect-to]").forEach((el) => {
    el.addEventListener("click", async (event) => {
      event.stopPropagation();
      if (!state.workflowConnectFromId) {
        toast(t("preview.workflow.connect.needSource"));
        return;
      }
      await connectWorkflowSteps(
        el.dataset.workflowTemplateId || "payroll-close",
        state.workflowConnectFromId,
        el.dataset.workflowStepId
      );
    });
  });

  document.querySelectorAll("[data-workflow-disconnect]").forEach((el) => {
    el.addEventListener("click", async (event) => {
      event.stopPropagation();
      await disconnectWorkflowSteps(
        el.dataset.workflowTemplateId || "payroll-close",
        el.dataset.workflowStepId,
        el.dataset.workflowNextStepId
      );
    });
  });

  document.querySelectorAll("[data-workflow-cancel-connect]").forEach((el) => {
    el.addEventListener("click", () => {
      state.workflowConnectFromId = "";
      render();
      toast(t("preview.workflow.connect.canceled"));
    });
  });

  document.querySelectorAll("[data-workflow-auto-layout]").forEach((el) => {
    el.addEventListener("click", async () => {
      await autoLayoutWorkflow(el.dataset.workflowTemplateId || "payroll-close");
    });
  });

  document.querySelectorAll("[data-workflow-preflight]").forEach((el) => {
    el.addEventListener("click", async () => {
      await preflightWorkflowTemplate(el.dataset.workflowTemplateId || "payroll-close");
    });
  });

  document.querySelectorAll("[data-workflow-status]").forEach((el) => {
    el.addEventListener("click", async () => {
      await mutateWorkflowStepStatus(
        el.dataset.workflowTemplateId || "payroll-close",
        el.dataset.workflowStepId,
        el.dataset.workflowStatus
      );
    });
  });

  document.querySelectorAll("[data-workflow-editor]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const nextStepIds = formData.getAll("next_step_ids").map((value) => String(value)).filter(Boolean);
      await mutateWorkflowStep(
        form.dataset.workflowTemplateId || "payroll-close",
        form.dataset.workflowStepId,
        {
          title: formData.get("title"),
          action: formData.get("action"),
          status: formData.get("status"),
          owner: formData.get("owner"),
          lane: formData.get("lane"),
          node_type: formData.get("node_type"),
          slo_minutes: workflowSloFromForm(formData),
          escalation_role: workflowOptionalFormValue(formData.get("escalation_role")),
          condition_expression: workflowConditionFromForm(formData),
          permission_scope: workflowPermissionScopeFromForm(formData),
          position_x: clampWorkflowPercent(formData.get("position_x")),
          position_y: clampWorkflowPercent(formData.get("position_y")),
          after_step_id: formData.get("after_step_id"),
          next_step_ids: nextStepIds
        }
      );
    });
  });

  document.querySelectorAll("[data-workflow-move-step]").forEach((el) => {
    el.addEventListener("click", async () => {
      const node = workflowTemplateNodes().find((item) => item.id === el.dataset.workflowStepId);
      if (!node) return;
      await moveWorkflowStep(
        el.dataset.workflowTemplateId || "payroll-close",
        el.dataset.workflowStepId,
        Number(node.positionX) + Number(el.dataset.workflowMoveX || 0),
        Number(node.positionY) + Number(el.dataset.workflowMoveY || 0)
      );
    });
  });

  document.querySelectorAll("[data-workflow-execute-step]").forEach((el) => {
    el.addEventListener("click", async () => {
      await executeWorkflowStep(
        el.dataset.workflowTemplateId || "payroll-close",
        el.dataset.workflowStepId
      );
    });
  });

  document.querySelectorAll("[data-workflow-add-step]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      await addWorkflowStep(
        form.dataset.workflowTemplateId || "payroll-close",
        {
          title: formData.get("title"),
          action: formData.get("action"),
          owner: formData.get("owner"),
          lane: formData.get("lane"),
          node_type: formData.get("node_type"),
          after_step_id: formData.get("after_step_id"),
          slo_minutes: workflowSloFromForm(formData),
          escalation_role: workflowOptionalFormValue(formData.get("escalation_role")),
          condition_expression: workflowConditionFromForm(formData),
          permission_scope: workflowPermissionScopeFromForm(formData)
        }
      );
    });
  });

  document.querySelectorAll("[data-workflow-palette-add]").forEach((el) => {
    el.addEventListener("click", async () => {
      await addWorkflowPaletteStep(
        el.dataset.workflowTemplateId || "payroll-close",
        el.dataset.workflowPaletteKind,
        el.dataset.workflowAfterStepId
      );
    });
  });

  document.querySelectorAll("[data-workflow-delete-step]").forEach((el) => {
    el.addEventListener("click", async () => {
      await deleteWorkflowStep(
        el.dataset.workflowTemplateId || "payroll-close",
        el.dataset.workflowStepId
      );
    });
  });

  document.querySelectorAll("[data-workflow-rollback-version]").forEach((el) => {
    el.addEventListener("click", async () => {
      await rollbackWorkflowTemplate(
        el.dataset.workflowTemplateId || "payroll-close",
        el.dataset.workflowRollbackVersion
      );
    });
  });

  document.querySelectorAll("[data-home-work-target]").forEach((el) => {
    el.addEventListener("click", () => {
      const target = el.dataset.homeWorkTarget;
      const account = selectedAccount();
      state.selectedWorkStepKey = el.dataset.workStepKey || "";
      state.activeId = account.navigationIds.includes(target) ? target : account.defaultRoute;
      render();
      const label = visibleNavigationItems().find((item) => item.id === state.activeId)?.label || t("screens.module.unavailable.title");
      toast(t("preview.toast.screenChanged", { screen: label }));
    });
  });

  document.querySelectorAll("[data-admin-key]").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedAdminKey = el.dataset.adminKey;
      render();
      toast(t("preview.toast.queueDetailOpened"));
    });
  });

  document.querySelectorAll("[data-refresh-live]").forEach((el) => {
    el.addEventListener("click", async () => {
      await refreshLiveView();
      toast(t("preview.toast.liveRefreshed"));
    });
  });
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
