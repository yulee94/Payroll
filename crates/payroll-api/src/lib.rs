pub mod error;
pub mod policy;
pub mod request;
pub mod response;

pub use error::PayrollApiError;
pub use policy::{OperationPolicy, OperationPolicySnapshot, PayrollInputBasis};
pub use request::{
    parse_payroll_api_request, request_id_from_payload, PayrollInputType, PayrollRunRequest,
    PayrollScope,
};
pub use response::{
    validate_payroll_api_payload, PayrollApiErrorResponse, PayrollApiResponse,
    PayrollValidationResponse,
};

pub const PAYROLL_API_VERSION: &str = "v1";
pub const PAYROLL_API_ENDPOINT: &str = "/api/payroll/v1/runs";
pub const PAYROLL_API_VALIDATE_ENDPOINT: &str = "/api/payroll/v1/runs/validate";
