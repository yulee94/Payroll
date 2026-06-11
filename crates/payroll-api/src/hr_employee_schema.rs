#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HrEmployeePostgresContract {
    pub schema_version: &'static str,
    pub migration_name: &'static str,
    pub migration_sql: &'static str,
    pub tables: &'static [&'static str],
}

pub const HR_EMPLOYEE_POSTGRES_SCHEMA_VERSION: &str = "bitween.hr.postgres.v1";
pub const HR_EMPLOYEE_STORE_SCHEMA: &str = "bitween.hr.employee-store.v1";
pub const HR_EMPLOYEE_POSTGRES_MIGRATION_NAME: &str = "003_hr_employee.sql";
pub const HR_EMPLOYEE_POSTGRES_MIGRATION_SQL: &str = include_str!("../migrations/003_hr_employee.sql");

pub const HR_EMPLOYEE_POSTGRES_TABLES: &[&str] = &["bitween_hr.employee"];

pub fn hr_employee_postgres_contract() -> HrEmployeePostgresContract {
    HrEmployeePostgresContract {
        schema_version: HR_EMPLOYEE_POSTGRES_SCHEMA_VERSION,
        migration_name: HR_EMPLOYEE_POSTGRES_MIGRATION_NAME,
        migration_sql: HR_EMPLOYEE_POSTGRES_MIGRATION_SQL,
        tables: HR_EMPLOYEE_POSTGRES_TABLES,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hr_employee_postgres_schema_declares_employee_table() {
        let contract = hr_employee_postgres_contract();

        assert_eq!(contract.schema_version, "bitween.hr.postgres.v1");
        assert_eq!(HR_EMPLOYEE_STORE_SCHEMA, "bitween.hr.employee-store.v1");
        assert_eq!(contract.migration_name, "003_hr_employee.sql");
        for table in contract.tables {
            assert!(
                contract.migration_sql.contains(table),
                "missing table declaration for {table}"
            );
        }
    }

    #[test]
    fn hr_employee_postgres_schema_enforces_scope_and_status() {
        let sql = HR_EMPLOYEE_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("CREATE TABLE IF NOT EXISTS bitween_hr.employee"));
        assert!(sql.contains("employee_key text NOT NULL"));
        assert!(sql.contains("employment_status text NOT NULL DEFAULT 'active'"));
        assert!(sql.contains("'active', 'on_leave', 'offboarding'"));
        assert!(sql.contains("sensitivity_label text NOT NULL DEFAULT 'restricted'"));
        assert!(sql.contains("ALTER TABLE bitween_hr.employee ENABLE ROW LEVEL SECURITY"));
        assert!(sql.contains("ALTER TABLE bitween_hr.employee FORCE ROW LEVEL SECURITY"));
        assert!(sql.contains("current_setting('bitween.tenant_id', true)"));
        assert!(sql.contains("current_setting('bitween.legal_entity_id', true)"));
        assert!(sql.contains("current_setting('bitween.workplace_id', true)"));
    }
}
