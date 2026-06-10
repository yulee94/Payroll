use bitween_payroll_api::{AuthSensitiveOperation, PlatformLiveConfig};
use serde::Serialize;
use std::process;

const AUTHZ_DECISION_SCHEMA: &str = "bitween.authz-decision.v1";

#[derive(Debug, Serialize)]
struct RouteAuthorizationDecision {
    schema: &'static str,
    ok: bool,
    allowed: bool,
    operation: String,
    reason: &'static str,
    policy_id: Option<&'static str>,
    auth_policy_schema: Option<&'static str>,
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let operation = std::env::args()
        .nth(1)
        .ok_or_else(|| "missing authorization operation".to_owned())?;
    let decision = authorize_operation(&operation)?;
    let body = serde_json::to_string_pretty(&decision).map_err(|error| error.to_string())?;
    println!("{body}");
    Ok(())
}

fn authorize_operation(operation: &str) -> Result<RouteAuthorizationDecision, String> {
    let operation = AuthSensitiveOperation::parse(operation)
        .ok_or_else(|| format!("unsupported authorization operation: {operation}"))?;
    let config = PlatformLiveConfig::from_env();
    if !config.session_is_authenticated() {
        return Ok(RouteAuthorizationDecision {
            schema: AUTHZ_DECISION_SCHEMA,
            ok: true,
            allowed: false,
            operation: operation.id().to_owned(),
            reason: "session_not_authenticated",
            policy_id: None,
            auth_policy_schema: None,
        });
    }

    let policy = config.session_authorization_decision(operation);
    Ok(RouteAuthorizationDecision {
        schema: AUTHZ_DECISION_SCHEMA,
        ok: true,
        allowed: policy.allowed,
        operation: policy.operation.to_owned(),
        reason: policy.reason,
        policy_id: Some(policy.policy_id),
        auth_policy_schema: Some(policy.schema),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    static ENV_LOCK: Mutex<()> = Mutex::new(());

    fn with_env(vars: &[(&str, &str)], test: impl FnOnce()) {
        let _guard = ENV_LOCK.lock().unwrap();
        let previous = vars
            .iter()
            .map(|(key, _)| (*key, std::env::var(key).ok()))
            .collect::<Vec<_>>();
        for (key, _) in vars {
            unsafe { std::env::remove_var(key) };
        }
        for (key, value) in vars {
            unsafe { std::env::set_var(key, value) };
        }
        test();
        for (key, value) in previous {
            match value {
                Some(value) => unsafe { std::env::set_var(key, value) },
                None => unsafe { std::env::remove_var(key) },
            }
        }
    }

    fn verified_env() -> Vec<(&'static str, &'static str)> {
        vec![
            ("BITWEEN_TENANT_ID", "tenant-acme"),
            ("BITWEEN_TENANT_NAME", "Acme"),
            ("BITWEEN_PAYROLL_AFFILIATE", "Acme"),
            ("BITWEEN_PAYROLL_WORKPLACE", "Seoul"),
            ("BITWEEN_PAYROLL_PERIOD", "2026-06"),
            ("BITWEEN_AUTH_CONFIGURED", "true"),
            ("BITWEEN_SESSION_JWT_VERIFIED", "true"),
            ("BITWEEN_SESSION_JWT_ISSUER", "https://auth.example.com"),
            ("BITWEEN_SESSION_JWT_AUDIENCE", "bitween-platform"),
            ("BITWEEN_SESSION_JWT_SUBJECT", "user-live-ops"),
            ("BITWEEN_SESSION_JWT_EXPIRES_AT_UNIX", "4102444800"),
            ("BITWEEN_WEBAUTHN_USER_VERIFIED", "true"),
            ("BITWEEN_SESSION_ACR_LEVEL", "elevated"),
            ("BITWEEN_SESSION_ACR_EVENT_AT_UNIX", "1"),
            ("BITWEEN_SESSION_ROLE", "hr_operator"),
            (
                "BITWEEN_SESSION_AUTHZ_POLICY_ID",
                "bitween.authz.rbac-abac-pbac.v1",
            ),
            ("BITWEEN_SESSION_AUTHZ_TENANT_ID", "tenant-acme"),
            ("BITWEEN_SESSION_AUTHZ_LEGAL_ENTITY", "Acme"),
            ("BITWEEN_SESSION_AUTHZ_WORKPLACE", "Seoul"),
        ]
    }

    #[test]
    fn denies_when_session_is_not_authenticated() {
        let vars = verified_env();
        with_env(&vars, || {
            unsafe { std::env::remove_var("BITWEEN_SESSION_ACR_LEVEL") };
            let decision = authorize_operation("hr_employee_write").unwrap();
            assert!(!decision.allowed);
            assert_eq!(decision.reason, "session_not_authenticated");
            assert_eq!(decision.policy_id, None);
        });
    }

    #[test]
    fn allows_authorized_hr_write() {
        let vars = verified_env();
        with_env(&vars, || {
            let decision = authorize_operation("hr_employee_write").unwrap();
            assert!(decision.allowed);
            assert_eq!(decision.reason, "authorized");
            assert_eq!(decision.policy_id, Some("bitween.authz.rbac-abac-pbac.v1"));
        });
    }

    #[test]
    fn denies_mismatched_legal_entity_scope() {
        let mut vars = verified_env();
        for (key, value) in &mut vars {
            if *key == "BITWEEN_SESSION_AUTHZ_LEGAL_ENTITY" {
                *value = "OTHER";
            }
        }
        with_env(&vars, || {
            let decision = authorize_operation("hr_employee_read").unwrap();
            assert!(!decision.allowed);
            assert_eq!(decision.reason, "abac_scope_denied");
        });
    }

    #[test]
    fn denies_unsupported_operation() {
        assert!(authorize_operation("admin_override").is_err());
    }
}
