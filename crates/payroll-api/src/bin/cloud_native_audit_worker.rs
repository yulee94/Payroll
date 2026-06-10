use serde::Serialize;
use std::collections::BTreeMap;
use std::env;
use std::process;

const CLOUD_NATIVE_AUDIT_WORKER_SCHEMA: &str = "bitween.cloud-native-audit-worker.v1";
const AUDIT_EVENT_SCHEMA: &str = "bitween.audit-event.v1";

#[derive(Clone, Debug, Eq, PartialEq)]
struct CloudNativeAuditEnv {
    values: BTreeMap<String, String>,
}

#[derive(Debug, Eq, PartialEq, Serialize)]
struct CloudNativeAuditReport {
    schema: &'static str,
    status: CloudNativeAuditStatus,
    audit_event_schema: &'static str,
    checks: Vec<CloudNativeAuditCheck>,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    missing_env: Vec<&'static str>,
    #[serde(skip_serializing_if = "Option::is_none")]
    redacted_postgres_dsn: Option<&'static str>,
}

#[derive(Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum CloudNativeAuditStatus {
    Ready,
    Blocked,
}

#[derive(Debug, Eq, PartialEq, Serialize)]
struct CloudNativeAuditCheck {
    id: &'static str,
    control: &'static str,
    state: CloudNativeAuditCheckState,
    evidence: &'static str,
}

#[derive(Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum CloudNativeAuditCheckState {
    Ready,
    Blocked,
}

fn main() {
    let report = run_cloud_native_audit(CloudNativeAuditEnv::from_process_env());
    println!(
        "{}",
        serde_json::to_string(&report)
            .unwrap_or_else(|_| "{\"schema\":\"bitween.cloud-native-audit-worker.v1\",\"status\":\"blocked\"}".to_owned())
    );
    if report.status == CloudNativeAuditStatus::Blocked {
        process::exit(2);
    }
}

fn run_cloud_native_audit(audit_env: CloudNativeAuditEnv) -> CloudNativeAuditReport {
    let mut checks = Vec::new();
    let mut missing_env = Vec::new();

    push_value_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "auth-required",
        "identity",
        "BITWEEN_AUTH_REQUIRED",
        Some("true"),
        "authentication required flag is true",
    );
    push_presence_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "postgres-dsn",
        "relational-store",
        "BITWEEN_POSTGRES_DSN",
        "PostgreSQL DSN is supplied by Secret",
    );
    push_value_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "postgres-tls",
        "relational-store",
        "BITWEEN_POSTGRES_TLS_POLICY",
        Some("verify-full"),
        "PostgreSQL TLS policy is verify-full",
    );
    for (id, env_key, evidence) in [
        (
            "postgres-tenant-scope",
            "BITWEEN_POSTGRES_TENANT_ID",
            "PostgreSQL tenant scope is configured",
        ),
        (
            "postgres-legal-entity-scope",
            "BITWEEN_POSTGRES_LEGAL_ENTITY_ID",
            "PostgreSQL legal-entity scope is configured",
        ),
        (
            "postgres-workplace-scope",
            "BITWEEN_POSTGRES_WORKPLACE_ID",
            "PostgreSQL workplace scope is configured",
        ),
    ] {
        push_presence_check(
            &audit_env,
            &mut checks,
            &mut missing_env,
            id,
            "tenant-isolation",
            env_key,
            evidence,
        );
    }
    push_presence_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "rustfs-endpoint",
        "object-store",
        "BITWEEN_RUSTFS_ENDPOINT",
        "RustFS endpoint is configured",
    );
    push_value_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "rustfs-archive-bucket",
        "object-store",
        "BITWEEN_RUSTFS_BUCKET",
        Some("bitween-archive-originals"),
        "RustFS archive bucket is the governed originals bucket",
    );
    push_presence_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "rustfs-evidence-bucket",
        "object-store",
        "BITWEEN_RUSTFS_BUCKET_EVIDENCE",
        "RustFS audit evidence bucket is configured",
    );
    push_presence_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "rustfs-access-key",
        "object-store",
        "BITWEEN_RUSTFS_ACCESS_KEY",
        "RustFS access key is supplied by Secret",
    );
    push_presence_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "rustfs-secret-key",
        "object-store",
        "BITWEEN_RUSTFS_SECRET_KEY",
        "RustFS secret key is supplied by Secret",
    );
    push_presence_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "audit-export-bucket",
        "audit-stream",
        "BITWEEN_AUDIT_EXPORT_BUCKET",
        "audit export bucket is configured",
    );
    push_value_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "audit-event-stream",
        "audit-stream",
        "BITWEEN_AUDIT_EVENT_STREAM",
        Some("postgres+otel"),
        "audit events are declared for PostgreSQL and OpenTelemetry sinks",
    );
    push_presence_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "otel-service-name",
        "observability",
        "BITWEEN_OTEL_SERVICE_NAME",
        "OpenTelemetry service name is configured",
    );
    push_presence_check(
        &audit_env,
        &mut checks,
        &mut missing_env,
        "otel-exporter",
        "observability",
        "BITWEEN_OTEL_EXPORTER_OTLP_ENDPOINT",
        "OpenTelemetry OTLP endpoint is configured",
    );

    let status = if checks
        .iter()
        .all(|check| check.state == CloudNativeAuditCheckState::Ready)
    {
        CloudNativeAuditStatus::Ready
    } else {
        CloudNativeAuditStatus::Blocked
    };

    CloudNativeAuditReport {
        schema: CLOUD_NATIVE_AUDIT_WORKER_SCHEMA,
        status,
        audit_event_schema: AUDIT_EVENT_SCHEMA,
        checks,
        missing_env,
        redacted_postgres_dsn: audit_env
            .get("BITWEEN_POSTGRES_DSN")
            .map(|_| "postgres://<redacted>"),
    }
}

impl CloudNativeAuditEnv {
    fn from_process_env() -> Self {
        Self {
            values: env::vars().collect(),
        }
    }

    fn get(&self, key: &str) -> Option<&str> {
        self.values
            .get(key)
            .map(String::as_str)
            .filter(|value| !value.trim().is_empty())
    }
}

fn push_presence_check(
    audit_env: &CloudNativeAuditEnv,
    checks: &mut Vec<CloudNativeAuditCheck>,
    missing_env: &mut Vec<&'static str>,
    id: &'static str,
    control: &'static str,
    env_key: &'static str,
    ready_evidence: &'static str,
) {
    let is_ready = audit_env.get(env_key).is_some();
    if !is_ready {
        missing_env.push(env_key);
    }
    checks.push(CloudNativeAuditCheck {
        id,
        control,
        state: if is_ready {
            CloudNativeAuditCheckState::Ready
        } else {
            CloudNativeAuditCheckState::Blocked
        },
        evidence: if is_ready {
            ready_evidence
        } else {
            "required environment value is absent"
        },
    });
}

fn push_value_check(
    audit_env: &CloudNativeAuditEnv,
    checks: &mut Vec<CloudNativeAuditCheck>,
    missing_env: &mut Vec<&'static str>,
    id: &'static str,
    control: &'static str,
    env_key: &'static str,
    expected: Option<&'static str>,
    ready_evidence: &'static str,
) {
    let actual = audit_env.get(env_key);
    if actual.is_none() {
        missing_env.push(env_key);
    }
    let is_ready = match (actual, expected) {
        (Some(actual), Some(expected)) => actual == expected,
        (Some(_), None) => true,
        (None, _) => false,
    };
    checks.push(CloudNativeAuditCheck {
        id,
        control,
        state: if is_ready {
            CloudNativeAuditCheckState::Ready
        } else {
            CloudNativeAuditCheckState::Blocked
        },
        evidence: if is_ready {
            ready_evidence
        } else if actual.is_some() {
            "configured value does not match the production contract"
        } else {
            "required environment value is absent"
        },
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    fn complete_env() -> CloudNativeAuditEnv {
        CloudNativeAuditEnv {
            values: BTreeMap::from([
                ("BITWEEN_AUTH_REQUIRED".to_owned(), "true".to_owned()),
                ("BITWEEN_POSTGRES_DSN".to_owned(), "postgres://bitween:credential@db:5432/bitween".to_owned()),
                ("BITWEEN_POSTGRES_TLS_POLICY".to_owned(), "verify-full".to_owned()),
                ("BITWEEN_POSTGRES_TENANT_ID".to_owned(), "tenant-acme".to_owned()),
                ("BITWEEN_POSTGRES_LEGAL_ENTITY_ID".to_owned(), "acme-corp".to_owned()),
                ("BITWEEN_POSTGRES_WORKPLACE_ID".to_owned(), "seoul".to_owned()),
                ("BITWEEN_RUSTFS_ENDPOINT".to_owned(), "http://bitween-rustfs:9000".to_owned()),
                ("BITWEEN_RUSTFS_BUCKET".to_owned(), "bitween-archive-originals".to_owned()),
                ("BITWEEN_RUSTFS_BUCKET_EVIDENCE".to_owned(), "bitween-audit-evidence".to_owned()),
                ("BITWEEN_RUSTFS_ACCESS_KEY".to_owned(), "access-key-from-secret".to_owned()),
                ("BITWEEN_RUSTFS_SECRET_KEY".to_owned(), "secret-key-from-secret".to_owned()),
                ("BITWEEN_AUDIT_EXPORT_BUCKET".to_owned(), "bitween-audit-evidence".to_owned()),
                ("BITWEEN_AUDIT_EVENT_STREAM".to_owned(), "postgres+otel".to_owned()),
                ("BITWEEN_OTEL_SERVICE_NAME".to_owned(), "bitween-cloud-native-audit-worker".to_owned()),
                ("BITWEEN_OTEL_EXPORTER_OTLP_ENDPOINT".to_owned(), "http://otel-collector:4317".to_owned()),
            ]),
        }
    }

    #[test]
    fn complete_environment_is_ready() {
        let report = run_cloud_native_audit(complete_env());

        assert_eq!(report.schema, CLOUD_NATIVE_AUDIT_WORKER_SCHEMA);
        assert_eq!(report.status, CloudNativeAuditStatus::Ready);
        assert_eq!(report.audit_event_schema, AUDIT_EVENT_SCHEMA);
        assert!(report.missing_env.is_empty());
        assert_eq!(report.redacted_postgres_dsn, Some("postgres://<redacted>"));
        assert!(report.checks.len() >= 10);
    }

    #[test]
    fn missing_required_environment_fails_closed_with_actionable_ids() {
        let report = run_cloud_native_audit(CloudNativeAuditEnv {
            values: BTreeMap::new(),
        });

        assert_eq!(report.status, CloudNativeAuditStatus::Blocked);
        assert!(report.missing_env.contains(&"BITWEEN_POSTGRES_DSN"));
        assert!(report.missing_env.contains(&"BITWEEN_RUSTFS_ENDPOINT"));
        assert!(report.missing_env.contains(&"BITWEEN_AUTH_REQUIRED"));
        assert!(report.redacted_postgres_dsn.is_none());
    }

    #[test]
    fn incorrect_security_contract_values_fail_closed() {
        let mut env = complete_env();
        env.values
            .insert("BITWEEN_AUTH_REQUIRED".to_owned(), "false".to_owned());
        env.values
            .insert("BITWEEN_POSTGRES_TLS_POLICY".to_owned(), "prefer".to_owned());

        let report = run_cloud_native_audit(env);

        assert_eq!(report.status, CloudNativeAuditStatus::Blocked);
        assert!(report
            .checks
            .iter()
            .any(|check| check.id == "auth-required" && check.state == CloudNativeAuditCheckState::Blocked));
        assert!(report
            .checks
            .iter()
            .any(|check| check.id == "postgres-tls" && check.state == CloudNativeAuditCheckState::Blocked));
    }

    #[test]
    fn serialized_report_never_exposes_raw_postgres_dsn() {
        let report = run_cloud_native_audit(complete_env());
        let serialized = serde_json::to_string(&report).expect("report serializes");

        assert!(serialized.contains("postgres://<redacted>"));
        assert!(!serialized.contains("credential"));
        assert!(!serialized.contains("db:5432"));
    }
}
