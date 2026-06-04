use serde::Serialize;

pub const STANDARD_MONTHLY_HOURS: f64 = 209.0;
pub const PAY_TYPE_HOURLY: &str = "hourly";
pub const PAY_TYPE_MONTHLY_SALARY: &str = "monthly_salary";
pub const FIXED_HOURS_SOURCE_CONTRACT: &str = "근로계약서 기준 고정";
pub const FIXED_HOURS_SOURCE_TEMPLATE: &str = "사업장 직군 템플릿";

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum FixedHoursPayType {
    #[default]
    Hourly,
    MonthlySalary,
}

impl FixedHoursPayType {
    pub fn normalize(value: impl AsRef<str>) -> Self {
        let text = value.as_ref().trim().replace(' ', "");
        if text.is_empty() {
            return Self::Hourly;
        }
        if text.contains("연봉") || matches!(text.as_str(), "monthly_salary" | "monthly" | "salary")
        {
            return Self::MonthlySalary;
        }
        match text.as_str() {
            PAY_TYPE_MONTHLY_SALARY => Self::MonthlySalary,
            PAY_TYPE_HOURLY => Self::Hourly,
            _ => Self::Hourly,
        }
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Hourly => PAY_TYPE_HOURLY,
            Self::MonthlySalary => PAY_TYPE_MONTHLY_SALARY,
        }
    }

    pub const fn label(self) -> &'static str {
        match self {
            Self::Hourly => "시급",
            Self::MonthlySalary => "연봉직",
        }
    }
}

impl Serialize for FixedHoursPayType {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct FixedHoursProfile {
    pub fixed_hours_mode: bool,
    pub monthly_fixed_hours: f64,
    pub daily_fixed_hours: f64,
    pub fixed_overtime_hours: f64,
    pub fixed_extension_hours: f64,
    pub pay_type: FixedHoursPayType,
    pub job_group: String,
    pub source: String,
    pub source_label: String,
    pub contract_id: String,
}

impl Default for FixedHoursProfile {
    fn default() -> Self {
        Self {
            fixed_hours_mode: false,
            monthly_fixed_hours: STANDARD_MONTHLY_HOURS,
            daily_fixed_hours: 0.0,
            fixed_overtime_hours: 0.0,
            fixed_extension_hours: 0.0,
            pay_type: FixedHoursPayType::Hourly,
            job_group: String::new(),
            source: String::new(),
            source_label: String::new(),
            contract_id: String::new(),
        }
    }
}

impl FixedHoursProfile {
    pub fn active() -> Self {
        Self {
            fixed_hours_mode: true,
            ..Self::default()
        }
    }

    pub fn normalized(self) -> Self {
        let mut monthly = self.monthly_fixed_hours;
        let daily = self.daily_fixed_hours;
        if monthly <= 0.0 && daily > 0.0 {
            monthly = daily * 26.0;
        }
        if monthly <= 0.0 {
            monthly = STANDARD_MONTHLY_HOURS;
        }
        Self {
            fixed_hours_mode: self.fixed_hours_mode,
            monthly_fixed_hours: round_decimal_places(monthly, 4),
            daily_fixed_hours: if daily > 0.0 {
                round_decimal_places(daily, 4)
            } else {
                0.0
            },
            fixed_overtime_hours: self.fixed_overtime_hours.max(0.0),
            fixed_extension_hours: self.fixed_extension_hours.max(0.0),
            pay_type: self.pay_type,
            job_group: clean(self.job_group),
            source: clean(self.source),
            source_label: clean(self.source_label),
            contract_id: clean(self.contract_id),
        }
    }

    pub fn with_monthly_fixed_hours(mut self, hours: f64) -> Self {
        self.monthly_fixed_hours = hours;
        self
    }

    pub fn with_daily_fixed_hours(mut self, hours: f64) -> Self {
        self.daily_fixed_hours = hours;
        self
    }

    pub fn with_fixed_overtime_hours(mut self, hours: f64) -> Self {
        self.fixed_overtime_hours = hours;
        self
    }

    pub fn with_fixed_extension_hours(mut self, hours: f64) -> Self {
        self.fixed_extension_hours = hours;
        self
    }

    pub fn with_pay_type(mut self, pay_type: FixedHoursPayType) -> Self {
        self.pay_type = pay_type;
        self
    }

    pub fn with_job_group(mut self, job_group: impl Into<String>) -> Self {
        self.job_group = job_group.into();
        self
    }

    pub fn with_source(mut self, source: impl Into<String>) -> Self {
        self.source = source.into();
        self
    }

    pub fn with_source_label(mut self, source_label: impl Into<String>) -> Self {
        self.source_label = source_label.into();
        self
    }

    pub fn with_contract_id(mut self, contract_id: impl Into<String>) -> Self {
        self.contract_id = contract_id.into();
        self
    }
}

#[derive(Clone, Debug, Default, PartialEq, Serialize)]
pub struct FixedHoursInvoice {
    pub name: String,
    pub workplace: String,
    pub work_days: f64,
    pub base_days: f64,
    pub ot_hours: f64,
    pub special_hours: f64,
    pub special_ext_hours: f64,
    #[serde(rename = "_invoice_work_days", skip_serializing_if = "Option::is_none")]
    pub invoice_work_days: Option<f64>,
    #[serde(rename = "_invoice_base_days", skip_serializing_if = "Option::is_none")]
    pub invoice_base_days: Option<f64>,
    #[serde(rename = "_invoice_ot_hours", skip_serializing_if = "Option::is_none")]
    pub invoice_ot_hours: Option<f64>,
    #[serde(
        rename = "_invoice_special_hours",
        skip_serializing_if = "Option::is_none"
    )]
    pub invoice_special_hours: Option<f64>,
    #[serde(
        rename = "_invoice_special_ext_hours",
        skip_serializing_if = "Option::is_none"
    )]
    pub invoice_special_ext_hours: Option<f64>,
    #[serde(
        rename = "_monthly_work_hours",
        skip_serializing_if = "Option::is_none"
    )]
    pub monthly_work_hours: Option<f64>,
    #[serde(rename = "_monthly_hours_source")]
    pub monthly_hours_source: String,
    #[serde(rename = "_fixed_hours_mode")]
    pub fixed_hours_mode: bool,
    #[serde(rename = "_fixed_hours_source")]
    pub fixed_hours_source: String,
    #[serde(rename = "_fixed_hours_pay_type")]
    pub fixed_hours_pay_type: String,
    #[serde(rename = "_fixed_hours_job_group")]
    pub fixed_hours_job_group: String,
    #[serde(rename = "_preserve_reference_hours")]
    pub preserve_reference_hours: bool,
}

impl FixedHoursInvoice {
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

    pub fn with_work_days(mut self, hours: f64) -> Self {
        self.work_days = hours;
        self
    }

    pub fn with_base_days(mut self, hours: f64) -> Self {
        self.base_days = hours;
        self
    }

    pub fn with_ot_hours(mut self, hours: f64) -> Self {
        self.ot_hours = hours;
        self
    }

    pub fn with_special_hours(mut self, hours: f64) -> Self {
        self.special_hours = hours;
        self
    }

    pub fn with_special_ext_hours(mut self, hours: f64) -> Self {
        self.special_ext_hours = hours;
        self
    }

    pub fn with_preserve_reference_hours(mut self, preserve: bool) -> Self {
        self.preserve_reference_hours = preserve;
        self
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct FixedHoursApplication {
    pub applied: bool,
    pub invoice: FixedHoursInvoice,
    pub profile: FixedHoursProfile,
    pub audit_flags: Vec<String>,
}

pub fn apply_fixed_hours_to_invoice<S>(
    invoice: FixedHoursInvoice,
    profile: &FixedHoursProfile,
    workplace: S,
) -> FixedHoursApplication
where
    S: Into<String>,
{
    let profile = profile.clone().normalized();
    if !profile.fixed_hours_mode {
        return FixedHoursApplication {
            applied: false,
            invoice,
            profile,
            audit_flags: Vec::new(),
        };
    }

    let mut invoice = invoice;
    preserve_invoice_values(&mut invoice);

    let mut monthly_hours = if profile.monthly_fixed_hours > 0.0 {
        profile.monthly_fixed_hours
    } else {
        STANDARD_MONTHLY_HOURS
    };
    let invoice_hours = invoice
        .invoice_work_days
        .or(invoice.invoice_base_days)
        .unwrap_or(0.0);
    if invoice.preserve_reference_hours && invoice_hours > 0.0 {
        monthly_hours = invoice_hours;
    }

    invoice.monthly_work_hours = Some(monthly_hours);
    invoice.monthly_hours_source = source_label(&profile).to_owned();
    invoice.fixed_hours_mode = true;
    invoice.fixed_hours_source = profile.source.clone();
    invoice.fixed_hours_pay_type = profile.pay_type.as_str().to_owned();
    invoice.fixed_hours_job_group = profile.job_group.clone();
    invoice.base_days = monthly_hours;
    invoice.work_days = monthly_hours;

    if profile.fixed_extension_hours > 0.0 {
        invoice.ot_hours = profile.fixed_extension_hours;
    }
    if profile.fixed_overtime_hours > 0.0 {
        invoice.special_hours = profile.fixed_overtime_hours;
    }

    let workplace = clean(workplace);
    if !workplace.is_empty() {
        invoice.workplace = workplace;
    }

    let audit_flags = fixed_hours_audit_flags(&invoice, &profile);
    FixedHoursApplication {
        applied: true,
        invoice,
        profile,
        audit_flags,
    }
}

pub fn fixed_hours_audit_flags(
    invoice: &FixedHoursInvoice,
    profile: &FixedHoursProfile,
) -> Vec<String> {
    let profile = profile.clone().normalized();
    if !profile.fixed_hours_mode || !invoice.fixed_hours_mode {
        return Vec::new();
    }

    let mut flags = Vec::new();
    let mut first = source_label(&profile).to_owned();
    let job_group = if profile.job_group.is_empty() {
        clean(&invoice.fixed_hours_job_group)
    } else {
        profile.job_group.clone()
    };
    if !job_group.is_empty() {
        first = format!("{first} ({job_group})");
    }
    flags.push(first);
    flags.push(format!("급여형태: {}", profile.pay_type.label()));

    let invoice_ot = invoice.invoice_ot_hours.unwrap_or(invoice.ot_hours);
    let invoice_special = invoice
        .invoice_special_hours
        .unwrap_or(invoice.special_hours);
    let fixed_ot = profile.fixed_extension_hours;
    let fixed_special = profile.fixed_overtime_hours;

    if fixed_ot > 0.0 && invoice_ot > 0.0 && (invoice_ot - fixed_ot).abs() > 0.01 {
        flags.push(format!(
            "청구서 연장({}h) ≠ 계약 고정({}h)",
            format_number(invoice_ot),
            format_number(fixed_ot)
        ));
    }
    if fixed_special > 0.0
        && invoice_special > 0.0
        && (invoice_special - fixed_special).abs() > 0.01
    {
        flags.push(format!(
            "청구서 특근({}h) ≠ 계약 고정({}h)",
            format_number(invoice_special),
            format_number(fixed_special)
        ));
    }

    let invoice_work = invoice.invoice_work_days.unwrap_or(0.0);
    let monthly = profile.monthly_fixed_hours;
    if invoice_work > 0.0 && monthly > 0.0 && (invoice_work - monthly).abs() > monthly * 0.05 {
        flags.push(format!(
            "청구서 근무시간({}h) ≠ 계약 월시간({}h)",
            format_number(invoice_work),
            format_number(monthly)
        ));
    }

    flags
}

fn preserve_invoice_values(invoice: &mut FixedHoursInvoice) {
    if invoice.invoice_work_days.is_none() {
        invoice.invoice_work_days = Some(invoice.work_days);
    }
    if invoice.invoice_base_days.is_none() {
        invoice.invoice_base_days = Some(invoice.base_days);
    }
    if invoice.invoice_ot_hours.is_none() {
        invoice.invoice_ot_hours = Some(invoice.ot_hours);
    }
    if invoice.invoice_special_hours.is_none() {
        invoice.invoice_special_hours = Some(invoice.special_hours);
    }
    if invoice.invoice_special_ext_hours.is_none() {
        invoice.invoice_special_ext_hours = Some(invoice.special_ext_hours);
    }
}

fn source_label(profile: &FixedHoursProfile) -> &str {
    if profile.source_label.is_empty() {
        FIXED_HOURS_SOURCE_CONTRACT
    } else {
        &profile.source_label
    }
}

fn round_decimal_places(value: f64, places: i32) -> f64 {
    let scale = 10_f64.powi(places);
    round_ties_even(value * scale) / scale
}

fn round_ties_even(value: f64) -> f64 {
    let floor = value.floor();
    let fraction = value - floor;
    if fraction < 0.5 - f64::EPSILON {
        floor
    } else if fraction > 0.5 + f64::EPSILON {
        floor + 1.0
    } else if (floor as i64).rem_euclid(2) == 0 {
        floor
    } else {
        floor + 1.0
    }
}

fn format_number(value: f64) -> String {
    let rounded = round_decimal_places(value, 4);
    if (rounded - rounded.round()).abs() < 1e-9 {
        return format!("{}", rounded.round() as i64);
    }
    let mut text = format!("{rounded:.4}");
    while text.contains('.') && text.ends_with('0') {
        text.pop();
    }
    if text.ends_with('.') {
        text.pop();
    }
    text
}

fn clean(value: impl Into<String>) -> String {
    value.into().trim().to_owned()
}

#[cfg(test)]
mod tests {
    use crate::fixed_hours::{
        apply_fixed_hours_to_invoice, FixedHoursInvoice, FixedHoursPayType, FixedHoursProfile,
        FIXED_HOURS_SOURCE_CONTRACT,
    };
    use crate::service::{PayrollApiService, ServiceConfig};

    fn contract_profile() -> FixedHoursProfile {
        FixedHoursProfile::active()
            .with_monthly_fixed_hours(209.0)
            .with_fixed_overtime_hours(10.0)
            .with_fixed_extension_hours(20.0)
            .with_pay_type(FixedHoursPayType::MonthlySalary)
            .with_job_group("경비")
            .with_source("contract")
            .with_source_label(FIXED_HOURS_SOURCE_CONTRACT)
            .with_contract_id("c1")
    }

    fn invoice() -> FixedHoursInvoice {
        FixedHoursInvoice::new("최연봉")
            .with_workplace("청구지")
            .with_work_days(150.0)
            .with_base_days(150.0)
            .with_ot_hours(5.0)
            .with_special_hours(3.0)
            .with_special_ext_hours(2.0)
    }

    #[test]
    fn normalizes_profile_like_python_contract_fields() {
        let profile = FixedHoursProfile::active()
            .with_monthly_fixed_hours(0.0)
            .with_daily_fixed_hours(8.0)
            .with_fixed_overtime_hours(-3.0)
            .with_fixed_extension_hours(7.25)
            .with_pay_type(FixedHoursPayType::normalize("연봉직"))
            .with_job_group(" 관리 ")
            .normalized();

        assert_eq!(profile.monthly_fixed_hours, 208.0);
        assert_eq!(profile.daily_fixed_hours, 8.0);
        assert_eq!(profile.fixed_overtime_hours, 0.0);
        assert_eq!(profile.fixed_extension_hours, 7.25);
        assert_eq!(profile.pay_type, FixedHoursPayType::MonthlySalary);
        assert_eq!(profile.job_group, "관리");
    }

    #[test]
    fn applies_fixed_profile_and_preserves_invoice_values() {
        let result = apply_fixed_hours_to_invoice(invoice(), &contract_profile(), "강남경비");
        let value = serde_json::to_value(&result.invoice).unwrap();

        assert!(result.applied);
        assert_eq!(result.invoice.workplace, "강남경비");
        assert_eq!(result.invoice.monthly_work_hours, Some(209.0));
        assert_eq!(
            result.invoice.monthly_hours_source,
            FIXED_HOURS_SOURCE_CONTRACT
        );
        assert!(result.invoice.fixed_hours_mode);
        assert_eq!(result.invoice.fixed_hours_source, "contract");
        assert_eq!(result.invoice.fixed_hours_pay_type, "monthly_salary");
        assert_eq!(result.invoice.fixed_hours_job_group, "경비");
        assert_eq!(result.invoice.base_days, 209.0);
        assert_eq!(result.invoice.work_days, 209.0);
        assert_eq!(result.invoice.ot_hours, 20.0);
        assert_eq!(result.invoice.special_hours, 10.0);
        assert_eq!(result.invoice.invoice_work_days, Some(150.0));
        assert_eq!(result.invoice.invoice_base_days, Some(150.0));
        assert_eq!(result.invoice.invoice_ot_hours, Some(5.0));
        assert_eq!(result.invoice.invoice_special_hours, Some(3.0));
        assert_eq!(result.invoice.invoice_special_ext_hours, Some(2.0));
        assert_eq!(value["_monthly_work_hours"], 209.0);
        assert_eq!(value["_fixed_hours_mode"], true);
        assert!(result
            .audit_flags
            .iter()
            .any(|flag| flag == "청구서 연장(5h) ≠ 계약 고정(20h)"));
        assert!(result
            .audit_flags
            .iter()
            .any(|flag| flag == "청구서 특근(3h) ≠ 계약 고정(10h)"));
        assert!(result
            .audit_flags
            .iter()
            .any(|flag| flag == "청구서 근무시간(150h) ≠ 계약 월시간(209h)"));
    }

    #[test]
    fn preserve_reference_hours_uses_invoice_hours_for_application() {
        let result = apply_fixed_hours_to_invoice(
            invoice().with_preserve_reference_hours(true),
            &contract_profile(),
            "",
        );

        assert_eq!(result.invoice.workplace, "청구지");
        assert_eq!(result.invoice.monthly_work_hours, Some(150.0));
        assert_eq!(result.invoice.base_days, 150.0);
        assert_eq!(result.invoice.work_days, 150.0);
        assert!(result
            .audit_flags
            .iter()
            .any(|flag| flag == "청구서 근무시간(150h) ≠ 계약 월시간(209h)"));
    }

    #[test]
    fn inactive_profile_leaves_invoice_unchanged() {
        let original = invoice();
        let result = apply_fixed_hours_to_invoice(
            original.clone(),
            &FixedHoursProfile::default(),
            "강남경비",
        );

        assert!(!result.applied);
        assert_eq!(result.invoice, original);
        assert!(result.audit_flags.is_empty());
    }

    #[test]
    fn service_delegates_fixed_hours_application() {
        let service = PayrollApiService::new(ServiceConfig::default());
        let result =
            service.apply_fixed_hours_to_invoice(invoice(), &contract_profile(), "강남경비");

        assert!(result.applied);
        assert_eq!(result.invoice.monthly_work_hours, Some(209.0));
        assert_eq!(result.invoice.ot_hours, 20.0);
        assert_eq!(result.invoice.special_hours, 10.0);
    }
}
