# Spec: Rust payroll EI 65+ decision slice

## Objective
Move the deterministic payroll decision for Korean age-65+ employment-insurance deduction from legacy compatibility code into Rust. Rust should preserve the observable behavior of `core.payroll.employment_insurance_65.resolve_ei_65_for_payroll` for valid payroll periods once a Rust service has supplied the latest KCOMWEL verification record, the resolved site management number, employee labels, and the tenant default for unknown status.

G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

## Tech Stack
- Rust crate: `crates/payroll-api` with existing `serde`/`serde_json` only; no new runtime dependencies.
- Historical source: pre-G028 compatibility source was removed; keep parity evidence in Rust tests, TypeScript contracts, and documented fixtures.
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`.

## Commands
- Format: `buck2 build '<target>[clippy.txt]'`
- Rust tests: `buck2 test //...`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- G028 retired the former compatibility gate; use Buck2 Rust tests plus TypeScript gates from AGENTS.md.
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `buck2 build '<target>[clippy.txt]'`

## Project Structure
- `crates/payroll-api/src/employment_insurance_65.rs` — age parsing, supplied verification DTO, payroll decision DTO, and pure decision logic.
- `crates/payroll-api/src/service.rs` — service facade method for the supplied-input EI 65+ decision.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck source list.
- `Rust parity test` and `Rust parity test` — Rust parity coverage for compatibility behavior.
- `frontend/src/contracts/payrollApi.ts`, `Rust-owned contract`, `Rust parity test` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust EI 65+ decision stays pure and deterministic for valid periods: callers supply identity text, payroll period, display labels, resolved site management number, the optional latest KCOMWEL verification record, and the unknown default. Rust returns the stable decision without reading settings, storage, network APIs, workbooks, or payroll invoice rows.

```rust
let result = resolve_ei_65_for_payroll(&Ei65PayrollInput::new("500615-1", "2026-05")
    .with_employee_name("미확인")
    .with_unknown_default(Ei65UnknownDefault::Skip));
assert_eq!(result.status, Ei65EligibilityStatus::Unknown);
assert!(!result.deduct_employment_insurance);
```

## Testing Strategy
- Add Rust unit tests for Korean RRN birth-date parsing, valid-period month-end age checks, under-65 liable behavior, 65+ zero-premium exemption, positive-premium liability, unknown skip/deduct defaults, warning labels, serialization field values, and service delegation.
- Keep Rust parity tests green to prove the compatibility adapter still behaves the same while Rust takes ownership of the supplied-input domain rule.
- Add Rust/TypeScript contract tests and TypeScript DTO definitions so frontend/server wrappers can rely on stable enum and field names.

## Boundaries
- Always: preserve legacy-compatible age threshold (65), valid-period month-end basis, premium `<= 0` as `exempt`, premium `> 0` as `liable`, unknown-default `skip`/`deduct` behavior, Korean warning wording, and `premium_amount: null` for unknown/under-65 decisions.
- Ask first: move KCOMWEL CSV import, local verification storage, live KCOMWEL API calls, tenant/site settings lookup, employee matching, payroll invoice mutation, EDI premium application, or workbook I/O into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, local KCOMWEL cache files, or generated runtime folders.

## Success Criteria
- Rust exposes `Ei65EligibilityStatus`, `Ei65UnknownDefault`, `Ei65VerificationRecord`, `Ei65PayrollInput`, `Ei65PayrollResult`, `age_years_from_korean_identity`, `is_age_65_plus_for_period`, and `resolve_ei_65_for_payroll`.
- `PayrollApiService` delegates the supplied-input EI 65+ decision through a framework-neutral method.
- Rust preserves legacy-compatible valid-period age determination, verification interpretation, unknown-default warning/result fields, and serialized DTO field names.
- G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add failing Rust tests for age parsing, decision branches, serialization, and service delegation.
- [x] Implement EI 65+ DTOs and pure decision logic without new dependencies.
- [x] Export the EI 65+ API and wire service facade/Buck source list.
- [x] Update TypeScript/Rust contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [x] Commit, PR, review, merge, and resync.
