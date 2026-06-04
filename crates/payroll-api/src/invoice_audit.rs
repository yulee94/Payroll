use crate::fixed_hours::{
    apply_fixed_hours_to_invoice, FixedHoursInvoice, FixedHoursProfile, FIXED_HOURS_SOURCE_CONTRACT,
};
use crate::workplace_hours::{
    apply_monthly_hours_to_invoice, WorkplaceHoursInvoice, WorkplaceHoursMode, WorkplaceHoursPolicy,
};
use serde::Serialize;

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum InvoiceAuditStatus {
    #[default]
    Pass,
    Warn,
}

impl InvoiceAuditStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pass => "pass",
            Self::Warn => "warn",
        }
    }

    pub const fn label(self) -> &'static str {
        match self {
            Self::Pass => "정상",
            Self::Warn => "확인",
        }
    }
}

impl Serialize for InvoiceAuditStatus {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, Default, PartialEq, Serialize)]
pub struct InvoiceAuditInvoice {
    pub name: String,
    pub workplace: String,
    pub base_days: f64,
    pub work_days: f64,
    pub leave_days: f64,
    pub ot_hours: f64,
    pub special_hours: f64,
    pub special_ext_hours: f64,
    pub base_hourly: f64,
    pub base_salary: i64,
    #[serde(rename = "_preserve_reference_hours")]
    pub preserve_reference_hours: bool,
}

impl InvoiceAuditInvoice {
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

    pub fn with_base_days(mut self, hours: f64) -> Self {
        self.base_days = hours;
        self
    }

    pub fn with_work_days(mut self, hours: f64) -> Self {
        self.work_days = hours;
        self
    }

    pub fn with_leave_days(mut self, days: f64) -> Self {
        self.leave_days = days;
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

    pub fn with_base_hourly(mut self, amount: f64) -> Self {
        self.base_hourly = amount;
        self
    }

    pub fn with_base_salary(mut self, amount: i64) -> Self {
        self.base_salary = amount;
        self
    }

    pub fn with_preserve_reference_hours(mut self, preserve: bool) -> Self {
        self.preserve_reference_hours = preserve;
        self
    }
}

#[derive(Clone, Debug, Default, PartialEq, Serialize)]
pub struct InvoiceAuditRecord {
    pub name: String,
    pub workplace: String,
    pub base_hourly: f64,
    #[serde(
        rename = "_monthly_work_hours",
        skip_serializing_if = "Option::is_none"
    )]
    pub monthly_work_hours: Option<f64>,
}

impl InvoiceAuditRecord {
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

    pub fn with_base_hourly(mut self, amount: f64) -> Self {
        self.base_hourly = amount;
        self
    }

    pub fn with_monthly_work_hours(mut self, hours: f64) -> Self {
        self.monthly_work_hours = Some(hours);
        self
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct InvoiceAuditRow {
    pub name: String,
    pub workplace: String,
    pub status: InvoiceAuditStatus,
    pub status_label: String,
    pub flags: Vec<String>,
    pub base_days: f64,
    pub work_days: f64,
    pub break_hours: Option<f64>,
    pub applied_monthly_hours: f64,
    pub hours_source: String,
    pub policy_mode: WorkplaceHoursMode,
    pub policy_fixed_hours: f64,
    pub base_hourly: f64,
    pub invoice_base_salary: i64,
    pub calc_base_salary: i64,
    pub formula: String,
    pub fixed_hours_mode: bool,
    pub fixed_hours_source: String,
}

pub fn estimate_break_hours(
    invoice: &InvoiceAuditInvoice,
    policy: &WorkplaceHoursPolicy,
) -> Option<f64> {
    let policy = policy.clone().normalized();
    let break_minutes = policy.break_minutes.unwrap_or(0.0);
    let daily_hours = match policy.daily_hours {
        Some(hours) if hours > 0.0 => hours,
        _ => 8.0,
    };
    let work = safe_number(invoice.work_days);
    let base = safe_number(invoice.base_days);
    let leave = safe_number(invoice.leave_days);

    if break_minutes > 0.0 && work > 0.0 {
        let work_days_count = if work <= 31.0 {
            work
        } else {
            work / daily_hours
        };
        return Some(round_decimal_places(
            (break_minutes / 60.0) * work_days_count,
            4,
        ));
    }

    if base > work && work > 0.0 && base >= 24.0 && work >= 1.0 {
        let gap = base - work - leave;
        if gap > 0.0 {
            return Some(round_decimal_places(gap, 4));
        }
    }
    None
}

pub fn audit_invoice_row<S>(
    invoice: InvoiceAuditInvoice,
    workplace: S,
    policy: &WorkplaceHoursPolicy,
    record: Option<&InvoiceAuditRecord>,
    fixed_profile: Option<&FixedHoursProfile>,
) -> InvoiceAuditRow
where
    S: AsRef<str>,
{
    let workplace = resolved_workplace(&invoice, workplace.as_ref(), record);
    let policy = policy.clone().normalized();
    let mut applied_hours = 0.0;
    let mut hours_source = String::new();
    let mut fixed_hours_mode = false;
    let mut fixed_hours_source = String::new();
    let mut fixed_flags = Vec::new();

    if let Some(profile) = fixed_profile {
        let normalized_profile = profile.clone().normalized();
        if normalized_profile.fixed_hours_mode {
            let fixed_invoice = fixed_invoice_from_audit(&invoice);
            let application =
                apply_fixed_hours_to_invoice(fixed_invoice, &normalized_profile, &workplace);
            applied_hours = application.invoice.monthly_work_hours.unwrap_or(0.0);
            hours_source = if application.invoice.monthly_hours_source.is_empty() {
                FIXED_HOURS_SOURCE_CONTRACT.to_owned()
            } else {
                application.invoice.monthly_hours_source.clone()
            };
            fixed_hours_mode = true;
            fixed_hours_source = normalized_profile.source_label.clone();
            fixed_flags = application.audit_flags;
        }
    }

    if !fixed_hours_mode {
        let workplace_invoice = WorkplaceHoursInvoice::new()
            .with_workplace(invoice.workplace.clone())
            .with_work_days(invoice.work_days)
            .with_base_days(invoice.base_days);
        let application = apply_monthly_hours_to_invoice(workplace_invoice, &workplace, &policy);
        applied_hours = application.hours;
        hours_source = application.source;
    }

    let fixed_hours = policy.hours;
    let base_days = safe_number(invoice.base_days);
    let work_days = safe_number(invoice.work_days);
    let break_hours = estimate_break_hours(&invoice, &policy);
    let base_hourly = selected_base_hourly(&invoice, record);
    let invoice_base_salary = invoice.base_salary;
    let calc_base_salary = if base_hourly > 0.0 {
        round_won(base_hourly * applied_hours)
    } else {
        0
    };

    let mut flags = Vec::new();
    let mut status = InvoiceAuditStatus::Pass;

    if matches!(
        policy.mode,
        WorkplaceHoursMode::InvoiceWorkDays | WorkplaceHoursMode::WorkOrFixed
    ) && work_days <= 0.0
    {
        flags.push("청구서 근무시간(J) 없음 — 고정값 대체".to_owned());
        status = InvoiceAuditStatus::Warn;
    }
    if matches!(
        policy.mode,
        WorkplaceHoursMode::InvoiceBaseDays | WorkplaceHoursMode::BaseOrFixed
    ) && base_days <= 0.0
    {
        flags.push("청구서 기준시간(I) 없음 — 고정값 대체".to_owned());
        status = InvoiceAuditStatus::Warn;
    }
    if policy.mode == WorkplaceHoursMode::Fixed
        && work_days > fixed_hours * 1.05
        && work_days >= 24.0
    {
        flags.push(format!(
            "청구서 근무시간({}h)이 사업장 고정({}h) 초과",
            format_number(work_days),
            format_number(fixed_hours)
        ));
        status = InvoiceAuditStatus::Warn;
    }
    if applied_hours > fixed_hours * 1.1 && policy.mode == WorkplaceHoursMode::Fixed {
        flags.push(format!(
            "적용 시간({}h)이 고정 기준({}h)보다 큼",
            format_number(applied_hours),
            format_number(fixed_hours)
        ));
        status = InvoiceAuditStatus::Warn;
    }
    if base_hourly > 0.0
        && invoice_base_salary > 0
        && (calc_base_salary - invoice_base_salary).abs() > 1
    {
        flags.push(format!(
            "기본급 불일치: 산출 {}원 vs 청구서 {}원",
            format_i64(calc_base_salary),
            format_i64(invoice_base_salary)
        ));
        status = InvoiceAuditStatus::Warn;
    } else if base_hourly <= 0.0 && invoice_base_salary > 0 {
        flags.push("명부 기본시급 없음 — 기본급 검증 생략".to_owned());
    }
    if break_hours.is_none() && base_days > work_days && work_days > 0.0 {
        flags.push("휴계 미설정 — I·J열 차이는 휴가·무급 포함 가능".to_owned());
    }

    if !fixed_flags.is_empty() {
        if fixed_flags.iter().any(|flag| flag.contains('≠')) {
            status = InvoiceAuditStatus::Warn;
        }
        fixed_flags.extend(flags);
        flags = fixed_flags;
    }

    let record_hours = record
        .and_then(|item| item.monthly_work_hours)
        .filter(|hours| hours.is_finite())
        .unwrap_or(0.0);
    if record.is_some() && record_hours > 0.0 && (record_hours - applied_hours).abs() > 0.01 {
        flags.push(format!(
            "대장 적용시간({}h)과 재검열({}h) 상이",
            format_number(record_hours),
            format_number(applied_hours)
        ));
        status = InvoiceAuditStatus::Warn;
    }

    let mut formula = format!(
        "기본시급 {}원 × {}시간",
        format_i64(round_ties_even(base_hourly) as i64),
        format_number(applied_hours)
    );
    if calc_base_salary > 0 {
        formula.push_str(&format!(" = {}원", format_i64(calc_base_salary)));
    }

    InvoiceAuditRow {
        name: invoice.name,
        workplace,
        status,
        status_label: status.label().to_owned(),
        flags,
        base_days,
        work_days,
        break_hours,
        applied_monthly_hours: applied_hours,
        hours_source,
        policy_mode: policy.mode,
        policy_fixed_hours: fixed_hours,
        base_hourly,
        invoice_base_salary,
        calc_base_salary,
        formula,
        fixed_hours_mode,
        fixed_hours_source,
    }
}

fn fixed_invoice_from_audit(invoice: &InvoiceAuditInvoice) -> FixedHoursInvoice {
    FixedHoursInvoice::new(invoice.name.clone())
        .with_workplace(invoice.workplace.clone())
        .with_work_days(invoice.work_days)
        .with_base_days(invoice.base_days)
        .with_ot_hours(invoice.ot_hours)
        .with_special_hours(invoice.special_hours)
        .with_special_ext_hours(invoice.special_ext_hours)
        .with_preserve_reference_hours(invoice.preserve_reference_hours)
}

fn resolved_workplace(
    invoice: &InvoiceAuditInvoice,
    workplace: &str,
    record: Option<&InvoiceAuditRecord>,
) -> String {
    let explicit = clean_ref(workplace);
    if !explicit.is_empty() {
        return explicit;
    }
    if let Some(record) = record {
        let record_workplace = clean_ref(&record.workplace);
        if !record_workplace.is_empty() {
            return record_workplace;
        }
    }
    clean_ref(&invoice.workplace)
}

fn selected_base_hourly(invoice: &InvoiceAuditInvoice, record: Option<&InvoiceAuditRecord>) -> f64 {
    if let Some(record) = record {
        if record.base_hourly.is_finite() && record.base_hourly != 0.0 {
            return record.base_hourly;
        }
    }
    safe_number(invoice.base_hourly)
}

fn safe_number(value: f64) -> f64 {
    if value.is_finite() {
        value
    } else {
        0.0
    }
}

fn round_won(amount: f64) -> i64 {
    round_ties_even(amount) as i64
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

fn format_i64(value: i64) -> String {
    let sign = if value < 0 { "-" } else { "" };
    let digits = value.abs().to_string();
    let mut out = String::new();
    for (index, ch) in digits.chars().rev().enumerate() {
        if index > 0 && index % 3 == 0 {
            out.push(',');
        }
        out.push(ch);
    }
    let grouped = out.chars().rev().collect::<String>();
    format!("{sign}{grouped}")
}

fn clean(value: impl Into<String>) -> String {
    value.into().trim().to_owned()
}

fn clean_ref(value: &str) -> String {
    value.trim().to_owned()
}

#[cfg(test)]
mod tests {
    use crate::fixed_hours::{FixedHoursPayType, FixedHoursProfile, FIXED_HOURS_SOURCE_CONTRACT};
    use crate::invoice_audit::{
        audit_invoice_row, estimate_break_hours, InvoiceAuditInvoice, InvoiceAuditRecord,
        InvoiceAuditStatus,
    };
    use crate::service::{PayrollApiService, ServiceConfig};
    use crate::workplace_hours::{WorkplaceHoursMode, WorkplaceHoursPolicy};
    use serde_json::json;

    #[test]
    fn audits_supplied_policy_record_mismatch_like_python() {
        let policy = WorkplaceHoursPolicy::new()
            .with_mode(WorkplaceHoursMode::Fixed)
            .with_hours(209.0);
        let invoice = InvoiceAuditInvoice::new("박감사")
            .with_base_days(209.0)
            .with_work_days(200.0)
            .with_base_salary(2_000_000);
        let record = InvoiceAuditRecord::new("박감사")
            .with_base_hourly(10_000.0)
            .with_monthly_work_hours(208.0);

        let row = audit_invoice_row(invoice, "앰코", &policy, Some(&record), None);

        assert_eq!(row.status, InvoiceAuditStatus::Warn);
        assert_eq!(row.status_label, "확인");
        assert_eq!(row.applied_monthly_hours, 209.0);
        assert_eq!(row.break_hours, Some(9.0));
        assert_eq!(row.calc_base_salary, 2_090_000);
        assert_eq!(row.formula, "기본시급 10,000원 × 209시간 = 2,090,000원");
        assert!(row
            .flags
            .contains(&"기본급 불일치: 산출 2,090,000원 vs 청구서 2,000,000원".to_owned()));
        assert!(row
            .flags
            .contains(&"대장 적용시간(208h)과 재검열(209h) 상이".to_owned()));
    }

    #[test]
    fn composes_fixed_profile_audit_flags_like_python() {
        let policy = WorkplaceHoursPolicy::new()
            .with_mode(WorkplaceHoursMode::Fixed)
            .with_hours(209.0);
        let invoice = InvoiceAuditInvoice::new("최연봉")
            .with_base_days(150.0)
            .with_work_days(150.0)
            .with_ot_hours(5.0)
            .with_special_hours(3.0)
            .with_special_ext_hours(2.0)
            .with_base_hourly(10_000.0)
            .with_base_salary(2_090_000);
        let profile = FixedHoursProfile::active()
            .with_monthly_fixed_hours(209.0)
            .with_fixed_overtime_hours(10.0)
            .with_fixed_extension_hours(20.0)
            .with_pay_type(FixedHoursPayType::MonthlySalary)
            .with_job_group("경비")
            .with_source("contract")
            .with_source_label(FIXED_HOURS_SOURCE_CONTRACT)
            .with_contract_id("c1");

        let row = audit_invoice_row(invoice, "강남경비", &policy, None, Some(&profile));

        assert_eq!(row.status, InvoiceAuditStatus::Warn);
        assert!(row.fixed_hours_mode);
        assert_eq!(row.fixed_hours_source, FIXED_HOURS_SOURCE_CONTRACT);
        assert_eq!(row.hours_source, FIXED_HOURS_SOURCE_CONTRACT);
        assert_eq!(row.applied_monthly_hours, 209.0);
        assert_eq!(row.calc_base_salary, 2_090_000);
        assert_eq!(
            &row.flags[..5],
            [
                "근로계약서 기준 고정 (경비)",
                "급여형태: 연봉직",
                "청구서 연장(5h) ≠ 계약 고정(20h)",
                "청구서 특근(3h) ≠ 계약 고정(10h)",
                "청구서 근무시간(150h) ≠ 계약 월시간(209h)",
            ]
        );
    }

    #[test]
    fn estimates_break_hours_from_policy_or_invoice_gap() {
        let policy = WorkplaceHoursPolicy::new()
            .with_mode(WorkplaceHoursMode::Fixed)
            .with_hours(209.0)
            .with_daily_hours(8.0)
            .with_break_minutes(60.0);
        let invoice = InvoiceAuditInvoice::new("이영희")
            .with_base_days(209.0)
            .with_work_days(20.0);

        assert_eq!(estimate_break_hours(&invoice, &policy), Some(20.0));

        let no_break_policy = WorkplaceHoursPolicy::new()
            .with_mode(WorkplaceHoursMode::Fixed)
            .with_hours(209.0);
        let gap_invoice = InvoiceAuditInvoice::new("박감사")
            .with_base_days(209.0)
            .with_work_days(200.0)
            .with_leave_days(4.0);

        assert_eq!(
            estimate_break_hours(&gap_invoice, &no_break_policy),
            Some(5.0)
        );
    }

    #[test]
    fn serializes_compatibility_shape() {
        let policy = WorkplaceHoursPolicy::new()
            .with_mode(WorkplaceHoursMode::InvoiceWorkDays)
            .with_hours(209.0);
        let invoice = InvoiceAuditInvoice::new("김철수")
            .with_base_days(209.0)
            .with_work_days(0.0)
            .with_base_hourly(9_000.0);

        let row = audit_invoice_row(invoice, "앰코", &policy, None, None);
        let value = serde_json::to_value(row).unwrap();

        assert_eq!(value["status"], "warn");
        assert_eq!(value["status_label"], "확인");
        assert_eq!(value["policy_mode"], "invoice_work_days");
        assert_eq!(value["applied_monthly_hours"], json!(209.0));
        assert_eq!(value["flags"][0], "청구서 근무시간(J) 없음 — 고정값 대체");
    }

    #[test]
    fn service_delegates_invoice_row_audit() {
        let service = PayrollApiService::new(ServiceConfig::default());
        let policy = WorkplaceHoursPolicy::new()
            .with_mode(WorkplaceHoursMode::Fixed)
            .with_hours(209.0);
        let invoice = InvoiceAuditInvoice::new("홍길동")
            .with_base_days(209.0)
            .with_work_days(200.0)
            .with_base_hourly(10_000.0)
            .with_base_salary(2_090_000);

        let row = service.audit_invoice_row(invoice, "앰코", &policy, None, None);

        assert_eq!(row.status, InvoiceAuditStatus::Pass);
        assert_eq!(row.calc_base_salary, 2_090_000);
    }
}
