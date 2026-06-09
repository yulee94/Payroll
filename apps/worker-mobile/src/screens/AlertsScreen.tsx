import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { acknowledgeAlert, listAlerts } from '../api/client';
import { Card } from '../components/Card';
import { PrimaryButton } from '../components/PrimaryButton';
import { colors, spacing } from '../theme/tokens';
import type { GeofenceAlert, MobileAuthState } from '../types';
import { useAsyncAction } from '../state/useAsyncAction';

interface AlertsScreenProps {
  auth: MobileAuthState;
}

export function AlertsScreen({ auth }: AlertsScreenProps) {
  const [alerts, setAlerts] = useState<GeofenceAlert[]>([]);
  const action = useAsyncAction();

  const refresh = async (): Promise<void> => {
    await action.run(async () => {
      const rows = await listAlerts(auth);
      setAlerts(rows);
      return rows;
    });
  };

  useEffect(() => {
    void refresh();
  }, [auth]);

  const ack = async (id: string): Promise<void> => {
    await action.run(async () => {
      await acknowledgeAlert(auth, id);
      await refresh();
    });
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.heading}>관리자 알림</Text>
        <PrimaryButton label="새로고침" onPress={refresh} disabled={action.busy} />
      </View>
      {action.error ? <Text style={styles.error}>{action.error}</Text> : null}
      {alerts.length === 0 ? <Text style={styles.muted}>열린 알림이 없습니다.</Text> : null}
      {alerts.map((alert) => (
        <Card key={alert.id}>
          <Text style={styles.title}>{alert.employee_name} · {alert.site_name}</Text>
          <Text style={styles.line}>{alert.detected_at}</Text>
          <Text style={styles.warning}>{alert.note || '승인 없는 근무지 이탈'}</Text>
          <PrimaryButton label="확인 처리" onPress={() => ack(alert.id)} disabled={action.busy} />
        </Card>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: colors.bg, gap: spacing.lg, padding: spacing.lg },
  headerRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  heading: { color: colors.ink, fontSize: 24, fontWeight: '900' },
  title: { color: colors.ink, fontSize: 18, fontWeight: '900' },
  line: { color: colors.muted },
  warning: { color: colors.warning, fontWeight: '800' },
  muted: { color: colors.muted },
  error: { color: colors.danger, fontWeight: '800' },
});
