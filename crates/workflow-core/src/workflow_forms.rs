use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const DOC_TYPE_GENERAL: &str = "GENERAL_DRAFT";
pub const DOC_TYPE_ATTENDANCE: &str = "ATTENDANCE_REQUEST";
pub const DOC_TYPE_PURCHASE: &str = "PURCHASE_REQUEST";
pub const DOC_TYPE_EXPENSE: &str = "EXPENSE_REPORT";
pub const DOC_TYPE_CLOSING: &str = "CLOSING_REPORT";
pub const DOC_TYPE_BUSINESS_TRIP_REQUEST: &str = "BUSINESS_TRIP_REQUEST";

pub const WORKFLOW_FORM_DOCUMENT_TYPES: [&str; 6] = [
    DOC_TYPE_GENERAL,
    DOC_TYPE_ATTENDANCE,
    DOC_TYPE_PURCHASE,
    DOC_TYPE_EXPENSE,
    DOC_TYPE_CLOSING,
    DOC_TYPE_BUSINESS_TRIP_REQUEST,
];

pub const ATTENDANCE_TYPE_LABELS: [(&str, &str); 10] = [
    ("annual_leave", "연차"),
    ("half_day_morning", "오전 반차"),
    ("half_day_afternoon", "오후 반차"),
    ("early_leave", "조퇴"),
    ("outside_work", "외근"),
    ("business_trip", "출장"),
    ("overtime", "야근"),
    ("holiday_work", "특근"),
    ("sick_leave", "병가"),
    ("other", "기타"),
];

const EXPENSE_CATEGORIES: [&str; 5] = ["법인카드", "현금·영수증", "경비정산", "출장비", "기타"];
const BUSINESS_TRIP_TRANSPORT_OPTIONS: [&str; 6] =
    ["대중교통", "법인차량", "개인차량", "항공", "기차", "기타"];

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowFormFieldDef {
    pub key: String,
    pub label: String,
    pub field_type: String,
    pub required: bool,
    pub options: Vec<String>,
    pub placeholder: String,
    pub maps_to: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowDocumentFields {
    pub title: String,
    pub summary: String,
    pub content: String,
    pub total_amount: i64,
    pub due_date: String,
    pub period_start: String,
    pub period_end: String,
    pub payload: BTreeMap<String, String>,
}

pub fn builtin_form_schema(document_type: &str) -> Vec<WorkflowFormFieldDef> {
    match document_type {
        DOC_TYPE_GENERAL => fields(&[
            field("title", "제목").required().maps_to("title"),
            field("period_start", "업무 시작일")
                .kind("date")
                .required()
                .maps_to("period_start"),
            field("period_end", "업무 종료일")
                .kind("date")
                .required()
                .maps_to("period_end"),
            field("purpose", "기안 목적").required(),
            field("content", "상세 내용")
                .kind("multiline")
                .required()
                .maps_to("summary"),
            field("expected_outcome", "기대 성과").kind("multiline"),
            field("due_date", "완료 희망일")
                .kind("date")
                .maps_to("due_date"),
        ]),
        DOC_TYPE_ATTENDANCE => fields(&[
            field("title", "제목").required().maps_to("title"),
            field("attendance_type", "근태 유형")
                .kind("select")
                .required()
                .options(ATTENDANCE_TYPE_LABELS.iter().map(|(_, label)| *label)),
            field("period_start", "시작일")
                .kind("date")
                .required()
                .maps_to("period_start"),
            field("period_end", "종료일")
                .kind("date")
                .required()
                .maps_to("period_end"),
            field("reason", "사유")
                .kind("multiline")
                .required()
                .maps_to("summary"),
            field("substitute", "업무 인수자").placeholder("부재 시 대리인"),
        ]),
        DOC_TYPE_PURCHASE => fields(&[
            field("title", "구매 건명").required().maps_to("title"),
            field("item_summary", "품목 요약").required(),
            field("vendor", "거래처/공급사"),
            field("period_start", "납기 희망일")
                .kind("date")
                .required()
                .maps_to("period_start"),
            field("period_end", "사용 기간 종료")
                .kind("date")
                .maps_to("period_end"),
            field("total_amount", "예상 금액(원)")
                .kind("number")
                .required()
                .maps_to("total_amount"),
            field("purpose", "구매 사유")
                .kind("multiline")
                .required()
                .maps_to("summary"),
        ]),
        DOC_TYPE_EXPENSE => fields(&[
            field("title", "지출 건명").required().maps_to("title"),
            field("expense_category", "지출 구분")
                .kind("select")
                .required()
                .options(EXPENSE_CATEGORIES),
            field("period_start", "사용일(시작)")
                .kind("date")
                .required()
                .maps_to("period_start"),
            field("period_end", "사용일(종료)")
                .kind("date")
                .maps_to("period_end"),
            field("total_amount", "금액(원)")
                .kind("number")
                .required()
                .maps_to("total_amount"),
            field("purpose", "지출 목적")
                .kind("multiline")
                .required()
                .maps_to("summary"),
        ]),
        DOC_TYPE_CLOSING => fields(&[
            field("title", "보고 제목").required().maps_to("title"),
            field("closing_month", "마감 월")
                .required()
                .placeholder("YYYY-MM"),
            field("period_start", "집계 시작")
                .kind("date")
                .required()
                .maps_to("period_start"),
            field("period_end", "집계 종료")
                .kind("date")
                .required()
                .maps_to("period_end"),
            field("summary", "실적 요약")
                .kind("multiline")
                .required()
                .maps_to("summary"),
            field("issues", "특이·리스크").kind("multiline"),
        ]),
        DOC_TYPE_BUSINESS_TRIP_REQUEST => fields(&[
            field("title", "출장 제목").required().maps_to("title"),
            field("period_start", "출장 시작일")
                .kind("date")
                .required()
                .maps_to("period_start"),
            field("period_end", "출장 종료일")
                .kind("date")
                .required()
                .maps_to("period_end"),
            field("destination", "출장지").required(),
            field("business_trip_purpose", "출장 목적")
                .kind("multiline")
                .required()
                .maps_to("summary"),
            field("expected_outcome", "기대 성과").kind("multiline"),
            field("transportation", "이동 수단")
                .kind("select")
                .required()
                .options(BUSINESS_TRIP_TRANSPORT_OPTIONS),
            field("estimated_amount", "예상 출장비(원)")
                .kind("number")
                .maps_to("total_amount"),
            field("executor_id", "출장 수행자 ID").required(),
            field("site_id", "현장/사업장 ID"),
            field("department_id", "부서 ID"),
            field("trip_dedupe_key", "출장 중복 방지 키")
                .placeholder("비워두면 문서 ID 기준 자동 연결"),
        ]),
        _ => builtin_form_schema(DOC_TYPE_GENERAL),
    }
}

pub fn validate_builtin_form_values(
    document_type: &str,
    values: &BTreeMap<String, String>,
) -> Vec<String> {
    let schema = builtin_form_schema(document_type);
    validate_form_values(&schema, values)
}

pub fn validate_form_values(
    schema: &[WorkflowFormFieldDef],
    values: &BTreeMap<String, String>,
) -> Vec<String> {
    let mut errors = Vec::new();

    for field in schema {
        let raw = clean(values.get(&field.key).map(String::as_str).unwrap_or(""));
        if field.required && raw.is_empty() {
            errors.push(format!("「{}」은(는) 필수입니다.", field.label));
        }
        if field.field_type == "number" && !raw.is_empty() && parse_python_int(&raw).is_none() {
            errors.push(format!("「{}」은(는) 숫자로 입력하세요.", field.label));
        }
        if field.key == "closing_month" && !raw.is_empty() && raw.chars().count() < 7 {
            errors.push("마감 월은 YYYY-MM 형식이어야 합니다.".to_string());
        }
    }

    let period_start = clean(values.get("period_start").map(String::as_str).unwrap_or(""));
    let period_end = clean(values.get("period_end").map(String::as_str).unwrap_or(""));
    if !period_start.is_empty() && !period_end.is_empty() && period_start > period_end {
        errors.push("시작일이 종료일보다 늦을 수 없습니다.".to_string());
    }

    errors
}

pub fn build_document_fields(
    document_type: &str,
    values: &BTreeMap<String, String>,
) -> WorkflowDocumentFields {
    let mut cleaned = BTreeMap::new();
    for (key, value) in values {
        cleaned.insert(key.clone(), clean(value));
    }

    let title = value(&cleaned, "title");
    let mut summary = first_value(
        &cleaned,
        &[
            "summary",
            "content",
            "business_trip_purpose",
            "purpose",
            "reason",
        ],
    );
    if summary.is_empty() {
        summary = [
            "business_trip_purpose",
            "purpose",
            "content",
            "reason",
            "item_summary",
        ]
        .iter()
        .filter_map(|key| {
            let value = value(&cleaned, key);
            (!value.is_empty()).then_some(value)
        })
        .collect::<Vec<_>>()
        .join("\n");
    }

    let amount_source = first_value(&cleaned, &["total_amount", "estimated_amount"]);
    let total_amount = if amount_source.is_empty() {
        0
    } else {
        parse_python_int(&amount_source).unwrap_or(0)
    };

    let mut payload = cleaned.clone();
    payload.insert("document_type".to_string(), document_type.to_string());

    WorkflowDocumentFields {
        title,
        content: summary.clone(),
        summary,
        total_amount,
        due_date: first_value(&cleaned, &["due_date", "period_end"]),
        period_start: value(&cleaned, "period_start"),
        period_end: value(&cleaned, "period_end"),
        payload,
    }
}

pub fn attendance_type_key(label: &str) -> String {
    ATTENDANCE_TYPE_LABELS
        .iter()
        .find_map(|(key, candidate_label)| {
            (*candidate_label == label).then_some((*key).to_string())
        })
        .unwrap_or_else(|| "other".to_string())
}

fn fields(items: &[FieldBuilder]) -> Vec<WorkflowFormFieldDef> {
    items.iter().map(FieldBuilder::build).collect()
}

fn field(key: &str, label: &str) -> FieldBuilder {
    FieldBuilder {
        key: key.to_string(),
        label: label.to_string(),
        field_type: "text".to_string(),
        required: false,
        options: Vec::new(),
        placeholder: String::new(),
        maps_to: String::new(),
    }
}

#[derive(Clone, Debug)]
struct FieldBuilder {
    key: String,
    label: String,
    field_type: String,
    required: bool,
    options: Vec<String>,
    placeholder: String,
    maps_to: String,
}

impl FieldBuilder {
    fn kind(mut self, field_type: &str) -> Self {
        self.field_type = field_type.to_string();
        self
    }

    fn required(mut self) -> Self {
        self.required = true;
        self
    }

    fn options<I, S>(mut self, options: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        self.options = options
            .into_iter()
            .map(|value| value.as_ref().to_string())
            .collect();
        self
    }

    fn placeholder(mut self, placeholder: &str) -> Self {
        self.placeholder = placeholder.to_string();
        self
    }

    fn maps_to(mut self, maps_to: &str) -> Self {
        self.maps_to = maps_to.to_string();
        self
    }

    fn build(&self) -> WorkflowFormFieldDef {
        WorkflowFormFieldDef {
            key: self.key.clone(),
            label: self.label.clone(),
            field_type: self.field_type.clone(),
            required: self.required,
            options: self.options.clone(),
            placeholder: self.placeholder.clone(),
            maps_to: self.maps_to.clone(),
        }
    }
}

fn first_value(values: &BTreeMap<String, String>, keys: &[&str]) -> String {
    keys.iter()
        .map(|key| value(values, key))
        .find(|value| !value.is_empty())
        .unwrap_or_default()
}

fn value(values: &BTreeMap<String, String>, key: &str) -> String {
    values.get(key).cloned().unwrap_or_default()
}

fn clean(value: &str) -> String {
    value.trim().to_string()
}

fn parse_python_int(value: &str) -> Option<i64> {
    value.replace(',', "").parse::<i64>().ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;

    fn values(items: &[(&str, &str)]) -> BTreeMap<String, String> {
        items
            .iter()
            .map(|(key, value)| ((*key).to_string(), (*value).to_string()))
            .collect()
    }

    #[test]
    fn builtin_business_trip_schema_and_validation_match_python_boundaries() {
        let schema = builtin_form_schema(DOC_TYPE_BUSINESS_TRIP_REQUEST);
        let keys: Vec<&str> = schema.iter().map(|field| field.key.as_str()).collect();
        assert!(keys.contains(&"destination"));
        assert!(keys.contains(&"business_trip_purpose"));
        assert!(keys.contains(&"executor_id"));

        let errors = validate_builtin_form_values(
            DOC_TYPE_BUSINESS_TRIP_REQUEST,
            &values(&[
                ("title", "부산 고객사 출장"),
                ("period_start", "2026-06-10"),
                ("period_end", "2026-06-09"),
                ("destination", "부산"),
                ("business_trip_purpose", "고객사 미팅"),
                ("transportation", "기차"),
                ("executor_id", "u-exec"),
            ]),
        );
        assert!(errors.iter().any(|error| error.contains("시작일")));
    }

    #[test]
    fn validation_messages_and_numeric_rules_match_python() {
        assert_eq!(
            builtin_form_schema("UNKNOWN_TYPE"),
            builtin_form_schema(DOC_TYPE_GENERAL)
        );

        let required_errors =
            validate_builtin_form_values(DOC_TYPE_GENERAL, &values(&[("title", "테스트")]));
        assert!(
            required_errors
                .iter()
                .any(|error| error.contains("기안 목적"))
        );

        let invalid_number = validate_builtin_form_values(
            DOC_TYPE_EXPENSE,
            &values(&[
                ("title", "법인카드"),
                ("expense_category", "법인카드"),
                ("period_start", "2026-05-01"),
                ("total_amount", "12.5"),
                ("purpose", "회의비"),
            ]),
        );
        assert!(invalid_number.iter().any(|error| error.contains("숫자")));

        let closing_month = validate_builtin_form_values(
            DOC_TYPE_CLOSING,
            &values(&[
                ("title", "마감"),
                ("closing_month", "2026-6"),
                ("period_start", "2026-06-01"),
                ("period_end", "2026-06-30"),
                ("summary", "요약"),
            ]),
        );
        assert!(closing_month.iter().any(|error| error.contains("YYYY-MM")));
    }

    #[test]
    fn document_field_shaping_matches_python_fallbacks() {
        let built = build_document_fields(
            DOC_TYPE_BUSINESS_TRIP_REQUEST,
            &values(&[
                ("title", " 부산 고객사 출장 "),
                ("period_start", "2026-06-10"),
                ("period_end", "2026-06-11"),
                ("destination", "부산"),
                ("business_trip_purpose", " 고객사 미팅 "),
                ("transportation", "기차"),
                ("estimated_amount", "150,000"),
                ("executor_id", "u-exec"),
                ("trip_dedupe_key", "trip:doc-1"),
            ]),
        );
        assert_eq!(built.title, "부산 고객사 출장");
        assert_eq!(built.summary, "고객사 미팅");
        assert_eq!(built.content, "고객사 미팅");
        assert_eq!(built.total_amount, 150_000);
        assert_eq!(
            built.payload.get("document_type"),
            Some(&DOC_TYPE_BUSINESS_TRIP_REQUEST.to_string())
        );
        assert_eq!(
            built.payload.get("trip_dedupe_key"),
            Some(&"trip:doc-1".to_string())
        );
    }

    #[test]
    fn item_summary_amount_and_attendance_fallbacks_match_python() {
        let built = build_document_fields(
            DOC_TYPE_PURCHASE,
            &values(&[
                ("title", "노트북"),
                ("item_summary", "개발 장비"),
                ("total_amount", "invalid"),
                ("estimated_amount", "99,999"),
                ("period_end", "2026-07-01"),
            ]),
        );
        assert_eq!(built.summary, "개발 장비");
        assert_eq!(built.total_amount, 0);
        assert_eq!(built.due_date, "2026-07-01");
        assert_eq!(attendance_type_key("오전 반차"), "half_day_morning");
        assert_eq!(attendance_type_key("없는 유형"), "other");
    }
}
