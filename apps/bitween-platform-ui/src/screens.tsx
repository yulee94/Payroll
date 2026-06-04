import { useMemo, useState } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";

import {
  ActionButton,
  Badge,
  Card,
  DataTable,
  EmptyState,
  FilterBar,
  Label,
  MetricGrid,
  SectionHeader
} from "./components";
import {
  moduleDashboards,
  navigationItems,
  payrollSteps,
  platformMetrics,
  readinessCards,
  workQueue
} from "./data";
import { colors, radius, spacing, toneColor } from "./theme";
import type { NavigationItem, PlatformId } from "./types";

type ScreenProps = {
  readonly active: NavigationItem;
  readonly onSelect: (id: PlatformId) => void;
};

export function LoginScreen({ onSelect }: Pick<ScreenProps, "onSelect">) {
  const [companyCode, setCompanyCode] = useState("");
  const [userId, setUserId] = useState("");
  const canSubmit = companyCode.trim().length > 0 && userId.trim().length > 0;

  return (
    <View style={styles.loginLayout}>
      <View style={styles.loginHero}>
        <Badge tone="ready">B2B operations</Badge>
        <View style={styles.loginHeroCopy}>
          <Text style={styles.heroBrand}>Bitween</Text>
          <Text style={styles.heroTitle}>로그인 후 권한에 맞는 업무 화면으로 이동합니다.</Text>
          <Text style={styles.heroCopy}>급여, HR, 전자결재, 자료함, AI, 관리자 화면을 하나의 업무 플랫폼 경험으로 정리합니다.</Text>
        </View>
        <View style={styles.heroStatusGrid}>
          {["권한 기반 메뉴", "업무별 상태", "자료 보호"].map((item) => (
            <View key={item} style={styles.heroStatus}>
              <Text style={styles.heroStatusText}>{item}</Text>
            </View>
          ))}
        </View>
      </View>
      <Card>
        <SectionHeader
          eyebrow="Secure sign in"
          title="로그인"
          description="실제 인증 연결 전까지는 화면 이동만 확인할 수 있는 프론트엔드 프리뷰입니다."
        />
        <View style={styles.formGroup}>
          <Label size="sm" weight="bold">법인 코드</Label>
          <TextInput
            autoCapitalize="characters"
            onChangeText={setCompanyCode}
            placeholder="예: BTW-2026"
            placeholderTextColor={colors.muted}
            style={styles.input}
            value={companyCode}
          />
        </View>
        <View style={styles.formGroup}>
          <Label size="sm" weight="bold">아이디</Label>
          <TextInput
            autoCapitalize="none"
            onChangeText={setUserId}
            placeholder="업무 계정 아이디"
            placeholderTextColor={colors.muted}
            style={styles.input}
            value={userId}
          />
        </View>
        <View style={styles.formGroup}>
          <Label size="sm" weight="bold">비밀번호</Label>
          <TextInput
            placeholder="비밀번호"
            placeholderTextColor={colors.muted}
            secureTextEntry
            style={styles.input}
          />
        </View>
        <ActionButton onPress={() => onSelect("home")}>{canSubmit ? "플랫폼 홈으로 이동" : "프리뷰로 로그인"}</ActionButton>
        <View style={styles.inlineNotice}>
          <Badge tone="neutral">관리자 발급</Badge>
          <Label size="sm" muted>계정이 없으면 관리자에게 법인 계정 발급을 요청하세요.</Label>
        </View>
      </Card>
    </View>
  );
}

export function LauncherScreen({ onSelect }: ScreenProps) {
  const launcherItems = useMemo(() => navigationItems.filter((item) => item.id !== "home"), []);

  return (
    <View style={styles.stack}>
      <Card>
        <SectionHeader
          eyebrow="Overview"
          title="오늘의 플랫폼 상태"
          description="중요한 업무 상태를 먼저 보고 필요한 메뉴로 바로 이동합니다."
          action={<ActionButton onPress={() => onSelect("payroll")} variant="secondary">급여 준비 확인</ActionButton>}
        />
        <MetricGrid items={platformMetrics} />
      </Card>

      <Card>
        <SectionHeader title="오늘의 업무" description="처리 우선순위가 높은 업무를 카드로 정리합니다." />
        <View style={styles.queueGrid}>
          {workQueue.map((item) => (
            <View key={item.id} style={styles.queueItem}>
              <View style={styles.queueHeader}>
                <Badge tone={item.tone}>{item.status}</Badge>
                <Label size="sm" muted>{item.due}</Label>
              </View>
              <Label weight="bold">{item.title}</Label>
              <Label size="sm" muted>{item.meta} · {item.owner}</Label>
            </View>
          ))}
        </View>
      </Card>

      <Card>
        <SectionHeader title="플랫폼 바로가기" description="업무별 화면이 같은 구조로 이어지도록 정리했습니다." />
        <View style={styles.launcherGrid}>
          {launcherItems.map((item) => (
            <View key={item.id} style={[styles.launcherCard, { borderTopColor: item.accent }]}>
              <Label size="sm" muted>{item.eyebrow}</Label>
              <Label weight="bold">{item.label}</Label>
              <Label size="sm" muted>{item.description}</Label>
              <ActionButton onPress={() => onSelect(item.id)} variant="ghost">열기</ActionButton>
            </View>
          ))}
        </View>
      </Card>
    </View>
  );
}

export function PayrollScreen({ onSelect }: ScreenProps) {
  return (
    <View style={styles.stack}>
      <PayrollReadiness onSelect={onSelect} />
      <Card>
        <SectionHeader
          eyebrow="Payroll flow"
          title="급여 산출 작업 흐름"
          description="계산 로직은 건드리지 않고, 사용자가 다음 작업을 파악하는 화면 구조만 정리합니다."
          action={<ActionButton onPress={() => onSelect("settings")} variant="secondary">급여 설정 확인</ActionButton>}
        />
        <View style={styles.stepGrid}>
          {payrollSteps.map((step, index) => (
            <View key={step.id} style={[styles.stepCard, { borderTopColor: toneColor(step.tone) }]}>
              <Text style={styles.stepIndex}>{String(index + 1).padStart(2, "0")}</Text>
              <Badge tone={step.tone}>{step.status}</Badge>
              <Label weight="bold">{step.title}</Label>
              <Label size="sm" muted>{step.detail}</Label>
            </View>
          ))}
        </View>
        <View style={styles.actionRow}>
          <ActionButton onPress={() => onSelect("payroll")}>산출 화면 유지</ActionButton>
          <ActionButton onPress={() => onSelect("archive")} variant="secondary">월별 자료함</ActionButton>
          <ActionButton onPress={() => onSelect("ai")} variant="ghost">AI 검토 준비</ActionButton>
        </View>
      </Card>
    </View>
  );
}

export function ModuleScreen({ active, onSelect }: ScreenProps) {
  if (active.id === "home" || active.id === "payroll") {
    return (
      <Card>
        <EmptyState title="화면을 준비하고 있습니다." description="선택한 메뉴는 전용 화면으로 이동됩니다." />
      </Card>
    );
  }

  const dashboard = moduleDashboards[active.id];

  return (
    <View style={styles.stack}>
      <Card>
        <SectionHeader
          eyebrow={active.eyebrow}
          title={dashboard.title}
          description={dashboard.subtitle}
          action={<ActionButton onPress={() => onSelect(dashboard.primaryAction.target)}>{dashboard.primaryAction.label}</ActionButton>}
        />
        <MetricGrid items={dashboard.metrics} />
      </Card>

      <Card>
        <SectionHeader
          title="업무 목록"
          description="필터와 테이블 구조를 먼저 고정해 이후 API 데이터 연결 시 화면 흔들림을 줄입니다."
          action={<ActionButton onPress={() => onSelect(dashboard.secondaryAction.target)} variant="secondary">{dashboard.secondaryAction.label}</ActionButton>}
        />
        <FilterBar filters={dashboard.filters} />
        {dashboard.rows.length > 0 ? (
          <DataTable rows={dashboard.rows} />
        ) : (
          <EmptyState title={dashboard.emptyTitle} description={dashboard.emptyDescription} />
        )}
      </Card>

      <View style={styles.actionPanels}>
        {[dashboard.primaryAction, dashboard.secondaryAction].map((action) => (
          <Card key={action.label} compact>
            <Label weight="bold">{action.label}</Label>
            <Label size="sm" muted>{action.description}</Label>
            <ActionButton onPress={() => onSelect(action.target)} variant="ghost">이동</ActionButton>
          </Card>
        ))}
      </View>
    </View>
  );
}

function PayrollReadiness({ onSelect }: Pick<ScreenProps, "onSelect">) {
  return (
    <Card>
      <SectionHeader
        eyebrow="Readiness"
        title="급여 자동화 준비 현황"
        description="기존 backend readiness 결과를 연결할 RN 표시 구조입니다."
        action={<ActionButton onPress={() => onSelect("settings")} variant="secondary">설정 확인</ActionButton>}
      />
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
  actionPanels: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  actionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm
  },
  formGroup: {
    gap: spacing.xs
  },
  heroBrand: {
    color: colors.card,
    fontSize: 24,
    fontWeight: "800",
    lineHeight: 32
  },
  heroCopy: {
    color: colors.card,
    fontSize: 15,
    fontWeight: "600",
    lineHeight: 22,
    maxWidth: 460
  },
  heroStatus: {
    backgroundColor: "#FFFFFF22",
    borderColor: "#FFFFFF44",
    borderRadius: radius.md,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm
  },
  heroStatusGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm
  },
  heroStatusText: {
    color: colors.card,
    fontSize: 13,
    fontWeight: "700"
  },
  heroTitle: {
    color: colors.card,
    fontSize: 24,
    fontWeight: "800",
    lineHeight: 32,
    maxWidth: 500
  },
  inlineNotice: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm
  },
  input: {
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.text,
    fontSize: 15,
    minHeight: 44,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md
  },
  launcherCard: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderTopWidth: 4,
    borderWidth: 1,
    flexBasis: 220,
    flexGrow: 1,
    gap: spacing.sm,
    padding: spacing.md
  },
  launcherGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  loginHero: {
    backgroundColor: colors.accent,
    borderRadius: radius.lg,
    flex: 1,
    gap: spacing.xxl,
    justifyContent: "space-between",
    minHeight: 420,
    padding: spacing.xl
  },
  loginHeroCopy: {
    gap: spacing.md
  },
  loginLayout: {
    alignItems: "stretch",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.xl
  },
  queueGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  queueHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: spacing.md,
    justifyContent: "space-between"
  },
  queueItem: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexBasis: 220,
    flexGrow: 1,
    gap: spacing.sm,
    padding: spacing.md
  },
  readinessCard: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
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
    fontWeight: "800",
    lineHeight: 26
  },
  stack: {
    gap: spacing.lg
  },
  stepCard: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderTopWidth: 4,
    borderWidth: 1,
    flexBasis: 210,
    flexGrow: 1,
    gap: spacing.sm,
    padding: spacing.md
  },
  stepGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  stepIndex: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: "800"
  }
});
