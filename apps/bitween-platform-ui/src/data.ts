import type {
  MetricItem,
  ModuleDashboard,
  NavigationItem,
  PayrollStep,
  ReadinessCard,
  WorkQueueItem
} from "./types";

type NonEmptyNavigation = readonly [NavigationItem, ...NavigationItem[]];

export const navigationItems = [
  {
    id: "home",
    label: "플랫폼 홈",
    eyebrow: "Launcher",
    description: "오늘의 업무, 빠른 실행, 플랫폼 상태를 한 화면에서 확인합니다.",
    accent: "#64748B"
  },
  {
    id: "payroll",
    label: "급여",
    eyebrow: "Payroll",
    description: "급여 자동화 준비 상태, 산출 진입, 월별 보고와 설정을 관리합니다.",
    accent: "#1F3864"
  },
  {
    id: "hr",
    label: "HR",
    eyebrow: "People",
    description: "직원 명부, 근태, 연차, 계약, 증명서 흐름을 정리합니다.",
    accent: "#0D9488"
  },
  {
    id: "workflow",
    label: "전자결재",
    eyebrow: "Workflow",
    description: "기안, 결재 대기, 진행 문서, 회람 상태를 추적합니다.",
    accent: "#2563EB"
  },
  {
    id: "archive",
    label: "자료함",
    eyebrow: "Archive",
    description: "법인, 사업장, 월별 산출 자료와 보고서를 찾고 미리 봅니다.",
    accent: "#475569"
  },
  {
    id: "ai",
    label: "AI",
    eyebrow: "Assistant",
    description: "업무 문맥을 기반으로 요약, 초안, 확인 질문을 도와줍니다.",
    accent: "#7C3AED"
  },
  {
    id: "admin",
    label: "관리자",
    eyebrow: "Admin",
    description: "법인, 사용자 권한, 조직과 운영 설정을 관리합니다.",
    accent: "#B45309"
  },
  {
    id: "settings",
    label: "설정",
    eyebrow: "Settings",
    description: "개인 화면, 급여 운영 기준, 플랫폼 환경을 조정합니다.",
    accent: "#0F766E"
  }
] satisfies NonEmptyNavigation;

export const platformMetrics: readonly MetricItem[] = [
  {
    id: "today",
    label: "오늘 처리할 업무",
    value: "9건",
    helper: "급여, 결재, 자료 확인 포함",
    tone: "attention"
  },
  {
    id: "ready",
    label: "연동 준비 완료",
    value: "5개",
    helper: "읽기 전용 API 연결 후보",
    tone: "ready"
  },
  {
    id: "blocked",
    label: "확인 필요",
    value: "2건",
    helper: "권한 또는 정책 확인 대기",
    tone: "blocked"
  },
  {
    id: "docs",
    label: "최근 자료",
    value: "12개",
    helper: "월별 보고서와 업로드 문서",
    tone: "neutral"
  }
];

export const readinessCards: readonly ReadinessCard[] = [
  {
    id: "roster",
    title: "근로자 명부",
    value: "연동 대기",
    detail: "backend readiness snapshot 연결 전까지 mock 상태로 표시합니다.",
    tone: "attention"
  },
  {
    id: "policy",
    title: "운영 기준",
    value: "API 계약 확인",
    detail: "지급일, 입력 방식, 근태 반올림 기준을 표시할 슬롯입니다.",
    tone: "neutral"
  },
  {
    id: "outputs",
    title: "월별 산출",
    value: "자료함 준비",
    detail: "최근 처리 월, 보고서, 급여차이 파일 상태를 연결합니다.",
    tone: "ready"
  },
  {
    id: "api",
    title: "API-ready",
    value: "계약 대기",
    detail: "payroll API adapter 응답 shape가 확정되면 교체합니다.",
    tone: "attention"
  }
];

export const payrollSteps: readonly PayrollStep[] = [
  {
    id: "settings",
    title: "운영 기준 확인",
    detail: "지급일, 보험/세액 기준, 급여 항목 매핑을 검토합니다.",
    status: "먼저 확인",
    tone: "attention"
  },
  {
    id: "upload",
    title: "입력 자료 준비",
    detail: "명부, 근태, 수당/공제 입력 파일을 업로드할 자리입니다.",
    status: "대기",
    tone: "neutral"
  },
  {
    id: "preview",
    title: "결과 미리보기",
    detail: "산출 결과, 오류, 변경 이력을 한 화면에서 비교합니다.",
    status: "준비됨",
    tone: "ready"
  },
  {
    id: "archive",
    title: "자료함 저장",
    detail: "월별 산출물과 보고서를 저장하고 추후 조회합니다.",
    status: "연결 예정",
    tone: "neutral"
  }
];

export const workQueue: readonly WorkQueueItem[] = [
  {
    id: "payroll-june",
    title: "6월 급여 산출 준비",
    meta: "급여 자동화",
    owner: "급여 담당",
    due: "오늘",
    status: "확인 필요",
    tone: "attention"
  },
  {
    id: "approval-pending",
    title: "전자결재 대기 문서",
    meta: "워크플로우",
    owner: "승인권자",
    due: "D-1",
    status: "3건",
    tone: "neutral"
  },
  {
    id: "archive-preview",
    title: "자료함 최근 보고서",
    meta: "아카이브",
    owner: "운영팀",
    due: "상시",
    status: "미리보기 가능",
    tone: "ready"
  }
];

export const moduleDashboards = {
  hr: {
    id: "hr",
    title: "HR 운영 현황",
    subtitle: "직원 명부, 근태, 증명서 요청을 한 화면에서 추적합니다.",
    filters: ["전체", "입사/퇴사", "근태", "증명서"],
    metrics: [
      { id: "employees", label: "재직 직원", value: "48명", helper: "법인 전체", tone: "ready" },
      { id: "attendance", label: "근태 확인", value: "6건", helper: "월말 마감 전 확인", tone: "attention" },
      { id: "certs", label: "증명서 요청", value: "2건", helper: "담당자 처리 대기", tone: "neutral" }
    ],
    rows: [
      {
        id: "hr-1",
        category: "근태 누락",
        status: "확인 필요",
        owner: "인사 담당",
        nextStep: "6월 2주차 누락 항목 확인",
        tone: "attention"
      },
      {
        id: "hr-2",
        category: "재직증명서",
        status: "접수",
        owner: "운영팀",
        nextStep: "발급 양식 검토",
        tone: "neutral"
      }
    ],
    primaryAction: {
      label: "직원 명부 보기",
      description: "명부와 급여 연동 상태를 확인합니다.",
      target: "hr"
    },
    secondaryAction: {
      label: "급여 준비로 이동",
      description: "급여 자동화 readiness를 확인합니다.",
      target: "payroll"
    },
    emptyTitle: "표시할 HR 업무가 없습니다.",
    emptyDescription: "명부 또는 근태 API가 연결되면 처리 대기 항목이 표시됩니다."
  },
  workflow: {
    id: "workflow",
    title: "전자결재 업무함",
    subtitle: "기안, 승인, 반려, 회람 문서를 상태별로 정리합니다.",
    filters: ["전체", "결재 대기", "진행 중", "반려"],
    metrics: [
      { id: "pending", label: "결재 대기", value: "3건", helper: "오늘 처리 권장", tone: "attention" },
      { id: "drafts", label: "임시저장", value: "1건", helper: "기안자 작성 중", tone: "neutral" },
      { id: "done", label: "완료 문서", value: "18건", helper: "이번 달 기준", tone: "ready" }
    ],
    rows: [
      {
        id: "wf-1",
        category: "급여 지급 품의",
        status: "결재 대기",
        owner: "대표 승인",
        nextStep: "금액 요약 확인",
        tone: "attention"
      },
      {
        id: "wf-2",
        category: "계약서 검토",
        status: "진행 중",
        owner: "법무 담당",
        nextStep: "첨부 파일 회람",
        tone: "neutral"
      }
    ],
    primaryAction: {
      label: "결재함 열기",
      description: "대기 중인 결재 문서를 검토합니다.",
      target: "workflow"
    },
    secondaryAction: {
      label: "자료함 확인",
      description: "첨부와 산출물을 확인합니다.",
      target: "archive"
    },
    emptyTitle: "대기 중인 결재 문서가 없습니다.",
    emptyDescription: "결재 API 연결 후 개인 권한에 맞는 문서가 표시됩니다."
  },
  archive: {
    id: "archive",
    title: "자료함",
    subtitle: "월별 급여 산출물, 보고서, 업로드 문서를 안전하게 찾습니다.",
    filters: ["전체", "급여", "계약", "보고서"],
    metrics: [
      { id: "reports", label: "최근 보고서", value: "12개", helper: "3개월 내 생성", tone: "ready" },
      { id: "missing", label: "정리 필요", value: "4개", helper: "분류 대기", tone: "attention" },
      { id: "shared", label: "공유 링크", value: "0개", helper: "외부 공유 없음", tone: "ready" }
    ],
    rows: [
      {
        id: "ar-1",
        category: "2026년 5월 급여 보고서",
        status: "보관됨",
        owner: "급여 담당",
        nextStep: "미리보기",
        tone: "ready"
      },
      {
        id: "ar-2",
        category: "근태 원본 파일",
        status: "분류 대기",
        owner: "운영팀",
        nextStep: "폴더 지정",
        tone: "attention"
      }
    ],
    primaryAction: {
      label: "최근 자료 보기",
      description: "최근 생성 문서를 먼저 확인합니다.",
      target: "archive"
    },
    secondaryAction: {
      label: "급여 화면으로 이동",
      description: "산출 결과와 연결 상태를 확인합니다.",
      target: "payroll"
    },
    emptyTitle: "자료함에 표시할 문서가 없습니다.",
    emptyDescription: "월별 산출물 또는 업로드 파일이 생기면 이곳에 표시됩니다."
  },
  ai: {
    id: "ai",
    title: "AI 업무 지원",
    subtitle: "급여/HR/결재 문맥을 읽고 요약과 검토 질문을 준비합니다.",
    filters: ["전체", "요약", "초안", "검토"],
    metrics: [
      { id: "prompts", label: "추천 작업", value: "5개", helper: "현재 화면 기준", tone: "ready" },
      { id: "reviews", label: "검토 대기", value: "2건", helper: "사람 확인 필요", tone: "attention" },
      { id: "policy", label: "정책 문맥", value: "연결 전", helper: "backend contract 필요", tone: "neutral" }
    ],
    rows: [
      {
        id: "ai-1",
        category: "급여 오류 요약",
        status: "추천",
        owner: "AI",
        nextStep: "오류 행 설명 생성",
        tone: "ready"
      },
      {
        id: "ai-2",
        category: "결재 의견 초안",
        status: "검토 필요",
        owner: "사용자",
        nextStep: "문서 맥락 확인",
        tone: "attention"
      }
    ],
    primaryAction: {
      label: "추천 작업 보기",
      description: "현재 화면에 맞는 AI 작업을 확인합니다.",
      target: "ai"
    },
    secondaryAction: {
      label: "설정 확인",
      description: "AI 사용 범위와 표시 설정을 확인합니다.",
      target: "settings"
    },
    emptyTitle: "추천할 AI 작업이 없습니다.",
    emptyDescription: "업무 문맥 API가 연결되면 화면별 추천 작업이 표시됩니다."
  },
  admin: {
    id: "admin",
    title: "관리자 콘솔",
    subtitle: "사용자, 권한, 법인 운영 설정을 분리해서 관리합니다.",
    filters: ["전체", "권한", "법인", "감사"],
    metrics: [
      { id: "users", label: "활성 사용자", value: "14명", helper: "초대 완료 계정", tone: "ready" },
      { id: "roles", label: "권한 검토", value: "2건", helper: "승인권자 확인", tone: "attention" },
      { id: "audit", label: "감사 로그", value: "정상", helper: "최근 오류 없음", tone: "ready" }
    ],
    rows: [
      {
        id: "ad-1",
        category: "신규 사용자 초대",
        status: "검토 중",
        owner: "관리자",
        nextStep: "역할 지정",
        tone: "attention"
      },
      {
        id: "ad-2",
        category: "법인 정보",
        status: "정상",
        owner: "운영 관리자",
        nextStep: "정기 검토",
        tone: "ready"
      }
    ],
    primaryAction: {
      label: "권한 검토",
      description: "사용자 역할과 접근 범위를 확인합니다.",
      target: "admin"
    },
    secondaryAction: {
      label: "설정으로 이동",
      description: "운영 기준 화면을 확인합니다.",
      target: "settings"
    },
    emptyTitle: "관리자 알림이 없습니다.",
    emptyDescription: "권한 변경이나 운영 알림이 생기면 표시됩니다."
  },
  settings: {
    id: "settings",
    title: "설정",
    subtitle: "개인 화면, 급여 운영 기준, 알림, 접근 환경을 정리합니다.",
    filters: ["전체", "개인", "급여", "알림"],
    metrics: [
      { id: "profile", label: "프로필", value: "완료", helper: "기본 정보 설정됨", tone: "ready" },
      { id: "payroll", label: "급여 기준", value: "확인 필요", helper: "지급일/반올림 기준", tone: "attention" },
      { id: "notice", label: "알림", value: "4개", helper: "업무별 수신 설정", tone: "neutral" }
    ],
    rows: [
      {
        id: "st-1",
        category: "급여 운영 기준",
        status: "확인 필요",
        owner: "급여 담당",
        nextStep: "정책 스토어 연결 후 표시",
        tone: "attention"
      },
      {
        id: "st-2",
        category: "화면 밀도",
        status: "권장",
        owner: "개인",
        nextStep: "업무형 레이아웃 유지",
        tone: "ready"
      }
    ],
    primaryAction: {
      label: "급여 설정 보기",
      description: "운영 기준 연결 영역을 확인합니다.",
      target: "settings"
    },
    secondaryAction: {
      label: "급여 화면으로 이동",
      description: "준비 현황과 함께 검토합니다.",
      target: "payroll"
    },
    emptyTitle: "설정 알림이 없습니다.",
    emptyDescription: "사용자 또는 운영 기준 변경이 필요한 경우 표시됩니다."
  }
} satisfies Record<Exclude<NavigationItem["id"], "home" | "payroll">, ModuleDashboard>;
