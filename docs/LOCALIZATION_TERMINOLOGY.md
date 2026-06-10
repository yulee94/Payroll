# Localization terminology and cultural context

Status: active UI language contract, 2026-06-09.

Bitween localization is product design, not direct string translation. Each
locale must read as one coherent business language for the operator using that
locale.

## Rules

- Do not hardcode visible UI copy in components, preview code, or backend
  payload adapters. Use stable i18n keys and catalog values.
- Korean (`ko-KR`) visible UI copy must be fully Korean except unavoidable
  product/tenant names such as `Bitween` and `Acme Corporation`.
- English (`en-US`) visible UI copy must be fully English and must not contain
  Korean fallback text.
- Chinese and Japanese values must not contain Korean fallback text.
- Avoid lazy loanwords and direct translation. Choose the term that fits the
  workflow, role, and Korean enterprise context.
- Culture context is part of correctness. Korean operator copy should use
  polite, workplace-natural phrasing, avoid exposing implementation vocabulary,
  and fit the reader's role: payroll operators see payroll work, HR operators see
  employee work, approvers see signing/decision work, and administrators see
  setup/security work.
- Technical implementation terms such as Rust, Buck2, PostgreSQL, RustFS,
  backend, schema, and source are not normal operator copy. Keep them in docs,
  verifiers, runbooks, or admin-only operational surfaces.

## Korean product glossary

| Product concept | Korean UI term | Rationale |
| --- | --- | --- |
| Workflow module / workflow canvas | 업무 관리 | The screen manages corporate work logic, handoffs, owners, and state. `워크플로` is a lazy loanword and is less natural for payroll/HR operators. |
| Workflow visualization / canvas | 업무 흐름도 | Use a Korean business term for the visual graph. Avoid `캔버스` in visible Korean copy unless it is part of a formal design-system term. |
| Workflow node | 단계 | Operators understand a business step; `노드` exposes implementation vocabulary. |
| Business logic | 업무 규칙 | Use the business rule being applied, not software logic terminology. |
| HR | 인사 | Korean payroll/SME operators expect 인사 for employee lifecycle work. |
| Payroll | 급여 | Payroll execution, close, and outputs are 급여 work. |
| Approval | 전자결재 | Signing and approvals are not generic workflow design. |
| Archive / 자료함 | 자료함 | This is the governed file/intake workbench. |
| Admin | 관리 | Use 관리 for tenant/security/setup surfaces. |
| Settings | 설정 | Use 설정 for profile, language, theme, workspace preferences. |
| AI assistance | 업무 지원 | Avoid exposing `AI` as a generic feature label; show the job it helps with. |
| Branch in tenant/legal-entity context | 법인 or 사업장 | Use 법인 for company/legal-entity account boundaries and 사업장 for workplace/site boundaries. |
| KPI | 성과 | Operator-facing performance/accountability language should be 성과. |
| EDI / insurance feed | 건강보험 확인 or 보험 신고 | Use the business task, not the acronym, unless an official form name requires it. |
| CSV / Excel / PDF | 표 파일 / 엑셀 / 문서 파일 | Prefer file-purpose terms in Korean operator copy. |
| GitHub / repository | 외부 저장소 | Nontechnical operators need the destination concept, not vendor/tool names. |
| Maintenance system identifier | 정비 시스템 | Hide internal system identifiers in normal UI. |
| To-do list | 할 일 목록 | Use natural work wording. |
| Dashboard | 현황 | Use the business status being shown instead of a generic dashboard label. |
| Profile | 내 정보 | Korean workplace software commonly treats account/profile as the user's own information surface. |
| Message | 쪽지 | Keep top-bar communication short and familiar without colliding with system alerts. |
| Session | 접속 | Use the user's access/login state rather than a technical session term. |
| Token / push / offline | 인증 확인 / 알림 / 연결 끊김 대응 | Use the security or device behavior the operator understands. |
| Source | 출처 | Use for file or integration origin; avoid technical source labels. |
| Runbook | 지원 절차 | Support operators need the procedure, not the English term. |
| Gate | 확인 단계 | Use where an enterprise control or maturity gate must be visible. |
| Platform | 업무 환경 | Use for the product shell/environment unless the formal product name requires otherwise. |
| Module | 업무 영역 | Use the business area, not a software module term. |
| Panel | 영역 | Use the visible work area or business purpose; avoid UI-construction jargon. |
| Card | 업무 항목 | Use when the UI element represents a piece of work. |
| Template | 양식 | Use for repeatable workflow or document shapes. |
| Tenant | 고객사 | Use for customer/company boundary in operator UI; keep `tenant_id` in APIs only. |
| Data | 자료 | Prefer 자료 in HR/payroll/archive screens; use 데이터 only inside engineering docs or formal data-platform contexts. |
| Archive as English/Korean loanword | 자료함 | Use the product surface name; avoid `아카이브` in operator copy. |
| Trigger | 시작점 | Use the business start condition. |
| Routing | 배정 or 인계 | Use 배정 for assignment and 인계 for handoff. |
| Preview | 확인 | Use the operator action rather than the technical preview mode. |
| Console | 관리 화면 | Use the screen purpose. |
| Filter | 조건 | Use for list narrowing in operator copy. |
| Upload | 올리기 | Use a plain action term. |
| Live | 실제 | Use actual/current state rather than a technical live-mode label. |

## Verification

`npm run verify:i18n` must fail when:

- localized glyphs appear outside `catalog.json`,
- a catalog row is missing a locale,
- Korean visible copy contains unapproved Latin tokens,
- Korean visible copy contains banned lazy workflow/direct-translation terms
  such as `워크플로`, `워크플로우`, `대시보드`, `세션`, `테넌트`,
  `플랫폼`, `데이터`, `아카이브`, `트리거`, `라우팅`, `프리뷰`,
  `콘솔`, `필터`, `업로드`, `미리보기`, or `라이브`,
- `navigation.workflow.label` or `navigation.workflow.eyebrow` regresses away
  from `업무 관리`,
- non-Korean locale values contain Korean fallback text.
