use crate::auth_policy::{
    AUTHZ_POLICY_ID, AuthAcrLevel, AuthSensitiveOperation, AuthWorkflowState, AuthzDecision,
    AuthzPolicy, AuthzRequest, evaluate_authorization, evaluate_step_up,
};
use crate::execution_plan::PAYROLL_RUST_NATIVE_EXECUTOR;
use crate::service::{
    HealthResponse, PayrollApiService, ReadinessCheck, ReadinessResponse, ReadinessState,
    ServiceConfig,
};
use serde::Serialize;
use std::time::{SystemTime, UNIX_EPOCH};

pub const PLATFORM_VIEW_SCHEMA: &str = "bitween.platform.live.v1";
pub const PLATFORM_VIEW_ENDPOINT: &str = "/api/platform/v1/view-model";

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PlatformLiveView {
    pub schema: &'static str,
    pub source: PlatformSource,
    pub session: PlatformSession,
    pub navigation: Vec<PlatformNavigationItem>,
    pub enterprise: EnterpriseMaturityView,
    pub payroll: PayrollOperationsView,
    pub work_queue: Vec<PlatformWorkItem>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PlatformSource {
    pub service: String,
    pub endpoint: &'static str,
    pub backend: &'static str,
    pub executor: &'static str,
    pub generated_at_unix: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PlatformSession {
    pub mode: &'static str,
    pub authenticated: bool,
    pub tenant_id: String,
    pub tenant_name: String,
    pub role: String,
    pub scope_label: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PlatformNavigationItem {
    pub id: &'static str,
    pub label: &'static str,
    pub purpose: &'static str,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EnterpriseMaturityView {
    pub model: &'static str,
    pub summary: String,
    pub gates: Vec<EnterpriseMaturityGate>,
    pub capability_tiers: Vec<EnterpriseCapabilityTier>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EnterpriseMaturityGate {
    pub id: &'static str,
    pub title: &'static str,
    pub status: &'static str,
    pub tone: &'static str,
    pub owner: &'static str,
    pub evidence: String,
    pub next_step: &'static str,
    pub source: &'static str,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EnterpriseCapabilityTier {
    pub id: &'static str,
    pub title: &'static str,
    pub status: &'static str,
    pub tone: &'static str,
    pub artifact: &'static str,
    pub owner: &'static str,
    pub evidence: String,
    pub next_step: &'static str,
    pub source: &'static str,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollOperationsView {
    pub scope: PayrollScopeView,
    pub health: HealthResponse,
    pub readiness: ReadinessResponse,
    pub readiness_cards: Vec<ReadinessCardView>,
    pub workstream: PayrollWorkstreamView,
    pub next_actions: Vec<PlatformWorkItem>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollScopeView {
    pub tenant_id: String,
    pub tenant_name: String,
    pub affiliate: String,
    pub workplace: String,
    pub period: String,
    pub configured: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ReadinessCardView {
    pub id: &'static str,
    pub title: &'static str,
    pub value: String,
    pub detail: String,
    pub tone: &'static str,
    pub source: &'static str,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollWorkstreamView {
    pub period_label: String,
    pub status: &'static str,
    pub tone: &'static str,
    pub current_step_id: &'static str,
    pub steps: Vec<PayrollWorkStepView>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollWorkStepView {
    pub id: &'static str,
    pub status: &'static str,
    pub tone: &'static str,
    pub owner: &'static str,
    pub action: &'static str,
    pub target: &'static str,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PlatformWorkItem {
    pub id: &'static str,
    pub title: &'static str,
    pub owner: &'static str,
    pub status: String,
    pub next_step: &'static str,
    pub target: &'static str,
    pub tone: &'static str,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlatformLiveConfig {
    pub service_config: ServiceConfig,
    pub tenant_id: String,
    pub tenant_name: String,
    pub affiliate: String,
    pub workplace: String,
    pub period: String,
    pub auth_provider_configured: bool,
    pub session_jwt_verified: bool,
    pub session_jwt_issuer: String,
    pub session_jwt_audience: String,
    pub session_jwt_subject: String,
    pub session_jwt_expires_at_unix: u64,
    pub session_webauthn_user_verified: bool,
    pub session_acr_level: String,
    pub session_acr_event_at_unix: u64,
    pub session_actor_role: String,
    pub session_authz_policy_id: String,
    pub session_authorized_tenant_id: String,
    pub session_authorized_legal_entity: String,
    pub session_authorized_workplace: String,
    pub archive_configured: bool,
    pub ontology_projection_configured: bool,
    pub workflow_template_configured: bool,
    pub compliance_pack_configured: bool,
    pub observability_configured: bool,
    pub finops_configured: bool,
    pub import_plan_declared: bool,
    pub support_runbook_configured: bool,
    pub payroll_inputs_closed: bool,
    pub attendance_closed: bool,
    pub deductions_reviewed: bool,
    pub payroll_calculated: bool,
    pub approval_requested: bool,
    pub payout_prepared: bool,
    pub payroll_evidence_archived: bool,
}

impl Default for PlatformLiveConfig {
    fn default() -> Self {
        Self {
            service_config: ServiceConfig::default(),
            tenant_id: String::new(),
            tenant_name: String::new(),
            affiliate: String::new(),
            workplace: String::new(),
            period: String::new(),
            auth_provider_configured: false,
            session_jwt_verified: false,
            session_jwt_issuer: String::new(),
            session_jwt_audience: String::new(),
            session_jwt_subject: String::new(),
            session_jwt_expires_at_unix: 0,
            session_webauthn_user_verified: false,
            session_acr_level: String::new(),
            session_acr_event_at_unix: 0,
            session_actor_role: String::new(),
            session_authz_policy_id: String::new(),
            session_authorized_tenant_id: String::new(),
            session_authorized_legal_entity: String::new(),
            session_authorized_workplace: String::new(),
            archive_configured: false,
            ontology_projection_configured: false,
            workflow_template_configured: false,
            compliance_pack_configured: false,
            observability_configured: false,
            finops_configured: false,
            import_plan_declared: false,
            support_runbook_configured: false,
            payroll_inputs_closed: false,
            attendance_closed: false,
            deductions_reviewed: false,
            payroll_calculated: false,
            approval_requested: false,
            payout_prepared: false,
            payroll_evidence_archived: false,
        }
    }
}

impl PlatformLiveConfig {
    pub fn from_env() -> Self {
        let mut config = Self::default();
        config.service_config.environment =
            env_value("BITWEEN_ENVIRONMENT").unwrap_or_else(|| "local".to_owned());
        config.service_config.build_sha = env_value("BITWEEN_BUILD_SHA").unwrap_or_default();
        config.tenant_id = env_value("BITWEEN_TENANT_ID").unwrap_or_default();
        config.tenant_name = env_value("BITWEEN_TENANT_NAME").unwrap_or_default();
        config.affiliate = env_value("BITWEEN_PAYROLL_AFFILIATE").unwrap_or_default();
        config.workplace = env_value("BITWEEN_PAYROLL_WORKPLACE").unwrap_or_default();
        config.period = env_value("BITWEEN_PAYROLL_PERIOD").unwrap_or_default();
        config.auth_provider_configured = env_flag("BITWEEN_AUTH_CONFIGURED");
        config.session_jwt_verified = env_flag("BITWEEN_SESSION_JWT_VERIFIED");
        config.session_jwt_issuer = env_value("BITWEEN_SESSION_JWT_ISSUER").unwrap_or_default();
        config.session_jwt_audience = env_value("BITWEEN_SESSION_JWT_AUDIENCE").unwrap_or_default();
        config.session_jwt_subject = env_value("BITWEEN_SESSION_JWT_SUBJECT").unwrap_or_default();
        config.session_jwt_expires_at_unix =
            env_u64("BITWEEN_SESSION_JWT_EXPIRES_AT_UNIX").unwrap_or_default();
        config.session_webauthn_user_verified = env_flag("BITWEEN_WEBAUTHN_USER_VERIFIED");
        config.session_acr_level = env_value("BITWEEN_SESSION_ACR_LEVEL").unwrap_or_default();
        config.session_acr_event_at_unix =
            env_u64("BITWEEN_SESSION_ACR_EVENT_AT_UNIX").unwrap_or_default();
        config.session_actor_role = env_value("BITWEEN_SESSION_ROLE").unwrap_or_default();
        config.session_authz_policy_id =
            env_value("BITWEEN_SESSION_AUTHZ_POLICY_ID").unwrap_or_default();
        config.session_authorized_tenant_id =
            env_value("BITWEEN_SESSION_AUTHZ_TENANT_ID").unwrap_or_default();
        config.session_authorized_legal_entity =
            env_value("BITWEEN_SESSION_AUTHZ_LEGAL_ENTITY")
                .or_else(|| env_value("BITWEEN_SESSION_AUTHZ_AFFILIATE"))
                .unwrap_or_default();
        config.session_authorized_workplace =
            env_value("BITWEEN_SESSION_AUTHZ_WORKPLACE").unwrap_or_default();
        config.archive_configured = env_flag("BITWEEN_ARCHIVE_CONFIGURED");
        config.ontology_projection_configured = env_flag("BITWEEN_ONTOLOGY_CONFIGURED");
        config.workflow_template_configured = env_flag("BITWEEN_WORKFLOW_CONFIGURED");
        config.compliance_pack_configured = env_flag("BITWEEN_COMPLIANCE_PACK_CONFIGURED");
        config.observability_configured = env_flag("BITWEEN_OBSERVABILITY_CONFIGURED");
        config.finops_configured = env_flag("BITWEEN_FINOPS_CONFIGURED");
        config.import_plan_declared = env_flag("BITWEEN_IMPORT_PLAN_DECLARED");
        config.support_runbook_configured = env_flag("BITWEEN_SUPPORT_RUNBOOK_CONFIGURED");
        config.payroll_inputs_closed = env_flag("BITWEEN_PAYROLL_INPUTS_CLOSED");
        config.attendance_closed = env_flag("BITWEEN_ATTENDANCE_CLOSED");
        config.deductions_reviewed = env_flag("BITWEEN_DEDUCTIONS_REVIEWED");
        config.payroll_calculated = env_flag("BITWEEN_PAYROLL_CALCULATED");
        config.approval_requested = env_flag("BITWEEN_PAYROLL_APPROVAL_REQUESTED");
        config.payout_prepared = env_flag("BITWEEN_PAYOUT_PREPARED");
        config.payroll_evidence_archived = env_flag("BITWEEN_PAYROLL_EVIDENCE_ARCHIVED");
        config
    }

    pub fn with_scope(
        mut self,
        tenant_id: impl Into<String>,
        tenant_name: impl Into<String>,
        affiliate: impl Into<String>,
        workplace: impl Into<String>,
        period: impl Into<String>,
    ) -> Self {
        self.tenant_id = clean(tenant_id.into());
        self.tenant_name = clean(tenant_name.into());
        self.affiliate = clean(affiliate.into());
        self.workplace = clean(workplace.into());
        self.period = clean(period.into());
        self
    }

    pub fn with_auth_provider_configured(mut self, configured: bool) -> Self {
        self.auth_provider_configured = configured;
        self
    }

    pub fn with_verified_session(mut self, verified: bool, role: impl Into<String>) -> Self {
        self.session_jwt_verified = verified;
        self.session_jwt_issuer = "https://auth.bitween.local".to_owned();
        self.session_jwt_audience = "bitween-platform".to_owned();
        self.session_jwt_subject = "user-live-ops".to_owned();
        self.session_jwt_expires_at_unix = 4_102_444_800;
        self.session_webauthn_user_verified = verified;
        self.session_acr_level = if verified { "elevated" } else { "" }.to_owned();
        self.session_acr_event_at_unix = if verified { 1 } else { 0 };
        self.session_actor_role = clean(role.into());
        self.session_authz_policy_id = if verified { AUTHZ_POLICY_ID } else { "" }.to_owned();
        self.session_authorized_tenant_id = if verified {
            self.tenant_id.clone()
        } else {
            String::new()
        };
        self.session_authorized_legal_entity = if verified {
            self.affiliate.clone()
        } else {
            String::new()
        };
        self.session_authorized_workplace = if verified {
            self.workplace.clone()
        } else {
            String::new()
        };
        self
    }

    pub fn with_jwt_claims(
        mut self,
        issuer: impl Into<String>,
        audience: impl Into<String>,
        subject: impl Into<String>,
        expires_at_unix: u64,
    ) -> Self {
        self.session_jwt_issuer = clean(issuer.into());
        self.session_jwt_audience = clean(audience.into());
        self.session_jwt_subject = clean(subject.into());
        self.session_jwt_expires_at_unix = expires_at_unix;
        self
    }

    pub fn with_webauthn_user_verified(mut self, verified: bool) -> Self {
        self.session_webauthn_user_verified = verified;
        self
    }

    pub fn with_acr_level(mut self, acr_level: impl Into<String>, event_at_unix: u64) -> Self {
        self.session_acr_level = clean(acr_level.into());
        self.session_acr_event_at_unix = event_at_unix;
        self
    }

    pub fn with_authorization_scope(
        mut self,
        policy_id: impl Into<String>,
        tenant_id: impl Into<String>,
        legal_entity: impl Into<String>,
        workplace: impl Into<String>,
    ) -> Self {
        self.session_authz_policy_id = clean(policy_id.into());
        self.session_authorized_tenant_id = clean(tenant_id.into());
        self.session_authorized_legal_entity = clean(legal_entity.into());
        self.session_authorized_workplace = clean(workplace.into());
        self
    }

    pub fn with_archive_configured(mut self, configured: bool) -> Self {
        self.archive_configured = configured;
        self
    }

    pub fn with_enterprise_operations_configured(mut self, configured: bool) -> Self {
        self.ontology_projection_configured = configured;
        self.workflow_template_configured = configured;
        self.compliance_pack_configured = configured;
        self.observability_configured = configured;
        self.finops_configured = configured;
        self.import_plan_declared = configured;
        self.support_runbook_configured = configured;
        self
    }

    pub fn with_payroll_workstream_completed(mut self, completed: bool) -> Self {
        self.payroll_inputs_closed = completed;
        self.attendance_closed = completed;
        self.deductions_reviewed = completed;
        self.payroll_calculated = completed;
        self.approval_requested = completed;
        self.payout_prepared = completed;
        self.payroll_evidence_archived = completed;
        self
    }

    fn scope_configured(&self) -> bool {
        !self.tenant_id.is_empty()
            && !self.tenant_name.is_empty()
            && !self.affiliate.is_empty()
            && !self.workplace.is_empty()
            && !self.period.is_empty()
    }

    fn session_authenticated(&self) -> bool {
        self.auth_provider_configured
            && self.session_jwt_verified
            && !self.session_jwt_issuer.is_empty()
            && !self.session_jwt_audience.is_empty()
            && !self.session_jwt_subject.is_empty()
            && self.session_jwt_expires_at_unix > generated_at_unix()
            && self.session_webauthn_user_verified
            && self.session_acr_valid()
    }

    fn session_acr(&self) -> Option<AuthAcrLevel> {
        AuthAcrLevel::parse(&self.session_acr_level)
    }

    fn session_acr_valid(&self) -> bool {
        self.session_acr().is_some()
            && self.session_acr_event_at_unix > 0
            && self.session_acr_event_at_unix <= generated_at_unix()
    }

    pub fn session_allows_sensitive_operation(&self, operation: AuthSensitiveOperation) -> bool {
        let Ok(policy) = AuthzPolicy::from_env() else {
            return false;
        };
        self.session_authenticated()
            && evaluate_step_up(&policy, self.session_acr(), operation).allowed
    }

    pub fn session_is_authenticated(&self) -> bool {
        self.session_authenticated()
    }

    pub fn session_authorization_decision(
        &self,
        operation: AuthSensitiveOperation,
    ) -> AuthzDecision {
        // Fail closed on an invalid configured policy: never fall back to the
        // built-in matrix when BITWEEN_AUTHZ_POLICY_JSON is set but invalid.
        let policy = match AuthzPolicy::from_env() {
            Ok(policy) => policy,
            Err(_) => return AuthzDecision::policy_invalid(operation),
        };
        evaluate_authorization(&policy, &self.session_authorization_request(operation))
    }

    pub fn session_authorizes_operation(&self, operation: AuthSensitiveOperation) -> bool {
        self.session_authenticated() && self.session_authorization_decision(operation).allowed
    }

    fn session_authorization_request(
        &self,
        operation: AuthSensitiveOperation,
    ) -> AuthzRequest<'_> {
        AuthzRequest {
            policy_id: &self.session_authz_policy_id,
            operation,
            current_acr: self.session_acr(),
            role: Some(&self.session_actor_role),
            actor_tenant_id: &self.session_authorized_tenant_id,
            resource_tenant_id: &self.tenant_id,
            actor_legal_entity: &self.session_authorized_legal_entity,
            resource_legal_entity: &self.affiliate,
            actor_workplace: &self.session_authorized_workplace,
            resource_workplace: &self.workplace,
            workflow_state: self.payroll_auth_workflow_state(),
        }
    }

    /// Derives the PBAC workflow state from the deployment lifecycle flags.
    ///
    /// The advanced flags must form a clean prefix chain: each stage requires
    /// every earlier stage to be set. When a flag is set without its full
    /// prefix (e.g. `approval_requested` without `payroll_calculated`), the
    /// combination is inconsistent and must fail closed via
    /// [`AuthWorkflowState::Inconsistent`] rather than demoting to the last
    /// consistent prefix state, which would open early-window operations.
    fn payroll_auth_workflow_state(&self) -> AuthWorkflowState {
        let inputs_trio =
            self.payroll_inputs_closed && self.attendance_closed && self.deductions_reviewed;
        let calculated_chain = inputs_trio && self.payroll_calculated;
        let approval_chain = calculated_chain && self.approval_requested;
        let approved_chain = approval_chain && self.payout_prepared;

        // Any advanced flag set without its required prefix is inconsistent.
        if self.payroll_calculated && !inputs_trio {
            return AuthWorkflowState::Inconsistent;
        }
        if self.approval_requested && !calculated_chain {
            return AuthWorkflowState::Inconsistent;
        }
        if self.payout_prepared && !approval_chain {
            return AuthWorkflowState::Inconsistent;
        }
        if self.payroll_evidence_archived && !approved_chain {
            return AuthWorkflowState::Inconsistent;
        }

        if self.payroll_evidence_archived {
            AuthWorkflowState::Archived
        } else if self.payout_prepared {
            AuthWorkflowState::Approved
        } else if self.approval_requested {
            AuthWorkflowState::ApprovalPending
        } else if self.payroll_calculated {
            AuthWorkflowState::Calculated
        } else if inputs_trio {
            AuthWorkflowState::InputsClosed
        } else {
            AuthWorkflowState::Open
        }
    }
}

pub fn build_platform_live_view(config: PlatformLiveConfig) -> PlatformLiveView {
    let service = PayrollApiService::new(config.service_config.clone());
    let health = service.health();
    let scope = scope_view(&config);
    let readiness = service.readiness(readiness_checks(&config));
    let readiness_cards = readiness_cards(&readiness, &scope);
    let workstream = payroll_workstream(&config, &readiness, &scope);
    let next_actions = next_actions(&readiness, &scope);
    let enterprise = enterprise_maturity(&config, &readiness, &scope, &next_actions);

    PlatformLiveView {
        schema: PLATFORM_VIEW_SCHEMA,
        source: PlatformSource {
            service: health.service.clone(),
            endpoint: PLATFORM_VIEW_ENDPOINT,
            backend: "rust_native",
            executor: PAYROLL_RUST_NATIVE_EXECUTOR,
            generated_at_unix: generated_at_unix(),
        },
        session: PlatformSession {
            mode: session_mode(&config),
            authenticated: config.session_authenticated(),
            tenant_id: blank_label(&scope.tenant_id, "unconfigured"),
            tenant_name: blank_label(&scope.tenant_name, "Tenant scope not configured"),
            role: session_role(&config),
            scope_label: scope_label(&scope),
        },
        navigation: navigation(),
        enterprise,
        payroll: PayrollOperationsView {
            scope,
            health,
            readiness,
            readiness_cards,
            workstream,
            next_actions: next_actions.clone(),
        },
        work_queue: next_actions,
    }
}

fn enterprise_maturity(
    config: &PlatformLiveConfig,
    readiness: &ReadinessResponse,
    scope: &PayrollScopeView,
    work_items: &[PlatformWorkItem],
) -> EnterpriseMaturityView {
    let gates = enterprise_gates(config, readiness, scope, work_items);
    let capability_tiers = enterprise_capability_tiers(config, scope, work_items);
    let ready_gates = gates.iter().filter(|gate| gate.tone == "ready").count();
    let blocked_gates = gates.iter().filter(|gate| gate.tone == "blocked").count();

    EnterpriseMaturityView {
        model: "unified_enterprise_capability_tier_v1",
        summary: format!(
            "{ready_gates}/{} enterprise gates ready; {blocked_gates} blockers require owner action.",
            gates.len()
        ),
        gates,
        capability_tiers,
    }
}

fn enterprise_gates(
    config: &PlatformLiveConfig,
    readiness: &ReadinessResponse,
    scope: &PayrollScopeView,
    work_items: &[PlatformWorkItem],
) -> Vec<EnterpriseMaturityGate> {
    let (scope_status, scope_tone) = status_for(scope.configured, "Ready", "Blocked");
    let (auth_status, auth_tone) = status_for(config.auth_provider_configured, "Ready", "Blocked");
    let (archive_status, archive_tone) =
        status_for(config.archive_configured, "Ready", "Needs evidence storage");
    let operating_bar_ready = readiness.ready
        && config.ontology_projection_configured
        && config.workflow_template_configured
        && config.compliance_pack_configured
        && config.observability_configured
        && config.finops_configured
        && config.support_runbook_configured;
    let (operating_status, operating_tone) =
        status_for(operating_bar_ready, "Ready", "Needs operating bar");

    vec![
        EnterpriseMaturityGate {
            id: "tenant-boundary",
            title: "Tenant and legal-entity boundary",
            status: scope_status,
            tone: scope_tone,
            owner: "IT/security admin",
            evidence: if scope.configured {
                scope_label(scope)
            } else {
                "Tenant, legal entity, workplace, and period are not fully configured.".to_owned()
            },
            next_step: "Keep tenant scope visible before any payroll action.",
            source: "crates/payroll-api",
        },
        EnterpriseMaturityGate {
            id: "policy-permission-boundary",
            title: "Policy and permission boundary",
            status: auth_status,
            tone: auth_tone,
            owner: "IT/security admin",
            evidence: if config.auth_provider_configured {
                "Production auth provider flag is enabled for the live shell.".to_owned()
            } else {
                "SSO/session provider is required before authenticated payroll actions can run."
                    .to_owned()
            },
            next_step: "Wire tenant SSO/session claims into Rust authorization before enabling write actions.",
            source: "crates/payroll-api",
        },
        EnterpriseMaturityGate {
            id: "rust-contract-source",
            title: "Rust source contract",
            status: "Ready",
            tone: "ready",
            owner: "Payroll platform engineering",
            evidence: PAYROLL_RUST_NATIVE_EXECUTOR.to_owned(),
            next_step: "Keep runtime payloads owned by Rust contracts and fail closed on contract drift.",
            source: "crates/payroll-api",
        },
        EnterpriseMaturityGate {
            id: "evidence-audit-archive",
            title: "Evidence and audit archive",
            status: archive_status,
            tone: archive_tone,
            owner: "Payroll operations",
            evidence: if config.archive_configured {
                "Evidence archive storage is configured for payroll outputs.".to_owned()
            } else {
                "Read-only readiness is available, but output evidence storage is not configured."
                    .to_owned()
            },
            next_step: "Connect archive storage before payroll execution produces regulated evidence.",
            source: "crates/payroll-api",
        },
        EnterpriseMaturityGate {
            id: "owner-action-loop",
            title: "Owner and next-action loop",
            status: if work_items.is_empty() { "Blocked" } else { "Ready" },
            tone: if work_items.is_empty() { "blocked" } else { "ready" },
            owner: "Finance operator",
            evidence: format!("{} live work item(s) emitted from readiness checks.", work_items.len()),
            next_step: "Every non-ready prerequisite must name an owner, target surface, and next action.",
            source: "crates/payroll-api",
        },
        EnterpriseMaturityGate {
            id: "enterprise-operating-bar",
            title: "Enterprise operating bar",
            status: operating_status,
            tone: operating_tone,
            owner: "Product and platform leadership",
            evidence: "Capability-tier checklist covers permits, ontology, workflow, UX, compliance, observability, cost, import, and runbook evidence.".to_owned(),
            next_step: "Close non-ready capability tiers before claiming production-grade enterprise maturity.",
            source: "DESIGN.md",
        },
    ]
}

fn enterprise_capability_tiers(
    config: &PlatformLiveConfig,
    scope: &PayrollScopeView,
    work_items: &[PlatformWorkItem],
) -> Vec<EnterpriseCapabilityTier> {
    let (permit_status, permit_tone) =
        status_for(config.auth_provider_configured, "Ready", "Blocked");
    let (ontology_status, ontology_tone) = status_for(
        config.ontology_projection_configured,
        "Ready",
        "Needs contract",
    );
    let (workflow_status, workflow_tone) = status_for(
        config.workflow_template_configured,
        "Ready",
        "Needs workflow",
    );
    let (compliance_status, compliance_tone) =
        status_for(config.compliance_pack_configured, "Ready", "Needs pack");
    let observability_ready = config.observability_configured && config.archive_configured;
    let (observability_status, observability_tone) =
        status_for(observability_ready, "Ready", "Needs telemetry");
    let (finops_status, finops_tone) =
        status_for(config.finops_configured, "Ready", "Needs cost model");
    let (import_status, import_tone) = if config.import_plan_declared {
        ("Ready", "ready")
    } else {
        ("Future work", "neutral")
    };
    let (runbook_status, runbook_tone) =
        status_for(config.support_runbook_configured, "Ready", "Needs runbook");

    vec![
        EnterpriseCapabilityTier {
            id: "permit-set",
            title: "Permit set",
            status: permit_status,
            tone: permit_tone,
            artifact: "tenant role and payroll action policy",
            owner: "IT/security admin",
            evidence: if config.auth_provider_configured {
                "Auth provider is configured for tenant-scoped policy checks.".to_owned()
            } else {
                "Role-specific payroll actions remain blocked until SSO/session claims are wired."
                    .to_owned()
            },
            next_step: "Bind tenant, actor, role, workplace, and action claims to Rust authorization.",
            source: "crates/payroll-api",
        },
        EnterpriseCapabilityTier {
            id: "ontology-projection",
            title: "Ontology projection",
            status: ontology_status,
            tone: ontology_tone,
            artifact: "tenant, affiliate, workplace, period, worker, payroll run",
            owner: "Payroll platform engineering",
            evidence: if scope.configured {
                scope_label(scope)
            } else {
                "Scope objects are not fully configured.".to_owned()
            },
            next_step: "Publish versioned payroll object and relationship contracts for cross-surface use.",
            source: "DESIGN.md",
        },
        EnterpriseCapabilityTier {
            id: "workflow-template",
            title: "Workflow template",
            status: workflow_status,
            tone: workflow_tone,
            artifact: "corporate workflow template and approval handoff contract",
            owner: "Finance operator",
            evidence: format!(
                "{} readiness work item(s) are available in the live shell.",
                work_items.len()
            ),
            next_step: "Keep approval signing separate from workflow logic, timeout, escalation, and replayable automation contracts.",
            source: "crates/payroll-api",
        },
        EnterpriseCapabilityTier {
            id: "ux-shell-manifest",
            title: "UX shell manifest",
            status: "Ready",
            tone: "ready",
            artifact: "platform navigation and surface purpose manifest",
            owner: "Product design",
            evidence: "Navigation and purposes are emitted by the Rust platform live view."
                .to_owned(),
            next_step: "Keep surfaces generated from live capabilities rather than hardcoded product sprawl.",
            source: "crates/payroll-api",
        },
        EnterpriseCapabilityTier {
            id: "compliance-pack-overlay",
            title: "Compliance pack overlay",
            status: compliance_status,
            tone: compliance_tone,
            artifact: "Korean payroll, labor, social-insurance evidence pack",
            owner: "Compliance owner",
            evidence: if config.compliance_pack_configured {
                "Compliance pack flag is configured for the live shell.".to_owned()
            } else {
                "Regional compliance pack and effective-date policy are not yet declared."
                    .to_owned()
            },
            next_step: "Map payroll readiness to effective-date rules, retention, legal hold, and audit export evidence.",
            source: "DESIGN.md",
        },
        EnterpriseCapabilityTier {
            id: "observability-audit-stream",
            title: "Observability and audit stream",
            status: observability_status,
            tone: observability_tone,
            artifact: "health, readiness, audit, and evidence telemetry",
            owner: "SRE/reliability",
            evidence: if observability_ready {
                "Readiness, service health, and archive evidence flags are configured.".to_owned()
            } else {
                "Readiness and health are visible; telemetry/archive proof still needs production wiring."
                    .to_owned()
            },
            next_step: "Add SLO rows, burn-rate gates, trace correlation, and audit-chain emission for payroll actions.",
            source: "crates/payroll-api",
        },
        EnterpriseCapabilityTier {
            id: "finops-cost-dimension",
            title: "FinOps cost dimension",
            status: finops_status,
            tone: finops_tone,
            artifact: "tenant, workplace, period, and execution cost allocation",
            owner: "Finance operator",
            evidence: if config.finops_configured {
                "FinOps cost dimension is configured for the live shell.".to_owned()
            } else {
                "Cost allocation is not yet declared for payroll execution and evidence storage."
                    .to_owned()
            },
            next_step: "Expose tenant/workplace/period cost labels before paid production execution.",
            source: "DESIGN.md",
        },
        EnterpriseCapabilityTier {
            id: "migration-import-declaration",
            title: "Migration/import declaration",
            status: import_status,
            tone: import_tone,
            artifact: "legacy payroll data import and decommission backlog",
            owner: "Product leadership",
            evidence: if config.import_plan_declared {
                "Import/decommission plan is declared as a governed backlog item.".to_owned()
            } else {
                "Import and legacy-system decommission are tracked as future work while product maturity gates come first.".to_owned()
            },
            next_step: "Keep import/decommission work sequenced after the production shell, readiness, and operating gates.",
            source: "docs/PYTHON_DECOMMISSION_INVENTORY.md",
        },
        EnterpriseCapabilityTier {
            id: "support-runbook-reference",
            title: "Support runbook reference",
            status: runbook_status,
            tone: runbook_tone,
            artifact: "operations runbook, owner, escalation, and recovery path",
            owner: "Customer success and SRE",
            evidence: if config.support_runbook_configured {
                "Support runbook flag is configured for the live shell.".to_owned()
            } else {
                "Runbook, escalation, and recovery links are not yet configured.".to_owned()
            },
            next_step: "Attach customer-support and incident runbooks to each readiness blocker and production action.",
            source: "DESIGN.md",
        },
    ]
}

fn readiness_checks(config: &PlatformLiveConfig) -> Vec<ReadinessCheck> {
    let mut checks = vec![
        ReadinessCheck::ready(
            "rust_payroll_api",
            "Rust payroll service initialized and available.",
        ),
        ReadinessCheck::ready(
            "rust_execution_backend",
            "Execution planning is owned by bitween-payroll-api Rust contracts.",
        ),
    ];

    if config.scope_configured() {
        checks.push(ReadinessCheck::ready(
            "tenant_scope",
            "Tenant, affiliate, workplace, and payroll period are configured.",
        ));
    } else {
        checks.push(ReadinessCheck::not_ready(
            "tenant_scope",
            "Set BITWEEN_TENANT_ID, BITWEEN_TENANT_NAME, BITWEEN_PAYROLL_AFFILIATE, BITWEEN_PAYROLL_WORKPLACE, and BITWEEN_PAYROLL_PERIOD.",
        ));
    }

    if config.auth_provider_configured {
        checks.push(ReadinessCheck::ready(
            "auth_provider",
            "Production auth provider is configured.",
        ));
    } else {
        checks.push(ReadinessCheck::not_ready(
            "auth_provider",
            "Configure production SSO/session provider before enabling authenticated payroll actions.",
        ));
    }

    if config.archive_configured {
        checks.push(ReadinessCheck::ready(
            "archive_storage",
            "Payroll evidence archive storage is configured.",
        ));
    } else {
        checks.push(ReadinessCheck::degraded(
            "archive_storage",
            "Evidence archive storage is not configured; read-only readiness remains available.",
        ));
    }

    checks
}

fn scope_view(config: &PlatformLiveConfig) -> PayrollScopeView {
    PayrollScopeView {
        tenant_id: config.tenant_id.clone(),
        tenant_name: config.tenant_name.clone(),
        affiliate: config.affiliate.clone(),
        workplace: config.workplace.clone(),
        period: config.period.clone(),
        configured: config.scope_configured(),
    }
}

fn readiness_cards(
    readiness: &ReadinessResponse,
    scope: &PayrollScopeView,
) -> Vec<ReadinessCardView> {
    readiness
        .checks
        .iter()
        .map(|check| ReadinessCardView {
            id: readiness_card_id(&check.name),
            title: readiness_card_title(&check.name),
            value: readiness_value(check),
            detail: readiness_detail(check, scope),
            tone: tone_for_state(&check.state),
            source: "crates/payroll-api",
        })
        .collect()
}

fn payroll_workstream(
    config: &PlatformLiveConfig,
    readiness: &ReadinessResponse,
    scope: &PayrollScopeView,
) -> PayrollWorkstreamView {
    let scope_ready = scope.configured;
    let auth_ready = config.auth_provider_configured;
    let platform_ready_for_work = scope_ready && auth_ready;
    let platform_blocked = readiness
        .checks
        .iter()
        .any(|check| check.required && check.state == ReadinessState::NotReady);

    let mut steps = Vec::new();

    if !scope_ready {
        steps.push(payroll_work_step(
            "set-payroll-scope",
            "blocked",
            "blocked",
            "payroll-admin",
            "set-scope",
            "admin",
        ));
    }

    if !auth_ready {
        steps.push(payroll_work_step(
            "configure-access",
            "blocked",
            "blocked",
            "it-admin",
            "configure-access",
            "admin",
        ));
    }

    let (attendance_status, attendance_tone) =
        sequential_status(config.attendance_closed, platform_ready_for_work);
    steps.push(payroll_work_step(
        "close-attendance",
        attendance_status,
        attendance_tone,
        "hr-operator",
        "close-attendance",
        "hr",
    ));

    let (inputs_status, inputs_tone) = sequential_status(
        config.payroll_inputs_closed,
        platform_ready_for_work && config.attendance_closed,
    );
    steps.push(payroll_work_step(
        "close-payroll-inputs",
        inputs_status,
        inputs_tone,
        "payroll-operator",
        "close-inputs",
        "payroll",
    ));

    let (deductions_status, deductions_tone) = sequential_status(
        config.deductions_reviewed,
        platform_ready_for_work && config.attendance_closed && config.payroll_inputs_closed,
    );
    steps.push(payroll_work_step(
        "review-deductions",
        deductions_status,
        deductions_tone,
        "payroll-operator",
        "review-deductions",
        "payroll",
    ));

    let (calculation_status, calculation_tone) = sequential_status(
        config.payroll_calculated,
        platform_ready_for_work
            && config.attendance_closed
            && config.payroll_inputs_closed
            && config.deductions_reviewed,
    );
    steps.push(payroll_work_step(
        "run-calculation",
        calculation_status,
        calculation_tone,
        "payroll-operator",
        "run-calculation",
        "payroll",
    ));

    let approval_available = platform_ready_for_work
        && config.attendance_closed
        && config.payroll_inputs_closed
        && config.deductions_reviewed
        && config.payroll_calculated;
    let (approval_status, approval_tone) = if config.approval_requested {
        ("completed", "ready")
    } else if approval_available && !config.workflow_template_configured {
        ("blocked", "blocked")
    } else {
        sequential_status(config.approval_requested, approval_available)
    };
    steps.push(payroll_work_step(
        "request-approval",
        approval_status,
        approval_tone,
        "payroll-operator",
        "request-approval",
        "approval",
    ));

    let (payout_status, payout_tone) = sequential_status(
        config.payout_prepared,
        approval_available && config.workflow_template_configured && config.approval_requested,
    );
    steps.push(payroll_work_step(
        "prepare-payout",
        payout_status,
        payout_tone,
        "payroll-operator",
        "prepare-payout",
        "archive",
    ));

    let archive_available = approval_available
        && config.workflow_template_configured
        && config.approval_requested
        && config.payout_prepared;
    let (archive_status, archive_tone) = if config.payroll_evidence_archived {
        ("completed", "ready")
    } else if archive_available && !config.archive_configured {
        ("blocked", "blocked")
    } else {
        sequential_status(config.payroll_evidence_archived, archive_available)
    };
    steps.push(payroll_work_step(
        "archive-payroll-evidence",
        archive_status,
        archive_tone,
        "payroll-operator",
        "archive-evidence",
        "archive",
    ));

    let current_step_id = steps
        .iter()
        .find(|step| step.status != "completed")
        .map(|step| step.id)
        .unwrap_or("archive-payroll-evidence");
    let current_tone = steps
        .iter()
        .find(|step| step.id == current_step_id)
        .map(|step| step.tone)
        .unwrap_or("ready");
    let all_completed = steps.iter().all(|step| step.status == "completed");
    let (status, tone) = if all_completed {
        ("completed", "ready")
    } else if platform_blocked || current_tone == "blocked" {
        ("blocked", "blocked")
    } else if current_tone == "attention" {
        ("ready", "attention")
    } else {
        ("waiting", "neutral")
    };

    PayrollWorkstreamView {
        period_label: scope_label(scope),
        status,
        tone,
        current_step_id,
        steps,
    }
}

fn payroll_work_step(
    id: &'static str,
    status: &'static str,
    tone: &'static str,
    owner: &'static str,
    action: &'static str,
    target: &'static str,
) -> PayrollWorkStepView {
    PayrollWorkStepView {
        id,
        status,
        tone,
        owner,
        action,
        target,
    }
}

fn sequential_status(done: bool, available: bool) -> (&'static str, &'static str) {
    if done {
        ("completed", "ready")
    } else if available {
        ("ready", "attention")
    } else {
        ("waiting", "neutral")
    }
}

fn next_actions(readiness: &ReadinessResponse, scope: &PayrollScopeView) -> Vec<PlatformWorkItem> {
    let mut items = readiness
        .checks
        .iter()
        .filter(|check| check.state != ReadinessState::Ready)
        .map(|check| work_item_for_check(check, scope))
        .collect::<Vec<_>>();

    if items.is_empty() {
        items.push(PlatformWorkItem {
            id: "confirm-payroll-close",
            title: "Confirm payroll close",
            owner: "Finance operator",
            status: "Ready".to_owned(),
            next_step: "Check current-period payroll inputs and exceptions before calculation.",
            target: "payroll",
            tone: "ready",
        });
    }

    items
}

fn work_item_for_check(check: &ReadinessCheck, scope: &PayrollScopeView) -> PlatformWorkItem {
    match check.name.as_str() {
        "tenant_scope" => PlatformWorkItem {
            id: "set-payroll-scope",
            title: "Set payroll scope",
            owner: "IT/security admin",
            status: readiness_value(check),
            next_step: "Confirm legal entity, workplace, and payroll period for this run.",
            target: "admin",
            tone: tone_for_state(&check.state),
        },
        "auth_provider" => PlatformWorkItem {
            id: "complete-access-setup",
            title: "Complete access setup",
            owner: "IT/security admin",
            status: readiness_value(check),
            next_step: "Confirm role access and sign-in policy before payroll actions are enabled.",
            target: "admin",
            tone: tone_for_state(&check.state),
        },
        "archive_storage" => PlatformWorkItem {
            id: "confirm-payroll-archive",
            title: "Confirm payroll archive",
            owner: "Payroll operations",
            status: readiness_value(check),
            next_step: "Confirm payroll output storage and access before outputs are created.",
            target: "archive",
            tone: tone_for_state(&check.state),
        },
        _ => PlatformWorkItem {
            id: "review-payroll-blocker",
            title: "Review payroll blocker",
            owner: "Finance operator",
            status: readiness_value(check),
            next_step: if scope.configured {
                "Review the blocked payroll input and assign the owner."
            } else {
                "Configure the payroll scope before resolving downstream blockers."
            },
            target: "payroll",
            tone: tone_for_state(&check.state),
        },
    }
}

fn navigation() -> Vec<PlatformNavigationItem> {
    vec![
        PlatformNavigationItem {
            id: "home",
            label: "Operations",
            purpose: "Start from the current payroll period and the next role-owned workflow step.",
        },
        PlatformNavigationItem {
            id: "hr",
            label: "HR",
            purpose: "Close people, attendance, and HR source inputs before payroll calculation.",
        },
        PlatformNavigationItem {
            id: "payroll",
            label: "Payroll",
            purpose: "Run the payroll close workflow for the selected tenant, workplace, and period.",
        },
        PlatformNavigationItem {
            id: "workflow",
            label: "Workflow",
            purpose: "Visualize and govern corporate workflow logic, routing, timeouts, and automation.",
        },
        PlatformNavigationItem {
            id: "approval",
            label: "Approvals",
            purpose: "Review, sign, approve, reject, and circulate documents that require formal approval.",
        },
        PlatformNavigationItem {
            id: "archive",
            label: "Archive",
            purpose: "Prepare payout evidence and archive payroll records.",
        },
        PlatformNavigationItem {
            id: "admin",
            label: "Admin",
            purpose: "Configure tenant, auth, scope, and operating prerequisites.",
        },
    ]
}

fn readiness_card_id(name: &str) -> &'static str {
    match name {
        "rust_payroll_api" => "rust-api",
        "rust_execution_backend" => "rust-execution",
        "tenant_scope" => "tenant-scope",
        "auth_provider" => "auth-provider",
        "archive_storage" => "archive-storage",
        _ => "readiness-check",
    }
}

fn readiness_card_title(name: &str) -> &'static str {
    match name {
        "rust_payroll_api" => "Rust payroll API",
        "rust_execution_backend" => "Rust execution backend",
        "tenant_scope" => "Tenant scope",
        "auth_provider" => "Authentication",
        "archive_storage" => "Evidence archive",
        _ => "Readiness check",
    }
}

fn readiness_value(check: &ReadinessCheck) -> String {
    match check.state {
        ReadinessState::Ready => "Ready".to_owned(),
        ReadinessState::Degraded => {
            if check.required {
                "Needs attention".to_owned()
            } else {
                "Degraded".to_owned()
            }
        }
        ReadinessState::NotReady => "Blocked".to_owned(),
    }
}

fn readiness_detail(check: &ReadinessCheck, scope: &PayrollScopeView) -> String {
    if check.name == "tenant_scope" && scope.configured {
        return format!(
            "{} / {} / {}",
            scope.affiliate, scope.workplace, scope.period
        );
    }
    check.message.clone()
}

fn tone_for_state(state: &ReadinessState) -> &'static str {
    match state {
        ReadinessState::Ready => "ready",
        ReadinessState::Degraded => "attention",
        ReadinessState::NotReady => "blocked",
    }
}

fn status_for(
    ready: bool,
    ready_label: &'static str,
    not_ready_label: &'static str,
) -> (&'static str, &'static str) {
    if ready {
        (ready_label, "ready")
    } else if not_ready_label == "Blocked" {
        (not_ready_label, "blocked")
    } else {
        (not_ready_label, "attention")
    }
}

fn scope_label(scope: &PayrollScopeView) -> String {
    if scope.configured {
        format!(
            "{} · {} · {}",
            scope.affiliate, scope.workplace, scope.period
        )
    } else {
        "Payroll scope not configured".to_owned()
    }
}

fn session_mode(config: &PlatformLiveConfig) -> &'static str {
    if config.session_authenticated() {
        "authenticated"
    } else if config.auth_provider_configured {
        "auth_required"
    } else {
        "local_readonly"
    }
}

fn session_role(config: &PlatformLiveConfig) -> String {
    if config.session_authenticated() {
        blank_label(&config.session_actor_role, "operations_operator")
    } else {
        "unauthenticated".to_owned()
    }
}

fn blank_label(value: &str, default_value: &str) -> String {
    if value.trim().is_empty() {
        default_value.to_owned()
    } else {
        value.to_owned()
    }
}

fn generated_at_unix() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0)
}

fn env_value(key: &str) -> Option<String> {
    std::env::var(key)
        .ok()
        .map(clean)
        .filter(|value| !value.is_empty())
}

fn env_flag(key: &str) -> bool {
    matches!(
        std::env::var(key)
            .ok()
            .as_deref()
            .map(str::trim)
            .map(|value| value.to_ascii_lowercase())
            .as_deref(),
        Some("1" | "true" | "yes" | "on")
    )
}

fn env_u64(key: &str) -> Option<u64> {
    env_value(key).and_then(|value| value.parse::<u64>().ok())
}

fn clean(value: String) -> String {
    value.trim().to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_rust_owned_live_platform_payload() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul Site", "2026-06")
                .with_auth_provider_configured(true)
                .with_archive_configured(true)
                .with_enterprise_operations_configured(true),
        );
        let value = serde_json::to_value(&view).unwrap();
        let body = serde_json::to_string(&view).unwrap();

        assert_eq!(view.schema, PLATFORM_VIEW_SCHEMA);
        assert_eq!(view.source.backend, "rust_native");
        assert_eq!(view.source.executor, PAYROLL_RUST_NATIVE_EXECUTOR);
        assert_eq!(view.payroll.readiness.state, ReadinessState::Ready);
        assert_eq!(
            view.enterprise.model,
            "unified_enterprise_capability_tier_v1"
        );
        assert_eq!(
            view.navigation.iter().map(|item| item.id).collect::<Vec<_>>(),
            vec![
                "home", "hr", "payroll", "workflow", "approval", "archive", "admin"
            ]
        );
        assert_eq!(value["payroll"]["scope"]["configured"], true);
        assert_eq!(
            value["enterprise"]["capability_tiers"][0]["id"],
            "permit-set"
        );
        assert_eq!(
            value["payroll"]["readiness_cards"][0]["source"],
            "crates/payroll-api"
        );
        assert!(!body.contains("python"));
        assert!(!body.contains(&["mo", "ck"].concat()));
        assert!(!body.contains(&["de", "mo"].concat()));
    }

    #[test]
    fn payroll_workstream_starts_with_hr_source_close_before_payroll_work() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
                .with_auth_provider_configured(true)
                .with_archive_configured(true)
                .with_enterprise_operations_configured(true),
        );
        let steps = &view.payroll.workstream.steps;

        assert_eq!(view.payroll.workstream.status, "ready");
        assert_eq!(view.payroll.workstream.current_step_id, "close-attendance");
        assert_eq!(steps[0].id, "close-attendance");
        assert_eq!(steps[0].target, "hr");
        assert_eq!(steps[0].owner, "hr-operator");
        assert_eq!(steps[1].id, "close-payroll-inputs");
        assert_eq!(steps[1].target, "payroll");
        assert_eq!(
            steps
                .iter()
                .find(|step| step.id == "request-approval")
                .unwrap()
                .target,
            "approval"
        );
    }

    #[test]
    fn completed_payroll_workstream_marks_all_steps_complete() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
                .with_auth_provider_configured(true)
                .with_archive_configured(true)
                .with_enterprise_operations_configured(true)
                .with_payroll_workstream_completed(true),
        );

        assert_eq!(view.payroll.workstream.status, "completed");
        assert_eq!(view.payroll.workstream.tone, "ready");
        assert_eq!(
            view.payroll.workstream.current_step_id,
            "archive-payroll-evidence"
        );
        assert!(view
            .payroll
            .workstream
            .steps
            .iter()
            .all(|step| step.status == "completed" && step.tone == "ready"));
    }

    #[test]
    fn enterprise_maturity_surfaces_capability_tier_operating_bar() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
                .with_auth_provider_configured(true)
                .with_archive_configured(true),
        );
        let gate_ids = view
            .enterprise
            .gates
            .iter()
            .map(|gate| gate.id)
            .collect::<Vec<_>>();
        let tier_ids = view
            .enterprise
            .capability_tiers
            .iter()
            .map(|tier| tier.id)
            .collect::<Vec<_>>();

        assert_eq!(
            gate_ids,
            vec![
                "tenant-boundary",
                "policy-permission-boundary",
                "rust-contract-source",
                "evidence-audit-archive",
                "owner-action-loop",
                "enterprise-operating-bar",
            ]
        );
        assert_eq!(
            tier_ids,
            vec![
                "permit-set",
                "ontology-projection",
                "workflow-template",
                "ux-shell-manifest",
                "compliance-pack-overlay",
                "observability-audit-stream",
                "finops-cost-dimension",
                "migration-import-declaration",
                "support-runbook-reference",
            ]
        );
        assert_eq!(
            view.enterprise
                .capability_tiers
                .iter()
                .find(|tier| tier.id == "migration-import-declaration")
                .unwrap()
                .status,
            "Future work"
        );
        assert!(view.enterprise.summary.contains("enterprise gates ready"));
    }

    #[test]
    fn readiness_cards_are_live_rust_contract() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
                .with_auth_provider_configured(true)
                .with_archive_configured(true)
                .with_enterprise_operations_configured(true),
        );
        let cards = &view.payroll.readiness_cards;
        let ids = cards.iter().map(|card| card.id).collect::<Vec<_>>();

        assert_eq!(
            ids,
            vec![
                "rust-api",
                "rust-execution",
                "tenant-scope",
                "auth-provider",
                "archive-storage",
            ]
        );
        assert!(cards.iter().all(|card| card.source == "crates/payroll-api"));
        assert!(cards.iter().all(|card| !card.title.is_empty()));
        assert!(cards.iter().all(|card| !card.value.is_empty()));
        assert!(cards.iter().all(|card| !card.detail.is_empty()));
        assert_eq!(cards[2].detail, "Acme / Seoul / 2026-06");
        assert_eq!(view.work_queue[0].id, "confirm-payroll-close");
    }

    #[test]
    fn missing_production_prerequisites_surface_blockers() {
        let view = build_platform_live_view(PlatformLiveConfig::default());
        let blocker_ids = view
            .work_queue
            .iter()
            .map(|item| item.id)
            .collect::<Vec<_>>();

        assert_eq!(view.payroll.readiness.state, ReadinessState::NotReady);
        assert!(!view.payroll.scope.configured);
        assert!(blocker_ids.contains(&"set-payroll-scope"));
        assert!(blocker_ids.contains(&"complete-access-setup"));
        assert_eq!(view.session.mode, "local_readonly");
        assert!(!view.session.authenticated);
        assert_eq!(view.session.role, "unauthenticated");
    }

    #[test]
    fn auth_provider_flag_alone_does_not_authenticate_session() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
                .with_auth_provider_configured(true),
        );

        assert_eq!(view.session.mode, "auth_required");
        assert!(!view.session.authenticated);
        assert_eq!(view.session.role, "unauthenticated");
    }

    #[test]
    fn verified_jwt_without_webauthn_does_not_authenticate_session() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
                .with_auth_provider_configured(true)
                .with_verified_session(true, "payroll_operator")
                .with_webauthn_user_verified(false),
        );

        assert_eq!(view.session.mode, "auth_required");
        assert!(!view.session.authenticated);
        assert_eq!(view.session.role, "unauthenticated");
    }

    #[test]
    fn verified_jwt_with_missing_registered_claims_does_not_authenticate_session() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
                .with_auth_provider_configured(true)
                .with_verified_session(true, "payroll_operator")
                .with_jwt_claims("", "bitween-platform", "user-live-ops", 4_102_444_800),
        );

        assert_eq!(view.session.mode, "auth_required");
        assert!(!view.session.authenticated);
        assert_eq!(view.session.role, "unauthenticated");
    }

    #[test]
    fn expired_verified_jwt_does_not_authenticate_session() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
                .with_auth_provider_configured(true)
                .with_verified_session(true, "payroll_operator")
                .with_jwt_claims(
                    "https://auth.bitween.local",
                    "bitween-platform",
                    "user-live-ops",
                    1,
                ),
        );

        assert_eq!(view.session.mode, "auth_required");
        assert!(!view.session.authenticated);
        assert_eq!(view.session.role, "unauthenticated");
    }

    #[test]
    fn verified_jwt_and_webauthn_without_acr_does_not_authenticate_session() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
                .with_auth_provider_configured(true)
                .with_verified_session(true, "payroll_operator")
                .with_acr_level("", 0),
        );

        assert_eq!(view.session.mode, "auth_required");
        assert!(!view.session.authenticated);
        assert_eq!(view.session.role, "unauthenticated");
    }

    #[test]
    fn verified_jwt_and_webauthn_with_future_acr_event_does_not_authenticate_session() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
                .with_auth_provider_configured(true)
                .with_verified_session(true, "payroll_operator")
                .with_acr_level("elevated", 4_102_444_800),
        );

        assert_eq!(view.session.mode, "auth_required");
        assert!(!view.session.authenticated);
        assert_eq!(view.session.role, "unauthenticated");
    }

    #[test]
    fn verified_jwt_and_webauthn_authenticate_session() {
        let view = build_platform_live_view(
            PlatformLiveConfig::default()
                .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
                .with_auth_provider_configured(true)
                .with_verified_session(true, "payroll_operator"),
        );

        assert_eq!(view.session.mode, "authenticated");
        assert!(view.session.authenticated);
        assert_eq!(view.session.role, "payroll_operator");
    }

    #[test]
    fn session_step_up_policy_blocks_sensitive_payroll_work_without_sensitive_acr() {
        let elevated = PlatformLiveConfig::default()
            .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
            .with_auth_provider_configured(true)
            .with_verified_session(true, "payroll_operator");
        let sensitive = elevated.clone().with_acr_level("sensitive", 1);

        assert!(elevated.session_allows_sensitive_operation(AuthSensitiveOperation::ReadWorkspace));
        assert!(elevated.session_allows_sensitive_operation(AuthSensitiveOperation::HrEmployeeWrite));
        assert!(!elevated.session_allows_sensitive_operation(AuthSensitiveOperation::PayrollRun));
        assert!(!elevated.session_allows_sensitive_operation(AuthSensitiveOperation::PayrollExport));
        assert!(sensitive.session_allows_sensitive_operation(AuthSensitiveOperation::PayrollRun));
        assert!(sensitive.session_allows_sensitive_operation(AuthSensitiveOperation::PayrollExport));
        assert!(!sensitive.session_allows_sensitive_operation(
            AuthSensitiveOperation::TenantDestructiveChange
        ));
    }

    #[test]
    fn session_authorization_requires_rbac_abac_pbac_and_step_up() {
        let mut payroll = PlatformLiveConfig::default()
            .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
            .with_auth_provider_configured(true)
            .with_verified_session(true, "payroll_operator")
            .with_acr_level("sensitive", 1);
        payroll.attendance_closed = true;
        payroll.payroll_inputs_closed = true;
        payroll.deductions_reviewed = true;

        assert!(payroll.session_authorizes_operation(AuthSensitiveOperation::PayrollRun));
        assert!(!payroll.session_authorizes_operation(AuthSensitiveOperation::PayrollExport));

        let approved = payroll.clone().with_payroll_workstream_completed(true);
        assert!(approved.session_authorizes_operation(AuthSensitiveOperation::PayrollExport));

        let wrong_scope =
            payroll
                .clone()
                .with_authorization_scope(AUTHZ_POLICY_ID, "tenant-other", "Acme", "Seoul");
        assert!(!wrong_scope.session_authorizes_operation(AuthSensitiveOperation::PayrollRun));

        let wrong_legal_entity =
            payroll
                .clone()
                .with_authorization_scope(AUTHZ_POLICY_ID, "tenant-acme", "OTHER", "Seoul");
        assert!(
            !wrong_legal_entity.session_authorizes_operation(AuthSensitiveOperation::PayrollRun)
        );

        let mut unknown_role = payroll.clone();
        unknown_role.session_actor_role = "superuser".to_owned();
        assert!(!unknown_role.session_authorizes_operation(AuthSensitiveOperation::PayrollRun));

        let policy_change = payroll.clone();
        assert!(
            !policy_change.session_authorizes_operation(AuthSensitiveOperation::PayrollPolicyChange)
        );
    }

    #[test]
    fn workflow_state_requires_the_full_flag_prefix_chain() {
        // Walk the lifecycle flags strictly in order. Each stage must observe
        // its own state only once every earlier flag is set, including the
        // ApprovalPending stage that an earlier prefix-demotion bug skipped.
        let mut config = PlatformLiveConfig::default();
        assert_eq!(config.payroll_auth_workflow_state(), AuthWorkflowState::Open);

        config.payroll_inputs_closed = true;
        config.attendance_closed = true;
        config.deductions_reviewed = true;
        assert_eq!(
            config.payroll_auth_workflow_state(),
            AuthWorkflowState::InputsClosed
        );

        config.payroll_calculated = true;
        assert_eq!(
            config.payroll_auth_workflow_state(),
            AuthWorkflowState::Calculated
        );

        config.approval_requested = true;
        assert_eq!(
            config.payroll_auth_workflow_state(),
            AuthWorkflowState::ApprovalPending
        );

        config.payout_prepared = true;
        assert_eq!(
            config.payroll_auth_workflow_state(),
            AuthWorkflowState::Approved
        );

        config.payroll_evidence_archived = true;
        assert_eq!(
            config.payroll_auth_workflow_state(),
            AuthWorkflowState::Archived
        );
    }

    #[test]
    fn lone_advanced_flags_without_prefix_are_inconsistent() {
        // A flag set without its required prefix must fail closed to
        // Inconsistent rather than demoting to the last consistent prefix state.
        let mut payout_only = PlatformLiveConfig::default();
        payout_only.payout_prepared = true;
        assert_eq!(
            payout_only.payroll_auth_workflow_state(),
            AuthWorkflowState::Inconsistent
        );

        let mut approval_without_calculated = PlatformLiveConfig::default();
        approval_without_calculated.payroll_inputs_closed = true;
        approval_without_calculated.attendance_closed = true;
        approval_without_calculated.deductions_reviewed = true;
        approval_without_calculated.approval_requested = true;
        assert_eq!(
            approval_without_calculated.payroll_auth_workflow_state(),
            AuthWorkflowState::Inconsistent
        );

        let mut calculated_without_inputs = PlatformLiveConfig::default();
        calculated_without_inputs.payroll_calculated = true;
        assert_eq!(
            calculated_without_inputs.payroll_auth_workflow_state(),
            AuthWorkflowState::Inconsistent
        );

        let mut archived_without_payout = PlatformLiveConfig::default();
        archived_without_payout.payroll_inputs_closed = true;
        archived_without_payout.attendance_closed = true;
        archived_without_payout.deductions_reviewed = true;
        archived_without_payout.payroll_calculated = true;
        archived_without_payout.approval_requested = true;
        archived_without_payout.payroll_evidence_archived = true;
        assert_eq!(
            archived_without_payout.payroll_auth_workflow_state(),
            AuthWorkflowState::Inconsistent
        );
    }

    #[test]
    fn inconsistent_workflow_state_denies_windowed_operations() {
        // An inconsistent flag combination (approval_requested without the
        // calculated chain) must deny every explicitly-windowed operation with
        // pbac_workflow_denied, even for a platform owner with critical ACR.
        let mut owner = PlatformLiveConfig::default()
            .with_scope("tenant-acme", "Acme", "Acme", "Seoul", "2026-06")
            .with_auth_provider_configured(true)
            .with_verified_session(true, "platform_owner")
            .with_acr_level("critical", 1);
        owner.payroll_inputs_closed = true;
        owner.attendance_closed = true;
        owner.deductions_reviewed = true;
        owner.approval_requested = true; // calculated chain is missing

        assert_eq!(
            owner.payroll_auth_workflow_state(),
            AuthWorkflowState::Inconsistent
        );
        for operation in [
            AuthSensitiveOperation::PayrollRun,
            AuthSensitiveOperation::PayrollExport,
            AuthSensitiveOperation::ApprovalSigning,
            AuthSensitiveOperation::WorkflowTemplateWrite,
        ] {
            let decision = owner.session_authorization_decision(operation);
            assert!(!decision.allowed, "{} must deny in inconsistent state", operation.id());
            assert_eq!(
                decision.reason,
                "pbac_workflow_denied",
                "{} must be pbac_workflow_denied in inconsistent state",
                operation.id()
            );
        }
    }
}
