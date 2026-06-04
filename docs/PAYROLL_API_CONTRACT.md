# Payroll Automation API Contract

Bitween 급여 자동화는 현재 데스크톱 앱 내부 서비스로 구현되어 있으며, HTTP 서버 레이어는 아직 붙이지 않았습니다. 외부 API 또는 웹 백엔드를 붙일 때는 아래 계약을 그대로 감싸면 됩니다.

## Entry Point

- 내부 진입점: `services.payroll_api_adapter.run_payroll_api(payload)`
- 예정 HTTP 엔드포인트: `POST /api/payroll/v1/runs`
- Content-Type: `application/json`

관련 준비상태 조회:

- 내부 진입점: `services.payroll_readiness.payroll_readiness_snapshot(tenant_id=...)`
- 예정 HTTP 엔드포인트: `GET /api/payroll/v1/readiness`
- 용도: 명부, 운영 기준, 산출 자료, API 계약 준비 상태를 프론트 대시보드에서 표시합니다.

## Request

`scope`는 세 가지 형태를 받습니다.

```json
{
  "scope": {
    "affiliate": "COSS",
    "workplace": "Site A",
    "period": "2026-05"
  }
}
```

또는 flat 형태:

```json
{
  "affiliate": "COSS",
  "workplace": "Site A",
  "period": "2026-05"
}
```

또는 scope key:

```json
{
  "scope": "COSS/Site A/2026-05"
}
```

이 슬래시형 scope 문자열은 외부 API용 사람이 읽기 쉬운 형식입니다. 내부 `PayrollScope.key` 값도 받을 수 있지만, 외부 연동에는 위 형식을 권장합니다.

필드:

| Field | Alias | Required | Description |
| --- | --- | --- | --- |
| `request_id` | `requestId`, `metadata.request_id` | No | 호출 측 추적 ID. 성공/오류 응답에 그대로 반환합니다. |
| `scope` | - | Yes | 법인, 사업장, 급여월 범위입니다. |
| `period` | - | Yes | `YYYY-MM` 형식입니다. |
| `input_type` | `inputType` | No | `auto`, `invoice`, `attendance`, `mixed`. 기본값은 `auto`입니다. |
| `invoice_path` | `invoicePath` | 입력 방식에 따라 | 청구서 Excel 경로입니다. |
| `attendance_path` | `attendancePath` | 입력 방식에 따라 | 근태 CSV/XLSX 경로입니다. |
| `tenant_id` | `tenantId` | No | 테넌트/법인별 급여 운영 기준을 해석할 때 사용합니다. |
| `metadata` | - | No | 호출 측에서 보관할 부가 정보입니다. |

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
  "invoice_path": "C:/Bitween/inbox/invoice_2026-05.xlsx",
  "attendance_path": "C:/Bitween/inbox/attendance_2026-05.csv",
  "tenant_id": "coss",
  "metadata": {
    "requested_by": "api",
    "source_system": "Bitween HTTP wrapper"
  }
}
```

## Success Response

```json
{
  "ok": true,
  "status": "success",
  "request_id": "payroll-run-2026-05-coss-site-a",
  "scope": "COSS/Site A/2026-05",
  "scope_key": "COSS\\u001fSite A\\u001f2026-05",
  "affiliate": "COSS",
  "workplace": "Site A",
  "period": "2026-05",
  "input_type": "mixed",
  "count": 28,
  "warnings": [],
  "paths": {
    "ledger": "C:/Bitween/output/COSS/Site A/2026-05/급여대장.xlsx",
    "payslip": "C:/Bitween/output/COSS/Site A/2026-05/급여명세서.xlsx",
    "payment": "C:/Bitween/output/COSS/Site A/2026-05/지급내역.xlsx"
  },
  "error_code": "",
  "details": {},
  "operation_policy_source": "tenant",
  "error": ""
}
```

## Error Response

검증 오류도 예외를 그대로 노출하지 않고 안정적인 JSON으로 반환합니다.

```json
{
  "ok": false,
  "status": "error",
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

응답에는 내부 예외 객체인 `exception`을 포함하지 않습니다.
`scope`는 외부 표시/연동용 문자열이고, `scope_key`는 기존 데스크톱 저장 구조와 호환되는 내부 키입니다.

### Error Codes

프론트엔드는 `error` 문구를 파싱하지 말고 `error_code`를 기준으로 화면 문구와 입력 포커스를 결정하면 됩니다.

| error_code | Meaning |
| --- | --- |
| `invalid_payload` | 요청 본문이 JSON object/dict 형태가 아닙니다. |
| `invalid_scope` | `scope`가 지원 형식이 아닙니다. |
| `missing_scope_fields` | `affiliate`, `workplace`, `period` 중 필수값이 없습니다. |
| `invalid_period` | `period`가 `YYYY-MM` 형식이 아닙니다. |
| `invalid_input_type` | `input_type`이 `auto`, `invoice`, `attendance`, `mixed` 중 하나가 아닙니다. |
| `missing_input_path` | 입력 방식에 필요한 `invoice_path` 또는 `attendance_path`가 없습니다. |
| `payroll_run_failed` | 요청 형식은 맞지만 급여 산출 처리 중 실패했습니다. |
| `validation_error` | 더 구체적인 코드가 없는 검증 실패입니다. |

## Implementation Notes

- `input_type=auto`는 테넌트/사업장 운영 기준이 있으면 그 기준을 우선 해석합니다.
- `auto`는 `invoice_path` 또는 `attendance_path` 중 최소 하나가 필요하고, 명시적인 `mixed`는 두 경로가 모두 필요합니다.
- 명시적인 `invoice`, `attendance`, `mixed` 요청은 호출자가 고른 입력 방식을 유지합니다.
- 결과에는 `operation_policy`와 `operation_policy_source`가 포함되어, 산출 당시 어떤 급여 운영 기준이 적용됐는지 API에서도 확인할 수 있습니다.
- 실제 직원 명부, 급여 파일, 사용자 데이터, API 키, 그룹웨어 쿠키는 GitHub에 커밋하지 않습니다.
