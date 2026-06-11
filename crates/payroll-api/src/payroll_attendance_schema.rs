#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PayrollAttendancePostgresContract {
    pub schema_version: &'static str,
    pub migration_name: &'static str,
    pub migration_sql: &'static str,
    pub tables: &'static [&'static str],
}

pub const PAYROLL_ATTENDANCE_POSTGRES_SCHEMA_VERSION: &str =
    "bitween.payroll-attendance.postgres.v1";
pub const PAYROLL_ATTENDANCE_POSTGRES_MIGRATION_NAME: &str =
    "005_payroll_attendance_intake.sql";
pub const PAYROLL_ATTENDANCE_POSTGRES_MIGRATION_SQL: &str =
    include_str!("../migrations/005_payroll_attendance_intake.sql");

pub const PAYROLL_ATTENDANCE_POSTGRES_TABLES: &[&str] = &[
    "bitween_hr.attendance_record",
    "bitween_payroll.payroll_input",
];

pub fn payroll_attendance_postgres_contract() -> PayrollAttendancePostgresContract {
    PayrollAttendancePostgresContract {
        schema_version: PAYROLL_ATTENDANCE_POSTGRES_SCHEMA_VERSION,
        migration_name: PAYROLL_ATTENDANCE_POSTGRES_MIGRATION_NAME,
        migration_sql: PAYROLL_ATTENDANCE_POSTGRES_MIGRATION_SQL,
        tables: PAYROLL_ATTENDANCE_POSTGRES_TABLES,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn payroll_attendance_postgres_schema_declares_canonical_tables() {
        let contract = payroll_attendance_postgres_contract();

        assert_eq!(
            contract.schema_version,
            "bitween.payroll-attendance.postgres.v1"
        );
        assert_eq!(
            contract.migration_name,
            "005_payroll_attendance_intake.sql"
        );
        for table in contract.tables {
            assert!(
                contract.migration_sql.contains(table),
                "missing table declaration for {table}"
            );
        }
    }

    #[test]
    fn payroll_attendance_postgres_schema_is_scoped_and_source_audited() {
        let sql = PAYROLL_ATTENDANCE_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("source_intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake"));
        assert!(sql.contains("source_row_hash char(64) NOT NULL"));
        assert!(sql.contains("source_payload jsonb NOT NULL"));
        assert!(sql.contains("ALTER TABLE bitween_hr.attendance_record ENABLE ROW LEVEL SECURITY"));
        assert!(sql.contains("ALTER TABLE bitween_hr.attendance_record FORCE ROW LEVEL SECURITY"));
        assert!(sql.contains("ALTER TABLE bitween_payroll.payroll_input ENABLE ROW LEVEL SECURITY"));
        assert!(sql.contains("ALTER TABLE bitween_payroll.payroll_input FORCE ROW LEVEL SECURITY"));
        assert!(sql.contains("current_setting('bitween.tenant_id', true)"));
        assert!(sql.contains("current_setting('bitween.legal_entity_id', true)"));
        assert!(sql.contains("current_setting('bitween.workplace_id', true)"));
    }
}
