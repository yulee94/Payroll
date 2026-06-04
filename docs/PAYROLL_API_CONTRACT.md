# Payroll Automation API Contract

Bitween payroll automation is migrating to a Rust backend service for Kubernetes-native production. The current Python adapter mirrors this contract only for compatibility and characterization until the Rust API becomes authoritative.

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
- Fixed-hours application function: `PayrollApiService::apply_fixed_hours_to_invoice(invoice, fixed_hours_profile, workplace)`
- Execution plan function: `PayrollApiService::plan_run_request(request, policy_snapshot)`
- Run-result response function: `PayrollApiService::run_response(result, request_id)`
- Health function: `PayrollApiService::health()`
- Readiness function: `PayrollApiService::readiness(checks)`
- Authorization function: `PayrollApiService::authorize_run_request(request, principal, action)`
- Purpose: move payroll request validation, scope parsing, input-method resolution, operation-policy resolution precedence, attendance aggregation, workplace monthly-hours application, invoice audit row evaluation, fixed-hours payroll row application, execution routing/planning, run-result response envelope shaping, probe-safe service boundary responses, and tenant/RBAC/ABAC authorization decisions into Rust.

Compatibility adapter:

- `services.payroll_api_adapter.run_payroll_api(payload)` mirrors the contract until the Rust service replaces it.
- `services.payroll_api_adapter.payroll_api_response(result, request_id=...)` remains the Python compatibility equivalent of `PayrollApiService::run_response(result, request_id)` while payroll execution is still Python-backed.
- `services.payroll_api_adapter.validate_payroll_api_payload(payload)` validates payloads without running payroll generation.

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

Python compatibility code may still parse `.csv`, `.txt`, `.xlsx`, and `.xlsm` attendance uploads and may still build invoice-compatible workbooks. Once attendance rows are normalized, Rust owns the payroll-domain aggregation rule through `aggregate_attendance_records(records, workplace, attendance_policy)` and `PayrollApiService::aggregate_attendance_records(records, workplace, attendance_policy)`.

Aggregation invariants:

1. Records are grouped by supplied `name_key`, or by a whitespace-normalized employee name when `name_key` is absent.
2. `late_grace_minutes` and `early_leave_grace_minutes` are applied per source record before totals are rounded.
3. Work, late/early, overtime, night, and special hours are rounded with Python-compatible half-even rounding.
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

Python compatibility code may still load tenant/site/global settings and canonical workplace aliases. Once a workplace-hours policy has been supplied for an invoice-compatible payroll row, Rust owns the deterministic monthly-hours selection rule through `resolve_monthly_work_hours(invoice, workplace, workplace_hours_policy)`, `apply_monthly_hours_to_invoice(invoice, workplace, workplace_hours_policy)`, and `PayrollApiService::apply_monthly_hours_to_invoice(invoice, workplace, workplace_hours_policy)`.

Application invariants:

1. Invalid or missing modes fall back to `fixed`; missing, invalid, or non-positive policy hours fall back to 209.
2. Optional `daily_hours` is retained only when positive, and `break_minutes` only when non-negative.
3. Invoice `work_days` and `base_days` are clamped at zero before mode selection.
4. All five Python-compatible modes remain stable: `fixed`, `invoice_work_days`, `invoice_base_days`, `work_or_fixed`, and `base_or_fixed`.
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

Python compatibility code may still resolve settings, match payroll ledger records, resolve employee fixed-hours profiles, read workbooks, and aggregate batch summaries. Once a single invoice row, workplace-hours policy, optional ledger record, and optional fixed-hours profile have been supplied, Rust owns the deterministic audit-row evaluation through `audit_invoice_row(invoice, workplace, workplace_hours_policy, ledger_record, fixed_hours_profile)` and `PayrollApiService::audit_invoice_row(invoice, workplace, workplace_hours_policy, ledger_record, fixed_hours_profile)`.

Audit invariants:

1. `status` remains either `pass` or `warn`, with Korean labels `정상` and `확인`.
2. Break-hour estimation uses positive `break_minutes` first; otherwise it falls back to the invoice `base_days - work_days - leave_days` gap when the I/J columns look hour-based.
3. Base-salary mismatch, missing invoice-hours, missing roster base-hourly, fixed-hours mismatch, and ledger monthly-hour mismatch flags preserve Python Korean wording.
4. Optional fixed-hours profiles reuse the Rust fixed-hours application/audit flags and prepend those flags before row-level warnings.
5. Batch summary aggregation, settings lookup, record matching, and workbook I/O remain Python compatibility boundaries in this slice.

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

## Fixed-Hours Application

Python compatibility code may still load HR contracts, site job-group templates, payroll settings, and employee rosters. Once a fixed-hours profile has been resolved for an invoice-compatible payroll row, Rust owns the payroll-domain application rule through `apply_fixed_hours_to_invoice(invoice, fixed_hours_profile, workplace)` and `PayrollApiService::apply_fixed_hours_to_invoice(invoice, fixed_hours_profile, workplace)`.

Application invariants:

1. Resolved profiles are normalized before application; monthly hours default to 209, or `daily_fixed_hours × 26` when monthly hours are absent.
2. Original invoice `work_days`, `base_days`, `ot_hours`, `special_hours`, and `special_ext_hours` are preserved under `_invoice_*` fields before replacement.
3. `fixed_extension_hours` replaces `ot_hours` when positive, and `fixed_overtime_hours` replaces `special_hours` when positive.
4. `_preserve_reference_hours` keeps the original invoice work/base hours for application while audit flags still compare against the resolved profile.
5. Audit flags preserve the Python compatibility Korean labels for the profile source, pay type, and hour mismatches.

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

For compatibility, Python may still load and save tenant/site settings, but Rust now owns the deterministic policy-resolution decision once a settings snapshot is supplied. Future HTTP, Tauri, mobile, worker, or Kubernetes wrappers should supply a snapshot to `PayrollApiService::validate_run_payload_with_policy_settings(payload, settings)` instead of resolving `operation_policy_source` in client code.

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

Rust now owns deterministic payroll execution planning once a request has been parsed and an operation-policy snapshot has been resolved. The plan does not generate payroll outputs yet; it tells future HTTP, worker, Tauri, or Kubernetes wrappers which source paths and compatibility steps will run before the Python executor is replaced.

Rust entry points:

- `plan_payroll_execution(request, policy_snapshot)`
- `PayrollApiService::plan_run_request(request, policy_snapshot)`

Planner invariants:

1. Explicit `invoice`, `attendance`, and `mixed` requests keep the caller-requested input type when required source paths exist.
2. `auto` requests resolve the executable input type from the normalized Rust operation policy.
3. `mixed` requests with only an attendance source plan an attendance fallback to preserve Python compatibility behavior.
4. Every step currently names `backend: "python_compatibility"` until Rust owns payroll output generation.

Example plan:

```json
{
  "ok": true,
  "scope": "COSS/Site A/2026-05",
  "scope_key": "COSS\u001fSite A\u001f2026-05",
  "affiliate": "COSS",
  "workplace": "Site A",
  "period": "2026-05",
  "input_type": "mixed",
  "requested_input_type": "auto",
  "backend": "python_compatibility",
  "compatibility_executor": "services.payroll_automation.run_payroll_automation",
  "source_paths": {
    "invoice": "s3://bitween-payroll/inbox/invoice_2026-05.xlsx",
    "attendance": "s3://bitween-payroll/inbox/attendance_2026-05.csv"
  },
  "missing_source_paths": [],
  "steps": [
    {
      "kind": "extract_attendance",
      "backend": "python_compatibility",
      "input": "s3://bitween-payroll/inbox/attendance_2026-05.csv",
      "output": "attendance_rows",
      "description": "Extract attendance rows before merging them into the invoice workbook."
    },
    {
      "kind": "attach_attendance_sheet",
      "backend": "python_compatibility",
      "input": "s3://bitween-payroll/inbox/invoice_2026-05.xlsx + attendance_rows",
      "output": "generated:mixed_invoice",
      "description": "Attach the attendance sheet to the supplied invoice workbook."
    },
    {
      "kind": "process_invoice",
      "backend": "python_compatibility",
      "input": "generated:mixed_invoice",
      "output": "payroll_outputs",
      "description": "Process the merged invoice workbook through the compatibility payroll executor."
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
    "affiliate": "COSS",
    "workplace": "Site A",
    "period": "2026-05"
  }
}
```

Flat shape:

```json
{
  "affiliate": "COSS",
  "workplace": "Site A",
  "period": "2026-05"
}
```

Scope key shape:

```json
{
  "scope": "COSS/Site A/2026-05"
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
  "request_id": "payroll-run-2026-05-coss-site-a",
  "scope": {
    "affiliate": "COSS",
    "workplace": "Site A",
    "period": "2026-05"
  },
  "input_type": "mixed",
  "invoice_path": "s3://bitween-payroll/inbox/invoice_2026-05.xlsx",
  "attendance_path": "s3://bitween-payroll/inbox/attendance_2026-05.csv",
  "tenant_id": "coss",
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
  "request_id": "payroll-run-2026-05-coss-site-a",
  "scope": "COSS/Site A/2026-05",
  "scope_key": "COSS\u001fSite A\u001f2026-05",
  "affiliate": "COSS",
  "workplace": "Site A",
  "period": "2026-05",
  "input_type": "mixed",
  "count": 28,
  "warnings": [],
  "paths": {
    "ledger": "s3://bitween-payroll/output/COSS/Site A/2026-05/급여대장.xlsx",
    "payslip": "s3://bitween-payroll/output/COSS/Site A/2026-05/급여명세서.xlsx",
    "payment": "s3://bitween-payroll/output/COSS/Site A/2026-05/지급내역.xlsx"
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
  "request_id": "payroll-run-2026-05-coss-site-a",
  "scope": "COSS/Site A/2026-05",
  "scope_key": "COSS\u001fSite A\u001f2026-05",
  "affiliate": "COSS",
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
  "request_id": "payroll-run-2026-05-coss-site-a",
  "scope": "COSS/Site A/2026-05",
  "scope_key": "COSS\u001fSite A\u001f2026-05",
  "affiliate": "COSS",
  "workplace": "Site A",
  "period": "2026-05",
  "input_type": "mixed",
  "requested_input_type": "mixed",
  "tenant_id": "coss",
  "paths": {
    "invoice": "s3://bitween-payroll/inbox/invoice_2026-05.xlsx",
    "attendance": "s3://bitween-payroll/inbox/attendance_2026-05.csv"
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

RBAC role families are `staff`, `finance`, and `admin`. Position families are `ceo`, `executive`, `director`, `manager`, `team_lead`, `senior`, `member`, and `intern`. Rust preserves the Python compatibility rule that CEO position bypasses team platform filtering, while non-CEO admin/finance grants are still filtered by `effective_platform_ids`.

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
  "tenant_id": "coss",
  "scope": "COSS/Site A/2026-05",
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
  "scope": "COSS/Site A/2026-05",
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
  "request_id": "payroll-run-2026-05-coss-site-a",
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
- Rust owns site -> tenant -> global policy-resolution precedence for supplied settings snapshots through `PayrollApiService::validate_run_payload_with_policy_settings`; Python settings persistence remains compatibility-only until the repository/storage migration lands.
- Rust owns supplied-policy workplace monthly-hours application through `PayrollApiService::apply_monthly_hours_to_invoice`; Python settings persistence and canonical workplace alias resolution remain compatibility-only until repository/storage migration lands.
- Rust owns supplied-input invoice audit row evaluation through `PayrollApiService::audit_invoice_row`; Python settings lookup, ledger matching, fixed-profile resolution, batch summaries, and workbook I/O remain compatibility-only boundaries.
- Rust owns resolved fixed-hours profile application through `PayrollApiService::apply_fixed_hours_to_invoice`; Python contract/template/settings resolution remains compatibility-only until persistence and HR contract repositories move to Rust.
- Rust now owns run-result success and execution-failure envelope shaping through `PayrollApiService::run_response`; Python execution remains a compatibility source until the Rust executor and persistence slices land.
- Rust normalizes `operation_policy` known fields before serializing responses: invalid input basis falls back to `hybrid`; attendance minute fields are clamped to Python-compatible ranges; missing-clock policy falls back to `warn`.
- `PayrollApiService` now owns framework-neutral health/readiness DTOs; future Axum/Actix/Tauri/Kubernetes wrappers should call those Rust functions rather than inventing parallel probe payloads.
- `PayrollApiService::authorize_run_request` owns tenant/RBAC/ABAC payroll action decisions; wrappers must supply trusted principals and must not authorize from frontend labels.
