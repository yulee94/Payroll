use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

pub const ROLE_STAFF: &str = "staff";
pub const ROLE_FINANCE: &str = "finance";
pub const ROLE_ADMIN: &str = "admin";

pub const WF_ROLE_ADMIN: &str = "admin";
pub const WF_ROLE_EXECUTIVE: &str = "executive";
pub const WF_ROLE_SITE_MANAGER: &str = "site_manager";
pub const WF_ROLE_DEPT_MANAGER: &str = "department_manager";
pub const WF_ROLE_APPROVER: &str = "approver";
pub const WF_ROLE_REQUESTER: &str = "requester";
pub const WF_ROLE_EXECUTOR: &str = "executor";
pub const WF_ROLE_FINANCE: &str = "finance";
pub const WF_ROLE_HR: &str = "hr";
pub const WF_ROLE_VIEWER: &str = "viewer";

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct BusinessTripPrincipal {
    pub user_id: String,
    pub tenant_id: String,
    pub role: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct BusinessTripProfile {
    pub workflow_roles: Vec<String>,
    pub site_ids: Vec<String>,
    pub department_ids: Vec<String>,
    pub org_unit_ids: Vec<String>,
    pub viewer_site_ids: Vec<String>,
    pub viewer_department_ids: Vec<String>,
    pub manager_user_id: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct BusinessTripPermissionTrip {
    pub tenant_id: String,
    pub origin_tenant_id: String,
    pub legal_tenant_id: String,
    pub requester_id: String,
    pub traveler_user_id: String,
    pub executor_id: String,
    pub site_id: String,
    pub department_id: String,
    pub org_unit_id: String,
    pub approver_ids: Vec<String>,
    pub approval_user_ids: Vec<String>,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct BusinessTripPermissionInput {
    pub principal: BusinessTripPrincipal,
    pub profile: Option<BusinessTripProfile>,
    pub requester_profile: Option<BusinessTripProfile>,
    pub trip: BusinessTripPermissionTrip,
    pub tenant_id: String,
}

pub fn workflow_roles(
    principal: &BusinessTripPrincipal,
    profile: Option<&BusinessTripProfile>,
) -> BTreeSet<String> {
    let mut roles = BTreeSet::new();
    if let Some(profile) = profile {
        for role in &profile.workflow_roles {
            let role = clean(role);
            if !role.is_empty() {
                roles.insert(role);
            }
        }
    }

    match normalize_role(&principal.role).as_str() {
        ROLE_ADMIN => {
            roles.insert(WF_ROLE_ADMIN.to_string());
            roles.insert(WF_ROLE_EXECUTIVE.to_string());
            roles.insert(WF_ROLE_APPROVER.to_string());
            roles.insert(WF_ROLE_FINANCE.to_string());
            roles.insert(WF_ROLE_HR.to_string());
        }
        ROLE_FINANCE => {
            roles.insert(WF_ROLE_FINANCE.to_string());
            roles.insert(WF_ROLE_APPROVER.to_string());
            roles.insert(WF_ROLE_EXECUTIVE.to_string());
        }
        _ => {}
    }

    if roles.is_empty() {
        roles.insert(WF_ROLE_REQUESTER.to_string());
    }
    roles
}

pub fn is_business_trip_legal_scope_allowed(
    principal: &BusinessTripPrincipal,
    trip: &BusinessTripPermissionTrip,
    tenant_id: &str,
) -> bool {
    let storage_tenant = clean(tenant_id);
    let row_storage_tenant = clean(&trip.tenant_id);
    if !row_storage_tenant.is_empty() && row_storage_tenant != storage_tenant {
        return false;
    }

    let origin_tenant = first_nonempty(&[
        trip.origin_tenant_id.as_str(),
        trip.legal_tenant_id.as_str(),
        row_storage_tenant.as_str(),
        storage_tenant.as_str(),
    ]);
    let user_tenant = clean(&principal.tenant_id);
    if user_tenant.is_empty() {
        return true;
    }
    if user_tenant == origin_tenant {
        return true;
    }
    !storage_tenant.is_empty() && user_tenant == storage_tenant && storage_tenant != origin_tenant
}

pub fn can_view_business_trip_lifecycle(input: &BusinessTripPermissionInput) -> bool {
    if !is_business_trip_legal_scope_allowed(&input.principal, &input.trip, &input.tenant_id) {
        return false;
    }

    let uid = clean(&input.principal.user_id);
    let roles = workflow_roles(&input.principal, input.profile.as_ref());
    if has_admin_view_role(&roles) {
        return true;
    }

    let requester_id = requester_id(&input.trip);
    let executor_id = clean(&input.trip.executor_id);
    if uid == requester_id || uid == executor_id {
        return true;
    }

    if roles.contains(WF_ROLE_APPROVER) && contains_id(explicit_approvers(&input.trip), &uid) {
        return true;
    }

    let Some(profile) = input.profile.as_ref() else {
        return false;
    };

    if !requester_id.is_empty()
        && input
            .requester_profile
            .as_ref()
            .is_some_and(|traveler_profile| clean(&traveler_profile.manager_user_id) == uid)
    {
        return true;
    }

    let site_id = clean(&input.trip.site_id);
    let dept_id = trip_department_id(&input.trip);
    let allowed_sites = &profile.site_ids;
    let allowed_departments = profile_department_ids(profile);
    if !site_id.is_empty()
        && contains_id(allowed_sites, &site_id)
        && (roles.contains(WF_ROLE_SITE_MANAGER) || roles.contains(WF_ROLE_HR))
    {
        return true;
    }
    if !dept_id.is_empty()
        && contains_id(allowed_departments, &dept_id)
        && (roles.contains(WF_ROLE_DEPT_MANAGER)
            || roles.contains(WF_ROLE_SITE_MANAGER)
            || roles.contains(WF_ROLE_HR))
    {
        return true;
    }

    if roles.contains(WF_ROLE_VIEWER)
        && ((!site_id.is_empty() && contains_id(&profile.viewer_site_ids, &site_id))
            || (!dept_id.is_empty() && contains_id(&profile.viewer_department_ids, &dept_id)))
    {
        return true;
    }

    false
}

pub fn can_manage_business_trip_lifecycle(input: &BusinessTripPermissionInput) -> bool {
    if !is_business_trip_legal_scope_allowed(&input.principal, &input.trip, &input.tenant_id) {
        return false;
    }

    let uid = clean(&input.principal.user_id);
    let roles = workflow_roles(&input.principal, input.profile.as_ref());
    if has_admin_view_role(&roles) {
        return true;
    }

    let requester_id = requester_id(&input.trip);
    let executor_id = clean(&input.trip.executor_id);
    uid == requester_id || uid == executor_id
}

fn has_admin_view_role(roles: &BTreeSet<String>) -> bool {
    roles.contains(WF_ROLE_ADMIN)
        || roles.contains(WF_ROLE_EXECUTIVE)
        || roles.contains(WF_ROLE_FINANCE)
}

fn normalize_role(value: &str) -> String {
    let role = value.trim().to_lowercase();
    match role.as_str() {
        ROLE_STAFF | ROLE_FINANCE | ROLE_ADMIN => role,
        "user" | "general" | "일반" => ROLE_STAFF.to_string(),
        "재무" | "finance_team" => ROLE_FINANCE.to_string(),
        _ => ROLE_STAFF.to_string(),
    }
}

fn requester_id(trip: &BusinessTripPermissionTrip) -> String {
    first_nonempty(&[trip.requester_id.as_str(), trip.traveler_user_id.as_str()])
}

fn trip_department_id(trip: &BusinessTripPermissionTrip) -> String {
    first_nonempty(&[trip.department_id.as_str(), trip.org_unit_id.as_str()])
}

fn explicit_approvers(trip: &BusinessTripPermissionTrip) -> &[String] {
    if trip.approver_ids.is_empty() {
        &trip.approval_user_ids
    } else {
        &trip.approver_ids
    }
}

fn profile_department_ids(profile: &BusinessTripProfile) -> &[String] {
    if profile.department_ids.is_empty() {
        &profile.org_unit_ids
    } else {
        &profile.department_ids
    }
}

fn contains_id(values: &[String], expected: &str) -> bool {
    values.iter().any(|value| value.trim() == expected)
}

fn first_nonempty(values: &[&str]) -> String {
    values
        .iter()
        .map(|value| value.trim())
        .find(|value| !value.is_empty())
        .unwrap_or_default()
        .to_string()
}

fn clean(value: &str) -> String {
    value.trim().to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn principal(user_id: &str, tenant_id: &str, role: &str) -> BusinessTripPrincipal {
        BusinessTripPrincipal {
            user_id: user_id.to_string(),
            tenant_id: tenant_id.to_string(),
            role: role.to_string(),
        }
    }

    fn profile(roles: &[&str]) -> BusinessTripProfile {
        BusinessTripProfile {
            workflow_roles: roles.iter().map(|value| value.to_string()).collect(),
            ..BusinessTripProfile::default()
        }
    }

    fn trip() -> BusinessTripPermissionTrip {
        BusinessTripPermissionTrip {
            tenant_id: "tenant-a".to_string(),
            origin_tenant_id: "tenant-a".to_string(),
            requester_id: "requester-1".to_string(),
            traveler_user_id: "traveler-1".to_string(),
            executor_id: "executor-1".to_string(),
            site_id: "site-1".to_string(),
            department_id: "dept-1".to_string(),
            approver_ids: vec!["approver-1".to_string()],
            ..BusinessTripPermissionTrip::default()
        }
    }

    fn input(
        user_id: &str,
        tenant_id: &str,
        role: &str,
        user_profile: Option<BusinessTripProfile>,
    ) -> BusinessTripPermissionInput {
        BusinessTripPermissionInput {
            principal: principal(user_id, tenant_id, role),
            profile: user_profile,
            requester_profile: None,
            trip: trip(),
            tenant_id: "tenant-a".to_string(),
        }
    }

    #[test]
    fn legal_scope_blocks_sibling_tenant_even_for_admin_role() {
        let mut shared_trip = trip();
        shared_trip.tenant_id = "workflow-root".to_string();
        shared_trip.origin_tenant_id = "tenant-a".to_string();

        assert!(is_business_trip_legal_scope_allowed(
            &principal("hq-admin", "workflow-root", "admin"),
            &shared_trip,
            "workflow-root"
        ));
        assert!(!is_business_trip_legal_scope_allowed(
            &principal("sibling-admin", "tenant-b", "admin"),
            &shared_trip,
            "workflow-root"
        ));
        assert!(!is_business_trip_legal_scope_allowed(
            &principal("row-mismatch", "tenant-a", "admin"),
            &shared_trip,
            "tenant-a"
        ));
    }

    #[test]
    fn workflow_roles_expand_base_roles_and_default_to_requester() {
        let admin_roles = workflow_roles(&principal("admin-1", "tenant-a", "admin"), None);
        assert!(admin_roles.contains("admin"));
        assert!(admin_roles.contains("executive"));
        assert!(admin_roles.contains("approver"));
        assert!(admin_roles.contains("finance"));
        assert!(admin_roles.contains("hr"));

        let finance_roles = workflow_roles(&principal("finance-1", "tenant-a", "재무"), None);
        assert!(finance_roles.contains("finance"));
        assert!(finance_roles.contains("approver"));
        assert!(finance_roles.contains("executive"));

        let staff_roles = workflow_roles(&principal("staff-1", "tenant-a", "general"), None);
        assert_eq!(
            staff_roles,
            ["requester"].into_iter().map(String::from).collect()
        );
    }

    #[test]
    fn view_matrix_matches_python_permission_boundary() {
        assert!(can_view_business_trip_lifecycle(&input(
            "admin-1",
            "tenant-a",
            "staff",
            Some(profile(&["admin"]))
        )));
        assert!(can_view_business_trip_lifecycle(&input(
            "requester-1",
            "tenant-a",
            "staff",
            None
        )));
        assert!(can_view_business_trip_lifecycle(&input(
            "executor-1",
            "tenant-a",
            "staff",
            None
        )));
        assert!(can_view_business_trip_lifecycle(&input(
            "approver-1",
            "tenant-a",
            "staff",
            Some(profile(&["approver"]))
        )));

        let mut traveler_fallback = input("traveler-1", "tenant-a", "staff", None);
        traveler_fallback.trip.requester_id.clear();
        assert!(can_view_business_trip_lifecycle(&traveler_fallback));

        let mut site_manager = profile(&["site_manager"]);
        site_manager.site_ids = vec!["site-1".to_string()];
        assert!(can_view_business_trip_lifecycle(&input(
            "site-manager-1",
            "tenant-a",
            "staff",
            Some(site_manager)
        )));

        let mut dept_hr = profile(&["hr"]);
        dept_hr.department_ids = vec!["dept-1".to_string()];
        assert!(can_view_business_trip_lifecycle(&input(
            "dept-hr-1",
            "tenant-a",
            "staff",
            Some(dept_hr)
        )));

        assert!(!can_view_business_trip_lifecycle(&input(
            "viewer-1",
            "tenant-a",
            "staff",
            Some(profile(&["viewer"]))
        )));

        let mut scoped_viewer = profile(&["viewer"]);
        scoped_viewer.viewer_site_ids = vec!["site-1".to_string()];
        assert!(can_view_business_trip_lifecycle(&input(
            "viewer-2",
            "tenant-a",
            "staff",
            Some(scoped_viewer)
        )));
    }

    #[test]
    fn supplied_requester_manager_can_view_but_not_manage() {
        let viewer_profile = profile(&["requester"]);
        let requester_profile = BusinessTripProfile {
            manager_user_id: "manager-1".to_string(),
            ..BusinessTripProfile::default()
        };
        let permission = BusinessTripPermissionInput {
            principal: principal("manager-1", "tenant-a", "staff"),
            profile: Some(viewer_profile),
            requester_profile: Some(requester_profile),
            trip: trip(),
            tenant_id: "tenant-a".to_string(),
        };

        assert!(can_view_business_trip_lifecycle(&permission));
        assert!(!can_manage_business_trip_lifecycle(&permission));
    }

    #[test]
    fn manage_authority_is_narrower_than_visibility() {
        assert!(can_manage_business_trip_lifecycle(&input(
            "admin-1",
            "tenant-a",
            "staff",
            Some(profile(&["admin"]))
        )));
        assert!(can_manage_business_trip_lifecycle(&input(
            "requester-1",
            "tenant-a",
            "staff",
            None
        )));
        assert!(can_manage_business_trip_lifecycle(&input(
            "executor-1",
            "tenant-a",
            "staff",
            None
        )));

        let mut site_manager = profile(&["site_manager"]);
        site_manager.site_ids = vec!["site-1".to_string()];
        let visible_only = input("site-manager-1", "tenant-a", "staff", Some(site_manager));
        assert!(can_view_business_trip_lifecycle(&visible_only));
        assert!(!can_manage_business_trip_lifecycle(&visible_only));
    }
}
