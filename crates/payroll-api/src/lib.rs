pub mod access;
pub mod attendance;
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
pub mod workplace_hours;

pub use access::{
    authorize_payroll_request, PayrollAccessDecision, PayrollAction, PayrollPermission,
    PayrollPosition, PayrollPrincipal, PayrollRole,
};
pub use attendance::{aggregate_attendance_records, AttendanceInvoiceRow, AttendanceSourceRecord};
pub use edi_insurance::{
    apply_edi_premiums_to_invoice, EdiInsuranceApplication, EdiInsuranceConfig,
    EdiInsuranceInvoice, EdiInsurancePremiumRecord, EdiPremiumSource,
};
pub use employment_insurance_65::{
    age_years_from_korean_identity, is_age_65_plus_for_period, resolve_ei_65_for_payroll,
    Ei65EligibilityStatus, Ei65PayrollInput, Ei65PayrollResult, Ei65UnknownDefault,
    Ei65VerificationRecord,
};
pub use error::PayrollApiError;
pub use execution_plan::{
    plan_payroll_execution, PayrollExecutionBackend, PayrollExecutionPlan, PayrollExecutionStep,
    PayrollExecutionStepKind, PAYROLL_PYTHON_COMPATIBILITY_EXECUTOR,
};
pub use fixed_hours::{
    apply_fixed_hours_to_invoice, fixed_hours_audit_flags, FixedHoursApplication,
    FixedHoursInvoice, FixedHoursPayType, FixedHoursProfile, FIXED_HOURS_SOURCE_CONTRACT,
    FIXED_HOURS_SOURCE_TEMPLATE, PAY_TYPE_HOURLY, PAY_TYPE_MONTHLY_SALARY,
};
pub use invoice_audit::{
    audit_invoice_batch, audit_invoice_row, estimate_break_hours, InvoiceAuditBatchItem,
    InvoiceAuditBatchResult, InvoiceAuditInvoice, InvoiceAuditRecord, InvoiceAuditRow,
    InvoiceAuditStatus, InvoiceAuditSummary,
};
pub use policy::{
    AttendancePolicy, MissingClockPolicy, OperationPolicy, OperationPolicySnapshot,
    PayrollInputBasis,
};
pub use policy_resolution::{
    resolve_operation_policy, OperationPolicySource, PayrollPolicySettings, ResolvedOperationPolicy,
};
pub use request::{
    parse_payroll_api_request, request_id_from_payload, PayrollInputType, PayrollRunRequest,
    PayrollScope,
};
pub use response::{
    validate_payroll_api_payload, validate_payroll_api_payload_with_policy_settings,
    PayrollApiErrorResponse, PayrollApiResponse, PayrollValidationResponse,
};
pub use run::{run_response_from_result, PayrollRunResponse, PayrollRunResult};
pub use service::{
    HealthResponse, HealthStatus, PayrollApiService, ReadinessCheck, ReadinessResponse,
    ReadinessState, ServiceConfig,
};
pub use site_benefits::{
    apply_site_benefits_to_invoice, IdentityInsuranceConfig, SiteBenefitsApplication,
    SiteBenefitsConfig, SiteBenefitsInvoice, WorkersDayConfig,
};
pub use workplace_hours::{
    apply_monthly_hours_to_invoice, resolve_monthly_work_hours, WorkplaceHoursInvoice,
    WorkplaceHoursMode, WorkplaceHoursPolicy, WorkplaceMonthlyHoursApplication,
    WorkplaceMonthlyHoursResolution, MODE_BASE_OR_FIXED, MODE_FIXED, MODE_INVOICE_BASE,
    MODE_INVOICE_WORK, MODE_WORK_OR_FIXED,
};

pub const PAYROLL_API_VERSION: &str = "v1";
pub const PAYROLL_API_ENDPOINT: &str = "/api/payroll/v1/runs";
pub const PAYROLL_API_VALIDATE_ENDPOINT: &str = "/api/payroll/v1/runs/validate";
pub const PAYROLL_API_HEALTH_ENDPOINT: &str = "/api/payroll/v1/healthz";
pub const PAYROLL_API_READINESS_ENDPOINT: &str = "/api/payroll/v1/readiness";
