use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

pub const FOLLOW_UP_ACTION_TODO: &str = "todo";
pub const FOLLOW_UP_ACTION_CALENDAR: &str = "calendar";

pub const SOURCE_WORKFLOW: &str = "workflow";
pub const SOURCE_WORKFLOW_APPROVAL: &str = "workflow_approval";
pub const SOURCE_WORKFLOW_CC: &str = "workflow_cc";
pub const SOURCE_WORKFLOW_EXECUTION: &str = "workflow_execution";

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowFollowUpDocument {
    pub title: String,
    pub document_no: String,
    pub document_id: String,
    pub document_type: String,
    pub document_type_label: String,
    pub trip_id: String,
    pub period_start: String,
    pub requested_date: String,
    pub period_end: String,
    pub due_date: String,
    pub requester_id: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowFollowUpApprovalStep {
    pub approver_id: String,
    pub approver_role: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowSubmissionFollowUpInput {
    pub document: WorkflowFollowUpDocument,
    pub approval_line: Vec<WorkflowFollowUpApprovalStep>,
    pub tenant_id: String,
    pub session_user_id: String,
    pub cc_user_ids: Vec<String>,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowApprovalCompleteFollowUpInput {
    pub document: WorkflowFollowUpDocument,
    pub tenant_id: String,
    pub executor_id: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowFollowUpAction {
    pub action_type: String,
    pub user_id: String,
    pub tenant_id: String,
    pub title: String,
    pub date: String,
    pub end_date: String,
    pub due_date: String,
    pub source: String,
    pub document_id: String,
    pub source_key: String,
    pub role: String,
    pub trip_id: String,
}

pub fn plan_submission_follow_up(
    input: &WorkflowSubmissionFollowUpInput,
) -> Vec<WorkflowFollowUpAction> {
    let doc = &input.document;
    let title = non_empty_or(&doc.title, "문서");
    let doc_no = doc.document_no.clone();
    let doc_id = doc.document_id.clone();
    let dtype_label = non_empty_or(&doc.document_type_label, "문서");
    let period_start = first_non_empty([&doc.period_start, &doc.requested_date, ""]);
    let period_end = first_non_empty([&doc.period_end, &doc.due_date, &period_start]);
    let due = first_non_empty([&period_end, &period_start]);
    let requester_id = first_non_empty([&doc.requester_id, &input.session_user_id]);
    let tenant_id = input.tenant_id.clone();
    let trip_id = doc.trip_id.clone();

    let mut cal_title = format!("[{dtype_label}] {title}");
    if !period_start.is_empty() && !period_end.is_empty() && period_start != period_end {
        cal_title = format!("{cal_title} ({period_start}~{period_end})");
    }

    let mut actions = vec![calendar_action(WorkflowFollowUpAction {
        user_id: requester_id.clone(),
        tenant_id: tenant_id.clone(),
        title: cal_title,
        date: first_non_empty([&period_start, &due]),
        end_date: period_end.clone(),
        source: SOURCE_WORKFLOW.to_string(),
        document_id: doc_id.clone(),
        source_key: format!("workflow:calendar:{doc_id}:requester:{requester_id}"),
        ..WorkflowFollowUpAction::default()
    })];

    actions.push(todo_action(WorkflowFollowUpAction {
        user_id: requester_id.clone(),
        tenant_id: tenant_id.clone(),
        title: format!("결재 진행: {title} ({doc_no})"),
        due_date: due.clone(),
        source: SOURCE_WORKFLOW.to_string(),
        document_id: doc_id.clone(),
        source_key: format!("workflow:todo:{doc_id}:requester:{requester_id}"),
        trip_id: trip_id.clone(),
        ..WorkflowFollowUpAction::default()
    }));

    let mut seen = BTreeSet::new();
    for (idx, step) in input.approval_line.iter().enumerate() {
        let uid = clean(&step.approver_id);
        if uid.is_empty() || seen.contains(&uid) {
            continue;
        }
        seen.insert(uid.clone());
        let ordinal = idx + 1;
        actions.push(todo_action(WorkflowFollowUpAction {
            user_id: uid.clone(),
            tenant_id: tenant_id.clone(),
            title: format!("결재 {ordinal}단계: {title} ({doc_no})"),
            due_date: due.clone(),
            source: SOURCE_WORKFLOW_APPROVAL.to_string(),
            document_id: doc_id.clone(),
            source_key: format!("workflow_approval:todo:{doc_id}:{ordinal}:{uid}"),
            role: step.approver_role.clone(),
            trip_id: trip_id.clone(),
            ..WorkflowFollowUpAction::default()
        }));
        actions.push(calendar_action(WorkflowFollowUpAction {
            user_id: uid.clone(),
            tenant_id: tenant_id.clone(),
            title: format!("결재: {title}"),
            date: first_non_empty([&due, &period_start]),
            end_date: period_end.clone(),
            source: SOURCE_WORKFLOW_APPROVAL.to_string(),
            document_id: doc_id.clone(),
            source_key: format!("workflow_approval:calendar:{doc_id}:{ordinal}:{uid}"),
            ..WorkflowFollowUpAction::default()
        }));
    }

    for cc_user_id in &input.cc_user_ids {
        let uid = clean(cc_user_id);
        if uid.is_empty() || seen.contains(&uid) || uid == requester_id {
            continue;
        }
        actions.push(todo_action(WorkflowFollowUpAction {
            user_id: uid.clone(),
            tenant_id: tenant_id.clone(),
            title: format!("참조: {title} ({doc_no})"),
            due_date: due.clone(),
            source: SOURCE_WORKFLOW_CC.to_string(),
            document_id: doc_id.clone(),
            source_key: format!("workflow_cc:todo:{doc_id}:{uid}"),
            trip_id: trip_id.clone(),
            ..WorkflowFollowUpAction::default()
        }));
    }

    actions
}

pub fn plan_approval_complete_follow_up(
    input: &WorkflowApprovalCompleteFollowUpInput,
) -> Vec<WorkflowFollowUpAction> {
    let doc = &input.document;
    let title = non_empty_or(&doc.title, "문서");
    let doc_id = doc.document_id.clone();
    let trip_id = doc.trip_id.clone();
    let period_end = first_non_empty([&doc.period_end, &doc.due_date]);
    let requester_id = doc.requester_id.clone();
    let tenant_id = input.tenant_id.clone();

    let mut actions = vec![todo_action(WorkflowFollowUpAction {
        user_id: requester_id.clone(),
        tenant_id: tenant_id.clone(),
        title: format!("실행·완료 확인: {title}"),
        due_date: period_end.clone(),
        source: SOURCE_WORKFLOW_EXECUTION.to_string(),
        document_id: doc_id.clone(),
        source_key: format!("workflow_execution:todo:{doc_id}:confirm:{requester_id}"),
        trip_id: trip_id.clone(),
        ..WorkflowFollowUpAction::default()
    })];

    if !input.executor_id.is_empty() && input.executor_id != requester_id {
        actions.push(todo_action(WorkflowFollowUpAction {
            user_id: input.executor_id.clone(),
            tenant_id: tenant_id.clone(),
            title: format!("실행: {title}"),
            due_date: period_end.clone(),
            source: SOURCE_WORKFLOW_EXECUTION.to_string(),
            document_id: doc_id.clone(),
            source_key: format!(
                "workflow_execution:todo:{doc_id}:executor:{}",
                input.executor_id
            ),
            trip_id: trip_id.clone(),
            ..WorkflowFollowUpAction::default()
        }));
        actions.push(calendar_action(WorkflowFollowUpAction {
            user_id: input.executor_id.clone(),
            tenant_id,
            title: format!("실행: {title}"),
            date: first_non_empty([&period_end, &doc.period_start]),
            source: SOURCE_WORKFLOW_EXECUTION.to_string(),
            document_id: doc_id.clone(),
            source_key: format!(
                "workflow_execution:calendar:{doc_id}:executor:{}",
                input.executor_id
            ),
            ..WorkflowFollowUpAction::default()
        }));
    }

    actions
}

fn todo_action(mut action: WorkflowFollowUpAction) -> WorkflowFollowUpAction {
    action.action_type = FOLLOW_UP_ACTION_TODO.to_string();
    action
}

fn calendar_action(mut action: WorkflowFollowUpAction) -> WorkflowFollowUpAction {
    action.action_type = FOLLOW_UP_ACTION_CALENDAR.to_string();
    action
}

fn non_empty_or(value: &str, default_value: &str) -> String {
    if value.is_empty() {
        default_value.to_string()
    } else {
        value.to_string()
    }
}

fn first_non_empty<const N: usize>(values: [&str; N]) -> String {
    values
        .into_iter()
        .find(|value| !value.is_empty())
        .unwrap_or_default()
        .to_string()
}

fn clean(value: &str) -> String {
    value.trim().to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn document() -> WorkflowFollowUpDocument {
        WorkflowFollowUpDocument {
            title: "대전 고객사 출장".to_string(),
            document_no: "WF-1".to_string(),
            document_id: "doc-1".to_string(),
            document_type: "BUSINESS_TRIP_REQUEST".to_string(),
            document_type_label: "출장신청서".to_string(),
            trip_id: "trip-1".to_string(),
            period_start: "2026-06-01".to_string(),
            period_end: "2026-06-03".to_string(),
            requester_id: "requester".to_string(),
            ..WorkflowFollowUpDocument::default()
        }
    }

    #[test]
    fn submission_follow_up_plan_matches_python_call_intents() {
        let actions = plan_submission_follow_up(&WorkflowSubmissionFollowUpInput {
            document: document(),
            approval_line: vec![
                WorkflowFollowUpApprovalStep {
                    approver_id: "".to_string(),
                    approver_role: "ignored".to_string(),
                },
                WorkflowFollowUpApprovalStep {
                    approver_id: " approver ".to_string(),
                    approver_role: "department_manager".to_string(),
                },
                WorkflowFollowUpApprovalStep {
                    approver_id: "approver".to_string(),
                    approver_role: "duplicate".to_string(),
                },
            ],
            tenant_id: "tenant-a".to_string(),
            session_user_id: "session-user".to_string(),
            cc_user_ids: vec![
                " approver ".to_string(),
                " cc-1 ".to_string(),
                "requester".to_string(),
                "".to_string(),
            ],
        });

        assert_eq!(actions.len(), 5);
        assert_eq!(actions[0].action_type, FOLLOW_UP_ACTION_CALENDAR);
        assert_eq!(actions[0].user_id, "requester");
        assert_eq!(
            actions[0].title,
            "[출장신청서] 대전 고객사 출장 (2026-06-01~2026-06-03)"
        );
        assert_eq!(actions[0].date, "2026-06-01");
        assert_eq!(actions[0].end_date, "2026-06-03");
        assert_eq!(
            actions[0].source_key,
            "workflow:calendar:doc-1:requester:requester"
        );

        assert_eq!(actions[1].action_type, FOLLOW_UP_ACTION_TODO);
        assert_eq!(actions[1].title, "결재 진행: 대전 고객사 출장 (WF-1)");
        assert_eq!(actions[1].due_date, "2026-06-03");
        assert_eq!(actions[1].trip_id, "trip-1");

        let approver_todo = actions
            .iter()
            .find(|action| action.source_key == "workflow_approval:todo:doc-1:2:approver")
            .unwrap();
        assert_eq!(approver_todo.title, "결재 2단계: 대전 고객사 출장 (WF-1)");
        assert_eq!(approver_todo.role, "department_manager");

        let cc_todo = actions
            .iter()
            .find(|action| action.source == SOURCE_WORKFLOW_CC)
            .unwrap();
        assert_eq!(cc_todo.user_id, "cc-1");
        assert_eq!(cc_todo.source_key, "workflow_cc:todo:doc-1:cc-1");
    }

    #[test]
    fn submission_defaults_and_due_dates_are_preserved() {
        let actions = plan_submission_follow_up(&WorkflowSubmissionFollowUpInput {
            document: WorkflowFollowUpDocument {
                document_id: "doc-2".to_string(),
                requested_date: "2026-07-01".to_string(),
                due_date: "2026-07-05".to_string(),
                ..WorkflowFollowUpDocument::default()
            },
            approval_line: vec![],
            tenant_id: "tenant-a".to_string(),
            session_user_id: "session-owner".to_string(),
            cc_user_ids: vec![],
        });
        assert_eq!(actions.len(), 2);
        assert_eq!(actions[0].user_id, "session-owner");
        assert_eq!(actions[0].title, "[문서] 문서 (2026-07-01~2026-07-05)");
        assert_eq!(actions[1].title, "결재 진행: 문서 ()");
        assert_eq!(actions[1].due_date, "2026-07-05");
    }

    #[test]
    fn approval_complete_plan_matches_python_call_intents() {
        let actions = plan_approval_complete_follow_up(&WorkflowApprovalCompleteFollowUpInput {
            document: document(),
            tenant_id: "tenant-a".to_string(),
            executor_id: "executor".to_string(),
        });
        assert_eq!(actions.len(), 3);
        assert_eq!(actions[0].action_type, FOLLOW_UP_ACTION_TODO);
        assert_eq!(actions[0].user_id, "requester");
        assert_eq!(actions[0].title, "실행·완료 확인: 대전 고객사 출장");
        assert_eq!(
            actions[0].source_key,
            "workflow_execution:todo:doc-1:confirm:requester"
        );
        assert_eq!(actions[0].trip_id, "trip-1");

        assert_eq!(actions[1].user_id, "executor");
        assert_eq!(
            actions[1].source_key,
            "workflow_execution:todo:doc-1:executor:executor"
        );
        assert_eq!(actions[2].action_type, FOLLOW_UP_ACTION_CALENDAR);
        assert_eq!(actions[2].date, "2026-06-03");
        assert_eq!(
            actions[2].source_key,
            "workflow_execution:calendar:doc-1:executor:executor"
        );
    }

    #[test]
    fn approval_complete_skips_executor_when_same_as_requester() {
        let actions = plan_approval_complete_follow_up(&WorkflowApprovalCompleteFollowUpInput {
            document: document(),
            tenant_id: "tenant-a".to_string(),
            executor_id: "requester".to_string(),
        });
        assert_eq!(actions.len(), 1);
        assert_eq!(
            actions[0].source_key,
            "workflow_execution:todo:doc-1:confirm:requester"
        );
    }
}
