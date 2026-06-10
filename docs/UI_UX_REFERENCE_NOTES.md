# UI/UX Reference Notes

Last updated: 2026-06-10

These notes are the bounded reference for the current Visual Ralph / AI-slop-cleaner UI pass. They translate source-backed enterprise product patterns into Bitween-specific implementation constraints.

## Sources reviewed

- SAP Fiori learning guidance (`https://learning.sap.com/courses/ui-development-with-sap-fiori/working-with-sap-fiori-design-guidelines_ab11c169-54de-4f51-87b9-f61c8a5198be`): choose layout/floorplan based on the user requirement and information shape; dynamic pages, flexible-column layouts, worklists, object pages, wizards, and overview pages each serve different jobs.
- Palantir Foundry Ontology guidance (`https://www.palantir.com/docs/foundry/ontology/overview`): model real operational objects, links, actions, functions, dynamic security, governance, and edit history as the substrate for workflow apps.
- n8n editor guidance (`https://docs.n8n.io/courses/level-one/chapter-1/`): workflow builders need a clear canvas, node/step model, add/edit affordances, and visible node actions without turning every screen into a text dashboard.
- n8n node guidance (`https://docs.n8n.io/workflows/components/nodes/`): nodes are the action/data-processing building blocks of a workflow, so Bitween workflow steps must represent executable business operations rather than decorative cards.
- Zapier Paths guidance (`https://help.zapier.com/hc/en-us/articles/8496288555917-Add-branching-logic-to-Zap-workflows-with-Paths`): branching is added through a step/plus affordance and creates named branches; Bitween needs explicit branch wiring and validation rather than hidden conditional text.
- monday workflow builder guidance (`https://support.monday.com/hc/en-us/articles/11065311570066-Get-started-with-AI-workflows`, `https://developer.monday.com/apps/docs/monday-workflows`): visual workflow builders combine blocks/triggers/actions/conditions in one visual space; Bitween should keep a palette, central canvas, and inspector/editor instead of a flat list of text cards.
- Material Design spacing/card guidance (`https://m3.material.io/foundations/layout/grids-spacing/spacing`, `https://m3.material.io/components/cards/guidelines`): spacing groups content and directs attention; cards need clear hierarchy and should not become uniform filler grids.
- 자료함/cloud intake benchmark (`docs/ARCHIVE_INTAKE_CLOUD_NATIVE.md`): best-in-class archive/intake products separate object payloads from metadata/workflow state, keep versioning/permissions/sensitivity first-class, quarantine untrusted uploads, rescue schema drift, and route ambiguous data to human review instead of silently admitting faulty rows.

## Bitween application rules

1. Home uses a bento/operator cockpit: today, this week, follow-ups, month close. No readiness wall, no generic marketing text.
2. HR is a management surface: add/remove/manage employees and HR lifecycle status. HR source close feeds payroll, but is not the payroll screen.
3. Payroll is a close-workflow surface: scope plus payroll-owned steps only.
4. Workflow is a separate corporate logic/canvas/editor surface: show routing, ownership, and editable state. 전자결재/approval is signing/approval only.
   - The workflow builder uses a three-zone editing pattern: step palette, canvas/analytics toolbar, and selected-step inspector. Wiring must be visible and persisted through handles/chips/forms; execution must produce auditable business data effects.
5. 자료함 is governed intake/export: any file/original/attachment/blob → RustFS archive → bounded extraction → PostgreSQL staging where appropriate → human mapping/anomaly review → admission/export/archive.
6. Topbar is global action utility: notifications, messages, help, settings, profile/sign out. Settings is not left navigation.
7. `?` help is contextual overlay; onboarding guidance must not become permanent body clutter.
8. Technical source/contract diagnostics live in automated verification/docs only.
9. Numbered stub-like workflow cards are unacceptable; cards must show role-relevant work, not placeholder sequence numbers or implementation internals.
10. Cards use hierarchy: emphasized focus card for current work, compact vertical rows for actionable lists, horizontal canvas for process relationships, dense table for HR records.
11. Sensitive data and write-path persistence must move to Rust/PostgreSQL with JWT/WebAuthn/authorization hardening before production; PostgreSQL is the relational system of record for metadata, staging, review, and admitted business data.
