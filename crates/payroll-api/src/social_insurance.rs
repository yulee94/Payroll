use serde::Serialize;

pub const NATIONAL_PENSION_RATE: f64 = 0.045;
pub const HEALTH_INSURANCE_RATE: f64 = 0.03545;
pub const LONG_TERM_CARE_RATIO: f64 = 0.1295;
pub const EMPLOYMENT_INSURANCE_WORKER_RATE: f64 = 0.009;
pub const PENSION_FLOOR: f64 = 390_000.0;
pub const PENSION_CEILING: f64 = 6_170_000.0;

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct SocialInsuranceInput {
    pub taxable_pay: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub preset_national_pension: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub preset_health_insurance: Option<f64>,
    pub insurance_exempt: bool,
}

impl SocialInsuranceInput {
    pub const fn new(taxable_pay: f64) -> Self {
        Self {
            taxable_pay,
            preset_national_pension: None,
            preset_health_insurance: None,
            insurance_exempt: false,
        }
    }

    pub const fn with_preset_national_pension(mut self, amount: f64) -> Self {
        self.preset_national_pension = Some(amount);
        self
    }

    pub const fn with_preset_health_insurance(mut self, amount: f64) -> Self {
        self.preset_health_insurance = Some(amount);
        self
    }

    pub const fn with_insurance_exempt(mut self, insurance_exempt: bool) -> Self {
        self.insurance_exempt = insurance_exempt;
        self
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct SocialInsuranceResult {
    pub national_pension: i64,
    pub health_insurance: i64,
    pub long_term_care: i64,
    pub employment_insurance: i64,
    pub total: i64,
    pub insurance_exempt: bool,
}

pub fn calculate_social_insurance(input: SocialInsuranceInput) -> SocialInsuranceResult {
    let taxable = safe_number(input.taxable_pay);

    if input.insurance_exempt {
        return SocialInsuranceResult {
            national_pension: 0,
            health_insurance: 0,
            long_term_care: 0,
            employment_insurance: 0,
            total: 0,
            insurance_exempt: true,
        };
    }

    let national_pension = input
        .preset_national_pension
        .filter(|amount| *amount > 0.0)
        .map(round_won)
        .unwrap_or_else(|| {
            round_won(clamp(taxable, PENSION_FLOOR, PENSION_CEILING) * NATIONAL_PENSION_RATE)
        });

    let health_insurance = input
        .preset_health_insurance
        .filter(|amount| *amount > 0.0)
        .map(round_won)
        .unwrap_or_else(|| round_won(taxable * HEALTH_INSURANCE_RATE));

    let long_term_care = round_won(health_insurance as f64 * LONG_TERM_CARE_RATIO);
    let employment_insurance = calculate_employment_insurance(taxable);
    let total = national_pension + health_insurance + long_term_care + employment_insurance;

    SocialInsuranceResult {
        national_pension,
        health_insurance,
        long_term_care,
        employment_insurance,
        total,
        insurance_exempt: false,
    }
}

pub fn calculate_employment_insurance(taxable_total: f64) -> i64 {
    round_won_tens(safe_number(taxable_total) * EMPLOYMENT_INSURANCE_WORKER_RATE)
}

fn safe_number(value: f64) -> f64 {
    if value.is_finite() { value } else { 0.0 }
}

fn clamp(value: f64, low: f64, high: f64) -> f64 {
    value.max(low).min(high)
}

fn round_won(amount: f64) -> i64 {
    round_ties_even(amount) as i64
}

fn round_won_tens(amount: f64) -> i64 {
    round_ties_even(amount / 10.0) as i64 * 10
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

    #[test]
    fn calculates_python_compatible_social_insurance_from_taxable_pay() {
        let result = calculate_social_insurance(SocialInsuranceInput::new(3_000_000.0));

        assert_eq!(result.national_pension, 135_000);
        assert_eq!(result.health_insurance, 106_350);
        assert_eq!(result.long_term_care, 13_772);
        assert_eq!(result.employment_insurance, 27_000);
        assert_eq!(result.total, 282_122);
        assert!(!result.insurance_exempt);
    }

    #[test]
    fn pension_base_is_clamped_to_python_floor_and_ceiling() {
        assert_eq!(
            calculate_social_insurance(SocialInsuranceInput::new(100_000.0)).national_pension,
            17_550
        );
        assert_eq!(
            calculate_social_insurance(SocialInsuranceInput::new(7_000_000.0)).national_pension,
            277_650
        );
    }

    #[test]
    fn positive_presets_override_pension_and_health_then_recalculate_ltc() {
        let result = calculate_social_insurance(
            SocialInsuranceInput::new(3_000_000.0)
                .with_preset_national_pension(123_456.5)
                .with_preset_health_insurance(76_543.5),
        );

        assert_eq!(result.national_pension, 123_456);
        assert_eq!(result.health_insurance, 76_544);
        assert_eq!(result.long_term_care, 9_912);
        assert_eq!(result.employment_insurance, 27_000);
        assert_eq!(result.total, 236_912);
    }

    #[test]
    fn insurance_exempt_zeroes_all_worker_contributions() {
        let result = calculate_social_insurance(
            SocialInsuranceInput::new(3_000_000.0).with_insurance_exempt(true),
        );

        assert_eq!(result.national_pension, 0);
        assert_eq!(result.health_insurance, 0);
        assert_eq!(result.long_term_care, 0);
        assert_eq!(result.employment_insurance, 0);
        assert_eq!(result.total, 0);
        assert!(result.insurance_exempt);
    }

    #[test]
    fn employment_insurance_uses_python_compatible_tens_rounding() {
        assert_eq!(calculate_employment_insurance(4_640_000.0), 41_760);
        assert_eq!(calculate_employment_insurance(4_640_555.0), 41_760);
    }

    #[test]
    fn serializes_stable_contract_shape() {
        let result = calculate_social_insurance(SocialInsuranceInput::new(3_000_000.0));
        let value = serde_json::to_value(result).unwrap();

        assert_eq!(value["national_pension"], 135_000);
        assert_eq!(value["health_insurance"], 106_350);
        assert_eq!(value["long_term_care"], 13_772);
        assert_eq!(value["employment_insurance"], 27_000);
        assert_eq!(value["total"], 282_122);
        assert_eq!(value["insurance_exempt"], false);
    }
}
