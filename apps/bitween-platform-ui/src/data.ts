import type { NavigationItem, ReadinessCard, WorkQueueItem } from "./types";

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

export const workQueue: readonly WorkQueueItem[] = [
  {
    title: "6월 급여 산출 준비",
    meta: "급여 · 자동화",
    status: "확인 필요",
    tone: "attention"
  },
  {
    title: "전자결재 대기 문서",
    meta: "워크플로우",
    status: "3건",
    tone: "neutral"
  },
  {
    title: "자료함 최근 보고서",
    meta: "아카이브",
    status: "미리보기 가능",
    tone: "ready"
  }
];
