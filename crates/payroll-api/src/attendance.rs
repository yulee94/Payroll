use crate::policy::AttendancePolicy;
use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Clone, Debug, Default, PartialEq, Serialize)]
pub struct AttendanceSourceRecord {
    pub name: String,
    pub name_key: String,
    pub dept: String,
    pub workplace: String,
    pub work_hours: f64,
    pub late_hours: f64,
    pub early_leave_hours: f64,
    pub overtime_hours: f64,
    pub night_hours: f64,
    pub special_hours: f64,
    pub leave_days: f64,
    pub unpaid_days: f64,
}

impl AttendanceSourceRecord {
    pub fn new(name: impl Into<String>) -> Self {
        let name = clean(name);
        Self {
            name_key: normalized_name_key(&name),
            name,
            ..Self::default()
        }
    }

    pub fn with_name_key(mut self, name_key: impl Into<String>) -> Self {
        self.name_key = clean(name_key);
        self
    }

    pub fn with_dept(mut self, dept: impl Into<String>) -> Self {
        self.dept = clean(dept);
        self
    }

    pub fn with_workplace(mut self, workplace: impl Into<String>) -> Self {
        self.workplace = clean(workplace);
        self
    }

    pub fn with_work_hours(mut self, hours: f64) -> Self {
        self.work_hours = hours;
        self
    }

    pub fn with_late_hours(mut self, hours: f64) -> Self {
        self.late_hours = hours;
        self
    }

    pub fn with_early_leave_hours(mut self, hours: f64) -> Self {
        self.early_leave_hours = hours;
        self
    }

    pub fn with_overtime_hours(mut self, hours: f64) -> Self {
        self.overtime_hours = hours;
        self
    }

    pub fn with_night_hours(mut self, hours: f64) -> Self {
        self.night_hours = hours;
        self
    }

    pub fn with_special_hours(mut self, hours: f64) -> Self {
        self.special_hours = hours;
        self
    }

    pub fn with_leave_days(mut self, days: f64) -> Self {
        self.leave_days = days;
        self
    }

    pub fn with_unpaid_days(mut self, days: f64) -> Self {
        self.unpaid_days = days;
        self
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct AttendanceInvoiceRow {
    pub row: u64,
    pub name: String,
    pub dept: String,
    pub hire_date: String,
    pub workplace: String,
    pub base_hourly: f64,
    pub ordinary_hourly: f64,
    pub base_days: f64,
    pub work_days: f64,
    pub unpaid_days: f64,
    pub leave_days: f64,
    pub ot_hours: f64,
    pub shift_hours: f64,
    pub night_hours: f64,
    pub special_hours: f64,
    pub special_ext_hours: f64,
    pub early_leave_hours: f64,
    pub base_salary: i64,
    pub base_deduction: i64,
    pub ot_pay: i64,
    pub night_pay: i64,
    pub special_pay: i64,
    pub special_ext_pay: i64,
    pub position_pay: i64,
    pub shift_pay: i64,
    pub workers_day_pay: i64,
    pub annual_pay: i64,
    pub transport: i64,
    pub subtotal: i64,
    pub gross_pay: i64,
    pub health_insurance: i64,
    pub long_term_care: i64,
    pub national_pension: i64,
    pub employment_insurance: i64,
    pub insurance_total: i64,
    #[serde(rename = "_attendance_days")]
    pub attendance_days: u64,
    #[serde(rename = "_attendance_input")]
    pub attendance_input: bool,
}

pub fn aggregate_attendance_records<I, S>(
    records: I,
    workplace: S,
    policy: &AttendancePolicy,
) -> Vec<AttendanceInvoiceRow>
where
    I: IntoIterator<Item = AttendanceSourceRecord>,
    S: Into<String>,
{
    let workplace = clean(workplace);
    let policy = policy.clone().normalized();
    let mut grouped: BTreeMap<String, GroupedAttendance> = BTreeMap::new();

    for record in records {
        let key = attendance_key(&record);
        if key.is_empty() {
            continue;
        }
        let item = grouped.entry(key).or_insert_with(|| GroupedAttendance {
            name: record.name.clone(),
            dept: record.dept.clone(),
            workplace: if record.workplace.is_empty() {
                workplace.clone()
            } else {
                record.workplace.clone()
            },
            ..GroupedAttendance::default()
        });

        item.work_hours += record.work_hours.max(0.0);
        if record.late_hours * 60.0 > policy.late_grace_minutes as f64 {
            item.late_hours +=
                (record.late_hours - policy.late_grace_minutes as f64 / 60.0).max(0.0);
        }
        if record.early_leave_hours * 60.0 > policy.early_leave_grace_minutes as f64 {
            item.early_leave_hours += (record.early_leave_hours
                - policy.early_leave_grace_minutes as f64 / 60.0)
                .max(0.0);
        }
        item.overtime_hours += record.overtime_hours;
        item.night_hours += record.night_hours;
        item.special_hours += record.special_hours;
        item.leave_days += record.leave_days;
        item.unpaid_days += record.unpaid_days;
        item.attendance_days += 1;
    }

    let mut rows = grouped
        .into_values()
        .map(|item| invoice_row(item, policy.rounding_minutes))
        .collect::<Vec<_>>();
    rows.sort_by(|left, right| left.name.cmp(&right.name));
    rows
}

#[derive(Clone, Debug, Default, PartialEq)]
struct GroupedAttendance {
    name: String,
    dept: String,
    workplace: String,
    work_hours: f64,
    late_hours: f64,
    early_leave_hours: f64,
    overtime_hours: f64,
    night_hours: f64,
    special_hours: f64,
    leave_days: f64,
    unpaid_days: f64,
    attendance_days: u64,
}

fn invoice_row(item: GroupedAttendance, rounding_minutes: i64) -> AttendanceInvoiceRow {
    let work_hours = round_hours(item.work_hours, rounding_minutes);
    AttendanceInvoiceRow {
        row: 0,
        name: item.name,
        dept: item.dept,
        hire_date: String::new(),
        workplace: item.workplace,
        base_hourly: 0.0,
        ordinary_hourly: 0.0,
        base_days: work_hours,
        work_days: work_hours,
        unpaid_days: item.unpaid_days,
        leave_days: item.leave_days,
        ot_hours: round_hours(item.overtime_hours, rounding_minutes),
        shift_hours: 0.0,
        night_hours: round_hours(item.night_hours, rounding_minutes),
        special_hours: round_hours(item.special_hours, rounding_minutes),
        special_ext_hours: 0.0,
        early_leave_hours: round_hours(item.early_leave_hours + item.late_hours, rounding_minutes),
        base_salary: 0,
        base_deduction: 0,
        ot_pay: 0,
        night_pay: 0,
        special_pay: 0,
        special_ext_pay: 0,
        position_pay: 0,
        shift_pay: 0,
        workers_day_pay: 0,
        annual_pay: 0,
        transport: 0,
        subtotal: 0,
        gross_pay: 0,
        health_insurance: 0,
        long_term_care: 0,
        national_pension: 0,
        employment_insurance: 0,
        insurance_total: 0,
        attendance_days: item.attendance_days,
        attendance_input: true,
    }
}

fn attendance_key(record: &AttendanceSourceRecord) -> String {
    let key = clean(&record.name_key);
    if key.is_empty() {
        normalized_name_key(&record.name)
    } else {
        key
    }
}

fn round_hours(hours: f64, rounding_minutes: i64) -> f64 {
    if hours <= 0.0 {
        return 0.0;
    }
    let unit = rounding_minutes.max(1) as f64;
    let rounded_minutes = round_ties_even(hours * 60.0 / unit) * unit;
    round_decimal_places(rounded_minutes / 60.0, 4)
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

fn normalized_name_key(value: &str) -> String {
    value.chars().filter(|ch| !ch.is_whitespace()).collect()
}

fn clean(value: impl Into<String>) -> String {
    value.into().trim().to_owned()
}

#[cfg(test)]
mod tests {
    use crate::attendance::{AttendanceSourceRecord, aggregate_attendance_records};
    use crate::policy::AttendancePolicy;
    use crate::service::{PayrollApiService, ServiceConfig};

    fn grouped_records() -> Vec<AttendanceSourceRecord> {
        vec![
            AttendanceSourceRecord::new("홍 길동")
                .with_dept("Payroll")
                .with_workplace("Site A")
                .with_work_hours(4.0)
                .with_late_hours(10.0 / 60.0)
                .with_overtime_hours(0.5)
                .with_night_hours(1.0),
            AttendanceSourceRecord::new("홍길동")
                .with_name_key("홍길동")
                .with_dept("Payroll")
                .with_workplace("Site A")
                .with_work_hours(4.0)
                .with_early_leave_hours(5.0 / 60.0)
                .with_overtime_hours(0.5)
                .with_special_hours(2.0)
                .with_leave_days(1.0)
                .with_unpaid_days(0.5),
        ]
    }

    #[test]
    fn aggregates_rows_by_normalized_name_with_grace_and_rounding() {
        let policy = AttendancePolicy {
            rounding_minutes: 15,
            late_grace_minutes: 5,
            early_leave_grace_minutes: 0,
            ..AttendancePolicy::default()
        };

        let rows = aggregate_attendance_records(grouped_records(), "Site A", &policy);
        let value = serde_json::to_value(&rows[0]).unwrap();

        assert_eq!(rows.len(), 1);
        let row = &rows[0];
        assert_eq!(row.name, "홍 길동");
        assert_eq!(row.dept, "Payroll");
        assert_eq!(row.workplace, "Site A");
        assert_eq!(row.attendance_days, 2);
        assert!(row.attendance_input);
        assert_eq!(row.work_days, 8.0);
        assert_eq!(row.early_leave_hours, 0.25);
        assert_eq!(row.ot_hours, 1.0);
        assert_eq!(row.night_hours, 1.0);
        assert_eq!(row.special_hours, 2.0);
        assert_eq!(row.leave_days, 1.0);
        assert_eq!(row.unpaid_days, 0.5);
        assert_eq!(row.subtotal, 0);
        assert_eq!(value["_attendance_days"], 2);
        assert_eq!(value["_attendance_input"], true);
        assert_eq!(value["base_salary"], 0);
    }

    #[test]
    fn sorts_invoice_rows_by_employee_name() {
        let rows = aggregate_attendance_records(
            vec![
                AttendanceSourceRecord::new("Charlie").with_work_hours(1.0),
                AttendanceSourceRecord::new("Alice").with_work_hours(1.0),
            ],
            "HQ",
            &AttendancePolicy::default(),
        );

        assert_eq!(
            rows.iter().map(|row| row.name.as_str()).collect::<Vec<_>>(),
            vec!["Alice", "Charlie"]
        );
    }

    #[test]
    fn uses_python_compatible_half_even_rounding() {
        let policy = AttendancePolicy {
            rounding_minutes: 10,
            ..AttendancePolicy::default()
        };
        let rows = aggregate_attendance_records(
            vec![AttendanceSourceRecord::new("Half Even").with_work_hours(5.0 / 60.0)],
            "HQ",
            &policy,
        );

        assert_eq!(rows[0].work_days, 0.0);
    }

    #[test]
    fn service_delegates_attendance_aggregation() {
        let service = PayrollApiService::new(ServiceConfig::default());
        let policy = AttendancePolicy {
            rounding_minutes: 15,
            late_grace_minutes: 5,
            ..AttendancePolicy::default()
        };

        let rows = service.aggregate_attendance_records(grouped_records(), "Site A", &policy);

        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0].work_days, 8.0);
        assert_eq!(rows[0].attendance_days, 2);
    }
}
