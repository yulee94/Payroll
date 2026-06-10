# PostgreSQL repository adapter decision

Status: accepted for first production persistence adapter slice, 2026-06-10.

## Context

Bitween production uses PostgreSQL as the relational system of record for HR,
payroll, workflow, archive/intake, settings, audit, staging, review, and
admission data. The workflow-template path, HR employee store, archive intake
store, and settings preference store now have Buck2-built Rust PostgreSQL
adapters. Local review files remain available only behind the explicit hermetic
local-review flag.

The next adapter must fit these constraints:

- Rust backend only.
- Buck2/Reindeer-managed dependencies.
- No fake DSN wiring.
- Internal product operated on managed Kubernetes.
- Secure handling of payroll/personnel data.
- Small first production slice that can be verified before broad persistence
  migration.

## Decision

Decision: use tokio-postgres with a TLS-capable connector boundary.

Use `tokio-postgres` as the first PostgreSQL driver for production repository
adapters. Keep the repository boundary explicit so local review adapters,
PostgreSQL adapters, and future test adapters cannot silently substitute for one
another.

Production database traffic must use a TLS-capable connector boundary. Prefer a
`tokio-postgres-rustls` path for direct database TLS where the managed
Kubernetes/network layer does not already provide an approved encrypted
transport boundary. NoTls must not be used for production database traffic.

`postgres` remains acceptable only as a blocking façade if a CLI edge or
one-shot migration tool needs synchronous ergonomics; it is documented as a
wrapper over `tokio-postgres` and should not become a separate database strategy.

sqlx is deferred for the first adapter slice. Its compile-time query checking
is attractive, but it introduces a larger runtime/build surface and requires
build-time database access or offline query metadata discipline. That is useful
later after the migration repository and CI database fixture are formalized, but
it is unnecessary for the first “real adapter exists and fails safely” slice.

## Source evidence

- `tokio-postgres` docs: native asynchronous PostgreSQL client, optional runtime
  feature, and TLS implemented through connector crates:
  https://docs.rs/tokio-postgres/latest/tokio_postgres/
- `tokio-postgres-rustls` docs: rustls integration for `tokio-postgres`, with
  explicit crypto-provider/root-store feature selection:
  https://docs.rs/tokio-postgres-rustls/latest/tokio_postgres_rustls/
- `postgres` docs: synchronous client and wrapper over `tokio-postgres` plus a
  Tokio runtime:
  https://docs.rs/postgres/latest/postgres/
- SQLx query macro docs: statically checked query macro and its configuration /
  offline-mode implications:
  https://docs.rs/sqlx/latest/sqlx/macro.query.html
- SQLx upstream README: async pure-Rust SQL toolkit, compile-time checked query
  option, runtime/TLS choices, safety and license statements:
  https://github.com/transact-rs/sqlx
- PostgreSQL `set_config` documentation: `is_local = true` is transaction
  scoped, while `false` applies for the current session; Bitween uses
  session-scoped tenant settings for RLS on the long-lived client session:
  https://www.postgresql.org/docs/current/functions-admin.html

## Implementation shape

1. Add the smallest dependency set through `Cargo.toml`, `Cargo.lock`, Reindeer
   vendor, and Reindeer buckify. Allowed Cargo usage stays limited to
   metadata/vendor inputs for Buck/Reindeer.
2. Add a `postgres_repository` module that owns:
   - DSN validation without logging secrets,
   - TLS mode policy,
   - tenant session-setting contract,
   - migration-readiness probe,
   - structured errors that redact host/user/password details.
3. Wire narrow repository paths incrementally on top of the migration runner:
   workflow-template read/write/edit/execute first, then HR employee management,
   then archive intake metadata/issues, then settings preferences.
4. Keep `BITWEEN_ALLOW_LOCAL_REVIEW_STORE=true` as the only local JSON review
   path. With a DSN, a route may proceed only when its Rust PostgreSQL adapter
   is linked and verified; otherwise the route/store must fail closed without
   local side effects.
5. Add Buck2 tests for input validation, redaction, SQL contract construction,
   and fail-closed behavior. Add integration tests only when a hermetic local
   PostgreSQL fixture exists.

## Current verified checkpoint

The first Rust boundary contract now exists in
`crates/payroll-api/src/postgres_repository.rs` and is exported from
`crates/payroll-api/src/lib.rs`. It is intentionally the shared configuration
and safety contract that live repository adapters must use:

- accepts only PostgreSQL DSN schemes,
- defaults to `verify-full` TLS policy,
- rejects no-TLS production modes with the stable
  `postgres_no_tls_rejected` error,
- exposes only `postgres://<redacted>` status text,
- keeps implicit migrations disabled,
- provides parameterized tenant/legal-entity/workplace session-setting SQL for
  future PostgreSQL row-level-security enforcement.

Production write paths must still fail closed unless the route has actual
Buck2-built repository read/write methods, the migration runner is linked, and
the route can return only sanitized PostgreSQL failure details.

The next dependency checkpoint is also verified: `tokio-postgres = "0.7"` is
declared in `crates/payroll-api/Cargo.toml`, locked in `Cargo.lock`, vendored
through Reindeer, and exposed to Buck as `//third-party/rust:tokio-postgres`.
`PostgresRepositoryConfig::validate_driver_config` parses configured DSNs through
`tokio_postgres::Config` without opening a network connection, then returns only
redacted driver metadata. The metadata names `tokio-postgres-rustls` as the
required TLS connector for the production connection slice.

The TLS connector dependency checkpoint is also verified:
`tokio-postgres-rustls = "0.14"`, `rustls = "0.23"`, and `webpki-roots = "1"`
are declared in `crates/payroll-api/Cargo.toml`, locked in `Cargo.lock`,
vendored through Reindeer, and exposed to Buck as
`//third-party/rust:tokio-postgres-rustls`, `//third-party/rust:rustls`, and
`//third-party/rust:webpki-roots`. `PostgresRepositoryConfig::build_tls_connector`
constructs a `tokio_postgres_rustls::MakeRustlsConnect` from a
`rustls::ClientConfig` and WebPKI root anchors without opening a network
connection. It only builds under the `verify-full` policy and records a profile
that marks the connector as `ring` + `webpki-roots` with `permits_no_tls: false`.

The connection/session checkpoint is now compiled and unit-tested:
`tokio = "1"` is declared as a direct dependency, exposed through
`//third-party/rust:tokio`, and used by
`PostgresRepositoryConfig::connect_client_session`. That entrypoint performs the
real `tokio_postgres::connect` call with the rustls connector, spawns the
connection future, and applies tenant/legal-entity/workplace scope with a single
parameterized `set_config` batch before returning a `PostgresClientSession`.
`PostgresTenantScope` rejects blank scope values, and connection/session errors
return only stable codes such as `postgres_connect_failed` or
`postgres_tenant_session_failed` plus `postgres://<redacted>`.

The migration runner checkpoint is also compiled and unit-tested. `sha2 =
"0.11"` is declared as a direct dependency, exposed through
`//third-party/rust:sha2`, and used to compute SHA-256 checksums for each
controlled migration. `required_postgres_migrations` enumerates the archive
intake, workflow-template, and HR employee migrations in order.
`PostgresClientSession`
creates an idempotent `bitween_migrations.schema_migration` registry,
short-circuits already-applied migrations with matching checksums, fails closed
with `postgres_migration_checksum_mismatch` on drift, and records
`PostgresMigrationReceipt` values after successful application.

The operational migration job checkpoint is compiled and unit-tested as
`//crates/payroll-api:postgres_migrate`. The job reads only explicit
`BITWEEN_POSTGRES_*` environment variables, requires tenant/legal-entity/
workplace scope, connects through `connect_client_session`, applies
`required_postgres_migrations`, returns stable JSON schema
`bitween.postgres-migrate.v1`, and exits non-zero with sanitized error codes
when configuration, connection, scope, or migration execution is unavailable.

The workflow-template repository adapter checkpoint is now compiled and
unit-tested as `//crates/payroll-api:workflow_template_store`. When
`BITWEEN_POSTGRES_DSN` is configured, the store uses explicit
`BITWEEN_POSTGRES_TENANT_ID`, `BITWEEN_POSTGRES_LEGAL_ENTITY_ID`, and
`BITWEEN_POSTGRES_WORKPLACE_ID`, connects through `connect_client_session`,
applies `required_postgres_migrations`, reads workflow templates/nodes/edges/
data records from PostgreSQL, and persists workflow edits/executions back into
`bitween_workflow.workflow_template`, `workflow_template_version`,
`workflow_node`, `workflow_edge`, `workflow_audit_event`, and
`workflow_data_record`. It preserves i18n fallback behavior for built-in payroll
steps by storing the step key when no user override exists, then returning no
visible title/action override to the UI.

The HR employee repository adapter checkpoint is now compiled and unit-tested as
`//crates/payroll-api:hr_employee_store`. When `BITWEEN_POSTGRES_DSN` is
configured, the store uses explicit `BITWEEN_POSTGRES_TENANT_ID`,
`BITWEEN_POSTGRES_LEGAL_ENTITY_ID`, and `BITWEEN_POSTGRES_WORKPLACE_ID`,
connects through `connect_client_session`, applies `required_postgres_migrations`,
reads employee records from `bitween_hr.employee`, and persists HR add/update/
remove operations to PostgreSQL instead of falling back to local review files.
The schema in `crates/payroll-api/migrations/003_hr_employee.sql` enforces
tenant/legal-entity/workplace scope, row-level security, constrained employment
statuses, restricted/confidential sensitivity labels, and update timestamps.

The archive intake repository adapter checkpoint is now compiled and unit-tested
as `//crates/payroll-api:archive_intake_store`. When `BITWEEN_POSTGRES_DSN` is
configured, the store uses explicit `BITWEEN_POSTGRES_TENANT_ID`,
`BITWEEN_POSTGRES_LEGAL_ENTITY_ID`, and `BITWEEN_POSTGRES_WORKPLACE_ID`,
connects through `connect_client_session`, applies `required_postgres_migrations`,
reads archive metadata/issues from `bitween_archive.archive_intake` and
`bitween_archive.archive_intake_issue`, and persists RustFS-backed file intake
metadata plus human guidance/anomaly issues in PostgreSQL inside one transaction.
Ready HR employee, HR attendance, and payroll tabular samples are also
translated into `hr_employee_staging`, `hr_attendance_staging`, or
`payroll_input_staging` rows with row hashes and full row payload JSON before
canonical admission. Ambiguous mappings and blocking anomalies still create
human guidance/anomaly items instead of silently admitting data. Original files
still belong in RustFS before metadata/staging insertion. The same adapter now
supports the human-review resolution loop: `resolve` marks matching open
guidance/anomaly issues as resolved with bounded audit JSON, hides resolved
items from the operator response, and recomputes intake `status`,
`next_action`, and `postgres_ready` from the remaining open issues. Canonical
admission is also live-wired: `admit` requires PostgreSQL mode, a reviewed
`ready_for_staging` intake, manager-gated `archive_admit` authorization at the
preview route, and canonical table support. It upserts reviewed
`hr_employee_staging` rows into `bitween_hr.employee`,
`hr_attendance_staging` rows into `bitween_hr.attendance_record`, and
`payroll_input_staging` rows into `bitween_payroll.payroll_input`; invalid rows
are marked, row counts/rollback evidence are recorded in
`bitween_archive.archive_admission_audit`, row-level recovery metadata is
captured in `bitween_archive.archive_admission_recovery_point`, and source
workbook sync metadata is queued in `bitween_archive.archive_source_sync`.
These version/recovery records store JSON row deltas, checksums, RustFS object
URIs, and audit metadata only; PostgreSQL does not store binary workbook
snapshots. `rollback` requires PostgreSQL mode and manager-gated
`archive_rollback` authorization, restores selected/all available recovery
points for HR employee, HR attendance, and payroll input admissions, marks
recovery points restored, re-opens staging rows for review, queues a rollback
source-sync item, and moves the intake back to `ready_for_staging` instead of
leaving reviewed rows stranded in a UI-only queue.

The settings preference repository adapter checkpoint is now compiled and
unit-tested as `//crates/payroll-api:user_preference_store`. When
`BITWEEN_POSTGRES_DSN` is configured, the store uses explicit
`BITWEEN_POSTGRES_TENANT_ID`, `BITWEEN_POSTGRES_LEGAL_ENTITY_ID`, and
`BITWEEN_POSTGRES_WORKPLACE_ID`, requires `BITWEEN_SESSION_JWT_SUBJECT` for the
user-specific preference key, connects through `connect_client_session`, applies
`required_postgres_migrations`, reads `bitween_settings.user_preference`, and
upserts Korean-first settings preferences into PostgreSQL.

Preview-route fail-closed evidence now covers every PostgreSQL-backed route
slice. `npm run verify:route-authorization` starts the preview server with a
configured `BITWEEN_POSTGRES_DSN` plus tenant/legal-entity/workplace/session
scope, then verifies HR, archive intake, settings preferences, and workflow
template routes use their Rust PostgreSQL adapters rather than local-review
files. When PostgreSQL is unavailable, each route returns a 503 store-specific
error with only `postgres://<redacted>` detail, and the verifier asserts that no
local-review store files were created. The route verifier also exercises
authorized archive issue review in local hermetic mode and verifies the
configured-DSN path fails closed before local side effects when PostgreSQL is
unavailable. Archive admission is covered by the same authorization/fail-closed
route evidence: unauthenticated admission requests are denied before storage, and
configured-DSN admission returns a redacted PostgreSQL-unavailable response
without writing local review files. Archive rollback is covered by the same
route evidence: unauthenticated rollback requests are denied before mutation,
and configured-DSN rollback returns a redacted PostgreSQL-unavailable response
without writing local review files.

A hermetic PostgreSQL integration fixture is still pending. Do not claim the
entire persistence layer is production-complete until live PostgreSQL fixture
evidence exists. A local fixture probe on 2026-06-10 found no `postgres`,
`initdb`, `pg_ctl`, `psql`, `docker`, `podman`, `colima`, or `rustfs`
binary, so the next pipeline-hardening item is a repository-owned
PostgreSQL/RustFS fixture that can run under Buck2/CI. PostgreSQL writes remain fail-closed for any route that does not yet have its own Buck2-built Rust PostgreSQL adapter.

The Reindeer/Buck vendor fixups for `getrandom`, `libc`, `parking_lot_core`,
`mio`, `tokio`, `tokio-util`, `rustls`, and `ring` are part of the dependency
checkpoint. They run required build scripts, include cfg-gated source trees, and
for `ring` preserve build-script-emitted native link libraries/search paths so
Buck can compile and link the same Rust/native source graph hermetically. The
current Apple Silicon local fixup pins `/usr/bin/clang` and `/usr/bin/ar` for
ring's build script; replacing that host-tool assumption with a repository-owned
Buck C/C++ toolchain remains a pipeline-hardening item before production CI
standardization.

## Security rules

- Never print a full DSN or password in errors, logs, audit events, or UI.
- Set tenant/legal-entity/workplace context in the database session before
  tenant-scoped operations so PostgreSQL row-level security can enforce the same
  boundary as Rust ABAC/RBAC/PBAC.
- Use `set_config(..., false)` for the session-scoped tenant/legal-entity/
  workplace context. `set_config(..., true)` is transaction-local per
  PostgreSQL documentation and would reset after the setup statement when not
  wrapped in the exact same transaction.
- Treat database responses as untrusted at the boundary: decode into explicit
  Rust DTOs and validate enum/status fields before returning them to callers.
- Keep migration application as a controlled job, not an implicit side effect of
  ordinary read requests.

## Non-decisions

- This does not select an ORM.
- This does not enable production writes by itself.
- This does not remove local hermetic review adapters.
- This does not defer PostgreSQL; it only keeps the first dependency slice small
  and auditable.
