# Bitween Platform UI

React Native + TypeScript frontend shell for Bitween cross-platform and web readiness.

This app is intentionally added in parallel to the existing Python/Tkinter desktop UI. It does not modify payroll calculation logic, service contracts, runtime data, or existing templates.

## Screens Covered

- Login
- Platform launcher/home
- Sidebar/menu navigation
- Payroll readiness and payroll entry flow
- HR, workflow, archive, AI, admin, and settings shell screens
- Shared card, badge, table, empty-state, and action button patterns

## Commands

```powershell
npm install
npm run typecheck
npm run web
```

## Backend Integration Policy

The current implementation uses typed mock data. Existing API-ready/service outputs should be connected through a small adapter layer once the backend contract is approved.

Do not change payroll backend internals from this frontend app. Missing fields should be documented as backend requests.
