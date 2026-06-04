# Bitween Platform UI

React Native + TypeScript frontend shell for Bitween cross-platform and web readiness.

This app is the documented frontend direction for Bitween. It is isolated from backend calculation logic, runtime data, credentials, and templates, and is intended to consume stable Rust/API contracts once each backend slice is approved.

## Screens Covered

- Login screen separated from the authenticated platform shell
- Platform launcher/home with metrics, work queue, and module cards
- Sidebar/menu navigation with compact horizontal behavior on narrow screens
- Payroll readiness and payroll workflow steps
- Payroll setting summary and file preview/archive workflow surfaces
- HR, workflow, archive, AI, admin, and settings dashboard screens
- Shared card, badge, table, filter, empty-state, metric, and action button patterns

## Source Map

- `App.tsx`: auth preview state, screen routing, shell entry
- `src/components.tsx`: shared React Native UI primitives
- `src/screens.tsx`: login, launcher, payroll, and module screens
- `src/data.ts`: typed safe mock data for frontend preview
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
npm run check:strict-config
npm run typecheck
npm run web
```

`check:strict-config` verifies that the frontend keeps `strict`, `noUncheckedIndexedAccess`, `noImplicitReturns`, and `noImplicitOverride` enabled in `tsconfig.json`, and that `typecheck` remains wired to `tsc --noEmit`. `typecheck` still performs the full TypeScript compile check after dependencies are installed.

Dependency-free UI preview:

```powershell
node preview/server.js
```

Then open `http://127.0.0.1:4173/` in a browser. This preview mirrors the current screen structure and interactions without requiring Expo dependencies.

## View Model Boundary

`src/viewModel.ts` is the frontend integration seam. During the preview phase it exports `previewPlatformViewModel`; later, Rust/API data should be mapped into the same read-only `PlatformViewModel` shape without changing payroll calculation or service internals.

## Kubernetes Integration

Production delivery should package this frontend as a containerized workload served through the Kubernetes frontend route described in `docs/KUBERNETES_NATIVE_STACK.md`. Static preview data must not be promoted as production data.

## Review Checklist

- Confirm login renders without authenticated navigation.
- Confirm login button moves to the platform launcher.
- Confirm navigation switches between payroll, HR, workflow, archive, AI, admin, and settings.
- Confirm payroll readiness cards and payroll workflow cards wrap without text clipping.
- Confirm payroll setting summary and file preview/archive rows are visible on the payroll screen.
- Confirm module tables show as table rows on wide screens and card rows on narrow screens.
- Confirm no backend service, calculation, runtime data, template, or credential file is touched.

## Backend Integration Policy

The current implementation uses typed mock data. Existing API-ready outputs should be connected through a small adapter layer once the backend contract is approved.

Do not change backend internals from this frontend app. Missing fields should be documented as backend requests.
