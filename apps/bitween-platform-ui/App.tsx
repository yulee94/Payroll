import { useMemo, useState } from "react";
import { StatusBar } from "expo-status-bar";
import { Linking, SafeAreaView, StyleSheet } from "react-native";

import { AppShell, AuthGate } from "./src/components";
import { defaultLocale, t, type SupportedLocale } from "./src/i18n";
import { colors, defaultSidebarThemeId, getSidebarTheme } from "./src/theme";
import type { PlatformId, SidebarThemeId } from "./src/types";
import { getLivePlatformViewModel, getNavigationItem } from "./src/viewModel";
import { LauncherScreen, ModuleScreen, PayrollScreen } from "./src/screens";

type AuthAction = "signin" | "signup" | "onboarding" | "signout";

const runtimeEnv = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {};
const authRouteEnv = {
  onboarding: "EXPO_PUBLIC_BITWEEN_ONBOARDING_START_URL",
  signin: "EXPO_PUBLIC_BITWEEN_AUTH_SIGNIN_URL",
  signout: "EXPO_PUBLIC_BITWEEN_AUTH_SIGNOUT_URL",
  signup: "EXPO_PUBLIC_BITWEEN_AUTH_SIGNUP_URL"
} as const satisfies Record<AuthAction, string>;

export default function App() {
  const [activeId, setActiveId] = useState<PlatformId>("home");
  const [authNotice, setAuthNotice] = useState<string | undefined>();
  const [locale, setLocale] = useState<SupportedLocale>(defaultLocale);
  const [sidebarThemeId, setSidebarThemeId] = useState<SidebarThemeId>(defaultSidebarThemeId);
  const viewModel = useMemo(() => getLivePlatformViewModel(locale), [locale]);
  const navigationItems = viewModel.launcher.navigation;
  const active = useMemo(
    () => navigationItems.find((item) => item.id === activeId) ?? getNavigationItem(activeId, locale),
    [activeId, locale, navigationItems],
  );
  const sidebarTheme = useMemo(() => getSidebarTheme(sidebarThemeId, locale), [locale, sidebarThemeId]);
  const session = viewModel.session;

  const select = (id: PlatformId) => {
    const canAccess = navigationItems.some((item) => item.id === id);
    setActiveId(canAccess || id === "settings" ? id : "home");
  };

  const openAuthRoute = async (action: AuthAction) => {
    const route = runtimeEnv[authRouteEnv[action]];
    if (!route) {
      setAuthNotice(t(locale, `auth.notice.${action}Missing`));
      return;
    }
    const canOpen = await Linking.canOpenURL(route);
    if (!canOpen) {
      setAuthNotice(t(locale, "auth.notice.routeFailed"));
      return;
    }
    await Linking.openURL(route);
  };

  if (!session.authenticated) {
    return (
      <SafeAreaView style={styles.root}>
        <StatusBar style="dark" />
        <AuthGate locale={locale} notice={authNotice} onAction={openAuthRoute} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.root}>
      <StatusBar style="dark" />
      <AppShell
        active={active}
        items={navigationItems}
        locale={locale}
        onLogout={() => openAuthRoute("signout")}
        onSelect={select}
        session={session}
        sidebarTheme={sidebarTheme}
      >
        {activeId === "home" ? (
          <LauncherScreen active={active} items={navigationItems} locale={locale} onSelect={select} />
        ) : activeId === "payroll" ? (
          <PayrollScreen active={active} locale={locale} onSelect={select} />
        ) : (
          <ModuleScreen
            active={active}
            locale={locale}
            onLocaleChange={setLocale}
            onSelect={select}
            onThemeChange={setSidebarThemeId}
            sidebarTheme={sidebarTheme}
          />
        )}
      </AppShell>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {
    backgroundColor: colors.bg,
    flex: 1
  }
});
