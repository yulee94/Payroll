import { useEffect, useState } from 'react';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { checkAttendance, getCurrentGeofence } from '../api/client';
import { Card } from '../components/Card';
import { PrimaryButton } from '../components/PrimaryButton';
import { getCurrentCoordinates, startShiftGeofence, stopShiftGeofence } from '../location/geofence';
import { requireBiometric } from '../security/biometrics';
import { colors, spacing } from '../theme/tokens';
import type { AttendanceEvent, MobileAuthState, SiteGeofence } from '../types';
import { useAsyncAction } from '../state/useAsyncAction';

interface HomeScreenProps {
  auth: MobileAuthState;
  deviceUid: string;
}

export function HomeScreen({ auth, deviceUid }: HomeScreenProps) {
  const [geofence, setGeofence] = useState<SiteGeofence | null>(null);
  const [lastEvent, setLastEvent] = useState<AttendanceEvent | null>(null);
  const [checkedIn, setCheckedIn] = useState(false);
  const action = useAsyncAction();

  useEffect(() => {
    void action.run(async () => {
      const current = await getCurrentGeofence(auth);
      setGeofence(current);
      return current;
    });
  }, [auth]);

  const submitAttendance = async (eventType: 'clock_in' | 'clock_out'): Promise<void> => {
    await action.run(async () => {
      if (!geofence) throw new Error('사업장 지오펜스가 설정되지 않았습니다.');
      const biometric = await requireBiometric(
        eventType === 'clock_in' ? '출근 인증' : '퇴근 인증',
        Platform.OS === 'ios' ? 'ios' : 'android',
      );
      if (!biometric.ok || biometric.kind === 'none') throw new Error('생체인증에 실패했습니다.');
      const coords = await getCurrentCoordinates();
      const event = await checkAttendance(auth, {
        deviceUid,
        siteName: geofence.site_name,
        eventType,
        latitude: coords.latitude,
        longitude: coords.longitude,
        biometricKind: biometric.kind,
        biometricRef: biometric.ref,
      });
      setLastEvent(event);
      const verified = event.status === 'verified';
      if (eventType === 'clock_in' && verified) {
        setCheckedIn(true);
        await startShiftGeofence(auth, deviceUid, geofence);
      }
      if (eventType === 'clock_out' && verified) {
        setCheckedIn(false);
        await stopShiftGeofence();
      }
      return event;
    });
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.heading}>안녕하세요, {auth.user.employee_name}님</Text>
      <Card>
        <Text style={styles.label}>현재 사업장</Text>
        <Text style={styles.value}>{geofence?.site_name ?? '불러오는 중'}</Text>
        <Text style={styles.muted}>근무 중 지오펜스 감시는 출근 후에만 활성화됩니다.</Text>
      </Card>
      <Card>
        <Text style={styles.label}>근무 상태</Text>
        <Text style={[styles.status, { color: checkedIn ? colors.success : colors.muted }]}>
          {checkedIn ? '출근 상태 · 이탈 감시 중' : '퇴근/대기 상태'}
        </Text>
        <View style={styles.row}>
          <PrimaryButton label="출근" onPress={() => submitAttendance('clock_in')} disabled={action.busy || checkedIn} tone="success" />
          <PrimaryButton label="퇴근" onPress={() => submitAttendance('clock_out')} disabled={action.busy || !checkedIn} tone="danger" />
        </View>
        {lastEvent ? (
          <Text style={styles.muted}>
            최근 기록: {lastEvent.event_type === 'clock_in' ? '출근' : '퇴근'} · {lastEvent.status}
            {lastEvent.note ? ` · ${lastEvent.note}` : ''}
          </Text>
        ) : null}
        {action.error ? <Text style={styles.error}>{action.error}</Text> : null}
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: colors.bg, gap: spacing.lg, padding: spacing.lg },
  heading: { color: colors.ink, fontSize: 24, fontWeight: '900' },
  label: { color: colors.muted, fontSize: 13, fontWeight: '800' },
  value: { color: colors.ink, fontSize: 22, fontWeight: '900' },
  status: { fontSize: 18, fontWeight: '900' },
  muted: { color: colors.muted, lineHeight: 20 },
  row: { flexDirection: 'row', gap: spacing.md },
  error: { color: colors.danger, fontWeight: '800' },
});
