-- Bitween canonical intake admission schema.
-- Target: self-hosted PostgreSQL 16+ / current, applied by a controlled Rust migration job.
-- Purpose: reviewed 자료함 staging rows admitted into HR attendance and payroll input records.

CREATE SCHEMA IF NOT EXISTS bitween_hr;
CREATE SCHEMA IF NOT EXISTS bitween_payroll;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION bitween_hr.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION bitween_payroll.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS bitween_hr.attendance_record (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  legal_entity_id text NOT NULL,
  workplace_id text NOT NULL,
  employee_key text NOT NULL CHECK (employee_key ~ '^employee-[a-zA-Z0-9_-]{1,96}$'),
  work_date date NOT NULL,
  source_intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake(id) ON DELETE RESTRICT,
  source_row_hash char(64) NOT NULL CHECK (source_row_hash ~ '^[0-9a-f]{64}$'),
  source_payload jsonb NOT NULL CHECK (jsonb_typeof(source_payload) = 'object'),
  admission_status text NOT NULL DEFAULT 'admitted' CHECK (admission_status IN ('admitted', 'replaced', 'reversed')),
  created_by text NOT NULL,
  updated_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, legal_entity_id, workplace_id, employee_key, work_date)
);

CREATE TRIGGER attendance_record_set_updated_at
BEFORE UPDATE ON bitween_hr.attendance_record
FOR EACH ROW EXECUTE FUNCTION bitween_hr.set_updated_at();

CREATE INDEX IF NOT EXISTS attendance_record_scope_date_idx
  ON bitween_hr.attendance_record (tenant_id, legal_entity_id, workplace_id, work_date, employee_key);
CREATE INDEX IF NOT EXISTS attendance_record_source_idx
  ON bitween_hr.attendance_record (tenant_id, source_intake_id);

CREATE TABLE IF NOT EXISTS bitween_payroll.payroll_input (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  legal_entity_id text NOT NULL,
  workplace_id text NOT NULL,
  payroll_period text NOT NULL CHECK (payroll_period ~ '^[0-9]{4}-[0-9]{2}$'),
  employee_key text NOT NULL CHECK (employee_key ~ '^employee-[a-zA-Z0-9_-]{1,96}$'),
  gross_pay numeric(18, 2) NOT NULL CHECK (gross_pay >= 0),
  deduction_total numeric(18, 2) NOT NULL DEFAULT 0 CHECK (deduction_total >= 0),
  source_intake_id uuid NOT NULL REFERENCES bitween_archive.archive_intake(id) ON DELETE RESTRICT,
  source_row_hash char(64) NOT NULL CHECK (source_row_hash ~ '^[0-9a-f]{64}$'),
  source_payload jsonb NOT NULL CHECK (jsonb_typeof(source_payload) = 'object'),
  admission_status text NOT NULL DEFAULT 'admitted' CHECK (admission_status IN ('admitted', 'replaced', 'reversed')),
  created_by text NOT NULL,
  updated_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, legal_entity_id, workplace_id, payroll_period, employee_key)
);

CREATE TRIGGER payroll_input_set_updated_at
BEFORE UPDATE ON bitween_payroll.payroll_input
FOR EACH ROW EXECUTE FUNCTION bitween_payroll.set_updated_at();

CREATE INDEX IF NOT EXISTS payroll_input_scope_period_idx
  ON bitween_payroll.payroll_input (tenant_id, legal_entity_id, workplace_id, payroll_period, employee_key);
CREATE INDEX IF NOT EXISTS payroll_input_source_idx
  ON bitween_payroll.payroll_input (tenant_id, source_intake_id);

ALTER TABLE bitween_hr.attendance_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_payroll.payroll_input ENABLE ROW LEVEL SECURITY;

CREATE POLICY attendance_record_scope_isolation ON bitween_hr.attendance_record
  USING (
    tenant_id = current_setting('bitween.tenant_id', true)
    AND legal_entity_id = current_setting('bitween.legal_entity_id', true)
    AND workplace_id = current_setting('bitween.workplace_id', true)
  )
  WITH CHECK (
    tenant_id = current_setting('bitween.tenant_id', true)
    AND legal_entity_id = current_setting('bitween.legal_entity_id', true)
    AND workplace_id = current_setting('bitween.workplace_id', true)
  );

CREATE POLICY payroll_input_scope_isolation ON bitween_payroll.payroll_input
  USING (
    tenant_id = current_setting('bitween.tenant_id', true)
    AND legal_entity_id = current_setting('bitween.legal_entity_id', true)
    AND workplace_id = current_setting('bitween.workplace_id', true)
  )
  WITH CHECK (
    tenant_id = current_setting('bitween.tenant_id', true)
    AND legal_entity_id = current_setting('bitween.legal_entity_id', true)
    AND workplace_id = current_setting('bitween.workplace_id', true)
  );
