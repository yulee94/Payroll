#[derive(Clone, Debug, Eq, PartialEq)]
pub struct WorkflowTemplatePostgresContract {
    pub schema_version: &'static str,
    pub migration_name: &'static str,
    pub migration_sql: &'static str,
    pub tables: &'static [&'static str],
    pub graph_tables: &'static [&'static str],
    pub audit_tables: &'static [&'static str],
}

pub const WORKFLOW_TEMPLATE_POSTGRES_SCHEMA_VERSION: &str = "bitween.workflow.postgres.v1";
pub const WORKFLOW_TEMPLATE_STORE_SCHEMA: &str = "bitween.workflow.template-store.v1";
pub const WORKFLOW_PREFLIGHT_SCHEMA: &str = "bitween.workflow.preflight.v1";
pub const WORKFLOW_EDIT_VALIDATION_SCHEMA: &str = "bitween.workflow.edit-validation.v1";
pub const WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_NAME: &str = "002_workflow_templates.sql";
pub const WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_SQL: &str =
    include_str!("../migrations/002_workflow_templates.sql");

pub const WORKFLOW_TEMPLATE_POSTGRES_TABLES: &[&str] = &[
    "bitween_workflow.workflow_template",
    "bitween_workflow.workflow_template_version",
    "bitween_workflow.workflow_node",
    "bitween_workflow.workflow_edge",
    "bitween_workflow.workflow_publish_check",
    "bitween_workflow.workflow_audit_event",
    "bitween_workflow.workflow_runtime_instance",
    "bitween_workflow.workflow_data_record",
];

pub const WORKFLOW_TEMPLATE_POSTGRES_GRAPH_TABLES: &[&str] = &[
    "bitween_workflow.workflow_template",
    "bitween_workflow.workflow_template_version",
    "bitween_workflow.workflow_node",
    "bitween_workflow.workflow_edge",
];

pub const WORKFLOW_TEMPLATE_POSTGRES_AUDIT_TABLES: &[&str] = &[
    "bitween_workflow.workflow_publish_check",
    "bitween_workflow.workflow_audit_event",
    "bitween_workflow.workflow_runtime_instance",
    "bitween_workflow.workflow_data_record",
];

pub fn workflow_template_postgres_contract() -> WorkflowTemplatePostgresContract {
    WorkflowTemplatePostgresContract {
        schema_version: WORKFLOW_TEMPLATE_POSTGRES_SCHEMA_VERSION,
        migration_name: WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_NAME,
        migration_sql: WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_SQL,
        tables: WORKFLOW_TEMPLATE_POSTGRES_TABLES,
        graph_tables: WORKFLOW_TEMPLATE_POSTGRES_GRAPH_TABLES,
        audit_tables: WORKFLOW_TEMPLATE_POSTGRES_AUDIT_TABLES,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn workflow_template_postgres_schema_declares_all_required_tables() {
        let contract = workflow_template_postgres_contract();

        assert_eq!(contract.schema_version, "bitween.workflow.postgres.v1");
        assert_eq!(WORKFLOW_TEMPLATE_STORE_SCHEMA, "bitween.workflow.template-store.v1");
        assert_eq!(WORKFLOW_PREFLIGHT_SCHEMA, "bitween.workflow.preflight.v1");
        assert_eq!(
            WORKFLOW_EDIT_VALIDATION_SCHEMA,
            "bitween.workflow.edit-validation.v1"
        );
        assert_eq!(contract.migration_name, "002_workflow_templates.sql");
        for table in contract.tables {
            assert!(
                contract.migration_sql.contains(table),
                "missing table declaration for {table}"
            );
        }
        for table in contract.graph_tables {
            assert!(
                contract.migration_sql.contains(table),
                "missing graph table declaration for {table}"
            );
        }
        for table in contract.audit_tables {
            assert!(
                contract.migration_sql.contains(table),
                "missing audit/runtime table declaration for {table}"
            );
        }
    }

    #[test]
    fn workflow_template_postgres_schema_models_editable_graphs() {
        let sql = WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("workflow_node"));
        assert!(sql.contains("workflow_edge"));
        assert!(sql.contains("from_node_id uuid NOT NULL REFERENCES bitween_workflow.workflow_node(id) ON DELETE CASCADE"));
        assert!(sql.contains("to_node_id uuid NOT NULL REFERENCES bitween_workflow.workflow_node(id) ON DELETE CASCADE"));
        assert!(sql.contains("CHECK (from_node_id <> to_node_id)"));
        assert!(sql.contains("position_x integer NOT NULL CHECK (position_x BETWEEN 0 AND 100)"));
        assert!(sql.contains("position_y integer NOT NULL CHECK (position_y BETWEEN 0 AND 100)"));
        assert!(sql.contains("condition_expression jsonb NOT NULL DEFAULT '{}'::jsonb"));
        assert!(sql.contains("permission_scope jsonb NOT NULL DEFAULT '{}'::jsonb"));
        assert!(sql.contains("edge_type text NOT NULL DEFAULT 'success'"));
    }

    #[test]
    fn workflow_template_postgres_schema_enforces_publish_audit_and_versioning() {
        let sql = WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("workflow_template_version"));
        assert!(sql.contains("graph_hash char(64) NOT NULL CHECK (graph_hash ~ '^[0-9a-f]{64}$')"));
        assert!(sql.contains("workflow_publish_check"));
        assert!(sql.contains("severity text NOT NULL CHECK (severity IN ('info', 'warning', 'blocking'))"));
        assert!(sql.contains("workflow_audit_event"));
        assert!(sql.contains("'add_step'"));
        assert!(sql.contains("'update_step'"));
        assert!(sql.contains("'delete_step'"));
        assert!(sql.contains("'execute_step'"));
        assert!(sql.contains("'publish_version'"));
        assert!(sql.contains("'rollback_version'"));
        assert!(sql.contains("before_state jsonb NOT NULL DEFAULT '{}'::jsonb"));
        assert!(sql.contains("after_state jsonb NOT NULL DEFAULT '{}'::jsonb"));
    }

    #[test]
    fn workflow_template_postgres_schema_supports_slo_escalation_and_runtime_instances() {
        let sql = WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("slo_minutes integer CHECK (slo_minutes IS NULL OR slo_minutes > 0)"));
        assert!(sql.contains("escalation_role text CHECK"));
        assert!(sql.contains("workflow_runtime_instance"));
        assert!(sql.contains("business_object_type text NOT NULL CHECK"));
        assert!(sql.contains("'payroll_period'"));
        assert!(sql.contains("'archive_intake'"));
        assert!(sql.contains("current_step_key text"));
        assert!(sql.contains("evidence jsonb NOT NULL DEFAULT '{}'::jsonb"));
    }

    #[test]
    fn workflow_template_postgres_schema_persists_runtime_data_records() {
        let sql = WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_SQL;

        assert!(sql.contains("workflow_data_record"));
        assert!(sql.contains("record_type text NOT NULL CHECK"));
        assert!(sql.contains("'payroll_calculation_plan'"));
        assert!(sql.contains("'approval_packet'"));
        assert!(sql.contains("scope_hash char(64) NOT NULL CHECK"));
        assert!(sql.contains("business_scope jsonb NOT NULL DEFAULT '{}'::jsonb"));
        assert!(sql.contains("payload jsonb NOT NULL DEFAULT '{}'::jsonb"));
        assert!(sql.contains("UNIQUE (tenant_id, template_version_id, step_key, record_type, scope_hash)"));
        assert!(sql.contains("workflow_data_record_tenant_isolation"));
    }

    #[test]
    fn workflow_template_postgres_schema_enforces_tenant_rls() {
        let sql = WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_SQL;

        for table in WORKFLOW_TEMPLATE_POSTGRES_TABLES {
            assert!(
                sql.contains(&format!("ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")),
                "missing RLS enablement for {table}"
            );
        }
        assert!(sql.contains("current_setting('bitween.tenant_id', true)"));
        assert!(sql.contains("WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true))"));
    }
}
