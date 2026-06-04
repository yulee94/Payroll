export const PAYROLL_API_VERSION = "v1" as const;
export const PAYROLL_API_ENDPOINT = "/api/payroll/v1/runs" as const;
export const PAYROLL_API_VALIDATE_ENDPOINT = "/api/payroll/v1/runs/validate" as const;
export const PAYROLL_API_HEALTH_ENDPOINT = "/api/payroll/v1/healthz" as const;
export const PAYROLL_API_READINESS_ENDPOINT = "/api/payroll/v1/readiness" as const;

export type PayrollInputType = "auto" | "invoice" | "attendance" | "mixed";
export type PayrollInputBasis = "invoice" | "attendance" | "hybrid";
export type PayrollMissingClockPolicy = "warn" | "ignore" | "deduct";
export type PayrollOperationPolicySource = "site" | "tenant" | "global" | "";
export type PayrollHealthStatus = "ok";
export type PayrollReadinessState = "ready" | "degraded" | "not_ready";
export type PayrollAction = "validate" | "run" | "settings";
export type PayrollPermission =
  | "platform.payroll"
  | "platform.payroll.executive"
  | "platform.payroll.settings";
export type PayrollExecutionBackend = "python_compatibility";
export type PayrollExecutionStepKind =
  | "extract_attendance"
  | "build_attendance_invoice"
  | "attach_attendance_sheet"
  | "process_invoice";

export type PayrollAccessReasonCode =
  | ""
  | "missing_principal_tenant"
  | "tenant_mismatch"
  | "missing_permission"
  | "affiliate_not_allowed"
  | "workplace_not_allowed";

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

export interface PayrollAttendanceSourceRecord {
  name: string;
  name_key?: string;
  dept?: string;
  workplace?: string;
  work_hours?: number;
  late_hours?: number;
  early_leave_hours?: number;
  overtime_hours?: number;
  night_hours?: number;
  special_hours?: number;
  leave_days?: number;
  unpaid_days?: number;
}

export interface PayrollAttendanceInvoiceRow {
  row: number;
  name: string;
  dept: string;
  hire_date: string;
  workplace: string;
  base_hourly: number;
  ordinary_hourly: number;
  base_days: number;
  work_days: number;
  unpaid_days: number;
  leave_days: number;
  ot_hours: number;
  shift_hours: number;
  night_hours: number;
  special_hours: number;
  special_ext_hours: number;
  early_leave_hours: number;
  base_salary: number;
  base_deduction: number;
  ot_pay: number;
  night_pay: number;
  special_pay: number;
  special_ext_pay: number;
  position_pay: number;
  shift_pay: number;
  workers_day_pay: number;
  annual_pay: number;
  transport: number;
  subtotal: number;
  gross_pay: number;
  health_insurance: number;
  long_term_care: number;
  national_pension: number;
  employment_insurance: number;
  insurance_total: number;
  _attendance_days: number;
  _attendance_input: true;
}

export type PayrollWorkplaceHoursMode =
  | "fixed"
  | "invoice_work_days"
  | "invoice_base_days"
  | "work_or_fixed"
  | "base_or_fixed";

export interface PayrollWorkplaceHoursPolicy {
  mode: PayrollWorkplaceHoursMode;
  hours: number;
  daily_hours?: number;
  break_minutes?: number;
}

export interface PayrollWorkplaceHoursInvoice {
  workplace: string;
  work_days: number;
  base_days: number;
  _monthly_work_hours?: number;
  _monthly_hours_source: string;
}

export interface PayrollWorkplaceMonthlyHoursResolution {
  hours: number;
  source: string;
  workplace: string;
  policy: PayrollWorkplaceHoursPolicy;
}

export interface PayrollWorkplaceMonthlyHoursApplication {
  hours: number;
  source: string;
  invoice: PayrollWorkplaceHoursInvoice;
  policy: PayrollWorkplaceHoursPolicy;
}


export type PayrollInvoiceAuditStatus = "pass" | "warn";

export interface PayrollInvoiceAuditInvoice {
  name: string;
  workplace?: string;
  base_days: number;
  work_days: number;
  leave_days?: number;
  ot_hours?: number;
  special_hours?: number;
  special_ext_hours?: number;
  base_hourly?: number;
  base_salary?: number;
  _preserve_reference_hours?: boolean;
}

export interface PayrollInvoiceAuditRecord {
  name: string;
  workplace?: string;
  base_hourly?: number;
  _monthly_work_hours?: number;
}

export interface PayrollInvoiceAuditRow {
  name: string;
  workplace: string;
  status: PayrollInvoiceAuditStatus;
  status_label: string;
  flags: string[];
  base_days: number;
  work_days: number;
  break_hours: number | null;
  applied_monthly_hours: number;
  hours_source: string;
  policy_mode: PayrollWorkplaceHoursMode;
  policy_fixed_hours: number;
  base_hourly: number;
  invoice_base_salary: number;
  calc_base_salary: number;
  formula: string;
  fixed_hours_mode: boolean;
  fixed_hours_source: string;
}

export type PayrollFixedHoursPayType = "hourly" | "monthly_salary";

export interface PayrollFixedHoursProfile {
  fixed_hours_mode: boolean;
  monthly_fixed_hours: number;
  daily_fixed_hours: number;
  fixed_overtime_hours: number;
  fixed_extension_hours: number;
  pay_type: PayrollFixedHoursPayType;
  job_group: string;
  source: string;
  source_label: string;
  contract_id?: string;
}

export interface PayrollFixedHoursInvoice {
  name: string;
  workplace: string;
  work_days: number;
  base_days: number;
  ot_hours: number;
  special_hours: number;
  special_ext_hours: number;
  _invoice_work_days?: number;
  _invoice_base_days?: number;
  _invoice_ot_hours?: number;
  _invoice_special_hours?: number;
  _invoice_special_ext_hours?: number;
  _monthly_work_hours?: number;
  _monthly_hours_source: string;
  _fixed_hours_mode: boolean;
  _fixed_hours_source: string;
  _fixed_hours_pay_type: PayrollFixedHoursPayType | "";
  _fixed_hours_job_group: string;
  _preserve_reference_hours: boolean;
}

export interface PayrollFixedHoursApplication {
  applied: boolean;
  invoice: PayrollFixedHoursInvoice;
  profile: PayrollFixedHoursProfile;
  audit_flags: string[];
}

export interface PayrollOperationPolicyResolution {
  workplace: string;
  policy: PayrollOperationPolicy;
  source: Exclude<PayrollOperationPolicySource, "">;
  has_site_override: boolean;
}

export interface PayrollExecutionStep {
  kind: PayrollExecutionStepKind;
  backend: PayrollExecutionBackend;
  input: string;
  output: string;
  description: string;
}

export interface PayrollExecutionPlan {
  ok: boolean;
  scope: string;
  scope_key: string;
  affiliate: string;
  workplace: string;
  period: string;
  input_type: Exclude<PayrollInputType, "auto">;
  requested_input_type: PayrollInputType;
  backend: PayrollExecutionBackend;
  compatibility_executor: string;
  source_paths: Partial<Record<"invoice" | "attendance", string>>;
  missing_source_paths: Array<"invoice" | "attendance" | string>;
  steps: PayrollExecutionStep[];
  operation_policy: PayrollOperationPolicy;
  operation_policy_source: PayrollOperationPolicySource;
  warnings: string[];
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
  operation_policy_source?: PayrollOperationPolicySource;
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
  operation_policy_source: Exclude<PayrollOperationPolicySource, "">;
}

export interface PayrollValidationErrorResponse extends PayrollApiBaseResponse {
  ok: false;
  status: "error";
  will_run: false;
  can_run: false;
  error_code: PayrollErrorCode | string;
}

export interface PayrollRunFailureResponse extends PayrollApiBaseResponse {
  ok: false;
  status: "error";
  will_run: true;
  can_run: false;
  error_code: "payroll_run_failed";
  scope: string;
  scope_key: string;
  affiliate: string;
  workplace: string;
  period: string;
  input_type: PayrollInputType;
  count: number;
  paths: Record<string, string>;
  payroll_audit?: Record<string, unknown>;
  roster?: Record<string, unknown>;
  operation_policy?: PayrollOperationPolicy;
  operation_policy_source?: PayrollOperationPolicySource;
}

export type PayrollErrorResponse = PayrollValidationErrorResponse | PayrollRunFailureResponse;

export type PayrollApiResponse =
  | PayrollSuccessResponse
  | PayrollValidationResponse
  | PayrollErrorResponse;

export interface PayrollAccessDecision {
  ok: boolean;
  allowed: boolean;
  action: PayrollAction;
  user_id: string;
  tenant_id: string;
  scope: string;
  reason_code: PayrollAccessReasonCode;
  reason: string;
  required_permissions: PayrollPermission[];
  granted_permissions: PayrollPermission[];
}

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
