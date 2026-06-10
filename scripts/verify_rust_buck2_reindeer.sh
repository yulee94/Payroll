#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

buck2 build //...
buck2 build \
  '//crates/payroll-api:payroll_api[check]' \
  '//crates/payroll-api:platform_live_view[check]' \
  '//crates/payroll-api:auth_session_validate[check]' \
  '//crates/payroll-api:authz_decision[check]' \
  '//crates/payroll-api:hr_employee_store[check]' \
  '//crates/payroll-api:archive_intake_store[check]' \
  '//crates/payroll-api:user_preference_store[check]' \
  '//crates/payroll-api:workflow_template_store[check]' \
  '//crates/payroll-api:postgres_migrate[check]' \
  '//crates/payroll-api:cloud_native_audit_worker[check]' \
  '//crates/workflow-core:workflow_core[check]'
buck2 test //...
reindeer --config reindeer.toml vendor
reindeer --config reindeer.toml buckify
git diff --exit-code -- third-party/rust/BUCK third-party/rust/vendor
