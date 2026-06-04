# Payroll Automation API Contract

Bitween payroll automation is migrating to a Rust backend service for Kubernetes-native production. The current Python adapter mirrors this contract only for compatibility and characterization until the Rust API becomes authoritative.

## Entry Point

Planned HTTP endpoint:

- `POST /api/payroll/v1/runs`
- Content-Type: `application/json`
- Production owner: Rust backend service deployed through Kubernetes (`docs/KUBERNETES_NATIVE_STACK.md`)

Rust transition entry point:

- Rust crate: `crates/payroll-api`
- Validation function: `bitween_payroll_api::validate_payroll_api_payload(payload, policy_snapshot)`
- Purpose: move payroll request validation, scope parsing, input-method resolution, and stable response shaping into Rust.

Compatibility adapter:

- `services.payroll_api_adapter.run_payroll_api(payload)` mirrors the contract until the Rust service replaces it.
- `services.payroll_api_adapter.validate_payroll_api_payload(payload)` validates payloads without running payroll generation.

TypeScript frontend contract:

- Type file: `frontend/src/contracts/payrollApi.ts`
- Purpose: keep frontend request/response field names aligned with Rust API responses.

Validation endpoint:

- `POST /api/payroll/v1/runs/validate`
- Alternative compatibility behavior: `run_payroll_api(payload)` with `validate_only: true` or `dry_run: true` returns validation only.

Readiness endpoint:

- `GET /api/payroll/v1/readiness`
- Purpose: expose roster, policy, source-data, and API-contract readiness cards to frontend dashboards.

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
  "operation_policy_source": "tenant",
  "error": ""
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
    "attendance": {
      "enabled": true,
      "rounding_minutes": 1,
      "late_grace_minutes": 0,
      "early_leave_grace_minutes": 0,
      "missing_clock_policy": "warn"
    }
  },
  "operation_policy_source": "tenant",
  "warnings": [],
  "error_code": "",
  "details": {},
  "error": ""
}
```

## Error Response

Validation errors return stable JSON and never expose internal exception objects.

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

- `input_type=auto` resolves against tenant/site operation policy first.
- `auto` requires at least one of `invoice_path` or `attendance_path`; explicit `mixed` requires both.
- `validate_only`/`dry_run` validates file references and request shape but does not generate payroll outputs.
- Frontend code can use `can_run` to enable or disable run actions.
- `input_type` in validation responses is the resolved input type; `requested_input_type` preserves caller input.
- Explicit `invoice`, `attendance`, and `mixed` requests preserve caller selection.
- Responses include `operation_policy` and `operation_policy_source` so operators can audit which policy was applied.
