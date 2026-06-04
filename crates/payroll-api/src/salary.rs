use crate::deductions::lookup_simplified_income_tax;
use crate::earnings::{
    PayrollEarningsBreakdown, PayrollEarningsHours, PayrollEarningsInput,
    calculate_payroll_earnings,
};
use crate::social_insurance::{SocialInsuranceInput, calculate_social_insurance};
use serde::Serialize;

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PayrollSalaryInput {
    pub name: String,
    pub emp_no: String,
    pub department: String,
    pub account_no: String,
    pub base_salary: f64,
    pub fixed_allowance: f64,
    pub ordinary_hourly: f64,
    pub overtime_hours: f64,
    pub night_hours: f64,
    pub holiday_hours: f64,
    pub overtime_amount_raw: f64,
    pub night_amount_raw: f64,
    pub holiday_amount_raw: f64,
    pub meal_days: f64,
    pub transport_allowance: f64,
    pub other_pay: f64,
    pub additional_pay: f64,
    pub weekly_work_hours: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub preset_national_pension: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub preset_health_insurance: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub preset_income_tax: Option<f64>,
    pub insurance_exempt: bool,
}

impl PayrollSalaryInput {
    pub fn new() -> Self {
        Self {
            name: String::new(),
            emp_no: String::new(),
            department: String::new(),
            account_no: String::new(),
            base_salary: 0.0,
            fixed_allowance: 0.0,
            ordinary_hourly: 0.0,
            overtime_hours: 0.0,
            night_hours: 0.0,
            holiday_hours: 0.0,
            overtime_amount_raw: 0.0,
            night_amount_raw: 0.0,
            holiday_amount_raw: 0.0,
            meal_days: 0.0,
            transport_allowance: 0.0,
            other_pay: 0.0,
            additional_pay: 0.0,
            weekly_work_hours: 40.0,
            preset_national_pension: None,
            preset_health_insurance: None,
            preset_income_tax: None,
            insurance_exempt: false,
        }
    }

    pub fn with_name(mut self, value: impl Into<String>) -> Self {
        self.name = value.into();
        self
    }

    pub fn with_emp_no(mut self, value: impl Into<String>) -> Self {
        self.emp_no = value.into();
        self
    }

    pub fn with_department(mut self, value: impl Into<String>) -> Self {
        self.department = value.into();
        self
    }

    pub fn with_account_no(mut self, value: impl Into<String>) -> Self {
        self.account_no = value.into();
        self
    }

    pub const fn with_base_salary(mut self, amount: f64) -> Self {
        self.base_salary = amount;
        self
    }

    pub const fn with_fixed_allowance(mut self, amount: f64) -> Self {
        self.fixed_allowance = amount;
        self
    }

    pub const fn with_ordinary_hourly(mut self, amount: f64) -> Self {
        self.ordinary_hourly = amount;
        self
    }

    pub const fn with_overtime_hours(mut self, hours: f64) -> Self {
        self.overtime_hours = hours;
        self
    }

    pub const fn with_night_hours(mut self, hours: f64) -> Self {
        self.night_hours = hours;
        self
    }

    pub const fn with_holiday_hours(mut self, hours: f64) -> Self {
        self.holiday_hours = hours;
        self
    }

    pub const fn with_overtime_amount_raw(mut self, amount: f64) -> Self {
        self.overtime_amount_raw = amount;
        self
    }

    pub const fn with_night_amount_raw(mut self, amount: f64) -> Self {
        self.night_amount_raw = amount;
        self
    }

    pub const fn with_holiday_amount_raw(mut self, amount: f64) -> Self {
        self.holiday_amount_raw = amount;
        self
    }

    pub const fn with_meal_days(mut self, days: f64) -> Self {
        self.meal_days = days;
        self
    }

    pub const fn with_transport_allowance(mut self, amount: f64) -> Self {
        self.transport_allowance = amount;
        self
    }

    pub const fn with_other_pay(mut self, amount: f64) -> Self {
        self.other_pay = amount;
        self
    }

    pub const fn with_additional_pay(mut self, amount: f64) -> Self {
        self.additional_pay = amount;
        self
    }

    pub const fn with_weekly_work_hours(mut self, hours: f64) -> Self {
        self.weekly_work_hours = hours;
        self
    }

    pub const fn with_preset_national_pension(mut self, amount: f64) -> Self {
        self.preset_national_pension = Some(amount);
        self
    }

    pub const fn with_preset_health_insurance(mut self, amount: f64) -> Self {
        self.preset_health_insurance = Some(amount);
        self
    }

    pub const fn with_preset_income_tax(mut self, amount: f64) -> Self {
        self.preset_income_tax = Some(amount);
        self
    }

    pub const fn with_insurance_exempt(mut self, insurance_exempt: bool) -> Self {
        self.insurance_exempt = insurance_exempt;
        self
    }
}

impl Default for PayrollSalaryInput {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PayrollSalaryTaxMethod {
    Preset,
    SimplifiedTable,
}

impl PayrollSalaryTaxMethod {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Preset => "PRESET",
            Self::SimplifiedTable => "SIMPLIFIED_TABLE",
        }
    }
}

impl Serialize for PayrollSalaryTaxMethod {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollSalaryDeductions {
    pub national_pension: i64,
    pub health_insurance: i64,
    pub long_term_care: i64,
    pub employment_insurance: i64,
    pub income_tax: i64,
    pub local_income_tax: i64,
    pub total: i64,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PayrollSalaryResult {
    pub name: String,
    pub emp_no: String,
    pub department: String,
    pub account_no: String,
    pub ordinary_hourly: f64,
    pub hours: PayrollEarningsHours,
    pub earnings: PayrollEarningsBreakdown,
    pub deductions: PayrollSalaryDeductions,
    pub gross_pay: i64,
    pub taxable_pay: i64,
    pub non_taxable_pay: i64,
    pub total_deductions: i64,
    pub net_pay: i64,
    pub tax_method: PayrollSalaryTaxMethod,
}

pub fn calculate_payroll_salary(input: PayrollSalaryInput) -> PayrollSalaryResult {
    let earnings_result = calculate_payroll_earnings(PayrollEarningsInput {
        base_salary: input.base_salary,
        fixed_allowance: input.fixed_allowance,
        ordinary_hourly: input.ordinary_hourly,
        overtime_hours: input.overtime_hours,
        night_hours: input.night_hours,
        holiday_hours: input.holiday_hours,
        overtime_amount_raw: input.overtime_amount_raw,
        night_amount_raw: input.night_amount_raw,
        holiday_amount_raw: input.holiday_amount_raw,
        meal_days: input.meal_days,
        transport_allowance: input.transport_allowance,
        other_pay: input.other_pay,
        additional_pay: input.additional_pay,
        weekly_work_hours: input.weekly_work_hours,
    });

    let mut social_input = SocialInsuranceInput::new(earnings_result.taxable_pay as f64)
        .with_insurance_exempt(input.insurance_exempt);
    if let Some(amount) = input.preset_national_pension {
        social_input = social_input.with_preset_national_pension(amount);
    }
    if let Some(amount) = input.preset_health_insurance {
        social_input = social_input.with_preset_health_insurance(amount);
    }
    let insurance = calculate_social_insurance(social_input);
    let tax = calculate_salary_income_tax(earnings_result.taxable_pay, input.preset_income_tax);

    let deductions = PayrollSalaryDeductions {
        national_pension: insurance.national_pension,
        health_insurance: insurance.health_insurance,
        long_term_care: insurance.long_term_care,
        employment_insurance: insurance.employment_insurance,
        income_tax: tax.income_tax,
        local_income_tax: tax.local_income_tax,
        total: insurance.total + tax.total,
    };
    let total_deductions = deductions.total;
    let net_pay = earnings_result.gross_pay - total_deductions;

    PayrollSalaryResult {
        name: input.name,
        emp_no: input.emp_no,
        department: input.department,
        account_no: input.account_no,
        ordinary_hourly: earnings_result.ordinary_hourly,
        hours: earnings_result.hours,
        earnings: earnings_result.earnings,
        deductions,
        gross_pay: earnings_result.gross_pay,
        taxable_pay: earnings_result.taxable_pay,
        non_taxable_pay: earnings_result.non_taxable_pay,
        total_deductions,
        net_pay,
        tax_method: tax.method,
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct SalaryIncomeTax {
    income_tax: i64,
    local_income_tax: i64,
    total: i64,
    method: PayrollSalaryTaxMethod,
}

fn calculate_salary_income_tax(
    taxable_pay: i64,
    preset_income_tax: Option<f64>,
) -> SalaryIncomeTax {
    let (income_tax, method) =
        if let Some(amount) = preset_income_tax.filter(|amount| *amount > 0.0) {
            (round_won(amount), PayrollSalaryTaxMethod::Preset)
        } else {
            (
                lookup_simplified_income_tax(taxable_pay),
                PayrollSalaryTaxMethod::SimplifiedTable,
            )
        };

    let local_income_tax = round_won(income_tax as f64 * 0.10);
    SalaryIncomeTax {
        income_tax,
        local_income_tax,
        total: income_tax + local_income_tax,
        method,
    }
}

fn round_won(amount: f64) -> i64 {
    round_ties_even(if amount.is_finite() { amount } else { 0.0 }) as i64
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

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn calculates_python_compatible_supplied_salary_result() {
        let result = calculate_payroll_salary(
            PayrollSalaryInput::new()
                .with_name("홍길동")
                .with_emp_no("E001")
                .with_department("Payroll")
                .with_account_no("111-222")
                .with_base_salary(2_090_000.0)
                .with_fixed_allowance(100_000.0)
                .with_overtime_hours(10.0)
                .with_night_hours(4.0)
                .with_holiday_hours(8.0)
                .with_meal_days(22.0)
                .with_transport_allowance(50_000.0)
                .with_other_pay(12_345.5)
                .with_additional_pay(100_000.0)
                .with_weekly_work_hours(35.0),
        );

        assert_eq!(result.name, "홍길동");
        assert_eq!(result.emp_no, "E001");
        assert_eq!(result.department, "Payroll");
        assert_eq!(result.account_no, "111-222");
        assert_eq!(result.ordinary_hourly, 10_478.47);
        assert_eq!(result.gross_pay, 2_871_528);
        assert_eq!(result.taxable_pay, 2_750_528);
        assert_eq!(result.deductions.national_pension, 123_774);
        assert_eq!(result.deductions.health_insurance, 97_506);
        assert_eq!(result.deductions.long_term_care, 12_627);
        assert_eq!(result.deductions.employment_insurance, 24_750);
        assert_eq!(result.deductions.income_tax, 210_000);
        assert_eq!(result.deductions.local_income_tax, 21_000);
        assert_eq!(result.total_deductions, 489_657);
        assert_eq!(result.net_pay, 2_381_871);
        assert_eq!(result.tax_method, PayrollSalaryTaxMethod::SimplifiedTable);
    }

    #[test]
    fn preserves_raw_amount_fallback_salary_parity() {
        let result = calculate_payroll_salary(
            PayrollSalaryInput::new()
                .with_name("김시급")
                .with_emp_no("E002")
                .with_department("Ops")
                .with_account_no("333-444")
                .with_ordinary_hourly(12_000.0)
                .with_overtime_amount_raw(300_000.0)
                .with_night_amount_raw(50_000.0)
                .with_holiday_amount_raw(200_000.0)
                .with_meal_days(50.0)
                .with_weekly_work_hours(40.0),
        );

        assert_eq!(result.hours.overtime, 16.666666666666668);
        assert_eq!(result.earnings.base_salary, 2_508_000);
        assert_eq!(result.gross_pay, 3_429_000);
        assert_eq!(result.non_taxable_pay, 200_000);
        assert_eq!(result.taxable_pay, 3_229_000);
        assert_eq!(result.deductions.total, 644_657);
        assert_eq!(result.net_pay, 2_784_343);
    }

    #[test]
    fn preset_insurance_and_tax_use_calculator_salary_rounding() {
        let result = calculate_payroll_salary(
            PayrollSalaryInput::new()
                .with_name("박프리셋")
                .with_base_salary(4_000_000.0)
                .with_meal_days(20.0)
                .with_preset_national_pension(123_456.5)
                .with_preset_health_insurance(76_543.5)
                .with_preset_income_tax(123_456.5),
        );

        assert_eq!(result.ordinary_hourly, 19_138.76);
        assert_eq!(result.earnings.weekly_holiday, 153_110);
        assert_eq!(result.gross_pay, 4_263_110);
        assert_eq!(result.taxable_pay, 4_153_110);
        assert_eq!(result.deductions.national_pension, 123_456);
        assert_eq!(result.deductions.health_insurance, 76_544);
        assert_eq!(result.deductions.long_term_care, 9_912);
        assert_eq!(result.deductions.employment_insurance, 37_380);
        assert_eq!(result.deductions.income_tax, 123_456);
        assert_eq!(result.deductions.local_income_tax, 12_346);
        assert_eq!(result.total_deductions, 383_094);
        assert_eq!(result.net_pay, 3_880_016);
        assert_eq!(result.tax_method, PayrollSalaryTaxMethod::Preset);
    }

    #[test]
    fn serializes_stable_calculator_compatible_shape() {
        let result = calculate_payroll_salary(
            PayrollSalaryInput::new()
                .with_name("홍길동")
                .with_base_salary(2_090_000.0)
                .with_fixed_allowance(100_000.0)
                .with_overtime_hours(10.0)
                .with_night_hours(4.0)
                .with_holiday_hours(8.0)
                .with_meal_days(22.0)
                .with_weekly_work_hours(35.0),
        );
        let value = serde_json::to_value(result).unwrap();

        assert_eq!(value["name"], json!("홍길동"));
        assert_eq!(value["ordinary_hourly"], json!(10_478.47));
        assert_eq!(value["gross_pay"], json!(2_709_182));
        assert_eq!(value["deductions"]["total"], json!(474_391));
        assert_eq!(value["tax_method"], json!("SIMPLIFIED_TABLE"));
        assert_eq!(value["net_pay"], json!(2_234_791));
    }
}
