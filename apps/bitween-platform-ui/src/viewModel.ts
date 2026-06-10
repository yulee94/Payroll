import { defaultLocale, t, type SupportedLocale } from "./i18n";
import type {
  CalendarEvent,
  MetricItem,
  ModuleDashboard,
  ModuleRow,
  NavigationItem,
  PayrollStep,
  PlatformId,
  TodoItem,
  WorkQueueItem
} from "./types";
import {
  getModuleDashboards,
  getNavigationItems
} from "./data";

export type NonEmptyNavigation = readonly [NavigationItem, ...NavigationItem[]];

export type SessionViewModel = {
  readonly authenticated: boolean;
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

const getLiveNavigationItems = (locale: SupportedLocale): NonEmptyNavigation => {
  const navigation = getNavigationItems(locale).filter((item) =>
    ["home", "hr", "payroll", "workflow", "approval", "archive", "admin"].includes(item.id),
  );
  const first = navigation[0] ?? getNavigationItems(locale)[0];
  if (!first) {
    throw new Error("No navigation items configured");
  }
  return [first, ...navigation.filter((item) => item.id !== first.id)];
};

export const getLivePlatformViewModel = (locale: SupportedLocale): PlatformViewModel => ({
  launcher: {
    calendarEvents: [],
    metrics: [],
    navigation: getLiveNavigationItems(locale),
    todayTodos: [],
    workQueue: []
  },
  modules: getModuleDashboards(locale),
  payroll: {
    previewRows: [],
    settingsRows: [],
    steps: []
  },
  session: {
    authenticated: false,
    companyCodeLabel: "tenant-acme",
    displayName: t(locale, "session.displayName"),
    employeeNumber: t(locale, "session.employeeNumber.pending"),
    roleLabel: t(locale, "session.roleLabel"),
    tenantName: t(locale, "preview.profile.defaultTenantName")
  }
});

export const getNavigationItem = (id: PlatformId, locale: SupportedLocale = defaultLocale): NavigationItem => {
  const navigation = getNavigationItems(locale);
  return navigation.find((item) => item.id === id) ?? navigation[0];
};
