#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

cargo test --workspace
reindeer --config reindeer.toml vendor
reindeer --config reindeer.toml buckify
git diff --exit-code -- third-party/rust/BUCK third-party/rust/vendor
buck2 build //crates/payroll-api:payroll_api
buck2 test //crates/payroll-api:payroll_api_test
