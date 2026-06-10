# Bitween Desktop Tauri Shell

This directory is reserved for the production desktop application that wraps the React Native Web-compatible Bitween platform UI with Tauri.

## Direction

- **UI source of truth:** `apps/bitween-platform-ui/` using TypeScript, React Native, Expo, and React Native Web.
- **Desktop shell:** Tauri packages the exported web assets for Windows, macOS, and Linux.
- **Native bridge:** Tauri Rust commands are allowed only for desktop-specific capabilities such as file dialogs, secure local settings, lifecycle hooks, and controlled shell integration.
- **Office contract:** Desktop Office work must follow `docs/OFFICE_PRODUCT_CONTRACT.md`; Tauri may add native affordances only after the Rust/PostgreSQL/RustFS Office slice is live-wired and verified.
- **Localization:** Desktop metadata, native dialogs, command errors, and capability-denied states must follow the active React Native locale for Korean, English, Chinese, and Japanese.
- **Business backend:** Production business behavior stays in Kubernetes-deployed Rust services; the desktop app calls those APIs through typed frontend adapters.

## Source-backed basis

- Tauri supports frontend frameworks that compile to HTML, JavaScript, and CSS: https://tauri.app/start/
- Tauri projects usually pair a JavaScript project with a `src-tauri/` Rust project: https://tauri.app/start/project-structure/
- Tauri frontend-to-Rust calls use typed commands and `invoke`: https://tauri.app/develop/calling-rust/
- Tauri capabilities govern what commands/windows can access: https://tauri.app/security/capabilities/
- Expo can export a React Native Web app as a production website: https://docs.expo.dev/workflow/web/
- NIST Zero Trust Architecture: https://www.nist.gov/publications/zero-trust-architecture-0
- RBAC + ABAC baseline for Bitween: `../../docs/SECURITY_AND_PERFORMANCE_BASELINE.md`

## Planned structure

```text
apps/bitween-desktop-tauri/
├── README.md
├── package.json                 # future Tauri CLI scripts
├── src-tauri/
│   ├── Cargo.toml               # future Tauri Rust crate
│   ├── tauri.conf.json          # points frontendDist to platform UI web export
│   ├── capabilities/default.json
│   └── src/
│       ├── lib.rs               # command registration
│       └── commands.rs          # typed desktop-only commands
└── docs/
    └── desktop-command-contracts.md
```

## Non-goals

- Do not create a second desktop-only React UI.
- Do not create a second desktop-only localization system.
- Do not move payroll, workflow, KPI, org, mobile, or AI business logic into Tauri commands.
- Do not store production secrets in the desktop bundle.
- Do not use local JSON stores as production authority.
- Do not grant broad Tauri capabilities; every command must have a least-privilege capability and typed validation.
- Do not treat desktop packaging, local network location, or logged-in UI state as trust.

## First implementation slice

1. Export web assets from `apps/bitween-platform-ui`.
2. Scaffold `src-tauri/` with no business commands.
3. Add a typed health/config command only if needed for shell diagnostics, with least-privilege capability scope.
4. Wire desktop API calls to the Kubernetes Rust API base URL through the existing frontend adapter boundary.
5. Add least-privilege capabilities and desktop build verification.

## Security and performance gates

- Every command must name its RBAC role family, ABAC attributes, validation schema, audit event, and capability file.
- Every desktop release must verify the React Native Web export, Tauri build, four-language localization review, and a frontend performance budget.
- Desktop-sensitive local data requires an explicit storage, encryption, retention, and deletion decision before implementation.
