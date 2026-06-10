import { defaultLocale, t, type SupportedLocale } from "./i18n";
import type { ReadinessTone, SidebarTheme, SidebarThemeId } from "./types";

export const pantoneBasis = {
  // Screen approximations for a Pantone-led enterprise UI palette.
  // Cloud Dancer anchors surfaces; Marina/Alexandrite/Burnt Sienna/Amaranth
  // supply accessible operational accents after contrast adjustment.
  alexandrite: "#00666C",
  amaranth: "#6F3C56",
  burntSienna: "#C65D52",
  cloudDancer: "#F0EEE9",
  marina: "#5085C3"
} as const;

export const colors = {
  accent: "#274E72",
  accentPressed: "#1C3B56",
  accentSoft: "#E7F0F9",
  bg: "#F7F5F0",
  blue: pantoneBasis.marina,
  border: "#DDD8CE",
  card: "#FFFEFA",
  cloud: pantoneBasis.cloudDancer,
  danger: "#9F342D",
  dangerSoft: "#FBE7E4",
  divider: "#E8E2D8",
  graphite: "#1F2328",
  graphiteSoft: "#EAE7E0",
  green: "#52643A",
  input: "#FFFDF8",
  muted: "#6E6A61",
  purple: pantoneBasis.amaranth,
  sky: pantoneBasis.marina,
  slate: "#767167",
  slateStrong: "#57534A",
  sidebar: pantoneBasis.cloudDancer,
  success: "#00666C",
  successSoft: "#E0F0EF",
  teal: pantoneBasis.alexandrite,
  tealActive: "#D9EFED",
  tealSoft: "#E8F4F2",
  tealStrong: "#005259",
  text: "#1F2328",
  warning: "#8C392F",
  warningSoft: "#FBE9E5",
  white: "#FFFFFF",
  whiteOverlay: "rgba(255, 253, 248, 0.72)"
} as const;

export const platformAccents = {
  admin: colors.warning,
  ai: colors.purple,
  approval: colors.blue,
  archive: colors.slateStrong,
  attendance: colors.sky,
  home: colors.slate,
  hr: colors.tealStrong,
  maintenanceRental: colors.green,
  payroll: colors.accent,
  recruit: colors.purple,
  settings: colors.teal,
  travel: colors.teal,
  workflow: colors.purple
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
    activeBackground: colors.accentSoft,
    activeText: colors.accent,
    id: "steel",
    sidebar: colors.sidebar,
    swatchEnd: colors.accentSoft,
    swatchStart: colors.sidebar
  },
  {
    activeBackground: colors.graphite,
    activeText: colors.white,
    id: "graphite",
    sidebar: colors.graphiteSoft,
    swatchEnd: colors.graphite,
    swatchStart: colors.graphiteSoft
  },
  {
    activeBackground: colors.tealActive,
    activeText: colors.teal,
    id: "teal",
    sidebar: colors.tealSoft,
    swatchEnd: colors.tealActive,
    swatchStart: colors.tealSoft
  },
  {
    activeBackground: colors.accent,
    activeText: colors.white,
    id: "navy",
    sidebar: colors.accentSoft,
    swatchEnd: colors.accent,
    swatchStart: colors.accentSoft
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
