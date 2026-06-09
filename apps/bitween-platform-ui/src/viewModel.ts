import { defaultLocale, type SupportedLocale } from "./i18n";
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
  TodoItem,
  WorkQueueItem
} from "./types";
import {
  getCalendarEvents,
  getModuleDashboards,
  getNavigationItems,
  getPreviewAccounts,
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
  readonly developerMode: boolean;
  readonly displayName: string;
  readonly employeeNumber: string;
  readonly modeLabel: string;
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

export const getPreviewAccountById = (
  locale: SupportedLocale,
  accountId: PreviewAccountId | undefined,
): PreviewAccount => {
  const accounts = getPreviewAccounts(locale);
  const fallback = accounts[0];
  if (!fallback) {
    throw new Error("No preview accounts configured");
  }
  return accounts.find((account) => account.id === accountId) ?? fallback;
};

export const getPreviewSession = (
  locale: SupportedLocale,
  accountId?: PreviewAccountId,
): SessionViewModel => {
  const account = getPreviewAccountById(locale, accountId);
  return {
    companyCodeLabel: account.companyCodeLabel,
    developerMode: account.developerMode,
    displayName: account.displayName,
    employeeNumber: account.employeeNumber,
    modeLabel: account.modeLabel,
    roleLabel: account.roleLabel,
    tenantName: account.tenantName
  };
};

export const getPreviewPlatformViewModel = (
  locale: SupportedLocale,
  accountId?: PreviewAccountId,
): PlatformViewModel => ({
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
  session: getPreviewSession(locale, accountId)
});

export const previewPlatformViewModel: PlatformViewModel = getPreviewPlatformViewModel(defaultLocale);

export const previewViewModelAdapter: PlatformViewModelAdapter = {
  load: (locale) => getPreviewPlatformViewModel(locale)
};

export const getNavigationItem = (id: PlatformId, locale: SupportedLocale = defaultLocale): NavigationItem => {
  const navigation = getNavigationItems(locale);
  return navigation.find((item) => item.id === id) ?? navigation[0];
};
