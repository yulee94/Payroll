# Payroll Automation API Contract

Bitween payroll automation is migrating to a Rust backend service for Kubernetes-native production. The Rust API is authoritative; this contract documents Rust-owned DTOs, TypeScript-facing fields, and remaining Rust service backlog.

## Entry Point

Planned HTTP endpoint:

- `POST /api/payroll/v1/runs`
- Content-Type: `application/json`
- Production owner: Rust backend service deployed through Kubernetes (`docs/KUBERNETES_NATIVE_STACK.md`)

Rust transition entry point:

- Rust crate: `crates/payroll-api`
- Service facade: `bitween_payroll_api::PayrollApiService`
- Validation function: `bitween_payroll_api::validate_payroll_api_payload(payload, policy_snapshot)`
- Policy-resolved validation function: `PayrollApiService::validate_run_payload_with_policy_settings(payload, settings)`
- Attendance aggregation function: `PayrollApiService::aggregate_attendance_records(records, workplace, attendance_policy)`
- Workplace monthly-hours application function: `PayrollApiService::apply_monthly_hours_to_invoice(invoice, workplace, workplace_hours_policy)`
- Invoice audit row function: `PayrollApiService::audit_invoice_row(invoice, workplace, workplace_hours_policy, ledger_record, fixed_hours_profile)`
- Invoice audit batch function: `PayrollApiService::audit_invoice_batch(items, workplace)`
- Social-insurance calculation function: `PayrollApiService::calculate_social_insurance(input)`
- Earnings calculation function: `PayrollApiService::calculate_payroll_earnings(input)`
- Salary calculation function: `PayrollApiService::calculate_payroll_salary(input)`
- Deduction finalization function: `PayrollApiService::finalize_payroll_deductions(input)`
- Employment-insurance 65+ decision function: `PayrollApiService::resolve_ei_65_for_payroll(input)`
- EDI insurance premium application function: `PayrollApiService::apply_edi_premiums_to_invoice(invoice, edi_record, edi_config, payroll_period)`
- Site-benefits application function: `PayrollApiService::apply_site_benefits_to_invoice(invoice, site_benefits_config, payroll_period)`
- Fixed-hours application function: `PayrollApiService::apply_fixed_hours_to_invoice(invoice, fixed_hours_profile, workplace)`
- Execution plan function: `PayrollApiService::plan_run_request(request, policy_snapshot)`
- Run-result response function: `PayrollApiService::run_response(result, request_id)`
- Health function: `PayrollApiService::health()`
- Readiness function: `PayrollApiService::readiness(checks)`
- Authorization function: `PayrollApiService::authorize_run_request(request, principal, action)`
- Purpose: move payroll request validation, scope parsing, input-method resolution, operation-policy resolution precedence, attendance aggregation, workplace monthly-hours application, invoice audit row evaluation and batch summarization, social-insurance calculation, supplied-input earnings/gross/taxable-pay calculation, supplied-input salary calculation, final deduction/net-pay calculation, employment-insurance 65+ payroll decisions, EDI insurance premium payroll row application, site-benefits payroll row application, fixed-hours payroll row application, execution routing/planning, run-result response envelope shaping, probe-safe service boundary responses, and tenant/RBAC/ABAC authorization decisions into Rust.

Compatibility adapter:

- `Rust-owned contract(payload)` is retired; Rust service contracts are authoritative.
- `Rust-owned contract(result, request_id=...)` is retired; `PayrollApiService::run_response(result, request_id)` is authoritative.
- `Rust-owned contract(payload)` is retired; Rust validation contracts are authoritative.

TypeScript frontend contract:

- Type file: `frontend/src/contracts/payrollApi.ts`
- Purpose: keep frontend request/response field names aligned with Rust API responses.

Validation endpoint:

- `POST /api/payroll/v1/runs/validate`
- Alternative compatibility behavior: `run_payroll_api(payload)` with `validate_only: true` or `dry_run: true` returns validation only.

Health endpoint:

- `GET /api/payroll/v1/healthz`
- Purpose: cheap liveness-style service response for routers, probes, and diagnostics.

Readiness endpoint:

- `GET /api/payroll/v1/readiness`
- Purpose: expose Rust service readiness checks for policy, persistence, compatibility fallback, and future tenant dependencies.


## Attendance Aggregation

remaining Rust service backlog must parse `.csv`, `.txt`, `.xlsx`, and `.xlsm` attendance uploads and may still build invoice-compatible workbooks. Once attendance rows are normalized, Rust owns the payroll-domain aggregation rule through `aggregate_attendance_records(records, workplace, attendance_policy)` and `PayrollApiService::aggregate_attendance_records(records, workplace, attendance_policy)`.

Aggregation invariants:

1. Records are grouped by supplied `name_key`, or by a whitespace-normalized employee name when `name_key` is absent.
2. `late_grace_minutes` and `early_leave_grace_minutes` are applied per source record before totals are rounded.
3. Work, late/early, overtime, night, and special hours are rounded with legacy-compatible half-even rounding.
4. Invoice rows are sorted by employee name and keep zero-valued payroll amount fields until the payroll calculator fills them.
5. Compatibility invoice fields `_attendance_days` and `_attendance_input` remain present for downstream invoice/workbook bridges.

Example normalized input records:

```json
[
  {
    "name": "홍 길동",
    "dept": "Payroll",
    "workplace": "Site A",
    "work_hours": 4.0,
    "late_hours": 0.1667,
    "overtime_hours": 0.5,
    "night_hours": 1.0
  },
  {
    "name": "홍길동",
    "name_key": "홍길동",
    "dept": "Payroll",
    "workplace": "Site A",
    "work_hours": 4.0,
    "early_leave_hours": 0.0833,
    "overtime_hours": 0.5,
    "special_hours": 2.0,
    "leave_days": 1.0,
    "unpaid_days": 0.5
  }
]
```

Example invoice-compatible output row:

```json
{
  "row": 0,
  "name": "홍 길동",
  "dept": "Payroll",
  "hire_date": "",
  "workplace": "Site A",
  "base_days": 8.0,
  "work_days": 8.0,
  "unpaid_days": 0.5,
  "leave_days": 1.0,
  "ot_hours": 1.0,
  "night_hours": 1.0,
  "special_hours": 2.0,
  "early_leave_hours": 0.25,
  "subtotal": 0,
  "_attendance_days": 2,
  "_attendance_input": true
}
```

## Workplace Monthly-Hours Application

remaining Rust service backlog must load tenant/site/global settings and canonical workplace aliases. Once a workplace-hours policy has been supplied for an invoice-compatible payroll row, Rust owns the deterministic monthly-hours selection rule through `resolve_monthly_work_hours(invoice, workplace, workplace_hours_policy)`, `apply_monthly_hours_to_invoice(invoice, workplace, workplace_hours_policy)`, and `PayrollApiService::apply_monthly_hours_to_invoice(invoice, workplace, workplace_hours_policy)`.

Application invariants:

1. Invalid or missing modes fall back to `fixed`; missing, invalid, or non-positive policy hours fall back to 209.
2. Optional `daily_hours` is retained only when positive, and `break_minutes` only when non-negative.
3. Invoice `work_days` and `base_days` are clamped at zero before mode selection.
4. All five legacy-compatible modes remain stable: `fixed`, `invoice_work_days`, `invoice_base_days`, `work_or_fixed`, and `base_or_fixed`.
5. `_monthly_work_hours` and `_monthly_hours_source` preserve the Korean source-label wording used by payroll reviewers.

Example supplied policy:

```json
{
  "mode": "invoice_work_days",
  "hours": 209,
  "daily_hours": 8,
  "break_minutes": 60
}
```

Example application output:

```json
{
  "hours": 192,
  "source": "청구장: 청구서 근무시간",
  "invoice": {
    "workplace": "청구장",
    "work_days": 192,
    "base_days": 209,
    "_monthly_work_hours": 192,
    "_monthly_hours_source": "청구장: 청구서 근무시간"
  },
  "policy": {
    "mode": "invoice_work_days",
    "hours": 209,
    "daily_hours": 8,
    "break_minutes": 60
  }
}
```


## Invoice Audit Row

remaining Rust service backlog must resolve settings, match payroll ledger records, resolve employee fixed-hours profiles, and read workbooks. Once a single invoice row, workplace-hours policy, optional ledger record, and optional fixed-hours profile have been supplied, Rust owns the deterministic audit-row evaluation through `audit_invoice_row(invoice, workplace, workplace_hours_policy, ledger_record, fixed_hours_profile)` and `PayrollApiService::audit_invoice_row(invoice, workplace, workplace_hours_policy, ledger_record, fixed_hours_profile)`.

Audit invariants:

1. `status` remains either `pass` or `warn`, with Korean labels `정상` and `확인`.
2. Break-hour estimation uses positive `break_minutes` first; otherwise it falls back to the invoice `base_days - work_days - leave_days` gap when the I/J columns look hour-based.
3. Base-salary mismatch, missing invoice-hours, missing roster base-hourly, fixed-hours mismatch, and ledger monthly-hour mismatch flags preserve documented Korean wording.
4. Optional fixed-hours profiles reuse the Rust fixed-hours application/audit flags and prepend those flags before row-level warnings.
5. Settings lookup, record matching, fixed-profile resolution, workbook I/O, and UI text rendering remain legacy compatibility boundaries in this slice.

Example audit row output:

```json
{
  "name": "박감사",
  "workplace": "앰코",
  "status": "warn",
  "status_label": "확인",
  "flags": [
    "기본급 불일치: 산출 2,090,000원 vs 청구서 2,000,000원",
    "대장 적용시간(208h)과 재검열(209h) 상이"
  ],
  "base_days": 209,
  "work_days": 200,
  "break_hours": 9,
  "applied_monthly_hours": 209,
  "hours_source": "앰코: 고정 209시간",
  "policy_mode": "fixed",
  "policy_fixed_hours": 209,
  "base_hourly": 10000,
  "invoice_base_salary": 2000000,
  "calc_base_salary": 2090000,
  "formula": "기본시급 10,000원 × 209시간 = 2,090,000원",
  "fixed_hours_mode": false,
  "fixed_hours_source": ""
}
```

## Invoice Audit Batch

remaining Rust service backlog must resolve workplace settings, match payroll
ledger records by employee, resolve optional fixed-hours profiles, parse
workbooks, and render UI summary text. Once callers supply per-row
`InvoiceAuditBatchItem` values, Rust owns deterministic batch summarization
through `audit_invoice_batch(items, workplace)` and
`PayrollApiService::audit_invoice_batch(items, workplace)`.

Batch item fields:

- `invoice`: the same supplied-input invoice shape used by `audit_invoice_row`.
- `workplace`: optional per-row workplace override; empty values fall back to the
  batch `workplace`.
- `policy`: supplied workplace monthly-hours policy for that row.
- `record`: optional supplied ledger record.
- `fixed_profile`: optional supplied fixed-hours profile.

Batch result invariants:

1. Row order is preserved exactly as supplied.
2. `summary.total`, `summary.pass`, `summary.warn`, `pass_count`, and
   `warn_count` are derived from Rust row statuses.
3. The result keeps the caller-supplied batch `workplace` label.
4. Row-level status, flags, formulas, hour sources, and fixed-hours fields are
   produced by the Rust row auditor.
5. Settings lookup, ledger matching, fixed-profile resolution, workbook I/O, and
   UI text rendering remain legacy compatibility boundaries in this slice.

Example batch result shape:

```json
{
  "workplace": "앰코",
  "summary": {
    "total": 3,
    "pass": 2,
    "warn": 1
  },
  "rows": [
    {
      "name": "A",
      "status": "pass"
    },
    {
      "name": "B",
      "status": "warn"
    },
    {
      "name": "C",
      "status": "pass"
    }
  ],
  "pass_count": 2,
  "warn_count": 1
}
```




## Payroll Social-Insurance Calculation

remaining Rust service backlog must parse employee identity numbers, determine
age/KCOMWEL eligibility, read roster/master workbooks, apply EDI premium
overrides, and mutate workbook/payroll rows. Once callers supply taxable pay,
optional preset pension/health values, and an already-resolved
`insurance_exempt` flag, Rust owns the pure social-insurance calculation through
`calculate_social_insurance(input)` and
`PayrollApiService::calculate_social_insurance(input)`.

Social-insurance invariants:

1. `taxable_pay` is supplied after non-taxable pay has already been removed by
   compatibility code.
2. `insurance_exempt: true` zeroes pension, health, long-term-care, employment,
   and total worker contributions.
3. Positive `preset_national_pension` overrides pension-rate calculation after
   legacy-compatible won rounding.
4. Positive `preset_health_insurance` overrides health-rate calculation; long-
   term care is recalculated from the rounded health amount.
5. Pension-rate calculation clamps taxable pay to `390_000..6_170_000` before
   applying `0.045`.
6. Health insurance applies `0.03545`, long-term care applies `0.1295` to the
   rounded health amount, and employment insurance applies `0.009` rounded to the
   nearest 10 won.

Example social-insurance output:

```json
{
  "national_pension": 135000,
  "health_insurance": 106350,
  "long_term_care": 13772,
  "employment_insurance": 27000,
  "total": 282122,
  "insurance_exempt": false
}
```

## Payroll Earnings Calculation

remaining Rust service backlog must parse invoices, merge employee masters,
normalize strings/cell values, calculate social insurance and taxes, finalize
deductions, and assemble final payroll records. Once callers supply normalized
numeric earnings inputs, Rust owns the pure earnings, gross-pay,
non-taxable-pay, and taxable-pay calculation through
`calculate_payroll_earnings(input)` and
`PayrollApiService::calculate_payroll_earnings(input)`.

Earnings invariants:

1. Positive `ordinary_hourly` overrides `(base_salary + fixed_allowance) / 209`;
   otherwise Rust calculates ordinary hourly from the supplied base/fixed pay.
2. Overtime, night, holiday, overlap, weekly-holiday, meal, transport, other,
   and additional pay use legacy-compatible won rounding.
3. Weekly holiday pay is prorated by
   `min(weekly_work_hours, 40) / 40 * 8 * ordinary_hourly`.
4. Raw overtime/night/holiday amounts are used only when computed pay is
   non-positive and the raw value is not likely an hours value.
5. Raw overtime amount updates returned overtime hours; raw night and holiday
   amounts preserve the supplied hours.
6. Non-positive base salary falls back to `ordinary_hourly * 209` when ordinary
   hourly is positive.
7. `non_taxable_pay` is the meal allowance capped at `200_000`, and
   `taxable_pay` is `gross_pay - non_taxable_pay`.

Example earnings output:

```json
{
  "ordinary_hourly": 10478.47,
  "hours": {
    "overtime": 10.0,
    "night": 4.0,
    "holiday": 8.0
  },
  "earnings": {
    "base_salary": 2090000,
    "fixed_allowance": 100000,
    "overtime": 157177,
    "night": 20957,
    "holiday": 125742,
    "overlap_premium": 20957,
    "weekly_holiday": 73349,
    "meal": 121000,
    "transport": 50000,
    "other": 12346,
    "additional": 100000
  },
  "gross_pay": 2871528,
  "non_taxable_pay": 121000,
  "taxable_pay": 2750528
}
```

## Payroll Salary Calculation

remaining Rust service backlog must parse invoices, merge employee masters,
normalize strings/cell values, determine age/KCOMWEL or EDI overrides, write
workbooks, and assemble final payroll records. Once callers supply normalized
salary inputs, Rust owns the pure one-employee salary calculation through
`calculate_payroll_salary(input)` and
`PayrollApiService::calculate_payroll_salary(input)`.

Salary calculation invariants:

1. Salary calculation composes the Rust-owned earnings and social-insurance
   calculations from supplied inputs.
2. `taxable_pay` remains the earnings taxable pay (`gross_pay -
   non_taxable_pay`) used by `calculator.calculate_salary`.
3. Preset income tax is rounded to won and local income tax is rounded to won at
   10%, preserving `tax.calculate_tax` behavior for this calculator path.
4. `tax_method` uses calculator-compatible uppercase values: `PRESET` and
   `SIMPLIFIED_TABLE`.
5. `total_deductions` is social-insurance total plus income/local tax total, and
   `net_pay` is `gross_pay - total_deductions`.

Example supplied salary output:

```json
{
  "name": "홍길동",
  "emp_no": "E001",
  "department": "Payroll",
  "account_no": "111-222",
  "ordinary_hourly": 10478.47,
  "deductions": {
    "national_pension": 123774,
    "health_insurance": 97506,
    "long_term_care": 12627,
    "employment_insurance": 24750,
    "income_tax": 210000,
    "local_income_tax": 21000,
    "total": 489657
  },
  "gross_pay": 2871528,
  "non_taxable_pay": 121000,
  "taxable_pay": 2750528,
  "total_deductions": 489657,
  "net_pay": 2381871,
  "tax_method": "SIMPLIFIED_TABLE"
}
```

## Payroll Deduction Finalization

remaining Rust service backlog must parse workbooks, match employee rosters,
resolve social insurance, apply EDI/site/fixed-hour rules, and assemble final
payroll records. Once callers supply gross pay, insurance total, optional preset
income/local taxes, and any identity-guarantee insurance deduction, Rust owns the
pure final deduction and net-pay calculation through
`finalize_payroll_deductions(input)` and
`PayrollApiService::finalize_payroll_deductions(input)`.

Deduction invariants:

1. `taxable_pay` is `gross_pay - insurance_total` exactly as supplied.
2. Positive `preset_income_tax` overrides the simplified tax table.
3. Positive `preset_local_income_tax` overrides automatic local tax only when
   preset income tax is used.
4. Automatic local tax for preset income tax is rounded to the nearest 10 won,
   matching `payroll_builder`.
5. Simplified-table local tax is rounded to the nearest won, matching
   `tax.calculate_tax`.
6. `identity_guarantee_insurance_deduction` contributes to `total_deduction` by
   absolute value.
7. `net_pay` is `gross_pay - total_deduction` with legacy-compatible won
   rounding.

Simplified income-tax brackets preserve the legacy compatibility table for one
monthly dependent: `0`, `8_000`, `42_000`, `120_000`, `210_000`, `310_000`,
`420_000`, `650_000`, `920_000`, `1_450_000`, and `2_100_000` at the documented
upper bounds through `10_000_000`; amounts above that use
`max(0, taxable_pay - 1_500_000) * 0.03` rounded to won.

Example finalization output:

```json
{
  "gross_pay": 3000000,
  "insurance_total": 300000,
  "taxable_pay": 2700000,
  "income_tax": 210000,
  "local_income_tax": 21000,
  "tax_total": 231000,
  "identity_guarantee_insurance_deduction": -20000,
  "total_deduction": 551000,
  "net_pay": 2449000,
  "method": "simplified_table"
}
```

## Employment-Insurance 65+ Payroll Decision

remaining Rust service backlog must import and persist KCOMWEL verification
records, resolve site management numbers from payroll settings, match employees,
call future live KCOMWEL APIs, coordinate supplied EDI premium inputs, mutate
payroll invoice rows, and read/write workbooks. Once callers supply identity, a valid payroll period,
labels, a resolved site management number, an optional latest KCOMWEL
verification record, and the tenant unknown-status default, Rust owns the pure
age-65+ employment-insurance decision through
`resolve_ei_65_for_payroll(input)` and
`PayrollApiService::resolve_ei_65_for_payroll(input)`.

Decision invariants:

1. Valid payroll periods use the calendar month end as the age basis.
2. Korean RRN century codes and six-digit birth dates use legacy-compatible age
   parsing for the supplied period.
3. Workers below age 65 return `liable`, `premium_amount: null`, and
   `deduct_employment_insurance: true` without requiring a KCOMWEL record.
4. Supplied KCOMWEL premiums `<= 0` return `exempt` and suppress employment
   insurance deduction.
5. Supplied positive KCOMWEL premiums return `liable` and keep employment
   insurance deduction enabled.
6. Missing records return `unknown` and apply the supplied unknown default:
   `skip` suppresses deduction and `deduct` keeps deduction enabled.
7. Unknown warnings preserve the documented Korean payroll-review wording
   compatibility code.

Example supplied-input decision:

```json
{
  "status": "exempt",
  "premium_amount": 0,
  "management_no": "1234567890",
  "deduct_employment_insurance": false,
  "warning": "",
  "default_action": "skip"
}
```

Example unknown decision:

```json
{
  "status": "unknown",
  "premium_amount": null,
  "management_no": "1234567890",
  "deduct_employment_insurance": false,
  "warning": "김순자: 만 65세 이상 고용보험 KCOMWEL 확인 미완료 → 설정 기본값(공제 생략) 적용",
  "default_action": "skip"
}
```


## EDI Insurance Premium Application

remaining Rust service backlog must import CSV/Excel EDI files, persist premium
records, call future EDI providers, resolve tenant/site settings and site
management numbers, match employees, and coordinate workbook I/O. Once callers
supply a single invoice row, EDI config, an optional latest premium record, and a
payroll period, Rust owns the deterministic row-field application through
`apply_edi_premiums_to_invoice(invoice, edi_record, edi_config, payroll_period)`
and
`PayrollApiService::apply_edi_premiums_to_invoice(invoice, edi_record, edi_config, payroll_period)`.

Config and source fields:

- `use_edi_premiums`: false returns `applied: false` with `EDI 보험료 사용 꺼짐`.
- `respect_age_exempt`: preserves pension, health, and long-term-care fields
  when the invoice row is already age-exempt.
- `source`: `manual`, `import`, `api`, or `calculated`; unknown values normalize
  to `import`.

Application invariants:

1. Missing records return `applied: false` with `EDI 보험료 없음` and leave the
   invoice unchanged.
2. Positive EDI pension, health, long-term-care, employment, and industrial
   accident values override the supplied invoice row.
3. Missing long-term-care falls back to legacy-compatible
   `round(health_insurance * 0.1295)` when EDI health insurance is positive.
4. A zero EDI employment premium clears existing employment insurance for
   non-age-exempt rows; positive employment premiums still apply.
5. Employer/employee industrial-accident split fields preserve supplied zero
   values.
6. `insurance_total` is recalculated from pension, health, long-term-care, and
   employment insurance, not industrial accident fields.
7. Applied rows receive `edi_premium_source`, `edi_premium_badge`,
   `edi_premium_period`, `edi_premium_fetched_at`, and
   `edi_premium_source_type` metadata.

Example application output:

```json
{
  "applied": true,
  "message": "EDI 보험료 적용",
  "invoice": {
    "name": "김철수",
    "employee_id": "E02",
    "workplace": "한국앰코",
    "national_pension": 80000,
    "health_insurance": 40000,
    "long_term_care": 5180,
    "employment_insurance": 20000,
    "industrial_accident": 3000,
    "industrial_accident_employer": 2000,
    "industrial_accident_employee": 0,
    "insurance_total": 145180,
    "insurance_exempt": false,
    "edi_premium_source": true,
    "edi_premium_badge": "EDI 조회",
    "edi_premium_period": "2026-06",
    "edi_premium_fetched_at": "2026-06-10T09:00:00",
    "edi_premium_source_type": "manual"
  }
}
```

## Site-Benefits Application

remaining Rust service backlog must resolve site/tenant/global benefit settings,
canonicalize workplace aliases, inspect and persist the yearly
identity-insurance ledger, parse workbooks, and recalculate payroll totals. Once
callers supply a single invoice row, resolved site-benefits config, and payroll
period, Rust owns the deterministic row-field application through
`apply_site_benefits_to_invoice(invoice, site_benefits_config, payroll_period)`
and
`PayrollApiService::apply_site_benefits_to_invoice(invoice, site_benefits_config, payroll_period)`.

Config fields:

- `workers_day_allowance`: `{ enabled, default_amount, auto_from_invoice }`
- `workers_day_source`: `site`, `tenant`, or `global`
- `identity_guarantee_insurance`: `{ enabled, annual_amount, billing_month }`
- `identity_insurance_source`: `site`, `tenant`, or `global`
- `identity_insurance_already_applied`: supplied yearly-ledger decision

Application invariants:

1. Config amounts are clamped at zero and identity billing month is clamped to
   `1..12`.
2. Workers' Day invoice-driven mode uses a positive supplied `workers_day_pay`
   regardless of period month.
3. Workers' Day fixed-default mode applies only in May when `default_amount` is
   positive.
4. Identity-guarantee insurance applies as a negative annual amount only in the
   configured billing month.
5. `identity_insurance_already_applied` suppresses the annual deduction without
   Rust reading or writing compatibility ledgers.

Example application output:

```json
{
  "workers_day_allowance": 12000,
  "identity_guarantee_insurance_deduction": -20000,
  "workers_day_source": "site",
  "identity_insurance_source": "site",
  "invoice": {
    "name": "박민수",
    "workplace": "한국앰코",
    "base_salary": 2090000,
    "workers_day_pay": 99999,
    "workers_day_allowance": 12000,
    "identity_guarantee_insurance_deduction": -20000,
    "_workers_day_source": "site",
    "_identity_insurance_source": "site"
  }
}
```

## Fixed-Hours Application

remaining Rust service backlog must load HR contracts, site job-group templates, payroll settings, and employee rosters. Once a fixed-hours profile has been resolved for an invoice-compatible payroll row, Rust owns the payroll-domain application rule through `apply_fixed_hours_to_invoice(invoice, fixed_hours_profile, workplace)` and `PayrollApiService::apply_fixed_hours_to_invoice(invoice, fixed_hours_profile, workplace)`.

Application invariants:

1. Resolved profiles are normalized before application; monthly hours default to 209, or `daily_fixed_hours × 26` when monthly hours are absent.
2. Original invoice `work_days`, `base_days`, `ot_hours`, `special_hours`, and `special_ext_hours` are preserved under `_invoice_*` fields before replacement.
3. `fixed_extension_hours` replaces `ot_hours` when positive, and `fixed_overtime_hours` replaces `special_hours` when positive.
4. `_preserve_reference_hours` keeps the original invoice work/base hours for application while audit flags still compare against the resolved profile.
5. Audit flags preserve the legacy compatibility Korean labels for the profile source, pay type, and hour mismatches.

Example fixed-hours profile:

```json
{
  "fixed_hours_mode": true,
  "monthly_fixed_hours": 209,
  "daily_fixed_hours": 0,
  "fixed_overtime_hours": 10,
  "fixed_extension_hours": 20,
  "pay_type": "monthly_salary",
  "job_group": "경비",
  "source": "contract",
  "source_label": "근로계약서 기준 고정",
  "contract_id": "c1"
}
```

Example application output:

```json
{
  "applied": true,
  "invoice": {
    "name": "최연봉",
    "workplace": "강남경비",
    "work_days": 209,
    "base_days": 209,
    "ot_hours": 20,
    "special_hours": 10,
    "special_ext_hours": 2,
    "_invoice_work_days": 150,
    "_invoice_base_days": 150,
    "_invoice_ot_hours": 5,
    "_invoice_special_hours": 3,
    "_invoice_special_ext_hours": 2,
    "_monthly_work_hours": 209,
    "_monthly_hours_source": "근로계약서 기준 고정",
    "_fixed_hours_mode": true,
    "_fixed_hours_source": "contract",
    "_fixed_hours_pay_type": "monthly_salary",
    "_fixed_hours_job_group": "경비"
  },
  "audit_flags": [
    "근로계약서 기준 고정 (경비)",
    "급여형태: 연봉직",
    "청구서 연장(5h) ≠ 계약 고정(20h)",
    "청구서 특근(3h) ≠ 계약 고정(10h)",
    "청구서 근무시간(150h) ≠ 계약 월시간(209h)"
  ]
}
```

## Operation Policy Resolution

G028 current-state note: the former repo-owned compatibility bridge is decommissioned; missing behavior must be restored through Rust/Buck2 services or TypeScript contracts only.

Resolution precedence:

1. `site` — canonical or aliased workplace has a site `payroll_operation_policy` override.
2. `tenant` — tenant-level `payroll_operation_policy` exists and no site override matched.
3. `global` — built-in Rust default when neither site nor tenant policy exists.

Resolver output shape:

```json
{
  "workplace": "Site A",
  "policy": {
    "input_basis": "hybrid",
    "payday": "25일",
    "show_setup_guide": true,
    "policy_note": "",
    "attendance": {
      "enabled": true,
      "source": "biometric",
      "rounding_minutes": 1,
      "late_grace_minutes": 0,
      "early_leave_grace_minutes": 0,
      "overtime_rounding_minutes": 1,
      "missing_clock_policy": "warn",
      "holiday_source": "invoice"
    }
  },
  "source": "site",
  "has_site_override": true
}
```

The selected policy is normalized in Rust before validation response serialization. Workplaces are trimmed, and alias/canonical matching is supported from the supplied settings snapshot; Rust-owned org configuration and settings persistence remain future slices.


## Execution Planning

Rust now owns deterministic payroll execution planning once a request has been parsed and an operation-policy snapshot has been resolved. The plan does not generate payroll outputs yet; it tells future HTTP, worker, Tauri, or Kubernetes wrappers which source paths and Rust-owned execution steps will run before payroll output generation is fully service-backed.

Rust entry points:

- `plan_payroll_execution(request, policy_snapshot)`
- `PayrollApiService::plan_run_request(request, policy_snapshot)`

Planner invariants:

1. Explicit `invoice`, `attendance`, and `mixed` requests keep the caller-requested input type when required source paths exist.
2. `auto` requests resolve the executable input type from the normalized Rust operation policy.
3. `mixed` requests with only an attendance source plan an attendance-only Rust execution path with an explicit warning.
4. Every step names `backend: "rust_native"` and `executor: "bitween_payroll_api::PayrollApiService"`.

Example plan:

```json
{
  "ok": true,
  "scope": "Acme/Site A/2026-05",
  "scope_key": "Acme\u001fSite A\u001f2026-05",
  "affiliate": "Acme",
  "workplace": "Site A",
  "period": "2026-05",
  "input_type": "mixed",
  "requested_input_type": "auto",
  "backend": "rust_native",
  "executor": "bitween_payroll_api::PayrollApiService",
  "source_paths": {
    "invoice": "rustfs://bitween-payroll/inbox/invoice_2026-05.xlsx",
    "attendance": "rustfs://bitween-payroll/inbox/attendance_2026-05.csv"
  },
  "missing_source_paths": [],
  "steps": [
    {
      "kind": "extract_attendance",
      "backend": "rust_native",
      "input": "rustfs://bitween-payroll/inbox/attendance_2026-05.csv",
      "output": "attendance_rows",
      "description": "Extract attendance rows with the Rust payroll service contract before merging them into the invoice workbook."
    },
    {
      "kind": "attach_attendance_sheet",
      "backend": "rust_native",
      "input": "rustfs://bitween-payroll/inbox/invoice_2026-05.xlsx + attendance_rows",
      "output": "generated:mixed_invoice",
      "description": "Attach the attendance sheet to the supplied invoice workbook through the Rust payroll service contract."
    },
    {
      "kind": "process_invoice",
      "backend": "rust_native",
      "input": "generated:mixed_invoice",
      "output": "payroll_outputs",
      "description": "Process the merged invoice workbook through the Rust payroll service contract."
    }
  ],
  "operation_policy": {
    "input_basis": "hybrid",
    "payday": "25일",
    "show_setup_guide": true,
    "policy_note": "",
    "attendance": {
      "enabled": true,
      "source": "biometric",
      "rounding_minutes": 1,
      "late_grace_minutes": 0,
      "early_leave_grace_minutes": 0,
      "overtime_rounding_minutes": 1,
      "missing_clock_policy": "warn",
      "holiday_source": "invoice"
    }
  },
  "operation_policy_source": "tenant",
  "warnings": []
}
```

## Kubernetes production behavior

- The Rust API is deployed as a Kubernetes Deployment behind a Service.
- External traffic reaches the API through the cluster ingress/gateway layer.
- Runtime configuration is provided through ConfigMaps; secrets and API credentials are provided through Secrets or an external secret manager.
- The service must expose readiness/liveness endpoints before production rollout.

## Request

`scope` accepts three shapes.

```json
{
  "scope": {
    "affiliate": "Acme",
    "workplace": "Site A",
    "period": "2026-05"
  }
}
```

Flat shape:

```json
{
  "affiliate": "Acme",
  "workplace": "Site A",
  "period": "2026-05"
}
```

Scope key shape:

```json
{
  "scope": "Acme/Site A/2026-05"
}
```

The slash form is the recommended external API representation. Internal `PayrollScope.key` values remain accepted for compatibility.

Fields:

| Field | Alias | Required | Description |
| --- | --- | --- | --- |
| `request_id` | `requestId`, `metadata.request_id` | No | Caller trace ID returned in success/error responses. |
| `scope` | - | Yes | Affiliate, workplace, and payroll month. |
| `period` | - | Yes | `YYYY-MM` format. |
| `input_type` | `inputType` | No | `auto`, `invoice`, `attendance`, `mixed`; default `auto`. |
| `invoice_path` | `invoicePath` | Depends on input type | Invoice Excel path or object-storage key. |
| `attendance_path` | `attendancePath` | Depends on input type | Attendance CSV/XLSX path or object-storage key. |
| `tenant_id` | `tenantId` | No | Tenant/legal entity used for payroll policy lookup. |
| `metadata` | - | No | Caller-owned metadata. |
| `validate_only` | `validateOnly`, `dry_run`, `dryRun` | No | `true` validates without producing payroll outputs. |

## Mixed Example

```json
{
  "request_id": "payroll-run-2026-05-acme-site-a",
  "scope": {
    "affiliate": "Acme",
    "workplace": "Site A",
    "period": "2026-05"
  },
  "input_type": "mixed",
  "invoice_path": "rustfs://bitween-payroll/inbox/invoice_2026-05.xlsx",
  "attendance_path": "rustfs://bitween-payroll/inbox/attendance_2026-05.csv",
  "tenant_id": "acme",
  "metadata": {
    "requested_by": "api",
    "source_system": "Bitween API"
  }
}
```

## Success Response

```json
{
  "ok": true,
  "status": "success",
  "will_run": true,
  "can_run": true,
  "request_id": "payroll-run-2026-05-acme-site-a",
  "scope": "Acme/Site A/2026-05",
  "scope_key": "Acme\u001fSite A\u001f2026-05",
  "affiliate": "Acme",
  "workplace": "Site A",
  "period": "2026-05",
  "input_type": "mixed",
  "count": 28,
  "warnings": [],
  "paths": {
    "ledger": "rustfs://bitween-payroll/output/Acme/Site A/2026-05/급여대장.xlsx",
    "payslip": "rustfs://bitween-payroll/output/Acme/Site A/2026-05/급여명세서.xlsx",
    "payment": "rustfs://bitween-payroll/output/Acme/Site A/2026-05/지급내역.xlsx"
  },
  "error_code": "",
  "details": {},
  "operation_policy": {
    "input_basis": "hybrid",
    "payday": "25일",
    "show_setup_guide": true,
    "policy_note": "",
    "attendance": {
      "enabled": true,
      "source": "biometric",
      "rounding_minutes": 1,
      "late_grace_minutes": 0,
      "early_leave_grace_minutes": 0,
      "overtime_rounding_minutes": 1,
      "missing_clock_policy": "warn",
      "holiday_source": "invoice"
    }
  },
  "operation_policy_source": "tenant",
  "error": ""
}
```

## Run Failure Response

Run failures happen after a request has passed validation and execution was attempted. They keep `will_run: true`, use `can_run: false`, and include the same scope/result fields as a success response so operators can correlate the failed run. Validation errors are documented separately below and keep `will_run: false`.

```json
{
  "ok": false,
  "status": "error",
  "will_run": true,
  "can_run": false,
  "request_id": "payroll-run-2026-05-acme-site-a",
  "scope": "Acme/Site A/2026-05",
  "scope_key": "Acme\u001fSite A\u001f2026-05",
  "affiliate": "Acme",
  "workplace": "Site A",
  "period": "2026-05",
  "input_type": "mixed",
  "count": 0,
  "warnings": ["급여 처리 실패"],
  "paths": {},
  "payroll_audit": {},
  "roster": {},
  "operation_policy": {
    "input_basis": "hybrid",
    "payday": "25일",
    "show_setup_guide": true,
    "policy_note": "",
    "attendance": {
      "enabled": true,
      "source": "biometric",
      "rounding_minutes": 1,
      "late_grace_minutes": 0,
      "early_leave_grace_minutes": 0,
      "overtime_rounding_minutes": 1,
      "missing_clock_policy": "warn",
      "holiday_source": "invoice"
    }
  },
  "operation_policy_source": "tenant",
  "error_code": "payroll_run_failed",
  "details": {},
  "error": "급여 처리 실패"
}
```

## Validation Response

```json
{
  "ok": true,
  "status": "validated",
  "will_run": false,
  "can_run": true,
  "request_id": "payroll-run-2026-05-acme-site-a",
  "scope": "Acme/Site A/2026-05",
  "scope_key": "Acme\u001fSite A\u001f2026-05",
  "affiliate": "Acme",
  "workplace": "Site A",
  "period": "2026-05",
  "input_type": "mixed",
  "requested_input_type": "mixed",
  "tenant_id": "acme",
  "paths": {
    "invoice": "rustfs://bitween-payroll/inbox/invoice_2026-05.xlsx",
    "attendance": "rustfs://bitween-payroll/inbox/attendance_2026-05.csv"
  },
  "metadata_keys": ["requested_by", "source_system"],
  "operation_policy": {
    "input_basis": "hybrid",
    "payday": "25일",
    "show_setup_guide": true,
    "policy_note": "",
    "attendance": {
      "enabled": true,
      "source": "biometric",
      "rounding_minutes": 1,
      "late_grace_minutes": 0,
      "early_leave_grace_minutes": 0,
      "overtime_rounding_minutes": 1,
      "missing_clock_policy": "warn",
      "holiday_source": "invoice"
    }
  },
  "operation_policy_source": "tenant",
  "warnings": [],
  "error_code": "",
  "details": {},
  "error": ""
}
```

## Authorization Invariants

The HTTP/session/JWT wrapper is not selected yet, but the Rust service facade now owns the payroll authorization decision once a trusted principal is supplied. Frontend labels are not authorization input. Server-side wrappers must build `PayrollPrincipal` from trusted session/JWT state and call `PayrollApiService::authorize_run_request(request, principal, action)`.

Actions and required permissions:

| action | Required permission | Purpose |
| --- | --- | --- |
| `validate` | `platform.payroll` | Validate payroll request shape and preview policy/input resolution. |
| `run` | `platform.payroll.executive` | Execute payroll-producing automation. |
| `settings` | `platform.payroll.settings` | Change tenant/site payroll operation policy. |

RBAC role families are `staff`, `finance`, and `admin`. Position families are `ceo`, `executive`, `director`, `manager`, `team_lead`, `senior`, `member`, and `intern`. Rust preserves the legacy compatibility rule that CEO position bypasses team platform filtering, while non-CEO admin/finance grants are still filtered by `effective_platform_ids`.

ABAC attributes are `tenant_id`, `affiliate`, `workplace`, `period`, `org_unit_id`, `effective_platform_ids`, `allowed_affiliates`, and `allowed_workplaces`. A supplied request `tenant_id` must match the principal tenant. Non-empty affiliate/workplace allow-lists restrict the request scope.

Stable denial reason codes:

| reason_code | Meaning |
| --- | --- |
| `missing_principal_tenant` | Trusted principal does not name a tenant/legal entity. |
| `tenant_mismatch` | Request tenant and principal tenant differ. |
| `missing_permission` | Principal lacks the action permission after role/position/platform filtering. |
| `affiliate_not_allowed` | Request affiliate is outside the principal ABAC scope. |
| `workplace_not_allowed` | Request workplace is outside the principal ABAC scope. |

## Authorization Decision Response

```json
{
  "ok": true,
  "allowed": true,
  "action": "run",
  "user_id": "user-finance",
  "tenant_id": "acme",
  "scope": "Acme/Site A/2026-05",
  "reason_code": "",
  "reason": "",
  "required_permissions": ["platform.payroll.executive"],
  "granted_permissions": ["platform.payroll", "platform.payroll.executive"]
}
```

Denied example:

```json
{
  "ok": false,
  "allowed": false,
  "action": "run",
  "user_id": "user-finance",
  "tenant_id": "other",
  "scope": "Acme/Site A/2026-05",
  "reason_code": "tenant_mismatch",
  "reason": "Payroll request tenant does not match the principal tenant.",
  "required_permissions": [],
  "granted_permissions": ["platform.payroll", "platform.payroll.executive"]
}
```

## Health Response

The Rust service facade owns this probe-safe shape before an HTTP framework is selected.

```json
{
  "ok": true,
  "status": "ok",
  "service": "bitween-payroll-api",
  "version": "v1",
  "environment": "production",
  "build_sha": "",
  "uptime_seconds": 0
}
```

## Readiness Response

Readiness aggregates named checks. Any required `not_ready` check makes the whole response `not_ready`; optional degraded checks document partial rollout state without marking the service ready for production traffic.

```json
{
  "ready": false,
  "state": "not_ready",
  "service": "bitween-payroll-api",
  "version": "v1",
  "checks": [
    {
      "name": "policy",
      "state": "ready",
      "required": true,
      "message": "Rust policy invariants loaded"
    },
    {
      "name": "python_execution",
      "state": "degraded",
      "required": false,
      "message": "Compatibility fallback still active"
    },
    {
      "name": "database",
      "state": "not_ready",
      "required": true,
      "message": "Rust persistence is not configured"
    }
  ]
}
```

## Validation Error Response

Validation errors return stable JSON, keep `will_run: false`, and never expose internal exception objects.

```json
{
  "ok": false,
  "status": "error",
  "will_run": false,
  "can_run": false,
  "request_id": "payroll-run-2026-05-acme-site-a",
  "error_code": "invalid_period",
  "error": "period는 YYYY-MM 형식이어야 합니다.",
  "warnings": ["period는 YYYY-MM 형식이어야 합니다."],
  "details": {
    "period": "202605",
    "period_format": "YYYY-MM"
  }
}
```

`scope` is the external display/integration string and `scope_key` is the internal compatibility key.

### Error Codes

Frontend code must use `error_code`, not parse `error` text.

| error_code | Meaning |
| --- | --- |
| `invalid_payload` | Request body is not a JSON object/dict. |
| `invalid_scope` | `scope` shape is unsupported. |
| `missing_scope_fields` | `affiliate`, `workplace`, or `period` is missing. |
| `invalid_period` | `period` is not `YYYY-MM`. |
| `invalid_input_type` | `input_type` is not one of `auto`, `invoice`, `attendance`, `mixed`. |
| `missing_input_path` | Required invoice or attendance input path is missing. |
| `payroll_run_failed` | Request shape was valid but payroll processing failed. |
| `validation_error` | Validation failed without a more specific code. |

## Implementation Notes

- `input_type=auto` resolves against the Rust-selected tenant/site/global operation policy first.
- `auto` requires at least one of `invoice_path` or `attendance_path`; explicit `mixed` requires both.
- `validate_only`/`dry_run` validates file references and request shape but does not generate payroll outputs.
- Frontend code can use `can_run` to enable or disable run actions.
- `input_type` in validation responses is the resolved input type; `requested_input_type` preserves caller input.
- Explicit `invoice`, `attendance`, and `mixed` requests preserve caller selection.
- Responses include `operation_policy` and `operation_policy_source` (`site`, `tenant`, or `global`) so operators can audit which policy was applied.
- Rust owns site -> tenant -> global policy-resolution precedence for supplied settings snapshots through `PayrollApiService::validate_run_payload_with_policy_settings`; settings persistence remains compatibility-only until the repository/storage migration lands.
- Rust owns supplied-policy workplace monthly-hours application through `PayrollApiService::apply_monthly_hours_to_invoice`; settings persistence and canonical workplace alias resolution remain compatibility-only until repository/storage migration lands.
- Rust owns supplied-input invoice audit row evaluation through `PayrollApiService::audit_invoice_row`; Settings lookup, ledger matching, fixed-profile resolution, and workbook I/O remain Rust service backlog boundaries.
- Rust owns supplied-input invoice audit batch summarization through `PayrollApiService::audit_invoice_batch`; Rust service backlog supplies resolved row inputs and keeps UI text rendering compatibility.
- Rust owns supplied-input social-insurance calculation through `PayrollApiService::calculate_social_insurance`; Rust service backlog parses identities, determines age/KCOMWEL eligibility, reads roster/master workbooks, applies EDI premium overrides, and mutates payroll rows.
- Rust owns supplied-input earnings/gross/non-taxable/taxable-pay calculation through `PayrollApiService::calculate_payroll_earnings`; Rust service backlog parses invoices, merges employee masters, normalizes cells, calculates insurance/tax/deductions, and assembles final payroll records.
- Rust owns supplied-input one-employee salary calculation through `PayrollApiService::calculate_payroll_salary`; Rust service backlog parses/merges payroll sources, resolves age/KCOMWEL/EDI data, writes workbooks, and assembles final payroll records.
- Rust owns supplied-input final deduction/net-pay calculation through `PayrollApiService::finalize_payroll_deductions`; Rust service backlog parses workbooks, matches rosters, resolves social insurance, and assembles final records.
- Rust owns supplied-input employment-insurance 65+ payroll decisions through `PayrollApiService::resolve_ei_65_for_payroll`; KCOMWEL record import/persistence, settings/site management-number resolution, live API calls, supplied EDI premium coordination, and payroll row mutation remain Rust service backlog boundaries.
- Rust owns supplied-record EDI insurance premium application through `PayrollApiService::apply_edi_premiums_to_invoice`; EDI file import/storage, settings/site management-number resolution, employee matching, and workbook I/O remain Rust service backlog boundaries.
- Rust owns supplied-config site-benefits row application through `PayrollApiService::apply_site_benefits_to_invoice`; Settings resolution, identity-insurance ledger checks/persistence, and payroll-total recalculation remain Rust service backlog boundaries.
- Rust owns resolved fixed-hours profile application through `PayrollApiService::apply_fixed_hours_to_invoice`; contract/template/settings resolution remains compatibility-only until persistence and HR contract repositories move to Rust.
- Rust now owns run-result success and execution-failure envelope shaping through `PayrollApiService::run_response`; Rust execution remains a compatibility source until the Rust executor and persistence slices land.
- Rust normalizes `operation_policy` known fields before serializing responses: invalid input basis falls back to `hybrid`; attendance minute fields are clamped to legacy-compatible ranges; missing-clock policy falls back to `warn`.
- `PayrollApiService` now owns framework-neutral health/readiness DTOs; future Axum/Actix/Tauri/Kubernetes wrappers should call those Rust functions rather than inventing parallel probe payloads.
- `PayrollApiService::authorize_run_request` owns tenant/RBAC/ABAC payroll action decisions; wrappers must supply trusted principals and must not authorize from frontend labels.
