#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UserPreferencePostgresContract {
    pub schema_version: &'static str,
    pub migration_name: &'static str,
    pub migration_sql: &'static str,
    pub tables: &'static [&'static str],
}

pub const USER_PREFERENCE_POSTGRES_SCHEMA_VERSION: &str = "bitween.settings.postgres.v1";
pub const USER_PREFERENCE_STORE_SCHEMA: &str = "bitween.user-preferences.v1";
pub const USER_PREFERENCE_POSTGRES_MIGRATION_NAME: &str = "004_user_preferences.sql";
pub const USER_PREFERENCE_POSTGRES_MIGRATION_SQL: &str =
    include_str!("../migrations/004_user_preferences.sql");

pub const USER_PREFERENCE_POSTGRES_TABLES: &[&str] = &["bitween_settings.user_preference"];

pub fn user_preference_postgres_contract() -> UserPreferencePostgresContract {
    UserPreferencePostgresContract {
        schema_version: USER_PREFERENCE_POSTGRES_SCHEMA_VERSION,
        migration_name: USER_PREFERENCE_POSTGRES_MIGRATION_NAME,
        migration_sql: USER_PREFERENCE_POSTGRES_MIGRATION_SQL,
        tables: USER_PREFERENCE_POSTGRES_TABLES,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn user_preference_postgres_schema_declares_preference_table() {
        let contract = user_preference_postgres_contract();

        assert_eq!(contract.schema_version, "bitween.settings.postgres.v1");
        assert_eq!(USER_PREFERENCE_STORE_SCHEMA, "bitween.user-preferences.v1");
        assert_eq!(contract.migration_name, "004_user_preferences.sql");
        for table in contract.tables {
            assert!(
                contract.migration_sql.contains(table),
                "missing table declaration for {table}"
            );
        }
    }

    #[test]
    fn user_preference_postgres_schema_is_tenant_scoped_and_korean_first() {
        let sql = USER_PREFERENCE_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("CREATE TABLE IF NOT EXISTS bitween_settings.user_preference"));
        assert!(sql.contains("locale text NOT NULL DEFAULT 'ko-KR'"));
        assert!(sql.contains("'ko-KR', 'en-US', 'zh-Hans-CN', 'ja-JP'"));
        assert!(sql.contains("sidebar_theme text NOT NULL DEFAULT 'steel'"));
        assert!(sql.contains("workspace_density text NOT NULL DEFAULT 'work_dense'"));
        assert!(sql.contains("UNIQUE (tenant_id, user_id)"));
        assert!(sql.contains("ALTER TABLE bitween_settings.user_preference ENABLE ROW LEVEL SECURITY"));
        assert!(sql.contains("ALTER TABLE bitween_settings.user_preference FORCE ROW LEVEL SECURITY"));
        assert!(sql.contains("current_setting('bitween.tenant_id', true)"));
    }
}
