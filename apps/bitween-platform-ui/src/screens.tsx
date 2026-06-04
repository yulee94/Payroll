import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { Badge, Card, Label } from "./components";
import { readinessCards, workQueue } from "./data";
import { colors, spacing, toneColor } from "./theme";
import type { NavigationItem, PlatformId } from "./types";

type ScreenProps = {
  readonly active: NavigationItem;
  readonly onSelect: (id: PlatformId) => void;
};

export function LoginScreen({ onSelect }: Pick<ScreenProps, "onSelect">) {
  return (
    <View style={styles.loginLayout}>
      <View style={styles.loginHero}>
        <Label size="xl" weight="bold">Bitween</Label>
        <Label muted>법인 업무 플랫폼</Label>
        <Text style={styles.heroCopy}>권한에 맞는 플랫폼과 자료만 보이도록 법인 계정으로 접속합니다.</Text>
      </View>
      <Card>
        <Label size="xl" weight="bold">로그인</Label>
        <Label muted>소속 법인 계정으로 로그인하면 플랫폼 홈으로 이동합니다.</Label>
        <TextInput placeholder="아이디" style={styles.input} />
        <TextInput placeholder="비밀번호" secureTextEntry style={styles.input} />
        <Pressable style={styles.primaryButton} onPress={() => onSelect("home")}>
          <Text style={styles.primaryButtonText}>로그인</Text>
        </Pressable>
        <Label size="sm" muted>계정이 없으면 관리자에게 발급을 요청하세요.</Label>
      </Card>
    </View>
  );
}

export function LauncherScreen({ onSelect }: ScreenProps) {
  return (
    <View style={styles.stack}>
      <Card>
        <Label size="xl" weight="bold">오늘의 업무</Label>
        <Label muted>급여, 전자결재, 자료함의 주요 상태를 먼저 확인합니다.</Label>
        <View style={styles.queueGrid}>
          {workQueue.map((item) => (
            <View key={item.title} style={styles.queueItem}>
              <Badge tone={item.tone}>{item.status}</Badge>
              <Label weight="bold">{item.title}</Label>
              <Label size="sm" muted>{item.meta}</Label>
            </View>
          ))}
        </View>
      </Card>
      <PayrollReadiness onSelect={onSelect} />
    </View>
  );
}

export function PayrollScreen({ onSelect }: ScreenProps) {
  return (
    <View style={styles.stack}>
      <PayrollReadiness onSelect={onSelect} />
      <Card>
        <Label size="lg" weight="bold">급여툴 진입</Label>
        <Label muted>파일 업로드, 처리 결과, 월별 보고, 설정으로 이어지는 작업 흐름입니다.</Label>
        <View style={styles.actionRow}>
          {[
            ["산출 시작", "payroll"],
            ["월별 자료함", "archive"],
            ["급여 설정", "settings"]
          ].map(([label, target]) => (
            <Pressable key={label} style={styles.secondaryButton} onPress={() => onSelect(target as PlatformId)}>
              <Text style={styles.secondaryButtonText}>{label}</Text>
            </Pressable>
          ))}
        </View>
      </Card>
    </View>
  );
}

export function ModuleScreen({ active }: ScreenProps) {
  return (
    <View style={styles.stack}>
      <Card>
        <Badge tone="neutral">Frontend shell</Badge>
        <Label size="lg" weight="bold">{active.label} 화면</Label>
        <Label muted>{active.description}</Label>
      </Card>
      <Card>
        <Label weight="bold">목록 / 탭 / 필터 자리</Label>
        <View style={styles.tableHeader}>
          <Text style={styles.tableCell}>구분</Text>
          <Text style={styles.tableCell}>상태</Text>
          <Text style={styles.tableCell}>다음 작업</Text>
        </View>
        <View style={styles.tableRow}>
          <Text style={styles.tableCell}>데이터 연결 전</Text>
          <Text style={styles.tableCell}>대기</Text>
          <Text style={styles.tableCell}>API contract 연결</Text>
        </View>
      </Card>
    </View>
  );
}

function PayrollReadiness({ onSelect }: Pick<ScreenProps, "onSelect">) {
  return (
    <Card>
      <View style={styles.cardHeader}>
        <View>
          <Label size="lg" weight="bold">급여 자동화 준비 현황</Label>
          <Label muted>기존 backend readiness 결과를 연결할 RN 표시 구조입니다.</Label>
        </View>
        <Pressable style={styles.secondaryButton} onPress={() => onSelect("settings")}>
          <Text style={styles.secondaryButtonText}>설정 확인</Text>
        </Pressable>
      </View>
      <View style={styles.readinessGrid}>
        {readinessCards.map((card) => (
          <View key={card.id} style={[styles.readinessCard, { borderTopColor: toneColor(card.tone) }]}>
            <Label size="sm" muted>{card.title}</Label>
            <Text style={[styles.readinessValue, { color: toneColor(card.tone) }]}>{card.value}</Text>
            <Label size="sm">{card.detail}</Label>
          </View>
        ))}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  actionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm
  },
  cardHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: spacing.lg,
    justifyContent: "space-between"
  },
  heroCopy: {
    color: colors.card,
    fontSize: 20,
    fontWeight: "700",
    lineHeight: 28,
    marginTop: spacing.xl,
    maxWidth: 420
  },
  input: {
    borderColor: colors.border,
    borderRadius: 6,
    borderWidth: 1,
    fontSize: 15,
    padding: spacing.md
  },
  loginHero: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    flex: 1,
    minHeight: 360,
    padding: spacing.xl
  },
  loginLayout: {
    alignItems: "stretch",
    flexDirection: "row",
    gap: spacing.xl
  },
  primaryButton: {
    alignItems: "center",
    backgroundColor: colors.accent,
    borderRadius: 6,
    padding: spacing.md
  },
  primaryButtonText: {
    color: colors.card,
    fontWeight: "700"
  },
  queueGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  queueItem: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: 8,
    borderWidth: 1,
    flexBasis: 220,
    flexGrow: 1,
    gap: spacing.sm,
    padding: spacing.md
  },
  readinessCard: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: 8,
    borderTopWidth: 4,
    borderWidth: 1,
    flexBasis: 220,
    flexGrow: 1,
    gap: spacing.xs,
    padding: spacing.md
  },
  readinessGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  readinessValue: {
    fontSize: 20,
    fontWeight: "800"
  },
  secondaryButton: {
    backgroundColor: colors.accentSoft,
    borderRadius: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm
  },
  secondaryButtonText: {
    color: colors.accent,
    fontWeight: "700"
  },
  stack: {
    gap: spacing.lg
  },
  tableCell: {
    color: colors.text,
    flex: 1,
    fontSize: 13
  },
  tableHeader: {
    backgroundColor: colors.accentSoft,
    borderRadius: 6,
    flexDirection: "row",
    padding: spacing.md
  },
  tableRow: {
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: "row",
    padding: spacing.md
  }
});
