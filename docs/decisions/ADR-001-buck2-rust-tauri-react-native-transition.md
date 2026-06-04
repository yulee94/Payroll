# ADR-001: Buck2, Rust backend, React Native, and Tauri transition

## Status

Accepted

## Date

2026-06-04

## Context

Bitween has merged the production business-trip lifecycle foundation and now needs the next production track:

- Introduce Buck2 as the planned monorepo build orchestrator.
- Rewrite backend behavior in idiomatic Rust, not Python.
- Clean up Python after Rust parity is proven.
- Continue the TypeScript React Native transition.
- Add a cross-platform desktop application path using Tauri plus the React Native web-compatible frontend.
- Enforce RBAC + ABAC authorization and Zero Trust boundaries across backend, Kubernetes, frontend, and desktop surfaces.
- Benchmark SAP, Remote People, and Workday feature/UI/UX maturity while localizing product scope for Korean SMEs and Korean labor-law operations.
- Support fully single-language UI modes for Korean, English, Chinese, and Japanese.
- Use WebAuthn/passkeys for phishing-resistant authentication and JWT only as short-lived signed API claims.

The current repository already contains:

- Rust workspace and `crates/payroll-api` as the first backend contract slice.
- TypeScript frontend contracts under `frontend/`.
- Expo / React Native / React Native Web platform UI under `apps/bitween-platform-ui/`.
- Python compatibility modules under `core/`, `services/`, and root-level modules that remain characterization sources until Rust parity exists.

## Source-backed basis

Official references checked for this decision:

- Buck2 getting-started and concepts: https://buck2.build/docs/getting_started/
- Buck2 build-rule determinism and explicit inputs: https://buck2.build/docs/concepts/build_rule/
- Buck2 language support for Rust/Python: https://buck2.build/docs/about/language_support/
- Buck2 Rust rule shape: https://buck2.build/docs/prelude/rules/rust/rust_binary/
- Reindeer Cargo-to-Buck dependency generation: https://github.com/facebookincubator/reindeer
- Tauri overview: https://tauri.app/start/
- Tauri project structure: https://tauri.app/start/project-structure/
- Tauri frontend-to-Rust command bridge: https://tauri.app/develop/calling-rust/
- Tauri security capabilities: https://tauri.app/security/capabilities/
- React Native platform-specific code: https://reactnative.dev/docs/platform-specific-code.html
- Expo web / React Native Web workflow: https://docs.expo.dev/workflow/web/
- Expo localization guide: https://docs.expo.dev/guides/localization/
- Expo localization API: https://docs.expo.dev/versions/latest/sdk/localization/
- MDN JavaScript internationalization guide: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Internationalization
- React Native I18nManager layout-direction support: https://reactnative.dev/docs/0.80/i18nmanager
- IETF RFC 5646 / BCP 47 language tags: https://datatracker.ietf.org/doc/rfc5646/
- W3C language-tag guidance: https://www.w3.org/International/articles/language-tags/
- NIST SP 800-207 Zero Trust Architecture: https://www.nist.gov/publications/zero-trust-architecture-0
- NIST SP 800-162 ABAC definition and considerations: https://csrc.nist.gov/pubs/sp/800/162/upd2/final
- NIST RBAC project and ANSI/INCITS 359 background: https://csrc.nist.gov/Projects/Role-Based-Access-Control
- Kubernetes RBAC authorization: https://kubernetes.io/docs/reference/access-authn-authz/rbac/
- Core Web Vitals thresholds and measurement guidance: https://web.dev/articles/vitals
- SAP Business One SME ERP scope: https://www.sap.com/products/erp/business-one.html
- SAP S/4HANA Cloud Public Edition best-practice process content: https://learning.sap.com/courses/implementing-sap-s-4hana-cloud-public-edition-asset-management-es/exploring-sap-s-4hana-cloud-public-edition-asset-management_b79eb66f-f5a1-4c11-b3e0-523b19c1dadf
- SAP SuccessFactors HCM suite scope: https://www.sap.com/products/hcm.html
- Workday Human Capital Management suite scope and persona guidance: https://www.workday.com/en-us/products/human-capital-management/overview.html
- Remote People global workforce platform self-service and compliance model: https://remotepeople.com/about/platform/
- Korean Ministry of Employment and Labor labor standards guidance: https://www.moel.go.kr/english/policy/laborStandards.do
- Korean Labor Standards Act current law entry: https://www.law.go.kr/LSW/lsEfInfoP.do?lsiSeq=283457
- 2026 Korean minimum wage public notice summary: https://www.korea.net/NewsFocus/policies/view?articleId=274970
- Korean Equal Employment Opportunity and Work-Family Balance Assistance Act current law entry: https://www.law.go.kr/LSW/lsInfoP.do?ancNo=21373&ancYd=20260219&efYd=20260820&lsiSeq=283455
- OECD 2026 Korea labor-market/SME recommendations: https://www.oecd.org/en/publications/2026/04/foundations-for-growth-and-competitiveness-2026_f68a156b/full-report/korea_5fb818a1.html
- IETF RFC 7519 JSON Web Token: https://datatracker.ietf.org/doc/html/rfc7519.html
- OWASP JWT Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
- W3C WebAuthn Level 3: https://www.w3.org/TR/webauthn-3/
- FIDO specifications overview: https://fidoalliance.org/specifications-overview/

## Decision

Adopt this transition direction:

1. **Buck2 is the target build graph, Cargo/npm stay authoritative until Buck2 targets are proven.**
   - Add Buck2 in slices after each target can be verified.
   - Do not replace working Cargo/npm checks with Buck2 until Buck2 reproduces the same Rust and frontend outputs.
   - Use explicit inputs and package boundaries; do not rely on symlinked or implicit source access.
   - Evaluate Reindeer before hand-writing third-party Rust dependency rules.

2. **Rust owns production backend behavior.**
   - Rust service/domain crates are the production backend path.
   - Python remains only as compatibility, characterization, migration tooling, or local data-conversion code until parity is proven.
   - Each Python cleanup must be attached to a Rust parity test and zero-production-use evidence.

3. **React Native owns the cross-platform frontend source.**
   - `apps/bitween-platform-ui/` remains the canonical TypeScript UI shell.
   - Use React Native / Expo / React Native Web patterns for shared components.
   - Use platform-specific files or `Platform` branches only for small platform deltas.

4. **Tauri desktop consumes the React Native Web static export rather than embedding a separate desktop-only UI.**
   - Desktop app source will live under `apps/bitween-desktop-tauri/`.
   - Tauri will package the Expo web export from `apps/bitween-platform-ui/`.
   - Tauri Rust commands are for desktop-only capabilities such as file dialogs, local secure storage, app lifecycle, and native shell integration.
   - Business APIs still go through the Kubernetes-exposed Rust backend unless a desktop command is explicitly designed as local-only.

5. **Kubernetes remains the production service runtime.**
   - Tauri desktop is a client distribution path, not a replacement for Kubernetes services.
   - Backend services, workers, CronJobs, migrations, ConfigMaps, Secrets, probes, and scaling stay in the Kubernetes stack.

6. **RBAC + ABAC is the authorization model, with Zero Trust as the security posture.**
   - RBAC grants coarse job-capability families such as employee, manager, payroll operator, HR admin, workflow approver, executive, auditor, and service account.
   - ABAC evaluates tenant/legal entity, workplace, department, document owner, approval line, lifecycle state, data sensitivity, device/session posture, request channel, and environment per request.
   - No API, worker, CronJob, Tauri command, or frontend capability hint is trusted without backend policy enforcement and audit evidence.

7. **Performance budgets are part of implementation readiness.**
   - Frontend and desktop web surfaces target Core Web Vitals budgets: LCP <= 2.5s, INP <= 200ms, CLS <= 0.1 at the 75th percentile.
   - Rust services must define latency/error/saturation budgets before HPA or production rollout.

8. **Industry-leader maturity is the benchmark, Korean SME is the product fit.**
   - Borrow operating discipline from SAP Business One/S/4HANA and SAP SuccessFactors: integrated modules, real-time reporting, role-specific UX, standardized process content, guided configuration, payroll/HR analytics, and workforce planning.
   - Borrow self-service/compliance maturity from Remote People: employee payslip/time-off/expense/document self-service, HR jurisdiction cockpit, templates, compliance monitoring, and alerts.
   - Borrow manager/employee experience maturity from Workday: persona-aware HCM, manager insights, workforce planning and analytics, talent/workforce management, extensibility, and configuration tooling.
   - Localize the product around Korean SME payroll, HR, workflow/electronic approval, Labor Standards Act records, 52-hour policy monitoring, minimum-wage configuration, four major social insurance, e-tax/NTS readiness, branch/workplace/legal-entity scoping, Excel/groupware migration, and manager accountability loops.
   - Do not clone SAP, Remote People, or Workday UI, proprietary content, or large-enterprise module breadth before core Bitween domains are production-ready.

9. **Authentication uses WebAuthn plus short-lived JWT claims.**
   - WebAuthn/passkeys are the target for phishing-resistant sign-in and step-up verification on privileged actions.
   - JWTs carry signed, short-lived API claims; possession of a JWT is never sufficient authorization without RBAC + ABAC policy checks.

10. **I18n is fully single-language across Korean, English, Chinese, and Japanese.**
   - Supported initial locales are `ko-KR`, `en-US`, `zh-Hans-CN`, and `ja-JP`.
   - A production screen must render in exactly one active language with no missing-key or mixed-language fallback.
   - Domain state, API errors, audit events, legal-policy references, and Tauri command messages use stable codes/metadata and are localized at the client boundary.
   - Korean legal source copy remains the source of truth, but user-facing explanations must be localized into the active language.

## Alternatives Considered

### Keep Cargo/npm only

- Pros: Lowest migration cost today; current checks already pass.
- Cons: Does not address monorepo build graph, deterministic target selection, or future multi-platform CI scaling.
- Rejected: Buck2 is now a requested direction, but the migration must be staged rather than disruptive.

### Big-bang Buck2 conversion

- Pros: One visible build-system switch.
- Cons: High breakage risk; Buck2 Rust dependency handling needs explicit third-party rule generation; frontend/Expo packaging needs careful target design.
- Rejected: Production quality requires proven target parity before toolchain replacement.

### React Native for Windows/macOS instead of Tauri

- Pros: More native desktop rendering for Windows/macOS.
- Cons: Splits the desktop path from Linux and from the existing Expo web-compatible shell; increases native platform maintenance.
- Rejected for now: Tauri can consume the web-compatible UI and provide a Rust-native desktop bridge across Windows/macOS/Linux.

### Tauri with a separate React DOM UI

- Pros: Direct fit for Tauri web frontend patterns.
- Cons: Duplicates the app surface and weakens the React Native transition.
- Rejected: The UI source of truth remains React Native / React Native Web.

### Delete Python immediately

- Pros: Faster apparent cleanup.
- Cons: Destroys behavior references before Rust parity, risks payroll/workflow regressions, and removes characterization tests.
- Rejected: Python cleanup must follow parity evidence.

## Consequences

- Early PRs should be documentation, target inventory, and one reproducible Buck2/Rust target at a time.
- Security and performance gates are documented in `docs/SECURITY_AND_PERFORMANCE_BASELINE.md`.
- Industry maturity, Korean SME labor-law localization, full single-language i18n, and JWT/WebAuthn guidance are documented in `docs/SAP_KOREAN_SME_BENCHMARK.md` and `docs/I18N_LOCALIZATION.md`.
- Rust service crates should expose contracts that TypeScript and Tauri can consume without importing Python internals.
- The desktop app should start as a wrapper around the web-compatible platform UI, then add Tauri commands only behind typed adapters.
- Python removal becomes a measured decommission program instead of ad-hoc deletion.
- CI must continue running Cargo/npm/Python checks until replacement Buck2 targets are proven and adopted.

## Acceptance criteria for first implementation PRs

- Buck2 plan identifies exact targets before introducing `.buckconfig`/`BUCK` files.
- Rust backend PRs include parity tests against current Python compatibility behavior plus RBAC/ABAC policy tests.
- Frontend PRs keep `apps/bitween-platform-ui/` as the source of truth, can export web assets for Tauri, and pass Korean/English/Chinese/Japanese translation completeness checks before production release.
- Desktop PRs never duplicate business logic in Tauri commands and declare least-privilege Tauri capabilities.
- Python cleanup PRs remove only code with Rust replacement evidence and passing characterization tests.
