-- Bitween 자료함 production intake schema.
-- Target: self-hosted PostgreSQL 16+ / current, applied by a controlled Rust migration job.
-- Originals are stored in RustFS. PostgreSQL stores metadata, staging, review, and admission audit.

CREATE SCHEMA IF NOT EXISTS bitween_archive;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION bitween_archive.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS bitween_archive.archive_intake (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  legal_entity_id text,
  workplace_id text,
  payroll_period text,
  uploader_user_id text NOT NULL,
  original_file_name text NOT NULL,
  stored_file_name text NOT NULL,
  object_uri text NOT NULL CHECK (object_uri LIKE 'rustfs://%'),
  object_bucket text NOT NULL,
  object_key text NOT NULL,
  content_sha256 char(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
  content_sample_sha256 char(64) NOT NULL CHECK (content_sample_sha256 ~ '^[0-9a-f]{64}$'),
  content_sample_row_count bigint NOT NULL DEFAULT 0 CHECK (content_sample_row_count >= 0),
  redacted_content_sample_excerpt text NOT NULL DEFAULT '' CHECK (char_length(redacted_content_sample_excerpt) <= 8192),
  extraction_status text NOT NULL DEFAULT 'not_readable' CHECK (
    extraction_status IN ('converted', 'needs_guidance', 'not_readable', 'not_applicable')
  ),
  content_type text NOT NULL,
  file_size_bytes bigint NOT NULL CHECK (file_size_bytes >= 0),
  family text NOT NULL CHECK (family IN ('hr', 'payroll', 'general_archive', 'unknown')),
  database_target text NOT NULL CHECK (
    database_target IN (
      'hr_employee_staging',
      'hr_attendance_staging',
      'payroll_input_staging',
      'archive_blob',
      'needs_mapping'
    )
  ),
  status text NOT NULL CHECK (
    status IN ('received', 'needs_guidance', 'ready_for_staging', 'archived', 'admitted', 'rejected')
  ),
  next_action text NOT NULL CHECK (
    next_action IN ('map_columns', 'resolve_anomalies', 'save_to_business_data', 'keep_in_archive', 'none')
  ),
  extracted_columns jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(extracted_columns) = 'array'),
  estimated_rows bigint NOT NULL DEFAULT 0 CHECK (estimated_rows >= 0),
  postgres_ready boolean NOT NULL DEFAULT false,
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  sensitivity_label text NOT NULL DEFAULT 'restricted',
  retention_policy text NOT NULL DEFAULT 'tenant_default',
  legal_hold boolean NOT NULL DEFAULT false,
  admission_batch_id uuid,
  admission_approved_by text,
  admission_approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (
    NOT postgres_ready OR (
      status = 'ready_for_staging'
      AND database_target IN ('hr_employee_staging', 'hr_attendance_staging', 'payroll_input_staging')
    )
  )
);

CREATE TRIGGER archive_intake_set_updated_at
BEFORE UPDATE ON bitween_archive.archive_intake
FOR EACH ROW EXECUTE FUNCTION bitween_archive.set_updated_at();

CREATE INDEX IF NOT EXISTS archive_intake_tenant_status_idx
  ON bitween_archive.archive_intake (tenant_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS archive_intake_scope_period_idx
  ON bitween_archive.archive_intake (tenant_id, legal_entity_id, workplace_id, payroll_period);
CREATE INDEX IF NOT EXISTS archive_intake_sha_idx
  ON bitween_archive.archive_intake (tenant_id, content_sha256);
CREATE INDEX IF NOT EXISTS archive_intake_object_idx
  ON bitween_archive.archive_intake (object_bucket, object_key);

CREATE TABLE IF NOT EXISTS bitween_archive.archive_intake_version (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake(id) ON DELETE CASCADE,
  tenant_id text NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  object_uri text NOT NULL CHECK (object_uri LIKE 'rustfs://%'),
  object_bucket text NOT NULL,
  object_key text NOT NULL,
  content_sha256 char(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
  file_size_bytes bigint NOT NULL CHECK (file_size_bytes >= 0),
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (intake_id, version)
);

CREATE INDEX IF NOT EXISTS archive_intake_version_tenant_idx
  ON bitween_archive.archive_intake_version (tenant_id, intake_id, version DESC);

CREATE TABLE IF NOT EXISTS bitween_archive.archive_intake_issue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake(id) ON DELETE CASCADE,
  tenant_id text NOT NULL,
  issue_type text NOT NULL CHECK (issue_type IN ('guidance', 'anomaly', 'security', 'validation')),
  code text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('info', 'warning', 'blocking')),
  column_name text,
  prompt text NOT NULL,
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'dismissed')),
  owner_role text NOT NULL DEFAULT 'archive_operator',
  resolution jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(resolution) = 'object'),
  resolved_by text,
  resolved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((status = 'open' AND resolved_at IS NULL) OR (status <> 'open' AND resolved_at IS NOT NULL))
);

CREATE TRIGGER archive_intake_issue_set_updated_at
BEFORE UPDATE ON bitween_archive.archive_intake_issue
FOR EACH ROW EXECUTE FUNCTION bitween_archive.set_updated_at();

CREATE INDEX IF NOT EXISTS archive_intake_issue_work_idx
  ON bitween_archive.archive_intake_issue (tenant_id, status, severity, created_at DESC);
CREATE INDEX IF NOT EXISTS archive_intake_issue_intake_idx
  ON bitween_archive.archive_intake_issue (intake_id, status);

CREATE TABLE IF NOT EXISTS bitween_archive.archive_mapping_template (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  business_family text NOT NULL CHECK (business_family IN ('hr', 'payroll')),
  source_fingerprint text NOT NULL,
  target_table text NOT NULL CHECK (
    target_table IN ('hr_employee_staging', 'hr_attendance_staging', 'payroll_input_staging')
  ),
  mapping jsonb NOT NULL CHECK (jsonb_typeof(mapping) = 'object'),
  validation_rules jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(validation_rules) = 'object'),
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'retired')),
  approved_by text,
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, business_family, source_fingerprint, target_table)
);

CREATE TRIGGER archive_mapping_template_set_updated_at
BEFORE UPDATE ON bitween_archive.archive_mapping_template
FOR EACH ROW EXECUTE FUNCTION bitween_archive.set_updated_at();

CREATE INDEX IF NOT EXISTS archive_mapping_template_lookup_idx
  ON bitween_archive.archive_mapping_template (tenant_id, business_family, status);

CREATE TABLE IF NOT EXISTS bitween_archive.hr_employee_staging (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake(id) ON DELETE CASCADE,
  tenant_id text NOT NULL,
  row_number integer NOT NULL CHECK (row_number > 0),
  row_hash char(64) NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
  employee_external_id text,
  display_name text,
  department text,
  employment_status text,
  row_payload jsonb NOT NULL CHECK (jsonb_typeof(row_payload) = 'object'),
  validation_status text NOT NULL DEFAULT 'pending_review' CHECK (
    validation_status IN ('pending_review', 'valid', 'invalid', 'admitted', 'rejected')
  ),
  issues jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(issues) = 'array'),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (intake_id, row_number)
);

CREATE TABLE IF NOT EXISTS bitween_archive.hr_attendance_staging (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake(id) ON DELETE CASCADE,
  tenant_id text NOT NULL,
  row_number integer NOT NULL CHECK (row_number > 0),
  row_hash char(64) NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
  employee_external_id text,
  work_date date,
  row_payload jsonb NOT NULL CHECK (jsonb_typeof(row_payload) = 'object'),
  validation_status text NOT NULL DEFAULT 'pending_review' CHECK (
    validation_status IN ('pending_review', 'valid', 'invalid', 'admitted', 'rejected')
  ),
  issues jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(issues) = 'array'),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (intake_id, row_number)
);

CREATE TABLE IF NOT EXISTS bitween_archive.payroll_input_staging (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake(id) ON DELETE CASCADE,
  tenant_id text NOT NULL,
  legal_entity_id text,
  workplace_id text,
  payroll_period text,
  row_number integer NOT NULL CHECK (row_number > 0),
  row_hash char(64) NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
  employee_external_id text,
  gross_pay numeric(18, 2),
  deduction_total numeric(18, 2),
  row_payload jsonb NOT NULL CHECK (jsonb_typeof(row_payload) = 'object'),
  validation_status text NOT NULL DEFAULT 'pending_review' CHECK (
    validation_status IN ('pending_review', 'valid', 'invalid', 'admitted', 'rejected')
  ),
  issues jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(issues) = 'array'),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (intake_id, row_number)
);

CREATE INDEX IF NOT EXISTS hr_employee_staging_review_idx
  ON bitween_archive.hr_employee_staging (tenant_id, validation_status, created_at DESC);
CREATE INDEX IF NOT EXISTS hr_attendance_staging_review_idx
  ON bitween_archive.hr_attendance_staging (tenant_id, validation_status, created_at DESC);
CREATE INDEX IF NOT EXISTS payroll_input_staging_review_idx
  ON bitween_archive.payroll_input_staging (tenant_id, payroll_period, validation_status, created_at DESC);

CREATE TABLE IF NOT EXISTS bitween_archive.archive_admission_audit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake(id) ON DELETE RESTRICT,
  tenant_id text NOT NULL,
  admission_batch_id uuid NOT NULL DEFAULT gen_random_uuid(),
  target_table text NOT NULL CHECK (
    target_table IN ('hr_employee', 'hr_attendance', 'payroll_input')
  ),
  admitted_rows integer NOT NULL CHECK (admitted_rows >= 0),
  rejected_rows integer NOT NULL CHECK (rejected_rows >= 0),
  mapping_template_id uuid REFERENCES bitween_archive.archive_mapping_template(id),
  approved_by text NOT NULL,
  approved_at timestamptz NOT NULL DEFAULT now(),
  rollback_ref jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(rollback_ref) = 'object'),
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(evidence) = 'object')
);

CREATE INDEX IF NOT EXISTS archive_admission_audit_tenant_idx
  ON bitween_archive.archive_admission_audit (tenant_id, approved_at DESC);

ALTER TABLE bitween_archive.archive_intake ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_intake_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_intake_issue ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_mapping_template ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.hr_employee_staging ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.hr_attendance_staging ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.payroll_input_staging ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_archive.archive_admission_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY archive_intake_tenant_isolation ON bitween_archive.archive_intake
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY archive_intake_version_tenant_isolation ON bitween_archive.archive_intake_version
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY archive_intake_issue_tenant_isolation ON bitween_archive.archive_intake_issue
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY archive_mapping_template_tenant_isolation ON bitween_archive.archive_mapping_template
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY hr_employee_staging_tenant_isolation ON bitween_archive.hr_employee_staging
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY hr_attendance_staging_tenant_isolation ON bitween_archive.hr_attendance_staging
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY payroll_input_staging_tenant_isolation ON bitween_archive.payroll_input_staging
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY archive_admission_audit_tenant_isolation ON bitween_archive.archive_admission_audit
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
