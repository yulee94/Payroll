use serde_json::{json, Value};
use std::{error::Error, fmt};

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PayrollApiError {
    InvalidPayload,
    InvalidScope,
    MissingScopeFields {
        missing_fields: Vec<String>,
    },
    InvalidPeriod {
        period: String,
    },
    InvalidInputType {
        input_type: String,
    },
    MissingInputPath {
        input_type: String,
        missing_fields: Vec<String>,
    },
}

impl PayrollApiError {
    pub fn code(&self) -> &'static str {
        match self {
            Self::InvalidPayload => "invalid_payload",
            Self::InvalidScope => "invalid_scope",
            Self::MissingScopeFields { .. } => "missing_scope_fields",
            Self::InvalidPeriod { .. } => "invalid_period",
            Self::InvalidInputType { .. } => "invalid_input_type",
            Self::MissingInputPath { .. } => "missing_input_path",
        }
    }

    pub fn details(&self) -> Value {
        match self {
            Self::InvalidPayload => json!({ "expected": "object" }),
            Self::InvalidScope => json!({
                "accepted_forms": ["affiliate/workplace/YYYY-MM", "scope object"]
            }),
            Self::MissingScopeFields { missing_fields } => {
                json!({ "missing_fields": missing_fields })
            }
            Self::InvalidPeriod { period } => {
                json!({ "period": period, "period_format": "YYYY-MM" })
            }
            Self::InvalidInputType { input_type } => json!({
                "input_type": input_type,
                "allowed_input_types": ["auto", "invoice", "attendance", "mixed"]
            }),
            Self::MissingInputPath {
                input_type,
                missing_fields,
            } => json!({
                "input_type": input_type,
                "missing_fields": missing_fields,
                "accepted_aliases": {
                    "invoice_path": ["invoice_path", "invoicePath"],
                    "attendance_path": ["attendance_path", "attendancePath"]
                }
            }),
        }
    }
}

impl fmt::Display for PayrollApiError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidPayload => write!(f, "급여 자동화 요청은 JSON object 형태여야 합니다."),
            Self::InvalidScope => write!(f, "scope는 문자열 또는 객체 형태여야 합니다."),
            Self::MissingScopeFields { missing_fields } => {
                write!(f, "scope 필드가 부족합니다: {}", missing_fields.join(", "))
            }
            Self::InvalidPeriod { .. } => write!(f, "period는 YYYY-MM 형식이어야 합니다."),
            Self::InvalidInputType { input_type } => {
                write!(f, "지원하지 않는 급여 입력 방식입니다: {input_type}")
            }
            Self::MissingInputPath { missing_fields, .. } => {
                write!(
                    f,
                    "급여 입력 파일 경로가 부족합니다: {}",
                    missing_fields.join(", ")
                )
            }
        }
    }
}

impl Error for PayrollApiError {}
