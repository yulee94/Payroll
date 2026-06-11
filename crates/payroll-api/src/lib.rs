pub mod access;
pub mod api_contract;
pub mod archive_intake_schema;
pub mod archive_rollback_schema;
pub mod auth_policy;
pub mod auth_session_schema;
pub mod auth_session;
pub mod attendance;
pub mod deductions;
pub mod earnings;
pub mod edi_insurance;
pub mod employment_insurance_65;
pub mod error;
pub mod execution_plan;
pub mod fixed_hours;
pub mod hr_employee_schema;
pub mod invoice_audit;
pub mod platform_view;
pub mod payroll_attendance_schema;
pub mod policy;
pub mod policy_resolution;
pub mod postgres_repository;
pub mod request;
pub mod rls_enforcement_schema;
pub mod response;
pub mod run;
pub mod salary;
pub mod service;
pub mod site_benefits;
pub mod social_insurance;
pub mod user_preference_schema;
pub mod workflow_template_schema;
pub mod workplace_hours;

pub use archive_intake_schema::{
    ARCHIVE_INTAKE_POSTGRES_MIGRATION_NAME, ARCHIVE_INTAKE_POSTGRES_MIGRATION_SQL,
    ARCHIVE_INTAKE_POSTGRES_SCHEMA_VERSION, ARCHIVE_INTAKE_POSTGRES_STAGING_TABLES,
    ARCHIVE_INTAKE_POSTGRES_TABLES, ARCHIVE_INTAKE_STORE_SCHEMA,
    ARCHIVE_SOURCE_SYNC_PLAN_SCHEMA, ArchiveIntakePostgresContract,
    archive_intake_postgres_contract,
};
pub use archive_rollback_schema::{
    ARCHIVE_ROLLBACK_POSTGRES_MIGRATION_NAME, ARCHIVE_ROLLBACK_POSTGRES_MIGRATION_SQL,
    ARCHIVE_ROLLBACK_POSTGRES_SCHEMA_VERSION, ARCHIVE_ROLLBACK_POSTGRES_TABLES,
    ArchiveRollbackPostgresContract, archive_rollback_postgres_contract,
};
pub use auth_policy::{
    AUTH_POLICY_SCHEMA, AUTHZ_POLICY_ENV, AUTHZ_POLICY_ID, AuthAcrLevel, AuthDataClass,
    AuthSensitiveOperation, AuthStepUpDecision, AuthWorkflowState, AuthzDecision, AuthzPolicy,
    AuthzPolicyError, AuthzRequest, OperationPolicy as AuthzOperationPolicy, RolePolicy,
    evaluate_authorization, evaluate_step_up, normalize_role,
};
pub use auth_session::{
    AUTH_OIDC_DISCOVERY_SCHEMA, AUTH_ROUTE_ACTION_SCHEMA, AUTH_ROUTES_SCHEMA,
    AUTH_SESSION_ALLOWED_ALGORITHM, AUTH_SESSION_SCHEMA, AUTH_WEBAUTHN_ASSERTION_SCHEMA,
    AUTH_WEBAUTHN_CHALLENGE_TTL_SECONDS, AuthSessionVerification, AuthSessionVerifierConfig,
    OidcDiscoveryValidation, OidcDiscoveryVerifierConfig, WebAuthnAssertionInput,
    WebAuthnAssertionVerification, WebAuthnAssertionVerifierConfig, validate_oidc_discovery,
    verify_jwt_session, verify_webauthn_assertion,
};
pub use auth_session_schema::{
    AUTH_SESSION_POSTGRES_MIGRATION_NAME, AUTH_SESSION_POSTGRES_MIGRATION_SQL,
    AUTH_SESSION_POSTGRES_SCHEMA_VERSION, AUTH_SESSION_POSTGRES_TABLES,
    AuthSessionPostgresContract, auth_session_event_insert_sql, auth_session_postgres_contract,
    auth_session_revocation_lookup_sql,
};
pub use access::{
    PayrollAccessDecision, PayrollAction, PayrollPermission, PayrollPosition, PayrollPrincipal,
    PayrollRole, authorize_payroll_request,
};
pub use api_contract::{API_CONTRACT_SCHEMA, ApiEndpointContract, api_endpoint_contracts};
pub use attendance::{AttendanceInvoiceRow, AttendanceSourceRecord, aggregate_attendance_records};
pub use deductions::{
    PayrollDeductionInput, PayrollDeductionResult, PayrollIncomeTaxResult, PayrollTaxMethod,
    calculate_payroll_income_tax, finalize_payroll_deductions, lookup_simplified_income_tax,
};
pub use earnings::{
    HOLIDAY_PREMIUM, MEAL_ALLOWANCE_PER_DAY, MEAL_NON_TAXABLE_CAP, NIGHT_PREMIUM, OVERLAP_PREMIUM,
    OVERTIME_PREMIUM, PayrollEarningsBreakdown, PayrollEarningsHours, PayrollEarningsInput,
    PayrollEarningsResult, STANDARD_MONTHLY_HOURS, calculate_ordinary_hourly,
    calculate_overlap_premium, calculate_payroll_earnings, calculate_weekly_holiday_pay,
};
pub use edi_insurance::{
    EdiInsuranceApplication, EdiInsuranceConfig, EdiInsuranceInvoice, EdiInsurancePremiumRecord,
    EdiPremiumSource, apply_edi_premiums_to_invoice,
};
pub use employment_insurance_65::{
    Ei65EligibilityStatus, Ei65PayrollInput, Ei65PayrollResult, Ei65UnknownDefault,
    Ei65VerificationRecord, age_years_from_korean_identity, is_age_65_plus_for_period,
    resolve_ei_65_for_payroll,
};
pub use error::PayrollApiError;
pub use execution_plan::{
    PAYROLL_RUST_NATIVE_EXECUTOR, PayrollExecutionBackend, PayrollExecutionPlan,
    PayrollExecutionStep, PayrollExecutionStepKind, plan_payroll_execution,
};
pub use fixed_hours::{
    FIXED_HOURS_SOURCE_CONTRACT, FIXED_HOURS_SOURCE_TEMPLATE, FixedHoursApplication,
    FixedHoursInvoice, FixedHoursPayType, FixedHoursProfile, PAY_TYPE_HOURLY,
    PAY_TYPE_MONTHLY_SALARY, apply_fixed_hours_to_invoice, fixed_hours_audit_flags,
};
pub use hr_employee_schema::{
    HR_EMPLOYEE_POSTGRES_MIGRATION_NAME, HR_EMPLOYEE_POSTGRES_MIGRATION_SQL,
    HR_EMPLOYEE_POSTGRES_SCHEMA_VERSION, HR_EMPLOYEE_POSTGRES_TABLES, HR_EMPLOYEE_STORE_SCHEMA,
    HrEmployeePostgresContract, hr_employee_postgres_contract,
};
pub use invoice_audit::{
    InvoiceAuditBatchItem, InvoiceAuditBatchResult, InvoiceAuditInvoice, InvoiceAuditRecord,
    InvoiceAuditRow, InvoiceAuditStatus, InvoiceAuditSummary, audit_invoice_batch,
    audit_invoice_row, estimate_break_hours,
};
pub use platform_view::{
    EnterpriseCapabilityTier, EnterpriseMaturityGate, EnterpriseMaturityView,
    PLATFORM_VIEW_ENDPOINT, PLATFORM_VIEW_SCHEMA, PayrollOperationsView, PayrollScopeView,
    PlatformLiveConfig, PlatformLiveView, PlatformNavigationItem, PlatformSession, PlatformSource,
    PlatformWorkItem, ReadinessCardView, build_platform_live_view,
};
pub use payroll_attendance_schema::{
    PAYROLL_ATTENDANCE_POSTGRES_MIGRATION_NAME, PAYROLL_ATTENDANCE_POSTGRES_MIGRATION_SQL,
    PAYROLL_ATTENDANCE_POSTGRES_SCHEMA_VERSION, PAYROLL_ATTENDANCE_POSTGRES_TABLES,
    PayrollAttendancePostgresContract, payroll_attendance_postgres_contract,
};
pub use policy::{
    AttendancePolicy, MissingClockPolicy, OperationPolicy, OperationPolicySnapshot,
    PayrollInputBasis,
};
pub use policy_resolution::{
    OperationPolicySource, PayrollPolicySettings, ResolvedOperationPolicy, resolve_operation_policy,
};
pub use postgres_repository::{
    PostgresClientSession, PostgresConnectionFailure, PostgresDriverConfig,
    PostgresMigration, PostgresMigrationReceipt, PostgresMigrationStatus,
    PostgresRepositoryConfig, PostgresRepositoryStatus, PostgresTenantScope,
    PostgresTlsConnector, PostgresTlsConnectorProfile, PostgresTlsPolicy,
    postgres_migration_insert_sql, postgres_migration_lookup_sql, postgres_migration_registry_sql,
    postgres_repository_status, required_postgres_migrations,
};
pub use request::{
    PayrollInputType, PayrollRunRequest, PayrollScope, parse_payroll_api_request,
    request_id_from_payload,
};
pub use rls_enforcement_schema::{
    RLS_ENFORCEMENT_POSTGRES_FORCED_TABLES, RLS_ENFORCEMENT_POSTGRES_MIGRATION_NAME,
    RLS_ENFORCEMENT_POSTGRES_MIGRATION_SQL, RLS_ENFORCEMENT_POSTGRES_SCHEMA_VERSION,
    RlsEnforcementPostgresContract, rls_enforcement_postgres_contract,
};
pub use response::{
    PayrollApiErrorResponse, PayrollApiResponse, PayrollValidationResponse,
    validate_payroll_api_payload, validate_payroll_api_payload_with_policy_settings,
};
pub use run::{PayrollRunResponse, PayrollRunResult, run_response_from_result};
pub use salary::{
    PayrollSalaryDeductions, PayrollSalaryInput, PayrollSalaryResult, PayrollSalaryTaxMethod,
    calculate_payroll_salary,
};
pub use service::{
    HealthResponse, HealthStatus, PayrollApiService, ReadinessCheck, ReadinessResponse,
    ReadinessState, ServiceConfig,
};
pub use site_benefits::{
    IdentityInsuranceConfig, SiteBenefitsApplication, SiteBenefitsConfig, SiteBenefitsInvoice,
    WorkersDayConfig, apply_site_benefits_to_invoice,
};
pub use social_insurance::{
    EMPLOYMENT_INSURANCE_WORKER_RATE, HEALTH_INSURANCE_RATE, LONG_TERM_CARE_RATIO,
    NATIONAL_PENSION_RATE, PENSION_CEILING, PENSION_FLOOR, SocialInsuranceInput,
    SocialInsuranceResult, calculate_employment_insurance, calculate_social_insurance,
};
pub use user_preference_schema::{
    USER_PREFERENCE_POSTGRES_MIGRATION_NAME, USER_PREFERENCE_POSTGRES_MIGRATION_SQL,
    USER_PREFERENCE_POSTGRES_SCHEMA_VERSION, USER_PREFERENCE_POSTGRES_TABLES,
    USER_PREFERENCE_STORE_SCHEMA,
    UserPreferencePostgresContract, user_preference_postgres_contract,
};
pub use workflow_template_schema::{
    WORKFLOW_EDIT_VALIDATION_SCHEMA, WORKFLOW_PREFLIGHT_SCHEMA, WORKFLOW_TEMPLATE_STORE_SCHEMA,
    WORKFLOW_TEMPLATE_POSTGRES_AUDIT_TABLES, WORKFLOW_TEMPLATE_POSTGRES_GRAPH_TABLES,
    WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_NAME, WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_SQL,
    WORKFLOW_TEMPLATE_POSTGRES_SCHEMA_VERSION, WORKFLOW_TEMPLATE_POSTGRES_TABLES,
    WorkflowTemplatePostgresContract, workflow_template_postgres_contract,
};
pub use workplace_hours::{
    MODE_BASE_OR_FIXED, MODE_FIXED, MODE_INVOICE_BASE, MODE_INVOICE_WORK, MODE_WORK_OR_FIXED,
    WorkplaceHoursInvoice, WorkplaceHoursMode, WorkplaceHoursPolicy,
    WorkplaceMonthlyHoursApplication, WorkplaceMonthlyHoursResolution,
    apply_monthly_hours_to_invoice, resolve_monthly_work_hours,
};

pub const PAYROLL_API_VERSION: &str = "v1";
pub const PAYROLL_API_ENDPOINT: &str = "/api/payroll/v1/runs";
pub const PAYROLL_API_VALIDATE_ENDPOINT: &str = "/api/payroll/v1/runs/validate";
pub const PAYROLL_API_HEALTH_ENDPOINT: &str = "/api/payroll/v1/healthz";
pub const PAYROLL_API_READINESS_ENDPOINT: &str = "/api/payroll/v1/readiness";
