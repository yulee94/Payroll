//! Dedicated monthly payroll-ledger importer.
//!
//! The generic archive intake mangles payroll ledgers that use a
//! two-row-per-worker bilingual layout, so this bin takes already-parsed
//! per-worker figures on stdin and upserts exactly ONE
//! `bitween_payroll.payroll_input` row per worker, carrying the per-component
//! breakdown in `source_payload`.
//!
//! Input contract (stdin JSON):
//! ```json
//! {
//!   "period": "2026-05",
//!   "source_file": "5월 급여대장.xlsx",
//!   "workers": [
//!     {
//!       "name": "...", "employee_key": "employee-...", (optional)
//!       "gross": 4538380, "income_tax": 265650, "local_income_tax": 26560,
//!       "health_insurance": 174540, "national_pension": 224720,
//!       "employment_insurance": 40840, "total_deductions": 732310, "net": 3806070
//!     }
//!   ]
//! }
//! ```
//!
//! `payroll_input.source_intake_id` is a NOT NULL FK into
//! `bitween_archive.archive_intake`, so the importer first ensures a dedicated
//! ledger-import intake row exists (keyed deterministically by content hash),
//! then references it from every payroll_input row.

use bitween_payroll_api::{
    PostgresClientSession, PostgresConnectionFailure, PostgresRepositoryConfig,
    PostgresTenantScope, required_postgres_migrations,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::io::{self, Read};
use std::process;

#[derive(Clone, Debug, Deserialize)]
struct LedgerImportInput {
    period: String,
    #[serde(default)]
    source_file: String,
    workers: Vec<LedgerWorkerInput>,
}

#[derive(Clone, Debug, Deserialize)]
struct LedgerWorkerInput {
    name: String,
    #[serde(default)]
    employee_key: Option<String>,
    #[serde(default, alias = "사번")]
    roster_id: Option<String>,
    gross: i64,
    income_tax: i64,
    local_income_tax: i64,
    health_insurance: i64,
    national_pension: i64,
    employment_insurance: i64,
    total_deductions: i64,
    net: i64,
}

#[derive(Clone, Debug, Serialize)]
struct LedgerImportResult {
    ok: bool,
    period: String,
    source_intake_id: String,
    imported: u64,
    workers: u64,
    gross_total: i64,
    deduction_total: i64,
    net_total: i64,
    warnings: Vec<String>,
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        process::exit(1);
    }
}

fn run() -> Result<(), String> {
    if !postgres_dsn_configured() {
        return Err(
            "payroll_ledger_import requires BITWEEN_POSTGRES_DSN and the canonical payroll_input table."
                .to_owned(),
        );
    }
    let input = read_input()?;
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|_| "payroll_ledger_import_runtime_failed".to_owned())?;
    let result = runtime.block_on(import(input))?;
    println!(
        "{}",
        serde_json::to_string(&result)
            .map_err(|_| "payroll_ledger_import_serialize_failed".to_owned())?
    );
    Ok(())
}

fn read_input() -> Result<LedgerImportInput, String> {
    let mut body = String::new();
    io::stdin()
        .read_to_string(&mut body)
        .map_err(|_| "payroll_ledger_import_stdin_read_failed".to_owned())?;
    let input: LedgerImportInput = serde_json::from_str(&body)
        .map_err(|_| "payroll_ledger_import_invalid_json".to_owned())?;
    validate_period(&input.period)?;
    if input.workers.is_empty() {
        return Err("payroll_ledger_import_no_workers".to_owned());
    }
    Ok(input)
}

fn validate_period(period: &str) -> Result<(), String> {
    let bytes = period.as_bytes();
    let well_formed = bytes.len() == 7
        && bytes[..4].iter().all(u8::is_ascii_digit)
        && bytes[4] == b'-'
        && bytes[5..].iter().all(u8::is_ascii_digit);
    if well_formed {
        Ok(())
    } else {
        Err("payroll_ledger_import_invalid_period".to_owned())
    }
}

async fn import(input: LedgerImportInput) -> Result<LedgerImportResult, String> {
    let session = connect_session().await?;
    let actor = postgres_actor();

    let content_sha256 = ledger_content_sha256(&input);
    let source_intake_id =
        ensure_ledger_intake(&session, &input, &content_sha256, &actor).await?;

    let mut warnings = Vec::new();
    let mut imported = 0u64;
    let mut gross_total = 0i64;
    let mut deduction_total = 0i64;
    let mut net_total = 0i64;
    let mut seen_keys = std::collections::BTreeSet::new();

    for worker in &input.workers {
        let employee_key = resolve_employee_key(worker, &input.period);
        if !seen_keys.insert(employee_key.clone()) {
            warnings.push(format!(
                "duplicate employee_key collapsed: {employee_key}"
            ));
        }
        let row_hash = worker_row_hash(&input.period, &employee_key, worker);
        let source_payload = serde_json::json!({
            "name": worker.name,
            "income_tax": worker.income_tax,
            "local_income_tax": worker.local_income_tax,
            "health_insurance": worker.health_insurance,
            "national_pension": worker.national_pension,
            "employment_insurance": worker.employment_insurance,
            "total_deductions": worker.total_deductions,
            "net": worker.net,
        })
        .to_string();

        // The payroll_input.deduction_total column is constrained to be
        // non-negative, but a small number of ledger workers carry a net
        // refund/correction (e.g. a negative insurance adjustment) so their
        // true total deduction is negative. Clamp the stored column to 0 to
        // satisfy the constraint and preserve the SIGNED truth in
        // source_payload.total_deductions, which is what reconciliation reads.
        let stored_deduction_total = worker.total_deductions.max(0);
        upsert_payroll_input(
            &session,
            &input.period,
            &employee_key,
            worker.gross,
            stored_deduction_total,
            &source_intake_id,
            &row_hash,
            &source_payload,
            &actor,
        )
        .await?;

        imported += 1;
        gross_total += worker.gross;
        // SIGNED economic total (matches source_payload.total_deductions);
        // intentionally distinct from the clamped (`max(0)`) DB column above.
        deduction_total += worker.total_deductions;
        net_total += worker.net;
    }

    Ok(LedgerImportResult {
        ok: true,
        period: input.period,
        source_intake_id,
        imported,
        workers: input.workers.len() as u64,
        gross_total,
        deduction_total,
        net_total,
        warnings,
    })
}

async fn connect_session() -> Result<PostgresClientSession, String> {
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

/// Ensure a dedicated ledger-import intake row exists for this period and source
/// content, returning its id. Idempotent on (tenant_id, content_sha256).
async fn ensure_ledger_intake(
    session: &PostgresClientSession,
    input: &LedgerImportInput,
    content_sha256: &str,
    actor: &str,
) -> Result<String, String> {
    if let Some(row) = session
        .client
        .query_opt(
            "SELECT id::text FROM bitween_archive.archive_intake \
             WHERE tenant_id = $1 AND content_sha256 = $2 \
             ORDER BY created_at ASC LIMIT 1",
            &[&session.scope.tenant_id, &content_sha256],
        )
        .await
        .map_err(|_| "payroll_ledger_import_intake_lookup_failed".to_owned())?
    {
        return Ok(row.get(0));
    }

    let original_file_name = if input.source_file.trim().is_empty() {
        format!("payroll-ledger-{}.import", input.period)
    } else {
        input.source_file.trim().to_owned()
    };
    let estimated_rows: i64 = input.workers.len() as i64;
    let empty_sample_sha = hex_sha256(&[]);
    let object_bucket = ledger_object_bucket();
    let object_key = format!("ledger-import/{}/{}", input.period, content_sha256);
    let object_uri = format!("rustfs://{object_bucket}/{object_key}");
    let row = session
        .client
        .query_one(
            "INSERT INTO bitween_archive.archive_intake ( \
                tenant_id, legal_entity_id, workplace_id, payroll_period, uploader_user_id, \
                original_file_name, stored_file_name, object_uri, object_bucket, object_key, \
                content_sha256, content_sample_sha256, content_sample_row_count, \
                extraction_status, content_type, file_size_bytes, family, database_target, \
                status, next_action, extracted_columns, estimated_rows, postgres_ready, sensitivity_label \
             ) VALUES ( \
                $1, $2, $3, $4, $5, \
                $6, $6, $7, $8, $9, \
                $10, $11, $12, \
                'converted', $13, 0, 'payroll', 'payroll_input_staging', \
                'admitted', 'save_to_business_data', '[]'::jsonb, $14, false, 'restricted' \
             ) RETURNING id::text",
            &[
                &session.scope.tenant_id,
                &session.scope.legal_entity_id,
                &session.scope.workplace_id,
                &input.period,
                &actor,
                &original_file_name,
                &object_uri,
                &object_bucket,
                &object_key,
                &content_sha256,
                &empty_sample_sha,
                &estimated_rows,
                &"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                &estimated_rows,
            ],
        )
        .await
        .map_err(|_| "payroll_ledger_import_intake_insert_failed".to_owned())?;
    Ok(row.get(0))
}

#[allow(clippy::too_many_arguments)]
async fn upsert_payroll_input(
    session: &PostgresClientSession,
    period: &str,
    employee_key: &str,
    gross_pay: i64,
    deduction_total: i64,
    source_intake_id: &str,
    source_row_hash: &str,
    source_payload: &str,
    actor: &str,
) -> Result<(), String> {
    session
        .client
        .execute(
            "INSERT INTO bitween_payroll.payroll_input ( \
                tenant_id, legal_entity_id, workplace_id, payroll_period, employee_key, \
                gross_pay, deduction_total, source_intake_id, source_row_hash, source_payload, \
                created_by, updated_by \
             ) VALUES ( \
                $1, $2, $3, $4, $5, \
                $6::text::numeric, $7::text::numeric, $8::text::uuid, $9, $10::text::jsonb, \
                $11, $11 \
             ) \
             ON CONFLICT (tenant_id, legal_entity_id, workplace_id, payroll_period, employee_key) \
             DO UPDATE SET \
                gross_pay = EXCLUDED.gross_pay, \
                deduction_total = EXCLUDED.deduction_total, \
                source_intake_id = EXCLUDED.source_intake_id, \
                source_row_hash = EXCLUDED.source_row_hash, \
                source_payload = EXCLUDED.source_payload, \
                admission_status = 'admitted', \
                updated_by = EXCLUDED.updated_by",
            &[
                &session.scope.tenant_id,
                &session.scope.legal_entity_id,
                &session.scope.workplace_id,
                &period,
                &employee_key,
                &gross_pay.to_string(),
                &deduction_total.to_string(),
                &source_intake_id,
                &source_row_hash,
                &source_payload,
                &actor,
            ],
        )
        .await
        .map_err(|_| "payroll_ledger_import_payroll_input_upsert_failed".to_owned())?;
    Ok(())
}

/// Derive a stable `employee-...` key satisfying the payroll_input regex.
///
/// Preference order: an explicitly supplied (already valid) employee_key, then
/// the roster 사번 (sanitized), else a deterministic name-based key. Korean
/// names cannot satisfy the ASCII regex, so the name path hashes the name into
/// the key while keeping it stable across re-imports.
fn resolve_employee_key(worker: &LedgerWorkerInput, period: &str) -> String {
    if let Some(key) = worker
        .employee_key
        .as_deref()
        .map(str::trim)
        .filter(|value| is_valid_employee_key(value))
    {
        return key.to_owned();
    }
    if let Some(roster_id) = worker.roster_id.as_deref().map(str::trim).filter(|value| !value.is_empty()) {
        let sanitized = sanitize_key_part(roster_id);
        if !sanitized.is_empty() {
            return format!("employee-{sanitized}");
        }
    }
    let digest = hex_sha256(worker.name.as_bytes());
    format!("employee-ledger-{}-{}", period.replace('-', ""), &digest[..16])
}

fn is_valid_employee_key(value: &str) -> bool {
    if let Some(rest) = value.strip_prefix("employee-") {
        !rest.is_empty()
            && rest.len() <= 96
            && rest
                .chars()
                .all(|ch| ch.is_ascii_alphanumeric() || ch == '_' || ch == '-')
    } else {
        false
    }
}

fn sanitize_key_part(value: &str) -> String {
    value
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || ch == '_' || ch == '-' {
                ch
            } else {
                '-'
            }
        })
        .collect::<String>()
        .trim_matches('-')
        .chars()
        .take(80)
        .collect()
}

fn worker_row_hash(period: &str, employee_key: &str, worker: &LedgerWorkerInput) -> String {
    let canonical = format!(
        "{period}|{employee_key}|{}|{}|{}|{}|{}|{}|{}|{}",
        worker.gross,
        worker.income_tax,
        worker.local_income_tax,
        worker.health_insurance,
        worker.national_pension,
        worker.employment_insurance,
        worker.total_deductions,
        worker.net,
    );
    hex_sha256(canonical.as_bytes())
}

fn ledger_object_bucket() -> String {
    std::env::var("BITWEEN_RUSTFS_BUCKET")
        .ok()
        .or_else(|| std::env::var("BITWEEN_RUSTFS_BUCKET_ARCHIVE").ok())
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "bitween-archive-originals".to_owned())
}

fn ledger_content_sha256(input: &LedgerImportInput) -> String {
    let canonical = format!(
        "payroll-ledger|{}|{}|{}",
        input.period,
        input.source_file.trim(),
        input.workers.len()
    );
    hex_sha256(canonical.as_bytes())
}

fn hex_sha256(data: &[u8]) -> String {
    let digest = Sha256::digest(data);
    digest.iter().map(|byte| format!("{byte:02x}")).collect()
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
        .unwrap_or_else(|| "payroll-ledger-import".to_owned())
}

fn postgres_failure(failure: PostgresConnectionFailure) -> String {
    format!("{} ({})", failure.code, failure.redacted_dsn)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn worker(name: &str) -> LedgerWorkerInput {
        LedgerWorkerInput {
            name: name.to_owned(),
            employee_key: None,
            roster_id: None,
            gross: 3_000_000,
            income_tax: 84_850,
            local_income_tax: 8_480,
            health_insurance: 106_350,
            national_pension: 135_000,
            employment_insurance: 27_000,
            total_deductions: 361_680,
            net: 2_638_320,
        }
    }

    #[test]
    fn period_validation_accepts_yyyy_dash_mm_only() {
        assert!(validate_period("2026-05").is_ok());
        assert!(validate_period("2026-5").is_err());
        assert!(validate_period("202605").is_err());
        assert!(validate_period("2026-13-01").is_err());
    }

    #[test]
    fn name_based_employee_key_is_ascii_safe_and_stable() {
        let w = worker("이름없는노동자");
        let key_a = resolve_employee_key(&w, "2026-05");
        let key_b = resolve_employee_key(&w, "2026-05");
        assert_eq!(key_a, key_b);
        assert!(is_valid_employee_key(&key_a), "{key_a}");
    }

    #[test]
    fn explicit_valid_employee_key_is_preferred() {
        let mut w = worker("Synthetic");
        w.employee_key = Some("employee-roster-0042".to_owned());
        assert_eq!(resolve_employee_key(&w, "2026-05"), "employee-roster-0042");
    }

    #[test]
    fn roster_id_is_sanitized_into_a_valid_key() {
        let mut w = worker("Synthetic");
        w.roster_id = Some("A-100/2".to_owned());
        let key = resolve_employee_key(&w, "2026-05");
        assert_eq!(key, "employee-A-100-2");
        assert!(is_valid_employee_key(&key));
    }

    #[test]
    fn invalid_explicit_key_falls_back_to_name_hash() {
        let mut w = worker("이름");
        w.employee_key = Some("not-an-employee-key".to_owned());
        let key = resolve_employee_key(&w, "2026-05");
        assert!(key.starts_with("employee-ledger-202605-"));
        assert!(is_valid_employee_key(&key));
    }

    #[test]
    fn row_hash_is_hex_sha256_and_deterministic() {
        let w = worker("Synthetic");
        let hash = worker_row_hash("2026-05", "employee-1", &w);
        assert_eq!(hash.len(), 64);
        assert!(hash.chars().all(|ch| ch.is_ascii_hexdigit()));
        assert_eq!(hash, worker_row_hash("2026-05", "employee-1", &w));
    }

    #[test]
    fn ledger_content_hash_changes_with_period_and_source() {
        let input_a = LedgerImportInput {
            period: "2026-05".to_owned(),
            source_file: "ledger.xlsx".to_owned(),
            workers: vec![worker("A")],
        };
        let input_b = LedgerImportInput {
            period: "2026-06".to_owned(),
            source_file: "ledger.xlsx".to_owned(),
            workers: vec![worker("A")],
        };
        assert_ne!(ledger_content_sha256(&input_a), ledger_content_sha256(&input_b));
    }
}
