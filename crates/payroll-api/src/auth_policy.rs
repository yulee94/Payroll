use serde::Serialize;

pub const AUTH_POLICY_SCHEMA: &str = "bitween.auth-policy.v1";
pub const AUTHZ_POLICY_ID: &str = "bitween.authz.rbac-abac-pbac.v1";

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize)]
pub enum AuthAcrLevel {
    Routine,
    Elevated,
    Sensitive,
    Critical,
}

impl AuthAcrLevel {
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().as_str() {
            "routine" => Some(Self::Routine),
            "elevated" => Some(Self::Elevated),
            "sensitive" => Some(Self::Sensitive),
            "critical" => Some(Self::Critical),
            _ => None,
        }
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Routine => "routine",
            Self::Elevated => "elevated",
            Self::Sensitive => "sensitive",
            Self::Critical => "critical",
        }
    }

    pub fn satisfies(self, required: Self) -> bool {
        self >= required
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AuthSensitiveOperation {
    ReadWorkspace,
    HrEmployeeRead,
    HrEmployeeWrite,
    ArchiveRead,
    ArchiveUpload,
    ArchiveReview,
    ArchiveAdmit,
    ArchiveRollback,
    ArchiveSync,
    UserPreferenceUpdate,
    WorkflowTemplateRead,
    WorkflowTemplateWrite,
    WorkflowStepExecute,
    PayrollRun,
    PayrollExport,
    PayrollPolicyChange,
    ApprovalSigning,
    TenantDestructiveChange,
}

impl AuthSensitiveOperation {
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().replace('-', "_").as_str() {
            "read_workspace" => Some(Self::ReadWorkspace),
            "hr_employee_read" => Some(Self::HrEmployeeRead),
            "hr_employee_write" => Some(Self::HrEmployeeWrite),
            "archive_read" => Some(Self::ArchiveRead),
            "archive_upload" => Some(Self::ArchiveUpload),
            "archive_review" => Some(Self::ArchiveReview),
            "archive_admit" => Some(Self::ArchiveAdmit),
            "archive_rollback" => Some(Self::ArchiveRollback),
            "archive_sync" => Some(Self::ArchiveSync),
            "user_preference_update" => Some(Self::UserPreferenceUpdate),
            "workflow_template_read" => Some(Self::WorkflowTemplateRead),
            "workflow_template_write" => Some(Self::WorkflowTemplateWrite),
            "workflow_step_execute" => Some(Self::WorkflowStepExecute),
            "payroll_run" => Some(Self::PayrollRun),
            "payroll_export" => Some(Self::PayrollExport),
            "payroll_policy_change" => Some(Self::PayrollPolicyChange),
            "approval_signing" => Some(Self::ApprovalSigning),
            "tenant_destructive_change" => Some(Self::TenantDestructiveChange),
            _ => None,
        }
    }

    pub const fn id(self) -> &'static str {
        match self {
            Self::ReadWorkspace => "read_workspace",
            Self::HrEmployeeRead => "hr_employee_read",
            Self::HrEmployeeWrite => "hr_employee_write",
            Self::ArchiveRead => "archive_read",
            Self::ArchiveUpload => "archive_upload",
            Self::ArchiveReview => "archive_review",
            Self::ArchiveAdmit => "archive_admit",
            Self::ArchiveRollback => "archive_rollback",
            Self::ArchiveSync => "archive_sync",
            Self::UserPreferenceUpdate => "user_preference_update",
            Self::WorkflowTemplateRead => "workflow_template_read",
            Self::WorkflowTemplateWrite => "workflow_template_write",
            Self::WorkflowStepExecute => "workflow_step_execute",
            Self::PayrollRun => "payroll_run",
            Self::PayrollExport => "payroll_export",
            Self::PayrollPolicyChange => "payroll_policy_change",
            Self::ApprovalSigning => "approval_signing",
            Self::TenantDestructiveChange => "tenant_destructive_change",
        }
    }

    pub const fn required_acr(self) -> AuthAcrLevel {
        match self {
            Self::ReadWorkspace | Self::UserPreferenceUpdate | Self::WorkflowTemplateRead => AuthAcrLevel::Routine,
            Self::HrEmployeeRead
            | Self::HrEmployeeWrite
            | Self::ArchiveRead
            | Self::ArchiveUpload => AuthAcrLevel::Elevated,
            Self::ArchiveReview
            | Self::ArchiveAdmit
            | Self::ArchiveRollback
            | Self::ArchiveSync
            | Self::PayrollRun
            | Self::PayrollExport
            | Self::PayrollPolicyChange
            | Self::WorkflowTemplateWrite
            | Self::WorkflowStepExecute
            | Self::ApprovalSigning => AuthAcrLevel::Sensitive,
            Self::TenantDestructiveChange => AuthAcrLevel::Critical,
        }
    }

    pub const fn required_data_class(self) -> AuthDataClass {
        match self {
            Self::ReadWorkspace | Self::UserPreferenceUpdate | Self::WorkflowTemplateRead => AuthDataClass::Internal,
            Self::HrEmployeeRead
            | Self::HrEmployeeWrite
            | Self::ArchiveRead
            | Self::ArchiveUpload
            | Self::ArchiveReview
            | Self::ArchiveAdmit
            | Self::ArchiveRollback
            | Self::ArchiveSync => AuthDataClass::EmployeeRestricted,
            Self::PayrollRun
            | Self::PayrollExport
            | Self::PayrollPolicyChange
            | Self::WorkflowTemplateWrite
            | Self::WorkflowStepExecute
            | Self::ApprovalSigning => AuthDataClass::PayrollConfidential,
            Self::TenantDestructiveChange => AuthDataClass::TenantCritical,
        }
    }

    const fn requires_workplace_scope(self) -> bool {
        match self {
            Self::ReadWorkspace
            | Self::UserPreferenceUpdate
            | Self::PayrollPolicyChange
            | Self::WorkflowTemplateRead
            | Self::WorkflowTemplateWrite
            | Self::TenantDestructiveChange => false,
            Self::HrEmployeeRead
            | Self::HrEmployeeWrite
            | Self::ArchiveRead
            | Self::ArchiveUpload
            | Self::ArchiveReview
            | Self::ArchiveAdmit
            | Self::ArchiveRollback
            | Self::ArchiveSync
            | Self::PayrollRun
            | Self::WorkflowStepExecute
            | Self::PayrollExport
            | Self::ApprovalSigning => true,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct AuthStepUpDecision {
    pub schema: &'static str,
    pub operation: &'static str,
    pub allowed: bool,
    pub current_acr: Option<&'static str>,
    pub required_acr: &'static str,
    pub reason: &'static str,
}

pub fn evaluate_step_up(
    current_acr: Option<AuthAcrLevel>,
    operation: AuthSensitiveOperation,
) -> AuthStepUpDecision {
    let required = operation.required_acr();
    let allowed = current_acr.is_some_and(|current| current.satisfies(required));
    AuthStepUpDecision {
        schema: AUTH_POLICY_SCHEMA,
        operation: operation.id(),
        allowed,
        current_acr: current_acr.map(AuthAcrLevel::as_str),
        required_acr: required.as_str(),
        reason: match (current_acr, allowed) {
            (None, _) => "acr_missing",
            (Some(_), true) => "acr_sufficient",
            (Some(_), false) => "step_up_required",
        },
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize)]
pub enum AuthDataClass {
    Internal,
    EmployeeRestricted,
    PayrollConfidential,
    TenantCritical,
}

impl AuthDataClass {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Internal => "internal",
            Self::EmployeeRestricted => "employee_restricted",
            Self::PayrollConfidential => "payroll_confidential",
            Self::TenantCritical => "tenant_critical",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub enum AuthWorkflowState {
    Open,
    InputsClosed,
    Calculated,
    ApprovalPending,
    Approved,
    Archived,
}

impl AuthWorkflowState {
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().as_str() {
            "open" => Some(Self::Open),
            "inputs_closed" | "inputs-closed" => Some(Self::InputsClosed),
            "calculated" => Some(Self::Calculated),
            "approval_pending" | "approval-pending" => Some(Self::ApprovalPending),
            "approved" => Some(Self::Approved),
            "archived" => Some(Self::Archived),
            _ => None,
        }
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Open => "open",
            Self::InputsClosed => "inputs_closed",
            Self::Calculated => "calculated",
            Self::ApprovalPending => "approval_pending",
            Self::Approved => "approved",
            Self::Archived => "archived",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub enum AuthzRole {
    PayrollOperator,
    PayrollManager,
    HrOperator,
    HrManager,
    ApprovalSigner,
    ItSecurityAdmin,
    PlatformOwner,
    SupportSre,
}

impl AuthzRole {
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().replace('-', "_").as_str() {
            "payroll_operator" | "payroll_ops" => Some(Self::PayrollOperator),
            "payroll_manager" | "payroll_lead" => Some(Self::PayrollManager),
            "hr_operator" | "hr_ops" => Some(Self::HrOperator),
            "hr_manager" | "people_manager" => Some(Self::HrManager),
            "approval_signer" | "approver" => Some(Self::ApprovalSigner),
            "it_security_admin" | "security_admin" | "tenant_admin" => Some(Self::ItSecurityAdmin),
            "platform_owner" | "product_platform_lead" => Some(Self::PlatformOwner),
            "support_sre" | "customer_support" => Some(Self::SupportSre),
            _ => None,
        }
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::PayrollOperator => "payroll_operator",
            Self::PayrollManager => "payroll_manager",
            Self::HrOperator => "hr_operator",
            Self::HrManager => "hr_manager",
            Self::ApprovalSigner => "approval_signer",
            Self::ItSecurityAdmin => "it_security_admin",
            Self::PlatformOwner => "platform_owner",
            Self::SupportSre => "support_sre",
        }
    }

    pub const fn max_data_class(self) -> AuthDataClass {
        match self {
            Self::SupportSre => AuthDataClass::Internal,
            Self::HrOperator | Self::HrManager => AuthDataClass::EmployeeRestricted,
            Self::PayrollOperator | Self::PayrollManager | Self::ApprovalSigner => {
                AuthDataClass::PayrollConfidential
            }
            Self::ItSecurityAdmin | Self::PlatformOwner => AuthDataClass::TenantCritical,
        }
    }

    pub const fn permits_operation(self, operation: AuthSensitiveOperation) -> bool {
        match self {
            Self::PayrollOperator => matches!(
                operation,
                AuthSensitiveOperation::ReadWorkspace
                    | AuthSensitiveOperation::UserPreferenceUpdate
                    | AuthSensitiveOperation::WorkflowTemplateRead
                    | AuthSensitiveOperation::ArchiveRead
                    | AuthSensitiveOperation::ArchiveUpload
                    | AuthSensitiveOperation::ArchiveReview
                    | AuthSensitiveOperation::PayrollRun
                    | AuthSensitiveOperation::WorkflowStepExecute
                    | AuthSensitiveOperation::PayrollExport
            ),
            Self::PayrollManager => matches!(
                operation,
                AuthSensitiveOperation::ReadWorkspace
                    | AuthSensitiveOperation::UserPreferenceUpdate
                    | AuthSensitiveOperation::WorkflowTemplateRead
                    | AuthSensitiveOperation::ArchiveRead
                    | AuthSensitiveOperation::ArchiveUpload
                    | AuthSensitiveOperation::ArchiveReview
                    | AuthSensitiveOperation::ArchiveAdmit
                    | AuthSensitiveOperation::ArchiveRollback
                    | AuthSensitiveOperation::ArchiveSync
                    | AuthSensitiveOperation::PayrollRun
                    | AuthSensitiveOperation::WorkflowStepExecute
                    | AuthSensitiveOperation::PayrollExport
                    | AuthSensitiveOperation::PayrollPolicyChange
                    | AuthSensitiveOperation::WorkflowTemplateWrite
            ),
            Self::HrOperator => matches!(
                operation,
                AuthSensitiveOperation::ReadWorkspace
                    | AuthSensitiveOperation::UserPreferenceUpdate
                    | AuthSensitiveOperation::WorkflowTemplateRead
                    | AuthSensitiveOperation::HrEmployeeRead
                    | AuthSensitiveOperation::HrEmployeeWrite
                    | AuthSensitiveOperation::ArchiveRead
                    | AuthSensitiveOperation::ArchiveUpload
                    | AuthSensitiveOperation::ArchiveReview
                    | AuthSensitiveOperation::WorkflowStepExecute
            ),
            Self::HrManager => matches!(
                operation,
                AuthSensitiveOperation::ReadWorkspace
                    | AuthSensitiveOperation::UserPreferenceUpdate
                    | AuthSensitiveOperation::WorkflowTemplateRead
                    | AuthSensitiveOperation::HrEmployeeRead
                    | AuthSensitiveOperation::HrEmployeeWrite
                    | AuthSensitiveOperation::ArchiveRead
                    | AuthSensitiveOperation::ArchiveUpload
                    | AuthSensitiveOperation::ArchiveReview
                    | AuthSensitiveOperation::ArchiveAdmit
                    | AuthSensitiveOperation::ArchiveRollback
                    | AuthSensitiveOperation::ArchiveSync
                    | AuthSensitiveOperation::WorkflowStepExecute
            ),
            Self::ApprovalSigner => matches!(
                operation,
                AuthSensitiveOperation::ReadWorkspace
                    | AuthSensitiveOperation::UserPreferenceUpdate
                    | AuthSensitiveOperation::WorkflowTemplateRead
                    | AuthSensitiveOperation::WorkflowStepExecute
                    | AuthSensitiveOperation::ApprovalSigning
            ),
            Self::ItSecurityAdmin => matches!(
                operation,
                AuthSensitiveOperation::ReadWorkspace
                    | AuthSensitiveOperation::UserPreferenceUpdate
                    | AuthSensitiveOperation::WorkflowTemplateRead
                    | AuthSensitiveOperation::WorkflowTemplateWrite
                    | AuthSensitiveOperation::TenantDestructiveChange
            ),
            Self::PlatformOwner => true,
            Self::SupportSre => matches!(
                operation,
                AuthSensitiveOperation::ReadWorkspace
                    | AuthSensitiveOperation::UserPreferenceUpdate
                    | AuthSensitiveOperation::WorkflowTemplateRead
            ),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AuthzRequest<'a> {
    pub policy_id: &'a str,
    pub operation: AuthSensitiveOperation,
    pub current_acr: Option<AuthAcrLevel>,
    pub role: Option<AuthzRole>,
    pub actor_tenant_id: &'a str,
    pub resource_tenant_id: &'a str,
    pub actor_legal_entity: &'a str,
    pub resource_legal_entity: &'a str,
    pub actor_workplace: &'a str,
    pub resource_workplace: &'a str,
    pub workflow_state: AuthWorkflowState,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct AuthzDecision {
    pub schema: &'static str,
    pub policy_id: &'static str,
    pub operation: &'static str,
    pub allowed: bool,
    pub reason: &'static str,
    pub current_acr: Option<&'static str>,
    pub required_acr: &'static str,
    pub role: Option<&'static str>,
    pub required_data_class: &'static str,
    pub workflow_state: &'static str,
    pub controls: [&'static str; 4],
}

pub fn evaluate_authorization(request: &AuthzRequest<'_>) -> AuthzDecision {
    let step_up = evaluate_step_up(request.current_acr, request.operation);
    let role = request.role;
    let required_data_class = request.operation.required_data_class();
    let mut allowed = false;
    let reason = if request.policy_id.trim() != AUTHZ_POLICY_ID {
        "policy_version_untrusted"
    } else if !step_up.allowed {
        step_up.reason
    } else if role.is_none() {
        "role_missing"
    } else if !role.unwrap().permits_operation(request.operation) {
        "rbac_denied"
    } else if !scope_allows(request) {
        "abac_scope_denied"
    } else if role.unwrap().max_data_class() < required_data_class {
        "abac_data_denied"
    } else if !workflow_allows(request.operation, request.workflow_state) {
        "pbac_workflow_denied"
    } else {
        allowed = true;
        "authorized"
    };

    AuthzDecision {
        schema: AUTH_POLICY_SCHEMA,
        policy_id: AUTHZ_POLICY_ID,
        operation: request.operation.id(),
        allowed,
        reason,
        current_acr: request.current_acr.map(AuthAcrLevel::as_str),
        required_acr: step_up.required_acr,
        role: role.map(AuthzRole::as_str),
        required_data_class: required_data_class.as_str(),
        workflow_state: request.workflow_state.as_str(),
        controls: ["pbac", "rbac", "abac", "acr_step_up"],
    }
}

fn scope_allows(request: &AuthzRequest<'_>) -> bool {
    if is_blank(request.actor_tenant_id)
        || is_blank(request.resource_tenant_id)
        || !same_scope(request.actor_tenant_id, request.resource_tenant_id)
        || is_blank(request.actor_legal_entity)
        || is_blank(request.resource_legal_entity)
        || !same_scope(request.actor_legal_entity, request.resource_legal_entity)
    {
        return false;
    }

    if request.operation.requires_workplace_scope() {
        return !is_blank(request.actor_workplace)
            && !is_blank(request.resource_workplace)
            && same_scope(request.actor_workplace, request.resource_workplace);
    }

    true
}

const fn workflow_allows(
    operation: AuthSensitiveOperation,
    workflow_state: AuthWorkflowState,
) -> bool {
    match operation {
        AuthSensitiveOperation::ReadWorkspace
        | AuthSensitiveOperation::HrEmployeeWrite
        | AuthSensitiveOperation::HrEmployeeRead
        | AuthSensitiveOperation::ArchiveRead
        | AuthSensitiveOperation::ArchiveUpload
        | AuthSensitiveOperation::ArchiveReview
        | AuthSensitiveOperation::ArchiveAdmit
        | AuthSensitiveOperation::ArchiveRollback
        | AuthSensitiveOperation::ArchiveSync
        | AuthSensitiveOperation::UserPreferenceUpdate
        | AuthSensitiveOperation::WorkflowTemplateRead
        | AuthSensitiveOperation::WorkflowTemplateWrite
        | AuthSensitiveOperation::PayrollPolicyChange
        | AuthSensitiveOperation::TenantDestructiveChange => true,
        AuthSensitiveOperation::WorkflowStepExecute => matches!(
            workflow_state,
            AuthWorkflowState::Open
                | AuthWorkflowState::InputsClosed
                | AuthWorkflowState::Calculated
                | AuthWorkflowState::ApprovalPending
        ),
        AuthSensitiveOperation::PayrollRun => matches!(
            workflow_state,
            AuthWorkflowState::InputsClosed | AuthWorkflowState::Calculated
        ),
        AuthSensitiveOperation::PayrollExport => matches!(
            workflow_state,
            AuthWorkflowState::Approved | AuthWorkflowState::Archived
        ),
        AuthSensitiveOperation::ApprovalSigning => matches!(
            workflow_state,
            AuthWorkflowState::Calculated | AuthWorkflowState::ApprovalPending
        ),
    }
}

fn same_scope(left: &str, right: &str) -> bool {
    left.trim() == right.trim()
}

fn is_blank(value: &str) -> bool {
    value.trim().is_empty()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request(operation: AuthSensitiveOperation) -> AuthzRequest<'static> {
        AuthzRequest {
            policy_id: AUTHZ_POLICY_ID,
            operation,
            current_acr: Some(operation.required_acr()),
            role: Some(AuthzRole::PayrollManager),
            actor_tenant_id: "tenant-acme",
            resource_tenant_id: "tenant-acme",
            actor_legal_entity: "Acme",
            resource_legal_entity: "Acme",
            actor_workplace: "Seoul",
            resource_workplace: "Seoul",
            workflow_state: AuthWorkflowState::InputsClosed,
        }
    }

    #[test]
    fn parses_only_controlled_acr_levels() {
        assert_eq!(AuthAcrLevel::parse("routine"), Some(AuthAcrLevel::Routine));
        assert_eq!(AuthAcrLevel::parse(" elevated "), Some(AuthAcrLevel::Elevated));
        assert_eq!(AuthAcrLevel::parse("sensitive"), Some(AuthAcrLevel::Sensitive));
        assert_eq!(AuthAcrLevel::parse("critical"), Some(AuthAcrLevel::Critical));
        assert_eq!(AuthAcrLevel::parse("mfa"), None);
        assert_eq!(AuthAcrLevel::parse(""), None);
    }

    #[test]
    fn parses_only_known_sensitive_operations() {
        assert_eq!(
            AuthSensitiveOperation::parse("hr_employee_read"),
            Some(AuthSensitiveOperation::HrEmployeeRead)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("hr_employee_write"),
            Some(AuthSensitiveOperation::HrEmployeeWrite)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("archive_read"),
            Some(AuthSensitiveOperation::ArchiveRead)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("archive_upload"),
            Some(AuthSensitiveOperation::ArchiveUpload)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("archive_review"),
            Some(AuthSensitiveOperation::ArchiveReview)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("archive_admit"),
            Some(AuthSensitiveOperation::ArchiveAdmit)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("archive_rollback"),
            Some(AuthSensitiveOperation::ArchiveRollback)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("archive_sync"),
            Some(AuthSensitiveOperation::ArchiveSync)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("user_preference_update"),
            Some(AuthSensitiveOperation::UserPreferenceUpdate)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("workflow_template_read"),
            Some(AuthSensitiveOperation::WorkflowTemplateRead)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("workflow-template-write"),
            Some(AuthSensitiveOperation::WorkflowTemplateWrite)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("workflow_step_execute"),
            Some(AuthSensitiveOperation::WorkflowStepExecute)
        );
        assert_eq!(
            AuthSensitiveOperation::parse("payroll-export"),
            Some(AuthSensitiveOperation::PayrollExport)
        );
        assert_eq!(AuthSensitiveOperation::parse("admin_override"), None);
        assert_eq!(AuthSensitiveOperation::parse(""), None);
    }

    #[test]
    fn routine_session_can_only_read_workspace() {
        let read = evaluate_step_up(
            Some(AuthAcrLevel::Routine),
            AuthSensitiveOperation::ReadWorkspace,
        );
        let payroll = evaluate_step_up(
            Some(AuthAcrLevel::Routine),
            AuthSensitiveOperation::PayrollRun,
        );

        assert!(read.allowed);
        assert_eq!(read.reason, "acr_sufficient");
        assert!(!payroll.allowed);
        assert_eq!(payroll.required_acr, "sensitive");
        assert_eq!(payroll.reason, "step_up_required");
    }

    #[test]
    fn elevated_session_can_write_hr_but_not_run_payroll() {
        let hr = evaluate_step_up(
            Some(AuthAcrLevel::Elevated),
            AuthSensitiveOperation::HrEmployeeWrite,
        );
        let archive = evaluate_step_up(
            Some(AuthAcrLevel::Elevated),
            AuthSensitiveOperation::ArchiveUpload,
        );
        let payroll = evaluate_step_up(
            Some(AuthAcrLevel::Elevated),
            AuthSensitiveOperation::PayrollRun,
        );

        assert!(hr.allowed);
        assert!(archive.allowed);
        assert!(!payroll.allowed);
        assert_eq!(payroll.required_acr, "sensitive");
    }

    #[test]
    fn sensitive_session_can_run_payroll_export_and_approval_signing() {
        for operation in [
            AuthSensitiveOperation::PayrollRun,
            AuthSensitiveOperation::WorkflowStepExecute,
            AuthSensitiveOperation::PayrollExport,
            AuthSensitiveOperation::PayrollPolicyChange,
            AuthSensitiveOperation::ApprovalSigning,
        ] {
            let decision = evaluate_step_up(Some(AuthAcrLevel::Sensitive), operation);
            assert!(decision.allowed, "operation {} should be allowed", operation.id());
            assert_eq!(decision.current_acr, Some("sensitive"));
        }
    }

    #[test]
    fn critical_tenant_change_requires_critical_acr() {
        let sensitive = evaluate_step_up(
            Some(AuthAcrLevel::Sensitive),
            AuthSensitiveOperation::TenantDestructiveChange,
        );
        let critical = evaluate_step_up(
            Some(AuthAcrLevel::Critical),
            AuthSensitiveOperation::TenantDestructiveChange,
        );

        assert!(!sensitive.allowed);
        assert_eq!(sensitive.required_acr, "critical");
        assert_eq!(sensitive.reason, "step_up_required");
        assert!(critical.allowed);
    }

    #[test]
    fn missing_acr_requires_step_up_without_leaking_claims() {
        let decision = evaluate_step_up(None, AuthSensitiveOperation::PayrollExport);

        assert!(!decision.allowed);
        assert_eq!(decision.schema, AUTH_POLICY_SCHEMA);
        assert_eq!(decision.current_acr, None);
        assert_eq!(decision.reason, "acr_missing");
        assert_eq!(decision.required_acr, "sensitive");
    }

    #[test]
    fn parses_only_known_rbac_roles() {
        assert_eq!(AuthzRole::parse("payroll_operator"), Some(AuthzRole::PayrollOperator));
        assert_eq!(AuthzRole::parse("payroll-manager"), Some(AuthzRole::PayrollManager));
        assert_eq!(AuthzRole::parse("approval_signer"), Some(AuthzRole::ApprovalSigner));
        assert_eq!(AuthzRole::parse("superuser"), None);
        assert_eq!(AuthzRole::parse(""), None);
    }

    #[test]
    fn payroll_operator_can_run_after_rbac_abac_pbac_and_step_up_pass() {
        let mut request = request(AuthSensitiveOperation::PayrollRun);
        request.role = Some(AuthzRole::PayrollOperator);
        request.current_acr = Some(AuthAcrLevel::Sensitive);
        request.workflow_state = AuthWorkflowState::InputsClosed;

        let decision = evaluate_authorization(&request);

        assert!(decision.allowed);
        assert_eq!(decision.reason, "authorized");
        assert_eq!(decision.controls, ["pbac", "rbac", "abac", "acr_step_up"]);
    }

    #[test]
    fn mismatched_tenant_or_workplace_is_abac_denied() {
        let mut tenant_mismatch = request(AuthSensitiveOperation::PayrollRun);
        tenant_mismatch.actor_tenant_id = "tenant-other";
        let mut legal_entity_mismatch = request(AuthSensitiveOperation::PayrollRun);
        legal_entity_mismatch.actor_legal_entity = "OTHER";
        let mut workplace_mismatch = request(AuthSensitiveOperation::PayrollRun);
        workplace_mismatch.actor_workplace = "Busan";

        assert_eq!(
            evaluate_authorization(&tenant_mismatch).reason,
            "abac_scope_denied"
        );
        assert_eq!(
            evaluate_authorization(&legal_entity_mismatch).reason,
            "abac_scope_denied"
        );
        assert_eq!(
            evaluate_authorization(&workplace_mismatch).reason,
            "abac_scope_denied"
        );
    }

    #[test]
    fn role_without_operation_right_is_rbac_denied() {
        let mut request = request(AuthSensitiveOperation::PayrollPolicyChange);
        request.role = Some(AuthzRole::PayrollOperator);

        let decision = evaluate_authorization(&request);

        assert!(!decision.allowed);
        assert_eq!(decision.reason, "rbac_denied");
    }

    #[test]
    fn hr_employee_routes_are_separate_from_payroll_roles() {
        let mut allowed = request(AuthSensitiveOperation::HrEmployeeRead);
        allowed.role = Some(AuthzRole::HrOperator);
        allowed.current_acr = Some(AuthAcrLevel::Elevated);

        let mut denied = allowed.clone();
        denied.role = Some(AuthzRole::PayrollOperator);

        assert!(evaluate_authorization(&allowed).allowed);
        assert_eq!(evaluate_authorization(&denied).reason, "rbac_denied");
    }

    #[test]
    fn archive_routes_are_shared_by_hr_and_payroll_business_roles() {
        for role in [AuthzRole::HrOperator, AuthzRole::PayrollOperator] {
            let mut request = request(AuthSensitiveOperation::ArchiveRead);
            request.role = Some(role);
            request.current_acr = Some(AuthAcrLevel::Elevated);

            assert!(
                evaluate_authorization(&request).allowed,
                "role {} should read archive intake",
                role.as_str()
            );
        }
    }

    #[test]
    fn archive_review_requires_step_up_but_keeps_shared_business_ownership() {
        for role in [AuthzRole::HrOperator, AuthzRole::PayrollOperator] {
            let mut request = request(AuthSensitiveOperation::ArchiveReview);
            request.role = Some(role);
            request.current_acr = Some(AuthAcrLevel::Elevated);
            assert_eq!(
                evaluate_authorization(&request).reason,
                "step_up_required"
            );

            request.current_acr = Some(AuthAcrLevel::Sensitive);
            assert!(
                evaluate_authorization(&request).allowed,
                "role {} should review archive intake issues after step-up",
                role.as_str()
            );
        }
    }

    #[test]
    fn archive_admission_requires_manager_ownership_and_sensitive_step_up() {
        let mut operator = request(AuthSensitiveOperation::ArchiveAdmit);
        operator.role = Some(AuthzRole::HrOperator);
        operator.current_acr = Some(AuthAcrLevel::Sensitive);
        assert_eq!(evaluate_authorization(&operator).reason, "rbac_denied");

        for role in [AuthzRole::HrManager, AuthzRole::PayrollManager] {
            let mut manager = request(AuthSensitiveOperation::ArchiveAdmit);
            manager.role = Some(role);
            manager.current_acr = Some(AuthAcrLevel::Elevated);
            assert_eq!(evaluate_authorization(&manager).reason, "step_up_required");

            manager.current_acr = Some(AuthAcrLevel::Sensitive);
            assert!(
                evaluate_authorization(&manager).allowed,
                "role {} should admit reviewed archive staging rows",
                role.as_str()
            );
        }
    }

    #[test]
    fn archive_rollback_requires_manager_ownership_and_sensitive_step_up() {
        let mut operator = request(AuthSensitiveOperation::ArchiveRollback);
        operator.role = Some(AuthzRole::PayrollOperator);
        operator.current_acr = Some(AuthAcrLevel::Sensitive);
        assert_eq!(evaluate_authorization(&operator).reason, "rbac_denied");

        for role in [AuthzRole::HrManager, AuthzRole::PayrollManager] {
            let mut manager = request(AuthSensitiveOperation::ArchiveRollback);
            manager.role = Some(role);
            manager.current_acr = Some(AuthAcrLevel::Elevated);
            assert_eq!(evaluate_authorization(&manager).reason, "step_up_required");

            manager.current_acr = Some(AuthAcrLevel::Sensitive);
            assert!(
                evaluate_authorization(&manager).allowed,
                "role {} should roll back admitted archive rows",
                role.as_str()
            );
        }
    }

    #[test]
    fn archive_source_sync_requires_manager_ownership_and_sensitive_step_up() {
        let mut operator = request(AuthSensitiveOperation::ArchiveSync);
        operator.role = Some(AuthzRole::PayrollOperator);
        operator.current_acr = Some(AuthAcrLevel::Sensitive);
        assert_eq!(evaluate_authorization(&operator).reason, "rbac_denied");

        for role in [AuthzRole::HrManager, AuthzRole::PayrollManager] {
            let mut manager = request(AuthSensitiveOperation::ArchiveSync);
            manager.role = Some(role);
            manager.current_acr = Some(AuthAcrLevel::Elevated);
            assert_eq!(evaluate_authorization(&manager).reason, "step_up_required");

            manager.current_acr = Some(AuthAcrLevel::Sensitive);
            assert!(
                evaluate_authorization(&manager).allowed,
                "role {} should sync reviewed archive source workbook versions",
                role.as_str()
            );
        }
    }

    #[test]
    fn user_preference_update_is_tenant_scoped_not_workplace_scoped() {
        let mut request = request(AuthSensitiveOperation::UserPreferenceUpdate);
        request.role = Some(AuthzRole::SupportSre);
        request.current_acr = Some(AuthAcrLevel::Routine);
        request.actor_workplace = "";
        request.resource_workplace = "";

        let decision = evaluate_authorization(&request);

        assert!(decision.allowed);
        assert_eq!(decision.reason, "authorized");
        assert_eq!(decision.required_data_class, "internal");
    }

    #[test]
    fn payroll_export_before_approval_is_pbac_denied() {
        let mut request = request(AuthSensitiveOperation::PayrollExport);
        request.current_acr = Some(AuthAcrLevel::Sensitive);
        request.role = Some(AuthzRole::PayrollOperator);
        request.workflow_state = AuthWorkflowState::Calculated;

        let decision = evaluate_authorization(&request);

        assert!(!decision.allowed);
        assert_eq!(decision.reason, "pbac_workflow_denied");
    }

    #[test]
    fn untrusted_policy_version_is_pbac_denied_before_permissions() {
        let mut request = request(AuthSensitiveOperation::PayrollRun);
        request.policy_id = "bitween.authz.legacy";
        request.current_acr = Some(AuthAcrLevel::Sensitive);
        request.role = Some(AuthzRole::PlatformOwner);

        let decision = evaluate_authorization(&request);

        assert!(!decision.allowed);
        assert_eq!(decision.reason, "policy_version_untrusted");
        assert_eq!(decision.policy_id, AUTHZ_POLICY_ID);
    }

    #[test]
    fn tenant_destructive_change_requires_critical_admin_or_owner() {
        let mut denied = request(AuthSensitiveOperation::TenantDestructiveChange);
        denied.role = Some(AuthzRole::PayrollManager);
        denied.current_acr = Some(AuthAcrLevel::Critical);
        denied.actor_workplace = "";
        denied.resource_workplace = "";

        let mut allowed = denied.clone();
        allowed.role = Some(AuthzRole::ItSecurityAdmin);

        assert_eq!(evaluate_authorization(&denied).reason, "rbac_denied");
        assert!(evaluate_authorization(&allowed).allowed);
    }
}
