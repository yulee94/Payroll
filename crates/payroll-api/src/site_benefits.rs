use serde::Serialize;

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct WorkersDayConfig {
    pub enabled: bool,
    pub default_amount: i64,
    pub auto_from_invoice: bool,
}

impl Default for WorkersDayConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            default_amount: 0,
            auto_from_invoice: true,
        }
    }
}

impl WorkersDayConfig {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn normalized(self) -> Self {
        Self {
            enabled: self.enabled,
            default_amount: self.default_amount.max(0),
            auto_from_invoice: self.auto_from_invoice,
        }
    }

    pub fn with_enabled(mut self, enabled: bool) -> Self {
        self.enabled = enabled;
        self
    }

    pub fn with_default_amount(mut self, amount: i64) -> Self {
        self.default_amount = amount;
        self
    }

    pub fn with_auto_from_invoice(mut self, auto_from_invoice: bool) -> Self {
        self.auto_from_invoice = auto_from_invoice;
        self
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct IdentityInsuranceConfig {
    pub enabled: bool,
    pub annual_amount: i64,
    pub billing_month: u8,
}

impl Default for IdentityInsuranceConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            annual_amount: 0,
            billing_month: 1,
        }
    }
}

impl IdentityInsuranceConfig {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn normalized(self) -> Self {
        Self {
            enabled: self.enabled,
            annual_amount: self.annual_amount.max(0),
            billing_month: self.billing_month.clamp(1, 12),
        }
    }

    pub fn with_enabled(mut self, enabled: bool) -> Self {
        self.enabled = enabled;
        self
    }

    pub fn with_annual_amount(mut self, amount: i64) -> Self {
        self.annual_amount = amount;
        self
    }

    pub fn with_billing_month(mut self, month: u8) -> Self {
        self.billing_month = month;
        self
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct SiteBenefitsConfig {
    pub workers_day_allowance: WorkersDayConfig,
    pub workers_day_source: String,
    pub identity_guarantee_insurance: IdentityInsuranceConfig,
    pub identity_insurance_source: String,
    pub identity_insurance_already_applied: bool,
}

impl Default for SiteBenefitsConfig {
    fn default() -> Self {
        Self {
            workers_day_allowance: WorkersDayConfig::new(),
            workers_day_source: "global".to_owned(),
            identity_guarantee_insurance: IdentityInsuranceConfig::new(),
            identity_insurance_source: "global".to_owned(),
            identity_insurance_already_applied: false,
        }
    }
}

impl SiteBenefitsConfig {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn normalized(self) -> Self {
        Self {
            workers_day_allowance: self.workers_day_allowance.normalized(),
            workers_day_source: clean_source(&self.workers_day_source),
            identity_guarantee_insurance: self.identity_guarantee_insurance.normalized(),
            identity_insurance_source: clean_source(&self.identity_insurance_source),
            identity_insurance_already_applied: self.identity_insurance_already_applied,
        }
    }

    pub fn with_workers_day(mut self, config: WorkersDayConfig, source: impl Into<String>) -> Self {
        self.workers_day_allowance = config;
        self.workers_day_source = clean_source(&source.into());
        self
    }

    pub fn with_identity_insurance(
        mut self,
        config: IdentityInsuranceConfig,
        source: impl Into<String>,
    ) -> Self {
        self.identity_guarantee_insurance = config;
        self.identity_insurance_source = clean_source(&source.into());
        self
    }

    pub fn with_identity_already_applied(mut self, already_applied: bool) -> Self {
        self.identity_insurance_already_applied = already_applied;
        self
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize)]
pub struct SiteBenefitsInvoice {
    pub name: String,
    pub workplace: String,
    pub base_salary: i64,
    pub workers_day_pay: i64,
    pub workers_day_allowance: i64,
    pub identity_guarantee_insurance_deduction: i64,
    #[serde(rename = "_workers_day_source")]
    pub workers_day_source: String,
    #[serde(rename = "_identity_insurance_source")]
    pub identity_insurance_source: String,
}

impl SiteBenefitsInvoice {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: clean(name),
            ..Self::default()
        }
    }

    pub fn with_workplace(mut self, workplace: impl Into<String>) -> Self {
        self.workplace = clean(workplace);
        self
    }

    pub fn with_base_salary(mut self, amount: i64) -> Self {
        self.base_salary = amount;
        self
    }

    pub fn with_workers_day_pay(mut self, amount: i64) -> Self {
        self.workers_day_pay = amount;
        self
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct SiteBenefitsApplication {
    pub workers_day_allowance: i64,
    pub identity_guarantee_insurance_deduction: i64,
    pub workers_day_source: String,
    pub identity_insurance_source: String,
    pub invoice: SiteBenefitsInvoice,
}

pub fn apply_site_benefits_to_invoice<S>(
    mut invoice: SiteBenefitsInvoice,
    config: &SiteBenefitsConfig,
    payroll_period: S,
) -> SiteBenefitsApplication
where
    S: AsRef<str>,
{
    let config = config.clone().normalized();
    let month = parse_period_month(payroll_period.as_ref());
    let workers_day_allowance = calc_workers_day_allowance(&invoice, &config, month);
    let identity_deduction = calc_identity_guarantee_insurance_deduction(&config, month);

    invoice.workers_day_allowance = workers_day_allowance;
    invoice.identity_guarantee_insurance_deduction = identity_deduction;
    invoice.workers_day_source = config.workers_day_source.clone();
    invoice.identity_insurance_source = config.identity_insurance_source.clone();

    SiteBenefitsApplication {
        workers_day_allowance,
        identity_guarantee_insurance_deduction: identity_deduction,
        workers_day_source: config.workers_day_source,
        identity_insurance_source: config.identity_insurance_source,
        invoice,
    }
}

fn calc_workers_day_allowance(
    invoice: &SiteBenefitsInvoice,
    config: &SiteBenefitsConfig,
    month: Option<u8>,
) -> i64 {
    let workers = config.workers_day_allowance.clone().normalized();
    if !workers.enabled {
        return 0;
    }
    if workers.auto_from_invoice {
        return invoice.workers_day_pay.max(0);
    }
    if workers.default_amount <= 0 {
        return 0;
    }
    if month == Some(5) {
        workers.default_amount
    } else {
        0
    }
}

fn calc_identity_guarantee_insurance_deduction(
    config: &SiteBenefitsConfig,
    month: Option<u8>,
) -> i64 {
    let identity = config.identity_guarantee_insurance.clone().normalized();
    if !identity.enabled || identity.annual_amount <= 0 {
        return 0;
    }
    if month != Some(identity.billing_month) {
        return 0;
    }
    if config.identity_insurance_already_applied {
        return 0;
    }
    -identity.annual_amount
}

fn parse_period_month(period: &str) -> Option<u8> {
    let raw = period.trim();
    if raw.len() >= 7 && raw.as_bytes().get(4) == Some(&b'-') {
        return raw[5..7].parse::<u8>().ok();
    }
    None
}

fn clean(value: impl Into<String>) -> String {
    value.into().trim().to_owned()
}

fn clean_source(value: &str) -> String {
    let source = value.trim();
    if source.is_empty() {
        "global".to_owned()
    } else {
        source.to_owned()
    }
}

#[cfg(test)]
mod tests {
    use crate::service::{PayrollApiService, ServiceConfig};
    use crate::site_benefits::{
        apply_site_benefits_to_invoice, IdentityInsuranceConfig, SiteBenefitsConfig,
        SiteBenefitsInvoice, WorkersDayConfig,
    };
    use serde_json::json;

    #[test]
    fn normalizes_configs_like_python() {
        let workers = WorkersDayConfig::new()
            .with_enabled(true)
            .with_default_amount(-1)
            .with_auto_from_invoice(false)
            .normalized();
        let identity = IdentityInsuranceConfig::new()
            .with_enabled(true)
            .with_annual_amount(-20)
            .with_billing_month(99)
            .normalized();

        assert!(workers.enabled);
        assert_eq!(workers.default_amount, 0);
        assert!(!workers.auto_from_invoice);
        assert!(identity.enabled);
        assert_eq!(identity.annual_amount, 0);
        assert_eq!(identity.billing_month, 12);
    }

    #[test]
    fn applies_workers_day_and_identity_deduction_for_supplied_config() {
        let invoice = SiteBenefitsInvoice::new("박민수")
            .with_workplace("한국앰코")
            .with_workers_day_pay(99_999)
            .with_base_salary(2_090_000);
        let config = SiteBenefitsConfig::new()
            .with_workers_day(
                WorkersDayConfig::new()
                    .with_enabled(true)
                    .with_default_amount(12_000)
                    .with_auto_from_invoice(false),
                "site",
            )
            .with_identity_insurance(
                IdentityInsuranceConfig::new()
                    .with_enabled(true)
                    .with_annual_amount(20_000)
                    .with_billing_month(5),
                "site",
            );

        let result = apply_site_benefits_to_invoice(invoice, &config, "2026-05");

        assert_eq!(result.workers_day_allowance, 12_000);
        assert_eq!(result.identity_guarantee_insurance_deduction, -20_000);
        assert_eq!(result.workers_day_source, "site");
        assert_eq!(result.identity_insurance_source, "site");
        assert_eq!(result.invoice.workers_day_allowance, 12_000);
        assert_eq!(
            result.invoice.identity_guarantee_insurance_deduction,
            -20_000
        );
        assert_eq!(result.invoice.workers_day_source, "site");
        assert_eq!(result.invoice.identity_insurance_source, "site");
    }

    #[test]
    fn suppresses_identity_deduction_when_already_applied() {
        let invoice = SiteBenefitsInvoice::new("박민수").with_workplace("한국앰코");
        let config = SiteBenefitsConfig::new()
            .with_identity_insurance(
                IdentityInsuranceConfig::new()
                    .with_enabled(true)
                    .with_annual_amount(20_000)
                    .with_billing_month(5),
                "site",
            )
            .with_identity_already_applied(true);

        let result = apply_site_benefits_to_invoice(invoice, &config, "2026-05");

        assert_eq!(result.identity_guarantee_insurance_deduction, 0);
        assert_eq!(result.invoice.identity_guarantee_insurance_deduction, 0);
    }

    #[test]
    fn serializes_compatibility_shape() {
        let invoice = SiteBenefitsInvoice::new("홍길동")
            .with_workers_day_pay(15_000)
            .with_base_salary(2_000_000);
        let config = SiteBenefitsConfig::new().with_workers_day(
            WorkersDayConfig::new()
                .with_enabled(true)
                .with_auto_from_invoice(true),
            "tenant",
        );

        let result = apply_site_benefits_to_invoice(invoice, &config, "2026-04");
        let value = serde_json::to_value(result).unwrap();

        assert_eq!(value["workers_day_allowance"], json!(15_000));
        assert_eq!(value["identity_guarantee_insurance_deduction"], json!(0));
        assert_eq!(value["workers_day_source"], "tenant");
        assert_eq!(value["invoice"]["_workers_day_source"], "tenant");
        assert_eq!(value["invoice"]["_identity_insurance_source"], "global");
    }

    #[test]
    fn service_delegates_site_benefits_application() {
        let service = PayrollApiService::new(ServiceConfig::default());
        let invoice = SiteBenefitsInvoice::new("홍길동");
        let config = SiteBenefitsConfig::new().with_workers_day(
            WorkersDayConfig::new()
                .with_enabled(true)
                .with_default_amount(10_000)
                .with_auto_from_invoice(false),
            "site",
        );

        let result = service.apply_site_benefits_to_invoice(invoice, &config, "2026-05");

        assert_eq!(result.workers_day_allowance, 10_000);
        assert_eq!(result.invoice.workers_day_allowance, 10_000);
    }
}
