# Frontend PR Merge Guide

작성일: 2026-06-04

이 문서는 Bitween frontend/UI PR을 메인 개발자가 승인할 때 충돌을 줄이기 위한 병합 가이드입니다. 모든 항목은 `apps/bitween-platform-ui` frontend 작업 기준이며, backend/payroll 계산, 서비스, 권한, 저장 로직은 병합 판단 범위에서 분리합니다.

## 현재 원칙

- `main`에는 직접 작업하지 않는다.
- frontend PR은 하나씩 검토하고, 병합 후 다음 PR을 최신 `main` 기준으로 다시 확인한다.
- Rust backend crates, frontend contract files, production `config`, template data, user data, output data, or workspace runtime data changes are reviewed as separate backend/platform work rather than as a frontend-only PR.
- PR 설명의 `Changed Screens`, `Tests`, `Backend Safety`, `Backend Requests`를 확인한 뒤 승인한다.

## 먼저 병합해도 되는 낮은 충돌 PR

다음 PR은 화면 코드와 직접 충돌이 적거나, 이후 검증 기준을 강화하는 성격이다.

| PR | 성격 | 권장 처리 |
| --- | --- | --- |
| #20 Add frontend UI review checklist | 문서 전용 | 먼저 병합 가능 |
| #19 Guard frontend strict TypeScript config | frontend tooling/docs | i18n/전환 PR보다 먼저 병합 권장 |

## 화면 개선 PR 묶음

다음 PR들은 React Native/Web 화면을 직접 바꾸므로 하나씩 병합하고 매번 preview를 확인한다.

| PR | 주요 화면 | 주요 파일 |
| --- | --- | --- |
| #13 Add settings workspace UI | 설정 | `src/screens.tsx`, `preview/app.js`, `preview/styles.css` |
| #14 Make home planner items actionable | 홈/런처 | `src/data.ts`, `src/screens.tsx`, `src/types.ts`, preview |
| #15 Use explicit module row action targets | 공통 업무 상세 이동 | `src/data.ts`, `src/screens.tsx`, `src/types.ts`, `preview/app.js` |
| #16 Improve filtered empty states | 공통 목록 빈 상태 | `src/screens.tsx`, preview |
| #18 Add status rails to work tables | 공통 테이블/카드 | `src/components.tsx`, preview |
| #22 Add frontend shell status footer | shell 하단 상태 영역 | `src/components.tsx`, `preview/app.js`, `preview/styles.css` |

권장 순서는 사용자 진입 흐름 기준으로 `#13 -> #14 -> #15 -> #16 -> #18 -> #22`이다. 단, PR #21을 먼저 병합한다면 위 PR들은 반드시 최신 `main`으로 rebase 또는 재검증이 필요하다.

## PR #21 처리 주의

PR #21은 i18n catalog, React Native 화면, static preview, 문서, 전환 계획을 한 번에 넓게 다룬다. 다음 파일들을 크게 수정하므로 개별 UI PR과 충돌 가능성이 높다.

- `apps/bitween-platform-ui/App.tsx`
- `apps/bitween-platform-ui/README.md`
- `apps/bitween-platform-ui/package.json`
- `apps/bitween-platform-ui/preview/app.js`
- `apps/bitween-platform-ui/preview/index.html`
- `apps/bitween-platform-ui/preview/server.js`
- `apps/bitween-platform-ui/src/components.tsx`
- `apps/bitween-platform-ui/src/data.ts`
- `apps/bitween-platform-ui/src/screens.tsx`
- `apps/bitween-platform-ui/src/theme.ts`
- `apps/bitween-platform-ui/src/types.ts`
- `apps/bitween-platform-ui/src/viewModel.ts`

PR #21을 먼저 병합할 경우:

- #13-#18, #22의 화면 변경은 최신 i18n catalog 구조에 맞춰 다시 적용한다.
- 화면 문구가 catalog 기반으로 이동했는지 확인한다.
- 언어별 route/action이 텍스트 추론에 의존하지 않는지 확인한다.
- `npm run verify:i18n`이 가능한 환경에서는 먼저 실행한다.

개별 UI PR을 먼저 병합할 경우:

- PR #21은 최신 `main` 기준으로 다시 충돌 확인한다.
- catalog 전환 중 이미 병합된 UI 문구가 누락되지 않았는지 비교한다.
- preview와 React Native 화면이 같은 화면 상태를 보여주는지 다시 확인한다.

## 병합 후 공통 검증

가능하면 각 PR 병합 후 다음을 확인한다.

- `git diff --check`
- `node --check apps/bitween-platform-ui/preview/app.js`
- `node --check apps/bitween-platform-ui/preview/server.js`
- `npm run verify:auth-routes --prefix apps/bitween-platform-ui`
- `npm run verify:signed-out-auth-ux --prefix apps/bitween-platform-ui`
- `npm run verify:data-mode --prefix apps/bitween-platform-ui`
- `npm run verify:i18n --prefix apps/bitween-platform-ui`
- `npm run typecheck --prefix apps/bitween-platform-ui`는 `npm`과 `node_modules`가 있는 환경에서 실행
- `npm audit --omit=dev --audit-level=moderate --prefix apps/bitween-platform-ui`
- `npm run live` 실행 후 `/api/platform/v1/view-model`이 `backend: rust_native`를 반환하는지 확인
- Rust live operations shell, 로그인/가입/온보딩 경로 상태, 홈/런처, 사이드 메뉴 이동, HR, 급여, workflow, 전자결재, 자료함, admin 화면의 버튼/탭/스크롤 확인

## Backend 요청 분리

frontend PR에서 backend 데이터가 부족한 경우 코드로 우회하지 않는다. 다음 항목은 PR 설명의 `Backend Requests`에만 남긴다.

- 실제 급여 산출/세금/공제 계산
- 건강보험EDI 연결 및 공제금액 갱신
- 실제 출퇴근 저장, GPS 정책, 관리자 승인 이력
- Branch/sub-account 생성, RBAC/ABAC 권한 저장
- 자료함 문서 저장, 미리보기, 접근 로그
- AI 추천/요약/초안 생성 API

## 승인 체크

메인 개발자는 병합 전 다음 세 가지를 확인한다.

- 변경 파일이 frontend 범위에 머문다.
- PR 설명의 테스트가 실제 변경 화면을 충분히 덮는다.
- backend 요청사항이 코드 변경이 아니라 문서화된 요청으로 남아 있다.
