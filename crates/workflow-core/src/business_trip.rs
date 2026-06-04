use serde_json::{Map, Value, json};
use std::error::Error;
use std::fmt;

pub const TRIP_STATUS_DRAFT: &str = "draft";
pub const TRIP_STATUS_PLANNED: &str = "planned";
pub const TRIP_STATUS_APPROVED: &str = "approved";
pub const TRIP_STATUS_IN_PROGRESS: &str = "in_progress";
pub const TRIP_STATUS_DIARY_DUE: &str = "diary_due";
pub const TRIP_STATUS_OVERDUE: &str = "overdue";
pub const TRIP_STATUS_COMPLETED: &str = "completed";
pub const TRIP_STATUS_CANCELLED: &str = "cancelled";

pub const TRIP_STATUSES: [&str; 8] = [
    TRIP_STATUS_DRAFT,
    TRIP_STATUS_PLANNED,
    TRIP_STATUS_APPROVED,
    TRIP_STATUS_IN_PROGRESS,
    TRIP_STATUS_DIARY_DUE,
    TRIP_STATUS_OVERDUE,
    TRIP_STATUS_COMPLETED,
    TRIP_STATUS_CANCELLED,
];

pub const KPI_REFLECTION_BLOCKED: &str = "blocked";
pub const KPI_REFLECTION_READY: &str = "ready";
pub const KPI_REFLECTION_REFLECTED: &str = "reflected";
pub const KPI_REFLECTION_NOT_APPLICABLE: &str = "not_applicable";

pub const KPI_REFLECTION_STATUSES: [&str; 4] = [
    KPI_REFLECTION_BLOCKED,
    KPI_REFLECTION_READY,
    KPI_REFLECTION_REFLECTED,
    KPI_REFLECTION_NOT_APPLICABLE,
];

pub const TRIP_SOURCE_KIND_WORKFLOW: &str = "workflow";
pub const TRIP_SOURCE_KIND_GW_IMPORT: &str = "gw_import";
pub const TRIP_SOURCE_KIND_MANUAL: &str = "manual";

pub const TRIP_SOURCE_KINDS: [&str; 3] = [
    TRIP_SOURCE_KIND_WORKFLOW,
    TRIP_SOURCE_KIND_GW_IMPORT,
    TRIP_SOURCE_KIND_MANUAL,
];

pub const TRIP_SOURCE_KEYS: [&str; 3] = ["kind", "document_id", "dedupe_key"];

pub const TRIP_VIEW_MODEL_KEYS: [&str; 37] = [
    "trip_id",
    "tenant_id",
    "origin_tenant_id",
    "legal_entity_id",
    "status",
    "kpi_reflection_status",
    "kpi_record_id",
    "title",
    "requester_id",
    "traveler_user_id",
    "traveler_name",
    "executor_id",
    "site_id",
    "department_id",
    "planned_start",
    "planned_end",
    "period_start",
    "period_end",
    "actual_start",
    "actual_end",
    "diary_due_at",
    "completed_at",
    "overdue_at",
    "plan_document_id",
    "attendance_request_id",
    "execution_task_id",
    "approved_document_id",
    "diary_document_id",
    "report_document_id",
    "escalation_level",
    "last_escalated_at",
    "escalation_target_user_ids",
    "follow_up_source_keys",
    "source",
    "dedupe_key",
    "created_at",
    "updated_at",
];

pub const fn business_trip_view_model_keys() -> [&'static str; 37] {
    TRIP_VIEW_MODEL_KEYS
}

pub fn normalize_trip_status(status: &str) -> &'static str {
    let value = status.trim();
    TRIP_STATUSES
        .iter()
        .copied()
        .find(|candidate| *candidate == value)
        .unwrap_or(TRIP_STATUS_DRAFT)
}

pub fn normalize_kpi_reflection_status(status: &str) -> &'static str {
    let value = status.trim();
    KPI_REFLECTION_STATUSES
        .iter()
        .copied()
        .find(|candidate| *candidate == value)
        .unwrap_or(KPI_REFLECTION_BLOCKED)
}

pub fn normalize_trip_source(source: &Value) -> Value {
    let raw = source.as_object();
    let mut kind = raw
        .and_then(|obj| obj.get("kind"))
        .map(value_to_trimmed_string)
        .unwrap_or_else(|| TRIP_SOURCE_KIND_MANUAL.to_string());
    if !TRIP_SOURCE_KINDS.contains(&kind.as_str()) {
        kind = TRIP_SOURCE_KIND_MANUAL.to_string();
    }
    let document_id = raw
        .and_then(|obj| obj.get("document_id"))
        .map(value_to_trimmed_string)
        .unwrap_or_default();
    let dedupe_key = raw
        .and_then(|obj| obj.get("dedupe_key"))
        .map(value_to_trimmed_string)
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| document_id.clone());

    json!({
        "kind": kind,
        "document_id": document_id,
        "dedupe_key": dedupe_key,
    })
}

pub fn migrate_business_trip_record(
    default_tenant_id: &str,
    record: &Value,
    now_iso: &str,
    fallback_trip_id: &str,
) -> Value {
    let source = normalize_trip_source(record.get("source").unwrap_or(&Value::Null));
    let source_dedupe = text_field(&source, "dedupe_key");
    let trip_id = first_nonempty(&[
        text_field(record, "trip_id"),
        text_field(record, "id"),
        fallback_trip_id.trim().to_string(),
    ]);
    let planned_start = first_nonempty(&[
        text_field(record, "planned_start"),
        text_field(record, "period_start"),
    ]);
    let planned_end = first_nonempty(&[
        text_field(record, "planned_end"),
        text_field(record, "period_end"),
    ]);
    let requester_id = first_nonempty(&[
        text_field(record, "requester_id"),
        text_field(record, "traveler_user_id"),
        text_field(record, "traveler_id"),
    ]);
    let traveler_user_id =
        first_nonempty(&[text_field(record, "traveler_user_id"), requester_id.clone()]);
    let tenant_id = first_nonempty(&[
        text_field(record, "tenant_id"),
        default_tenant_id.trim().to_string(),
    ]);
    let origin_tenant_id = first_nonempty(&[
        text_field(record, "origin_tenant_id"),
        text_field(record, "legal_tenant_id"),
        text_field(record, "tenant_origin_id"),
        text_field(record, "tenant_id"),
        default_tenant_id.trim().to_string(),
    ]);
    let mut status = normalize_trip_status(&text_field(record, "status")).to_string();
    let mut kpi_status =
        normalize_kpi_reflection_status(&text_field(record, "kpi_reflection_status")).to_string();

    if status == TRIP_STATUS_CANCELLED {
        kpi_status = KPI_REFLECTION_NOT_APPLICABLE.to_string();
    } else if status != TRIP_STATUS_COMPLETED
        && (kpi_status == KPI_REFLECTION_READY || kpi_status == KPI_REFLECTION_REFLECTED)
    {
        kpi_status = KPI_REFLECTION_BLOCKED.to_string();
    }

    if status.is_empty() {
        status = TRIP_STATUS_DRAFT.to_string();
    }

    let mut migrated = record.as_object().cloned().unwrap_or_default();
    insert_string(&mut migrated, "id", &trip_id);
    insert_string(&mut migrated, "trip_id", &trip_id);
    insert_string(&mut migrated, "tenant_id", &tenant_id);
    insert_string(&mut migrated, "origin_tenant_id", &origin_tenant_id);
    insert_string(
        &mut migrated,
        "legal_entity_id",
        &text_field(record, "legal_entity_id").or_else_str(&text_field(record, "entity_id")),
    );
    insert_string(&mut migrated, "status", &status);
    insert_string(&mut migrated, "kpi_reflection_status", &kpi_status);
    insert_string(
        &mut migrated,
        "kpi_record_id",
        &text_field(record, "kpi_record_id"),
    );
    insert_string(&mut migrated, "title", &text_field(record, "title"));
    insert_string(
        &mut migrated,
        "requester_id",
        &first_nonempty(&[requester_id.clone(), traveler_user_id.clone()]),
    );
    insert_string(
        &mut migrated,
        "traveler_user_id",
        &first_nonempty(&[traveler_user_id, requester_id]),
    );
    insert_string(
        &mut migrated,
        "traveler_name",
        &first_nonempty(&[
            text_field(record, "traveler_name"),
            text_field(record, "requester_name"),
        ]),
    );
    insert_string(
        &mut migrated,
        "executor_id",
        &text_field(record, "executor_id"),
    );
    insert_string(&mut migrated, "site_id", &text_field(record, "site_id"));
    insert_string(
        &mut migrated,
        "department_id",
        &text_field(record, "department_id"),
    );
    insert_string(&mut migrated, "planned_start", &planned_start);
    insert_string(&mut migrated, "planned_end", &planned_end);
    insert_string(
        &mut migrated,
        "period_start",
        &first_nonempty(&[text_field(record, "period_start"), planned_start]),
    );
    insert_string(
        &mut migrated,
        "period_end",
        &first_nonempty(&[text_field(record, "period_end"), planned_end]),
    );
    insert_string(
        &mut migrated,
        "actual_start",
        &text_field(record, "actual_start"),
    );
    insert_string(
        &mut migrated,
        "actual_end",
        &text_field(record, "actual_end"),
    );
    insert_string(
        &mut migrated,
        "diary_due_at",
        &text_field(record, "diary_due_at"),
    );
    insert_string(
        &mut migrated,
        "completed_at",
        &text_field(record, "completed_at"),
    );
    insert_string(
        &mut migrated,
        "overdue_at",
        &text_field(record, "overdue_at"),
    );
    insert_string(
        &mut migrated,
        "plan_document_id",
        &first_nonempty(&[
            text_field(record, "plan_document_id"),
            text_field(record, "approved_document_id"),
        ]),
    );
    insert_string(
        &mut migrated,
        "attendance_request_id",
        &text_field(record, "attendance_request_id"),
    );
    insert_string(
        &mut migrated,
        "execution_task_id",
        &text_field(record, "execution_task_id"),
    );
    insert_string(
        &mut migrated,
        "approved_document_id",
        &text_field(record, "approved_document_id"),
    );
    insert_string(
        &mut migrated,
        "diary_document_id",
        &text_field(record, "diary_document_id"),
    );
    insert_string(
        &mut migrated,
        "report_document_id",
        &text_field(record, "report_document_id"),
    );
    migrated.insert(
        "escalation_level".to_string(),
        Value::Number(_int_or_zero(record.get("escalation_level")).into()),
    );
    insert_string(
        &mut migrated,
        "last_escalated_at",
        &text_field(record, "last_escalated_at"),
    );
    migrated.insert(
        "escalation_target_user_ids".to_string(),
        Value::Array(string_list(record.get("escalation_target_user_ids"))),
    );
    migrated.insert(
        "follow_up_source_keys".to_string(),
        Value::Array(string_list(record.get("follow_up_source_keys"))),
    );
    migrated.insert("source".to_string(), source);
    insert_string(
        &mut migrated,
        "dedupe_key",
        &first_nonempty(&[text_field(record, "dedupe_key"), source_dedupe, trip_id]),
    );
    insert_string(
        &mut migrated,
        "created_at",
        &first_nonempty(&[text_field(record, "created_at"), now_iso.trim().to_string()]),
    );
    insert_string(
        &mut migrated,
        "updated_at",
        &first_nonempty(&[text_field(record, "updated_at"), now_iso.trim().to_string()]),
    );

    Value::Object(migrated)
}

pub fn business_trip_view_model(record: &Value, now_iso: &str, fallback_trip_id: &str) -> Value {
    let migrated = migrate_business_trip_record(
        &text_field(record, "tenant_id"),
        record,
        now_iso,
        fallback_trip_id,
    );
    let mut view = Map::new();
    for key in TRIP_VIEW_MODEL_KEYS {
        view.insert(
            key.to_string(),
            migrated
                .get(key)
                .cloned()
                .unwrap_or_else(|| Value::String(String::new())),
        );
    }
    Value::Object(view)
}

pub fn can_transition_trip_status(current: &str, target: &str) -> bool {
    transition_targets(normalize_trip_status(current)).contains(&normalize_trip_status(target))
}

pub fn transition_trip_status(
    record: &Value,
    target: &str,
    now_iso: &str,
) -> Result<Value, BusinessTripTransitionError> {
    let current = normalize_trip_status(&text_field(record, "status"));
    let target = normalize_trip_status(target);
    let tenant_id = text_field(record, "tenant_id");
    if target == current {
        return Ok(migrate_business_trip_record(
            &tenant_id,
            record,
            now_iso,
            &text_field(record, "trip_id"),
        ));
    }
    if !can_transition_trip_status(current, target) {
        return Err(BusinessTripTransitionError {
            current: current.to_string(),
            target: target.to_string(),
        });
    }

    let fallback_trip_id = text_field(record, "trip_id");
    let mut updated = migrate_business_trip_record(&tenant_id, record, now_iso, &fallback_trip_id);
    let Some(obj) = updated.as_object_mut() else {
        return Ok(updated);
    };
    insert_string(obj, "status", target);
    insert_string(obj, "updated_at", now_iso.trim());

    if target == TRIP_STATUS_IN_PROGRESS && map_text_field(obj, "actual_start").is_empty() {
        insert_string(obj, "actual_start", now_iso.trim());
    }
    if target == TRIP_STATUS_DIARY_DUE {
        if map_text_field(obj, "actual_start").is_empty() {
            insert_string(obj, "actual_start", now_iso.trim());
        }
        if map_text_field(obj, "actual_end").is_empty() {
            insert_string(obj, "actual_end", now_iso.trim());
        }
        if map_text_field(obj, "diary_due_at").is_empty() {
            insert_string(obj, "diary_due_at", now_iso.trim());
        }
    }
    if target == TRIP_STATUS_OVERDUE && map_text_field(obj, "overdue_at").is_empty() {
        insert_string(obj, "overdue_at", now_iso.trim());
    }
    if target == TRIP_STATUS_COMPLETED
        && map_text_field(obj, "kpi_reflection_status") == KPI_REFLECTION_BLOCKED
    {
        if map_text_field(obj, "actual_end").is_empty() {
            insert_string(obj, "actual_end", now_iso.trim());
        }
        if map_text_field(obj, "completed_at").is_empty() {
            insert_string(obj, "completed_at", now_iso.trim());
        }
        insert_string(obj, "kpi_reflection_status", KPI_REFLECTION_READY);
    }
    if target == TRIP_STATUS_CANCELLED {
        insert_string(obj, "kpi_reflection_status", KPI_REFLECTION_NOT_APPLICABLE);
    }

    Ok(updated)
}

pub fn business_trip_source_matches(record: &Value, source: &Value) -> bool {
    let normalized = normalize_trip_source(source);
    let dedupe_key = text_field(&normalized, "dedupe_key");
    let document_id = text_field(&normalized, "document_id");
    let row_source = normalize_trip_source(record.get("source").unwrap_or(&Value::Null));

    (!dedupe_key.is_empty()
        && (text_field(record, "dedupe_key") == dedupe_key
            || text_field(&row_source, "dedupe_key") == dedupe_key))
        || (!document_id.is_empty() && text_field(&row_source, "document_id") == document_id)
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BusinessTripTransitionError {
    pub current: String,
    pub target: String,
}

impl fmt::Display for BusinessTripTransitionError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Invalid business trip status transition: {} -> {}",
            self.current, self.target
        )
    }
}

impl Error for BusinessTripTransitionError {}

fn transition_targets(status: &str) -> &'static [&'static str] {
    match status {
        TRIP_STATUS_DRAFT => &[TRIP_STATUS_PLANNED, TRIP_STATUS_CANCELLED],
        TRIP_STATUS_PLANNED => &[TRIP_STATUS_APPROVED, TRIP_STATUS_CANCELLED],
        TRIP_STATUS_APPROVED => &[TRIP_STATUS_IN_PROGRESS, TRIP_STATUS_CANCELLED],
        TRIP_STATUS_IN_PROGRESS => &[TRIP_STATUS_DIARY_DUE, TRIP_STATUS_OVERDUE],
        TRIP_STATUS_DIARY_DUE => &[TRIP_STATUS_COMPLETED, TRIP_STATUS_OVERDUE],
        TRIP_STATUS_OVERDUE => &[TRIP_STATUS_COMPLETED, TRIP_STATUS_CANCELLED],
        TRIP_STATUS_COMPLETED | TRIP_STATUS_CANCELLED => &[],
        _ => &[],
    }
}

fn map_text_field(map: &Map<String, Value>, field: &str) -> String {
    map.get(field)
        .map(value_to_trimmed_string)
        .unwrap_or_default()
}

fn text_field(value: &Value, field: &str) -> String {
    value
        .as_object()
        .and_then(|obj| obj.get(field))
        .map(value_to_trimmed_string)
        .unwrap_or_default()
}

fn value_to_trimmed_string(value: &Value) -> String {
    match value {
        Value::Null => String::new(),
        Value::String(text) => text.trim().to_string(),
        Value::Number(number) => number.to_string().trim().to_string(),
        Value::Bool(boolean) => boolean.to_string(),
        other => other.to_string().trim().to_string(),
    }
}

fn first_nonempty(values: &[String]) -> String {
    values
        .iter()
        .find(|value| !value.trim().is_empty())
        .map(|value| value.trim().to_string())
        .unwrap_or_default()
}

fn insert_string(map: &mut Map<String, Value>, key: &str, value: &str) {
    map.insert(key.to_string(), Value::String(value.trim().to_string()));
}

fn _int_or_zero(value: Option<&Value>) -> i64 {
    let amount = match value {
        Some(Value::Number(number)) => number.as_i64().unwrap_or(0),
        Some(Value::String(text)) => text.trim().parse::<i64>().unwrap_or(0),
        Some(Value::Bool(true)) => 1,
        _ => 0,
    };
    amount.max(0)
}

fn string_list(value: Option<&Value>) -> Vec<Value> {
    match value {
        Some(Value::Array(values)) => values
            .iter()
            .map(value_to_trimmed_string)
            .filter(|text| !text.is_empty())
            .map(Value::String)
            .collect(),
        Some(other) => {
            let text = value_to_trimmed_string(other);
            if text.is_empty() {
                Vec::new()
            } else {
                vec![Value::String(text)]
            }
        }
        None => Vec::new(),
    }
}

trait OrElseStr {
    fn or_else_str(self, fallback: &str) -> String;
}

impl OrElseStr for String {
    fn or_else_str(self, fallback: &str) -> String {
        if self.trim().is_empty() {
            fallback.trim().to_string()
        } else {
            self.trim().to_string()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn status_taxonomy_and_transitions_match_python_contract() {
        assert_eq!(
            TRIP_STATUSES,
            [
                "draft",
                "planned",
                "approved",
                "in_progress",
                "diary_due",
                "overdue",
                "completed",
                "cancelled"
            ]
        );
        assert_eq!(
            KPI_REFLECTION_STATUSES,
            ["blocked", "ready", "reflected", "not_applicable"]
        );
        assert!(!can_transition_trip_status("in_progress", "completed"));
        assert!(can_transition_trip_status("in_progress", "diary_due"));
    }

    #[test]
    fn migrates_legacy_record_and_preserves_view_model_shape() {
        let legacy = json!({
            "id": "legacy-1",
            "tenant_id": "",
            "status": "unknown-status",
            "source": {"kind": "bad", "document_id": "DOC-7"},
            "legacy_note": "kept"
        });

        let migrated =
            migrate_business_trip_record("tenant-a", &legacy, "2026-06-04T09:00:00Z", "fallback-1");
        let view = business_trip_view_model(&migrated, "2026-06-04T09:00:00Z", "fallback-1");

        assert_eq!(migrated["id"], "legacy-1");
        assert_eq!(migrated["trip_id"], "legacy-1");
        assert_eq!(migrated["tenant_id"], "tenant-a");
        assert_eq!(migrated["origin_tenant_id"], "tenant-a");
        assert_eq!(migrated["status"], "draft");
        assert_eq!(migrated["kpi_reflection_status"], "blocked");
        assert_eq!(
            migrated["source"],
            json!({"kind": "manual", "document_id": "DOC-7", "dedupe_key": "DOC-7"})
        );
        assert_eq!(migrated["dedupe_key"], "DOC-7");
        assert_eq!(migrated["legacy_note"], "kept");
        assert_eq!(business_trip_view_model_keys(), TRIP_VIEW_MODEL_KEYS);
        assert_eq!(view["trip_id"], "legacy-1");
        assert!(view.get("legacy_note").is_none());
    }

    #[test]
    fn transition_sets_timestamp_fields_and_kpi_state() {
        let trip = migrate_business_trip_record(
            "tenant-a",
            &json!({"trip_id": "trip-1", "status": "approved", "kpi_reflection_status": "blocked"}),
            "2026-06-04T08:00:00Z",
            "fallback-1",
        );
        let in_progress =
            transition_trip_status(&trip, "in_progress", "2026-06-04T09:00:00Z").unwrap();
        let diary_due =
            transition_trip_status(&in_progress, "diary_due", "2026-06-04T18:00:00Z").unwrap();
        let completed =
            transition_trip_status(&diary_due, "completed", "2026-06-05T10:00:00Z").unwrap();

        assert_eq!(in_progress["actual_start"], "2026-06-04T09:00:00Z");
        assert_eq!(diary_due["actual_end"], "2026-06-04T18:00:00Z");
        assert_eq!(diary_due["diary_due_at"], "2026-06-04T18:00:00Z");
        assert_eq!(completed["completed_at"], "2026-06-05T10:00:00Z");
        assert_eq!(completed["kpi_reflection_status"], "ready");
    }

    #[test]
    fn source_matching_preserves_dedupe_and_document_id_idempotency() {
        let trip = migrate_business_trip_record(
            "tenant-a",
            &json!({
                "trip_id": "trip-1",
                "source": {"kind": "gw_import", "document_id": "GW-42", "dedupe_key": "gw:GW-42"}
            }),
            "2026-06-04T08:00:00Z",
            "fallback-1",
        );

        assert_eq!(TRIP_SOURCE_KEYS, ["kind", "document_id", "dedupe_key"]);
        assert!(business_trip_source_matches(
            &trip,
            &json!({"kind": "gw_import", "dedupe_key": "gw:GW-42"})
        ));
        assert!(business_trip_source_matches(
            &trip,
            &json!({"document_id": "GW-42"})
        ));
        assert!(!business_trip_source_matches(
            &trip,
            &json!({"document_id": "GW-99"})
        ));
    }

    #[test]
    fn rejects_skipping_required_lifecycle_steps_and_marks_cancelled_not_applicable() {
        let trip = migrate_business_trip_record(
            "tenant-a",
            &json!({"trip_id": "trip-1", "status": "draft"}),
            "2026-06-04T08:00:00Z",
            "fallback-1",
        );

        assert!(transition_trip_status(&trip, "completed", "2026-06-04T09:00:00Z").is_err());
        let cancelled = transition_trip_status(&trip, "cancelled", "2026-06-04T09:00:00Z").unwrap();
        assert_eq!(cancelled["status"], "cancelled");
        assert_eq!(cancelled["kpi_reflection_status"], "not_applicable");
    }
}
