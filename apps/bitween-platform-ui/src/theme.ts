import type { ReadinessTone } from "./types";

export const colors = {
  accent: "#1F3864",
  accentSoft: "#E8F2FC",
  bg: "#F5F7FA",
  border: "#DDE5EE",
  card: "#FFFFFF",
  danger: "#B91C1C",
  muted: "#667085",
  sidebar: "#EDF3FA",
  success: "#047857",
  text: "#111827",
  warning: "#B45309"
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32
} as const;

export const toneColor = (tone: ReadinessTone): string => {
  switch (tone) {
    case "ready":
      return colors.success;
    case "attention":
      return colors.warning;
    case "blocked":
      return colors.danger;
    case "neutral":
      return colors.muted;
  }
};
