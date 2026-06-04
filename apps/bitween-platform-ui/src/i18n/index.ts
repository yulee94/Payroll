import catalog from "./catalog.json";

export type SupportedLocale = "ko-KR" | "en-US" | "zh-Hans-CN" | "ja-JP";
export type MessageParams = Readonly<Record<string, string | number>>;

export const defaultLocale: SupportedLocale = "ko-KR";
export const supportedLocales = catalog.supportedLocales as readonly SupportedLocale[];

type CatalogMessage = {
  readonly key: string;
  readonly values: Readonly<Record<SupportedLocale, string>>;
};

type LanguageDisplayName = {
  readonly locale: SupportedLocale;
  readonly values: Readonly<Record<SupportedLocale, string>>;
};

const messages = catalog.messages as readonly CatalogMessage[];
const languageDisplayNames = catalog.languageDisplayNames as readonly LanguageDisplayName[];
const messageByKey = new Map(messages.map((message) => [message.key, message.values] as const));
const languageDisplayNameByLocale = new Map(languageDisplayNames.map((row) => [row.locale, row.values] as const));

const interpolate = (template: string, params: MessageParams = {}): string =>
  template.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, key: string) => {
    const value = params[key];
    return value === undefined ? match : String(value);
  });

export const isSupportedLocale = (locale: string): locale is SupportedLocale =>
  supportedLocales.includes(locale as SupportedLocale);

export const normalizeLocale = (locale: string | undefined): SupportedLocale => {
  if (!locale) {
    return defaultLocale;
  }
  if (isSupportedLocale(locale)) {
    return locale;
  }
  const language = locale.split("-")[0]?.toLowerCase();
  if (language === "ko") return "ko-KR";
  if (language === "en") return "en-US";
  if (language === "zh") return "zh-Hans-CN";
  if (language === "ja") return "ja-JP";
  return defaultLocale;
};

export const t = (locale: SupportedLocale, key: string, params?: MessageParams): string => {
  const values = messageByKey.get(key);
  const localized = values?.[locale];
  if (!localized) {
    throw new Error(`Missing i18n message "${key}" for locale "${locale}"`);
  }
  return interpolate(localized, params);
};

export const getLanguageDisplayName = (activeLocale: SupportedLocale, locale: SupportedLocale): string => {
  const values = languageDisplayNameByLocale.get(locale);
  const localized = values?.[activeLocale];
  if (!localized) {
    throw new Error(`Missing i18n language display name "${locale}" for active locale "${activeLocale}"`);
  }
  return localized;
};

export const getLanguageOptions = (activeLocale: SupportedLocale) =>
  supportedLocales.map((locale) => ({
    locale,
    label: getLanguageDisplayName(activeLocale, locale)
  }));
