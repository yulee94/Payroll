# Bitween UI Static Preview

Dependency-free browser preview for reviewing the current frontend direction before Expo dependencies are installed.

## Run

```powershell
node preview/server.js
```

Open `http://127.0.0.1:4173/`.

## Scope

- Mirrors the current login, launcher, sidebar, payroll, HR, workflow, archive, AI, admin, and settings screen structure.
- Uses safe mock data only.
- Does not call backend services or touch payroll calculation logic.
- Exists for quick design review; the production implementation remains the React Native TypeScript app under `src/`.
