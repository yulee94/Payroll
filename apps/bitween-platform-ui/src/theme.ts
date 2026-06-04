import type { ReadinessTone } from "./types";

export const colors = {
  accent: "#1F3864",
  accentPressed: "#172B4D",
  accentSoft: "#E8F2FC",
  bg: "#F5F7FA",
  border: "#DDE5EE",
  card: "#FFFFFF",
  danger: "#B91C1C",
  dangerSoft: "#FEE2E2",
  divider: "#E7EDF4",
  input: "#FBFCFE",
  muted: "#667085",
  sidebar: "#EDF3FA",
  success: "#047857",
  successSoft: "#DFF6EC",
  text: "#111827",
  warning: "#B45309",
  warningSoft: "#FEF3C7"
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32
} as const;

export const radius = {
  sm: 4,
  md: 6,
  lg: 8
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

export const toneBackground = (tone: ReadinessTone): string => {
  switch (tone) {
    case "ready":
      return colors.successSoft;
    case "attention":
      return colors.warningSoft;
    case "blocked":
      return colors.dangerSoft;
    case "neutral":
      return colors.accentSoft;
  }
};
