use serde::Serialize;

const SIMPLIFIED_TAX_TABLE: &[(i64, i64)] = &[
    (1_060_000, 0),
    (1_500_000, 8_000),
    (2_000_000, 42_000),
    (2_500_000, 120_000),
    (3_000_000, 210_000),
    (3_500_000, 310_000),
    (4_000_000, 420_000),
    (5_000_000, 650_000),
    (6_000_000, 920_000),
    (8_000_000, 1_450_000),
    (10_000_000, 2_100_000),
];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PayrollTaxMethod {
    Preset,
    SimplifiedTable,
}

impl PayrollTaxMethod {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Preset => "preset",
            Self::SimplifiedTable => "simplified_table",
        }
    }
}

impl Serialize for PayrollTaxMethod {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollDeductionInput {
    pub gross_pay: i64,
    pub insurance_total: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub preset_income_tax: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub preset_local_income_tax: Option<i64>,
    pub identity_guarantee_insurance_deduction: i64,
}

impl PayrollDeductionInput {
    pub const fn new(gross_pay: i64, insurance_total: i64) -> Self {
        Self {
            gross_pay,
            insurance_total,
            preset_income_tax: None,
            preset_local_income_tax: None,
            identity_guarantee_insurance_deduction: 0,
        }
    }

    pub fn with_preset_income_tax(mut self, amount: i64) -> Self {
        self.preset_income_tax = Some(amount);
        self
    }

    pub fn with_preset_local_income_tax(mut self, amount: i64) -> Self {
        self.preset_local_income_tax = Some(amount);
        self
    }

    pub const fn with_identity_guarantee_insurance_deduction(mut self, amount: i64) -> Self {
        self.identity_guarantee_insurance_deduction = amount;
        self
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollIncomeTaxResult {
    pub income_tax: i64,
    pub local_income_tax: i64,
    pub total: i64,
    pub method: PayrollTaxMethod,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollDeductionResult {
    pub gross_pay: i64,
    pub insurance_total: i64,
    pub taxable_pay: i64,
    pub income_tax: i64,
    pub local_income_tax: i64,
    pub tax_total: i64,
    pub identity_guarantee_insurance_deduction: i64,
    pub total_deduction: i64,
    pub net_pay: i64,
    pub method: PayrollTaxMethod,
}

pub fn lookup_simplified_income_tax(monthly_taxable: i64) -> i64 {
    for (upper_bound, tax) in SIMPLIFIED_TAX_TABLE {
        if monthly_taxable <= *upper_bound {
            return *tax;
        }
    }
    round_won(((monthly_taxable - 1_500_000).max(0) as f64) * 0.03)
}

pub fn calculate_payroll_income_tax(
    taxable_pay: i64,
    preset_income_tax: Option<i64>,
    preset_local_income_tax: Option<i64>,
) -> PayrollIncomeTaxResult {
    let (income_tax, method) = if let Some(amount) = preset_income_tax.filter(|amount| *amount > 0)
    {
        (amount, PayrollTaxMethod::Preset)
    } else {
        (
            lookup_simplified_income_tax(taxable_pay),
            PayrollTaxMethod::SimplifiedTable,
        )
    };

    let local_income_tax = if method == PayrollTaxMethod::Preset {
        preset_local_income_tax
            .filter(|amount| *amount > 0)
            .unwrap_or_else(|| round_won_tens(income_tax as f64 * 0.10))
    } else {
        round_won(income_tax as f64 * 0.10)
    };

    PayrollIncomeTaxResult {
        income_tax,
        local_income_tax,
        total: income_tax + local_income_tax,
        method,
    }
}

pub fn finalize_payroll_deductions(input: PayrollDeductionInput) -> PayrollDeductionResult {
    let taxable_pay = input.gross_pay - input.insurance_total;
    let tax = calculate_payroll_income_tax(
        taxable_pay,
        input.preset_income_tax,
        input.preset_local_income_tax,
    );
    let identity_deduction = input.identity_guarantee_insurance_deduction;
    let total_deduction = input.insurance_total + tax.total + identity_deduction.abs();
    let net_pay = round_won((input.gross_pay - total_deduction) as f64);

    PayrollDeductionResult {
        gross_pay: input.gross_pay,
        insurance_total: input.insurance_total,
        taxable_pay,
        income_tax: tax.income_tax,
        local_income_tax: tax.local_income_tax,
        tax_total: tax.total,
        identity_guarantee_insurance_deduction: identity_deduction,
        total_deduction,
        net_pay,
        method: tax.method,
    }
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
    fn simplified_tax_table_matches_python_brackets() {
        assert_eq!(lookup_simplified_income_tax(-100_000), 0);
        assert_eq!(lookup_simplified_income_tax(1_060_000), 0);
        assert_eq!(lookup_simplified_income_tax(1_060_001), 8_000);
        assert_eq!(lookup_simplified_income_tax(3_000_000), 210_000);
        assert_eq!(lookup_simplified_income_tax(10_500_000), 270_000);
    }

    #[test]
    fn finalizes_simplified_tax_deductions_and_net_pay() {
        let result = finalize_payroll_deductions(PayrollDeductionInput::new(3_000_000, 300_000));

        assert_eq!(result.taxable_pay, 2_700_000);
        assert_eq!(result.income_tax, 210_000);
        assert_eq!(result.local_income_tax, 21_000);
        assert_eq!(result.tax_total, 231_000);
        assert_eq!(result.total_deduction, 531_000);
        assert_eq!(result.net_pay, 2_469_000);
        assert_eq!(result.method, PayrollTaxMethod::SimplifiedTable);
    }

    #[test]
    fn preset_income_tax_uses_tens_rounded_local_tax_when_local_absent() {
        let result = finalize_payroll_deductions(
            PayrollDeductionInput::new(4_000_000, 450_000).with_preset_income_tax(123_456),
        );

        assert_eq!(result.income_tax, 123_456);
        assert_eq!(result.local_income_tax, 12_350);
        assert_eq!(result.method, PayrollTaxMethod::Preset);
    }

    #[test]
    fn preset_local_tax_overrides_auto_local_tax() {
        let result = finalize_payroll_deductions(
            PayrollDeductionInput::new(4_000_000, 450_000)
                .with_preset_income_tax(123_456)
                .with_preset_local_income_tax(7_777),
        );

        assert_eq!(result.income_tax, 123_456);
        assert_eq!(result.local_income_tax, 7_777);
    }

    #[test]
    fn identity_guarantee_deduction_uses_absolute_amount() {
        let result = finalize_payroll_deductions(
            PayrollDeductionInput::new(3_000_000, 300_000)
                .with_identity_guarantee_insurance_deduction(-20_000),
        );

        assert_eq!(result.identity_guarantee_insurance_deduction, -20_000);
        assert_eq!(result.total_deduction, 551_000);
        assert_eq!(result.net_pay, 2_449_000);
    }

    #[test]
    fn serializes_stable_contract_shape() {
        let result = finalize_payroll_deductions(
            PayrollDeductionInput::new(3_000_000, 300_000)
                .with_identity_guarantee_insurance_deduction(-20_000),
        );
        let value = serde_json::to_value(result).unwrap();

        assert_eq!(value["method"], "simplified_table");
        assert_eq!(value["taxable_pay"], 2_700_000);
        assert_eq!(value["total_deduction"], 551_000);
        assert_eq!(value["net_pay"], 2_449_000);
    }
}
