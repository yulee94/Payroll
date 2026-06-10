use bitween_payroll_api::{
    PostgresConnectionFailure, PostgresMigrationReceipt, PostgresRepositoryConfig,
    PostgresTenantScope, required_postgres_migrations,
};
use serde::Serialize;
use std::env;
use std::process;

const POSTGRES_MIGRATE_SCHEMA: &str = "bitween.postgres-migrate.v1";

#[derive(Clone, Debug, Eq, PartialEq)]
struct MigrationJobEnv {
    dsn: Option<String>,
    tls_policy: Option<String>,
    tenant_id: Option<String>,
    legal_entity_id: Option<String>,
    workplace_id: Option<String>,
}

#[derive(Debug, Eq, PartialEq, Serialize)]
struct MigrationJobResponse {
    schema: &'static str,
    status: MigrationJobStatus,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    receipts: Vec<MigrationReceiptView>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error_code: Option<String>,
    redacted_dsn: &'static str,
}

#[derive(Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum MigrationJobStatus {
    Applied,
    Blocked,
}

#[derive(Debug, Eq, PartialEq, Serialize)]
struct MigrationReceiptView {
    name: String,
    checksum_sha256: String,
    status: String,
}

fn main() {
    let response = run_migration_job_blocking(MigrationJobEnv::from_process_env());
    println!(
        "{}",
        serde_json::to_string(&response)
            .unwrap_or_else(|_| "{\"schema\":\"bitween.postgres-migrate.v1\",\"status\":\"blocked\",\"error_code\":\"postgres_migration_response_serialize_failed\",\"redacted_dsn\":\"postgres://<redacted>\"}".to_owned())
    );

    if response.status == MigrationJobStatus::Blocked {
        process::exit(1);
    }
}

fn run_migration_job_blocking(job_env: MigrationJobEnv) -> MigrationJobResponse {
    let runtime = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(_) => return blocked("postgres_migration_runtime_failed"),
    };

    runtime.block_on(run_migration_job(job_env))
}

async fn run_migration_job(job_env: MigrationJobEnv) -> MigrationJobResponse {
    let scope = match job_env.tenant_scope() {
        Ok(scope) => scope,
        Err(error_code) => return blocked(error_code),
    };
    let config = match PostgresRepositoryConfig::from_env_parts(job_env.dsn, job_env.tls_policy) {
        Ok(config) => config,
        Err(error_code) => return blocked(error_code),
    };
    let session = match config.connect_client_session(scope).await {
        Ok(session) => session,
        Err(failure) => return blocked_connection(failure),
    };

    match session
        .apply_required_migrations(&required_postgres_migrations())
        .await
    {
        Ok(receipts) => MigrationJobResponse {
            schema: POSTGRES_MIGRATE_SCHEMA,
            status: MigrationJobStatus::Applied,
            receipts: receipts.into_iter().map(MigrationReceiptView::from).collect(),
            error_code: None,
            redacted_dsn: "postgres://<redacted>",
        },
        Err(failure) => blocked_connection(failure),
    }
}

fn blocked(error_code: impl Into<String>) -> MigrationJobResponse {
    MigrationJobResponse {
        schema: POSTGRES_MIGRATE_SCHEMA,
        status: MigrationJobStatus::Blocked,
        receipts: Vec::new(),
        error_code: Some(error_code.into()),
        redacted_dsn: "postgres://<redacted>",
    }
}

fn blocked_connection(failure: PostgresConnectionFailure) -> MigrationJobResponse {
    MigrationJobResponse {
        schema: POSTGRES_MIGRATE_SCHEMA,
        status: MigrationJobStatus::Blocked,
        receipts: Vec::new(),
        error_code: Some(failure.code),
        redacted_dsn: "postgres://<redacted>",
    }
}

impl MigrationJobEnv {
    fn from_process_env() -> Self {
        Self {
            dsn: env::var("BITWEEN_POSTGRES_DSN").ok(),
            tls_policy: env::var("BITWEEN_POSTGRES_TLS_POLICY").ok(),
            tenant_id: env::var("BITWEEN_POSTGRES_TENANT_ID").ok(),
            legal_entity_id: env::var("BITWEEN_POSTGRES_LEGAL_ENTITY_ID").ok(),
            workplace_id: env::var("BITWEEN_POSTGRES_WORKPLACE_ID").ok(),
        }
    }

    fn tenant_scope(&self) -> Result<PostgresTenantScope, String> {
        let tenant_id = self
            .tenant_id
            .clone()
            .ok_or_else(|| "postgres_tenant_scope_required".to_owned())?;
        let legal_entity_id = self
            .legal_entity_id
            .clone()
            .ok_or_else(|| "postgres_legal_entity_scope_required".to_owned())?;
        let workplace_id = self
            .workplace_id
            .clone()
            .ok_or_else(|| "postgres_workplace_scope_required".to_owned())?;

        PostgresTenantScope::new(tenant_id, legal_entity_id, workplace_id)
    }
}

impl From<PostgresMigrationReceipt> for MigrationReceiptView {
    fn from(receipt: PostgresMigrationReceipt) -> Self {
        Self {
            name: receipt.name,
            checksum_sha256: receipt.checksum_sha256,
            status: format!("{:?}", receipt.status).to_ascii_snake_case(),
        }
    }
}

trait SnakeCase {
    fn to_ascii_snake_case(&self) -> String;
}

impl SnakeCase for str {
    fn to_ascii_snake_case(&self) -> String {
        let mut output = String::with_capacity(self.len() + 4);
        for (index, character) in self.chars().enumerate() {
            if character.is_ascii_uppercase() {
                if index > 0 {
                    output.push('_');
                }
                output.push(character.to_ascii_lowercase());
            } else {
                output.push(character);
            }
        }
        output
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn migration_job_requires_explicit_dsn() {
        let response = run_migration_job_blocking(MigrationJobEnv {
            dsn: None,
            tls_policy: None,
            tenant_id: Some("tenant-acme".to_owned()),
            legal_entity_id: Some("acme-corp".to_owned()),
            workplace_id: Some("seoul".to_owned()),
        });

        assert_eq!(response.status, MigrationJobStatus::Blocked);
        assert_eq!(response.error_code, Some("postgres_dsn_required".to_owned()));
        assert_eq!(response.redacted_dsn, "postgres://<redacted>");
    }

    #[test]
    fn migration_job_requires_explicit_scope() {
        let response = run_migration_job_blocking(MigrationJobEnv {
            dsn: Some("postgres://bitween:example-pass@localhost:5432/bitween".to_owned()),
            tls_policy: Some("verify-full".to_owned()),
            tenant_id: Some("tenant-acme".to_owned()),
            legal_entity_id: None,
            workplace_id: Some("seoul".to_owned()),
        });

        assert_eq!(response.status, MigrationJobStatus::Blocked);
        assert_eq!(
            response.error_code,
            Some("postgres_legal_entity_scope_required".to_owned())
        );
        assert_eq!(response.redacted_dsn, "postgres://<redacted>");
    }

    #[test]
    fn migration_receipt_status_is_snake_case() {
        let receipt = MigrationReceiptView::from(PostgresMigrationReceipt {
            name: "001_archive_intake.sql".to_owned(),
            checksum_sha256: "0".repeat(64),
            status: bitween_payroll_api::PostgresMigrationStatus::AlreadyApplied,
        });

        assert_eq!(receipt.status, "already_applied");
    }
}
