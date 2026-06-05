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
  TodoItem,
  WorkQueueItem
} from "./types";
import {
  getCalendarEvents,
  getModuleDashboards,
  getNavigationItems,
  getPayrollIntegrationRows,
  getPayrollSettingsRows,
  getPayrollSteps,
  getPlatformMetrics,
  getPreviewRows,
  getReadinessCards,
  getTodayTodos,
  getWorkQueue
} from "./data";

export type NonEmptyNavigation = readonly [NavigationItem, ...NavigationItem[]];

export type SessionViewModel = {
  readonly companyCodeLabel: string;
  readonly displayName: string;
  readonly employeeNumber: string;
  readonly roleLabel: string;
  readonly tenantName: string;
};

export type LauncherViewModel = {
  readonly calendarEvents: readonly CalendarEvent[];
  readonly metrics: readonly MetricItem[];
  readonly todayTodos: readonly TodoItem[];
  readonly navigation: NonEmptyNavigation;
  readonly workQueue: readonly WorkQueueItem[];
};

export type PayrollViewModel = {
  readonly integrationRows: readonly ModuleRow[];
  readonly previewRows: readonly ModuleRow[];
  readonly readinessCards: readonly ReadinessCard[];
  readonly settingsRows: readonly ModuleRow[];
  readonly steps: readonly PayrollStep[];
};

export type PlatformViewModel = {
  readonly launcher: LauncherViewModel;
  readonly modules: Readonly<Record<Exclude<PlatformId, "home" | "payroll">, ModuleDashboard>>;
  readonly payroll: PayrollViewModel;
  readonly session: SessionViewModel;
};

export type PlatformViewModelAdapter = {
  readonly load: (locale: SupportedLocale) => Promise<PlatformViewModel> | PlatformViewModel;
};

type ModuleId = Exclude<PlatformId, "home" | "payroll">;

const moduleIds = ["hr", "attendance", "recruit", "travel", "workflow", "archive", "ai", "admin", "settings"] as const satisfies readonly ModuleId[];

const emptyAction = (locale: SupportedLocale, target: PlatformId) => ({
  label: t(locale, "actions.open"),
  description: t(locale, `navigation.${target}.description`),
  target
});

const createEmptyModuleDashboard = (locale: SupportedLocale, id: ModuleId): ModuleDashboard => ({
  id,
  title: t(locale, `navigation.${id}.label`),
  subtitle: t(locale, `navigation.${id}.description`),
  metrics: [],
  filters: [t(locale, "screens.filters.all")],
  rows: [],
  primaryAction: emptyAction(locale, id),
  secondaryAction: emptyAction(locale, "home"),
  emptyTitle: t(locale, `modules.${id}.emptyTitle`),
  emptyDescription: t(locale, `modules.${id}.emptyDescription`)
});

export const createEmptyPlatformViewModel = (locale: SupportedLocale): PlatformViewModel => ({
  launcher: {
    calendarEvents: [],
    metrics: [],
    navigation: getNavigationItems(locale),
    todayTodos: [],
    workQueue: []
  },
  modules: Object.fromEntries(moduleIds.map((id) => [id, createEmptyModuleDashboard(locale, id)])) as Readonly<Record<ModuleId, ModuleDashboard>>,
  payroll: {
    integrationRows: [],
    previewRows: [],
    readinessCards: [],
    settingsRows: [],
    steps: []
  },
  session: {
    companyCodeLabel: "-",
    displayName: "",
    employeeNumber: "-",
    roleLabel: t(locale, "session.emptyRoleLabel"),
    tenantName: "Bitween"
  }
});

export const getPreviewSession = (locale: SupportedLocale): SessionViewModel => ({
  companyCodeLabel: "0000",
  displayName: "admin",
  employeeNumber: "BW-0001",
  roleLabel: t(locale, "session.roleLabel"),
  tenantName: "Bitween Demo"
});

export const getPreviewPlatformViewModel = (locale: SupportedLocale): PlatformViewModel => ({
  launcher: {
    calendarEvents: getCalendarEvents(locale),
    metrics: getPlatformMetrics(locale),
    navigation: getNavigationItems(locale),
    todayTodos: getTodayTodos(locale),
    workQueue: getWorkQueue(locale)
  },
  modules: getModuleDashboards(locale),
  payroll: {
    integrationRows: getPayrollIntegrationRows(locale),
    previewRows: getPreviewRows(locale),
    readinessCards: getReadinessCards(locale),
    settingsRows: getPayrollSettingsRows(locale),
    steps: getPayrollSteps(locale)
  },
  session: getPreviewSession(locale)
});

export const isDemoDataMode = (): boolean => {
  const runtimeFlag =
    typeof globalThis === "object" && "BITWEEN_DEMO_DATA" in globalThis
      ? String((globalThis as typeof globalThis & { BITWEEN_DEMO_DATA?: unknown }).BITWEEN_DEMO_DATA)
      : "";
  return runtimeFlag === "1" || runtimeFlag.toLowerCase() === "true";
};

export const previewPlatformViewModel: PlatformViewModel = getPreviewPlatformViewModel(defaultLocale);

export const previewViewModelAdapter: PlatformViewModelAdapter = {
  load: (locale) => getPreviewPlatformViewModel(locale)
};

export const getNavigationItem = (id: PlatformId, locale: SupportedLocale = defaultLocale): NavigationItem => {
  const navigation = getNavigationItems(locale);
  return navigation.find((item) => item.id === id) ?? navigation[0];
};
