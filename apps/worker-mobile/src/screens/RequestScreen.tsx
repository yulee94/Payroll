import { useState } from 'react';
import { ScrollView, StyleSheet, Text } from 'react-native';
import { ApiError, createAttendanceRequest } from '../api/client';
import { Card } from '../components/Card';
import { Field } from '../components/Field';
import { PrimaryButton } from '../components/PrimaryButton';
import { enqueueOfflineRequest } from '../offline/localQueue';
import { colors, spacing } from '../theme/tokens';
import type { AttendanceRequestInput, MobileAuthState } from '../types';
import { useAsyncAction } from '../state/useAsyncAction';

interface RequestScreenProps {
  auth: MobileAuthState;
  deviceUid: string;
}

export function RequestScreen({ auth, deviceUid }: RequestScreenProps) {
  const [request, setRequest] = useState<AttendanceRequestInput>({
    title: '외출신청서',
    attendance_type: '외출',
    start_at: '',
    end_at: '',
    site_name: '',
    reason: '',
  });
  const [done, setDone] = useState(false);
  const [queued, setQueued] = useState(false);
  const action = useAsyncAction();

  const update = <K extends keyof AttendanceRequestInput>(key: K, value: AttendanceRequestInput[K]): void => {
    setRequest((prev) => ({ ...prev, [key]: value }));
  };

  const submit = async (): Promise<void> => {
    await action.run(async () => {
      setDone(false);
      setQueued(false);
      try {
        await createAttendanceRequest(auth, request);
        setDone(true);
      } catch (err) {
        if (err instanceof ApiError) {
          throw err;
        }
        const branchId = auth.branchId || request.site_name || 'unassigned';
        await enqueueOfflineRequest({
          deviceId: auth.deviceUid || deviceUid,
          branchId,
          requestType: 'attendance_request',
          payload: { ...request, branch_id: branchId },
        });
        setQueued(true);
      }
    });
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.heading}>근무지 이탈 / 휴가 신청</Text>
      <Card>
        <Field label="문서 제목" value={request.title} onChangeText={(v) => update('title', v)} />
        <Field label="신청 유형" value={request.attendance_type} onChangeText={(v) => update('attendance_type', v as AttendanceRequestInput['attendance_type'])} hint="연차, 병가, 출장, 외출, 조퇴 중 선택" />
        <Field label="시작" value={request.start_at} onChangeText={(v) => update('start_at', v)} hint="예: 2026-06-04T10:00:00" />
        <Field label="종료" value={request.end_at} onChangeText={(v) => update('end_at', v)} hint="예: 2026-06-04T12:00:00" />
        <Field label="사업장" value={request.site_name} onChangeText={(v) => update('site_name', v)} hint="출근 기록과 연결되는 사업장명" />
        <Field label="사유" value={request.reason} onChangeText={(v) => update('reason', v)} multiline />
        <PrimaryButton label="결재 요청" onPress={submit} disabled={action.busy || !request.start_at || !request.end_at || !request.reason} />
        {done ? <Text style={styles.success}>결재 요청이 등록되었습니다. 승인 전 이탈 시 알림이 발생합니다.</Text> : null}
        {queued ? <Text style={styles.success}>네트워크 복구 후 자동 동기화되도록 오프라인 큐에 저장했습니다.</Text> : null}
        {action.error ? <Text style={styles.error}>{action.error}</Text> : null}
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: colors.bg, gap: spacing.lg, padding: spacing.lg },
  heading: { color: colors.ink, fontSize: 24, fontWeight: '900' },
  success: { color: colors.success, fontWeight: '800', lineHeight: 20 },
  error: { color: colors.danger, fontWeight: '800' },
});
