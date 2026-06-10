use crate::request::PayrollRunRequest;
use serde::Serialize;
use std::collections::BTreeSet;

const PAYROLL_PLATFORM_ID: &str = "payroll";

#[derive(Clone, Copy, Debug, Default, Eq, Ord, PartialEq, PartialOrd)]
pub enum PayrollRole {
    #[default]
    Staff,
    Finance,
    Admin,
}

impl PayrollRole {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Staff => "staff",
            Self::Finance => "finance",
            Self::Admin => "admin",
        }
    }
}

impl Serialize for PayrollRole {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, Ord, PartialEq, PartialOrd)]
pub enum PayrollPosition {
    Ceo,
    Executive,
    Director,
    Manager,
    TeamLead,
    Senior,
    #[default]
    Member,
    Intern,
}

impl PayrollPosition {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Ceo => "ceo",
            Self::Executive => "executive",
            Self::Director => "director",
            Self::Manager => "manager",
            Self::TeamLead => "team_lead",
            Self::Senior => "senior",
            Self::Member => "member",
            Self::Intern => "intern",
        }
    }
}

impl Serialize for PayrollPosition {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum PayrollPermission {
    PayrollPlatform,
    PayrollExecutive,
    PayrollSettings,
}

impl PayrollPermission {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::PayrollPlatform => "platform.payroll",
            Self::PayrollExecutive => "platform.payroll.executive",
            Self::PayrollSettings => "platform.payroll.settings",
        }
    }
}

impl Serialize for PayrollPermission {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum PayrollAction {
    Validate,
    Run,
    Settings,
}

impl PayrollAction {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Validate => "validate",
            Self::Run => "run",
            Self::Settings => "settings",
        }
    }
}

impl Serialize for PayrollAction {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PayrollPrincipal {
    pub user_id: String,
    pub tenant_id: String,
    pub role: PayrollRole,
    pub position: PayrollPosition,
    pub org_unit_id: String,
    pub effective_platform_ids: BTreeSet<String>,
    pub allowed_affiliates: BTreeSet<String>,
    pub allowed_workplaces: BTreeSet<String>,
}

impl PayrollPrincipal {
    pub fn new(user_id: impl Into<String>, tenant_id: impl Into<String>) -> Self {
        Self {
            user_id: clean(user_id),
            tenant_id: clean(tenant_id),
            role: PayrollRole::Staff,
            position: PayrollPosition::Member,
            org_unit_id: String::new(),
            effective_platform_ids: BTreeSet::new(),
            allowed_affiliates: BTreeSet::new(),
            allowed_workplaces: BTreeSet::new(),
        }
    }

    pub fn with_role(mut self, role: PayrollRole) -> Self {
        self.role = role;
        self
    }

    pub fn with_position(mut self, position: PayrollPosition) -> Self {
        self.position = position;
        self
    }

    pub fn with_org_unit(mut self, org_unit_id: impl Into<String>) -> Self {
        self.org_unit_id = clean(org_unit_id);
        self
    }

    pub fn with_effective_platforms<I, S>(mut self, platforms: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        self.effective_platform_ids = platforms
            .into_iter()
            .map(clean_lower)
            .filter(|value| !value.is_empty())
            .collect();
        self
    }

    pub fn with_allowed_affiliates<I, S>(mut self, affiliates: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        self.allowed_affiliates = affiliates
            .into_iter()
            .map(clean)
            .filter(|value| !value.is_empty())
            .collect();
        self
    }

    pub fn with_allowed_workplaces<I, S>(mut self, workplaces: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        self.allowed_workplaces = workplaces
            .into_iter()
            .map(clean)
            .filter(|value| !value.is_empty())
            .collect();
        self
    }

    pub fn permissions(&self) -> BTreeSet<PayrollPermission> {
        let mut permissions = position_permissions(self.position);
        match self.role {
            PayrollRole::Admin => permissions.extend(all_payroll_permissions()),
            PayrollRole::Finance => permissions.extend([
                PayrollPermission::PayrollPlatform,
                PayrollPermission::PayrollExecutive,
            ]),
            PayrollRole::Staff => {}
        }

        if self.position != PayrollPosition::Ceo
            && !self.org_unit_id.is_empty()
            && !self.effective_platform_ids.contains(PAYROLL_PLATFORM_ID)
        {
            permissions.remove(&PayrollPermission::PayrollPlatform);
            permissions.remove(&PayrollPermission::PayrollExecutive);
            permissions.remove(&PayrollPermission::PayrollSettings);
        }

        permissions
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollAccessDecision {
    pub ok: bool,
    pub allowed: bool,
    pub action: PayrollAction,
    pub user_id: String,
    pub tenant_id: String,
    pub scope: String,
    pub reason_code: String,
    pub reason: String,
    pub required_permissions: Vec<PayrollPermission>,
    pub granted_permissions: Vec<PayrollPermission>,
}

pub fn authorize_payroll_request(
    request: &PayrollRunRequest,
    principal: &PayrollPrincipal,
    action: PayrollAction,
) -> PayrollAccessDecision {
    let granted_permissions = sorted_permissions(principal.permissions());
    let scope = request.scope.display();
    let request_tenant = request.tenant_id.as_deref().map(clean).unwrap_or_default();
    let tenant_id = if request_tenant.is_empty() {
        principal.tenant_id.clone()
    } else {
        request_tenant.clone()
    };

    if principal.tenant_id.is_empty() {
        return denied(
            request,
            principal,
            action,
            tenant_id,
            "missing_principal_tenant",
            "Payroll access requires a tenant-scoped principal.",
            Vec::new(),
            granted_permissions,
        );
    }

    if !request_tenant.is_empty() && request_tenant != principal.tenant_id {
        return denied(
            request,
            principal,
            action,
            tenant_id,
            "tenant_mismatch",
            "Payroll request tenant does not match the principal tenant.",
            Vec::new(),
            granted_permissions,
        );
    }

    let required_permissions = required_permissions(action);
    if !required_permissions
        .iter()
        .all(|permission| granted_permissions.contains(permission))
    {
        return denied(
            request,
            principal,
            action,
            tenant_id,
            "missing_permission",
            "Payroll action requires a permission that is not granted to the principal.",
            required_permissions,
            granted_permissions,
        );
    }

    if !principal.allowed_affiliates.is_empty()
        && !principal
            .allowed_affiliates
            .contains(&request.scope.affiliate)
    {
        return denied(
            request,
            principal,
            action,
            tenant_id,
            "affiliate_not_allowed",
            "Payroll request affiliate is outside the principal access scope.",
            required_permissions,
            granted_permissions,
        );
    }

    if !principal.allowed_workplaces.is_empty()
        && !principal
            .allowed_workplaces
            .contains(&request.scope.workplace)
    {
        return denied(
            request,
            principal,
            action,
            tenant_id,
            "workplace_not_allowed",
            "Payroll request workplace is outside the principal access scope.",
            required_permissions,
            granted_permissions,
        );
    }

    PayrollAccessDecision {
        ok: true,
        allowed: true,
        action,
        user_id: principal.user_id.clone(),
        tenant_id,
        scope,
        reason_code: String::new(),
        reason: String::new(),
        required_permissions,
        granted_permissions,
    }
}

fn denied(
    request: &PayrollRunRequest,
    principal: &PayrollPrincipal,
    action: PayrollAction,
    tenant_id: String,
    reason_code: impl Into<String>,
    reason: impl Into<String>,
    required_permissions: Vec<PayrollPermission>,
    granted_permissions: Vec<PayrollPermission>,
) -> PayrollAccessDecision {
    PayrollAccessDecision {
        ok: false,
        allowed: false,
        action,
        user_id: principal.user_id.clone(),
        tenant_id,
        scope: request.scope.display(),
        reason_code: reason_code.into(),
        reason: reason.into(),
        required_permissions,
        granted_permissions,
    }
}

fn position_permissions(position: PayrollPosition) -> BTreeSet<PayrollPermission> {
    match position {
        PayrollPosition::Ceo => all_payroll_permissions(),
        PayrollPosition::Executive => all_payroll_permissions(),
        PayrollPosition::Director => [
            PayrollPermission::PayrollPlatform,
            PayrollPermission::PayrollExecutive,
        ]
        .into_iter()
        .collect(),
        PayrollPosition::Manager | PayrollPosition::TeamLead | PayrollPosition::Senior => {
            [PayrollPermission::PayrollPlatform].into_iter().collect()
        }
        PayrollPosition::Member | PayrollPosition::Intern => BTreeSet::new(),
    }
}

fn all_payroll_permissions() -> BTreeSet<PayrollPermission> {
    [
        PayrollPermission::PayrollPlatform,
        PayrollPermission::PayrollExecutive,
        PayrollPermission::PayrollSettings,
    ]
    .into_iter()
    .collect()
}

fn required_permissions(action: PayrollAction) -> Vec<PayrollPermission> {
    match action {
        PayrollAction::Validate => vec![PayrollPermission::PayrollPlatform],
        PayrollAction::Run => vec![PayrollPermission::PayrollExecutive],
        PayrollAction::Settings => vec![PayrollPermission::PayrollSettings],
    }
}

fn sorted_permissions(permissions: BTreeSet<PayrollPermission>) -> Vec<PayrollPermission> {
    permissions.into_iter().collect()
}

fn clean(value: impl Into<String>) -> String {
    value.into().trim().to_owned()
}

fn clean_lower(value: impl Into<String>) -> String {
    clean(value).to_ascii_lowercase()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::request::{PayrollInputType, PayrollRunRequest, PayrollScope};
    use std::{collections::BTreeMap, path::PathBuf};

    fn request(tenant_id: &str, workplace: &str) -> PayrollRunRequest {
        PayrollRunRequest {
            request_id: "req-auth".to_owned(),
            scope: PayrollScope::new("Acme", workplace, "2026-05").unwrap(),
            input_type: PayrollInputType::Mixed,
            invoice_path: Some(PathBuf::from("invoice.xlsx")),
            attendance_path: Some(PathBuf::from("attendance.csv")),
            tenant_id: Some(tenant_id.to_owned()),
            metadata: BTreeMap::new(),
            validate_only: false,
        }
    }

    #[test]
    fn finance_manager_in_payroll_unit_can_run_payroll() {
        let principal = PayrollPrincipal::new("user-finance", "acme")
            .with_role(PayrollRole::Finance)
            .with_position(PayrollPosition::Manager)
            .with_org_unit("finance")
            .with_effective_platforms(["payroll", "accounting"]);

        let decision =
            authorize_payroll_request(&request("acme", "Site A"), &principal, PayrollAction::Run);
        let value = serde_json::to_value(&decision).unwrap();

        assert!(decision.allowed);
        assert_eq!(value["ok"], true);
        assert_eq!(value["action"], "run");
        assert_eq!(value["reason_code"], "");
        assert_eq!(value["tenant_id"], "acme");
        assert_eq!(
            value["required_permissions"],
            serde_json::json!(["platform.payroll.executive"])
        );
    }

    #[test]
    fn team_platform_filter_denies_non_ceo_admin_outside_payroll() {
        let principal = PayrollPrincipal::new("user-admin", "acme")
            .with_role(PayrollRole::Admin)
            .with_position(PayrollPosition::Member)
            .with_org_unit("maintenance")
            .with_effective_platforms(["maintenance"]);

        let decision = authorize_payroll_request(
            &request("acme", "Site A"),
            &principal,
            PayrollAction::Validate,
        );

        assert!(!decision.allowed);
        assert_eq!(decision.reason_code, "missing_permission");
        assert_eq!(
            decision.required_permissions,
            vec![PayrollPermission::PayrollPlatform]
        );
    }

    #[test]
    fn ceo_bypasses_team_platform_filter_for_payroll() {
        let principal = PayrollPrincipal::new("user-ceo", "acme")
            .with_role(PayrollRole::Staff)
            .with_position(PayrollPosition::Ceo)
            .with_org_unit("root")
            .with_effective_platforms(["maintenance"]);

        let decision = authorize_payroll_request(
            &request("acme", "Site A"),
            &principal,
            PayrollAction::Settings,
        );

        assert!(decision.allowed);
        assert_eq!(decision.reason_code, "");
    }

    #[test]
    fn tenant_mismatch_is_denied_before_permission_checks() {
        let principal = PayrollPrincipal::new("user-finance", "acme")
            .with_role(PayrollRole::Finance)
            .with_position(PayrollPosition::Manager)
            .with_org_unit("finance")
            .with_effective_platforms(["payroll"]);

        let decision =
            authorize_payroll_request(&request("other", "Site A"), &principal, PayrollAction::Run);

        assert!(!decision.allowed);
        assert_eq!(decision.reason_code, "tenant_mismatch");
        assert_eq!(decision.tenant_id, "other");
    }

    #[test]
    fn missing_principal_tenant_is_denied() {
        let principal = PayrollPrincipal::new("user-finance", "")
            .with_role(PayrollRole::Finance)
            .with_position(PayrollPosition::Manager)
            .with_org_unit("finance")
            .with_effective_platforms(["payroll"]);

        let decision =
            authorize_payroll_request(&request("", "Site A"), &principal, PayrollAction::Run);

        assert!(!decision.allowed);
        assert_eq!(decision.reason_code, "missing_principal_tenant");
    }

    #[test]
    fn affiliate_abac_restriction_denies_unlisted_affiliate() {
        let principal = PayrollPrincipal::new("user-finance", "acme")
            .with_role(PayrollRole::Finance)
            .with_position(PayrollPosition::Manager)
            .with_org_unit("finance")
            .with_effective_platforms(["payroll"])
            .with_allowed_affiliates(["OTHER"]);

        let decision =
            authorize_payroll_request(&request("acme", "Site A"), &principal, PayrollAction::Run);

        assert!(!decision.allowed);
        assert_eq!(decision.reason_code, "affiliate_not_allowed");
    }

    #[test]
    fn workplace_abac_restriction_denies_unlisted_site() {
        let principal = PayrollPrincipal::new("user-finance", "acme")
            .with_role(PayrollRole::Finance)
            .with_position(PayrollPosition::Manager)
            .with_org_unit("finance")
            .with_effective_platforms(["payroll"])
            .with_allowed_workplaces(["Site A"]);

        let decision =
            authorize_payroll_request(&request("acme", "Site B"), &principal, PayrollAction::Run);

        assert!(!decision.allowed);
        assert_eq!(decision.reason_code, "workplace_not_allowed");
    }
}
