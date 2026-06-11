//! Payroll RUN + source reconciliation.
//!
//! Reads `bitween_payroll.payroll_input` for a period, reconstructs each
//! worker's source-ledger figures from `gross_pay`, `deduction_total`, and the
//! `source_payload` component breakdown, then reconciles them with the shared
//! [`bitween_payroll_api::reconcile_period`] engine:
//!
//! - PRESET mode round-trips the ledger's insurance total + preset income/local
//!   tax through `finalize_payroll_deductions` and asserts the engine reproduces
//!   the ledger net exactly (integrity check).
//! - RECOMPUTE mode runs the same engine with no presets (간이세액표 + local
//!   10%) and records the tax variance honestly.
//!
//! Output: the reconciliation report as JSON on stdout.
//!
//! Usage: `payroll_run <period>` (period also accepted via BITWEEN_PAYROLL_PERIOD).

use bitween_payroll_api::{
    LedgerWorker, PostgresClientSession, PostgresConnectionFailure, PostgresRepositoryConfig,
    PostgresTenantScope, ReconciliationReport, reconcile_period, required_postgres_migrations,
};
use std::process;

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        process::exit(1);
    }
}

fn run() -> Result<(), String> {
    if !postgres_dsn_configured() {
        return Err(
            "payroll_run requires BITWEEN_POSTGRES_DSN and the canonical payroll_input table."
                .to_owned(),
        );
    }
    let period = resolve_period()?;
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|_| "payroll_run_runtime_failed".to_owned())?;
    let report = runtime.block_on(reconcile(period))?;
    println!(
        "{}",
        serde_json::to_string(&report).map_err(|_| "payroll_run_serialize_failed".to_owned())?
    );
    Ok(())
}

fn resolve_period() -> Result<String, String> {
    let period = std::env::args()
        .nth(1)
        .or_else(|| std::env::var("BITWEEN_PAYROLL_PERIOD").ok())
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "payroll_run_period_required".to_owned())?;
    validate_period(&period)?;
    Ok(period)
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
        Err("payroll_run_invalid_period".to_owned())
    }
}

async fn reconcile(period: String) -> Result<ReconciliationReport, String> {
    let session = connect_session().await?;
    let ledger = load_ledger(&session, &period).await?;
    if ledger.is_empty() {
        return Err(format!("payroll_run_no_input_rows_for_period:{period}"));
    }
    Ok(reconcile_period(period, &ledger))
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

async fn load_ledger(
    session: &PostgresClientSession,
    period: &str,
) -> Result<Vec<LedgerWorker>, String> {
    let rows = session
        .client
        .query(
            "SELECT employee_key, gross_pay::text, deduction_total::text, source_payload::text \
             FROM bitween_payroll.payroll_input \
             WHERE tenant_id = $1 AND legal_entity_id = $2 AND workplace_id = $3 \
               AND payroll_period = $4 AND admission_status = 'admitted' \
             ORDER BY employee_key",
            &[
                &session.scope.tenant_id,
                &session.scope.legal_entity_id,
                &session.scope.workplace_id,
                &period,
            ],
        )
        .await
        .map_err(|_| "payroll_run_payroll_input_query_failed".to_owned())?;

    let mut ledger = Vec::with_capacity(rows.len());
    for row in rows {
        let employee_key: String = row.get(0);
        let gross_pay_text: String = row.get(1);
        let deduction_total_text: String = row.get(2);
        let source_payload_text: String = row.get(3);

        let gross = parse_numeric_to_won(&gross_pay_text)?;
        let column_deduction_total = parse_numeric_to_won(&deduction_total_text)?;
        let payload: serde_json::Value = serde_json::from_str(&source_payload_text)
            .map_err(|_| "payroll_run_source_payload_decode_failed".to_owned())?;

        let income_tax = payload_i64(&payload, "income_tax");
        let local_income_tax = payload_i64(&payload, "local_income_tax");
        let health_insurance = payload_i64(&payload, "health_insurance");
        let national_pension = payload_i64(&payload, "national_pension");
        let employment_insurance = payload_i64(&payload, "employment_insurance");
        let name = payload
            .get("name")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("")
            .to_owned();
        // The deduction_total column is clamped non-negative at import; the
        // SIGNED truth (a worker can carry a net refund) lives in
        // source_payload.total_deductions. Prefer it so reconciliation matches.
        let total_deductions = payload
            .get("total_deductions")
            .and_then(json_i64)
            .unwrap_or(column_deduction_total);
        let net = payload
            .get("net")
            .and_then(json_i64)
            .unwrap_or(gross - total_deductions);

        ledger.push(LedgerWorker {
            employee_key,
            name,
            gross,
            income_tax,
            local_income_tax,
            health_insurance,
            national_pension,
            employment_insurance,
            total_deductions,
            net,
        });
    }
    Ok(ledger)
}

/// Parse a PostgreSQL `numeric` text representation into whole won. The ledger
/// figures are integers; we round any fractional remainder to the nearest won.
fn parse_numeric_to_won(value: &str) -> Result<i64, String> {
    let parsed: f64 = value
        .trim()
        .parse()
        .map_err(|_| "payroll_run_numeric_parse_failed".to_owned())?;
    Ok(parsed.round() as i64)
}

fn payload_i64(payload: &serde_json::Value, key: &str) -> i64 {
    payload.get(key).and_then(json_i64).unwrap_or(0)
}

fn json_i64(value: &serde_json::Value) -> Option<i64> {
    if let Some(int) = value.as_i64() {
        Some(int)
    } else if let Some(float) = value.as_f64() {
        Some(float.round() as i64)
    } else if let Some(text) = value.as_str() {
        text.trim().parse::<f64>().ok().map(|float| float.round() as i64)
    } else {
        None
    }
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

fn postgres_failure(failure: PostgresConnectionFailure) -> String {
    format!("{} ({})", failure.code, failure.redacted_dsn)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn period_validation_matches_payroll_input_constraint() {
        assert!(validate_period("2026-05").is_ok());
        assert!(validate_period("2026-5").is_err());
        assert!(validate_period("abcd-ef").is_err());
    }

    #[test]
    fn numeric_text_parses_to_whole_won() {
        assert_eq!(parse_numeric_to_won("97646611").unwrap(), 97_646_611);
        assert_eq!(parse_numeric_to_won("97646611.00").unwrap(), 97_646_611);
        assert_eq!(parse_numeric_to_won("100.49").unwrap(), 100);
        assert!(parse_numeric_to_won("not-a-number").is_err());
    }

    #[test]
    fn payload_i64_reads_int_float_and_string_components() {
        let payload = serde_json::json!({
            "income_tax": 265650,
            "local_income_tax": 26560.0,
            "health_insurance": "174540"
        });
        assert_eq!(payload_i64(&payload, "income_tax"), 265_650);
        assert_eq!(payload_i64(&payload, "local_income_tax"), 26_560);
        assert_eq!(payload_i64(&payload, "health_insurance"), 174_540);
        assert_eq!(payload_i64(&payload, "missing"), 0);
    }
}
