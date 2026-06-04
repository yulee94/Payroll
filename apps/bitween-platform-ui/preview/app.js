const tones = {
  ready: "tone-ready",
  attention: "tone-attention",
  blocked: "tone-blocked",
  neutral: "tone-neutral"
};

const demoAccount = {
  companyCode: "0000",
  password: "admin",
  userId: "admin"
};

const sessionLabel = "Bitween Demo · admin · 0000";
const employeeNumber = "BW-0001";
const companyLogoUri =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%231F3864'/%3E%3Cpath d='M18 18h18c7 0 11 4 11 9 0 4-2 7-6 8 5 1 8 5 8 10 0 6-5 10-13 10H18V18zm11 14h6c3 0 5-1 5-4s-2-4-5-4h-6v8zm0 17h7c4 0 6-2 6-5s-2-5-6-5h-7v10z' fill='white'/%3E%3C/svg%3E";

const navItems = [
  ["home", "플랫폼 홈", "Launcher", "오늘의 업무, 빠른 실행, 플랫폼 상태를 한 화면에서 확인합니다.", "#64748B"],
  ["payroll", "급여", "Payroll", "급여 자동화 준비 상태, 산출 진입, 월별 보고와 설정을 관리합니다.", "#1F3864"],
  ["hr", "HR", "People", "직원 명부, 이력서, 사직서, 증명서 흐름을 정리합니다.", "#0D9488"],
  ["recruit", "채용", "Recruit", "지원자 경력, 자격, 부서 배치 후보를 관리합니다.", "#9333EA"],
  ["workflow", "전자결재", "Workflow", "기안, 결재 대기, 진행 문서, 회람 상태를 추적합니다.", "#2563EB"],
  ["archive", "자료함", "Archive", "법인, 사업장, 월별 산출 자료와 보고서를 찾고 미리 봅니다.", "#475569"],
  ["ai", "AI", "Assistant", "업무 문맥을 기반으로 요약, 초안, 확인 질문을 도와줍니다.", "#7C3AED"],
  ["admin", "관리자", "Admin", "법인, 사용자 권한, 조직과 운영 설정을 관리합니다.", "#B45309"],
  ["settings", "설정", "Settings", "개인 화면, 급여 운영 기준, 플랫폼 환경을 조정합니다.", "#0F766E"]
].map(([id, label, eyebrow, description, accent]) => ({ id, label, eyebrow, description, accent }));

const sidebarThemes = [
  ["steel", "스틸 블루", "현재 톤보다 선명한 업무형 파랑"],
  ["graphite", "그래파이트", "차분하고 밀도 있는 관리자형"],
  ["teal", "틸 그린", "신뢰감 있는 HR/운영형"],
  ["navy", "딥 네이비", "가장 강한 기업용 대비"]
].map(([id, label, description]) => ({ id, label, description }));

const languageOptions = [
  ["ko", "한국어", "현재 적용"],
  ["en", "English", "준비"],
  ["zh", "中文", "준비"]
];

const state = {
  activeId: "home",
  authed: false,
  companyCode: "",
  filter: "전체",
  loginFeedback: "",
  password: "",
  selectedPayrollCardKey: "",
  selectedPayrollStepKey: "",
  selectedQueueKey: "",
  selectedLanguage: "ko",
  search: "",
  selectedRowKey: "",
  sidebarTheme: "steel",
  userId: ""
};

const platformMetrics = [
  ["오늘 처리할 업무", "9건", "급여, 결재, 자료 확인 포함", "attention"],
  ["연동 준비 완료", "5개", "연동 준비 항목 포함", "ready"],
  ["확인 필요", "2건", "권한 또는 정책 확인 대기", "blocked"],
  ["최근 자료", "12개", "월별 보고서와 업로드 문서", "neutral"]
];

const readinessCards = [
  ["근로자 명부", "연동 대기", "최근 명부 기준과 급여 대상자 상태를 확인하세요.", "attention"],
  ["운영 기준", "기준 검토", "지급일, 입력 방식, 근태 반올림 기준을 확인합니다.", "neutral"],
  ["월별 산출", "자료함 준비", "최근 처리 월과 보고서 보관 상태를 확인합니다.", "ready"],
  ["자료 연동", "확인 필요", "외부 자료 연동 전 입력 누락 여부를 확인합니다.", "attention"]
];

const payrollSteps = [
  ["01", "운영 기준 확인", "지급일, 보험/세액 기준, 급여 항목 매핑을 검토합니다.", "먼저 확인", "attention"],
  ["02", "입력 자료 준비", "명부, 근태, 수당/공제 입력 파일을 업로드할 자리입니다.", "대기", "neutral"],
  ["03", "결과 미리보기", "산출 결과, 오류, 변경 이력을 한 화면에서 비교합니다.", "준비됨", "ready"],
  ["04", "자료함 저장", "월별 산출물과 보고서를 저장하고 추후 조회합니다.", "연결 예정", "neutral"]
];

const workQueue = [
  ["6월 급여 산출 준비", "급여 자동화", "급여 담당", "오늘", "확인 필요", "attention"],
  ["전자결재 대기 문서", "워크플로우", "승인권자", "D-1", "3건", "neutral"],
  ["자료함 최근 보고서", "아카이브", "운영팀", "상시", "미리보기 가능", "ready"]
];

const calendarEvents = [
  ["2026.06.04", "10:00", "급여 산출 기준 확인", "attention"],
  ["2026.06.04", "14:00", "전자결재 대기 문서 검토", "neutral"],
  ["2026.06.05", "09:30", "채용 후보자 부서 배치 회의", "ready"]
];

const todayTodos = [
  ["6월 급여 산출 준비", "급여 담당", "오늘", "attention", false],
  ["전자결재 대기 문서", "승인권자", "오늘", "neutral", false],
  ["자료함 최근 보고서 확인", "운영팀", "완료", "ready", true]
];

const payrollSettingsRows = [
  ["설정 대상", "법인 기본", "급여 담당", "사업장별 예외 여부 확인", "neutral"],
  ["휴업수당 지급률", "법정 기준 확인", "급여 담당", "최저 기준 이상 입력값 검토", "attention"],
  ["월 기본근로시간", "209시간", "운영 관리자", "사업장별 고정/대체 방식 표시", "ready"]
];

const previewRows = [
  ["Excel 미리보기", "시트 선택", "자료함", "표/텍스트 보기 전환", "ready"],
  ["필터 초기화", "지원", "사용자", "필터 적용 상태 안내", "neutral"],
  ["수정본 업로드", "권한 필요", "급여 담당", "현재 scope 파일일 때만 노출", "attention"]
];

const dashboards = {
  hr: dashboard("HR 운영 현황", "직원 명부, 이력서, 사직서, 재직/경력증명서 요청을 한 화면에서 추적합니다.", ["전체", "직원명부", "이력서", "사직서", "증명서"], [
    ["재직 직원", "48명", "법인 전체", "ready"],
    ["근태 확인", "6건", "월말 마감 전 확인", "attention"],
    ["증명서 요청", "2건", "담당자 처리 대기", "neutral"]
  ], [
    ["직원명부 업데이트", "확인 필요", "인사 담당", "부서/직무 최신 정보 확인", "attention"],
    ["재직증명서/경력증명서", "접수", "운영팀", "발급 양식 검토", "neutral"],
    ["이력서/사직서 관리", "정리 중", "인사 담당", "입사/퇴사 문서 분류", "ready"]
  ]),
  recruit: dashboard("채용 인재 관리", "지원자 경력과 자격 정보를 공유하고 부서별 필요 인재를 배치합니다.", ["전체", "지원자", "경력", "자격", "배치"], [
    ["지원자", "8명", "공유 가능 후보", "ready"],
    ["자격 검토", "3건", "부서 확인 대기", "attention"],
    ["배치 후보", "4명", "직무 적합 후보", "neutral"]
  ], [
    ["지원자 경력 공유", "검토 중", "채용 담당", "부서장 열람 권한 확인", "attention"],
    ["자격사항 매칭", "추천", "운영팀", "필요 부서 후보 배치", "ready"]
  ]),
  workflow: dashboard("전자결재 업무함", "기안, 승인, 반려, 회람 문서를 상태별로 정리합니다.", ["전체", "결재 대기", "진행 중", "반려"], [
    ["결재 대기", "3건", "오늘 처리 권장", "attention"],
    ["임시저장", "1건", "기안자 작성 중", "neutral"],
    ["완료 문서", "18건", "이번 달 기준", "ready"]
  ], [
    ["급여 지급 품의", "결재 대기", "대표 승인", "금액 요약 확인", "attention"],
    ["계약서 검토", "진행 중", "법무 담당", "첨부 파일 회람", "neutral"]
  ]),
  archive: dashboard("자료함", "월별 급여 산출물, 보고서, 업로드 문서를 안전하게 찾습니다.", ["전체", "급여", "계약", "보고서"], [
    ["최근 보고서", "12개", "3개월 내 생성", "ready"],
    ["정리 필요", "4개", "분류 대기", "attention"],
    ["공유 링크", "0개", "외부 공유 없음", "ready"]
  ], [
    ["2026년 5월 급여 보고서", "보관됨", "급여 담당", "미리보기", "ready"],
    ["근태 원본 파일", "분류 대기", "운영팀", "폴더 지정", "attention"]
  ]),
  ai: dashboard("AI 업무 지원", "급여/HR/결재 문맥을 읽고 요약과 검토 질문을 준비합니다.", ["전체", "요약", "초안", "검토"], [
    ["추천 작업", "5개", "현재 화면 기준", "ready"],
    ["검토 대기", "2건", "사람 확인 필요", "attention"],
    ["정책 문맥", "확인 전", "업무 기준 확인 후 사용", "neutral"]
  ], [
    ["급여 오류 요약", "추천", "AI", "오류 행 설명 생성", "ready"],
    ["결재 의견 초안", "검토 필요", "사용자", "문서 맥락 확인", "attention"]
  ]),
  admin: dashboard("관리자 콘솔", "사용자, 권한, 법인 운영 설정을 분리해서 관리합니다.", ["전체", "권한", "법인", "감사"], [
    ["활성 사용자", "14명", "초대 완료 계정", "ready"],
    ["권한 검토", "2건", "승인권자 확인", "attention"],
    ["감사 로그", "정상", "최근 오류 없음", "ready"]
  ], [
    ["신규 사용자 초대", "검토 중", "관리자", "역할 지정", "attention"],
    ["법인 정보", "정상", "운영 관리자", "정기 검토", "ready"]
  ]),
  settings: dashboard("설정", "개인 화면, 급여 운영 기준, 알림, 접근 환경을 정리합니다.", ["전체", "개인", "급여", "알림"], [
    ["프로필", "완료", "기본 정보 설정됨", "ready"],
    ["급여 기준", "확인 필요", "지급일/반올림 기준", "attention"],
    ["알림", "4개", "업무별 수신 설정", "neutral"]
  ], [
    ["급여 운영 기준", "확인 필요", "급여 담당", "지급일과 반올림 기준 확인", "attention"],
    ["화면 밀도", "권장", "개인", "업무형 레이아웃 유지", "ready"]
  ])
};

function dashboard(title, subtitle, filters, metrics, rows) {
  return { title, subtitle, filters, metrics, rows };
}

function html(strings, ...values) {
  return strings.reduce((out, str, i) => out + str + (values[i] ?? ""), "");
}

function escapeText(value) {
  return String(value).replace(/[&<>"']/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[m]);
}

function badge(text, tone = "neutral") {
  return `<span class="badge ${tones[tone]}">${escapeText(text)}</span>`;
}

function button(label, target, variant = "secondary") {
  return `<button class="btn ${variant}" data-target="${target}">${escapeText(label)}</button>`;
}

function render() {
  document.getElementById("app").innerHTML = state.authed ? renderShell() : renderLogin();
  bindEvents();
}

function renderLogin() {
  return html`
    <section class="login-page">
      <div class="login-grid">
        <div class="login-hero">
          ${badge("B2B operations", "ready")}
          <div class="hero-copy">
            <div class="brand">Bitween</div>
            <h1 class="hero-title">로그인 후 권한에 맞는 업무 화면으로 이동합니다.</h1>
            <p class="hero-desc">급여, HR, 전자결재, 자료함, AI, 관리자 화면을 하나의 업무 플랫폼 경험으로 정리합니다.</p>
          </div>
          <div class="hero-pills">
            <span class="hero-pill">권한 기반 메뉴</span>
            <span class="hero-pill">업무별 상태</span>
            <span class="hero-pill">자료 보호</span>
          </div>
        </div>
        <form class="card login-card" id="login-form">
          ${sectionHead("Secure sign in", "로그인", "법인 계정으로 접속하면 권한에 맞는 업무 화면으로 이동합니다.")}
          ${field("법인 코드", "company-code", "0000", "text", state.companyCode)}
          ${field("아이디", "user-id", "admin", "text", state.userId)}
          ${field("비밀번호", "password", "admin", "password", state.password)}
          ${state.loginFeedback ? `<div class="inline-warning">${badge("확인 필요", "attention")}<span>${state.loginFeedback}</span></div>` : ""}
          <div class="login-actions">
            <button class="btn primary" type="submit">플랫폼 홈으로 이동</button>
            <button class="btn secondary" type="button" data-demo-login="true">Demo 계정으로 접속</button>
          </div>
          <div class="notice">${badge("Demo 계정", "neutral")}<span class="helper">법인코드 0000 · 아이디 admin · 비밀번호 admin</span></div>
        </form>
      </div>
    </section>
  `;
}

function field(label, id, placeholder, type = "text", value = "") {
  return `<label class="field" for="${id}"><span>${label}</span><input id="${id}" type="${type}" value="${escapeText(value)}" placeholder="${placeholder}" /></label>`;
}

function renderShell() {
  const active = navItems.find((item) => item.id === state.activeId) || navItems[0];
  return html`
    <section class="shell sidebar-theme-${state.sidebarTheme}">
      <aside class="sidebar">
        <div class="brand-block">
          <img class="company-logo" src="${companyLogoUri}" alt="Bitween 회사 로고" />
          <div><strong>Bitween</strong><span>업무 플랫폼</span></div>
        </div>
        <div class="sidebar-options" aria-label="sidebar color options">
          <span class="sidebar-options-title">메뉴 색상 옵션</span>
          <div class="sidebar-theme-grid">
            ${sidebarThemes.map((theme) => `
              <button class="sidebar-theme-chip ${state.sidebarTheme === theme.id ? "active" : ""}" data-sidebar-theme="${theme.id}" title="${theme.description}">
                <span class="sidebar-swatch sidebar-swatch-${theme.id}"></span>
                <strong>${theme.label}</strong>
              </button>
            `).join("")}
          </div>
        </div>
        <nav class="nav" aria-label="platform menu">
            ${navItems.map((item) => `
            <button class="nav-button ${item.id === active.id ? "active" : ""}" data-target="${item.id}" style="${item.id === active.id ? `border-left-color:${item.accent}` : ""}">
              <strong>${item.label}</strong>
            </button>
          `).join("")}
        </nav>
      </aside>
      <div class="main">
        <header class="topbar">
          <div class="topbar-copy">
            <h1>${active.label}</h1>
          </div>
          <div class="top-actions">
            ${badge(sessionLabel, "neutral")}
            ${badge(`사번 ${employeeNumber}`, "neutral")}
            <button class="btn ghost compact-btn" data-logout="true">로그아웃</button>
          </div>
        </header>
        <div class="content">${renderScreen(active.id)}</div>
      </div>
    </section>
    <div class="toast" id="toast">화면이 업데이트되었습니다.</div>
  `;
}

function renderScreen(id) {
  if (id === "home") return renderHome();
  if (id === "payroll") return renderPayroll();
  return renderModule(id);
}

function renderHome() {
  const selectedQueue = selectedQueueItem();

  return html`
    <section class="card">
      ${sectionHead("", "오늘의 플랫폼 상태", "중요한 업무 상태를 먼저 보고 필요한 메뉴로 바로 이동합니다.", button("급여 준비 확인", "payroll", "secondary"))}
      ${metrics(platformMetrics)}
    </section>
    <section class="planner-grid">
      <div class="card planner-card">
        ${sectionHead("", "오늘 일정", "2026년 6월 4일 기준 주요 일정을 확인합니다.")}
        <div class="calendar-day"><span>2026.06</span><strong>04</strong><em>목요일</em></div>
        <div class="planner-list">${calendarEvents.map(([date, time, title, tone]) => `
          <div class="planner-item">${badge(time, tone)}<div><strong>${title}</strong><span class="helper">${date}</span></div></div>
        `).join("")}</div>
      </div>
      <div class="card planner-card">
        ${sectionHead("", "To-do list", "오늘 업무는 계속 표시하고 실행한 항목은 흐리게 표시합니다.")}
        <div class="planner-list">${todayTodos.map(([title, owner, time, tone, done]) => `
          <div class="planner-item todo-item ${done ? "done" : ""}">${badge(time, tone)}<div><strong>${title}</strong><span class="helper">${owner}</span></div></div>
        `).join("")}</div>
      </div>
    </section>
    <section class="card">
      ${sectionHead("", "오늘의 업무", "처리 우선순위가 높은 업무를 카드로 정리합니다.")}
      <div class="queue-grid">${workQueue.map(([title, meta, owner, due, status, tone]) => `
        <button class="queue-card select-card ${state.selectedQueueKey === queueKey([title, meta, owner, due, status, tone]) ? "selected" : ""}" data-queue-key="${escapeText(queueKey([title, meta, owner, due, status, tone]))}">
          <div class="queue-head">${badge(status, tone)}<span class="helper">${due}</span></div>
          <strong>${title}</strong>
          <span class="helper">${meta} · ${owner}</span>
        </button>
      `).join("")}</div>
      ${selectedQueue ? queueDetail(selectedQueue) : ""}
    </section>
    <section class="card">
      ${sectionHead("", "플랫폼 바로가기", "업무별 화면이 같은 구조로 이어지도록 정리했습니다.")}
      <div class="launcher-grid">${navItems.filter((item) => item.id !== "home").map((item) => `
        <article class="launcher-card" style="border-top-color:${item.accent}">
          <span class="eyebrow">${item.eyebrow}</span>
          <strong>${item.label}</strong>
          <span class="helper">${item.description}</span>
          ${button("열기", item.id, "ghost")}
        </article>
      `).join("")}</div>
    </section>
  `;
}

function queueKey(row) {
  return row.slice(0, 3).join("|");
}

function selectedQueueItem() {
  return workQueue.find((row) => queueKey(row) === state.selectedQueueKey) || workQueue[0];
}

function queueDetail([title, meta, owner, due, status, tone]) {
  return `<div class="detail-panel">
    <div class="detail-head"><div><span class="helper">선택한 오늘의 업무</span><strong>${escapeText(title)}</strong></div>${badge(status, tone)}</div>
    <div class="detail-grid">
      <div class="detail-item"><span class="helper">담당</span><strong>${escapeText(owner)}</strong></div>
      <div class="detail-item"><span class="helper">기한</span><strong>${escapeText(due)}</strong></div>
      <div class="detail-item"><span class="helper">업무 영역</span><span>${escapeText(meta)}</span></div>
    </div>
    <div class="action-row">${button("관련 화면 열기", queueTarget(meta), "secondary")}${button("담당 흐름 확인", state.activeId, "ghost")}</div>
  </div>`;
}

function queueTarget(meta) {
  if (meta.includes("급여")) return "payroll";
  if (meta.includes("워크") || meta.includes("결재")) return "workflow";
  if (meta.includes("아카이브") || meta.includes("자료")) return "archive";
  return "home";
}

function renderPayroll() {
  const selectedReadiness = selectedPayrollReadiness();
  const selectedStep = selectedPayrollStep();
  return html`
    <section class="card">
      ${sectionHead("Readiness", "급여 자동화 준비 현황", "산출 전 필요한 기준과 자료 상태를 먼저 확인합니다.", button("설정 확인", "settings", "secondary"))}
      <div class="card-grid">${readinessCards.map(([title, value, detail, tone]) => `
        <button class="mini-card readiness-card select-card ${state.selectedPayrollCardKey === payrollCardKey([title, value, detail, tone]) ? "selected" : ""}" data-payroll-card-key="${escapeText(payrollCardKey([title, value, detail, tone]))}" style="border-top-color:${toneColor(tone)}">
          <span class="helper">${title}</span>
          <strong class="metric-value" style="color:${toneColor(tone)}">${value}</strong>
          <span>${detail}</span>
        </button>
      `).join("")}</div>
      ${selectedReadiness ? payrollReadinessDetail(selectedReadiness) : ""}
    </section>
    <section class="card">
      ${sectionHead("Payroll flow", "급여 산출 작업 흐름", "운영 기준 확인부터 입력 자료 준비, 결과 검토, 자료함 저장까지 순서대로 진행합니다.", button("급여 설정 확인", "settings", "secondary"))}
      <div class="step-grid">${payrollSteps.map(([index, title, detail, status, tone]) => `
        <button class="step-card select-card ${state.selectedPayrollStepKey === payrollStepKey([index, title, detail, status, tone]) ? "selected" : ""}" data-payroll-step-key="${escapeText(payrollStepKey([index, title, detail, status, tone]))}" style="border-top-color:${toneColor(tone)}">
          <span class="eyebrow">${index}</span>
          ${badge(status, tone)}
          <strong>${title}</strong>
          <span class="helper">${detail}</span>
        </button>
      `).join("")}</div>
      ${selectedStep ? payrollStepDetail(selectedStep) : ""}
      <div class="action-row">${button("산출 화면 유지", "payroll", "primary")}${button("월별 자료함", "archive")}${button("AI 검토 준비", "ai", "ghost")}</div>
    </section>
    <section class="card">
      ${sectionHead("Settings summary", "급여 산출 설정 요약", "산출 전 확인해야 할 핵심 급여 기준을 한눈에 검토합니다.", button("상세 설정", "settings", "secondary"))}
      ${table(payrollSettingsRows)}
    </section>
    <section class="card">
      ${sectionHead("Preview and archive", "파일 미리보기 작업", "Excel 미리보기, 시트 선택, 필터 초기화, 수정본 업로드 같은 사용자 흐름을 분리했습니다.", button("자료함 열기", "archive", "secondary"))}
      ${table(previewRows)}
    </section>
  `;
}

function payrollCardKey(row) {
  return row.slice(0, 2).join("|");
}

function payrollStepKey(row) {
  return row.slice(0, 2).join("|");
}

function selectedPayrollReadiness() {
  return readinessCards.find((row) => payrollCardKey(row) === state.selectedPayrollCardKey) || readinessCards[0];
}

function selectedPayrollStep() {
  return payrollSteps.find((row) => payrollStepKey(row) === state.selectedPayrollStepKey) || payrollSteps[0];
}

function payrollReadinessDetail([title, value, detail, tone]) {
  return `<div class="detail-panel">
    <div class="detail-head"><div><span class="helper">선택한 준비 항목</span><strong>${escapeText(title)}</strong></div>${badge(value, tone)}</div>
    <span>${escapeText(detail)}</span>
    <div class="action-row">${button("준비 상태 확인", "payroll", "secondary")}${button("관련 자료 보기", "archive", "ghost")}</div>
  </div>`;
}

function payrollStepDetail([, title, detail, status, tone]) {
  return `<div class="detail-panel">
    <div class="detail-head"><div><span class="helper">선택한 산출 단계</span><strong>${escapeText(title)}</strong></div>${badge(status, tone)}</div>
    <span>${escapeText(detail)}</span>
    <div class="action-row">${button("단계 작업 보기", "payroll", "secondary")}${button("도움말 확인", "ai", "ghost")}</div>
  </div>`;
}

function renderModule(id) {
  const data = dashboards[id];
  if (!data) return empty("화면을 준비하고 있습니다.", "선택한 메뉴는 전용 화면으로 이동됩니다.");
  const rows = filterRows(data.rows);
  const selectedRow = selectedWorkRow(rows);
  return html`
    <section class="card">
      ${sectionHead("", data.title, "", button(primaryLabel(id), id, "primary"))}
      ${metrics(data.metrics)}
    </section>
    ${id === "settings" ? i18nSettingsPanel() : ""}
    <section class="card">
      ${sectionHead("", "업무 목록", "필터로 상태를 좁히고 필요한 다음 작업을 확인합니다.", button(secondaryLabel(id), secondaryTarget(id), "secondary"))}
      <div class="list-toolbar">
        <div class="filters">${data.filters.map((filter) => `<button class="filter-chip ${state.filter === filter ? "active" : ""}" data-filter="${filter}">${filter}</button>`).join("")}</div>
        <label class="search-box" for="work-search"><span>검색</span><input id="work-search" type="search" value="${escapeText(state.search)}" placeholder="업무, 상태, 담당자 검색" /></label>
      </div>
      <div class="list-summary"><strong>${rows.length}건</strong><span class="helper">${state.filter} 필터${state.search ? ` · "${escapeText(state.search)}" 검색` : ""}</span></div>
      ${table(rows, true)}
      ${selectedRow ? workDetail(selectedRow) : ""}
    </section>
    <div class="action-panels">
      <section class="card"><strong>${primaryLabel(id)}</strong><span class="helper">주요 업무 화면으로 이동합니다.</span>${button("이동", id, "ghost")}</section>
      <section class="card"><strong>${secondaryLabel(id)}</strong><span class="helper">연관 업무 화면을 이어서 확인합니다.</span>${button("이동", secondaryTarget(id), "ghost")}</section>
    </div>
  `;
}

function sectionHead(eyebrow, title, desc, action = "") {
  return `<div class="section-head"><div class="section-title">${eyebrow ? `<span class="eyebrow">${eyebrow}</span>` : ""}<h2>${title}</h2>${desc ? `<p>${desc}</p>` : ""}</div>${action}</div>`;
}

function i18nSettingsPanel() {
  return `<section class="card">
    ${sectionHead("", "국제화 설정", "한국어, 영어, 중국어 화면 전환을 준비합니다.")}
    <div class="language-grid">${languageOptions.map(([code, label, status]) => `
      <button class="language-option ${state.selectedLanguage === code ? "selected" : ""}" data-language="${code}">
        <strong>${label}</strong><span class="helper">${state.selectedLanguage === code ? "선택됨" : status}</span>
      </button>
    `).join("")}</div>
  </section>`;
}

function metrics(items) {
  return `<div class="metric-grid">${items.map(([label, value, helper, tone]) => `
    <article class="metric-card" style="border-left-color:${toneColor(tone)}">
      <span class="helper">${label}</span>
      <strong class="metric-value" style="color:${toneColor(tone)}">${value}</strong>
      <span>${helper}</span>
    </article>
  `).join("")}</div>`;
}

function table(rows, selectable = false) {
  if (!rows.length) return empty("표시할 항목이 없습니다.", "처리할 업무가 생기면 목록이 자동으로 채워집니다.");
  return `<div class="table">
    <div class="table-row header"><span>구분</span><span>상태</span><span>담당</span><span>다음 작업</span></div>
    ${rows.map(([category, status, owner, next, tone]) => {
      const key = rowKey([category, status, owner, next, tone]);
      const content = `<span><strong>${category}</strong></span><span>${badge(status, tone)}</span><span>${owner}</span><span>${next}</span>`;
      return selectable ? `
      <button class="table-row row-button ${state.selectedRowKey === key ? "selected" : ""}" data-row-key="${escapeText(key)}">
        ${content}
      </button>
    ` : `
      <div class="table-row">
        <span><strong>${category}</strong></span><span>${badge(status, tone)}</span><span>${owner}</span><span>${next}</span>
      </div>
    `;
    }).join("")}
  </div>`;
}

function rowKey(row) {
  return row.slice(0, 4).join("|");
}

function selectedWorkRow(rows) {
  if (!rows.length) return undefined;
  return rows.find((row) => rowKey(row) === state.selectedRowKey) || rows[0];
}

function workDetail([category, status, owner, next, tone]) {
  return `<div class="detail-panel">
    <div class="detail-head"><div><span class="helper">선택한 업무</span><strong>${escapeText(category)}</strong></div>${badge(status, tone)}</div>
    <div class="detail-grid">
      <div class="detail-item"><span class="helper">담당</span><strong>${escapeText(owner)}</strong></div>
      <div class="detail-item"><span class="helper">다음 작업</span><span>${escapeText(next)}</span></div>
    </div>
    <div class="action-row">${button("관련 화면 열기", workRowTarget([category, status, owner, next, tone]), "secondary")}${button("담당자 확인", state.activeId, "ghost")}</div>
  </div>`;
}

function workRowTarget(row) {
  const haystack = row.slice(0, 4).join(" ");
  if (haystack.includes("급여") || haystack.includes("산출") || haystack.includes("월 기본근로시간")) return "payroll";
  if (haystack.includes("결재") || haystack.includes("회람") || haystack.includes("기안")) return "workflow";
  if (haystack.includes("자료") || haystack.includes("보고서") || haystack.includes("파일") || haystack.includes("폴더")) return "archive";
  if (haystack.includes("권한") || haystack.includes("사용자") || haystack.includes("역할") || haystack.includes("법인")) return "admin";
  if (haystack.includes("채용") || haystack.includes("지원자") || haystack.includes("자격") || haystack.includes("배치")) return "recruit";
  if (haystack.includes("설정") || haystack.includes("알림") || haystack.includes("환경")) return "settings";
  if (haystack.includes("AI") || haystack.includes("요약") || haystack.includes("초안")) return "ai";
  if (haystack.includes("근태") || haystack.includes("증명서") || haystack.includes("직원")) return "hr";
  return "home";
}

function filterRows(rows) {
  const query = state.search.trim().toLowerCase();
  return rows.filter((row) => {
    const haystack = row.join(" ").toLowerCase();
    const filterMatch = state.filter === "전체" || haystack.includes(state.filter.toLowerCase());
    const queryMatch = !query || haystack.includes(query);
    return filterMatch && queryMatch;
  });
}

function empty(title, desc) {
  return `<div class="empty"><strong>${title}</strong><span class="helper">${desc}</span></div>`;
}

function toneColor(tone) {
  return {
    ready: "#047857",
    attention: "#B45309",
    blocked: "#B91C1C",
    neutral: "#667085"
  }[tone] || "#667085";
}

function primaryLabel(id) {
  return ({
    hr: "직원 명부 보기",
    recruit: "지원자 보기",
    workflow: "결재함 열기",
    archive: "최근 자료 보기",
    ai: "추천 작업 보기",
    admin: "권한 검토",
    settings: "급여 설정 보기"
  })[id] || "열기";
}

function secondaryLabel(id) {
  return ({
    hr: "급여 준비로 이동",
    recruit: "HR로 이동",
    workflow: "자료함 확인",
    archive: "급여 화면으로 이동",
    ai: "설정 확인",
    admin: "설정으로 이동",
    settings: "급여 화면으로 이동"
  })[id] || "연관 화면";
}

function secondaryTarget(id) {
  return ({
    hr: "payroll",
    recruit: "hr",
    workflow: "archive",
    archive: "payroll",
    ai: "settings",
    admin: "settings",
    settings: "payroll"
  })[id] || "home";
}

function bindEvents() {
  document.querySelectorAll("[data-target]").forEach((el) => {
    el.addEventListener("click", () => {
      state.authed = true;
      state.activeId = el.dataset.target;
      state.filter = "전체";
      state.search = "";
      state.selectedRowKey = "";
      state.selectedPayrollCardKey = "";
      state.selectedPayrollStepKey = "";
      state.selectedQueueKey = "";
      state.loginFeedback = "";
      render();
      toast(`"${navItems.find((item) => item.id === state.activeId)?.label || "화면"}" 화면으로 이동했습니다.`);
    });
  });

  document.querySelectorAll("[data-filter]").forEach((el) => {
    el.addEventListener("click", () => {
      state.filter = el.dataset.filter;
      state.selectedRowKey = "";
      render();
      toast(`${state.filter} 필터가 선택되었습니다.`);
    });
  });

  document.querySelectorAll("[data-row-key]").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedRowKey = el.dataset.rowKey;
      render();
      toast("업무 상세를 열었습니다.");
    });
  });

  document.querySelectorAll("[data-sidebar-theme]").forEach((el) => {
    el.addEventListener("click", () => {
      state.sidebarTheme = el.dataset.sidebarTheme || "steel";
      render();
      toast("사이드 메뉴 색상 옵션을 적용했습니다.");
    });
  });

  document.querySelectorAll("[data-language]").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedLanguage = el.dataset.language || "ko";
      render();
      toast("국제화 설정을 선택했습니다.");
    });
  });

  document.querySelectorAll("[data-payroll-card-key]").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedPayrollCardKey = el.dataset.payrollCardKey;
      render();
      toast("급여 준비 항목을 선택했습니다.");
    });
  });

  document.querySelectorAll("[data-payroll-step-key]").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedPayrollStepKey = el.dataset.payrollStepKey;
      render();
      toast("급여 산출 단계를 선택했습니다.");
    });
  });

  document.querySelectorAll("[data-queue-key]").forEach((el) => {
    el.addEventListener("click", () => {
      state.selectedQueueKey = el.dataset.queueKey;
      render();
      toast("오늘의 업무 상세를 열었습니다.");
    });
  });

  document.querySelectorAll("[data-logout]").forEach((el) => {
    el.addEventListener("click", () => {
      state.authed = false;
      state.activeId = "home";
      state.filter = "전체";
      state.loginFeedback = "";
      state.password = "";
      state.selectedPayrollCardKey = "";
      state.selectedPayrollStepKey = "";
      state.selectedQueueKey = "";
      state.search = "";
      state.selectedRowKey = "";
      render();
      toast("로그아웃했습니다.");
    });
  });

  document.querySelectorAll("[data-demo-login]").forEach((el) => {
    el.addEventListener("click", () => {
      state.companyCode = demoAccount.companyCode;
      state.userId = demoAccount.userId;
      state.password = demoAccount.password;
      state.loginFeedback = "";
      state.authed = true;
      state.activeId = "home";
      state.filter = "전체";
      state.search = "";
      state.selectedPayrollCardKey = "";
      state.selectedPayrollStepKey = "";
      state.selectedQueueKey = "";
      state.selectedRowKey = "";
      render();
      toast("Demo 계정으로 접속했습니다.");
    });
  });

  const search = document.getElementById("work-search");
  if (search) {
    search.addEventListener("input", (event) => {
      const cursor = event.target.selectionStart;
      state.search = event.target.value;
      state.selectedRowKey = "";
      render();
      window.requestAnimationFrame(() => {
        const nextSearch = document.getElementById("work-search");
        if (nextSearch) {
          nextSearch.focus();
          nextSearch.setSelectionRange(cursor, cursor);
        }
      });
    });
  }

  const companyCode = document.getElementById("company-code");
  if (companyCode) {
    companyCode.addEventListener("input", (event) => {
      state.companyCode = event.target.value;
    });
  }

  const userId = document.getElementById("user-id");
  if (userId) {
    userId.addEventListener("input", (event) => {
      state.userId = event.target.value;
    });
  }

  const password = document.getElementById("password");
  if (password) {
    password.addEventListener("input", (event) => {
      state.password = event.target.value;
    });
  }

  const form = document.getElementById("login-form");
  if (form) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      state.companyCode = document.getElementById("company-code")?.value.trim() || "";
      state.userId = document.getElementById("user-id")?.value.trim() || "";
      state.password = document.getElementById("password")?.value.trim() || "";
      if (!state.companyCode || !state.userId || !state.password) {
        state.loginFeedback = "demo 계정은 법인코드 0000, 아이디 admin, 비밀번호 admin입니다.";
        render();
        toast("로그인 정보를 확인하세요.");
        return;
      }
      if (
        state.companyCode !== demoAccount.companyCode ||
        state.userId !== demoAccount.userId ||
        state.password !== demoAccount.password
      ) {
        state.loginFeedback = "demo 계정 정보가 일치하지 않습니다. 법인코드 0000, 아이디 admin, 비밀번호 admin으로 입력하세요.";
        render();
        toast("demo 계정 정보를 확인하세요.");
        return;
      }
      state.loginFeedback = "";
      state.authed = true;
      state.activeId = "home";
      render();
      toast("플랫폼 홈으로 이동했습니다.");
    });
  }
}

function toast(text) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = text;
  el.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => el.classList.remove("show"), 1400);
}

if ("EventSource" in window) {
  const source = new EventSource("/events");
  source.addEventListener("reload", () => window.location.reload());
}

render();
