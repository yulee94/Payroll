import { useMemo, useState } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaView, StyleSheet, View } from "react-native";

import { AppShell } from "./src/components";
import { colors } from "./src/theme";
import type { PlatformId } from "./src/types";
import { getNavigationItem, previewPlatformViewModel } from "./src/viewModel";
import { LauncherScreen, LoginScreen, ModuleScreen, PayrollScreen } from "./src/screens";

export default function App() {
  const [activeId, setActiveId] = useState<PlatformId>("home");
  const [authenticated, setAuthenticated] = useState(false);
  const active = useMemo(() => getNavigationItem(activeId), [activeId]);
  const navigationItems = previewPlatformViewModel.launcher.navigation;

  const select = (id: PlatformId) => {
    if (!authenticated && id !== "home") {
      setAuthenticated(true);
    }
    setActiveId(id);
  };

  if (!authenticated) {
    return (
      <SafeAreaView style={styles.root}>
        <StatusBar style="dark" />
        <View style={styles.loginFrame}>
          <LoginScreen onSelect={(id) => {
            setAuthenticated(true);
            setActiveId(id);
          }} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.root}>
      <StatusBar style="dark" />
      <AppShell active={active} items={navigationItems} onSelect={select}>
        {activeId === "home" ? (
          <LauncherScreen active={active} onSelect={select} />
        ) : activeId === "payroll" ? (
          <PayrollScreen active={active} onSelect={select} />
        ) : (
          <ModuleScreen active={active} onSelect={select} />
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
