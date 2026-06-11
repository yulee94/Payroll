-- Bitween workflow template production graph schema.
-- Target: self-hosted PostgreSQL 16+ / current, applied by a controlled Rust migration job.
-- Purpose: durable corporate workflow templates, graph nodes/edges, publication versions, SLO/escalation metadata, and audit evidence.

CREATE SCHEMA IF NOT EXISTS bitween_workflow;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION bitween_workflow.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_template (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id text NOT NULL,
  template_key text NOT NULL CHECK (template_key ~ '^[a-z0-9][a-z0-9_-]{1,80}$'),
  title_key text NOT NULL,
  business_domain text NOT NULL CHECK (business_domain IN ('hr', 'payroll', 'approval', 'archive', 'admin', 'cross_functional')),
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'retired')),
  active_version integer NOT NULL DEFAULT 1 CHECK (active_version > 0),
  owner_role text NOT NULL CHECK (
    owner_role IN (
      'hr_operator',
      'hr_manager',
      'payroll_operator',
      'payroll_manager',
      'approval_signer',
      'archive_operator',
      'it_security_admin',
      'platform_owner'
    )
  ),
  policy_id text NOT NULL DEFAULT 'bitween.authz.rbac-abac-pbac.v1',
  created_by text NOT NULL,
  updated_by text NOT NULL,
  published_by text,
  published_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, template_key)
);

CREATE TRIGGER workflow_template_set_updated_at
BEFORE UPDATE ON bitween_workflow.workflow_template
FOR EACH ROW EXECUTE FUNCTION bitween_workflow.set_updated_at();

CREATE INDEX IF NOT EXISTS workflow_template_lookup_idx
  ON bitween_workflow.workflow_template (tenant_id, status, business_domain, updated_at DESC);

CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_template_version (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template(id) ON DELETE CASCADE,
  tenant_id text NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'replaced', 'rolled_back')),
  graph_hash char(64) NOT NULL CHECK (graph_hash ~ '^[0-9a-f]{64}$'),
  change_summary text NOT NULL,
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  published_by text,
  published_at timestamptz,
  rollback_of_version integer CHECK (rollback_of_version IS NULL OR rollback_of_version > 0),
  UNIQUE (template_id, version)
);

CREATE INDEX IF NOT EXISTS workflow_template_version_lookup_idx
  ON bitween_workflow.workflow_template_version (tenant_id, template_id, version DESC);

CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_node (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template(id) ON DELETE CASCADE,
  template_version_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template_version(id) ON DELETE CASCADE,
  tenant_id text NOT NULL,
  step_key text NOT NULL CHECK (step_key ~ '^[a-z0-9][a-z0-9_-]{1,80}$'),
  title text NOT NULL CHECK (char_length(title) <= 120),
  action text NOT NULL CHECK (char_length(action) <= 240),
  owner_role text NOT NULL CHECK (
    owner_role IN (
      'hr_operator',
      'hr_manager',
      'payroll_operator',
      'payroll_manager',
      'approval_signer',
      'archive_operator',
      'it_security_admin',
      'platform_owner'
    )
  ),
  status text NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'needs_attention', 'completed', 'blocked')),
  tone text NOT NULL DEFAULT 'neutral' CHECK (tone IN ('blocked', 'ready', 'attention', 'neutral')),
  lane text NOT NULL CHECK (lane IN ('source', 'rule', 'operation', 'approval', 'record')),
  node_type text NOT NULL CHECK (node_type IN ('trigger', 'condition', 'action', 'approval', 'record')),
  position_x integer NOT NULL CHECK (position_x BETWEEN 0 AND 100),
  position_y integer NOT NULL CHECK (position_y BETWEEN 0 AND 100),
  condition_expression jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(condition_expression) = 'object'),
  permission_scope jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(permission_scope) = 'object'),
  slo_minutes integer CHECK (slo_minutes IS NULL OR slo_minutes > 0),
  escalation_role text CHECK (
    escalation_role IS NULL OR escalation_role IN (
      'hr_manager',
      'payroll_manager',
      'it_security_admin',
      'platform_owner'
    )
  ),
  enabled boolean NOT NULL DEFAULT true,
  updated_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (template_version_id, step_key)
);

CREATE TRIGGER workflow_node_set_updated_at
BEFORE UPDATE ON bitween_workflow.workflow_node
FOR EACH ROW EXECUTE FUNCTION bitween_workflow.set_updated_at();

CREATE INDEX IF NOT EXISTS workflow_node_template_idx
  ON bitween_workflow.workflow_node (tenant_id, template_version_id, lane, position_y, position_x);
CREATE INDEX IF NOT EXISTS workflow_node_owner_work_idx
  ON bitween_workflow.workflow_node (tenant_id, owner_role, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_edge (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template(id) ON DELETE CASCADE,
  template_version_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template_version(id) ON DELETE CASCADE,
  tenant_id text NOT NULL,
  from_node_id uuid NOT NULL REFERENCES bitween_workflow.workflow_node(id) ON DELETE CASCADE,
  to_node_id uuid NOT NULL REFERENCES bitween_workflow.workflow_node(id) ON DELETE CASCADE,
  edge_type text NOT NULL DEFAULT 'success' CHECK (edge_type IN ('success', 'condition_true', 'condition_false', 'exception', 'approval_rejected')),
  condition_expression jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(condition_expression) = 'object'),
  sort_order integer NOT NULL DEFAULT 0 CHECK (sort_order >= 0),
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (from_node_id <> to_node_id),
  UNIQUE (template_version_id, from_node_id, to_node_id, edge_type)
);

CREATE INDEX IF NOT EXISTS workflow_edge_from_idx
  ON bitween_workflow.workflow_edge (tenant_id, template_version_id, from_node_id, sort_order);
CREATE INDEX IF NOT EXISTS workflow_edge_to_idx
  ON bitween_workflow.workflow_edge (tenant_id, template_version_id, to_node_id);

CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_publish_check (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template(id) ON DELETE CASCADE,
  template_version_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template_version(id) ON DELETE CASCADE,
  tenant_id text NOT NULL,
  check_code text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('info', 'warning', 'blocking')),
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'waived')),
  detail jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(detail) = 'object'),
  resolved_by text,
  resolved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((status = 'open' AND resolved_at IS NULL) OR (status <> 'open' AND resolved_at IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS workflow_publish_check_open_idx
  ON bitween_workflow.workflow_publish_check (tenant_id, template_version_id, status, severity);

CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_audit_event (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template(id) ON DELETE CASCADE,
  template_version_id uuid REFERENCES bitween_workflow.workflow_template_version(id) ON DELETE SET NULL,
  tenant_id text NOT NULL,
  step_key text,
  action text NOT NULL CHECK (
    action IN (
      'create_template',
      'add_step',
      'update_step',
      'delete_step',
      'connect_edge',
      'delete_edge',
      'execute_step',
      'validate_publish',
      'publish_version',
      'rollback_version'
    )
  ),
  actor_user_id text NOT NULL,
  actor_role text NOT NULL,
  before_state jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(before_state) = 'object'),
  after_state jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(after_state) = 'object'),
  trace_id text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS workflow_audit_event_tenant_idx
  ON bitween_workflow.workflow_audit_event (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS workflow_audit_event_template_idx
  ON bitween_workflow.workflow_audit_event (template_id, created_at DESC);

CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_runtime_instance (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template(id) ON DELETE RESTRICT,
  template_version_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template_version(id) ON DELETE RESTRICT,
  tenant_id text NOT NULL,
  business_object_type text NOT NULL CHECK (business_object_type IN ('payroll_period', 'hr_case', 'archive_intake', 'approval_document')),
  business_object_id text NOT NULL,
  status text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'blocked', 'cancelled')),
  current_step_key text,
  started_by text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(evidence) = 'object'),
  UNIQUE (tenant_id, business_object_type, business_object_id, template_version_id)
);

CREATE INDEX IF NOT EXISTS workflow_runtime_instance_work_idx
  ON bitween_workflow.workflow_runtime_instance (tenant_id, status, current_step_key, started_at DESC);

CREATE TABLE IF NOT EXISTS bitween_workflow.workflow_data_record (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  runtime_instance_id uuid REFERENCES bitween_workflow.workflow_runtime_instance(id) ON DELETE CASCADE,
  template_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template(id) ON DELETE RESTRICT,
  template_version_id uuid NOT NULL REFERENCES bitween_workflow.workflow_template_version(id) ON DELETE RESTRICT,
  tenant_id text NOT NULL,
  step_key text NOT NULL CHECK (step_key ~ '^[a-z0-9][a-z0-9_-]{1,80}$'),
  record_type text NOT NULL CHECK (
    record_type IN (
      'scope_lock',
      'authorization_gate_check',
      'attendance_source_close',
      'payroll_input_freeze',
      'deduction_exception_review',
      'payroll_calculation_plan',
      'approval_packet',
      'payout_package',
      'evidence_archive_admission',
      'custom_workflow_action'
    )
  ),
  target text NOT NULL CHECK (char_length(target) <= 120),
  status text NOT NULL CHECK (
    status IN (
      'recorded',
      'verified',
      'closed',
      'frozen',
      'reviewed',
      'planned',
      'created',
      'prepared',
      'queued'
    )
  ),
  scope_hash char(64) NOT NULL CHECK (scope_hash ~ '^[0-9a-f]{64}$'),
  business_scope jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(business_scope) = 'object'),
  record_count integer NOT NULL DEFAULT 0 CHECK (record_count >= 0),
  payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload) = 'object'),
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(evidence) = 'object'),
  updated_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, template_version_id, step_key, record_type, scope_hash)
);

CREATE TRIGGER workflow_data_record_set_updated_at
BEFORE UPDATE ON bitween_workflow.workflow_data_record
FOR EACH ROW EXECUTE FUNCTION bitween_workflow.set_updated_at();

CREATE INDEX IF NOT EXISTS workflow_data_record_work_idx
  ON bitween_workflow.workflow_data_record (tenant_id, template_version_id, step_key, updated_at DESC);
CREATE INDEX IF NOT EXISTS workflow_data_record_type_idx
  ON bitween_workflow.workflow_data_record (tenant_id, record_type, status, updated_at DESC);

ALTER TABLE bitween_workflow.workflow_template ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_template FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_template_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_template_version FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_node ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_node FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_edge ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_edge FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_publish_check ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_publish_check FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_audit_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_audit_event FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_runtime_instance ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_runtime_instance FORCE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_data_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE bitween_workflow.workflow_data_record FORCE ROW LEVEL SECURITY;

CREATE POLICY workflow_template_tenant_isolation ON bitween_workflow.workflow_template
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY workflow_template_version_tenant_isolation ON bitween_workflow.workflow_template_version
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY workflow_node_tenant_isolation ON bitween_workflow.workflow_node
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY workflow_edge_tenant_isolation ON bitween_workflow.workflow_edge
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY workflow_publish_check_tenant_isolation ON bitween_workflow.workflow_publish_check
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY workflow_audit_event_tenant_isolation ON bitween_workflow.workflow_audit_event
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY workflow_runtime_instance_tenant_isolation ON bitween_workflow.workflow_runtime_instance
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
CREATE POLICY workflow_data_record_tenant_isolation ON bitween_workflow.workflow_data_record
  USING (tenant_id = current_setting('bitween.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('bitween.tenant_id', true));
