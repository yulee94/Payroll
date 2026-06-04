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
  calendarEvents,
  moduleDashboards,
  payrollIntegrationRows,
  navigationItems,
  payrollSettingsRows,
  payrollSteps,
  platformMetrics,
  previewRows,
  readinessCards,
  todayTodos,
  workQueue
} from "./data";
import { colors, radius, spacing, toneColor } from "./theme";
import type { CalendarEvent, ModuleRow, NavigationItem, PayrollStep, PlatformId, ReadinessCard, TodoItem, WorkQueueItem } from "./types";

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

const languageOptions = [
  { code: "ko", label: "한국어", status: "현재 적용" },
  { code: "en", label: "English", status: "준비" },
  { code: "zh", label: "中文", status: "준비" }
] as const;

type LanguageCode = (typeof languageOptions)[number]["code"];

const attendanceLogs = [
  { id: "att-log-1", label: "출근", place: "본사", time: "09:02", tone: "ready" },
  { id: "att-log-2", label: "외근", place: "고객사", time: "13:40", tone: "attention" },
  { id: "att-log-3", label: "퇴근", place: "대기", time: "--:--", tone: "neutral" }
] as const;

const travelWorkflowStages = [
  { id: "travel-plan", label: "출장계획", detail: "출장신청서와 일정 목적을 먼저 정리합니다.", status: "작성/승인", tone: "neutral" },
  { id: "travel-run", label: "출장실행", detail: "현장 방문, 이동, 고객 미팅 상태를 표시합니다.", status: "진행 중", tone: "attention" },
  { id: "travel-diary", label: "업무일지", detail: "출장 중 처리한 업무와 후속 조치를 기록합니다.", status: "오늘 작성", tone: "attention" },
  { id: "travel-result", label: "실적반영", detail: "계약, 매출, 고객 대응 결과를 성과에 연결합니다.", status: "검토 대기", tone: "neutral" },
  { id: "travel-review", label: "상급자 view", detail: "on-going과 Completed 상태를 관리자가 나눠 확인합니다.", status: "view 준비", tone: "ready" }
] as const;

const adminPermissionRows = [
  { id: "role-owner", role: "Branch 관리자", payroll: "전체", executive: "요청 승인", archive: "전체", tone: "ready" },
  { id: "role-manager", role: "경영진", payroll: "열람", executive: "열람", archive: "경영 자료", tone: "neutral" },
  { id: "role-employee", role: "일반 사원", payroll: "본인 자료", executive: "차단", archive: "공유 자료", tone: "attention" }
] as const;

const payrollIntegrationChecks = [
  { id: "branch-docs", label: "법인/사업장 입력자료", value: "3곳", detail: "근태문서와 청구서 유형을 사업장별로 구분합니다.", tone: "attention" },
  { id: "edi", label: "건강보험EDI", value: "확인 전", detail: "급여 작업 전 보험료 변동 확인이 필요한 상태입니다.", tone: "attention" },
  { id: "mapping", label: "양식 매핑", value: "2종", detail: "근태문서/청구서 입력 양식 연결 예정입니다.", tone: "neutral" },
  { id: "policy", label: "산출 진입", value: "대기", detail: "backend API 계약 후 실제 검증 흐름으로 전환합니다.", tone: "ready" }
] as const;

const archiveFolders = [
  { id: "folder-payroll", label: "급여 산출물", count: "12개", owner: "급여 담당", tone: "ready", target: "payroll" },
  { id: "folder-attendance", label: "근태 원본", count: "4개", owner: "운영팀", tone: "attention", target: "attendance" },
  { id: "folder-approval", label: "결재 첨부", count: "8개", owner: "승인권자", tone: "neutral", target: "workflow" },
  { id: "folder-travel", label: "출장/업무일지", count: "7개", owner: "영업팀", tone: "ready", target: "travel" }
] as const;

const archiveDocuments = [
  { id: "doc-payroll", title: "2026년 5월 급여 보고서", type: "Excel", owner: "급여 담당", status: "보관됨", tone: "ready" },
  { id: "doc-attendance", title: "6월 1주차 근태 원본", type: "CSV", owner: "운영팀", status: "분류 대기", tone: "attention" },
  { id: "doc-travel", title: "부산 출장 업무일지", type: "PDF", owner: "영업팀", status: "성과 연결", tone: "neutral" }
] as const;

const aiRecommendations = [
  { id: "ai-payroll-errors", title: "급여 산출 오류 요약", source: "급여 준비 현황", status: "추천", tone: "ready", target: "payroll" },
  { id: "ai-approval-comment", title: "결재 의견 초안", source: "전자결재 대기 문서", status: "검토 필요", tone: "attention", target: "workflow" },
  { id: "ai-archive-summary", title: "자료함 문서 요약", source: "2026년 5월 급여 보고서", status: "미리보기", tone: "neutral", target: "archive" }
] as const;

const aiDraftCards = [
  { id: "draft-summary", label: "요약", title: "급여 기준 확인 요약", detail: "누락된 입력자료, EDI 확인 전 상태, 산출 전 검토 항목을 짧게 정리합니다.", tone: "ready" },
  { id: "draft-question", label: "확인 질문", title: "관리자에게 물어볼 항목", detail: "경영진 급여 열람 권한과 Branch 하위계정 범위를 확인하도록 제안합니다.", tone: "attention" },
  { id: "draft-comment", label: "초안", title: "결재 의견 문장", detail: "급여 지급 품의에 붙일 검토 의견 초안을 사람이 확인하기 전 상태로 표시합니다.", tone: "neutral" }
] as const;

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
          title="오늘의 플랫폼 상태"
          description="중요한 업무 상태를 먼저 보고 필요한 메뉴로 바로 이동합니다."
          action={<ActionButton onPress={() => onSelect("payroll")} variant="secondary">급여 준비 확인</ActionButton>}
        />
        <MetricGrid items={platformMetrics} />
      </Card>

      <CalendarTodoPanel events={calendarEvents} todos={todayTodos} />

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
      <PayrollIntegrationPanel onSelect={onSelect} />
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

function PayrollIntegrationPanel({ onSelect }: Pick<ScreenProps, "onSelect">) {
  return (
    <Card>
      <SectionHeader
        title="급여 연동 준비 점검"
        description="법인/사업장별 근태문서, 청구서, 건강보험EDI 확인 상태를 산출 전 화면에서 먼저 정리합니다."
        action={<ActionButton onPress={() => onSelect("admin")} variant="secondary">Branch 권한 확인</ActionButton>}
      />
      <View style={styles.integrationGrid}>
        {payrollIntegrationChecks.map((item) => (
          <View key={item.id} style={[styles.integrationCard, { borderTopColor: toneColor(item.tone) }]}>
            <Label size="sm" muted>{item.label}</Label>
            <Text style={[styles.integrationValue, { color: toneColor(item.tone) }]}>{item.value}</Text>
            <Label size="sm">{item.detail}</Label>
          </View>
        ))}
      </View>
      <DataTable rows={payrollIntegrationRows} />
      <View style={styles.inlineNotice}>
        <Badge tone="neutral">Frontend 준비</Badge>
        <Label size="sm" muted>실제 건강보험EDI 조회, 보험료 공제금액 반영, 사업장별 입력 양식 검증은 backend/API 계약 후 연결합니다.</Label>
      </View>
    </Card>
  );
}

function CalendarTodoPanel({ events, todos }: { readonly events: readonly CalendarEvent[]; readonly todos: readonly TodoItem[] }) {
  return (
    <View style={styles.homePlannerGrid}>
      <Card style={styles.homePlannerCard}>
        <SectionHeader title="오늘 일정" description="2026년 6월 4일 기준 주요 일정을 확인합니다." />
        <View style={styles.calendarDay}>
          <Text style={styles.calendarMonth}>2026.06</Text>
          <Text style={styles.calendarDate}>04</Text>
          <Label size="sm" muted>목요일</Label>
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
        <SectionHeader title="To-do list" description="오늘 업무는 계속 표시하고, 실행한 항목은 흐리게 표시합니다." />
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
  const [selectedLanguage, setSelectedLanguage] = useState<LanguageCode>("ko");
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
          title={dashboard.title}
          action={<ActionButton onPress={() => onSelect(dashboard.primaryAction.target)}>{dashboard.primaryAction.label}</ActionButton>}
        />
        <MetricGrid items={dashboard.metrics} />
      </Card>

      {active.id === "attendance" ? <AttendancePhonePanel /> : null}
      {active.id === "travel" ? <TravelWorklogPanel /> : null}
      {active.id === "admin" ? <AdminAccountPanel /> : null}
      {active.id === "archive" ? <ArchiveLibraryPanel onSelect={onSelect} /> : null}
      {active.id === "ai" ? <AiWorkspacePanel onSelect={onSelect} /> : null}

      {active.id === "settings" ? (
        <Card>
          <SectionHeader title="국제화 설정" description="한국어, 영어, 중국어 화면 전환을 준비합니다." />
          <View style={styles.languageGrid}>
            {languageOptions.map((option) => {
              const selected = option.code === selectedLanguage;
              return (
                <Pressable
                  accessibilityRole="button"
                  key={option.code}
                  onPress={() => setSelectedLanguage(option.code)}
                  style={({ pressed }) => [styles.languageOption, selected && styles.languageOptionSelected, pressed && styles.buttonPressed]}
                >
                  <Label weight="bold">{option.label}</Label>
                  <Label size="sm" muted>{selected ? "선택됨" : option.status}</Label>
                </Pressable>
              );
            })}
          </View>
        </Card>
      ) : null}

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

function ArchiveLibraryPanel({ onSelect }: Pick<ScreenProps, "onSelect">) {
  return (
    <Card>
      <SectionHeader
        title="자료함 작업대"
        description="급여 산출물, 근태 원본, 결재 첨부, 출장/업무일지 자료를 폴더별로 확인하고 최근 문서를 바로 미리봅니다."
        action={<ActionButton onPress={() => onSelect("payroll")} variant="secondary">급여 자료 확인</ActionButton>}
      />
      <View style={styles.archiveFolderGrid}>
        {archiveFolders.map((folder) => (
          <Pressable
            accessibilityRole="button"
            key={folder.id}
            onPress={() => onSelect(folder.target)}
            style={({ pressed }) => [styles.archiveFolderCard, { borderTopColor: toneColor(folder.tone) }, pressed && styles.buttonPressed]}
          >
            <Badge tone={folder.tone}>{folder.count}</Badge>
            <Label weight="bold">{folder.label}</Label>
            <Label size="sm" muted>{folder.owner}</Label>
          </Pressable>
        ))}
      </View>
      <View style={styles.archivePreviewGrid}>
        <View style={styles.archiveDocumentList}>
          {archiveDocuments.map((document) => (
            <View key={document.id} style={styles.archiveDocumentItem}>
              <Badge tone={document.tone}>{document.status}</Badge>
              <View style={styles.plannerCopy}>
                <Label weight="bold">{document.title}</Label>
                <Label size="sm" muted>{document.type} · {document.owner}</Label>
              </View>
            </View>
          ))}
        </View>
        <View style={styles.archivePreviewPane}>
          <Label size="sm" muted>선택 문서 미리보기</Label>
          <Label weight="bold">2026년 5월 급여 보고서</Label>
          <View style={styles.archiveMetaGrid}>
            <View style={styles.archiveMetaItem}>
              <Label size="sm" muted>보안 범위</Label>
              <Label weight="bold">급여 담당 / Branch 관리자</Label>
            </View>
            <View style={styles.archiveMetaItem}>
              <Label size="sm" muted>상태</Label>
              <Label weight="bold">보관됨</Label>
            </View>
          </View>
          <View style={styles.actionRow}>
            <ActionButton onPress={() => onSelect("payroll")} variant="secondary">급여 화면 열기</ActionButton>
            <ActionButton onPress={() => onSelect("admin")} variant="ghost">권한 확인</ActionButton>
          </View>
        </View>
      </View>
    </Card>
  );
}

function AiWorkspacePanel({ onSelect }: Pick<ScreenProps, "onSelect">) {
  return (
    <Card>
      <SectionHeader
        title="AI 업무 작업대"
        description="급여, 결재, 자료함 문맥에서 추천 작업을 고르고 사람이 확인해야 할 초안과 질문을 분리합니다."
        action={<ActionButton onPress={() => onSelect("settings")} variant="secondary">AI 사용 범위 확인</ActionButton>}
      />
      <View style={styles.aiWorkspaceGrid}>
        <View style={styles.aiRecommendationList}>
          {aiRecommendations.map((item) => (
            <Pressable
              accessibilityRole="button"
              key={item.id}
              onPress={() => onSelect(item.target)}
              style={({ pressed }) => [styles.aiRecommendationItem, { borderLeftColor: toneColor(item.tone) }, pressed && styles.buttonPressed]}
            >
              <Badge tone={item.tone}>{item.status}</Badge>
              <View style={styles.plannerCopy}>
                <Label weight="bold">{item.title}</Label>
                <Label size="sm" muted>{item.source}</Label>
              </View>
            </Pressable>
          ))}
        </View>
        <View style={styles.aiPreviewPane}>
          <Label size="sm" muted>사람 검토 필요</Label>
          <Label weight="bold">AI가 만든 문장은 바로 확정하지 않고 담당자가 확인합니다.</Label>
          <View style={styles.aiDraftGrid}>
            {aiDraftCards.map((card) => (
              <View key={card.id} style={[styles.aiDraftCard, { borderTopColor: toneColor(card.tone) }]}>
                <Badge tone={card.tone}>{card.label}</Badge>
                <Label weight="bold">{card.title}</Label>
                <Label size="sm" muted>{card.detail}</Label>
              </View>
            ))}
          </View>
          <View style={styles.actionRow}>
            <ActionButton onPress={() => onSelect("payroll")} variant="secondary">급여 문맥 열기</ActionButton>
            <ActionButton onPress={() => onSelect("archive")} variant="ghost">자료함 문서 보기</ActionButton>
          </View>
        </View>
      </View>
    </Card>
  );
}

function AdminAccountPanel() {
  return (
    <Card>
      <SectionHeader title="법인 Branch / 하위계정 권한" description="회사 하나를 하나의 Branch로 보고, 하위계정과 민감 문서 접근 범위를 화면에서 분리합니다." />
      <View style={styles.adminBranchGrid}>
        <View style={styles.adminBranchCard}>
          <Label size="sm" muted>Branch 계정</Label>
          <Label weight="bold">Bitween Demo · 법인코드 0000</Label>
          <Label size="sm" muted>법인 기본사항 입력, 사업장 정보, 하위계정 생성 권한을 이 화면에서 검토합니다.</Label>
        </View>
        <View style={styles.adminBranchCard}>
          <Label size="sm" muted>하위계정 구조</Label>
          <Label weight="bold">관리자 2명 · 경영진 3명 · 일반 사원 9명</Label>
          <Label size="sm" muted>신규 계정은 Branch 소속, 부서, 역할을 지정한 뒤 초대합니다.</Label>
        </View>
      </View>
      <View style={styles.permissionMatrix}>
        {adminPermissionRows.map((row) => (
          <View key={row.id} style={styles.permissionRow}>
            <View style={styles.permissionRole}>
              <Badge tone={row.tone}>{row.role}</Badge>
            </View>
            <View style={styles.permissionCell}>
              <Label size="sm" muted>급여</Label>
              <Label weight="bold">{row.payroll}</Label>
            </View>
            <View style={styles.permissionCell}>
              <Label size="sm" muted>경영진 급여</Label>
              <Label weight="bold">{row.executive}</Label>
            </View>
            <View style={styles.permissionCell}>
              <Label size="sm" muted>자료함</Label>
              <Label weight="bold">{row.archive}</Label>
            </View>
          </View>
        ))}
      </View>
    </Card>
  );
}

function TravelWorklogPanel() {
  return (
    <Card>
      <SectionHeader title="출장/업무일지 흐름" description="출장계획부터 출장실행, 업무일지, 실적반영, 상급자 검토까지 한 화면에서 확인합니다." />
      <View style={styles.travelStageGrid}>
        {travelWorkflowStages.map((stage, index) => (
          <View key={stage.id} style={[styles.travelStageCard, { borderTopColor: toneColor(stage.tone) }]}>
            <Text style={styles.travelStageStep}>{String(index + 1).padStart(2, "0")}</Text>
            <Badge tone={stage.tone}>{stage.status}</Badge>
            <Label weight="bold">{stage.label}</Label>
            <Label size="sm" muted>{stage.detail}</Label>
          </View>
        ))}
      </View>
      <View style={styles.travelReviewGrid}>
        <View style={styles.travelReviewCard}>
          <Label size="sm" muted>상급자 on-going view</Label>
          <Label weight="bold">진행 중 출장 2건</Label>
          <Label size="sm" muted>출장실행, 업무일지 작성, 실적 반영 대기 상태를 분리해서 봅니다.</Label>
        </View>
        <View style={styles.travelReviewCard}>
          <Label size="sm" muted>상급자 Completed view</Label>
          <Label weight="bold">완료 반영 7건</Label>
          <Label size="sm" muted>검토 완료된 출장신청서, 업무일지, 성과 연결 내역을 보관 화면으로 넘깁니다.</Label>
        </View>
      </View>
    </Card>
  );
}

function AttendancePhonePanel() {
  return (
    <Card>
      <SectionHeader title="휴대폰 출퇴근" description="직원이 모바일에서 확인하는 오늘의 출근/퇴근 상태입니다." />
      <View style={styles.attendanceGrid}>
        <View style={styles.phoneFrame}>
          <View style={styles.phoneHeader}>
            <Label size="sm" muted>오늘 상태</Label>
            <Badge tone="ready">출근 확인</Badge>
          </View>
          <View style={styles.phoneClock}>
            <Text style={styles.phoneTime}>09:02</Text>
            <Label size="sm" muted>본사 120m 이내 · 위치 확인됨</Label>
          </View>
          <View style={styles.punchActions}>
            <Pressable accessibilityRole="button" style={({ pressed }) => [styles.punchButton, pressed && styles.buttonPressed]}>
              <Text style={styles.punchButtonText}>출근</Text>
            </Pressable>
            <Pressable accessibilityRole="button" style={({ pressed }) => [styles.punchButtonSecondary, pressed && styles.buttonPressed]}>
              <Text style={styles.punchButtonSecondaryText}>퇴근</Text>
            </Pressable>
          </View>
          <View style={styles.locationNotice}>
            <Label size="sm" weight="bold">위치 확인</Label>
            <Label size="sm" muted>GPS 또는 현장 QR 확인 후 기록되는 모바일 UI 자리입니다.</Label>
          </View>
        </View>
        <View style={styles.attendanceSide}>
          <View style={styles.attendanceSummaryCard}>
            <Label size="sm" muted>관리자 확인</Label>
            <Label weight="bold">외근 위치 확인 1건</Label>
            <Label size="sm" muted>사유와 위치 메모를 확인한 뒤 승인 흐름으로 연결합니다.</Label>
          </View>
          <View style={styles.attendanceLogList}>
            {attendanceLogs.map((log) => (
              <View key={log.id} style={styles.attendanceLogItem}>
                <Badge tone={log.tone}>{log.label}</Badge>
                <View style={styles.plannerCopy}>
                  <Label weight="bold">{log.time}</Label>
                  <Label size="sm" muted>{log.place}</Label>
                </View>
              </View>
            ))}
          </View>
        </View>
      </View>
    </Card>
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

  if (item.meta.includes("출장") || item.meta.includes("업무일지")) {
    return "travel";
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

  if (haystack.includes("출장") || haystack.includes("업무일지") || haystack.includes("실적")) {
    return "travel";
  }

  if (haystack.includes("자료") || haystack.includes("보고서") || haystack.includes("파일") || haystack.includes("폴더")) {
    return "archive";
  }

  if (haystack.includes("권한") || haystack.includes("사용자") || haystack.includes("역할") || haystack.includes("법인")) {
    return "admin";
  }

  if (haystack.includes("채용") || haystack.includes("지원자") || haystack.includes("자격") || haystack.includes("배치")) {
    return "recruit";
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

  if (haystack.includes("출근") || haystack.includes("퇴근") || haystack.includes("외근")) {
    return "attendance";
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
