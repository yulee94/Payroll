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
cargo test --workspace
```

`third-party/rust/BUCK` and `third-party/rust/vendor/` are generated from the
Cargo workspace lockfile. Do not hand-edit generated Buck rules or vendored
sources; update Cargo manifests, rerun Reindeer, and review the generated diff.

Vendoring is intentional so Buck2 builds do not depend on crates.io network
access at build time.
