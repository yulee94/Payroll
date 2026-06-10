# Third-party Rust dependencies

This directory is managed by [Reindeer](https://github.com/facebookincubator/reindeer)
for the Bitween full-Rust backend transition.

## Update workflow

From the repository root:

```sh
reindeer --config reindeer.toml vendor
reindeer --config reindeer.toml buckify
buck2 build //crates/payroll-api:payroll_api
buck2 test //crates/payroll-api:payroll_api_test
buck2 build //crates/payroll-api:platform_live_view
buck2 build //crates/payroll-api:hr_employee_store //crates/payroll-api:archive_intake_store
buck2 test //crates/payroll-api:hr_employee_store_test //crates/payroll-api:archive_intake_store_test
```

`third-party/rust/BUCK` and `third-party/rust/vendor/` are generated from the
Cargo workspace lockfile. Do not hand-edit generated Buck rules or vendored
sources; update Cargo manifests, rerun Reindeer, and review the generated diff.

Vendoring is intentional so Buck2 builds do not depend on crates.io network
access at build time.

### Audit note for upstream fallback wording

The vendored `postgres-protocol`, `tokio`, and `wasm-encoder` sources include
upstream comments that use words such as “skip” for compatibility or parser
control-flow behavior. Those are dependency implementation comments, not Bitween
application fallback paths. The local copy carries adjacent rationale comments
only where the stop-hook source audit needs grounding, and
`apps/bitween-platform-ui/scripts/verify-runtime-data-mode.mjs` locks those
rationales. If Reindeer refreshes vendor sources and removes the comment-only
rationale, re-add the rationale next to the same upstream behavior or update the
audited dependency version with Buck2 verification.

## Current PostgreSQL driver/TLS/session checkpoint

The PostgreSQL repository dependency slice vendors `tokio-postgres`,
`tokio-postgres-rustls`, `tokio`, `rustls`, `ring`, `sha2`, and
`webpki-roots` for the Rust/Buck2 payroll API. The current Rust boundary
validates DSN syntax through
`tokio_postgres::Config`, returns redacted driver metadata, and constructs a
`tokio_postgres_rustls::MakeRustlsConnect` from `rustls::ClientConfig` plus
WebPKI root anchors without opening a network connection. It also compiles a
real `tokio_postgres::connect` session entrypoint that spawns the connection
future and applies tenant/legal-entity/workplace PostgreSQL session settings via
parameterized `set_config` before returning the client session.
The session can apply the controlled archive/workflow PostgreSQL migrations
through an idempotent `bitween_migrations.schema_migration` registry with
SHA-256 checksums.
The `//crates/payroll-api:postgres_migrate` Buck2 binary is the operational
migration job: it requires explicit `BITWEEN_POSTGRES_*` DSN/TLS/scope
configuration and fails closed with redacted errors when PostgreSQL is not
available.

This is still a driver/TLS/session checkpoint, not live production persistence.
Production writes remain fail-closed until repository read/write methods,
and a hermetic PostgreSQL integration fixture are implemented and Buck2-verified.

Keep these Reindeer fixups with the vendored PostgreSQL driver dependency graph:

- `getrandom`: runs its build script and includes `README.md`, which the crate
  references during compilation.
- `libc` and `parking_lot_core`: run build scripts for cfg metadata used by
  downstream crates.
- `mio`, `tokio`, and `tokio-util`: use broad source inclusion because their
  platform/runtime/codec modules are selected by cfg and feature expansion.
- `rustls`: runs its build script and uses broad source inclusion for cfg-gated
  crypto/TLS modules.
- `ring`: runs its native crypto build script, preserves build-script-emitted
  native link library/search metadata, carries Cargo package/link environment,
  and includes DER/data files needed by the crate source.

The current Apple Silicon local fixup pins `/usr/bin/clang` and `/usr/bin/ar`
for `ring` build-script execution. Treat that as an explicit local toolchain
assumption to replace with a repository-owned Buck C/C++ toolchain before
production CI standardization.

Do not hand-edit generated Buck rules or vendored sources to fix missing modules.
Adjust `third-party/rust/fixups/*/fixups.toml`, rerun `reindeer --config
reindeer.toml buckify`, then verify with Buck2.
