# Bitween UI Static Preview

Dependency-free browser preview for reviewing the current frontend direction before Expo dependencies are installed.
The preview is split into `index.html`, `styles.css`, and `app.js` so UI changes can be reviewed without rebuilding Expo. User-facing copy is loaded from `../src/i18n/catalog.json` through the local preview server; do not add inline localized strings to `app.js`.

## Run

```powershell
node preview/server.js
```

Open `http://127.0.0.1:4173/`.

The preview does not provide demo credentials, fake authentication, fabricated
business records, or stubbed payroll data. Until a real backend is connected,
use **Review empty shell** to inspect navigation and layout without live data.

## Scope

- Mirrors the current login, launcher, sidebar, payroll, HR, workflow, archive, AI, admin, and settings screen structure.
- Uses empty states when live data is unavailable.
- Pulls labels, statuses, helper text, toast copy, and language names from the same catalog array as the React Native app.
- Does not call backend services or touch payroll calculation logic.
- Exists for quick design review; the production implementation remains the React Native TypeScript app under `src/`.
