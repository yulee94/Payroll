-- Bitween archive admission rollback schema.
-- Target: self-hosted PostgreSQL 16+ / current, applied by a controlled Rust migration job.
-- Purpose: auditable reversal of 자료함 rows previously admitted into canonical HR/payroll tables.

CREATE SCHEMA IF NOT EXISTS bitween_archive;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE bitween_hr.employee
  ADD COLUMN IF NOT EXISTS source_intake_id uuid REFERENCES bitween_archive.archive_intake(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS source_row_hash char(64) CHECK (source_row_hash IS NULL OR source_row_hash ~ '^[0-9a-f]{64}$'),
  ADD COLUMN IF NOT EXISTS source_payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(source_payload) = 'object'),
  ADD COLUMN IF NOT EXISTS admission_status text NOT NULL DEFAULT 'admitted' CHECK (admission_status IN ('admitted', 'replaced', 'reversed'));

CREATE INDEX IF NOT EXISTS employee_source_intake_idx
  ON bitween_hr.employee (tenant_id, source_intake_id)
  WHERE source_intake_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS bitween_archive.archive_admission_recovery_point (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake(id) ON DELETE RESTRICT,
  tenant_id text NOT NULL,
  target_table text NOT NULL CHECK (
    target_table IN ('hr_employee', 'hr_attendance', 'payroll_input')
  ),
  business_key text NOT NULL CHECK (char_length(business_key) BETWEEN 1 AND 256),
  action text NOT NULL CHECK (action IN ('insert', 'replace')),
  before_exists boolean NOT NULL,
  before_payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(before_payload) = 'object'),
  after_payload jsonb NOT NULL CHECK (jsonb_typeof(after_payload) = 'object'),
  recovery_status text NOT NULL DEFAULT 'available' CHECK (recovery_status IN ('available', 'restored')),
  captured_by text NOT NULL,
  captured_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, intake_id, target_table, business_key)
);

CREATE INDEX IF NOT EXISTS archive_admission_recovery_point_lookup_idx
  ON bitween_archive.archive_admission_recovery_point (tenant_id, intake_id, target_table, recovery_status);

CREATE TABLE IF NOT EXISTS bitween_archive.archive_source_sync (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake(id) ON DELETE RESTRICT,
  tenant_id text NOT NULL,
  source_version integer NOT NULL CHECK (source_version > 0),
  target_table text NOT NULL CHECK (
    target_table IN ('hr_employee', 'hr_attendance', 'payroll_input')
  ),
  operation text NOT NULL CHECK (operation IN ('admission', 'rollback', 'recovery')),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'synced', 'failed')),
  source_object_uri text NOT NULL CHECK (source_object_uri LIKE 'rustfs://%'),
  generated_object_uri text CHECK (generated_object_uri IS NULL OR generated_object_uri LIKE 'rustfs://%'),
  change_payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(change_payload) = 'object'),
  requested_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS archive_source_sync_pending_idx
  ON bitween_archive.archive_source_sync (tenant_id, status, created_at)
  WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS bitween_archive.archive_admission_rollback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake(id) ON DELETE RESTRICT,
  tenant_id text NOT NULL,
  target_table text NOT NULL CHECK (
    target_table IN ('hr_employee', 'hr_attendance', 'payroll_input')
  ),
  reversed_rows integer NOT NULL CHECK (reversed_rows >= 0),
  requested_by text NOT NULL,
  requested_at timestamptz NOT NULL DEFAULT now(),
  reason text NOT NULL CHECK (char_length(reason) BETWEEN 1 AND 512),
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(evidence) = 'object')
);

CREATE INDEX IF NOT EXISTS archive_admission_rollback_tenant_idx
  ON bitween_archive.archive_admission_rollback (tenant_id, requested_at DESC);

ALTER TABLE bitween_archive.archive_admission_recovery_point ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_admission_recovery_point FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_source_sync ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_source_sync FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_admission_rollback ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_admission_rollback FORCE ROW LEVEL SECURITY;

CREATE POLICY archive_admission_recovery_point_tenant_isolation
  ON bitween_archive.archive_admission_recovery_point
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));

CREATE POLICY archive_source_sync_tenant_isolation
  ON bitween_archive.archive_source_sync
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));

CREATE POLICY archive_admission_rollback_tenant_isolation
  ON bitween_archive.archive_admission_rollback
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
