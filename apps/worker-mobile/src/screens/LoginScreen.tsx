import { useState } from 'react';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import { listBranches, login, recordConsents, registerDevice } from '../api/client';
import { Card } from '../components/Card';
import { Field } from '../components/Field';
import { PrimaryButton } from '../components/PrimaryButton';
import { getOrCreateDeviceUid, mobilePlatform } from '../security/deviceIdentity';
import { saveAuthState } from '../security/secureSession';
import { requestWorkerPermissions } from '../location/geofence';
import { colors, spacing } from '../theme/tokens';
import type { ConsentKind, MobileAuthState } from '../types';
import { useAsyncAction } from '../state/useAsyncAction';

const REQUIRED_CONSENTS: ConsentKind[] = ['privacy', 'location', 'biometric', 'notifications', 'payroll'];

interface LoginScreenProps {
  onLogin: (auth: MobileAuthState, deviceUid: string) => void;
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [tenantId, setTenantId] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mfaOtp, setMfaOtp] = useState('');
  const action = useAsyncAction();

  const submit = async (): Promise<void> => {
    await action.run(async () => {
      const deviceUid = await getOrCreateDeviceUid();
      const auth = await login({ tenantId, username, password, deviceUid, mfaOtp });
      const branches = await listBranches(auth);
      const branch = branches.find((row) => row.active) ?? branches[0];
      if (!branch) {
        throw new Error('접근 가능한 사업장 권한이 없습니다.');
      }
      const permissions = await requestWorkerPermissions();
      if (!permissions.ok) {
        throw new Error(`필수 권한이 허용되지 않았습니다: ${permissions.reason}`);
      }
      const push = await Notifications.getDevicePushTokenAsync().catch(() => ({ data: '' }));
      const pushToken = typeof push.data === 'string' ? push.data : JSON.stringify(push.data ?? '');
      if (!pushToken) {
        throw new Error('푸시 알림 토큰 발급에 실패했습니다.');
      }
      await registerDevice(auth, {
        deviceUid,
        branchId: branch.branch_id,
        platform: mobilePlatform(),
        pushToken,
        appVersion: Constants.expoConfig?.version ?? '0.1.0',
        osVersion: String(Platform.Version),
      });
      await recordConsents(auth, deviceUid, REQUIRED_CONSENTS);
      const scopedAuth: MobileAuthState = { ...auth, branchId: branch.branch_id, deviceUid };
      await saveAuthState(scopedAuth);
      onLogin(scopedAuth, deviceUid);
    });
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Bitween Worker</Text>
      <Text style={styles.subtitle}>Android/iPhone 출퇴근 · 급여 · 연차 셀프서비스</Text>
      <Card>
        <Field label="고객사/법인 ID" value={tenantId} onChangeText={setTenantId} autoCapitalize="none" />
        <Field label="아이디" value={username} onChangeText={setUsername} autoCapitalize="none" />
        <Field label="비밀번호" value={password} onChangeText={setPassword} secureTextEntry />
        <Field label="OTP / MFA 코드" value={mfaOtp} onChangeText={setMfaOtp} keyboardType="number-pad" autoCapitalize="none" />
        {action.error ? <Text style={styles.error}>{action.error}</Text> : null}
        <PrimaryButton label="MFA 확인 후 기기 등록" onPress={submit} disabled={action.busy || !tenantId || !username || !password || mfaOtp.length < 6} />
      </Card>
      <View style={styles.notice}>
        <Text style={styles.noticeText}>회사 계정 로그인 → OTP/MFA → 기기 등록 → 사업장/권한 확인 후 앱을 사용할 수 있습니다.</Text>
        <Text style={styles.noticeText}>푸시 알림은 작업 배정, 승인 요청, 장애/공지/정산 알림 수신을 위해 필수입니다.</Text>
        <Text style={styles.noticeText}>위치정보는 근무시간 출퇴근/지오펜스 확인에만 사용됩니다.</Text>
        <Text style={styles.noticeText}>생체정보 원본은 Bitween 서버에 저장하지 않고 기기 인증 결과만 전송합니다.</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: colors.bg, flexGrow: 1, gap: spacing.lg, padding: spacing.xl, paddingTop: 72 },
  title: { color: colors.ink, fontSize: 34, fontWeight: '900' },
  subtitle: { color: colors.muted, fontSize: 16 },
  error: { color: colors.danger, fontWeight: '700' },
  notice: { gap: spacing.xs },
  noticeText: { color: colors.muted, fontSize: 13, lineHeight: 18 },
});
