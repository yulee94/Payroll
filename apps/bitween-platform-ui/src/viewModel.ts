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
  calendarEvents,
  moduleDashboards,
  navigationItems,
  payrollSettingsRows,
  payrollSteps,
  platformMetrics,
  previewRows,
  readinessCards,
  todayTodos,
  workQueue
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
  readonly load: () => Promise<PlatformViewModel> | PlatformViewModel;
};

export const previewSession: SessionViewModel = {
  companyCodeLabel: "0000",
  displayName: "admin",
  employeeNumber: "BW-0001",
  roleLabel: "Demo 관리자",
  tenantName: "Bitween Demo"
};

export const previewPlatformViewModel: PlatformViewModel = {
  launcher: {
    calendarEvents,
    metrics: platformMetrics,
    navigation: navigationItems,
    todayTodos,
    workQueue
  },
  modules: moduleDashboards,
  payroll: {
    previewRows,
    readinessCards,
    settingsRows: payrollSettingsRows,
    steps: payrollSteps
  },
  session: previewSession
};

export const previewViewModelAdapter: PlatformViewModelAdapter = {
  load: () => previewPlatformViewModel
};

export const getNavigationItem = (id: PlatformId): NavigationItem =>
  previewPlatformViewModel.launcher.navigation.find((item) => item.id === id) ??
  previewPlatformViewModel.launcher.navigation[0];
