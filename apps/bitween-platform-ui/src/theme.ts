import { defaultLocale, t, type SupportedLocale } from "./i18n";
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

type SidebarThemeDefinition = Omit<SidebarTheme, "label" | "description">;

const sidebarThemeDefinitions = [
  {
    activeBackground: "#DBEAFE",
    activeText: "#1F3864",
    id: "steel",
    sidebar: "#EDF3FA",
    swatchEnd: "#DBEAFE",
    swatchStart: "#EDF3FA"
  },
  {
    activeBackground: "#111827",
    activeText: "#FFFFFF",
    id: "graphite",
    sidebar: "#F3F4F6",
    swatchEnd: "#111827",
    swatchStart: "#F3F4F6"
  },
  {
    activeBackground: "#CCFBF1",
    activeText: "#0F766E",
    id: "teal",
    sidebar: "#E8F5F3",
    swatchEnd: "#CCFBF1",
    swatchStart: "#E8F5F3"
  },
  {
    activeBackground: "#1F3864",
    activeText: "#FFFFFF",
    id: "navy",
    sidebar: "#E8EEF7",
    swatchEnd: "#1F3864",
    swatchStart: "#E8EEF7"
  }
] as const satisfies readonly SidebarThemeDefinition[];

export const defaultSidebarThemeId: SidebarThemeId = "steel";

const localizeSidebarTheme = (locale: SupportedLocale, theme: SidebarThemeDefinition): SidebarTheme => ({
  ...theme,
  label: t(locale, `sidebarThemes.${theme.id}.label`),
  description: t(locale, `sidebarThemes.${theme.id}.description`)
});

export const getSidebarThemes = (locale: SupportedLocale): readonly SidebarTheme[] =>
  sidebarThemeDefinitions.map((theme) => localizeSidebarTheme(locale, theme));

export const sidebarThemes = getSidebarThemes(defaultLocale);

export function getSidebarTheme(id: SidebarThemeId, locale: SupportedLocale = defaultLocale): SidebarTheme {
  const themes = getSidebarThemes(locale);
  const fallback = themes[0];
  if (!fallback) {
    throw new Error("No sidebar themes configured");
  }
  return themes.find((theme) => theme.id === id) ?? fallback;
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
