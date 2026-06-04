# Spec: Rust payroll social-insurance calculation slice

## Objective
Move the deterministic supplied-input Korean social-insurance calculation from Python compatibility code into Rust. Rust should preserve the observable behavior of `insurance.calculate_insurance` and `utils.calc_employment_insurance` once callers supply taxable pay, optional preset pension/health values, and an already-resolved insurance-exempt flag.

Python may still parse employee identity numbers, determine age/KCOMWEL eligibility, read roster/master workbooks, apply EDI premium overrides, and mutate workbook/payroll rows in this slice. Rust owns only the pure calculation from supplied numeric inputs to pension, health, long-term-care, employment insurance, and total.

## Tech Stack
- Rust crate: `crates/payroll-api` on Rust 2024 / Rust 1.96 with existing `serde`/`serde_json` only; no new runtime dependencies.
- Compatibility sources: `insurance.py` (`calculate_insurance`, constants) and `utils.py` (`round_won`, `round_won_tens`, `calc_employment_insurance`).
- Contract surfaces: `docs/PAYROLL_API_CONTRACT.md`, `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`.

## Commands
- Format: `cargo fmt --check`
- Rust tests: `cargo test --workspace`
- Buck target: `buck2 test //crates/payroll-api:payroll_api_test`
- Python contract tests: `/tmp/payroll-policy-venv/bin/python -m unittest tests.test_payroll_api_contract -v`
- TypeScript contract: `npm run typecheck --prefix frontend`
- Diff hygiene: `git diff --check`
- Bounded lint gate: `cargo clippy --workspace -- -D warnings -A clippy::too_many_arguments -A clippy::derivable_impls -A clippy::large_enum_variant`

## Project Structure
- `crates/payroll-api/src/social_insurance.rs` — constants, DTOs, and pure social-insurance calculation logic.
- `crates/payroll-api/src/service.rs` — service facade method for supplied-input social-insurance calculation.
- `crates/payroll-api/src/lib.rs` and `crates/payroll-api/BUCK` — public exports and Buck source list.
- `frontend/src/contracts/payrollApi.ts`, `services/payroll_api_contract.py`, `tests/test_payroll_api_contract.py` — DTO contract alignment.
- `docs/` — API and migration checkpoint docs.

## Code Style
Rust social-insurance calculation stays pure and deterministic: callers supply numeric payroll inputs and pre-resolved exemption status. Rust returns stable DTO fields without reading employee masters, identities, EDI files, settings, or workbooks.

```rust
let result = calculate_social_insurance(SocialInsuranceInput::new(3_000_000.0));
assert_eq!(result.total, 282_122);
```

## Testing Strategy
- Add Rust unit tests for base-rate calculation, pension floor/ceiling clamps, preset pension/health precedence, exemption zeroing, Python-compatible won/tens rounding, serialization shape, and service delegation.
- Add Python contract tests and TypeScript DTO definitions so frontend/server wrappers can rely on stable field names.
- Keep Python compatibility behavior as parity source; this slice does not replace identity/KCOMWEL/EDI/workbook orchestration.

## Boundaries
- Always: preserve pension rate `0.045`, health rate `0.03545`, long-term-care ratio `0.1295`, employment-insurance worker rate `0.009`, pension floor `390_000`, pension ceiling `6_170_000`, positive preset precedence, Python-compatible half-even won rounding, employment insurance tens rounding, and exemption zeroing.
- Ask first: move identity parsing, KCOMWEL age-65 decisions, EDI premium import/override, employee-master lookup, workbook parsing/writing, or final payroll record mutation into Rust.
- Never: commit payroll outputs, employee rosters, tenant runtime data, credentials, local tax/insurance files, or generated runtime folders.

## Success Criteria
- Rust exposes `SocialInsuranceInput`, `SocialInsuranceResult`, `calculate_social_insurance`, `calculate_employment_insurance`, and `PayrollApiService::calculate_social_insurance(input)`.
- Rust preserves Python-compatible supplied-input insurance calculation behavior.
- Contracts/docs identify Rust as owner of supplied-input social-insurance calculation while Python remains the identity/KCOMWEL/EDI/workbook bridge.
- All listed verification commands pass locally or have an explicit external blocker.

## Task Checklist
- [x] Add failing Rust tests for base rates, clamps, presets, exemption, rounding, serialization, and service behavior.
- [x] Implement social-insurance DTOs and pure calculation logic without new dependencies.
- [x] Export the social-insurance API and wire service facade/Buck source list.
- [x] Update TypeScript/Python contract metadata and contract tests.
- [x] Update migration and API docs with the new checkpoint.
- [x] Run local verification and self-review.
- [x] Commit, PR, review, merge, and resync.
