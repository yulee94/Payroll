import type {
  MetricItem,
  ModuleDashboard,
  ModuleRow,
  NavigationItem,
  PayrollStep,
  PlatformId,
  ReadinessCard,
  WorkQueueItem
} from "./types";
import {
  moduleDashboards,
  navigationItems,
  payrollSettingsRows,
  payrollSteps,
  platformMetrics,
  previewRows,
  readinessCards,
  workQueue
} from "./data";

export type NonEmptyNavigation = readonly [NavigationItem, ...NavigationItem[]];

export type SessionViewModel = {
  readonly companyCodeLabel: string;
  readonly displayName: string;
  readonly roleLabel: string;
  readonly tenantName: string;
};

export type LauncherViewModel = {
  readonly metrics: readonly MetricItem[];
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
  companyCodeLabel: "BTW-2026",
  displayName: "급여 담당자",
  roleLabel: "운영 관리자",
  tenantName: "Bitween 법인"
};

export const previewPlatformViewModel: PlatformViewModel = {
  launcher: {
    metrics: platformMetrics,
    navigation: navigationItems,
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
