use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};

pub const AUTH_POLICY_SCHEMA: &str = "bitween.auth-policy.v1";
pub const AUTHZ_POLICY_ID: &str = "bitween.authz.rbac-abac-pbac.v1";

/// Environment variable that overrides the built-in authorization policy with a
/// data-driven JSON document. Unset or blank falls back to [`AuthzPolicy::builtin`].
/// When set but invalid, callers MUST fail closed (deny with `authz_policy_invalid`)
/// rather than silently reverting to the built-in matrix.
pub const AUTHZ_POLICY_ENV: &str = "BITWEEN_AUTHZ_POLICY_JSON";

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

    /// The full closed set of operations. Operations are code touchpoints, so the
    /// enum stays closed while roles become open, data-driven strings.
    pub const ALL: [Self; 18] = [
        Self::ReadWorkspace,
        Self::HrEmployeeRead,
        Self::HrEmployeeWrite,
        Self::ArchiveRead,
        Self::ArchiveUpload,
        Self::ArchiveReview,
        Self::ArchiveAdmit,
        Self::ArchiveRollback,
        Self::ArchiveSync,
        Self::UserPreferenceUpdate,
        Self::WorkflowTemplateRead,
        Self::WorkflowTemplateWrite,
        Self::WorkflowStepExecute,
        Self::PayrollRun,
        Self::PayrollExport,
        Self::PayrollPolicyChange,
        Self::ApprovalSigning,
        Self::TenantDestructiveChange,
    ];

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

    /// The built-in workflow states in which this operation is permitted, or
    /// `None` when the operation is permitted in every state. This is the source
    /// of truth for the built-in PBAC gates.
    fn builtin_allowed_workflow_states(self) -> Option<BTreeSet<String>> {
        match self {
            Self::ReadWorkspace
            | Self::HrEmployeeWrite
            | Self::HrEmployeeRead
            | Self::ArchiveRead
            | Self::ArchiveUpload
            | Self::ArchiveReview
            | Self::ArchiveAdmit
            | Self::ArchiveRollback
            | Self::ArchiveSync
            | Self::UserPreferenceUpdate
            | Self::WorkflowTemplateRead
            | Self::TenantDestructiveChange => None,
            // Policy and template changes are frozen while a payroll cycle is in
            // flight: edits after inputs close would invalidate what the approver
            // reviews, so they reopen only once the run is approved or archived.
            Self::WorkflowTemplateWrite | Self::PayrollPolicyChange => Some(workflow_state_set(&[
                AuthWorkflowState::Open,
                AuthWorkflowState::Approved,
                AuthWorkflowState::Archived,
            ])),
            Self::WorkflowStepExecute => Some(workflow_state_set(&[
                AuthWorkflowState::Open,
                AuthWorkflowState::InputsClosed,
                AuthWorkflowState::Calculated,
                AuthWorkflowState::ApprovalPending,
            ])),
            Self::PayrollRun => Some(workflow_state_set(&[
                AuthWorkflowState::InputsClosed,
                AuthWorkflowState::Calculated,
            ])),
            Self::PayrollExport => Some(workflow_state_set(&[
                AuthWorkflowState::Approved,
                AuthWorkflowState::Archived,
            ])),
            Self::ApprovalSigning => Some(workflow_state_set(&[
                AuthWorkflowState::Calculated,
                AuthWorkflowState::ApprovalPending,
            ])),
        }
    }
}

fn workflow_state_set(states: &[AuthWorkflowState]) -> BTreeSet<String> {
    states.iter().map(|state| state.as_str().to_owned()).collect()
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
    policy: &AuthzPolicy,
    current_acr: Option<AuthAcrLevel>,
    operation: AuthSensitiveOperation,
) -> AuthStepUpDecision {
    let required = policy.required_acr(operation);
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
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().replace('-', "_").as_str() {
            "internal" => Some(Self::Internal),
            "employee_restricted" => Some(Self::EmployeeRestricted),
            "payroll_confidential" => Some(Self::PayrollConfidential),
            "tenant_critical" => Some(Self::TenantCritical),
            _ => None,
        }
    }

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
    /// The deployment workflow flags do not form a clean prefix chain (e.g. an
    /// advanced flag is set without the states that must precede it). This is a
    /// fail-closed sentinel: it is denied for every operation that declares an
    /// explicit workflow window and is never accepted by [`Self::parse`], so no
    /// custom policy can open a window on it. Operations with no window (`None`)
    /// stay allowed, which is the intended asymmetry.
    Inconsistent,
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
            // "inconsistent" is intentionally not parseable: a custom policy must
            // never be able to declare a window that opens on the fail-closed
            // sentinel state.
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
            Self::Inconsistent => "inconsistent",
        }
    }
}

/// Normalizes a raw role string the same way the legacy `AuthzRole::parse`
/// alias table did: trim, lowercase, '-' to '_', then fold known aliases onto
/// their canonical role id. The result is the key used for role-policy lookup.
pub fn normalize_role(value: &str) -> String {
    let normalized = value.trim().to_ascii_lowercase().replace('-', "_");
    match normalized.as_str() {
        "payroll_operator" | "payroll_ops" => "payroll_operator",
        "payroll_manager" | "payroll_lead" => "payroll_manager",
        "hr_operator" | "hr_ops" => "hr_operator",
        "hr_manager" | "people_manager" => "hr_manager",
        "approval_signer" | "approver" => "approval_signer",
        "it_security_admin" | "security_admin" | "tenant_admin" => "it_security_admin",
        "platform_owner" | "product_platform_lead" => "platform_owner",
        "support_sre" | "customer_support" => "support_sre",
        other => other,
    }
    .to_owned()
}

/// A role entry in the data-driven policy: a data-class ceiling plus the set of
/// operation ids the role may exercise. The grant `"*"` permits every operation.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct RolePolicy {
    pub max_data_class: AuthDataClass,
    pub grants: BTreeSet<String>,
}

impl RolePolicy {
    fn permits(&self, operation: AuthSensitiveOperation) -> bool {
        self.grants.contains("*") || self.grants.contains(operation.id())
    }
}

/// An operation entry in the data-driven policy. `allowed_workflow_states`
/// of `None` means the operation is permitted in every workflow state.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct OperationPolicy {
    pub required_acr: AuthAcrLevel,
    pub required_data_class: AuthDataClass,
    pub requires_workplace_scope: bool,
    pub allowed_workflow_states: Option<BTreeSet<String>>,
}

impl OperationPolicy {
    fn workflow_allows(&self, workflow_state: AuthWorkflowState) -> bool {
        match &self.allowed_workflow_states {
            None => true,
            Some(states) => states.contains(workflow_state.as_str()),
        }
    }
}

/// The data-driven authorization policy. Built-in by default; overridable via
/// the `BITWEEN_AUTHZ_POLICY_JSON` environment variable.
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct AuthzPolicy {
    pub policy_id: String,
    pub roles: BTreeMap<String, RolePolicy>,
    pub operations: BTreeMap<String, OperationPolicy>,
}

impl AuthzPolicy {
    /// Reproduces the current on-disk matrix exactly, built from the existing
    /// enum const fns so there is one source of truth. Role aliases are folded
    /// into the canonical role map keys.
    pub fn builtin() -> Self {
        let mut operations = BTreeMap::new();
        for operation in AuthSensitiveOperation::ALL {
            operations.insert(
                operation.id().to_owned(),
                OperationPolicy {
                    required_acr: operation.required_acr(),
                    required_data_class: operation.required_data_class(),
                    requires_workplace_scope: operation.requires_workplace_scope(),
                    allowed_workflow_states: operation.builtin_allowed_workflow_states(),
                },
            );
        }

        let mut roles = BTreeMap::new();
        for (role_id, max_data_class, grants) in builtin_role_matrix() {
            roles.insert(
                role_id.to_owned(),
                RolePolicy {
                    max_data_class,
                    grants: grants.iter().map(|grant| (*grant).to_owned()).collect(),
                },
            );
        }

        Self {
            policy_id: AUTHZ_POLICY_ID.to_owned(),
            roles,
            operations,
        }
    }

    /// Loads the policy from `BITWEEN_AUTHZ_POLICY_JSON`. Unset or blank returns
    /// the built-in policy. When set, the JSON is parsed and validated; any error
    /// returns `Err` so callers fail closed (they must never fall back to the
    /// built-in policy when the variable is set but invalid).
    pub fn from_env() -> Result<Self, AuthzPolicyError> {
        Self::from_env_var(std::env::var(AUTHZ_POLICY_ENV))
    }

    /// Pure decision over the raw `BITWEEN_AUTHZ_POLICY_JSON` lookup result so
    /// the fail-closed contract is unit-testable without mutating process env:
    /// - `Ok(non-blank)` parses the JSON document,
    /// - `Ok(blank)` or `Err(NotPresent)` returns the built-in policy,
    /// - `Err(NotUnicode)` is a configured-but-unreadable value and MUST fail
    ///   closed (the documented contract forbids silently reverting to builtin).
    fn from_env_var(raw: Result<String, std::env::VarError>) -> Result<Self, AuthzPolicyError> {
        match raw {
            Ok(raw) if !raw.trim().is_empty() => Self::from_json(&raw),
            Ok(_) => Ok(Self::builtin()),
            Err(std::env::VarError::NotPresent) => Ok(Self::builtin()),
            Err(std::env::VarError::NotUnicode(_)) => Err(AuthzPolicyError::new(
                "BITWEEN_AUTHZ_POLICY_JSON is set to a non-unicode value and cannot be read",
            )),
        }
    }

    /// Parses and validates a JSON policy document.
    pub fn from_json(raw: &str) -> Result<Self, AuthzPolicyError> {
        let value: serde_json::Value =
            serde_json::from_str(raw).map_err(|error| AuthzPolicyError::new(error.to_string()))?;
        Self::from_value(&value)
    }

    fn from_value(value: &serde_json::Value) -> Result<Self, AuthzPolicyError> {
        let object = value
            .as_object()
            .ok_or_else(|| AuthzPolicyError::new("policy document must be a JSON object"))?;

        let policy_id = object
            .get("policy_id")
            .and_then(|value| value.as_str())
            .unwrap_or_default()
            .trim()
            .to_owned();
        if policy_id.is_empty() {
            return Err(AuthzPolicyError::new("policy_id must be a non-empty string"));
        }

        let operations = parse_operations(object.get("operations"))?;
        let roles = parse_roles(object.get("roles"), &operations)?;

        Ok(Self {
            policy_id,
            roles,
            operations,
        })
    }

    fn role(&self, role_key: &str) -> Option<&RolePolicy> {
        self.roles.get(role_key)
    }

    fn operation(&self, operation: AuthSensitiveOperation) -> Option<&OperationPolicy> {
        self.operations.get(operation.id())
    }

    fn required_acr(&self, operation: AuthSensitiveOperation) -> AuthAcrLevel {
        self.operation(operation)
            .map(|entry| entry.required_acr)
            .unwrap_or_else(|| operation.required_acr())
    }

    fn required_data_class(&self, operation: AuthSensitiveOperation) -> AuthDataClass {
        self.operation(operation)
            .map(|entry| entry.required_data_class)
            .unwrap_or_else(|| operation.required_data_class())
    }
}

fn builtin_role_matrix() -> Vec<(&'static str, AuthDataClass, Vec<&'static str>)> {
    use AuthSensitiveOperation as Op;

    let all_ids: Vec<&'static str> = vec!["*"];
    let business_read = [
        Op::ReadWorkspace.id(),
        Op::UserPreferenceUpdate.id(),
        Op::WorkflowTemplateRead.id(),
    ];

    vec![
        (
            "payroll_operator",
            AuthDataClass::PayrollConfidential,
            [
                business_read.as_slice(),
                &[
                    Op::ArchiveRead.id(),
                    Op::ArchiveUpload.id(),
                    Op::ArchiveReview.id(),
                    Op::PayrollRun.id(),
                    Op::WorkflowStepExecute.id(),
                    Op::PayrollExport.id(),
                ],
            ]
            .concat(),
        ),
        (
            "payroll_manager",
            AuthDataClass::PayrollConfidential,
            [
                business_read.as_slice(),
                &[
                    Op::ArchiveRead.id(),
                    Op::ArchiveUpload.id(),
                    Op::ArchiveReview.id(),
                    Op::ArchiveAdmit.id(),
                    Op::ArchiveRollback.id(),
                    Op::ArchiveSync.id(),
                    Op::PayrollRun.id(),
                    Op::WorkflowStepExecute.id(),
                    Op::PayrollExport.id(),
                    Op::PayrollPolicyChange.id(),
                    Op::WorkflowTemplateWrite.id(),
                ],
            ]
            .concat(),
        ),
        (
            // WorkflowStepExecute is intentionally absent from the HR roles: it is
            // classified payroll_confidential, above their employee_restricted
            // data-class ceiling, so a grant here could never be exercised.
            "hr_operator",
            AuthDataClass::EmployeeRestricted,
            [
                business_read.as_slice(),
                &[
                    Op::HrEmployeeRead.id(),
                    Op::HrEmployeeWrite.id(),
                    Op::ArchiveRead.id(),
                    Op::ArchiveUpload.id(),
                    Op::ArchiveReview.id(),
                ],
            ]
            .concat(),
        ),
        (
            "hr_manager",
            AuthDataClass::EmployeeRestricted,
            [
                business_read.as_slice(),
                &[
                    Op::HrEmployeeRead.id(),
                    Op::HrEmployeeWrite.id(),
                    Op::ArchiveRead.id(),
                    Op::ArchiveUpload.id(),
                    Op::ArchiveReview.id(),
                    Op::ArchiveAdmit.id(),
                    Op::ArchiveRollback.id(),
                    Op::ArchiveSync.id(),
                ],
            ]
            .concat(),
        ),
        (
            "approval_signer",
            AuthDataClass::PayrollConfidential,
            [
                business_read.as_slice(),
                &[Op::WorkflowStepExecute.id(), Op::ApprovalSigning.id()],
            ]
            .concat(),
        ),
        (
            "it_security_admin",
            AuthDataClass::TenantCritical,
            [
                business_read.as_slice(),
                &[
                    Op::WorkflowTemplateWrite.id(),
                    Op::TenantDestructiveChange.id(),
                ],
            ]
            .concat(),
        ),
        ("platform_owner", AuthDataClass::TenantCritical, all_ids),
        (
            "support_sre",
            AuthDataClass::Internal,
            business_read.to_vec(),
        ),
    ]
}

fn parse_operations(
    value: Option<&serde_json::Value>,
) -> Result<BTreeMap<String, OperationPolicy>, AuthzPolicyError> {
    let object = value
        .and_then(|value| value.as_object())
        .ok_or_else(|| AuthzPolicyError::new("operations must be a JSON object"))?;

    let mut operations = BTreeMap::new();
    for (operation_id, entry) in object {
        let operation = AuthSensitiveOperation::parse(operation_id)
            .ok_or_else(|| AuthzPolicyError::new(format!("unknown operation id: {operation_id}")))?;
        // Same fail-open footgun as duplicate role keys: parse() folds case,
        // whitespace, and '-'/'_' variants onto one canonical operation, so two
        // colliding keys would silently overwrite and a looser window could
        // swallow a tighter one. Reject the collision and fail closed.
        if operations.contains_key(operation.id()) {
            return Err(AuthzPolicyError::new(format!(
                "operation {operation_id} normalizes to {}, which is already defined by another operation key (duplicate operation)",
                operation.id()
            )));
        }
        let entry = entry
            .as_object()
            .ok_or_else(|| AuthzPolicyError::new(format!("operation {operation_id} must be an object")))?;

        let required_acr = entry
            .get("required_acr")
            .and_then(|value| value.as_str())
            .and_then(AuthAcrLevel::parse)
            .ok_or_else(|| {
                AuthzPolicyError::new(format!("operation {operation_id} has unknown required_acr"))
            })?;
        let required_data_class = entry
            .get("required_data_class")
            .and_then(|value| value.as_str())
            .and_then(AuthDataClass::parse)
            .ok_or_else(|| {
                AuthzPolicyError::new(format!(
                    "operation {operation_id} has unknown required_data_class"
                ))
            })?;
        let requires_workplace_scope = entry
            .get("requires_workplace_scope")
            .and_then(|value| value.as_bool())
            .ok_or_else(|| {
                AuthzPolicyError::new(format!(
                    "operation {operation_id} must set requires_workplace_scope"
                ))
            })?;
        let allowed_workflow_states = match entry.get("allowed_workflow_states") {
            None | Some(serde_json::Value::Null) => None,
            Some(serde_json::Value::Array(states)) => {
                let mut set = BTreeSet::new();
                for state in states {
                    let state = state.as_str().and_then(AuthWorkflowState::parse).ok_or_else(|| {
                        AuthzPolicyError::new(format!(
                            "operation {operation_id} has unknown workflow state"
                        ))
                    })?;
                    set.insert(state.as_str().to_owned());
                }
                Some(set)
            }
            Some(_) => {
                return Err(AuthzPolicyError::new(format!(
                    "operation {operation_id} allowed_workflow_states must be an array or null"
                )));
            }
        };

        operations.insert(
            operation.id().to_owned(),
            OperationPolicy {
                required_acr,
                required_data_class,
                requires_workplace_scope,
                allowed_workflow_states,
            },
        );
    }

    Ok(operations)
}

fn parse_roles(
    value: Option<&serde_json::Value>,
    operations: &BTreeMap<String, OperationPolicy>,
) -> Result<BTreeMap<String, RolePolicy>, AuthzPolicyError> {
    let object = value
        .and_then(|value| value.as_object())
        .ok_or_else(|| AuthzPolicyError::new("roles must be a JSON object"))?;
    if object.is_empty() {
        return Err(AuthzPolicyError::new("roles must not be empty"));
    }

    let mut roles = BTreeMap::new();
    for (role_id, entry) in object {
        let entry = entry
            .as_object()
            .ok_or_else(|| AuthzPolicyError::new(format!("role {role_id} must be an object")))?;

        let max_data_class = entry
            .get("max_data_class")
            .and_then(|value| value.as_str())
            .and_then(AuthDataClass::parse)
            .ok_or_else(|| {
                AuthzPolicyError::new(format!("role {role_id} has unknown max_data_class"))
            })?;

        let grant_values = entry
            .get("grants")
            .and_then(|value| value.as_array())
            .ok_or_else(|| AuthzPolicyError::new(format!("role {role_id} must list grants")))?;

        let mut grants = BTreeSet::new();
        for grant in grant_values {
            let grant = grant
                .as_str()
                .ok_or_else(|| AuthzPolicyError::new(format!("role {role_id} grant must be a string")))?
                .trim()
                .to_owned();
            if grant == "*" {
                // A wildcard grant can exercise every operation, so its ceiling
                // must clear the maximum required_data_class across ALL
                // operations (custom override where present, builtin otherwise).
                // Otherwise the wildcard would carry permanently dead grants.
                let max_required = AuthSensitiveOperation::ALL
                    .into_iter()
                    .map(|operation| {
                        operations
                            .get(operation.id())
                            .map(|entry| entry.required_data_class)
                            .unwrap_or_else(|| operation.required_data_class())
                    })
                    .max()
                    .unwrap_or(AuthDataClass::Internal);
                if max_data_class < max_required {
                    return Err(AuthzPolicyError::new(format!(
                        "role {role_id} grants \"*\" but its data-class ceiling is below the maximum operation requirement (dead grant)"
                    )));
                }
                grants.insert(grant);
                continue;
            }
            let operation = AuthSensitiveOperation::parse(&grant).ok_or_else(|| {
                AuthzPolicyError::new(format!("role {role_id} grants unknown operation: {grant}"))
            })?;
            // Dead grants are configuration errors: a grant the ceiling can never
            // exercise mirrors the every_rbac_grant_is_reachable invariant.
            let required = operations
                .get(operation.id())
                .map(|entry| entry.required_data_class)
                .unwrap_or_else(|| operation.required_data_class());
            if max_data_class < required {
                return Err(AuthzPolicyError::new(format!(
                    "role {role_id} is granted {} but its data-class ceiling is below the operation requirement (dead grant)",
                    operation.id()
                )));
            }
            grants.insert(operation.id().to_owned());
        }

        // Two JSON keys that normalize to the same canonical role id (e.g.
        // "it_security_admin" and "tenant_admin") must not silently overwrite
        // each other: a privileged definition replacing a restricted one would
        // be a fail-open footgun. Reject the collision and fail closed.
        let canonical = normalize_role(role_id);
        if roles.contains_key(&canonical) {
            return Err(AuthzPolicyError::new(format!(
                "role {role_id} normalizes to {canonical}, which is already defined by another role key (duplicate role)"
            )));
        }
        roles.insert(canonical, RolePolicy { max_data_class, grants });
    }

    Ok(roles)
}

/// A load-time policy validation error. Callers translate this into the
/// `authz_policy_invalid` deny reason.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AuthzPolicyError {
    message: String,
}

impl AuthzPolicyError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }

    pub fn message(&self) -> &str {
        &self.message
    }
}

impl std::fmt::Display for AuthzPolicyError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "authz_policy_invalid: {}", self.message)
    }
}

impl std::error::Error for AuthzPolicyError {}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AuthzRequest<'a> {
    pub policy_id: &'a str,
    pub operation: AuthSensitiveOperation,
    pub current_acr: Option<AuthAcrLevel>,
    pub role: Option<&'a str>,
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
    pub policy_id: String,
    pub operation: &'static str,
    pub allowed: bool,
    pub reason: &'static str,
    pub current_acr: Option<&'static str>,
    pub required_acr: &'static str,
    pub role: Option<String>,
    pub required_data_class: &'static str,
    pub workflow_state: &'static str,
    pub controls: [&'static str; 4],
}

impl AuthzDecision {
    /// Builds the fail-closed decision used when the configured policy document
    /// is invalid. Callers that load the policy from the environment translate a
    /// load error into this denial instead of falling back to the built-in
    /// policy, per the `BITWEEN_AUTHZ_POLICY_JSON` contract.
    pub fn policy_invalid(operation: AuthSensitiveOperation) -> Self {
        Self {
            schema: AUTH_POLICY_SCHEMA,
            policy_id: String::new(),
            operation: operation.id(),
            allowed: false,
            reason: "authz_policy_invalid",
            current_acr: None,
            required_acr: operation.required_acr().as_str(),
            role: None,
            required_data_class: operation.required_data_class().as_str(),
            workflow_state: AuthWorkflowState::Inconsistent.as_str(),
            controls: ["pbac", "rbac", "abac", "acr_step_up"],
        }
    }
}

pub fn evaluate_authorization(policy: &AuthzPolicy, request: &AuthzRequest<'_>) -> AuthzDecision {
    let step_up = evaluate_step_up(policy, request.current_acr, request.operation);
    let required_data_class = policy.required_data_class(request.operation);
    let normalized_role = request
        .role
        .map(str::trim)
        .filter(|role| !role.is_empty())
        .map(normalize_role);
    let role_entry = normalized_role
        .as_deref()
        .and_then(|role_key| policy.role(role_key));

    let mut allowed = false;
    let reason = if request.policy_id.trim() != policy.policy_id {
        "policy_version_untrusted"
    } else if !step_up.allowed {
        step_up.reason
    } else if normalized_role.is_none() {
        "role_missing"
    } else if role_entry.is_none_or(|entry| !entry.permits(request.operation)) {
        "rbac_denied"
    } else if !scope_allows(policy, request) {
        "abac_scope_denied"
    } else if role_entry.unwrap().max_data_class < required_data_class {
        "abac_data_denied"
    } else if !workflow_allows(policy, request.operation, request.workflow_state) {
        "pbac_workflow_denied"
    } else {
        allowed = true;
        "authorized"
    };

    // Only echo the role when it resolves to a real policy entry. Unknown
    // (non-blank) roles still deny with `rbac_denied`, but echoing the raw
    // caller-supplied string back would reflect arbitrary input into the
    // decision; surface `None` instead.
    let decision_role = role_entry.is_some().then(|| normalized_role.clone()).flatten();

    AuthzDecision {
        schema: AUTH_POLICY_SCHEMA,
        policy_id: policy.policy_id.clone(),
        operation: request.operation.id(),
        allowed,
        reason,
        current_acr: request.current_acr.map(AuthAcrLevel::as_str),
        required_acr: step_up.required_acr,
        role: decision_role,
        required_data_class: required_data_class.as_str(),
        workflow_state: request.workflow_state.as_str(),
        controls: ["pbac", "rbac", "abac", "acr_step_up"],
    }
}

fn scope_allows(policy: &AuthzPolicy, request: &AuthzRequest<'_>) -> bool {
    if is_blank(request.actor_tenant_id)
        || is_blank(request.resource_tenant_id)
        || !same_scope(request.actor_tenant_id, request.resource_tenant_id)
        || is_blank(request.actor_legal_entity)
        || is_blank(request.resource_legal_entity)
        || !same_scope(request.actor_legal_entity, request.resource_legal_entity)
    {
        return false;
    }

    if requires_workplace_scope(policy, request.operation) {
        return !is_blank(request.actor_workplace)
            && !is_blank(request.resource_workplace)
            && same_scope(request.actor_workplace, request.resource_workplace);
    }

    true
}

fn requires_workplace_scope(policy: &AuthzPolicy, operation: AuthSensitiveOperation) -> bool {
    policy
        .operation(operation)
        .map(|entry| entry.requires_workplace_scope)
        .unwrap_or_else(|| operation.requires_workplace_scope())
}

fn workflow_allows(
    policy: &AuthzPolicy,
    operation: AuthSensitiveOperation,
    workflow_state: AuthWorkflowState,
) -> bool {
    // A custom policy that omits an operation from its `operations` map falls
    // back to the builtin workflow window exactly like required_acr,
    // required_data_class, and requires_workplace_scope do, so the PBAC gate
    // fails closed rather than silently opening "all states allowed".
    match policy.operation(operation) {
        Some(entry) => entry.workflow_allows(workflow_state),
        None => match operation.builtin_allowed_workflow_states() {
            Some(states) => states.contains(workflow_state.as_str()),
            None => true,
        },
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

    fn builtin() -> AuthzPolicy {
        AuthzPolicy::builtin()
    }

    fn request(operation: AuthSensitiveOperation) -> AuthzRequest<'static> {
        AuthzRequest {
            policy_id: AUTHZ_POLICY_ID,
            operation,
            current_acr: Some(operation.required_acr()),
            role: Some("payroll_manager"),
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
        let policy = builtin();
        let read = evaluate_step_up(
            &policy,
            Some(AuthAcrLevel::Routine),
            AuthSensitiveOperation::ReadWorkspace,
        );
        let payroll = evaluate_step_up(
            &policy,
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
        let policy = builtin();
        let hr = evaluate_step_up(
            &policy,
            Some(AuthAcrLevel::Elevated),
            AuthSensitiveOperation::HrEmployeeWrite,
        );
        let archive = evaluate_step_up(
            &policy,
            Some(AuthAcrLevel::Elevated),
            AuthSensitiveOperation::ArchiveUpload,
        );
        let payroll = evaluate_step_up(
            &policy,
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
        let policy = builtin();
        for operation in [
            AuthSensitiveOperation::PayrollRun,
            AuthSensitiveOperation::WorkflowStepExecute,
            AuthSensitiveOperation::PayrollExport,
            AuthSensitiveOperation::PayrollPolicyChange,
            AuthSensitiveOperation::ApprovalSigning,
        ] {
            let decision = evaluate_step_up(&policy, Some(AuthAcrLevel::Sensitive), operation);
            assert!(decision.allowed, "operation {} should be allowed", operation.id());
            assert_eq!(decision.current_acr, Some("sensitive"));
        }
    }

    #[test]
    fn critical_tenant_change_requires_critical_acr() {
        let policy = builtin();
        let sensitive = evaluate_step_up(
            &policy,
            Some(AuthAcrLevel::Sensitive),
            AuthSensitiveOperation::TenantDestructiveChange,
        );
        let critical = evaluate_step_up(
            &policy,
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
        let policy = builtin();
        let decision = evaluate_step_up(&policy, None, AuthSensitiveOperation::PayrollExport);

        assert!(!decision.allowed);
        assert_eq!(decision.schema, AUTH_POLICY_SCHEMA);
        assert_eq!(decision.current_acr, None);
        assert_eq!(decision.reason, "acr_missing");
        assert_eq!(decision.required_acr, "sensitive");
    }

    #[test]
    fn parses_and_normalizes_role_aliases() {
        assert_eq!(normalize_role("payroll_operator"), "payroll_operator");
        assert_eq!(normalize_role("payroll-ops"), "payroll_operator");
        assert_eq!(normalize_role("approver"), "approval_signer");
        assert_eq!(normalize_role("tenant_admin"), "it_security_admin");
        // Unknown roles normalize to their canonical string form.
        assert_eq!(normalize_role("superuser"), "superuser");
        // Unknown roles are simply absent from the built-in role map.
        let policy = builtin();
        assert!(policy.role("superuser").is_none());
        assert!(policy.role("payroll_operator").is_some());
    }

    #[test]
    fn payroll_operator_can_run_after_rbac_abac_pbac_and_step_up_pass() {
        let policy = builtin();
        let mut request = request(AuthSensitiveOperation::PayrollRun);
        request.role = Some("payroll_operator");
        request.current_acr = Some(AuthAcrLevel::Sensitive);
        request.workflow_state = AuthWorkflowState::InputsClosed;

        let decision = evaluate_authorization(&policy, &request);

        assert!(decision.allowed);
        assert_eq!(decision.reason, "authorized");
        assert_eq!(decision.controls, ["pbac", "rbac", "abac", "acr_step_up"]);
    }

    #[test]
    fn mismatched_tenant_or_workplace_is_abac_denied() {
        let policy = builtin();
        let mut tenant_mismatch = request(AuthSensitiveOperation::PayrollRun);
        tenant_mismatch.actor_tenant_id = "tenant-other";
        let mut legal_entity_mismatch = request(AuthSensitiveOperation::PayrollRun);
        legal_entity_mismatch.actor_legal_entity = "OTHER";
        let mut workplace_mismatch = request(AuthSensitiveOperation::PayrollRun);
        workplace_mismatch.actor_workplace = "Busan";

        assert_eq!(
            evaluate_authorization(&policy, &tenant_mismatch).reason,
            "abac_scope_denied"
        );
        assert_eq!(
            evaluate_authorization(&policy, &legal_entity_mismatch).reason,
            "abac_scope_denied"
        );
        assert_eq!(
            evaluate_authorization(&policy, &workplace_mismatch).reason,
            "abac_scope_denied"
        );
    }

    #[test]
    fn role_without_operation_right_is_rbac_denied() {
        let policy = builtin();
        let mut request = request(AuthSensitiveOperation::PayrollPolicyChange);
        request.role = Some("payroll_operator");

        let decision = evaluate_authorization(&policy, &request);

        assert!(!decision.allowed);
        assert_eq!(decision.reason, "rbac_denied");
    }

    #[test]
    fn unknown_role_is_rbac_denied_but_blank_role_is_role_missing() {
        let policy = builtin();
        let mut unknown = request(AuthSensitiveOperation::PayrollRun);
        unknown.role = Some("superuser");
        unknown.current_acr = Some(AuthAcrLevel::Sensitive);
        assert_eq!(evaluate_authorization(&policy, &unknown).reason, "rbac_denied");

        let mut blank = request(AuthSensitiveOperation::PayrollRun);
        blank.role = Some("   ");
        blank.current_acr = Some(AuthAcrLevel::Sensitive);
        assert_eq!(evaluate_authorization(&policy, &blank).reason, "role_missing");

        let mut absent = request(AuthSensitiveOperation::PayrollRun);
        absent.role = None;
        absent.current_acr = Some(AuthAcrLevel::Sensitive);
        assert_eq!(evaluate_authorization(&policy, &absent).reason, "role_missing");
    }

    #[test]
    fn hr_employee_routes_are_separate_from_payroll_roles() {
        let policy = builtin();
        let mut allowed = request(AuthSensitiveOperation::HrEmployeeRead);
        allowed.role = Some("hr_operator");
        allowed.current_acr = Some(AuthAcrLevel::Elevated);

        let mut denied = allowed.clone();
        denied.role = Some("payroll_operator");

        assert!(evaluate_authorization(&policy, &allowed).allowed);
        assert_eq!(evaluate_authorization(&policy, &denied).reason, "rbac_denied");
    }

    #[test]
    fn archive_routes_are_shared_by_hr_and_payroll_business_roles() {
        let policy = builtin();
        for role in ["hr_operator", "payroll_operator"] {
            let mut request = request(AuthSensitiveOperation::ArchiveRead);
            request.role = Some(role);
            request.current_acr = Some(AuthAcrLevel::Elevated);

            assert!(
                evaluate_authorization(&policy, &request).allowed,
                "role {role} should read archive intake"
            );
        }
    }

    #[test]
    fn archive_review_requires_step_up_but_keeps_shared_business_ownership() {
        let policy = builtin();
        for role in ["hr_operator", "payroll_operator"] {
            let mut request = request(AuthSensitiveOperation::ArchiveReview);
            request.role = Some(role);
            request.current_acr = Some(AuthAcrLevel::Elevated);
            assert_eq!(
                evaluate_authorization(&policy, &request).reason,
                "step_up_required"
            );

            request.current_acr = Some(AuthAcrLevel::Sensitive);
            assert!(
                evaluate_authorization(&policy, &request).allowed,
                "role {role} should review archive intake issues after step-up"
            );
        }
    }

    #[test]
    fn archive_admission_requires_manager_ownership_and_sensitive_step_up() {
        let policy = builtin();
        let mut operator = request(AuthSensitiveOperation::ArchiveAdmit);
        operator.role = Some("hr_operator");
        operator.current_acr = Some(AuthAcrLevel::Sensitive);
        assert_eq!(evaluate_authorization(&policy, &operator).reason, "rbac_denied");

        for role in ["hr_manager", "payroll_manager"] {
            let mut manager = request(AuthSensitiveOperation::ArchiveAdmit);
            manager.role = Some(role);
            manager.current_acr = Some(AuthAcrLevel::Elevated);
            assert_eq!(evaluate_authorization(&policy, &manager).reason, "step_up_required");

            manager.current_acr = Some(AuthAcrLevel::Sensitive);
            assert!(
                evaluate_authorization(&policy, &manager).allowed,
                "role {role} should admit reviewed archive staging rows"
            );
        }
    }

    #[test]
    fn archive_rollback_requires_manager_ownership_and_sensitive_step_up() {
        let policy = builtin();
        let mut operator = request(AuthSensitiveOperation::ArchiveRollback);
        operator.role = Some("payroll_operator");
        operator.current_acr = Some(AuthAcrLevel::Sensitive);
        assert_eq!(evaluate_authorization(&policy, &operator).reason, "rbac_denied");

        for role in ["hr_manager", "payroll_manager"] {
            let mut manager = request(AuthSensitiveOperation::ArchiveRollback);
            manager.role = Some(role);
            manager.current_acr = Some(AuthAcrLevel::Elevated);
            assert_eq!(evaluate_authorization(&policy, &manager).reason, "step_up_required");

            manager.current_acr = Some(AuthAcrLevel::Sensitive);
            assert!(
                evaluate_authorization(&policy, &manager).allowed,
                "role {role} should roll back admitted archive rows"
            );
        }
    }

    #[test]
    fn archive_source_sync_requires_manager_ownership_and_sensitive_step_up() {
        let policy = builtin();
        let mut operator = request(AuthSensitiveOperation::ArchiveSync);
        operator.role = Some("payroll_operator");
        operator.current_acr = Some(AuthAcrLevel::Sensitive);
        assert_eq!(evaluate_authorization(&policy, &operator).reason, "rbac_denied");

        for role in ["hr_manager", "payroll_manager"] {
            let mut manager = request(AuthSensitiveOperation::ArchiveSync);
            manager.role = Some(role);
            manager.current_acr = Some(AuthAcrLevel::Elevated);
            assert_eq!(evaluate_authorization(&policy, &manager).reason, "step_up_required");

            manager.current_acr = Some(AuthAcrLevel::Sensitive);
            assert!(
                evaluate_authorization(&policy, &manager).allowed,
                "role {role} should sync reviewed archive source workbook versions"
            );
        }
    }

    #[test]
    fn user_preference_update_is_tenant_scoped_not_workplace_scoped() {
        let policy = builtin();
        let mut request = request(AuthSensitiveOperation::UserPreferenceUpdate);
        request.role = Some("support_sre");
        request.current_acr = Some(AuthAcrLevel::Routine);
        request.actor_workplace = "";
        request.resource_workplace = "";

        let decision = evaluate_authorization(&policy, &request);

        assert!(decision.allowed);
        assert_eq!(decision.reason, "authorized");
        assert_eq!(decision.required_data_class, "internal");
    }

    const ALL_ROLES: [&str; 8] = [
        "payroll_operator",
        "payroll_manager",
        "hr_operator",
        "hr_manager",
        "approval_signer",
        "it_security_admin",
        "platform_owner",
        "support_sre",
    ];

    #[test]
    fn every_rbac_grant_is_reachable_under_the_data_class_ceiling() {
        let policy = builtin();
        for role_id in ALL_ROLES {
            let role = policy.role(role_id).expect("builtin role present");
            for operation in AuthSensitiveOperation::ALL {
                if role.permits(operation) {
                    assert!(
                        role.max_data_class >= policy.required_data_class(operation),
                        "role {role_id} is RBAC-granted {} but its data-class ceiling \
                         makes the grant unreachable (dead permission)",
                        operation.id()
                    );
                }
            }
        }
    }

    #[test]
    fn policy_and_template_changes_are_frozen_during_active_payroll_cycle() {
        let policy = builtin();
        for operation in [
            AuthSensitiveOperation::PayrollPolicyChange,
            AuthSensitiveOperation::WorkflowTemplateWrite,
        ] {
            for state in [
                AuthWorkflowState::InputsClosed,
                AuthWorkflowState::Calculated,
                AuthWorkflowState::ApprovalPending,
            ] {
                let mut denied = request(operation);
                denied.workflow_state = state;
                assert_eq!(
                    evaluate_authorization(&policy, &denied).reason,
                    "pbac_workflow_denied",
                    "{} must be frozen in {}",
                    operation.id(),
                    state.as_str()
                );
            }

            for state in [
                AuthWorkflowState::Open,
                AuthWorkflowState::Approved,
                AuthWorkflowState::Archived,
            ] {
                let mut allowed = request(operation);
                allowed.workflow_state = state;
                assert!(
                    evaluate_authorization(&policy, &allowed).allowed,
                    "{} should be allowed in {}",
                    operation.id(),
                    state.as_str()
                );
            }
        }
    }

    #[test]
    fn payroll_export_before_approval_is_pbac_denied() {
        let policy = builtin();
        let mut request = request(AuthSensitiveOperation::PayrollExport);
        request.current_acr = Some(AuthAcrLevel::Sensitive);
        request.role = Some("payroll_operator");
        request.workflow_state = AuthWorkflowState::Calculated;

        let decision = evaluate_authorization(&policy, &request);

        assert!(!decision.allowed);
        assert_eq!(decision.reason, "pbac_workflow_denied");
    }

    #[test]
    fn untrusted_policy_version_is_pbac_denied_before_permissions() {
        let policy = builtin();
        let mut request = request(AuthSensitiveOperation::PayrollRun);
        request.policy_id = "bitween.authz.legacy";
        request.current_acr = Some(AuthAcrLevel::Sensitive);
        request.role = Some("platform_owner");

        let decision = evaluate_authorization(&policy, &request);

        assert!(!decision.allowed);
        assert_eq!(decision.reason, "policy_version_untrusted");
        assert_eq!(decision.policy_id, AUTHZ_POLICY_ID);
    }

    #[test]
    fn tenant_destructive_change_requires_critical_admin_or_owner() {
        let policy = builtin();
        let mut denied = request(AuthSensitiveOperation::TenantDestructiveChange);
        denied.role = Some("payroll_manager");
        denied.current_acr = Some(AuthAcrLevel::Critical);
        denied.actor_workplace = "";
        denied.resource_workplace = "";

        let mut allowed = denied.clone();
        allowed.role = Some("it_security_admin");

        assert_eq!(evaluate_authorization(&policy, &denied).reason, "rbac_denied");
        assert!(evaluate_authorization(&policy, &allowed).allowed);
    }

    #[test]
    fn builtin_matches_legacy_policy_id_and_shape() {
        let policy = builtin();
        assert_eq!(policy.policy_id, AUTHZ_POLICY_ID);
        assert_eq!(policy.operations.len(), 18);
        assert_eq!(policy.roles.len(), 8);
    }

    #[test]
    fn custom_policy_json_grants_a_custom_role_an_operation() {
        let raw = r#"{
            "policy_id": "bitween.authz.rbac-abac-pbac.v1",
            "operations": {
                "payroll_run": {
                    "required_acr": "sensitive",
                    "required_data_class": "payroll_confidential",
                    "requires_workplace_scope": true,
                    "allowed_workflow_states": ["inputs_closed", "calculated"]
                }
            },
            "roles": {
                "finance_runner": {
                    "max_data_class": "payroll_confidential",
                    "grants": ["payroll_run"]
                }
            }
        }"#;
        let policy = AuthzPolicy::from_json(raw).expect("custom policy parses");

        let mut request = request(AuthSensitiveOperation::PayrollRun);
        request.role = Some("finance_runner");
        request.current_acr = Some(AuthAcrLevel::Sensitive);
        request.workflow_state = AuthWorkflowState::InputsClosed;

        let decision = evaluate_authorization(&policy, &request);
        assert!(decision.allowed);
        assert_eq!(decision.reason, "authorized");
        assert_eq!(decision.role.as_deref(), Some("finance_runner"));
    }

    #[test]
    fn wildcard_grant_permits_every_operation() {
        let raw = r#"{
            "policy_id": "bitween.authz.rbac-abac-pbac.v1",
            "operations": {
                "read_workspace": {
                    "required_acr": "routine",
                    "required_data_class": "internal",
                    "requires_workplace_scope": false
                }
            },
            "roles": {
                "superuser": {
                    "max_data_class": "tenant_critical",
                    "grants": ["*"]
                }
            }
        }"#;
        let policy = AuthzPolicy::from_json(raw).expect("wildcard policy parses");

        let mut request = request(AuthSensitiveOperation::ReadWorkspace);
        request.role = Some("superuser");
        request.current_acr = Some(AuthAcrLevel::Routine);
        request.actor_workplace = "";
        request.resource_workplace = "";

        let decision = evaluate_authorization(&policy, &request);
        assert!(decision.allowed);
        assert_eq!(decision.reason, "authorized");
    }

    #[test]
    fn dead_grant_below_data_class_ceiling_is_rejected_at_load() {
        let raw = r#"{
            "policy_id": "bitween.authz.rbac-abac-pbac.v1",
            "operations": {
                "payroll_run": {
                    "required_acr": "sensitive",
                    "required_data_class": "payroll_confidential",
                    "requires_workplace_scope": true,
                    "allowed_workflow_states": ["inputs_closed"]
                }
            },
            "roles": {
                "hr_runner": {
                    "max_data_class": "employee_restricted",
                    "grants": ["payroll_run"]
                }
            }
        }"#;
        let error = AuthzPolicy::from_json(raw).expect_err("dead grant must be rejected");
        assert!(error.message().contains("dead grant"));
    }

    #[test]
    fn invalid_json_and_empty_fields_are_rejected() {
        assert!(AuthzPolicy::from_json("not json").is_err());
        assert!(AuthzPolicy::from_json(r#"{"policy_id":"","roles":{},"operations":{}}"#).is_err());
        // Empty roles map.
        assert!(
            AuthzPolicy::from_json(
                r#"{"policy_id":"x","operations":{},"roles":{}}"#
            )
            .is_err()
        );
        // Unknown operation id in operations.
        assert!(
            AuthzPolicy::from_json(
                r#"{"policy_id":"x","operations":{"admin_override":{"required_acr":"routine","required_data_class":"internal","requires_workplace_scope":false}},"roles":{"r":{"max_data_class":"internal","grants":[]}}}"#
            )
            .is_err()
        );
        // Unknown operation id in a grant.
        assert!(
            AuthzPolicy::from_json(
                r#"{"policy_id":"x","operations":{},"roles":{"r":{"max_data_class":"internal","grants":["admin_override"]}}}"#
            )
            .is_err()
        );
    }

    #[test]
    fn from_env_blank_falls_back_to_builtin() {
        // No assumption about process env: from_json with the builtin shape is the
        // contract path; from_env behavior under env is covered in the binary test.
        let policy = AuthzPolicy::builtin();
        assert_eq!(policy.policy_id, AUTHZ_POLICY_ID);
    }

    #[test]
    fn custom_policy_missing_operation_falls_back_to_builtin_workflow_window() {
        // Finding #1: a custom policy that omits an operation from its
        // `operations` map must fall back to the builtin workflow window (fail
        // closed), not "all states allowed".
        let raw = r#"{
            "policy_id": "bitween.authz.rbac-abac-pbac.v1",
            "operations": {},
            "roles": {
                "finance_runner": {
                    "max_data_class": "payroll_confidential",
                    "grants": ["payroll_export"]
                }
            }
        }"#;
        let policy = AuthzPolicy::from_json(raw).expect("policy with empty operations parses");

        // payroll_export builtin window is approved|archived only.
        let mut calculated = request(AuthSensitiveOperation::PayrollExport);
        calculated.role = Some("finance_runner");
        calculated.current_acr = Some(AuthAcrLevel::Sensitive);
        calculated.workflow_state = AuthWorkflowState::Calculated;
        let denied = evaluate_authorization(&policy, &calculated);
        assert!(!denied.allowed);
        assert_eq!(denied.reason, "pbac_workflow_denied");

        let mut approved = calculated.clone();
        approved.workflow_state = AuthWorkflowState::Approved;
        let allowed = evaluate_authorization(&policy, &approved);
        assert!(allowed.allowed);
        assert_eq!(allowed.reason, "authorized");
    }

    #[test]
    fn colliding_role_keys_are_rejected_at_load() {
        // Finding #2: two JSON keys normalizing to the same canonical role id
        // must be rejected (fail closed) rather than silently overwriting.
        let raw = r#"{
            "policy_id": "bitween.authz.rbac-abac-pbac.v1",
            "operations": {},
            "roles": {
                "payroll_ops": {
                    "max_data_class": "payroll_confidential",
                    "grants": ["payroll_run"]
                },
                "payroll_operator": {
                    "max_data_class": "internal",
                    "grants": []
                }
            }
        }"#;
        let error = AuthzPolicy::from_json(raw).expect_err("colliding role keys must be rejected");
        assert!(error.message().contains("duplicate role"));
    }

    #[test]
    fn colliding_operation_keys_are_rejected_at_load() {
        // Same fail-open footgun as colliding role keys, proven end-to-end in
        // review: "payroll-export" with a tight [approved] window and
        // "payroll_export" with a null (all-states) window collapse onto one
        // canonical id, and the looser survivor silently widened the PBAC gate.
        let raw = r#"{
            "policy_id": "bitween.authz.rbac-abac-pbac.v1",
            "operations": {
                "payroll-export": {
                    "required_acr": "sensitive",
                    "required_data_class": "payroll_confidential",
                    "requires_workplace_scope": true,
                    "allowed_workflow_states": ["approved"]
                },
                "payroll_export": {
                    "required_acr": "sensitive",
                    "required_data_class": "payroll_confidential",
                    "requires_workplace_scope": true,
                    "allowed_workflow_states": null
                }
            },
            "roles": {
                "payroll_operator": {
                    "max_data_class": "payroll_confidential",
                    "grants": ["payroll_export"]
                }
            }
        }"#;
        let error =
            AuthzPolicy::from_json(raw).expect_err("colliding operation keys must be rejected");
        assert!(error.message().contains("duplicate operation"));
    }

    #[test]
    fn from_env_var_decision_is_fail_closed_for_non_unicode() {
        // Finding #3: NotUnicode is a configured-but-unreadable value and must
        // fail closed, while NotPresent and blank fall back to the builtin.
        assert!(
            AuthzPolicy::from_env_var(Err(std::env::VarError::NotPresent))
                .expect("unset falls back to builtin")
                .policy_id
                == AUTHZ_POLICY_ID
        );
        assert!(
            AuthzPolicy::from_env_var(Ok("   ".to_owned()))
                .expect("blank falls back to builtin")
                .policy_id
                == AUTHZ_POLICY_ID
        );
        let non_unicode = {
            use std::os::unix::ffi::OsStringExt;
            std::ffi::OsString::from_vec(vec![0x66, 0x80, 0x6f])
        };
        let error = AuthzPolicy::from_env_var(Err(std::env::VarError::NotUnicode(non_unicode)))
            .expect_err("non-unicode value must fail closed");
        assert!(error.message().contains("non-unicode"));
    }

    #[test]
    fn wildcard_grant_below_max_data_class_is_rejected_at_load() {
        // Finding #4: a "*" grant must clear the maximum required_data_class
        // across all operations or it carries dead grants.
        let raw = r#"{
            "policy_id": "bitween.authz.rbac-abac-pbac.v1",
            "operations": {},
            "roles": {
                "weak_wildcard": {
                    "max_data_class": "internal",
                    "grants": ["*"]
                }
            }
        }"#;
        let error = AuthzPolicy::from_json(raw).expect_err("under-ceiled wildcard must be rejected");
        assert!(error.message().contains("dead grant"));
    }

    #[test]
    fn unknown_role_decision_does_not_echo_arbitrary_role() {
        // Finding #5: unknown (non-blank) roles still deny with rbac_denied, but
        // the decision role must be null rather than the echoed caller string.
        let policy = builtin();
        let mut unknown = request(AuthSensitiveOperation::PayrollRun);
        unknown.role = Some("superuser");
        unknown.current_acr = Some(AuthAcrLevel::Sensitive);
        let decision = evaluate_authorization(&policy, &unknown);
        assert_eq!(decision.reason, "rbac_denied");
        assert_eq!(decision.role, None);

        // A known role is still echoed.
        let mut known = request(AuthSensitiveOperation::PayrollRun);
        known.role = Some("payroll_operator");
        known.current_acr = Some(AuthAcrLevel::Sensitive);
        assert_eq!(
            evaluate_authorization(&policy, &known).role.as_deref(),
            Some("payroll_operator")
        );
    }

    #[test]
    fn inconsistent_workflow_state_is_denied_for_every_windowed_operation() {
        // Finding #7 (auth level): the Inconsistent sentinel must be denied for
        // every operation that declares an explicit workflow window.
        let policy = builtin();
        for operation in [
            AuthSensitiveOperation::PayrollRun,
            AuthSensitiveOperation::PayrollExport,
            AuthSensitiveOperation::ApprovalSigning,
            AuthSensitiveOperation::WorkflowTemplateWrite,
        ] {
            let mut denied = request(operation);
            denied.role = Some("platform_owner");
            denied.current_acr = Some(AuthAcrLevel::Critical);
            denied.workflow_state = AuthWorkflowState::Inconsistent;
            let decision = evaluate_authorization(&policy, &denied);
            assert!(!decision.allowed, "{} must deny in inconsistent state", operation.id());
            assert_eq!(
                decision.reason,
                "pbac_workflow_denied",
                "{} must be pbac_workflow_denied in inconsistent state",
                operation.id()
            );
        }

        // Operations with no window (None) stay allowed even in the sentinel
        // state: that asymmetry is intended.
        let mut open_op = request(AuthSensitiveOperation::ReadWorkspace);
        open_op.role = Some("support_sre");
        open_op.current_acr = Some(AuthAcrLevel::Routine);
        open_op.actor_workplace = "";
        open_op.resource_workplace = "";
        open_op.workflow_state = AuthWorkflowState::Inconsistent;
        assert!(evaluate_authorization(&policy, &open_op).allowed);
    }

    #[test]
    fn inconsistent_workflow_state_is_not_parseable() {
        // No custom policy may open a window on the sentinel state.
        assert_eq!(AuthWorkflowState::parse("inconsistent"), None);
        assert_eq!(AuthWorkflowState::Inconsistent.as_str(), "inconsistent");
    }
}
