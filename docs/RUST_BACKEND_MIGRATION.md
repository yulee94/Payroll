# Idiomatic Rust backend rewrite backlog

## Status

Backlog / not started as a standalone migration. This is a production-quality rewrite track and is not an MVP shortcut.

## Goal

Rewrite backend code in idiomatic Rust while preserving the observable business behavior already covered by compatibility tests. The target runtime is the Kubernetes-native stack documented in `docs/KUBERNETES_NATIVE_STACK.md`.

## Required execution disciplines

- **Incremental implementation:** migrate thin vertical slices behind stable contracts; no big-bang rewrite.
- **Source-driven development:** before choosing or using Rust/Kubernetes libraries, verify current official docs and record the source in an ADR or implementation note.
- **Test-driven development:** write characterization tests for current behavior, then Rust contract/parity tests before implementation.
- **Doubt-driven development:** run adversarial review for architecture, migration boundaries, tenant isolation, concurrency, data migration, and security decisions.
- **Code review and quality:** every slice needs independent review across correctness, readability, architecture, security, and performance before merge.
- **Code simplification:** remove compatibility code only after parity is proven; avoid duplicating existing complexity in Rust.

## Migration phases

1. **Inventory and boundaries**
   - Map Python compatibility modules to domain capabilities.
   - Freeze external DTOs and state transitions.
   - Identify tenant/legal-entity authorization invariants.

2. **Contract and characterization tests**
   - Lock payroll, workflow, business-trip lifecycle, KPI, org/role, mobile attendance, and AI policy behavior.
   - Keep tests DAMP and outcome-focused.

3. **Rust architecture ADRs**
   - Choose HTTP framework, async runtime, persistence library, validation approach, error model, observability, and Kubernetes packaging with official-source citations.
   - Reject unsupported or undocumented patterns explicitly.

4. **First production slice**
   - Expand `crates/payroll-api` into the first service boundary or create a dedicated Rust API service crate.
   - Ship one endpoint family with Rust tests, TypeScript contract alignment, and compatibility parity.

5. **Workflow and trip lifecycle slice**
   - Port document state, execution tasks, business-trip lifecycle, overdue evaluation, escalation, report proof, and KPI reflection.
   - Preserve legal-tenant scoping and proof-gated transitions.

6. **Persistence and migration**
   - Move production state to a database/object-storage layer behind Rust repositories.
   - Run schema/data migrations as Kubernetes Jobs with audit evidence.

7. **Kubernetes productionization**
   - Add container builds, Deployments, Services, Ingress/Gateway route, ConfigMaps, Secrets, probes, HPA, CronJobs, and migration Jobs.
   - Store release manifests or Helm/Kustomize overlays under a dedicated deployment surface such as `deploy/kubernetes/`.
   - Verify readiness/liveness behavior and safe shutdown.

8. **Decommission compatibility code**
   - Prove zero production usage.
   - Remove compatibility adapters, tests, and docs in separate reviewable commits.

## Non-goals

- Do not start a broad Rust rewrite inside an unrelated feature gate.
- Do not treat local compatibility UI or JSON runtime stores as production deployment architecture.
- Do not add dependencies based on memory or popularity alone.
