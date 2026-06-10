-- Bitween user preference production schema.
-- Target: self-hosted PostgreSQL 16+ / current, applied by a controlled Rust migration job.
-- Purpose: tenant-scoped operator settings such as language, density, theme, and payroll view preference.

CREATE SCHEMA IF NOT EXISTS bitween_settings;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION bitween_settings.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS bitween_settings.user_preference (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  user_id text NOT NULL CHECK (char_length(user_id) BETWEEN 1 AND 160),
  locale text NOT NULL DEFAULT 'ko-KR' CHECK (locale IN ('ko-KR', 'en-US', 'zh-Hans-CN', 'ja-JP')),
  sidebar_theme text NOT NULL DEFAULT 'steel' CHECK (sidebar_theme IN ('steel', 'graphite', 'teal', 'navy')),
  workspace_density text NOT NULL DEFAULT 'work_dense' CHECK (workspace_density IN ('work_dense', 'comfortable')),
  notification_digest text NOT NULL DEFAULT 'role_work' CHECK (notification_digest IN ('role_work', 'urgent_only')),
  payroll_standard_view text NOT NULL DEFAULT 'before_run' CHECK (payroll_standard_view IN ('before_run', 'always_visible')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, user_id)
);

CREATE TRIGGER user_preference_set_updated_at
BEFORE UPDATE ON bitween_settings.user_preference
FOR EACH ROW EXECUTE FUNCTION bitween_settings.set_updated_at();

CREATE INDEX IF NOT EXISTS user_preference_tenant_user_idx
  ON bitween_settings.user_preference (tenant_id, user_id);

ALTER TABLE bitween_settings.user_preference ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_preference_tenant_isolation ON bitween_settings.user_preference
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
