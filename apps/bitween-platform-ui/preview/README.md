# Bitween UI Static Preview

Dependency-free demo preview for reviewing the current frontend direction before Expo dependencies are installed.
The preview is split into `index.html`, `styles.css`, and `app.js` so UI changes can be reviewed without rebuilding Expo. User-facing copy is loaded from `../src/i18n/catalog.json` through the local preview server; do not add inline localized strings to `app.js`.
This path intentionally uses safe mock data. Use it only when the demo version is requested.

## Run

```powershell
npm run demo
```

`npm run preview` starts the same demo-only route for compatibility.

Open `http://127.0.0.1:4173/`.

Demo login:

- Company code: `0000`
- User ID: `admin`
- Password: `admin`

## Scope

- Mirrors the current login, launcher, sidebar, payroll, HR, workflow, archive, AI, admin, and settings screen structure.
- Uses safe mock data only and is explicitly demo-only.
- Pulls labels, statuses, helper text, toast copy, and language names from the same catalog array as the React Native app.
- Does not call backend services or touch payroll calculation logic.
- Exists for quick design review; the production implementation remains the React Native TypeScript app under `src/`.
