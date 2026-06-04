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

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct OperationPolicy {
    #[serde(default)]
    pub input_basis: PayrollInputBasis,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub payday: Option<String>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub attendance: BTreeMap<String, Value>,
    #[serde(flatten)]
    pub extra: BTreeMap<String, Value>,
}

impl Default for OperationPolicy {
    fn default() -> Self {
        Self {
            input_basis: PayrollInputBasis::Hybrid,
            payday: Some("25일".to_owned()),
            attendance: BTreeMap::new(),
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
}
