-- Bitween HR employee production schema.
-- Target: self-hosted PostgreSQL 16+ / current, applied by a controlled Rust migration job.
-- Purpose: tenant-scoped employee records for HR management workflows.

CREATE SCHEMA IF NOT EXISTS bitween_hr;
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

CREATE TABLE IF NOT EXISTS bitween_hr.employee (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  legal_entity_id text NOT NULL,
  workplace_id text NOT NULL,
  employee_key text NOT NULL CHECK (employee_key ~ '^employee-[a-zA-Z0-9_-]{1,96}$'),
  display_name text NOT NULL CHECK (char_length(display_name) BETWEEN 1 AND 120),
  team text NOT NULL CHECK (char_length(team) BETWEEN 1 AND 120),
  role_title text NOT NULL CHECK (char_length(role_title) BETWEEN 1 AND 120),
  employment_status text NOT NULL DEFAULT 'active' CHECK (employment_status IN ('active', 'on_leave', 'offboarding')),
  sensitivity_label text NOT NULL DEFAULT 'restricted' CHECK (sensitivity_label IN ('restricted', 'confidential')),
  created_by text NOT NULL,
  updated_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, employee_key)
);

CREATE TRIGGER employee_set_updated_at
BEFORE UPDATE ON bitween_hr.employee
FOR EACH ROW EXECUTE FUNCTION bitween_hr.set_updated_at();

CREATE INDEX IF NOT EXISTS employee_scope_status_idx
  ON bitween_hr.employee (tenant_id, legal_entity_id, workplace_id, employment_status, display_name);
CREATE INDEX IF NOT EXISTS employee_team_idx
  ON bitween_hr.employee (tenant_id, team, display_name);

ALTER TABLE bitween_hr.employee ENABLE ROW LEVEL SECURITY;

CREATE POLICY employee_tenant_scope_isolation ON bitween_hr.employee
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
