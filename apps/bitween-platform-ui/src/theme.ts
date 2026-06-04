import type { ReadinessTone, SidebarTheme, SidebarThemeId } from "./types";

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

const steelSidebarTheme = {
  activeBackground: "#DBEAFE",
  activeText: "#1F3864",
  description: "현재 톤보다 선명한 업무형 파랑",
  id: "steel",
  label: "스틸 블루",
  sidebar: "#EDF3FA",
  swatchEnd: "#DBEAFE",
  swatchStart: "#EDF3FA"
} as const satisfies SidebarTheme;

const graphiteSidebarTheme = {
  activeBackground: "#111827",
  activeText: "#FFFFFF",
  description: "차분하고 밀도 있는 관리자형",
  id: "graphite",
  label: "그래파이트",
  sidebar: "#F3F4F6",
  swatchEnd: "#111827",
  swatchStart: "#F3F4F6"
} as const satisfies SidebarTheme;

const tealSidebarTheme = {
  activeBackground: "#CCFBF1",
  activeText: "#0F766E",
  description: "신뢰감 있는 HR/운영형",
  id: "teal",
  label: "틸 그린",
  sidebar: "#E8F5F3",
  swatchEnd: "#CCFBF1",
  swatchStart: "#E8F5F3"
} as const satisfies SidebarTheme;

const navySidebarTheme = {
  activeBackground: "#1F3864",
  activeText: "#FFFFFF",
  description: "가장 강한 기업용 대비",
  id: "navy",
  label: "딥 네이비",
  sidebar: "#E8EEF7",
  swatchEnd: "#1F3864",
  swatchStart: "#E8EEF7"
} as const satisfies SidebarTheme;

export const defaultSidebarThemeId: SidebarThemeId = "steel";

export const sidebarThemes = [steelSidebarTheme, graphiteSidebarTheme, tealSidebarTheme, navySidebarTheme] as const;

export function getSidebarTheme(id: SidebarThemeId): SidebarTheme {
  switch (id) {
    case "steel":
      return steelSidebarTheme;
    case "graphite":
      return graphiteSidebarTheme;
    case "teal":
      return tealSidebarTheme;
    case "navy":
      return navySidebarTheme;
  }
}

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
