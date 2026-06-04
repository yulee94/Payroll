# Industry maturity benchmark for Korean SME Bitween direction

## Purpose

Benchmark the feature depth, UI/UX maturity, compliance posture, and operating discipline of industry leaders such as SAP, Remote People, and Workday without cloning their proprietary UI, terminology, or enterprise complexity. Bitween should preserve Korean SME realities: payroll and HR operations, groupware/electronic approval, Excel-heavy transitions, four major social insurance workflows, Korean labor-law records, e-tax invoice integration, branch/workplace/legal-entity scoping, mobile attendance, and manager dashboards.

## Source-backed evidence

- SAP Business One positions its SME ERP scope around accounting/financials, purchasing, inventory, sales, customer relationships, reporting, and analytics: https://www.sap.com/products/erp/business-one.html
- SAP Business One Help describes a small/midsize ERP divided into modules for business functions, with real-time business information in a single system and extensibility across interfaces/mobile/analysis tools: https://help.sap.com/docs/SAP_BUSINESS_ONE/68a2e87fb29941b5bf959a184d9c6727/6b40396fcce04dcaba5c9bd5aab3d25d-5888.html
- SAP S/4HANA Cloud Public Edition best-practice content emphasizes standardized core processes, finance, sourcing/procurement, manufacturing, sales, supply chain, role-specific UX, embedded analytics, guided configuration, and data migration: https://learning.sap.com/courses/implementing-sap-s-4hana-cloud-public-edition-asset-management-es/exploring-sap-s-4hana-cloud-public-edition-asset-management_b79eb66f-f5a1-4c11-b3e0-523b19c1dadf
- SAP SuccessFactors HCM covers core HR/payroll, talent management, HR analytics, workforce planning, and employee experience management: https://www.sap.com/products/hcm.html
- Workday HCM positions its suite around Core HCM, workforce planning and analytics, talent management, workforce management, experience and engagement, extensibility, and persona-aware data models: https://www.workday.com/en-us/products/human-capital-management/overview.html
- Remote People emphasizes an employee self-service portal for payslips, time-off, expenses, and documents, plus an HR single pane of glass across jurisdictions with built-in tax, pension, social security, labor-law compliance, templates, monitoring, and alerts: https://remotepeople.com/about/platform/
- Korean four major social insurance categories are employment insurance, industrial accident compensation insurance, national pension, and national health insurance: https://www.investkorea.org/ik-en/cntnts/i-413/web.do
- Korea e-tax invoice localization must account for National Tax Service reporting/verification workflows; SAP documents Korean electronic customer tax invoice handling through eDocument Cockpit/service providers: https://help.sap.com/docs/SAP_S4HANA_CLOUD/6418c31b58e840619e5e74885df6d3b4/256609a121c14fdfaff70d7d720faffd.html
- The Korean Ministry of Employment and Labor describes the Labor Standards Act as setting minimum standards for wages, working hours, holidays, and leave; it also documents the 52-hour weekly working-hour ceiling: https://www.moel.go.kr/english/policy/laborStandards.do
- The National Law Information Center lists the Korean Labor Standards Act currently scheduled with a 2026-08-20 effective text: https://www.law.go.kr/LSW/lsEfInfoP.do?lsiSeq=283457
- Korea's official public information portal reported the 2026 minimum wage as KRW 10,320 per hour and KRW 2,156,880 monthly when calculated on 209 work hours: https://www.korea.net/NewsFocus/policies/view?articleId=274970
- The National Law Information Center lists the Equal Employment Opportunity and Work-Family Balance Assistance Act with 2026 effective amendments, including work-family support obligations that affect HR workflows: https://www.law.go.kr/LSW/lsInfoP.do?ancNo=21373&ancYd=20260219&efYd=20260820&lsiSeq=283455
- OECD's 2026 Korea growth and competitiveness recommendations call out SME innovation incentives and reducing labor-market mismatch and labor shortages through vocational/work-based skill development: https://www.oecd.org/en/publications/2026/04/foundations-for-growth-and-competitiveness-2026_f68a156b/full-report/korea_5fb818a1.html
- JWT is standardized by IETF RFC 7519 as compact URL-safe claims encoded as JWS/JWE: https://datatracker.ietf.org/doc/html/rfc7519.html
- OWASP documents common JWT security pitfalls and mitigations: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
- WebAuthn Level 3 defines strong, scoped, public-key credentials for web applications with user-agent mediation and authenticator consent: https://www.w3.org/TR/webauthn-3/
- FIDO positions WebAuthn and CTAP together as FIDO2 and passkeys for sign-in: https://fidoalliance.org/specifications-overview/
- Expo localization and JavaScript `Intl` APIs support locale detection and locale-aware formatting for the React Native/Web/Tauri UI path: https://docs.expo.dev/guides/localization/ and https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Internationalization

## Direct recommendation

Design Bitween as **industry-leader mature HR/workflow/payroll operations for Korean SMEs**, not SAP/Workday-scale enterprise complexity.

Core product benchmark:

| Industry benchmark pattern | Korean SME Bitween adaptation |
| --- | --- |
| Single ERP system across modules | One platform shell across payroll, HR, workflow, business trips, KPI, archive, AI, admin, and settings |
| Financials/accounting/purchasing/sales/inventory modules | Payroll, HR, electronic approval, attendance, archive, groupware import, compliance docs, e-tax/e-insurance integration readiness |
| Real-time reporting and analytics | Manager ongoing/completed/overdue views, payroll readiness, KPI reflection, executive dashboards |
| Role-specific UX | RBAC + ABAC-aware surfaces for employee, manager, payroll operator, HR admin, workflow approver, executive, auditor |
| Best-practice process content | Korean templates for 출장신청서, 업무일지, 출장보고서, payroll operation policy, social insurance, NTS/eDocument workflows |
| Guided configuration and migration | Korean SME setup wizard for legal entity, workplace, payday, attendance rounding, approval lines, social insurance profiles, data import |
| Extensibility and interfaces | Rust API contracts, TypeScript DTOs, Kubernetes services, Tauri desktop shell, groupware/import adapters |

## Feature and UI/UX maturity target

Bitween should feel mature in the way SAP, Remote People, and Workday feel mature: users always know what work is pending, what evidence exists, which rule applies, and what action is allowed next.

| Maturity dimension | Industry-leader signal | Bitween production target |
| --- | --- | --- |
| Role workspaces | SAP/Workday split work by employee, manager, HR, payroll, analytics, and admin personas | Persona-specific landing pages with the same domain objects, filtered by RBAC + ABAC capability hints |
| Employee self-service | Remote People surfaces payslips, time-off, expenses, and documents to employees | Korean employee portal for payslips, leave, attendance corrections, 출장/업무일지, documents, and requests |
| Manager insight hub | Workday emphasizes manager insights and faster decisions | Manager dashboard for ongoing/completed/overdue work, approval bottlenecks, KPI reflection, payroll readiness, and escalation |
| Compliance cockpit | Remote People treats compliance monitoring/templates as core workflow | Korean labor-law cockpit for wage, working-hour, leave, social insurance, NTS/e-tax, and document-retention readiness |
| Guided configuration | SAP best-practice content and Workday configuration patterns reduce blank-page setup | Korean SME setup wizard with legal entity, workplace, payday, employment type, approval line, 52-hour policy, minimum-wage baseline, and template packs |
| Data density without clutter | Enterprise HCM products expose many objects while preserving task focus | Dense tables, dashboards, and timelines with search, filters, bulk actions, preview panels, and clear empty/error/loading states |
| Cross-platform continuity | Users expect web/mobile/desktop parity for common HR actions | React Native source of truth exported for web and Tauri desktop; platform-specific behavior only where the platform requires it |
| Single-language localization | Mature global HR tools avoid mixed-language operational screens | Fully single-language Korean, English, Chinese, and Japanese UI modes backed by catalog arrays with no missing-key fallback in production |
| Auditable actions | Mature systems show who changed what, why, and under which rule | Every approval, payroll export, KPI reflection, auth step-up, import, and policy change has an audit trail and explainable policy decision |

## UI/UX richness principles

1. **Korean-first information architecture.** Navigation and templates should reflect Korean SME operations: 급여, 근태, 연차, 출장, 업무일지, 전자결재, 4대보험, 세금계산서, 증빙, 법인/사업장.
2. **No placeholder maturity.** A screen can be intentionally read-only or disabled, but it must explain status, source of truth, missing setup, required permission, and next action.
3. **Lifecycle timelines.** Payroll runs, business trips, 업무일지, approvals, imports, compliance reviews, and KPI reflection need timeline, owner, due date, evidence, and escalation state.
4. **Legal and policy explanations at point of work.** Show the applicable Korean rule/policy summary where a user makes payroll, leave, working-time, approval, or employment-record decisions; link to the internal policy source, not raw legal advice.
5. **Manager and executive rollups.** Every operational object that can be pending should be visible in ongoing/completed/overdue views with accountability, drilldown, and export controls.
6. **Accessible production UI.** Preserve keyboard navigation, semantic labels, sufficient contrast, responsive layouts, and realistic Korean copy; avoid generic AI-card layouts and decorative gradients.
7. **Performance-aware richness.** Rich dashboards must remain paginated, virtualized, cached, and measured against Core Web Vitals / desktop export budgets.
8. **Full single-language localization.** Korean, English, Chinese, and Japanese users should see one complete language per session, including auth/security errors, policy help, manager dashboards, desktop shell copy, and accessibility labels. UI copy should be pulled from catalog arrays, not hardcoded inside components.

## Korean labor market and law localization

Bitween is not a general global HCM clone. The product should encode Korean SME constraints and keep legal facts source-driven:

| Area | Product implication |
| --- | --- |
| Wage and minimum wage | Maintain yearly minimum-wage baseline configuration, wage-statement/wage-ledger readiness, monthly/hourly conversion rules, and exception warnings. |
| Working time | Track scheduled work, overtime, holiday/night work, rest, and 52-hour policy warnings with manager escalation before payroll close. |
| Leave and holidays | Treat annual leave, holiday work, leave balance, unused leave payout inputs, and proof documents as payroll-affecting records. |
| Work-family / equal employment | Track parental leave, reduced working-hours requests, return-to-work support, and HR evidence without exposing sensitive data beyond permitted roles. |
| Four major social insurance | Keep employment insurance, industrial accident compensation insurance, national pension, and national health insurance setup/status as first-class readiness surfaces. |
| E-tax/NTS readiness | Preserve e-tax invoice and National Tax Service integration readiness as an accounting/compliance workflow, not a generic file upload. |
| SME labor mismatch | Provide guided onboarding, templates, training/checklist flows, and migration/import assistance so small HR/payroll teams can adopt without enterprise consultants. |
| Foreign/remote workers | Support jurisdiction/workplace/employment-type attributes in ABAC and payroll policy without assuming one-size-fits-all labor treatment. |

Implementation note: this document is product and architecture guidance, not legal advice. Implementation PRs that encode Korean legal thresholds must cite the exact official law/guidance effective date they rely on and must make yearly policy values configurable.

## Korean SME product principles

1. **Fast adoption over enterprise breadth.** Keep setup guided, opinionated, and localized for Korean payroll/HR/workflow operations.
2. **Excel/import coexistence during migration.** SMEs often start from Excel and groupware exports; preserve import/preview/reconciliation while moving authority to Rust services.
3. **Korean compliance-first workflows.** Labor Standards Act records, 52-hour policy monitoring, minimum-wage configuration, four major social insurance, work-family/equal-employment evidence, year-end/tax documents, e-tax invoice/NTS integration, and labor/workplace records are first-class product surfaces.
4. **Manager accountability loops.** Every work/trip lifecycle should have ongoing, completed, overdue, escalation, and KPI reflection states visible to supervisors.
5. **Role-specific but small-team friendly.** Support separation of duties without forcing large-enterprise org structures.
6. **Configurable, not bespoke.** Use guided configuration and approved templates rather than custom-code changes per customer.

## Authentication benchmark: JWT + WebAuthn

### WebAuthn / passkeys

Use WebAuthn as the phishing-resistant authentication direction for privileged and eventually default sign-in:

- Payroll operators, HR admins, executives, auditors, and service administrators should require WebAuthn/passkey enrollment for production access.
- Manager approvals, payroll export, data migration, policy changes, and KPI reflection overrides should support step-up WebAuthn verification.
- Store public credential metadata server-side; never store private keys.
- Relying Party IDs and origins must match production domains and Tauri/web deployment constraints.
- Recovery flows need explicit policy: admin reset, backup credentials, device loss, and employee offboarding.

### JWT

Use JWT only as a short-lived signed claim carrier for APIs, not as an unrevokable long-lived session store:

- Required registered claims: `iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, and `jti` where appropriate.
- Include tenant/legal entity, workplace, role family, assurance level, and device/session posture as bounded claims or policy lookup references.
- Validate issuer, audience, signature algorithm, expiration, not-before, and token ID/revocation state at every API boundary.
- Prefer asymmetric signing for service-to-service verification once multiple Rust services exist.
- Store browser tokens in secure httpOnly sameSite cookies when feasible; Tauri/mobile storage needs an explicit secure-storage decision.
- JWT claims do not replace RBAC + ABAC checks; they provide authenticated facts used by the policy engine.

## Authorization and Zero Trust fit

- SAP-like role-specific UX maps to RBAC role families.
- Korean SME legal entity/workplace/department/document state maps to ABAC attributes.
- Zero Trust means every API, worker, CronJob, desktop command, and integration import validates identity, authorization, payload, tenant scope, and audit trail.
- Frontend/Tauri UI can show capability hints but cannot enforce final access.

## Implementation handoff

1. Add an authentication/authorization contract document before implementing auth code.
2. Implement WebAuthn registration/authentication as a Rust backend slice with TypeScript frontend ceremonies.
3. Introduce JWT after identity/session policy is defined; test invalid alg, wrong audience, expired token, revoked `jti`, wrong tenant, and insufficient assurance.
4. Add policy tests for payroll export, trip report approval, KPI reflection, manager dashboard access, admin config changes, and migration Jobs.
5. Add the Korean labor-law policy registry as configuration-backed data with source/effective-date metadata before hardcoding yearly thresholds.
6. Keep Korean SME setup screens focused on defaults/templates instead of broad enterprise customization.
7. Add UI/UX maturity review gates for persona workspaces, lifecycle timelines, legal/policy explanations, manager rollups, accessibility, full single-language i18n, and performance budgets.

## Non-goals

- Do not copy SAP UI, terminology, module names, or proprietary content.
- Do not expand scope into full manufacturing/procurement ERP before payroll/HR/workflow/KPI are production-ready.
- Do not treat JWT possession as authorization.
- Do not ship password-only production access for privileged roles.
