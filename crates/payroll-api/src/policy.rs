use serde::{Deserialize, Deserializer, Serialize, Serializer};
use serde_json::Value;
use std::{collections::BTreeMap, str::FromStr};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PayrollInputBasis {
    Invoice,
    Attendance,
    Hybrid,
}

impl PayrollInputBasis {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Invoice => "invoice",
            Self::Attendance => "attendance",
            Self::Hybrid => "hybrid",
        }
    }

    fn from_python_policy_value(value: Option<&Value>) -> Self {
        match text(value).as_deref() {
            Some("invoice") => Self::Invoice,
            Some("attendance") => Self::Attendance,
            Some("hybrid") => Self::Hybrid,
            _ => Self::Hybrid,
        }
    }
}

impl Default for PayrollInputBasis {
    fn default() -> Self {
        Self::Hybrid
    }
}

impl FromStr for PayrollInputBasis {
    type Err = ();

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value.trim().to_ascii_lowercase().as_str() {
            "invoice" => Ok(Self::Invoice),
            "attendance" => Ok(Self::Attendance),
            "hybrid" | "mixed" => Ok(Self::Hybrid),
            _ => Err(()),
        }
    }
}

impl Serialize for PayrollInputBasis {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

impl<'de> Deserialize<'de> for PayrollInputBasis {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        Ok(value.parse().unwrap_or_default())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MissingClockPolicy {
    Warn,
    Ignore,
    Deduct,
}

impl MissingClockPolicy {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Warn => "warn",
            Self::Ignore => "ignore",
            Self::Deduct => "deduct",
        }
    }

    fn from_python_policy_value(value: Option<&Value>) -> Self {
        match text(value).as_deref() {
            Some("ignore") => Self::Ignore,
            Some("deduct") => Self::Deduct,
            Some("warn") => Self::Warn,
            _ => Self::Warn,
        }
    }
}

impl Default for MissingClockPolicy {
    fn default() -> Self {
        Self::Warn
    }
}

impl FromStr for MissingClockPolicy {
    type Err = ();

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value.trim() {
            "warn" => Ok(Self::Warn),
            "ignore" => Ok(Self::Ignore),
            "deduct" => Ok(Self::Deduct),
            _ => Err(()),
        }
    }
}

impl Serialize for MissingClockPolicy {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

impl<'de> Deserialize<'de> for MissingClockPolicy {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        Ok(value.parse().unwrap_or_default())
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct AttendancePolicy {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_attendance_source")]
    pub source: String,
    #[serde(default = "default_one_minute")]
    pub rounding_minutes: i64,
    #[serde(default)]
    pub late_grace_minutes: i64,
    #[serde(default)]
    pub early_leave_grace_minutes: i64,
    #[serde(default = "default_one_minute")]
    pub overtime_rounding_minutes: i64,
    #[serde(default)]
    pub missing_clock_policy: MissingClockPolicy,
    #[serde(default = "default_holiday_source")]
    pub holiday_source: String,
    #[serde(flatten)]
    pub extra: BTreeMap<String, Value>,
}

impl Default for AttendancePolicy {
    fn default() -> Self {
        Self {
            enabled: true,
            source: default_attendance_source(),
            rounding_minutes: 1,
            late_grace_minutes: 0,
            early_leave_grace_minutes: 0,
            overtime_rounding_minutes: 1,
            missing_clock_policy: MissingClockPolicy::Warn,
            holiday_source: default_holiday_source(),
            extra: BTreeMap::new(),
        }
    }
}

impl AttendancePolicy {
    pub fn normalize(raw: Option<&Value>) -> Self {
        let base = Self::default();
        let Some(object) = raw.and_then(Value::as_object) else {
            return base;
        };
        Self {
            enabled: python_bool(object.get("enabled"), base.enabled),
            source: text(object.get("source")).unwrap_or(base.source),
            rounding_minutes: int_between(
                object.get("rounding_minutes"),
                base.rounding_minutes,
                1,
                60,
            ),
            late_grace_minutes: int_between(
                object.get("late_grace_minutes"),
                base.late_grace_minutes,
                0,
                240,
            ),
            early_leave_grace_minutes: int_between(
                object.get("early_leave_grace_minutes"),
                base.early_leave_grace_minutes,
                0,
                240,
            ),
            overtime_rounding_minutes: int_between(
                object.get("overtime_rounding_minutes"),
                base.overtime_rounding_minutes,
                1,
                60,
            ),
            missing_clock_policy: MissingClockPolicy::from_python_policy_value(
                object.get("missing_clock_policy"),
            ),
            holiday_source: text(object.get("holiday_source")).unwrap_or(base.holiday_source),
            extra: extra_fields(
                object,
                &[
                    "enabled",
                    "source",
                    "rounding_minutes",
                    "late_grace_minutes",
                    "early_leave_grace_minutes",
                    "overtime_rounding_minutes",
                    "missing_clock_policy",
                    "holiday_source",
                ],
            ),
        }
    }

    pub fn normalized(self) -> Self {
        let raw = serde_json::to_value(self).unwrap_or(Value::Null);
        Self::normalize(Some(&raw))
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct OperationPolicy {
    #[serde(default)]
    pub input_basis: PayrollInputBasis,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub payday: Option<String>,
    #[serde(default = "default_true")]
    pub show_setup_guide: bool,
    #[serde(default)]
    pub policy_note: String,
    #[serde(default)]
    pub attendance: AttendancePolicy,
    #[serde(flatten)]
    pub extra: BTreeMap<String, Value>,
}

impl Default for OperationPolicy {
    fn default() -> Self {
        Self {
            input_basis: PayrollInputBasis::Hybrid,
            payday: Some("25일".to_owned()),
            show_setup_guide: true,
            policy_note: String::new(),
            attendance: AttendancePolicy::default(),
            extra: BTreeMap::new(),
        }
    }
}

impl OperationPolicy {
    pub fn new(input_basis: PayrollInputBasis) -> Self {
        Self {
            input_basis,
            ..Self::default()
        }
    }

    pub fn with_payday(mut self, payday: impl Into<String>) -> Self {
        self.payday = Some(payday.into());
        self
    }

    pub fn normalize(raw: Value) -> Self {
        let base = Self::default();
        let Some(object) = raw.as_object() else {
            return base;
        };
        Self {
            input_basis: PayrollInputBasis::from_python_policy_value(object.get("input_basis")),
            payday: Some(text(object.get("payday")).unwrap_or_else(|| "25일".to_owned())),
            show_setup_guide: python_bool(object.get("show_setup_guide"), true),
            policy_note: text(object.get("policy_note")).unwrap_or_default(),
            attendance: AttendancePolicy::normalize(object.get("attendance")),
            extra: extra_fields(
                object,
                &[
                    "input_basis",
                    "payday",
                    "show_setup_guide",
                    "policy_note",
                    "attendance",
                ],
            ),
        }
    }

    pub fn normalized(self) -> Self {
        let raw = serde_json::to_value(self).unwrap_or(Value::Null);
        Self::normalize(raw)
    }
}

#[derive(Clone, Debug, Default, Deserialize, PartialEq, Serialize)]
pub struct OperationPolicySnapshot {
    #[serde(default)]
    pub policy: OperationPolicy,
    #[serde(default)]
    pub source: String,
}

impl OperationPolicySnapshot {
    pub fn new(policy: OperationPolicy, source: impl Into<String>) -> Self {
        Self {
            policy,
            source: source.into(),
        }
    }

    pub fn normalized(raw_policy: Value, source: impl Into<String>) -> Self {
        Self::new(OperationPolicy::normalize(raw_policy), source)
    }

    pub fn normalize(self) -> Self {
        Self {
            policy: self.policy.normalized(),
            source: self.source,
        }
    }
}

fn default_true() -> bool {
    true
}

fn default_one_minute() -> i64 {
    1
}

fn default_attendance_source() -> String {
    "biometric".to_owned()
}

fn default_holiday_source() -> String {
    "invoice".to_owned()
}

fn text(value: Option<&Value>) -> Option<String> {
    let trimmed = match value? {
        Value::Null => return None,
        Value::String(value) => value.trim().to_owned(),
        Value::Bool(value) => value.to_string(),
        Value::Number(value) => value.to_string(),
        Value::Array(_) | Value::Object(_) => return None,
    };
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed)
    }
}

fn python_bool(value: Option<&Value>, default: bool) -> bool {
    match value {
        None | Some(Value::Null) => default,
        Some(Value::Bool(value)) => *value,
        Some(Value::Number(value)) => value.as_f64().is_some_and(|number| number != 0.0),
        Some(Value::String(value)) => !value.is_empty(),
        Some(Value::Array(values)) => !values.is_empty(),
        Some(Value::Object(values)) => !values.is_empty(),
    }
}

fn int_between(value: Option<&Value>, default: i64, minimum: i64, maximum: i64) -> i64 {
    let parsed = match value {
        Some(Value::Number(value)) => value.as_f64(),
        Some(Value::String(value)) => value.parse::<f64>().ok(),
        Some(Value::Bool(value)) => Some(if *value { 1.0 } else { 0.0 }),
        Some(Value::Null | Value::Array(_) | Value::Object(_)) | None => None,
    }
    .map(|value| value as i64)
    .unwrap_or(default);

    parsed.clamp(minimum, maximum)
}

fn extra_fields(
    object: &serde_json::Map<String, Value>,
    known_fields: &[&str],
) -> BTreeMap<String, Value> {
    object
        .iter()
        .filter(|(key, _)| !known_fields.contains(&key.as_str()))
        .map(|(key, value)| (key.clone(), value.clone()))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn normalizes_invalid_policy_to_python_safe_defaults() {
        let policy = OperationPolicy::normalize(json!({
            "input_basis": "spreadsheet",
            "payday": "",
            "show_setup_guide": false,
            "policy_note": "  keep this note  ",
            "attendance": {
                "enabled": false,
                "source": " biometric-terminal ",
                "rounding_minutes": -10,
                "late_grace_minutes": 9999,
                "early_leave_grace_minutes": "bad",
                "overtime_rounding_minutes": 0,
                "missing_clock_policy": "bad",
                "holiday_source": " timesheet "
            }
        }));

        assert_eq!(policy.input_basis, PayrollInputBasis::Hybrid);
        assert_eq!(policy.payday.as_deref(), Some("25일"));
        assert!(!policy.show_setup_guide);
        assert_eq!(policy.policy_note, "keep this note");
        assert!(!policy.attendance.enabled);
        assert_eq!(policy.attendance.source, "biometric-terminal");
        assert_eq!(policy.attendance.rounding_minutes, 1);
        assert_eq!(policy.attendance.late_grace_minutes, 240);
        assert_eq!(policy.attendance.early_leave_grace_minutes, 0);
        assert_eq!(policy.attendance.overtime_rounding_minutes, 1);
        assert_eq!(
            policy.attendance.missing_clock_policy,
            MissingClockPolicy::Warn
        );
        assert_eq!(policy.attendance.holiday_source, "timesheet");
    }

    #[test]
    fn default_policy_serializes_python_compatible_shape() {
        let value = serde_json::to_value(OperationPolicy::default()).unwrap();

        assert_eq!(value["input_basis"], "hybrid");
        assert_eq!(value["payday"], "25일");
        assert_eq!(value["show_setup_guide"], true);
        assert_eq!(value["policy_note"], "");
        assert_eq!(value["attendance"]["enabled"], true);
        assert_eq!(value["attendance"]["source"], "biometric");
        assert_eq!(value["attendance"]["rounding_minutes"], 1);
        assert_eq!(value["attendance"]["late_grace_minutes"], 0);
        assert_eq!(value["attendance"]["early_leave_grace_minutes"], 0);
        assert_eq!(value["attendance"]["overtime_rounding_minutes"], 1);
        assert_eq!(value["attendance"]["missing_clock_policy"], "warn");
        assert_eq!(value["attendance"]["holiday_source"], "invoice");
    }

    #[test]
    fn preserves_unknown_extension_fields_after_normalization() {
        let policy = OperationPolicy::normalize(json!({
            "input_basis": "attendance",
            "legal_basis_id": "kr-lsa-2026",
            "attendance": {
                "missing_clock_policy": "deduct",
                "device_policy": "strict"
            }
        }));

        assert_eq!(policy.input_basis, PayrollInputBasis::Attendance);
        assert_eq!(policy.extra["legal_basis_id"], "kr-lsa-2026");
        assert_eq!(
            policy.attendance.missing_clock_policy,
            MissingClockPolicy::Deduct
        );
        assert_eq!(policy.attendance.extra["device_policy"], "strict");
    }
}
