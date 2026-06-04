# Bitween Frontend UI Guide

Bitween frontend work is TypeScript-first. The production frontend direction is the React Native / web-ready shell under `apps/bitween-platform-ui/` plus shared contracts under `frontend/`.

## Branch Rule

- Keep UI PRs reviewable by grouping changes by screen, route, or component family.
- Do not commit directly to backend-focused branches unless a contract slice requires coordinated frontend and backend updates.
- If a UI change needs missing backend data, document the request instead of changing backend internals.

## Allowed Scope

- `apps/bitween-platform-ui/` screens, components, preview, theme, view models, and app shell.
- `frontend/` TypeScript DTOs, type guards, and request builders.
- UI assets, icons, theme presets, locale display text, and frontend documentation.
- Read-only adapters that map approved API responses into frontend view models.

## Do Not Change

- Payroll calculation formulas, tax/insurance logic, payroll builders, archive storage behavior, service contracts, runtime data, or templates.
- Rust backend behavior except through an approved contract update.
- Compatibility service internals to obtain missing UI data.
- Real employee rosters, payroll outputs, API keys, cookies, sessions, tenant runtime data, or workbook templates.

## UI Direction

- Calm B2B platform style: restrained color, clear hierarchy, dense but scannable information.
- Prefer consistent cards, tables, tabs, filters, status badges, empty states, and action buttons.
- Every screen should make the next likely action visible without relying on backend changes.
- Prevent text clipping, overlapping controls, broken buttons, and awkward scrolling at supported viewport sizes.
- Empty, loading, error, and permission states should be explicit and polite.

## Backend Data Policy

- UI consumes approved API/service outputs as read-only view models.
- Do not import backend modules directly into frontend code.
- If the UI needs a field that services do not expose yet, list it in `apps/bitween-platform-ui/docs/backend-contract-requests.md`.
- Production frontend calls the Kubernetes-exposed API layer; local mock data is preview-only.

## Verification Checklist

```powershell
cd apps/bitween-platform-ui
npm install
npm run typecheck
node preview/server.js
```

Manual UI review:

- Login renders without authenticated navigation.
- Login moves to the platform launcher.
- Navigation switches between payroll, HR, workflow, archive, AI, admin, and settings.
- Payroll readiness cards and workflow cards wrap without text clipping.
- Payroll setting summary and file preview/archive rows are visible.
- Module tables show rows on wide screens and cards on narrow screens.
- No backend service, calculation, runtime data, template, or credential file is touched.
