export type PlatformId =
  | "home"
  | "payroll"
  | "hr"
  | "attendance"
  | "recruit"
  | "travel"
  | "workflow"
  | "archive"
  | "ai"
  | "admin"
  | "settings";

export type ReadinessTone = "ready" | "attention" | "blocked" | "neutral";

export type SidebarThemeId = "steel" | "graphite" | "teal" | "navy";

export type SidebarTheme = {
  readonly id: SidebarThemeId;
  readonly label: string;
  readonly description: string;
  readonly sidebar: string;
  readonly activeBackground: string;
  readonly activeText: string;
  readonly swatchEnd: string;
  readonly swatchStart: string;
};

export type NavigationItem = {
  readonly id: PlatformId;
  readonly label: string;
  readonly eyebrow: string;
  readonly description: string;
  readonly accent: string;
};

export type ReadinessCard = {
  readonly id: string;
  readonly title: string;
  readonly value: string;
  readonly detail: string;
  readonly tone: ReadinessTone;
};

export type WorkQueueItem = {
  readonly id: string;
  readonly title: string;
  readonly meta: string;
  readonly owner: string;
  readonly due: string;
  readonly status: string;
  readonly target: PlatformId;
  readonly tone: ReadinessTone;
};

export type CalendarEvent = {
  readonly id: string;
  readonly dateLabel: string;
  readonly title: string;
  readonly timeLabel: string;
  readonly tone: ReadinessTone;
};

export type TodoItem = {
  readonly id: string;
  readonly completed: boolean;
  readonly owner: string;
  readonly target: PlatformId;
  readonly title: string;
  readonly timeLabel: string;
  readonly tone: ReadinessTone;
};

export type MetricItem = {
  readonly id: string;
  readonly label: string;
  readonly value: string;
  readonly helper: string;
  readonly tone: ReadinessTone;
};

export type ActionItem = {
  readonly label: string;
  readonly description: string;
  readonly target: PlatformId;
};

export type ModuleRow = {
  readonly id: string;
  readonly category: string;
  readonly status: string;
  readonly owner: string;
  readonly nextStep: string;
  readonly target: PlatformId;
  readonly tone: ReadinessTone;
};

export type ModuleDashboard = {
  readonly id: Exclude<PlatformId, "home" | "payroll">;
  readonly title: string;
  readonly subtitle: string;
  readonly metrics: readonly MetricItem[];
  readonly filters: readonly string[];
  readonly rows: readonly ModuleRow[];
  readonly primaryAction: ActionItem;
  readonly secondaryAction: ActionItem;
  readonly emptyTitle: string;
  readonly emptyDescription: string;
};

export type PayrollStep = {
  readonly id: string;
  readonly title: string;
  readonly detail: string;
  readonly status: string;
  readonly tone: ReadinessTone;
};
