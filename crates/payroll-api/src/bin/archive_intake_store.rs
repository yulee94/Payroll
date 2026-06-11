use bitween_payroll_api::{
    ARCHIVE_INTAKE_STORE_SCHEMA, ARCHIVE_SOURCE_SYNC_PLAN_SCHEMA, PostgresClientSession,
    PostgresConnectionFailure, PostgresRepositoryConfig, PostgresTenantScope,
    required_postgres_migrations,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use std::process;
use std::time::{SystemTime, UNIX_EPOCH};

const ARCHIVE_SOURCE_SYNC_CONTENT_TYPE: &str = "application/vnd.ms-excel; charset=utf-8";
// Bounds the caller-declared file_size_bytes from intake metadata; this store
// never measures object bytes. Real upload-size and decompression-bomb
// enforcement happens in the uploader before the object reaches RustFS.
const MAX_FILE_BYTES: u64 = 50 * 1024 * 1024;
const EMPTY_SHA256: &str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct ArchiveIntakeStore {
    schema: String,
    intakes: Vec<ArchiveIntakeRecord>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct ArchiveIntakeRecord {
    id: String,
    original_file_name: String,
    stored_file_name: String,
    file_type: String,
    file_size_bytes: u64,
    content_sha256: String,
    #[serde(default)]
    content_sample_sha256: String,
    #[serde(default)]
    content_sample_row_count: u64,
    #[serde(default)]
    extraction_status: ArchiveExtractionStatus,
    #[serde(default)]
    object_uri: String,
    #[serde(default)]
    object_bucket: String,
    #[serde(default)]
    object_key: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    blob_ref: String,
    family: FileFamily,
    database_target: DatabaseTarget,
    status: ArchiveIntakeStatus,
    next_action: ArchiveIntakeAction,
    extracted_columns: Vec<String>,
    #[serde(default)]
    source_fingerprint: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    field_mappings: Vec<FieldMapping>,
    estimated_rows: u64,
    guidance_items: Vec<GuidanceItem>,
    anomalies: Vec<AnomalyItem>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    source_versions: Vec<ArchiveSourceVersion>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    recovery_points: Vec<ArchiveRecoveryPoint>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    source_sync_items: Vec<ArchiveSourceSyncItem>,
    postgres_ready: bool,
    updated_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum FileFamily {
    Hr,
    Payroll,
    GeneralArchive,
    Unknown,
}

impl FileFamily {
    fn prefix(&self) -> &'static str {
        match self {
            Self::Hr => "hr",
            Self::Payroll => "payroll",
            Self::GeneralArchive => "archive",
            Self::Unknown => "needs-review",
        }
    }

    fn as_postgres_value(&self) -> &'static str {
        match self {
            Self::Hr => "hr",
            Self::Payroll => "payroll",
            Self::GeneralArchive => "general_archive",
            Self::Unknown => "unknown",
        }
    }

    fn from_postgres_value(value: &str) -> Result<Self, String> {
        match value {
            "hr" => Ok(Self::Hr),
            "payroll" => Ok(Self::Payroll),
            "general_archive" => Ok(Self::GeneralArchive),
            "unknown" => Ok(Self::Unknown),
            _ => Err("unsupported archive family from PostgreSQL".to_owned()),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum DatabaseTarget {
    HrEmployeeStaging,
    HrAttendanceStaging,
    PayrollInputStaging,
    ArchiveBlob,
    NeedsMapping,
}

impl Default for DatabaseTarget {
    fn default() -> Self {
        Self::NeedsMapping
    }
}

impl DatabaseTarget {
    fn as_postgres_value(&self) -> &'static str {
        match self {
            Self::HrEmployeeStaging => "hr_employee_staging",
            Self::HrAttendanceStaging => "hr_attendance_staging",
            Self::PayrollInputStaging => "payroll_input_staging",
            Self::ArchiveBlob => "archive_blob",
            Self::NeedsMapping => "needs_mapping",
        }
    }

    fn from_postgres_value(value: &str) -> Result<Self, String> {
        match value {
            "hr_employee_staging" => Ok(Self::HrEmployeeStaging),
            "hr_attendance_staging" => Ok(Self::HrAttendanceStaging),
            "payroll_input_staging" => Ok(Self::PayrollInputStaging),
            "archive_blob" => Ok(Self::ArchiveBlob),
            "needs_mapping" => Ok(Self::NeedsMapping),
            _ => Err("unsupported archive database target from PostgreSQL".to_owned()),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum ArchiveExtractionStatus {
    Converted,
    NeedsGuidance,
    NotReadable,
    NotApplicable,
}

impl Default for ArchiveExtractionStatus {
    fn default() -> Self {
        Self::NotReadable
    }
}

impl ArchiveExtractionStatus {
    fn as_postgres_value(&self) -> &'static str {
        match self {
            Self::Converted => "converted",
            Self::NeedsGuidance => "needs_guidance",
            Self::NotReadable => "not_readable",
            Self::NotApplicable => "not_applicable",
        }
    }

    fn from_postgres_value(value: &str) -> Result<Self, String> {
        match value {
            "converted" => Ok(Self::Converted),
            "needs_guidance" => Ok(Self::NeedsGuidance),
            "not_readable" => Ok(Self::NotReadable),
            "not_applicable" => Ok(Self::NotApplicable),
            _ => Err("unsupported archive extraction status from PostgreSQL".to_owned()),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum ArchiveIntakeStatus {
    Received,
    NeedsGuidance,
    ReadyForStaging,
    Archived,
    Admitted,
    Rejected,
}

impl ArchiveIntakeStatus {
    fn as_postgres_value(&self) -> &'static str {
        match self {
            Self::Received => "received",
            Self::NeedsGuidance => "needs_guidance",
            Self::ReadyForStaging => "ready_for_staging",
            Self::Archived => "archived",
            Self::Admitted => "admitted",
            Self::Rejected => "rejected",
        }
    }

    fn from_postgres_value(value: &str) -> Result<Self, String> {
        match value {
            "received" => Ok(Self::Received),
            "needs_guidance" => Ok(Self::NeedsGuidance),
            "ready_for_staging" => Ok(Self::ReadyForStaging),
            "archived" => Ok(Self::Archived),
            "admitted" => Ok(Self::Admitted),
            "rejected" => Ok(Self::Rejected),
            _ => Err("unsupported archive intake status from PostgreSQL".to_owned()),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum ArchiveIntakeAction {
    MapColumns,
    ResolveAnomalies,
    SaveToBusinessData,
    KeepInArchive,
}

impl ArchiveIntakeAction {
    fn as_postgres_value(&self) -> &'static str {
        match self {
            Self::MapColumns => "map_columns",
            Self::ResolveAnomalies => "resolve_anomalies",
            Self::SaveToBusinessData => "save_to_business_data",
            Self::KeepInArchive => "keep_in_archive",
        }
    }

    fn from_postgres_value(value: &str) -> Result<Self, String> {
        match value {
            "map_columns" => Ok(Self::MapColumns),
            "resolve_anomalies" => Ok(Self::ResolveAnomalies),
            "save_to_business_data" => Ok(Self::SaveToBusinessData),
            "keep_in_archive" | "none" => Ok(Self::KeepInArchive),
            _ => Err("unsupported archive next action from PostgreSQL".to_owned()),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct GuidanceItem {
    id: String,
    code: GuidanceCode,
    severity: GuidanceSeverity,
    column: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct FieldMapping {
    #[serde(default)]
    source_column: String,
    #[serde(default)]
    target_table: DatabaseTarget,
    #[serde(default)]
    target_field: String,
    #[serde(default)]
    confidence: u8,
    #[serde(default)]
    required: bool,
    #[serde(default)]
    status: FieldMappingStatus,
    #[serde(default = "default_true")]
    editable: bool,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    reason_codes: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    value_shape: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum FieldMappingStatus {
    Inferred,
    NeedsReview,
    Preserved,
    Confirmed,
    Ignored,
}

impl FieldMappingStatus {
    fn is_review_blocking(&self) -> bool {
        matches!(self, Self::NeedsReview | Self::Preserved)
    }
}

impl Default for FieldMappingStatus {
    fn default() -> Self {
        Self::NeedsReview
    }
}

fn default_true() -> bool {
    true
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
struct ArchiveFieldMappingInput {
    #[serde(default, alias = "sourceFingerprint")]
    source_fingerprint: String,
    #[serde(default)]
    mappings: Vec<FieldMappingDecisionInput>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
struct FieldMappingDecisionInput {
    #[serde(alias = "sourceColumn")]
    source_column: String,
    #[serde(alias = "targetTable")]
    target_table: DatabaseTarget,
    #[serde(alias = "targetField")]
    target_field: String,
    status: FieldMappingStatus,
    #[serde(default, alias = "ignoreReason")]
    ignore_reason: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct FieldMappingTemplatePayload {
    source_fingerprint: String,
    mappings: Vec<FieldMapping>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum GuidanceCode {
    ChooseBusinessArea,
    ExplainColumn,
    ConfirmMissingRequiredData,
    UploadReadableSheet,
}

impl GuidanceCode {
    fn as_postgres_value(&self) -> &'static str {
        match self {
            Self::ChooseBusinessArea => "choose_business_area",
            Self::ExplainColumn => "explain_column",
            Self::ConfirmMissingRequiredData => "confirm_missing_required_data",
            Self::UploadReadableSheet => "upload_readable_sheet",
        }
    }

    fn from_postgres_value(value: &str) -> Result<Self, String> {
        match value {
            "choose_business_area" => Ok(Self::ChooseBusinessArea),
            "explain_column" => Ok(Self::ExplainColumn),
            "confirm_missing_required_data" => Ok(Self::ConfirmMissingRequiredData),
            "upload_readable_sheet" => Ok(Self::UploadReadableSheet),
            _ => Err("unsupported archive guidance code from PostgreSQL".to_owned()),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct AnomalyItem {
    id: String,
    code: AnomalyCode,
    severity: GuidanceSeverity,
    column: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum AnomalyCode {
    EmptyFile,
    LargeFile,
    NoRowsDetected,
    UnknownFileStructure,
}

impl AnomalyCode {
    fn as_postgres_value(&self) -> &'static str {
        match self {
            Self::EmptyFile => "empty_file",
            Self::LargeFile => "large_file",
            Self::NoRowsDetected => "no_rows_detected",
            Self::UnknownFileStructure => "unknown_file_structure",
        }
    }

    fn from_postgres_value(value: &str) -> Result<Self, String> {
        match value {
            "empty_file" => Ok(Self::EmptyFile),
            "large_file" => Ok(Self::LargeFile),
            "no_rows_detected" => Ok(Self::NoRowsDetected),
            "unknown_file_structure" => Ok(Self::UnknownFileStructure),
            _ => Err("unsupported archive anomaly code from PostgreSQL".to_owned()),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum GuidanceSeverity {
    Info,
    Warning,
    Blocking,
}

impl GuidanceSeverity {
    fn as_postgres_value(&self) -> &'static str {
        match self {
            Self::Info => "info",
            Self::Warning => "warning",
            Self::Blocking => "blocking",
        }
    }

    fn from_postgres_value(value: &str) -> Result<Self, String> {
        match value {
            "info" => Ok(Self::Info),
            "warning" => Ok(Self::Warning),
            "blocking" => Ok(Self::Blocking),
            _ => Err("unsupported archive guidance severity from PostgreSQL".to_owned()),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
struct ArchiveIntakeInput {
    file_name: Option<String>,
    file_type: Option<String>,
    file_size_bytes: Option<u64>,
    content_sha256: Option<String>,
    sample_text: Option<String>,
    object_uri: Option<String>,
    blob_uri: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct ArchiveIssueResolutionInput {
    issue_type: Option<String>,
    issue_id: Option<String>,
    code: Option<String>,
    column: Option<String>,
    decision: Option<String>,
    note: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
struct ArchiveIssueResolutionAudit {
    decision: String,
    note: String,
    resolved_by: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct ArchiveRollbackInput {
    reason: Option<String>,
    recovery_point_id: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
struct ArchiveRollbackEvidence {
    source: &'static str,
    target_table: String,
    reversed_rows: i32,
    recovery_point_id: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct ArchiveRecoveryPoint {
    id: String,
    target_table: String,
    business_key: String,
    action: String,
    before_exists: bool,
    recovery_status: String,
    captured_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct ArchiveSourceSyncItem {
    id: String,
    operation: String,
    status: String,
    source_object_uri: String,
    generated_object_uri: String,
    created_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct ArchiveSourceVersion {
    version: i32,
    object_uri: String,
    content_sha256: String,
    file_size_bytes: u64,
    created_at_unix: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
struct ArchiveSourceSyncPlan {
    schema: &'static str,
    generated_at_unix: u64,
    sync_items: Vec<ArchiveSourceSyncPlanItem>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
struct ArchiveSourceSyncPlanItem {
    sync_item_id: String,
    intake_id: String,
    operation: String,
    target_table: String,
    source_object_uri: String,
    generated_object_uri: String,
    object_key: String,
    content_type: &'static str,
    content_sha256: String,
    file_size_bytes: u64,
    body_text: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct ArchiveSourceSyncCompletionInput {
    sync_item_id: Option<String>,
    generated_object_uri: Option<String>,
    content_sha256: Option<String>,
    file_size_bytes: Option<u64>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ArchiveSourceSyncCompletion {
    sync_item_id: String,
    generated_object_uri: String,
    content_sha256: String,
    file_size_bytes: i64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct ArchiveSourceSyncFailureInput {
    sync_item_id: Option<String>,
    error: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ArchiveSourceSyncFailure {
    sync_item_id: String,
    error: String,
}

#[derive(Clone, Debug, PartialEq)]
struct ArchiveSourceSyncPendingRow {
    sync_item_id: String,
    intake_id: String,
    source_version: i32,
    target_table: String,
    operation: String,
    source_object_uri: String,
    change_payload: serde_json::Value,
    workbook_rows: Vec<serde_json::Value>,
    created_by: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
struct ArchiveAdmissionEvidence {
    source: &'static str,
    target_table: String,
    admitted_rows: i32,
    rejected_rows: i32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct RustFsObjectRef {
    uri: String,
    bucket: String,
    key: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct StagedBusinessRow {
    row_number: i32,
    row_hash: String,
    row_payload_json: String,
    employee_external_id: Option<String>,
    display_name: Option<String>,
    department: Option<String>,
    employment_status: Option<String>,
    work_date: Option<String>,
    gross_pay: Option<String>,
    deduction_total: Option<String>,
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    let action = args
        .first()
        .map(String::as_str)
        .ok_or_else(|| "missing archive intake action".to_owned())?;

    if postgres_dsn_configured() {
        return run_postgres(args);
    }

    let path = store_path()?;

    match action {
        "list" => print_store(&load_store(&path)?),
        "add" => {
            let input = read_input()?;
            let mut store = load_store(&path)?;
            let id_seed = now_unix_nanos();
            let record = build_intake_record(input, now_unix(), id_seed)?;
            store.intakes.push(record);
            sort_intakes(&mut store);
            save_store(&path, &store)?;
            print_store(&store)
        }
        "resolve" => {
            let intake_id = args
                .get(1)
                .map(String::as_str)
                .ok_or_else(|| "missing archive intake id for issue resolution".to_owned())?;
            let input = read_resolution_input()?;
            let mut store = load_store(&path)?;
            resolve_local_intake_issue(&mut store, intake_id, input, now_unix())?;
            sort_intakes(&mut store);
            save_store(&path, &store)?;
            print_store(&store)
        }
        "map-fields" => {
            let intake_id = args
                .get(1)
                .map(String::as_str)
                .ok_or_else(|| "missing archive intake id for field mapping".to_owned())?;
            let input = read_field_mapping_input()?;
            let mut store = load_store(&path)?;
            apply_local_field_mappings(&mut store, intake_id, input, now_unix())?;
            sort_intakes(&mut store);
            save_store(&path, &store)?;
            print_store(&store)
        }
        "admit" => Err(
            "PostgreSQL archive admission requires BITWEEN_POSTGRES_DSN and canonical HR/payroll tables."
                .to_owned(),
        ),
        "rollback" => Err(
            "PostgreSQL archive rollback requires BITWEEN_POSTGRES_DSN and canonical HR/payroll tables."
                .to_owned(),
        ),
        "source-sync-plan" | "source-sync-complete" | "source-sync-fail" => Err(
            "PostgreSQL archive source synchronization requires BITWEEN_POSTGRES_DSN, canonical tables, and RustFS object storage."
                .to_owned(),
        ),
        _ => Err(format!("unsupported archive intake action: {action}")),
    }
}

fn run_postgres(args: Vec<String>) -> Result<(), String> {
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|_| "archive_postgres_runtime_failed".to_owned())?;
    runtime.block_on(run_postgres_async(args))
}

async fn run_postgres_async(args: Vec<String>) -> Result<(), String> {
    let action = args
        .first()
        .map(String::as_str)
        .ok_or_else(|| "missing archive intake action".to_owned())?;
    let mut session = postgres_archive_session().await?;

    match action {
        "list" => print_store(&load_postgres_store(&session).await?),
        "add" => {
            let input = read_input()?;
            add_postgres_intake(&mut session, input, now_unix(), now_unix_nanos()).await?;
            print_store(&load_postgres_store(&session).await?)
        }
        "resolve" => {
            let intake_id = args
                .get(1)
                .map(String::as_str)
                .ok_or_else(|| "missing archive intake id for issue resolution".to_owned())?;
            let input = read_resolution_input()?;
            resolve_postgres_intake_issue(&mut session, intake_id, input).await?;
            print_store(&load_postgres_store(&session).await?)
        }
        "map-fields" => {
            let intake_id = args
                .get(1)
                .map(String::as_str)
                .ok_or_else(|| "missing archive intake id for field mapping".to_owned())?;
            let input = read_field_mapping_input()?;
            apply_postgres_field_mappings(&mut session, intake_id, input).await?;
            print_store(&load_postgres_store(&session).await?)
        }
        "admit" => {
            let intake_id = args
                .get(1)
                .map(String::as_str)
                .ok_or_else(|| "missing archive intake id for admission".to_owned())?;
            admit_postgres_intake(&mut session, intake_id).await?;
            print_store(&load_postgres_store(&session).await?)
        }
        "rollback" => {
            let intake_id = args
                .get(1)
                .map(String::as_str)
                .ok_or_else(|| "missing archive intake id for rollback".to_owned())?;
            let input = read_rollback_input()?;
            rollback_postgres_intake(&mut session, intake_id, input).await?;
            print_store(&load_postgres_store(&session).await?)
        }
        "source-sync-plan" => {
            let intake_id = args.get(1).map(String::as_str);
            print_source_sync_plan(
                &load_postgres_source_sync_plan(&session, intake_id, now_unix()).await?,
            )
        }
        "source-sync-complete" => {
            let input = read_source_sync_completion_input()?;
            complete_postgres_source_sync(&mut session, input).await?;
            print_store(&load_postgres_store(&session).await?)
        }
        "source-sync-fail" => {
            let input = read_source_sync_failure_input()?;
            fail_postgres_source_sync(&mut session, input).await?;
            print_store(&load_postgres_store(&session).await?)
        }
        _ => Err(format!("unsupported archive intake action: {action}")),
    }
}

async fn postgres_archive_session() -> Result<PostgresClientSession, String> {
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

async fn load_postgres_store(session: &PostgresClientSession) -> Result<ArchiveIntakeStore, String> {
    let rows = session
        .client
        .query(
            "SELECT id::text, original_file_name, stored_file_name, content_type, file_size_bytes, \
                    content_sha256, content_sample_sha256, content_sample_row_count, extraction_status, \
                    object_uri, object_bucket, object_key, family, database_target, \
                    status, next_action, extracted_columns::text, estimated_rows, postgres_ready, \
                    EXTRACT(EPOCH FROM updated_at)::bigint \
             FROM bitween_archive.archive_intake \
             WHERE tenant_id = $1 \
             ORDER BY updated_at DESC, original_file_name",
            &[&session.scope.tenant_id],
        )
        .await
        .map_err(|_| "archive_postgres_intake_query_failed".to_owned())?;

    let mut intakes = Vec::with_capacity(rows.len());
    for row in rows {
        let id: String = row.get(0);
        let file_size_bytes: i64 = row.get(4);
        let content_sample_row_count: i64 = row.get(7);
        let extraction_status: String = row.get(8);
        let family: String = row.get(12);
        let database_target: String = row.get(13);
        let status: String = row.get(14);
        let next_action: String = row.get(15);
        let extracted_columns_json: String = row.get(16);
        let estimated_rows: i64 = row.get(17);
        let updated_at_unix: i64 = row.get(19);
        let (guidance_items, anomalies) = load_postgres_issues(session, &id).await?;
        let source_versions = load_postgres_source_versions(session, &id).await?;
        let recovery_points = load_postgres_recovery_points(session, &id).await?;
        let source_sync_items = load_postgres_source_sync_items(session, &id).await?;

        let object_uri: String = row.get(9);
        let database_target = DatabaseTarget::from_postgres_value(&database_target)?;
        let extracted_columns = decode_columns_json(&extracted_columns_json)?;
        let source_fingerprint = source_fingerprint(&extracted_columns, &database_target);
        let field_mappings =
            load_postgres_field_mappings(session, &family, &database_target, &source_fingerprint)
                .await?
                .unwrap_or_else(|| infer_field_mappings(&database_target, &extracted_columns));
        intakes.push(ArchiveIntakeRecord {
            id,
            original_file_name: row.get(1),
            stored_file_name: row.get(2),
            file_type: row.get(3),
            file_size_bytes: file_size_bytes.try_into().unwrap_or(0),
            content_sha256: row.get(5),
            content_sample_sha256: row.get(6),
            content_sample_row_count: content_sample_row_count.try_into().unwrap_or(0),
            extraction_status: ArchiveExtractionStatus::from_postgres_value(&extraction_status)?,
            object_uri: object_uri.clone(),
            object_bucket: row.get(10),
            object_key: row.get(11),
            blob_ref: object_uri,
            family: FileFamily::from_postgres_value(&family)?,
            database_target,
            status: ArchiveIntakeStatus::from_postgres_value(&status)?,
            next_action: ArchiveIntakeAction::from_postgres_value(&next_action)?,
            extracted_columns,
            source_fingerprint,
            field_mappings,
            estimated_rows: estimated_rows.try_into().unwrap_or(0),
            guidance_items,
            anomalies,
            source_versions,
            recovery_points,
            source_sync_items,
            postgres_ready: row.get(18),
            updated_at_unix: updated_at_unix.try_into().unwrap_or(0),
        });
    }

    let mut store = ArchiveIntakeStore {
        schema: ARCHIVE_INTAKE_STORE_SCHEMA.to_owned(),
        intakes,
    };
    sort_intakes(&mut store);
    Ok(store)
}

async fn load_postgres_issues(
    session: &PostgresClientSession,
    intake_id: &str,
) -> Result<(Vec<GuidanceItem>, Vec<AnomalyItem>), String> {
    let rows = session
        .client
        .query(
            "SELECT issue_type, code, severity, COALESCE(column_name, '') \
             FROM bitween_archive.archive_intake_issue \
             WHERE tenant_id = $1 AND intake_id = $2::text::uuid AND status = 'open' \
             ORDER BY created_at, code, COALESCE(column_name, '')",
            &[&session.scope.tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_issue_query_failed".to_owned())?;

    let mut guidance_items = Vec::new();
    let mut anomalies = Vec::new();
    for row in rows {
        let issue_type: String = row.get(0);
        let code: String = row.get(1);
        let severity: String = row.get(2);
        let column: String = row.get(3);
        match issue_type.as_str() {
            "guidance" => guidance_items.push(GuidanceItem {
                id: issue_item_id("guidance", &code, &column),
                code: GuidanceCode::from_postgres_value(&code)?,
                severity: GuidanceSeverity::from_postgres_value(&severity)?,
                column,
            }),
            "anomaly" => anomalies.push(AnomalyItem {
                id: issue_item_id("anomaly", &code, &column),
                code: AnomalyCode::from_postgres_value(&code)?,
                severity: GuidanceSeverity::from_postgres_value(&severity)?,
                column,
            }),
            _ => return Err("unsupported archive issue type from PostgreSQL".to_owned()),
        }
    }
    Ok((guidance_items, anomalies))
}

async fn load_postgres_field_mappings(
    session: &PostgresClientSession,
    family: &str,
    database_target: &DatabaseTarget,
    source_fingerprint: &str,
) -> Result<Option<Vec<FieldMapping>>, String> {
    let Some(business_family) = mapping_business_family(family) else {
        return Ok(None);
    };
    if !matches!(
        database_target,
        DatabaseTarget::HrEmployeeStaging
            | DatabaseTarget::HrAttendanceStaging
            | DatabaseTarget::PayrollInputStaging
    ) {
        return Ok(None);
    }
    let target_table = database_target.as_postgres_value();
    let Some(row) = session
        .client
        .query_opt(
            "SELECT mapping::text \
             FROM bitween_archive.archive_mapping_template \
             WHERE tenant_id = $1 \
               AND business_family = $2 \
               AND source_fingerprint = $3 \
               AND target_table = $4 \
               AND status IN ('active', 'draft') \
             ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, updated_at DESC \
             LIMIT 1",
            &[
                &session.scope.tenant_id,
                &business_family,
                &source_fingerprint,
                &target_table,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_mapping_template_query_failed".to_owned())?
    else {
        return Ok(None);
    };
    let body: String = row.get(0);
    let payload = serde_json::from_str::<FieldMappingTemplatePayload>(&body)
        .map_err(|_| "archive_postgres_mapping_template_decode_failed".to_owned())?;
    Ok(Some(payload.mappings))
}

fn mapping_business_family(family: &str) -> Option<&'static str> {
    match family {
        "hr" => Some("hr"),
        "payroll" => Some("payroll"),
        _ => None,
    }
}

async fn load_postgres_source_versions(
    session: &PostgresClientSession,
    intake_id: &str,
) -> Result<Vec<ArchiveSourceVersion>, String> {
    let rows = session
        .client
        .query(
            "SELECT version, object_uri, content_sha256, file_size_bytes, \
                    EXTRACT(EPOCH FROM created_at)::bigint \
             FROM bitween_archive.archive_intake_version \
             WHERE tenant_id = $1 AND intake_id = $2::text::uuid \
             ORDER BY version DESC \
             LIMIT 20",
            &[&session.scope.tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_source_versions_query_failed".to_owned())?;

    Ok(rows
        .into_iter()
        .map(|row| {
            let file_size_bytes: i64 = row.get(3);
            let created_at_unix: i64 = row.get(4);
            ArchiveSourceVersion {
                version: row.get(0),
                object_uri: row.get(1),
                content_sha256: row.get(2),
                file_size_bytes: file_size_bytes.try_into().unwrap_or(0),
                created_at_unix: created_at_unix.try_into().unwrap_or(0),
            }
        })
        .collect())
}

async fn load_postgres_recovery_points(
    session: &PostgresClientSession,
    intake_id: &str,
) -> Result<Vec<ArchiveRecoveryPoint>, String> {
    let rows = session
        .client
        .query(
            "SELECT id::text, target_table, business_key, action, before_exists, recovery_status, \
                    EXTRACT(EPOCH FROM captured_at)::bigint \
             FROM bitween_archive.archive_admission_recovery_point \
             WHERE tenant_id = $1 AND intake_id = $2::text::uuid \
             ORDER BY captured_at DESC, business_key \
             LIMIT 50",
            &[&session.scope.tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_recovery_points_query_failed".to_owned())?;

    Ok(rows
        .into_iter()
        .map(|row| {
            let captured_at_unix: i64 = row.get(6);
            ArchiveRecoveryPoint {
                id: row.get(0),
                target_table: row.get(1),
                business_key: row.get(2),
                action: row.get(3),
                before_exists: row.get(4),
                recovery_status: row.get(5),
                captured_at_unix: captured_at_unix.try_into().unwrap_or(0),
            }
        })
        .collect())
}

async fn load_postgres_source_sync_items(
    session: &PostgresClientSession,
    intake_id: &str,
) -> Result<Vec<ArchiveSourceSyncItem>, String> {
    let rows = session
        .client
        .query(
            "SELECT id::text, operation, status, source_object_uri, COALESCE(generated_object_uri, ''), \
                    EXTRACT(EPOCH FROM created_at)::bigint \
             FROM bitween_archive.archive_source_sync \
             WHERE tenant_id = $1 AND intake_id = $2::text::uuid \
             ORDER BY created_at DESC \
             LIMIT 20",
            &[&session.scope.tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_source_sync_query_failed".to_owned())?;

    Ok(rows
        .into_iter()
        .map(|row| {
            let created_at_unix: i64 = row.get(5);
            ArchiveSourceSyncItem {
                id: row.get(0),
                operation: row.get(1),
                status: row.get(2),
                source_object_uri: row.get(3),
                generated_object_uri: row.get(4),
                created_at_unix: created_at_unix.try_into().unwrap_or(0),
            }
        })
        .collect())
}

async fn load_postgres_source_sync_plan(
    session: &PostgresClientSession,
    intake_id: Option<&str>,
    generated_at_unix: u64,
) -> Result<ArchiveSourceSyncPlan, String> {
    let intake_filter = intake_id.unwrap_or_default();
    let rows = session
        .client
        .query(
            "SELECT s.id::text, s.intake_id::text, s.source_version, s.target_table, s.operation, \
                    s.source_object_uri, s.change_payload::text, \
                    COALESCE(( \
                      CASE s.target_table \
                        WHEN 'hr_employee' THEN ( \
                          SELECT jsonb_agg(jsonb_build_object( \
                              'row_number', row_number, 'validation_status', validation_status, \
                              'employee_external_id', employee_external_id, 'display_name', display_name, \
                              'department', department, 'employment_status', employment_status, \
                              'row_hash', row_hash \
                            ) ORDER BY row_number) \
                          FROM bitween_archive.hr_employee_staging r \
                          WHERE r.tenant_id = s.tenant_id AND r.intake_id = s.intake_id \
                        ) \
                        WHEN 'hr_attendance' THEN ( \
                          SELECT jsonb_agg(jsonb_build_object( \
                              'row_number', row_number, 'validation_status', validation_status, \
                              'employee_external_id', employee_external_id, 'work_date', work_date, \
                              'row_hash', row_hash \
                            ) ORDER BY row_number) \
                          FROM bitween_archive.hr_attendance_staging r \
                          WHERE r.tenant_id = s.tenant_id AND r.intake_id = s.intake_id \
                        ) \
                        WHEN 'payroll_input' THEN ( \
                          SELECT jsonb_agg(jsonb_build_object( \
                              'row_number', row_number, 'validation_status', validation_status, \
                              'employee_external_id', employee_external_id, 'gross_pay', gross_pay, \
                              'deduction_total', deduction_total, 'row_hash', row_hash \
                            ) ORDER BY row_number) \
                          FROM bitween_archive.payroll_input_staging r \
                          WHERE r.tenant_id = s.tenant_id AND r.intake_id = s.intake_id \
                        ) \
                        ELSE '[]'::jsonb \
                      END \
                    ), '[]'::jsonb)::text AS workbook_rows, \
                    s.requested_by \
             FROM bitween_archive.archive_source_sync s \
             WHERE s.tenant_id = $1 AND s.status = 'pending' \
               AND ($2 = '' OR s.intake_id = NULLIF($2, '')::uuid) \
             ORDER BY s.created_at ASC, s.id ASC \
             LIMIT 25",
            &[&session.scope.tenant_id, &intake_filter],
        )
        .await
        .map_err(|_| "archive_postgres_source_sync_plan_query_failed".to_owned())?;

    let bucket = source_sync_bucket()?;
    let sync_items = rows
        .into_iter()
        .map(|row| {
            let change_payload = parse_json_value(row.get::<usize, String>(6).as_str())?;
            let workbook_rows = parse_json_array(row.get::<usize, String>(7).as_str())?;
            let pending = ArchiveSourceSyncPendingRow {
                sync_item_id: row.get(0),
                intake_id: row.get(1),
                source_version: row.get(2),
                target_table: row.get(3),
                operation: row.get(4),
                source_object_uri: row.get(5),
                change_payload,
                workbook_rows,
                created_by: row.get(8),
            };
            build_source_sync_plan_item(&pending, &bucket)
        })
        .collect::<Result<Vec<_>, _>>()?;

    Ok(ArchiveSourceSyncPlan {
        schema: ARCHIVE_SOURCE_SYNC_PLAN_SCHEMA,
        generated_at_unix,
        sync_items,
    })
}

fn source_sync_bucket() -> Result<String, String> {
    source_sync_bucket_from_parts(
        std::env::var("BITWEEN_RUSTFS_BUCKET").ok(),
        std::env::var("BITWEEN_RUSTFS_BUCKET_ARCHIVE").ok(),
    )
}

fn source_sync_bucket_from_parts(
    primary_bucket: Option<String>,
    archive_bucket: Option<String>,
) -> Result<String, String> {
    let bucket = primary_bucket
        .or(archive_bucket)
        .map(clean)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "archive_source_sync_rustfs_bucket_required".to_owned())?;
    if !bucket.chars().all(|ch| ch.is_ascii_lowercase() || ch.is_ascii_digit() || ch == '-' || ch == '.')
        || bucket.starts_with('-')
        || bucket.ends_with('-')
        || bucket.len() < 3
        || bucket.len() > 63
    {
        return Err("archive_source_sync_rustfs_bucket_invalid".to_owned());
    }
    Ok(bucket)
}

fn parse_json_value(body: &str) -> Result<serde_json::Value, String> {
    serde_json::from_str(body).map_err(|_| "archive_postgres_source_sync_json_decode_failed".to_owned())
}

fn parse_json_array(body: &str) -> Result<Vec<serde_json::Value>, String> {
    match parse_json_value(body)? {
        serde_json::Value::Array(items) => Ok(items),
        _ => Err("archive_postgres_source_sync_rows_not_array".to_owned()),
    }
}

fn build_source_sync_plan_item(
    row: &ArchiveSourceSyncPendingRow,
    bucket: &str,
) -> Result<ArchiveSourceSyncPlanItem, String> {
    let body_text = source_sync_workbook_xml(row)?;
    let body_bytes = body_text.as_bytes();
    let object_key = source_sync_object_key(row);
    let content_sha256 = hex_sha256(body_bytes);
    let file_size_bytes = u64::try_from(body_bytes.len())
        .map_err(|_| "archive_source_sync_workbook_too_large".to_owned())?;
    Ok(ArchiveSourceSyncPlanItem {
        sync_item_id: row.sync_item_id.clone(),
        intake_id: row.intake_id.clone(),
        operation: row.operation.clone(),
        target_table: row.target_table.clone(),
        source_object_uri: row.source_object_uri.clone(),
        generated_object_uri: format!("rustfs://{bucket}/{object_key}"),
        object_key,
        content_type: ARCHIVE_SOURCE_SYNC_CONTENT_TYPE,
        content_sha256,
        file_size_bytes,
        body_text,
    })
}

fn source_sync_object_key(row: &ArchiveSourceSyncPendingRow) -> String {
    format!(
        "derived/{}/{}/{}-{}.xml",
        source_sync_key_part(&row.intake_id),
        row.source_version,
        source_sync_key_part(&row.sync_item_id),
        source_sync_key_part(&row.operation)
    )
}

fn source_sync_key_part(value: &str) -> String {
    let cleaned = value
        .chars()
        .map(|ch| match ch {
            'a'..='z' | 'A'..='Z' | '0'..='9' | '-' | '_' => ch.to_ascii_lowercase(),
            _ => '-',
        })
        .collect::<String>();
    cleaned
        .trim_matches('-')
        .chars()
        .take(96)
        .collect::<String>()
        .if_empty("item")
}

trait IfEmpty {
    fn if_empty(self, default_value: &str) -> String;
}

impl IfEmpty for String {
    fn if_empty(self, default_value: &str) -> String {
        if self.is_empty() {
            default_value.to_owned()
        } else {
            self
        }
    }
}

fn source_sync_workbook_xml(row: &ArchiveSourceSyncPendingRow) -> Result<String, String> {
    let metadata_rows = vec![
        ("schema", ARCHIVE_SOURCE_SYNC_PLAN_SCHEMA.to_owned()),
        ("sync_item_id", row.sync_item_id.clone()),
        ("intake_id", row.intake_id.clone()),
        ("operation", row.operation.clone()),
        ("target_table", row.target_table.clone()),
        ("source_version", row.source_version.to_string()),
        ("source_object_uri", row.source_object_uri.clone()),
        ("requested_by", row.created_by.clone()),
        ("binary_snapshot_stored", "false".to_owned()),
        (
            "postgres_payload",
            row.change_payload
                .get("postgres_payload")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("row_delta_json")
                .to_owned(),
        ),
        (
            "workbook_strategy",
            row.change_payload
                .get("workbook_strategy")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("immutable_original_plus_derived_rustfs_version")
                .to_owned(),
        ),
        (
            "admitted_rows",
            json_scalar_to_string(row.change_payload.get("admitted_rows")),
        ),
        (
            "rejected_rows",
            json_scalar_to_string(row.change_payload.get("rejected_rows")),
        ),
        (
            "reversed_rows",
            json_scalar_to_string(row.change_payload.get("reversed_rows")),
        ),
    ];

    let mut body = String::new();
    body.push_str(r#"<?xml version="1.0" encoding="UTF-8"?>"#);
    body.push('\n');
    body.push_str(
        r#"<?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">"#,
    );
    body.push_str(r#"<Worksheet ss:Name="Sync"><Table>"#);
    for (key, value) in metadata_rows {
        push_excel_row(&mut body, &[key.to_owned(), value]);
    }
    body.push_str(r#"</Table></Worksheet>"#);
    body.push_str(r#"<Worksheet ss:Name="Rows"><Table>"#);
    push_excel_row(
        &mut body,
        &[
            "row_number".to_owned(),
            "validation_status".to_owned(),
            "employee_external_id".to_owned(),
            "display_name".to_owned(),
            "department".to_owned(),
            "work_date".to_owned(),
            "gross_pay".to_owned(),
            "deduction_total".to_owned(),
            "row_hash".to_owned(),
        ],
    );
    for item in &row.workbook_rows {
        push_excel_row(
            &mut body,
            &[
                json_scalar_to_string(item.get("row_number")),
                json_scalar_to_string(item.get("validation_status")),
                json_scalar_to_string(item.get("employee_external_id")),
                json_scalar_to_string(item.get("display_name")),
                json_scalar_to_string(item.get("department")),
                json_scalar_to_string(item.get("work_date")),
                json_scalar_to_string(item.get("gross_pay")),
                json_scalar_to_string(item.get("deduction_total")),
                json_scalar_to_string(item.get("row_hash")),
            ],
        );
    }
    body.push_str(r#"</Table></Worksheet></Workbook>"#);
    Ok(body)
}

fn push_excel_row(body: &mut String, values: &[String]) {
    body.push_str("<Row>");
    for value in values {
        body.push_str(r#"<Cell><Data ss:Type="String">"#);
        body.push_str(&xml_escape(value));
        body.push_str("</Data></Cell>");
    }
    body.push_str("</Row>");
}

fn xml_escape(value: &str) -> String {
    value
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&apos;")
}

fn json_scalar_to_string(value: Option<&serde_json::Value>) -> String {
    match value {
        Some(serde_json::Value::String(value)) => value.clone(),
        Some(serde_json::Value::Number(value)) => value.to_string(),
        Some(serde_json::Value::Bool(value)) => value.to_string(),
        Some(serde_json::Value::Null) | None => String::new(),
        Some(value) => value.to_string(),
    }
}

fn hex_sha256(data: &[u8]) -> String {
    let digest = Sha256::digest(data);
    digest.iter().map(|byte| format!("{byte:02x}")).collect()
}

async fn add_postgres_intake(
    session: &mut PostgresClientSession,
    input: ArchiveIntakeInput,
    updated_at_unix: u64,
    id_seed: u128,
) -> Result<(), String> {
    let sample_text = input.sample_text.clone().unwrap_or_default();
    let mut record = build_intake_record(input, updated_at_unix, id_seed)?;
    if let Some(field_mappings) = load_postgres_field_mappings(
        session,
        record.family.as_postgres_value(),
        &record.database_target,
        &record.source_fingerprint,
    )
    .await?
    {
        record.field_mappings = field_mappings;
        refresh_local_intake_review_state(&mut record, updated_at_unix);
    }
    let staged_rows = staged_rows_for_record_with_mappings(
        &record.database_target,
        &record.extracted_columns,
        &sample_text,
        &record.field_mappings,
    )?;
    let file_size_bytes: i64 = record
        .file_size_bytes
        .try_into()
        .map_err(|_| "archive_postgres_file_size_out_of_range".to_owned())?;
    let content_sample_row_count: i64 = record
        .content_sample_row_count
        .try_into()
        .map_err(|_| "archive_postgres_sample_row_count_out_of_range".to_owned())?;
    let estimated_rows: i64 = record
        .estimated_rows
        .try_into()
        .map_err(|_| "archive_postgres_estimated_rows_out_of_range".to_owned())?;
    let extracted_columns_json = encode_columns_json(&record.extracted_columns)?;
    let redacted_content_sample_excerpt = redacted_content_sample_excerpt(&sample_text);
    let tenant_id = session.scope.tenant_id.clone();
    let legal_entity_id = session.scope.legal_entity_id.clone();
    let workplace_id = session.scope.workplace_id.clone();
    let payroll_period = std::env::var("BITWEEN_PAYROLL_PERIOD")
        .ok()
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty());
    let actor = postgres_actor();
    let family = record.family.as_postgres_value();
    let database_target = record.database_target.as_postgres_value();
    let status = record.status.as_postgres_value();
    let next_action = record.next_action.as_postgres_value();
    let extraction_status = record.extraction_status.as_postgres_value();

    let transaction = session
        .client
        .transaction()
        .await
        .map_err(|_| "archive_postgres_transaction_failed".to_owned())?;
    let row = transaction
        .query_one(
            "INSERT INTO bitween_archive.archive_intake ( \
                tenant_id, legal_entity_id, workplace_id, payroll_period, uploader_user_id, \
                original_file_name, stored_file_name, object_uri, object_bucket, object_key, \
                content_sha256, content_sample_sha256, content_sample_row_count, redacted_content_sample_excerpt, \
                extraction_status, content_type, file_size_bytes, family, database_target, status, \
                next_action, extracted_columns, estimated_rows, postgres_ready, sensitivity_label \
             ) VALUES ( \
                $1, $2, $3, $4, $5, \
                $6, $7, $8, $9, $10, \
                $11, $12, $13, $14, \
                $15, $16, $17, $18, $19, $20, \
                $21, $22::text::jsonb, $23, $24, 'restricted' \
             ) RETURNING id::text",
            &[
                &tenant_id,
                &legal_entity_id,
                &workplace_id,
                &payroll_period,
                &actor,
                &record.original_file_name,
                &record.stored_file_name,
                &record.object_uri,
                &record.object_bucket,
                &record.object_key,
                &record.content_sha256,
                &record.content_sample_sha256,
                &content_sample_row_count,
                &redacted_content_sample_excerpt,
                &extraction_status,
                &record.file_type,
                &file_size_bytes,
                &family,
                &database_target,
                &status,
                &next_action,
                &extracted_columns_json,
                &estimated_rows,
                &record.postgres_ready,
            ],
        )
        .await
        .map_err(|e| format!("archive_postgres_intake_insert_failed: {e}"))?;
    let intake_id: String = row.get(0);

    transaction
        .execute(
            "INSERT INTO bitween_archive.archive_intake_version ( \
                intake_id, tenant_id, version, object_uri, object_bucket, object_key, \
                content_sha256, file_size_bytes, created_by \
             ) VALUES ($1::text::uuid, $2, 1, $3, $4, $5, $6, $7, $8)",
            &[
                &intake_id,
                &tenant_id,
                &record.object_uri,
                &record.object_bucket,
                &record.object_key,
                &record.content_sha256,
                &file_size_bytes,
                &actor,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_version_insert_failed".to_owned())?;

    insert_postgres_staging_rows(
        &transaction,
        &record.database_target,
        &intake_id,
        &tenant_id,
        &legal_entity_id,
        &workplace_id,
        payroll_period.as_deref(),
        &staged_rows,
    )
    .await?;

    for item in &record.guidance_items {
        let code = item.code.as_postgres_value();
        let severity = item.severity.as_postgres_value();
        let prompt = issue_prompt(code, &item.column);
        transaction
            .execute(
                "INSERT INTO bitween_archive.archive_intake_issue ( \
                    intake_id, tenant_id, issue_type, code, severity, column_name, prompt, owner_role \
                 ) VALUES ($1::text::uuid, $2, 'guidance', $3, $4, NULLIF($5, ''), $6, 'archive_operator')",
                &[
                    &intake_id,
                    &tenant_id,
                    &code,
                    &severity,
                    &item.column,
                    &prompt,
                ],
            )
            .await
            .map_err(|_| "archive_postgres_issue_insert_failed".to_owned())?;
    }
    for item in &record.anomalies {
        let code = item.code.as_postgres_value();
        let severity = item.severity.as_postgres_value();
        let prompt = issue_prompt(code, &item.column);
        transaction
            .execute(
                "INSERT INTO bitween_archive.archive_intake_issue ( \
                    intake_id, tenant_id, issue_type, code, severity, column_name, prompt, owner_role \
                 ) VALUES ($1::text::uuid, $2, 'anomaly', $3, $4, NULLIF($5, ''), $6, 'archive_operator')",
                &[
                    &intake_id,
                    &tenant_id,
                    &code,
                    &severity,
                    &item.column,
                    &prompt,
                ],
            )
            .await
            .map_err(|_| "archive_postgres_issue_insert_failed".to_owned())?;
    }
    transaction
        .commit()
        .await
        .map_err(|_| "archive_postgres_commit_failed".to_owned())?;
    Ok(())
}

async fn resolve_postgres_intake_issue(
    session: &mut PostgresClientSession,
    intake_id: &str,
    input: ArchiveIssueResolutionInput,
) -> Result<(), String> {
    let issue_type = normalized_issue_type(&input)?;
    let code = normalized_issue_code(&input)?;
    let column = normalized_issue_column(&input);
    let actor = postgres_actor();
    let resolution_json = issue_resolution_json(&input, &actor)?;
    let tenant_id = session.scope.tenant_id.clone();

    let transaction = session
        .client
        .transaction()
        .await
        .map_err(|_| "archive_postgres_transaction_failed".to_owned())?;
    let updated = transaction
        .execute(
            "UPDATE bitween_archive.archive_intake_issue \
             SET status = 'resolved', resolution = $6::text::jsonb, resolved_by = $7, resolved_at = now() \
             WHERE tenant_id = $1 \
               AND intake_id = $2::text::uuid \
               AND issue_type = $3 \
               AND code = $4 \
               AND COALESCE(column_name, '') = $5 \
               AND status = 'open'",
            &[
                &tenant_id,
                &intake_id,
                &issue_type,
                &code,
                &column,
                &resolution_json,
                &actor,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_issue_resolution_failed".to_owned())?;
    if updated == 0 {
        return Err("archive_postgres_issue_not_found".to_owned());
    }

    refresh_postgres_intake_review_state(&transaction, &tenant_id, intake_id).await?;
    transaction
        .commit()
        .await
        .map_err(|_| "archive_postgres_commit_failed".to_owned())?;
    Ok(())
}

async fn apply_postgres_field_mappings(
    session: &mut PostgresClientSession,
    intake_id: &str,
    input: ArchiveFieldMappingInput,
) -> Result<(), String> {
    let tenant_id = session.scope.tenant_id.clone();
    let actor = postgres_actor();
    let transaction = session
        .client
        .transaction()
        .await
        .map_err(|_| "archive_postgres_transaction_failed".to_owned())?;
    let row = transaction
        .query_opt(
            "SELECT family, database_target, extracted_columns::text, \
                    content_sample_row_count, status, next_action \
             FROM bitween_archive.archive_intake \
             WHERE tenant_id = $1 AND id = $2::text::uuid \
             FOR UPDATE",
            &[&tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_mapping_intake_lookup_failed".to_owned())?
        .ok_or_else(|| "archive_intake_not_found".to_owned())?;
    let family_value: String = row.get(0);
    let database_target_value: String = row.get(1);
    let extracted_columns_json: String = row.get(2);
    let content_sample_row_count: i64 = row.get(3);
    let status_value: String = row.get(4);
    let next_action_value: String = row.get(5);
    let family = FileFamily::from_postgres_value(&family_value)?;
    let database_target = DatabaseTarget::from_postgres_value(&database_target_value)?;
    let extracted_columns = decode_columns_json(&extracted_columns_json)?;
    let source_fingerprint = source_fingerprint(&extracted_columns, &database_target);
    let mut record = ArchiveIntakeRecord {
        id: intake_id.to_owned(),
        original_file_name: String::new(),
        stored_file_name: String::new(),
        file_type: String::new(),
        file_size_bytes: 0,
        content_sha256: String::new(),
        content_sample_sha256: EMPTY_SHA256.to_owned(),
        content_sample_row_count: content_sample_row_count.try_into().unwrap_or(0),
        extraction_status: ArchiveExtractionStatus::NeedsGuidance,
        object_uri: String::new(),
        object_bucket: String::new(),
        object_key: String::new(),
        blob_ref: String::new(),
        family,
        database_target,
        status: ArchiveIntakeStatus::from_postgres_value(&status_value)?,
        next_action: ArchiveIntakeAction::from_postgres_value(&next_action_value)?,
        extracted_columns,
        source_fingerprint,
        field_mappings: Vec::new(),
        estimated_rows: 0,
        guidance_items: Vec::new(),
        anomalies: Vec::new(),
        source_versions: Vec::new(),
        recovery_points: Vec::new(),
        source_sync_items: Vec::new(),
        postgres_ready: false,
        updated_at_unix: now_unix(),
    };
    record.field_mappings = infer_field_mappings(&record.database_target, &record.extracted_columns);
    apply_field_mapping_decisions(&mut record, input)?;
    upsert_postgres_mapping_template(&transaction, &tenant_id, &actor, &family_value, &record)
        .await?;
    refresh_postgres_mapping_issues(&transaction, &tenant_id, intake_id, &record).await?;
    refresh_postgres_intake_review_state(&transaction, &tenant_id, intake_id).await?;
    transaction
        .commit()
        .await
        .map_err(|_| "archive_postgres_commit_failed".to_owned())?;
    Ok(())
}

async fn upsert_postgres_mapping_template(
    transaction: &tokio_postgres::Transaction<'_>,
    tenant_id: &str,
    actor: &str,
    family_value: &str,
    record: &ArchiveIntakeRecord,
) -> Result<(), String> {
    let business_family = mapping_business_family(family_value)
        .ok_or_else(|| "archive_field_mapping_business_family_required".to_owned())?;
    let target_table = record.database_target.as_postgres_value();
    if !matches!(
        record.database_target,
        DatabaseTarget::HrEmployeeStaging
            | DatabaseTarget::HrAttendanceStaging
            | DatabaseTarget::PayrollInputStaging
    ) {
        return Err("archive_field_mapping_target_table_unsupported".to_owned());
    }
    let payload = FieldMappingTemplatePayload {
        source_fingerprint: record.source_fingerprint.clone(),
        mappings: record.field_mappings.clone(),
    };
    let mapping_json = serde_json::to_string(&payload)
        .map_err(|_| "archive_field_mapping_template_encode_failed".to_owned())?;
    let has_open_mapping_review =
        !missing_required_mapping_fields(&record.database_target, &record.field_mappings).is_empty()
            || record
                .field_mappings
                .iter()
                .any(|mapping| mapping.status.is_review_blocking());
    let status = if has_open_mapping_review { "draft" } else { "active" };
    let approved_by = if status == "active" {
        Some(actor.to_owned())
    } else {
        None
    };
    transaction
        .execute(
            "INSERT INTO bitween_archive.archive_mapping_template ( \
                tenant_id, business_family, source_fingerprint, target_table, mapping, status, approved_by, approved_at \
             ) VALUES ($1, $2, $3, $4, $5::text::jsonb, $6, $7, CASE WHEN $6 = 'active' THEN now() ELSE NULL END) \
             ON CONFLICT (tenant_id, business_family, source_fingerprint, target_table) \
             DO UPDATE SET mapping = EXCLUDED.mapping, \
                           status = EXCLUDED.status, \
                           approved_by = EXCLUDED.approved_by, \
                           approved_at = EXCLUDED.approved_at",
            &[
                &tenant_id,
                &business_family,
                &record.source_fingerprint,
                &target_table,
                &mapping_json,
                &status,
                &approved_by,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_mapping_template_upsert_failed".to_owned())?;
    Ok(())
}

async fn refresh_postgres_mapping_issues(
    transaction: &tokio_postgres::Transaction<'_>,
    tenant_id: &str,
    intake_id: &str,
    record: &ArchiveIntakeRecord,
) -> Result<(), String> {
    let actor = postgres_actor();
    let resolution_json = serde_json::json!({
        "decision": "field_mapping_reviewed",
        "note": "Field mapping guidance recalculated from operator mapping decisions.",
        "resolved_by": actor,
    })
    .to_string();
    for required_field in required_target_fields(&record.database_target) {
        transaction
            .execute(
                "UPDATE bitween_archive.archive_intake_issue \
                 SET status = 'resolved', resolution = $4::text::jsonb, resolved_by = $5, resolved_at = now() \
                 WHERE tenant_id = $1 \
                   AND intake_id = $2::text::uuid \
                   AND issue_type = 'guidance' \
                   AND code = 'confirm_missing_required_data' \
                   AND COALESCE(column_name, '') = $3 \
                   AND status = 'open'",
                &[
                    &tenant_id,
                    &intake_id,
                    &required_field,
                    &resolution_json,
                    &actor,
                ],
            )
            .await
            .map_err(|_| "archive_postgres_mapping_issue_refresh_failed".to_owned())?;
    }
    for source_column in &record.extracted_columns {
        transaction
            .execute(
                "UPDATE bitween_archive.archive_intake_issue \
                 SET status = 'resolved', resolution = $4::text::jsonb, resolved_by = $5, resolved_at = now() \
                 WHERE tenant_id = $1 \
                   AND intake_id = $2::text::uuid \
                   AND issue_type = 'guidance' \
                   AND code = 'explain_column' \
                   AND COALESCE(column_name, '') = $3 \
                   AND status = 'open'",
                &[
                    &tenant_id,
                    &intake_id,
                    &source_column,
                    &resolution_json,
                    &actor,
                ],
            )
            .await
            .map_err(|_| "archive_postgres_mapping_issue_refresh_failed".to_owned())?;
    }
    for item in &record.guidance_items {
        if !matches!(
            item.code,
            GuidanceCode::ConfirmMissingRequiredData | GuidanceCode::ExplainColumn
        ) {
            continue;
        }
        let code = item.code.as_postgres_value();
        let severity = item.severity.as_postgres_value();
        let prompt = issue_prompt(code, &item.column);
        transaction
            .execute(
                "INSERT INTO bitween_archive.archive_intake_issue ( \
                    intake_id, tenant_id, issue_type, code, severity, column_name, prompt, owner_role \
                 ) VALUES ($1::text::uuid, $2, 'guidance', $3, $4, NULLIF($5, ''), $6, 'archive_operator')",
                &[
                    &intake_id,
                    &tenant_id,
                    &code,
                    &severity,
                    &item.column,
                    &prompt,
                ],
            )
            .await
            .map_err(|_| "archive_postgres_mapping_issue_insert_failed".to_owned())?;
    }
    Ok(())
}

async fn refresh_postgres_intake_review_state(
    transaction: &tokio_postgres::Transaction<'_>,
    tenant_id: &str,
    intake_id: &str,
) -> Result<(), String> {
    transaction
        .execute(
            "WITH open_issue_state AS ( \
                SELECT \
                  COALESCE(bool_or(issue_type = 'anomaly'), false) AS has_open_anomaly, \
                  COUNT(*) > 0 AS has_open_issue \
                FROM bitween_archive.archive_intake_issue \
                WHERE tenant_id = $1 AND intake_id = $2::text::uuid AND status = 'open' \
             ) \
             UPDATE bitween_archive.archive_intake \
             SET postgres_ready = ( \
                    database_target IN ('hr_employee_staging', 'hr_attendance_staging', 'payroll_input_staging') \
                    AND NOT (SELECT has_open_issue FROM open_issue_state) \
                 ), \
                 status = CASE \
                   WHEN (SELECT has_open_issue FROM open_issue_state) THEN 'needs_guidance' \
                   WHEN database_target IN ('hr_employee_staging', 'hr_attendance_staging', 'payroll_input_staging') THEN 'ready_for_staging' \
                   ELSE 'archived' \
                 END, \
                 next_action = CASE \
                   WHEN (SELECT has_open_issue FROM open_issue_state) AND (SELECT has_open_anomaly FROM open_issue_state) THEN 'resolve_anomalies' \
                   WHEN (SELECT has_open_issue FROM open_issue_state) THEN 'map_columns' \
                   WHEN database_target IN ('hr_employee_staging', 'hr_attendance_staging', 'payroll_input_staging') THEN 'save_to_business_data' \
                   ELSE 'keep_in_archive' \
                 END, \
                 extraction_status = CASE \
                   WHEN database_target = 'archive_blob' THEN 'not_applicable' \
                   WHEN (SELECT has_open_issue FROM open_issue_state) THEN 'needs_guidance' \
                   WHEN database_target IN ('hr_employee_staging', 'hr_attendance_staging', 'payroll_input_staging') \
                        AND content_sample_row_count > 0 THEN 'converted' \
                   ELSE 'not_readable' \
                 END \
             WHERE tenant_id = $1 AND id = $2::text::uuid",
            &[&tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_intake_review_state_update_failed".to_owned())?;
    Ok(())
}

async fn admit_postgres_intake(
    session: &mut PostgresClientSession,
    intake_id: &str,
) -> Result<(), String> {
    let tenant_id = session.scope.tenant_id.clone();
    let legal_entity_id = session.scope.legal_entity_id.clone();
    let workplace_id = session.scope.workplace_id.clone();
    let actor = postgres_actor();
    let transaction = session
        .client
        .transaction()
        .await
        .map_err(|_| "archive_postgres_transaction_failed".to_owned())?;
    let intake = transaction
        .query_opt(
            "SELECT database_target, status, postgres_ready, payroll_period \
             FROM bitween_archive.archive_intake \
             WHERE tenant_id = $1 AND id = $2::text::uuid \
             FOR UPDATE",
            &[&tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_admission_lookup_failed".to_owned())?
        .ok_or_else(|| "archive_intake_not_found".to_owned())?;
    let database_target: String = intake.get(0);
    let status: String = intake.get(1);
    let postgres_ready: bool = intake.get(2);
    let payroll_period: Option<String> = intake.get(3);
    if status != "ready_for_staging" || !postgres_ready {
        return Err("archive_postgres_admission_requires_ready_review".to_owned());
    }

    let target = DatabaseTarget::from_postgres_value(&database_target)?;
    let (target_table, admitted_rows, rejected_rows) = match target {
        DatabaseTarget::HrEmployeeStaging => {
            let admitted_rows = admit_postgres_hr_employee_staging(
                &transaction,
                intake_id,
                &tenant_id,
                &legal_entity_id,
                &workplace_id,
                &actor,
            )
            .await?;
            let rejected_rows =
                reject_invalid_hr_employee_staging(&transaction, intake_id, &tenant_id).await?
                    + reject_unadmitted_hr_employee_staging(&transaction, intake_id, &tenant_id)
                        .await?;
            ("hr_employee", admitted_rows, rejected_rows)
        }
        DatabaseTarget::HrAttendanceStaging => {
            let admitted_rows = admit_postgres_hr_attendance_staging(
                &transaction,
                intake_id,
                &tenant_id,
                &legal_entity_id,
                &workplace_id,
                &actor,
            )
            .await?;
            let rejected_rows =
                reject_invalid_hr_attendance_staging(&transaction, intake_id, &tenant_id).await?
                    + reject_unadmitted_hr_attendance_staging(&transaction, intake_id, &tenant_id)
                        .await?;
            ("hr_attendance", admitted_rows, rejected_rows)
        }
        DatabaseTarget::PayrollInputStaging => {
            let payroll_period = payroll_period
                .as_deref()
                .filter(|value| !value.trim().is_empty())
                .ok_or_else(|| "archive_postgres_payroll_period_required".to_owned())?;
            let admitted_rows = admit_postgres_payroll_input_staging(
                &transaction,
                intake_id,
                &tenant_id,
                &legal_entity_id,
                &workplace_id,
                payroll_period,
                &actor,
            )
            .await?;
            let rejected_rows =
                reject_invalid_payroll_input_staging(&transaction, intake_id, &tenant_id).await?
                    + reject_unadmitted_payroll_input_staging(&transaction, intake_id, &tenant_id)
                        .await?;
            ("payroll_input", admitted_rows, rejected_rows)
        }
        DatabaseTarget::ArchiveBlob | DatabaseTarget::NeedsMapping => {
            return Err("archive_postgres_admission_target_unsupported".to_owned());
        }
    };
    if admitted_rows == 0 && rejected_rows == 0 {
        return Err("archive_postgres_no_admissible_staging_rows".to_owned());
    }
    insert_postgres_admission_audit(
        &transaction,
        intake_id,
        &tenant_id,
        target_table,
        admitted_rows,
        rejected_rows,
        &actor,
    )
    .await?;
    insert_postgres_source_sync(
        &transaction,
        intake_id,
        &tenant_id,
        target_table,
        "admission",
        &actor,
        admitted_rows,
        rejected_rows,
        0,
    )
    .await?;
    let admitted_status = if rejected_rows == 0 {
        ArchiveIntakeStatus::Admitted
    } else {
        ArchiveIntakeStatus::Rejected
    };
    let admitted_status = admitted_status.as_postgres_value();
    transaction
        .execute(
            "UPDATE bitween_archive.archive_intake \
             SET status = $3, postgres_ready = false, next_action = 'none', \
                 admission_approved_by = $4, admission_approved_at = now() \
             WHERE tenant_id = $1 AND id = $2::text::uuid",
            &[&tenant_id, &intake_id, &admitted_status, &actor],
        )
        .await
        .map_err(|_| "archive_postgres_admission_status_update_failed".to_owned())?;
    transaction
        .commit()
        .await
        .map_err(|_| "archive_postgres_commit_failed".to_owned())?;
    Ok(())
}

async fn admit_postgres_hr_employee_staging(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
    legal_entity_id: &str,
    workplace_id: &str,
    actor: &str,
) -> Result<i32, String> {
    let admitted = transaction
        .query_one(
            "WITH admissible_rows AS ( \
                SELECT id, \
                  'employee-' || lower(regexp_replace( \
                    COALESCE(NULLIF(employee_external_id, ''), substring(row_hash from 1 for 16)), \
                    '[^a-zA-Z0-9_-]+', '-', 'g' \
                  )) AS employee_key, \
                  display_name, department, COALESCE(NULLIF(employment_status, ''), 'active') AS employment_status, \
                  row_hash, row_payload \
                FROM bitween_archive.hr_employee_staging \
                WHERE tenant_id = $1 \
                  AND intake_id = $2::text::uuid \
                  AND validation_status IN ('pending_review', 'valid') \
                  AND NULLIF(display_name, '') IS NOT NULL \
                  AND NULLIF(department, '') IS NOT NULL \
             ), existing_rows AS ( \
                SELECT a.employee_key, e.employee_key IS NOT NULL AS before_exists, \
                  COALESCE(jsonb_build_object( \
                    'display_name', e.display_name, 'team', e.team, 'role_title', e.role_title, \
                    'employment_status', e.employment_status, 'source_intake_id', e.source_intake_id, \
                    'source_row_hash', e.source_row_hash, 'source_payload', e.source_payload, \
                    'admission_status', e.admission_status \
                  ), '{}'::jsonb) AS before_payload, \
                  jsonb_build_object( \
                    'display_name', a.display_name, 'team', a.department, 'role_title', 'Employee', \
                    'employment_status', CASE WHEN a.employment_status IN ('active', 'on_leave', 'offboarding') THEN a.employment_status ELSE 'active' END, \
                    'source_intake_id', $2::text::uuid, 'source_row_hash', a.row_hash, 'source_payload', a.row_payload, \
                    'admission_status', 'admitted' \
                  ) AS after_payload \
                FROM admissible_rows a \
                LEFT JOIN bitween_hr.employee e \
                  ON e.tenant_id = $1 AND e.legal_entity_id = $3 AND e.workplace_id = $4 \
                  AND e.employee_key = a.employee_key \
             ), recovery_points AS ( \
                INSERT INTO bitween_archive.archive_admission_recovery_point ( \
                    intake_id, tenant_id, target_table, business_key, action, before_exists, before_payload, after_payload, captured_by \
                ) \
                SELECT $2::text::uuid, $1, 'hr_employee', employee_key, \
                       CASE WHEN before_exists THEN 'replace' ELSE 'insert' END, \
                       before_exists, before_payload, after_payload, $5 \
                FROM existing_rows \
                ON CONFLICT (tenant_id, intake_id, target_table, business_key) DO UPDATE \
                  SET action = EXCLUDED.action, before_exists = EXCLUDED.before_exists, \
                      before_payload = EXCLUDED.before_payload, after_payload = EXCLUDED.after_payload, \
                      recovery_status = 'available', captured_by = EXCLUDED.captured_by, captured_at = now() \
                RETURNING business_key \
             ), upserted AS ( \
                INSERT INTO bitween_hr.employee ( \
                    tenant_id, legal_entity_id, workplace_id, employee_key, display_name, team, \
                    role_title, employment_status, source_intake_id, source_row_hash, source_payload, \
                    admission_status, created_by, updated_by \
                ) \
                SELECT $1, $3, $4, employee_key, display_name, department, 'Employee', \
                       CASE WHEN employment_status IN ('active', 'on_leave', 'offboarding') THEN employment_status ELSE 'active' END, \
                       $2::text::uuid, row_hash, row_payload, 'admitted', \
                       $5, $5 \
                FROM admissible_rows \
                ON CONFLICT (tenant_id, legal_entity_id, workplace_id, employee_key) DO UPDATE \
                  SET display_name = EXCLUDED.display_name, team = EXCLUDED.team, \
                      role_title = EXCLUDED.role_title, employment_status = EXCLUDED.employment_status, \
                      source_intake_id = EXCLUDED.source_intake_id, source_row_hash = EXCLUDED.source_row_hash, \
                      source_payload = EXCLUDED.source_payload, admission_status = 'replaced', \
                      updated_by = EXCLUDED.updated_by \
                RETURNING employee_key \
             ), marked AS ( \
                UPDATE bitween_archive.hr_employee_staging \
                SET validation_status = 'admitted' \
                WHERE id IN ( \
                    SELECT id FROM admissible_rows \
                    WHERE employee_key IN (SELECT employee_key FROM upserted) \
                ) \
                RETURNING id \
             ) \
             SELECT COUNT(*)::int FROM marked",
            &[&tenant_id, &intake_id, &legal_entity_id, &workplace_id, &actor],
        )
        .await
        .map_err(|_| "archive_postgres_hr_employee_admission_failed".to_owned())?;
    Ok(admitted.get(0))
}

async fn reject_invalid_hr_employee_staging(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
) -> Result<i32, String> {
    let issues_json = "[{\"code\":\"missing_required_hr_employee_field\"}]";
    let rejected = transaction
        .execute(
            "UPDATE bitween_archive.hr_employee_staging \
             SET validation_status = 'invalid', issues = $3::text::jsonb \
             WHERE tenant_id = $1 \
               AND intake_id = $2::text::uuid \
               AND validation_status IN ('pending_review', 'valid') \
               AND (NULLIF(display_name, '') IS NULL OR NULLIF(department, '') IS NULL)",
            &[&tenant_id, &intake_id, &issues_json],
        )
        .await
        .map_err(|_| "archive_postgres_hr_employee_invalid_mark_failed".to_owned())?;
    i32::try_from(rejected).map_err(|_| "archive_postgres_rejected_count_out_of_range".to_owned())
}

async fn reject_unadmitted_hr_employee_staging(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
) -> Result<i32, String> {
    let issues_json = "[{\"code\":\"duplicate_hr_employee_requires_review\"}]";
    let rejected = transaction
        .execute(
            "UPDATE bitween_archive.hr_employee_staging \
             SET validation_status = 'invalid', issues = $3::text::jsonb \
             WHERE tenant_id = $1 \
               AND intake_id = $2::text::uuid \
               AND validation_status IN ('pending_review', 'valid')",
            &[&tenant_id, &intake_id, &issues_json],
        )
        .await
        .map_err(|_| "archive_postgres_hr_employee_unadmitted_mark_failed".to_owned())?;
    i32::try_from(rejected).map_err(|_| "archive_postgres_rejected_count_out_of_range".to_owned())
}

async fn admit_postgres_hr_attendance_staging(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
    legal_entity_id: &str,
    workplace_id: &str,
    actor: &str,
) -> Result<i32, String> {
    let admitted = transaction
        .query_one(
            "WITH admissible_rows AS ( \
                SELECT id, \
                  'employee-' || lower(regexp_replace( \
                    employee_external_id, '[^a-zA-Z0-9_-]+', '-', 'g' \
                  )) AS employee_key, \
                  work_date, row_hash, row_payload, \
                  'employee-' || lower(regexp_replace(employee_external_id, '[^a-zA-Z0-9_-]+', '-', 'g')) || '|' || work_date::text AS business_key \
                FROM bitween_archive.hr_attendance_staging \
                WHERE tenant_id = $1 \
                  AND intake_id = $2::text::uuid \
                  AND validation_status IN ('pending_review', 'valid') \
                  AND NULLIF(employee_external_id, '') IS NOT NULL \
                  AND work_date IS NOT NULL \
             ), existing_rows AS ( \
                SELECT a.business_key, e.employee_key IS NOT NULL AS before_exists, \
                  COALESCE(jsonb_build_object( \
                    'employee_key', e.employee_key, 'work_date', e.work_date, \
                    'source_intake_id', e.source_intake_id, 'source_row_hash', e.source_row_hash, \
                    'source_payload', e.source_payload, 'admission_status', e.admission_status \
                  ), '{}'::jsonb) AS before_payload, \
                  jsonb_build_object( \
                    'employee_key', a.employee_key, 'work_date', a.work_date, \
                    'source_intake_id', $2::text::uuid, 'source_row_hash', a.row_hash, \
                    'source_payload', a.row_payload, 'admission_status', 'admitted' \
                  ) AS after_payload \
                FROM admissible_rows a \
                LEFT JOIN bitween_hr.attendance_record e \
                  ON e.tenant_id = $1 AND e.legal_entity_id = $3 AND e.workplace_id = $4 \
                 AND e.employee_key = a.employee_key AND e.work_date = a.work_date \
             ), recovery_points AS ( \
                INSERT INTO bitween_archive.archive_admission_recovery_point ( \
                    intake_id, tenant_id, target_table, business_key, action, before_exists, before_payload, after_payload, captured_by \
                ) \
                SELECT $2::text::uuid, $1, 'hr_attendance', business_key, \
                       CASE WHEN before_exists THEN 'replace' ELSE 'insert' END, \
                       before_exists, before_payload, after_payload, $5 \
                FROM existing_rows \
                ON CONFLICT (tenant_id, intake_id, target_table, business_key) DO UPDATE \
                  SET action = EXCLUDED.action, before_exists = EXCLUDED.before_exists, \
                      before_payload = EXCLUDED.before_payload, after_payload = EXCLUDED.after_payload, \
                      recovery_status = 'available', captured_by = EXCLUDED.captured_by, captured_at = now() \
                RETURNING business_key \
             ), upserted AS ( \
                INSERT INTO bitween_hr.attendance_record ( \
                    tenant_id, legal_entity_id, workplace_id, employee_key, work_date, \
                    source_intake_id, source_row_hash, source_payload, created_by, updated_by \
                ) \
                SELECT $1, $3, $4, employee_key, work_date, $2::text::uuid, row_hash, row_payload, $5, $5 \
                FROM admissible_rows \
                ON CONFLICT (tenant_id, legal_entity_id, workplace_id, employee_key, work_date) DO UPDATE \
                  SET source_intake_id = EXCLUDED.source_intake_id, source_row_hash = EXCLUDED.source_row_hash, \
                      source_payload = EXCLUDED.source_payload, admission_status = 'replaced', updated_by = EXCLUDED.updated_by \
                RETURNING employee_key, work_date \
             ), marked AS ( \
                UPDATE bitween_archive.hr_attendance_staging \
                SET validation_status = 'admitted' \
                WHERE id IN ( \
                    SELECT id FROM admissible_rows \
                    WHERE (employee_key, work_date) IN (SELECT employee_key, work_date FROM upserted) \
                ) \
                RETURNING id \
             ) \
             SELECT COUNT(*)::int FROM marked",
            &[&tenant_id, &intake_id, &legal_entity_id, &workplace_id, &actor],
        )
        .await
        .map_err(|_| "archive_postgres_hr_attendance_admission_failed".to_owned())?;
    Ok(admitted.get(0))
}

async fn reject_invalid_hr_attendance_staging(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
) -> Result<i32, String> {
    let issues_json = "[{\"code\":\"missing_required_hr_attendance_field\"}]";
    let rejected = transaction
        .execute(
            "UPDATE bitween_archive.hr_attendance_staging \
             SET validation_status = 'invalid', issues = $3::text::jsonb \
             WHERE tenant_id = $1 \
               AND intake_id = $2::text::uuid \
               AND validation_status IN ('pending_review', 'valid') \
               AND (NULLIF(employee_external_id, '') IS NULL OR work_date IS NULL)",
            &[&tenant_id, &intake_id, &issues_json],
        )
        .await
        .map_err(|_| "archive_postgres_hr_attendance_invalid_mark_failed".to_owned())?;
    i32::try_from(rejected).map_err(|_| "archive_postgres_rejected_count_out_of_range".to_owned())
}

async fn reject_unadmitted_hr_attendance_staging(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
) -> Result<i32, String> {
    let issues_json = "[{\"code\":\"duplicate_hr_attendance_requires_review\"}]";
    let rejected = transaction
        .execute(
            "UPDATE bitween_archive.hr_attendance_staging \
             SET validation_status = 'invalid', issues = $3::text::jsonb \
             WHERE tenant_id = $1 \
               AND intake_id = $2::text::uuid \
               AND validation_status IN ('pending_review', 'valid')",
            &[&tenant_id, &intake_id, &issues_json],
        )
        .await
        .map_err(|_| "archive_postgres_hr_attendance_unadmitted_mark_failed".to_owned())?;
    i32::try_from(rejected).map_err(|_| "archive_postgres_rejected_count_out_of_range".to_owned())
}

#[allow(clippy::too_many_arguments)]
async fn admit_postgres_payroll_input_staging(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
    legal_entity_id: &str,
    workplace_id: &str,
    payroll_period: &str,
    actor: &str,
) -> Result<i32, String> {
    let admitted = transaction
        .query_one(
            "WITH admissible_rows AS ( \
                SELECT id, \
                  'employee-' || lower(regexp_replace( \
                    employee_external_id, '[^a-zA-Z0-9_-]+', '-', 'g' \
                  )) AS employee_key, \
                  gross_pay, COALESCE(deduction_total, 0) AS deduction_total, row_hash, row_payload, \
                  $5 || '|' || 'employee-' || lower(regexp_replace(employee_external_id, '[^a-zA-Z0-9_-]+', '-', 'g')) AS business_key \
                FROM bitween_archive.payroll_input_staging \
                WHERE tenant_id = $1 \
                  AND intake_id = $2::text::uuid \
                  AND validation_status IN ('pending_review', 'valid') \
                  AND NULLIF(employee_external_id, '') IS NOT NULL \
                  AND gross_pay IS NOT NULL \
             ), existing_rows AS ( \
                SELECT a.business_key, p.employee_key IS NOT NULL AS before_exists, \
                  COALESCE(jsonb_build_object( \
                    'payroll_period', p.payroll_period, 'employee_key', p.employee_key, \
                    'gross_pay', p.gross_pay, 'deduction_total', p.deduction_total, \
                    'source_intake_id', p.source_intake_id, 'source_row_hash', p.source_row_hash, \
                    'source_payload', p.source_payload, 'admission_status', p.admission_status \
                  ), '{}'::jsonb) AS before_payload, \
                  jsonb_build_object( \
                    'payroll_period', $5, 'employee_key', a.employee_key, \
                    'gross_pay', a.gross_pay, 'deduction_total', a.deduction_total, \
                    'source_intake_id', $2::text::uuid, 'source_row_hash', a.row_hash, \
                    'source_payload', a.row_payload, 'admission_status', 'admitted' \
                  ) AS after_payload \
                FROM admissible_rows a \
                LEFT JOIN bitween_payroll.payroll_input p \
                  ON p.tenant_id = $1 AND p.legal_entity_id = $3 AND p.workplace_id = $4 \
                 AND p.payroll_period = $5 AND p.employee_key = a.employee_key \
             ), recovery_points AS ( \
                INSERT INTO bitween_archive.archive_admission_recovery_point ( \
                    intake_id, tenant_id, target_table, business_key, action, before_exists, before_payload, after_payload, captured_by \
                ) \
                SELECT $2::text::uuid, $1, 'payroll_input', business_key, \
                       CASE WHEN before_exists THEN 'replace' ELSE 'insert' END, \
                       before_exists, before_payload, after_payload, $6 \
                FROM existing_rows \
                ON CONFLICT (tenant_id, intake_id, target_table, business_key) DO UPDATE \
                  SET action = EXCLUDED.action, before_exists = EXCLUDED.before_exists, \
                      before_payload = EXCLUDED.before_payload, after_payload = EXCLUDED.after_payload, \
                      recovery_status = 'available', captured_by = EXCLUDED.captured_by, captured_at = now() \
                RETURNING business_key \
             ), upserted AS ( \
                INSERT INTO bitween_payroll.payroll_input ( \
                    tenant_id, legal_entity_id, workplace_id, payroll_period, employee_key, \
                    gross_pay, deduction_total, source_intake_id, source_row_hash, source_payload, created_by, updated_by \
                ) \
                SELECT $1, $3, $4, $5, employee_key, gross_pay, deduction_total, $2::text::uuid, row_hash, row_payload, $6, $6 \
                FROM admissible_rows \
                ON CONFLICT (tenant_id, legal_entity_id, workplace_id, payroll_period, employee_key) DO UPDATE \
                  SET gross_pay = EXCLUDED.gross_pay, deduction_total = EXCLUDED.deduction_total, \
                      source_intake_id = EXCLUDED.source_intake_id, source_row_hash = EXCLUDED.source_row_hash, \
                      source_payload = EXCLUDED.source_payload, admission_status = 'replaced', updated_by = EXCLUDED.updated_by \
                RETURNING employee_key \
             ), marked AS ( \
                UPDATE bitween_archive.payroll_input_staging \
                SET validation_status = 'admitted' \
                WHERE id IN ( \
                    SELECT id FROM admissible_rows \
                    WHERE employee_key IN (SELECT employee_key FROM upserted) \
                ) \
                RETURNING id \
             ) \
             SELECT COUNT(*)::int FROM marked",
            &[
                &tenant_id,
                &intake_id,
                &legal_entity_id,
                &workplace_id,
                &payroll_period,
                &actor,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_payroll_input_admission_failed".to_owned())?;
    Ok(admitted.get(0))
}

async fn reject_invalid_payroll_input_staging(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
) -> Result<i32, String> {
    let issues_json = "[{\"code\":\"missing_required_payroll_input_field\"}]";
    let rejected = transaction
        .execute(
            "UPDATE bitween_archive.payroll_input_staging \
             SET validation_status = 'invalid', issues = $3::text::jsonb \
             WHERE tenant_id = $1 \
               AND intake_id = $2::text::uuid \
               AND validation_status IN ('pending_review', 'valid') \
               AND (NULLIF(employee_external_id, '') IS NULL OR gross_pay IS NULL)",
            &[&tenant_id, &intake_id, &issues_json],
        )
        .await
        .map_err(|_| "archive_postgres_payroll_input_invalid_mark_failed".to_owned())?;
    i32::try_from(rejected).map_err(|_| "archive_postgres_rejected_count_out_of_range".to_owned())
}

async fn reject_unadmitted_payroll_input_staging(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
) -> Result<i32, String> {
    let issues_json = "[{\"code\":\"duplicate_payroll_input_requires_review\"}]";
    let rejected = transaction
        .execute(
            "UPDATE bitween_archive.payroll_input_staging \
             SET validation_status = 'invalid', issues = $3::text::jsonb \
             WHERE tenant_id = $1 \
               AND intake_id = $2::text::uuid \
               AND validation_status IN ('pending_review', 'valid')",
            &[&tenant_id, &intake_id, &issues_json],
        )
        .await
        .map_err(|_| "archive_postgres_payroll_input_unadmitted_mark_failed".to_owned())?;
    i32::try_from(rejected).map_err(|_| "archive_postgres_rejected_count_out_of_range".to_owned())
}

async fn insert_postgres_admission_audit(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
    target_table: &str,
    admitted_rows: i32,
    rejected_rows: i32,
    actor: &str,
) -> Result<(), String> {
    let evidence = ArchiveAdmissionEvidence {
        source: "archive_intake_store",
        target_table: target_table.to_owned(),
        admitted_rows,
        rejected_rows,
    };
    let evidence_json = serde_json::to_string(&evidence)
        .map_err(|_| "archive_postgres_admission_evidence_encode_failed".to_owned())?;
    let rollback_json = match target_table {
        "hr_employee" => "{\"strategy\":\"targeted_employee_upsert_audit\"}",
        "hr_attendance" => "{\"strategy\":\"targeted_attendance_reversal_audit\"}",
        "payroll_input" => "{\"strategy\":\"targeted_payroll_input_reversal_audit\"}",
        _ => "{\"strategy\":\"targeted_admission_audit\"}",
    };
    transaction
        .execute(
            "INSERT INTO bitween_archive.archive_admission_audit ( \
                intake_id, tenant_id, target_table, admitted_rows, rejected_rows, approved_by, rollback_ref, evidence \
             ) VALUES ($1::text::uuid, $2, $3, $4, $5, $6, $7::text::jsonb, $8::text::jsonb)",
            &[
                &intake_id,
                &tenant_id,
                &target_table,
                &admitted_rows,
                &rejected_rows,
                &actor,
                &rollback_json,
                &evidence_json,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_admission_audit_insert_failed".to_owned())?;
    Ok(())
}

#[allow(clippy::too_many_arguments)]
async fn insert_postgres_source_sync(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
    target_table: &str,
    operation: &str,
    actor: &str,
    admitted_rows: i32,
    rejected_rows: i32,
    reversed_rows: i32,
) -> Result<(), String> {
    let change_payload = serde_json::json!({
        "source": "archive_intake_store",
        "target_table": target_table,
        "admitted_rows": admitted_rows,
        "rejected_rows": rejected_rows,
        "reversed_rows": reversed_rows,
        "binary_snapshot_stored": false,
        "postgres_payload": "row_delta_json",
        "workbook_strategy": "immutable_original_plus_derived_rustfs_version"
    });
    let change_payload_json = serde_json::to_string(&change_payload)
        .map_err(|_| "archive_postgres_source_sync_payload_encode_failed".to_owned())?;
    transaction
        .execute(
            "INSERT INTO bitween_archive.archive_source_sync ( \
                intake_id, tenant_id, source_version, target_table, operation, status, \
                source_object_uri, change_payload, requested_by \
             ) \
             SELECT id, tenant_id, version, $3, $4, 'pending', object_uri, $5::text::jsonb, $6 \
             FROM bitween_archive.archive_intake \
             WHERE tenant_id = $1 AND id = $2::text::uuid",
            &[
                &tenant_id,
                &intake_id,
                &target_table,
                &operation,
                &change_payload_json,
                &actor,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_source_sync_insert_failed".to_owned())?;
    Ok(())
}

async fn complete_postgres_source_sync(
    session: &mut PostgresClientSession,
    input: ArchiveSourceSyncCompletionInput,
) -> Result<(), String> {
    let tenant_id = session.scope.tenant_id.clone();
    let actor = postgres_actor();
    let sync_item_id = input
        .sync_item_id
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "missing required intake field: sync_item_id".to_owned())?
        .to_owned();
    let transaction = session
        .client
        .transaction()
        .await
        .map_err(|_| "archive_postgres_transaction_failed".to_owned())?;
    let row = transaction
        .query_opt(
            "SELECT intake_id::text, source_version, target_table, operation, source_object_uri, \
                    change_payload::text, requested_by \
             FROM bitween_archive.archive_source_sync \
             WHERE tenant_id = $1 AND id = $2::text::uuid AND status = 'pending' \
             FOR UPDATE",
            &[&tenant_id, &sync_item_id],
        )
        .await
        .map_err(|_| "archive_postgres_source_sync_complete_lookup_failed".to_owned())?
        .ok_or_else(|| "archive_postgres_source_sync_not_pending".to_owned())?;
    let pending = ArchiveSourceSyncPendingRow {
        sync_item_id,
        intake_id: row.get(0),
        source_version: row.get(1),
        target_table: row.get(2),
        operation: row.get(3),
        source_object_uri: row.get(4),
        change_payload: parse_json_value(row.get::<usize, String>(5).as_str())?,
        workbook_rows: Vec::new(),
        created_by: row.get(6),
    };
    let completion = validate_source_sync_completion_for_pending(input, &pending, &source_sync_bucket()?)?;
    let file_size_bytes = completion.file_size_bytes;
    let metadata_json = serde_json::json!({
        "generated_content_sha256": completion.content_sha256,
        "generated_file_size_bytes": file_size_bytes,
        "generated_by": actor,
        "binary_snapshot_stored": false,
        "object_store": "rustfs"
    })
    .to_string();
    let updated = transaction
        .execute(
            "UPDATE bitween_archive.archive_source_sync \
             SET status = 'synced', generated_object_uri = $3, synced_at = now(), \
                 change_payload = change_payload || $4::text::jsonb \
             WHERE tenant_id = $1 AND id = $2::text::uuid AND status = 'pending'",
            &[
                &tenant_id,
                &completion.sync_item_id,
                &completion.generated_object_uri,
                &metadata_json,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_source_sync_complete_failed".to_owned())?;
    if updated == 0 {
        return Err("archive_postgres_source_sync_not_pending".to_owned());
    }
    transaction
        .commit()
        .await
        .map_err(|_| "archive_postgres_commit_failed".to_owned())?;
    Ok(())
}

async fn fail_postgres_source_sync(
    session: &mut PostgresClientSession,
    input: ArchiveSourceSyncFailureInput,
) -> Result<(), String> {
    let failure = validate_source_sync_failure(input)?;
    let tenant_id = session.scope.tenant_id.clone();
    let metadata_json = serde_json::json!({
        "last_error": failure.error,
        "binary_snapshot_stored": false,
        "object_store": "rustfs"
    })
    .to_string();
    let updated = session
        .client
        .execute(
            "UPDATE bitween_archive.archive_source_sync \
             SET status = 'failed', change_payload = change_payload || $3::text::jsonb \
             WHERE tenant_id = $1 AND id = $2::text::uuid AND status = 'pending'",
            &[&tenant_id, &failure.sync_item_id, &metadata_json],
        )
        .await
        .map_err(|_| "archive_postgres_source_sync_fail_failed".to_owned())?;
    if updated == 0 {
        return Err("archive_postgres_source_sync_not_pending".to_owned());
    }
    Ok(())
}

fn validate_source_sync_completion(
    input: ArchiveSourceSyncCompletionInput,
) -> Result<ArchiveSourceSyncCompletion, String> {
    let sync_item_id = required_field(input.sync_item_id, "sync_item_id")?;
    let generated_object_uri = required_field(input.generated_object_uri, "generated_object_uri")?;
    if !generated_object_uri.starts_with("rustfs://") {
        return Err("archive_source_sync_generated_object_uri_must_be_rustfs".to_owned());
    }
    let content_sha256 = required_field(input.content_sha256, "content_sha256")?;
    if !is_sha256_hex(&content_sha256) {
        return Err("archive_source_sync_generated_checksum_invalid".to_owned());
    }
    let file_size_bytes = input
        .file_size_bytes
        .ok_or_else(|| "missing required intake field: file_size_bytes".to_owned())?;
    if file_size_bytes == 0 || file_size_bytes > MAX_FILE_BYTES {
        return Err("archive_source_sync_generated_file_size_invalid".to_owned());
    }
    Ok(ArchiveSourceSyncCompletion {
        sync_item_id,
        generated_object_uri,
        content_sha256,
        file_size_bytes: i64::try_from(file_size_bytes)
            .map_err(|_| "archive_source_sync_generated_file_size_invalid".to_owned())?,
    })
}

fn validate_source_sync_completion_for_pending(
    input: ArchiveSourceSyncCompletionInput,
    pending: &ArchiveSourceSyncPendingRow,
    bucket: &str,
) -> Result<ArchiveSourceSyncCompletion, String> {
    let completion = validate_source_sync_completion(input)?;
    let expected_uri = format!(
        "rustfs://{}/{}",
        bucket,
        source_sync_object_key(pending)
    );
    if completion.generated_object_uri != expected_uri {
        return Err("archive_source_sync_generated_object_uri_mismatch".to_owned());
    }
    Ok(completion)
}

fn validate_source_sync_failure(
    input: ArchiveSourceSyncFailureInput,
) -> Result<ArchiveSourceSyncFailure, String> {
    let sync_item_id = required_field(input.sync_item_id, "sync_item_id")?;
    let error = required_field(input.error, "error")?;
    Ok(ArchiveSourceSyncFailure {
        sync_item_id,
        error: bounded_note(error),
    })
}

fn is_sha256_hex(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|byte| byte.is_ascii_hexdigit())
}

async fn rollback_postgres_intake(
    session: &mut PostgresClientSession,
    intake_id: &str,
    input: ArchiveRollbackInput,
) -> Result<(), String> {
    let tenant_id = session.scope.tenant_id.clone();
    let legal_entity_id = session.scope.legal_entity_id.clone();
    let workplace_id = session.scope.workplace_id.clone();
    let actor = postgres_actor();
    let recovery_point_id = rollback_recovery_point_id(&input);
    let reason = rollback_reason(input);
    let transaction = session
        .client
        .transaction()
        .await
        .map_err(|_| "archive_postgres_transaction_failed".to_owned())?;
    let intake = transaction
        .query_opt(
            "SELECT database_target, status \
             FROM bitween_archive.archive_intake \
             WHERE tenant_id = $1 AND id = $2::text::uuid \
             FOR UPDATE",
            &[&tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_rollback_lookup_failed".to_owned())?
        .ok_or_else(|| "archive_intake_not_found".to_owned())?;
    let database_target: String = intake.get(0);
    let status: String = intake.get(1);
    if status != "admitted" && status != "rejected" {
        return Err("archive_postgres_rollback_requires_completed_admission".to_owned());
    }

    let target = DatabaseTarget::from_postgres_value(&database_target)?;
    let (target_table, reversed_rows) = match target {
        DatabaseTarget::HrEmployeeStaging => {
            let rows = reverse_postgres_hr_employee_admission(
                &transaction,
                intake_id,
                &tenant_id,
                &legal_entity_id,
                &workplace_id,
                &actor,
                &recovery_point_id,
            )
            .await?;
            reset_postgres_hr_employee_staging_after_rollback(&transaction, intake_id, &tenant_id)
                .await?;
            ("hr_employee", rows)
        }
        DatabaseTarget::HrAttendanceStaging => {
            let rows = reverse_postgres_hr_attendance_admission(
                &transaction,
                intake_id,
                &tenant_id,
                &legal_entity_id,
                &workplace_id,
                &actor,
                &recovery_point_id,
            )
            .await?;
            reset_postgres_hr_attendance_staging_after_rollback(&transaction, intake_id, &tenant_id)
                .await?;
            ("hr_attendance", rows)
        }
        DatabaseTarget::PayrollInputStaging => {
            let rows = reverse_postgres_payroll_input_admission(
                &transaction,
                intake_id,
                &tenant_id,
                &legal_entity_id,
                &workplace_id,
                &actor,
                &recovery_point_id,
            )
            .await?;
            reset_postgres_payroll_input_staging_after_rollback(&transaction, intake_id, &tenant_id)
                .await?;
            ("payroll_input", rows)
        }
        DatabaseTarget::ArchiveBlob | DatabaseTarget::NeedsMapping => {
            return Err("archive_postgres_rollback_target_unsupported".to_owned());
        }
    };
    if reversed_rows == 0 {
        return Err("archive_postgres_no_reversible_rows".to_owned());
    }
    insert_postgres_rollback_audit(
        &transaction,
        intake_id,
        &tenant_id,
        target_table,
        reversed_rows,
        &actor,
        &reason,
        &recovery_point_id,
    )
    .await?;
    insert_postgres_source_sync(
        &transaction,
        intake_id,
        &tenant_id,
        target_table,
        "rollback",
        &actor,
        0,
        0,
        reversed_rows,
    )
    .await?;
    transaction
        .execute(
            "UPDATE bitween_archive.archive_intake \
             SET status = 'ready_for_staging', postgres_ready = true, next_action = 'save_to_business_data', \
                 admission_approved_by = NULL, admission_approved_at = NULL \
             WHERE tenant_id = $1 AND id = $2::text::uuid",
            &[&tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_rollback_status_update_failed".to_owned())?;
    transaction
        .commit()
        .await
        .map_err(|_| "archive_postgres_commit_failed".to_owned())?;
    Ok(())
}

async fn reverse_postgres_hr_employee_admission(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
    legal_entity_id: &str,
    workplace_id: &str,
    actor: &str,
    recovery_point_id: &str,
) -> Result<i32, String> {
    let reversed = transaction
        .query_one(
            "WITH available AS ( \
                SELECT id, business_key, action, before_payload \
                FROM bitween_archive.archive_admission_recovery_point \
                WHERE tenant_id = $1 AND intake_id = $2::text::uuid AND target_table = 'hr_employee' \
                  AND recovery_status = 'available' \
                  AND ($6 = '' OR id = NULLIF($6, '')::uuid) \
             ), restored AS ( \
                UPDATE bitween_hr.employee e \
                SET display_name = a.before_payload->>'display_name', \
                    team = a.before_payload->>'team', \
                    role_title = a.before_payload->>'role_title', \
                    employment_status = a.before_payload->>'employment_status', \
                    source_intake_id = NULLIF(a.before_payload->>'source_intake_id', '')::uuid, \
                    source_row_hash = NULLIF(a.before_payload->>'source_row_hash', ''), \
                    source_payload = COALESCE(a.before_payload->'source_payload', '{}'::jsonb), \
                    admission_status = COALESCE(NULLIF(a.before_payload->>'admission_status', ''), 'admitted'), \
                    updated_by = $5 \
                FROM available a \
                WHERE a.action = 'replace' \
                  AND e.tenant_id = $1 AND e.legal_entity_id = $3 AND e.workplace_id = $4 \
                  AND e.employee_key = a.business_key \
                RETURNING a.id \
             ), reversed AS ( \
                UPDATE bitween_hr.employee e \
                SET admission_status = 'reversed', updated_by = $5 \
                FROM available a \
                WHERE a.action = 'insert' \
                  AND e.tenant_id = $1 AND e.legal_entity_id = $3 AND e.workplace_id = $4 \
                  AND e.employee_key = a.business_key \
                  AND e.admission_status <> 'reversed' \
                RETURNING a.id \
             ), touched AS ( \
                SELECT id FROM restored UNION SELECT id FROM reversed \
             ), marked AS ( \
                UPDATE bitween_archive.archive_admission_recovery_point s \
                SET recovery_status = 'restored' \
                WHERE s.id IN (SELECT id FROM touched) \
                RETURNING id \
             ) \
             SELECT COUNT(*)::int FROM marked",
            &[
                &tenant_id,
                &intake_id,
                &legal_entity_id,
                &workplace_id,
                &actor,
                &recovery_point_id,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_hr_employee_rollback_failed".to_owned())?;
    Ok(reversed.get(0))
}

async fn reverse_postgres_hr_attendance_admission(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
    legal_entity_id: &str,
    workplace_id: &str,
    actor: &str,
    recovery_point_id: &str,
) -> Result<i32, String> {
    let reversed = transaction
        .query_one(
            "WITH available AS ( \
                SELECT id, business_key, action, before_payload \
                FROM bitween_archive.archive_admission_recovery_point \
                WHERE tenant_id = $1 AND intake_id = $2::text::uuid AND target_table = 'hr_attendance' \
                  AND recovery_status = 'available' \
                  AND ($6 = '' OR id = NULLIF($6, '')::uuid) \
             ), restored AS ( \
                UPDATE bitween_hr.attendance_record r \
                SET source_intake_id = NULLIF(a.before_payload->>'source_intake_id', '')::uuid, \
                    source_row_hash = NULLIF(a.before_payload->>'source_row_hash', ''), \
                    source_payload = COALESCE(a.before_payload->'source_payload', '{}'::jsonb), \
                    admission_status = COALESCE(NULLIF(a.before_payload->>'admission_status', ''), 'admitted'), \
                    updated_by = $5 \
                FROM available a \
                WHERE a.action = 'replace' \
                  AND r.tenant_id = $1 AND r.legal_entity_id = $3 AND r.workplace_id = $4 \
                  AND (r.employee_key || '|' || r.work_date::text) = a.business_key \
                RETURNING a.id \
             ), reversed AS ( \
                UPDATE bitween_hr.attendance_record r \
                SET admission_status = 'reversed', updated_by = $5 \
                FROM available a \
                WHERE a.action = 'insert' \
                  AND r.tenant_id = $1 AND r.legal_entity_id = $3 AND r.workplace_id = $4 \
                  AND (r.employee_key || '|' || r.work_date::text) = a.business_key \
                  AND r.admission_status <> 'reversed' \
                RETURNING a.id \
             ), touched AS ( \
                SELECT id FROM restored UNION SELECT id FROM reversed \
             ), marked AS ( \
                UPDATE bitween_archive.archive_admission_recovery_point s \
                SET recovery_status = 'restored' \
                WHERE s.id IN (SELECT id FROM touched) \
                RETURNING id \
             ) \
             SELECT COUNT(*)::int FROM marked",
            &[
                &tenant_id,
                &intake_id,
                &legal_entity_id,
                &workplace_id,
                &actor,
                &recovery_point_id,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_hr_attendance_rollback_failed".to_owned())?;
    Ok(reversed.get(0))
}

async fn reverse_postgres_payroll_input_admission(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
    legal_entity_id: &str,
    workplace_id: &str,
    actor: &str,
    recovery_point_id: &str,
) -> Result<i32, String> {
    let reversed = transaction
        .query_one(
            "WITH available AS ( \
                SELECT id, business_key, action, before_payload \
                FROM bitween_archive.archive_admission_recovery_point \
                WHERE tenant_id = $1 AND intake_id = $2::text::uuid AND target_table = 'payroll_input' \
                  AND recovery_status = 'available' \
                  AND ($6 = '' OR id = NULLIF($6, '')::uuid) \
             ), restored AS ( \
                UPDATE bitween_payroll.payroll_input p \
                SET gross_pay = (a.before_payload->>'gross_pay')::numeric, \
                    deduction_total = (a.before_payload->>'deduction_total')::numeric, \
                    source_intake_id = NULLIF(a.before_payload->>'source_intake_id', '')::uuid, \
                    source_row_hash = NULLIF(a.before_payload->>'source_row_hash', ''), \
                    source_payload = COALESCE(a.before_payload->'source_payload', '{}'::jsonb), \
                    admission_status = COALESCE(NULLIF(a.before_payload->>'admission_status', ''), 'admitted'), \
                    updated_by = $5 \
                FROM available a \
                WHERE a.action = 'replace' \
                  AND p.tenant_id = $1 AND p.legal_entity_id = $3 AND p.workplace_id = $4 \
                  AND (p.payroll_period || '|' || p.employee_key) = a.business_key \
                RETURNING a.id \
             ), reversed AS ( \
                UPDATE bitween_payroll.payroll_input p \
                SET admission_status = 'reversed', updated_by = $5 \
                FROM available a \
                WHERE a.action = 'insert' \
                  AND p.tenant_id = $1 AND p.legal_entity_id = $3 AND p.workplace_id = $4 \
                  AND (p.payroll_period || '|' || p.employee_key) = a.business_key \
                  AND p.admission_status <> 'reversed' \
                RETURNING a.id \
             ), touched AS ( \
                SELECT id FROM restored UNION SELECT id FROM reversed \
             ), marked AS ( \
                UPDATE bitween_archive.archive_admission_recovery_point s \
                SET recovery_status = 'restored' \
                WHERE s.id IN (SELECT id FROM touched) \
                RETURNING id \
             ) \
             SELECT COUNT(*)::int FROM marked",
            &[
                &tenant_id,
                &intake_id,
                &legal_entity_id,
                &workplace_id,
                &actor,
                &recovery_point_id,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_payroll_input_rollback_failed".to_owned())?;
    Ok(reversed.get(0))
}

async fn reset_postgres_hr_employee_staging_after_rollback(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
) -> Result<(), String> {
    transaction
        .execute(
            "UPDATE bitween_archive.hr_employee_staging \
             SET validation_status = 'valid' \
             WHERE tenant_id = $1 AND intake_id = $2::text::uuid AND validation_status = 'admitted'",
            &[&tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_hr_employee_rollback_staging_reset_failed".to_owned())?;
    Ok(())
}

async fn reset_postgres_hr_attendance_staging_after_rollback(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
) -> Result<(), String> {
    transaction
        .execute(
            "UPDATE bitween_archive.hr_attendance_staging \
             SET validation_status = 'valid' \
             WHERE tenant_id = $1 AND intake_id = $2::text::uuid AND validation_status = 'admitted'",
            &[&tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_hr_attendance_rollback_staging_reset_failed".to_owned())?;
    Ok(())
}

async fn reset_postgres_payroll_input_staging_after_rollback(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
) -> Result<(), String> {
    transaction
        .execute(
            "UPDATE bitween_archive.payroll_input_staging \
             SET validation_status = 'valid' \
             WHERE tenant_id = $1 AND intake_id = $2::text::uuid AND validation_status = 'admitted'",
            &[&tenant_id, &intake_id],
        )
        .await
        .map_err(|_| "archive_postgres_payroll_input_rollback_staging_reset_failed".to_owned())?;
    Ok(())
}

async fn insert_postgres_rollback_audit(
    transaction: &tokio_postgres::Transaction<'_>,
    intake_id: &str,
    tenant_id: &str,
    target_table: &str,
    reversed_rows: i32,
    actor: &str,
    reason: &str,
    recovery_point_id: &str,
) -> Result<(), String> {
    let evidence = ArchiveRollbackEvidence {
        source: "archive_intake_store",
        target_table: target_table.to_owned(),
        reversed_rows,
        recovery_point_id: recovery_point_id.to_owned(),
    };
    let evidence_json = serde_json::to_string(&evidence)
        .map_err(|_| "archive_postgres_rollback_evidence_encode_failed".to_owned())?;
    transaction
        .execute(
            "INSERT INTO bitween_archive.archive_admission_rollback ( \
                intake_id, tenant_id, target_table, reversed_rows, requested_by, reason, evidence \
             ) VALUES ($1::text::uuid, $2, $3, $4, $5, $6, $7::text::jsonb)",
            &[
                &intake_id,
                &tenant_id,
                &target_table,
                &reversed_rows,
                &actor,
                &reason,
                &evidence_json,
            ],
        )
        .await
        .map_err(|_| "archive_postgres_rollback_audit_insert_failed".to_owned())?;
    Ok(())
}

#[allow(clippy::too_many_arguments)]
async fn insert_postgres_staging_rows(
    transaction: &tokio_postgres::Transaction<'_>,
    database_target: &DatabaseTarget,
    intake_id: &str,
    tenant_id: &str,
    legal_entity_id: &str,
    workplace_id: &str,
    payroll_period: Option<&str>,
    rows: &[StagedBusinessRow],
) -> Result<(), String> {
    for row in rows {
        match database_target {
            DatabaseTarget::HrEmployeeStaging => {
                transaction
                    .execute(
                        "INSERT INTO bitween_archive.hr_employee_staging ( \
                            intake_id, tenant_id, row_number, row_hash, employee_external_id, \
                            display_name, department, employment_status, row_payload \
                         ) VALUES ($1::text::uuid, $2, $3, $4, $5, $6, $7, $8, $9::text::jsonb)",
                        &[
                            &intake_id,
                            &tenant_id,
                            &row.row_number,
                            &row.row_hash,
                            &row.employee_external_id,
                            &row.display_name,
                            &row.department,
                            &row.employment_status,
                            &row.row_payload_json,
                        ],
                    )
                    .await
                    .map_err(|_| "archive_postgres_hr_employee_staging_insert_failed".to_owned())?;
            }
            DatabaseTarget::HrAttendanceStaging => {
                transaction
                    .execute(
                        "INSERT INTO bitween_archive.hr_attendance_staging ( \
                            intake_id, tenant_id, row_number, row_hash, employee_external_id, \
                            work_date, row_payload \
                         ) VALUES ($1::text::uuid, $2, $3, $4, $5, NULLIF($6, '')::date, $7::text::jsonb)",
                        &[
                            &intake_id,
                            &tenant_id,
                            &row.row_number,
                            &row.row_hash,
                            &row.employee_external_id,
                            &row.work_date,
                            &row.row_payload_json,
                        ],
                    )
                    .await
                    .map_err(|_| "archive_postgres_hr_attendance_staging_insert_failed".to_owned())?;
            }
            DatabaseTarget::PayrollInputStaging => {
                transaction
                    .execute(
                        "INSERT INTO bitween_archive.payroll_input_staging ( \
                            intake_id, tenant_id, legal_entity_id, workplace_id, payroll_period, \
                            row_number, row_hash, employee_external_id, gross_pay, deduction_total, row_payload \
                         ) VALUES ( \
                            $1::text::uuid, $2, $3, $4, $5, $6, $7, $8, \
                            NULLIF($9, '')::numeric, NULLIF($10, '')::numeric, $11::text::jsonb \
                         )",
                        &[
                            &intake_id,
                            &tenant_id,
                            &legal_entity_id,
                            &workplace_id,
                            &payroll_period,
                            &row.row_number,
                            &row.row_hash,
                            &row.employee_external_id,
                            &row.gross_pay,
                            &row.deduction_total,
                            &row.row_payload_json,
                        ],
                    )
                    .await
                    .map_err(|_| "archive_postgres_payroll_staging_insert_failed".to_owned())?;
            }
            DatabaseTarget::ArchiveBlob | DatabaseTarget::NeedsMapping => {}
        }
    }
    Ok(())
}

fn resolve_local_intake_issue(
    store: &mut ArchiveIntakeStore,
    intake_id: &str,
    input: ArchiveIssueResolutionInput,
    updated_at_unix: u64,
) -> Result<(), String> {
    let issue_type = normalized_issue_type(&input)?;
    let code = normalized_issue_code(&input)?;
    let column = normalized_issue_column(&input);
    let issue_id = input
        .issue_id
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty());
    let record = store
        .intakes
        .iter_mut()
        .find(|record| record.id == intake_id)
        .ok_or_else(|| "archive_intake_not_found".to_owned())?;

    let before_guidance = record.guidance_items.len();
    let before_anomalies = record.anomalies.len();
    if issue_type == "guidance" {
        record.guidance_items.retain(|item| {
            !guidance_item_matches_resolution(item, issue_id, &code, &column)
        });
    } else if issue_type == "anomaly" {
        record
            .anomalies
            .retain(|item| !anomaly_item_matches_resolution(item, issue_id, &code, &column));
    }

    if before_guidance == record.guidance_items.len() && before_anomalies == record.anomalies.len()
    {
        return Err("archive_issue_not_found".to_owned());
    }
    refresh_local_intake_review_state(record, updated_at_unix);
    Ok(())
}

fn apply_local_field_mappings(
    store: &mut ArchiveIntakeStore,
    intake_id: &str,
    input: ArchiveFieldMappingInput,
    updated_at_unix: u64,
) -> Result<(), String> {
    let record = store
        .intakes
        .iter_mut()
        .find(|record| record.id == intake_id)
        .ok_or_else(|| "archive_intake_not_found".to_owned())?;
    apply_field_mapping_decisions(record, input)?;
    refresh_local_intake_review_state(record, updated_at_unix);
    Ok(())
}

fn apply_field_mapping_decisions(
    record: &mut ArchiveIntakeRecord,
    input: ArchiveFieldMappingInput,
) -> Result<(), String> {
    if clean(input.source_fingerprint.clone()) != record.source_fingerprint {
        return Err("archive_field_mapping_source_fingerprint_mismatch".to_owned());
    }
    if input.mappings.is_empty() {
        return Err("archive_field_mapping_decisions_required".to_owned());
    }
    if record.field_mappings.is_empty() {
        record.field_mappings = infer_field_mappings(&record.database_target, &record.extracted_columns);
    }

    for decision in input.mappings {
        validate_field_mapping_decision(record, &decision)?;
        let source_column = clean(decision.source_column.clone());
        let mapping = record
            .field_mappings
            .iter_mut()
            .find(|mapping| mapping.source_column == source_column)
            .ok_or_else(|| "archive_field_mapping_source_column_not_found".to_owned())?;
        mapping.target_table = decision.target_table;
        mapping.target_field = clean(decision.target_field);
        mapping.required = target_field_required(&mapping.target_table, &mapping.target_field);
        mapping.status = decision.status;
        mapping.confidence = if matches!(&mapping.status, FieldMappingStatus::Confirmed) {
            100
        } else if matches!(&mapping.status, FieldMappingStatus::Ignored) {
            0
        } else {
            mapping.confidence.min(90)
        };
        mapping.reason_codes = if matches!(&mapping.status, FieldMappingStatus::Ignored) {
            vec!["operator_ignored".to_owned()]
        } else {
            vec!["operator_reviewed".to_owned()]
        };
        mapping.value_shape = None;
    }
    rebuild_required_mapping_guidance(record);
    Ok(())
}

fn validate_field_mapping_decision(
    record: &ArchiveIntakeRecord,
    decision: &FieldMappingDecisionInput,
) -> Result<(), String> {
    let source_column = clean(decision.source_column.clone());
    if !record
        .extracted_columns
        .iter()
        .any(|column| column == &source_column)
    {
        return Err("archive_field_mapping_source_column_not_found".to_owned());
    }
    if decision.target_table != record.database_target {
        return Err("archive_field_mapping_target_table_mismatch".to_owned());
    }
    let target_field = clean(decision.target_field.clone());
    if !target_field_allowed(&decision.target_table, &target_field) {
        return Err("archive_field_mapping_target_field_unsupported".to_owned());
    }
    if target_field_required(&decision.target_table, &target_field)
        && matches!(decision.status, FieldMappingStatus::Ignored)
    {
        return Err("archive_field_mapping_required_target_cannot_be_ignored".to_owned());
    }
    if target_field == "ignored" && !matches!(decision.status, FieldMappingStatus::Ignored) {
        return Err("archive_field_mapping_ignored_target_requires_ignored_status".to_owned());
    }
    if target_field == "source_payload" && !matches!(decision.status, FieldMappingStatus::Confirmed)
    {
        return Err("archive_field_mapping_source_payload_requires_confirmed_status".to_owned());
    }
    match decision.status {
        FieldMappingStatus::Confirmed
        | FieldMappingStatus::Ignored
        | FieldMappingStatus::NeedsReview => Ok(()),
        FieldMappingStatus::Inferred | FieldMappingStatus::Preserved => {
            Err("archive_field_mapping_operator_status_required".to_owned())
        }
    }
}

fn rebuild_required_mapping_guidance(record: &mut ArchiveIntakeRecord) {
    record
        .guidance_items
        .retain(|item| {
            !item.id.starts_with("guidance-required-")
                && !item.id.starts_with("guidance-unclear-")
        });
    for required_field in missing_required_mapping_fields(&record.database_target, &record.field_mappings) {
        let id = required_mapping_guidance_id(&required_field);
        if !record.guidance_items.iter().any(|item| item.id == id) {
            record.guidance_items.push(GuidanceItem {
                id,
                code: GuidanceCode::ConfirmMissingRequiredData,
                severity: GuidanceSeverity::Blocking,
                column: required_field,
            });
        }
    }
    for mapping in unclear_field_mappings(&record.field_mappings) {
        let id = unclear_mapping_guidance_id(&mapping.source_column);
        if !record.guidance_items.iter().any(|item| item.id == id) {
            record.guidance_items.push(GuidanceItem {
                id,
                code: GuidanceCode::ExplainColumn,
                severity: GuidanceSeverity::Warning,
                column: mapping.source_column.clone(),
            });
        }
    }
}

fn guidance_item_matches_resolution(
    item: &GuidanceItem,
    issue_id: Option<&str>,
    code: &str,
    column: &str,
) -> bool {
    issue_id == Some(item.id.as_str())
        || (item.code.as_postgres_value() == code && clean(item.column.clone()) == column)
}

fn anomaly_item_matches_resolution(
    item: &AnomalyItem,
    issue_id: Option<&str>,
    code: &str,
    column: &str,
) -> bool {
    issue_id == Some(item.id.as_str())
        || (item.code.as_postgres_value() == code && clean(item.column.clone()) == column)
}

fn refresh_local_intake_review_state(record: &mut ArchiveIntakeRecord, updated_at_unix: u64) {
    rebuild_required_mapping_guidance(record);
    let has_open_issue = !record.guidance_items.is_empty() || !record.anomalies.is_empty();
    let has_open_anomaly = !record.anomalies.is_empty();
    let staging_target = matches!(
        record.database_target,
        DatabaseTarget::HrEmployeeStaging
            | DatabaseTarget::HrAttendanceStaging
            | DatabaseTarget::PayrollInputStaging
    );

    record.postgres_ready = staging_target && !has_open_issue;
    record.status = if has_open_issue {
        ArchiveIntakeStatus::NeedsGuidance
    } else if staging_target {
        ArchiveIntakeStatus::ReadyForStaging
    } else {
        ArchiveIntakeStatus::Archived
    };
    record.next_action = if has_open_anomaly {
        ArchiveIntakeAction::ResolveAnomalies
    } else if has_open_issue {
        ArchiveIntakeAction::MapColumns
    } else if staging_target {
        ArchiveIntakeAction::SaveToBusinessData
    } else {
        ArchiveIntakeAction::KeepInArchive
    };
    record.extraction_status = extraction_status_for(
        &record.database_target,
        &record.status,
        record.content_sample_row_count,
        record.content_sample_sha256 != EMPTY_SHA256 || record.content_sample_row_count > 0,
    );
    record.updated_at_unix = updated_at_unix;
}

fn normalized_issue_type(input: &ArchiveIssueResolutionInput) -> Result<String, String> {
    let value = input
        .issue_type
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "archive_issue_type_required".to_owned())?
        .to_ascii_lowercase();
    match value.as_str() {
        "guidance" | "anomaly" => Ok(value),
        _ => Err("archive_issue_type_unsupported".to_owned()),
    }
}

fn normalized_issue_code(input: &ArchiveIssueResolutionInput) -> Result<String, String> {
    input
        .code
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_owned)
        .ok_or_else(|| "archive_issue_code_required".to_owned())
}

fn normalized_issue_column(input: &ArchiveIssueResolutionInput) -> String {
    input
        .column
        .clone()
        .map(clean)
        .unwrap_or_default()
}

fn issue_resolution_json(
    input: &ArchiveIssueResolutionInput,
    resolved_by: &str,
) -> Result<String, String> {
    let audit = ArchiveIssueResolutionAudit {
        decision: input
            .decision
            .clone()
            .map(clean)
            .filter(|value| !value.is_empty())
            .unwrap_or_else(|| "confirmed_by_operator".to_owned()),
        note: input
            .note
            .clone()
            .map(clean)
            .filter(|value| !value.is_empty())
            .unwrap_or_default()
            .chars()
            .take(512)
            .collect(),
        resolved_by: clean(resolved_by.to_owned()),
    };
    serde_json::to_string(&audit).map_err(|_| "archive_issue_resolution_encode_failed".to_owned())
}

fn rollback_reason(input: ArchiveRollbackInput) -> String {
    input
        .reason
        .map(clean)
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "operator_requested".to_owned())
        .chars()
        .take(512)
        .collect()
}

fn bounded_note(value: String) -> String {
    clean(value).chars().take(512).collect()
}

fn rollback_recovery_point_id(input: &ArchiveRollbackInput) -> String {
    input
        .recovery_point_id
        .clone()
        .map(clean)
        .filter(|value| !value.is_empty())
        .unwrap_or_default()
}

fn print_store(store: &ArchiveIntakeStore) -> Result<(), String> {
    let body = serde_json::to_string_pretty(store).map_err(|error| error.to_string())?;
    println!("{body}");
    Ok(())
}

fn print_source_sync_plan(plan: &ArchiveSourceSyncPlan) -> Result<(), String> {
    let body = serde_json::to_string_pretty(plan).map_err(|error| error.to_string())?;
    println!("{body}");
    Ok(())
}

fn build_intake_record(
    input: ArchiveIntakeInput,
    updated_at_unix: u64,
    id_seed: u128,
) -> Result<ArchiveIntakeRecord, String> {
    let original_file_name = required_field(input.file_name, "file_name")?;
    let file_type = normalize_file_type(input.file_type.as_deref(), &original_file_name);
    let file_size_bytes = input
        .file_size_bytes
        .ok_or_else(|| "missing required intake field: file_size_bytes".to_owned())?;
    let content_sha256 = required_field(input.content_sha256, "content_sha256")?;
    let sample_text = input.sample_text.unwrap_or_default();
    let extracted_columns = extract_columns(&sample_text);
    let estimated_rows = estimate_rows(&sample_text);
    let content_sample_sha256 = sha256_hex(sample_text.as_bytes());
    let content_sample_row_count = estimated_rows;
    let family = classify_family(
        &original_file_name,
        &file_type,
        &sample_text,
        &extracted_columns,
    );
    let database_target = database_target(&family, &original_file_name, &extracted_columns);
    let object_ref = rustfs_object_ref(input.object_uri.or(input.blob_uri))?;
    let stored_file_name = normalized_stored_file_name(&family, id_seed, &file_type);
    let source_fingerprint = source_fingerprint(&extracted_columns, &database_target);
    let field_mappings =
        infer_field_mappings_with_sample(&database_target, &extracted_columns, &sample_text);
    let mut guidance_items = guidance_items(
        &family,
        &database_target,
        &extracted_columns,
        estimated_rows,
        &field_mappings,
    );
    let anomalies = anomalies(file_size_bytes, &family, &extracted_columns, estimated_rows);
    if anomalies.iter().any(|item| item.severity == GuidanceSeverity::Blocking)
        && !guidance_items
            .iter()
            .any(|item| item.code == GuidanceCode::UploadReadableSheet)
    {
        guidance_items.push(GuidanceItem {
            id: "guidance-readable-sheet".to_owned(),
            code: GuidanceCode::UploadReadableSheet,
            severity: GuidanceSeverity::Blocking,
            column: String::new(),
        });
    }
    let postgres_ready = guidance_items.is_empty()
        && anomalies
            .iter()
            .all(|item| item.severity != GuidanceSeverity::Blocking)
        && !matches!(
            database_target,
            DatabaseTarget::ArchiveBlob | DatabaseTarget::NeedsMapping
        );
    let status = if !guidance_items.is_empty()
        || anomalies
            .iter()
            .any(|item| item.severity == GuidanceSeverity::Blocking)
    {
        ArchiveIntakeStatus::NeedsGuidance
    } else if postgres_ready {
        ArchiveIntakeStatus::ReadyForStaging
    } else {
        ArchiveIntakeStatus::Archived
    };
    let next_action = match status {
        ArchiveIntakeStatus::NeedsGuidance if !anomalies.is_empty() => {
            ArchiveIntakeAction::ResolveAnomalies
        }
        ArchiveIntakeStatus::NeedsGuidance => ArchiveIntakeAction::MapColumns,
        ArchiveIntakeStatus::ReadyForStaging => ArchiveIntakeAction::SaveToBusinessData,
        ArchiveIntakeStatus::Received
        | ArchiveIntakeStatus::Archived
        | ArchiveIntakeStatus::Admitted
        | ArchiveIntakeStatus::Rejected => {
            ArchiveIntakeAction::KeepInArchive
        }
    };
    let extraction_status = extraction_status_for(
        &database_target,
        &status,
        content_sample_row_count,
        !sample_text.trim().is_empty(),
    );

    Ok(ArchiveIntakeRecord {
        id: format!("intake-{id_seed}"),
        original_file_name,
        stored_file_name,
        file_type,
        file_size_bytes,
        content_sha256,
        content_sample_sha256,
        content_sample_row_count,
        extraction_status,
        object_uri: object_ref.uri.clone(),
        object_bucket: object_ref.bucket,
        object_key: object_ref.key,
        blob_ref: object_ref.uri,
        family,
        database_target,
        status,
        next_action,
        extracted_columns,
        source_fingerprint,
        field_mappings,
        estimated_rows,
        guidance_items,
        anomalies,
        source_versions: Vec::new(),
        recovery_points: Vec::new(),
        source_sync_items: Vec::new(),
        postgres_ready,
        updated_at_unix,
    })
}

fn normalize_file_type(input_type: Option<&str>, file_name: &str) -> String {
    let extension = file_name
        .rsplit_once('.')
        .map(|(_, extension)| extension)
        .unwrap_or_default()
        .trim()
        .to_ascii_lowercase();
    let browser_type = input_type
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .unwrap_or_default()
        .to_ascii_lowercase();
    if !extension.is_empty() {
        extension
    } else if !browser_type.is_empty() {
        browser_type
            .rsplit_once('/')
            .map(|(_, subtype)| subtype)
            .unwrap_or(browser_type.as_str())
            .to_owned()
    } else {
        "unknown".to_owned()
    }
}

fn rustfs_object_ref(value: Option<String>) -> Result<RustFsObjectRef, String> {
    let uri = required_field(value, "object_uri")?;
    let without_scheme = uri
        .strip_prefix("rustfs://")
        .ok_or_else(|| "archive intake object_uri must start with rustfs://".to_owned())?;
    let (bucket, key) = without_scheme
        .split_once('/')
        .ok_or_else(|| "archive intake object_uri must include bucket and object key".to_owned())?;
    let bucket = clean(bucket.to_owned());
    let key = clean(key.to_owned());
    if bucket.is_empty() || key.is_empty() {
        return Err("archive intake object_uri must include bucket and object key".to_owned());
    }
    Ok(RustFsObjectRef { uri, bucket, key })
}

fn normalize_loaded_record(record: &mut ArchiveIntakeRecord) {
    if record.object_uri.is_empty() && !record.blob_ref.is_empty() {
        record.object_uri = record.blob_ref.clone();
    }
    if (record.object_bucket.is_empty() || record.object_key.is_empty())
        && let Ok(object_ref) = rustfs_object_ref(Some(record.object_uri.clone()))
    {
        record.object_bucket = object_ref.bucket;
        record.object_key = object_ref.key;
    }
    if record.blob_ref.is_empty() {
        record.blob_ref = record.object_uri.clone();
    }
    if record.content_sample_sha256.is_empty() {
        record.content_sample_sha256 = EMPTY_SHA256.to_owned();
    }
    if record.source_fingerprint.is_empty() {
        record.source_fingerprint = source_fingerprint(&record.extracted_columns, &record.database_target);
    }
    if record.field_mappings.is_empty() {
        record.field_mappings = infer_field_mappings(&record.database_target, &record.extracted_columns);
    }
    rebuild_required_mapping_guidance(record);
    record.extraction_status = extraction_status_for(
        &record.database_target,
        &record.status,
        record.content_sample_row_count,
        record.content_sample_sha256 != EMPTY_SHA256 || record.content_sample_row_count > 0,
    );
}

fn classify_family(
    file_name: &str,
    file_type: &str,
    sample_text: &str,
    columns: &[String],
) -> FileFamily {
    let text = format!(
        "{} {} {}",
        file_name.to_lowercase(),
        file_type.to_lowercase(),
        sample_text.lines().take(2).collect::<Vec<_>>().join(" ").to_lowercase()
    );
    let normalized_columns = columns
        .iter()
        .map(|column| normalized_header_key(column))
        .collect::<Vec<_>>();
    let payroll_score = score_terms(
        &text,
        &normalized_columns,
        &[
            "payroll",
            "salary",
            "급여",
            "임금",
            "공제총액",
            "기본급",
            "잔업시간",
            "지급총액",
            "지급액",
            "청구금액",
        ],
    );
    let hr_score = score_terms(
        &text,
        &normalized_columns,
        &[
            "hr",
            "employee",
            "roster",
            "attendance",
            "근로자명부",
            "직원",
            "사원",
            "인사",
            "근태",
            "출퇴근",
            "휴가",
            "주민번호",
            "입사일",
            "퇴사일",
            "휴대폰",
            "계좌",
        ],
    );
    if hr_score > 0 && hr_score >= payroll_score {
        FileFamily::Hr
    } else if payroll_score > 0 {
        FileFamily::Payroll
    } else if !columns.is_empty() {
        FileFamily::Unknown
    } else {
        FileFamily::GeneralArchive
    }
}

fn score_terms(text: &str, normalized_columns: &[String], terms: &[&str]) -> usize {
    terms
        .iter()
        .map(|term| {
            let term_key = normalized_header_key(term);
            usize::from(text.contains(term))
                + normalized_columns
                    .iter()
                    .filter(|column| **column == term_key || column.contains(&term_key))
                    .count()
        })
        .sum()
}

fn database_target(
    family: &FileFamily,
    file_name: &str,
    columns: &[String],
) -> DatabaseTarget {
    let text = format!("{} {}", file_name.to_lowercase(), columns.join(" ").to_lowercase());
    match family {
        FileFamily::Payroll => DatabaseTarget::PayrollInputStaging,
        FileFamily::Hr if contains_any(&text, &["attendance", "근태", "출퇴근", "timesheet"]) => {
            DatabaseTarget::HrAttendanceStaging
        }
        FileFamily::Hr => DatabaseTarget::HrEmployeeStaging,
        FileFamily::GeneralArchive => DatabaseTarget::ArchiveBlob,
        FileFamily::Unknown => DatabaseTarget::NeedsMapping,
    }
}

fn extract_columns(sample_text: &str) -> Vec<String> {
    let Some((_, header_line)) = best_header_line(sample_text) else {
        return Vec::new();
    };
    split_delimited_line(header_line, table_delimiter(header_line))
        .into_iter()
        .map(|value| value.trim().trim_matches('"').to_owned())
        .filter(|value| !value.is_empty())
        .take(48)
        .collect()
}

fn estimate_rows(sample_text: &str) -> u64 {
    let Some((header_index, _)) = best_header_line(sample_text) else {
        return 0;
    };
    sample_text
        .lines()
        .filter(|line| !line.trim().is_empty())
        .skip(header_index + 1)
        .count() as u64
}

fn best_header_line(sample_text: &str) -> Option<(usize, &str)> {
    let lines = sample_text
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .collect::<Vec<_>>();
    let first = *lines.first()?;
    let mut best = (0usize, first, 0isize);
    for (index, line) in lines.iter().take(40).enumerate() {
        let cells = split_delimited_line(line, table_delimiter(line));
        let score = header_cells_score(&cells);
        if score > best.2 {
            best = (index, *line, score);
        }
    }
    Some((best.0, best.1))
}

fn header_cells_score(cells: &[String]) -> isize {
    let non_empty = cells
        .iter()
        .map(|cell| clean(cell.clone()))
        .filter(|cell| !cell.is_empty())
        .collect::<Vec<_>>();
    if non_empty.len() < 2 {
        return 0;
    }
    let aliases = [
        "no", "순", "번호", "사번", "직원번호", "사원번호", "성명", "성 명", "이름",
        "직원명", "소속", "부서", "조직", "근무지", "업무", "직무", "직책", "기본시급",
        "통상시급", "급여", "지급액", "지급총액", "공제", "공제총액", "입사일",
        "퇴사일", "근무일", "주민번호", "휴대폰", "email", "e-mail", "은행", "계좌",
    ];
    let alias_keys = aliases
        .iter()
        .map(|alias| normalized_header_key(alias))
        .collect::<Vec<_>>();
    let alias_score = non_empty
        .iter()
        .filter(|cell| {
            let key = normalized_header_key(cell);
            alias_keys
                .iter()
                .any(|alias| key == *alias || (!alias.is_empty() && key.contains(alias)))
        })
        .count() as isize
        * 5;
    let text_score = non_empty
        .iter()
        .filter(|cell| cell.chars().any(|ch| ch.is_ascii_alphabetic() || ('가'..='힣').contains(&ch)))
        .count() as isize;
    let numeric_penalty = non_empty
        .iter()
        .filter(|cell| normalized_numeric_text(cell).is_some())
        .count() as isize
        * 2;
    alias_score + text_score + non_empty.len().min(12) as isize - numeric_penalty
}

fn extraction_status_for(
    database_target: &DatabaseTarget,
    status: &ArchiveIntakeStatus,
    content_sample_row_count: u64,
    has_sample_text: bool,
) -> ArchiveExtractionStatus {
    if matches!(database_target, DatabaseTarget::ArchiveBlob) {
        return ArchiveExtractionStatus::NotApplicable;
    }
    if matches!(status, ArchiveIntakeStatus::NeedsGuidance)
        || matches!(database_target, DatabaseTarget::NeedsMapping)
    {
        return ArchiveExtractionStatus::NeedsGuidance;
    }
    if matches!(
        database_target,
        DatabaseTarget::HrEmployeeStaging
            | DatabaseTarget::HrAttendanceStaging
            | DatabaseTarget::PayrollInputStaging
    ) && content_sample_row_count > 0
    {
        return ArchiveExtractionStatus::Converted;
    }
    if has_sample_text {
        ArchiveExtractionStatus::NeedsGuidance
    } else {
        ArchiveExtractionStatus::NotReadable
    }
}

fn guidance_items(
    family: &FileFamily,
    database_target: &DatabaseTarget,
    columns: &[String],
    estimated_rows: u64,
    field_mappings: &[FieldMapping],
) -> Vec<GuidanceItem> {
    let mut items = Vec::new();
    if matches!(family, FileFamily::Unknown)
        || matches!(database_target, DatabaseTarget::NeedsMapping)
    {
        items.push(GuidanceItem {
            id: "guidance-business-area".to_owned(),
            code: GuidanceCode::ChooseBusinessArea,
            severity: GuidanceSeverity::Blocking,
            column: String::new(),
        });
    }
    if columns.is_empty() && !matches!(family, FileFamily::GeneralArchive) {
        items.push(GuidanceItem {
            id: "guidance-readable-sheet".to_owned(),
            code: GuidanceCode::UploadReadableSheet,
            severity: GuidanceSeverity::Blocking,
            column: String::new(),
        });
    }
    if estimated_rows == 0 && !matches!(family, FileFamily::GeneralArchive) {
        items.push(GuidanceItem {
            id: "guidance-missing-data".to_owned(),
            code: GuidanceCode::ConfirmMissingRequiredData,
            severity: GuidanceSeverity::Blocking,
            column: String::new(),
        });
    }
    for required_field in missing_required_mapping_fields(database_target, field_mappings) {
        items.push(GuidanceItem {
            id: required_mapping_guidance_id(&required_field),
            code: GuidanceCode::ConfirmMissingRequiredData,
            severity: GuidanceSeverity::Blocking,
            column: required_field,
        });
    }
    for mapping in unclear_field_mappings(field_mappings) {
        items.push(GuidanceItem {
            id: unclear_mapping_guidance_id(&mapping.source_column),
            code: GuidanceCode::ExplainColumn,
            severity: GuidanceSeverity::Warning,
            column: mapping.source_column.clone(),
        });
    }
    items
}

fn source_fingerprint(columns: &[String], database_target: &DatabaseTarget) -> String {
    let normalized_columns = columns
        .iter()
        .map(|column| normalized_header_key(column))
        .collect::<Vec<_>>()
        .join("\u{1f}");
    let source = format!(
        "{}\u{1f}{}",
        normalized_columns,
        database_target.as_postgres_value()
    );
    format!("sha256:{}", sha256_hex(source.as_bytes()))
}

fn infer_field_mappings(database_target: &DatabaseTarget, columns: &[String]) -> Vec<FieldMapping> {
    if columns.is_empty() || matches!(database_target, DatabaseTarget::ArchiveBlob) {
        return Vec::new();
    }
    columns
        .iter()
        .map(|column| {
            let inferred = inferred_target_field(database_target, column);
            let (target_field, confidence, status, reason_codes) =
                inferred.unwrap_or_else(|| {
                    (
                        "source_payload".to_owned(),
                        35,
                        FieldMappingStatus::Preserved,
                        vec!["preserved_for_review".to_owned()],
                    )
                });
            let required = target_field_required(database_target, &target_field);
            FieldMapping {
                source_column: column.clone(),
                target_table: database_target.clone(),
                target_field,
                confidence,
                required,
                status,
                editable: true,
                reason_codes,
                value_shape: None,
            }
        })
        .collect()
}

fn infer_field_mappings_with_sample(
    database_target: &DatabaseTarget,
    columns: &[String],
    sample_text: &str,
) -> Vec<FieldMapping> {
    let mut mappings = infer_field_mappings(database_target, columns);
    annotate_field_mapping_value_shapes(&mut mappings, columns, sample_text);
    mappings
}

fn annotate_field_mapping_value_shapes(
    mappings: &mut [FieldMapping],
    columns: &[String],
    sample_text: &str,
) {
    let parsed_rows = parse_business_rows(columns, sample_text);
    for mapping in mappings {
        mapping.value_shape = value_shape_for_column(columns, &parsed_rows, &mapping.source_column);
    }
}

fn value_shape_for_column(
    columns: &[String],
    parsed_rows: &[Vec<String>],
    source_column: &str,
) -> Option<String> {
    let index = columns.iter().position(|column| column == source_column)?;
    let samples = parsed_rows
        .iter()
        .filter_map(|row| row.get(index))
        .map(|value| clean(value.clone()))
        .filter(|value| !value.is_empty())
        .take(20)
        .collect::<Vec<_>>();
    if samples.is_empty() {
        return Some("empty".to_owned());
    }
    if samples.iter().all(|value| normalized_numeric_text(value).is_some()) {
        return Some("numeric_normalized".to_owned());
    }
    if samples.iter().all(|value| normalized_date_text(value).is_some()) {
        return Some("date_normalized".to_owned());
    }
    if samples.iter().any(|value| looks_like_korean_resident_id(value)) {
        return Some("sensitive_identifier_redacted".to_owned());
    }
    if samples.iter().any(|value| looks_like_email(value)) {
        return Some("email_redacted".to_owned());
    }
    if samples.iter().any(|value| looks_like_phone(value)) {
        return Some("phone_redacted".to_owned());
    }
    if samples
        .iter()
        .all(|value| value.len() <= 32 && value.chars().all(|ch| ch.is_alphanumeric() || "-_".contains(ch)))
    {
        return Some("identifier".to_owned());
    }
    Some("text_sanitized".to_owned())
}

fn looks_like_korean_resident_id(value: &str) -> bool {
    let digits = value.chars().filter(|ch| ch.is_ascii_digit()).count();
    digits == 13 && value.contains('-')
}

fn looks_like_phone(value: &str) -> bool {
    let digits = value.chars().filter(|ch| ch.is_ascii_digit()).count();
    digits >= 9 && digits <= 12 && value.chars().all(|ch| ch.is_ascii_digit() || " -()+".contains(ch))
}

fn inferred_target_field(
    database_target: &DatabaseTarget,
    column: &str,
) -> Option<(String, u8, FieldMappingStatus, Vec<String>)> {
    let key = normalized_header_key(column);
    if key.is_empty() {
        return None;
    }
    let mapping = match database_target {
        DatabaseTarget::HrEmployeeStaging => hr_employee_target_for_key(&key),
        DatabaseTarget::HrAttendanceStaging => attendance_target_for_key(&key),
        DatabaseTarget::PayrollInputStaging => payroll_target_for_key(&key),
        DatabaseTarget::ArchiveBlob | DatabaseTarget::NeedsMapping => None,
    }?;
    let confidence = if mapping.1 { 96 } else { 82 };
    Some((
        mapping.0.to_owned(),
        confidence,
        FieldMappingStatus::Inferred,
        vec!["header_alias".to_owned()],
    ))
}

fn hr_employee_target_for_key(key: &str) -> Option<(&'static str, bool)> {
    target_for_key(
        key,
        &[
            ("source_row_number", true, &["no", "no.", "순", "번호"][..]),
            (
                "employee_external_id",
                true,
                &["사번", "직원번호", "사원번호", "employeeid", "employee_id", "externalid"],
            ),
            ("display_name", true, &["성명", "성 명", "이름", "직원명", "name", "displayname"]),
            ("department", true, &["소속", "부서", "조직", "department", "team"]),
            ("workplace", true, &["근무지", "사업장", "workplace", "site"]),
            ("job_duty", true, &["업무", "직무", "담당업무", "jobduty", "job"]),
            ("role_title", true, &["직책", "직위", "직급", "title", "role"]),
            ("base_hourly_rate", true, &["기본시급", "basehourlyrate"]),
            ("regular_hourly_rate", true, &["통상시급", "regularhourlyrate"]),
            ("allowance", true, &["수당", "allowance"]),
            ("national_pension", true, &["국민연금", "nationalpension"]),
            ("health_insurance", true, &["건강보험", "healthinsurance"]),
            ("income_tax", true, &["소득세", "incometax"]),
            ("annual_leave_accrued", true, &["발생연차"]),
            ("annual_leave_used", true, &["사용연차"]),
            ("annual_leave_balance", true, &["잔여연차"]),
            ("resident_registration_number", true, &["주민번호", "주민등록번호"]),
            ("hire_date", true, &["입사일", "hiredate"]),
            ("insurance_start_date", true, &["보험가입일"]),
            ("termination_date", true, &["퇴사일", "terminationdate"]),
            ("insurance_end_date", true, &["보험상실일"]),
            ("address", true, &["주소", "address"]),
            ("mobile_phone", true, &["휴대폰", "전화번호", "mobile", "phone"]),
            ("email", true, &["email", "e-mail", "이메일"]),
            ("severance_interim_settlement", true, &["퇴직금중간정산"]),
            ("bank_name", true, &["은행", "bank"]),
            ("bank_account", true, &["계좌", "account"]),
            ("certification", true, &["자격증", "certification"]),
        ],
    )
}

fn attendance_target_for_key(key: &str) -> Option<(&'static str, bool)> {
    target_for_key(
        key,
        &[
            ("employee_external_id", true, &["사번", "직원번호", "사원번호", "employeeid"]),
            ("display_name", true, &["성명", "성 명", "이름", "직원명", "name"]),
            ("work_date", true, &["근무일", "일자", "date", "workdate"]),
            ("work_hours", true, &["근무시간", "시간", "hours"]),
            ("attendance_status", true, &["근태", "상태", "status"]),
        ],
    )
}

fn payroll_target_for_key(key: &str) -> Option<(&'static str, bool)> {
    target_for_key(
        key,
        &[
            ("source_row_number", true, &["순", "no", "no.", "번호"][..]),
            ("employee_external_id", true, &["사번", "직원번호", "사원번호", "employeeid", "코드"]),
            ("display_name", true, &["성명", "성 명", "이름", "직원명", "name"]),
            ("department", true, &["소속", "부서", "조직", "department"]),
            ("workplace", true, &["근무지", "사업장", "workplace"]),
            ("hire_date", true, &["입사일", "hiredate"]),
            ("termination_date", true, &["퇴사일", "terminationdate"]),
            ("base_hourly_rate", true, &["기본시급", "basehourlyrate"]),
            ("regular_hourly_rate", true, &["통상시급", "regularhourlyrate"]),
            ("base_pay", true, &["기본급", "기 본 급", "basepay"]),
            ("gross_pay", true, &["급여", "지급총액", "총지급", "합계", "청구금액", "지급액", "grosspay"]),
            ("deduction_total", true, &["공제총액", "공 제 총 액", "공제금액", "공제", "deductiontotal"]),
            ("overtime_hours", true, &["잔업시간", "ot", "o/t", "overtime"]),
            ("shift_hours", true, &["교대시간"]),
            ("night_hours", true, &["심야시간"]),
            ("holiday_hours", true, &["특근시간"]),
            ("position_allowance", true, &["직책수당"]),
            ("labor_cost", true, &["노무비계"]),
            ("supply_amount", true, &["공급가액"]),
            ("vat", true, &["부가세"]),
        ],
    )
}

fn target_for_key(
    key: &str,
    mappings: &[(&'static str, bool, &[&str])],
) -> Option<(&'static str, bool)> {
    mappings
        .iter()
        .find(|(_, _, aliases)| aliases.iter().any(|alias| key == normalized_header_key(alias)))
        .map(|(target, exact, _)| (*target, *exact))
        .or_else(|| {
            mappings
                .iter()
                .find(|(_, _, aliases)| {
                    aliases.iter().any(|alias| {
                        let alias_key = normalized_header_key(alias);
                        alias_key.len() >= 3 && key.contains(&alias_key)
                    })
                })
                .map(|(target, exact, _)| (*target, *exact))
        })
}

fn canonical_target_fields(database_target: &DatabaseTarget) -> Vec<&'static str> {
    let mut fields = match database_target {
        DatabaseTarget::HrEmployeeStaging => vec![
            "employee_external_id",
            "display_name",
            "department",
            "workplace",
            "job_duty",
            "role_title",
            "base_hourly_rate",
            "regular_hourly_rate",
            "allowance",
            "national_pension",
            "health_insurance",
            "income_tax",
            "annual_leave_accrued",
            "annual_leave_used",
            "annual_leave_balance",
            "resident_registration_number",
            "hire_date",
            "insurance_start_date",
            "termination_date",
            "insurance_end_date",
            "address",
            "mobile_phone",
            "email",
            "severance_interim_settlement",
            "bank_name",
            "bank_account",
            "certification",
            "source_row_number",
            "employment_status",
        ],
        DatabaseTarget::HrAttendanceStaging => vec![
            "employee_external_id",
            "display_name",
            "work_date",
            "work_hours",
            "attendance_status",
        ],
        DatabaseTarget::PayrollInputStaging => vec![
            "employee_external_id",
            "display_name",
            "department",
            "workplace",
            "hire_date",
            "termination_date",
            "base_hourly_rate",
            "regular_hourly_rate",
            "base_pay",
            "gross_pay",
            "deduction_total",
            "overtime_hours",
            "shift_hours",
            "night_hours",
            "holiday_hours",
            "position_allowance",
            "labor_cost",
            "supply_amount",
            "vat",
            "source_row_number",
        ],
        DatabaseTarget::ArchiveBlob | DatabaseTarget::NeedsMapping => Vec::new(),
    };
    fields.push("source_payload");
    fields.push("ignored");
    fields
}

fn required_target_fields(database_target: &DatabaseTarget) -> Vec<&'static str> {
    match database_target {
        DatabaseTarget::HrEmployeeStaging => vec!["display_name", "department"],
        DatabaseTarget::HrAttendanceStaging => vec!["employee_external_id", "work_date"],
        DatabaseTarget::PayrollInputStaging => vec!["employee_external_id", "gross_pay"],
        DatabaseTarget::ArchiveBlob | DatabaseTarget::NeedsMapping => Vec::new(),
    }
}

fn target_field_required(database_target: &DatabaseTarget, target_field: &str) -> bool {
    required_target_fields(database_target)
        .iter()
        .any(|required| *required == target_field)
}

fn target_field_allowed(database_target: &DatabaseTarget, target_field: &str) -> bool {
    canonical_target_fields(database_target)
        .iter()
        .any(|field| *field == target_field)
}

fn missing_required_mapping_fields(
    database_target: &DatabaseTarget,
    field_mappings: &[FieldMapping],
) -> Vec<String> {
    required_target_fields(database_target)
        .into_iter()
        .filter(|required| {
            !field_mappings.iter().any(|mapping| {
                mapping.target_table == *database_target
                    && mapping.target_field == *required
                    && !matches!(
                        mapping.status,
                        FieldMappingStatus::Ignored | FieldMappingStatus::NeedsReview
                    )
            })
        })
        .map(str::to_owned)
        .collect()
}

fn unclear_field_mappings(field_mappings: &[FieldMapping]) -> Vec<&FieldMapping> {
    field_mappings
        .iter()
        .filter(|mapping| mapping.status.is_review_blocking())
        .collect()
}

fn required_mapping_guidance_id(required_field: &str) -> String {
    format!("guidance-required-{}", stable_key(required_field))
}

fn unclear_mapping_guidance_id(source_column: &str) -> String {
    format!("guidance-unclear-{}", stable_key(source_column))
}

fn normalized_header_key(value: &str) -> String {
    value
        .chars()
        .flat_map(char::to_lowercase)
        .filter(|ch| ch.is_alphanumeric() || ('가'..='힣').contains(ch))
        .collect()
}

fn anomalies(
    file_size_bytes: u64,
    family: &FileFamily,
    columns: &[String],
    estimated_rows: u64,
) -> Vec<AnomalyItem> {
    let mut items = Vec::new();
    if file_size_bytes == 0 {
        items.push(AnomalyItem {
            id: "anomaly-empty-file".to_owned(),
            code: AnomalyCode::EmptyFile,
            severity: GuidanceSeverity::Blocking,
            column: String::new(),
        });
    }
    if file_size_bytes > MAX_FILE_BYTES {
        items.push(AnomalyItem {
            id: "anomaly-large-file".to_owned(),
            code: AnomalyCode::LargeFile,
            severity: GuidanceSeverity::Blocking,
            column: String::new(),
        });
    }
    if !matches!(family, FileFamily::GeneralArchive) && columns.is_empty() {
        items.push(AnomalyItem {
            id: "anomaly-unknown-structure".to_owned(),
            code: AnomalyCode::UnknownFileStructure,
            severity: GuidanceSeverity::Blocking,
            column: String::new(),
        });
    }
    if !matches!(family, FileFamily::GeneralArchive) && estimated_rows == 0 {
        items.push(AnomalyItem {
            id: "anomaly-no-rows".to_owned(),
            code: AnomalyCode::NoRowsDetected,
            severity: GuidanceSeverity::Blocking,
            column: String::new(),
        });
    }
    items
}

fn staged_rows_for_record_with_mappings(
    database_target: &DatabaseTarget,
    columns: &[String],
    sample_text: &str,
    field_mappings: &[FieldMapping],
) -> Result<Vec<StagedBusinessRow>, String> {
    if !matches!(
        database_target,
        DatabaseTarget::HrEmployeeStaging
            | DatabaseTarget::HrAttendanceStaging
            | DatabaseTarget::PayrollInputStaging
    ) || columns.is_empty()
    {
        return Ok(Vec::new());
    }

    let parsed_rows = parse_business_rows(columns, sample_text);
    parsed_rows
        .into_iter()
        .enumerate()
        .map(|(index, row)| {
            let payload = row_payload_json(columns, &row)?;
            let row_number = i32::try_from(index + 1)
                .map_err(|_| "archive_staging_row_number_out_of_range".to_owned())?;
            Ok(StagedBusinessRow {
                row_number,
                row_hash: sha256_hex(payload.as_bytes()),
                row_payload_json: payload,
                employee_external_id: value_for_target_field(
                    columns,
                    &row,
                    field_mappings,
                    "employee_external_id",
                    &["employee id", "employee_id", "external id", "사번", "직원번호", "사원번호"],
                ),
                display_name: value_for_target_field(
                    columns,
                    &row,
                    field_mappings,
                    "display_name",
                    &["display name", "name", "성명", "이름", "직원명"],
                ),
                department: value_for_target_field(
                    columns,
                    &row,
                    field_mappings,
                    "department",
                    &["department", "team", "부서", "조직"],
                ),
                employment_status: value_for_target_field(
                    columns,
                    &row,
                    field_mappings,
                    "employment_status",
                    &["employment status", "status", "재직", "상태"],
                ),
                work_date: value_for_target_field(
                    columns,
                    &row,
                    field_mappings,
                    "work_date",
                    &["work date", "date", "근무일", "일자"],
                )
                    .and_then(|value| normalized_date_text(&value)),
                gross_pay: value_for_target_field(
                    columns,
                    &row,
                    field_mappings,
                    "gross_pay",
                    &[
                        "gross pay",
                        "gross",
                        "amount",
                        "salary",
                        "pay",
                        "wage",
                        "급여",
                        "임금",
                        "지급",
                        "금액",
                    ],
                )
                .and_then(|value| normalized_numeric_text(&value)),
                deduction_total: value_for_target_field(
                    columns,
                    &row,
                    field_mappings,
                    "deduction_total",
                    &["deduction total", "deduction", "공제"],
                )
                .and_then(|value| normalized_numeric_text(&value)),
            })
        })
        .collect()
}

fn parse_business_rows(columns: &[String], sample_text: &str) -> Vec<Vec<String>> {
    let lines = sample_text
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .collect::<Vec<_>>();
    if lines.is_empty() {
        return Vec::new();
    }
    let header_index = lines
        .iter()
        .position(|line| {
            let parsed = split_delimited_line(line, table_delimiter(line));
            parsed
                .iter()
                .filter(|value| !value.trim().is_empty())
                .zip(columns.iter())
                .all(|(left, right)| clean(left.clone()) == clean(right.clone()))
                && parsed.iter().filter(|value| !value.trim().is_empty()).count()
                    == columns.len()
        })
        .or_else(|| best_header_line(sample_text).map(|(index, _)| index))
        .unwrap_or(0);
    let header_line = lines.get(header_index).copied().unwrap_or_default();
    let delimiter = table_delimiter(header_line);
    lines
        .into_iter()
        .skip(header_index + 1)
        .take(500)
        .map(|line| split_delimited_line(line, delimiter))
        .filter(|row| row.iter().any(|value| !value.trim().is_empty()))
        .map(|mut row| {
            row.truncate(columns.len());
            while row.len() < columns.len() {
                row.push(String::new());
            }
            row
        })
        .collect()
}

fn redacted_content_sample_excerpt(sample_text: &str) -> String {
    let mut excerpt = String::new();
    for (line_index, line) in sample_text.lines().filter(|line| !line.trim().is_empty()).enumerate()
    {
        if line_index >= 50 || excerpt.chars().count() >= 8192 {
            break;
        }
        let delimiter = table_delimiter(line);
        let redacted_line = split_delimited_line(line, delimiter)
            .into_iter()
            .map(|cell| redact_sensitive_cell(&cell))
            .collect::<Vec<_>>()
            .join(&delimiter.to_string());
        if !excerpt.is_empty() {
            excerpt.push('\n');
        }
        excerpt.push_str(&redacted_line);
    }
    excerpt.chars().take(8192).collect()
}

fn redact_sensitive_cell(value: &str) -> String {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return String::new();
    }
    if looks_like_email(trimmed) {
        return "[redacted-email]".to_owned();
    }
    if contains_korean_rrn(trimmed) {
        return "[redacted-korean-rrn]".to_owned();
    }
    if looks_like_korean_name(trimmed) {
        return "[redacted-name]".to_owned();
    }
    trimmed.chars().take(256).collect()
}

fn looks_like_email(value: &str) -> bool {
    let lower = value.to_ascii_lowercase();
    let Some((local, domain)) = lower.split_once('@') else {
        return false;
    };
    !local.is_empty()
        && domain.contains('.')
        && domain
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '-' | '.'))
}

fn contains_korean_rrn(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.windows(14).any(|window| {
        window[..6].iter().all(u8::is_ascii_digit)
            && window[6] == b'-'
            && window[7..].iter().all(u8::is_ascii_digit)
    })
}

fn looks_like_korean_name(value: &str) -> bool {
    let count = value.chars().count();
    (2..=4).contains(&count)
        && value
            .chars()
            .all(|ch| ('\u{ac00}'..='\u{d7a3}').contains(&ch))
}

fn table_delimiter(first_line: &str) -> char {
    if first_line.contains('\t') {
        '\t'
    } else if first_line.contains(';') {
        ';'
    } else {
        ','
    }
}

fn split_delimited_line(line: &str, delimiter: char) -> Vec<String> {
    let mut cells = Vec::new();
    let mut current = String::new();
    let mut chars = line.chars().peekable();
    let mut in_quotes = false;
    while let Some(ch) = chars.next() {
        if ch == '"' {
            if in_quotes && chars.peek() == Some(&'"') {
                current.push('"');
                chars.next();
            } else {
                in_quotes = !in_quotes;
            }
        } else if ch == delimiter && !in_quotes {
            cells.push(current.trim().to_owned());
            current.clear();
        } else {
            current.push(ch);
        }
    }
    cells.push(current.trim().to_owned());
    cells
}

fn row_payload_json(columns: &[String], row: &[String]) -> Result<String, String> {
    let mut payload = serde_json::Map::new();
    for (index, column) in columns.iter().enumerate() {
        let key = clean(column.clone());
        if key.is_empty() {
            continue;
        }
        payload.insert(
            key,
            serde_json::Value::String(row.get(index).cloned().unwrap_or_default()),
        );
    }
    serde_json::to_string(&serde_json::Value::Object(payload))
        .map_err(|_| "archive_staging_payload_encode_failed".to_owned())
}

fn value_for_target_field(
    columns: &[String],
    row: &[String],
    field_mappings: &[FieldMapping],
    target_field: &str,
    fallback_aliases: &[&str],
) -> Option<String> {
    field_mappings
        .iter()
        .find(|mapping| {
            mapping.target_field == target_field
                && !matches!(
                    mapping.status,
                    FieldMappingStatus::Ignored | FieldMappingStatus::NeedsReview
                )
        })
        .and_then(|mapping| {
            columns
                .iter()
                .position(|column| column == &mapping.source_column)
                .and_then(|index| row.get(index))
        })
        .map(|value| clean(value.clone()))
        .filter(|value| !value.is_empty())
        .or_else(|| value_for_column(columns, row, fallback_aliases))
}

fn value_for_column(columns: &[String], row: &[String], aliases: &[&str]) -> Option<String> {
    columns
        .iter()
        .enumerate()
        .find(|(_, column)| column_matches(column, aliases))
        .and_then(|(index, _)| row.get(index))
        .map(|value| clean(value.clone()))
        .filter(|value| !value.is_empty())
}

fn column_matches(column: &str, aliases: &[&str]) -> bool {
    let normalized = column.trim().to_lowercase().replace(['_', '-'], " ");
    aliases.iter().any(|alias| normalized.contains(alias))
}

fn normalized_numeric_text(value: &str) -> Option<String> {
    let cleaned = value
        .trim()
        .replace(',', "")
        .replace('₩', "")
        .replace('원', "");
    if cleaned.is_empty() {
        return None;
    }
    let mut has_digit = false;
    for (index, ch) in cleaned.chars().enumerate() {
        if ch.is_ascii_digit() {
            has_digit = true;
        } else if ch == '.' {
            continue;
        } else if ch == '-' && index == 0 {
            continue;
        } else {
            return None;
        }
    }
    has_digit.then_some(cleaned)
}

fn normalized_date_text(value: &str) -> Option<String> {
    let cleaned = value.trim();
    if cleaned.len() == 10
        && cleaned.as_bytes().get(4) == Some(&b'-')
        && cleaned.as_bytes().get(7) == Some(&b'-')
        && cleaned
            .chars()
            .enumerate()
            .all(|(index, ch)| index == 4 || index == 7 || ch.is_ascii_digit())
    {
        Some(cleaned.to_owned())
    } else {
        None
    }
}

fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

fn normalized_stored_file_name(family: &FileFamily, id_seed: u128, file_type: &str) -> String {
    let extension = stable_key(file_type);
    if extension.is_empty() || extension == "unknown" {
        format!("{}-{}", family.prefix(), id_seed)
    } else {
        format!("{}-{}.{}", family.prefix(), id_seed, extension)
    }
}

fn contains_any(value: &str, needles: &[&str]) -> bool {
    needles.iter().any(|needle| value.contains(needle))
}

fn stable_key(value: &str) -> String {
    value
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() {
                ch.to_ascii_lowercase()
            } else {
                '-'
            }
        })
        .collect::<String>()
        .trim_matches('-')
        .to_owned()
}

fn encode_columns_json(columns: &[String]) -> Result<String, String> {
    serde_json::to_string(columns).map_err(|_| "archive_columns_encode_failed".to_owned())
}

fn decode_columns_json(value: &str) -> Result<Vec<String>, String> {
    serde_json::from_str::<Vec<String>>(value)
        .map_err(|_| "archive_postgres_columns_decode_failed".to_owned())
}

fn issue_item_id(prefix: &str, code: &str, column: &str) -> String {
    let column_key = stable_key(column);
    if column_key.is_empty() {
        format!("{prefix}-{}", stable_key(code))
    } else {
        format!("{prefix}-{}-{column_key}", stable_key(code))
    }
}

fn issue_prompt(code: &str, column: &str) -> String {
    let column = column.trim();
    if column.is_empty() {
        code.to_owned()
    } else {
        format!("{code}:{column}")
    }
}

fn load_store(path: &Path) -> Result<ArchiveIntakeStore, String> {
    if !path.exists() {
        return Ok(empty_store());
    }
    let body = fs::read_to_string(path).map_err(|error| error.to_string())?;
    let mut store =
        serde_json::from_str::<ArchiveIntakeStore>(&body).map_err(|error| error.to_string())?;
    for record in &mut store.intakes {
        normalize_loaded_record(record);
    }
    sort_intakes(&mut store);
    Ok(store)
}

fn save_store(path: &Path, store: &ArchiveIntakeStore) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    let body = serde_json::to_string_pretty(store).map_err(|error| error.to_string())?;
    fs::write(path, format!("{body}\n")).map_err(|error| error.to_string())
}

fn empty_store() -> ArchiveIntakeStore {
    ArchiveIntakeStore {
        schema: ARCHIVE_INTAKE_STORE_SCHEMA.to_owned(),
        intakes: Vec::new(),
    }
}

fn sort_intakes(store: &mut ArchiveIntakeStore) {
    store.intakes.sort_by(|left, right| {
        right
            .updated_at_unix
            .cmp(&left.updated_at_unix)
            .then(left.original_file_name.cmp(&right.original_file_name))
    });
}

fn read_input() -> Result<ArchiveIntakeInput, String> {
    let mut body = String::new();
    io::stdin()
        .read_to_string(&mut body)
        .map_err(|error| error.to_string())?;
    serde_json::from_str(&body).map_err(|error| error.to_string())
}

fn read_resolution_input() -> Result<ArchiveIssueResolutionInput, String> {
    let mut body = String::new();
    io::stdin()
        .read_to_string(&mut body)
        .map_err(|error| error.to_string())?;
    serde_json::from_str(&body).map_err(|error| error.to_string())
}

fn read_field_mapping_input() -> Result<ArchiveFieldMappingInput, String> {
    let mut body = String::new();
    io::stdin()
        .read_to_string(&mut body)
        .map_err(|error| error.to_string())?;
    serde_json::from_str(&body).map_err(|error| error.to_string())
}

fn read_rollback_input() -> Result<ArchiveRollbackInput, String> {
    let mut body = String::new();
    io::stdin()
        .read_to_string(&mut body)
        .map_err(|error| error.to_string())?;
    if body.trim().is_empty() {
        return Ok(ArchiveRollbackInput {
            reason: None,
            recovery_point_id: None,
        });
    }
    serde_json::from_str(&body).map_err(|error| error.to_string())
}

fn read_source_sync_completion_input() -> Result<ArchiveSourceSyncCompletionInput, String> {
    let mut body = String::new();
    io::stdin()
        .read_to_string(&mut body)
        .map_err(|error| error.to_string())?;
    serde_json::from_str(&body).map_err(|error| error.to_string())
}

fn read_source_sync_failure_input() -> Result<ArchiveSourceSyncFailureInput, String> {
    let mut body = String::new();
    io::stdin()
        .read_to_string(&mut body)
        .map_err(|error| error.to_string())?;
    serde_json::from_str(&body).map_err(|error| error.to_string())
}

fn required_field(value: Option<String>, name: &str) -> Result<String, String> {
    value
        .map(clean)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| format!("missing required intake field: {name}"))
}

fn clean(value: String) -> String {
    value.trim().to_owned()
}

fn store_path() -> Result<PathBuf, String> {
    local_review_store_path(
        std::env::var("BITWEEN_ALLOW_LOCAL_REVIEW_STORE").ok().as_deref(),
        std::env::var("BITWEEN_ARCHIVE_INTAKE_STORE").ok(),
    )
}

fn local_review_store_path(
    allow_local_review_store: Option<&str>,
    configured_path: Option<String>,
) -> Result<PathBuf, String> {
    if !truthy(allow_local_review_store) {
        return Err(
            "PostgreSQL relational archive intake storage is required; set BITWEEN_POSTGRES_DSN for production wiring or BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true only for hermetic local review."
                .to_owned(),
        );
    }
    Ok(configured_path
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(".bitween/local-review/archive/intake.json")))
}

fn truthy(value: Option<&str>) -> bool {
    matches!(
        value.map(str::trim).map(str::to_ascii_lowercase).as_deref(),
        Some("1" | "true" | "yes" | "on")
    )
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
        .unwrap_or_else(|| "archive-intake-store".to_owned())
}

fn postgres_failure(failure: PostgresConnectionFailure) -> String {
    format!("{} ({})", failure.code, failure.redacted_dsn)
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

    fn staged_rows_for_record(
        database_target: &DatabaseTarget,
        columns: &[String],
        sample_text: &str,
    ) -> Result<Vec<StagedBusinessRow>, String> {
        let field_mappings = infer_field_mappings(database_target, columns);
        staged_rows_for_record_with_mappings(database_target, columns, sample_text, &field_mappings)
    }

    fn input(file_name: impl Into<String>, sample_text: impl Into<String>) -> ArchiveIntakeInput {
        ArchiveIntakeInput {
            file_name: Some(file_name.into()),
            file_type: None,
            file_size_bytes: Some(2048),
            content_sha256: Some(
                "d3b07384d113edec49eaa6238ad5ff00f8f1685d2d7ca21e8495a7c09f2c8f4b"
                    .to_owned(),
            ),
            sample_text: Some(sample_text.into()),
            object_uri: Some("rustfs://bitween-archive/quarantine/test-object".to_owned()),
            blob_uri: Some("rustfs://bitween-archive/quarantine/test-object".to_owned()),
        }
    }

    #[test]
    fn payroll_file_is_renamed_and_prepared_for_relational_staging() {
        let sample_text = "사번,성명,급여,공제\nACME-001,ACME_SAMPLE_EMPLOYEE,3000000,200000";
        let record = build_intake_record(
            input("June 급여.xlsx", sample_text),
            100,
            7,
        )
        .unwrap();

        assert_eq!(record.family, FileFamily::Payroll);
        assert_eq!(record.database_target, DatabaseTarget::PayrollInputStaging);
        assert_eq!(record.stored_file_name, "payroll-7.xlsx");
        assert_eq!(record.extracted_columns, vec!["사번", "성명", "급여", "공제"]);
        assert_eq!(
            record.object_uri,
            "rustfs://bitween-archive/quarantine/test-object"
        );
        assert_eq!(record.object_bucket, "bitween-archive");
        assert_eq!(record.object_key, "quarantine/test-object");
        assert_eq!(record.content_sample_sha256, sha256_hex(sample_text.as_bytes()));
        assert_eq!(record.content_sample_row_count, 1);
        assert_eq!(record.extraction_status, ArchiveExtractionStatus::Converted);
        assert!(record.postgres_ready);
        assert_eq!(record.status, ArchiveIntakeStatus::ReadyForStaging);
        assert_eq!(record.next_action, ArchiveIntakeAction::SaveToBusinessData);
        assert!(record.field_mappings.iter().any(|mapping| {
            mapping.source_column == "급여"
                && mapping.target_field == "gross_pay"
                && mapping.value_shape.as_deref() == Some("numeric_normalized")
        }));

        let api_body = serde_json::to_string(&record).unwrap();
        assert!(api_body.contains("content_sample_sha256"));
        assert!(api_body.contains("content_sample_row_count"));
        assert!(!api_body.contains("3000000"));
    }

    #[test]
    fn hr_file_missing_required_department_creates_mapping_guidance() {
        let record = build_intake_record(
            input("employee-roster.csv", "이름,특이값\nACME_SAMPLE_EMPLOYEE,ABC"),
            100,
            8,
        )
        .unwrap();

        assert_eq!(record.family, FileFamily::Hr);
        assert_eq!(record.database_target, DatabaseTarget::HrEmployeeStaging);
        assert_eq!(record.status, ArchiveIntakeStatus::NeedsGuidance);
        assert!(!record.postgres_ready);
        assert!(record.guidance_items.iter().any(|item| {
            item.code == GuidanceCode::ConfirmMissingRequiredData && item.column == "department"
        }));
        assert!(record.guidance_items.iter().any(|item| {
            item.code == GuidanceCode::ExplainColumn && item.column == "특이값"
        }));
        assert!(record.field_mappings.iter().any(|mapping| {
            mapping.source_column == "특이값"
                && mapping.target_field == "source_payload"
                && mapping.status == FieldMappingStatus::Preserved
                && mapping.value_shape.as_deref() == Some("identifier")
        }));
    }

    #[test]
    fn ready_payroll_sample_rows_are_translated_to_staging_payloads() {
        let columns = vec!["사번".to_owned(), "성명".to_owned(), "급여".to_owned(), "공제".to_owned()];
        let rows = staged_rows_for_record(
            &DatabaseTarget::PayrollInputStaging,
            &columns,
            "사번,성명,급여,공제\nACME-001,ACME_SAMPLE_EMPLOYEE,\"3,000,000\",200000",
        )
        .unwrap();

        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0].row_number, 1);
        assert_eq!(rows[0].employee_external_id.as_deref(), Some("ACME-001"));
        assert_eq!(rows[0].display_name.as_deref(), Some("ACME_SAMPLE_EMPLOYEE"));
        assert_eq!(rows[0].gross_pay.as_deref(), Some("3000000"));
        assert_eq!(rows[0].deduction_total.as_deref(), Some("200000"));
        assert_eq!(rows[0].row_hash.len(), 64);
        assert!(rows[0].row_payload_json.contains("\"급여\":\"3,000,000\""));
    }

    #[test]
    fn ready_hr_and_attendance_samples_translate_to_target_staging_fields() {
        let hr_columns = vec!["사번".to_owned(), "성명".to_owned(), "부서".to_owned(), "상태".to_owned()];
        let hr_rows = staged_rows_for_record(
            &DatabaseTarget::HrEmployeeStaging,
            &hr_columns,
            "사번,성명,부서,상태\nACME-002,Acme Operator,People,active",
        )
        .unwrap();
        assert_eq!(hr_rows[0].employee_external_id.as_deref(), Some("ACME-002"));
        assert_eq!(hr_rows[0].display_name.as_deref(), Some("Acme Operator"));
        assert_eq!(hr_rows[0].department.as_deref(), Some("People"));
        assert_eq!(hr_rows[0].employment_status.as_deref(), Some("active"));

        let attendance_columns = vec!["사번".to_owned(), "근무일".to_owned(), "시간".to_owned()];
        let attendance_rows = staged_rows_for_record(
            &DatabaseTarget::HrAttendanceStaging,
            &attendance_columns,
            "사번,근무일,시간\nACME-002,2026-06-10,8",
        )
        .unwrap();
        assert_eq!(
            attendance_rows[0].employee_external_id.as_deref(),
            Some("ACME-002")
        );
        assert_eq!(attendance_rows[0].work_date.as_deref(), Some("2026-06-10"));
    }

    #[test]
    fn unresolved_mapping_samples_do_not_stage_business_rows() {
        let rows = staged_rows_for_record(
            &DatabaseTarget::NeedsMapping,
            &["Alpha".to_owned(), "Beta".to_owned()],
            "Alpha,Beta\n1,2",
        )
        .unwrap();
        assert!(rows.is_empty());
    }

    #[test]
    fn local_field_mapping_promotes_required_target_and_replays_staging_fields() {
        let record = build_intake_record(
            input("June 급여.csv", "직원키,지급액\nACME-001,3000000"),
            100,
            8,
        )
        .unwrap();
        assert_eq!(record.status, ArchiveIntakeStatus::NeedsGuidance);
        assert!(!record.postgres_ready);
        let mut store = ArchiveIntakeStore {
            schema: ARCHIVE_INTAKE_STORE_SCHEMA.to_owned(),
            intakes: vec![record],
        };

        let fingerprint = store.intakes[0].source_fingerprint.clone();
        apply_local_field_mappings(
            &mut store,
            "intake-8",
            ArchiveFieldMappingInput {
                source_fingerprint: fingerprint,
                mappings: vec![FieldMappingDecisionInput {
                    source_column: "직원키".to_owned(),
                    target_table: DatabaseTarget::PayrollInputStaging,
                    target_field: "employee_external_id".to_owned(),
                    status: FieldMappingStatus::Confirmed,
                    ignore_reason: None,
                }],
            },
            200,
        )
        .unwrap();

        let record = &store.intakes[0];
        assert!(record.guidance_items.is_empty());
        assert_eq!(record.status, ArchiveIntakeStatus::ReadyForStaging);
        assert_eq!(record.next_action, ArchiveIntakeAction::SaveToBusinessData);
        assert!(record.postgres_ready);
        assert_eq!(record.updated_at_unix, 200);
        let rows = staged_rows_for_record_with_mappings(
            &record.database_target,
            &record.extracted_columns,
            "직원키,지급액\nACME-001,3000000",
            &record.field_mappings,
        )
        .unwrap();
        assert_eq!(rows[0].employee_external_id.as_deref(), Some("ACME-001"));
        assert_eq!(rows[0].gross_pay.as_deref(), Some("3000000"));
    }

    #[test]
    fn unclear_optional_columns_require_explicit_source_payload_or_ignore_decision() {
        let record = build_intake_record(
            input("employee-roster.csv", "이름,조직,메모\nACME_SAMPLE_EMPLOYEE,People,Needs follow up"),
            100,
            18,
        )
        .unwrap();
        assert_eq!(record.status, ArchiveIntakeStatus::NeedsGuidance);
        assert!(record.guidance_items.iter().any(|item| {
            item.code == GuidanceCode::ExplainColumn && item.column == "메모"
        }));
        let mut store = ArchiveIntakeStore {
            schema: ARCHIVE_INTAKE_STORE_SCHEMA.to_owned(),
            intakes: vec![record],
        };
        let fingerprint = store.intakes[0].source_fingerprint.clone();
        apply_local_field_mappings(
            &mut store,
            "intake-18",
            ArchiveFieldMappingInput {
                source_fingerprint: fingerprint,
                mappings: vec![FieldMappingDecisionInput {
                    source_column: "메모".to_owned(),
                    target_table: DatabaseTarget::HrEmployeeStaging,
                    target_field: "source_payload".to_owned(),
                    status: FieldMappingStatus::Confirmed,
                    ignore_reason: None,
                }],
            },
            200,
        )
        .unwrap();
        assert!(store.intakes[0].guidance_items.is_empty());
        assert_eq!(store.intakes[0].status, ArchiveIntakeStatus::ReadyForStaging);
    }

    #[test]
    fn csv_preamble_rows_are_skipped_before_schema_mapping() {
        let sample = "근로자 명부\n작성일,2026-06-10\n이름,조직,메모\nACME_SAMPLE_EMPLOYEE,People,Follow up";
        let record = build_intake_record(input("employee-roster.csv", sample), 100, 19).unwrap();

        assert_eq!(record.extracted_columns, vec!["이름", "조직", "메모"]);
        assert_eq!(record.content_sample_row_count, 1);
        assert_eq!(record.database_target, DatabaseTarget::HrEmployeeStaging);
        assert!(record.guidance_items.iter().any(|item| {
            item.code == GuidanceCode::ExplainColumn && item.column == "메모"
        }));
        let rows = staged_rows_for_record_with_mappings(
            &record.database_target,
            &record.extracted_columns,
            sample,
            &record.field_mappings,
        )
        .unwrap();
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0].display_name.as_deref(), Some("ACME_SAMPLE_EMPLOYEE"));
        assert_eq!(rows[0].department.as_deref(), Some("People"));
    }

    #[test]
    fn issue_resolution_requires_actionable_issue_identity() {
        let error = normalized_issue_type(&ArchiveIssueResolutionInput {
            issue_type: Some("security".to_owned()),
            issue_id: None,
            code: Some("explain_column".to_owned()),
            column: Some("조직".to_owned()),
            decision: None,
            note: None,
        })
        .unwrap_err();
        assert_eq!(error, "archive_issue_type_unsupported");

        let error = normalized_issue_code(&ArchiveIssueResolutionInput {
            issue_type: Some("guidance".to_owned()),
            issue_id: None,
            code: Some(" ".to_owned()),
            column: Some("조직".to_owned()),
            decision: None,
            note: None,
        })
        .unwrap_err();
        assert_eq!(error, "archive_issue_code_required");
    }

    #[test]
    fn issue_resolution_audit_is_bounded_and_sanitized() {
        let long_note = "a".repeat(700);
        let body = issue_resolution_json(
            &ArchiveIssueResolutionInput {
                issue_type: Some("guidance".to_owned()),
                issue_id: None,
                code: Some("explain_column".to_owned()),
                column: Some("조직".to_owned()),
                decision: Some(" confirmed_by_operator ".to_owned()),
                note: Some(long_note),
            },
            " operator-acme ",
        )
        .unwrap();
        let value: serde_json::Value = serde_json::from_str(&body).unwrap();
        assert_eq!(value["decision"], "confirmed_by_operator");
        assert_eq!(value["resolved_by"], "operator-acme");
        assert_eq!(value["note"].as_str().unwrap().len(), 512);
    }

    #[test]
    fn unclassified_table_is_accepted_as_blob_with_mapping_question() {
        let record = build_intake_record(input("sheet.csv", "Alpha,Beta\n1,2"), 100, 9).unwrap();

        assert_eq!(record.family, FileFamily::Unknown);
        assert_eq!(record.database_target, DatabaseTarget::NeedsMapping);
        assert_eq!(record.status, ArchiveIntakeStatus::NeedsGuidance);
        assert!(record.guidance_items.iter().any(|item| {
            item.code == GuidanceCode::ChooseBusinessArea
        }));
    }

    #[test]
    fn arbitrary_non_tabular_file_stays_in_archive_without_postgres_admission() {
        let record = build_intake_record(input("scan.pdf", ""), 100, 11).unwrap();

        assert_eq!(record.family, FileFamily::GeneralArchive);
        assert_eq!(record.database_target, DatabaseTarget::ArchiveBlob);
        assert_eq!(record.status, ArchiveIntakeStatus::Archived);
        assert_eq!(record.content_sample_row_count, 0);
        assert_eq!(record.extraction_status, ArchiveExtractionStatus::NotApplicable);
        assert!(!record.postgres_ready);
        assert!(record.guidance_items.is_empty());
    }

    #[test]
    fn content_sample_excerpt_is_bounded_redacted_and_not_binary_snapshot() {
        let resident_number = format!("{}-{}", "900101", "1234567");
        let sample_text = format!(
            "성명,주민등록번호,이메일,급여\n{},{},worker@example.com,3000000\n{}",
            "홍길동",
            resident_number,
            "a".repeat(9000)
        );

        let excerpt = redacted_content_sample_excerpt(&sample_text);

        assert!(excerpt.len() <= 8192);
        assert!(excerpt.contains("[redacted-name]"));
        assert!(excerpt.contains("[redacted-korean-rrn]"));
        assert!(excerpt.contains("[redacted-email]"));
        assert!(!excerpt.contains(&resident_number));
        assert!(!excerpt.contains("worker@example.com"));
        assert!(!excerpt.contains("홍길동"));
    }

    #[test]
    fn empty_or_oversized_file_is_fault_tolerant_and_blocked_for_review() {
        let record = build_intake_record(
            ArchiveIntakeInput {
                file_name: Some("attendance.csv".to_owned()),
                file_type: None,
                file_size_bytes: Some(0),
                content_sha256: Some(
                    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                        .to_owned(),
                ),
                sample_text: Some("name,date\n".to_owned()),
                object_uri: Some("rustfs://bitween-archive/quarantine/empty-object".to_owned()),
                blob_uri: Some("rustfs://bitween-archive/quarantine/empty-object".to_owned()),
            },
            100,
            10,
        )
        .unwrap();

        assert_eq!(record.status, ArchiveIntakeStatus::NeedsGuidance);
        assert!(record.anomalies.iter().any(|item| item.code == AnomalyCode::EmptyFile));
        assert!(record.guidance_items.iter().any(|item| {
            item.code == GuidanceCode::ConfirmMissingRequiredData
        }));
    }

    #[test]
    fn rustfs_object_uri_is_required_for_blob_storage_before_postgres_review() {
        let error = build_intake_record(
            ArchiveIntakeInput {
                file_name: Some("payroll.csv".to_owned()),
                file_type: None,
                file_size_bytes: Some(10),
                content_sha256: Some(
                    "d3b07384d113edec49eaa6238ad5ff00f8f1685d2d7ca21e8495a7c09f2c8f4b"
                        .to_owned(),
                ),
                sample_text: Some("name,pay\nACME_SAMPLE_EMPLOYEE,1".to_owned()),
                object_uri: Some("file:///tmp/payroll.csv".to_owned()),
                blob_uri: None,
            },
            100,
            12,
        )
        .unwrap_err();

        assert!(error.contains("rustfs://"));
    }

    #[test]
    fn local_file_store_requires_explicit_hermetic_review_flag() {
        let error = local_review_store_path(None, None).unwrap_err();
        assert!(error.contains("PostgreSQL relational archive intake storage is required"));
        assert_eq!(
            local_review_store_path(Some("true"), None).unwrap(),
            PathBuf::from(".bitween/local-review/archive/intake.json")
        );
        assert_eq!(
            local_review_store_path(Some("yes"), Some("/tmp/archive.json".to_owned())).unwrap(),
            PathBuf::from("/tmp/archive.json")
        );
    }

    #[test]
    fn archive_postgres_enum_mapping_is_snake_case_and_fail_closed() {
        assert_eq!(FileFamily::Payroll.as_postgres_value(), "payroll");
        assert_eq!(
            DatabaseTarget::HrEmployeeStaging.as_postgres_value(),
            "hr_employee_staging"
        );
        assert_eq!(
            ArchiveIntakeStatus::NeedsGuidance.as_postgres_value(),
            "needs_guidance"
        );
        assert_eq!(
            ArchiveIntakeAction::SaveToBusinessData.as_postgres_value(),
            "save_to_business_data"
        );
        assert_eq!(
            GuidanceCode::ConfirmMissingRequiredData.as_postgres_value(),
            "confirm_missing_required_data"
        );
        assert_eq!(AnomalyCode::NoRowsDetected.as_postgres_value(), "no_rows_detected");
        assert_eq!(GuidanceSeverity::Blocking.as_postgres_value(), "blocking");

        assert_eq!(
            FileFamily::from_postgres_value("general_archive").unwrap(),
            FileFamily::GeneralArchive
        );
        assert_eq!(
            DatabaseTarget::from_postgres_value("payroll_input_staging").unwrap(),
            DatabaseTarget::PayrollInputStaging
        );
        assert_eq!(
            ArchiveIntakeStatus::from_postgres_value("admitted").unwrap(),
            ArchiveIntakeStatus::Admitted
        );
        assert_eq!(
            ArchiveIntakeStatus::from_postgres_value("rejected").unwrap(),
            ArchiveIntakeStatus::Rejected
        );
        assert!(GuidanceCode::from_postgres_value("custom").is_err());
        assert!(AnomalyCode::from_postgres_value("custom").is_err());
        assert!(GuidanceSeverity::from_postgres_value("critical").is_err());
    }

    #[test]
    fn canonical_admission_paths_cover_all_staging_targets() {
        let source = include_str!("archive_intake_store.rs");

        assert!(source.contains("admit_postgres_hr_employee_staging"));
        assert!(source.contains("admit_postgres_hr_attendance_staging"));
        assert!(source.contains("admit_postgres_payroll_input_staging"));
        assert!(source.contains("archive_admission_recovery_point"));
        assert!(source.contains("before_payload"));
        assert!(source.contains("after_payload"));
        assert!(source.contains("ON CONFLICT (tenant_id, legal_entity_id, workplace_id, employee_key) DO UPDATE"));
        assert!(source.contains("archive_source_sync"));
        assert!(source.contains("bitween_hr.employee"));
        assert!(source.contains("bitween_hr.attendance_record"));
        assert!(source.contains("bitween_payroll.payroll_input"));
        assert!(source.contains("archive_admission_audit"));
        assert!(source.contains("archive_postgres_admission_requires_ready_review"));
    }

    #[test]
    fn canonical_rollback_paths_cover_all_staging_targets() {
        let source = include_str!("archive_intake_store.rs");

        assert!(source.contains("rollback_postgres_intake"));
        assert!(source.contains("archive_admission_rollback"));
        assert!(source.contains("reverse_postgres_hr_employee_admission"));
        assert!(source.contains("reverse_postgres_hr_attendance_admission"));
        assert!(source.contains("reverse_postgres_payroll_input_admission"));
        assert!(source.contains("recovery_status = 'restored'"));
        assert!(source.contains("admission_status = 'reversed'"));
        assert!(source.contains("validation_status = 'valid'"));
        assert!(source.contains("recovery_point_id"));
        assert!(source.contains("archive_postgres_rollback_requires_completed_admission"));
    }

    #[test]
    fn source_sync_plan_generates_excel_compatible_rustfs_artifact_without_binary_snapshot() {
        let pending = ArchiveSourceSyncPendingRow {
            sync_item_id: "00000000-0000-0000-0000-000000000001".to_owned(),
            intake_id: "00000000-0000-0000-0000-000000000002".to_owned(),
            source_version: 3,
            target_table: "hr_employee".to_owned(),
            operation: "admission".to_owned(),
            source_object_uri: "rustfs://bitween-archive/quarantine/acme-roster.xlsx".to_owned(),
            change_payload: serde_json::json!({
                "admitted_rows": 1,
                "rejected_rows": 0,
                "reversed_rows": 0,
                "binary_snapshot_stored": false,
                "postgres_payload": "row_delta_json",
                "workbook_strategy": "immutable_original_plus_derived_rustfs_version"
            }),
            workbook_rows: vec![serde_json::json!({
                "row_number": 1,
                "validation_status": "admitted",
                "employee_external_id": "E-100",
                "display_name": "ACME_SAMPLE_EMPLOYEE",
                "department": "People",
                "row_hash": "row-hash"
            })],
            created_by: "payroll_manager".to_owned(),
        };

        let item = build_source_sync_plan_item(&pending, "bitween-archive").unwrap();

        assert_eq!(item.content_type, ARCHIVE_SOURCE_SYNC_CONTENT_TYPE);
        assert_eq!(item.generated_object_uri, format!("rustfs://bitween-archive/{}", item.object_key));
        assert!(item.object_key.starts_with("derived/00000000-0000-0000-0000-000000000002/3/"));
        assert_eq!(item.content_sha256, hex_sha256(item.body_text.as_bytes()));
        assert!(item.body_text.contains("<?mso-application progid=\"Excel.Sheet\"?>"));
        assert!(item.body_text.contains("binary_snapshot_stored"));
        assert!(item.body_text.contains(">false<"));
        assert!(item.body_text.contains("ACME_SAMPLE_EMPLOYEE"));
        assert!(!item.body_text.to_ascii_lowercase().contains("ss:type=\"binary\""));
    }

    #[test]
    fn source_sync_completion_requires_immutable_rustfs_object_metadata() {
        assert_eq!(
            validate_source_sync_completion(ArchiveSourceSyncCompletionInput {
                sync_item_id: Some("sync-id".to_owned()),
                generated_object_uri: Some("rustfs://bitween-archive/derived/source.xml".to_owned()),
                content_sha256: Some("a".repeat(64)),
                file_size_bytes: Some(128),
            })
            .unwrap()
            .file_size_bytes,
            128
        );
        assert!(
            validate_source_sync_completion(ArchiveSourceSyncCompletionInput {
                sync_item_id: Some("sync-id".to_owned()),
                generated_object_uri: Some("file:///tmp/source.xml".to_owned()),
                content_sha256: Some("a".repeat(64)),
                file_size_bytes: Some(128),
            })
            .is_err()
        );
        assert!(
            validate_source_sync_completion(ArchiveSourceSyncCompletionInput {
                sync_item_id: Some("sync-id".to_owned()),
                generated_object_uri: Some("rustfs://bitween-archive/derived/source.xml".to_owned()),
                content_sha256: Some("not-a-checksum".to_owned()),
                file_size_bytes: Some(128),
            })
            .is_err()
        );
        let pending = ArchiveSourceSyncPendingRow {
            sync_item_id: "sync-id".to_owned(),
            intake_id: "intake-id".to_owned(),
            source_version: 1,
            target_table: "hr_employee".to_owned(),
            operation: "admission".to_owned(),
            source_object_uri: "rustfs://bitween-archive/quarantine/source.xlsx".to_owned(),
            change_payload: serde_json::json!({ "binary_snapshot_stored": false }),
            workbook_rows: Vec::new(),
            created_by: "payroll_manager".to_owned(),
        };
        let expected_uri = format!(
            "rustfs://bitween-archive/{}",
            source_sync_object_key(&pending)
        );
        assert!(
            validate_source_sync_completion_for_pending(
                ArchiveSourceSyncCompletionInput {
                    sync_item_id: Some("sync-id".to_owned()),
                    generated_object_uri: Some(expected_uri),
                    content_sha256: Some("a".repeat(64)),
                    file_size_bytes: Some(128),
                },
                &pending,
                "bitween-archive",
            )
            .is_ok()
        );
        assert!(
            validate_source_sync_completion_for_pending(
                ArchiveSourceSyncCompletionInput {
                    sync_item_id: Some("sync-id".to_owned()),
                    generated_object_uri: Some("rustfs://bitween-archive/derived/other.xml".to_owned()),
                    content_sha256: Some("a".repeat(64)),
                    file_size_bytes: Some(128),
                },
                &pending,
                "bitween-archive",
            )
            .is_err()
        );
        assert_eq!(
            validate_source_sync_failure(ArchiveSourceSyncFailureInput {
                sync_item_id: Some("sync-id".to_owned()),
                error: Some("x".repeat(700)),
            })
            .unwrap()
            .error
            .len(),
            512
        );
    }

    #[test]
    fn source_sync_bucket_requires_explicit_valid_rustfs_archive_bucket() {
        assert_eq!(
            source_sync_bucket_from_parts(None, Some("bitween-archive-originals".to_owned()))
                .unwrap(),
            "bitween-archive-originals"
        );
        assert_eq!(
            source_sync_bucket_from_parts(
                Some("bitween-archive-runtime".to_owned()),
                Some("bitween-archive-originals".to_owned()),
            )
            .unwrap(),
            "bitween-archive-runtime"
        );
        assert_eq!(
            source_sync_bucket_from_parts(None, None).unwrap_err(),
            "archive_source_sync_rustfs_bucket_required"
        );
        assert_eq!(
            source_sync_bucket_from_parts(Some("Bitween Archive".to_owned()), None).unwrap_err(),
            "archive_source_sync_rustfs_bucket_invalid"
        );
    }

    #[test]
    fn rollback_reason_is_defaulted_bounded_and_sanitized() {
        assert_eq!(
            rollback_reason(ArchiveRollbackInput {
                reason: None,
                recovery_point_id: None
            }),
            "operator_requested"
        );
        assert_eq!(
            rollback_reason(ArchiveRollbackInput {
                reason: Some("  duplicate upload  ".to_owned()),
                recovery_point_id: None
            }),
            "duplicate upload"
        );
        assert_eq!(
            rollback_reason(ArchiveRollbackInput {
                reason: Some("x".repeat(600)),
                recovery_point_id: Some("recovery-point-id".to_owned())
            })
            .len(),
            512
        );
        assert_eq!(
            rollback_recovery_point_id(&ArchiveRollbackInput {
                reason: None,
                recovery_point_id: Some("  recovery-point-id  ".to_owned())
            }),
            "recovery-point-id"
        );
    }

    #[test]
    fn archive_postgres_columns_json_round_trips_without_user_data() {
        let columns = vec!["성명".to_owned(), "급여".to_owned(), "공제".to_owned()];
        let encoded = encode_columns_json(&columns).unwrap();
        assert_eq!(decode_columns_json(&encoded).unwrap(), columns);
        assert!(decode_columns_json("{bad-json").is_err());
    }
}
