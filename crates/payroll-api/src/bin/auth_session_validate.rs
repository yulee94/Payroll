use std::env;
use std::time::{SystemTime, UNIX_EPOCH};

use bitween_payroll_api::{
    AuthSessionVerification, AuthSessionVerifierConfig, OidcDiscoveryVerifierConfig,
    PostgresRepositoryConfig, PostgresTenantScope, WebAuthnAssertionInput,
    WebAuthnAssertionVerifierConfig, auth_session_event_insert_sql,
    auth_session_revocation_lookup_sql, required_postgres_migrations, validate_oidc_discovery,
    verify_jwt_session, verify_webauthn_assertion,
};
use sha2::{Digest, Sha256};

fn main() {
    let token = env::var("BITWEEN_SESSION_JWT").unwrap_or_default();
    let jwks_json = env::var("BITWEEN_AUTH_JWKS_JSON").unwrap_or_default();
    let expected_issuer = env::var("BITWEEN_AUTH_EXPECTED_ISSUER").unwrap_or_default();
    let expected_audience = env::var("BITWEEN_AUTH_EXPECTED_AUDIENCE").unwrap_or_default();
    let now_unix = env::var("BITWEEN_SESSION_NOW_UNIX")
        .ok()
        .and_then(|value| value.parse::<u64>().ok())
        .unwrap_or_else(current_unix_seconds);

    let mut verification = verify_jwt_session(
        &token,
        &jwks_json,
        &AuthSessionVerifierConfig::new(expected_issuer, expected_audience, now_unix),
    );
    if verification.verified {
        if let Err(reason) = enforce_oidc_discovery_if_configured() {
            verification = AuthSessionVerification::denied(reason);
        }
    }
    if verification.verified {
        if let Err(reason) = enforce_webauthn_assertion_if_configured(now_unix) {
            verification = AuthSessionVerification::denied(reason);
        }
    }
    if verification.verified {
        match session_security_mode() {
            Ok(SessionSecurityMode::Off) => {}
            Ok(SessionSecurityMode::Postgres) => {
                if let Err(reason) = enforce_postgres_session_security(&verification) {
                    verification = AuthSessionVerification::denied(reason);
                }
            }
            Err(reason) => {
                verification = AuthSessionVerification::denied(reason);
            }
        }
    }
    println!(
        "{}",
        serde_json::to_string(&verification).expect("auth session verification JSON")
    );
    if !verification.verified {
        std::process::exit(2);
    }
}

fn enforce_oidc_discovery_if_configured() -> Result<(), &'static str> {
    let discovery_json = env::var("BITWEEN_AUTH_OIDC_CONFIGURATION_JSON").unwrap_or_default();
    if discovery_json.trim().is_empty() {
        return Ok(());
    }
    let expected_issuer = env::var("BITWEEN_AUTH_EXPECTED_ISSUER").unwrap_or_default();
    let expected_jwks_uri = env::var("BITWEEN_AUTH_EXPECTED_JWKS_URI")
        .ok()
        .filter(|value| !value.trim().is_empty());
    let validation = validate_oidc_discovery(
        &discovery_json,
        &OidcDiscoveryVerifierConfig::new(expected_issuer, expected_jwks_uri),
    );
    if validation.verified {
        Ok(())
    } else {
        Err(validation.reason)
    }
}

fn enforce_webauthn_assertion_if_configured(now_unix: u64) -> Result<(), &'static str> {
    let assertion_json = env::var("BITWEEN_WEBAUTHN_ASSERTION_JSON").unwrap_or_default();
    if assertion_json.trim().is_empty() {
        return Ok(());
    }
    let assertion = serde_json::from_str::<WebAuthnAssertionInput>(&assertion_json)
        .map_err(|_| "webauthn_assertion_invalid")?;
    let config = WebAuthnAssertionVerifierConfig::new(
        env::var("BITWEEN_WEBAUTHN_RP_ID").unwrap_or_default(),
        env::var("BITWEEN_WEBAUTHN_EXPECTED_ORIGIN").unwrap_or_default(),
        env::var("BITWEEN_WEBAUTHN_CHALLENGE").unwrap_or_default(),
        env::var("BITWEEN_WEBAUTHN_CHALLENGE_ISSUED_AT_UNIX")
            .ok()
            .and_then(|value| value.parse::<u64>().ok())
            .unwrap_or_default(),
        now_unix,
        env::var("BITWEEN_WEBAUTHN_PREVIOUS_SIGN_COUNT")
            .ok()
            .and_then(|value| value.parse::<u32>().ok())
            .unwrap_or_default(),
        env::var("BITWEEN_WEBAUTHN_CREDENTIAL_PUBLIC_KEY_X").unwrap_or_default(),
        env::var("BITWEEN_WEBAUTHN_CREDENTIAL_PUBLIC_KEY_Y").unwrap_or_default(),
    );
    let verification = verify_webauthn_assertion(&assertion, &config);
    if verification.verified {
        Ok(())
    } else {
        Err(verification.reason)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum SessionSecurityMode {
    Off,
    Postgres,
}

fn session_security_mode() -> Result<SessionSecurityMode, &'static str> {
    match env::var("BITWEEN_AUTH_SESSION_SECURITY_MODE")
        .unwrap_or_default()
        .trim()
        .replace('_', "-")
        .to_ascii_lowercase()
        .as_str()
    {
        "" | "off" | "disabled" => Ok(SessionSecurityMode::Off),
        "postgres" | "postgresql" => Ok(SessionSecurityMode::Postgres),
        _ => Err("auth_session_security_mode_invalid"),
    }
}

fn enforce_postgres_session_security(
    verification: &AuthSessionVerification,
) -> Result<(), &'static str> {
    let dsn = env::var("BITWEEN_POSTGRES_DSN").ok();
    if dsn.as_deref().unwrap_or_default().trim().is_empty() {
        return Err("auth_session_security_store_required");
    }
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|_| "auth_session_security_runtime_failed")?;
    runtime.block_on(enforce_postgres_session_security_async(verification, dsn))
}

async fn enforce_postgres_session_security_async(
    verification: &AuthSessionVerification,
    dsn: Option<String>,
) -> Result<(), &'static str> {
    let config = PostgresRepositoryConfig::from_env_parts(
        dsn,
        env::var("BITWEEN_POSTGRES_TLS_POLICY").ok(),
    )
    .map_err(|_| "auth_session_security_store_config_invalid")?;
    let scope = PostgresTenantScope::new(
        verification.authorized_tenant_id.clone(),
        verification.authorized_legal_entity.clone(),
        verification.authorized_workplace.clone(),
    )
    .map_err(|_| "auth_session_security_scope_invalid")?;
    let session = config
        .connect_client_session(scope)
        .await
        .map_err(|_| "auth_session_security_store_unavailable")?;
    session
        .apply_required_migrations(&required_postgres_migrations())
        .await
        .map_err(|_| "auth_session_security_migration_failed")?;
    if session
        .client
        .query_opt(
            auth_session_revocation_lookup_sql(),
            &[&verification.authorized_tenant_id, &verification.jwt_id_sha256],
        )
        .await
        .map_err(|_| "auth_session_revocation_lookup_failed")?
        .is_some()
    {
        return Err("jwt_revoked");
    }
    let subject_sha256 = hex_sha256(&verification.subject);
    let metadata = "{}";
    let expires_at_unix = i64::try_from(verification.expires_at_unix)
        .map_err(|_| "auth_session_expiration_invalid")?;
    session
        .client
        .execute(
            auth_session_event_insert_sql(),
            &[
                &verification.authorized_tenant_id,
                &verification.authorized_legal_entity,
                &verification.authorized_workplace,
                &verification.jwt_id_sha256,
                &subject_sha256,
                &verification.issuer,
                &verification.audience,
                &verification.key_id,
                &verification.algorithm,
                &"verified",
                &verification.reason,
                &verification.acr_level,
                &verification.role,
                &expires_at_unix,
                &metadata,
            ],
        )
        .await
        .map_err(|_| "auth_session_event_audit_failed")?;
    Ok(())
}

fn current_unix_seconds() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or_default()
}

fn hex_sha256(value: &str) -> String {
    let digest = Sha256::digest(value.as_bytes());
    digest.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use bitween_payroll_api::{AuthSessionVerifierConfig, verify_jwt_session};

    const TEST_TOKEN: &str = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InRlc3Qta2V5LTEifQ.eyJpc3MiOiJodHRwczovL2F1dGguYWNtZS5leGFtcGxlIiwic3ViIjoidXNlci1saXZlLW9wcyIsImF1ZCI6ImJpdHdlZW4tcGxhdGZvcm0iLCJleHAiOjQxMDI0NDQ4MDAsIm5iZiI6MTcwMDAwMDAwMCwiaWF0IjoxNzAwMDAwMDAwLCJqdGkiOiJzZXNzaW9uLXRva2VuLTAwMSIsImFjciI6InNlbnNpdGl2ZSIsImF1dGhfdGltZSI6MTcwMDAwMDAwMCwiYW1yIjpbInB3ZCIsIndlYmF1dGhuIl0sImJpdHdlZW5fcm9sZSI6InBheXJvbGxfbWFuYWdlciIsImJpdHdlZW5fdGVuYW50X2lkIjoidGVuYW50LWFjbWUiLCJiaXR3ZWVuX2xlZ2FsX2VudGl0eSI6IkFjbWUiLCJiaXR3ZWVuX3dvcmtwbGFjZSI6IlNlb3VsIn0.C5cBG8-5NUAfjf2zzua4IvNtYSLs11eHTF96G1kwSSDxfsBNCBw731oJAbxGmnlzZi9RVZTH0bjC2sf5ldqIb5T0g2z3KyH7V1DeMg0uZERm7J4evWaJ3VnHh5RYEgO06mM7zD9XBU7hS4-_32Ol1wQ4KPuoH9wfTc9798YKTlIIm_hYgH42IUoB_Snws2GgdVJ-CwnCKwZubIJ_bdPj8c6UXREaxlz6Up5Z8Xfgfbtrt5ENnAmCe4NX6Uy605ukwzVUSK7pep7wD-u6UAB0k2SbSAEz-oL_6CiYJcHLx5CVHl4BceaB_coaGL4mdOw-nflOelaL8GPDN-jhS5NiJw";
    const TEST_JWKS: &str = r#"{"keys":[{"kty":"RSA","n":"mwaczqZWd1GkBo8DQtJAEjFd4v4XGkBQt1KI7Flawe0lW9omwfolE6dut3Rrff4qhI3ncSjIOlf8NZ4EMmkH5wL6ktdRj0MWpDvSj7ZPAi1RvdKL6KrUGxpMtQymivPn2dd37KtaxZB4vbXYMU8vPJki3tjpI3bGNePRvmd8eYP2h5QmDXZFcqZJZ3oBIzKxH7NFjgZUetysXNvZLKqvLdnez_uCD83KoqV81l97IMJCHFBmoTnO3wyD0QXnBvNbyW7Sat8ekgx9PHuv8AhWjze9di4dy7n-Im2fN7Mry0afvFCpxmqj-vqVru8igUw13ngqq9vxjQ047zs5SWMMgQ","e":"AQAB","kid":"test-key-1","alg":"RS256","use":"sig"}]}"#;

    #[test]
    fn binary_uses_shared_verifier_contract() {
        let verification = verify_jwt_session(
            TEST_TOKEN,
            TEST_JWKS,
            &AuthSessionVerifierConfig::new(
                "https://auth.acme.example",
                "bitween-platform",
                1_800_000_000,
            ),
        );

        assert!(verification.verified);
        assert_eq!(verification.role, "payroll_manager");
    }

    #[test]
    fn subject_hash_is_stable_hex_without_exposing_subject() {
        let hash = hex_sha256("user-live-ops");

        assert_eq!(hash.len(), 64);
        assert_ne!(hash, "user-live-ops");
        assert!(hash.chars().all(|character| character.is_ascii_hexdigit()));
        assert_eq!(hash, hex_sha256("user-live-ops"));
    }

    #[test]
    fn postgres_security_sql_contract_uses_hashed_jti_lookup_and_audit_insert() {
        assert_eq!(
            auth_session_revocation_lookup_sql(),
            "SELECT 1 FROM bitween_auth.jwt_revocation WHERE tenant_id = $1 AND jwt_id_sha256 = $2 AND expires_at > now() LIMIT 1"
        );
        assert!(auth_session_event_insert_sql().contains("bitween_auth.session_event_audit"));
        assert!(auth_session_event_insert_sql().contains("jwt_id_sha256"));
        assert!(!auth_session_event_insert_sql().to_ascii_lowercase().contains("raw_token"));
    }
}
