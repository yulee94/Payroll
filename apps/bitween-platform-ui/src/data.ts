import { defaultLocale, t, type SupportedLocale } from "./i18n";
import type {
  CalendarEvent,
  MetricItem,
  ModuleDashboard,
  ModuleRow,
  NavigationItem,
  PayrollStep,
  PlatformId,
  PreviewAccount,
  PreviewAccountId,
  ReadinessCard,
  ReadinessTone,
  TodoItem,
  WorkQueueItem
} from "./types";

type NonEmptyNavigation = readonly [NavigationItem, ...NavigationItem[]];
type ModuleId = Exclude<PlatformId, "home" | "payroll">;
type MetricDefinition = { readonly id: string; readonly tone: ReadinessTone };
type RowDefinition = { readonly id: string; readonly target: PlatformId; readonly tone: ReadinessTone };
type ActionDefinition = { readonly target: PlatformId };
type PreviewAccountDefinition = {
  readonly id: PreviewAccountId;
  readonly companyCode: string;
  readonly defaultRoute: PlatformId;
  readonly developerMode: boolean;
  readonly employeeNumber: string;
  readonly navigationIds: readonly PlatformId[];
  readonly password: string;
  readonly tone: ReadinessTone;
  readonly userId: string;
};
type ModuleDefinition = {
  readonly filters: readonly string[];
  readonly metrics: readonly MetricDefinition[];
  readonly rows: readonly RowDefinition[];
  readonly primaryAction: ActionDefinition;
  readonly secondaryAction: ActionDefinition;
};

const navigationItemDefinitions = [
  { id: "home", accent: "#64748B" },
  { id: "payroll", accent: "#1F3864" },
  { id: "hr", accent: "#0D9488" },
  { id: "attendance", accent: "#0284C7" },
  { id: "recruit", accent: "#9333EA" },
  { id: "travel", accent: "#0F766E" },
  { id: "workflow", accent: "#2563EB" },
  { id: "archive", accent: "#475569" },
  { id: "ai", accent: "#7C3AED" },
  { id: "admin", accent: "#B45309" },
  { id: "settings", accent: "#0F766E" }
] as const satisfies readonly { readonly id: PlatformId; readonly accent: string }[];

const previewAccountDefinitions = [
  {
    companyCode: "0000",
    defaultRoute: "attendance",
    developerMode: false,
    employeeNumber: "BW-1001",
    id: "fieldWorker",
    navigationIds: ["home", "attendance", "payroll", "settings"],
    password: "worker",
    tone: "ready",
    userId: "worker"
  },
  {
    companyCode: "0000",
    defaultRoute: "admin",
    developerMode: false,
    employeeNumber: "BW-3001",
    id: "operationsAdmin",
    navigationIds: ["home", "payroll", "hr", "attendance", "workflow", "archive", "admin", "settings"],
    password: "office",
    tone: "neutral",
    userId: "office.admin"
  },
  {
    companyCode: "0000",
    defaultRoute: "payroll",
    developerMode: false,
    employeeNumber: "BW-4001",
    id: "executive",
    navigationIds: ["home", "payroll", "workflow", "archive", "ai", "settings"],
    password: "executive",
    tone: "attention",
    userId: "executive"
  },
  {
    companyCode: "0000",
    defaultRoute: "settings",
    developerMode: true,
    employeeNumber: "BW-0001",
    id: "superAdmin",
    navigationIds: ["home", "payroll", "hr", "attendance", "recruit", "travel", "workflow", "archive", "ai", "admin", "settings"],
    password: "Dldsnckd94!",
    tone: "blocked",
    userId: "admin"
  }
] as const satisfies readonly PreviewAccountDefinition[];

const platformMetricDefinitions = [
  { id: "today", tone: "attention" },
  { id: "ready", tone: "ready" },
  { id: "blocked", tone: "blocked" },
  { id: "docs", tone: "neutral" }
] as const satisfies readonly MetricDefinition[];

const readinessDefinitions = [
  { id: "roster", tone: "attention" },
  { id: "policy", tone: "neutral" },
  { id: "outputs", tone: "ready" },
  { id: "api", tone: "attention" }
] as const satisfies readonly MetricDefinition[];

const payrollStepDefinitions = [
  { id: "settings", tone: "attention" },
  { id: "upload", tone: "neutral" },
  { id: "preview", tone: "ready" },
  { id: "archive", tone: "neutral" }
] as const satisfies readonly MetricDefinition[];

const payrollSettingRowDefinitions = [
  { id: "payroll-setting-1", target: "settings", tone: "neutral" },
  { id: "payroll-setting-2", target: "settings", tone: "attention" },
  { id: "payroll-setting-3", target: "settings", tone: "ready" }
] as const satisfies readonly RowDefinition[];

const payrollIntegrationRowDefinitions = [
  { id: "payroll-integration-1", target: "payroll", tone: "attention" },
  { id: "payroll-integration-2", target: "payroll", tone: "neutral" },
  { id: "payroll-integration-3", target: "payroll", tone: "ready" }
] as const satisfies readonly RowDefinition[];

const previewRowDefinitions = [
  { id: "preview-1", target: "archive", tone: "ready" },
  { id: "preview-2", target: "archive", tone: "neutral" },
  { id: "preview-3", target: "archive", tone: "attention" }
] as const satisfies readonly RowDefinition[];

const workQueueDefinitions = [
  { id: "payroll-june", target: "payroll", tone: "attention" },
  { id: "approval-pending", target: "workflow", tone: "neutral" },
  { id: "travel-diary", target: "travel", tone: "attention" },
  { id: "archive-preview", target: "archive", tone: "ready" }
] as const satisfies readonly RowDefinition[];

const calendarEventDefinitions = [
  { dateLabel: "2026.06.04", id: "calendar-payroll", target: "payroll", timeLabel: "10:00", tone: "attention" },
  { dateLabel: "2026.06.04", id: "calendar-approval", target: "workflow", timeLabel: "14:00", tone: "neutral" },
  { dateLabel: "2026.06.05", id: "calendar-recruit", target: "recruit", timeLabel: "09:30", tone: "ready" },
  { dateLabel: "2026.06.05", id: "calendar-travel", target: "travel", timeLabel: "16:00", tone: "attention" }
] as const satisfies readonly { readonly dateLabel: string; readonly id: string; readonly target: PlatformId; readonly timeLabel: string; readonly tone: ReadinessTone }[];

const todoDefinitions = [
  { completed: false, id: "todo-payroll", target: "payroll", tone: "attention" },
  { completed: false, id: "todo-approval", target: "workflow", tone: "neutral" },
  { completed: false, id: "todo-travel", target: "travel", tone: "attention" },
  { completed: true, id: "todo-archive", target: "archive", tone: "ready" }
] as const satisfies readonly { readonly completed: boolean; readonly id: string; readonly target: PlatformId; readonly tone: ReadinessTone }[];

const moduleDefinitions = {
  hr: {
    filters: ["all", "roster", "resume", "resignation", "certificate"],
    metrics: [
      { id: "employees", tone: "ready" },
      { id: "attendance", tone: "attention" },
      { id: "certs", tone: "neutral" }
    ],
    rows: [
      { id: "hr-1", target: "hr", tone: "attention" },
      { id: "hr-2", target: "hr", tone: "neutral" },
      { id: "hr-3", target: "hr", tone: "ready" }
    ],
    primaryAction: { target: "hr" },
    secondaryAction: { target: "payroll" }
  },
  attendance: {
    filters: ["all", "checkIn", "checkOut", "attention"],
    metrics: [
      { id: "checked-in", tone: "ready" },
      { id: "pending", tone: "attention" },
      { id: "weekly", tone: "neutral" }
    ],
    rows: [
      { id: "attendance-1", target: "attendance", tone: "ready" },
      { id: "attendance-2", target: "attendance", tone: "attention" }
    ],
    primaryAction: { target: "attendance" },
    secondaryAction: { target: "hr" }
  },
  recruit: {
    filters: ["all", "applicant", "career", "credential", "placement"],
    metrics: [
      { id: "applicants", tone: "ready" },
      { id: "qualified", tone: "attention" },
      { id: "placement", tone: "neutral" }
    ],
    rows: [
      { id: "recruit-1", target: "recruit", tone: "attention" },
      { id: "recruit-2", target: "recruit", tone: "ready" }
    ],
    primaryAction: { target: "recruit" },
    secondaryAction: { target: "hr" }
  },
  travel: {
    filters: ["all", "plan", "run", "diary", "result", "review"],
    metrics: [
      { id: "plans", tone: "neutral" },
      { id: "diary", tone: "attention" },
      { id: "completed", tone: "ready" }
    ],
    rows: [
      { id: "travel-1", target: "travel", tone: "attention" },
      { id: "travel-2", target: "travel", tone: "neutral" },
      { id: "travel-3", target: "archive", tone: "ready" }
    ],
    primaryAction: { target: "travel" },
    secondaryAction: { target: "workflow" }
  },
  workflow: {
    filters: ["all", "pending", "ongoing", "returned"],
    metrics: [
      { id: "pending", tone: "attention" },
      { id: "drafts", tone: "neutral" },
      { id: "done", tone: "ready" }
    ],
    rows: [
      { id: "wf-1", target: "workflow", tone: "attention" },
      { id: "wf-2", target: "archive", tone: "neutral" }
    ],
    primaryAction: { target: "workflow" },
    secondaryAction: { target: "archive" }
  },
  archive: {
    filters: ["all", "payroll", "contract", "report"],
    metrics: [
      { id: "reports", tone: "ready" },
      { id: "missing", tone: "attention" },
      { id: "shared", tone: "ready" }
    ],
    rows: [
      { id: "ar-1", target: "archive", tone: "ready" },
      { id: "ar-2", target: "attendance", tone: "attention" }
    ],
    primaryAction: { target: "archive" },
    secondaryAction: { target: "payroll" }
  },
  ai: {
    filters: ["all", "summary", "draft", "review"],
    metrics: [
      { id: "prompts", tone: "ready" },
      { id: "reviews", tone: "attention" },
      { id: "policy", tone: "neutral" }
    ],
    rows: [
      { id: "ai-1", target: "payroll", tone: "ready" },
      { id: "ai-2", target: "workflow", tone: "attention" }
    ],
    primaryAction: { target: "ai" },
    secondaryAction: { target: "settings" }
  },
  admin: {
    filters: ["all", "permission", "branch", "subaccount", "audit"],
    metrics: [
      { id: "branch", tone: "ready" },
      { id: "users", tone: "ready" },
      { id: "roles", tone: "attention" },
      { id: "audit", tone: "ready" }
    ],
    rows: [
      { id: "ad-1", target: "admin", tone: "attention" },
      { id: "ad-2", target: "admin", tone: "ready" },
      { id: "ad-3", target: "admin", tone: "attention" }
    ],
    primaryAction: { target: "admin" },
    secondaryAction: { target: "settings" }
  },
  settings: {
    filters: ["all", "personal", "payroll", "notification"],
    metrics: [
      { id: "profile", tone: "ready" },
      { id: "payroll", tone: "attention" },
      { id: "notice", tone: "neutral" }
    ],
    rows: [
      { id: "st-1", target: "payroll", tone: "attention" },
      { id: "st-2", target: "settings", tone: "ready" }
    ],
    primaryAction: { target: "settings" },
    secondaryAction: { target: "payroll" }
  }
} as const satisfies Record<ModuleId, ModuleDefinition>;

const localizeMetric = (locale: SupportedLocale, namespace: string, item: MetricDefinition): MetricItem => ({
  id: item.id,
  label: t(locale, `${namespace}.${item.id}.label`),
  value: t(locale, `${namespace}.${item.id}.value`),
  helper: t(locale, `${namespace}.${item.id}.helper`),
  tone: item.tone
});

const localizeRow = (locale: SupportedLocale, namespace: string, row: RowDefinition): ModuleRow => ({
  id: row.id,
  category: t(locale, `${namespace}.${row.id}.category`),
  status: t(locale, `${namespace}.${row.id}.status`),
  owner: t(locale, `${namespace}.${row.id}.owner`),
  nextStep: t(locale, `${namespace}.${row.id}.nextStep`),
  target: row.target,
  tone: row.tone
});

export const getPreviewAccounts = (locale: SupportedLocale): readonly PreviewAccount[] =>
  previewAccountDefinitions.map((account) => ({
    ...account,
    companyCodeLabel: account.companyCode,
    description: t(locale, `accounts.${account.id}.description`),
    displayName: t(locale, `accounts.${account.id}.displayName`),
    label: t(locale, `accounts.${account.id}.label`),
    modeLabel: t(locale, `accounts.${account.id}.modeLabel`),
    roleLabel: t(locale, `accounts.${account.id}.roleLabel`),
    tenantName: t(locale, `accounts.${account.id}.tenantName`)
  }));

export const getNavigationItems = (locale: SupportedLocale): NonEmptyNavigation =>
  navigationItemDefinitions.map((item) => ({
    id: item.id,
    label: t(locale, `navigation.${item.id}.label`),
    eyebrow: t(locale, `navigation.${item.id}.eyebrow`),
    description: t(locale, `navigation.${item.id}.description`),
    accent: item.accent
  })) as unknown as NonEmptyNavigation;

export const getPlatformMetrics = (locale: SupportedLocale): readonly MetricItem[] =>
  platformMetricDefinitions.map((item) => localizeMetric(locale, "platform.metrics", item));

export const getReadinessCards = (locale: SupportedLocale): readonly ReadinessCard[] =>
  readinessDefinitions.map((item) => ({
    id: item.id,
    title: t(locale, `payroll.readiness.${item.id}.title`),
    value: t(locale, `payroll.readiness.${item.id}.value`),
    detail: t(locale, `payroll.readiness.${item.id}.detail`),
    tone: item.tone
  }));

export const getPayrollSteps = (locale: SupportedLocale): readonly PayrollStep[] =>
  payrollStepDefinitions.map((item) => ({
    id: item.id,
    title: t(locale, `payroll.steps.${item.id}.title`),
    detail: t(locale, `payroll.steps.${item.id}.detail`),
    status: t(locale, `payroll.steps.${item.id}.status`),
    tone: item.tone
  }));

export const getPayrollSettingsRows = (locale: SupportedLocale): readonly ModuleRow[] =>
  payrollSettingRowDefinitions.map((row) => localizeRow(locale, "rows.payrollSettings", row));

export const getPayrollIntegrationRows = (locale: SupportedLocale): readonly ModuleRow[] =>
  payrollIntegrationRowDefinitions.map((row) => localizeRow(locale, "rows.payrollIntegration", row));

export const getPreviewRows = (locale: SupportedLocale): readonly ModuleRow[] =>
  previewRowDefinitions.map((row) => localizeRow(locale, "rows.preview", row));

export const getWorkQueue = (locale: SupportedLocale): readonly WorkQueueItem[] =>
  workQueueDefinitions.map((item) => ({
    id: item.id,
    title: t(locale, `workQueue.${item.id}.title`),
    meta: t(locale, `workQueue.${item.id}.meta`),
    owner: t(locale, `workQueue.${item.id}.owner`),
    due: t(locale, `workQueue.${item.id}.due`),
    status: t(locale, `workQueue.${item.id}.status`),
    target: item.target,
    tone: item.tone
  }));

export const getCalendarEvents = (locale: SupportedLocale): readonly CalendarEvent[] =>
  calendarEventDefinitions.map((event) => ({
    dateLabel: event.dateLabel,
    id: event.id,
    target: event.target,
    timeLabel: event.timeLabel,
    title: t(locale, `calendarEvents.${event.id}.title`),
    tone: event.tone
  }));

export const getTodayTodos = (locale: SupportedLocale): readonly TodoItem[] =>
  todoDefinitions.map((todo) => ({
    completed: todo.completed,
    id: todo.id,
    owner: t(locale, `todayTodos.${todo.id}.owner`),
    target: todo.target,
    title: t(locale, `todayTodos.${todo.id}.title`),
    timeLabel: t(locale, `todayTodos.${todo.id}.timeLabel`),
    tone: todo.tone
  }));

export const getModuleDashboards = (locale: SupportedLocale): Readonly<Record<ModuleId, ModuleDashboard>> => {
  const localizeModule = (id: ModuleId, definition: ModuleDefinition): ModuleDashboard => ({
    id,
    title: t(locale, `modules.${id}.title`),
    subtitle: t(locale, `modules.${id}.subtitle`),
    filters: definition.filters.map((filter) => t(locale, `modules.${id}.filters.${filter}`)),
    metrics: definition.metrics.map((metric) => localizeMetric(locale, `modules.${id}.metrics`, metric)),
    rows: definition.rows.map((row) => localizeRow(locale, `modules.${id}.rows`, row)),
    primaryAction: {
      label: t(locale, `modules.${id}.primaryAction.label`),
      description: t(locale, `modules.${id}.primaryAction.description`),
      target: definition.primaryAction.target
    },
    secondaryAction: {
      label: t(locale, `modules.${id}.secondaryAction.label`),
      description: t(locale, `modules.${id}.secondaryAction.description`),
      target: definition.secondaryAction.target
    },
    emptyTitle: t(locale, `modules.${id}.emptyTitle`),
    emptyDescription: t(locale, `modules.${id}.emptyDescription`)
  });

  return {
    hr: localizeModule("hr", moduleDefinitions.hr),
    attendance: localizeModule("attendance", moduleDefinitions.attendance),
    recruit: localizeModule("recruit", moduleDefinitions.recruit),
    travel: localizeModule("travel", moduleDefinitions.travel),
    workflow: localizeModule("workflow", moduleDefinitions.workflow),
    archive: localizeModule("archive", moduleDefinitions.archive),
    ai: localizeModule("ai", moduleDefinitions.ai),
    admin: localizeModule("admin", moduleDefinitions.admin),
    settings: localizeModule("settings", moduleDefinitions.settings)
  };
};

export const navigationItems = getNavigationItems(defaultLocale);
export const previewAccounts = getPreviewAccounts(defaultLocale);
export const platformMetrics = getPlatformMetrics(defaultLocale);
export const readinessCards = getReadinessCards(defaultLocale);
export const payrollSteps = getPayrollSteps(defaultLocale);
export const payrollSettingsRows = getPayrollSettingsRows(defaultLocale);
export const payrollIntegrationRows = getPayrollIntegrationRows(defaultLocale);
export const previewRows = getPreviewRows(defaultLocale);
export const workQueue = getWorkQueue(defaultLocale);
export const calendarEvents = getCalendarEvents(defaultLocale);
export const todayTodos = getTodayTodos(defaultLocale);
export const moduleDashboards = getModuleDashboards(defaultLocale);
