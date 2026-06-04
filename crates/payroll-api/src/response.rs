use crate::error::PayrollApiError;
use crate::policy::OperationPolicySnapshot;
use crate::policy_resolution::{PayrollPolicySettings, resolve_operation_policy};
use crate::request::{PayrollRunRequest, parse_payroll_api_request, request_id_from_payload};
use serde::Serialize;
use serde_json::{Value, json};
use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(untagged)]
pub enum PayrollApiResponse {
    Validated(PayrollValidationResponse),
    Error(PayrollApiErrorResponse),
}

impl PayrollApiResponse {
    pub fn ok(&self) -> bool {
        matches!(self, Self::Validated(_))
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PayrollValidationResponse {
    pub ok: bool,
    pub status: &'static str,
    pub will_run: bool,
    pub can_run: bool,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub request_id: String,
    pub scope: String,
    pub scope_key: String,
    pub affiliate: String,
    pub workplace: String,
    pub period: String,
    pub input_type: crate::request::PayrollInputType,
    pub requested_input_type: crate::request::PayrollInputType,
    pub tenant_id: String,
    pub paths: BTreeMap<String, String>,
    pub metadata_keys: Vec<String>,
    pub operation_policy: crate::policy::OperationPolicy,
    pub operation_policy_source: String,
    pub warnings: Vec<String>,
    pub error_code: String,
    pub details: Value,
    pub error: String,
}

impl PayrollValidationResponse {
    pub fn from_request(
        request: &PayrollRunRequest,
        policy_snapshot: OperationPolicySnapshot,
    ) -> Self {
        let policy_snapshot = policy_snapshot.normalize();
        let mut paths = BTreeMap::new();
        if let Some(path) = request.invoice_path.as_ref() {
            paths.insert("invoice".to_owned(), path.to_string_lossy().into_owned());
        }
        if let Some(path) = request.attendance_path.as_ref() {
            paths.insert("attendance".to_owned(), path.to_string_lossy().into_owned());
        }

        Self {
            ok: true,
            status: "validated",
            will_run: false,
            can_run: true,
            request_id: request.request_id.clone(),
            scope: request.scope.display(),
            scope_key: request.scope.key(),
            affiliate: request.scope.affiliate.clone(),
            workplace: request.scope.workplace.clone(),
            period: request.scope.period.clone(),
            input_type: request.resolved_input_type(&policy_snapshot.policy),
            requested_input_type: request.input_type,
            tenant_id: request.tenant_id.clone().unwrap_or_default(),
            paths,
            metadata_keys: request.metadata.keys().cloned().collect(),
            operation_policy: policy_snapshot.policy,
            operation_policy_source: policy_snapshot.source,
            warnings: Vec::new(),
            error_code: String::new(),
            details: json!({}),
            error: String::new(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PayrollApiErrorResponse {
    pub ok: bool,
    pub status: &'static str,
    pub will_run: bool,
    pub can_run: bool,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub request_id: String,
    pub error_code: String,
    pub error: String,
    pub warnings: Vec<String>,
    pub details: Value,
}

impl PayrollApiErrorResponse {
    pub fn from_error(error: PayrollApiError, request_id: impl Into<String>) -> Self {
        let message = error.to_string();
        Self {
            ok: false,
            status: "error",
            will_run: false,
            can_run: false,
            request_id: request_id.into(),
            error_code: error.code().to_owned(),
            error: message.clone(),
            warnings: vec![message],
            details: error.details(),
        }
    }
}

pub fn validate_payroll_api_payload(
    payload: Value,
    policy_snapshot: impl Into<Option<OperationPolicySnapshot>>,
) -> PayrollApiResponse {
    let request_id = request_id_from_payload(&payload);
    match parse_payroll_api_request(payload) {
        Ok(request) => PayrollApiResponse::Validated(PayrollValidationResponse::from_request(
            &request,
            policy_snapshot.into().unwrap_or_default(),
        )),
        Err(error) => {
            PayrollApiResponse::Error(PayrollApiErrorResponse::from_error(error, request_id))
        }
    }
}

pub fn validate_payroll_api_payload_with_policy_settings(
    payload: Value,
    settings: &PayrollPolicySettings,
) -> PayrollApiResponse {
    let request_id = request_id_from_payload(&payload);
    match parse_payroll_api_request(payload) {
        Ok(request) => {
            let resolved = resolve_operation_policy(&request.scope.workplace, settings);
            PayrollApiResponse::Validated(PayrollValidationResponse::from_request(
                &request,
                resolved.snapshot(),
            ))
        }
        Err(error) => {
            PayrollApiResponse::Error(PayrollApiErrorResponse::from_error(error, request_id))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::policy::{AttendancePolicy, MissingClockPolicy, OperationPolicy, PayrollInputBasis};
    use crate::request::{PayrollInputType, PayrollScope};
    use serde_json::json;

    #[test]
    fn validates_nested_payload_without_running_payroll() {
        let response = validate_payroll_api_payload(
            json!({
                "request_id": "req-validate",
                "scope": {
                    "affiliate": "Affiliate",
                    "workplace": "Site A",
                    "period": "2026-05"
                },
                "invoicePath": "invoice.xlsx",
                "attendancePath": "attendance.csv",
                "inputType": "mixed",
                "tenantId": "tenant-a",
                "metadata": {"requested_by": "frontend"}
            }),
            Some(OperationPolicySnapshot::new(
                OperationPolicy::new(PayrollInputBasis::Hybrid).with_payday("25일"),
                "tenant",
            )),
        );
        let value = serde_json::to_value(response).unwrap();

        assert_eq!(value["ok"], true);
        assert_eq!(value["status"], "validated");
        assert_eq!(value["will_run"], false);
        assert_eq!(value["can_run"], true);
        assert_eq!(value["request_id"], "req-validate");
        assert_eq!(value["scope"], "Affiliate/Site A/2026-05");
        assert_eq!(
            value["scope_key"],
            PayrollScope::new("Affiliate", "Site A", "2026-05")
                .unwrap()
                .key()
        );
        assert_eq!(value["input_type"], "mixed");
        assert_eq!(value["requested_input_type"], "mixed");
        assert_eq!(value["tenant_id"], "tenant-a");
        assert_eq!(value["paths"]["invoice"], "invoice.xlsx");
        assert_eq!(value["paths"]["attendance"], "attendance.csv");
        assert_eq!(value["metadata_keys"], json!(["requested_by"]));
        assert_eq!(value["operation_policy_source"], "tenant");
    }

    #[test]
    fn resolves_auto_input_from_operation_policy() {
        let response = validate_payroll_api_payload(
            json!({
                "request_id": "req-auto",
                "affiliate": "Affiliate",
                "workplace": "Site A",
                "period": "2026-05",
                "attendance_path": "attendance.csv",
                "input_type": "auto",
                "validate_only": true
            }),
            Some(OperationPolicySnapshot::new(
                OperationPolicy::new(PayrollInputBasis::Attendance),
                "site",
            )),
        );
        let value = serde_json::to_value(response).unwrap();

        assert_eq!(value["status"], "validated");
        assert_eq!(value["input_type"], "attendance");
        assert_eq!(value["requested_input_type"], "auto");
        assert_eq!(value["operation_policy_source"], "site");
    }

    #[test]
    fn returns_stable_error_for_invalid_period() {
        let response = validate_payroll_api_payload(
            json!({
                "requestId": "req-bad",
                "affiliate": "Affiliate",
                "workplace": "Site A",
                "period": "202605",
                "invoice_path": "invoice.xlsx"
            }),
            None,
        );
        let value = serde_json::to_value(response).unwrap();

        assert_eq!(value["ok"], false);
        assert_eq!(value["status"], "error");
        assert_eq!(value["request_id"], "req-bad");
        assert_eq!(value["error_code"], "invalid_period");
        assert_eq!(value["details"]["period_format"], "YYYY-MM");
    }

    #[test]
    fn parses_internal_scope_key() {
        let scope = PayrollScope::new("Affiliate", "Site A", "2026-05").unwrap();
        let request = parse_payroll_api_request(json!({
            "scope": scope.key(),
            "invoice_path": "invoice.xlsx"
        }))
        .unwrap();

        assert_eq!(request.scope, scope);
        assert_eq!(request.input_type, PayrollInputType::Auto);
    }

    #[test]
    fn returns_stable_error_for_non_object_payload() {
        let response = validate_payroll_api_payload(json!("bad"), None);
        let value = serde_json::to_value(response).unwrap();

        assert_eq!(value["ok"], false);
        assert_eq!(value["error_code"], "invalid_payload");
        assert_eq!(value["will_run"], false);
        assert_eq!(value["can_run"], false);
    }

    #[test]
    fn validation_response_serializes_normalized_operation_policy() {
        let mut policy = OperationPolicy::new(PayrollInputBasis::Attendance);
        policy.payday = Some(String::new());
        policy.policy_note = "  reviewed by payroll ops  ".to_owned();
        policy.attendance = AttendancePolicy {
            rounding_minutes: -30,
            late_grace_minutes: 9999,
            early_leave_grace_minutes: -1,
            overtime_rounding_minutes: 0,
            missing_clock_policy: MissingClockPolicy::Deduct,
            ..AttendancePolicy::default()
        };

        let response = validate_payroll_api_payload(
            json!({
                "request_id": "req-policy",
                "affiliate": "Affiliate",
                "workplace": "Site A",
                "period": "2026-05",
                "attendance_path": "attendance.csv",
                "input_type": "auto"
            }),
            Some(OperationPolicySnapshot::new(policy, "site")),
        );
        let value = serde_json::to_value(response).unwrap();

        assert_eq!(value["status"], "validated");
        assert_eq!(value["input_type"], "attendance");
        assert_eq!(value["operation_policy"]["input_basis"], "attendance");
        assert_eq!(value["operation_policy"]["payday"], "25일");
        assert_eq!(
            value["operation_policy"]["policy_note"],
            "reviewed by payroll ops"
        );
        assert_eq!(
            value["operation_policy"]["attendance"]["rounding_minutes"],
            1
        );
        assert_eq!(
            value["operation_policy"]["attendance"]["late_grace_minutes"],
            240
        );
        assert_eq!(
            value["operation_policy"]["attendance"]["early_leave_grace_minutes"],
            0
        );
        assert_eq!(
            value["operation_policy"]["attendance"]["overtime_rounding_minutes"],
            1
        );
        assert_eq!(
            value["operation_policy"]["attendance"]["missing_clock_policy"],
            "deduct"
        );
    }
}
