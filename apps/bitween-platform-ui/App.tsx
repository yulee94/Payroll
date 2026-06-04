import { useMemo, useState } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaView, StyleSheet, View } from "react-native";

import { AppShell } from "./src/components";
import { defaultLocale, t, type SupportedLocale } from "./src/i18n";
import { colors, defaultSidebarThemeId, getSidebarTheme } from "./src/theme";
import type { PlatformId, SidebarThemeId } from "./src/types";
import { getNavigationItem, getPreviewPlatformViewModel } from "./src/viewModel";
import { LauncherScreen, LoginScreen, ModuleScreen, PayrollScreen } from "./src/screens";

export default function App() {
  const [activeId, setActiveId] = useState<PlatformId>("home");
  const [authenticated, setAuthenticated] = useState(false);
  const [locale, setLocale] = useState<SupportedLocale>(defaultLocale);
  const [sidebarThemeId, setSidebarThemeId] = useState<SidebarThemeId>(defaultSidebarThemeId);
  const viewModel = useMemo(() => getPreviewPlatformViewModel(locale), [locale]);
  const active = useMemo(() => getNavigationItem(activeId, locale), [activeId, locale]);
  const navigationItems = viewModel.launcher.navigation;
  const sidebarTheme = useMemo(() => getSidebarTheme(sidebarThemeId, locale), [locale, sidebarThemeId]);
  const session = viewModel.session;
  const sessionLabel = `${session.tenantName} · ${session.roleLabel} · ${session.companyCodeLabel}`;

  const select = (id: PlatformId) => {
    if (!authenticated && id !== "home") {
      setAuthenticated(true);
    }
    setActiveId(id);
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
            locale={locale}
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
        onLogout={logout}
        onSelect={select}
        onThemeChange={setSidebarThemeId}
        sessionLabel={sessionLabel}
        sidebarTheme={sidebarTheme}
      >
        {activeId === "home" ? (
          <LauncherScreen active={active} locale={locale} onSelect={select} />
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
