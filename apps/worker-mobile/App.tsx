import { useEffect, useState } from 'react';
import { Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import Constants from 'expo-constants';
import { StatusBar } from 'expo-status-bar';
import { LoginScreen } from './src/screens/LoginScreen';
import { HomeScreen } from './src/screens/HomeScreen';
import { PayrollScreen } from './src/screens/PayrollScreen';
import { RequestScreen } from './src/screens/RequestScreen';
import { AlertsScreen } from './src/screens/AlertsScreen';
import { getAppConfig } from './src/api/client';
import { clearAuthState, loadAuthState } from './src/security/secureSession';
import { getOrCreateDeviceUid } from './src/security/deviceIdentity';
import { syncQueuedOfflineRequests } from './src/offline/localQueue';
import { colors, spacing } from './src/theme/tokens';
import type { MobileAuthState, MobileVersionPolicy } from './src/types';

type Tab = 'attendance' | 'payroll' | 'request' | 'alerts';

const tabs: Array<{ id: Tab; label: string }> = [
  { id: 'attendance', label: '출퇴근' },
  { id: 'payroll', label: '내 급여' },
  { id: 'request', label: '신청' },
  { id: 'alerts', label: '알림' },
];

export default function App() {
  const [auth, setAuth] = useState<MobileAuthState | null>(null);
  const [deviceUid, setDeviceUid] = useState('');
  const [tab, setTab] = useState<Tab>('attendance');
  const [booting, setBooting] = useState(true);
  const [versionPolicy, setVersionPolicy] = useState<MobileVersionPolicy | null>(null);

  useEffect(() => {
    void (async () => {
      const [savedAuth, uid, config] = await Promise.all([
        loadAuthState(),
        getOrCreateDeviceUid(),
        getAppConfig(Constants.expoConfig?.version ?? '0.1.0').catch(() => null),
      ]);
      setAuth(savedAuth);
      setDeviceUid(uid);
      setVersionPolicy(config?.version_policy ?? null);
      setBooting(false);
    })();
  }, []);

  useEffect(() => {
    if (!auth) return;
    void syncQueuedOfflineRequests(auth).catch(() => undefined);
  }, [auth]);

  const logout = async (): Promise<void> => {
    await clearAuthState();
    setAuth(null);
    setTab('attendance');
  };

  if (booting) {
    return (
      <SafeAreaView style={styles.boot}>
        <StatusBar style="dark" />
        <Text style={styles.bootText}>Bitween Worker 준비 중...</Text>
      </SafeAreaView>
    );
  }

  if (versionPolicy?.maintenance_mode || versionPolicy?.force_update_required) {
    return (
      <SafeAreaView style={styles.boot}>
        <StatusBar style="dark" />
        <Text style={styles.bootText}>
          {versionPolicy.maintenance_mode ? '서비스 점검 중입니다' : '앱 업데이트가 필요합니다'}
        </Text>
        <Text style={styles.gateText}>
          {versionPolicy.notice_message
            || `최소 지원 버전은 ${versionPolicy.minimum_supported_version}, 최신 버전은 ${versionPolicy.latest_version}입니다.`}
        </Text>
      </SafeAreaView>
    );
  }

  if (!auth) {
    return (
      <SafeAreaView style={styles.root}>
        <StatusBar style="dark" />
        <LoginScreen onLogin={(nextAuth, nextDeviceUid) => { setAuth(nextAuth); setDeviceUid(nextDeviceUid); }} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.root}>
      <StatusBar style="dark" />
      <View style={styles.topBar}>
        <View>
          <Text style={styles.brand}>Bitween Worker</Text>
          <Text style={styles.user}>{auth.user.employee_name} · {auth.user.role}</Text>
        </View>
        <Pressable onPress={logout} style={styles.logout}>
          <Text style={styles.logoutText}>로그아웃</Text>
        </Pressable>
      </View>
      <View style={styles.content}>
        {tab === 'attendance' ? <HomeScreen auth={auth} deviceUid={deviceUid} /> : null}
        {tab === 'payroll' ? <PayrollScreen auth={auth} /> : null}
        {tab === 'request' ? <RequestScreen auth={auth} deviceUid={deviceUid} /> : null}
        {tab === 'alerts' ? <AlertsScreen auth={auth} /> : null}
      </View>
      <ScrollView horizontal contentContainerStyle={styles.tabs} showsHorizontalScrollIndicator={false}>
        {tabs.map((item) => (
          <Pressable
            key={item.id}
            onPress={() => setTab(item.id)}
            style={[styles.tab, tab === item.id && styles.activeTab]}
          >
            <Text style={[styles.tabText, tab === item.id && styles.activeTabText]}>{item.label}</Text>
          </Pressable>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { backgroundColor: colors.bg, flex: 1 },
  boot: { alignItems: 'center', backgroundColor: colors.bg, flex: 1, justifyContent: 'center' },
  bootText: { color: colors.ink, fontSize: 18, fontWeight: '800' },
  gateText: { color: colors.muted, fontSize: 14, lineHeight: 20, marginTop: spacing.md, paddingHorizontal: spacing.xl, textAlign: 'center' },
  topBar: {
    alignItems: 'center',
    backgroundColor: colors.card,
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: spacing.lg,
  },
  brand: { color: colors.ink, fontSize: 18, fontWeight: '900' },
  user: { color: colors.muted, fontSize: 13 },
  logout: { borderColor: colors.border, borderRadius: 999, borderWidth: 1, paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
  logoutText: { color: colors.ink, fontWeight: '800' },
  content: { flex: 1 },
  tabs: {
    backgroundColor: colors.card,
    borderTopColor: colors.border,
    borderTopWidth: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  tab: { borderRadius: 999, paddingHorizontal: spacing.lg, paddingVertical: spacing.sm },
  activeTab: { backgroundColor: colors.primary },
  tabText: { color: colors.muted, fontWeight: '900' },
  activeTabText: { color: '#fff' },
});
