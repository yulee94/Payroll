-- Bitween auth session security schema.
-- Target: self-hosted PostgreSQL 16+ / current, applied by a controlled Rust migration job.
-- Purpose: JWT replay/revocation state and session verification audit without storing raw tokens.

CREATE SCHEMA IF NOT EXISTS bitween_auth;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS bitween_auth.jwt_revocation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  jwt_id_sha256 char(64) NOT NULL CHECK (jwt_id_sha256 ~ '^[0-9a-f]{64}$'),
  subject_sha256 char(64) CHECK (subject_sha256 IS NULL OR subject_sha256 ~ '^[0-9a-f]{64}$'),
  reason text NOT NULL CHECK (char_length(reason) BETWEEN 1 AND 256),
  revoked_by text NOT NULL CHECK (char_length(revoked_by) BETWEEN 1 AND 160),
  revoked_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, jwt_id_sha256)
);

CREATE INDEX IF NOT EXISTS jwt_revocation_active_idx
  ON bitween_auth.jwt_revocation (tenant_id, jwt_id_sha256, expires_at);

CREATE TABLE IF NOT EXISTS bitween_auth.session_event_audit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  legal_entity_id text NOT NULL,
  workplace_id text NOT NULL,
  jwt_id_sha256 char(64) CHECK (jwt_id_sha256 IS NULL OR jwt_id_sha256 ~ '^[0-9a-f]{64}$'),
  subject_sha256 char(64) CHECK (subject_sha256 IS NULL OR subject_sha256 ~ '^[0-9a-f]{64}$'),
  issuer text NOT NULL CHECK (char_length(issuer) BETWEEN 1 AND 512),
  audience text NOT NULL CHECK (char_length(audience) BETWEEN 1 AND 256),
  key_id text NOT NULL CHECK (char_length(key_id) BETWEEN 1 AND 256),
  algorithm text NOT NULL CHECK (algorithm IN ('RS256')),
  verification_result text NOT NULL CHECK (verification_result IN ('verified', 'blocked')),
  reason text NOT NULL CHECK (char_length(reason) BETWEEN 1 AND 128),
  acr_level text CHECK (acr_level IS NULL OR acr_level IN ('routine', 'elevated', 'sensitive', 'critical')),
  role text CHECK (role IS NULL OR char_length(role) BETWEEN 1 AND 128),
  expires_at_unix bigint CHECK (expires_at_unix IS NULL OR expires_at_unix > 0),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
  observed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS session_event_audit_tenant_observed_idx
  ON bitween_auth.session_event_audit (tenant_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS session_event_audit_jti_idx
  ON bitween_auth.session_event_audit (tenant_id, jwt_id_sha256, observed_at DESC)
  WHERE jwt_id_sha256 IS NOT NULL;

ALTER TABLE bitween_auth.jwt_revocation ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_auth.session_event_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY jwt_revocation_tenant_isolation ON bitween_auth.jwt_revocation
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));

CREATE POLICY session_event_audit_tenant_isolation ON bitween_auth.session_event_audit
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
