use serde::Serialize;

const EDI_APPLIED_BADGE: &str = "EDI 조회";
const EDI_OFF_MESSAGE: &str = "EDI 보험료 사용 꺼짐";
const EDI_MISSING_MESSAGE: &str = "EDI 보험료 없음";
const EDI_APPLIED_MESSAGE: &str = "EDI 보험료 적용";
const LONG_TERM_CARE_RATIO: f64 = 0.1295;

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum EdiPremiumSource {
    Manual,
    #[default]
    Import,
    Api,
    Calculated,
}

impl EdiPremiumSource {
    pub fn normalize(value: impl AsRef<str>) -> Self {
        match value.as_ref().trim().to_ascii_lowercase().as_str() {
            "manual" => Self::Manual,
            "api" => Self::Api,
            "calculated" => Self::Calculated,
            "import" => Self::Import,
            _ => Self::Import,
        }
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Manual => "manual",
            Self::Import => "import",
            Self::Api => "api",
            Self::Calculated => "calculated",
        }
    }

    pub const fn label(self) -> &'static str {
        match self {
            Self::Manual => "수동 등록",
            Self::Import => "CSV 가져오기",
            Self::Api => "EDI API",
            Self::Calculated => "자동 산출",
        }
    }
}

impl Serialize for EdiPremiumSource {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EdiInsuranceConfig {
    pub use_edi_premiums: bool,
    pub respect_age_exempt: bool,
}

impl Default for EdiInsuranceConfig {
    fn default() -> Self {
        Self {
            use_edi_premiums: false,
            respect_age_exempt: true,
        }
    }
}

impl EdiInsuranceConfig {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_use_edi_premiums(mut self, enabled: bool) -> Self {
        self.use_edi_premiums = enabled;
        self
    }

    pub fn with_respect_age_exempt(mut self, respect: bool) -> Self {
        self.respect_age_exempt = respect;
        self
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EdiInsurancePremiumRecord {
    pub employee_id: String,
    pub employee_name: String,
    pub period: String,
    pub national_pension: i64,
    pub health_insurance: i64,
    pub long_term_care: i64,
    pub employment_insurance: i64,
    pub industrial_accident: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub industrial_accident_employer: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub industrial_accident_employee: Option<i64>,
    pub management_no: String,
    pub source: EdiPremiumSource,
    pub fetched_at: String,
    pub workplace: String,
    pub note: String,
}

impl EdiInsurancePremiumRecord {
    pub fn new(period: impl Into<String>) -> Self {
        Self {
            employee_id: String::new(),
            employee_name: String::new(),
            period: normalize_period(&period.into()),
            national_pension: 0,
            health_insurance: 0,
            long_term_care: 0,
            employment_insurance: 0,
            industrial_accident: 0,
            industrial_accident_employer: None,
            industrial_accident_employee: None,
            management_no: String::new(),
            source: EdiPremiumSource::Import,
            fetched_at: String::new(),
            workplace: String::new(),
            note: String::new(),
        }
    }

    pub fn normalized(self) -> Self {
        Self {
            employee_id: clean(&self.employee_id),
            employee_name: clean(&self.employee_name),
            period: normalize_period(&self.period),
            national_pension: self.national_pension.max(0),
            health_insurance: self.health_insurance.max(0),
            long_term_care: self.long_term_care.max(0),
            employment_insurance: self.employment_insurance.max(0),
            industrial_accident: self.industrial_accident.max(0),
            industrial_accident_employer: self
                .industrial_accident_employer
                .map(|amount| amount.max(0)),
            industrial_accident_employee: self
                .industrial_accident_employee
                .map(|amount| amount.max(0)),
            management_no: clean(&self.management_no),
            source: self.source,
            fetched_at: clean(&self.fetched_at),
            workplace: clean(&self.workplace),
            note: clean(&self.note),
        }
    }

    pub fn with_employee_id(mut self, employee_id: impl Into<String>) -> Self {
        self.employee_id = clean(employee_id);
        self
    }

    pub fn with_employee_name(mut self, employee_name: impl Into<String>) -> Self {
        self.employee_name = clean(employee_name);
        self
    }

    pub fn with_period(mut self, period: impl Into<String>) -> Self {
        self.period = normalize_period(&period.into());
        self
    }

    pub fn with_national_pension(mut self, amount: i64) -> Self {
        self.national_pension = amount;
        self
    }

    pub fn with_health_insurance(mut self, amount: i64) -> Self {
        self.health_insurance = amount;
        self
    }

    pub fn with_long_term_care(mut self, amount: i64) -> Self {
        self.long_term_care = amount;
        self
    }

    pub fn with_employment_insurance(mut self, amount: i64) -> Self {
        self.employment_insurance = amount;
        self
    }

    pub fn with_industrial_accident(mut self, amount: i64) -> Self {
        self.industrial_accident = amount;
        self
    }

    pub fn with_industrial_accident_employer(mut self, amount: i64) -> Self {
        self.industrial_accident_employer = Some(amount);
        self
    }

    pub fn with_industrial_accident_employee(mut self, amount: i64) -> Self {
        self.industrial_accident_employee = Some(amount);
        self
    }

    pub fn with_management_no(mut self, management_no: impl Into<String>) -> Self {
        self.management_no = clean(management_no);
        self
    }

    pub fn with_source(mut self, source: EdiPremiumSource) -> Self {
        self.source = source;
        self
    }

    pub fn with_source_text(mut self, source: impl AsRef<str>) -> Self {
        self.source = EdiPremiumSource::normalize(source);
        self
    }

    pub fn with_fetched_at(mut self, fetched_at: impl Into<String>) -> Self {
        self.fetched_at = clean(fetched_at);
        self
    }

    pub fn with_workplace(mut self, workplace: impl Into<String>) -> Self {
        self.workplace = clean(workplace);
        self
    }

    pub fn with_note(mut self, note: impl Into<String>) -> Self {
        self.note = clean(note);
        self
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize)]
pub struct EdiInsuranceInvoice {
    pub name: String,
    pub employee_id: String,
    pub workplace: String,
    pub national_pension: i64,
    pub health_insurance: i64,
    pub long_term_care: i64,
    pub employment_insurance: i64,
    pub industrial_accident: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub industrial_accident_employer: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub industrial_accident_employee: Option<i64>,
    pub insurance_total: i64,
    pub insurance_exempt: bool,
    pub edi_premium_source: bool,
    pub edi_premium_badge: String,
    pub edi_premium_period: String,
    pub edi_premium_fetched_at: String,
    pub edi_premium_source_type: String,
}

impl EdiInsuranceInvoice {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: clean(name),
            ..Self::default()
        }
    }

    pub fn with_employee_id(mut self, employee_id: impl Into<String>) -> Self {
        self.employee_id = clean(employee_id);
        self
    }

    pub fn with_workplace(mut self, workplace: impl Into<String>) -> Self {
        self.workplace = clean(workplace);
        self
    }

    pub fn with_national_pension(mut self, amount: i64) -> Self {
        self.national_pension = amount;
        self
    }

    pub fn with_health_insurance(mut self, amount: i64) -> Self {
        self.health_insurance = amount;
        self
    }

    pub fn with_long_term_care(mut self, amount: i64) -> Self {
        self.long_term_care = amount;
        self
    }

    pub fn with_employment_insurance(mut self, amount: i64) -> Self {
        self.employment_insurance = amount;
        self
    }

    pub fn with_industrial_accident(mut self, amount: i64) -> Self {
        self.industrial_accident = amount;
        self
    }

    pub fn with_industrial_accident_employer(mut self, amount: i64) -> Self {
        self.industrial_accident_employer = Some(amount);
        self
    }

    pub fn with_industrial_accident_employee(mut self, amount: i64) -> Self {
        self.industrial_accident_employee = Some(amount);
        self
    }

    pub fn with_insurance_total(mut self, amount: i64) -> Self {
        self.insurance_total = amount;
        self
    }

    pub fn with_insurance_exempt(mut self, exempt: bool) -> Self {
        self.insurance_exempt = exempt;
        self
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct EdiInsuranceApplication {
    pub applied: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub record: Option<EdiInsurancePremiumRecord>,
    pub message: String,
    pub invoice: EdiInsuranceInvoice,
}

pub fn apply_edi_premiums_to_invoice<S>(
    mut invoice: EdiInsuranceInvoice,
    record: Option<&EdiInsurancePremiumRecord>,
    config: &EdiInsuranceConfig,
    payroll_period: S,
) -> EdiInsuranceApplication
where
    S: AsRef<str>,
{
    if !config.use_edi_premiums {
        return EdiInsuranceApplication {
            applied: false,
            record: None,
            message: EDI_OFF_MESSAGE.to_owned(),
            invoice,
        };
    }

    let Some(record) = record.cloned().map(EdiInsurancePremiumRecord::normalized) else {
        return EdiInsuranceApplication {
            applied: false,
            record: None,
            message: EDI_MISSING_MESSAGE.to_owned(),
            invoice,
        };
    };

    let age_exempt = config.respect_age_exempt && invoice.insurance_exempt;

    if !age_exempt {
        if record.national_pension > 0 {
            invoice.national_pension = record.national_pension;
        }
        if record.health_insurance > 0 {
            invoice.health_insurance = record.health_insurance;
        }
        if record.long_term_care > 0 {
            invoice.long_term_care = record.long_term_care;
        } else if record.health_insurance > 0 {
            invoice.long_term_care =
                round_won(record.health_insurance as f64 * LONG_TERM_CARE_RATIO);
        }
    }

    if record.employment_insurance > 0 {
        invoice.employment_insurance = record.employment_insurance;
    } else if record.employment_insurance == 0 && !age_exempt {
        invoice.employment_insurance = 0;
    }

    if record.industrial_accident > 0 {
        invoice.industrial_accident = record.industrial_accident;
    }
    if let Some(amount) = record.industrial_accident_employer {
        invoice.industrial_accident_employer = Some(amount);
    }
    if let Some(amount) = record.industrial_accident_employee {
        invoice.industrial_accident_employee = Some(amount);
    }

    invoice.edi_premium_source = true;
    invoice.edi_premium_badge = EDI_APPLIED_BADGE.to_owned();
    invoice.edi_premium_period = normalize_period(payroll_period.as_ref());
    invoice.edi_premium_fetched_at = record.fetched_at.clone();
    invoice.edi_premium_source_type = record.source.as_str().to_owned();
    invoice.insurance_total = invoice.national_pension.max(0)
        + invoice.health_insurance.max(0)
        + invoice.long_term_care.max(0)
        + invoice.employment_insurance.max(0);

    EdiInsuranceApplication {
        applied: true,
        record: Some(record),
        message: EDI_APPLIED_MESSAGE.to_owned(),
        invoice,
    }
}

fn normalize_period(period: &str) -> String {
    let text = period.trim().replace(['.', '/'], "-");
    if text.is_empty() {
        return String::new();
    }
    if let Some((year, month)) = parse_year_month(&text) {
        return format!("{year:04}-{month:02}");
    }
    let compact = text.replace('-', "");
    if compact.len() == 6 && compact.chars().all(|ch| ch.is_ascii_digit()) {
        let year = compact[0..4].parse::<i32>().unwrap_or_default();
        let month = compact[4..6].parse::<u8>().unwrap_or_default();
        if (1..=12).contains(&month) {
            return format!("{year:04}-{month:02}");
        }
    }
    text.chars().take(7).collect()
}

fn parse_year_month(text: &str) -> Option<(i32, u8)> {
    let mut parts = text.split('-');
    let year = parts.next()?.parse::<i32>().ok()?;
    let month = parts.next()?.parse::<u8>().ok()?;
    if parts.next().is_some() || !(1..=12).contains(&month) {
        return None;
    }
    Some((year, month))
}

fn round_won(amount: f64) -> i64 {
    round_ties_even(amount) as i64
}

fn round_ties_even(value: f64) -> f64 {
    let floor = value.floor();
    let diff = value - floor;
    if (diff - 0.5).abs() < 1e-9 {
        if (floor as i64) % 2 == 0 {
            floor
        } else {
            floor + 1.0
        }
    } else {
        value.round()
    }
}

fn clean(value: impl Into<String>) -> String {
    value.into().trim().to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn disabled_config_leaves_invoice_unchanged() {
        let invoice = EdiInsuranceInvoice::new("이영희").with_employment_insurance(18_000);
        let record = EdiInsurancePremiumRecord::new("2026-06").with_national_pension(999_999);
        let result = apply_edi_premiums_to_invoice(
            invoice,
            Some(&record),
            &EdiInsuranceConfig::new().with_use_edi_premiums(false),
            "2026-06",
        );

        assert!(!result.applied);
        assert_eq!(result.message, "EDI 보험료 사용 꺼짐");
        assert_eq!(result.invoice.employment_insurance, 18_000);
        assert!(!result.invoice.edi_premium_source);
        assert!(result.record.is_none());
    }

    #[test]
    fn missing_record_returns_no_edi_message() {
        let result = apply_edi_premiums_to_invoice(
            EdiInsuranceInvoice::new("무자료"),
            None,
            &EdiInsuranceConfig::new().with_use_edi_premiums(true),
            "2026-06",
        );

        assert!(!result.applied);
        assert_eq!(result.message, "EDI 보험료 없음");
        assert!(result.record.is_none());
    }

    #[test]
    fn applies_supplied_record_and_recalculates_total() {
        let record = EdiInsurancePremiumRecord::new("2026-06")
            .with_employee_id("E02")
            .with_employee_name("김철수")
            .with_national_pension(80_000)
            .with_health_insurance(40_000)
            .with_employment_insurance(20_000)
            .with_industrial_accident(3_000)
            .with_industrial_accident_employer(2_000)
            .with_industrial_accident_employee(0)
            .with_source(EdiPremiumSource::Manual)
            .with_fetched_at("2026-06-10T09:00:00");
        let result = apply_edi_premiums_to_invoice(
            EdiInsuranceInvoice::new("김철수"),
            Some(&record),
            &EdiInsuranceConfig::new().with_use_edi_premiums(true),
            "2026/6",
        );

        assert!(result.applied);
        assert_eq!(result.message, "EDI 보험료 적용");
        assert_eq!(result.invoice.national_pension, 80_000);
        assert_eq!(result.invoice.health_insurance, 40_000);
        assert_eq!(result.invoice.long_term_care, 5_180);
        assert_eq!(result.invoice.employment_insurance, 20_000);
        assert_eq!(result.invoice.industrial_accident, 3_000);
        assert_eq!(result.invoice.industrial_accident_employer, Some(2_000));
        assert_eq!(result.invoice.industrial_accident_employee, Some(0));
        assert_eq!(result.invoice.insurance_total, 145_180);
        assert!(result.invoice.edi_premium_source);
        assert_eq!(result.invoice.edi_premium_badge, "EDI 조회");
        assert_eq!(result.invoice.edi_premium_period, "2026-06");
        assert_eq!(result.invoice.edi_premium_source_type, "manual");
        assert!(result.record.is_some());
    }

    #[test]
    fn age_exempt_preserves_pension_health_and_ltc_but_applies_positive_employment() {
        let invoice = EdiInsuranceInvoice::new("고령자")
            .with_insurance_exempt(true)
            .with_national_pension(0)
            .with_health_insurance(0)
            .with_long_term_care(0)
            .with_employment_insurance(0);
        let record = EdiInsurancePremiumRecord::new("2026-06")
            .with_national_pension(80_000)
            .with_health_insurance(40_000)
            .with_long_term_care(5_000)
            .with_employment_insurance(20_000);
        let result = apply_edi_premiums_to_invoice(
            invoice,
            Some(&record),
            &EdiInsuranceConfig::new().with_use_edi_premiums(true),
            "2026-06",
        );

        assert!(result.applied);
        assert_eq!(result.invoice.national_pension, 0);
        assert_eq!(result.invoice.health_insurance, 0);
        assert_eq!(result.invoice.long_term_care, 0);
        assert_eq!(result.invoice.employment_insurance, 20_000);
        assert_eq!(result.invoice.insurance_total, 20_000);
    }

    #[test]
    fn zero_employment_record_clears_non_exempt_existing_employment() {
        let invoice = EdiInsuranceInvoice::new("일반")
            .with_health_insurance(40_000)
            .with_long_term_care(5_180)
            .with_employment_insurance(18_000);
        let record = EdiInsurancePremiumRecord::new("2026-06").with_employment_insurance(0);
        let result = apply_edi_premiums_to_invoice(
            invoice,
            Some(&record),
            &EdiInsuranceConfig::new().with_use_edi_premiums(true),
            "2026-06",
        );

        assert!(result.applied);
        assert_eq!(result.invoice.employment_insurance, 0);
        assert_eq!(result.invoice.insurance_total, 45_180);
    }

    #[test]
    fn can_ignore_age_exemption_when_requested() {
        let invoice = EdiInsuranceInvoice::new("고령자")
            .with_insurance_exempt(true)
            .with_national_pension(0);
        let record = EdiInsurancePremiumRecord::new("2026-06").with_national_pension(80_000);
        let result = apply_edi_premiums_to_invoice(
            invoice,
            Some(&record),
            &EdiInsuranceConfig::new()
                .with_use_edi_premiums(true)
                .with_respect_age_exempt(false),
            "2026-06",
        );

        assert!(result.applied);
        assert_eq!(result.invoice.national_pension, 80_000);
    }

    #[test]
    fn serializes_stable_contract_shape() {
        let record = EdiInsurancePremiumRecord::new("202606")
            .with_health_insurance(40_000)
            .with_source_text("bad-source");
        let result = apply_edi_premiums_to_invoice(
            EdiInsuranceInvoice::new("계약"),
            Some(&record),
            &EdiInsuranceConfig::new().with_use_edi_premiums(true),
            "202606",
        );
        let value = serde_json::to_value(result).unwrap();

        assert_eq!(value["applied"], true);
        assert_eq!(value["invoice"]["edi_premium_badge"], "EDI 조회");
        assert_eq!(value["invoice"]["edi_premium_period"], "2026-06");
        assert_eq!(value["record"]["period"], "2026-06");
        assert_eq!(value["record"]["source"], "import");
    }
}
