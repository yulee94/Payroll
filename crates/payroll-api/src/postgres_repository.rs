use sha2::{Digest, Sha256};

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PostgresRepositoryConfig {
    dsn: String,
    pub tls_policy: PostgresTlsPolicy,
    pub implicit_migrations_allowed: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PostgresTlsPolicy {
    VerifyFull,
    VerifyCa,
    ApprovedEncryptedNetworkBoundary,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PostgresRepositoryStatus {
    MissingDsn,
    Configured {
        tls_policy: PostgresTlsPolicy,
        redacted_dsn: String,
        implicit_migrations_allowed: bool,
    },
    Invalid {
        error_code: String,
    },
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PostgresDriverConfig {
    pub driver_crate: &'static str,
    pub required_tls_connector_crate: &'static str,
    pub redacted_dsn: String,
    pub tls_policy: PostgresTlsPolicy,
    pub implicit_migrations_allowed: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PostgresTlsConnectorProfile {
    pub connector_crate: &'static str,
    pub crypto_provider: &'static str,
    pub root_store: &'static str,
    pub root_count: usize,
    pub verification: &'static str,
    pub sni_enabled: bool,
    pub permits_no_tls: bool,
}

#[derive(Clone)]
pub struct PostgresTlsConnector {
    _connector: tokio_postgres_rustls::MakeRustlsConnect,
    pub profile: PostgresTlsConnectorProfile,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PostgresTenantScope {
    pub tenant_id: String,
    pub legal_entity_id: String,
    pub workplace_id: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PostgresConnectionFailure {
    pub code: String,
    pub redacted_dsn: String,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PostgresMigration {
    pub name: &'static str,
    pub sql: &'static str,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PostgresMigrationReceipt {
    pub name: String,
    pub checksum_sha256: String,
    pub status: PostgresMigrationStatus,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PostgresMigrationStatus {
    Applied,
    AlreadyApplied,
}

pub struct PostgresClientSession {
    pub client: tokio_postgres::Client,
    pub connection_task: tokio::task::JoinHandle<Result<(), &'static str>>,
    pub scope: PostgresTenantScope,
    pub redacted_dsn: String,
}

impl PostgresTenantScope {
    pub fn new(
        tenant_id: impl Into<String>,
        legal_entity_id: impl Into<String>,
        workplace_id: impl Into<String>,
    ) -> Result<Self, String> {
        let scope = Self {
            tenant_id: clean_scope_part(tenant_id.into())?,
            legal_entity_id: clean_scope_part(legal_entity_id.into())?,
            workplace_id: clean_scope_part(workplace_id.into())?,
        };
        Ok(scope)
    }
}

impl PostgresTlsConnector {
    fn into_make_tls_connect(self) -> tokio_postgres_rustls::MakeRustlsConnect {
        self._connector
    }
}

impl PostgresMigration {
    pub fn checksum_sha256(&self) -> String {
        let digest = Sha256::digest(self.sql.as_bytes());
        digest
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    }
}

impl PostgresClientSession {
    pub async fn apply_required_migrations(
        &self,
        migrations: &[PostgresMigration],
    ) -> Result<Vec<PostgresMigrationReceipt>, PostgresConnectionFailure> {
        self.client
            .batch_execute(postgres_migration_registry_sql())
            .await
            .map_err(|_| self.failure("postgres_migration_registry_failed"))?;

        let mut receipts = Vec::with_capacity(migrations.len());
        for migration in migrations {
            receipts.push(self.apply_migration(*migration).await?);
        }
        Ok(receipts)
    }

    async fn apply_migration(
        &self,
        migration: PostgresMigration,
    ) -> Result<PostgresMigrationReceipt, PostgresConnectionFailure> {
        let checksum = migration.checksum_sha256();
        if let Some(row) = self
            .client
            .query_opt(postgres_migration_lookup_sql(), &[&migration.name])
            .await
            .map_err(|_| self.failure("postgres_migration_lookup_failed"))?
        {
            let existing_checksum: String = row.get(0);
            if existing_checksum == checksum {
                return Ok(PostgresMigrationReceipt {
                    name: migration.name.to_owned(),
                    checksum_sha256: checksum,
                    status: PostgresMigrationStatus::AlreadyApplied,
                });
            }

            return Err(self.failure("postgres_migration_checksum_mismatch"));
        }

        self.client
            .batch_execute(migration.sql)
            .await
            .map_err(|_| self.failure("postgres_migration_apply_failed"))?;
        self.client
            .execute(
                postgres_migration_insert_sql(),
                &[&migration.name, &checksum],
            )
            .await
            .map_err(|_| self.failure("postgres_migration_record_failed"))?;

        Ok(PostgresMigrationReceipt {
            name: migration.name.to_owned(),
            checksum_sha256: checksum,
            status: PostgresMigrationStatus::Applied,
        })
    }

    fn failure(&self, code: impl Into<String>) -> PostgresConnectionFailure {
        PostgresConnectionFailure {
            code: code.into(),
            redacted_dsn: self.redacted_dsn.clone(),
        }
    }
}

impl PostgresRepositoryConfig {
    pub fn from_env_parts(dsn: Option<String>, tls_policy: Option<String>) -> Result<Self, String> {
        let clean_dsn = clean_dsn(dsn)?;
        Ok(Self {
            dsn: clean_dsn,
            tls_policy: PostgresTlsPolicy::parse(tls_policy)?,
            implicit_migrations_allowed: false,
        })
    }

    pub fn redacted_dsn(&self) -> &'static str {
        "postgres://<redacted>"
    }

    pub fn dsn_is_configured(&self) -> bool {
        !self.dsn.is_empty()
    }

    pub fn tenant_session_setting_sql() -> [&'static str; 3] {
        [
            "SELECT set_config('bitween.tenant_id', $1, false)",
            "SELECT set_config('bitween.legal_entity_id', $2, false)",
            "SELECT set_config('bitween.workplace_id', $3, false)",
        ]
    }

    pub fn tenant_session_setting_batch_sql() -> &'static str {
        "SELECT set_config('bitween.tenant_id', $1, false), set_config('bitween.legal_entity_id', $2, false), set_config('bitween.workplace_id', $3, false)"
    }

    pub fn validate_driver_config(&self) -> Result<PostgresDriverConfig, String> {
        let _driver_config = self
            .dsn
            .parse::<tokio_postgres::Config>()
            .map_err(|_| "postgres_dsn_invalid_driver_config".to_owned())?;

        Ok(PostgresDriverConfig {
            driver_crate: "tokio-postgres",
            required_tls_connector_crate: "tokio-postgres-rustls",
            redacted_dsn: self.redacted_dsn().to_owned(),
            tls_policy: self.tls_policy,
            implicit_migrations_allowed: self.implicit_migrations_allowed,
        })
    }

    pub fn build_tls_connector(&self) -> Result<PostgresTlsConnector, String> {
        if self.tls_policy != PostgresTlsPolicy::VerifyFull {
            return Err("postgres_tls_connector_requires_verify_full".to_owned());
        }

        let root_store = rustls::RootCertStore {
            roots: webpki_roots::TLS_SERVER_ROOTS.to_vec(),
        };
        let root_count = root_store.roots.len();
        let tls_config = rustls::ClientConfig::builder()
            .with_root_certificates(root_store)
            .with_no_client_auth();
        let connector = tokio_postgres_rustls::MakeRustlsConnect::new(tls_config);

        Ok(PostgresTlsConnector {
            _connector: connector,
            profile: PostgresTlsConnectorProfile {
                connector_crate: "tokio-postgres-rustls",
                crypto_provider: "ring",
                root_store: "webpki-roots",
                root_count,
                verification: "verify-full",
                sni_enabled: true,
                permits_no_tls: false,
            },
        })
    }

    pub async fn connect_client_session(
        &self,
        scope: PostgresTenantScope,
    ) -> Result<PostgresClientSession, PostgresConnectionFailure> {
        let connector = self
            .build_tls_connector()
            .map_err(|error_code| self.connection_failure(error_code))?
            .into_make_tls_connect();
        let (client, connection) = tokio_postgres::connect(self.dsn.as_str(), connector)
            .await
            .map_err(|_| self.connection_failure("postgres_connect_failed"))?;
        let connection_task = tokio::spawn(async move {
            connection
                .await
                .map_err(|_| "postgres_connection_task_failed")
        });

        client
            .execute(
                Self::tenant_session_setting_batch_sql(),
                &[&scope.tenant_id, &scope.legal_entity_id, &scope.workplace_id],
            )
            .await
            .map_err(|_| self.connection_failure("postgres_tenant_session_failed"))?;

        Ok(PostgresClientSession {
            client,
            connection_task,
            scope,
            redacted_dsn: self.redacted_dsn().to_owned(),
        })
    }

    fn connection_failure(&self, code: impl Into<String>) -> PostgresConnectionFailure {
        PostgresConnectionFailure {
            code: code.into(),
            redacted_dsn: self.redacted_dsn().to_owned(),
        }
    }
}

pub fn required_postgres_migrations() -> [PostgresMigration; 7] {
    [
        PostgresMigration {
            name: crate::archive_intake_schema::ARCHIVE_INTAKE_POSTGRES_MIGRATION_NAME,
            sql: crate::archive_intake_schema::ARCHIVE_INTAKE_POSTGRES_MIGRATION_SQL,
        },
        PostgresMigration {
            name: crate::workflow_template_schema::WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_NAME,
            sql: crate::workflow_template_schema::WORKFLOW_TEMPLATE_POSTGRES_MIGRATION_SQL,
        },
        PostgresMigration {
            name: crate::hr_employee_schema::HR_EMPLOYEE_POSTGRES_MIGRATION_NAME,
            sql: crate::hr_employee_schema::HR_EMPLOYEE_POSTGRES_MIGRATION_SQL,
        },
        PostgresMigration {
            name: crate::user_preference_schema::USER_PREFERENCE_POSTGRES_MIGRATION_NAME,
            sql: crate::user_preference_schema::USER_PREFERENCE_POSTGRES_MIGRATION_SQL,
        },
        PostgresMigration {
            name: crate::payroll_attendance_schema::PAYROLL_ATTENDANCE_POSTGRES_MIGRATION_NAME,
            sql: crate::payroll_attendance_schema::PAYROLL_ATTENDANCE_POSTGRES_MIGRATION_SQL,
        },
        PostgresMigration {
            name: crate::archive_rollback_schema::ARCHIVE_ROLLBACK_POSTGRES_MIGRATION_NAME,
            sql: crate::archive_rollback_schema::ARCHIVE_ROLLBACK_POSTGRES_MIGRATION_SQL,
        },
        PostgresMigration {
            name: crate::auth_session_schema::AUTH_SESSION_POSTGRES_MIGRATION_NAME,
            sql: crate::auth_session_schema::AUTH_SESSION_POSTGRES_MIGRATION_SQL,
        },
    ]
}

pub fn postgres_migration_registry_sql() -> &'static str {
    "CREATE SCHEMA IF NOT EXISTS bitween_migrations;\nCREATE TABLE IF NOT EXISTS bitween_migrations.schema_migration (\n    migration_name text PRIMARY KEY,\n    checksum_sha256 char(64) NOT NULL CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),\n    applied_at timestamptz NOT NULL DEFAULT now()\n);"
}

pub fn postgres_migration_lookup_sql() -> &'static str {
    "SELECT checksum_sha256 FROM bitween_migrations.schema_migration WHERE migration_name = $1"
}

pub fn postgres_migration_insert_sql() -> &'static str {
    "INSERT INTO bitween_migrations.schema_migration (migration_name, checksum_sha256) VALUES ($1, $2)"
}

impl PostgresTlsPolicy {
    fn parse(value: Option<String>) -> Result<Self, String> {
        let normalized = value
            .as_deref()
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .unwrap_or("verify-full")
            .replace('_', "-")
            .to_ascii_lowercase();

        match normalized.as_str() {
            "verify-full" | "require" => Ok(Self::VerifyFull),
            "verify-ca" => Ok(Self::VerifyCa),
            "approved-encrypted-network-boundary" | "service-mesh" | "mesh" | "mtls-sidecar" => {
                Ok(Self::ApprovedEncryptedNetworkBoundary)
            }
            "no-tls" | "notls" | "disable" | "disabled" => Err("postgres_no_tls_rejected".to_owned()),
            _ => Err("postgres_tls_policy_invalid".to_owned()),
        }
    }
}

pub fn postgres_repository_status(
    dsn: Option<String>,
    tls_policy: Option<String>,
) -> PostgresRepositoryStatus {
    match PostgresRepositoryConfig::from_env_parts(dsn, tls_policy) {
        Ok(config) => PostgresRepositoryStatus::Configured {
            tls_policy: config.tls_policy,
            redacted_dsn: config.redacted_dsn().to_owned(),
            implicit_migrations_allowed: config.implicit_migrations_allowed,
        },
        Err(error_code) if error_code == "postgres_dsn_required" => PostgresRepositoryStatus::MissingDsn,
        Err(error_code) => PostgresRepositoryStatus::Invalid { error_code },
    }
}

fn clean_dsn(value: Option<String>) -> Result<String, String> {
    let dsn = value
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "postgres_dsn_required".to_owned())?;

    if dsn.starts_with("postgres://") || dsn.starts_with("postgresql://") {
        Ok(dsn)
    } else {
        Err("postgres_dsn_invalid_scheme".to_owned())
    }
}

fn clean_scope_part(value: String) -> Result<String, String> {
    let cleaned = value.trim().to_owned();
    if cleaned.is_empty() {
        Err("postgres_scope_required".to_owned())
    } else {
        Ok(cleaned)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn repository_config_redacts_dsn_and_defaults_to_verify_full_tls() {
        let config = PostgresRepositoryConfig::from_env_parts(
            Some("postgres://bitween:example-pass@localhost:5432/bitween".to_owned()),
            None,
        )
        .expect("valid DSN should produce a config");

        assert_eq!(config.tls_policy, PostgresTlsPolicy::VerifyFull);
        assert_eq!(config.redacted_dsn(), "postgres://<redacted>");
        assert!(!config.redacted_dsn().contains("example-pass"));
        assert!(!config.redacted_dsn().contains("localhost"));
        assert!(!config.redacted_dsn().contains("bitween@"));
    }

    #[test]
    fn repository_config_rejects_no_tls_for_production() {
        let error = PostgresRepositoryConfig::from_env_parts(
            Some("postgres://bitween:example-pass@localhost:5432/bitween".to_owned()),
            Some("no_tls".to_owned()),
        )
        .expect_err("production no-TLS mode must be rejected");

        assert_eq!(error, "postgres_no_tls_rejected");
    }

    #[test]
    fn repository_status_reports_missing_and_configured_without_leaking_dsn() {
        let missing = postgres_repository_status(None, None);
        assert_eq!(missing, PostgresRepositoryStatus::MissingDsn);

        let configured = postgres_repository_status(
            Some("postgres://bitween:example-pass@localhost:5432/bitween".to_owned()),
            Some("verify-ca".to_owned()),
        );
        assert_eq!(
            configured,
            PostgresRepositoryStatus::Configured {
                tls_policy: PostgresTlsPolicy::VerifyCa,
                redacted_dsn: "postgres://<redacted>".to_owned(),
                implicit_migrations_allowed: false,
            }
        );
    }

    #[test]
    fn tenant_session_settings_are_parameterized_contracts() {
        let settings = PostgresRepositoryConfig::tenant_session_setting_sql();

        assert_eq!(
            settings,
            [
                "SELECT set_config('bitween.tenant_id', $1, false)",
                "SELECT set_config('bitween.legal_entity_id', $2, false)",
                "SELECT set_config('bitween.workplace_id', $3, false)",
            ]
        );
    }

    #[test]
    fn tenant_session_batch_sql_applies_scope_with_three_parameters() {
        assert_eq!(
            PostgresRepositoryConfig::tenant_session_setting_batch_sql(),
            "SELECT set_config('bitween.tenant_id', $1, false), set_config('bitween.legal_entity_id', $2, false), set_config('bitween.workplace_id', $3, false)"
        );
    }

    #[test]
    fn tenant_scope_trims_values_and_rejects_blanks() {
        let scope = PostgresTenantScope::new(" tenant-acme ", " acme-corp ", " seoul ")
            .expect("non-empty scope values should be accepted");
        assert_eq!(scope.tenant_id, "tenant-acme");
        assert_eq!(scope.legal_entity_id, "acme-corp");
        assert_eq!(scope.workplace_id, "seoul");

        let error = PostgresTenantScope::new("tenant-acme", " ", "seoul")
            .expect_err("blank legal entity scope must be rejected");
        assert_eq!(error, "postgres_scope_required");
    }

    #[test]
    fn driver_config_uses_tokio_postgres_and_tls_connector_without_leaking_dsn() {
        let config = PostgresRepositoryConfig::from_env_parts(
            Some("postgres://bitween:example-pass@localhost:5432/bitween".to_owned()),
            Some("verify-full".to_owned()),
        )
        .expect("valid DSN should produce a config");

        let driver = config
            .validate_driver_config()
            .expect("valid DSN should produce a driver config");

        assert_eq!(driver.driver_crate, "tokio-postgres");
        assert_eq!(
            driver.required_tls_connector_crate,
            "tokio-postgres-rustls"
        );
        assert_eq!(driver.redacted_dsn, "postgres://<redacted>");
        assert_eq!(driver.tls_policy, PostgresTlsPolicy::VerifyFull);
        assert!(!driver.implicit_migrations_allowed);
    }

    #[test]
    fn rustls_tls_connector_builds_without_network_and_uses_webpki_roots() {
        let config = PostgresRepositoryConfig::from_env_parts(
            Some("postgres://bitween:example-pass@localhost:5432/bitween".to_owned()),
            Some("verify-full".to_owned()),
        )
        .expect("valid DSN should produce a config");

        let connector = config
            .build_tls_connector()
            .expect("valid TLS policy should build a rustls connector without network access");

        assert_eq!(connector.profile.connector_crate, "tokio-postgres-rustls");
        assert_eq!(connector.profile.crypto_provider, "ring");
        assert_eq!(connector.profile.root_store, "webpki-roots");
        assert_eq!(connector.profile.verification, "verify-full");
        assert!(connector.profile.sni_enabled);
        assert!(connector.profile.root_count > 0);
        assert!(!connector.profile.permits_no_tls);
    }

    #[test]
    fn connection_failure_never_leaks_dsn_details() {
        let config = PostgresRepositoryConfig::from_env_parts(
            Some("postgres://bitween:example-pass@localhost:5432/bitween".to_owned()),
            Some("verify-full".to_owned()),
        )
        .expect("valid DSN should produce a config");

        let failure = config.connection_failure("postgres_connect_failed");

        assert_eq!(failure.code, "postgres_connect_failed");
        assert_eq!(failure.redacted_dsn, "postgres://<redacted>");
        assert!(!failure.redacted_dsn.contains("example-pass"));
        assert!(!failure.redacted_dsn.contains("localhost"));
        assert!(!failure.redacted_dsn.contains("bitween@"));
    }

    #[test]
    fn required_migrations_include_archive_workflow_hr_settings_payroll_rollback_and_auth_in_order() {
        let migrations = required_postgres_migrations();

        assert_eq!(migrations.len(), 7);
        assert_eq!(migrations[0].name, "001_archive_intake.sql");
        assert!(migrations[0].sql.contains("bitween_archive.archive_intake"));
        assert_eq!(migrations[1].name, "002_workflow_templates.sql");
        assert!(migrations[1].sql.contains("bitween_workflow.workflow_template"));
        assert_eq!(migrations[2].name, "003_hr_employee.sql");
        assert!(migrations[2].sql.contains("bitween_hr.employee"));
        assert_eq!(migrations[3].name, "004_user_preferences.sql");
        assert!(migrations[3].sql.contains("bitween_settings.user_preference"));
        assert_eq!(migrations[4].name, "005_payroll_attendance_intake.sql");
        assert!(migrations[4].sql.contains("bitween_payroll.payroll_input"));
        assert!(migrations[4].sql.contains("bitween_hr.attendance_record"));
        assert_eq!(migrations[5].name, "006_archive_admission_rollback.sql");
        assert!(migrations[5]
            .sql
            .contains("bitween_archive.archive_admission_rollback"));
        assert!(migrations[5].sql.contains("source_intake_id uuid REFERENCES"));
        assert_eq!(migrations[6].name, "007_auth_session_security.sql");
        assert!(migrations[6].sql.contains("bitween_auth.jwt_revocation"));
        assert!(migrations[6].sql.contains("bitween_auth.session_event_audit"));
    }

    #[test]
    fn migration_checksum_is_stable_hex_sha256() {
        let migration = PostgresMigration {
            name: "example.sql",
            sql: "SELECT 1;",
        };
        let checksum = migration.checksum_sha256();

        assert_eq!(checksum.len(), 64);
        assert!(checksum.chars().all(|character| character.is_ascii_hexdigit()));
        assert_eq!(checksum, migration.checksum_sha256());
    }

    #[test]
    fn migration_registry_sql_is_idempotent_and_checksum_guarded() {
        let registry = postgres_migration_registry_sql();

        assert!(registry.contains("CREATE SCHEMA IF NOT EXISTS bitween_migrations"));
        assert!(registry.contains("CREATE TABLE IF NOT EXISTS bitween_migrations.schema_migration"));
        assert!(registry.contains("migration_name text PRIMARY KEY"));
        assert!(registry.contains("checksum_sha256 char(64) NOT NULL CHECK"));
        assert!(registry.contains("applied_at timestamptz NOT NULL DEFAULT now()"));
    }

    #[test]
    fn migration_lookup_and_insert_are_parameterized() {
        assert_eq!(
            postgres_migration_lookup_sql(),
            "SELECT checksum_sha256 FROM bitween_migrations.schema_migration WHERE migration_name = $1"
        );
        assert_eq!(
            postgres_migration_insert_sql(),
            "INSERT INTO bitween_migrations.schema_migration (migration_name, checksum_sha256) VALUES ($1, $2)"
        );
    }
}
