use serde::Serialize;

pub const EI65_EXEMPT_AGE_YEARS: i32 = 65;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Ei65EligibilityStatus {
    Exempt,
    Liable,
    Unknown,
}

impl Ei65EligibilityStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Exempt => "exempt",
            Self::Liable => "liable",
            Self::Unknown => "unknown",
        }
    }

    pub const fn label(self) -> &'static str {
        match self {
            Self::Exempt => "납부 없음 (0원)",
            Self::Liable => "납부 대상",
            Self::Unknown => "미확인",
        }
    }
}

impl Serialize for Ei65EligibilityStatus {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum Ei65UnknownDefault {
    #[default]
    Skip,
    Deduct,
}

impl Ei65UnknownDefault {
    pub fn normalize(value: impl AsRef<str>) -> Self {
        if value.as_ref().trim().eq_ignore_ascii_case("deduct") {
            Self::Deduct
        } else {
            Self::Skip
        }
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Skip => "skip",
            Self::Deduct => "deduct",
        }
    }

    pub const fn action_label(self) -> &'static str {
        match self {
            Self::Skip => "공제 생략",
            Self::Deduct => "공제 적용",
        }
    }
}

impl Serialize for Ei65UnknownDefault {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct Ei65VerificationRecord {
    pub employee_id: String,
    pub employee_name: String,
    pub check_date: String,
    pub premium_amount: i64,
    pub management_no: String,
    pub source: String,
}

impl Ei65VerificationRecord {
    pub fn new(premium_amount: i64) -> Self {
        Self {
            employee_id: String::new(),
            employee_name: String::new(),
            check_date: String::new(),
            premium_amount: premium_amount.max(0),
            management_no: String::new(),
            source: "manual".to_owned(),
        }
    }

    pub fn normalized(self) -> Self {
        Self {
            employee_id: clean(&self.employee_id),
            employee_name: clean(&self.employee_name),
            check_date: clean(&self.check_date).chars().take(10).collect(),
            premium_amount: self.premium_amount.max(0),
            management_no: clean(&self.management_no),
            source: normalize_source(&self.source),
        }
    }

    pub fn status(&self) -> Ei65EligibilityStatus {
        if self.premium_amount <= 0 {
            Ei65EligibilityStatus::Exempt
        } else {
            Ei65EligibilityStatus::Liable
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

    pub fn with_check_date(mut self, check_date: impl Into<String>) -> Self {
        self.check_date = clean(check_date).chars().take(10).collect();
        self
    }

    pub fn with_management_no(mut self, management_no: impl Into<String>) -> Self {
        self.management_no = clean(management_no);
        self
    }

    pub fn with_source(mut self, source: impl Into<String>) -> Self {
        self.source = normalize_source(&source.into());
        self
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct Ei65PayrollInput {
    pub identity: String,
    pub payroll_period: String,
    pub employee_id: String,
    pub employee_name: String,
    pub workplace: String,
    pub site_management_no: String,
    pub unknown_default: Ei65UnknownDefault,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub latest_verification: Option<Ei65VerificationRecord>,
}

impl Ei65PayrollInput {
    pub fn new(identity: impl Into<String>, payroll_period: impl Into<String>) -> Self {
        Self {
            identity: clean(identity),
            payroll_period: clean(payroll_period),
            employee_id: String::new(),
            employee_name: String::new(),
            workplace: String::new(),
            site_management_no: String::new(),
            unknown_default: Ei65UnknownDefault::Skip,
            latest_verification: None,
        }
    }

    pub fn normalized(self) -> Self {
        Self {
            identity: clean(&self.identity),
            payroll_period: clean(&self.payroll_period),
            employee_id: clean(&self.employee_id),
            employee_name: clean(&self.employee_name),
            workplace: clean(&self.workplace),
            site_management_no: clean(&self.site_management_no),
            unknown_default: self.unknown_default,
            latest_verification: self
                .latest_verification
                .map(Ei65VerificationRecord::normalized),
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

    pub fn with_workplace(mut self, workplace: impl Into<String>) -> Self {
        self.workplace = clean(workplace);
        self
    }

    pub fn with_site_management_no(mut self, management_no: impl Into<String>) -> Self {
        self.site_management_no = clean(management_no);
        self
    }

    pub fn with_unknown_default(mut self, action: Ei65UnknownDefault) -> Self {
        self.unknown_default = action;
        self
    }

    pub fn with_unknown_default_text(mut self, action: impl AsRef<str>) -> Self {
        self.unknown_default = Ei65UnknownDefault::normalize(action);
        self
    }

    pub fn with_verification(mut self, record: Ei65VerificationRecord) -> Self {
        self.latest_verification = Some(record.normalized());
        self
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct Ei65PayrollResult {
    pub status: Ei65EligibilityStatus,
    pub premium_amount: Option<i64>,
    pub management_no: String,
    pub deduct_employment_insurance: bool,
    pub warning: String,
    pub default_action: Ei65UnknownDefault,
}

pub fn resolve_ei_65_for_payroll(input: &Ei65PayrollInput) -> Ei65PayrollResult {
    let input = input.clone().normalized();
    if !is_age_65_plus_for_period(&input.identity, &input.payroll_period) {
        return Ei65PayrollResult {
            status: Ei65EligibilityStatus::Liable,
            premium_amount: None,
            management_no: String::new(),
            deduct_employment_insurance: true,
            warning: String::new(),
            default_action: Ei65UnknownDefault::Skip,
        };
    }

    if let Some(record) = input.latest_verification {
        let status = record.status();
        let management_no = if record.management_no.is_empty() {
            input.site_management_no
        } else {
            record.management_no
        };
        return Ei65PayrollResult {
            status,
            premium_amount: Some(record.premium_amount),
            management_no,
            deduct_employment_insurance: status == Ei65EligibilityStatus::Liable,
            warning: String::new(),
            default_action: Ei65UnknownDefault::Skip,
        };
    }

    let label = first_non_empty([&input.employee_name, &input.employee_id]).unwrap_or("해당 직원");
    let warning = format!(
        "{label}: 만 {EI65_EXEMPT_AGE_YEARS}세 이상 고용보험 KCOMWEL 확인 미완료 → 설정 기본값({}) 적용",
        input.unknown_default.action_label()
    );

    Ei65PayrollResult {
        status: Ei65EligibilityStatus::Unknown,
        premium_amount: None,
        management_no: input.site_management_no,
        deduct_employment_insurance: input.unknown_default == Ei65UnknownDefault::Deduct,
        warning,
        default_action: input.unknown_default,
    }
}

pub fn is_age_65_plus_for_period(
    identity: impl AsRef<str>,
    payroll_period: impl AsRef<str>,
) -> bool {
    age_years_from_korean_identity(identity, payroll_period)
        .map(|age| age >= EI65_EXEMPT_AGE_YEARS)
        .unwrap_or(false)
}

pub fn age_years_from_korean_identity(
    identity: impl AsRef<str>,
    payroll_period: impl AsRef<str>,
) -> Option<i32> {
    let as_of = period_end_date(payroll_period.as_ref())?;
    let birth = birth_date_from_korean_identity(identity.as_ref(), as_of)?;
    Some(age_years_at(birth, as_of))
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct SimpleDate {
    year: i32,
    month: u8,
    day: u8,
}

fn period_end_date(period: &str) -> Option<SimpleDate> {
    let mut parts = period.trim().split('-');
    let year = parts.next()?.parse::<i32>().ok()?;
    let month = parts.next()?.parse::<u8>().ok()?;
    if parts.next().is_some() || !(1..=12).contains(&month) {
        return None;
    }
    Some(SimpleDate {
        year,
        month,
        day: days_in_month(year, month),
    })
}

fn birth_date_from_korean_identity(value: &str, as_of: SimpleDate) -> Option<SimpleDate> {
    let digits = value
        .chars()
        .filter(|ch| ch.is_ascii_digit())
        .collect::<String>();
    if digits.len() < 6 {
        return None;
    }
    let yy = digits.get(0..2)?.parse::<i32>().ok()?;
    let month = digits.get(2..4)?.parse::<u8>().ok()?;
    let day = digits.get(4..6)?.parse::<u8>().ok()?;
    if !(1..=12).contains(&month) || day == 0 || day > 31 {
        return None;
    }

    let year = if digits.len() >= 7 {
        match digits.as_bytes()[6] {
            b'1' | b'2' | b'5' | b'6' => 1900 + yy,
            b'3' | b'4' | b'7' | b'8' => 2000 + yy,
            b'9' | b'0' => 1800 + yy,
            _ => pivot_year(yy, as_of),
        }
    } else {
        pivot_year(yy, as_of)
    };

    if day > days_in_month(year, month) {
        return None;
    }
    Some(SimpleDate { year, month, day })
}

fn pivot_year(yy: i32, as_of: SimpleDate) -> i32 {
    let pivot = as_of.year.rem_euclid(100);
    if yy > pivot {
        1900 + yy
    } else {
        2000 + yy
    }
}

fn age_years_at(birth: SimpleDate, as_of: SimpleDate) -> i32 {
    let mut years = as_of.year - birth.year;
    if (as_of.month, as_of.day) < (birth.month, birth.day) {
        years -= 1;
    }
    years
}

fn days_in_month(year: i32, month: u8) -> u8 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if is_leap_year(year) => 29,
        2 => 28,
        _ => 0,
    }
}

fn is_leap_year(year: i32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || year % 400 == 0
}

fn normalize_source(value: &str) -> String {
    let text = value.trim().to_ascii_lowercase();
    match text.as_str() {
        "manual" | "import" | "api" => text,
        _ => "manual".to_owned(),
    }
}

fn clean(value: impl Into<String>) -> String {
    value.into().trim().to_owned()
}

fn first_non_empty<const N: usize>(values: [&str; N]) -> Option<&str> {
    values.into_iter().find(|value| !value.trim().is_empty())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_korean_rrn_age_at_valid_payroll_period_end() {
        assert_eq!(
            age_years_from_korean_identity("500615-1", "2026-05"),
            Some(75)
        );
        assert_eq!(
            age_years_from_korean_identity("600501-1", "2026-05"),
            Some(66)
        );
        assert_eq!(
            age_years_from_korean_identity("650601-1", "2026-05"),
            Some(60)
        );
        assert!(is_age_65_plus_for_period("500615-1", "2026-05"));
        assert!(!is_age_65_plus_for_period("650601-1", "2026-05"));
    }

    #[test]
    fn parses_two_digit_birth_year_with_period_pivot() {
        assert_eq!(
            age_years_from_korean_identity("991231", "2026-05"),
            Some(26)
        );
        assert_eq!(
            age_years_from_korean_identity("270101", "2026-05"),
            Some(99)
        );
        assert_eq!(age_years_from_korean_identity("260101", "2026-05"), Some(0));
        assert_eq!(age_years_from_korean_identity("250101", "2026-05"), Some(1));
    }

    #[test]
    fn invalid_identity_or_period_is_not_age_exempt() {
        assert_eq!(age_years_from_korean_identity("bad", "2026-05"), None);
        assert_eq!(age_years_from_korean_identity("500230-1", "2026-05"), None);
        assert_eq!(age_years_from_korean_identity("500615-1", "bad"), None);
        assert!(!is_age_65_plus_for_period("bad", "2026-05"));
    }

    #[test]
    fn under_65_workers_remain_liable_without_kcomwel_lookup() {
        let result = resolve_ei_65_for_payroll(&Ei65PayrollInput::new("650601-1", "2026-05"));

        assert_eq!(result.status, Ei65EligibilityStatus::Liable);
        assert_eq!(result.premium_amount, None);
        assert_eq!(result.management_no, "");
        assert!(result.deduct_employment_insurance);
        assert_eq!(result.warning, "");
        assert_eq!(result.default_action, Ei65UnknownDefault::Skip);
    }

    #[test]
    fn zero_premium_record_exempts_age_65_plus_employment_insurance() {
        let record = Ei65VerificationRecord::new(0).with_management_no("1234567890");
        let result = resolve_ei_65_for_payroll(
            &Ei65PayrollInput::new("500615-1", "2026-05").with_verification(record),
        );

        assert_eq!(result.status, Ei65EligibilityStatus::Exempt);
        assert_eq!(result.premium_amount, Some(0));
        assert_eq!(result.management_no, "1234567890");
        assert!(!result.deduct_employment_insurance);
    }

    #[test]
    fn positive_premium_record_keeps_age_65_plus_employment_insurance_deduction() {
        let record = Ei65VerificationRecord::new(15_000).with_management_no("9876543210");
        let result = resolve_ei_65_for_payroll(
            &Ei65PayrollInput::new("500615-1", "2026-05").with_verification(record),
        );

        assert_eq!(result.status, Ei65EligibilityStatus::Liable);
        assert_eq!(result.premium_amount, Some(15_000));
        assert_eq!(result.management_no, "9876543210");
        assert!(result.deduct_employment_insurance);
    }

    #[test]
    fn negative_premium_normalizes_to_exempt_zero() {
        let record = Ei65VerificationRecord::new(-10).with_management_no("MGMT");
        let result = resolve_ei_65_for_payroll(
            &Ei65PayrollInput::new("500615-1", "2026-05").with_verification(record),
        );

        assert_eq!(result.status, Ei65EligibilityStatus::Exempt);
        assert_eq!(result.premium_amount, Some(0));
        assert!(!result.deduct_employment_insurance);
    }

    #[test]
    fn unknown_age_65_plus_status_applies_skip_default_with_warning() {
        let result = resolve_ei_65_for_payroll(
            &Ei65PayrollInput::new("500615-1", "2026-05")
                .with_employee_name("미확인")
                .with_site_management_no("SITE-1")
                .with_unknown_default(Ei65UnknownDefault::Skip),
        );

        assert_eq!(result.status, Ei65EligibilityStatus::Unknown);
        assert_eq!(result.premium_amount, None);
        assert_eq!(result.management_no, "SITE-1");
        assert!(!result.deduct_employment_insurance);
        assert_eq!(result.default_action, Ei65UnknownDefault::Skip);
        assert!(result.warning.contains("미확인"));
        assert!(result.warning.contains("공제 생략"));
    }

    #[test]
    fn unknown_age_65_plus_status_can_default_to_deduct() {
        let result = resolve_ei_65_for_payroll(
            &Ei65PayrollInput::new("500615-1", "2026-05")
                .with_employee_id("E-65")
                .with_unknown_default(Ei65UnknownDefault::Deduct),
        );

        assert_eq!(result.status, Ei65EligibilityStatus::Unknown);
        assert!(result.deduct_employment_insurance);
        assert_eq!(result.default_action, Ei65UnknownDefault::Deduct);
        assert!(result.warning.contains("E-65"));
        assert!(result.warning.contains("공제 적용"));
    }

    #[test]
    fn unknown_label_falls_back_to_employee_phrase() {
        let result = resolve_ei_65_for_payroll(&Ei65PayrollInput::new("500615-1", "2026-05"));

        assert!(result.warning.contains("해당 직원"));
    }

    #[test]
    fn record_management_no_falls_back_to_site_value() {
        let record = Ei65VerificationRecord::new(0);
        let result = resolve_ei_65_for_payroll(
            &Ei65PayrollInput::new("500615-1", "2026-05")
                .with_site_management_no("SITE-MGMT")
                .with_verification(record),
        );

        assert_eq!(result.management_no, "SITE-MGMT");
    }

    #[test]
    fn serializes_stable_contract_values() {
        let record = Ei65VerificationRecord::new(0).with_management_no("123");
        let result = resolve_ei_65_for_payroll(
            &Ei65PayrollInput::new("500615-1", "2026-05").with_verification(record),
        );
        let value = serde_json::to_value(result).unwrap();

        assert_eq!(value["status"], "exempt");
        assert_eq!(value["premium_amount"], 0);
        assert_eq!(value["management_no"], "123");
        assert_eq!(value["deduct_employment_insurance"], false);
        assert_eq!(value["default_action"], "skip");

        let unknown = resolve_ei_65_for_payroll(
            &Ei65PayrollInput::new("500615-1", "2026-05")
                .with_unknown_default(Ei65UnknownDefault::Skip),
        );
        let unknown_value = serde_json::to_value(unknown).unwrap();
        assert_eq!(unknown_value["premium_amount"], serde_json::Value::Null);
    }
}
