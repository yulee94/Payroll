#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RlsEnforcementPostgresContract {
    pub schema_version: &'static str,
    pub migration_name: &'static str,
    pub migration_sql: &'static str,
    pub forced_tables: &'static [&'static str],
}

pub const RLS_ENFORCEMENT_POSTGRES_SCHEMA_VERSION: &str = "bitween.rls-enforcement.postgres.v1";
pub const RLS_ENFORCEMENT_POSTGRES_MIGRATION_NAME: &str = "008_rls_force_and_employee_scope.sql";
pub const RLS_ENFORCEMENT_POSTGRES_MIGRATION_SQL: &str =
    include_str!("../migrations/008_rls_force_and_employee_scope.sql");

/// Every tenant-scoped table that migrations 001-007 placed under
/// `ENABLE ROW LEVEL SECURITY`. Migration 008 must additionally `FORCE` RLS on each so
/// the owning role cannot bypass tenant isolation. The list mirrors the per-schema
/// `*_POSTGRES_TABLES` consts; it is restated here so the FORCE coverage is a single
/// auditable contract.
pub const RLS_ENFORCEMENT_POSTGRES_FORCED_TABLES: &[&str] = &[
    // 001_archive_intake.sql
    "bitween_archive.archive_intake",
    "bitween_archive.archive_intake_version",
    "bitween_archive.archive_intake_issue",
    "bitween_archive.archive_mapping_template",
    "bitween_archive.hr_employee_staging",
    "bitween_archive.hr_attendance_staging",
    "bitween_archive.payroll_input_staging",
    "bitween_archive.archive_admission_audit",
    // 002_workflow_templates.sql
    "bitween_workflow.workflow_template",
    "bitween_workflow.workflow_template_version",
    "bitween_workflow.workflow_node",
    "bitween_workflow.workflow_edge",
    "bitween_workflow.workflow_publish_check",
    "bitween_workflow.workflow_audit_event",
    "bitween_workflow.workflow_runtime_instance",
    "bitween_workflow.workflow_data_record",
    // 003_hr_employee.sql
    "bitween_hr.employee",
    // 004_user_preferences.sql
    "bitween_settings.user_preference",
    // 005_payroll_attendance_intake.sql
    "bitween_hr.attendance_record",
    "bitween_payroll.payroll_input",
    // 006_archive_admission_rollback.sql
    "bitween_archive.archive_admission_recovery_point",
    "bitween_archive.archive_source_sync",
    "bitween_archive.archive_admission_rollback",
    // 007_auth_session_security.sql
    "bitween_auth.jwt_revocation",
    "bitween_auth.session_event_audit",
];

pub fn rls_enforcement_postgres_contract() -> RlsEnforcementPostgresContract {
    RlsEnforcementPostgresContract {
        schema_version: RLS_ENFORCEMENT_POSTGRES_SCHEMA_VERSION,
        migration_name: RLS_ENFORCEMENT_POSTGRES_MIGRATION_NAME,
        migration_sql: RLS_ENFORCEMENT_POSTGRES_MIGRATION_SQL,
        forced_tables: RLS_ENFORCEMENT_POSTGRES_FORCED_TABLES,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::archive_intake_schema::ARCHIVE_INTAKE_POSTGRES_TABLES;
    use crate::archive_rollback_schema::ARCHIVE_ROLLBACK_POSTGRES_TABLES;
    use crate::auth_session_schema::AUTH_SESSION_POSTGRES_TABLES;
    use crate::hr_employee_schema::HR_EMPLOYEE_POSTGRES_TABLES;
    use crate::payroll_attendance_schema::PAYROLL_ATTENDANCE_POSTGRES_TABLES;
    use crate::user_preference_schema::USER_PREFERENCE_POSTGRES_TABLES;
    use crate::workflow_template_schema::WORKFLOW_TEMPLATE_POSTGRES_TABLES;

    #[test]
    fn rls_enforcement_schema_declares_migration_008_metadata() {
        let contract = rls_enforcement_postgres_contract();

        assert_eq!(contract.schema_version, "bitween.rls-enforcement.postgres.v1");
        assert_eq!(contract.migration_name, "008_rls_force_and_employee_scope.sql");
        assert_eq!(contract.forced_tables.len(), 25);
    }

    #[test]
    fn rls_enforcement_forced_tables_cover_every_rls_enabled_table() {
        // The FORCE coverage must equal the union of every per-schema table list that
        // migrations 001-007 placed under ENABLE ROW LEVEL SECURITY.
        let mut expected: Vec<&str> = Vec::new();
        expected.extend_from_slice(ARCHIVE_INTAKE_POSTGRES_TABLES);
        expected.extend_from_slice(WORKFLOW_TEMPLATE_POSTGRES_TABLES);
        expected.extend_from_slice(HR_EMPLOYEE_POSTGRES_TABLES);
        expected.extend_from_slice(USER_PREFERENCE_POSTGRES_TABLES);
        expected.extend_from_slice(PAYROLL_ATTENDANCE_POSTGRES_TABLES);
        expected.extend_from_slice(ARCHIVE_ROLLBACK_POSTGRES_TABLES);
        expected.extend_from_slice(&AUTH_SESSION_POSTGRES_TABLES);
        expected.sort_unstable();

        let mut forced: Vec<&str> = RLS_ENFORCEMENT_POSTGRES_FORCED_TABLES.to_vec();
        forced.sort_unstable();

        assert_eq!(forced, expected);
    }

    #[test]
    fn rls_enforcement_schema_forces_rls_on_every_table() {
        let sql = RLS_ENFORCEMENT_POSTGRES_MIGRATION_SQL;

        for table in RLS_ENFORCEMENT_POSTGRES_FORCED_TABLES {
            assert!(
                sql.contains(&format!("ALTER TABLE {table} FORCE ROW LEVEL SECURITY")),
                "missing RLS force for {table}; table owners bypass RLS without FORCE"
            );
        }
    }

    #[test]
    fn rls_enforcement_schema_swaps_employee_unique_key_to_full_scope() {
        let sql = RLS_ENFORCEMENT_POSTGRES_MIGRATION_SQL;

        // Drop the old auto-named inline constraint from 003.
        assert!(sql.contains(
            "ALTER TABLE bitween_hr.employee\n  DROP CONSTRAINT IF EXISTS employee_tenant_id_employee_key_key;"
        ));
        // Add the named scope-inclusive constraint that the archive-intake upsert targets.
        assert!(sql.contains("ADD CONSTRAINT employee_tenant_scope_key"));
        assert!(sql.contains(
            "UNIQUE (tenant_id, legal_entity_id, workplace_id, employee_key)"
        ));
        // Re-runnable: the ADD is guarded against duplicate_object/duplicate_table.
        assert!(sql.contains("EXCEPTION"));
        assert!(sql.contains("WHEN duplicate_table OR duplicate_object THEN NULL"));
    }

    #[test]
    fn rls_enforcement_schema_documents_checksum_stable_rationale() {
        let sql = RLS_ENFORCEMENT_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("postgres_migration_checksum_mismatch"));
        assert!(sql.contains("SEPARATE migration"));
        assert!(sql.contains("AFTER 003"));
    }
}
