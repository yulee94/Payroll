pub mod access;
pub mod attendance;
pub mod deductions;
pub mod earnings;
pub mod edi_insurance;
pub mod employment_insurance_65;
pub mod error;
pub mod execution_plan;
pub mod fixed_hours;
pub mod invoice_audit;
pub mod policy;
pub mod policy_resolution;
pub mod request;
pub mod response;
pub mod run;
pub mod service;
pub mod site_benefits;
pub mod social_insurance;
pub mod workplace_hours;

pub use access::{
    PayrollAccessDecision, PayrollAction, PayrollPermission, PayrollPosition, PayrollPrincipal,
    PayrollRole, authorize_payroll_request,
};
pub use attendance::{AttendanceInvoiceRow, AttendanceSourceRecord, aggregate_attendance_records};
pub use deductions::{
    PayrollDeductionInput, PayrollDeductionResult, PayrollIncomeTaxResult, PayrollTaxMethod,
    calculate_payroll_income_tax, finalize_payroll_deductions, lookup_simplified_income_tax,
};
pub use earnings::{
    HOLIDAY_PREMIUM, MEAL_ALLOWANCE_PER_DAY, MEAL_NON_TAXABLE_CAP, NIGHT_PREMIUM, OVERLAP_PREMIUM,
    OVERTIME_PREMIUM, PayrollEarningsBreakdown, PayrollEarningsHours, PayrollEarningsInput,
    PayrollEarningsResult, STANDARD_MONTHLY_HOURS, calculate_ordinary_hourly,
    calculate_overlap_premium, calculate_payroll_earnings, calculate_weekly_holiday_pay,
};
pub use edi_insurance::{
    EdiInsuranceApplication, EdiInsuranceConfig, EdiInsuranceInvoice, EdiInsurancePremiumRecord,
    EdiPremiumSource, apply_edi_premiums_to_invoice,
};
pub use employment_insurance_65::{
    Ei65EligibilityStatus, Ei65PayrollInput, Ei65PayrollResult, Ei65UnknownDefault,
    Ei65VerificationRecord, age_years_from_korean_identity, is_age_65_plus_for_period,
    resolve_ei_65_for_payroll,
};
pub use error::PayrollApiError;
pub use execution_plan::{
    PAYROLL_PYTHON_COMPATIBILITY_EXECUTOR, PayrollExecutionBackend, PayrollExecutionPlan,
    PayrollExecutionStep, PayrollExecutionStepKind, plan_payroll_execution,
};
pub use fixed_hours::{
    FIXED_HOURS_SOURCE_CONTRACT, FIXED_HOURS_SOURCE_TEMPLATE, FixedHoursApplication,
    FixedHoursInvoice, FixedHoursPayType, FixedHoursProfile, PAY_TYPE_HOURLY,
    PAY_TYPE_MONTHLY_SALARY, apply_fixed_hours_to_invoice, fixed_hours_audit_flags,
};
pub use invoice_audit::{
    InvoiceAuditBatchItem, InvoiceAuditBatchResult, InvoiceAuditInvoice, InvoiceAuditRecord,
    InvoiceAuditRow, InvoiceAuditStatus, InvoiceAuditSummary, audit_invoice_batch,
    audit_invoice_row, estimate_break_hours,
};
pub use policy::{
    AttendancePolicy, MissingClockPolicy, OperationPolicy, OperationPolicySnapshot,
    PayrollInputBasis,
};
pub use policy_resolution::{
    OperationPolicySource, PayrollPolicySettings, ResolvedOperationPolicy, resolve_operation_policy,
};
pub use request::{
    PayrollInputType, PayrollRunRequest, PayrollScope, parse_payroll_api_request,
    request_id_from_payload,
};
pub use response::{
    PayrollApiErrorResponse, PayrollApiResponse, PayrollValidationResponse,
    validate_payroll_api_payload, validate_payroll_api_payload_with_policy_settings,
};
pub use run::{PayrollRunResponse, PayrollRunResult, run_response_from_result};
pub use service::{
    HealthResponse, HealthStatus, PayrollApiService, ReadinessCheck, ReadinessResponse,
    ReadinessState, ServiceConfig,
};
pub use site_benefits::{
    IdentityInsuranceConfig, SiteBenefitsApplication, SiteBenefitsConfig, SiteBenefitsInvoice,
    WorkersDayConfig, apply_site_benefits_to_invoice,
};
pub use social_insurance::{
    EMPLOYMENT_INSURANCE_WORKER_RATE, HEALTH_INSURANCE_RATE, LONG_TERM_CARE_RATIO,
    NATIONAL_PENSION_RATE, PENSION_CEILING, PENSION_FLOOR, SocialInsuranceInput,
    SocialInsuranceResult, calculate_employment_insurance, calculate_social_insurance,
};
pub use workplace_hours::{
    MODE_BASE_OR_FIXED, MODE_FIXED, MODE_INVOICE_BASE, MODE_INVOICE_WORK, MODE_WORK_OR_FIXED,
    WorkplaceHoursInvoice, WorkplaceHoursMode, WorkplaceHoursPolicy,
    WorkplaceMonthlyHoursApplication, WorkplaceMonthlyHoursResolution,
    apply_monthly_hours_to_invoice, resolve_monthly_work_hours,
};

pub const PAYROLL_API_VERSION: &str = "v1";
pub const PAYROLL_API_ENDPOINT: &str = "/api/payroll/v1/runs";
pub const PAYROLL_API_VALIDATE_ENDPOINT: &str = "/api/payroll/v1/runs/validate";
pub const PAYROLL_API_HEALTH_ENDPOINT: &str = "/api/payroll/v1/healthz";
pub const PAYROLL_API_READINESS_ENDPOINT: &str = "/api/payroll/v1/readiness";
