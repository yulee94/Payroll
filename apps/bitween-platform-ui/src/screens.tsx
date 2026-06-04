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
  getCalendarEvents,
  getModuleDashboards,
  getNavigationItems,
  getPayrollIntegrationRows,
  getPayrollSettingsRows,
  getPayrollSteps,
  getPlatformMetrics,
  getPreviewRows,
  getReadinessCards,
  getTodayTodos,
  getWorkQueue
} from "./data";
import { getLanguageOptions, t, type SupportedLocale } from "./i18n";
import { colors, radius, spacing, toneColor } from "./theme";
import type { CalendarEvent, ModuleRow, NavigationItem, PayrollStep, PlatformId, ReadinessCard, ReadinessTone, TodoItem, WorkQueueItem } from "./types";

type ScreenProps = {
  readonly active: NavigationItem;
  readonly locale: SupportedLocale;
  readonly onSelect: (id: PlatformId) => void;
};

type LoginScreenProps = Pick<ScreenProps, "locale" | "onSelect"> & {
  readonly onLocaleChange: (locale: SupportedLocale) => void;
};

type LocalizedScreenProps = ScreenProps & {
  readonly onLocaleChange: (locale: SupportedLocale) => void;
};

type ModuleId = Exclude<PlatformId, "home" | "payroll">;
type ToneDefinition = { readonly id: string; readonly tone: ReadinessTone };
type TargetToneDefinition = ToneDefinition & { readonly target: PlatformId };

const demoAccount = {
  companyCode: "0000",
  password: "admin",
  userId: "admin"
} as const;

const heroStatusIds = ["roleMenu", "workflowStatus", "dataProtection"] as const;

const attendanceLogDefinitions = [
  { id: "att-log-1", time: "09:02", tone: "ready" },
  { id: "att-log-2", time: "13:40", tone: "attention" },
  { id: "att-log-3", time: "--:--", tone: "neutral" }
] as const satisfies readonly (ToneDefinition & { readonly time: string })[];

const travelWorkflowStageDefinitions = [
  { id: "travel-plan", tone: "neutral" },
  { id: "travel-run", tone: "attention" },
  { id: "travel-diary", tone: "attention" },
  { id: "travel-result", tone: "neutral" },
  { id: "travel-review", tone: "ready" }
] as const satisfies readonly ToneDefinition[];

const adminPermissionDefinitions = [
  { id: "role-owner", tone: "ready" },
  { id: "role-manager", tone: "neutral" },
  { id: "role-employee", tone: "attention" }
] as const satisfies readonly ToneDefinition[];

const payrollIntegrationCheckDefinitions = [
  { id: "branch-docs", tone: "attention" },
  { id: "edi", tone: "attention" },
  { id: "mapping", tone: "neutral" },
  { id: "policy", tone: "ready" }
] as const satisfies readonly ToneDefinition[];

const archiveFolderDefinitions = [
  { id: "folder-payroll", tone: "ready", target: "payroll" },
  { id: "folder-attendance", tone: "attention", target: "attendance" },
  { id: "folder-approval", tone: "neutral", target: "workflow" },
  { id: "folder-travel", tone: "ready", target: "travel" }
] as const satisfies readonly TargetToneDefinition[];

const archiveDocumentDefinitions = [
  { id: "doc-payroll", tone: "ready" },
  { id: "doc-attendance", tone: "attention" },
  { id: "doc-travel", tone: "neutral" }
] as const satisfies readonly ToneDefinition[];

const archiveReviewDefinitions = [
  { id: "payrollOutputs", target: "payroll", tone: "ready" },
  { id: "accessReview", target: "admin", tone: "attention" },
  { id: "approvalFiles", target: "workflow", tone: "neutral" }
] as const satisfies readonly TargetToneDefinition[];

const aiRecommendationDefinitions = [
  { id: "ai-payroll-errors", tone: "ready", target: "payroll" },
  { id: "ai-approval-comment", tone: "attention", target: "workflow" },
  { id: "ai-archive-summary", tone: "neutral", target: "archive" }
] as const satisfies readonly TargetToneDefinition[];

const aiDraftDefinitions = [
  { id: "draft-summary", tone: "ready" },
  { id: "draft-question", tone: "attention" },
  { id: "draft-comment", tone: "neutral" }
] as const satisfies readonly ToneDefinition[];

const tScreen = (locale: SupportedLocale, key: string, params?: Readonly<Record<string, string | number>>) =>
  t(locale, `screens.${key}`, params);

function isModuleId(id: PlatformId): id is ModuleId {
  return id !== "home" && id !== "payroll";
}

export function LoginScreen({ locale, onLocaleChange, onSelect }: LoginScreenProps) {
  const [companyCode, setCompanyCode] = useState("");
  const [feedbackKey, setFeedbackKey] = useState<string | undefined>();
  const [password, setPassword] = useState("");
  const [userId, setUserId] = useState("");
  const canSubmit = companyCode.trim().length > 0 && userId.trim().length > 0 && password.trim().length > 0;
  const languageOptions = useMemo(() => getLanguageOptions(locale), [locale]);
  const demoParams = demoAccount;

  const handleLogin = () => {
    if (!canSubmit) {
      setFeedbackKey("login.feedback.missingDemo");
      return;
    }
    if (
      companyCode.trim() !== demoAccount.companyCode ||
      userId.trim() !== demoAccount.userId ||
      password.trim() !== demoAccount.password
    ) {
      setFeedbackKey("login.feedback.invalidDemo");
      return;
    }
    setFeedbackKey(undefined);
    onSelect("home");
  };

  const handleDemoLogin = () => {
    setCompanyCode(demoAccount.companyCode);
    setUserId(demoAccount.userId);
    setPassword(demoAccount.password);
    setFeedbackKey(undefined);
    onSelect("home");
  };

  return (
    <View style={styles.loginLayout}>
      <View style={styles.loginHero}>
        <Badge tone="ready">{tScreen(locale, "login.hero.badge")}</Badge>
        <View style={styles.loginHeroCopy}>
          <Text style={styles.heroBrand}>Bitween</Text>
          <Text style={styles.heroTitle}>{tScreen(locale, "login.hero.title")}</Text>
          <Text style={styles.heroCopy}>{tScreen(locale, "login.hero.copy")}</Text>
        </View>
        <View style={styles.heroStatusGrid}>
          {heroStatusIds.map((item) => (
            <View key={item} style={styles.heroStatus}>
              <Text style={styles.heroStatusText}>{tScreen(locale, `login.hero.status.${item}`)}</Text>
            </View>
          ))}
        </View>
      </View>
      <Card style={styles.loginCard}>
        <SectionHeader
          eyebrow={tScreen(locale, "login.form.eyebrow")}
          title={tScreen(locale, "login.form.title")}
          description={tScreen(locale, "login.form.description")}
        />
        <View style={styles.languageGrid}>
          {languageOptions.map((option) => {
            const selected = option.locale === locale;
            return (
              <Pressable
                accessibilityRole="button"
                key={option.locale}
                onPress={() => onLocaleChange(option.locale)}
                style={({ pressed }) => [styles.languageOption, selected && styles.languageOptionSelected, pressed && styles.buttonPressed]}
              >
                <Label weight="bold">{option.label}</Label>
                <Label size="sm" muted>{t(locale, selected ? "settings.i18n.status.selected" : "settings.i18n.status.available")}</Label>
              </Pressable>
            );
          })}
        </View>
        <View style={styles.formGroup}>
          <Label size="sm" weight="bold">{tScreen(locale, "login.form.companyCode")}</Label>
          <TextInput
            autoCapitalize="characters"
            autoComplete="organization"
            onChangeText={setCompanyCode}
            placeholder={demoAccount.companyCode}
            placeholderTextColor={colors.muted}
            returnKeyType="next"
            style={styles.input}
            value={companyCode}
          />
        </View>
        <View style={styles.formGroup}>
          <Label size="sm" weight="bold">{tScreen(locale, "login.form.userId")}</Label>
          <TextInput
            autoCapitalize="none"
            autoComplete="username"
            onChangeText={setUserId}
            placeholder={demoAccount.userId}
            placeholderTextColor={colors.muted}
            returnKeyType="next"
            style={styles.input}
            value={userId}
          />
        </View>
        <View style={styles.formGroup}>
          <Label size="sm" weight="bold">{tScreen(locale, "login.form.password")}</Label>
          <TextInput
            autoComplete="password"
            onChangeText={setPassword}
            placeholder={demoAccount.password}
            placeholderTextColor={colors.muted}
            returnKeyType="done"
            secureTextEntry
            style={styles.input}
            value={password}
          />
        </View>
        {feedbackKey ? (
          <View style={styles.inlineNotice}>
            <Badge tone="attention">{tScreen(locale, "login.feedback.badge")}</Badge>
            <Label size="sm" muted>{tScreen(locale, feedbackKey, demoParams)}</Label>
          </View>
        ) : null}
        <View style={styles.loginActions}>
          <ActionButton onPress={handleLogin}>{tScreen(locale, canSubmit ? "login.actions.enterHome" : "login.actions.login")}</ActionButton>
          <ActionButton onPress={handleDemoLogin} variant="secondary">{tScreen(locale, "login.actions.demo")}</ActionButton>
        </View>
        <View style={styles.inlineNotice}>
          <Badge tone="neutral">{tScreen(locale, "login.demo.badge")}</Badge>
          <Label size="sm" muted>{tScreen(locale, "login.demo.summary", demoParams)}</Label>
        </View>
      </Card>
    </View>
  );
}

export function LauncherScreen({ locale, onSelect }: ScreenProps) {
  const navigationItems = useMemo(() => getNavigationItems(locale), [locale]);
  const platformMetrics = useMemo(() => getPlatformMetrics(locale), [locale]);
  const workQueue = useMemo(() => getWorkQueue(locale), [locale]);
  const calendarEvents = useMemo(() => getCalendarEvents(locale), [locale]);
  const todayTodos = useMemo(() => getTodayTodos(locale), [locale]);
  const payrollSettingsRows = useMemo(() => getPayrollSettingsRows(locale), [locale]);
  const previewRows = useMemo(() => getPreviewRows(locale), [locale]);
  const launcherItems = useMemo(() => navigationItems.filter((item) => item.id !== "home"), [navigationItems]);
  const [selectedQueueId, setSelectedQueueId] = useState<string | undefined>(workQueue[0]?.id);
  const selectedQueue = workQueue.find((item) => item.id === selectedQueueId) ?? workQueue[0];

  useEffect(() => {
    setSelectedQueueId(workQueue[0]?.id);
  }, [workQueue]);

  return (
    <View style={styles.stack}>
      <Card>
        <SectionHeader
          title={tScreen(locale, "launcher.platformStatus.title")}
          description={tScreen(locale, "launcher.platformStatus.description")}
          action={<ActionButton onPress={() => onSelect("payroll")} variant="secondary">{tScreen(locale, "launcher.platformStatus.action")}</ActionButton>}
        />
        <MetricGrid items={platformMetrics} />
      </Card>

      <CalendarTodoPanel events={calendarEvents} locale={locale} todos={todayTodos} />

      <Card>
        <SectionHeader title={tScreen(locale, "launcher.workQueue.title")} description={tScreen(locale, "launcher.workQueue.description")} />
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
              <Label size="sm" muted>{tScreen(locale, "launcher.workQueue.metaOwner", { meta: item.meta, owner: item.owner })}</Label>
            </Pressable>
          ))}
        </View>
        {selectedQueue ? <WorkQueueDetailPanel item={selectedQueue} locale={locale} onSelect={onSelect} /> : null}
      </Card>

      <Card>
        <SectionHeader title={tScreen(locale, "launcher.shortcuts.title")} description={tScreen(locale, "launcher.shortcuts.description")} />
        <View style={styles.launcherGrid}>
          {launcherItems.map((item) => (
            <View key={item.id} style={[styles.launcherCard, { borderTopColor: item.accent }]}>
              <Label size="sm" muted>{item.eyebrow}</Label>
              <Label weight="bold">{item.label}</Label>
              <Label size="sm" muted>{item.description}</Label>
              <ActionButton onPress={() => onSelect(item.id)} variant="ghost">{tScreen(locale, "actions.open")}</ActionButton>
            </View>
          ))}
        </View>
      </Card>
      <Card>
        <SectionHeader
          eyebrow={tScreen(locale, "launcher.settingsSummary.eyebrow")}
          title={tScreen(locale, "launcher.settingsSummary.title")}
          description={tScreen(locale, "launcher.settingsSummary.description")}
          action={<ActionButton onPress={() => onSelect("settings")} variant="secondary">{tScreen(locale, "launcher.settingsSummary.action")}</ActionButton>}
        />
        <DataTable locale={locale} rows={payrollSettingsRows} />
      </Card>
      <Card>
        <SectionHeader
          eyebrow={tScreen(locale, "launcher.previewArchive.eyebrow")}
          title={tScreen(locale, "launcher.previewArchive.title")}
          description={tScreen(locale, "launcher.previewArchive.description")}
          action={<ActionButton onPress={() => onSelect("archive")} variant="secondary">{tScreen(locale, "launcher.previewArchive.action")}</ActionButton>}
        />
        <DataTable locale={locale} rows={previewRows} />
      </Card>
    </View>
  );
}

export function PayrollScreen({ locale, onSelect }: ScreenProps) {
  const readinessCards = useMemo(() => getReadinessCards(locale), [locale]);
  const payrollSteps = useMemo(() => getPayrollSteps(locale), [locale]);
  const [selectedReadinessId, setSelectedReadinessId] = useState<string | undefined>(readinessCards[0]?.id);
  const [selectedStepId, setSelectedStepId] = useState<string | undefined>(payrollSteps[0]?.id);
  const selectedReadiness = readinessCards.find((card) => card.id === selectedReadinessId) ?? readinessCards[0];
  const selectedStep = payrollSteps.find((step) => step.id === selectedStepId) ?? payrollSteps[0];

  useEffect(() => {
    setSelectedReadinessId(readinessCards[0]?.id);
    setSelectedStepId(payrollSteps[0]?.id);
  }, [payrollSteps, readinessCards]);

  return (
    <View style={styles.stack}>
      <PayrollReadiness cards={readinessCards} locale={locale} onSelect={onSelect} selectedId={selectedReadiness?.id} onSelectCard={(card) => setSelectedReadinessId(card.id)} />
      {selectedReadiness ? <PayrollReadinessDetail card={selectedReadiness} locale={locale} /> : null}
      <PayrollIntegrationPanel locale={locale} onSelect={onSelect} />
      <Card>
        <SectionHeader
          eyebrow={tScreen(locale, "payroll.flow.eyebrow")}
          title={tScreen(locale, "payroll.flow.title")}
          description={tScreen(locale, "payroll.flow.description")}
          action={<ActionButton onPress={() => onSelect("settings")} variant="secondary">{tScreen(locale, "payroll.flow.action")}</ActionButton>}
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
        {selectedStep ? <PayrollStepDetail locale={locale} step={selectedStep} /> : null}
        <View style={styles.actionRow}>
          <ActionButton onPress={() => onSelect("payroll")}>{tScreen(locale, "payroll.actions.keepPayroll")}</ActionButton>
          <ActionButton onPress={() => onSelect("archive")} variant="secondary">{tScreen(locale, "payroll.actions.monthlyArchive")}</ActionButton>
          <ActionButton onPress={() => onSelect("ai")} variant="ghost">{tScreen(locale, "payroll.actions.prepareAiReview")}</ActionButton>
        </View>
      </Card>
    </View>
  );
}

function PayrollIntegrationPanel({ locale, onSelect }: Pick<ScreenProps, "locale" | "onSelect">) {
  const payrollIntegrationRows = useMemo(() => getPayrollIntegrationRows(locale), [locale]);

  return (
    <Card>
      <SectionHeader
        title={tScreen(locale, "payroll.integration.title")}
        description={tScreen(locale, "payroll.integration.description")}
        action={<ActionButton onPress={() => onSelect("admin")} variant="secondary">{tScreen(locale, "payroll.integration.action")}</ActionButton>}
      />
      <View style={styles.integrationGrid}>
        {payrollIntegrationCheckDefinitions.map((item) => (
          <View key={item.id} style={[styles.integrationCard, { borderTopColor: toneColor(item.tone) }]}>
            <Label size="sm" muted>{tScreen(locale, `payroll.integrationChecks.${item.id}.label`)}</Label>
            <Text style={[styles.integrationValue, { color: toneColor(item.tone) }]}>{tScreen(locale, `payroll.integrationChecks.${item.id}.value`)}</Text>
            <Label size="sm">{tScreen(locale, `payroll.integrationChecks.${item.id}.detail`)}</Label>
          </View>
        ))}
      </View>
      <DataTable locale={locale} rows={payrollIntegrationRows} />
      <View style={styles.inlineNotice}>
        <Badge tone="neutral">{tScreen(locale, "payroll.integration.notice.badge")}</Badge>
        <Label size="sm" muted>{tScreen(locale, "payroll.integration.notice.description")}</Label>
      </View>
    </Card>
  );
}

function CalendarTodoPanel({ events, locale, todos }: { readonly events: readonly CalendarEvent[]; readonly locale: SupportedLocale; readonly todos: readonly TodoItem[] }) {
  return (
    <View style={styles.homePlannerGrid}>
      <Card style={styles.homePlannerCard}>
        <SectionHeader title={tScreen(locale, "calendar.title")} description={tScreen(locale, "calendar.description")} />
        <View style={styles.calendarDay}>
          <Text style={styles.calendarMonth}>2026.06</Text>
          <Text style={styles.calendarDate}>04</Text>
          <Label size="sm" muted>{tScreen(locale, "calendar.weekday")}</Label>
        </View>
        <View style={styles.plannerList}>
          {events.map((event) => (
            <View key={event.id} style={styles.plannerItem}>
              <Badge tone={event.tone}>{event.timeLabel}</Badge>
              <View style={styles.plannerCopy}>
                <Label weight="bold">{event.title}</Label>
                <Label size="sm" muted>{event.dateLabel}</Label>
              </View>
            </View>
          ))}
        </View>
      </Card>
      <Card style={styles.homePlannerCard}>
        <SectionHeader title={tScreen(locale, "todo.title")} description={tScreen(locale, "todo.description")} />
        <View style={styles.plannerList}>
          {todos.map((todo) => (
            <View key={todo.id} style={[styles.todoItem, todo.completed && styles.todoItemDone]}>
              <Badge tone={todo.tone}>{todo.timeLabel}</Badge>
              <View style={styles.plannerCopy}>
                <Label weight="bold">{todo.title}</Label>
                <Label size="sm" muted>{todo.owner}</Label>
              </View>
            </View>
          ))}
        </View>
      </Card>
    </View>
  );
}

export function ModuleScreen({ active, locale, onLocaleChange, onSelect }: LocalizedScreenProps) {
  const moduleDashboards = useMemo(() => getModuleDashboards(locale), [locale]);

  if (!isModuleId(active.id)) {
    return (
      <Card>
        <EmptyState title={tScreen(locale, "module.unavailable.title")} description={tScreen(locale, "module.unavailable.description")} />
      </Card>
    );
  }

  const dashboard = moduleDashboards[active.id];
  const defaultFilter = dashboard.filters[0] ?? tScreen(locale, "filters.all");
  const [activeFilter, setActiveFilter] = useState<string>(defaultFilter);
  const [search, setSearch] = useState("");
  const [selectedRowId, setSelectedRowId] = useState<string | undefined>(dashboard.rows[0]?.id);
  const languageOptions = useMemo(() => getLanguageOptions(locale), [locale]);
  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return dashboard.rows.filter((row) => {
      const haystack = [row.category, row.status, row.owner, row.nextStep].join(" ").toLowerCase();
      const matchesFilter = activeFilter === defaultFilter || row.category.includes(activeFilter) || row.status.includes(activeFilter);
      const matchesSearch = normalizedSearch.length === 0 || haystack.includes(normalizedSearch);
      return matchesFilter && matchesSearch;
    });
  }, [activeFilter, dashboard.rows, defaultFilter, search]);
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
          title={dashboard.title}
          action={<ActionButton onPress={() => onSelect(dashboard.primaryAction.target)}>{dashboard.primaryAction.label}</ActionButton>}
        />
        <MetricGrid items={dashboard.metrics} />
      </Card>

      {active.id === "attendance" ? <AttendancePhonePanel locale={locale} /> : null}
      {active.id === "travel" ? <TravelWorklogPanel locale={locale} /> : null}
      {active.id === "admin" ? <AdminAccountPanel locale={locale} /> : null}
      {active.id === "archive" ? <ArchiveLibraryPanel locale={locale} onSelect={onSelect} /> : null}
      {active.id === "ai" ? <AiWorkspacePanel locale={locale} onSelect={onSelect} /> : null}

      {active.id === "settings" ? (
        <Card>
          <SectionHeader title={t(locale, "settings.i18n.title")} description={t(locale, "settings.i18n.description")} />
          <View style={styles.languageGrid}>
            {languageOptions.map((option) => {
              const selected = option.locale === locale;
              return (
                <Pressable
                  accessibilityRole="button"
                  key={option.locale}
                  onPress={() => onLocaleChange(option.locale)}
                  style={({ pressed }) => [styles.languageOption, selected && styles.languageOptionSelected, pressed && styles.buttonPressed]}
                >
                  <Label weight="bold">{option.label}</Label>
                  <Label size="sm" muted>{t(locale, selected ? "settings.i18n.status.selected" : "settings.i18n.status.available")}</Label>
                </Pressable>
              );
            })}
          </View>
          <View style={styles.inlineNotice}>
            <Badge tone="neutral">{t(locale, "settings.i18n.catalogRule.title")}</Badge>
            <Label size="sm" muted>{t(locale, "settings.i18n.catalogRule.description")}</Label>
          </View>
        </Card>
      ) : null}

      <Card>
        <SectionHeader
          title={tScreen(locale, "module.list.title")}
          description={tScreen(locale, "module.list.description")}
          action={<ActionButton onPress={() => onSelect(dashboard.secondaryAction.target)} variant="secondary">{dashboard.secondaryAction.label}</ActionButton>}
        />
        <View style={styles.listToolbar}>
          <FilterBar active={activeFilter} filters={dashboard.filters} onSelect={setActiveFilter} />
          <View style={styles.searchGroup}>
            <Label size="sm" weight="bold">{tScreen(locale, "module.search.label")}</Label>
            <TextInput
              autoCapitalize="none"
              onChangeText={setSearch}
              placeholder={tScreen(locale, "module.search.placeholder")}
              placeholderTextColor={colors.muted}
              returnKeyType="search"
              style={styles.input}
              value={search}
            />
          </View>
        </View>
        <View style={styles.listSummary}>
          <Label weight="bold">{tScreen(locale, "module.list.count", { count: filteredRows.length })}</Label>
          <Label size="sm" muted>{search ? tScreen(locale, "module.list.filteredWithSearch", { filter: activeFilter, search }) : tScreen(locale, "module.list.filtered", { filter: activeFilter })}</Label>
        </View>
        {dashboard.rows.length > 0 ? (
          <DataTable locale={locale} onRowPress={selectRow} rows={filteredRows} selectedRowId={selectedRow?.id} />
        ) : (
          <EmptyState title={dashboard.emptyTitle} description={dashboard.emptyDescription} />
        )}
        {selectedRow ? <WorkDetailPanel locale={locale} row={selectedRow} onSelect={onSelect} /> : null}
      </Card>

      <View style={styles.actionPanels}>
        {[dashboard.primaryAction, dashboard.secondaryAction].map((action) => (
          <Card key={action.label} compact style={styles.actionPanelCard}>
            <Label weight="bold">{action.label}</Label>
            <Label size="sm" muted>{action.description}</Label>
            <ActionButton onPress={() => onSelect(action.target)} variant="ghost">{tScreen(locale, "actions.move")}</ActionButton>
          </Card>
        ))}
      </View>
    </View>
  );
}

type PayrollReadinessProps = Pick<ScreenProps, "locale" | "onSelect"> & {
  readonly cards: readonly ReadinessCard[];
  readonly onSelectCard: (card: ReadinessCard) => void;
  readonly selectedId?: string;
};

function PayrollReadiness({ cards, locale, onSelect, onSelectCard, selectedId }: PayrollReadinessProps) {
  return (
    <Card>
      <SectionHeader
        eyebrow={tScreen(locale, "payroll.readiness.eyebrow")}
        title={tScreen(locale, "payroll.readiness.title")}
        description={tScreen(locale, "payroll.readiness.description")}
        action={<ActionButton onPress={() => onSelect("settings")} variant="secondary">{tScreen(locale, "payroll.readiness.action")}</ActionButton>}
      />
      <View style={styles.readinessGrid}>
        {cards.map((card) => (
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

function PayrollReadinessDetail({ card, locale }: { readonly card: ReadinessCard; readonly locale: SupportedLocale }) {
  return (
    <View style={styles.detailPanel}>
      <View style={styles.detailHeader}>
        <View style={styles.detailTitle}>
          <Label size="sm" muted>{tScreen(locale, "payroll.readinessDetail.label")}</Label>
          <Label weight="bold">{card.title}</Label>
        </View>
        <Badge tone={card.tone}>{card.value}</Badge>
      </View>
      <Label>{card.detail}</Label>
      <View style={styles.actionRow}>
        <ActionButton onPress={() => undefined} variant="secondary">{tScreen(locale, "payroll.readinessDetail.actions.status")}</ActionButton>
        <ActionButton onPress={() => undefined} variant="ghost">{tScreen(locale, "payroll.readinessDetail.actions.materials")}</ActionButton>
      </View>
    </View>
  );
}

function PayrollStepDetail({ locale, step }: { readonly locale: SupportedLocale; readonly step: PayrollStep }) {
  return (
    <View style={styles.detailPanel}>
      <View style={styles.detailHeader}>
        <View style={styles.detailTitle}>
          <Label size="sm" muted>{tScreen(locale, "payroll.stepDetail.label")}</Label>
          <Label weight="bold">{step.title}</Label>
        </View>
        <Badge tone={step.tone}>{step.status}</Badge>
      </View>
      <Label>{step.detail}</Label>
      <View style={styles.actionRow}>
        <ActionButton onPress={() => undefined} variant="secondary">{tScreen(locale, "payroll.stepDetail.actions.work")}</ActionButton>
        <ActionButton onPress={() => undefined} variant="ghost">{tScreen(locale, "payroll.stepDetail.actions.help")}</ActionButton>
      </View>
    </View>
  );
}

function ArchiveLibraryPanel({ locale, onSelect }: Pick<ScreenProps, "locale" | "onSelect">) {
  return (
    <Card>
      <SectionHeader
        title={tScreen(locale, "archive.title")}
        description={tScreen(locale, "archive.description")}
        action={<ActionButton onPress={() => onSelect("payroll")} variant="secondary">{tScreen(locale, "archive.action")}</ActionButton>}
      />
      <View style={styles.archiveFolderGrid}>
        {archiveFolderDefinitions.map((folder) => (
          <Pressable
            accessibilityRole="button"
            key={folder.id}
            onPress={() => onSelect(folder.target)}
            style={({ pressed }) => [styles.archiveFolderCard, { borderTopColor: toneColor(folder.tone) }, pressed && styles.buttonPressed]}
          >
            <Badge tone={folder.tone}>{tScreen(locale, `archive.folders.${folder.id}.count`)}</Badge>
            <Label weight="bold">{tScreen(locale, `archive.folders.${folder.id}.label`)}</Label>
            <Label size="sm" muted>{tScreen(locale, `archive.folders.${folder.id}.owner`)}</Label>
          </Pressable>
        ))}
      </View>
      <View style={styles.archiveReviewPanel}>
        <SectionHeader title={tScreen(locale, "archive.review.title")} description={tScreen(locale, "archive.review.description")} />
        <View style={styles.archiveReviewGrid}>
          {archiveReviewDefinitions.map((item) => (
            <Pressable
              accessibilityRole="button"
              key={item.id}
              onPress={() => onSelect(item.target)}
              style={({ pressed }) => [styles.archiveReviewCard, { borderTopColor: toneColor(item.tone) }, pressed && styles.buttonPressed]}
            >
              <View style={styles.archiveReviewHead}>
                <Label size="sm" muted>{tScreen(locale, `archive.review.cards.${item.id}.label`)}</Label>
                <Badge tone={item.tone}>{tScreen(locale, `archive.review.cards.${item.id}.status`)}</Badge>
              </View>
              <Label weight="bold">{tScreen(locale, `archive.review.cards.${item.id}.title`)}</Label>
              <Label size="sm" muted>{tScreen(locale, `archive.review.cards.${item.id}.detail`)}</Label>
            </Pressable>
          ))}
        </View>
      </View>
      <View style={styles.archivePreviewGrid}>
        <View style={styles.archiveDocumentList}>
          {archiveDocumentDefinitions.map((document) => (
            <View key={document.id} style={styles.archiveDocumentItem}>
              <Badge tone={document.tone}>{tScreen(locale, `archive.documents.${document.id}.status`)}</Badge>
              <View style={styles.plannerCopy}>
                <Label weight="bold">{tScreen(locale, `archive.documents.${document.id}.title`)}</Label>
                <Label size="sm" muted>{tScreen(locale, "archive.documents.meta", {
                  type: tScreen(locale, `archive.documents.${document.id}.type`),
                  owner: tScreen(locale, `archive.documents.${document.id}.owner`)
                })}</Label>
              </View>
            </View>
          ))}
        </View>
        <View style={styles.archivePreviewPane}>
          <Label size="sm" muted>{tScreen(locale, "archive.preview.label")}</Label>
          <Label weight="bold">{tScreen(locale, "archive.preview.title")}</Label>
          <View style={styles.archiveMetaGrid}>
            <View style={styles.archiveMetaItem}>
              <Label size="sm" muted>{tScreen(locale, "archive.preview.securityScope.label")}</Label>
              <Label weight="bold">{tScreen(locale, "archive.preview.securityScope.value")}</Label>
            </View>
            <View style={styles.archiveMetaItem}>
              <Label size="sm" muted>{tScreen(locale, "archive.preview.status.label")}</Label>
              <Label weight="bold">{tScreen(locale, "archive.preview.status.value")}</Label>
            </View>
          </View>
          <View style={styles.actionRow}>
            <ActionButton onPress={() => onSelect("payroll")} variant="secondary">{tScreen(locale, "archive.preview.actions.payroll")}</ActionButton>
            <ActionButton onPress={() => onSelect("admin")} variant="ghost">{tScreen(locale, "archive.preview.actions.permissions")}</ActionButton>
          </View>
        </View>
      </View>
    </Card>
  );
}

function AiWorkspacePanel({ locale, onSelect }: Pick<ScreenProps, "locale" | "onSelect">) {
  return (
    <Card>
      <SectionHeader
        title={tScreen(locale, "ai.title")}
        description={tScreen(locale, "ai.description")}
        action={<ActionButton onPress={() => onSelect("settings")} variant="secondary">{tScreen(locale, "ai.action")}</ActionButton>}
      />
      <View style={styles.aiWorkspaceGrid}>
        <View style={styles.aiRecommendationList}>
          {aiRecommendationDefinitions.map((item) => (
            <Pressable
              accessibilityRole="button"
              key={item.id}
              onPress={() => onSelect(item.target)}
              style={({ pressed }) => [styles.aiRecommendationItem, { borderLeftColor: toneColor(item.tone) }, pressed && styles.buttonPressed]}
            >
              <Badge tone={item.tone}>{tScreen(locale, `ai.recommendations.${item.id}.status`)}</Badge>
              <View style={styles.plannerCopy}>
                <Label weight="bold">{tScreen(locale, `ai.recommendations.${item.id}.title`)}</Label>
                <Label size="sm" muted>{tScreen(locale, `ai.recommendations.${item.id}.source`)}</Label>
              </View>
            </Pressable>
          ))}
        </View>
        <View style={styles.aiPreviewPane}>
          <Label size="sm" muted>{tScreen(locale, "ai.preview.label")}</Label>
          <Label weight="bold">{tScreen(locale, "ai.preview.title")}</Label>
          <View style={styles.aiDraftGrid}>
            {aiDraftDefinitions.map((card) => (
              <View key={card.id} style={[styles.aiDraftCard, { borderTopColor: toneColor(card.tone) }]}>
                <Badge tone={card.tone}>{tScreen(locale, `ai.drafts.${card.id}.label`)}</Badge>
                <Label weight="bold">{tScreen(locale, `ai.drafts.${card.id}.title`)}</Label>
                <Label size="sm" muted>{tScreen(locale, `ai.drafts.${card.id}.detail`)}</Label>
              </View>
            ))}
          </View>
          <View style={styles.actionRow}>
            <ActionButton onPress={() => onSelect("payroll")} variant="secondary">{tScreen(locale, "ai.preview.actions.payroll")}</ActionButton>
            <ActionButton onPress={() => onSelect("archive")} variant="ghost">{tScreen(locale, "ai.preview.actions.archive")}</ActionButton>
          </View>
        </View>
      </View>
    </Card>
  );
}

function AdminAccountPanel({ locale }: Pick<ScreenProps, "locale">) {
  return (
    <Card>
      <SectionHeader title={tScreen(locale, "admin.title")} description={tScreen(locale, "admin.description")} />
      <View style={styles.adminBranchGrid}>
        <View style={styles.adminBranchCard}>
          <Label size="sm" muted>{tScreen(locale, "admin.branchAccount.label")}</Label>
          <Label weight="bold">{tScreen(locale, "admin.branchAccount.value")}</Label>
          <Label size="sm" muted>{tScreen(locale, "admin.branchAccount.detail")}</Label>
        </View>
        <View style={styles.adminBranchCard}>
          <Label size="sm" muted>{tScreen(locale, "admin.subaccount.label")}</Label>
          <Label weight="bold">{tScreen(locale, "admin.subaccount.value")}</Label>
          <Label size="sm" muted>{tScreen(locale, "admin.subaccount.detail")}</Label>
        </View>
      </View>
      <View style={styles.permissionMatrix}>
        {adminPermissionDefinitions.map((row) => (
          <View key={row.id} style={styles.permissionRow}>
            <View style={styles.permissionRole}>
              <Badge tone={row.tone}>{tScreen(locale, `admin.permissions.${row.id}.role`)}</Badge>
            </View>
            <View style={styles.permissionCell}>
              <Label size="sm" muted>{tScreen(locale, "admin.permissions.columns.payroll")}</Label>
              <Label weight="bold">{tScreen(locale, `admin.permissions.${row.id}.payroll`)}</Label>
            </View>
            <View style={styles.permissionCell}>
              <Label size="sm" muted>{tScreen(locale, "admin.permissions.columns.executive")}</Label>
              <Label weight="bold">{tScreen(locale, `admin.permissions.${row.id}.executive`)}</Label>
            </View>
            <View style={styles.permissionCell}>
              <Label size="sm" muted>{tScreen(locale, "admin.permissions.columns.archive")}</Label>
              <Label weight="bold">{tScreen(locale, `admin.permissions.${row.id}.archive`)}</Label>
            </View>
          </View>
        ))}
      </View>
    </Card>
  );
}

function TravelWorklogPanel({ locale }: Pick<ScreenProps, "locale">) {
  return (
    <Card>
      <SectionHeader title={tScreen(locale, "travel.title")} description={tScreen(locale, "travel.description")} />
      <View style={styles.travelStageGrid}>
        {travelWorkflowStageDefinitions.map((stage, index) => (
          <View key={stage.id} style={[styles.travelStageCard, { borderTopColor: toneColor(stage.tone) }]}>
            <Text style={styles.travelStageStep}>{String(index + 1).padStart(2, "0")}</Text>
            <Badge tone={stage.tone}>{tScreen(locale, `travel.stages.${stage.id}.status`)}</Badge>
            <Label weight="bold">{tScreen(locale, `travel.stages.${stage.id}.label`)}</Label>
            <Label size="sm" muted>{tScreen(locale, `travel.stages.${stage.id}.detail`)}</Label>
          </View>
        ))}
      </View>
      <View style={styles.travelReviewGrid}>
        <View style={styles.travelReviewCard}>
          <Label size="sm" muted>{tScreen(locale, "travel.review.ongoing.label")}</Label>
          <Label weight="bold">{tScreen(locale, "travel.review.ongoing.value")}</Label>
          <Label size="sm" muted>{tScreen(locale, "travel.review.ongoing.detail")}</Label>
        </View>
        <View style={styles.travelReviewCard}>
          <Label size="sm" muted>{tScreen(locale, "travel.review.completed.label")}</Label>
          <Label weight="bold">{tScreen(locale, "travel.review.completed.value")}</Label>
          <Label size="sm" muted>{tScreen(locale, "travel.review.completed.detail")}</Label>
        </View>
      </View>
    </Card>
  );
}

function AttendancePhonePanel({ locale }: Pick<ScreenProps, "locale">) {
  return (
    <Card>
      <SectionHeader title={tScreen(locale, "attendance.title")} description={tScreen(locale, "attendance.description")} />
      <View style={styles.attendanceGrid}>
        <View style={styles.phoneFrame}>
          <View style={styles.phoneHeader}>
            <Label size="sm" muted>{tScreen(locale, "attendance.phone.todayStatus")}</Label>
            <Badge tone="ready">{tScreen(locale, "attendance.phone.checkedIn")}</Badge>
          </View>
          <View style={styles.phoneClock}>
            <Text style={styles.phoneTime}>09:02</Text>
            <Label size="sm" muted>{tScreen(locale, "attendance.phone.location")}</Label>
          </View>
          <View style={styles.punchActions}>
            <Pressable accessibilityRole="button" style={({ pressed }) => [styles.punchButton, pressed && styles.buttonPressed]}>
              <Text style={styles.punchButtonText}>{tScreen(locale, "attendance.phone.checkIn")}</Text>
            </Pressable>
            <Pressable accessibilityRole="button" style={({ pressed }) => [styles.punchButtonSecondary, pressed && styles.buttonPressed]}>
              <Text style={styles.punchButtonSecondaryText}>{tScreen(locale, "attendance.phone.checkOut")}</Text>
            </Pressable>
          </View>
          <View style={styles.locationNotice}>
            <Label size="sm" weight="bold">{tScreen(locale, "attendance.locationNotice.title")}</Label>
            <Label size="sm" muted>{tScreen(locale, "attendance.locationNotice.description")}</Label>
          </View>
        </View>
        <View style={styles.attendanceSide}>
          <View style={styles.attendanceSummaryCard}>
            <Label size="sm" muted>{tScreen(locale, "attendance.manager.label")}</Label>
            <Label weight="bold">{tScreen(locale, "attendance.manager.value")}</Label>
            <Label size="sm" muted>{tScreen(locale, "attendance.manager.detail")}</Label>
          </View>
          <View style={styles.attendanceLogList}>
            {attendanceLogDefinitions.map((log) => (
              <View key={log.id} style={styles.attendanceLogItem}>
                <Badge tone={log.tone}>{tScreen(locale, `attendance.logs.${log.id}.label`)}</Badge>
                <View style={styles.plannerCopy}>
                  <Label weight="bold">{log.time}</Label>
                  <Label size="sm" muted>{tScreen(locale, `attendance.logs.${log.id}.place`)}</Label>
                </View>
              </View>
            ))}
          </View>
        </View>
      </View>
    </Card>
  );
}

function WorkDetailPanel({ locale, row, onSelect }: { readonly locale: SupportedLocale; readonly row: ModuleRow; readonly onSelect: (id: PlatformId) => void }) {
  return (
    <View style={styles.detailPanel}>
      <View style={styles.detailHeader}>
        <View style={styles.detailTitle}>
          <Label size="sm" muted>{tScreen(locale, "workDetail.selectedLabel")}</Label>
          <Label weight="bold">{row.category}</Label>
        </View>
        <Badge tone={row.tone}>{row.status}</Badge>
      </View>
      <View style={styles.detailGrid}>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workDetail.owner")}</Label>
          <Label weight="bold">{row.owner}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workDetail.nextStep")}</Label>
          <Label>{row.nextStep}</Label>
        </View>
      </View>
      <View style={styles.actionRow}>
        <ActionButton onPress={() => onSelect(row.target)} variant="secondary">{tScreen(locale, "workDetail.actions.openRelated")}</ActionButton>
        <ActionButton onPress={() => undefined} variant="ghost">{tScreen(locale, "workDetail.actions.confirmOwner")}</ActionButton>
      </View>
    </View>
  );
}

function WorkQueueDetailPanel({ item, locale, onSelect }: { readonly item: WorkQueueItem; readonly locale: SupportedLocale; readonly onSelect: (id: PlatformId) => void }) {
  return (
    <View style={styles.detailPanel}>
      <View style={styles.detailHeader}>
        <View style={styles.detailTitle}>
          <Label size="sm" muted>{tScreen(locale, "workQueueDetail.selectedLabel")}</Label>
          <Label weight="bold">{item.title}</Label>
        </View>
        <Badge tone={item.tone}>{item.status}</Badge>
      </View>
      <View style={styles.detailGrid}>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workQueueDetail.owner")}</Label>
          <Label weight="bold">{item.owner}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workQueueDetail.due")}</Label>
          <Label weight="bold">{item.due}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workQueueDetail.area")}</Label>
          <Label>{item.meta}</Label>
        </View>
      </View>
      <View style={styles.actionRow}>
        <ActionButton onPress={() => onSelect(item.target)} variant="secondary">{tScreen(locale, "workQueueDetail.actions.openRelated")}</ActionButton>
        <ActionButton onPress={() => undefined} variant="ghost">{tScreen(locale, "workQueueDetail.actions.confirmFlow")}</ActionButton>
      </View>
    </View>
  );
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
  aiDraftCard: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderTopWidth: 4,
    borderWidth: 1,
    flexBasis: 180,
    flexGrow: 1,
    gap: spacing.sm,
    padding: spacing.md
  },
  aiDraftGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  aiPreviewPane: {
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexBasis: 340,
    flexGrow: 1,
    gap: spacing.md,
    padding: spacing.md
  },
  aiRecommendationItem: {
    alignItems: "flex-start",
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderLeftWidth: 4,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.md
  },
  aiRecommendationList: {
    flexBasis: 300,
    flexGrow: 1,
    gap: spacing.sm
  },
  aiWorkspaceGrid: {
    alignItems: "stretch",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.lg
  },
  archiveDocumentItem: {
    alignItems: "flex-start",
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.md
  },
  archiveDocumentList: {
    flexBasis: 300,
    flexGrow: 1,
    gap: spacing.sm
  },
  archiveFolderCard: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderTopWidth: 4,
    borderWidth: 1,
    flexBasis: 190,
    flexGrow: 1,
    gap: spacing.sm,
    padding: spacing.md
  },
  archiveFolderGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  archiveMetaGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm
  },
  archiveMetaItem: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexBasis: 160,
    flexGrow: 1,
    gap: spacing.xs,
    padding: spacing.md
  },
  archivePreviewGrid: {
    alignItems: "stretch",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.lg
  },
  archivePreviewPane: {
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexBasis: 320,
    flexGrow: 1,
    gap: spacing.md,
    padding: spacing.md
  },
  archiveReviewCard: {
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
  archiveReviewGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  archiveReviewHead: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    justifyContent: "space-between"
  },
  archiveReviewPanel: {
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.md
  },
  adminBranchCard: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexBasis: 260,
    flexGrow: 1,
    gap: spacing.xs,
    padding: spacing.md
  },
  adminBranchGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  attendanceGrid: {
    alignItems: "stretch",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.lg
  },
  attendanceLogItem: {
    alignItems: "flex-start",
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.md
  },
  attendanceLogList: {
    gap: spacing.sm
  },
  attendanceSide: {
    flexBasis: 280,
    flexGrow: 1,
    gap: spacing.md
  },
  attendanceSummaryCard: {
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.xs,
    padding: spacing.md
  },
  buttonPressed: {
    opacity: 0.86
  },
  calendarDate: {
    color: colors.accent,
    fontSize: 34,
    fontWeight: "800",
    lineHeight: 40
  },
  calendarDay: {
    alignItems: "center",
    backgroundColor: colors.accentSoft,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.xs,
    padding: spacing.lg
  },
  calendarMonth: {
    color: colors.muted,
    fontSize: 13,
    fontWeight: "800",
    lineHeight: 18
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
  integrationCard: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderTopWidth: 4,
    borderWidth: 1,
    flexBasis: 210,
    flexGrow: 1,
    gap: spacing.xs,
    padding: spacing.md
  },
  integrationGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  integrationValue: {
    fontSize: 20,
    fontWeight: "800",
    lineHeight: 26
  },
  homePlannerCard: {
    flexBasis: 320,
    flexGrow: 1
  },
  homePlannerGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.lg
  },
  languageGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  languageOption: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexBasis: 160,
    flexGrow: 1,
    gap: spacing.xs,
    padding: spacing.md
  },
  languageOptionSelected: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.accent
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
  plannerCopy: {
    flex: 1,
    gap: spacing.xs,
    minWidth: 0
  },
  plannerItem: {
    alignItems: "flex-start",
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.md
  },
  plannerList: {
    gap: spacing.sm
  },
  locationNotice: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.xs,
    padding: spacing.md
  },
  phoneClock: {
    alignItems: "center",
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.xs,
    padding: spacing.lg
  },
  phoneFrame: {
    backgroundColor: colors.card,
    borderColor: colors.text,
    borderRadius: 24,
    borderWidth: 2,
    flexBasis: 280,
    flexGrow: 1,
    gap: spacing.md,
    maxWidth: 360,
    padding: spacing.lg
  },
  phoneHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    justifyContent: "space-between"
  },
  phoneTime: {
    color: colors.accent,
    fontSize: 36,
    fontWeight: "800",
    lineHeight: 44
  },
  permissionCell: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexBasis: 150,
    flexGrow: 1,
    gap: spacing.xs,
    padding: spacing.md
  },
  permissionMatrix: {
    gap: spacing.sm
  },
  permissionRole: {
    flexBasis: 150,
    flexGrow: 1
  },
  permissionRow: {
    alignItems: "stretch",
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    padding: spacing.sm
  },
  punchActions: {
    flexDirection: "row",
    gap: spacing.sm
  },
  punchButton: {
    alignItems: "center",
    backgroundColor: colors.accent,
    borderRadius: radius.lg,
    flex: 1,
    justifyContent: "center",
    minHeight: 52,
    padding: spacing.md
  },
  punchButtonSecondary: {
    alignItems: "center",
    backgroundColor: colors.accentSoft,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flex: 1,
    justifyContent: "center",
    minHeight: 52,
    padding: spacing.md
  },
  punchButtonSecondaryText: {
    color: colors.accent,
    fontSize: 16,
    fontWeight: "800"
  },
  punchButtonText: {
    color: colors.card,
    fontSize: 16,
    fontWeight: "800"
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
  },
  todoItem: {
    alignItems: "flex-start",
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.md
  },
  todoItemDone: {
    backgroundColor: colors.input,
    opacity: 0.5
  },
  travelReviewCard: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexBasis: 260,
    flexGrow: 1,
    gap: spacing.xs,
    padding: spacing.md
  },
  travelReviewGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  travelStageCard: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderTopWidth: 4,
    borderWidth: 1,
    flexBasis: 190,
    flexGrow: 1,
    gap: spacing.sm,
    padding: spacing.md
  },
  travelStageGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  travelStageStep: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: "800"
  }
});
