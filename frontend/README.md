# Bitween Frontend Contracts

This folder is the TypeScript boundary for the future Bitween web frontend.

Current scope:

- Keep API DTOs, type guards, and small request builders here.
- Build UI pages in TypeScript without importing Python modules.
- Treat `frontend/src/contracts/payrollApi.ts` as the source of truth for payroll run and validation responses on the frontend side.

Backend boundaries:

- Python desktop services remain under `services/`, `core/`, and `ui/`.
- Rust backend transition work lives under `crates/`.
- Frontend code should call HTTP/client adapters, not payroll calculation internals.

Local checks:

```powershell
npm install
npm run typecheck
```
