# Bitween Frontend Contracts

This folder is the TypeScript contract boundary for Bitween frontend clients.

Current scope:

- Keep API DTOs, type guards, and small request builders here.
- Treat `frontend/src/contracts/payrollApi.ts` as the source of truth for payroll run and validation responses on the frontend side.
- Keep field names aligned with Rust backend contracts.
- Frontend code should call HTTP/client adapters, not payroll calculation internals.

Backend boundaries:

- Rust backend transition work lives under `crates/` and future Rust service crates.
- Compatibility adapters under `services/` and `core/` remain characterization sources only until Rust parity is proven.
- Production frontend traffic goes through Kubernetes-exposed API services.

Local checks:

```powershell
npm install
npm run typecheck
```
