# Bitween Platform UI

React Native + TypeScript frontend shell for Bitween cross-platform and web readiness.

This app is the documented frontend direction for Bitween. It is isolated from backend calculation logic, runtime data, credentials, and templates, and is intended to consume stable Rust/API contracts once each backend slice is approved.

## Screens Covered

- Rust-backed live operations shell with authenticated role workspaces
- HR, payroll, workflow, 전자결재, 자료함, admin, and settings surfaces routed from the Rust live view-model
- Payroll operator work, schedule, follow-up, and close-period workflows without technical readiness walls
- Signed-out auth gate that starts configured company identity, access request, onboarding, and sign-out routes
- Shared card, badge, table, filter, empty-state, metric, and action button patterns

## Source Map

- `App.tsx`: live shell routing and React Native entry
- `src/components.tsx`: shared React Native UI primitives
- `src/screens.tsx`: launcher, payroll, and module screens
- `src/data.ts`: legacy static review data for surfaces not yet migrated; do not use for production/live wiring
- `src/i18n/catalog.json`: catalog-array source for localized UI copy
- `src/i18n/index.ts`: locale normalization, translation lookup, and language option helpers
- `scripts/verify-i18n-catalog.mjs`: verifies every catalog row has Korean, English, Chinese, and Japanese values and rejects localized UI copy outside the catalog in the React Native and static preview sources
- `src/viewModel.ts`: frontend read-only view-model boundary and adapter shape
- `src/types.ts`: strict frontend domain types
- `src/theme.ts`: color, spacing, radius, and status-tone tokens
- `preview/index.html`: dependency-free interactive browser preview for design review
- `preview/server.js`: tiny local static server for the preview

## Dependency Baseline

The package is aligned to Expo SDK 54, which targets React Native 0.81, React 19.1, and react-native-web 0.21.

## Commands

```powershell
npm install
npm run verify:auth-routes
npm run verify:signed-out-auth-ux
npm run check:strict-config
npm run verify:data-mode
npm run verify:i18n
npm run typecheck
npm audit --omit=dev --audit-level=moderate
npm run export:web
npm run web
```

`check:strict-config` verifies that the frontend keeps `strict`, `noUncheckedIndexedAccess`, `noImplicitReturns`, and `noImplicitOverride` enabled in `tsconfig.json`, and that `typecheck` remains wired to `tsc --noEmit`. `typecheck` still performs the full TypeScript compile check after dependencies are installed.

Dependency-free UI preview:

```powershell
npm run preview
```

Then open `http://127.0.0.1:4174/` in a browser. This preview reads `/catalog.json`, preflights `/api/auth/v1/routes`, and reads the Rust-generated `/api/platform/v1/view-model` payload through the Buck2 live view target.

## View Model Boundary

`src/viewModel.ts` is the frontend integration seam. Rust/API data should be mapped into the same read-only `PlatformViewModel` shape without changing payroll calculation or service internals.

## Kubernetes Integration

Production delivery should package this frontend as a containerized workload served through the Kubernetes frontend route described in `docs/KUBERNETES_NATIVE_STACK.md`. Static preview data must not be promoted as production data.

## Review Checklist

- Confirm `npm run verify:auth-routes`, `npm run verify:signed-out-auth-ux`, `npm run verify:data-mode`, and `npm run verify:i18n` pass before changing auth or user-facing copy.
- Confirm signed-out users see route-aware company account actions instead of a dead-end missing-address toast.
- Confirm navigation switches between HR, payroll, workflow, 전자결재, 자료함, and admin surfaces exposed by the Rust payload.
- Confirm payroll work, schedule, follow-up, and file/archive rows are visible without technical backend/build/storage diagnostics.
- Confirm module tables show as table rows on wide screens and card rows on narrow screens.
- Confirm new user-facing copy comes from catalog arrays instead of inline component strings.
- Confirm Korean is the first visible language; other locales remain catalog-complete for future rollout.
- Confirm no backend service, calculation, runtime data, template, or credential file is touched.

## I18n Policy

Production UI copy must be catalog-array driven. Add new copy to `src/i18n/catalog.json` as `{ key, values }` rows for `ko-KR`, `en-US`, `zh-Hans-CN`, and `ja-JP`; then reference the key from UI code through `src/i18n/index.ts` or the static preview translator.

Do not hardcode user-facing labels, statuses, errors, helper text, auth/security copy, or desktop command messages inside components. Source arrays should hold stable ids, tone, target, dates, and sample data only; labels, statuses, details, empty states, table headers, toast messages, and language names come from the catalog. `npm run verify:i18n` fails when localized CJK/Korean/Japanese/Chinese copy appears in the React Native source or dependency-free preview outside `catalog.json`.

## Backend Integration Policy

The browser runtime is wired to the Rust `bitween-payroll-api` live view-model endpoint. Remaining static TypeScript data is legacy review material and must be replaced by Rust/API contracts before production release.

Do not change backend internals from this frontend app. Missing fields should be documented as backend requests.
