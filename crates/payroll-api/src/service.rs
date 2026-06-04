use crate::access::{
    authorize_payroll_request, PayrollAccessDecision, PayrollAction, PayrollPrincipal,
};
use crate::attendance::{
    aggregate_attendance_records, AttendanceInvoiceRow, AttendanceSourceRecord,
};
use crate::execution_plan::{plan_payroll_execution, PayrollExecutionPlan};
use crate::fixed_hours::{
    apply_fixed_hours_to_invoice, FixedHoursApplication, FixedHoursInvoice, FixedHoursProfile,
};
use crate::policy::{AttendancePolicy, OperationPolicySnapshot};
use crate::policy_resolution::PayrollPolicySettings;
use crate::request::PayrollRunRequest;
use crate::response::{
    validate_payroll_api_payload, validate_payroll_api_payload_with_policy_settings,
    PayrollApiResponse,
};
use crate::run::{run_response_from_result, PayrollRunResponse, PayrollRunResult};
use serde::Serialize;
use serde_json::Value;
use std::time::Instant;

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum HealthStatus {
    Ok,
}

impl HealthStatus {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Ok => "ok",
        }
    }
}

impl Serialize for HealthStatus {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ReadinessState {
    Ready,
    Degraded,
    NotReady,
}

impl ReadinessState {
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Ready => "ready",
            Self::Degraded => "degraded",
            Self::NotReady => "not_ready",
        }
    }
}

impl Serialize for ReadinessState {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ServiceConfig {
    pub service_name: String,
    pub environment: String,
    pub build_sha: String,
}

impl Default for ServiceConfig {
    fn default() -> Self {
        Self {
            service_name: "bitween-payroll-api".to_owned(),
            environment: "local".to_owned(),
            build_sha: String::new(),
        }
    }
}

#[derive(Clone, Debug)]
pub struct PayrollApiService {
    config: ServiceConfig,
    started_at: Instant,
}

impl Default for PayrollApiService {
    fn default() -> Self {
        Self::new(ServiceConfig::default())
    }
}

impl PayrollApiService {
    pub fn new(config: ServiceConfig) -> Self {
        Self {
            config,
            started_at: Instant::now(),
        }
    }

    pub fn validate_run_payload(
        &self,
        payload: Value,
        policy_snapshot: impl Into<Option<OperationPolicySnapshot>>,
    ) -> PayrollApiResponse {
        validate_payroll_api_payload(payload, policy_snapshot)
    }

    pub fn validate_run_payload_with_policy_settings(
        &self,
        payload: Value,
        settings: &PayrollPolicySettings,
    ) -> PayrollApiResponse {
        validate_payroll_api_payload_with_policy_settings(payload, settings)
    }

    pub fn authorize_run_request(
        &self,
        request: &PayrollRunRequest,
        principal: &PayrollPrincipal,
        action: PayrollAction,
    ) -> PayrollAccessDecision {
        authorize_payroll_request(request, principal, action)
    }

    pub fn aggregate_attendance_records<I, S>(
        &self,
        records: I,
        workplace: S,
        policy: &AttendancePolicy,
    ) -> Vec<AttendanceInvoiceRow>
    where
        I: IntoIterator<Item = AttendanceSourceRecord>,
        S: Into<String>,
    {
        aggregate_attendance_records(records, workplace, policy)
    }

    pub fn plan_run_request(
        &self,
        request: &PayrollRunRequest,
        policy_snapshot: impl Into<OperationPolicySnapshot>,
    ) -> PayrollExecutionPlan {
        plan_payroll_execution(request, policy_snapshot)
    }

    pub fn apply_fixed_hours_to_invoice<S>(
        &self,
        invoice: FixedHoursInvoice,
        profile: &FixedHoursProfile,
        workplace: S,
    ) -> FixedHoursApplication
    where
        S: Into<String>,
    {
        apply_fixed_hours_to_invoice(invoice, profile, workplace)
    }

    pub fn run_response(
        &self,
        result: PayrollRunResult,
        request_id: impl Into<String>,
    ) -> PayrollRunResponse {
        run_response_from_result(result, request_id)
    }

    pub fn health(&self) -> HealthResponse {
        HealthResponse {
            ok: true,
            status: HealthStatus::Ok,
            service: self.config.service_name.clone(),
            version: crate::PAYROLL_API_VERSION.to_owned(),
            environment: self.config.environment.clone(),
            build_sha: self.config.build_sha.clone(),
            uptime_seconds: self.started_at.elapsed().as_secs(),
        }
    }

    pub fn readiness(&self, checks: impl IntoIterator<Item = ReadinessCheck>) -> ReadinessResponse {
        let checks = checks.into_iter().collect::<Vec<_>>();
        let state = readiness_state(&checks);
        ReadinessResponse {
            ready: state == ReadinessState::Ready,
            state,
            service: self.config.service_name.clone(),
            version: crate::PAYROLL_API_VERSION.to_owned(),
            checks,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct HealthResponse {
    pub ok: bool,
    pub status: HealthStatus,
    pub service: String,
    pub version: String,
    pub environment: String,
    pub build_sha: String,
    pub uptime_seconds: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ReadinessResponse {
    pub ready: bool,
    pub state: ReadinessState,
    pub service: String,
    pub version: String,
    pub checks: Vec<ReadinessCheck>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ReadinessCheck {
    pub name: String,
    pub state: ReadinessState,
    pub required: bool,
    pub message: String,
}

impl ReadinessCheck {
    pub fn ready(name: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            state: ReadinessState::Ready,
            required: true,
            message: message.into(),
        }
    }

    pub fn degraded(name: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            state: ReadinessState::Degraded,
            required: false,
            message: message.into(),
        }
    }

    pub fn not_ready(name: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            state: ReadinessState::NotReady,
            required: true,
            message: message.into(),
        }
    }
}

fn readiness_state(checks: &[ReadinessCheck]) -> ReadinessState {
    if checks
        .iter()
        .any(|check| check.required && check.state == ReadinessState::NotReady)
    {
        ReadinessState::NotReady
    } else if checks
        .iter()
        .any(|check| check.state == ReadinessState::Degraded)
    {
        ReadinessState::Degraded
    } else {
        ReadinessState::Ready
    }
}

#[cfg(test)]
mod tests {
    use crate::access::{PayrollAction, PayrollPosition, PayrollPrincipal, PayrollRole};
    use crate::policy::{OperationPolicy, OperationPolicySnapshot, PayrollInputBasis};
    use crate::request::parse_payroll_api_request;
    use crate::service::{
        HealthStatus, PayrollApiService, ReadinessCheck, ReadinessState, ServiceConfig,
    };
    use serde_json::json;

    #[test]
    fn service_validates_payroll_payload_with_policy_snapshot() {
        let service = PayrollApiService::new(ServiceConfig::default());
        let response = service.validate_run_payload(
            json!({
                "request_id": "req-service",
                "affiliate": "Affiliate",
                "workplace": "Site A",
                "period": "2026-05",
                "attendance_path": "attendance.csv",
                "input_type": "auto"
            }),
            Some(OperationPolicySnapshot::new(
                OperationPolicy::new(PayrollInputBasis::Attendance),
                "site",
            )),
        );
        let value = serde_json::to_value(response).unwrap();

        assert_eq!(value["status"], "validated");
        assert_eq!(value["input_type"], "attendance");
        assert_eq!(value["operation_policy_source"], "site");
    }

    #[test]
    fn service_authorizes_parsed_payroll_request() {
        let service = PayrollApiService::new(ServiceConfig::default());
        let request = parse_payroll_api_request(json!({
            "request_id": "req-auth-service",
            "affiliate": "COSS",
            "workplace": "Site A",
            "period": "2026-05",
            "invoice_path": "invoice.xlsx",
            "tenant_id": "coss"
        }))
        .unwrap();
        let principal = PayrollPrincipal::new("user-finance", "coss")
            .with_role(PayrollRole::Finance)
            .with_position(PayrollPosition::Manager)
            .with_org_unit("finance")
            .with_effective_platforms(["payroll"]);

        let decision = service.authorize_run_request(&request, &principal, PayrollAction::Run);
        let value = serde_json::to_value(&decision).unwrap();

        assert!(decision.allowed);
        assert_eq!(value["ok"], true);
        assert_eq!(value["action"], "run");
        assert_eq!(value["scope"], "COSS/Site A/2026-05");
    }

    #[test]
    fn health_response_is_stable_and_probe_safe() {
        let service = PayrollApiService::new(ServiceConfig {
            service_name: "bitween-payroll-api".to_owned(),
            environment: "test".to_owned(),
            build_sha: "abc123".to_owned(),
        });
        let health = service.health();
        let value = serde_json::to_value(&health).unwrap();

        assert_eq!(health.status, HealthStatus::Ok);
        assert_eq!(value["ok"], true);
        assert_eq!(value["status"], "ok");
        assert_eq!(value["service"], "bitween-payroll-api");
        assert_eq!(value["version"], crate::PAYROLL_API_VERSION);
        assert_eq!(value["environment"], "test");
        assert_eq!(value["build_sha"], "abc123");
        assert!(value["uptime_seconds"].as_u64().unwrap() <= 1);
    }

    #[test]
    fn readiness_aggregates_required_checks_without_secrets() {
        let service = PayrollApiService::new(ServiceConfig::default());
        let readiness = service.readiness(vec![
            ReadinessCheck::ready("policy", "Rust policy invariants loaded"),
            ReadinessCheck::degraded("python_execution", "Compatibility fallback still active"),
            ReadinessCheck::not_ready("database", "Rust persistence is not configured"),
        ]);
        let value = serde_json::to_value(&readiness).unwrap();

        assert!(!readiness.ready);
        assert_eq!(readiness.state, ReadinessState::NotReady);
        assert_eq!(value["ready"], false);
        assert_eq!(value["state"], "not_ready");
        assert_eq!(value["checks"][0]["name"], "policy");
        assert_eq!(value["checks"][0]["required"], true);
        assert_eq!(value["checks"][1]["state"], "degraded");
        assert_eq!(value["checks"][1]["required"], false);
        assert_eq!(value["checks"][2]["state"], "not_ready");
        assert_eq!(value["checks"][2]["required"], true);
        assert!(value
            .to_string()
            .contains("Rust persistence is not configured"));
        assert!(!value.to_string().to_ascii_lowercase().contains("secret"));
    }
}
