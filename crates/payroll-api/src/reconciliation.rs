use crate::deductions::{PayrollDeductionInput, PayrollTaxMethod, finalize_payroll_deductions};
use serde::Serialize;

/// One worker's source-ledger figures, as imported into `payroll_input`
/// (`gross_pay`, `deduction_total`, and the `source_payload` breakdown).
///
/// The component breakdown lets the reconciliation engine reconstruct the
/// statutory insurance total (`national_pension + health_insurance +
/// employment_insurance`) and feed the ledger's preset income/local tax back
/// into [`finalize_payroll_deductions`].
#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct LedgerWorker {
    pub employee_key: String,
    pub name: String,
    pub gross: i64,
    pub income_tax: i64,
    pub local_income_tax: i64,
    pub health_insurance: i64,
    pub national_pension: i64,
    pub employment_insurance: i64,
    pub total_deductions: i64,
    pub net: i64,
}

impl LedgerWorker {
    /// Statutory insurance total fed into the deduction engine
    /// (the engine treats income/local tax separately from insurance).
    pub fn insurance_total(&self) -> i64 {
        self.national_pension + self.health_insurance + self.employment_insurance
    }

    /// Sum of every recorded component. For a self-consistent ledger this
    /// equals `total_deductions`.
    pub fn component_sum(&self) -> i64 {
        self.income_tax
            + self.local_income_tax
            + self.health_insurance
            + self.national_pension
            + self.employment_insurance
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct WorkerReconciliation {
    pub employee_key: String,
    pub name: String,
    pub gross: i64,
    pub source_deductions: i64,
    pub source_net: i64,
    /// Net recomputed by the engine in PRESET mode (ledger tax + insurance fed
    /// back in). This is the integrity round-trip and must match exactly.
    pub computed_net: i64,
    pub net_match: bool,
    /// Income + local tax recorded on the ledger.
    pub source_tax: i64,
    /// Income + local tax the engine derives from the 간이세액표 with no presets.
    pub recomputed_tax: i64,
    /// `recomputed_tax - source_tax`. Reported honestly; never forced to zero.
    pub tax_variance: i64,
    pub recomputed_income_tax: i64,
    pub recomputed_local_income_tax: i64,
    pub recompute_method: PayrollTaxMethod,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ReconciliationTotals {
    pub gross: i64,
    pub total_deductions: i64,
    pub net: i64,
    pub workers: u64,
    pub net_match_count: u64,
    pub all_net_match: bool,
    pub source_tax: i64,
    pub recomputed_tax: i64,
    pub tax_variance: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ReconciliationReport {
    pub period: String,
    pub workers: Vec<WorkerReconciliation>,
    pub totals: ReconciliationTotals,
}

/// Reconcile one worker against the source ledger.
///
/// PRESET mode round-trips the ledger's own insurance total + preset
/// income/local tax through [`finalize_payroll_deductions`] and asserts the
/// engine reproduces the ledger net.
///
/// RECOMPUTE mode runs the same engine with no presets so the 간이세액표 +
/// local 10% path computes income tax from scratch; the variance versus the
/// ledger tax is recorded as-is.
pub fn reconcile_worker(worker: &LedgerWorker) -> WorkerReconciliation {
    let insurance_total = worker.insurance_total();

    let preset = finalize_payroll_deductions(
        PayrollDeductionInput::new(worker.gross, insurance_total)
            .with_preset_income_tax(worker.income_tax)
            .with_preset_local_income_tax(worker.local_income_tax),
    );

    let recompute =
        finalize_payroll_deductions(PayrollDeductionInput::new(worker.gross, insurance_total));

    let source_tax = worker.income_tax + worker.local_income_tax;
    let recomputed_tax = recompute.tax_total;

    WorkerReconciliation {
        employee_key: worker.employee_key.clone(),
        name: worker.name.clone(),
        gross: worker.gross,
        source_deductions: worker.total_deductions,
        source_net: worker.net,
        computed_net: preset.net_pay,
        net_match: preset.net_pay == worker.net,
        source_tax,
        recomputed_tax,
        tax_variance: recomputed_tax - source_tax,
        recomputed_income_tax: recompute.income_tax,
        recomputed_local_income_tax: recompute.local_income_tax,
        recompute_method: recompute.method,
    }
}

/// Reconcile an entire period and aggregate the totals.
pub fn reconcile_period(period: impl Into<String>, ledger: &[LedgerWorker]) -> ReconciliationReport {
    let workers: Vec<WorkerReconciliation> = ledger.iter().map(reconcile_worker).collect();

    let mut totals = ReconciliationTotals {
        gross: 0,
        total_deductions: 0,
        net: 0,
        workers: workers.len() as u64,
        net_match_count: 0,
        all_net_match: true,
        source_tax: 0,
        recomputed_tax: 0,
        tax_variance: 0,
    };

    for worker in &workers {
        totals.gross += worker.gross;
        totals.total_deductions += worker.source_deductions;
        totals.net += worker.source_net;
        totals.source_tax += worker.source_tax;
        totals.recomputed_tax += worker.recomputed_tax;
        if worker.net_match {
            totals.net_match_count += 1;
        } else {
            totals.all_net_match = false;
        }
    }
    totals.tax_variance = totals.recomputed_tax - totals.source_tax;

    ReconciliationReport {
        period: period.into(),
        workers,
        totals,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Synthetic worker — NOT real PII. Mirrors the self-consistent ledger
    // identity (net = gross - total_deductions, components sum to total).
    fn synthetic_worker(employee_key: &str) -> LedgerWorker {
        LedgerWorker {
            employee_key: employee_key.to_owned(),
            name: "Synthetic Worker".to_owned(),
            gross: 3_000_000,
            income_tax: 84_850,
            local_income_tax: 8_480,
            health_insurance: 106_350,
            national_pension: 135_000,
            employment_insurance: 27_000,
            total_deductions: 361_680,
            net: 2_638_320,
        }
    }

    #[test]
    fn synthetic_fixture_satisfies_net_identity() {
        let worker = synthetic_worker("employee-synthetic-1");
        assert_eq!(worker.net, worker.gross - worker.total_deductions);
        assert_eq!(worker.component_sum(), worker.total_deductions);
    }

    #[test]
    fn preset_mode_reproduces_ledger_net_exactly() {
        let worker = synthetic_worker("employee-synthetic-1");
        let reconciliation = reconcile_worker(&worker);

        assert_eq!(reconciliation.computed_net, worker.net);
        assert!(reconciliation.net_match);
        assert_eq!(reconciliation.source_net, worker.net);
    }

    #[test]
    fn recompute_mode_reports_tax_variance_without_forcing_match() {
        let worker = synthetic_worker("employee-synthetic-1");
        let reconciliation = reconcile_worker(&worker);

        // taxable = 3,000,000 - (135,000 + 106,350 + 27,000) = 2,731,650.
        // 간이세액표 bracket (<= 3,000,000) => 210,000 income tax, +10% local.
        assert_eq!(reconciliation.recompute_method, PayrollTaxMethod::SimplifiedTable);
        assert_eq!(reconciliation.recomputed_income_tax, 210_000);
        assert_eq!(reconciliation.recomputed_local_income_tax, 21_000);
        assert_eq!(reconciliation.recomputed_tax, 231_000);
        assert_eq!(reconciliation.source_tax, 84_850 + 8_480);
        // Variance is the honest difference, not zero.
        assert_eq!(
            reconciliation.tax_variance,
            reconciliation.recomputed_tax - reconciliation.source_tax
        );
        assert_ne!(reconciliation.tax_variance, 0);
    }

    #[test]
    fn period_totals_aggregate_and_flag_all_net_match() {
        let ledger = vec![
            synthetic_worker("employee-synthetic-1"),
            synthetic_worker("employee-synthetic-2"),
        ];
        let report = reconcile_period("2026-05", &ledger);

        assert_eq!(report.period, "2026-05");
        assert_eq!(report.totals.workers, 2);
        assert_eq!(report.totals.net_match_count, 2);
        assert!(report.totals.all_net_match);
        assert_eq!(report.totals.gross, 6_000_000);
        assert_eq!(report.totals.total_deductions, 723_360);
        assert_eq!(report.totals.net, 5_276_640);
    }

    #[test]
    fn net_mismatch_is_reported_when_ledger_net_is_inconsistent() {
        let mut worker = synthetic_worker("employee-synthetic-1");
        // Corrupt the recorded net so it no longer matches gross - deductions.
        worker.net += 1;
        let reconciliation = reconcile_worker(&worker);

        assert!(!reconciliation.net_match);
        assert_ne!(reconciliation.computed_net, reconciliation.source_net);

        let report = reconcile_period("2026-05", &[worker]);
        assert!(!report.totals.all_net_match);
        assert_eq!(report.totals.net_match_count, 0);
    }
}
