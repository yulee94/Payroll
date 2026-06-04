use serde::Serialize;

pub const STANDARD_MONTHLY_HOURS: f64 = 209.0;
pub const MODE_FIXED: &str = "fixed";
pub const MODE_INVOICE_WORK: &str = "invoice_work_days";
pub const MODE_INVOICE_BASE: &str = "invoice_base_days";
pub const MODE_WORK_OR_FIXED: &str = "work_or_fixed";
pub const MODE_BASE_OR_FIXED: &str = "base_or_fixed";

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum WorkplaceHoursMode {
    #[default]
    Fixed,
    InvoiceWorkDays,
    InvoiceBaseDays,
    WorkOrFixed,
    BaseOrFixed,
}

impl WorkplaceHoursMode {
    pub fn normalize(value: impl AsRef<str>) -> Self {
        match value.as_ref().trim() {
            MODE_INVOICE_WORK => Self::InvoiceWorkDays,
            MODE_INVOICE_BASE => Self::InvoiceBaseDays,
            MODE_WORK_OR_FIXED => Self::WorkOrFixed,
            MODE_BASE_OR_FIXED => Self::BaseOrFixed,
            MODE_FIXED => Self::Fixed,
            _ => Self::Fixed,
        }
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Fixed => MODE_FIXED,
            Self::InvoiceWorkDays => MODE_INVOICE_WORK,
            Self::InvoiceBaseDays => MODE_INVOICE_BASE,
            Self::WorkOrFixed => MODE_WORK_OR_FIXED,
            Self::BaseOrFixed => MODE_BASE_OR_FIXED,
        }
    }

    pub const fn label(self) -> &'static str {
        match self {
            Self::Fixed => "고정 시간",
            Self::InvoiceWorkDays => "청구서 근무시간(J열)",
            Self::InvoiceBaseDays => "청구서 기준시간(I열)",
            Self::WorkOrFixed => "근무시간 우선 (없으면 고정)",
            Self::BaseOrFixed => "기준시간 우선 (없으면 고정)",
        }
    }
}

impl Serialize for WorkplaceHoursMode {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct WorkplaceHoursPolicy {
    pub mode: WorkplaceHoursMode,
    pub hours: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub daily_hours: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub break_minutes: Option<f64>,
}

impl Default for WorkplaceHoursPolicy {
    fn default() -> Self {
        Self {
            mode: WorkplaceHoursMode::Fixed,
            hours: STANDARD_MONTHLY_HOURS,
            daily_hours: None,
            break_minutes: None,
        }
    }
}

impl WorkplaceHoursPolicy {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn normalized(self) -> Self {
        let hours = if self.hours.is_finite() && self.hours > 0.0 {
            self.hours
        } else {
            STANDARD_MONTHLY_HOURS
        };
        Self {
            mode: self.mode,
            hours: round_decimal_places(hours, 4),
            daily_hours: self
                .daily_hours
                .filter(|hours| hours.is_finite() && *hours > 0.0)
                .map(|hours| round_decimal_places(hours, 4)),
            break_minutes: self
                .break_minutes
                .filter(|minutes| minutes.is_finite() && *minutes >= 0.0)
                .map(|minutes| round_decimal_places(minutes, 2)),
        }
    }

    pub fn with_mode(mut self, mode: WorkplaceHoursMode) -> Self {
        self.mode = mode;
        self
    }

    pub fn with_mode_text(mut self, mode: impl AsRef<str>) -> Self {
        self.mode = WorkplaceHoursMode::normalize(mode);
        self
    }

    pub fn with_hours(mut self, hours: f64) -> Self {
        self.hours = hours;
        self
    }

    pub fn with_daily_hours(mut self, daily_hours: f64) -> Self {
        self.daily_hours = Some(daily_hours);
        self
    }

    pub fn with_break_minutes(mut self, break_minutes: f64) -> Self {
        self.break_minutes = Some(break_minutes);
        self
    }
}

#[derive(Clone, Debug, Default, PartialEq, Serialize)]
pub struct WorkplaceHoursInvoice {
    pub workplace: String,
    pub work_days: f64,
    pub base_days: f64,
    #[serde(
        rename = "_monthly_work_hours",
        skip_serializing_if = "Option::is_none"
    )]
    pub monthly_work_hours: Option<f64>,
    #[serde(rename = "_monthly_hours_source")]
    pub monthly_hours_source: String,
}

impl WorkplaceHoursInvoice {
    pub fn new() -> Self {
        Self::default()
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
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct WorkplaceMonthlyHoursResolution {
    pub hours: f64,
    pub source: String,
    pub workplace: String,
    pub policy: WorkplaceHoursPolicy,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct WorkplaceMonthlyHoursApplication {
    pub hours: f64,
    pub source: String,
    pub invoice: WorkplaceHoursInvoice,
    pub policy: WorkplaceHoursPolicy,
}

pub fn resolve_monthly_work_hours<S>(
    invoice: &WorkplaceHoursInvoice,
    workplace: S,
    policy: &WorkplaceHoursPolicy,
) -> WorkplaceMonthlyHoursResolution
where
    S: AsRef<str>,
{
    let policy = policy.clone().normalized();
    let fixed_hours = policy.hours;
    let workplace = clean_ref(workplace.as_ref());
    let workplace_label = if workplace.is_empty() {
        "(기본)".to_owned()
    } else {
        workplace.clone()
    };
    let work_hours = positive_invoice_hours(invoice.work_days);
    let base_hours = positive_invoice_hours(invoice.base_days);

    let (hours, detail) = match policy.mode {
        WorkplaceHoursMode::Fixed => (fixed_hours, format!("고정 {fixed_hours}시간")),
        WorkplaceHoursMode::InvoiceWorkDays => {
            if work_hours > 0.0 {
                (work_hours, "청구서 근무시간".to_owned())
            } else {
                (
                    fixed_hours,
                    format!("고정 {fixed_hours}시간(근무시간 없음)"),
                )
            }
        }
        WorkplaceHoursMode::InvoiceBaseDays => {
            if base_hours > 0.0 {
                (base_hours, "청구서 기준시간".to_owned())
            } else {
                (
                    fixed_hours,
                    format!("고정 {fixed_hours}시간(기준시간 없음)"),
                )
            }
        }
        WorkplaceHoursMode::WorkOrFixed => {
            if work_hours > 0.0 {
                (work_hours, format!("청구서 근무시간 {work_hours}"))
            } else {
                (fixed_hours, format!("고정 {fixed_hours}시간"))
            }
        }
        WorkplaceHoursMode::BaseOrFixed => {
            if base_hours > 0.0 {
                (base_hours, format!("청구서 기준시간 {base_hours}"))
            } else {
                (fixed_hours, format!("고정 {fixed_hours}시간"))
            }
        }
    };

    WorkplaceMonthlyHoursResolution {
        hours,
        source: format!("{workplace_label}: {detail}"),
        workplace,
        policy,
    }
}

pub fn apply_monthly_hours_to_invoice<S>(
    invoice: WorkplaceHoursInvoice,
    workplace: S,
    policy: &WorkplaceHoursPolicy,
) -> WorkplaceMonthlyHoursApplication
where
    S: AsRef<str>,
{
    let resolution = resolve_monthly_work_hours(&invoice, workplace, policy);
    let mut invoice = invoice;
    invoice.monthly_work_hours = Some(resolution.hours);
    invoice.monthly_hours_source = resolution.source.clone();

    WorkplaceMonthlyHoursApplication {
        hours: resolution.hours,
        source: resolution.source,
        invoice,
        policy: resolution.policy,
    }
}

fn positive_invoice_hours(hours: f64) -> f64 {
    if hours.is_finite() {
        hours.max(0.0)
    } else {
        0.0
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

fn clean(value: impl Into<String>) -> String {
    clean_ref(&value.into())
}

fn clean_ref(value: &str) -> String {
    value.trim().to_owned()
}

#[cfg(test)]
mod tests {
    use crate::service::{PayrollApiService, ServiceConfig};
    use crate::workplace_hours::{
        WorkplaceHoursInvoice, WorkplaceHoursMode, WorkplaceHoursPolicy,
        apply_monthly_hours_to_invoice, resolve_monthly_work_hours,
    };
    use serde_json::json;

    #[test]
    fn normalizes_invalid_policy_to_fixed_standard_hours() {
        let policy = WorkplaceHoursPolicy::new()
            .with_mode_text("not-a-mode")
            .with_hours(-1.0)
            .with_daily_hours(-8.0)
            .with_break_minutes(-15.0)
            .normalized();

        assert_eq!(policy.mode, WorkplaceHoursMode::Fixed);
        assert_eq!(policy.hours, 209.0);
        assert_eq!(policy.daily_hours, None);
        assert_eq!(policy.break_minutes, None);
    }

    #[test]
    fn resolves_python_compatible_modes_from_supplied_policy() {
        let cases = vec![
            (
                WorkplaceHoursPolicy::new()
                    .with_mode(WorkplaceHoursMode::WorkOrFixed)
                    .with_hours(209.0),
                WorkplaceHoursInvoice::new()
                    .with_work_days(195.0)
                    .with_base_days(209.0),
                "청구장",
                195.0,
                "청구장: 청구서 근무시간 195",
            ),
            (
                WorkplaceHoursPolicy::new()
                    .with_mode(WorkplaceHoursMode::WorkOrFixed)
                    .with_hours(209.0),
                WorkplaceHoursInvoice::new()
                    .with_work_days(0.0)
                    .with_base_days(209.0),
                "청구장",
                209.0,
                "청구장: 고정 209시간",
            ),
            (
                WorkplaceHoursPolicy::new()
                    .with_mode(WorkplaceHoursMode::InvoiceBaseDays)
                    .with_hours(200.0),
                WorkplaceHoursInvoice::new()
                    .with_work_days(180.0)
                    .with_base_days(-5.0),
                "기준장",
                200.0,
                "기준장: 고정 200시간(기준시간 없음)",
            ),
            (
                WorkplaceHoursPolicy::new()
                    .with_mode(WorkplaceHoursMode::BaseOrFixed)
                    .with_hours(209.0),
                WorkplaceHoursInvoice::new()
                    .with_work_days(190.0)
                    .with_base_days(207.5),
                "",
                207.5,
                "(기본): 청구서 기준시간 207.5",
            ),
        ];

        for (policy, invoice, workplace, expected_hours, expected_source) in cases {
            let resolved = resolve_monthly_work_hours(&invoice, workplace, &policy);

            assert_eq!(resolved.hours, expected_hours);
            assert_eq!(resolved.source, expected_source);
        }
    }

    #[test]
    fn applies_monthly_metadata_to_invoice() {
        let policy = WorkplaceHoursPolicy::new()
            .with_mode(WorkplaceHoursMode::InvoiceWorkDays)
            .with_hours(209.0);
        let invoice = WorkplaceHoursInvoice::new()
            .with_work_days(192.0)
            .with_base_days(209.0);

        let applied = apply_monthly_hours_to_invoice(invoice, "청구장", &policy);

        assert_eq!(applied.hours, 192.0);
        assert_eq!(applied.source, "청구장: 청구서 근무시간");
        assert_eq!(applied.invoice.monthly_work_hours, Some(192.0));
        assert_eq!(
            applied.invoice.monthly_hours_source,
            "청구장: 청구서 근무시간"
        );
    }

    #[test]
    fn serializes_compatibility_keys() {
        let policy = WorkplaceHoursPolicy::new()
            .with_mode(WorkplaceHoursMode::Fixed)
            .with_hours(200.0)
            .with_daily_hours(8.0)
            .with_break_minutes(60.0);
        let invoice = WorkplaceHoursInvoice::new()
            .with_work_days(0.0)
            .with_base_days(0.0);

        let applied = apply_monthly_hours_to_invoice(invoice, "테스트장", &policy);
        let value = serde_json::to_value(applied).unwrap();

        assert_eq!(value["hours"], json!(200.0));
        assert_eq!(value["policy"]["mode"], "fixed");
        assert_eq!(value["policy"]["daily_hours"], json!(8.0));
        assert_eq!(value["policy"]["break_minutes"], json!(60.0));
        assert_eq!(value["invoice"]["_monthly_work_hours"], json!(200.0));
        assert_eq!(
            value["invoice"]["_monthly_hours_source"],
            "테스트장: 고정 200시간"
        );
    }

    #[test]
    fn service_delegates_workplace_hours_application() {
        let service = PayrollApiService::new(ServiceConfig::default());
        let policy = WorkplaceHoursPolicy::new()
            .with_mode(WorkplaceHoursMode::InvoiceWorkDays)
            .with_hours(209.0);
        let invoice = WorkplaceHoursInvoice::new().with_work_days(195.0);

        let applied = service.apply_monthly_hours_to_invoice(invoice, "청구장", &policy);

        assert_eq!(applied.hours, 195.0);
        assert_eq!(applied.invoice.monthly_work_hours, Some(195.0));
    }
}
