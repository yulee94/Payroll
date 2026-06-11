use bitween_payroll_api::{
    PostgresClientSession, PostgresConnectionFailure, PostgresRepositoryConfig,
    PostgresTenantScope, WORKFLOW_EDIT_VALIDATION_SCHEMA, WORKFLOW_PREFLIGHT_SCHEMA,
    WORKFLOW_TEMPLATE_STORE_SCHEMA, required_postgres_migrations,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashSet};
use std::fs;
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use std::process;
use std::time::{SystemTime, UNIX_EPOCH};

const DEFAULT_TEMPLATE_ID: &str = "payroll-close";
const MAX_POSITION: u16 = 100;
const MAX_LABEL_LEN: usize = 120;
const MAX_ACTION_LEN: usize = 240;
const MAX_METADATA_KEY_LEN: usize = 40;
const MAX_METADATA_VALUE_LEN: usize = 180;
const MAX_SLO_MINUTES: u16 = 10_080;

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowTemplateStore {
    schema: String,
    templates: Vec<WorkflowTemplate>,
    #[serde(default)]
    template_versions: Vec<WorkflowTemplateVersionRecord>,
    #[serde(default)]
    analytics: Vec<WorkflowTemplateAnalytics>,
    audit_events: Vec<WorkflowAuditEvent>,
    #[serde(default)]
    runtime_events: Vec<WorkflowRuntimeEvent>,
    #[serde(default)]
    data_records: Vec<WorkflowDataRecord>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowTemplate {
    id: String,
    version: u32,
    title_key: String,
    steps: Vec<WorkflowStepOverride>,
    updated_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowTemplateVersionRecord {
    id: String,
    template_id: String,
    version: u32,
    graph_hash: String,
    change_summary: String,
    actor_role: String,
    created_at_unix: u64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    rollback_of_version: Option<u32>,
    steps: Vec<WorkflowStepOverride>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowStepOverride {
    id: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    title: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    action: Option<String>,
    owner: String,
    status: String,
    tone: String,
    lane: String,
    node_type: String,
    #[serde(default)]
    position_x: u16,
    #[serde(default)]
    position_y: u16,
    #[serde(default)]
    next_step_ids: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    slo_minutes: Option<u16>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    escalation_role: Option<String>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    condition_expression: BTreeMap<String, String>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    permission_scope: BTreeMap<String, String>,
    enabled: bool,
    updated_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowAuditEvent {
    id: String,
    template_id: String,
    step_id: String,
    action: String,
    actor_role: String,
    updated_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowRuntimeEvent {
    id: String,
    template_id: String,
    step_id: String,
    action: String,
    actor_role: String,
    affected_step_ids: Vec<String>,
    #[serde(default)]
    data_operations: Vec<WorkflowDataOperation>,
    status_before: String,
    status_after: String,
    updated_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowDataOperation {
    id: String,
    operation_type: String,
    target: String,
    status: String,
    record_count: u16,
    metadata: BTreeMap<String, String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowDataRecord {
    id: String,
    template_id: String,
    step_id: String,
    record_type: String,
    target: String,
    status: String,
    record_count: u16,
    metadata: BTreeMap<String, String>,
    updated_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowTemplateAnalytics {
    template_id: String,
    step_count: u16,
    edge_count: u16,
    branch_count: u16,
    blocked_count: u16,
    waiting_count: u16,
    completed_count: u16,
    disconnected_step_ids: Vec<String>,
    cycle_detected: bool,
    longest_path_steps: u16,
    owner_loads: Vec<WorkflowLoad>,
    lane_loads: Vec<WorkflowLoad>,
    validation_issues: Vec<WorkflowValidationIssue>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowLoad {
    key: String,
    count: u16,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowValidationIssue {
    code: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    step_id: Option<String>,
    severity: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowPreflightReport {
    schema: String,
    template_id: String,
    template_version: u32,
    graph_hash: String,
    status: String,
    planned_step_ids: Vec<String>,
    blocker_count: u16,
    warning_count: u16,
    issues: Vec<WorkflowPreflightIssue>,
    next_actions: Vec<WorkflowPreflightNextAction>,
    data_operations: Vec<WorkflowDataOperation>,
    generated_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowPreflightIssue {
    code: String,
    severity: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    step_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    owner: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowPreflightNextAction {
    step_id: String,
    owner: String,
    action: String,
    due_window: String,
    reason: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct WorkflowEditValidationReport {
    schema: String,
    template_id: String,
    step_id: String,
    operation: String,
    status: String,
    would_persist: bool,
    blocker_count: u16,
    warning_count: u16,
    issues: Vec<WorkflowPreflightIssue>,
    proposed_analytics: WorkflowTemplateAnalytics,
    generated_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
struct WorkflowStepInput {
    id: Option<String>,
    title: Option<String>,
    action: Option<String>,
    owner: Option<String>,
    status: Option<String>,
    tone: Option<String>,
    lane: Option<String>,
    node_type: Option<String>,
    position_x: Option<u16>,
    position_y: Option<u16>,
    next_step_ids: Option<Vec<String>>,
    after_step_id: Option<String>,
    enabled: Option<bool>,
    slo_minutes: Option<u16>,
    escalation_role: Option<String>,
    condition_expression: Option<BTreeMap<String, String>>,
    permission_scope: Option<BTreeMap<String, String>>,
    actor_role: Option<String>,
    scope_tenant: Option<String>,
    scope_workplace: Option<String>,
    scope_period: Option<String>,
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let mut args = std::env::args().skip(1).collect::<Vec<_>>();
    let action = args
        .first()
        .map(String::as_str)
        .ok_or_else(|| "missing workflow template action".to_owned())?;

    if postgres_dsn_configured() {
        return run_postgres(args);
    }

    let path = store_path()?;

    match action {
        "get" => print_store(&load_store(&path)?),
        "add-step" => {
            args.remove(0);
            let template_id = args
                .first()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let input = read_input()?;
            let mut store = load_store(&path)?;
            add_step(&mut store, template_id, input, now_unix(), now_unix_nanos())?;
            save_store(&path, &store)?;
            print_store(&store)
        }
        "update-step" => {
            args.remove(0);
            let template_id = args
                .first()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let step_id = args
                .get(1)
                .ok_or_else(|| "missing workflow step id".to_owned())?;
            let input = read_input()?;
            let mut store = load_store(&path)?;
            update_step(&mut store, template_id, step_id, input, now_unix(), now_unix_nanos())?;
            save_store(&path, &store)?;
            print_store(&store)
        }
        "delete-step" => {
            args.remove(0);
            let template_id = args
                .first()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let step_id = args
                .get(1)
                .ok_or_else(|| "missing workflow step id".to_owned())?;
            let input = read_input()?;
            let mut store = load_store(&path)?;
            delete_step(&mut store, template_id, step_id, input, now_unix(), now_unix_nanos())?;
            save_store(&path, &store)?;
            print_store(&store)
        }
        "execute-step" => {
            args.remove(0);
            let template_id = args
                .first()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let step_id = args
                .get(1)
                .ok_or_else(|| "missing workflow step id".to_owned())?;
            let input = read_input()?;
            let mut store = load_store(&path)?;
            execute_step(&mut store, template_id, step_id, input, now_unix(), now_unix_nanos())?;
            save_store(&path, &store)?;
            print_store(&store)
        }
        "rollback-template" => {
            args.remove(0);
            let template_id = args
                .first()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let version = args
                .get(1)
                .ok_or_else(|| "missing workflow template rollback version".to_owned())?
                .parse::<u32>()
                .map_err(|_| "workflow rollback version must be a number".to_owned())?;
            let input = read_input()?;
            let mut store = load_store(&path)?;
            rollback_template(&mut store, template_id, version, input, now_unix(), now_unix_nanos())?;
            save_store(&path, &store)?;
            print_store(&store)
        }
        "preflight-template" => {
            args.remove(0);
            let template_id = args
                .first()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let input = read_input()?;
            let store = load_store(&path)?;
            print_preflight_report(&preflight_template(
                &store,
                template_id,
                input,
                now_unix(),
                now_unix_nanos(),
            )?)
        }
        "validate-step-update" => {
            args.remove(0);
            let template_id = args
                .first()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let step_id = args
                .get(1)
                .ok_or_else(|| "missing workflow step id".to_owned())?;
            let input = read_input()?;
            let store = load_store(&path)?;
            print_edit_validation_report(&validate_step_update(
                &store,
                template_id,
                step_id,
                input,
                now_unix(),
                now_unix_nanos(),
            )?)
        }
        _ => Err(format!("unsupported workflow template action: {action}")),
    }
}

fn run_postgres(mut args: Vec<String>) -> Result<(), String> {
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|_| "workflow_postgres_runtime_failed".to_owned())?;
    runtime.block_on(run_postgres_async(&mut args))
}

async fn run_postgres_async(args: &mut Vec<String>) -> Result<(), String> {
    let action = args
        .first()
        .cloned()
        .ok_or_else(|| "missing workflow template action".to_owned())?;
    let mut session = postgres_workflow_session().await?;
    let mut store = load_postgres_store(&session).await?;
    if store.templates.is_empty() {
        store = default_store(now_unix());
        save_postgres_store(&mut session, &store, "bootstrap_workflow_templates").await?;
    }

    match action.as_str() {
        "get" => print_store(&store),
        "add-step" => {
            args.remove(0);
            let template_id = args
                .first()
                .cloned()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let input = read_input()?;
            add_step(&mut store, &template_id, input, now_unix(), now_unix_nanos())?;
            save_postgres_store(&mut session, &store, "add_step").await?;
            print_store(&store)
        }
        "update-step" => {
            args.remove(0);
            let template_id = args
                .first()
                .cloned()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let step_id = args
                .get(1)
                .cloned()
                .ok_or_else(|| "missing workflow step id".to_owned())?;
            let input = read_input()?;
            update_step(
                &mut store,
                &template_id,
                &step_id,
                input,
                now_unix(),
                now_unix_nanos(),
            )?;
            save_postgres_store(&mut session, &store, "update_step").await?;
            print_store(&store)
        }
        "delete-step" => {
            args.remove(0);
            let template_id = args
                .first()
                .cloned()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let step_id = args
                .get(1)
                .cloned()
                .ok_or_else(|| "missing workflow step id".to_owned())?;
            let input = read_input()?;
            delete_step(
                &mut store,
                &template_id,
                &step_id,
                input,
                now_unix(),
                now_unix_nanos(),
            )?;
            save_postgres_store(&mut session, &store, "delete_step").await?;
            print_store(&store)
        }
        "execute-step" => {
            args.remove(0);
            let template_id = args
                .first()
                .cloned()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let step_id = args
                .get(1)
                .cloned()
                .ok_or_else(|| "missing workflow step id".to_owned())?;
            let input = read_input()?;
            execute_step(
                &mut store,
                &template_id,
                &step_id,
                input,
                now_unix(),
                now_unix_nanos(),
            )?;
            save_postgres_store(&mut session, &store, "execute_step").await?;
            print_store(&store)
        }
        "rollback-template" => {
            args.remove(0);
            let template_id = args
                .first()
                .cloned()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let version = args
                .get(1)
                .ok_or_else(|| "missing workflow template rollback version".to_owned())?
                .parse::<u32>()
                .map_err(|_| "workflow rollback version must be a number".to_owned())?;
            let input = read_input()?;
            rollback_template(
                &mut store,
                &template_id,
                version,
                input,
                now_unix(),
                now_unix_nanos(),
            )?;
            save_postgres_store(&mut session, &store, "rollback_version").await?;
            print_store(&store)
        }
        "preflight-template" => {
            args.remove(0);
            let template_id = args
                .first()
                .cloned()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let input = read_input()?;
            print_preflight_report(&preflight_template(
                &store,
                &template_id,
                input,
                now_unix(),
                now_unix_nanos(),
            )?)
        }
        "validate-step-update" => {
            args.remove(0);
            let template_id = args
                .first()
                .cloned()
                .ok_or_else(|| "missing workflow template id".to_owned())?;
            let step_id = args
                .get(1)
                .cloned()
                .ok_or_else(|| "missing workflow step id".to_owned())?;
            let input = read_input()?;
            print_edit_validation_report(&validate_step_update(
                &store,
                &template_id,
                &step_id,
                input,
                now_unix(),
                now_unix_nanos(),
            )?)
        }
        _ => Err(format!("unsupported workflow template action: {action}")),
    }
}

fn print_store(store: &WorkflowTemplateStore) -> Result<(), String> {
    let mut view = store.clone();
    refresh_store_analytics(&mut view);
    let body = serde_json::to_string_pretty(&view).map_err(|error| error.to_string())?;
    println!("{body}");
    Ok(())
}

fn print_preflight_report(report: &WorkflowPreflightReport) -> Result<(), String> {
    let body = serde_json::to_string_pretty(report).map_err(|error| error.to_string())?;
    println!("{body}");
    Ok(())
}

fn print_edit_validation_report(report: &WorkflowEditValidationReport) -> Result<(), String> {
    let body = serde_json::to_string_pretty(report).map_err(|error| error.to_string())?;
    println!("{body}");
    Ok(())
}

fn add_step(
    store: &mut WorkflowTemplateStore,
    template_id: &str,
    input: WorkflowStepInput,
    updated_at_unix: u64,
    event_seed: u128,
) -> Result<(), String> {
    let actor_role = input.actor_role.clone();
    let template = template_mut(store, template_id)?;
    let original_template = template.clone();
    let title = clean_label_required(input.title.clone(), "title", MAX_LABEL_LEN)?;
    let action = clean_label_required(input.action.clone(), "action", MAX_ACTION_LEN)?;
    let id = input
        .id
        .clone()
        .map(|value| clean_step_id(value, "step id"))
        .transpose()?
        .unwrap_or_else(|| unique_step_id(template, &title, event_seed));
    if template.steps.iter().any(|step| step.id == id) {
        return Err(format!("workflow step already exists: {id}"));
    }

    let lane = input
        .lane
        .map(|value| allowed_value(value, "lane", allowed_lanes()))
        .transpose()?
        .unwrap_or_else(|| "operation".to_owned());
    let node_type = input
        .node_type
        .map(|value| allowed_value(value, "node_type", allowed_node_types()))
        .transpose()?
        .unwrap_or_else(|| "action".to_owned());
    let status = input
        .status
        .map(|value| allowed_value(value, "status", allowed_statuses()))
        .transpose()?
        .unwrap_or_else(|| "waiting".to_owned());
    let tone = input
        .tone
        .map(|value| allowed_value(value, "tone", allowed_tones()))
        .transpose()?
        .unwrap_or_else(|| tone_for_status(&status).to_owned());
    let owner = input
        .owner
        .map(|value| allowed_value(value, "owner", allowed_owners()))
        .transpose()?
        .unwrap_or_else(|| "platform_owner".to_owned());
    let next_step_ids = input
        .next_step_ids
        .map(|ids| clean_next_step_ids(ids, &id, &template.steps))
        .transpose()?
        .unwrap_or_default();
    let slo_minutes = input.slo_minutes.map(validate_slo_minutes).transpose()?;
    let escalation_role = input
        .escalation_role
        .map(|value| allowed_value(value, "escalation_role", allowed_owners()))
        .transpose()?;
    let condition_expression = input
        .condition_expression
        .map(|values| clean_metadata_map(values, "condition_expression"))
        .transpose()?
        .unwrap_or_default();
    let permission_scope = input
        .permission_scope
        .map(|values| clean_metadata_map(values, "permission_scope"))
        .transpose()?
        .unwrap_or_default();
    let position_y = input.position_y.unwrap_or_else(|| next_position_y(&template.steps));
    let mut step = WorkflowStepOverride {
        id: id.clone(),
        title: Some(title),
        action: Some(action),
        owner,
        status,
        tone,
        lane,
        node_type,
        position_x: validate_position(input.position_x.unwrap_or(0), "position_x")?,
        position_y: validate_position(position_y, "position_y")?,
        next_step_ids,
        slo_minutes,
        escalation_role,
        condition_expression,
        permission_scope,
        enabled: input.enabled.unwrap_or(true),
        updated_at_unix,
    };
    normalize_step_position(&mut step);
    template.steps.push(step);
    if let Some(after_step_id) = input.after_step_id {
        place_step_after(template, &id, &after_step_id)?;
    }
    if let Err(error) = reject_blocking_graph_issues(template) {
        *template = original_template;
        return Err(error);
    }
    template.updated_at_unix = updated_at_unix;
    publish_template_version(store, template_id, "add_step", actor_role.clone(), updated_at_unix, None)?;
    push_audit_event(store, template_id, &id, "add_step", actor_role, updated_at_unix, event_seed)?;
    sort_store(store);
    refresh_store_analytics(store);
    Ok(())
}

fn update_step(
    store: &mut WorkflowTemplateStore,
    template_id: &str,
    step_id: &str,
    input: WorkflowStepInput,
    updated_at_unix: u64,
    event_seed: u128,
) -> Result<(), String> {
    let clean_id = clean_step_id(step_id.to_owned(), "step id")?;
    let actor_role = input.actor_role.clone();
    let next_step_ids = input
        .next_step_ids
        .clone()
        .map(|ids| {
            let template = store
                .templates
                .iter()
                .find(|template| template.id == template_id)
                .ok_or_else(|| "workflow template not found".to_owned())?;
            clean_next_step_ids(ids, &clean_id, &template.steps)
        })
        .transpose()?;
    let template = template_mut(store, template_id)?;
    let original_template = template.clone();
    let current_index = step_index(template, &clean_id)?;

    if let Some(title) = input.title.clone() {
        template.steps[current_index].title = Some(clean_label(title, "title", MAX_LABEL_LEN)?);
    }
    if let Some(action) = input.action.clone() {
        template.steps[current_index].action = Some(clean_label(action, "action", MAX_ACTION_LEN)?);
    }
    if let Some(owner) = input.owner {
        template.steps[current_index].owner = allowed_value(owner, "owner", allowed_owners())?;
    }
    if let Some(status) = input.status {
        template.steps[current_index].status = allowed_value(status, "status", allowed_statuses())?;
        template.steps[current_index].tone = tone_for_status(&template.steps[current_index].status).to_owned();
    }
    if let Some(tone) = input.tone {
        template.steps[current_index].tone = allowed_value(tone, "tone", allowed_tones())?;
    }
    if let Some(lane) = input.lane {
        template.steps[current_index].lane = allowed_value(lane, "lane", allowed_lanes())?;
    }
    if let Some(node_type) = input.node_type {
        template.steps[current_index].node_type = allowed_value(node_type, "node_type", allowed_node_types())?;
    }
    if let Some(position_x) = input.position_x {
        template.steps[current_index].position_x = validate_position(position_x, "position_x")?;
    }
    if let Some(position_y) = input.position_y {
        template.steps[current_index].position_y = validate_position(position_y, "position_y")?;
    }
    if let Some(enabled) = input.enabled {
        template.steps[current_index].enabled = enabled;
    }
    if let Some(slo_minutes) = input.slo_minutes {
        template.steps[current_index].slo_minutes = Some(validate_slo_minutes(slo_minutes)?);
    }
    if let Some(escalation_role) = input.escalation_role {
        template.steps[current_index].escalation_role =
            Some(allowed_value(escalation_role, "escalation_role", allowed_owners())?);
    }
    if let Some(condition_expression) = input.condition_expression {
        template.steps[current_index].condition_expression =
            clean_metadata_map(condition_expression, "condition_expression")?;
    }
    if let Some(permission_scope) = input.permission_scope {
        template.steps[current_index].permission_scope = clean_metadata_map(permission_scope, "permission_scope")?;
    }
    template.steps[current_index].updated_at_unix = updated_at_unix;
    if let Some(after_step_id) = input.after_step_id {
        place_step_after(template, &clean_id, &after_step_id)?;
    }
    if let Some(next_step_ids) = next_step_ids {
        let current_index = step_index(template, &clean_id)?;
        template.steps[current_index].next_step_ids = next_step_ids;
    }
    if let Err(error) = reject_blocking_graph_issues(template) {
        *template = original_template;
        return Err(error);
    }
    template.updated_at_unix = updated_at_unix;
    publish_template_version(store, template_id, "update_step", actor_role.clone(), updated_at_unix, None)?;
    push_audit_event(store, template_id, &clean_id, "update_step", actor_role, updated_at_unix, event_seed)?;
    sort_store(store);
    refresh_store_analytics(store);
    Ok(())
}

fn delete_step(
    store: &mut WorkflowTemplateStore,
    template_id: &str,
    step_id: &str,
    input: WorkflowStepInput,
    updated_at_unix: u64,
    event_seed: u128,
) -> Result<(), String> {
    let clean_id = clean_step_id(step_id.to_owned(), "step id")?;
    let actor_role = input.actor_role.clone();
    let template = template_mut(store, template_id)?;
    let original_template = template.clone();
    let index = step_index(template, &clean_id)?;
    if template.steps.len() <= 1 {
        return Err("workflow template must keep at least one step".to_owned());
    }
    let deleted_next_ids = template.steps[index].next_step_ids.clone();
    template.steps.remove(index);
    for step in &mut template.steps {
        if step.next_step_ids.iter().any(|id| id == &clean_id) {
            step.next_step_ids.retain(|id| id != &clean_id);
            for next_id in &deleted_next_ids {
                if next_id != &step.id && !step.next_step_ids.contains(next_id) {
                    step.next_step_ids.push(next_id.clone());
                }
            }
        }
    }
    if let Err(error) = reject_blocking_graph_issues(template) {
        *template = original_template;
        return Err(error);
    }
    template.updated_at_unix = updated_at_unix;
    publish_template_version(store, template_id, "delete_step", actor_role.clone(), updated_at_unix, None)?;
    push_audit_event(store, template_id, &clean_id, "delete_step", actor_role, updated_at_unix, event_seed)?;
    sort_store(store);
    refresh_store_analytics(store);
    Ok(())
}

fn rollback_template(
    store: &mut WorkflowTemplateStore,
    template_id: &str,
    version: u32,
    input: WorkflowStepInput,
    updated_at_unix: u64,
    event_seed: u128,
) -> Result<(), String> {
    if version == 0 {
        return Err("workflow rollback version must be greater than zero".to_owned());
    }
    let clean_template_id = clean_step_id(template_id.to_owned(), "template id")?;
    let actor_role = input.actor_role.clone();
    let target = store
        .template_versions
        .iter()
        .find(|record| record.template_id == clean_template_id && record.version == version)
        .cloned()
        .ok_or_else(|| format!("workflow template version not found: {version}"))?;
    if target.steps.is_empty() {
        return Err("workflow rollback version has no graph".to_owned());
    }

    let template = template_mut(store, &clean_template_id)?;
    let original_template = template.clone();
    template.steps = target.steps;
    if let Err(error) = reject_blocking_graph_issues(template) {
        *template = original_template;
        return Err(error);
    }
    template.updated_at_unix = updated_at_unix;
    publish_template_version(
        store,
        &clean_template_id,
        "rollback_version",
        actor_role.clone(),
        updated_at_unix,
        Some(version),
    )?;
    push_audit_event(
        store,
        &clean_template_id,
        "template",
        "rollback_version",
        actor_role,
        updated_at_unix,
        event_seed,
    )?;
    sort_store(store);
    refresh_store_analytics(store);
    Ok(())
}

fn execute_step(
    store: &mut WorkflowTemplateStore,
    template_id: &str,
    step_id: &str,
    input: WorkflowStepInput,
    updated_at_unix: u64,
    event_seed: u128,
) -> Result<(), String> {
    let clean_id = clean_step_id(step_id.to_owned(), "step id")?;
    let actor_role = input.actor_role.clone();
    let (status_before, affected_step_ids, data_operations) = {
        let template = template_mut(store, template_id)?;
        let index = step_index(template, &clean_id)?;
        if !template.steps[index].enabled {
            return Err("workflow step is disabled".to_owned());
        }
        let status_before = template.steps[index].status.clone();
        let affected_step_ids = template.steps[index].next_step_ids.clone();
        let data_operations = data_operations_for_step(
            template,
            index,
            &input,
            &affected_step_ids,
            updated_at_unix,
            event_seed,
        )?;
        template.steps[index].status = "completed".to_owned();
        template.steps[index].tone = "ready".to_owned();
        template.steps[index].updated_at_unix = updated_at_unix;

        for next_step_id in &affected_step_ids {
            if let Some(next_step) = template.steps.iter_mut().find(|step| &step.id == next_step_id) {
                if matches!(next_step.status.as_str(), "waiting" | "needs_attention") {
                    next_step.status = "needs_attention".to_owned();
                    next_step.tone = "attention".to_owned();
                    next_step.updated_at_unix = updated_at_unix;
                }
            }
        }

        template.updated_at_unix = updated_at_unix;
        (status_before, affected_step_ids, data_operations)
    };
    apply_data_operations(store, template_id, &clean_id, &data_operations, updated_at_unix)?;
    publish_template_version(store, template_id, "execute_step", actor_role.clone(), updated_at_unix, None)?;
    push_audit_event(
        store,
        template_id,
        &clean_id,
        "execute_step",
        actor_role.clone(),
        updated_at_unix,
        event_seed,
    )?;
    push_runtime_event(
        store,
        template_id,
        &clean_id,
        "execute_step",
        actor_role,
        affected_step_ids,
        data_operations,
        status_before,
        "completed".to_owned(),
        updated_at_unix,
        event_seed,
    )?;
    sort_store(store);
    refresh_store_analytics(store);
    Ok(())
}

fn apply_data_operations(
    store: &mut WorkflowTemplateStore,
    template_id: &str,
    step_id: &str,
    data_operations: &[WorkflowDataOperation],
    updated_at_unix: u64,
) -> Result<(), String> {
    for operation in data_operations {
        let record_id = data_record_id(template_id, step_id, operation)?;
        let record = WorkflowDataRecord {
            id: record_id.clone(),
            template_id: template_id.to_owned(),
            step_id: step_id.to_owned(),
            record_type: operation.operation_type.clone(),
            target: operation.target.clone(),
            status: operation.status.clone(),
            record_count: operation.record_count,
            metadata: operation.metadata.clone(),
            updated_at_unix,
        };
        if let Some(existing) = store.data_records.iter_mut().find(|existing| existing.id == record_id) {
            *existing = record;
        } else {
            store.data_records.push(record);
        }
    }
    Ok(())
}

fn data_record_id(
    template_id: &str,
    step_id: &str,
    operation: &WorkflowDataOperation,
) -> Result<String, String> {
    let scope_key = [
        operation.metadata.get("scope_tenant").map(String::as_str).unwrap_or("tenant"),
        operation.metadata.get("scope_workplace").map(String::as_str).unwrap_or("workplace"),
        operation.metadata.get("scope_period").map(String::as_str).unwrap_or("period"),
    ]
    .join("-");
    Ok(format!(
        "workflow-data-record-{}-{}-{}-{}",
        clean_step_id(template_id.to_owned(), "template id")?,
        clean_step_id(step_id.to_owned(), "step id")?,
        clean_step_id(operation.operation_type.clone(), "operation_type")?,
        clean_step_id(scope_key, "scope key")?
    ))
}

fn template_mut<'a>(store: &'a mut WorkflowTemplateStore, template_id: &str) -> Result<&'a mut WorkflowTemplate, String> {
    store
        .templates
        .iter_mut()
        .find(|template| template.id == template_id)
        .ok_or_else(|| "workflow template not found".to_owned())
}

fn template_ref<'a>(store: &'a WorkflowTemplateStore, template_id: &str) -> Result<&'a WorkflowTemplate, String> {
    store
        .templates
        .iter()
        .find(|template| template.id == template_id)
        .ok_or_else(|| "workflow template not found".to_owned())
}

fn step_index(template: &WorkflowTemplate, step_id: &str) -> Result<usize, String> {
    template
        .steps
        .iter()
        .position(|step| step.id == step_id)
        .ok_or_else(|| "workflow step not found".to_owned())
}

fn push_audit_event(
    store: &mut WorkflowTemplateStore,
    template_id: &str,
    step_id: &str,
    action: &str,
    actor_role: Option<String>,
    updated_at_unix: u64,
    event_seed: u128,
) -> Result<(), String> {
    store.audit_events.push(WorkflowAuditEvent {
        id: format!("workflow-event-{event_seed}"),
        template_id: template_id.to_owned(),
        step_id: step_id.to_owned(),
        action: action.to_owned(),
        actor_role: actor_role
            .map(|value| allowed_value(value, "actor_role", allowed_owners()))
            .transpose()?
            .unwrap_or_else(|| "platform_owner".to_owned()),
        updated_at_unix,
    });
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn push_runtime_event(
    store: &mut WorkflowTemplateStore,
    template_id: &str,
    step_id: &str,
    action: &str,
    actor_role: Option<String>,
    affected_step_ids: Vec<String>,
    data_operations: Vec<WorkflowDataOperation>,
    status_before: String,
    status_after: String,
    updated_at_unix: u64,
    event_seed: u128,
) -> Result<(), String> {
    store.runtime_events.push(WorkflowRuntimeEvent {
        id: format!("workflow-runtime-event-{event_seed}"),
        template_id: template_id.to_owned(),
        step_id: step_id.to_owned(),
        action: action.to_owned(),
        actor_role: actor_role
            .map(|value| allowed_value(value, "actor_role", allowed_owners()))
            .transpose()?
            .unwrap_or_else(|| "platform_owner".to_owned()),
        affected_step_ids,
        data_operations,
        status_before,
        status_after,
        updated_at_unix,
    });
    Ok(())
}

fn publish_template_version(
    store: &mut WorkflowTemplateStore,
    template_id: &str,
    change_summary: &str,
    actor_role: Option<String>,
    updated_at_unix: u64,
    rollback_of_version: Option<u32>,
) -> Result<(), String> {
    let clean_template_id = clean_template_key(template_id.to_owned(), "template id")?;
    let actor_role = actor_role
        .map(|value| allowed_value(value, "actor_role", allowed_owners()))
        .transpose()?
        .unwrap_or_else(|| "platform_owner".to_owned());
    let next_version = next_template_version(store, &clean_template_id)?;
    let template = {
        let template = template_mut(store, &clean_template_id)?;
        template.version = next_version;
        template.updated_at_unix = updated_at_unix;
        template.clone()
    };
    store.template_versions.push(template_version_record(
        &template,
        change_summary,
        &actor_role,
        updated_at_unix,
        rollback_of_version,
    )?);
    Ok(())
}

fn next_template_version(store: &WorkflowTemplateStore, template_id: &str) -> Result<u32, String> {
    let current = store
        .templates
        .iter()
        .find(|template| template.id == template_id)
        .map(|template| template.version)
        .ok_or_else(|| "workflow template not found".to_owned())?;
    let max_recorded = store
        .template_versions
        .iter()
        .filter(|record| record.template_id == template_id)
        .map(|record| record.version)
        .max()
        .unwrap_or(current);
    Ok(max_recorded.max(current).saturating_add(1))
}

fn template_version_record(
    template: &WorkflowTemplate,
    change_summary: &str,
    actor_role: &str,
    created_at_unix: u64,
    rollback_of_version: Option<u32>,
) -> Result<WorkflowTemplateVersionRecord, String> {
    let graph_hash = workflow_graph_hash(template)?;
    let change_summary = clean_label(change_summary.to_owned(), "change_summary", MAX_LABEL_LEN)?;
    let actor_role = allowed_value(actor_role.to_owned(), "actor_role", allowed_owners())?;
    Ok(WorkflowTemplateVersionRecord {
        id: format!(
            "workflow-template-version-{}-{}-{}",
            clean_template_key(template.id.clone(), "template id")?,
            template.version,
            &graph_hash[..12]
        ),
        template_id: template.id.clone(),
        version: template.version,
        graph_hash,
        change_summary,
        actor_role,
        created_at_unix,
        rollback_of_version,
        steps: template.steps.clone(),
    })
}

fn ensure_template_version_records(
    store: &mut WorkflowTemplateStore,
    created_at_unix: u64,
) -> Result<(), String> {
    let templates = store.templates.clone();
    for template in templates {
        if !store
            .template_versions
            .iter()
            .any(|record| record.template_id == template.id && record.version == template.version)
        {
            store.template_versions.push(template_version_record(
                &template,
                "import_current_version",
                "platform_owner",
                created_at_unix,
                None,
            )?);
        }
    }
    Ok(())
}

fn preflight_template(
    store: &WorkflowTemplateStore,
    template_id: &str,
    input: WorkflowStepInput,
    generated_at_unix: u64,
    event_seed: u128,
) -> Result<WorkflowPreflightReport, String> {
    let template = template_ref(store, template_id)?;
    let analytics = analyze_template(template);
    let mut issues = analytics
        .validation_issues
        .iter()
        .map(|issue| WorkflowPreflightIssue {
            code: issue.code.clone(),
            severity: issue.severity.clone(),
            step_id: issue.step_id.clone(),
            owner: issue
                .step_id
                .as_deref()
                .and_then(|step_id| template.steps.iter().find(|step| step.id == step_id))
                .map(|step| step.owner.clone()),
        })
        .collect::<Vec<_>>();
    for step in template
        .steps
        .iter()
        .filter(|step| step.enabled && step.status == "blocked")
    {
        issues.push(WorkflowPreflightIssue {
            code: "blocked_step".to_owned(),
            severity: "error".to_owned(),
            step_id: Some(step.id.clone()),
            owner: Some(step.owner.clone()),
        });
    }

    let blocker_count = issues
        .iter()
        .filter(|issue| issue.severity == "error")
        .count() as u16;
    let warning_count = issues
        .iter()
        .filter(|issue| issue.severity == "warning")
        .count() as u16;
    let planned_step_ids = planned_step_ids_for_template(template);
    let next_actions = planned_step_ids
        .iter()
        .filter_map(|step_id| template.steps.iter().find(|step| step.id == *step_id))
        .filter(|step| step.enabled && step.status != "completed")
        .take(5)
        .map(|step| WorkflowPreflightNextAction {
            step_id: step.id.clone(),
            owner: step.owner.clone(),
            action: step
                .action
                .clone()
                .unwrap_or_else(|| step.title.clone().unwrap_or_else(|| step.id.clone())),
            due_window: step
                .slo_minutes
                .map(|minutes| format!("{minutes}m"))
                .unwrap_or_else(|| "not_set".to_owned()),
            reason: if step.status == "blocked" {
                "remove_blocker".to_owned()
            } else if step.status == "waiting" {
                "owner_review".to_owned()
            } else {
                "ready_to_start".to_owned()
            },
        })
        .collect::<Vec<_>>();
    let mut data_operations = Vec::new();
    if blocker_count == 0 {
        for (offset, step_id) in planned_step_ids.iter().enumerate() {
            let index = step_index(template, step_id)?;
            if !template.steps[index].enabled {
                continue;
            }
            data_operations.extend(data_operations_for_step(
                template,
                index,
                &input,
                &template.steps[index].next_step_ids,
                generated_at_unix,
                event_seed.saturating_add(offset as u128),
            )?);
        }
    }
    let status = if blocker_count > 0 {
        "blocked"
    } else if warning_count > 0 {
        "needs_review"
    } else {
        "ready"
    }
    .to_owned();

    Ok(WorkflowPreflightReport {
        schema: WORKFLOW_PREFLIGHT_SCHEMA.to_owned(),
        template_id: template.id.clone(),
        template_version: template.version,
        graph_hash: workflow_graph_hash(template)?,
        status,
        planned_step_ids,
        blocker_count,
        warning_count,
        issues,
        next_actions,
        data_operations,
        generated_at_unix,
    })
}

fn validate_step_update(
    store: &WorkflowTemplateStore,
    template_id: &str,
    step_id: &str,
    input: WorkflowStepInput,
    generated_at_unix: u64,
    event_seed: u128,
) -> Result<WorkflowEditValidationReport, String> {
    template_ref(store, template_id)?;
    let clean_step_id = clean_step_id(step_id.to_owned(), "step id")?;
    let mut draft = store.clone();
    let update_result = update_step(
        &mut draft,
        template_id,
        &clean_step_id,
        input,
        generated_at_unix,
        event_seed,
    );
    let template = if update_result.is_ok() {
        template_ref(&draft, template_id)?
    } else {
        template_ref(store, template_id)?
    };
    let analytics = analyze_template(template);
    let mut issues = analytics_to_preflight_issues(template, &analytics);
    if let Err(error) = update_result {
        if let Some(code) = workflow_graph_rejection_code(&error) {
            issues.push(WorkflowPreflightIssue {
                code: code.to_owned(),
                severity: "error".to_owned(),
                step_id: Some(clean_step_id.clone()),
                owner: template
                    .steps
                    .iter()
                    .find(|step| step.id == clean_step_id)
                    .map(|step| step.owner.clone()),
            });
        } else {
            return Err(error);
        }
    }
    dedupe_preflight_issues(&mut issues);
    let blocker_count = issues
        .iter()
        .filter(|issue| issue.severity == "error")
        .count() as u16;
    let warning_count = issues
        .iter()
        .filter(|issue| issue.severity == "warning")
        .count() as u16;
    Ok(WorkflowEditValidationReport {
        schema: WORKFLOW_EDIT_VALIDATION_SCHEMA.to_owned(),
        template_id: template.id.clone(),
        step_id: clean_step_id,
        operation: "update_step".to_owned(),
        status: if blocker_count > 0 {
            "blocked"
        } else if warning_count > 0 {
            "needs_review"
        } else {
            "accepted"
        }
        .to_owned(),
        would_persist: blocker_count == 0,
        blocker_count,
        warning_count,
        issues,
        proposed_analytics: analytics,
        generated_at_unix,
    })
}

fn analytics_to_preflight_issues(
    template: &WorkflowTemplate,
    analytics: &WorkflowTemplateAnalytics,
) -> Vec<WorkflowPreflightIssue> {
    analytics
        .validation_issues
        .iter()
        .map(|issue| WorkflowPreflightIssue {
            code: issue.code.clone(),
            severity: issue.severity.clone(),
            step_id: issue.step_id.clone(),
            owner: issue
                .step_id
                .as_deref()
                .and_then(|step_id| template.steps.iter().find(|step| step.id == step_id))
                .map(|step| step.owner.clone()),
        })
        .collect()
}

fn dedupe_preflight_issues(issues: &mut Vec<WorkflowPreflightIssue>) {
    let mut seen = HashSet::new();
    issues.retain(|issue| {
        seen.insert((
            issue.code.clone(),
            issue.severity.clone(),
            issue.step_id.clone(),
            issue.owner.clone(),
        ))
    });
}

fn workflow_graph_rejection_code(error: &str) -> Option<&'static str> {
    if error.contains("cycle_detected") {
        Some("cycle_detected")
    } else {
        None
    }
}

fn planned_step_ids_for_template(template: &WorkflowTemplate) -> Vec<String> {
    let step_ids = template
        .steps
        .iter()
        .map(|step| step.id.clone())
        .collect::<HashSet<_>>();
    let adjacency = template
        .steps
        .iter()
        .map(|step| {
            (
                step.id.clone(),
                step
                    .next_step_ids
                    .iter()
                    .filter(|id| step_ids.contains(*id))
                    .cloned()
                    .collect::<Vec<_>>(),
            )
        })
        .collect::<BTreeMap<_, _>>();
    let incoming = incoming_counts(&adjacency);
    let roots = template
        .steps
        .iter()
        .filter(|step| incoming.get(&step.id).copied().unwrap_or(0) == 0)
        .map(|step| step.id.clone())
        .collect::<Vec<_>>();
    let mut planned = Vec::new();
    let mut visited = HashSet::new();
    for root in roots {
        collect_planned_steps(&root, &adjacency, &mut visited, &mut planned);
    }
    for step in &template.steps {
        if visited.insert(step.id.clone()) {
            planned.push(step.id.clone());
        }
    }
    planned
}

fn collect_planned_steps(
    step_id: &str,
    adjacency: &BTreeMap<String, Vec<String>>,
    visited: &mut HashSet<String>,
    planned: &mut Vec<String>,
) {
    if !visited.insert(step_id.to_owned()) {
        return;
    }
    planned.push(step_id.to_owned());
    if let Some(next_ids) = adjacency.get(step_id) {
        for next_id in next_ids {
            collect_planned_steps(next_id, adjacency, visited, planned);
        }
    }
}

fn data_operations_for_step(
    template: &WorkflowTemplate,
    index: usize,
    input: &WorkflowStepInput,
    affected_step_ids: &[String],
    updated_at_unix: u64,
    event_seed: u128,
) -> Result<Vec<WorkflowDataOperation>, String> {
    let step = template
        .steps
        .get(index)
        .ok_or_else(|| "workflow step not found".to_owned())?;
    let analytics = analyze_template(template);
    let completed_dependencies = completed_upstream_steps(template, &step.id);
    let (operation_type, target, status, record_count) = match step.id.as_str() {
        "set-payroll-scope" => ("scope_lock", "payroll_scope", "recorded", 1),
        "configure-access" => ("authorization_gate_check", "authorization_policy", "verified", 1),
        "close-attendance" => ("attendance_source_close", "hr_attendance", "closed", 1),
        "close-payroll-inputs" => ("payroll_input_freeze", "payroll_inputs", "frozen", 1),
        "review-deductions" => ("deduction_exception_review", "payroll_deductions", "reviewed", analytics.blocked_count),
        "run-calculation" => ("payroll_calculation_plan", "payroll", "planned", completed_dependencies.saturating_add(1)),
        "request-approval" => ("approval_packet", "electronic_approval", "created", completed_dependencies.saturating_add(1)),
        "prepare-payout" => ("payout_package", "payment_file", "prepared", completed_dependencies.saturating_add(1)),
        "archive-payroll-evidence" => ("evidence_archive_admission", "rustfs_postgres_evidence", "queued", completed_dependencies.saturating_add(1)),
        _ => ("custom_workflow_action", "workflow_runtime", "recorded", affected_step_ids.len() as u16),
    };
    let mut metadata = operation_metadata(template, step, input, &analytics)?;
    metadata.insert("affected_step_count".to_owned(), affected_step_ids.len().to_string());
    metadata.insert("completed_dependency_count".to_owned(), completed_dependencies.to_string());
    metadata.insert("updated_at_unix".to_owned(), updated_at_unix.to_string());
    Ok(vec![WorkflowDataOperation {
        id: format!("workflow-data-operation-{event_seed}-0"),
        operation_type: operation_type.to_owned(),
        target: target.to_owned(),
        status: status.to_owned(),
        record_count,
        metadata,
    }])
}

fn operation_metadata(
    template: &WorkflowTemplate,
    step: &WorkflowStepOverride,
    input: &WorkflowStepInput,
    analytics: &WorkflowTemplateAnalytics,
) -> Result<BTreeMap<String, String>, String> {
    let mut metadata = BTreeMap::new();
    metadata.insert("template_id".to_owned(), template.id.clone());
    metadata.insert("template_version".to_owned(), template.version.to_string());
    metadata.insert("step_id".to_owned(), step.id.clone());
    metadata.insert("step_owner".to_owned(), step.owner.clone());
    metadata.insert("lane".to_owned(), step.lane.clone());
    metadata.insert("node_type".to_owned(), step.node_type.clone());
    if let Some(slo_minutes) = step.slo_minutes {
        metadata.insert("slo_minutes".to_owned(), slo_minutes.to_string());
    }
    if let Some(escalation_role) = &step.escalation_role {
        metadata.insert("escalation_role".to_owned(), escalation_role.clone());
    }
    metadata.insert(
        "condition_count".to_owned(),
        step.condition_expression.len().to_string(),
    );
    metadata.insert(
        "permission_scope_count".to_owned(),
        step.permission_scope.len().to_string(),
    );
    metadata.insert("branch_count".to_owned(), analytics.branch_count.to_string());
    metadata.insert("edge_count".to_owned(), analytics.edge_count.to_string());
    metadata.insert("validation_issue_count".to_owned(), analytics.validation_issues.len().to_string());
    if let Some(scope_tenant) = clean_optional_metadata(input.scope_tenant.clone(), "scope_tenant")? {
        metadata.insert("scope_tenant".to_owned(), scope_tenant);
    }
    if let Some(scope_workplace) = clean_optional_metadata(input.scope_workplace.clone(), "scope_workplace")? {
        metadata.insert("scope_workplace".to_owned(), scope_workplace);
    }
    if let Some(scope_period) = clean_optional_metadata(input.scope_period.clone(), "scope_period")? {
        metadata.insert("scope_period".to_owned(), scope_period);
    }
    Ok(metadata)
}

fn completed_upstream_steps(template: &WorkflowTemplate, step_id: &str) -> u16 {
    template
        .steps
        .iter()
        .filter(|candidate| candidate.next_step_ids.iter().any(|next_id| next_id == step_id))
        .filter(|candidate| candidate.status == "completed")
        .count() as u16
}

fn place_step_after(template: &mut WorkflowTemplate, step_id: &str, after_step_id: &str) -> Result<(), String> {
    let clean_after_id = clean_step_id(after_step_id.to_owned(), "after_step_id")?;
    if clean_after_id == step_id {
        return Err("workflow step cannot be placed after itself".to_owned());
    }
    let current_index = step_index(template, step_id)?;
    let after_index = step_index(template, &clean_after_id)?;
    for step in &mut template.steps {
        step.next_step_ids.retain(|id| id != step_id);
    }
    let previous_next_ids = template.steps[after_index].next_step_ids.clone();
    template.steps[current_index].next_step_ids = previous_next_ids
        .into_iter()
        .filter(|id| id != step_id && id != &clean_after_id)
        .collect();
    template.steps[after_index].next_step_ids = vec![step_id.to_owned()];
    let lane = template.steps[current_index].lane.clone();
    template.steps[current_index].position_x = lane_position_x(&lane);
    template.steps[current_index].position_y = template.steps[after_index].position_y.saturating_add(1).min(MAX_POSITION);
    Ok(())
}

async fn postgres_workflow_session() -> Result<PostgresClientSession, String> {
    let config = PostgresRepositoryConfig::from_env_parts(
        std::env::var("BITWEEN_POSTGRES_DSN").ok(),
        std::env::var("BITWEEN_POSTGRES_TLS_POLICY").ok(),
    )?;
    let scope = PostgresTenantScope::new(
        required_env("BITWEEN_POSTGRES_TENANT_ID")?,
        required_env("BITWEEN_POSTGRES_LEGAL_ENTITY_ID")?,
        required_env("BITWEEN_POSTGRES_WORKPLACE_ID")?,
    )?;
    let session = config
        .connect_client_session(scope)
        .await
        .map_err(postgres_failure)?;
    session
        .apply_required_migrations(&required_postgres_migrations())
        .await
        .map_err(postgres_failure)?;
    Ok(session)
}

async fn load_postgres_store(session: &PostgresClientSession) -> Result<WorkflowTemplateStore, String> {
    let template_rows = session
        .client
        .query(
            "SELECT t.id::text, v.id::text, t.template_key, v.version, t.title_key, EXTRACT(EPOCH FROM t.updated_at)::bigint \
             FROM bitween_workflow.workflow_template t \
             JOIN bitween_workflow.workflow_template_version v \
               ON v.template_id = t.id AND v.tenant_id = t.tenant_id AND v.version = t.active_version \
             WHERE t.tenant_id = $1 \
             ORDER BY t.template_key",
            &[&session.scope.tenant_id],
        )
        .await
        .map_err(|_| "workflow_postgres_template_query_failed".to_owned())?;

    let mut templates = Vec::with_capacity(template_rows.len());
    let mut template_versions = Vec::new();
    let mut data_records = Vec::new();
    for row in template_rows {
        let template_id: String = row.get(0);
        let version_id: String = row.get(1);
        let template_key: String = row.get(2);
        let version: i32 = row.get(3);
        let title_key: String = row.get(4);
        let updated_at_unix: i64 = row.get(5);

        let mut steps = load_postgres_steps(session, &version_id).await?;
        apply_postgres_edges(session, &version_id, &mut steps).await?;
        data_records.extend(
            load_postgres_data_records(session, &template_key, &template_id, &version_id).await?,
        );
        template_versions.extend(load_postgres_template_versions(session, &template_key, &template_id).await?);

        templates.push(WorkflowTemplate {
            id: template_key,
            version: version.try_into().unwrap_or(1),
            title_key,
            steps,
            updated_at_unix: updated_at_unix.try_into().unwrap_or(0),
        });
    }

    let mut store = WorkflowTemplateStore {
        schema: WORKFLOW_TEMPLATE_STORE_SCHEMA.to_owned(),
        templates,
        template_versions,
        analytics: Vec::new(),
        audit_events: Vec::new(),
        runtime_events: Vec::new(),
        data_records,
    };
    sort_store(&mut store);
    refresh_store_analytics(&mut store);
    Ok(store)
}

async fn load_postgres_steps(
    session: &PostgresClientSession,
    version_id: &str,
) -> Result<Vec<WorkflowStepOverride>, String> {
    let rows = session
        .client
        .query(
            "SELECT id::text, step_key, title, action, owner_role, status, tone, lane, node_type, \
                    position_x, position_y, slo_minutes, escalation_role, \
                    condition_expression::text, permission_scope::text, enabled, \
                    EXTRACT(EPOCH FROM updated_at)::bigint \
             FROM bitween_workflow.workflow_node \
             WHERE tenant_id = $1 AND template_version_id = $2::uuid \
             ORDER BY position_y, position_x, step_key",
            &[&session.scope.tenant_id, &version_id],
        )
        .await
        .map_err(|_| "workflow_postgres_node_query_failed".to_owned())?;

    rows.into_iter()
        .map(|row| {
            let step_key: String = row.get(1);
            let title: String = row.get(2);
            let action: String = row.get(3);
            let position_x: i32 = row.get(9);
            let position_y: i32 = row.get(10);
            let slo_minutes: Option<i32> = row.get(11);
            let condition_json: String = row.get(13);
            let permission_json: String = row.get(14);
            let updated_at_unix: i64 = row.get(16);
            Ok(WorkflowStepOverride {
                id: step_key.clone(),
                title: title_override_from_postgres(&step_key, title),
                action: title_override_from_postgres(&step_key, action),
                owner: row.get(4),
                status: row.get(5),
                tone: row.get(6),
                lane: row.get(7),
                node_type: row.get(8),
                position_x: position_x.try_into().unwrap_or(0),
                position_y: position_y.try_into().unwrap_or(0),
                next_step_ids: Vec::new(),
                slo_minutes: slo_minutes.and_then(|value| value.try_into().ok()),
                escalation_role: row.get(12),
                condition_expression: json_string_map(&condition_json)?,
                permission_scope: json_string_map(&permission_json)?,
                enabled: row.get(15),
                updated_at_unix: updated_at_unix.try_into().unwrap_or(0),
            })
        })
        .collect()
}

async fn apply_postgres_edges(
    session: &PostgresClientSession,
    version_id: &str,
    steps: &mut [WorkflowStepOverride],
) -> Result<(), String> {
    let rows = session
        .client
        .query(
            "SELECT from_node.step_key, to_node.step_key \
             FROM bitween_workflow.workflow_edge edge \
             JOIN bitween_workflow.workflow_node from_node ON from_node.id = edge.from_node_id \
             JOIN bitween_workflow.workflow_node to_node ON to_node.id = edge.to_node_id \
             WHERE edge.tenant_id = $1 AND edge.template_version_id = $2::uuid \
             ORDER BY from_node.step_key, edge.sort_order, to_node.step_key",
            &[&session.scope.tenant_id, &version_id],
        )
        .await
        .map_err(|_| "workflow_postgres_edge_query_failed".to_owned())?;

    for row in rows {
        let from_step: String = row.get(0);
        let to_step: String = row.get(1);
        if let Some(step) = steps.iter_mut().find(|candidate| candidate.id == from_step) {
            step.next_step_ids.push(to_step);
        }
    }
    Ok(())
}

async fn load_postgres_data_records(
    session: &PostgresClientSession,
    template_key: &str,
    template_id: &str,
    version_id: &str,
) -> Result<Vec<WorkflowDataRecord>, String> {
    let rows = session
        .client
        .query(
            "SELECT step_key, record_type, target, status, record_count, payload::text, \
                    EXTRACT(EPOCH FROM updated_at)::bigint \
             FROM bitween_workflow.workflow_data_record \
             WHERE tenant_id = $1 AND template_version_id = $2::uuid \
             ORDER BY updated_at DESC, step_key",
            &[&session.scope.tenant_id, &version_id],
        )
        .await
        .map_err(|_| "workflow_postgres_data_record_query_failed".to_owned())?;

    rows.into_iter()
        .map(|row| {
            let step_id: String = row.get(0);
            let record_type: String = row.get(1);
            let metadata_json: String = row.get(5);
            let updated_at_unix: i64 = row.get(6);
            Ok(WorkflowDataRecord {
                id: format!(
                    "workflow-data-record-{}-{}-{}-{}",
                    clean_step_id(template_key.to_owned(), "template id")?,
                    clean_step_id(step_id.clone(), "step id")?,
                    clean_step_id(record_type.clone(), "record_type")?,
                    &sha256_hex(format!("{template_id}:{version_id}:{step_id}:{record_type}").as_bytes())[..12]
                ),
                template_id: template_key.to_owned(),
                step_id,
                record_type,
                target: row.get(2),
                status: row.get(3),
                record_count: row.get::<_, i32>(4).try_into().unwrap_or(0),
                metadata: json_string_map(&metadata_json)?,
                updated_at_unix: updated_at_unix.try_into().unwrap_or(0),
            })
        })
        .collect()
}

async fn load_postgres_template_versions(
    session: &PostgresClientSession,
    template_key: &str,
    template_id: &str,
) -> Result<Vec<WorkflowTemplateVersionRecord>, String> {
    let rows = session
        .client
        .query(
            "SELECT id::text, version, graph_hash, change_summary, created_by, \
                    EXTRACT(EPOCH FROM created_at)::bigint, rollback_of_version \
             FROM bitween_workflow.workflow_template_version \
             WHERE tenant_id = $1 AND template_id = $2::uuid \
             ORDER BY version",
            &[&session.scope.tenant_id, &template_id],
        )
        .await
        .map_err(|_| "workflow_postgres_version_history_query_failed".to_owned())?;

    let mut versions = Vec::with_capacity(rows.len());
    for row in rows {
        let version_id: String = row.get(0);
        let version: i32 = row.get(1);
        let created_at_unix: i64 = row.get(5);
        let rollback_of_version: Option<i32> = row.get(6);
        let mut steps = load_postgres_steps(session, &version_id).await?;
        apply_postgres_edges(session, &version_id, &mut steps).await?;
        versions.push(WorkflowTemplateVersionRecord {
            id: format!(
                "workflow-template-version-{}-{}",
                clean_template_key(template_key.to_owned(), "template id")?,
                version
            ),
            template_id: template_key.to_owned(),
            version: version.try_into().unwrap_or(1),
            graph_hash: row.get(2),
            change_summary: row.get(3),
            actor_role: row.get(4),
            created_at_unix: created_at_unix.try_into().unwrap_or(0),
            rollback_of_version: rollback_of_version.and_then(|value| value.try_into().ok()),
            steps,
        });
    }
    Ok(versions)
}

async fn save_postgres_store(
    session: &mut PostgresClientSession,
    store: &WorkflowTemplateStore,
    action: &str,
) -> Result<(), String> {
    let tenant_id = session.scope.tenant_id.clone();
    let transaction = session
        .client
        .transaction()
        .await
        .map_err(|_| "workflow_postgres_transaction_start_failed".to_owned())?;
    for template in &store.templates {
        save_postgres_template(&transaction, &tenant_id, store, template, action).await?;
    }
    transaction
        .commit()
        .await
        .map_err(|_| "workflow_postgres_transaction_commit_failed".to_owned())
}

async fn save_postgres_template(
    transaction: &tokio_postgres::Transaction<'_>,
    tenant_id: &str,
    store: &WorkflowTemplateStore,
    template: &WorkflowTemplate,
    action: &str,
) -> Result<(), String> {
    let actor = postgres_actor();
    let active_version: i32 = template.version.try_into().unwrap_or(1);
    let version_record = store
        .template_versions
        .iter()
        .find(|record| record.template_id == template.id && record.version == template.version);
    let change_summary = version_record
        .map(|record| record.change_summary.clone())
        .unwrap_or_else(|| format!("workflow_template_store:{action}"));
    let rollback_of_version = version_record
        .and_then(|record| record.rollback_of_version)
        .and_then(|version| i32::try_from(version).ok());
    let template_id = transaction
        .query_one(
            "INSERT INTO bitween_workflow.workflow_template \
               (tenant_id, template_key, title_key, business_domain, status, active_version, owner_role, created_by, updated_by) \
             VALUES ($1, $2, $3, 'payroll', 'published', $4, 'payroll_manager', $5, $5) \
             ON CONFLICT (tenant_id, template_key) DO UPDATE SET \
               title_key = EXCLUDED.title_key, active_version = EXCLUDED.active_version, \
               status = 'published', updated_by = EXCLUDED.updated_by, updated_at = now() \
             RETURNING id::text",
            &[
                &tenant_id,
                &template.id,
                &template.title_key,
                &active_version,
                &actor,
            ],
        )
        .await
        .map_err(|_| "workflow_postgres_template_upsert_failed".to_owned())?
        .get::<_, String>(0);

    let graph_hash = workflow_graph_hash(template)?;
    let version_id = transaction
        .query_one(
            "INSERT INTO bitween_workflow.workflow_template_version \
               (template_id, tenant_id, version, status, graph_hash, change_summary, created_by, rollback_of_version) \
             VALUES ($1::uuid, $2, $3, 'published', $4, $5, $6, $7) \
             ON CONFLICT (template_id, version) DO UPDATE SET \
               status = 'published', graph_hash = EXCLUDED.graph_hash, change_summary = EXCLUDED.change_summary, \
               rollback_of_version = EXCLUDED.rollback_of_version, \
               published_by = EXCLUDED.created_by, published_at = now() \
             RETURNING id::text",
            &[
                &template_id,
                &tenant_id,
                &active_version,
                &graph_hash,
                &change_summary,
                &actor,
                &rollback_of_version,
            ],
        )
        .await
        .map_err(|_| "workflow_postgres_version_upsert_failed".to_owned())?
        .get::<_, String>(0);

    transaction
        .execute(
            "DELETE FROM bitween_workflow.workflow_edge WHERE tenant_id = $1 AND template_version_id = $2::uuid",
            &[&tenant_id, &version_id],
        )
        .await
        .map_err(|_| "workflow_postgres_edge_replace_failed".to_owned())?;
    transaction
        .execute(
            "DELETE FROM bitween_workflow.workflow_node WHERE tenant_id = $1 AND template_version_id = $2::uuid",
            &[&tenant_id, &version_id],
        )
        .await
        .map_err(|_| "workflow_postgres_node_replace_failed".to_owned())?;

    let node_ids = save_postgres_nodes(transaction, tenant_id, template, &template_id, &version_id, &actor).await?;
    save_postgres_edges(transaction, tenant_id, template, &template_id, &version_id, &node_ids, &actor).await?;
    save_postgres_data_records(transaction, tenant_id, store_data_for_template(store, &template.id), &template_id, &version_id, &actor).await?;
    insert_postgres_audit_event(transaction, tenant_id, &template_id, Some(&version_id), None, action, &actor).await?;
    Ok(())
}

async fn save_postgres_nodes(
    transaction: &tokio_postgres::Transaction<'_>,
    tenant_id: &str,
    template: &WorkflowTemplate,
    template_id: &str,
    version_id: &str,
    actor: &str,
) -> Result<BTreeMap<String, String>, String> {
    let mut node_ids = BTreeMap::new();
    for step in &template.steps {
        let title = step.title.clone().unwrap_or_else(|| step.id.clone());
        let action = step.action.clone().unwrap_or_else(|| step.id.clone());
        let position_x: i32 = step.position_x.into();
        let position_y: i32 = step.position_y.into();
        let slo_minutes = step.slo_minutes.map(i32::from);
        let condition_expression = serde_json::to_string(&step.condition_expression)
            .map_err(|_| "workflow_postgres_condition_serialize_failed".to_owned())?;
        let permission_scope = serde_json::to_string(&step.permission_scope)
            .map_err(|_| "workflow_postgres_permission_serialize_failed".to_owned())?;
        let node_id = transaction
            .query_one(
                "INSERT INTO bitween_workflow.workflow_node \
                   (template_id, template_version_id, tenant_id, step_key, title, action, owner_role, status, tone, lane, node_type, \
                    position_x, position_y, condition_expression, permission_scope, slo_minutes, escalation_role, enabled, updated_by) \
                 VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::jsonb, $15::jsonb, $16, $17, $18, $19) \
                 RETURNING id::text",
                &[
                    &template_id,
                    &version_id,
                    &tenant_id,
                    &step.id,
                    &title,
                    &action,
                    &step.owner,
                    &step.status,
                    &step.tone,
                    &step.lane,
                    &step.node_type,
                    &position_x,
                    &position_y,
                    &condition_expression,
                    &permission_scope,
                    &slo_minutes,
                    &step.escalation_role,
                    &step.enabled,
                    &actor,
                ],
            )
            .await
            .map_err(|_| "workflow_postgres_node_insert_failed".to_owned())?
            .get::<_, String>(0);
        node_ids.insert(step.id.clone(), node_id);
    }
    Ok(node_ids)
}

async fn save_postgres_edges(
    transaction: &tokio_postgres::Transaction<'_>,
    tenant_id: &str,
    template: &WorkflowTemplate,
    template_id: &str,
    version_id: &str,
    node_ids: &BTreeMap<String, String>,
    actor: &str,
) -> Result<(), String> {
    for step in &template.steps {
        let from_node_id = node_ids
            .get(&step.id)
            .ok_or_else(|| "workflow_postgres_edge_from_missing".to_owned())?;
        for (sort_order, next_step_id) in step.next_step_ids.iter().enumerate() {
            let to_node_id = node_ids
                .get(next_step_id)
                .ok_or_else(|| "workflow_postgres_edge_to_missing".to_owned())?;
            let sort_order: i32 = sort_order.try_into().unwrap_or(0);
            transaction
                .execute(
                    "INSERT INTO bitween_workflow.workflow_edge \
                       (template_id, template_version_id, tenant_id, from_node_id, to_node_id, edge_type, condition_expression, sort_order, created_by) \
                     VALUES ($1::uuid, $2::uuid, $3, $4::uuid, $5::uuid, 'success', '{}'::jsonb, $6, $7)",
                    &[
                        &template_id,
                        &version_id,
                        &tenant_id,
                        &from_node_id,
                        &to_node_id,
                        &sort_order,
                        &actor,
                    ],
                )
                .await
                .map_err(|_| "workflow_postgres_edge_insert_failed".to_owned())?;
        }
    }
    Ok(())
}

async fn save_postgres_data_records(
    transaction: &tokio_postgres::Transaction<'_>,
    tenant_id: &str,
    records: Vec<WorkflowDataRecord>,
    template_id: &str,
    version_id: &str,
    actor: &str,
) -> Result<(), String> {
    for record in records {
        let scope_hash = sha256_hex(record.id.as_bytes());
        let business_scope = serde_json::to_string(&record.metadata)
            .map_err(|_| "workflow_postgres_business_scope_serialize_failed".to_owned())?;
        let payload = business_scope.clone();
        let evidence = serde_json::to_string(&BTreeMap::from([(
            "source".to_owned(),
            "workflow_template_store".to_owned(),
        )]))
        .map_err(|_| "workflow_postgres_evidence_serialize_failed".to_owned())?;
        let record_count: i32 = record.record_count.into();
        transaction
            .execute(
                "INSERT INTO bitween_workflow.workflow_data_record \
                   (template_id, template_version_id, tenant_id, step_key, record_type, target, status, scope_hash, business_scope, record_count, payload, evidence, updated_by) \
                 VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11::jsonb, $12::jsonb, $13) \
                 ON CONFLICT (tenant_id, template_version_id, step_key, record_type, scope_hash) DO UPDATE SET \
                   target = EXCLUDED.target, status = EXCLUDED.status, business_scope = EXCLUDED.business_scope, \
                   record_count = EXCLUDED.record_count, payload = EXCLUDED.payload, evidence = EXCLUDED.evidence, \
                   updated_by = EXCLUDED.updated_by, updated_at = now()",
                &[
                    &template_id,
                    &version_id,
                    &tenant_id,
                    &record.step_id,
                    &record.record_type,
                    &record.target,
                    &record.status,
                    &scope_hash,
                    &business_scope,
                    &record_count,
                    &payload,
                    &evidence,
                    &actor,
                ],
            )
            .await
            .map_err(|_| "workflow_postgres_data_record_upsert_failed".to_owned())?;
    }
    Ok(())
}

async fn insert_postgres_audit_event(
    transaction: &tokio_postgres::Transaction<'_>,
    tenant_id: &str,
    template_id: &str,
    version_id: Option<&str>,
    step_key: Option<&str>,
    action: &str,
    actor: &str,
) -> Result<(), String> {
    let version_id_param = version_id.map(str::to_owned);
    let step_key_param = step_key.map(str::to_owned);
    let after_state = serde_json::to_string(&BTreeMap::from([(
        "operation".to_owned(),
        action.to_owned(),
    )]))
    .map_err(|_| "workflow_postgres_audit_serialize_failed".to_owned())?;
    transaction
        .execute(
            "INSERT INTO bitween_workflow.workflow_audit_event \
               (template_id, template_version_id, tenant_id, step_key, action, actor_user_id, actor_role, before_state, after_state, trace_id) \
             VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, 'platform_owner', '{}'::jsonb, $7::jsonb, $8)",
            &[
                &template_id,
                &version_id_param,
                &tenant_id,
                &step_key_param,
                &postgres_audit_action(action),
                &actor,
                &after_state,
                &format!("workflow-template-store-{action}"),
            ],
        )
        .await
        .map_err(|_| "workflow_postgres_audit_insert_failed".to_owned())?;
    Ok(())
}

fn postgres_audit_action(action: &str) -> &'static str {
    match action {
        "bootstrap_workflow_templates" => "create_template",
        "add_step" => "add_step",
        "update_step" => "update_step",
        "delete_step" => "delete_step",
        "execute_step" => "execute_step",
        "rollback_version" => "rollback_version",
        _ => "update_step",
    }
}

fn store_data_for_template(store: &WorkflowTemplateStore, template_id: &str) -> Vec<WorkflowDataRecord> {
    store
        .data_records
        .iter()
        .filter(|record| record.template_id == template_id)
        .cloned()
        .collect()
}

fn postgres_dsn_configured() -> bool {
    std::env::var("BITWEEN_POSTGRES_DSN")
        .ok()
        .map(|value| !value.trim().is_empty())
        .unwrap_or(false)
}

fn required_env(name: &str) -> Result<String, String> {
    std::env::var(name)
        .ok()
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty())
        .ok_or_else(|| match name {
            "BITWEEN_POSTGRES_TENANT_ID" => "postgres_tenant_scope_required".to_owned(),
            "BITWEEN_POSTGRES_LEGAL_ENTITY_ID" => "postgres_legal_entity_scope_required".to_owned(),
            "BITWEEN_POSTGRES_WORKPLACE_ID" => "postgres_workplace_scope_required".to_owned(),
            _ => format!("missing required environment: {name}"),
        })
}

fn postgres_actor() -> String {
    std::env::var("BITWEEN_SESSION_JWT_SUBJECT")
        .ok()
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "workflow-template-store".to_owned())
}

fn postgres_failure(failure: PostgresConnectionFailure) -> String {
    format!("{} ({})", failure.code, failure.redacted_dsn)
}

fn title_override_from_postgres(step_key: &str, value: String) -> Option<String> {
    let cleaned = value.trim().to_owned();
    if cleaned.is_empty() || cleaned == step_key {
        None
    } else {
        Some(cleaned)
    }
}

fn json_string_map(value: &str) -> Result<BTreeMap<String, String>, String> {
    let parsed = serde_json::from_str::<serde_json::Value>(value)
        .map_err(|_| "workflow_postgres_json_parse_failed".to_owned())?;
    let serde_json::Value::Object(map) = parsed else {
        return Err("workflow_postgres_json_object_required".to_owned());
    };

    Ok(map
        .into_iter()
        .map(|(key, value)| (key, json_value_to_string(value)))
        .collect())
}

fn json_value_to_string(value: serde_json::Value) -> String {
    match value {
        serde_json::Value::String(value) => value,
        serde_json::Value::Bool(value) => value.to_string(),
        serde_json::Value::Number(value) => value.to_string(),
        serde_json::Value::Null => String::new(),
        other => other.to_string(),
    }
}

fn workflow_graph_hash(template: &WorkflowTemplate) -> Result<String, String> {
    let body = serde_json::to_vec(template)
        .map_err(|_| "workflow_postgres_graph_hash_serialize_failed".to_owned())?;
    Ok(sha256_hex(&body))
}

fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    digest
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>()
}

fn load_store(path: &Path) -> Result<WorkflowTemplateStore, String> {
    if !path.exists() {
        return Ok(default_store(now_unix()));
    }
    let body = fs::read_to_string(path).map_err(|error| error.to_string())?;
    let store = serde_json::from_str::<WorkflowTemplateStore>(&body).map_err(|error| error.to_string())?;
    validate_store(store)
}

fn save_store(path: &Path, store: &WorkflowTemplateStore) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    let body = serde_json::to_string_pretty(store).map_err(|error| error.to_string())?;
    fs::write(path, format!("{body}\n")).map_err(|error| error.to_string())
}

fn validate_store(mut store: WorkflowTemplateStore) -> Result<WorkflowTemplateStore, String> {
    store.schema = WORKFLOW_TEMPLATE_STORE_SCHEMA.to_owned();
    if store.templates.is_empty() {
        store.templates = default_store(now_unix()).templates;
    }
    for template in &mut store.templates {
        if template.id.trim().is_empty() {
            return Err("workflow template id is required".to_owned());
        }
        if template.steps.is_empty() && template.id == DEFAULT_TEMPLATE_ID {
            template.steps = default_steps(template.updated_at_unix);
        }
        let step_ids = template
            .steps
            .iter()
            .map(|step| clean_step_id(step.id.clone(), "step id"))
            .collect::<Result<HashSet<_>, _>>()?;
        for step in &mut template.steps {
            step.id = clean_step_id(step.id.clone(), "step id")?;
            step.title = step
                .title
                .clone()
                .map(|value| clean_label(value, "title", MAX_LABEL_LEN))
                .transpose()?;
            step.action = step
                .action
                .clone()
                .map(|value| clean_label(value, "action", MAX_ACTION_LEN))
                .transpose()?;
            step.owner = allowed_value(step.owner.clone(), "owner", allowed_owners())?;
            step.status = allowed_value(step.status.clone(), "status", allowed_statuses())?;
            step.tone = allowed_value(step.tone.clone(), "tone", allowed_tones())?;
            step.lane = allowed_value(step.lane.clone(), "lane", allowed_lanes())?;
            step.node_type = allowed_value(step.node_type.clone(), "node_type", allowed_node_types())?;
            step.position_x = validate_position(step.position_x, "position_x")?;
            step.position_y = validate_position(step.position_y, "position_y")?;
            step.slo_minutes = step.slo_minutes.map(validate_slo_minutes).transpose()?;
            step.escalation_role = step
                .escalation_role
                .clone()
                .map(|value| allowed_value(value, "escalation_role", allowed_owners()))
                .transpose()?;
            step.condition_expression =
                clean_metadata_map(step.condition_expression.clone(), "condition_expression")?;
            step.permission_scope = clean_metadata_map(step.permission_scope.clone(), "permission_scope")?;
            backfill_builtin_step_controls(step);
            normalize_step_position(step);
            step.next_step_ids = clean_existing_next_ids(step.next_step_ids.clone(), &step.id, &step_ids)?;
        }
        if template.steps.iter().all(|step| step.next_step_ids.is_empty()) {
            wire_sequentially(template);
        }
    }
    store.template_versions = store
        .template_versions
        .into_iter()
        .map(validate_template_version_record)
        .collect::<Result<Vec<_>, _>>()?;
    let timestamp = store
        .templates
        .iter()
        .map(|template| template.updated_at_unix)
        .max()
        .unwrap_or_else(now_unix);
    ensure_template_version_records(&mut store, timestamp)?;
    sort_store(&mut store);
    refresh_store_analytics(&mut store);
    Ok(store)
}

fn validate_template_version_record(
    mut record: WorkflowTemplateVersionRecord,
) -> Result<WorkflowTemplateVersionRecord, String> {
    record.template_id = clean_template_key(record.template_id, "template id")?;
    if record.version == 0 {
        return Err("workflow template version must be greater than zero".to_owned());
    }
    record.change_summary = clean_label(record.change_summary, "change_summary", MAX_LABEL_LEN)?;
    record.actor_role = allowed_value(record.actor_role, "actor_role", allowed_owners())?;
    if matches!(record.rollback_of_version, Some(0)) {
        return Err("workflow rollback version must be greater than zero".to_owned());
    }
    record.steps = validate_historical_steps(record.steps)?;
    let template = WorkflowTemplate {
        id: record.template_id.clone(),
        version: record.version,
        title_key: "preview.workflow.templates.payrollClose.title".to_owned(),
        steps: record.steps.clone(),
        updated_at_unix: record.created_at_unix,
    };
    record.graph_hash = workflow_graph_hash(&template)?;
    record.id = format!(
        "workflow-template-version-{}-{}-{}",
        record.template_id,
        record.version,
        &record.graph_hash[..12]
    );
    Ok(record)
}

fn validate_historical_steps(mut steps: Vec<WorkflowStepOverride>) -> Result<Vec<WorkflowStepOverride>, String> {
    if steps.is_empty() {
        return Err("workflow template version must keep at least one step".to_owned());
    }
    let step_ids = steps
        .iter()
        .map(|step| clean_step_id(step.id.clone(), "step id"))
        .collect::<Result<HashSet<_>, _>>()?;
    for step in &mut steps {
        step.id = clean_step_id(step.id.clone(), "step id")?;
        step.title = step
            .title
            .clone()
            .map(|value| clean_label(value, "title", MAX_LABEL_LEN))
            .transpose()?;
        step.action = step
            .action
            .clone()
            .map(|value| clean_label(value, "action", MAX_ACTION_LEN))
            .transpose()?;
        step.owner = allowed_value(step.owner.clone(), "owner", allowed_owners())?;
        step.status = allowed_value(step.status.clone(), "status", allowed_statuses())?;
        step.tone = allowed_value(step.tone.clone(), "tone", allowed_tones())?;
        step.lane = allowed_value(step.lane.clone(), "lane", allowed_lanes())?;
        step.node_type = allowed_value(step.node_type.clone(), "node_type", allowed_node_types())?;
        step.position_x = validate_position(step.position_x, "position_x")?;
        step.position_y = validate_position(step.position_y, "position_y")?;
        step.slo_minutes = step.slo_minutes.map(validate_slo_minutes).transpose()?;
        step.escalation_role = step
            .escalation_role
            .clone()
            .map(|value| allowed_value(value, "escalation_role", allowed_owners()))
            .transpose()?;
        step.condition_expression = clean_metadata_map(step.condition_expression.clone(), "condition_expression")?;
        step.permission_scope = clean_metadata_map(step.permission_scope.clone(), "permission_scope")?;
        backfill_builtin_step_controls(step);
        normalize_step_position(step);
        step.next_step_ids = clean_existing_next_ids(step.next_step_ids.clone(), &step.id, &step_ids)?;
    }
    if steps.iter().all(|step| step.next_step_ids.is_empty()) {
        wire_sequentially_for_steps(&mut steps);
    }
    steps.sort_by(step_sort_key_cmp);
    Ok(steps)
}

fn default_store(updated_at_unix: u64) -> WorkflowTemplateStore {
    let mut store = WorkflowTemplateStore {
        schema: WORKFLOW_TEMPLATE_STORE_SCHEMA.to_owned(),
        templates: vec![WorkflowTemplate {
            id: DEFAULT_TEMPLATE_ID.to_owned(),
            version: 1,
            title_key: "preview.workflow.templates.payrollClose.title".to_owned(),
            steps: default_steps(updated_at_unix),
            updated_at_unix,
        }],
        template_versions: Vec::new(),
        analytics: Vec::new(),
        audit_events: Vec::new(),
        runtime_events: Vec::new(),
        data_records: Vec::new(),
    };
    ensure_template_version_records(&mut store, updated_at_unix)
        .expect("default workflow template version record is valid");
    refresh_store_analytics(&mut store);
    store
}

fn default_steps(updated_at_unix: u64) -> Vec<WorkflowStepOverride> {
    let mut steps = vec![
        step("set-payroll-scope", "payroll_manager", "rule", "condition", 30, 10, updated_at_unix),
        step("configure-access", "it_security_admin", "rule", "condition", 30, 20, updated_at_unix),
        step("close-attendance", "hr_operator", "source", "trigger", 10, 30, updated_at_unix),
        step("close-payroll-inputs", "payroll_operator", "operation", "action", 50, 40, updated_at_unix),
        step("review-deductions", "payroll_manager", "operation", "condition", 50, 50, updated_at_unix),
        step("run-calculation", "payroll_operator", "operation", "action", 50, 60, updated_at_unix),
        step("request-approval", "approval_signer", "approval", "approval", 70, 70, updated_at_unix),
        step("prepare-payout", "payroll_manager", "operation", "action", 50, 80, updated_at_unix),
        step("archive-payroll-evidence", "archive_operator", "record", "record", 90, 90, updated_at_unix),
    ];
    wire_sequentially_for_steps(&mut steps);
    steps
}

fn step(
    id: &str,
    owner: &str,
    lane: &str,
    node_type: &str,
    position_x: u16,
    position_y: u16,
    updated_at_unix: u64,
) -> WorkflowStepOverride {
    WorkflowStepOverride {
        id: id.to_owned(),
        title: None,
        action: None,
        owner: owner.to_owned(),
        status: "needs_attention".to_owned(),
        tone: "attention".to_owned(),
        lane: lane.to_owned(),
        node_type: node_type.to_owned(),
        position_x,
        position_y,
        next_step_ids: Vec::new(),
        slo_minutes: default_slo_minutes(id),
        escalation_role: default_escalation_role(owner),
        condition_expression: default_condition_expression(id),
        permission_scope: default_permission_scope(id),
        enabled: true,
        updated_at_unix,
    }
}

fn default_slo_minutes(id: &str) -> Option<u16> {
    Some(match id {
        "set-payroll-scope" => 180,
        "configure-access" => 180,
        "close-attendance" => 240,
        "close-payroll-inputs" => 180,
        "review-deductions" => 180,
        "run-calculation" => 120,
        "request-approval" => 240,
        "prepare-payout" => 180,
        "archive-payroll-evidence" => 480,
        _ => return None,
    })
}

fn default_escalation_role(owner: &str) -> Option<String> {
    Some(match owner {
        "hr_operator" => "hr_manager",
        "payroll_operator" => "payroll_manager",
        "approval_signer" => "payroll_manager",
        "archive_operator" => "payroll_manager",
        "it_security_admin" => "platform_owner",
        "hr_manager" | "payroll_manager" | "platform_owner" => owner,
        _ => return None,
    }
    .to_owned())
}

fn default_condition_expression(id: &str) -> BTreeMap<String, String> {
    let rule = match id {
        "set-payroll-scope" => "tenant workplace and pay period must be selected",
        "configure-access" => "actor role must match tenant and payroll period policy",
        "review-deductions" => "deduction exceptions must be assigned before calculation",
        _ => return BTreeMap::new(),
    };
    BTreeMap::from([("rule".to_owned(), rule.to_owned())])
}

fn default_permission_scope(id: &str) -> BTreeMap<String, String> {
    let object_scope = match id {
        "close-attendance" => "hr_attendance",
        "archive-payroll-evidence" => "payroll_evidence",
        "request-approval" => "approval_packet",
        "set-payroll-scope"
        | "configure-access"
        | "close-payroll-inputs"
        | "review-deductions"
        | "run-calculation"
        | "prepare-payout" => "payroll_period",
        _ => return BTreeMap::new(),
    };
    BTreeMap::from([
        ("data_class".to_owned(), "sensitive".to_owned()),
        ("tenant_required".to_owned(), "true".to_owned()),
        ("object_scope".to_owned(), object_scope.to_owned()),
    ])
}

fn backfill_builtin_step_controls(step: &mut WorkflowStepOverride) {
    if step.slo_minutes.is_none() {
        step.slo_minutes = default_slo_minutes(&step.id);
    }
    if step.escalation_role.is_none() && step.slo_minutes.is_some() {
        step.escalation_role = default_escalation_role(&step.owner);
    }
    if step.condition_expression.is_empty() {
        step.condition_expression = default_condition_expression(&step.id);
    }
    if step.permission_scope.is_empty() {
        step.permission_scope = default_permission_scope(&step.id);
    }
}

fn wire_sequentially(template: &mut WorkflowTemplate) {
    template.steps.sort_by(step_sort_key_cmp);
    wire_sequentially_for_steps(&mut template.steps);
}

fn wire_sequentially_for_steps(steps: &mut [WorkflowStepOverride]) {
    for index in 0..steps.len() {
        steps[index].next_step_ids = steps
            .get(index + 1)
            .map(|next| vec![next.id.clone()])
            .unwrap_or_default();
    }
}

fn sort_store(store: &mut WorkflowTemplateStore) {
    store.templates.sort_by(|left, right| left.id.cmp(&right.id));
    for template in &mut store.templates {
        template.steps.sort_by(step_sort_key_cmp);
    }
    store
        .template_versions
        .sort_by(|left, right| (left.template_id.as_str(), left.version).cmp(&(right.template_id.as_str(), right.version)));
    store.audit_events.sort_by(|left, right| left.updated_at_unix.cmp(&right.updated_at_unix));
    store.runtime_events.sort_by(|left, right| left.updated_at_unix.cmp(&right.updated_at_unix));
    store.data_records.sort_by(|left, right| left.id.cmp(&right.id));
}

fn refresh_store_analytics(store: &mut WorkflowTemplateStore) {
    store.analytics = store.templates.iter().map(analyze_template).collect();
}

fn reject_blocking_graph_issues(template: &WorkflowTemplate) -> Result<(), String> {
    let analytics = analyze_template(template);
    if let Some(issue) = analytics
        .validation_issues
        .iter()
        .find(|issue| issue.severity == "error")
    {
        return Err(format!(
            "workflow graph edit rejected: {}",
            issue.code
        ));
    }
    Ok(())
}

fn analyze_template(template: &WorkflowTemplate) -> WorkflowTemplateAnalytics {
    let step_ids = template
        .steps
        .iter()
        .map(|step| step.id.clone())
        .collect::<HashSet<_>>();
    let adjacency = template
        .steps
        .iter()
        .map(|step| {
            (
                step.id.clone(),
                step
                    .next_step_ids
                    .iter()
                    .filter(|id| step_ids.contains(*id))
                    .cloned()
                    .collect::<Vec<_>>(),
            )
        })
        .collect::<BTreeMap<_, _>>();
    let incoming = incoming_counts(&adjacency);
    let roots = template
        .steps
        .iter()
        .filter(|step| incoming.get(&step.id).copied().unwrap_or(0) == 0)
        .map(|step| step.id.clone())
        .collect::<Vec<_>>();
    let reachable = reachable_steps(&roots, &adjacency);
    let disconnected_step_ids = template
        .steps
        .iter()
        .filter(|step| !reachable.contains(&step.id))
        .map(|step| step.id.clone())
        .collect::<Vec<_>>();
    let cycle_detected = graph_has_cycle(&adjacency);
    let longest_path_steps = roots
        .iter()
        .map(|root| longest_path_from(root, &adjacency, &mut HashSet::new()))
        .max()
        .unwrap_or(0);
    let mut validation_issues = Vec::new();
    if cycle_detected {
        validation_issues.push(WorkflowValidationIssue {
            code: "cycle_detected".to_owned(),
            step_id: None,
            severity: "error".to_owned(),
        });
    }
    for step_id in &disconnected_step_ids {
        validation_issues.push(WorkflowValidationIssue {
            code: "disconnected_step".to_owned(),
            step_id: Some(step_id.clone()),
            severity: "warning".to_owned(),
        });
    }
    for step in template.steps.iter().filter(|step| step.enabled) {
        if step.slo_minutes.is_none() {
            validation_issues.push(WorkflowValidationIssue {
                code: "missing_slo".to_owned(),
                step_id: Some(step.id.clone()),
                severity: "warning".to_owned(),
            });
        }
        if step.slo_minutes.is_some() && step.escalation_role.is_none() {
            validation_issues.push(WorkflowValidationIssue {
                code: "missing_escalation_role".to_owned(),
                step_id: Some(step.id.clone()),
                severity: "warning".to_owned(),
            });
        }
        if step.node_type == "condition" && step.condition_expression.is_empty() {
            validation_issues.push(WorkflowValidationIssue {
                code: "missing_condition_expression".to_owned(),
                step_id: Some(step.id.clone()),
                severity: "warning".to_owned(),
            });
        }
        if step.permission_scope.is_empty() {
            validation_issues.push(WorkflowValidationIssue {
                code: "missing_permission_scope".to_owned(),
                step_id: Some(step.id.clone()),
                severity: "warning".to_owned(),
            });
        }
    }

    WorkflowTemplateAnalytics {
        template_id: template.id.clone(),
        step_count: template.steps.len() as u16,
        edge_count: adjacency.values().map(Vec::len).sum::<usize>() as u16,
        branch_count: adjacency.values().filter(|next| next.len() > 1).count() as u16,
        blocked_count: template.steps.iter().filter(|step| step.status == "blocked").count() as u16,
        waiting_count: template.steps.iter().filter(|step| step.status == "waiting").count() as u16,
        completed_count: template.steps.iter().filter(|step| step.status == "completed").count() as u16,
        disconnected_step_ids,
        cycle_detected,
        longest_path_steps,
        owner_loads: load_counts(template.steps.iter().map(|step| step.owner.as_str())),
        lane_loads: load_counts(template.steps.iter().map(|step| step.lane.as_str())),
        validation_issues,
    }
}

fn incoming_counts(adjacency: &BTreeMap<String, Vec<String>>) -> BTreeMap<String, u16> {
    let mut counts = adjacency
        .keys()
        .map(|id| (id.clone(), 0))
        .collect::<BTreeMap<_, _>>();
    for next_ids in adjacency.values() {
        for next_id in next_ids {
            if let Some(count) = counts.get_mut(next_id) {
                *count += 1;
            }
        }
    }
    counts
}

fn reachable_steps(roots: &[String], adjacency: &BTreeMap<String, Vec<String>>) -> HashSet<String> {
    let mut reachable = HashSet::new();
    for root in roots {
        collect_reachable(root, adjacency, &mut reachable);
    }
    reachable
}

fn collect_reachable(
    step_id: &str,
    adjacency: &BTreeMap<String, Vec<String>>,
    reachable: &mut HashSet<String>,
) {
    if !reachable.insert(step_id.to_owned()) {
        return;
    }
    if let Some(next_ids) = adjacency.get(step_id) {
        for next_id in next_ids {
            collect_reachable(next_id, adjacency, reachable);
        }
    }
}

fn graph_has_cycle(adjacency: &BTreeMap<String, Vec<String>>) -> bool {
    let mut visiting = HashSet::new();
    let mut visited = HashSet::new();
    adjacency
        .keys()
        .any(|step_id| cycle_from(step_id, adjacency, &mut visiting, &mut visited))
}

fn cycle_from(
    step_id: &str,
    adjacency: &BTreeMap<String, Vec<String>>,
    visiting: &mut HashSet<String>,
    visited: &mut HashSet<String>,
) -> bool {
    if visited.contains(step_id) {
        return false;
    }
    if !visiting.insert(step_id.to_owned()) {
        return true;
    }
    if let Some(next_ids) = adjacency.get(step_id) {
        for next_id in next_ids {
            if cycle_from(next_id, adjacency, visiting, visited) {
                return true;
            }
        }
    }
    visiting.remove(step_id);
    visited.insert(step_id.to_owned());
    false
}

fn longest_path_from(
    step_id: &str,
    adjacency: &BTreeMap<String, Vec<String>>,
    active_path: &mut HashSet<String>,
) -> u16 {
    if !active_path.insert(step_id.to_owned()) {
        return 0;
    }
    let longest_child = adjacency
        .get(step_id)
        .map(|next_ids| {
            next_ids
                .iter()
                .map(|next_id| longest_path_from(next_id, adjacency, active_path))
                .max()
                .unwrap_or(0)
        })
        .unwrap_or(0);
    active_path.remove(step_id);
    1 + longest_child
}

fn load_counts<'a>(values: impl Iterator<Item = &'a str>) -> Vec<WorkflowLoad> {
    let mut counts = BTreeMap::<String, u16>::new();
    for value in values {
        *counts.entry(value.to_owned()).or_insert(0) += 1;
    }
    counts
        .into_iter()
        .map(|(key, count)| WorkflowLoad { key, count })
        .collect()
}

fn step_sort_key_cmp(left: &WorkflowStepOverride, right: &WorkflowStepOverride) -> std::cmp::Ordering {
    (left.position_y, left.position_x, default_step_rank(&left.id), &left.id)
        .cmp(&(right.position_y, right.position_x, default_step_rank(&right.id), &right.id))
}

fn default_step_rank(id: &str) -> u8 {
    match id {
        "set-payroll-scope" => 0,
        "configure-access" => 1,
        "close-attendance" => 2,
        "close-payroll-inputs" => 3,
        "review-deductions" => 4,
        "run-calculation" => 5,
        "request-approval" => 6,
        "prepare-payout" => 7,
        "archive-payroll-evidence" => 8,
        _ => 99,
    }
}

fn read_input() -> Result<WorkflowStepInput, String> {
    let mut body = String::new();
    io::stdin()
        .read_to_string(&mut body)
        .map_err(|error| error.to_string())?;
    serde_json::from_str(&body).map_err(|error| error.to_string())
}

fn allowed_value(value: String, name: &str, allowed: &[&str]) -> Result<String, String> {
    let cleaned = clean_non_empty(value, name)?;
    if allowed.iter().any(|candidate| *candidate == cleaned) {
        return Ok(cleaned);
    }
    Err(format!("unsupported workflow {name}: {cleaned}"))
}

fn clean_non_empty(value: String, name: &str) -> Result<String, String> {
    let cleaned = value.trim().to_ascii_lowercase().replace('-', "_");
    if cleaned.is_empty() {
        return Err(format!("missing workflow {name}"));
    }
    Ok(cleaned)
}

fn clean_step_id(value: String, name: &str) -> Result<String, String> {
    let cleaned = value
        .trim()
        .to_ascii_lowercase()
        .chars()
        .map(|character| if character.is_ascii_alphanumeric() { character } else { '-' })
        .collect::<String>()
        .split('-')
        .filter(|part| !part.is_empty())
        .collect::<Vec<_>>()
        .join("-");
    if cleaned.is_empty() {
        return Err(format!("missing workflow {name}"));
    }
    Ok(cleaned)
}

fn clean_template_key(value: String, name: &str) -> Result<String, String> {
    clean_step_id(value, name)
}

fn clean_label_required(value: Option<String>, name: &str, max_len: usize) -> Result<String, String> {
    let Some(value) = value else {
        return Err(format!("missing workflow {name}"));
    };
    clean_label(value, name, max_len)
}

fn clean_label(value: String, name: &str, max_len: usize) -> Result<String, String> {
    let cleaned = value.split_whitespace().collect::<Vec<_>>().join(" ");
    if cleaned.is_empty() {
        return Err(format!("missing workflow {name}"));
    }
    if cleaned.chars().count() > max_len {
        return Err(format!("workflow {name} is too long"));
    }
    Ok(cleaned)
}

fn clean_optional_metadata(value: Option<String>, name: &str) -> Result<Option<String>, String> {
    value
        .map(|value| clean_label(value, name, MAX_LABEL_LEN))
        .transpose()
}

fn unique_step_id(template: &WorkflowTemplate, title: &str, event_seed: u128) -> String {
    let base = clean_step_id(title.to_owned(), "step id")
        .unwrap_or_else(|_| format!("step-{}", &sha256_hex(title.as_bytes())[..8]));
    if !template.steps.iter().any(|step| step.id == base) {
        return base;
    }
    let mut suffix = 2;
    loop {
        let candidate = format!("{base}-{suffix}");
        if !template.steps.iter().any(|step| step.id == candidate) {
            return candidate;
        }
        suffix += 1;
        if suffix > 999 {
            return format!("{base}-{event_seed}");
        }
    }
}

fn validate_position(value: u16, name: &str) -> Result<u16, String> {
    if value > MAX_POSITION {
        return Err(format!("workflow {name} must be between 0 and {MAX_POSITION}"));
    }
    Ok(value)
}

fn validate_slo_minutes(value: u16) -> Result<u16, String> {
    if value == 0 || value > MAX_SLO_MINUTES {
        return Err(format!(
            "workflow slo_minutes must be between 1 and {MAX_SLO_MINUTES}"
        ));
    }
    Ok(value)
}

fn clean_metadata_map(
    values: BTreeMap<String, String>,
    name: &str,
) -> Result<BTreeMap<String, String>, String> {
    let mut cleaned = BTreeMap::new();
    for (key, value) in values {
        let key = clean_metadata_key(key, name)?;
        let value = clean_label(value, name, MAX_METADATA_VALUE_LEN)?;
        cleaned.insert(key, value);
    }
    Ok(cleaned)
}

fn clean_metadata_key(value: String, name: &str) -> Result<String, String> {
    let cleaned = value
        .trim()
        .to_ascii_lowercase()
        .chars()
        .map(|character| if character.is_ascii_alphanumeric() { character } else { '_' })
        .collect::<String>()
        .split('_')
        .filter(|part| !part.is_empty())
        .collect::<Vec<_>>()
        .join("_");
    if cleaned.is_empty() {
        return Err(format!("missing workflow {name} key"));
    }
    if cleaned.chars().count() > MAX_METADATA_KEY_LEN {
        return Err(format!("workflow {name} key is too long"));
    }
    Ok(cleaned)
}

fn normalize_step_position(step: &mut WorkflowStepOverride) {
    if step.position_x == 0 {
        step.position_x = lane_position_x(&step.lane);
    }
    if step.position_y == 0 {
        step.position_y = ((default_step_rank(&step.id) as u16) + 1) * 10;
    }
}

fn lane_position_x(lane: &str) -> u16 {
    match lane {
        "source" => 10,
        "rule" => 30,
        "operation" => 50,
        "approval" => 70,
        "record" => 90,
        _ => 50,
    }
}

fn next_position_y(steps: &[WorkflowStepOverride]) -> u16 {
    steps
        .iter()
        .map(|step| step.position_y)
        .max()
        .unwrap_or(0)
        .saturating_add(10)
        .min(MAX_POSITION)
}

fn clean_next_step_ids(
    values: Vec<String>,
    step_id: &str,
    steps: &[WorkflowStepOverride],
) -> Result<Vec<String>, String> {
    let ids = steps
        .iter()
        .map(|step| step.id.clone())
        .collect::<HashSet<_>>();
    clean_existing_next_ids(values, step_id, &ids)
}

fn clean_existing_next_ids(
    values: Vec<String>,
    step_id: &str,
    step_ids: &HashSet<String>,
) -> Result<Vec<String>, String> {
    let mut seen = HashSet::new();
    let mut cleaned = Vec::new();
    for value in values {
        let id = clean_step_id(value, "next_step_id")?;
        if id == step_id {
            return Err("workflow step cannot connect to itself".to_owned());
        }
        if !step_ids.contains(&id) {
            return Err(format!("workflow next step not found: {id}"));
        }
        if seen.insert(id.clone()) {
            cleaned.push(id);
        }
    }
    Ok(cleaned)
}

fn tone_for_status(status: &str) -> &'static str {
    match status {
        "blocked" => "blocked",
        "completed" | "ready" => "ready",
        "waiting" => "neutral",
        _ => "attention",
    }
}

fn allowed_statuses() -> &'static [&'static str] {
    &["blocked", "completed", "needs_attention", "ready", "waiting"]
}

fn allowed_tones() -> &'static [&'static str] {
    &["blocked", "ready", "attention", "neutral"]
}

fn allowed_lanes() -> &'static [&'static str] {
    &["source", "rule", "operation", "approval", "record"]
}

fn allowed_node_types() -> &'static [&'static str] {
    &["trigger", "condition", "action", "approval", "record"]
}

fn allowed_owners() -> &'static [&'static str] {
    &[
        "hr_operator",
        "hr_manager",
        "payroll_operator",
        "payroll_manager",
        "approval_signer",
        "archive_operator",
        "it_security_admin",
        "platform_owner",
    ]
}

fn store_path() -> Result<PathBuf, String> {
    local_review_store_path(
        std::env::var("BITWEEN_ALLOW_LOCAL_REVIEW_STORE").ok().as_deref(),
        std::env::var("BITWEEN_WORKFLOW_TEMPLATE_STORE").ok(),
    )
}

fn local_review_store_path(
    allow_local_review_store: Option<&str>,
    configured_path: Option<String>,
) -> Result<PathBuf, String> {
    if !truthy(allow_local_review_store) {
        return Err(
            "PostgreSQL relational workflow template storage is required; set BITWEEN_POSTGRES_DSN for production wiring or BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true only for hermetic local review."
                .to_owned(),
        );
    }
    Ok(configured_path
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(".bitween/local-review/workflow/templates.json")))
}

fn truthy(value: Option<&str>) -> bool {
    matches!(
        value.map(str::trim).map(str::to_ascii_lowercase).as_deref(),
        Some("1" | "true" | "yes" | "on")
    )
}

fn now_unix() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0)
}

fn now_unix_nanos() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_nanos())
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn update(status: &str) -> WorkflowStepInput {
        WorkflowStepInput {
            id: None,
            title: None,
            action: None,
            owner: None,
            status: Some(status.to_owned()),
            tone: None,
            lane: None,
            node_type: None,
            position_x: None,
            position_y: None,
            next_step_ids: None,
            after_step_id: None,
            enabled: None,
            slo_minutes: None,
            escalation_role: None,
            condition_expression: None,
            permission_scope: None,
            actor_role: Some("platform_owner".to_owned()),
            scope_tenant: None,
            scope_workplace: None,
            scope_period: None,
        }
    }

    fn new_step_input(title: &str) -> WorkflowStepInput {
        WorkflowStepInput {
            id: None,
            title: Some(title.to_owned()),
            action: Some("Confirm the exception owner before payroll continues.".to_owned()),
            owner: Some("payroll_manager".to_owned()),
            status: Some("waiting".to_owned()),
            tone: None,
            lane: Some("operation".to_owned()),
            node_type: Some("condition".to_owned()),
            position_x: None,
            position_y: None,
            next_step_ids: None,
            after_step_id: Some("review-deductions".to_owned()),
            enabled: Some(true),
            slo_minutes: Some(240),
            escalation_role: Some("payroll_manager".to_owned()),
            condition_expression: Some(BTreeMap::from([(
                "rule".to_owned(),
                "deduction exceptions must be assigned before calculation".to_owned(),
            )])),
            permission_scope: Some(BTreeMap::from([
                ("data_class".to_owned(), "sensitive".to_owned()),
                ("tenant_required".to_owned(), "true".to_owned()),
            ])),
            actor_role: Some("platform_owner".to_owned()),
            scope_tenant: None,
            scope_workplace: None,
            scope_period: None,
        }
    }

    #[test]
    fn default_store_contains_payroll_close_template_steps_and_edges() {
        let store = default_store(10);
        assert_eq!(store.schema, WORKFLOW_TEMPLATE_STORE_SCHEMA);
        assert_eq!(store.templates[0].id, DEFAULT_TEMPLATE_ID);
        assert!(store.templates[0].steps.iter().any(|step| step.id == "close-attendance"));
        assert!(store.templates[0].steps.iter().any(|step| step.id == "request-approval"));
        let attendance = store.templates[0]
            .steps
            .iter()
            .find(|step| step.id == "close-attendance")
            .unwrap();
        assert_eq!(attendance.next_step_ids, vec!["close-payroll-inputs"]);
        assert_eq!(attendance.position_x, 10);
        assert_eq!(attendance.slo_minutes, Some(240));
        assert_eq!(attendance.escalation_role, Some("hr_manager".to_owned()));
        assert_eq!(
            attendance.permission_scope.get("data_class"),
            Some(&"sensitive".to_owned())
        );
        let scope_gate = store.templates[0]
            .steps
            .iter()
            .find(|step| step.id == "set-payroll-scope")
            .unwrap();
        assert_eq!(
            scope_gate.condition_expression.get("rule"),
            Some(&"tenant workplace and pay period must be selected".to_owned())
        );
    }

    #[test]
    fn update_step_persists_status_tone_editor_fields_and_audit() {
        let mut store = default_store(10);
        update_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "close-attendance",
            WorkflowStepInput {
                owner: Some("hr_manager".to_owned()),
                lane: Some("source".to_owned()),
                node_type: Some("trigger".to_owned()),
                position_x: Some(10),
                position_y: Some(33),
                ..update("completed")
            },
            20,
            99,
        )
        .unwrap();
        let step = store.templates[0]
            .steps
            .iter()
            .find(|step| step.id == "close-attendance")
            .unwrap();
        assert_eq!(step.status, "completed");
        assert_eq!(step.tone, "ready");
        assert_eq!(step.owner, "hr_manager");
        assert_eq!(step.position_y, 33);
        assert_eq!(step.updated_at_unix, 20);
        assert_eq!(store.audit_events.len(), 1);
        assert_eq!(store.audit_events[0].action, "update_step");
    }

    #[test]
    fn update_step_persists_workflow_maturity_controls() {
        let mut store = default_store(10);
        update_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "review-deductions",
            WorkflowStepInput {
                slo_minutes: Some(90),
                escalation_role: Some("payroll_manager".to_owned()),
                condition_expression: Some(BTreeMap::from([(
                    "rule".to_owned(),
                    "deduction exceptions must have reviewer and evidence".to_owned(),
                )])),
                permission_scope: Some(BTreeMap::from([
                    ("data_class".to_owned(), "sensitive".to_owned()),
                    ("tenant_required".to_owned(), "true".to_owned()),
                ])),
                ..update("waiting")
            },
            20,
            99,
        )
        .unwrap();
        let step = store.templates[0]
            .steps
            .iter()
            .find(|step| step.id == "review-deductions")
            .unwrap();
        assert_eq!(step.slo_minutes, Some(90));
        assert_eq!(step.escalation_role, Some("payroll_manager".to_owned()));
        assert_eq!(
            step.condition_expression.get("rule"),
            Some(&"deduction exceptions must have reviewer and evidence".to_owned())
        );
        assert_eq!(
            step.permission_scope.get("tenant_required"),
            Some(&"true".to_owned())
        );
    }

    #[test]
    fn add_step_creates_persisted_node_and_rewires_edges() {
        let mut store = default_store(10);
        add_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            new_step_input("Exception review"),
            20,
            99,
        )
        .unwrap();
        let template = &store.templates[0];
        assert!(template.steps.iter().any(|step| step.id == "exception-review"));
        let parent = template
            .steps
            .iter()
            .find(|step| step.id == "review-deductions")
            .unwrap();
        assert_eq!(parent.next_step_ids, vec!["exception-review"]);
        let added = template
            .steps
            .iter()
            .find(|step| step.id == "exception-review")
            .unwrap();
        assert_eq!(added.next_step_ids, vec!["run-calculation"]);
        assert_eq!(store.audit_events[0].action, "add_step");
    }

    #[test]
    fn graph_edits_preserve_text_version_history_and_rollback_restores_prior_graph() {
        let mut store = default_store(10);
        let initial_version = store.templates[0].version;
        assert_eq!(store.template_versions.len(), 1);
        assert_eq!(store.template_versions[0].version, initial_version);

        add_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            new_step_input("Exception review"),
            20,
            99,
        )
        .unwrap();

        assert_eq!(store.templates[0].version, initial_version + 1);
        assert_eq!(store.template_versions.len(), 2);
        assert!(store.templates[0].steps.iter().any(|step| step.id == "exception-review"));
        assert!(store
            .template_versions
            .iter()
            .any(|version| version.change_summary == "add_step" && version.graph_hash.len() == 64));

        rollback_template(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            initial_version,
            WorkflowStepInput {
                actor_role: Some("platform_owner".to_owned()),
                ..update("waiting")
            },
            30,
            100,
        )
        .unwrap();

        assert_eq!(store.templates[0].version, initial_version + 2);
        assert!(!store.templates[0].steps.iter().any(|step| step.id == "exception-review"));
        assert_eq!(store.audit_events.last().unwrap().action, "rollback_version");
        let rollback_record = store.template_versions.last().unwrap();
        assert_eq!(rollback_record.rollback_of_version, Some(initial_version));
        assert_eq!(rollback_record.change_summary, "rollback_version");
        assert_eq!(rollback_record.steps.len(), 9);
    }

    #[test]
    fn korean_business_titles_generate_stable_ascii_internal_step_ids() {
        let mut store = default_store(10);
        add_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            WorkflowStepInput {
                title: Some("공제 예외 확인".to_owned()),
                action: Some("누락 증빙을 확인하고 급여 계산 전 담당자에게 인계".to_owned()),
                owner: Some("payroll_manager".to_owned()),
                status: Some("waiting".to_owned()),
                lane: Some("operation".to_owned()),
                node_type: Some("condition".to_owned()),
                after_step_id: Some("review-deductions".to_owned()),
                slo_minutes: Some(120),
                escalation_role: Some("payroll_manager".to_owned()),
                condition_expression: Some(BTreeMap::from([(
                    "rule".to_owned(),
                    "공제 예외가 남아 있으면 계산 전 확인".to_owned(),
                )])),
                permission_scope: Some(BTreeMap::from([
                    ("data_class".to_owned(), "sensitive".to_owned()),
                    ("tenant_required".to_owned(), "true".to_owned()),
                    ("object_scope".to_owned(), "payroll_period".to_owned()),
                ])),
                actor_role: Some("platform_owner".to_owned()),
                id: None,
                tone: None,
                position_x: None,
                position_y: None,
                next_step_ids: None,
                enabled: Some(true),
                scope_tenant: None,
                scope_workplace: None,
                scope_period: None,
            },
            20,
            99,
        )
        .unwrap();
        let added = store.templates[0]
            .steps
            .iter()
            .find(|step| step.title.as_deref() == Some("공제 예외 확인"))
            .unwrap();
        assert!(added.id.starts_with("step-"));
        assert!(added.id.chars().all(|character| character.is_ascii_alphanumeric() || character == '-'));
    }

    #[test]
    fn analytics_detect_branch_load_and_validation_shape() {
        let mut store = default_store(10);
        update_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "review-deductions",
            WorkflowStepInput {
                next_step_ids: Some(vec![
                    "run-calculation".to_owned(),
                    "request-approval".to_owned(),
                ]),
                ..update("waiting")
            },
            20,
            99,
        )
        .unwrap();
        let analytics = store
            .analytics
            .iter()
            .find(|analytics| analytics.template_id == DEFAULT_TEMPLATE_ID)
            .unwrap();
        assert_eq!(analytics.step_count, 9);
        assert_eq!(analytics.branch_count, 1);
        assert!(analytics.edge_count >= 9);
        assert!(!analytics.cycle_detected);
        assert!(analytics.longest_path_steps >= 8);
        assert!(analytics.owner_loads.iter().any(|load| load.key == "payroll_manager"));
        assert!(analytics.lane_loads.iter().any(|load| load.key == "operation"));
    }

    #[test]
    fn analytics_flags_missing_slo_condition_and_permission_controls() {
        let mut store = default_store(10);
        add_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            WorkflowStepInput {
                title: Some("Unscoped decision".to_owned()),
                action: Some("Ask payroll manager to classify this branch.".to_owned()),
                owner: Some("payroll_manager".to_owned()),
                status: Some("waiting".to_owned()),
                lane: Some("rule".to_owned()),
                node_type: Some("condition".to_owned()),
                after_step_id: Some("review-deductions".to_owned()),
                permission_scope: Some(BTreeMap::new()),
                condition_expression: Some(BTreeMap::new()),
                ..update("waiting")
            },
            20,
            99,
        )
        .unwrap();
        let analytics = store
            .analytics
            .iter()
            .find(|analytics| analytics.template_id == DEFAULT_TEMPLATE_ID)
            .unwrap();
        assert!(analytics.validation_issues.iter().any(|issue| {
            issue.code == "missing_slo" && issue.step_id.as_deref() == Some("unscoped-decision")
        }));
        assert!(analytics.validation_issues.iter().any(|issue| {
            issue.code == "missing_condition_expression"
                && issue.step_id.as_deref() == Some("unscoped-decision")
        }));
        assert!(analytics.validation_issues.iter().any(|issue| {
            issue.code == "missing_permission_scope"
                && issue.step_id.as_deref() == Some("unscoped-decision")
        }));
    }

    #[test]
    fn preflight_report_plans_executable_graph_with_data_operations() {
        let store = default_store(10);
        let report = preflight_template(
            &store,
            DEFAULT_TEMPLATE_ID,
            WorkflowStepInput {
                actor_role: Some("payroll_manager".to_owned()),
                scope_tenant: Some("Acme Corporation".to_owned()),
                scope_workplace: Some("Seoul".to_owned()),
                scope_period: Some("2026-06".to_owned()),
                ..update("ready")
            },
            20,
            99,
        )
        .unwrap();

        assert_eq!(report.template_id, DEFAULT_TEMPLATE_ID);
        assert_eq!(report.status, "ready");
        assert_eq!(report.planned_step_ids.first().map(String::as_str), Some("set-payroll-scope"));
        assert!(report.planned_step_ids.iter().any(|id| id == "run-calculation"));
        assert!(report.next_actions.iter().any(|action| {
            action.step_id == "set-payroll-scope" && action.owner == "payroll_manager"
        }));
        assert!(report.data_operations.iter().any(|operation| {
            operation.operation_type == "payroll_calculation_plan"
                && operation.metadata.get("scope_period").map(String::as_str) == Some("2026-06")
        }));
        assert_eq!(report.blocker_count, 0);
    }

    #[test]
    fn preflight_report_blocks_cycle_before_workflow_execution() {
        let mut store = default_store(10);
        let step = store.templates[0]
            .steps
            .iter_mut()
            .find(|step| step.id == "set-payroll-scope")
            .unwrap();
        step.next_step_ids = vec!["set-payroll-scope".to_owned()];
        step.status = "blocked".to_owned();
        step.tone = "blocked".to_owned();
        let report = preflight_template(
            &store,
            DEFAULT_TEMPLATE_ID,
            WorkflowStepInput {
                actor_role: Some("payroll_manager".to_owned()),
                scope_tenant: Some("Acme Corporation".to_owned()),
                scope_workplace: Some("Seoul".to_owned()),
                scope_period: Some("2026-06".to_owned()),
                ..update("ready")
            },
            30,
            199,
        )
        .unwrap();

        assert_eq!(report.status, "blocked");
        assert!(report.blocker_count >= 1);
        assert!(report.issues.iter().any(|issue| issue.code == "cycle_detected"));
        assert!(report.issues.iter().any(|issue| {
            issue.code == "blocked_step" && issue.step_id.as_deref() == Some("set-payroll-scope")
        }));
        assert!(report.data_operations.is_empty());
    }

    #[test]
    fn update_step_rejects_cycle_creating_branch_before_persisting() {
        let mut store = default_store(10);
        let original_version = store.templates[0].version;
        let original_next_ids = store.templates[0]
            .steps
            .iter()
            .find(|step| step.id == "request-approval")
            .unwrap()
            .next_step_ids
            .clone();

        let error = update_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "request-approval",
            WorkflowStepInput {
                next_step_ids: Some(vec!["close-attendance".to_owned()]),
                ..update("waiting")
            },
            40,
            299,
        )
        .unwrap_err();

        assert!(error.contains("cycle_detected"));
        let request_approval = store.templates[0]
            .steps
            .iter()
            .find(|step| step.id == "request-approval")
            .unwrap();
        assert_eq!(request_approval.next_step_ids, original_next_ids);
        assert_eq!(store.templates[0].version, original_version);
        assert!(store.audit_events.is_empty());
        assert!(store.template_versions.iter().all(|record| record.change_summary != "update_step"));
    }

    #[test]
    fn edit_validation_dry_runs_branch_merge_without_mutating_store() {
        let store = default_store(10);
        let original_version = store.templates[0].version;
        let accepted = validate_step_update(
            &store,
            DEFAULT_TEMPLATE_ID,
            "review-deductions",
            WorkflowStepInput {
                next_step_ids: Some(vec![
                    "run-calculation".to_owned(),
                    "request-approval".to_owned(),
                ]),
                ..update("waiting")
            },
            40,
            299,
        )
        .unwrap();

        assert_eq!(accepted.schema, WORKFLOW_EDIT_VALIDATION_SCHEMA);
        assert_eq!(accepted.status, "accepted");
        assert!(accepted.would_persist);
        assert_eq!(accepted.proposed_analytics.branch_count, 1);
        assert_eq!(store.templates[0].version, original_version);
        assert_eq!(store.audit_events.len(), 0);

        let blocked = validate_step_update(
            &store,
            DEFAULT_TEMPLATE_ID,
            "request-approval",
            WorkflowStepInput {
                next_step_ids: Some(vec!["close-attendance".to_owned()]),
                ..update("waiting")
            },
            41,
            300,
        )
        .unwrap();
        assert_eq!(blocked.status, "blocked");
        assert!(!blocked.would_persist);
        assert!(blocked.blocker_count >= 1);
        assert!(blocked.issues.iter().any(|issue| issue.code == "cycle_detected"));
        assert_eq!(store.templates[0].version, original_version);
        assert_eq!(store.audit_events.len(), 0);
    }

    #[test]
    fn execute_step_runs_action_and_advances_connected_steps() {
        let mut store = default_store(10);
        execute_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "review-deductions",
            WorkflowStepInput {
                actor_role: Some("payroll_manager".to_owned()),
                ..update("waiting")
            },
            20,
            99,
        )
        .unwrap();
        let template = &store.templates[0];
        let executed = template
            .steps
            .iter()
            .find(|step| step.id == "review-deductions")
            .unwrap();
        let downstream = template
            .steps
            .iter()
            .find(|step| step.id == "run-calculation")
            .unwrap();
        assert_eq!(executed.status, "completed");
        assert_eq!(executed.tone, "ready");
        assert_eq!(downstream.status, "needs_attention");
        assert_eq!(store.audit_events.last().unwrap().action, "execute_step");
        assert_eq!(store.runtime_events.len(), 1);
        assert_eq!(store.runtime_events[0].affected_step_ids, vec!["run-calculation"]);
        assert_eq!(
            store.runtime_events[0].data_operations[0].operation_type,
            "deduction_exception_review"
        );
        assert!(store
            .data_records
            .iter()
            .any(|record| record.record_type == "deduction_exception_review"));
        assert!(store.analytics[0].completed_count >= 1);
    }

    #[test]
    fn execute_calculation_step_records_payroll_data_operation_scope() {
        let mut store = default_store(10);
        execute_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "run-calculation",
            WorkflowStepInput {
                actor_role: Some("payroll_manager".to_owned()),
                scope_tenant: Some("Acme Corporation".to_owned()),
                scope_workplace: Some("Seoul".to_owned()),
                scope_period: Some("2026-06".to_owned()),
                ..update("waiting")
            },
            20,
            99,
        )
        .unwrap();
        let runtime_event = &store.runtime_events[0];
        let operation = &runtime_event.data_operations[0];
        assert_eq!(operation.operation_type, "payroll_calculation_plan");
        assert_eq!(operation.target, "payroll");
        assert_eq!(operation.status, "planned");
        assert_eq!(
            operation.metadata.get("scope_tenant"),
            Some(&"Acme Corporation".to_owned())
        );
        assert_eq!(
            operation.metadata.get("scope_workplace"),
            Some(&"Seoul".to_owned())
        );
        assert_eq!(
            operation.metadata.get("scope_period"),
            Some(&"2026-06".to_owned())
        );
        assert_eq!(operation.metadata.get("slo_minutes"), Some(&"120".to_owned()));
        assert_eq!(
            operation.metadata.get("escalation_role"),
            Some(&"payroll_manager".to_owned())
        );
        assert_eq!(
            operation.metadata.get("permission_scope_count"),
            Some(&"3".to_owned())
        );
        let data_record = store
            .data_records
            .iter()
            .find(|record| record.record_type == "payroll_calculation_plan")
            .unwrap();
        assert_eq!(data_record.target, "payroll");
        assert_eq!(data_record.metadata.get("scope_period"), Some(&"2026-06".to_owned()));
        assert_eq!(runtime_event.affected_step_ids, vec!["request-approval"]);
    }

    #[test]
    fn repeated_execution_upserts_business_data_record_for_same_scope() {
        let mut store = default_store(10);
        let input = WorkflowStepInput {
            actor_role: Some("payroll_manager".to_owned()),
            scope_tenant: Some("Acme Corporation".to_owned()),
            scope_workplace: Some("Seoul".to_owned()),
            scope_period: Some("2026-06".to_owned()),
            ..update("waiting")
        };
        execute_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "request-approval",
            input.clone(),
            20,
            99,
        )
        .unwrap();
        execute_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "request-approval",
            input,
            30,
            100,
        )
        .unwrap();
        let records = store
            .data_records
            .iter()
            .filter(|record| record.record_type == "approval_packet")
            .collect::<Vec<_>>();
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].updated_at_unix, 30);
        assert_eq!(store.runtime_events.len(), 2);
    }

    #[test]
    fn delete_step_removes_node_and_preserves_downstream_wiring() {
        let mut store = default_store(10);
        add_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            new_step_input("Exception review"),
            20,
            99,
        )
        .unwrap();
        delete_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "exception-review",
            WorkflowStepInput { actor_role: Some("platform_owner".to_owned()), ..update("waiting") },
            30,
            100,
        )
        .unwrap();
        let template = &store.templates[0];
        assert!(!template.steps.iter().any(|step| step.id == "exception-review"));
        let parent = template
            .steps
            .iter()
            .find(|step| step.id == "review-deductions")
            .unwrap();
        assert_eq!(parent.next_step_ids, vec!["run-calculation"]);
        assert_eq!(store.audit_events.last().unwrap().action, "delete_step");
    }

    #[test]
    fn rejects_unknown_status_owner_and_bad_edge() {
        let mut store = default_store(10);
        let bad_status = update_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "close-attendance",
            update("maybe"),
            20,
            99,
        );
        assert!(bad_status.unwrap_err().contains("unsupported workflow status"));

        let bad_owner = update_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "close-attendance",
            WorkflowStepInput {
                owner: Some("superuser".to_owned()),
                ..update("waiting")
            },
            20,
            99,
        );
        assert!(bad_owner.unwrap_err().contains("unsupported workflow owner"));

        let bad_edge = update_step(
            &mut store,
            DEFAULT_TEMPLATE_ID,
            "close-attendance",
            WorkflowStepInput {
                next_step_ids: Some(vec!["missing".to_owned()]),
                ..update("waiting")
            },
            20,
            99,
        );
        assert!(bad_edge.unwrap_err().contains("workflow next step not found"));
    }

    #[test]
    fn local_review_store_is_explicitly_required() {
        let error = local_review_store_path(None, None).unwrap_err();
        assert!(error.contains("PostgreSQL relational workflow template storage is required"));
        let path = local_review_store_path(Some("true"), Some("/tmp/workflow.json".to_owned())).unwrap();
        assert_eq!(path, PathBuf::from("/tmp/workflow.json"));
    }

    #[test]
    fn postgres_helpers_preserve_i18n_defaults_and_audit_actions() {
        assert_eq!(
            title_override_from_postgres("close-attendance", "close-attendance".to_owned()),
            None
        );
        assert_eq!(
            title_override_from_postgres("custom-step", "Custom step".to_owned()),
            Some("Custom step".to_owned())
        );
        assert_eq!(postgres_audit_action("bootstrap_workflow_templates"), "create_template");
        assert_eq!(postgres_audit_action("execute_step"), "execute_step");

        let metadata = json_string_map(r#"{"scope_period":"2026-06","approved":true,"count":3}"#)
            .unwrap();
        assert_eq!(metadata.get("scope_period"), Some(&"2026-06".to_owned()));
        assert_eq!(metadata.get("approved"), Some(&"true".to_owned()));
        assert_eq!(metadata.get("count"), Some(&"3".to_owned()));

        let hash = workflow_graph_hash(&default_store(10).templates[0]).unwrap();
        assert_eq!(hash.len(), 64);
        assert!(hash.chars().all(|character| character.is_ascii_hexdigit()));
    }

    #[test]
    fn validates_existing_store_and_normalizes_schema_positions_and_edges() {
        let mut store = default_store(10);
        store.schema = "old".to_owned();
        store.templates[0].steps[0].status = "ready".to_owned();
        store.templates[0].steps[0].position_x = 0;
        store.templates[0].steps[0].next_step_ids.clear();
        for step in &mut store.templates[0].steps {
            step.next_step_ids.clear();
        }
        let validated = validate_store(store).unwrap();
        assert_eq!(validated.schema, WORKFLOW_TEMPLATE_STORE_SCHEMA);
        assert_eq!(validated.templates[0].steps[0].tone, "attention");
        assert_ne!(validated.templates[0].steps[0].position_x, 0);
        assert!(!validated.templates[0].steps[0].next_step_ids.is_empty());
    }
}
