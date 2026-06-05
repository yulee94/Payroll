import { useMemo, useState } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaView, StyleSheet, View } from "react-native";

import { AppShell, Badge, Label } from "./src/components";
import { defaultLocale, t, type SupportedLocale } from "./src/i18n";
import { colors, defaultSidebarThemeId, getSidebarTheme } from "./src/theme";
import type { PlatformId, SidebarThemeId } from "./src/types";
import { createEmptyPlatformViewModel, getNavigationItem, getPreviewPlatformViewModel, isDemoDataMode } from "./src/viewModel";
import { LauncherScreen, LoginScreen, ModuleScreen, PayrollScreen } from "./src/screens";

type ModuleId = Exclude<PlatformId, "home" | "payroll">;

function isModuleId(id: PlatformId): id is ModuleId {
  return id !== "home" && id !== "payroll";
}

export default function App() {
  const [activeId, setActiveId] = useState<PlatformId>("home");
  const [authenticated, setAuthenticated] = useState(false);
  const [locale, setLocale] = useState<SupportedLocale>(defaultLocale);
  const [sidebarThemeId, setSidebarThemeId] = useState<SidebarThemeId>(defaultSidebarThemeId);
  const demoDataEnabled = isDemoDataMode();
  const viewModel = useMemo(
    () => (demoDataEnabled ? getPreviewPlatformViewModel(locale) : createEmptyPlatformViewModel(locale)),
    [demoDataEnabled, locale]
  );
  const active = useMemo(() => getNavigationItem(activeId, locale), [activeId, locale]);
  const navigationItems = viewModel.launcher.navigation;
  const sidebarTheme = useMemo(() => getSidebarTheme(sidebarThemeId, locale), [locale, sidebarThemeId]);
  const session = viewModel.session;
  const companyCodeLabel = session.companyCodeLabel === "-" ? t(locale, "session.emptyCompanyCodeLabel") : session.companyCodeLabel;
  const employeeNumberLabel =
    session.employeeNumber === "-" ? t(locale, "shell.employeeNumber.empty") : t(locale, "shell.employeeNumber", { number: session.employeeNumber });
  const sessionLabel = `${session.tenantName} / ${session.roleLabel} / ${companyCodeLabel}`;

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
            demoMode={demoDataEnabled}
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
        employeeNumberLabel={employeeNumberLabel}
        items={navigationItems}
        locale={locale}
        logoutLabel={t(locale, "shell.logout")}
        onLogout={logout}
        onSelect={select}
        onThemeChange={setSidebarThemeId}
        sessionLabel={sessionLabel}
        sidebarTheme={sidebarTheme}
      >
        {demoDataEnabled ? (
          <View style={styles.demoBanner}>
            <Badge tone="attention">{t(locale, "preview.demoMode.badge")}</Badge>
            <View style={styles.demoBannerCopy}>
              <Label weight="bold">{t(locale, "preview.demoMode.title")}</Label>
              <Label size="sm" muted>{t(locale, "preview.demoMode.description")}</Label>
            </View>
          </View>
        ) : null}
        {activeId === "home" ? (
          <LauncherScreen active={active} data={viewModel.launcher} locale={locale} onSelect={select} payroll={viewModel.payroll} />
        ) : activeId === "payroll" ? (
          <PayrollScreen active={active} data={viewModel.payroll} demoMode={demoDataEnabled} locale={locale} onSelect={select} />
        ) : isModuleId(activeId) ? (
          <ModuleScreen
            active={active}
            dashboard={viewModel.modules[activeId]}
            demoMode={demoDataEnabled}
            locale={locale}
            onLocaleChange={setLocale}
            onSelect={select}
          />
        ) : null}
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
  },
  demoBanner: {
    alignItems: "flex-start",
    backgroundColor: "#fff7ed",
    borderColor: "#fed7aa",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    gap: 12,
    padding: 14
  },
  demoBannerCopy: {
    flex: 1,
    gap: 2
  }
});
