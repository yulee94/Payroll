use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

pub const ROLE_STAFF: &str = "staff";
pub const ROLE_FINANCE: &str = "finance";
pub const ROLE_ADMIN: &str = "admin";

pub const DOC_STATUS_DRAFT: &str = "draft";
pub const DOC_STATUS_SUBMITTED: &str = "submitted";
pub const DOC_STATUS_IN_REVIEW: &str = "in_review";
pub const DOC_STATUS_APPROVED: &str = "approved";
pub const DOC_STATUS_REQUESTED_CHANGES: &str = "requested_changes";
pub const DOC_STATUS_CLOSED: &str = "closed";

pub const STEP_PENDING: &str = "pending";
pub const STEP_APPROVED: &str = "approved";

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

pub const DOC_TYPE_BUSINESS_TRIP_REQUEST: &str = "BUSINESS_TRIP_REQUEST";

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
    pub legal_entity_id: String,
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
pub struct BusinessTripPermissionDocument {
    pub document_type: String,
    pub origin_tenant_id: String,
    pub legal_tenant_id: String,
    pub legal_entity_id: String,
    pub content_trip_id: String,
    pub content_origin_tenant_id: String,
    pub content_legal_tenant_id: String,
    pub content_legal_entity_id: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowApprovalStep {
    pub approver_id: String,
    pub status: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowPermissionDocument {
    pub document_type: String,
    pub origin_tenant_id: String,
    pub legal_tenant_id: String,
    pub legal_entity_id: String,
    pub content_trip_id: String,
    pub content_origin_tenant_id: String,
    pub content_legal_tenant_id: String,
    pub content_legal_entity_id: String,
    pub status: String,
    pub requester_id: String,
    pub site_id: String,
    pub approval_steps: Vec<WorkflowApprovalStep>,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct BusinessTripPermissionInput {
    pub principal: BusinessTripPrincipal,
    pub profile: Option<BusinessTripProfile>,
    pub requester_profile: Option<BusinessTripProfile>,
    pub trip: BusinessTripPermissionTrip,
    pub tenant_id: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowDocumentPermissionInput {
    pub principal: BusinessTripPrincipal,
    pub profile: Option<BusinessTripProfile>,
    pub document: WorkflowPermissionDocument,
    pub tenant_id: String,
    pub can_approve_workflow: bool,
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

pub fn is_business_trip_related_document(document: &BusinessTripPermissionDocument) -> bool {
    clean(&document.document_type) == DOC_TYPE_BUSINESS_TRIP_REQUEST
        || !clean(&document.content_trip_id).is_empty()
}

pub fn is_business_trip_document_legal_scope_allowed(
    principal: &BusinessTripPrincipal,
    document: &BusinessTripPermissionDocument,
    tenant_id: &str,
) -> bool {
    if !is_business_trip_related_document(document) {
        return true;
    }

    let storage_tenant = clean(tenant_id);
    let origin_tenant = first_nonempty(&[
        document.origin_tenant_id.as_str(),
        document.content_origin_tenant_id.as_str(),
        document.content_legal_tenant_id.as_str(),
        storage_tenant.as_str(),
    ]);
    let trip = BusinessTripPermissionTrip {
        tenant_id: storage_tenant.clone(),
        origin_tenant_id: origin_tenant,
        legal_entity_id: first_nonempty(&[
            document.legal_entity_id.as_str(),
            document.content_legal_entity_id.as_str(),
        ]),
        ..BusinessTripPermissionTrip::default()
    };
    is_business_trip_legal_scope_allowed(principal, &trip, &storage_tenant)
}

pub fn can_view_document(input: &WorkflowDocumentPermissionInput) -> bool {
    if !workflow_permission_document_legal_scope_allowed(
        &input.principal,
        &input.document,
        &input.tenant_id,
    ) {
        return false;
    }

    let uid = clean(&input.principal.user_id);
    let roles = workflow_roles(&input.principal, input.profile.as_ref());
    if has_admin_view_role(&roles) {
        return true;
    }

    if !uid.is_empty() && clean(&input.document.requester_id) == uid {
        return true;
    }

    if !uid.is_empty()
        && input
            .document
            .approval_steps
            .iter()
            .any(|step| clean(&step.approver_id) == uid)
    {
        return true;
    }

    let Some(profile) = input.profile.as_ref() else {
        return false;
    };
    let site_id = clean(&input.document.site_id);
    !site_id.is_empty()
        && contains_id(&profile.site_ids, &site_id)
        && (roles.contains(WF_ROLE_SITE_MANAGER) || roles.contains(WF_ROLE_HR))
}

pub fn can_edit_document(input: &WorkflowDocumentPermissionInput) -> bool {
    if !workflow_permission_document_legal_scope_allowed(
        &input.principal,
        &input.document,
        &input.tenant_id,
    ) {
        return false;
    }

    let status = clean(&input.document.status);
    if status == DOC_STATUS_CLOSED || status == DOC_STATUS_APPROVED {
        return false;
    }

    let uid = clean(&input.principal.user_id);
    if uid.is_empty() || clean(&input.document.requester_id) != uid {
        return false;
    }

    status == DOC_STATUS_DRAFT || status == DOC_STATUS_REQUESTED_CHANGES
}

pub fn can_submit_document(input: &WorkflowDocumentPermissionInput) -> bool {
    can_edit_document(input)
}

pub fn can_approve_document(input: &WorkflowDocumentPermissionInput) -> bool {
    if !workflow_permission_document_legal_scope_allowed(
        &input.principal,
        &input.document,
        &input.tenant_id,
    ) {
        return false;
    }

    let status = clean(&input.document.status);
    if status != DOC_STATUS_SUBMITTED && status != DOC_STATUS_IN_REVIEW {
        return false;
    }

    let Some(current) = input
        .document
        .approval_steps
        .iter()
        .find(|step| clean(&step.status) == STEP_PENDING)
    else {
        return false;
    };

    let uid = clean(&input.principal.user_id);
    if !uid.is_empty() && clean(&current.approver_id) == uid {
        return true;
    }

    let roles = workflow_roles(&input.principal, input.profile.as_ref());
    input.can_approve_workflow && has_admin_view_role(&roles)
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

pub fn can_administer_business_trip_lifecycle(
    principal: &BusinessTripPrincipal,
    profile: Option<&BusinessTripProfile>,
) -> bool {
    let roles = workflow_roles(principal, profile);
    has_admin_view_role(&roles)
}

pub fn can_view_site_report(
    principal: &BusinessTripPrincipal,
    profile: Option<&BusinessTripProfile>,
    site_id: &str,
) -> bool {
    let roles = workflow_roles(principal, profile);
    if has_admin_view_role(&roles) {
        return true;
    }

    let Some(profile) = profile else {
        return false;
    };
    contains_id(&profile.site_ids, &clean(site_id))
}

pub fn can_close_month(
    principal: &BusinessTripPrincipal,
    profile: Option<&BusinessTripProfile>,
    site_id: &str,
) -> bool {
    let roles = workflow_roles(principal, profile);
    if roles.contains(WF_ROLE_ADMIN) || roles.contains(WF_ROLE_FINANCE) {
        return can_view_site_report(principal, profile, site_id);
    }
    roles.contains(WF_ROLE_SITE_MANAGER) && can_view_site_report(principal, profile, site_id)
}

pub fn can_manage_execution_task(
    principal: &BusinessTripPrincipal,
    profile: Option<&BusinessTripProfile>,
    executor_id: &str,
) -> bool {
    let roles = workflow_roles(principal, profile);
    if roles.contains(WF_ROLE_ADMIN) {
        return true;
    }

    clean(&principal.user_id) == clean(executor_id)
}

pub fn can_run_business_trip_overdue_evaluator(
    principal: &BusinessTripPrincipal,
    profile: Option<&BusinessTripProfile>,
) -> bool {
    let roles = workflow_roles(principal, profile);
    has_admin_view_role(&roles)
        || roles.contains(WF_ROLE_SITE_MANAGER)
        || roles.contains(WF_ROLE_DEPT_MANAGER)
        || roles.contains(WF_ROLE_HR)
}

pub fn can_evaluate_business_trip_overdue(input: &BusinessTripPermissionInput) -> bool {
    if !is_business_trip_legal_scope_allowed(&input.principal, &input.trip, &input.tenant_id) {
        return false;
    }

    let roles = workflow_roles(&input.principal, input.profile.as_ref());
    if has_admin_view_role(&roles) {
        return true;
    }

    let Some(profile) = input.profile.as_ref() else {
        return false;
    };

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

    !dept_id.is_empty()
        && contains_id(allowed_departments, &dept_id)
        && (roles.contains(WF_ROLE_DEPT_MANAGER)
            || roles.contains(WF_ROLE_SITE_MANAGER)
            || roles.contains(WF_ROLE_HR))
}

fn has_admin_view_role(roles: &BTreeSet<String>) -> bool {
    roles.contains(WF_ROLE_ADMIN)
        || roles.contains(WF_ROLE_EXECUTIVE)
        || roles.contains(WF_ROLE_FINANCE)
}

fn workflow_permission_document_legal_scope_allowed(
    principal: &BusinessTripPrincipal,
    document: &WorkflowPermissionDocument,
    tenant_id: &str,
) -> bool {
    is_business_trip_document_legal_scope_allowed(
        principal,
        &BusinessTripPermissionDocument {
            document_type: document.document_type.clone(),
            origin_tenant_id: document.origin_tenant_id.clone(),
            legal_tenant_id: document.legal_tenant_id.clone(),
            legal_entity_id: document.legal_entity_id.clone(),
            content_trip_id: document.content_trip_id.clone(),
            content_origin_tenant_id: document.content_origin_tenant_id.clone(),
            content_legal_tenant_id: document.content_legal_tenant_id.clone(),
            content_legal_entity_id: document.content_legal_entity_id.clone(),
        },
        tenant_id,
    )
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

    fn document(document_type: &str) -> BusinessTripPermissionDocument {
        BusinessTripPermissionDocument {
            document_type: document_type.to_string(),
            ..BusinessTripPermissionDocument::default()
        }
    }

    #[test]
    fn site_report_visibility_and_month_close_match_python_roles() {
        assert!(can_view_site_report(
            &principal("admin-1", "tenant-a", "admin"),
            None,
            "site-1"
        ));
        assert!(can_close_month(
            &principal("finance-1", "tenant-a", "finance"),
            None,
            "site-1"
        ));

        let mut site_manager = profile(&["site_manager"]);
        site_manager.site_ids = vec!["site-1".to_string()];
        assert!(can_view_site_report(
            &principal("site-manager-1", "tenant-a", "staff"),
            Some(&site_manager),
            "site-1"
        ));
        assert!(can_close_month(
            &principal("site-manager-1", "tenant-a", "staff"),
            Some(&site_manager),
            "site-1"
        ));
        assert!(!can_view_site_report(
            &principal("site-manager-1", "tenant-a", "staff"),
            Some(&site_manager),
            "site-2"
        ));

        let mut hr_profile = profile(&["hr"]);
        hr_profile.site_ids = vec!["site-1".to_string()];
        assert!(can_view_site_report(
            &principal("hr-1", "tenant-a", "staff"),
            Some(&hr_profile),
            "site-1"
        ));
        assert!(!can_close_month(
            &principal("hr-1", "tenant-a", "staff"),
            Some(&hr_profile),
            "site-1"
        ));
    }

    #[test]
    fn execution_task_management_matches_python_assignment_rule() {
        assert!(can_manage_execution_task(
            &principal("admin-1", "tenant-a", "staff"),
            Some(&profile(&["admin"])),
            "someone-else"
        ));
        assert!(can_manage_execution_task(
            &principal("executor-1", "tenant-a", "staff"),
            None,
            "executor-1"
        ));
        assert!(!can_manage_execution_task(
            &principal("executor-role-only", "tenant-a", "staff"),
            Some(&profile(&["executor"])),
            "other-executor"
        ));
    }

    #[test]
    fn business_trip_document_relatedness_matches_python_shape() {
        let mut request_document = document(DOC_TYPE_BUSINESS_TRIP_REQUEST);
        assert!(is_business_trip_related_document(&request_document));

        request_document.document_type = "GENERAL".to_string();
        request_document.content_trip_id = "trip-1".to_string();
        assert!(is_business_trip_related_document(&request_document));

        let unrelated = document("GENERAL");
        assert!(!is_business_trip_related_document(&unrelated));
    }

    #[test]
    fn business_trip_document_legal_scope_matches_python_boundary() {
        let mut unrelated = document("GENERAL");
        unrelated.origin_tenant_id = "tenant-a".to_string();
        assert!(is_business_trip_document_legal_scope_allowed(
            &principal("sibling-admin", "tenant-b", "admin"),
            &unrelated,
            "workflow-root"
        ));

        let mut related = document(DOC_TYPE_BUSINESS_TRIP_REQUEST);
        related.origin_tenant_id = "tenant-a".to_string();
        assert!(is_business_trip_document_legal_scope_allowed(
            &principal("hq-admin", "workflow-root", "admin"),
            &related,
            "workflow-root"
        ));
        assert!(is_business_trip_document_legal_scope_allowed(
            &principal("tenant-admin", "tenant-a", "admin"),
            &related,
            "workflow-root"
        ));
        assert!(is_business_trip_document_legal_scope_allowed(
            &principal("legacy-session", "", "staff"),
            &related,
            "workflow-root"
        ));
        assert!(!is_business_trip_document_legal_scope_allowed(
            &principal("sibling-admin", "tenant-b", "admin"),
            &related,
            "workflow-root"
        ));

        let mut payload_scoped = document("GENERAL");
        payload_scoped.content_trip_id = "trip-2".to_string();
        payload_scoped.content_legal_tenant_id = "tenant-c".to_string();
        assert!(is_business_trip_document_legal_scope_allowed(
            &principal("tenant-c-user", "tenant-c", "staff"),
            &payload_scoped,
            "workflow-root"
        ));
        assert!(!is_business_trip_document_legal_scope_allowed(
            &principal("tenant-a-user", "tenant-a", "staff"),
            &payload_scoped,
            "workflow-root"
        ));
    }

    #[test]
    fn administration_and_overdue_runner_authority_match_python_roles() {
        assert!(can_administer_business_trip_lifecycle(
            &principal("admin-1", "tenant-a", "staff"),
            Some(&profile(&["admin"]))
        ));
        assert!(!can_administer_business_trip_lifecycle(
            &principal("site-manager-1", "tenant-a", "staff"),
            Some(&profile(&["site_manager"]))
        ));

        assert!(can_run_business_trip_overdue_evaluator(
            &principal("finance-1", "tenant-a", "staff"),
            Some(&profile(&["finance"]))
        ));
        assert!(can_run_business_trip_overdue_evaluator(
            &principal("site-manager-1", "tenant-a", "staff"),
            Some(&profile(&["site_manager"]))
        ));
        assert!(can_run_business_trip_overdue_evaluator(
            &principal("dept-manager-1", "tenant-a", "staff"),
            Some(&profile(&["department_manager"]))
        ));
        assert!(can_run_business_trip_overdue_evaluator(
            &principal("hr-1", "tenant-a", "staff"),
            Some(&profile(&["hr"]))
        ));
        assert!(!can_run_business_trip_overdue_evaluator(
            &principal("viewer-1", "tenant-a", "staff"),
            Some(&profile(&["viewer"]))
        ));
        assert!(!can_run_business_trip_overdue_evaluator(
            &principal("approver-1", "tenant-a", "staff"),
            Some(&profile(&["approver"]))
        ));
    }

    #[test]
    fn overdue_evaluation_is_scoped_and_excludes_direct_travelers() {
        let admin_input = input("admin-1", "tenant-a", "staff", Some(profile(&["admin"])));
        assert!(can_evaluate_business_trip_overdue(&admin_input));

        let mut site_manager = profile(&["site_manager"]);
        site_manager.site_ids = vec!["site-1".to_string()];
        let site_input = input("site-manager-1", "tenant-a", "staff", Some(site_manager));
        assert!(can_evaluate_business_trip_overdue(&site_input));

        let mut dept_manager = profile(&["department_manager"]);
        dept_manager.department_ids = vec!["dept-1".to_string()];
        let dept_input = input("dept-manager-1", "tenant-a", "staff", Some(dept_manager));
        assert!(can_evaluate_business_trip_overdue(&dept_input));

        let direct_requester = input("requester-1", "tenant-a", "staff", None);
        assert!(can_view_business_trip_lifecycle(&direct_requester));
        assert!(!can_evaluate_business_trip_overdue(&direct_requester));

        let scoped_viewer = {
            let mut profile = profile(&["viewer"]);
            profile.viewer_site_ids = vec!["site-1".to_string()];
            input("viewer-1", "tenant-a", "staff", Some(profile))
        };
        assert!(can_view_business_trip_lifecycle(&scoped_viewer));
        assert!(!can_evaluate_business_trip_overdue(&scoped_viewer));

        let mut sibling_admin = input("admin-1", "tenant-b", "staff", Some(profile(&["admin"])));
        sibling_admin.trip.tenant_id = "workflow-root".to_string();
        sibling_admin.trip.origin_tenant_id = "tenant-a".to_string();
        sibling_admin.tenant_id = "workflow-root".to_string();
        assert!(!can_evaluate_business_trip_overdue(&sibling_admin));
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

    #[test]
    fn document_view_edit_submit_permissions_match_python_boundary() {
        let mut site_manager = profile(&["site_manager"]);
        site_manager.site_ids = vec!["site-1".to_string()];

        let document = WorkflowPermissionDocument {
            document_type: DOC_TYPE_BUSINESS_TRIP_REQUEST.to_string(),
            origin_tenant_id: "tenant-a".to_string(),
            requester_id: "requester-1".to_string(),
            site_id: "site-1".to_string(),
            status: DOC_STATUS_DRAFT.to_string(),
            approval_steps: vec![WorkflowApprovalStep {
                approver_id: "approver-1".to_string(),
                status: STEP_PENDING.to_string(),
            }],
            ..WorkflowPermissionDocument::default()
        };

        let requester = WorkflowDocumentPermissionInput {
            principal: principal("requester-1", "tenant-a", "staff"),
            profile: None,
            document: document.clone(),
            tenant_id: "tenant-a".to_string(),
            can_approve_workflow: false,
        };
        assert!(can_view_document(&requester));
        assert!(can_edit_document(&requester));
        assert!(can_submit_document(&requester));

        let site_scoped_viewer = WorkflowDocumentPermissionInput {
            principal: principal("site-manager-1", "tenant-a", "staff"),
            profile: Some(site_manager),
            document: document.clone(),
            tenant_id: "tenant-a".to_string(),
            can_approve_workflow: false,
        };
        assert!(can_view_document(&site_scoped_viewer));
        assert!(!can_edit_document(&site_scoped_viewer));
        assert!(!can_submit_document(&site_scoped_viewer));

        let mut terminal = requester.clone();
        terminal.document.status = DOC_STATUS_APPROVED.to_string();
        assert!(!can_edit_document(&terminal));
        assert!(!can_submit_document(&terminal));

        let blank_principal = WorkflowDocumentPermissionInput {
            principal: principal("", "tenant-a", "staff"),
            profile: None,
            document: WorkflowPermissionDocument {
                document_type: DOC_TYPE_BUSINESS_TRIP_REQUEST.to_string(),
                origin_tenant_id: "tenant-a".to_string(),
                status: DOC_STATUS_DRAFT.to_string(),
                ..WorkflowPermissionDocument::default()
            },
            tenant_id: "tenant-a".to_string(),
            can_approve_workflow: false,
        };
        assert!(!can_view_document(&blank_principal));
        assert!(!can_edit_document(&blank_principal));
        assert!(!can_submit_document(&blank_principal));
    }

    #[test]
    fn document_approval_requires_current_pending_step_or_supplied_org_override() {
        let document = WorkflowPermissionDocument {
            document_type: DOC_TYPE_BUSINESS_TRIP_REQUEST.to_string(),
            origin_tenant_id: "tenant-a".to_string(),
            requester_id: "requester-1".to_string(),
            status: DOC_STATUS_SUBMITTED.to_string(),
            approval_steps: vec![
                WorkflowApprovalStep {
                    approver_id: "already-approved".to_string(),
                    status: STEP_APPROVED.to_string(),
                },
                WorkflowApprovalStep {
                    approver_id: "current-approver".to_string(),
                    status: STEP_PENDING.to_string(),
                },
            ],
            ..WorkflowPermissionDocument::default()
        };

        let current_approver = WorkflowDocumentPermissionInput {
            principal: principal("current-approver", "tenant-a", "staff"),
            profile: Some(profile(&["approver"])),
            document: document.clone(),
            tenant_id: "tenant-a".to_string(),
            can_approve_workflow: false,
        };
        assert!(can_view_document(&current_approver));
        assert!(can_approve_document(&current_approver));

        let prior_step_approver = WorkflowDocumentPermissionInput {
            principal: principal("already-approved", "tenant-a", "staff"),
            profile: Some(profile(&["approver"])),
            document: document.clone(),
            tenant_id: "tenant-a".to_string(),
            can_approve_workflow: false,
        };
        assert!(can_view_document(&prior_step_approver));
        assert!(!can_approve_document(&prior_step_approver));

        let org_override = WorkflowDocumentPermissionInput {
            principal: principal("finance-1", "tenant-a", "staff"),
            profile: Some(profile(&["finance"])),
            document: document.clone(),
            tenant_id: "tenant-a".to_string(),
            can_approve_workflow: true,
        };
        assert!(can_approve_document(&org_override));

        let scoped_manager_without_admin_authority = WorkflowDocumentPermissionInput {
            principal: principal("site-manager-1", "tenant-a", "staff"),
            profile: Some(profile(&["site_manager"])),
            document,
            tenant_id: "tenant-a".to_string(),
            can_approve_workflow: true,
        };
        assert!(!can_approve_document(
            &scoped_manager_without_admin_authority
        ));
    }
}
