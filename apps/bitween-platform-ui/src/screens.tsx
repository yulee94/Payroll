import { useEffect, useMemo, useState } from "react";
import { Linking, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

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
  getPayrollIntegrationRows,
  getPayrollSettingsRows,
  getPayrollSteps,
  getPreviewRows,
  getTodayTodos,
  getWorkQueue
} from "./data";
import { getLanguageOptions, t, type SupportedLocale } from "./i18n";
import { colors, getSidebarThemes, radius, spacing, toneColor } from "./theme";
import type {
  CalendarEvent,
  ModuleRow,
  NavigationItem,
  PayrollStep,
  PlatformId,
  ReadinessTone,
  SidebarTheme,
  SidebarThemeId,
  TodoItem,
  WorkQueueItem
} from "./types";

type ScreenProps = {
  readonly active: NavigationItem;
  readonly items?: readonly NavigationItem[];
  readonly locale: SupportedLocale;
  readonly onSelect: (id: PlatformId) => void;
};

type LocalizedScreenProps = ScreenProps & {
  readonly onLocaleChange: (locale: SupportedLocale) => void;
  readonly onThemeChange: (theme: SidebarThemeId) => void;
  readonly sidebarTheme: SidebarTheme;
};

type ModuleId = Exclude<PlatformId, "home" | "payroll">;
type ToneDefinition = { readonly id: string; readonly tone: ReadinessTone };
type TargetToneDefinition = ToneDefinition & { readonly target: PlatformId };

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

const approvalSummaryDefinitions = [
  { id: "pendingApproval", target: "approval", tone: "attention" },
  { id: "returnedDraft", target: "approval", tone: "neutral" },
  { id: "attachments", target: "archive", tone: "ready" }
] as const satisfies readonly TargetToneDefinition[];

const workflowCanvasDefinitions = [
  { id: "employeeChange", target: "hr", tone: "attention" },
  { id: "payrollClose", target: "payroll", tone: "neutral" },
  { id: "approvalHandoff", target: "approval", tone: "attention" },
  { id: "recordArchive", target: "archive", tone: "ready" }
] as const satisfies readonly TargetToneDefinition[];

const recruitPlacementDefinitions = [
  { id: "applicantFit", target: "hr", tone: "attention" },
  { id: "credentialCheck", target: "archive", tone: "neutral" },
  { id: "departmentMatch", target: "admin", tone: "ready" }
] as const satisfies readonly TargetToneDefinition[];

const hrPeopleReviewDefinitions = [
  { id: "roster", target: "attendance", tone: "ready" },
  { id: "payrollImpact", target: "payroll", tone: "attention" },
  { id: "certificates", target: "archive", tone: "attention" },
  { id: "placement", target: "recruit", tone: "neutral" }
] as const satisfies readonly TargetToneDefinition[];

const adminPermissionDefinitions = [
  { id: "role-owner", tone: "ready" },
  { id: "role-manager", tone: "neutral" },
  { id: "role-employee", tone: "attention" }
] as const satisfies readonly ToneDefinition[];

const adminReviewDefinitions = [
  { id: "payrollPermission", target: "payroll", tone: "attention" },
  { id: "archiveAccess", target: "archive", tone: "neutral" },
  { id: "branchAccounts", target: "settings", tone: "ready" }
] as const satisfies readonly TargetToneDefinition[];

const payrollIntegrationCheckDefinitions = [
  { id: "branch-docs", tone: "attention" },
  { id: "edi", tone: "attention" },
  { id: "mapping", tone: "neutral" },
  { id: "policy", tone: "ready" }
] as const satisfies readonly ToneDefinition[];

const payrollWorkDefinitions = [
  { id: "hrClose", target: "hr", tone: "attention" },
  { id: "inputFiles", target: "archive", tone: "neutral" },
  { id: "deductionReview", target: "payroll", tone: "attention" },
  { id: "approvalRequest", target: "approval", tone: "neutral" }
] as const satisfies readonly TargetToneDefinition[];

const archiveFolderDefinitions = [
  { id: "folder-payroll", tone: "ready", target: "payroll" },
  { id: "folder-attendance", tone: "attention", target: "attendance" },
  { id: "folder-approval", tone: "neutral", target: "approval" },
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
  { id: "approvalFiles", target: "approval", tone: "neutral" }
] as const satisfies readonly TargetToneDefinition[];

const aiRecommendationDefinitions = [
  { id: "ai-payroll-errors", tone: "ready", target: "payroll" },
  { id: "ai-approval-comment", tone: "attention", target: "approval" },
  { id: "ai-archive-summary", tone: "neutral", target: "archive" }
] as const satisfies readonly TargetToneDefinition[];

const aiDraftDefinitions = [
  { id: "draft-summary", tone: "ready" },
  { id: "draft-question", tone: "attention" },
  { id: "draft-comment", tone: "neutral" }
] as const satisfies readonly ToneDefinition[];

const settingsPreferenceDefinitions = [
  { id: "density", target: "home", tone: "ready" },
  { id: "notice", target: "approval", tone: "neutral" },
  { id: "security", target: "admin", tone: "attention" },
  { id: "payroll", target: "payroll", tone: "attention" }
] as const satisfies readonly TargetToneDefinition[];

const maintenanceRentalIntegration = {
  repositoryUrl: "https://github.com/yulee94/maintenance_system",
  runtimeUrl: "https://github.com/yulee94/maintenance_system"
} as const;

const maintenanceRentalBridgeDefinitions = [
  { id: "source", tone: "ready" },
  { id: "brand", tone: "neutral" },
  { id: "sync", tone: "attention" }
] as const satisfies readonly ToneDefinition[];

const tScreen = (locale: SupportedLocale, key: string, params?: Readonly<Record<string, string | number>>) =>
  t(locale, `screens.${key}`, params);

const calendarDisplayParts = (locale: SupportedLocale) => {
  const date = new Date();
  return {
    date: new Intl.DateTimeFormat(locale, { day: "2-digit" }).format(date),
    month: new Intl.DateTimeFormat(locale, { month: "2-digit", year: "numeric" }).format(date),
    weekday: new Intl.DateTimeFormat(locale, { weekday: "long" }).format(date)
  };
};

function isModuleId(id: PlatformId): id is ModuleId {
  return id !== "home" && id !== "payroll";
}
export function LauncherScreen({ items, locale, onSelect }: ScreenProps) {
  const workQueue = useMemo(() => getWorkQueue(locale), [locale]);
  const calendarEvents = useMemo(() => getCalendarEvents(locale), [locale]);
  const todayTodos = useMemo(() => getTodayTodos(locale), [locale]);
  const payrollSettingsRows = useMemo(() => getPayrollSettingsRows(locale), [locale]);
  const previewRows = useMemo(() => getPreviewRows(locale), [locale]);
  const [selectedQueueId, setSelectedQueueId] = useState<string | undefined>(workQueue[0]?.id);
  const selectedQueue = workQueue.find((item) => item.id === selectedQueueId) ?? workQueue[0];
  const nextEvent = calendarEvents[0];
  const nextFollowUp = todayTodos.find((todo) => !todo.completed) ?? todayTodos[0];
  const nextPrep = payrollSettingsRows[0] ?? previewRows[0];

  useEffect(() => {
    setSelectedQueueId(workQueue[0]?.id);
  }, [workQueue]);

  return (
    <View style={styles.stack}>
      <Card>
        <SectionHeader
          title={tScreen(locale, "launcher.dayFocus.title")}
          description={tScreen(locale, "launcher.dayFocus.description")}
          action={selectedQueue ? <ActionButton onPress={() => onSelect(selectedQueue.target)} variant="secondary">{tScreen(locale, "launcher.dayFocus.action")}</ActionButton> : undefined}
        />
        <View style={styles.homeFocusGrid}>
          {selectedQueue ? (
            <Pressable
              accessibilityRole="button"
              onPress={() => onSelect(selectedQueue.target)}
              style={({ pressed }) => [styles.homeFocusCardPrimary, pressed && styles.buttonPressed]}
            >
              <View style={styles.queueHeader}>
                <Badge tone={selectedQueue.tone}>{selectedQueue.status}</Badge>
                <Label size="sm" muted>{selectedQueue.due}</Label>
              </View>
              <Label size="lg" weight="bold">{selectedQueue.title}</Label>
              <Label muted>{tScreen(locale, "launcher.workQueue.metaOwner", { meta: selectedQueue.meta, owner: selectedQueue.owner })}</Label>
            </Pressable>
          ) : null}
          <View style={styles.homeFocusSide}>
            {nextEvent ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => onSelect(nextEvent.target)}
                style={({ pressed }) => [styles.homeFocusCard, pressed && styles.buttonPressed]}
              >
                <Label size="sm" muted>{tScreen(locale, "launcher.dayFocus.nextSchedule")}</Label>
                <Label weight="bold">{nextEvent.title}</Label>
                <Label size="sm" muted>{nextEvent.dateLabel} · {nextEvent.timeLabel}</Label>
              </Pressable>
            ) : null}
            {nextFollowUp ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => onSelect(nextFollowUp.target)}
                style={({ pressed }) => [styles.homeFocusCard, pressed && styles.buttonPressed]}
              >
                <Label size="sm" muted>{tScreen(locale, "launcher.dayFocus.followUp")}</Label>
                <Label weight="bold">{nextFollowUp.title}</Label>
                <Label size="sm" muted>{nextFollowUp.owner} · {nextFollowUp.timeLabel}</Label>
              </Pressable>
            ) : null}
          </View>
        </View>
      </Card>

      <CalendarTodoPanel events={calendarEvents} locale={locale} onSelect={onSelect} todos={todayTodos} />

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
      {nextPrep ? (
        <Card>
          <SectionHeader
            title={tScreen(locale, "launcher.monthPrep.title")}
            description={tScreen(locale, "launcher.monthPrep.description")}
            action={<ActionButton onPress={() => onSelect(nextPrep.target)} variant="secondary">{tScreen(locale, "launcher.monthPrep.action")}</ActionButton>}
          />
          <View style={styles.homePrepGrid}>
            {[nextPrep, ...previewRows.slice(0, 2)].map((item) => (
              <Pressable
                accessibilityRole="button"
                key={item.id}
                onPress={() => onSelect(item.target)}
                style={({ pressed }) => [styles.homePrepCard, { borderTopColor: toneColor(item.tone) }, pressed && styles.buttonPressed]}
              >
                <Badge tone={item.tone}>{item.status}</Badge>
                <Label weight="bold">{item.category}</Label>
                <Label size="sm" muted>{item.nextStep}</Label>
              </Pressable>
            ))}
          </View>
        </Card>
      ) : null}
    </View>
  );
}

export function PayrollScreen({ locale, onSelect }: ScreenProps) {
  const payrollSteps = useMemo(() => getPayrollSteps(locale), [locale]);
  const [selectedStepId, setSelectedStepId] = useState<string | undefined>(payrollSteps[0]?.id);
  const selectedStep = payrollSteps.find((step) => step.id === selectedStepId) ?? payrollSteps[0];

  useEffect(() => {
    setSelectedStepId(payrollSteps[0]?.id);
  }, [payrollSteps]);

  return (
    <View style={styles.stack}>
      <PayrollWorkPanel locale={locale} onSelect={onSelect} />
      <PayrollIntegrationPanel locale={locale} onSelect={onSelect} />
      <Card>
        <SectionHeader
          eyebrow={tScreen(locale, "payroll.flow.eyebrow")}
          title={tScreen(locale, "payroll.flow.title")}
          description={tScreen(locale, "payroll.flow.description")}
          action={<ActionButton onPress={() => onSelect("settings")} variant="secondary">{tScreen(locale, "payroll.flow.action")}</ActionButton>}
        />
        <View style={styles.stepGrid}>
          {payrollSteps.map((step) => (
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

function CalendarTodoPanel({
  events,
  locale,
  onSelect,
  todos
}: {
  readonly events: readonly CalendarEvent[];
  readonly locale: SupportedLocale;
  readonly onSelect: (id: PlatformId) => void;
  readonly todos: readonly TodoItem[];
}) {
  const completedTodos = todos.filter((todo) => todo.completed).length;
  const totalTodos = todos.length;
  const pendingTodos = totalTodos - completedTodos;
  const completionRatio = totalTodos > 0 ? completedTodos / totalTodos : 0;
  const progressStyle = { width: `${Math.round(completionRatio * 100)}%` } as const;
  const today = useMemo(() => calendarDisplayParts(locale), [locale]);
  return (
    <View style={styles.homePlannerGrid}>
      <Card style={styles.homePlannerCard}>
        <SectionHeader title={tScreen(locale, "calendar.title")} description={tScreen(locale, "calendar.description")} />
        <View style={styles.calendarDay}>
          <Text style={styles.calendarMonth}>{today.month}</Text>
          <Text style={styles.calendarDate}>{today.date}</Text>
          <Label size="sm" muted>{today.weekday}</Label>
        </View>
        <View style={styles.plannerList}>
          {events.map((event) => (
            <Pressable
              accessibilityRole="button"
              key={event.id}
              onPress={() => onSelect(event.target)}
              style={({ pressed }) => [styles.plannerItem, pressed && styles.buttonPressed]}
            >
              <Badge tone={event.tone}>{event.timeLabel}</Badge>
              <View style={styles.plannerCopy}>
                <Label weight="bold">{event.title}</Label>
                <Label size="sm" muted>{event.dateLabel} · {tScreen(locale, "workDetail.actions.openRelated")}</Label>
              </View>
            </Pressable>
          ))}
        </View>
      </Card>
      <Card style={styles.homePlannerCard}>
        <SectionHeader title={tScreen(locale, "todo.title")} description={tScreen(locale, "todo.description")} />
        <View style={styles.todoProgressPanel}>
          <View style={styles.todoProgressHeader}>
            <Label weight="bold">{tScreen(locale, "todo.progress.title", { done: completedTodos, total: totalTodos })}</Label>
            <Label size="sm" muted>{tScreen(locale, "todo.progress.pending", { count: pendingTodos })}</Label>
          </View>
          <View style={styles.todoProgressTrack}>
            <View style={[styles.todoProgressFill, progressStyle]} />
          </View>
        </View>
        <View style={styles.plannerList}>
          {todos.map((todo) => (
            <Pressable
              accessibilityRole="button"
              key={todo.id}
              onPress={() => onSelect(todo.target)}
              style={({ pressed }) => [styles.todoItem, todo.completed && styles.todoItemDone, pressed && styles.buttonPressed]}
            >
              <Badge tone={todo.tone}>{todo.timeLabel}</Badge>
              <View style={styles.plannerCopy}>
                <Label weight="bold">{todo.title}</Label>
                <Label size="sm" muted>{todo.owner} · {tScreen(locale, "workDetail.actions.openRelated")}</Label>
              </View>
            </Pressable>
          ))}
        </View>
      </Card>
    </View>
  );
}

export function ModuleScreen({ active, locale, onLocaleChange, onSelect, onThemeChange, sidebarTheme }: LocalizedScreenProps) {
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
  const [attendancePhoneVisible, setAttendancePhoneVisible] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedRowId, setSelectedRowId] = useState<string | undefined>(dashboard.rows[0]?.id);
  const languageOptions = useMemo(() => getLanguageOptions(locale), [locale]);
  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return dashboard.rows.filter((row) => {
      const haystack = [
        row.category,
        row.status,
        row.owner,
        row.nextStep,
        row.dueWindow,
        row.blockers,
        row.permission,
        row.liveState
      ].join(" ").toLowerCase();
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
    setAttendancePhoneVisible(false);
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
  const runModuleAction = (target: PlatformId) => {
    if (active.id === "attendance" && target === "attendance") {
      setAttendancePhoneVisible(true);
      return;
    }
    onSelect(target);
  };
  const resetListFilters = () => {
    setActiveFilter(defaultFilter);
    setSearch("");
    setSelectedRowId(dashboard.rows[0]?.id);
  };

  return (
    <View style={styles.stack}>
      <Card>
        <SectionHeader
          title={dashboard.title}
          action={<ActionButton onPress={() => runModuleAction(dashboard.primaryAction.target)}>{dashboard.primaryAction.label}</ActionButton>}
        />
        <MetricGrid items={dashboard.metrics} />
      </Card>

      {active.id === "attendance" ? (
        <>
          <AttendanceAppPrompt locale={locale} onOpen={() => setAttendancePhoneVisible(true)} />
          {(attendancePhoneVisible || active.id === "attendance") ? <AttendancePhonePanel locale={locale} /> : null}
        </>
      ) : null}
      {active.id === "workflow" ? <WorkflowCanvasPanel locale={locale} onSelect={onSelect} /> : null}
      {active.id === "approval" ? <ApprovalPanel locale={locale} onSelect={onSelect} /> : null}
      {active.id === "recruit" ? <RecruitPlacementPanel locale={locale} onSelect={onSelect} /> : null}
      {active.id === "hr" ? <HrPeoplePanel locale={locale} onSelect={onSelect} /> : null}
      {active.id === "travel" ? <TravelWorklogPanel locale={locale} /> : null}
      {active.id === "maintenanceRental" ? <MaintenanceRentalBridgePanel locale={locale} /> : null}
      {active.id === "admin" ? <AdminAccountPanel locale={locale} onSelect={onSelect} /> : null}
      {active.id === "archive" ? <ArchiveLibraryPanel locale={locale} onSelect={onSelect} /> : null}
      {active.id === "ai" ? <AiWorkspacePanel locale={locale} onSelect={onSelect} /> : null}

      {active.id === "settings" ? (
        <Card>
          <SectionHeader title={t(locale, "settings.i18n.title")} description={t(locale, "settings.i18n.description")} />
          <View style={styles.settingsStatusGrid}>
            <View style={styles.settingsStatusItem}>
              <Label size="sm" muted>{t(locale, "settings.i18n.status.selected")}</Label>
              <Label weight="bold">{languageOptions.find((option) => option.locale === locale)?.label ?? locale}</Label>
            </View>
            <View style={styles.settingsStatusItem}>
              <Label size="sm" muted>{t(locale, "settings.i18n.status.available")}</Label>
              <Label weight="bold">{languageOptions.length}</Label>
            </View>
            <View style={styles.settingsStatusItem}>
              <Label size="sm" muted>{t(locale, "settings.i18n.catalogRule.title")}</Label>
              <Label size="sm">{t(locale, "settings.i18n.catalogRule.description")}</Label>
            </View>
          </View>
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
      {active.id === "settings" ? (
        <SettingsControlPanel
          locale={locale}
          onSelect={onSelect}
          onThemeChange={onThemeChange}
          sidebarTheme={sidebarTheme}
        />
      ) : null}

      <Card>
        <SectionHeader
          title={tScreen(locale, "module.list.title")}
          action={<ActionButton onPress={() => onSelect(dashboard.secondaryAction.target)} variant="secondary">{dashboard.secondaryAction.label}</ActionButton>}
        />
        <View style={styles.listToolbar}>
          <FilterBar active={activeFilter} filters={dashboard.filters} onSelect={setActiveFilter} />
          <View style={styles.searchGroup}>
            <Label size="sm" weight="bold">{tScreen(locale, "module.search.label")}</Label>
            <TextInput
              autoCapitalize="none"
              accessibilityLabel={tScreen(locale, "module.search.accessibilityLabel")}
              onChangeText={setSearch}
              returnKeyType="search"
              style={styles.input}
              value={search}
            />
            <Label size="sm" muted>{tScreen(locale, "module.search.hint")}</Label>
            {search ? (
              <ActionButton accessibilityLabel={tScreen(locale, "module.search.clearAccessibilityLabel")} onPress={() => setSearch("")} variant="ghost">
                {tScreen(locale, "module.search.clear")}
              </ActionButton>
            ) : null}
          </View>
        </View>
        <View style={styles.listSummary}>
          <View style={styles.listSummaryCount}>
            <Label weight="bold">{tScreen(locale, "module.list.count", { count: filteredRows.length })}</Label>
          </View>
          <View style={styles.listSummaryCopy}>
            <Label size="sm" muted>{search ? tScreen(locale, "module.list.filteredWithSearch", { filter: activeFilter, search }) : tScreen(locale, "module.list.filtered", { filter: activeFilter })}</Label>
          </View>
        </View>
        {dashboard.rows.length === 0 ? (
          <EmptyState title={dashboard.emptyTitle} description={dashboard.emptyDescription} />
        ) : filteredRows.length > 0 ? (
          <DataTable locale={locale} onRowPress={selectRow} rows={filteredRows} selectedRowId={selectedRow?.id} />
        ) : (
          <View style={styles.filteredEmptyState}>
            <EmptyState title={tScreen(locale, "module.filteredEmpty.title")} description={tScreen(locale, "module.filteredEmpty.description")} />
            <ActionButton onPress={resetListFilters} variant="secondary">{tScreen(locale, "module.filteredEmpty.reset")}</ActionButton>
          </View>
        )}
        {selectedRow ? <WorkDetailPanel locale={locale} row={selectedRow} onSelect={onSelect} /> : null}
      </Card>

      <View style={styles.actionPanels}>
        {[dashboard.primaryAction, dashboard.secondaryAction].map((action) => (
          <Card key={action.label} compact style={styles.actionPanelCard}>
            <Label weight="bold">{action.label}</Label>
            <ActionButton onPress={() => runModuleAction(action.target)} variant="ghost">{tScreen(locale, "actions.move")}</ActionButton>
          </Card>
        ))}
      </View>
    </View>
  );
}

function PayrollWorkPanel({ locale, onSelect }: Pick<ScreenProps, "locale" | "onSelect">) {
  return (
    <Card>
      <SectionHeader
        eyebrow={tScreen(locale, "payroll.work.eyebrow")}
        title={tScreen(locale, "payroll.work.title")}
        description={tScreen(locale, "payroll.work.description")}
        action={<ActionButton onPress={() => onSelect("hr")} variant="secondary">{tScreen(locale, "payroll.work.action")}</ActionButton>}
      />
      <View style={styles.payrollWorkGrid}>
        {payrollWorkDefinitions.map((item) => (
          <Pressable
            accessibilityRole="button"
            key={item.id}
            onPress={() => onSelect(item.target)}
            style={({ pressed }) => [
              styles.payrollWorkCard,
              { borderTopColor: toneColor(item.tone) },
              pressed && styles.buttonPressed
            ]}
          >
            <View style={styles.payrollWorkCardHead}>
              <Badge tone={item.tone}>{tScreen(locale, `payroll.work.items.${item.id}.status`)}</Badge>
              <Label size="sm" muted>{tScreen(locale, `payroll.work.items.${item.id}.due`)}</Label>
            </View>
            <Label weight="bold">{tScreen(locale, `payroll.work.items.${item.id}.title`)}</Label>
            <Label size="sm" muted>{tScreen(locale, `payroll.work.items.${item.id}.detail`)}</Label>
            <Label size="sm">{tScreen(locale, `payroll.work.items.${item.id}.owner`)}</Label>
          </Pressable>
        ))}
      </View>
    </Card>
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
      <View style={styles.detailGrid}>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workDetail.dueWindow")}</Label>
          <Label weight="bold">{step.dueWindow}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workDetail.blockers")}</Label>
          <Label>{step.blockers}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workDetail.permission")}</Label>
          <Label>{step.permission}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workDetail.liveState")}</Label>
          <Label>{step.liveState}</Label>
        </View>
      </View>
      <View style={styles.actionRow}>
        <ActionButton onPress={() => undefined} variant="secondary">{tScreen(locale, "payroll.stepDetail.actions.work")}</ActionButton>
        <ActionButton onPress={() => undefined} variant="ghost">{tScreen(locale, "payroll.stepDetail.actions.help")}</ActionButton>
      </View>
    </View>
  );
}

function WorkflowCanvasPanel({ locale, onSelect }: Pick<ScreenProps, "locale" | "onSelect">) {
  return (
    <Card>
      <SectionHeader
        title={tScreen(locale, "workflowCanvas.title")}
        description={tScreen(locale, "workflowCanvas.description")}
        action={<ActionButton onPress={() => onSelect("approval")} variant="secondary">{tScreen(locale, "workflowCanvas.action")}</ActionButton>}
      />
      <View style={styles.workflowCanvasGrid}>
        {workflowCanvasDefinitions.map((item) => (
          <Pressable
            accessibilityRole="button"
            key={item.id}
            onPress={() => onSelect(item.target)}
            style={({ pressed }) => [styles.workflowCanvasNode, { borderTopColor: toneColor(item.tone) }, pressed && styles.buttonPressed]}
          >
            <View style={styles.summaryCardHead}>
              <Label size="sm" muted>{tScreen(locale, `workflowCanvas.nodes.${item.id}.label`)}</Label>
              <Badge tone={item.tone}>{tScreen(locale, `workflowCanvas.nodes.${item.id}.status`)}</Badge>
            </View>
            <Label weight="bold">{tScreen(locale, `workflowCanvas.nodes.${item.id}.title`)}</Label>
            <Label size="sm" muted>{tScreen(locale, `workflowCanvas.nodes.${item.id}.detail`)}</Label>
          </Pressable>
        ))}
      </View>
      <View style={styles.inlineNotice}>
        <Badge tone="neutral">{tScreen(locale, "workflowCanvas.notice.badge")}</Badge>
        <Label size="sm" muted>{tScreen(locale, "workflowCanvas.notice.description")}</Label>
      </View>
    </Card>
  );
}

function ApprovalPanel({ locale, onSelect }: Pick<ScreenProps, "locale" | "onSelect">) {
  return (
    <Card>
      <SectionHeader
        title={tScreen(locale, "approval.title")}
        description={tScreen(locale, "approval.description")}
        action={<ActionButton onPress={() => onSelect("archive")} variant="secondary">{tScreen(locale, "approval.action")}</ActionButton>}
      />
      <View style={styles.approvalSummaryGrid}>
        {approvalSummaryDefinitions.map((item) => (
          <Pressable
            accessibilityRole="button"
            key={item.id}
            onPress={() => onSelect(item.target)}
            style={({ pressed }) => [styles.approvalSummaryCard, { borderTopColor: toneColor(item.tone) }, pressed && styles.buttonPressed]}
          >
            <View style={styles.summaryCardHead}>
              <Label size="sm" muted>{tScreen(locale, `approval.cards.${item.id}.label`)}</Label>
              <Badge tone={item.tone}>{tScreen(locale, `approval.cards.${item.id}.status`)}</Badge>
            </View>
            <Label weight="bold">{tScreen(locale, `approval.cards.${item.id}.title`)}</Label>
            <Label size="sm" muted>{tScreen(locale, `approval.cards.${item.id}.detail`)}</Label>
          </Pressable>
        ))}
      </View>
      <View style={styles.inlineNotice}>
        <Badge tone="neutral">{tScreen(locale, "approval.notice.badge")}</Badge>
        <Label size="sm" muted>{tScreen(locale, "approval.notice.description")}</Label>
      </View>
    </Card>
  );
}

function RecruitPlacementPanel({ locale, onSelect }: Pick<ScreenProps, "locale" | "onSelect">) {
  return (
    <Card>
      <SectionHeader
        title={tScreen(locale, "recruitPlacement.title")}
        description={tScreen(locale, "recruitPlacement.description")}
        action={<ActionButton onPress={() => onSelect("hr")} variant="secondary">{tScreen(locale, "recruitPlacement.action")}</ActionButton>}
      />
      <View style={styles.recruitPlacementGrid}>
        {recruitPlacementDefinitions.map((item) => (
          <Pressable
            accessibilityRole="button"
            key={item.id}
            onPress={() => onSelect(item.target)}
            style={({ pressed }) => [styles.recruitPlacementCard, { borderTopColor: toneColor(item.tone) }, pressed && styles.buttonPressed]}
          >
            <View style={styles.recruitPlacementHead}>
              <Label size="sm" muted>{tScreen(locale, `recruitPlacement.cards.${item.id}.label`)}</Label>
              <Badge tone={item.tone}>{tScreen(locale, `recruitPlacement.cards.${item.id}.status`)}</Badge>
            </View>
            <Label weight="bold">{tScreen(locale, `recruitPlacement.cards.${item.id}.title`)}</Label>
            <Label size="sm" muted>{tScreen(locale, `recruitPlacement.cards.${item.id}.detail`)}</Label>
          </Pressable>
        ))}
      </View>
      <View style={styles.inlineNotice}>
        <Badge tone="neutral">{tScreen(locale, "recruitPlacement.notice.badge")}</Badge>
        <Label size="sm" muted>{tScreen(locale, "recruitPlacement.notice.description")}</Label>
      </View>
    </Card>
  );
}

function HrPeoplePanel({ locale, onSelect }: Pick<ScreenProps, "locale" | "onSelect">) {
  return (
    <Card>
      <SectionHeader
        title={tScreen(locale, "hrPeople.title")}
        description={tScreen(locale, "hrPeople.description")}
        action={<ActionButton onPress={() => onSelect("payroll")} variant="secondary">{tScreen(locale, "hrPeople.action")}</ActionButton>}
      />
      <View style={styles.hrPeopleGrid}>
        {hrPeopleReviewDefinitions.map((item) => (
          <Pressable
            accessibilityRole="button"
            key={item.id}
            onPress={() => onSelect(item.target)}
            style={({ pressed }) => [styles.hrPeopleCard, { borderTopColor: toneColor(item.tone) }, pressed && styles.buttonPressed]}
          >
            <View style={styles.hrPeopleHead}>
              <Label size="sm" muted>{tScreen(locale, `hrPeople.cards.${item.id}.label`)}</Label>
              <Badge tone={item.tone}>{tScreen(locale, `hrPeople.cards.${item.id}.status`)}</Badge>
            </View>
            <Label weight="bold">{tScreen(locale, `hrPeople.cards.${item.id}.title`)}</Label>
            <Label size="sm" muted>{tScreen(locale, `hrPeople.cards.${item.id}.detail`)}</Label>
          </Pressable>
        ))}
      </View>
      <View style={styles.inlineNotice}>
        <Badge tone="neutral">{tScreen(locale, "hrPeople.notice.badge")}</Badge>
        <Label size="sm" muted>{tScreen(locale, "hrPeople.notice.description")}</Label>
      </View>
    </Card>
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

function MaintenanceRentalBridgePanel({ locale }: Pick<ScreenProps, "locale">) {
  const openRuntime = () => {
    void Linking.openURL(maintenanceRentalIntegration.runtimeUrl);
  };
  const openRepository = () => {
    void Linking.openURL(maintenanceRentalIntegration.repositoryUrl);
  };

  return (
    <Card>
      <SectionHeader
        eyebrow={tScreen(locale, "maintenanceRental.eyebrow")}
        title={tScreen(locale, "maintenanceRental.title")}
        description={tScreen(locale, "maintenanceRental.description")}
        action={<ActionButton onPress={openRuntime} variant="primary">{tScreen(locale, "maintenanceRental.actions.open")}</ActionButton>}
      />
      <View style={styles.integrationGrid}>
        {maintenanceRentalBridgeDefinitions.map((item) => (
          <View key={item.id} style={[styles.integrationCard, { borderTopColor: toneColor(item.tone) }]}>
            <Label size="sm" muted>{tScreen(locale, `maintenanceRental.cards.${item.id}.label`)}</Label>
            <Text style={[styles.integrationValue, { color: toneColor(item.tone) }]}>{tScreen(locale, `maintenanceRental.cards.${item.id}.value`)}</Text>
            <Label size="sm">{tScreen(locale, `maintenanceRental.cards.${item.id}.detail`)}</Label>
          </View>
        ))}
      </View>
      <View style={styles.detailGrid}>
        <View style={styles.detailItem}>
          <Badge tone="ready">{tScreen(locale, "maintenanceRental.flow.badge")}</Badge>
          <Label weight="bold">{tScreen(locale, "maintenanceRental.flow.title")}</Label>
          <Label size="sm" muted>{tScreen(locale, "maintenanceRental.flow.detail")}</Label>
        </View>
        <View style={styles.detailItem}>
          <Badge tone="neutral">{tScreen(locale, "maintenanceRental.bitween.badge")}</Badge>
          <Label weight="bold">{tScreen(locale, "maintenanceRental.bitween.title")}</Label>
          <Label size="sm" muted>{tScreen(locale, "maintenanceRental.bitween.detail")}</Label>
        </View>
      </View>
      <View style={styles.inlineNotice}>
        <Badge tone="neutral">{tScreen(locale, "maintenanceRental.notice.badge")}</Badge>
        <Label size="sm" muted>{tScreen(locale, "maintenanceRental.notice.detail")}</Label>
      </View>
      <View style={styles.actionRow}>
        <ActionButton onPress={openRuntime} variant="primary">{tScreen(locale, "maintenanceRental.actions.open")}</ActionButton>
        <ActionButton onPress={openRepository} variant="ghost">{tScreen(locale, "maintenanceRental.actions.github")}</ActionButton>
      </View>
    </Card>
  );
}

type SettingsControlPanelProps = Pick<ScreenProps, "locale" | "onSelect"> & {
  readonly onThemeChange: (theme: SidebarThemeId) => void;
  readonly sidebarTheme: SidebarTheme;
};

function SettingsControlPanel({ locale, onSelect, onThemeChange, sidebarTheme }: SettingsControlPanelProps) {
  const sidebarThemes = useMemo(() => getSidebarThemes(locale), [locale]);

  return (
    <Card>
      <SectionHeader
        title={tScreen(locale, "settingsControl.title")}
        description={tScreen(locale, "settingsControl.description")}
        action={<ActionButton onPress={() => onSelect("admin")} variant="secondary">{tScreen(locale, "settingsControl.action")}</ActionButton>}
      />
      <View style={styles.settingsThemePanel}>
        <SectionHeader title={t(locale, "settings.theme.title")} description={t(locale, "settings.theme.description")} />
        <View style={styles.settingsThemeGrid}>
          {sidebarThemes.map((item) => {
            const selected = item.id === sidebarTheme.id;
            return (
              <Pressable
                accessibilityHint={item.description}
                accessibilityLabel={t(locale, "settings.theme.optionLabel", { label: item.label, description: item.description })}
                accessibilityRole="button"
                accessibilityState={{ selected }}
                key={item.id}
                onPress={() => onThemeChange(item.id)}
                style={({ pressed }) => [
                  styles.settingsThemeOption,
                  selected && styles.settingsThemeOptionSelected,
                  pressed && styles.buttonPressed
                ]}
              >
                <View style={[styles.settingsThemeSwatch, { backgroundColor: item.swatchStart, borderColor: item.swatchEnd }]}>
                  <View style={[styles.settingsThemeSwatchInset, { backgroundColor: item.swatchEnd }]} />
                </View>
                <View style={styles.settingsThemeCopy}>
                  <Label weight="bold">{item.label}</Label>
                  <Label size="sm" muted>{item.description}</Label>
                </View>
                <Badge tone={selected ? "ready" : "neutral"}>
                  {t(locale, selected ? "settings.i18n.status.selected" : "settings.i18n.status.available")}
                </Badge>
              </Pressable>
            );
          })}
        </View>
        <View style={styles.settingsThemeCurrent}>
          <View style={[styles.settingsThemeCurrentRail, { backgroundColor: sidebarTheme.activeText }]} />
          <View style={styles.settingsThemeCopy}>
            <Label size="sm" weight="bold">{t(locale, "settings.theme.current", { theme: sidebarTheme.label })}</Label>
            <Label size="sm" muted>{sidebarTheme.description}</Label>
          </View>
        </View>
      </View>
      <View style={styles.settingsGrid}>
        {settingsPreferenceDefinitions.map((item) => (
          <Pressable
            accessibilityRole="button"
            key={item.id}
            onPress={() => onSelect(item.target)}
            style={({ pressed }) => [styles.settingsPreferenceCard, { borderTopColor: toneColor(item.tone) }, pressed && styles.buttonPressed]}
          >
            <View style={styles.settingsPreferenceHead}>
              <Label size="sm" muted>{tScreen(locale, `settingsControl.cards.${item.id}.label`)}</Label>
              <Badge tone={item.tone}>{tScreen(locale, `settingsControl.cards.${item.id}.value`)}</Badge>
            </View>
            <Label size="sm">{tScreen(locale, `settingsControl.cards.${item.id}.detail`)}</Label>
          </Pressable>
        ))}
      </View>
      <View style={styles.settingsNotice}>
        <Badge tone="neutral">{tScreen(locale, "settingsControl.notice.badge")}</Badge>
        <Label size="sm" muted>{tScreen(locale, "settingsControl.notice.description")}</Label>
      </View>
    </Card>
  );
}

function AdminAccountPanel({ locale, onSelect }: Pick<ScreenProps, "locale" | "onSelect">) {
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
      <View style={styles.adminReviewPanel}>
        <SectionHeader title={tScreen(locale, "admin.review.title")} description={tScreen(locale, "admin.review.description")} />
        <View style={styles.adminReviewGrid}>
          {adminReviewDefinitions.map((item) => (
            <Pressable
              accessibilityRole="button"
              key={item.id}
              onPress={() => onSelect(item.target)}
              style={({ pressed }) => [styles.adminReviewCard, { borderTopColor: toneColor(item.tone) }, pressed && styles.buttonPressed]}
            >
              <View style={styles.adminReviewHead}>
                <Label size="sm" muted>{tScreen(locale, `admin.review.cards.${item.id}.label`)}</Label>
                <Badge tone={item.tone}>{tScreen(locale, `admin.review.cards.${item.id}.status`)}</Badge>
              </View>
              <Label weight="bold">{tScreen(locale, `admin.review.cards.${item.id}.title`)}</Label>
              <Label size="sm" muted>{tScreen(locale, `admin.review.cards.${item.id}.detail`)}</Label>
            </Pressable>
          ))}
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
        {travelWorkflowStageDefinitions.map((stage) => (
          <View key={stage.id} style={[styles.travelStageCard, { borderTopColor: toneColor(stage.tone) }]}>
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

function AttendanceAppPrompt({ locale, onOpen }: Pick<ScreenProps, "locale"> & { readonly onOpen: () => void }) {
  return (
    <Card>
      <SectionHeader
        title={tScreen(locale, "attendance.appPrompt.title")}
        description={tScreen(locale, "attendance.appPrompt.description")}
        action={<ActionButton onPress={onOpen}>{tScreen(locale, "attendance.appPrompt.action")}</ActionButton>}
      />
      <View style={styles.inlineNotice}>
        <Badge tone="neutral">{tScreen(locale, "attendance.appPrompt.badge")}</Badge>
        <Label size="sm" muted>{tScreen(locale, "attendance.appPrompt.notice")}</Label>
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
          <Label size="sm" muted>{tScreen(locale, "workDetail.dueWindow")}</Label>
          <Label weight="bold">{row.dueWindow}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workDetail.blockers")}</Label>
          <Label>{row.blockers}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workDetail.permission")}</Label>
          <Label>{row.permission}</Label>
        </View>
        <View style={styles.detailItem}>
          <Label size="sm" muted>{tScreen(locale, "workDetail.liveState")}</Label>
          <Label>{row.liveState}</Label>
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
  adminReviewCard: {
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
  adminReviewGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  adminReviewHead: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    justifyContent: "space-between"
  },
  adminReviewPanel: {
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.md
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
  filteredEmptyState: {
    alignItems: "flex-start",
    gap: spacing.md
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
  hrPeopleCard: {
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
  hrPeopleGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  hrPeopleHead: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    justifyContent: "space-between"
  },
  homeFocusCard: {
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.xs,
    minHeight: 96,
    padding: spacing.md
  },
  homeFocusCardPrimary: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.accent,
    borderLeftColor: colors.accent,
    borderLeftWidth: 5,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexBasis: 320,
    flexGrow: 2,
    gap: spacing.sm,
    minHeight: 184,
    padding: spacing.lg
  },
  homeFocusGrid: {
    alignItems: "stretch",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  homeFocusSide: {
    flexBasis: 240,
    flexGrow: 1,
    gap: spacing.md
  },
  homePrepCard: {
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
  homePrepGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
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
  settingsStatusGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  settingsStatusItem: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexBasis: 180,
    flexGrow: 1,
    gap: spacing.xs,
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
  listSummaryCopy: {
    flex: 1,
    minWidth: 160
  },
  listSummaryCount: {
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs
  },
  listToolbar: {
    alignItems: "flex-end",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  settingsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  settingsNotice: {
    alignItems: "center",
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    padding: spacing.md
  },
  settingsPreferenceCard: {
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
  settingsPreferenceHead: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    justifyContent: "space-between"
  },
  settingsThemeCopy: {
    flex: 1,
    gap: spacing.xs,
    minWidth: 0
  },
  settingsThemeCurrent: {
    alignItems: "stretch",
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.sm,
    padding: spacing.md
  },
  settingsThemeCurrentRail: {
    borderRadius: 999,
    width: 4
  },
  settingsThemeGrid: {
    gap: spacing.sm
  },
  settingsThemeOption: {
    alignItems: "center",
    backgroundColor: colors.input,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
    padding: spacing.md
  },
  settingsThemeOptionSelected: {
    backgroundColor: colors.accentSoft,
    borderColor: colors.accent
  },
  settingsThemePanel: {
    gap: spacing.md,
    marginBottom: spacing.lg
  },
  settingsThemeSwatch: {
    borderRadius: 999,
    borderWidth: 1,
    height: 28,
    overflow: "hidden",
    width: 28
  },
  settingsThemeSwatchInset: {
    alignSelf: "flex-end",
    height: 28,
    width: 14
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
  recruitPlacementCard: {
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
  recruitPlacementGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  recruitPlacementHead: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    justifyContent: "space-between"
  },
  payrollWorkCard: {
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
  payrollWorkCardHead: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    justifyContent: "space-between"
  },
  payrollWorkGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  stack: {
    gap: spacing.lg
  },
  stackXs: {
    gap: spacing.xs
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
  approvalSummaryCard: {
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
  approvalSummaryGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  summaryCardHead: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    justifyContent: "space-between"
  },
  workflowCanvasGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md
  },
  workflowCanvasNode: {
    backgroundColor: colors.bg,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderTopWidth: 4,
    borderWidth: 1,
    flexBasis: 180,
    flexGrow: 1,
    gap: spacing.sm,
    padding: spacing.md
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
  todoProgressFill: {
    backgroundColor: colors.success,
    borderRadius: 999,
    minHeight: 8
  },
  todoProgressHeader: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    justifyContent: "space-between"
  },
  todoProgressPanel: {
    backgroundColor: colors.successSoft,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.md
  },
  todoProgressTrack: {
    backgroundColor: colors.card,
    borderRadius: 999,
    minHeight: 8,
    overflow: "hidden"
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
  }
});
