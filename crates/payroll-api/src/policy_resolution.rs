use crate::policy::{OperationPolicy, OperationPolicySnapshot};
use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum OperationPolicySource {
    Site,
    Tenant,
    Global,
}

impl OperationPolicySource {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Site => "site",
            Self::Tenant => "tenant",
            Self::Global => "global",
        }
    }
}

impl Serialize for OperationPolicySource {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct PayrollPolicySettings {
    pub tenant_policy: Option<OperationPolicy>,
    pub site_policies: BTreeMap<String, OperationPolicy>,
    pub workplace_aliases: BTreeMap<String, Vec<String>>,
}

impl PayrollPolicySettings {
    pub fn with_tenant_policy(mut self, policy: OperationPolicy) -> Self {
        self.tenant_policy = Some(policy);
        self
    }

    pub fn with_site_policy(
        mut self,
        workplace: impl Into<String>,
        policy: OperationPolicy,
    ) -> Self {
        let workplace = clean(workplace);
        if !workplace.is_empty() {
            let canonical = canonical_workplace(&workplace, &self.workplace_aliases);
            self.site_policies.insert(canonical, policy);
        }
        self
    }

    pub fn with_workplace_aliases<I, S>(mut self, canonical: impl Into<String>, aliases: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        let canonical = clean(canonical);
        if canonical.is_empty() {
            return self;
        }
        let mut values = aliases
            .into_iter()
            .map(clean)
            .filter(|value| !value.is_empty())
            .collect::<Vec<_>>();
        if !values.iter().any(|value| value == &canonical) {
            values.push(canonical.clone());
        }
        values.sort();
        values.dedup();
        self.workplace_aliases.insert(canonical, values);
        self
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ResolvedOperationPolicy {
    pub workplace: String,
    pub policy: OperationPolicy,
    pub source: OperationPolicySource,
    pub has_site_override: bool,
}

impl ResolvedOperationPolicy {
    pub fn snapshot(&self) -> OperationPolicySnapshot {
        OperationPolicySnapshot::new(self.policy.clone(), self.source.as_str())
    }
}

pub fn resolve_operation_policy(
    workplace: impl Into<String>,
    settings: &PayrollPolicySettings,
) -> ResolvedOperationPolicy {
    let workplace = canonical_workplace(&clean(workplace), &settings.workplace_aliases);

    if !workplace.is_empty()
        && let Some(policy) = settings.site_policies.get(&workplace)
    {
        return resolved(workplace, policy.clone(), OperationPolicySource::Site, true);
    }

    if let Some(policy) = settings.tenant_policy.clone() {
        return resolved(workplace, policy, OperationPolicySource::Tenant, false);
    }

    resolved(
        workplace,
        OperationPolicy::default(),
        OperationPolicySource::Global,
        false,
    )
}

fn resolved(
    workplace: String,
    policy: OperationPolicy,
    source: OperationPolicySource,
    has_site_override: bool,
) -> ResolvedOperationPolicy {
    ResolvedOperationPolicy {
        workplace,
        policy: policy.normalized(),
        source,
        has_site_override,
    }
}

fn canonical_workplace(
    workplace: &str,
    workplace_aliases: &BTreeMap<String, Vec<String>>,
) -> String {
    if workplace.is_empty() {
        return String::new();
    }
    for (canonical, aliases) in workplace_aliases {
        let canonical = clean(canonical);
        if workplace == canonical || aliases.iter().map(clean).any(|alias| alias == workplace) {
            return canonical;
        }
    }
    workplace.to_owned()
}

fn clean(value: impl Into<String>) -> String {
    value.into().trim().to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::policy::{OperationPolicy, PayrollInputBasis};
    use crate::service::{PayrollApiService, ServiceConfig};
    use serde_json::json;

    #[test]
    fn site_policy_overrides_tenant_policy_and_normalizes() {
        let mut site_policy = OperationPolicy::new(PayrollInputBasis::Invoice);
        site_policy.payday = Some(String::new());
        site_policy.attendance.rounding_minutes = -10;
        let settings = PayrollPolicySettings::default()
            .with_tenant_policy(OperationPolicy::new(PayrollInputBasis::Attendance))
            .with_site_policy("Site A", site_policy);

        let resolved = resolve_operation_policy(" Site A ", &settings);
        let value = serde_json::to_value(&resolved).unwrap();

        assert_eq!(resolved.source, OperationPolicySource::Site);
        assert_eq!(resolved.workplace, "Site A");
        assert!(resolved.has_site_override);
        assert_eq!(resolved.policy.input_basis, PayrollInputBasis::Invoice);
        assert_eq!(value["source"], "site");
        assert_eq!(value["has_site_override"], true);
        assert_eq!(value["policy"]["payday"], "25일");
        assert_eq!(value["policy"]["attendance"]["rounding_minutes"], 1);
    }

    #[test]
    fn supplied_aliases_canonicalize_site_policy_lookup() {
        let settings = PayrollPolicySettings::default()
            .with_workplace_aliases("Site A", ["A Site", "site-a"])
            .with_site_policy("Site A", OperationPolicy::new(PayrollInputBasis::Invoice));

        let resolved = resolve_operation_policy("site-a", &settings);

        assert_eq!(resolved.source, OperationPolicySource::Site);
        assert_eq!(resolved.workplace, "Site A");
        assert_eq!(resolved.policy.input_basis, PayrollInputBasis::Invoice);
    }

    #[test]
    fn tenant_policy_falls_back_when_site_override_is_absent() {
        let settings = PayrollPolicySettings::default()
            .with_tenant_policy(OperationPolicy::new(PayrollInputBasis::Attendance));

        let resolved = resolve_operation_policy("Site B", &settings);

        assert_eq!(resolved.source, OperationPolicySource::Tenant);
        assert!(!resolved.has_site_override);
        assert_eq!(resolved.workplace, "Site B");
        assert_eq!(resolved.policy.input_basis, PayrollInputBasis::Attendance);
    }

    #[test]
    fn global_default_is_used_without_site_or_tenant_policy() {
        let settings = PayrollPolicySettings::default();

        let resolved = resolve_operation_policy("", &settings);

        assert_eq!(resolved.source, OperationPolicySource::Global);
        assert_eq!(resolved.workplace, "");
        assert_eq!(resolved.policy.input_basis, PayrollInputBasis::Hybrid);
    }

    #[test]
    fn service_validates_payload_with_rust_policy_resolution() {
        let service = PayrollApiService::new(ServiceConfig::default());
        let settings = PayrollPolicySettings::default()
            .with_tenant_policy(OperationPolicy::new(PayrollInputBasis::Invoice))
            .with_site_policy(
                "Site A",
                OperationPolicy::new(PayrollInputBasis::Attendance),
            );

        let response = service.validate_run_payload_with_policy_settings(
            json!({
                "request_id": "req-policy-resolution",
                "affiliate": "COSS",
                "workplace": "Site A",
                "period": "2026-05",
                "attendance_path": "attendance.csv",
                "input_type": "auto"
            }),
            &settings,
        );
        let value = serde_json::to_value(response).unwrap();

        assert_eq!(value["status"], "validated");
        assert_eq!(value["input_type"], "attendance");
        assert_eq!(value["requested_input_type"], "auto");
        assert_eq!(value["operation_policy_source"], "site");
        assert_eq!(value["operation_policy"]["input_basis"], "attendance");
    }
}
