# Bitween Frontend UI Guide

Bitween frontend work is TypeScript-first. The production frontend direction is the React Native / web-ready shell under `apps/bitween-platform-ui/` plus shared contracts under `frontend/`. Tauri desktop delivery must consume the React Native Web export instead of forking a desktop-only UI.

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
- Target industry-leader maturity inspired by SAP, Remote People, and Workday without cloning their UI: role workspaces, employee self-service, manager insight hubs, compliance cockpit, guided setup, lifecycle timelines, audit trails, and real Korean production copy.
- Korean labor-market and labor-law context should be visible at the point of work: wage/minimum-wage readiness, 52-hour working-time warnings, leave/holiday evidence, four major social insurance, e-tax/NTS readiness, employment/work-family records, and workplace/legal-entity scoping.
- Rich dashboards must remain data-dense but usable: search, filters, bulk actions, preview panels, status transitions, accountable owners, due dates, escalation state, and clear disabled-action reasons.
- All production UI copy must support a fully single-language mode for Korean (`ko-KR`), English (`en-US`), Chinese (`zh-Hans-CN`), and Japanese (`ja-JP`). No production screen should mix languages because a translation key is missing.
- Avoid user-facing string literals in components; use typed translation keys, locale-aware formatters, and stable backend error/status codes.
- Pull UI copy from catalog arrays such as `apps/bitween-platform-ui/src/i18n/catalog.json`; add `{ key, values }` rows for all supported locales before referencing text in a component.
- Keep source arrays limited to stable ids, tone, target, date/time, and sample data. Labels, statuses, details, empty states, table headers, toast copy, language names, and preview copy must be pulled from the catalog.
- CJK and English layouts must be reviewed for text expansion, IME input, line breaks, dense tables, accessibility labels, and desktop window sizes.

## Backend Data Policy

- UI consumes approved API/service outputs as read-only view models.
- UI may display capability hints from RBAC/ABAC policy responses, but backend Rust services must enforce final authorization.
- Do not import backend modules directly into frontend code.
- If the UI needs a field that services do not expose yet, list it in `apps/bitween-platform-ui/docs/backend-contract-requests.md`.
- Production frontend calls the Kubernetes-exposed API layer; local mock data is preview-only.

## Verification Checklist

```powershell
cd apps/bitween-platform-ui
npm install
npm run verify:i18n
npm run typecheck
npm run export:web
node preview/server.js
```

Manual UI review:

- Login renders without authenticated navigation.
- Login moves to the platform launcher.
- Navigation switches between payroll, HR, workflow, archive, AI, admin, and settings.
- Payroll readiness cards and workflow cards wrap without text clipping.
- Payroll setting summary and file preview/archive rows are visible.
- Module tables show rows on wide screens and cards on narrow screens.
- Employee self-service, manager ongoing/completed/overdue, compliance cockpit, and setup screens have realistic Korean labels and explicit empty/loading/error/permission states.
- Any legal/policy text shown in UI is a product-policy summary with an internal source/effective-date reference, not unsupported legal advice.
- Screens render fully in Korean, English, Chinese, and Japanese with no mixed-language fallback or clipped CJK/English text.
- `npm run verify:i18n` passes and confirms no localized CJK/Korean/Japanese/Chinese copy exists outside `apps/bitween-platform-ui/src/i18n/catalog.json` in the React Native/static preview source.
- No backend service, calculation, runtime data, template, or credential file is touched.

## Desktop / Tauri UI Rule

- Keep `apps/bitween-platform-ui/` as the shared React Native source of truth.
- Export React Native Web assets for Tauri; do not create a separate React DOM desktop UI.
- Desktop-only affordances must be isolated behind typed adapters and Tauri commands.
- Permission-denied, partial-access, and manager/escalation states must be explicit in UI copy and must not rely on color alone.
- Measure frontend/desktop performance against Core Web Vitals budgets before production desktop release.
- Tauri app metadata, native dialog labels, desktop command errors, and capability-denied states must use the same active locale as the React Native UI.
