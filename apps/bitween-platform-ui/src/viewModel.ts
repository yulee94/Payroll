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

export const getPreviewSession = (locale: SupportedLocale): SessionViewModel => ({
  companyCodeLabel: "",
  displayName: t(locale, "preview.liveData.sessionUnavailable"),
  employeeNumber: "",
  roleLabel: t(locale, "preview.liveData.employeeUnavailable"),
  tenantName: ""
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
    previewRows: getPreviewRows(locale),
    readinessCards: getReadinessCards(locale),
    settingsRows: getPayrollSettingsRows(locale),
    steps: getPayrollSteps(locale)
  },
  session: getPreviewSession(locale)
});

export const previewPlatformViewModel: PlatformViewModel = getPreviewPlatformViewModel(defaultLocale);

export const previewViewModelAdapter: PlatformViewModelAdapter = {
  load: (locale) => getPreviewPlatformViewModel(locale)
};

export const getNavigationItem = (id: PlatformId, locale: SupportedLocale = defaultLocale): NavigationItem => {
  const navigation = getNavigationItems(locale);
  return navigation.find((item) => item.id === id) ?? navigation[0];
};
