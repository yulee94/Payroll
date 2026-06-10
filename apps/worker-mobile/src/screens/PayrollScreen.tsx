import { useMemo, useState } from 'react';
import { Platform, ScrollView, StyleSheet, Text } from 'react-native';
import { getPayroll } from '../api/client';
import { Card } from '../components/Card';
import { Field } from '../components/Field';
import { PrimaryButton } from '../components/PrimaryButton';
import { requireBiometric } from '../security/biometrics';
import { colors, spacing } from '../theme/tokens';
import type { MobileAuthState, PayrollSummary } from '../types';
import { useAsyncAction } from '../state/useAsyncAction';

interface PayrollScreenProps {
  auth: MobileAuthState;
}

function won(value: number): string {
  return `${Math.round(value).toLocaleString('ko-KR')}원`;
}

function currentPeriod(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

export function PayrollScreen({ auth }: PayrollScreenProps) {
  const [period, setPeriod] = useState(currentPeriod());
  const [summary, setSummary] = useState<PayrollSummary | null>(null);
  const action = useAsyncAction();
  const statusLabel = useMemo(() => {
    if (!summary) return '';
    return summary.status === 'finalized' ? '확정 급여' : '현재월 추정치';
  }, [summary]);

  const load = async (): Promise<void> => {
    await action.run(async () => {
      const biometric = await requireBiometric('급여정보 열람 인증', Platform.OS === 'ios' ? 'ios' : 'android');
      if (!biometric.ok) throw new Error('급여정보 열람에는 생체인증이 필요합니다.');
      const result = await getPayroll(auth, period);
      setSummary(result);
      return result;
    });
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.heading}>내 급여 / 연차</Text>
      <Card>
        <Field label="급여월" value={period} onChangeText={setPeriod} hint="YYYY-MM 형식으로 입력" />
        <PrimaryButton label="생체인증 후 조회" onPress={load} disabled={action.busy || period.length < 7} />
        {action.error ? <Text style={styles.error}>{action.error}</Text> : null}
      </Card>
      {summary ? (
        <Card>
          <Text style={styles.badge}>{statusLabel}</Text>
          <Text style={styles.name}>{summary.employee_name} · {summary.period}</Text>
          <Text style={styles.line}>총지급: {won(summary.gross_pay)}</Text>
          <Text style={styles.line}>세금: {won(summary.tax)}</Text>
          <Text style={styles.line}>공제합계: {won(summary.total_deduction)}</Text>
          <Text style={styles.net}>실수령: {won(summary.net_pay)}</Text>
          <Text style={styles.line}>잔여연차: {summary.remaining_leave.toLocaleString('ko-KR')}일</Text>
          <Text style={styles.line}>근무시간: {summary.work_hours.toLocaleString('ko-KR')}시간</Text>
          {summary.estimate_notice ? <Text style={styles.notice}>{summary.estimate_notice}</Text> : null}
        </Card>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: colors.bg, gap: spacing.lg, padding: spacing.lg },
  heading: { color: colors.ink, fontSize: 24, fontWeight: '900' },
  badge: { alignSelf: 'flex-start', backgroundColor: '#dbeafe', borderRadius: 999, color: colors.primary, fontWeight: '900', paddingHorizontal: spacing.md, paddingVertical: spacing.xs },
  name: { color: colors.ink, fontSize: 20, fontWeight: '900' },
  line: { color: colors.ink, fontSize: 16 },
  net: { color: colors.success, fontSize: 22, fontWeight: '900' },
  notice: { color: colors.warning, fontSize: 13, lineHeight: 19 },
  error: { color: colors.danger, fontWeight: '800' },
});
