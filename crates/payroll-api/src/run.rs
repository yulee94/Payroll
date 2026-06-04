use crate::policy::OperationPolicy;
use crate::request::{PayrollInputType, PayrollScope};
use serde::Serialize;
use serde_json::{Value, json};
use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq)]
pub struct PayrollRunResult {
    pub ok: bool,
    pub scope: PayrollScope,
    pub input_type: PayrollInputType,
    pub count: u64,
    pub warnings: Vec<String>,
    pub paths: BTreeMap<String, String>,
    pub payroll_audit: Value,
    pub roster: Value,
    pub operation_policy: OperationPolicy,
    pub operation_policy_source: String,
    pub error: String,
}

impl PayrollRunResult {
    pub fn success(scope: PayrollScope, input_type: PayrollInputType) -> Self {
        Self {
            ok: true,
            scope,
            input_type,
            count: 0,
            warnings: Vec::new(),
            paths: BTreeMap::new(),
            payroll_audit: json!({}),
            roster: json!({}),
            operation_policy: OperationPolicy::default(),
            operation_policy_source: String::new(),
            error: String::new(),
        }
    }

    pub fn failure(
        scope: PayrollScope,
        input_type: PayrollInputType,
        error: impl Into<String>,
    ) -> Self {
        Self {
            ok: false,
            error: error.into(),
            ..Self::success(scope, input_type)
        }
    }

    pub fn with_count(mut self, count: u64) -> Self {
        self.count = count;
        self
    }

    pub fn with_warning(mut self, warning: impl Into<String>) -> Self {
        self.warnings.push(warning.into());
        self
    }

    pub fn with_path(mut self, name: impl Into<String>, path: impl Into<String>) -> Self {
        self.paths.insert(name.into(), path.into());
        self
    }

    pub fn with_payroll_audit(mut self, payroll_audit: Value) -> Self {
        self.payroll_audit = payroll_audit;
        self
    }

    pub fn with_roster(mut self, roster: Value) -> Self {
        self.roster = roster;
        self
    }

    pub fn with_operation_policy(
        mut self,
        operation_policy: OperationPolicy,
        source: impl Into<String>,
    ) -> Self {
        self.operation_policy = operation_policy;
        self.operation_policy_source = source.into();
        self
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PayrollRunResponse {
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
    pub input_type: PayrollInputType,
    pub count: u64,
    pub warnings: Vec<String>,
    pub paths: BTreeMap<String, String>,
    pub payroll_audit: Value,
    pub roster: Value,
    pub operation_policy: OperationPolicy,
    pub operation_policy_source: String,
    pub error_code: String,
    pub details: Value,
    pub error: String,
}

pub fn run_response_from_result(
    result: PayrollRunResult,
    request_id: impl Into<String>,
) -> PayrollRunResponse {
    let status = if result.ok { "success" } else { "error" };
    let error_code = if result.ok {
        String::new()
    } else {
        "payroll_run_failed".to_owned()
    };

    PayrollRunResponse {
        ok: result.ok,
        status,
        will_run: true,
        can_run: result.ok,
        request_id: request_id.into(),
        scope: result.scope.display(),
        scope_key: result.scope.key(),
        affiliate: result.scope.affiliate,
        workplace: result.scope.workplace,
        period: result.scope.period,
        input_type: result.input_type,
        count: result.count,
        warnings: result.warnings,
        paths: result.paths,
        payroll_audit: result.payroll_audit,
        roster: result.roster,
        operation_policy: result.operation_policy.normalized(),
        operation_policy_source: result.operation_policy_source,
        error_code,
        details: json!({}),
        error: result.error,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::policy::{AttendancePolicy, MissingClockPolicy, OperationPolicy, PayrollInputBasis};
    use crate::request::{PayrollInputType, PayrollScope};
    use crate::service::{PayrollApiService, ServiceConfig};
    use serde_json::json;

    #[test]
    fn formats_success_run_response_without_exception_object() {
        let scope = PayrollScope::new("COSS", "Site A", "2026-05").unwrap();
        let policy = OperationPolicy {
            input_basis: PayrollInputBasis::Attendance,
            payday: Some(String::new()),
            attendance: AttendancePolicy {
                rounding_minutes: -30,
                missing_clock_policy: MissingClockPolicy::Deduct,
                ..AttendancePolicy::default()
            },
            ..OperationPolicy::default()
        };

        let response = run_response_from_result(
            PayrollRunResult::success(scope.clone(), PayrollInputType::Mixed)
                .with_count(28)
                .with_warning("rounded overtime")
                .with_path("ledger", "s3://bitween-payroll/output/ledger.xlsx")
                .with_path("payslip", "s3://bitween-payroll/output/payslip.xlsx")
                .with_payroll_audit(json!({"generated_by": "rust"}))
                .with_roster(json!({"source": "templates"}))
                .with_operation_policy(policy, "tenant"),
            "payroll-run-2026-05-coss-site-a",
        );
        let value = serde_json::to_value(response).unwrap();

        assert_eq!(value["ok"], true);
        assert_eq!(value["status"], "success");
        assert_eq!(value["will_run"], true);
        assert_eq!(value["can_run"], true);
        assert_eq!(value["request_id"], "payroll-run-2026-05-coss-site-a");
        assert_eq!(value["scope"], "COSS/Site A/2026-05");
        assert_eq!(value["scope_key"], scope.key());
        assert_eq!(value["affiliate"], "COSS");
        assert_eq!(value["workplace"], "Site A");
        assert_eq!(value["period"], "2026-05");
        assert_eq!(value["input_type"], "mixed");
        assert_eq!(value["count"], 28);
        assert_eq!(value["warnings"], json!(["rounded overtime"]));
        assert_eq!(
            value["paths"]["ledger"],
            "s3://bitween-payroll/output/ledger.xlsx"
        );
        assert_eq!(value["payroll_audit"]["generated_by"], "rust");
        assert_eq!(value["roster"]["source"], "templates");
        assert_eq!(value["operation_policy"]["input_basis"], "attendance");
        assert_eq!(value["operation_policy"]["payday"], "25일");
        assert_eq!(
            value["operation_policy"]["attendance"]["rounding_minutes"],
            1
        );
        assert_eq!(
            value["operation_policy"]["attendance"]["missing_clock_policy"],
            "deduct"
        );
        assert_eq!(value["operation_policy_source"], "tenant");
        assert_eq!(value["error_code"], "");
        assert_eq!(value["details"], json!({}));
        assert_eq!(value["error"], "");
        assert!(value.get("exception").is_none());
    }

    #[test]
    fn formats_run_failure_as_execution_error_not_validation_error() {
        let scope = PayrollScope::new("Affiliate", "Site A", "2026-05").unwrap();

        let response = run_response_from_result(
            PayrollRunResult::failure(scope.clone(), PayrollInputType::Attendance, "boom")
                .with_warning("manual review required"),
            "req-1",
        );
        let value = serde_json::to_value(response).unwrap();

        assert_eq!(value["ok"], false);
        assert_eq!(value["status"], "error");
        assert_eq!(value["will_run"], true);
        assert_eq!(value["can_run"], false);
        assert_eq!(value["request_id"], "req-1");
        assert_eq!(value["scope"], "Affiliate/Site A/2026-05");
        assert_eq!(value["scope_key"], scope.key());
        assert_eq!(value["input_type"], "attendance");
        assert_eq!(value["error_code"], "payroll_run_failed");
        assert_eq!(value["details"], json!({}));
        assert_eq!(value["error"], "boom");
        assert_eq!(value["warnings"], json!(["manual review required"]));
        assert!(value.get("exception").is_none());
    }

    #[test]
    fn omits_empty_request_id_from_run_response() {
        let scope = PayrollScope::new("COSS", "Site A", "2026-05").unwrap();

        let response = run_response_from_result(
            PayrollRunResult::success(scope, PayrollInputType::Invoice),
            "",
        );
        let value = serde_json::to_value(response).unwrap();

        assert!(value.get("request_id").is_none());
        assert_eq!(value["status"], "success");
    }

    #[test]
    fn service_delegates_run_response_shaping() {
        let service = PayrollApiService::new(ServiceConfig::default());
        let scope = PayrollScope::new("COSS", "Site A", "2026-05").unwrap();

        let response = service.run_response(
            PayrollRunResult::success(scope, PayrollInputType::Invoice).with_count(2),
            "req-service-run",
        );
        let value = serde_json::to_value(response).unwrap();

        assert_eq!(value["status"], "success");
        assert_eq!(value["request_id"], "req-service-run");
        assert_eq!(value["count"], 2);
    }
}
