use crate::policy::{OperationPolicy, OperationPolicySnapshot};
use crate::request::{PayrollInputType, PayrollRunRequest};
use serde::Serialize;
use std::collections::BTreeMap;

pub const PAYROLL_PYTHON_COMPATIBILITY_EXECUTOR: &str =
    "services.payroll_automation.run_payroll_automation";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PayrollExecutionBackend {
    PythonCompatibility,
}

impl PayrollExecutionBackend {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::PythonCompatibility => "python_compatibility",
        }
    }
}

impl Serialize for PayrollExecutionBackend {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PayrollExecutionStepKind {
    ExtractAttendance,
    BuildAttendanceInvoice,
    AttachAttendanceSheet,
    ProcessInvoice,
}

impl PayrollExecutionStepKind {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ExtractAttendance => "extract_attendance",
            Self::BuildAttendanceInvoice => "build_attendance_invoice",
            Self::AttachAttendanceSheet => "attach_attendance_sheet",
            Self::ProcessInvoice => "process_invoice",
        }
    }
}

impl Serialize for PayrollExecutionStepKind {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollExecutionStep {
    pub kind: PayrollExecutionStepKind,
    pub backend: PayrollExecutionBackend,
    pub input: String,
    pub output: String,
    pub description: String,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PayrollExecutionPlan {
    pub ok: bool,
    pub scope: String,
    pub scope_key: String,
    pub affiliate: String,
    pub workplace: String,
    pub period: String,
    pub input_type: PayrollInputType,
    pub requested_input_type: PayrollInputType,
    pub backend: PayrollExecutionBackend,
    pub compatibility_executor: String,
    pub source_paths: BTreeMap<String, String>,
    pub missing_source_paths: Vec<String>,
    pub steps: Vec<PayrollExecutionStep>,
    pub operation_policy: OperationPolicy,
    pub operation_policy_source: String,
    pub warnings: Vec<String>,
}

pub fn plan_payroll_execution(
    request: &PayrollRunRequest,
    policy_snapshot: impl Into<OperationPolicySnapshot>,
) -> PayrollExecutionPlan {
    let policy_snapshot = policy_snapshot.into().normalize();
    let mut source_paths = source_paths(request);
    let (input_type, mut warnings) = planned_input_type(request, &policy_snapshot.policy);
    let mut missing_source_paths = Vec::new();
    let mut steps = Vec::new();

    match input_type {
        PayrollInputType::Invoice => {
            if let Some(invoice_path) = source_paths.get("invoice") {
                steps.push(step(
                    PayrollExecutionStepKind::ProcessInvoice,
                    invoice_path,
                    "payroll_outputs",
                    "Process the invoice workbook through the compatibility payroll executor.",
                ));
            } else {
                missing_source_paths.push("invoice".to_owned());
            }
        }
        PayrollInputType::Attendance => {
            if let Some(attendance_path) = source_paths.get("attendance") {
                steps.extend(attendance_steps(attendance_path));
            } else {
                missing_source_paths.push("attendance".to_owned());
            }
        }
        PayrollInputType::Mixed => match (
            source_paths.get("invoice").cloned(),
            source_paths.get("attendance").cloned(),
        ) {
            (Some(invoice_path), Some(attendance_path)) => {
                steps.push(step(
                    PayrollExecutionStepKind::ExtractAttendance,
                    &attendance_path,
                    "attendance_rows",
                    "Extract attendance rows before merging them into the invoice workbook.",
                ));
                steps.push(step(
                    PayrollExecutionStepKind::AttachAttendanceSheet,
                    format!("{} + attendance_rows", invoice_path),
                    "generated:mixed_invoice",
                    "Attach the attendance sheet to the supplied invoice workbook.",
                ));
                steps.push(step(
                    PayrollExecutionStepKind::ProcessInvoice,
                    "generated:mixed_invoice",
                    "payroll_outputs",
                    "Process the merged invoice workbook through the compatibility payroll executor.",
                ));
            }
            (Some(invoice_path), None) => {
                warnings.push(
                    "mixed request is missing attendance; planned invoice fallback for Python compatibility"
                        .to_owned(),
                );
                steps.push(step(
                    PayrollExecutionStepKind::ProcessInvoice,
                    &invoice_path,
                    "payroll_outputs",
                    "Process the invoice workbook through the compatibility payroll executor.",
                ));
                source_paths.remove("attendance");
            }
            (None, Some(attendance_path)) => {
                warnings.push(
                    "mixed request is missing invoice; planned attendance fallback for Python compatibility"
                        .to_owned(),
                );
                steps.extend(attendance_steps(&attendance_path));
                source_paths.remove("invoice");
            }
            (None, None) => {
                missing_source_paths.extend(["invoice".to_owned(), "attendance".to_owned()]);
            }
        },
        PayrollInputType::Auto => unreachable!("auto is resolved before planning execution steps"),
    }

    PayrollExecutionPlan {
        ok: missing_source_paths.is_empty(),
        scope: request.scope.display(),
        scope_key: request.scope.key(),
        affiliate: request.scope.affiliate.clone(),
        workplace: request.scope.workplace.clone(),
        period: request.scope.period.clone(),
        input_type,
        requested_input_type: request.input_type,
        backend: PayrollExecutionBackend::PythonCompatibility,
        compatibility_executor: PAYROLL_PYTHON_COMPATIBILITY_EXECUTOR.to_owned(),
        source_paths,
        missing_source_paths,
        steps,
        operation_policy: policy_snapshot.policy,
        operation_policy_source: policy_snapshot.source,
        warnings,
    }
}

fn planned_input_type(
    request: &PayrollRunRequest,
    policy: &OperationPolicy,
) -> (PayrollInputType, Vec<String>) {
    let input_type = request.resolved_input_type(policy);
    if input_type != PayrollInputType::Mixed {
        return (input_type, Vec::new());
    }

    match (&request.invoice_path, &request.attendance_path) {
        (None, Some(_)) => (
            PayrollInputType::Attendance,
            vec![
                "mixed request is missing invoice; planned attendance fallback for Python compatibility"
                    .to_owned(),
            ],
        ),
        (Some(_), None) => (
            PayrollInputType::Invoice,
            vec![
                "mixed request is missing attendance; planned invoice fallback for Python compatibility"
                    .to_owned(),
            ],
        ),
        _ => (PayrollInputType::Mixed, Vec::new()),
    }
}

fn source_paths(request: &PayrollRunRequest) -> BTreeMap<String, String> {
    let mut source_paths = BTreeMap::new();
    if let Some(path) = request.invoice_path.as_ref() {
        source_paths.insert("invoice".to_owned(), path.to_string_lossy().into_owned());
    }
    if let Some(path) = request.attendance_path.as_ref() {
        source_paths.insert("attendance".to_owned(), path.to_string_lossy().into_owned());
    }
    source_paths
}

fn attendance_steps(attendance_path: &str) -> Vec<PayrollExecutionStep> {
    vec![
        step(
            PayrollExecutionStepKind::ExtractAttendance,
            attendance_path,
            "attendance_rows",
            "Extract attendance rows for the selected workplace and period.",
        ),
        step(
            PayrollExecutionStepKind::BuildAttendanceInvoice,
            "attendance_rows",
            "generated:attendance_invoice",
            "Build a compatibility invoice workbook from attendance rows.",
        ),
        step(
            PayrollExecutionStepKind::ProcessInvoice,
            "generated:attendance_invoice",
            "payroll_outputs",
            "Process the generated attendance invoice through the compatibility payroll executor.",
        ),
    ]
}

fn step(
    kind: PayrollExecutionStepKind,
    input: impl Into<String>,
    output: impl Into<String>,
    description: impl Into<String>,
) -> PayrollExecutionStep {
    PayrollExecutionStep {
        kind,
        backend: PayrollExecutionBackend::PythonCompatibility,
        input: input.into(),
        output: output.into(),
        description: description.into(),
    }
}

#[cfg(test)]
mod tests {
    use crate::execution_plan::{
        PayrollExecutionBackend, PayrollExecutionStepKind, plan_payroll_execution,
    };
    use crate::policy::{OperationPolicy, OperationPolicySnapshot, PayrollInputBasis};
    use crate::request::{
        PayrollInputType, PayrollRunRequest, PayrollScope, parse_payroll_api_request,
    };
    use crate::service::{PayrollApiService, ServiceConfig};
    use serde_json::json;
    use std::{collections::BTreeMap, path::PathBuf};

    #[test]
    fn plans_auto_attendance_policy_to_compatibility_steps() {
        let request = parse_payroll_api_request(json!({
            "request_id": "req-plan-attendance",
            "affiliate": "COSS",
            "workplace": "Site A",
            "period": "2026-05",
            "attendance_path": "attendance.csv",
            "input_type": "auto"
        }))
        .unwrap();

        let plan = plan_payroll_execution(
            &request,
            OperationPolicySnapshot::new(
                OperationPolicy::new(PayrollInputBasis::Attendance),
                "site",
            ),
        );
        let value = serde_json::to_value(&plan).unwrap();

        assert!(plan.ok);
        assert_eq!(plan.backend, PayrollExecutionBackend::PythonCompatibility);
        assert_eq!(plan.input_type, PayrollInputType::Attendance);
        assert_eq!(plan.requested_input_type, PayrollInputType::Auto);
        assert_eq!(plan.source_paths["attendance"], "attendance.csv");
        assert_eq!(plan.missing_source_paths, Vec::<String>::new());
        assert_eq!(
            plan.steps[0].kind,
            PayrollExecutionStepKind::ExtractAttendance
        );
        assert_eq!(
            plan.steps[1].kind,
            PayrollExecutionStepKind::BuildAttendanceInvoice
        );
        assert_eq!(plan.steps[2].kind, PayrollExecutionStepKind::ProcessInvoice);
        assert_eq!(value["backend"], "python_compatibility");
        assert_eq!(value["steps"][1]["kind"], "build_attendance_invoice");
        assert_eq!(value["operation_policy_source"], "site");
    }

    #[test]
    fn explicit_invoice_request_ignores_attendance_policy() {
        let request = parse_payroll_api_request(json!({
            "request_id": "req-plan-invoice",
            "affiliate": "COSS",
            "workplace": "Site A",
            "period": "2026-05",
            "invoice_path": "invoice.xlsx",
            "input_type": "invoice"
        }))
        .unwrap();

        let plan = plan_payroll_execution(
            &request,
            OperationPolicySnapshot::new(
                OperationPolicy::new(PayrollInputBasis::Attendance),
                "tenant",
            ),
        );

        assert!(plan.ok);
        assert_eq!(plan.input_type, PayrollInputType::Invoice);
        assert_eq!(plan.requested_input_type, PayrollInputType::Invoice);
        assert_eq!(plan.steps.len(), 1);
        assert_eq!(plan.steps[0].kind, PayrollExecutionStepKind::ProcessInvoice);
        assert_eq!(plan.source_paths["invoice"], "invoice.xlsx");
        assert_eq!(plan.operation_policy_source, "tenant");
    }

    #[test]
    fn plans_mixed_sources_with_attendance_attachment_step() {
        let request = parse_payroll_api_request(json!({
            "request_id": "req-plan-mixed",
            "affiliate": "COSS",
            "workplace": "Site A",
            "period": "2026-05",
            "invoice_path": "invoice.xlsx",
            "attendance_path": "attendance.csv",
            "input_type": "mixed"
        }))
        .unwrap();

        let plan = plan_payroll_execution(
            &request,
            OperationPolicySnapshot::new(OperationPolicy::new(PayrollInputBasis::Hybrid), "global"),
        );
        let kinds = plan.steps.iter().map(|step| step.kind).collect::<Vec<_>>();

        assert!(plan.ok);
        assert_eq!(plan.input_type, PayrollInputType::Mixed);
        assert_eq!(plan.source_paths["invoice"], "invoice.xlsx");
        assert_eq!(plan.source_paths["attendance"], "attendance.csv");
        assert_eq!(
            kinds,
            vec![
                PayrollExecutionStepKind::ExtractAttendance,
                PayrollExecutionStepKind::AttachAttendanceSheet,
                PayrollExecutionStepKind::ProcessInvoice,
            ]
        );
    }

    #[test]
    fn mixed_without_invoice_falls_back_to_attendance_plan_for_python_compatibility() {
        let request = PayrollRunRequest {
            request_id: "req-plan-fallback".to_owned(),
            scope: PayrollScope::new("COSS", "Site A", "2026-05").unwrap(),
            input_type: PayrollInputType::Mixed,
            invoice_path: None,
            attendance_path: Some(PathBuf::from("attendance.csv")),
            tenant_id: Some("coss".to_owned()),
            metadata: BTreeMap::new(),
            validate_only: false,
        };

        let plan = plan_payroll_execution(
            &request,
            OperationPolicySnapshot::new(OperationPolicy::new(PayrollInputBasis::Hybrid), "tenant"),
        );

        assert!(plan.ok);
        assert_eq!(plan.requested_input_type, PayrollInputType::Mixed);
        assert_eq!(plan.input_type, PayrollInputType::Attendance);
        assert_eq!(
            plan.steps[0].kind,
            PayrollExecutionStepKind::ExtractAttendance
        );
        assert!(
            plan.warnings
                .iter()
                .any(|warning| warning.contains("attendance fallback"))
        );
    }

    #[test]
    fn service_delegates_execution_planning() {
        let service = PayrollApiService::new(ServiceConfig::default());
        let request = parse_payroll_api_request(json!({
            "request_id": "req-service-plan",
            "affiliate": "COSS",
            "workplace": "Site A",
            "period": "2026-05",
            "invoice_path": "invoice.xlsx",
            "input_type": "invoice"
        }))
        .unwrap();

        let plan = service.plan_run_request(
            &request,
            OperationPolicySnapshot::new(OperationPolicy::new(PayrollInputBasis::Invoice), "site"),
        );

        assert_eq!(plan.scope, "COSS/Site A/2026-05");
        assert_eq!(plan.input_type, PayrollInputType::Invoice);
        assert_eq!(
            plan.steps[0].backend,
            PayrollExecutionBackend::PythonCompatibility
        );
    }
}
