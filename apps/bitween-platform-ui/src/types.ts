export type PlatformId =
  | "home"
  | "payroll"
  | "hr"
  | "workflow"
  | "archive"
  | "ai"
  | "admin"
  | "settings";

export type ReadinessTone = "ready" | "attention" | "blocked" | "neutral";

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
  readonly title: string;
  readonly meta: string;
  readonly status: string;
  readonly tone: ReadinessTone;
};
