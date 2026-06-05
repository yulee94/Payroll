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

const heroStatusIds = ["roleMenu", "workflowStatus", "dataProtection"] as const;

const attendanceLogDefinitions: readonly (ToneDefinition & { readonly time: string })[] = [];
const travelWorkflowStageDefinitions: readonly ToneDefinition[] = [];
const adminPermissionDefinitions: readonly ToneDefinition[] = [];
const payrollIntegrationCheckDefinitions: readonly ToneDefinition[] = [];
const archiveFolderDefinitions: readonly TargetToneDefinition[] = [];
const archiveDocumentDefinitions: readonly ToneDefinition[] = [];
const aiRecommendationDefinitions: readonly TargetToneDefinition[] = [];
const aiDraftDefinitions: readonly ToneDefinition[] = [];

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

  const handleLogin = () => {
    if (!canSubmit) {
      setFeedbackKey("login.feedback.missingRequired");
      return;
    }
    setFeedbackKey("login.feedback.liveAuthUnavailable");
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
            <Label size="sm" muted>{tScreen(locale, feedbackKey)}</Label>
          </View>
        ) : null}
        <View style={styles.loginActions}>
          <ActionButton onPress={handleLogin}>{tScreen(locale, "login.actions.login")}</ActionButton>
          <ActionButton onPress={() => onSelect("home")} variant="secondary">{tScreen(locale, "login.actions.reviewEmptyShell")}</ActionButton>
        </View>
        <View style={styles.inlineNotice}>
          <Badge tone="neutral">{tScreen(locale, "login.live.badge")}</Badge>
          <Label size="sm" muted>{tScreen(locale, "login.live.summary")}</Label>
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
        {workQueue.length > 0 ? (
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
        ) : (
          <EmptyState title={t(locale, "preview.liveData.emptyTitle")} description={t(locale, "preview.liveData.noWorkQueue")} />
        )}
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
        {payrollSteps.length > 0 ? (
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
        ) : (
          <EmptyState title={t(locale, "preview.liveData.emptyTitle")} description={t(locale, "preview.liveData.noPayrollFlow")} />
        )}
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
        {events.length > 0 ? (
          <>
            <View style={styles.calendarDay}>
              <Text style={styles.calendarMonth}>{events[0]?.dateLabel ?? ""}</Text>
              <Text style={styles.calendarDate}></Text>
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
          </>
        ) : (
          <EmptyState title={t(locale, "preview.liveData.emptyTitle")} description={t(locale, "preview.liveData.noCalendar")} />
        )}
      </Card>
      <Card style={styles.homePlannerCard}>
        <SectionHeader title={tScreen(locale, "todo.title")} description={tScreen(locale, "todo.description")} />
        {todos.length > 0 ? (
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
        ) : (
          <EmptyState title={t(locale, "preview.liveData.emptyTitle")} description={t(locale, "preview.liveData.noTodos")} />
        )}
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
  const selectedLanguage = languageOptions.find((option) => option.locale === locale) ?? languageOptions[0];
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
          <View style={styles.languageSummaryPanel}>
            <Badge tone="ready">{t(locale, "settings.i18n.current.badge")}</Badge>
            <Label weight="bold">{t(locale, "settings.i18n.current.title", { language: selectedLanguage?.label ?? locale })}</Label>
            <Label size="sm" muted>{t(locale, "settings.i18n.current.description")}</Label>
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
      {cards.length > 0 ? (
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
      ) : (
        <EmptyState title={t(locale, "preview.liveData.emptyTitle")} description={t(locale, "preview.liveData.noPayrollReadiness")} />
      )}
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
      <EmptyState title={t(locale, "preview.liveData.emptyTitle")} description={t(locale, "preview.liveData.noArchive")} />
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
      <EmptyState title={t(locale, "preview.liveData.emptyTitle")} description={t(locale, "preview.liveData.noAi")} />
    </Card>
  );
}

function AdminAccountPanel({ locale }: Pick<ScreenProps, "locale">) {
  return (
    <Card>
      <SectionHeader title={tScreen(locale, "admin.title")} description={tScreen(locale, "admin.description")} />
      <EmptyState title={t(locale, "preview.liveData.emptyTitle")} description={t(locale, "preview.liveData.noAdmin")} />
    </Card>
  );
}

function TravelWorklogPanel({ locale }: Pick<ScreenProps, "locale">) {
  return (
    <Card>
      <SectionHeader title={tScreen(locale, "travel.title")} description={tScreen(locale, "travel.description")} />
      <EmptyState title={t(locale, "preview.liveData.emptyTitle")} description={t(locale, "preview.liveData.noTravel")} />
    </Card>
  );
}

function AttendancePhonePanel({ locale }: Pick<ScreenProps, "locale">) {
  return (
    <Card>
      <SectionHeader title={tScreen(locale, "attendance.title")} description={tScreen(locale, "attendance.description")} />
      <EmptyState title={t(locale, "preview.liveData.emptyTitle")} description={t(locale, "preview.liveData.noAttendance")} />
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
  languageSummaryPanel: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.md
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
