import { defaultLocale, t, type SupportedLocale } from "./i18n";
import type {
  CalendarEvent,
  MetricItem,
  ModuleDashboard,
  ModuleRow,
  NavigationItem,
  PayrollStep,
  PlatformId,
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

const platformMetricDefinitions: readonly MetricDefinition[] = [];
const readinessDefinitions: readonly MetricDefinition[] = [];
const payrollStepDefinitions: readonly MetricDefinition[] = [];
const payrollSettingRowDefinitions: readonly RowDefinition[] = [];
const payrollIntegrationRowDefinitions: readonly RowDefinition[] = [];
const previewRowDefinitions: readonly RowDefinition[] = [];
const workQueueDefinitions: readonly RowDefinition[] = [];
const calendarEventDefinitions: readonly {
  readonly dateLabel: string;
  readonly id: string;
  readonly timeLabel: string;
  readonly tone: ReadinessTone;
}[] = [];
const todoDefinitions: readonly {
  readonly completed: boolean;
  readonly id: string;
  readonly tone: ReadinessTone;
}[] = [];

const moduleDefinitions = {
  hr: {
    filters: ["all", "roster", "resume", "resignation", "certificate"],
    metrics: [],
    rows: [],
    primaryAction: { target: "hr" },
    secondaryAction: { target: "payroll" }
  },
  attendance: {
    filters: ["all", "checkIn", "checkOut", "attention"],
    metrics: [],
    rows: [],
    primaryAction: { target: "attendance" },
    secondaryAction: { target: "hr" }
  },
  recruit: {
    filters: ["all", "applicant", "career", "credential", "placement"],
    metrics: [],
    rows: [],
    primaryAction: { target: "recruit" },
    secondaryAction: { target: "hr" }
  },
  travel: {
    filters: ["all", "plan", "run", "diary", "result", "review"],
    metrics: [],
    rows: [],
    primaryAction: { target: "travel" },
    secondaryAction: { target: "workflow" }
  },
  workflow: {
    filters: ["all", "pending", "ongoing", "returned"],
    metrics: [],
    rows: [],
    primaryAction: { target: "workflow" },
    secondaryAction: { target: "archive" }
  },
  archive: {
    filters: ["all", "payroll", "contract", "report"],
    metrics: [],
    rows: [],
    primaryAction: { target: "archive" },
    secondaryAction: { target: "payroll" }
  },
  ai: {
    filters: ["all", "summary", "draft", "review"],
    metrics: [],
    rows: [],
    primaryAction: { target: "ai" },
    secondaryAction: { target: "settings" }
  },
  admin: {
    filters: ["all", "permission", "branch", "subaccount", "audit"],
    metrics: [],
    rows: [],
    primaryAction: { target: "admin" },
    secondaryAction: { target: "settings" }
  },
  settings: {
    filters: ["all", "personal", "payroll", "notification"],
    metrics: [],
    rows: [],
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
    timeLabel: event.timeLabel,
    title: t(locale, `calendarEvents.${event.id}.title`),
    tone: event.tone
  }));

export const getTodayTodos = (locale: SupportedLocale): readonly TodoItem[] =>
  todoDefinitions.map((todo) => ({
    completed: todo.completed,
    id: todo.id,
    owner: t(locale, `todayTodos.${todo.id}.owner`),
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
