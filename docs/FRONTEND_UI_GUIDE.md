# Bitween Frontend UI Guide

This branch is dedicated to user-facing frontend/UI/UX improvements only.

## Branch Rule

- Working branch: `codex/frontend-platform-ui`
- Do not commit directly to `main`, `codex/commercialization-foundation`, or backend-focused branches.
- Keep UI PRs reviewable by grouping changes by screen or component.

## Allowed Scope

- `ui/` screen components and dialogs
- Login, launcher, sidebar navigation, platform cards, workspace hub, archive/preview panels, settings panels
- UI assets, icons, theme presets, locale display text, and frontend documentation
- `app_ui.py` only for page routing, layout, and UI wiring

## Do Not Change

- Payroll calculation formulas, tax/insurance logic, payroll builders, archive storage behavior, service contracts, or runtime data
- `services/payroll_automation.py`, `services/payroll_api_adapter.py`, `services/payroll_api_contract.py`, `services/payroll_readiness.py`, `services/payroll_policy_store.py`, `services/payroll_settings_store.py`, `services/payroll_ui_bridge.py`, `services/payroll_settings_ui_bridge.py`
- `core/payroll/`, `payroll_builder.py`, `payroll_archive.py`, `tax.py`, `insurance.py`, `main.py` calculation flow
- Real employee rosters, payroll outputs, API keys, cookies, sessions, tenant runtime data, or workbook templates

## UI Direction

- Calm B2B platform style: restrained color, clear hierarchy, dense but scannable information.
- Prefer consistent cards, tables, tabs, filters, status badges, empty states, and action buttons.
- Every screen should make the next likely action visible without relying on backend changes.
- Prevent text clipping, overlapping controls, broken buttons, and awkward scrolling at supported window sizes.
- Empty, loading, error, and permission states should be explicit and polite.

## Backend Data Policy

- UI may read already provided service results, such as payroll readiness cards or snapshots.
- Do not modify service internals to obtain missing data.
- If the UI needs a field that services do not expose yet, list it as a backend request in the PR.

## Verification Checklist

- App launch via `python main.py`
- Login screen layout, form submission, error state, remember toggle, password visibility toggle
- Launcher/home scrolling, payroll readiness status, platform cards, appearance area
- Sidebar section expansion, active state, navigation to payroll, HR, workflow, settings, admin pages
- Archive folder empty state, file selection, double-click folder navigation, preview panel loading/error state
- Module hub tabs, table empty state, refresh button, add button dialog path
- Payroll settings scroll, inputs, save buttons, status text
- Focused tests when local repo and dependencies are available
