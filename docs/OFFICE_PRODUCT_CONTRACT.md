# Office Product Contract

Status: future product, not exposed in navigation until live-wired.

## Objective

Bitween Office is a required product line for managed-Kubernetes Bitween, but it must not appear as a visible module until the backend, storage, collaboration, authorization, audit, and UI contracts are live. It covers documents, spreadsheets, and slides for Korean-first HR/payroll/business workspaces where Office artifacts can be linked to workflow, approval, payroll evidence, 자료함 intake, and audit packs without becoming a separate unmanaged file silo.

## Reference basis

Use `~/Developer/oyatie/oya/office` as local reference material for product decomposition and maturity patterns only. Current Oyatie reference surfaces include Rust office/domain/kernel/API crates such as `oya-office-doc-domain`, `oya-office-sheet-domain`, `oya-office-slide-domain`, `oya-office-collab-domain`, `oya-office-storage-kernel`, `oya-office-drive-domain`, and `oya-office-collab-gateway-app`.

Relevant Oyatie catalog references to adapt, not copy:

- `registry/catalog/oya-workspace-document-format-kernel.yaml`
- `registry/catalog/oya-workspace-sheets-kernel.yaml`
- `registry/catalog/oya-workspace-collab-runtime-kernel.yaml`
- `registry/catalog/oya-collab-crdt-portability-kernel.yaml`

## Architecture contract

- Rust service crates own Office domain behavior. Future crates should be scoped as Office document, spreadsheet, slide, drive/storage, collaboration, search, authorization, and format workers under `crates/` or future Rust service-crate paths.
- React Native remains the shared UI source of truth for web/mobile-compatible Office surfaces. Tauri is a packaging/native-bridge path for desktop Office capabilities such as controlled file open/save dialogs, OS lifecycle hooks, and secure desktop settings; it must not hold business logic or bypass Kubernetes Rust services.
- PostgreSQL metadata owns relational workspace/document records, permissions, shared links, collaboration sessions, logical versions/deltas, review status, audit references, and search-index metadata.
- RustFS blobs own originals, imported/exported binaries, embedded media, preview/render artifacts, and evidence files. PostgreSQL stores object URI/checksum/version references, not whole-file binary copies.
- real-time collaboration uses a CRDT/operation-log boundary with deterministic merge validation, tenant-scoped session membership, resumable cursor checkpoints, and append-only audit for edit sessions.
- History, recovery, and rollback use logical versions/deltas, operation records, object checksums, and metadata recovery records. Rollback must not clone full binaries into PostgreSQL.
- ABAC + RBAC + PBAC is required before every Office read/write/share/export/collaboration mutation. Decisions must include tenant/legal-entity/workplace scope, resource classification, workflow state where applicable, and auditable deny reasons.
- Sensitive HR/payroll/personnel data inside Office artifacts must be classified and redacted in logs, telemetry, previews, and support exports. Fixtures use Acme / Acme Corporation only.

## Visibility and UI gates

Office must stay absent from left navigation, topbar shortcuts, and route lists until verification gates before visibility prove that all visible controls are live-wired. The first visible Office slice must include:

1. Rust/Buck2 build, check, clippy, and tests for the relevant Office service crate or binary.
2. PostgreSQL schema or repository evidence for metadata, permissions, version records, and audit references.
3. RustFS object lifecycle evidence for originals, exported binaries, previews, and media.
4. Authorization tests for ABAC + RBAC + PBAC Office operations.
5. Korean-first catalog-backed UI copy with no hardcoded visible strings.
6. Browser/runtime verification for every visible Office button, menu, and command.
7. Handoff evidence and an updated verifier that prevents regression into non-live UI.

## Initial backlog slices

- Define `docs`, `sheets`, and `slides` REST/DTO schemas in Rust with stable TypeScript contracts.
- Add PostgreSQL migrations for Office workspace metadata, object references, versions, operation logs, and audit events.
- Add a RustFS adapter contract for Office originals, embeds, exports, and previews.
- Add collaboration session admission, CRDT/operation-log validation, and audit-event persistence.
- Add search/index metadata and redaction boundaries before content preview/search appears in UI.
- Add Tauri desktop command contracts only after web routes are live and authorized.

## Verification

Run this contract gate after any Office-adjacent change:

```powershell
cd apps/bitween-platform-ui
npm run verify:office-contract
```

This gate intentionally proves the Office requirement remains durable while the visible product is not yet live. It does not make the Office module complete.
