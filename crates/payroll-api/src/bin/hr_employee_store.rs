use bitween_payroll_api::{
    HR_EMPLOYEE_STORE_SCHEMA, PostgresClientSession, PostgresConnectionFailure,
    PostgresRepositoryConfig, PostgresTenantScope, required_postgres_migrations,
};
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use std::process;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct EmployeeStore {
    schema: String,
    employees: Vec<EmployeeRecord>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct EmployeeRecord {
    id: String,
    name: String,
    team: String,
    role: String,
    status: EmployeeStatus,
    updated_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
enum EmployeeStatus {
    Active,
    OnLeave,
    Offboarding,
}

impl EmployeeStatus {
    fn as_postgres_value(&self) -> &'static str {
        match self {
            Self::Active => "active",
            Self::OnLeave => "on_leave",
            Self::Offboarding => "offboarding",
        }
    }

    fn from_postgres_value(value: &str) -> Result<Self, String> {
        match value {
            "active" => Ok(Self::Active),
            "on_leave" => Ok(Self::OnLeave),
            "offboarding" => Ok(Self::Offboarding),
            _ => Err("unsupported employee status from PostgreSQL".to_owned()),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
struct EmployeeInput {
    name: Option<String>,
    team: Option<String>,
    role: Option<String>,
    status: Option<EmployeeStatus>,
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
        .ok_or_else(|| "missing employee store action".to_owned())?;

    if postgres_dsn_configured() {
        return run_postgres(args);
    }

    let path = store_path()?;

    match action {
        "list" => print_store(&load_store(&path)?),
        "add" => {
            let input = read_input()?;
            let mut store = load_store(&path)?;
            add_employee(&mut store, input, now_unix(), now_unix_nanos())?;
            save_store(&path, &store)?;
            print_store(&store)
        }
        "update" => {
            args.remove(0);
            let id = args
                .first()
                .ok_or_else(|| "missing employee id for update".to_owned())?;
            let input = read_input()?;
            let mut store = load_store(&path)?;
            update_employee(&mut store, id, input, now_unix())?;
            save_store(&path, &store)?;
            print_store(&store)
        }
        "remove" => {
            args.remove(0);
            let id = args
                .first()
                .ok_or_else(|| "missing employee id for remove".to_owned())?;
            let mut store = load_store(&path)?;
            remove_employee(&mut store, id)?;
            save_store(&path, &store)?;
            print_store(&store)
        }
        _ => Err(format!("unsupported employee store action: {action}")),
    }
}

fn run_postgres(mut args: Vec<String>) -> Result<(), String> {
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|_| "hr_postgres_runtime_failed".to_owned())?;
    runtime.block_on(run_postgres_async(&mut args))
}

async fn run_postgres_async(args: &mut Vec<String>) -> Result<(), String> {
    let action = args
        .first()
        .cloned()
        .ok_or_else(|| "missing employee store action".to_owned())?;
    let session = postgres_employee_session().await?;

    match action.as_str() {
        "list" => print_store(&load_postgres_store(&session).await?),
        "add" => {
            let input = read_input()?;
            add_postgres_employee(&session, input, now_unix(), now_unix_nanos()).await?;
            print_store(&load_postgres_store(&session).await?)
        }
        "update" => {
            args.remove(0);
            let id = args
                .first()
                .cloned()
                .ok_or_else(|| "missing employee id for update".to_owned())?;
            let input = read_input()?;
            update_postgres_employee(&session, &id, input).await?;
            print_store(&load_postgres_store(&session).await?)
        }
        "remove" => {
            args.remove(0);
            let id = args
                .first()
                .cloned()
                .ok_or_else(|| "missing employee id for remove".to_owned())?;
            remove_postgres_employee(&session, &id).await?;
            print_store(&load_postgres_store(&session).await?)
        }
        _ => Err(format!("unsupported employee store action: {action}")),
    }
}

fn print_store(store: &EmployeeStore) -> Result<(), String> {
    let body = serde_json::to_string_pretty(store).map_err(|error| error.to_string())?;
    println!("{body}");
    Ok(())
}

fn add_employee(
    store: &mut EmployeeStore,
    input: EmployeeInput,
    updated_at_unix: u64,
    id_seed: u128,
) -> Result<(), String> {
    let record = EmployeeRecord {
        id: format!("employee-{id_seed}"),
        name: required_field(input.name, "name")?,
        team: required_field(input.team, "team")?,
        role: required_field(input.role, "role")?,
        status: input.status.unwrap_or(EmployeeStatus::Active),
        updated_at_unix,
    };
    store.employees.push(record);
    sort_employees(store);
    Ok(())
}

fn update_employee(
    store: &mut EmployeeStore,
    id: &str,
    input: EmployeeInput,
    updated_at_unix: u64,
) -> Result<(), String> {
    let record = store
        .employees
        .iter_mut()
        .find(|record| record.id == id)
        .ok_or_else(|| "employee not found".to_owned())?;
    if let Some(name) = input.name.map(clean).filter(|value| !value.is_empty()) {
        record.name = name;
    }
    if let Some(team) = input.team.map(clean).filter(|value| !value.is_empty()) {
        record.team = team;
    }
    if let Some(role) = input.role.map(clean).filter(|value| !value.is_empty()) {
        record.role = role;
    }
    if let Some(status) = input.status {
        record.status = status;
    }
    record.updated_at_unix = updated_at_unix;
    sort_employees(store);
    Ok(())
}

fn remove_employee(store: &mut EmployeeStore, id: &str) -> Result<(), String> {
    let before = store.employees.len();
    store.employees.retain(|record| record.id != id);
    if store.employees.len() == before {
        return Err("employee not found".to_owned());
    }
    Ok(())
}

async fn postgres_employee_session() -> Result<PostgresClientSession, String> {
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

async fn load_postgres_store(session: &PostgresClientSession) -> Result<EmployeeStore, String> {
    let rows = session
        .client
        .query(
            "SELECT employee_key, display_name, team, role_title, employment_status, \
                    EXTRACT(EPOCH FROM updated_at)::bigint \
             FROM bitween_hr.employee \
             WHERE tenant_id = $1 AND legal_entity_id = $2 AND workplace_id = $3 \
               AND admission_status <> 'reversed' \
             ORDER BY display_name, employee_key",
            &[
                &session.scope.tenant_id,
                &session.scope.legal_entity_id,
                &session.scope.workplace_id,
            ],
        )
        .await
        .map_err(|_| "hr_postgres_employee_query_failed".to_owned())?;

    let employees = rows
        .into_iter()
        .map(|row| {
            let status: String = row.get(4);
            let updated_at_unix: i64 = row.get(5);
            Ok(EmployeeRecord {
                id: row.get(0),
                name: row.get(1),
                team: row.get(2),
                role: row.get(3),
                status: EmployeeStatus::from_postgres_value(&status)?,
                updated_at_unix: updated_at_unix.try_into().unwrap_or(0),
            })
        })
        .collect::<Result<Vec<_>, String>>()?;

    Ok(EmployeeStore {
        schema: HR_EMPLOYEE_STORE_SCHEMA.to_owned(),
        employees,
    })
}

async fn add_postgres_employee(
    session: &PostgresClientSession,
    input: EmployeeInput,
    _updated_at_unix: u64,
    id_seed: u128,
) -> Result<(), String> {
    let name = required_field(input.name, "name")?;
    let team = required_field(input.team, "team")?;
    let role = required_field(input.role, "role")?;
    let status = input.status.unwrap_or(EmployeeStatus::Active);
    let employee_key = format!("employee-{id_seed}");
    let actor = postgres_actor();

    session
        .client
        .execute(
            "INSERT INTO bitween_hr.employee \
               (tenant_id, legal_entity_id, workplace_id, employee_key, display_name, team, role_title, employment_status, created_by, updated_by) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9)",
            &[
                &session.scope.tenant_id,
                &session.scope.legal_entity_id,
                &session.scope.workplace_id,
                &employee_key,
                &name,
                &team,
                &role,
                &status.as_postgres_value(),
                &actor,
            ],
        )
        .await
        .map_err(|_| "hr_postgres_employee_insert_failed".to_owned())?;
    Ok(())
}

async fn update_postgres_employee(
    session: &PostgresClientSession,
    employee_key: &str,
    input: EmployeeInput,
) -> Result<(), String> {
    let existing = session
        .client
        .query_opt(
            "SELECT display_name, team, role_title, employment_status \
             FROM bitween_hr.employee \
             WHERE tenant_id = $1 AND legal_entity_id = $2 AND workplace_id = $3 AND employee_key = $4 \
               AND admission_status <> 'reversed'",
            &[
                &session.scope.tenant_id,
                &session.scope.legal_entity_id,
                &session.scope.workplace_id,
                &employee_key,
            ],
        )
        .await
        .map_err(|_| "hr_postgres_employee_lookup_failed".to_owned())?
        .ok_or_else(|| "employee not found".to_owned())?;

    let current_status: String = existing.get(3);
    let name = input
        .name
        .map(clean)
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| existing.get(0));
    let team = input
        .team
        .map(clean)
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| existing.get(1));
    let role = input
        .role
        .map(clean)
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| existing.get(2));
    let status = input
        .status
        .unwrap_or(EmployeeStatus::from_postgres_value(&current_status)?);
    let actor = postgres_actor();
    let changed = session
        .client
        .execute(
            "UPDATE bitween_hr.employee \
             SET display_name = $5, team = $6, role_title = $7, employment_status = $8, updated_by = $9 \
             WHERE tenant_id = $1 AND legal_entity_id = $2 AND workplace_id = $3 AND employee_key = $4 \
               AND admission_status <> 'reversed'",
            &[
                &session.scope.tenant_id,
                &session.scope.legal_entity_id,
                &session.scope.workplace_id,
                &employee_key,
                &name,
                &team,
                &role,
                &status.as_postgres_value(),
                &actor,
            ],
        )
        .await
        .map_err(|_| "hr_postgres_employee_update_failed".to_owned())?;
    if changed == 0 {
        return Err("employee not found".to_owned());
    }
    Ok(())
}

async fn remove_postgres_employee(
    session: &PostgresClientSession,
    employee_key: &str,
) -> Result<(), String> {
    let changed = session
        .client
        .execute(
            "DELETE FROM bitween_hr.employee \
             WHERE tenant_id = $1 AND legal_entity_id = $2 AND workplace_id = $3 AND employee_key = $4 \
               AND admission_status <> 'reversed'",
            &[
                &session.scope.tenant_id,
                &session.scope.legal_entity_id,
                &session.scope.workplace_id,
                &employee_key,
            ],
        )
        .await
        .map_err(|_| "hr_postgres_employee_delete_failed".to_owned())?;
    if changed == 0 {
        return Err("employee not found".to_owned());
    }
    Ok(())
}

fn load_store(path: &Path) -> Result<EmployeeStore, String> {
    if !path.exists() {
        return Ok(empty_store());
    }
    let body = fs::read_to_string(path).map_err(|error| error.to_string())?;
    let mut store = serde_json::from_str::<EmployeeStore>(&body).map_err(|error| error.to_string())?;
    sort_employees(&mut store);
    Ok(store)
}

fn save_store(path: &Path, store: &EmployeeStore) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    let body = serde_json::to_string_pretty(store).map_err(|error| error.to_string())?;
    fs::write(path, format!("{body}\n")).map_err(|error| error.to_string())
}

fn empty_store() -> EmployeeStore {
    EmployeeStore {
        schema: HR_EMPLOYEE_STORE_SCHEMA.to_owned(),
        employees: Vec::new(),
    }
}

fn sort_employees(store: &mut EmployeeStore) {
    store.employees.sort_by(|left, right| left.name.cmp(&right.name));
}

fn read_input() -> Result<EmployeeInput, String> {
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
        .ok_or_else(|| format!("missing required employee field: {name}"))
}

fn clean(value: String) -> String {
    value.trim().to_owned()
}

fn store_path() -> Result<PathBuf, String> {
    local_review_store_path(
        std::env::var("BITWEEN_ALLOW_LOCAL_REVIEW_STORE").ok().as_deref(),
        std::env::var("BITWEEN_HR_EMPLOYEE_STORE").ok(),
    )
}

fn local_review_store_path(
    allow_local_review_store: Option<&str>,
    configured_path: Option<String>,
) -> Result<PathBuf, String> {
    if !truthy(allow_local_review_store) {
        return Err(
            "PostgreSQL relational employee storage is required; set BITWEEN_POSTGRES_DSN for production wiring or BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true only for hermetic local review."
                .to_owned(),
        );
    }
    Ok(configured_path
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(".bitween/local-review/hr/employees.json")))
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
        .unwrap_or_else(|| "hr-employee-store".to_owned())
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

    fn input(
        name: impl Into<String>,
        team: impl Into<String>,
        role: impl Into<String>,
    ) -> EmployeeInput {
        EmployeeInput {
            name: Some(name.into()),
            team: Some(team.into()),
            role: Some(role.into()),
            status: None,
        }
    }

    #[test]
    fn add_employee_creates_sorted_live_record() {
        let mut store = empty_store();

        add_employee(&mut store, input("Kim", "HR", "Manager"), 10, 2).unwrap();
        add_employee(&mut store, input("An", "Payroll", "Operator"), 11, 1).unwrap();

        assert_eq!(store.schema, HR_EMPLOYEE_STORE_SCHEMA);
        assert_eq!(
            store
                .employees
                .iter()
                .map(|record| record.name.as_str())
                .collect::<Vec<_>>(),
            vec!["An", "Kim"]
        );
        assert_eq!(store.employees[0].id, "employee-1");
        assert_eq!(store.employees[0].status, EmployeeStatus::Active);
    }

    #[test]
    fn update_employee_changes_status_without_losing_fields() {
        let mut store = empty_store();
        add_employee(&mut store, input("Lee", "Payroll", "Operator"), 10, 1).unwrap();

        update_employee(
            &mut store,
            "employee-1",
            EmployeeInput {
                name: None,
                team: None,
                role: Some("Lead".to_owned()),
                status: Some(EmployeeStatus::OnLeave),
            },
            20,
        )
        .unwrap();

        let record = &store.employees[0];
        assert_eq!(record.name, "Lee");
        assert_eq!(record.team, "Payroll");
        assert_eq!(record.role, "Lead");
        assert_eq!(record.status, EmployeeStatus::OnLeave);
        assert_eq!(record.updated_at_unix, 20);
    }

    #[test]
    fn remove_employee_deletes_only_the_requested_record() {
        let mut store = empty_store();
        add_employee(&mut store, input("An", "Payroll", "Operator"), 10, 1).unwrap();
        add_employee(&mut store, input("Kim", "HR", "Manager"), 10, 2).unwrap();

        remove_employee(&mut store, "employee-1").unwrap();

        assert_eq!(store.employees.len(), 1);
        assert_eq!(store.employees[0].id, "employee-2");
        assert_eq!(
            remove_employee(&mut store, "missing").unwrap_err(),
            "employee not found"
        );
    }

    #[test]
    fn add_employee_rejects_missing_sensitive_identity_fields() {
        let mut store = empty_store();
        let error = add_employee(
            &mut store,
            EmployeeInput {
                name: Some(" ".to_owned()),
                team: Some("Payroll".to_owned()),
                role: Some("Operator".to_owned()),
                status: None,
            },
            10,
            1,
        )
        .unwrap_err();

        assert_eq!(error, "missing required employee field: name");
        assert!(store.employees.is_empty());
    }

    #[test]
    fn local_file_store_requires_explicit_hermetic_review_flag() {
        let error = local_review_store_path(None, None).unwrap_err();
        assert!(error.contains("PostgreSQL relational employee storage is required"));
        assert_eq!(
            local_review_store_path(Some("true"), None).unwrap(),
            PathBuf::from(".bitween/local-review/hr/employees.json")
        );
        assert_eq!(
            local_review_store_path(Some("1"), Some("/tmp/hr.json".to_owned())).unwrap(),
            PathBuf::from("/tmp/hr.json")
        );
    }

    #[test]
    fn postgres_status_mapping_is_snake_case_and_fail_closed() {
        assert_eq!(EmployeeStatus::Active.as_postgres_value(), "active");
        assert_eq!(EmployeeStatus::OnLeave.as_postgres_value(), "on_leave");
        assert_eq!(EmployeeStatus::Offboarding.as_postgres_value(), "offboarding");
        assert_eq!(
            EmployeeStatus::from_postgres_value("on_leave").unwrap(),
            EmployeeStatus::OnLeave
        );
        assert_eq!(
            EmployeeStatus::from_postgres_value("suspended").unwrap_err(),
            "unsupported employee status from PostgreSQL"
        );
    }

    #[test]
    fn postgres_employee_queries_hide_reversed_archive_admissions() {
        let source = include_str!("hr_employee_store.rs");

        assert!(source.contains("admission_status <> 'reversed'"));
        assert!(source.contains("FROM bitween_hr.employee"));
    }
}
