use serde::Serialize;

pub const STANDARD_MONTHLY_HOURS: f64 = 209.0;
pub const MEAL_ALLOWANCE_PER_DAY: f64 = 5_500.0;
pub const MEAL_NON_TAXABLE_CAP: i64 = 200_000;
pub const OVERTIME_PREMIUM: f64 = 1.5;
pub const NIGHT_PREMIUM: f64 = 0.5;
pub const HOLIDAY_PREMIUM: f64 = 1.5;
pub const OVERLAP_PREMIUM: f64 = 0.5;

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct PayrollEarningsInput {
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
}

impl PayrollEarningsInput {
    pub const fn new() -> Self {
        Self {
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
        }
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
}

impl Default for PayrollEarningsInput {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollEarningsBreakdown {
    pub base_salary: i64,
    pub fixed_allowance: i64,
    pub overtime: i64,
    pub night: i64,
    pub holiday: i64,
    pub overlap_premium: i64,
    pub weekly_holiday: i64,
    pub meal: i64,
    pub transport: i64,
    pub other: i64,
    pub additional: i64,
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct PayrollEarningsHours {
    pub overtime: f64,
    pub night: f64,
    pub holiday: f64,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PayrollEarningsResult {
    pub ordinary_hourly: f64,
    pub hours: PayrollEarningsHours,
    pub earnings: PayrollEarningsBreakdown,
    pub gross_pay: i64,
    pub taxable_pay: i64,
    pub non_taxable_pay: i64,
}

pub fn calculate_ordinary_hourly(base_salary: f64, fixed_allowance: f64, preset: f64) -> f64 {
    let preset = safe_number(preset);
    if preset > 0.0 {
        return preset;
    }

    let total = safe_number(base_salary) + safe_number(fixed_allowance);
    if total <= 0.0 {
        0.0
    } else {
        total / STANDARD_MONTHLY_HOURS
    }
}

pub fn calculate_weekly_holiday_pay(ordinary_hourly: f64, weekly_work_hours: f64) -> i64 {
    let ordinary_hourly = safe_number(ordinary_hourly);
    if ordinary_hourly <= 0.0 {
        return 0;
    }

    let ratio = safe_number(weekly_work_hours).min(40.0) / 40.0;
    let hours = 8.0 * ratio;
    round_won(ordinary_hourly * hours)
}

pub fn calculate_overlap_premium(
    overtime_hours: f64,
    night_hours: f64,
    ordinary_hourly: f64,
) -> i64 {
    let overlap = safe_number(overtime_hours)
        .max(0.0)
        .min(safe_number(night_hours).max(0.0));
    round_won(overlap * safe_number(ordinary_hourly) * OVERLAP_PREMIUM)
}

pub fn calculate_payroll_earnings(input: PayrollEarningsInput) -> PayrollEarningsResult {
    let mut base_salary = safe_number(input.base_salary);
    let fixed_allowance = safe_number(input.fixed_allowance);
    let ordinary_hourly =
        calculate_ordinary_hourly(base_salary, fixed_allowance, input.ordinary_hourly);

    let mut overtime_hours = safe_number(input.overtime_hours);
    let night_hours = safe_number(input.night_hours);
    let holiday_hours = safe_number(input.holiday_hours);

    let mut overtime_amount = round_won(overtime_hours * ordinary_hourly * OVERTIME_PREMIUM);
    if overtime_amount <= 0 {
        let raw = safe_number(input.overtime_amount_raw);
        if raw > 0.0 && !is_likely_hours(raw, ordinary_hourly) {
            overtime_amount = round_won(raw);
            if ordinary_hourly > 0.0 {
                overtime_hours = raw / (ordinary_hourly * OVERTIME_PREMIUM);
            }
        }
    }

    let mut night_amount = round_won(night_hours * ordinary_hourly * NIGHT_PREMIUM);
    if night_amount <= 0 {
        let raw = safe_number(input.night_amount_raw);
        if raw > 0.0 && !is_likely_hours(raw, ordinary_hourly) {
            night_amount = round_won(raw);
        }
    }

    let mut holiday_amount = round_won(holiday_hours * ordinary_hourly * HOLIDAY_PREMIUM);
    if holiday_amount <= 0 {
        let raw = safe_number(input.holiday_amount_raw);
        if raw > 0.0 && !is_likely_hours(raw, ordinary_hourly) {
            holiday_amount = round_won(raw);
        }
    }

    let overlap_amount = calculate_overlap_premium(overtime_hours, night_hours, ordinary_hourly);
    let meal_allowance = round_won(safe_number(input.meal_days) * MEAL_ALLOWANCE_PER_DAY);
    let transport = round_won(input.transport_allowance);
    let other_pay = round_won(input.other_pay);
    let additional_pay = round_won(input.additional_pay);
    let weekly_holiday_pay = calculate_weekly_holiday_pay(ordinary_hourly, input.weekly_work_hours);

    if base_salary <= 0.0 && ordinary_hourly > 0.0 {
        base_salary = round_won(ordinary_hourly * STANDARD_MONTHLY_HOURS) as f64;
    }

    let earnings = PayrollEarningsBreakdown {
        base_salary: round_won(base_salary),
        fixed_allowance: round_won(fixed_allowance),
        overtime: overtime_amount,
        night: night_amount,
        holiday: holiday_amount,
        overlap_premium: overlap_amount,
        weekly_holiday: weekly_holiday_pay,
        meal: meal_allowance,
        transport,
        other: other_pay,
        additional: additional_pay,
    };
    let gross_pay = earnings.base_salary
        + earnings.fixed_allowance
        + earnings.overtime
        + earnings.night
        + earnings.holiday
        + earnings.overlap_premium
        + earnings.weekly_holiday
        + earnings.meal
        + earnings.transport
        + earnings.other
        + earnings.additional;
    let non_taxable_pay = meal_allowance.min(MEAL_NON_TAXABLE_CAP);
    let taxable_pay = gross_pay - non_taxable_pay;

    PayrollEarningsResult {
        ordinary_hourly: round_to_cents(ordinary_hourly),
        hours: PayrollEarningsHours {
            overtime: overtime_hours,
            night: night_hours,
            holiday: holiday_hours,
        },
        earnings,
        gross_pay,
        taxable_pay: round_won(taxable_pay as f64),
        non_taxable_pay: round_won(non_taxable_pay as f64),
    }
}

fn is_likely_hours(value: f64, ordinary_hourly: f64) -> bool {
    if value <= 0.0 {
        return false;
    }
    if value <= 300.0 {
        let expected_pay = safe_number(ordinary_hourly) * OVERTIME_PREMIUM * value;
        if value >= 1_000.0 {
            return false;
        }
        if expected_pay > 0.0 && (value - expected_pay).abs() / expected_pay < 0.05 {
            return false;
        }
        return true;
    }
    false
}

fn safe_number(value: f64) -> f64 {
    if value.is_finite() { value } else { 0.0 }
}

fn round_to_cents(amount: f64) -> f64 {
    round_ties_even(amount * 100.0) / 100.0
}

fn round_won(amount: f64) -> i64 {
    round_ties_even(safe_number(amount)) as i64
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
    fn calculates_python_compatible_ordinary_hourly_helpers() {
        assert_eq!(
            calculate_ordinary_hourly(2_090_000.0, 100_000.0, 0.0),
            10_478.468899521531
        );
        assert_eq!(calculate_ordinary_hourly(0.0, 0.0, 12_000.0), 12_000.0);
        assert_eq!(calculate_weekly_holiday_pay(10_000.0, 35.0), 70_000);
        assert_eq!(calculate_overlap_premium(10.0, 4.0, 10_000.0), 20_000);
    }

    #[test]
    fn calculates_supplied_input_earnings_gross_and_taxable_pay() {
        let result = calculate_payroll_earnings(
            PayrollEarningsInput::new()
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

        assert_eq!(result.ordinary_hourly, 10_478.47);
        assert_eq!(result.hours.overtime, 10.0);
        assert_eq!(result.hours.night, 4.0);
        assert_eq!(result.hours.holiday, 8.0);
        assert_eq!(result.earnings.base_salary, 2_090_000);
        assert_eq!(result.earnings.fixed_allowance, 100_000);
        assert_eq!(result.earnings.overtime, 157_177);
        assert_eq!(result.earnings.night, 20_957);
        assert_eq!(result.earnings.holiday, 125_742);
        assert_eq!(result.earnings.overlap_premium, 20_957);
        assert_eq!(result.earnings.weekly_holiday, 73_349);
        assert_eq!(result.earnings.meal, 121_000);
        assert_eq!(result.earnings.transport, 50_000);
        assert_eq!(result.earnings.other, 12_346);
        assert_eq!(result.earnings.additional, 100_000);
        assert_eq!(result.gross_pay, 2_871_528);
        assert_eq!(result.non_taxable_pay, 121_000);
        assert_eq!(result.taxable_pay, 2_750_528);
    }

    #[test]
    fn uses_raw_amount_fallback_and_caps_non_taxable_meal_pay() {
        let result = calculate_payroll_earnings(
            PayrollEarningsInput::new()
                .with_ordinary_hourly(12_000.0)
                .with_overtime_amount_raw(300_000.0)
                .with_night_amount_raw(50_000.0)
                .with_holiday_amount_raw(200_000.0)
                .with_meal_days(50.0)
                .with_weekly_work_hours(40.0),
        );

        assert_eq!(result.ordinary_hourly, 12_000.0);
        assert_eq!(result.hours.overtime, 16.666666666666668);
        assert_eq!(result.hours.night, 0.0);
        assert_eq!(result.hours.holiday, 0.0);
        assert_eq!(result.earnings.base_salary, 2_508_000);
        assert_eq!(result.earnings.overtime, 300_000);
        assert_eq!(result.earnings.night, 50_000);
        assert_eq!(result.earnings.holiday, 200_000);
        assert_eq!(result.earnings.overlap_premium, 0);
        assert_eq!(result.earnings.weekly_holiday, 96_000);
        assert_eq!(result.earnings.meal, 275_000);
        assert_eq!(result.gross_pay, 3_429_000);
        assert_eq!(result.non_taxable_pay, 200_000);
        assert_eq!(result.taxable_pay, 3_229_000);
    }

    #[test]
    fn serializes_stable_contract_shape() {
        let result = calculate_payroll_earnings(
            PayrollEarningsInput::new()
                .with_base_salary(2_090_000.0)
                .with_fixed_allowance(100_000.0)
                .with_overtime_hours(10.0)
                .with_night_hours(4.0)
                .with_holiday_hours(8.0)
                .with_meal_days(22.0)
                .with_weekly_work_hours(35.0),
        );
        let value = serde_json::to_value(result).unwrap();

        assert_eq!(value["ordinary_hourly"], json!(10_478.47));
        assert_eq!(value["hours"]["overtime"], json!(10.0));
        assert_eq!(value["earnings"]["overlap_premium"], json!(20_957));
        assert_eq!(value["gross_pay"], json!(2_709_182));
        assert_eq!(value["non_taxable_pay"], json!(121_000));
        assert_eq!(value["taxable_pay"], json!(2_588_182));
    }
}
