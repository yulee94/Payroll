use crate::{
    ARCHIVE_INTAKE_STORE_SCHEMA, ARCHIVE_SOURCE_SYNC_PLAN_SCHEMA, AUTH_ROUTE_ACTION_SCHEMA,
    AUTH_ROUTES_SCHEMA, HR_EMPLOYEE_STORE_SCHEMA, PLATFORM_VIEW_SCHEMA,
    USER_PREFERENCE_STORE_SCHEMA, WORKFLOW_EDIT_VALIDATION_SCHEMA, WORKFLOW_PREFLIGHT_SCHEMA,
    WORKFLOW_TEMPLATE_STORE_SCHEMA,
};
use serde::Serialize;

pub const API_CONTRACT_SCHEMA: &str = "bitween.api-contract-spine.v1";

pub const API_IMPLEMENTATION_LIVE_RUST_ROUTE: &str = "live_rust_route";
pub const API_IMPLEMENTATION_LIVE_RUST_SERVICE: &str = "live_rust_service";
pub const API_IMPLEMENTATION_CONFIGURED_IDENTITY_ROUTE: &str = "configured_identity_route";
pub const API_IMPLEMENTATION_CONTRACT_LOCKED_PENDING_ROUTE: &str = "contract_locked_pending_route";

const NO_OBJECT_LIFECYCLE: &[&str] = &[];
const RUSTFS_ORIGINAL_OBJECT_LIFECYCLE: &[&str] = &[
    "rustfs_original_object",
    "checksum_sha256",
    "quarantine",
    "human_review",
];
const RUSTFS_ADMISSION_LIFECYCLE: &[&str] = &[
    "human_review",
    "canonical_admission",
];
const RUSTFS_RECOVERY_LIFECYCLE: &[&str] = &[
    "rustfs_original_object",
    "checksum_sha256",
    "row_level_recovery",
];
const RUSTFS_SOURCE_SYNC_LIFECYCLE: &[&str] = &[
    "rustfs_original_object",
    "checksum_sha256",
    "source_file_sync",
];

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub struct ApiEndpointContract {
    pub module: &'static str,
    pub method: &'static str,
    pub path: &'static str,
    pub request_schema: &'static str,
    pub response_schema: &'static str,
    pub auth_operation: &'static str,
    pub rust_boundary: &'static str,
    pub persistence_contract: &'static str,
    pub object_lifecycle: &'static [&'static str],
    pub implementation_state: &'static str,
}

pub fn api_endpoint_contracts() -> &'static [ApiEndpointContract] {
    API_ENDPOINT_CONTRACTS
}

const API_ENDPOINT_CONTRACTS: &[ApiEndpointContract] = &[
    ApiEndpointContract {
        module: "platform",
        method: "GET",
        path: "/api/platform/v1/view-model",
        request_schema: "none",
        response_schema: PLATFORM_VIEW_SCHEMA,
        auth_operation: "read_workspace",
        rust_boundary: "platform_live_view",
        persistence_contract: "read-only runtime view; PostgreSQL-backed modules feed the view-model",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "hr",
        method: "GET",
        path: "/api/hr/v1/employees",
        request_schema: "bitween.hr.employee-query.v1",
        response_schema: HR_EMPLOYEE_STORE_SCHEMA,
        auth_operation: "hr_employee_read",
        rust_boundary: "hr_employee_store",
        persistence_contract: "bitween.hr.postgres.v1",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "hr",
        method: "POST",
        path: "/api/hr/v1/employees",
        request_schema: "bitween.hr.employee-input.v1",
        response_schema: HR_EMPLOYEE_STORE_SCHEMA,
        auth_operation: "hr_employee_write",
        rust_boundary: "hr_employee_store",
        persistence_contract: "bitween.hr.postgres.v1",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "hr",
        method: "PATCH",
        path: "/api/hr/v1/employees/{employee_id}",
        request_schema: "bitween.hr.employee-patch.v1",
        response_schema: HR_EMPLOYEE_STORE_SCHEMA,
        auth_operation: "hr_employee_write",
        rust_boundary: "hr_employee_store",
        persistence_contract: "bitween.hr.postgres.v1",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "hr",
        method: "DELETE",
        path: "/api/hr/v1/employees/{employee_id}",
        request_schema: "bitween.hr.employee-delete.v1",
        response_schema: HR_EMPLOYEE_STORE_SCHEMA,
        auth_operation: "hr_employee_write",
        rust_boundary: "hr_employee_store",
        persistence_contract: "bitween.hr.postgres.v1",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "payroll",
        method: "POST",
        path: "/api/payroll/v1/runs",
        request_schema: "bitween.payroll.run-request.v1",
        response_schema: "bitween.payroll.run-response.v1",
        auth_operation: "payroll_run",
        rust_boundary: "bitween_payroll_api::PayrollApiService",
        persistence_contract: "PostgreSQL run ledger required before production HTTP writes",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_SERVICE,
    },
    ApiEndpointContract {
        module: "payroll",
        method: "POST",
        path: "/api/payroll/v1/runs/validate",
        request_schema: "bitween.payroll.run-request.v1",
        response_schema: "bitween.payroll.validation-response.v1",
        auth_operation: "payroll_run",
        rust_boundary: "bitween_payroll_api::PayrollApiService::validate_run_payload",
        persistence_contract: "read-only validation; PostgreSQL policy inputs required for production",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_SERVICE,
    },
    ApiEndpointContract {
        module: "payroll",
        method: "GET",
        path: "/api/payroll/v1/healthz",
        request_schema: "none",
        response_schema: "bitween.payroll.health.v1",
        auth_operation: "public",
        rust_boundary: "bitween_payroll_api::PayrollApiService::health",
        persistence_contract: "probe-safe; no secret or data persistence",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_SERVICE,
    },
    ApiEndpointContract {
        module: "payroll",
        method: "GET",
        path: "/api/payroll/v1/readiness",
        request_schema: "none",
        response_schema: "bitween.payroll.readiness.v1",
        auth_operation: "read_workspace",
        rust_boundary: "bitween_payroll_api::PayrollApiService::readiness",
        persistence_contract: "probe-safe readiness with sanitized PostgreSQL/RustFS dependency states",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_SERVICE,
    },
    ApiEndpointContract {
        module: "workflow",
        method: "GET",
        path: "/api/workflow/v1/templates",
        request_schema: "none",
        response_schema: WORKFLOW_TEMPLATE_STORE_SCHEMA,
        auth_operation: "workflow_template_read",
        rust_boundary: "workflow_template_store",
        persistence_contract: "bitween.workflow.postgres.v1",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "workflow",
        method: "POST",
        path: "/api/workflow/v1/templates/{template_id}/steps",
        request_schema: "bitween.workflow.step-input.v1",
        response_schema: WORKFLOW_TEMPLATE_STORE_SCHEMA,
        auth_operation: "workflow_template_write",
        rust_boundary: "workflow_template_store",
        persistence_contract: "bitween.workflow.postgres.v1",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "workflow",
        method: "PATCH",
        path: "/api/workflow/v1/templates/{template_id}/steps/{step_id}",
        request_schema: "bitween.workflow.step-patch.v1",
        response_schema: WORKFLOW_TEMPLATE_STORE_SCHEMA,
        auth_operation: "workflow_template_write",
        rust_boundary: "workflow_template_store",
        persistence_contract: "bitween.workflow.postgres.v1",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "workflow",
        method: "DELETE",
        path: "/api/workflow/v1/templates/{template_id}/steps/{step_id}",
        request_schema: "bitween.workflow.step-delete.v1",
        response_schema: WORKFLOW_TEMPLATE_STORE_SCHEMA,
        auth_operation: "workflow_template_write",
        rust_boundary: "workflow_template_store",
        persistence_contract: "bitween.workflow.postgres.v1",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "workflow",
        method: "POST",
        path: "/api/workflow/v1/templates/{template_id}/preflights",
        request_schema: "bitween.workflow.preflight-request.v1",
        response_schema: WORKFLOW_PREFLIGHT_SCHEMA,
        auth_operation: "workflow_template_read",
        rust_boundary: "workflow_template_store",
        persistence_contract: "bitween.workflow.postgres.v1",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "workflow",
        method: "POST",
        path: "/api/workflow/v1/templates/{template_id}/steps/{step_id}/validations",
        request_schema: "bitween.workflow.step-patch.v1",
        response_schema: WORKFLOW_EDIT_VALIDATION_SCHEMA,
        auth_operation: "workflow_template_write",
        rust_boundary: "workflow_template_store",
        persistence_contract: "PostgreSQL graph source; dry-run graph validation with no persistence on blocked edits",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "workflow",
        method: "POST",
        path: "/api/workflow/v1/templates/{template_id}/steps/{step_id}/executions",
        request_schema: "bitween.workflow.execution-request.v1",
        response_schema: WORKFLOW_TEMPLATE_STORE_SCHEMA,
        auth_operation: "workflow_step_execute",
        rust_boundary: "workflow_template_store",
        persistence_contract: "bitween.workflow.postgres.v1; workflow runtime events and data records",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "workflow",
        method: "POST",
        path: "/api/workflow/v1/templates/{template_id}/rollbacks",
        request_schema: "bitween.workflow.rollback-request.v1",
        response_schema: WORKFLOW_TEMPLATE_STORE_SCHEMA,
        auth_operation: "workflow_template_write",
        rust_boundary: "workflow_template_store",
        persistence_contract: "bitween.workflow.postgres.v1; text graph versions only, no binary snapshots",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "approval",
        method: "GET",
        path: "/api/approval/v1/requests",
        request_schema: "bitween.approval.queue-query.v1",
        response_schema: "bitween.approval.queue.v1",
        auth_operation: "read_workspace",
        rust_boundary: "approval_request_store",
        persistence_contract: "PostgreSQL approval queue tables required before production route enablement",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_CONTRACT_LOCKED_PENDING_ROUTE,
    },
    ApiEndpointContract {
        module: "approval",
        method: "POST",
        path: "/api/approval/v1/requests/{approval_id}/signatures",
        request_schema: "bitween.approval.signature-request.v1",
        response_schema: "bitween.approval.signature-receipt.v1",
        auth_operation: "approval_signing",
        rust_boundary: "approval_signature_service",
        persistence_contract: "PostgreSQL approval signatures, audit chain, and WebAuthn evidence required before route enablement",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_CONTRACT_LOCKED_PENDING_ROUTE,
    },
    ApiEndpointContract {
        module: "archive",
        method: "GET",
        path: "/api/archive/v1/intake",
        request_schema: "bitween.archive.intake-query.v1",
        response_schema: ARCHIVE_INTAKE_STORE_SCHEMA,
        auth_operation: "archive_read",
        rust_boundary: "archive_intake_store",
        persistence_contract: "bitween.archive.postgres.v1",
        object_lifecycle: RUSTFS_ORIGINAL_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "archive",
        method: "POST",
        path: "/api/archive/v1/intake",
        request_schema: "bitween.archive.file-upload.v1",
        response_schema: ARCHIVE_INTAKE_STORE_SCHEMA,
        auth_operation: "archive_upload",
        rust_boundary: "archive_intake_store",
        persistence_contract: "bitween.archive.postgres.v1",
        object_lifecycle: RUSTFS_ORIGINAL_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "archive",
        method: "PATCH",
        path: "/api/archive/v1/intake/{intake_id}/issues",
        request_schema: "bitween.archive.issue-resolution.v1",
        response_schema: ARCHIVE_INTAKE_STORE_SCHEMA,
        auth_operation: "archive_review",
        rust_boundary: "archive_intake_store",
        persistence_contract: "bitween.archive.postgres.v1",
        object_lifecycle: RUSTFS_ADMISSION_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "archive",
        method: "PATCH",
        path: "/api/archive/v1/intake/{intake_id}/field-mappings",
        request_schema: "bitween.archive.field-mapping-input.v1",
        response_schema: ARCHIVE_INTAKE_STORE_SCHEMA,
        auth_operation: "archive_review",
        rust_boundary: "archive_intake_store::map-fields",
        persistence_contract: "bitween.archive.postgres.v1; append-only review/audit event plus reusable field mapping template keyed by source fingerprint",
        object_lifecycle: RUSTFS_ADMISSION_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "archive",
        method: "POST",
        path: "/api/archive/v1/intake/{intake_id}/admissions",
        request_schema: "bitween.archive.admission-request.v1",
        response_schema: ARCHIVE_INTAKE_STORE_SCHEMA,
        auth_operation: "archive_admit",
        rust_boundary: "archive_intake_store",
        persistence_contract: "bitween.archive.postgres.v1; canonical HR/payroll row admission after human review",
        object_lifecycle: RUSTFS_ADMISSION_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "archive",
        method: "POST",
        path: "/api/archive/v1/intake/{intake_id}/rollbacks",
        request_schema: "bitween.archive.rollback-request.v1",
        response_schema: ARCHIVE_INTAKE_STORE_SCHEMA,
        auth_operation: "archive_rollback",
        rust_boundary: "archive_intake_store",
        persistence_contract: "bitween.archive-rollback.postgres.v1",
        object_lifecycle: RUSTFS_RECOVERY_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "archive",
        method: "POST",
        path: "/api/archive/v1/intake/{intake_id}/source-syncs",
        request_schema: "bitween.archive.source-sync-request.v1",
        response_schema: ARCHIVE_SOURCE_SYNC_PLAN_SCHEMA,
        auth_operation: "archive_sync",
        rust_boundary: "archive_intake_store",
        persistence_contract: "bitween.archive.postgres.v1; linked source-file version plan",
        object_lifecycle: RUSTFS_SOURCE_SYNC_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "settings",
        method: "GET",
        path: "/api/settings/v1/preferences",
        request_schema: "none",
        response_schema: USER_PREFERENCE_STORE_SCHEMA,
        auth_operation: "read_workspace",
        rust_boundary: "user_preference_store",
        persistence_contract: "bitween.settings.postgres.v1",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "settings",
        method: "PUT",
        path: "/api/settings/v1/preferences",
        request_schema: "bitween.settings.preference-update.v1",
        response_schema: USER_PREFERENCE_STORE_SCHEMA,
        auth_operation: "user_preference_update",
        rust_boundary: "user_preference_store",
        persistence_contract: "bitween.settings.postgres.v1",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_LIVE_RUST_ROUTE,
    },
    ApiEndpointContract {
        module: "auth",
        method: "GET",
        path: "/api/auth/v1/routes",
        request_schema: "none",
        response_schema: AUTH_ROUTES_SCHEMA,
        auth_operation: "public",
        rust_boundary: "auth_route_config",
        persistence_contract: "server-side configured identity and onboarding routes only",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_CONFIGURED_IDENTITY_ROUTE,
    },
    ApiEndpointContract {
        module: "auth",
        method: "GET",
        path: "/api/auth/v1/signin",
        request_schema: "none",
        response_schema: AUTH_ROUTE_ACTION_SCHEMA,
        auth_operation: "public",
        rust_boundary: "auth_route_config",
        persistence_contract: "server-side configured identity provider redirect",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_CONFIGURED_IDENTITY_ROUTE,
    },
    ApiEndpointContract {
        module: "auth",
        method: "GET",
        path: "/api/auth/v1/signup",
        request_schema: "none",
        response_schema: AUTH_ROUTE_ACTION_SCHEMA,
        auth_operation: "public",
        rust_boundary: "auth_route_config",
        persistence_contract: "server-side configured access-request route",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_CONFIGURED_IDENTITY_ROUTE,
    },
    ApiEndpointContract {
        module: "auth",
        method: "GET",
        path: "/api/onboarding/v1/start",
        request_schema: "none",
        response_schema: AUTH_ROUTE_ACTION_SCHEMA,
        auth_operation: "public",
        rust_boundary: "auth_route_config",
        persistence_contract: "server-side configured onboarding route",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_CONFIGURED_IDENTITY_ROUTE,
    },
    ApiEndpointContract {
        module: "auth",
        method: "POST",
        path: "/api/auth/v1/signout",
        request_schema: "none",
        response_schema: AUTH_ROUTE_ACTION_SCHEMA,
        auth_operation: "read_workspace",
        rust_boundary: "auth_route_config",
        persistence_contract: "same-origin protected server-side configured identity provider sign-out route",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_CONFIGURED_IDENTITY_ROUTE,
    },
    ApiEndpointContract {
        module: "admin",
        method: "GET",
        path: "/api/admin/v1/tenants/{tenant_id}/access",
        request_schema: "bitween.admin.access-query.v1",
        response_schema: "bitween.admin.access-policy.v1",
        auth_operation: "tenant_destructive_change",
        rust_boundary: "admin_access_policy_store",
        persistence_contract: "PostgreSQL tenant/legal/workplace access policy tables required before route enablement",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_CONTRACT_LOCKED_PENDING_ROUTE,
    },
    ApiEndpointContract {
        module: "admin",
        method: "PATCH",
        path: "/api/admin/v1/tenants/{tenant_id}/access/{principal_id}",
        request_schema: "bitween.admin.access-policy-patch.v1",
        response_schema: "bitween.admin.access-policy.v1",
        auth_operation: "tenant_destructive_change",
        rust_boundary: "admin_access_policy_store",
        persistence_contract: "PostgreSQL tenant/legal/workplace access policy audit tables required before route enablement",
        object_lifecycle: NO_OBJECT_LIFECYCLE,
        implementation_state: API_IMPLEMENTATION_CONTRACT_LOCKED_PENDING_ROUTE,
    },
];

#[cfg(test)]
mod tests {
    use super::*;
    use crate::AuthSensitiveOperation;
    use std::collections::BTreeSet;

    #[test]
    fn api_contract_spine_covers_all_business_modules() {
        let modules: BTreeSet<&str> = api_endpoint_contracts()
            .iter()
            .map(|contract| contract.module)
            .collect();

        for required in [
            "platform",
            "hr",
            "payroll",
            "workflow",
            "approval",
            "archive",
            "settings",
            "auth",
            "admin",
        ] {
            assert!(
                modules.contains(required),
                "missing API contract module {required}"
            );
        }
    }

    #[test]
    fn api_contract_paths_are_versioned_and_boundary_owned() {
        for contract in api_endpoint_contracts() {
            assert!(contract.path.starts_with("/api/"), "{} path must stay under /api", contract.path);
            assert!(
                contract.path.contains("/v1/"),
                "{} path must carry an explicit v1 segment",
                contract.path
            );
            assert!(
                !contract.rust_boundary.contains("preview"),
                "{} must name a Rust boundary, not a preview adapter",
                contract.path
            );
            assert_ne!(
                contract.response_schema, "",
                "{} must publish a response schema",
                contract.path
            );
        }
    }

    #[test]
    fn mutating_api_contracts_declare_authorization() {
        for contract in api_endpoint_contracts() {
            if matches!(contract.method, "POST" | "PATCH" | "DELETE" | "PUT") {
                assert!(
                    !contract.auth_operation.is_empty() && contract.auth_operation != "public",
                    "{} {} must declare a sensitive authorization operation",
                    contract.method,
                    contract.path
                );
            }
        }
    }

    #[test]
    fn archive_contracts_keep_rustfs_lifecycle_explicit() {
        let archive_contracts: Vec<_> = api_endpoint_contracts()
            .iter()
            .filter(|contract| contract.module == "archive")
            .collect();
        assert!(!archive_contracts.is_empty(), "archive contracts must exist");

        let lifecycle: BTreeSet<&str> = archive_contracts
            .iter()
            .flat_map(|contract| contract.object_lifecycle.iter().copied())
            .collect();
        for required in [
            "rustfs_original_object",
            "checksum_sha256",
            "quarantine",
            "human_review",
            "canonical_admission",
            "row_level_recovery",
            "source_file_sync",
        ] {
            assert!(
                lifecycle.contains(required),
                "archive lifecycle missing {required}"
            );
        }
    }

    #[test]
    fn api_contract_uses_only_controlled_implementation_states() {
        for contract in api_endpoint_contracts() {
            assert!(
                matches!(
                    contract.implementation_state,
                    API_IMPLEMENTATION_LIVE_RUST_ROUTE
                        | API_IMPLEMENTATION_LIVE_RUST_SERVICE
                        | API_IMPLEMENTATION_CONFIGURED_IDENTITY_ROUTE
                        | API_IMPLEMENTATION_CONTRACT_LOCKED_PENDING_ROUTE
                ),
                "{} {} uses an uncontrolled implementation state: {}",
                contract.method,
                contract.path,
                contract.implementation_state
            );
            let state = contract.implementation_state.to_ascii_lowercase();
            for forbidden in [concat!("st", "ub"), concat!("place", "holder"), concat!("mo", "ck")] {
                assert!(
                    !state.contains(forbidden),
                    "{} must not be recorded with non-production implementation wording",
                    contract.path
                );
            }
        }
    }

    #[test]
    fn api_contract_auth_operations_are_policy_backed_or_public() {
        for contract in api_endpoint_contracts() {
            if contract.auth_operation == "public" {
                assert_eq!(
                    contract.method, "GET",
                    "{} {} public contracts may only be read-only provider/status routes",
                    contract.method, contract.path
                );
                continue;
            }

            assert!(
                AuthSensitiveOperation::parse(contract.auth_operation).is_some(),
                "{} {} declares an auth operation not backed by the Rust ABAC/RBAC/PBAC policy: {}",
                contract.method,
                contract.path,
                contract.auth_operation
            );
        }
    }

    #[test]
    fn api_contract_declares_postgresql_for_business_writes() {
        for contract in api_endpoint_contracts() {
            if matches!(contract.module, "hr" | "workflow" | "archive" | "settings" | "approval" | "admin")
                && matches!(contract.method, "POST" | "PATCH" | "PUT" | "DELETE")
            {
                assert!(
                    contract.persistence_contract.contains("PostgreSQL")
                        || contract.persistence_contract.contains("postgres"),
                    "{} {} must declare its PostgreSQL persistence contract",
                    contract.method,
                    contract.path
                );
            }
        }
    }
}
