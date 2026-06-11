#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ArchiveIntakePostgresContract {
    pub schema_version: &'static str,
    pub migration_name: &'static str,
    pub migration_sql: &'static str,
    pub tables: &'static [&'static str],
    pub staging_tables: &'static [&'static str],
}

pub const ARCHIVE_INTAKE_POSTGRES_SCHEMA_VERSION: &str = "bitween.archive.postgres.v1";
pub const ARCHIVE_INTAKE_STORE_SCHEMA: &str = "bitween.archive.intake-store.v1";
pub const ARCHIVE_SOURCE_SYNC_PLAN_SCHEMA: &str = "bitween.archive.source-sync-plan.v1";
pub const ARCHIVE_INTAKE_POSTGRES_MIGRATION_NAME: &str = "001_archive_intake.sql";
pub const ARCHIVE_INTAKE_POSTGRES_MIGRATION_SQL: &str =
    include_str!("../migrations/001_archive_intake.sql");

pub const ARCHIVE_INTAKE_POSTGRES_TABLES: &[&str] = &[
    "bitween_archive.archive_intake",
    "bitween_archive.archive_intake_version",
    "bitween_archive.archive_intake_issue",
    "bitween_archive.archive_mapping_template",
    "bitween_archive.hr_employee_staging",
    "bitween_archive.hr_attendance_staging",
    "bitween_archive.payroll_input_staging",
    "bitween_archive.archive_admission_audit",
];

pub const ARCHIVE_INTAKE_POSTGRES_STAGING_TABLES: &[&str] = &[
    "bitween_archive.hr_employee_staging",
    "bitween_archive.hr_attendance_staging",
    "bitween_archive.payroll_input_staging",
];

pub fn archive_intake_postgres_contract() -> ArchiveIntakePostgresContract {
    ArchiveIntakePostgresContract {
        schema_version: ARCHIVE_INTAKE_POSTGRES_SCHEMA_VERSION,
        migration_name: ARCHIVE_INTAKE_POSTGRES_MIGRATION_NAME,
        migration_sql: ARCHIVE_INTAKE_POSTGRES_MIGRATION_SQL,
        tables: ARCHIVE_INTAKE_POSTGRES_TABLES,
        staging_tables: ARCHIVE_INTAKE_POSTGRES_STAGING_TABLES,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn archive_intake_postgres_schema_declares_all_required_tables() {
        let contract = archive_intake_postgres_contract();

        assert_eq!(contract.schema_version, "bitween.archive.postgres.v1");
        assert_eq!(ARCHIVE_INTAKE_STORE_SCHEMA, "bitween.archive.intake-store.v1");
        assert_eq!(
            ARCHIVE_SOURCE_SYNC_PLAN_SCHEMA,
            "bitween.archive.source-sync-plan.v1"
        );
        assert_eq!(contract.migration_name, "001_archive_intake.sql");
        for table in contract.tables {
            assert!(
                contract.migration_sql.contains(table),
                "missing table declaration for {table}"
            );
        }
        for table in contract.staging_tables {
            assert!(
                contract.migration_sql.contains(table),
                "missing staging table declaration for {table}"
            );
        }
    }

    #[test]
    fn archive_intake_postgres_schema_requires_rustfs_and_checksum_metadata() {
        let sql = ARCHIVE_INTAKE_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("object_uri text NOT NULL CHECK (object_uri LIKE 'rustfs://%')"));
        assert!(sql.contains("content_sha256 char(64) NOT NULL"));
        assert!(sql.contains("content_sha256 ~ '^[0-9a-f]{64}$'"));
        assert!(sql.contains("object_bucket text NOT NULL"));
        assert!(sql.contains("object_key text NOT NULL"));
        let lowered = sql.to_lowercase();
        assert!(!lowered.contains(&("min".to_owned() + "io")));
        assert!(!lowered.contains(&("min".to_owned() + "io://")));
    }

    #[test]
    fn archive_intake_postgres_schema_persists_bounded_content_sample_evidence() {
        let sql = ARCHIVE_INTAKE_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("content_sample_sha256 char(64) NOT NULL"));
        assert!(sql.contains("content_sample_sha256 ~ '^[0-9a-f]{64}$'"));
        assert!(sql.contains("content_sample_row_count bigint NOT NULL DEFAULT 0"));
        assert!(sql.contains("content_sample_row_count >= 0"));
        assert!(sql.contains("redacted_content_sample_excerpt text NOT NULL DEFAULT ''"));
        assert!(sql.contains("char_length(redacted_content_sample_excerpt) <= 8192"));
        assert!(sql.contains("extraction_status text NOT NULL DEFAULT 'not_readable'"));
        assert!(sql.contains("extraction_status IN ('converted', 'needs_guidance', 'not_readable', 'not_applicable')"));
        assert!(!sql.to_lowercase().contains("sample_text bytea"));
    }

    #[test]
    fn archive_intake_postgres_schema_enforces_review_before_admission() {
        let sql = ARCHIVE_INTAKE_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("postgres_ready boolean NOT NULL DEFAULT false"));
        assert!(sql.contains("status = 'ready_for_staging'"));
        assert!(sql.contains("archive_intake_issue"));
        assert!(sql.contains("severity text NOT NULL CHECK (severity IN ('info', 'warning', 'blocking'))"));
        assert!(sql.contains("status text NOT NULL DEFAULT 'open'"));
        assert!(sql.contains("archive_admission_audit"));
        assert!(sql.contains("approved_by text NOT NULL"));
        assert!(sql.contains("rollback_ref jsonb NOT NULL DEFAULT '{}'::jsonb"));
    }

    #[test]
    fn archive_intake_postgres_schema_enforces_tenant_rls() {
        let sql = ARCHIVE_INTAKE_POSTGRES_MIGRATION_SQL;

        for table in ARCHIVE_INTAKE_POSTGRES_TABLES {
            assert!(
                sql.contains(&format!("ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")),
                "missing RLS enablement for {table}"
            );
            assert!(
                sql.contains(&format!("ALTER TABLE {table} FORCE ROW LEVEL SECURITY")),
                "missing RLS force for {table}; table owners bypass RLS without FORCE"
            );
        }
        assert!(sql.contains("current_setting('bitween.tenant_id', true)"));
        assert!(sql.contains("WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true))"));
    }
}
