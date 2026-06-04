pub mod error;
pub mod policy;
pub mod request;
pub mod response;
pub mod service;

pub use error::PayrollApiError;
pub use policy::{
    AttendancePolicy, MissingClockPolicy, OperationPolicy, OperationPolicySnapshot,
    PayrollInputBasis,
};
pub use request::{
    parse_payroll_api_request, request_id_from_payload, PayrollInputType, PayrollRunRequest,
    PayrollScope,
};
pub use response::{
    validate_payroll_api_payload, PayrollApiErrorResponse, PayrollApiResponse,
    PayrollValidationResponse,
};
pub use service::{
    HealthResponse, HealthStatus, PayrollApiService, ReadinessCheck, ReadinessResponse,
    ReadinessState, ServiceConfig,
};

pub const PAYROLL_API_VERSION: &str = "v1";
pub const PAYROLL_API_ENDPOINT: &str = "/api/payroll/v1/runs";
pub const PAYROLL_API_VALIDATE_ENDPOINT: &str = "/api/payroll/v1/runs/validate";
pub const PAYROLL_API_HEALTH_ENDPOINT: &str = "/api/payroll/v1/healthz";
pub const PAYROLL_API_READINESS_ENDPOINT: &str = "/api/payroll/v1/readiness";
