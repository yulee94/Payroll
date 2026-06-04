export const PAYROLL_API_VERSION = "v1" as const;
export const PAYROLL_API_ENDPOINT = "/api/payroll/v1/runs" as const;
export const PAYROLL_API_VALIDATE_ENDPOINT = "/api/payroll/v1/runs/validate" as const;
export const PAYROLL_API_HEALTH_ENDPOINT = "/api/payroll/v1/healthz" as const;
export const PAYROLL_API_READINESS_ENDPOINT = "/api/payroll/v1/readiness" as const;

export type PayrollInputType = "auto" | "invoice" | "attendance" | "mixed";
export type PayrollInputBasis = "invoice" | "attendance" | "hybrid";
export type PayrollMissingClockPolicy = "warn" | "ignore" | "deduct";
export type PayrollHealthStatus = "ok";
export type PayrollReadinessState = "ready" | "degraded" | "not_ready";

export type PayrollErrorCode =
  | "invalid_payload"
  | "invalid_scope"
  | "missing_scope_fields"
  | "invalid_period"
  | "invalid_input_type"
  | "missing_input_path"
  | "payroll_run_failed"
  | "validation_error";

export interface PayrollScopePayload {
  affiliate: string;
  workplace: string;
  period: string;
}

export type PayrollApiScope = string | PayrollScopePayload;

export interface PayrollApiRequest {
  request_id?: string;
  requestId?: string;
  scope?: PayrollApiScope;
  affiliate?: string;
  workplace?: string;
  period?: string;
  input_type?: PayrollInputType;
  inputType?: PayrollInputType;
  invoice_path?: string;
  invoicePath?: string;
  attendance_path?: string;
  attendancePath?: string;
  tenant_id?: string;
  tenantId?: string;
  metadata?: Record<string, unknown>;
  validate_only?: boolean;
  validateOnly?: boolean;
  dry_run?: boolean;
  dryRun?: boolean;
}

export interface PayrollAttendancePolicy {
  enabled: boolean;
  source: string;
  rounding_minutes: number;
  late_grace_minutes: number;
  early_leave_grace_minutes: number;
  overtime_rounding_minutes: number;
  missing_clock_policy: PayrollMissingClockPolicy;
  holiday_source: string;
  [key: string]: unknown;
}

export interface PayrollOperationPolicy {
  input_basis: PayrollInputBasis;
  payday: string;
  show_setup_guide: boolean;
  policy_note: string;
  attendance: PayrollAttendancePolicy;
  [key: string]: unknown;
}

export interface PayrollApiBaseResponse {
  ok: boolean;
  status: "success" | "validated" | "error";
  will_run: boolean;
  can_run: boolean;
  request_id?: string;
  error_code: "" | PayrollErrorCode | string;
  warnings: string[];
  details: Record<string, unknown>;
  error: string;
}

export interface PayrollSuccessResponse extends PayrollApiBaseResponse {
  ok: true;
  status: "success";
  will_run: true;
  can_run: true;
  scope: string;
  scope_key: string;
  affiliate: string;
  workplace: string;
  period: string;
  input_type: Exclude<PayrollInputType, "auto">;
  count: number;
  paths: Record<string, string>;
  payroll_audit?: Record<string, unknown>;
  roster?: Record<string, unknown>;
  operation_policy?: PayrollOperationPolicy;
  operation_policy_source?: string;
}

export interface PayrollValidationResponse extends PayrollApiBaseResponse {
  ok: true;
  status: "validated";
  will_run: false;
  can_run: true;
  scope: string;
  scope_key: string;
  affiliate: string;
  workplace: string;
  period: string;
  input_type: Exclude<PayrollInputType, "auto">;
  requested_input_type: PayrollInputType;
  tenant_id: string;
  paths: Partial<Record<"invoice" | "attendance", string>>;
  metadata_keys: string[];
  operation_policy: PayrollOperationPolicy;
  operation_policy_source: string;
}

export interface PayrollErrorResponse extends PayrollApiBaseResponse {
  ok: false;
  status: "error";
  will_run: false;
  can_run: false;
  error_code: PayrollErrorCode | string;
}

export type PayrollApiResponse =
  | PayrollSuccessResponse
  | PayrollValidationResponse
  | PayrollErrorResponse;

export interface PayrollHealthResponse {
  ok: true;
  status: PayrollHealthStatus;
  service: string;
  version: typeof PAYROLL_API_VERSION;
  environment: string;
  build_sha: string;
  uptime_seconds: number;
}

export interface PayrollReadinessCheck {
  name: string;
  state: PayrollReadinessState;
  required: boolean;
  message: string;
}

export interface PayrollReadinessResponse {
  ready: boolean;
  state: PayrollReadinessState;
  service: string;
  version: typeof PAYROLL_API_VERSION;
  checks: PayrollReadinessCheck[];
}

export function buildPayrollValidateRequest(request: PayrollApiRequest): PayrollApiRequest {
  return {
    ...request,
    validate_only: true,
  };
}

export function isPayrollValidationResponse(
  response: PayrollApiResponse,
): response is PayrollValidationResponse {
  return response.ok && response.status === "validated";
}

export function isPayrollSuccessResponse(
  response: PayrollApiResponse,
): response is PayrollSuccessResponse {
  return response.ok && response.status === "success";
}

export function isPayrollErrorResponse(
  response: PayrollApiResponse,
): response is PayrollErrorResponse {
  return response.ok === false;
}
