use crate::error::PayrollApiError;
use crate::policy::{OperationPolicy, PayrollInputBasis};
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use serde_json::Value;
use std::{collections::BTreeMap, fmt, path::PathBuf, str::FromStr};

const SCOPE_SEPARATOR: char = '\u{1f}';

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PayrollScope {
    pub affiliate: String,
    pub workplace: String,
    pub period: String,
}

impl PayrollScope {
    pub fn new(
        affiliate: impl Into<String>,
        workplace: impl Into<String>,
        period: impl Into<String>,
    ) -> Result<Self, PayrollApiError> {
        let scope = Self {
            affiliate: affiliate.into().trim().to_owned(),
            workplace: workplace.into().trim().to_owned(),
            period: period.into().trim().to_owned(),
        };
        if !is_period(&scope.period) {
            return Err(PayrollApiError::InvalidPeriod {
                period: scope.period,
            });
        }
        Ok(scope)
    }

    pub fn parse_api(value: &str) -> Result<Self, PayrollApiError> {
        let value = value.trim();
        let separator = if value.contains(SCOPE_SEPARATOR) {
            SCOPE_SEPARATOR
        } else {
            '/'
        };
        let parts = value
            .splitn(3, separator)
            .map(str::trim)
            .collect::<Vec<_>>();
        if parts.len() != 3 || parts.iter().any(|part| part.is_empty()) {
            return Err(PayrollApiError::InvalidScope);
        }
        Self::new(parts[0], parts[1], parts[2])
    }

    pub fn key(&self) -> String {
        format!(
            "{}{}{}{}{}",
            self.affiliate, SCOPE_SEPARATOR, self.workplace, SCOPE_SEPARATOR, self.period
        )
    }

    pub fn display(&self) -> String {
        format!("{}/{}/{}", self.affiliate, self.workplace, self.period)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PayrollInputType {
    Auto,
    Invoice,
    Attendance,
    Mixed,
}

impl PayrollInputType {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Auto => "auto",
            Self::Invoice => "invoice",
            Self::Attendance => "attendance",
            Self::Mixed => "mixed",
        }
    }
}

impl Default for PayrollInputType {
    fn default() -> Self {
        Self::Auto
    }
}

impl fmt::Display for PayrollInputType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

impl FromStr for PayrollInputType {
    type Err = ();

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value.trim().to_ascii_lowercase().as_str() {
            "auto" => Ok(Self::Auto),
            "invoice" => Ok(Self::Invoice),
            "attendance" => Ok(Self::Attendance),
            "mixed" => Ok(Self::Mixed),
            _ => Err(()),
        }
    }
}

impl Serialize for PayrollInputType {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(self.as_str())
    }
}

impl<'de> Deserialize<'de> for PayrollInputType {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        value
            .parse()
            .map_err(|_| serde::de::Error::custom("invalid payroll input type"))
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct PayrollRunRequest {
    pub request_id: String,
    pub scope: PayrollScope,
    pub input_type: PayrollInputType,
    pub invoice_path: Option<PathBuf>,
    pub attendance_path: Option<PathBuf>,
    pub tenant_id: Option<String>,
    pub metadata: BTreeMap<String, Value>,
    pub validate_only: bool,
}

impl PayrollRunRequest {
    pub fn inferred_input_type(&self) -> PayrollInputType {
        match (&self.invoice_path, &self.attendance_path) {
            (Some(_), Some(_)) => PayrollInputType::Mixed,
            (None, Some(_)) => PayrollInputType::Attendance,
            _ => PayrollInputType::Invoice,
        }
    }

    pub fn resolved_input_type(&self, policy: &OperationPolicy) -> PayrollInputType {
        match self.input_type {
            PayrollInputType::Auto => match policy.input_basis {
                PayrollInputBasis::Attendance => PayrollInputType::Attendance,
                PayrollInputBasis::Invoice => PayrollInputType::Invoice,
                PayrollInputBasis::Hybrid => self.inferred_input_type(),
            },
            explicit => explicit,
        }
    }
}

#[derive(Debug, Deserialize)]
struct RawPayload {
    #[serde(default, alias = "requestId")]
    request_id: Option<Value>,
    #[serde(default)]
    scope: Option<Value>,
    #[serde(default)]
    affiliate: Option<Value>,
    #[serde(default)]
    workplace: Option<Value>,
    #[serde(default)]
    period: Option<Value>,
    #[serde(default, alias = "inputType")]
    input_type: Option<Value>,
    #[serde(default, alias = "invoicePath")]
    invoice_path: Option<Value>,
    #[serde(default, alias = "attendancePath")]
    attendance_path: Option<Value>,
    #[serde(default, alias = "tenantId")]
    tenant_id: Option<Value>,
    #[serde(default)]
    metadata: Option<Value>,
    #[serde(default, alias = "validateOnly", alias = "dry_run", alias = "dryRun")]
    validate_only: Option<Value>,
}

pub fn parse_payroll_api_request(payload: Value) -> Result<PayrollRunRequest, PayrollApiError> {
    if !payload.is_object() {
        return Err(PayrollApiError::InvalidPayload);
    }
    let mut raw = serde_json::from_value::<RawPayload>(payload)
        .map_err(|_| PayrollApiError::InvalidPayload)?;
    let metadata = metadata_map(raw.metadata.take());
    let request_id = text(raw.request_id.as_ref())
        .or_else(|| metadata_text(&metadata, "request_id"))
        .or_else(|| metadata_text(&metadata, "requestId"))
        .unwrap_or_default();
    let validate_only = raw.validate_only.as_ref().is_some_and(truthy)
        || metadata.get("validate_only").is_some_and(truthy)
        || metadata.get("validateOnly").is_some_and(truthy);
    let scope = scope_from_raw(&raw)?;
    let input_type = parse_input_type(raw.input_type.as_ref())?;
    let invoice_path = path_from_value(raw.invoice_path.as_ref());
    let attendance_path = path_from_value(raw.attendance_path.as_ref());

    validate_required_paths(input_type, invoice_path.as_ref(), attendance_path.as_ref())?;

    Ok(PayrollRunRequest {
        request_id,
        scope,
        input_type,
        invoice_path,
        attendance_path,
        tenant_id: text(raw.tenant_id.as_ref()),
        metadata,
        validate_only,
    })
}

pub fn request_id_from_payload(payload: &Value) -> String {
    let Some(object) = payload.as_object() else {
        return String::new();
    };
    let metadata = object
        .get("metadata")
        .and_then(Value::as_object)
        .map(|m| m.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
        .unwrap_or_else(BTreeMap::new);
    text(object.get("request_id"))
        .or_else(|| text(object.get("requestId")))
        .or_else(|| metadata_text(&metadata, "request_id"))
        .or_else(|| metadata_text(&metadata, "requestId"))
        .unwrap_or_default()
}

fn scope_from_raw(raw: &RawPayload) -> Result<PayrollScope, PayrollApiError> {
    if let Some(scope) = raw.scope.as_ref() {
        if let Some(scope) = text(Some(scope)) {
            return PayrollScope::parse_api(&scope);
        }
        let Some(scope) = scope.as_object() else {
            return Err(PayrollApiError::InvalidScope);
        };
        return scope_from_parts(
            text(scope.get("affiliate")),
            text(scope.get("workplace")),
            text(scope.get("period")),
        );
    }

    scope_from_parts(
        text(raw.affiliate.as_ref()),
        text(raw.workplace.as_ref()),
        text(raw.period.as_ref()),
    )
}

fn scope_from_parts(
    affiliate: Option<String>,
    workplace: Option<String>,
    period: Option<String>,
) -> Result<PayrollScope, PayrollApiError> {
    let mut missing = Vec::new();
    if affiliate.as_deref().unwrap_or_default().is_empty() {
        missing.push("affiliate".to_owned());
    }
    if workplace.as_deref().unwrap_or_default().is_empty() {
        missing.push("workplace".to_owned());
    }
    if period.as_deref().unwrap_or_default().is_empty() {
        missing.push("period".to_owned());
    }
    if !missing.is_empty() {
        return Err(PayrollApiError::MissingScopeFields {
            missing_fields: missing,
        });
    }
    PayrollScope::new(
        affiliate.unwrap_or_default(),
        workplace.unwrap_or_default(),
        period.unwrap_or_default(),
    )
}

fn parse_input_type(value: Option<&Value>) -> Result<PayrollInputType, PayrollApiError> {
    let input_type = text(value).unwrap_or_else(|| "auto".to_owned());
    input_type
        .parse()
        .map_err(|_| PayrollApiError::InvalidInputType { input_type })
}

fn validate_required_paths(
    input_type: PayrollInputType,
    invoice_path: Option<&PathBuf>,
    attendance_path: Option<&PathBuf>,
) -> Result<(), PayrollApiError> {
    let mut missing = Vec::new();
    match input_type {
        PayrollInputType::Auto if invoice_path.is_none() && attendance_path.is_none() => {
            missing.extend(["invoice_path".to_owned(), "attendance_path".to_owned()]);
        }
        PayrollInputType::Invoice if invoice_path.is_none() => {
            missing.push("invoice_path".to_owned());
        }
        PayrollInputType::Attendance if attendance_path.is_none() => {
            missing.push("attendance_path".to_owned());
        }
        PayrollInputType::Mixed => {
            if invoice_path.is_none() {
                missing.push("invoice_path".to_owned());
            }
            if attendance_path.is_none() {
                missing.push("attendance_path".to_owned());
            }
        }
        _ => {}
    }
    if missing.is_empty() {
        Ok(())
    } else {
        Err(PayrollApiError::MissingInputPath {
            input_type: input_type.to_string(),
            missing_fields: missing,
        })
    }
}

fn metadata_map(value: Option<Value>) -> BTreeMap<String, Value> {
    match value {
        Some(Value::Object(map)) => map.into_iter().collect(),
        _ => BTreeMap::new(),
    }
}

fn metadata_text(metadata: &BTreeMap<String, Value>, key: &str) -> Option<String> {
    text(metadata.get(key))
}

fn path_from_value(value: Option<&Value>) -> Option<PathBuf> {
    text(value).map(PathBuf::from)
}

fn text(value: Option<&Value>) -> Option<String> {
    let value = value?;
    let trimmed = match value {
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

fn truthy(value: &Value) -> bool {
    match value {
        Value::Bool(value) => *value,
        Value::Number(value) => value.as_f64().is_some_and(|n| n != 0.0),
        Value::String(value) => matches!(
            value.trim().to_ascii_lowercase().as_str(),
            "1" | "true" | "yes" | "y" | "on"
        ),
        Value::Null | Value::Array(_) | Value::Object(_) => false,
    }
}

fn is_period(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.len() == 7
        && bytes[4] == b'-'
        && bytes[..4].iter().all(u8::is_ascii_digit)
        && bytes[5..].iter().all(u8::is_ascii_digit)
}
