pub mod access;
pub mod attendance;
pub mod error;
pub mod execution_plan;
pub mod policy;
pub mod policy_resolution;
pub mod request;
pub mod response;
pub mod run;
pub mod service;

pub use access::{
    authorize_payroll_request, PayrollAccessDecision, PayrollAction, PayrollPermission,
    PayrollPosition, PayrollPrincipal, PayrollRole,
};
pub use attendance::{aggregate_attendance_records, AttendanceInvoiceRow, AttendanceSourceRecord};
pub use error::PayrollApiError;
pub use execution_plan::{
    plan_payroll_execution, PayrollExecutionBackend, PayrollExecutionPlan, PayrollExecutionStep,
    PayrollExecutionStepKind, PAYROLL_PYTHON_COMPATIBILITY_EXECUTOR,
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

pub const PAYROLL_API_VERSION: &str = "v1";
pub const PAYROLL_API_ENDPOINT: &str = "/api/payroll/v1/runs";
pub const PAYROLL_API_VALIDATE_ENDPOINT: &str = "/api/payroll/v1/runs/validate";
pub const PAYROLL_API_HEALTH_ENDPOINT: &str = "/api/payroll/v1/healthz";
pub const PAYROLL_API_READINESS_ENDPOINT: &str = "/api/payroll/v1/readiness";
