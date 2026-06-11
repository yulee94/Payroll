pub const AUTH_SESSION_POSTGRES_SCHEMA_VERSION: &str = "bitween.auth-session-postgres.v1";
pub const AUTH_SESSION_POSTGRES_MIGRATION_NAME: &str = "007_auth_session_security.sql";
pub const AUTH_SESSION_POSTGRES_MIGRATION_SQL: &str = include_str!("../migrations/007_auth_session_security.sql");
pub const AUTH_SESSION_POSTGRES_TABLES: [&str; 2] = [
    "bitween_auth.jwt_revocation",
    "bitween_auth.session_event_audit",
];

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AuthSessionPostgresContract {
    pub schema_version: &'static str,
    pub migration_name: &'static str,
    pub tables: &'static [&'static str],
    pub revocation_lookup_sql: &'static str,
    pub session_event_insert_sql: &'static str,
}

pub fn auth_session_postgres_contract() -> AuthSessionPostgresContract {
    AuthSessionPostgresContract {
        schema_version: AUTH_SESSION_POSTGRES_SCHEMA_VERSION,
        migration_name: AUTH_SESSION_POSTGRES_MIGRATION_NAME,
        tables: &AUTH_SESSION_POSTGRES_TABLES,
        revocation_lookup_sql: auth_session_revocation_lookup_sql(),
        session_event_insert_sql: auth_session_event_insert_sql(),
    }
}

pub fn auth_session_revocation_lookup_sql() -> &'static str {
    "SELECT 1 FROM bitween_auth.jwt_revocation WHERE tenant_id = $1 AND jwt_id_sha256 = $2 AND expires_at > now() LIMIT 1"
}

pub fn auth_session_event_insert_sql() -> &'static str {
    "INSERT INTO bitween_auth.session_event_audit (tenant_id, legal_entity_id, workplace_id, jwt_id_sha256, subject_sha256, issuer, audience, key_id, algorithm, verification_result, reason, acr_level, role, expires_at_unix, metadata) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15::jsonb)"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn auth_session_schema_declares_revocation_and_audit_tables() {
        let contract = auth_session_postgres_contract();

        assert_eq!(contract.schema_version, "bitween.auth-session-postgres.v1");
        assert_eq!(contract.migration_name, "007_auth_session_security.sql");
        assert_eq!(contract.tables, &AUTH_SESSION_POSTGRES_TABLES);
        assert!(AUTH_SESSION_POSTGRES_MIGRATION_SQL.contains("bitween_auth.jwt_revocation"));
        assert!(AUTH_SESSION_POSTGRES_MIGRATION_SQL.contains("bitween_auth.session_event_audit"));
        assert!(AUTH_SESSION_POSTGRES_MIGRATION_SQL.contains("jwt_id_sha256 char(64)"));
        assert!(AUTH_SESSION_POSTGRES_MIGRATION_SQL.contains("subject_sha256 char(64)"));
        assert!(!AUTH_SESSION_POSTGRES_MIGRATION_SQL.to_ascii_lowercase().contains("raw_token"));
        assert!(!AUTH_SESSION_POSTGRES_MIGRATION_SQL.to_ascii_lowercase().contains("access_token"));
    }

    #[test]
    fn auth_session_schema_enforces_tenant_rls() {
        for table in AUTH_SESSION_POSTGRES_TABLES {
            assert!(
                AUTH_SESSION_POSTGRES_MIGRATION_SQL
                    .contains(&format!("ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")),
                "missing RLS enablement for {table}"
            );
        }
        assert!(AUTH_SESSION_POSTGRES_MIGRATION_SQL.contains("jwt_revocation_tenant_isolation"));
        assert!(AUTH_SESSION_POSTGRES_MIGRATION_SQL.contains("session_event_audit_tenant_isolation"));
        assert!(AUTH_SESSION_POSTGRES_MIGRATION_SQL.contains("current_setting('bitween.tenant_id', true)"));
    }

    #[test]
    fn auth_session_sql_is_parameterized() {
        let lookup = auth_session_revocation_lookup_sql();
        let insert = auth_session_event_insert_sql();

        assert!(lookup.contains("tenant_id = $1"));
        assert!(lookup.contains("jwt_id_sha256 = $2"));
        assert!(insert.contains("VALUES ($1, $2, $3"));
        assert!(insert.contains("$15::jsonb"));
        assert!(!lookup.contains("format("));
        assert!(!insert.contains("format("));
    }
}
