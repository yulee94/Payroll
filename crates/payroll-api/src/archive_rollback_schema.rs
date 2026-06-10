#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ArchiveRollbackPostgresContract {
    pub schema_version: &'static str,
    pub migration_name: &'static str,
    pub migration_sql: &'static str,
    pub tables: &'static [&'static str],
}

pub const ARCHIVE_ROLLBACK_POSTGRES_SCHEMA_VERSION: &str =
    "bitween.archive-rollback.postgres.v1";
pub const ARCHIVE_ROLLBACK_POSTGRES_MIGRATION_NAME: &str =
    "006_archive_admission_rollback.sql";
pub const ARCHIVE_ROLLBACK_POSTGRES_MIGRATION_SQL: &str =
    include_str!("../migrations/006_archive_admission_rollback.sql");

pub const ARCHIVE_ROLLBACK_POSTGRES_TABLES: &[&str] =
    &[
        "bitween_archive.archive_admission_recovery_point",
        "bitween_archive.archive_source_sync",
        "bitween_archive.archive_admission_rollback",
    ];

pub fn archive_rollback_postgres_contract() -> ArchiveRollbackPostgresContract {
    ArchiveRollbackPostgresContract {
        schema_version: ARCHIVE_ROLLBACK_POSTGRES_SCHEMA_VERSION,
        migration_name: ARCHIVE_ROLLBACK_POSTGRES_MIGRATION_NAME,
        migration_sql: ARCHIVE_ROLLBACK_POSTGRES_MIGRATION_SQL,
        tables: ARCHIVE_ROLLBACK_POSTGRES_TABLES,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn archive_rollback_schema_declares_auditable_rollback_contract() {
        let contract = archive_rollback_postgres_contract();

        assert_eq!(
            contract.schema_version,
            "bitween.archive-rollback.postgres.v1"
        );
        assert_eq!(
            contract.migration_name,
            "006_archive_admission_rollback.sql"
        );
        for table in contract.tables {
            assert!(
                contract.migration_sql.contains(table),
                "missing table declaration for {table}"
            );
        }
    }

    #[test]
    fn archive_rollback_schema_keeps_source_lineage_and_tenant_rls() {
        let sql = ARCHIVE_ROLLBACK_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("ALTER TABLE bitween_hr.employee"));
        assert!(sql.contains("source_intake_id uuid REFERENCES bitween_archive.archive_intake"));
        assert!(sql.contains("source_row_hash char(64)"));
        assert!(sql.contains("source_payload jsonb NOT NULL DEFAULT '{}'::jsonb"));
        assert!(sql.contains("admission_status text NOT NULL DEFAULT 'admitted'"));
        assert!(sql.contains("archive_admission_recovery_point"));
        assert!(sql.contains("before_payload jsonb NOT NULL DEFAULT '{}'::jsonb"));
        assert!(sql.contains("after_payload jsonb NOT NULL"));
        assert!(sql.contains("recovery_status text NOT NULL DEFAULT 'available'"));
        assert!(sql.contains("archive_source_sync"));
        assert!(sql.contains("source_object_uri text NOT NULL CHECK (source_object_uri LIKE 'rustfs://%')"));
        assert!(sql.contains("generated_object_uri text CHECK"));
        assert!(sql.contains("target_table IN ('hr_employee', 'hr_attendance', 'payroll_input')"));
        assert!(sql.contains("ALTER TABLE bitween_archive.archive_admission_recovery_point ENABLE ROW LEVEL SECURITY"));
        assert!(sql.contains("ALTER TABLE bitween_archive.archive_source_sync ENABLE ROW LEVEL SECURITY"));
        assert!(sql.contains("ALTER TABLE bitween_archive.archive_admission_rollback ENABLE ROW LEVEL SECURITY"));
        assert!(sql.contains("archive_admission_recovery_point_tenant_isolation"));
        assert!(sql.contains("archive_source_sync_tenant_isolation"));
        assert!(sql.contains("archive_admission_rollback_tenant_isolation"));
        assert!(sql.contains("current_setting('bitween.tenant_id', true)"));
        assert!(!sql.to_ascii_lowercase().contains("bytea"));
    }
}
