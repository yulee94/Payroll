-- Bitween row-level-security enforcement and employee scope-key migration.
-- Target: self-hosted PostgreSQL 16+ / current, applied by a controlled Rust migration job.
-- Purpose: FORCE row level security on every tenant-scoped table and widen the
--          bitween_hr.employee unique key to the full tenant/legal-entity/workplace scope.
--
-- Why this is a SEPARATE migration (do not fold into 001-007):
--   Migrations 001-007 shipped on main (PR #83) and their sha256 checksums are
--   recorded in bitween_migrations.schema_migration. The migration ledger hard-fails
--   with postgres_migration_checksum_mismatch (see crates/payroll-api/src/postgres_repository.rs,
--   apply_migration_in_transaction) if a previously applied migration's bytes change.
--   Editing 001-007 in place to add FORCE ROW LEVEL SECURITY or to change the employee
--   unique key would therefore break every upgrade from a database already provisioned
--   from main. Applying these changes as migration 008 keeps the checksums of the
--   shipped migrations stable while delivering the hardening on upgrade.
--
-- Ordering: 008 runs AFTER 003 in required_postgres_migrations(), so the
--   employee table from 003 already exists. The scope-inclusive upsert in
--   crates/payroll-api/src/bin/archive_intake_store.rs
--   (ON CONFLICT (tenant_id, legal_entity_id, workplace_id, employee_key)) depends on
--   the named unique constraint added below, so 008 must precede any admission run.
--
-- Idempotency: FORCE ROW LEVEL SECURITY is idempotent (re-running is a no-op), so the
--   plain ALTER statements are safe to re-run. The employee key swap drops the old
--   auto-named inline constraint with IF EXISTS and adds the new named constraint inside
--   a DO block that swallows duplicate_table/duplicate_object so re-runs are no-ops.

-- FORCE ROW LEVEL SECURITY: ENABLE alone still lets the table owner (the role that
-- runs migrations and the stores) bypass RLS. FORCE closes that gap so tenant
-- isolation holds even for the owning role. Idempotent: repeated FORCE is a no-op.

-- 001_archive_intake.sql tables
ALTER TABLE bitween_archive.archive_intake FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_intake_version FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_intake_issue FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_mapping_template FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.hr_employee_staging FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.hr_attendance_staging FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.payroll_input_staging FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_admission_audit FORCE ROW LEVEL SECURITY;

-- 002_workflow_templates.sql tables
ALTER TABLE bitween_workflow.workflow_template FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_template_version FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_node FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_edge FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_publish_check FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_audit_event FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_runtime_instance FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_data_record FORCE ROW LEVEL SECURITY;

-- 003_hr_employee.sql tables
ALTER TABLE bitween_hr.employee FORCE ROW LEVEL SECURITY;

-- 004_user_preferences.sql tables
ALTER TABLE bitween_settings.user_preference FORCE ROW LEVEL SECURITY;

-- 005_payroll_attendance_intake.sql tables
ALTER TABLE bitween_hr.attendance_record FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_payroll.payroll_input FORCE ROW LEVEL SECURITY;

-- 006_archive_admission_rollback.sql tables
ALTER TABLE bitween_archive.archive_admission_recovery_point FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_source_sync FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_admission_rollback FORCE ROW LEVEL SECURITY;

-- 007_auth_session_security.sql tables
ALTER TABLE bitween_auth.jwt_revocation FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_auth.session_event_audit FORCE ROW LEVEL SECURITY;

-- Employee scope key swap.
-- 003 shipped an inline UNIQUE (tenant_id, employee_key) which PostgreSQL auto-named
-- employee_tenant_id_employee_key_key. The same employee_key can legitimately recur
-- across legal entities / workplaces within one tenant, so the unique key must include
-- the full scope. Drop the old auto-named constraint and add a stable named constraint
-- that the archive-intake employee upsert targets via ON CONFLICT.
ALTER TABLE bitween_hr.employee
  DROP CONSTRAINT IF EXISTS employee_tenant_id_employee_key_key;

DO $$
BEGIN
  ALTER TABLE bitween_hr.employee
    ADD CONSTRAINT employee_tenant_scope_key
    UNIQUE (tenant_id, legal_entity_id, workplace_id, employee_key);
EXCEPTION
  WHEN duplicate_table OR duplicate_object THEN NULL;
END $$;
