import { useEffect, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

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
  payrollSettingsRows,
  payrollSteps,
  platformMetrics,
  previewRows,
  readinessCards,
  workQueue
} from "./data";
import { colors, radius, spacing, toneColor } from "./theme";
import type { ModuleRow, NavigationItem, PayrollStep, PlatformId, ReadinessCard, WorkQueueItem } from "./types";

type ScreenProps = {
  readonly active: NavigationItem;
  readonly onSelect: (id: PlatformId) => void;
};

type ModuleId = keyof typeof moduleDashboards;

const demoAccount = {
  companyCode: "0000",
  password: "admin",
  userId: "admin"
} as const;

function isModuleId(id: PlatformId): id is ModuleId {
  return id !== "home" && id !== "payroll";
}

export function LoginScreen({ onSelect }: Pick<ScreenProps, "onSelect">) {
  const [companyCode, setCompanyCode] = useState("");
  const [feedback, setFeedback] = useState("");
  const [password, setPassword] = useState("");
  const [userId, setUserId] = useState("");
  const canSubmit = companyCode.trim().length > 0 && userId.trim().length > 0 && password.trim().length > 0;

  const handleLogin = () => {
    if (!canSubmit) {
      setFeedback("demo 계정은 법인코드 0000, 아이디 admin, 비밀번호 admin입니다.");
      return;
    }
    if (
      companyCode.trim() !== demoAccount.companyCode ||
      userId.trim() !== demoAccount.userId ||
      password.trim() !== demoAccount.password
    ) {
      setFeedback("demo 계정 정보가 일치하지 않습니다. 법인코드 0000, 아이디 admin, 비밀번호 admin으로 입력하세요.");
      return;
    }
    setFeedback("");
    onSelect("home");
  };

  const handleDemoLogin = () => {
    setCompanyCode(demoAccount.companyCode);
    setUserId(demoAccount.userId);
    setPassword(demoAccount.password);
    setFeedback("");
    onSelect("home");
  };

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
      <Card style={styles.loginCard}>
        <SectionHeader
          eyebrow="Secure sign in"
          title="로그인"
          description="법인 계정으로 접속하면 권한에 맞는 업무 화면으로 이동합니다."
        />
        <View style={styles.formGroup}>
          <Label size="sm" weight="bold">법인 코드</Label>
          <TextInput
            autoCapitalize="characters"
            autoComplete="organization"
            onChangeText={setCompanyCode}
            placeholder="0000"
            placeholderTextColor={colors.muted}
            returnKeyType="next"
            style={styles.input}
            value={companyCode}
          />
        </View>
        <View style={styles.formGroup}>
          <Label size="sm" weight="bold">아이디</Label>
          <TextInput
            autoCapitalize="none"
            autoComplete="username"
            onChangeText={setUserId}
            placeholder="admin"
            placeholderTextColor={colors.muted}
            returnKeyType="next"
            style={styles.input}
            value={userId}
          />
        </View>
        <View style={styles.formGroup}>
          <Label size="sm" weight="bold">비밀번호</Label>
          <TextInput
            autoComplete="password"
            onChangeText={setPassword}
            placeholder="admin"
            placeholderTextColor={colors.muted}
            returnKeyType="done"
            secureTextEntry
            style={styles.input}
            value={password}
          />
        </View>
        {feedback ? (
          <View style={styles.inlineNotice}>
            <Badge tone="attention">확인 필요</Badge>
            <Label size="sm" muted>{feedback}</Label>
          </View>
        ) : null}
        <View style={styles.loginActions}>
          <ActionButton onPress={handleLogin}>{canSubmit ? "플랫폼 홈으로 이동" : "로그인"}</ActionButton>
          <ActionButton onPress={handleDemoLogin} variant="secondary">Demo 계정으로 접속</ActionButton>
        </View>
        <View style={styles.inlineNotice}>
          <Badge tone="neutral">Demo 계정</Badge>
          <Label size="sm" muted>법인코드 0000 · 아이디 admin · 비밀번호 admin</Label>
        </View>
      </Card>
    </View>
  );
}

export function LauncherScreen({ onSelect }: ScreenProps) {
  const launcherItems = useMemo(() => navigationItems.filter((item) => item.id !== "home"), []);
  const [selectedQueueId, setSelectedQueueId] = useState<string | undefined>(workQueue[0]?.id);
  const selectedQueue = workQueue.find((item) => item.id === selectedQueueId) ?? workQueue[0];

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
            <Pressable
              accessibilityRole="button"
              key={item.id}
              onPress={() => setSelectedQueueId(item.id)}
              style={({ pressed }) => [
                styles.queueItem,
                selectedQueueId === item.id && styles.queueItemSelected,
                pressed && styles.buttonPressed
              ]}
            >
              <View style={styles.queueHeader}>
                <Badge tone={item.tone}>{item.status}</Badge>
                <Label size="sm" muted>{item.due}</Label>
              </View>
              <Label weight="bold">{item.title}</Label>
              <Label size="sm" muted>{item.meta} · {item.owner}</Label>
            </Pressable>
          ))}
        </View>
        {selectedQueue ? <WorkQueueDetailPanel item={selectedQueue} onSelect={onSelect} /> : null}
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
      <Card>
        <SectionHeader
          eyebrow="Settings summary"
          title="급여 산출 설정 요약"
          description="산출 전 확인해야 할 핵심 급여 기준을 한눈에 검토합니다."
          action={<ActionButton onPress={() => onSelect("settings")} variant="secondary">상세 설정</ActionButton>}
        />
        <DataTable rows={payrollSettingsRows} />
      </Card>
      <Card>
        <SectionHeader
          eyebrow="Preview and archive"
          title="파일 미리보기 작업"
          description="Excel 미리보기, 시트 선택, 필터 초기화, 수정본 업로드 같은 사용자 흐름을 분리했습니다."
          action={<ActionButton onPress={() => onSelect("archive")} variant="secondary">자료함 열기</ActionButton>}
        />
        <DataTable rows={previewRows} />
      </Card>
    </View>
  );
}

export function PayrollScreen({ onSelect }: ScreenProps) {
  const [selectedReadinessId, setSelectedReadinessId] = useState<string | undefined>(readinessCards[0]?.id);
  const [selectedStepId, setSelectedStepId] = useState<string | undefined>(payrollSteps[0]?.id);
  const selectedReadiness = readinessCards.find((card) => card.id === selectedReadinessId) ?? readinessCards[0];
  const selectedStep = payrollSteps.find((step) => step.id === selectedStepId) ?? payrollSteps[0];

  return (
    <View style={styles.stack}>
      <PayrollReadiness onSelect={onSelect} selectedId={selectedReadiness?.id} onSelectCard={(card) => setSelectedReadinessId(card.id)} />
      {selectedReadiness ? <PayrollReadinessDetail card={selectedReadiness} /> : null}
      <Card>
        <SectionHeader
          eyebrow="Payroll flow"
          title="급여 산출 작업 흐름"
          description="운영 기준 확인부터 입력 자료 준비, 결과 검토, 자료함 저장까지 순서대로 진행합니다."
          action={<ActionButton onPress={() => onSelect("settings")} variant="secondary">급여 설정 확인</ActionButton>}
        />
        <View style={styles.stepGrid}>
          {payrollSteps.map((step, index) => (
            <Pressable
              accessibilityRole="button"
              key={step.id}
              onPress={() => setSelectedStepId(step.id)}
              style={({ pressed }) => [
                styles.stepCard,
                { borderTopColor: toneColor(step.tone) },
                selectedStepId === step.id && styles.stepCardSelected,
                pressed && styles.buttonPressed
              ]}
            >
              <Text style={styles.stepIndex}>{String(index + 1).padStart(2, "0")}</Text>
              <Badge tone={step.tone}>{step.status}</Badge>
              <Label weight="bold">{step.title}</Label>
              <Label size="sm" muted>{step.detail}</Label>
            </Pressable>
          ))}
        </View>
        {selectedStep ? <PayrollStepDetail step={selectedStep} /> : null}
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
  if (!isModuleId(active.id)) {
    return (
      <Card>
        <EmptyState title="화면을 준비하고 있습니다." description="선택한 메뉴는 전용 화면으로 이동됩니다." />
      </Card>
    );
  }

  const dashboard = moduleDashboards[active.id];
  const defaultFilter = dashboard.filters[0] ?? "전체";
  const [activeFilter, setActiveFilter] = useState<string>(defaultFilter);
  const [search, setSearch] = useState("");
  const [selectedRowId, setSelectedRowId] = useState<string | undefined>(dashboard.rows[0]?.id);
  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return dashboard.rows.filter((row) => {
      const haystack = [row.category, row.status, row.owner, row.nextStep].join(" ").toLowerCase();
      const matchesFilter = activeFilter === "전체" || haystack.includes(activeFilter.toLowerCase());
      const matchesSearch = normalizedSearch.length === 0 || haystack.includes(normalizedSearch);
      return matchesFilter && matchesSearch;
    });
  }, [activeFilter, dashboard.rows, search]);
  const selectedRow = useMemo(
    () => filteredRows.find((row) => row.id === selectedRowId) ?? filteredRows[0],
    [filteredRows, selectedRowId]
  );

  useEffect(() => {
    setActiveFilter(defaultFilter);
    setSearch("");
    setSelectedRowId(dashboard.rows[0]?.id);
  }, [active.id, dashboard.rows, defaultFilter]);

  useEffect(() => {
    setSelectedRowId((current) => {
      if (filteredRows.some((row) => row.id === current)) {
        return current;
      }
      return filteredRows[0]?.id;
    });
  }, [filteredRows]);

  const selectRow = (row: ModuleRow) => {
    setSelectedRowId(row.id);
  };

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
          description="필터로 상태를 좁히고 필요한 다음 작업을 확인합니다."
          action={<ActionButton onPress={() => onSelect(dashboard.secondaryAction.target)} variant="secondary">{dashboard.secondaryAction.label}</ActionButton>}
        />
        <View style={styles.listToolbar}>
          <FilterBar active={activeFilter} filters={dashboard.filters} onSelect={setActiveFilter} />
          <View style={styles.searchGroup}>
            <Label size="sm" weight="bold">검색</Label>
            <TextInput
              autoCapitalize="none"
              onChangeText={setSearch}
              placeholder="업무, 상태, 담당자 검색"
              placeholderTextColor={colors.muted}
              returnKeyType="search"
              style={styles.input}
              value={search}
            />
          </View>
        </View>
        <View style={styles.listSummary}>
          <Label weight="bold">{filteredRows.length}건</Label>
          <Label size="sm" muted>{activeFilter} 필터{search ? ` · "${search}" 검색` : ""}</Label>
        </View>
        {dashboard.rows.length > 0 ? (
          <DataTable onRowPress={selectRow} rows={filteredRows} selectedRowId={selectedRow?.id} />
        ) : (
          <EmptyState title={dashboard.emptyTitle} description={dashboard.emptyDescription} />
        )}
        {selectedRow ? <WorkDetailPanel row={selectedRow} onSelect={onSelect} /> : null}
      </Card>

      <View style={styles.actionPanels}>
        {[dashboard.primaryAction, dashboard.secondaryAction].map((action) => (
          <Card key={action.label} compact style={styles.actionPanelCard}>
            <Label weight="bold">{action.label}</Label>
            <Label size="sm" muted>{action.description}</Label>
            <ActionButton onPress={() => onSelect(action.target)} variant="ghost">이동</ActionButton>
          </Card>
        ))}
      </View>
    </View>
  );
}

type PayrollReadinessProps = Pick<ScreenProps, "onSelect"> & {
  readonly onSelectCard: (card: ReadinessCard) => void;
  readonly selectedId?: string;
};

function PayrollReadiness({ onSelect, onSelectCard, selectedId }: PayrollReadinessProps) {
  return (
    <Card>
      <SectionHeader
        eyebrow="Readiness"
        title="급여 자동화 준비 현황"
        description="산출 전 필요한 기준과 자료 상태를 먼저 확인합니다."
        action={<ActionButton onPress={() => onSelect("settings")} variant="secondary">설정 확인</ActionButton>}
      />
      <View style={styles.readinessGrid}>
        {readinessCards.map((card) => (
          <Pressable
            accessibilityRole="button"
            key={card.id}
            onPress={() => onSelectCard(card)}
            style={({ pressed }) => [
              styles.readinessCard,
              { borderTopColor: toneColor(card.tone) },
              selectedId === card.id && styles.readinessCardSelected,
              pressed && styles.buttonPressed
            ]}
          >
            <Label size="sm" muted>{card.title}</Label>
            <Text style={[styles.readinessValue, { color: toneColor(card.tone) }]}>{card.value}</Text>
            <Label size="sm">{card.detail}</Label>
          </Pressable>
        ))}
      </View>
    </Card>
  );
}

function PayrollReadinessDetail({ card }: { readonly card: ReadinessCard }) {
  return (
    <View style={styles.detailPanel}>
      <View style={styles.detailHeader}>
        <View style={styles.detailTitle}>
          <Label size="sm" muted>선택한 준비 항목</Label>
          <Label weight="bold">{card.title}</Label>
        </View>
        <Badge tone={card.tone}>{card.value}</Badge>
      </View>
      <Label>{card.detail}</Label>
      <View style={styles.actionRow}>
        <ActionButton onPress={() => undefined} variant="secondary">준비 상태 확인</ActionButton>
        <ActionButton onPress={() => undefined} variant="ghost">관련 자료 보기</ActionButton>
      </View>
    </View>
  );
}

function PayrollStepDetail({ step }: { readonly step: PayrollStep }) {
  return (
    <View style={styles.detailPanel}>
      <View style={styles.detailHeader}>
        <View style={styles.detailTitle}>
          <Label size="sm" muted>선택한 산출 단계</Label>
          <Label weight="bold">{step.title}</Label>
        </View>
        <Badge tone={step.tone}>{step.status}</Badge>
      </View>
      <Label>{step.detail}</Label>
      <View style={styles.actionRow}>
        <ActionButton onPress={() => undefined} variant="secondary">단계 작업 보기</ActionButton>
        <ActionButton onPress={() => undefined} variant="ghost">도움말 확인</ActionButton>
      </View>
    </View>
  );
}

function WorkDetailPanel({ row, onSelect }: { readonly row: ModuleRow; readonly onSelect: (id: PlatformId) => void }) {
  const target = workRowTarget(row);

  return (
    <View style={styles.detailPanel}>
      <View style={styles.detailHeader}>
        <View style={styles.detailTitle}>
          <Label size="sm" muted>선택한 업무</Label>
          <Label weight="bold">{row.category}</Label>
        </View>
        <Badge tone={row.tone}>{row.status}</Badge>
      </View>
      <View style={styles.detailGrid}>
        <View style={styles.detailItem}>
          <Label size="sm" muted>담당</Label>
          <Label weight="bold">{row.owner}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>다음 작업</Label>
          <Label>{row.nextStep}</Label>
        </View>
      </View>
      <View style={styles.actionRow}>
        <ActionButton onPress={() => onSelect(target)} variant="secondary">관련 화면 열기</ActionButton>
        <ActionButton onPress={() => undefined} variant="ghost">담당자 확인</ActionButton>
      </View>
    </View>
  );
}

function WorkQueueDetailPanel({ item, onSelect }: { readonly item: WorkQueueItem; readonly onSelect: (id: PlatformId) => void }) {
  const target = workQueueTarget(item);

  return (
    <View style={styles.detailPanel}>
      <View style={styles.detailHeader}>
        <View style={styles.detailTitle}>
          <Label size="sm" muted>선택한 오늘의 업무</Label>
          <Label weight="bold">{item.title}</Label>
        </View>
        <Badge tone={item.tone}>{item.status}</Badge>
      </View>
      <View style={styles.detailGrid}>
        <View style={styles.detailItem}>
          <Label size="sm" muted>담당</Label>
          <Label weight="bold">{item.owner}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>기한</Label>
          <Label weight="bold">{item.due}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>업무 영역</Label>
          <Label>{item.meta}</Label>
        </View>
      </View>
      <View style={styles.actionRow}>
        <ActionButton onPress={() => onSelect(target)} variant="secondary">관련 화면 열기</ActionButton>
        <ActionButton onPress={() => undefined} variant="ghost">담당 흐름 확인</ActionButton>
      </View>
    </View>
  );
}

function workQueueTarget(item: WorkQueueItem): PlatformId {
  if (item.meta.includes("급여")) {
    return "payroll";
  }

  if (item.meta.includes("워크") || item.meta.includes("결재")) {
    return "workflow";
  }

  if (item.meta.includes("아카이브") || item.meta.includes("자료")) {
    return "archive";
  }

  return "home";
}

function workRowTarget(row: ModuleRow): PlatformId {
  const haystack = [row.category, row.status, row.owner, row.nextStep].join(" ");

  if (haystack.includes("급여") || haystack.includes("산출") || haystack.includes("월 기본근로시간")) {
    return "payroll";
  }

  if (haystack.includes("결재") || haystack.includes("회람") || haystack.includes("기안")) {
    return "workflow";
  }

  if (haystack.includes("자료") || haystack.includes("보고서") || haystack.includes("파일") || haystack.includes("폴더")) {
    return "archive";
  }

  if (haystack.includes("권한") || haystack.includes("사용자") || haystack.includes("역할") || haystack.includes("법인")) {
    return "admin";
  }

  if (haystack.includes("설정") || haystack.includes("알림") || haystack.includes("환경")) {
    return "settings";
  }

  if (haystack.includes("AI") || haystack.includes("요약") || haystack.includes("초안")) {
    return "ai";
  }

  if (haystack.includes("근태") || haystack.includes("증명서") || haystack.includes("직원")) {
    return "hr";
  }

  return "home";
}

const styles = StyleSheet.create({
  actionPanels: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  actionPanelCard: {
    flexBasis: 220,
    flexGrow: 1
  },
  actionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm
  },
  buttonPressed: {
    opacity: 0.86
  },
  detailGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  detailHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
    justifyContent: "space-between"
  },
  detailItem: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexBasis: 220,
    flexGrow: 1,
    gap: spacing.xs,
    padding: spacing.md
  },
  detailPanel: {
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.md
  },
  detailTitle: {
    gap: spacing.xs
  },
  formGroup: {
    gap: spacing.xs
  },
  heroCopy: {
    color: colors.card,
    fontSize: 15,
    fontWeight: "600",
    lineHeight: 22,
    maxWidth: 460
  },
  heroBrand: {
    color: colors.card,
    fontSize: 24,
    fontWeight: "800",
    lineHeight: 32
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
  listSummary: {
    alignItems: "center",
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm
  },
  listToolbar: {
    alignItems: "flex-end",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
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
  loginActions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm
  },
  loginHero: {
    backgroundColor: colors.accent,
    borderRadius: radius.lg,
    flexBasis: 420,
    flexGrow: 1,
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
    alignSelf: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.xl,
    maxWidth: 1120,
    width: "100%"
  },
  loginCard: {
    flexBasis: 360,
    flexGrow: 1
  },
  searchGroup: {
    flexBasis: 240,
    flexGrow: 1,
    gap: spacing.xs
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
  queueItemSelected: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.accent
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
  readinessCardSelected: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.accent
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
  stepCardSelected: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.accent
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
