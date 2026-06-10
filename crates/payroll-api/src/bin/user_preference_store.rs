use bitween_payroll_api::{
    PostgresClientSession, PostgresConnectionFailure, PostgresRepositoryConfig,
    PostgresTenantScope, required_postgres_migrations,
    USER_PREFERENCE_STORE_SCHEMA,
};
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use std::process;
use std::time::{SystemTime, UNIX_EPOCH};

const DEFAULT_LOCALE: &str = "ko-KR";
const DEFAULT_SIDEBAR_THEME: &str = "steel";
const DEFAULT_WORKSPACE_DENSITY: &str = "work_dense";
const DEFAULT_NOTIFICATION_DIGEST: &str = "role_work";
const DEFAULT_PAYROLL_STANDARD_VIEW: &str = "before_run";

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct UserPreferenceStore {
    schema: String,
    current: UserPreferences,
    updated_at_unix: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct UserPreferences {
    locale: String,
    sidebar_theme: String,
    workspace_density: String,
    notification_digest: String,
    payroll_standard_view: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
struct UserPreferenceInput {
    locale: Option<String>,
    sidebar_theme: Option<String>,
    workspace_density: Option<String>,
    notification_digest: Option<String>,
    payroll_standard_view: Option<String>,
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
        .ok_or_else(|| "missing user preference action".to_owned())?;

    if postgres_dsn_configured() {
        return run_postgres(args);
    }

    let path = store_path()?;

    match action {
        "get" => print_store(&load_store(&path)?),
        "update" => {
            let input = read_input()?;
            let mut store = load_store(&path)?;
            update_preferences(&mut store, input, now_unix())?;
            save_store(&path, &store)?;
            print_store(&store)
        }
        _ => Err(format!("unsupported user preference action: {action}")),
    }
}

fn run_postgres(args: Vec<String>) -> Result<(), String> {
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|_| "settings_postgres_runtime_failed".to_owned())?;
    runtime.block_on(run_postgres_async(args))
}

async fn run_postgres_async(args: Vec<String>) -> Result<(), String> {
    let action = args
        .first()
        .map(String::as_str)
        .ok_or_else(|| "missing user preference action".to_owned())?;
    let session = postgres_user_preference_session().await?;
    let user_id = postgres_actor()?;

    match action {
        "get" => print_store(&load_postgres_store(&session, &user_id).await?),
        "update" => {
            let input = read_input()?;
            let mut store = load_postgres_store(&session, &user_id).await?;
            update_preferences(&mut store, input, now_unix())?;
            save_postgres_store(&session, &user_id, &store).await?;
            print_store(&load_postgres_store(&session, &user_id).await?)
        }
        _ => Err(format!("unsupported user preference action: {action}")),
    }
}

async fn postgres_user_preference_session() -> Result<PostgresClientSession, String> {
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

async fn load_postgres_store(
    session: &PostgresClientSession,
    user_id: &str,
) -> Result<UserPreferenceStore, String> {
    let row = session
        .client
        .query_opt(
            postgres_user_preference_select_sql(),
            &[&session.scope.tenant_id, &user_id],
        )
        .await
        .map_err(|_| "settings_postgres_preference_query_failed".to_owned())?;
    let Some(row) = row else {
        return Ok(empty_store(now_unix()));
    };

    let updated_at_unix: i64 = row.get(5);
    validate_store(UserPreferenceStore {
        schema: USER_PREFERENCE_STORE_SCHEMA.to_owned(),
        current: UserPreferences {
            locale: row.get(0),
            sidebar_theme: row.get(1),
            workspace_density: row.get(2),
            notification_digest: row.get(3),
            payroll_standard_view: row.get(4),
        },
        updated_at_unix: updated_at_unix.try_into().unwrap_or(0),
    })
}

async fn save_postgres_store(
    session: &PostgresClientSession,
    user_id: &str,
    store: &UserPreferenceStore,
) -> Result<(), String> {
    session
        .client
        .execute(
            postgres_user_preference_upsert_sql(),
            &[
                &session.scope.tenant_id,
                &user_id,
                &store.current.locale,
                &store.current.sidebar_theme,
                &store.current.workspace_density,
                &store.current.notification_digest,
                &store.current.payroll_standard_view,
            ],
        )
        .await
        .map_err(|_| "settings_postgres_preference_upsert_failed".to_owned())?;
    Ok(())
}

fn print_store(store: &UserPreferenceStore) -> Result<(), String> {
    let body = serde_json::to_string_pretty(store).map_err(|error| error.to_string())?;
    println!("{body}");
    Ok(())
}

fn update_preferences(
    store: &mut UserPreferenceStore,
    input: UserPreferenceInput,
    updated_at_unix: u64,
) -> Result<(), String> {
    if let Some(locale) = input.locale {
        store.current.locale = allowed_value(locale, "locale", &["ko-KR", "en-US", "zh-Hans-CN", "ja-JP"])?;
    }
    if let Some(sidebar_theme) = input.sidebar_theme {
        store.current.sidebar_theme = allowed_value(sidebar_theme, "sidebar_theme", &["steel", "graphite", "teal", "navy"])?;
    }
    if let Some(workspace_density) = input.workspace_density {
        store.current.workspace_density = allowed_value(workspace_density, "workspace_density", &["work_dense", "comfortable"])?;
    }
    if let Some(notification_digest) = input.notification_digest {
        store.current.notification_digest = allowed_value(notification_digest, "notification_digest", &["role_work", "urgent_only"])?;
    }
    if let Some(payroll_standard_view) = input.payroll_standard_view {
        store.current.payroll_standard_view = allowed_value(payroll_standard_view, "payroll_standard_view", &["before_run", "always_visible"])?;
    }
    store.updated_at_unix = updated_at_unix;
    Ok(())
}

fn allowed_value(value: String, name: &str, allowed: &[&str]) -> Result<String, String> {
    let cleaned = value.trim().to_owned();
    if allowed.iter().any(|candidate| *candidate == cleaned) {
        return Ok(cleaned);
    }
    Err(format!("unsupported user preference value for {name}"))
}

fn postgres_user_preference_select_sql() -> &'static str {
    "SELECT locale, sidebar_theme, workspace_density, notification_digest, payroll_standard_view, \
            EXTRACT(EPOCH FROM updated_at)::bigint \
     FROM bitween_settings.user_preference \
     WHERE tenant_id = $1 AND user_id = $2"
}

fn postgres_user_preference_upsert_sql() -> &'static str {
    "INSERT INTO bitween_settings.user_preference ( \
        tenant_id, user_id, locale, sidebar_theme, workspace_density, notification_digest, payroll_standard_view \
     ) VALUES ($1, $2, $3, $4, $5, $6, $7) \
     ON CONFLICT (tenant_id, user_id) DO UPDATE SET \
        locale = EXCLUDED.locale, \
        sidebar_theme = EXCLUDED.sidebar_theme, \
        workspace_density = EXCLUDED.workspace_density, \
        notification_digest = EXCLUDED.notification_digest, \
        payroll_standard_view = EXCLUDED.payroll_standard_view"
}

fn load_store(path: &Path) -> Result<UserPreferenceStore, String> {
    if !path.exists() {
        return Ok(empty_store(now_unix()));
    }
    let body = fs::read_to_string(path).map_err(|error| error.to_string())?;
    let store = serde_json::from_str::<UserPreferenceStore>(&body).map_err(|error| error.to_string())?;
    validate_store(store)
}

fn save_store(path: &Path, store: &UserPreferenceStore) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    let body = serde_json::to_string_pretty(store).map_err(|error| error.to_string())?;
    fs::write(path, format!("{body}\n")).map_err(|error| error.to_string())
}

fn validate_store(mut store: UserPreferenceStore) -> Result<UserPreferenceStore, String> {
    if store.schema != USER_PREFERENCE_STORE_SCHEMA {
        store.schema = USER_PREFERENCE_STORE_SCHEMA.to_owned();
    }
    store.current.locale = allowed_value(
        store.current.locale,
        "locale",
        &["ko-KR", "en-US", "zh-Hans-CN", "ja-JP"],
    )?;
    store.current.sidebar_theme = allowed_value(
        store.current.sidebar_theme,
        "sidebar_theme",
        &["steel", "graphite", "teal", "navy"],
    )?;
    store.current.workspace_density = allowed_value(
        store.current.workspace_density,
        "workspace_density",
        &["work_dense", "comfortable"],
    )?;
    store.current.notification_digest = allowed_value(
        store.current.notification_digest,
        "notification_digest",
        &["role_work", "urgent_only"],
    )?;
    store.current.payroll_standard_view = allowed_value(
        store.current.payroll_standard_view,
        "payroll_standard_view",
        &["before_run", "always_visible"],
    )?;
    Ok(store)
}

fn empty_store(updated_at_unix: u64) -> UserPreferenceStore {
    UserPreferenceStore {
        schema: USER_PREFERENCE_STORE_SCHEMA.to_owned(),
        current: UserPreferences {
            locale: DEFAULT_LOCALE.to_owned(),
            sidebar_theme: DEFAULT_SIDEBAR_THEME.to_owned(),
            workspace_density: DEFAULT_WORKSPACE_DENSITY.to_owned(),
            notification_digest: DEFAULT_NOTIFICATION_DIGEST.to_owned(),
            payroll_standard_view: DEFAULT_PAYROLL_STANDARD_VIEW.to_owned(),
        },
        updated_at_unix,
    }
}

fn read_input() -> Result<UserPreferenceInput, String> {
    let mut body = String::new();
    io::stdin()
        .read_to_string(&mut body)
        .map_err(|error| error.to_string())?;
    serde_json::from_str(&body).map_err(|error| error.to_string())
}

fn store_path() -> Result<PathBuf, String> {
    local_review_store_path(
        std::env::var("BITWEEN_ALLOW_LOCAL_REVIEW_STORE").ok().as_deref(),
        std::env::var("BITWEEN_USER_PREFERENCE_STORE").ok(),
    )
}

fn local_review_store_path(
    allow_local_review_store: Option<&str>,
    configured_path: Option<String>,
) -> Result<PathBuf, String> {
    if !truthy(allow_local_review_store) {
        return Err(
            "PostgreSQL relational user preference storage is required; set BITWEEN_POSTGRES_DSN for production wiring or BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true only for hermetic local review."
                .to_owned(),
        );
    }
    Ok(configured_path
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(".bitween/local-review/settings/preferences.json")))
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

fn postgres_actor() -> Result<String, String> {
    std::env::var("BITWEEN_SESSION_JWT_SUBJECT")
        .ok()
        .map(|value| value.trim().to_owned())
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "postgres_user_subject_required".to_owned())
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_preferences_are_korean_first_and_work_dense() {
        let store = empty_store(10);
        assert_eq!(store.schema, "bitween.user-preferences.v1");
        assert_eq!(store.current.locale, "ko-KR");
        assert_eq!(store.current.sidebar_theme, "steel");
        assert_eq!(store.current.workspace_density, "work_dense");
        assert_eq!(store.updated_at_unix, 10);
    }

    #[test]
    fn update_preferences_validates_theme_and_locale() {
        let mut store = empty_store(1);
        update_preferences(
            &mut store,
            UserPreferenceInput {
                locale: Some("ko-KR".to_owned()),
                sidebar_theme: Some("navy".to_owned()),
                workspace_density: Some("comfortable".to_owned()),
                notification_digest: Some("urgent_only".to_owned()),
                payroll_standard_view: Some("always_visible".to_owned()),
            },
            99,
        )
        .unwrap();
        assert_eq!(store.current.sidebar_theme, "navy");
        assert_eq!(store.current.workspace_density, "comfortable");
        assert_eq!(store.current.notification_digest, "urgent_only");
        assert_eq!(store.current.payroll_standard_view, "always_visible");
        assert_eq!(store.updated_at_unix, 99);
    }

    #[test]
    fn unsupported_preferences_are_rejected() {
        let mut store = empty_store(1);
        let error = update_preferences(
            &mut store,
            UserPreferenceInput {
                locale: Some("fr-FR".to_owned()),
                sidebar_theme: None,
                workspace_density: None,
                notification_digest: None,
                payroll_standard_view: None,
            },
            99,
        )
        .unwrap_err();
        assert!(error.contains("unsupported user preference value for locale"));
    }

    #[test]
    fn local_file_store_requires_explicit_hermetic_review_flag() {
        let error = local_review_store_path(None, None).unwrap_err();
        assert!(error.contains("PostgreSQL relational user preference storage is required"));
        let path = local_review_store_path(Some("true"), None).unwrap();
        assert_eq!(path, PathBuf::from(".bitween/local-review/settings/preferences.json"));
    }

    #[test]
    fn postgres_preference_sql_is_tenant_user_scoped_and_upserts() {
        let select = postgres_user_preference_select_sql();
        assert!(select.contains("bitween_settings.user_preference"));
        assert!(select.contains("tenant_id = $1 AND user_id = $2"));

        let upsert = postgres_user_preference_upsert_sql();
        assert!(upsert.contains("INSERT INTO bitween_settings.user_preference"));
        assert!(upsert.contains("ON CONFLICT (tenant_id, user_id) DO UPDATE"));
        assert!(upsert.contains("locale = EXCLUDED.locale"));
        assert!(upsert.contains("payroll_standard_view = EXCLUDED.payroll_standard_view"));
    }
}
