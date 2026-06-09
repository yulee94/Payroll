import { useMemo, useState } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaView, StyleSheet, View } from "react-native";

import { AppShell } from "./src/components";
import { getPreviewAccounts } from "./src/data";
import { defaultLocale, t, type SupportedLocale } from "./src/i18n";
import { colors, defaultSidebarThemeId, getSidebarTheme } from "./src/theme";
import type { PlatformId, PreviewAccountId, SidebarThemeId } from "./src/types";
import { getNavigationItem, getPreviewPlatformViewModel } from "./src/viewModel";
import { LauncherScreen, LoginScreen, ModuleScreen, PayrollScreen } from "./src/screens";

export default function App() {
  const [activeId, setActiveId] = useState<PlatformId>("home");
  const [authenticated, setAuthenticated] = useState(false);
  const [accountId, setAccountId] = useState<PreviewAccountId>("fieldWorker");
  const [locale, setLocale] = useState<SupportedLocale>(defaultLocale);
  const [sidebarThemeId, setSidebarThemeId] = useState<SidebarThemeId>(defaultSidebarThemeId);
  const accounts = useMemo(() => getPreviewAccounts(locale), [locale]);
  const account = useMemo(() => {
    const fallback = accounts[0];
    if (!fallback) {
      throw new Error("No preview accounts configured");
    }
    return accounts.find((item) => item.id === accountId) ?? fallback;
  }, [accountId, accounts]);
  const viewModel = useMemo(() => getPreviewPlatformViewModel(locale, account.id), [account.id, locale]);
  const navigationItems = useMemo(
    () => viewModel.launcher.navigation.filter((item) => account.navigationIds.includes(item.id)),
    [account.navigationIds, viewModel.launcher.navigation],
  );
  const active = useMemo(
    () => navigationItems.find((item) => item.id === activeId) ?? getNavigationItem(activeId, locale),
    [activeId, locale, navigationItems],
  );
  const sidebarTheme = useMemo(() => getSidebarTheme(sidebarThemeId, locale), [locale, sidebarThemeId]);
  const session = viewModel.session;
  const sessionLabel = `${session.tenantName} · ${session.roleLabel} · ${session.companyCodeLabel}`;

  const select = (id: PlatformId) => {
    if (!authenticated && id !== "home") {
      setAuthenticated(true);
    }
    const canAccess = navigationItems.some((item) => item.id === id);
    setActiveId(canAccess ? id : account.defaultRoute);
  };

  const login = (nextAccountId: PreviewAccountId) => {
    const fallback = accounts[0];
    if (!fallback) {
      throw new Error("No preview accounts configured");
    }
    const nextAccount = accounts.find((item) => item.id === nextAccountId) ?? fallback;
    setAccountId(nextAccount.id);
    setAuthenticated(true);
    setActiveId(nextAccount.defaultRoute);
  };

  const logout = () => {
    setAuthenticated(false);
    setActiveId("home");
  };

  if (!authenticated) {
    return (
      <SafeAreaView style={styles.root}>
        <StatusBar style="dark" />
        <View style={styles.loginFrame}>
          <LoginScreen
            accounts={accounts}
            locale={locale}
            onLogin={login}
            onLocaleChange={setLocale}
            onSelect={(id) => {
              setAuthenticated(true);
              setActiveId(id);
            }}
          />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.root}>
      <StatusBar style="dark" />
      <AppShell
        active={active}
        employeeNumberLabel={t(locale, "shell.employeeNumber", { number: session.employeeNumber })}
        items={navigationItems}
        locale={locale}
        logoutLabel={t(locale, "shell.logout")}
        modeLabel={session.modeLabel}
        developerMode={session.developerMode}
        onLogout={logout}
        onSelect={select}
        onThemeChange={setSidebarThemeId}
        sessionLabel={sessionLabel}
        sidebarTheme={sidebarTheme}
      >
        {activeId === "home" ? (
          <LauncherScreen active={active} items={navigationItems} locale={locale} onSelect={select} />
        ) : activeId === "payroll" ? (
          <PayrollScreen active={active} locale={locale} onSelect={select} />
        ) : (
          <ModuleScreen active={active} locale={locale} onLocaleChange={setLocale} onSelect={select} />
        )}
      </AppShell>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {
    backgroundColor: colors.bg,
    flex: 1
  },
  loginFrame: {
    flex: 1,
    justifyContent: "center",
    padding: 24
  }
});
