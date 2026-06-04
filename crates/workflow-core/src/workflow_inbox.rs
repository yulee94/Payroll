use serde::{Deserialize, Serialize};

pub const DOC_STATUS_DRAFT: &str = "draft";
pub const DOC_STATUS_SUBMITTED: &str = "submitted";
pub const DOC_STATUS_IN_REVIEW: &str = "in_review";
pub const DOC_STATUS_APPROVED: &str = "approved";
pub const DOC_STATUS_REJECTED: &str = "rejected";
pub const DOC_STATUS_REQUESTED_CHANGES: &str = "requested_changes";
pub const DOC_STATUS_CANCELLED: &str = "cancelled";
pub const DOC_STATUS_COMPLETED: &str = "completed";
pub const DOC_STATUS_CLOSED: &str = "closed";

pub const INBOX_TO_APPROVE: &str = "to_approve";
pub const INBOX_MY_DRAFT: &str = "my_draft";
pub const INBOX_CIRCULATE: &str = "circulate";
pub const INBOX_IN_PROGRESS: &str = "in_progress";
pub const INBOX_COMPLETED: &str = "completed";
pub const INBOX_REJECTED: &str = "rejected";
pub const INBOX_REFERENCE: &str = "reference";
pub const INBOX_ALL: &str = "all";
pub const INBOX_MY_REQUESTS: &str = "my_requests";
pub const INBOX_PENDING_APPROVAL: &str = "pending_approval";

pub const INBOX_IDS: [&str; 8] = [
    INBOX_TO_APPROVE,
    INBOX_MY_DRAFT,
    INBOX_CIRCULATE,
    INBOX_IN_PROGRESS,
    INBOX_COMPLETED,
    INBOX_REJECTED,
    INBOX_REFERENCE,
    INBOX_ALL,
];

pub const GW_INBOX_QUICK_TAB_IDS: [&str; 4] =
    [INBOX_ALL, INBOX_TO_APPROVE, INBOX_MY_DRAFT, INBOX_CIRCULATE];

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowInboxApprovalStep {
    pub approver_id: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowInboxDocument {
    pub status: String,
    pub requester_id: String,
    pub approval_steps: Vec<WorkflowInboxApprovalStep>,
    pub cc_user_ids: Vec<String>,
    pub cc_users: Vec<String>,
    pub content_gw_list: String,
    pub content_imported_from: String,
    pub content_gw_doc_id: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowInboxMatchInput {
    pub document: WorkflowInboxDocument,
    pub inbox_id: String,
    pub user_id: String,
    pub can_approve_document: bool,
}

pub fn matches_inbox(input: &WorkflowInboxMatchInput) -> bool {
    let inbox_id = supplied(&input.inbox_id);
    if inbox_id.is_empty() || inbox_id == INBOX_ALL {
        return true;
    }

    let uid = supplied(&input.user_id);
    let status = supplied(&input.document.status);
    let is_mine = !uid.is_empty() && supplied(&input.document.requester_id) == uid;
    let on_line = !uid.is_empty()
        && input
            .document
            .approval_steps
            .iter()
            .any(|step| supplied(&step.approver_id) == uid);
    let in_cc = !uid.is_empty() && contains_user_id(cc_users(&input.document), &uid);
    let can_approve = input.can_approve_document;

    match inbox_id.as_str() {
        INBOX_TO_APPROVE => {
            if is_gw_import(&input.document) {
                let gw_list = gw_list_kind(&input.document);
                if matches!(
                    gw_list.as_str(),
                    "pending" | "to_approve" | "inbox_scrape" | "inbox"
                ) {
                    return is_active_approval_status(&status);
                }
            }
            can_approve && is_active_approval_status(&status)
        }
        INBOX_MY_DRAFT => {
            if is_gw_import(&input.document) {
                let gw_list = gw_list_kind(&input.document);
                return matches!(
                    gw_list.as_str(),
                    "draft" | "drafts" | "my_draft" | "drafts_page1" | "기안" | "browser"
                );
            }
            is_mine
                && matches!(
                    status.as_str(),
                    DOC_STATUS_DRAFT | DOC_STATUS_REQUESTED_CHANGES
                )
        }
        INBOX_IN_PROGRESS => (is_mine || on_line) && is_active_approval_status(&status),
        INBOX_COMPLETED => {
            matches!(
                status.as_str(),
                DOC_STATUS_APPROVED | DOC_STATUS_COMPLETED | DOC_STATUS_CLOSED
            ) && (is_mine || on_line || in_cc)
        }
        INBOX_REJECTED => {
            matches!(status.as_str(), DOC_STATUS_REJECTED | DOC_STATUS_CANCELLED)
                && (is_mine || on_line)
        }
        INBOX_CIRCULATE => {
            if is_gw_import(&input.document) {
                let gw_list = gw_list_kind(&input.document);
                if matches!(
                    gw_list.as_str(),
                    "circulate" | "circulate_home_widget" | "공람" | "reference"
                ) {
                    return true;
                }
            }
            if !in_cc {
                return false;
            }
            if can_approve && is_active_approval_status(&status) {
                return false;
            }
            !matches!(status.as_str(), DOC_STATUS_DRAFT | DOC_STATUS_CANCELLED)
        }
        INBOX_REFERENCE => !in_cc && on_line && !is_mine && status != DOC_STATUS_DRAFT,
        INBOX_MY_REQUESTS => is_mine,
        INBOX_PENDING_APPROVAL => matches_inbox(&WorkflowInboxMatchInput {
            inbox_id: INBOX_TO_APPROVE.to_string(),
            ..input.clone()
        }),
        _ => true,
    }
}

pub fn filter_inbox_ids(
    document: &WorkflowInboxDocument,
    user_id: &str,
    can_approve_document: bool,
) -> Vec<String> {
    INBOX_IDS
        .into_iter()
        .filter(|inbox_id| {
            matches_inbox(&WorkflowInboxMatchInput {
                document: document.clone(),
                inbox_id: (*inbox_id).to_string(),
                user_id: user_id.to_string(),
                can_approve_document,
            })
        })
        .map(String::from)
        .collect()
}

fn is_active_approval_status(status: &str) -> bool {
    matches!(status, DOC_STATUS_SUBMITTED | DOC_STATUS_IN_REVIEW)
}

fn is_gw_import(document: &WorkflowInboxDocument) -> bool {
    !supplied(&document.content_imported_from).is_empty()
        || !supplied(&document.content_gw_doc_id).is_empty()
}

fn gw_list_kind(document: &WorkflowInboxDocument) -> String {
    supplied(&document.content_gw_list).to_lowercase()
}

fn cc_users(document: &WorkflowInboxDocument) -> &[String] {
    if document.cc_user_ids.is_empty() {
        &document.cc_users
    } else {
        &document.cc_user_ids
    }
}

fn contains_user_id(values: &[String], expected: &str) -> bool {
    values.iter().any(|value| supplied(value) == expected)
}

fn supplied(value: &str) -> String {
    value.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn document(status: &str) -> WorkflowInboxDocument {
        WorkflowInboxDocument {
            status: status.to_string(),
            requester_id: "requester-1".to_string(),
            approval_steps: vec![WorkflowInboxApprovalStep {
                approver_id: "approver-1".to_string(),
            }],
            ..WorkflowInboxDocument::default()
        }
    }

    fn input(
        document: WorkflowInboxDocument,
        inbox_id: &str,
        user_id: &str,
        can_approve_document: bool,
    ) -> WorkflowInboxMatchInput {
        WorkflowInboxMatchInput {
            document,
            inbox_id: inbox_id.to_string(),
            user_id: user_id.to_string(),
            can_approve_document,
        }
    }

    #[test]
    fn standard_inbox_matrix_matches_python_boundaries() {
        assert!(matches_inbox(&input(
            document(DOC_STATUS_SUBMITTED),
            INBOX_TO_APPROVE,
            "approver-1",
            true,
        )));
        assert!(matches_inbox(&input(
            document(DOC_STATUS_SUBMITTED),
            INBOX_IN_PROGRESS,
            "requester-1",
            false,
        )));
        assert!(matches_inbox(&input(
            document(DOC_STATUS_IN_REVIEW),
            INBOX_IN_PROGRESS,
            "approver-1",
            false,
        )));
        assert!(matches_inbox(&input(
            document(DOC_STATUS_DRAFT),
            INBOX_MY_DRAFT,
            "requester-1",
            false,
        )));
        assert!(matches_inbox(&input(
            document(DOC_STATUS_APPROVED),
            INBOX_COMPLETED,
            "approver-1",
            false,
        )));
        assert!(matches_inbox(&input(
            document(DOC_STATUS_REJECTED),
            INBOX_REJECTED,
            "requester-1",
            false,
        )));
    }

    #[test]
    fn circulate_reference_and_legacy_aliases_match_python_boundaries() {
        let mut cc_document = document(DOC_STATUS_SUBMITTED);
        cc_document.cc_user_ids = vec!["cc-1".to_string()];

        assert!(matches_inbox(&input(
            cc_document.clone(),
            INBOX_CIRCULATE,
            "cc-1",
            false,
        )));
        assert!(!matches_inbox(&input(
            cc_document,
            INBOX_REFERENCE,
            "cc-1",
            false,
        )));

        let line_document = document(DOC_STATUS_APPROVED);
        assert!(matches_inbox(&input(
            line_document,
            INBOX_REFERENCE,
            "approver-1",
            false,
        )));

        assert!(matches_inbox(&input(
            document(DOC_STATUS_DRAFT),
            INBOX_MY_REQUESTS,
            "requester-1",
            false,
        )));
        assert!(matches_inbox(&input(
            document(DOC_STATUS_SUBMITTED),
            INBOX_PENDING_APPROVAL,
            "approver-1",
            true,
        )));
    }

    #[test]
    fn gw_import_overrides_match_python_list_kinds() {
        let mut pending = document(DOC_STATUS_SUBMITTED);
        pending.content_imported_from = "gw".to_string();
        pending.content_gw_list = "inbox".to_string();
        assert!(matches_inbox(&input(
            pending,
            INBOX_TO_APPROVE,
            "u1",
            false
        )));

        let mut draft = document(DOC_STATUS_APPROVED);
        draft.content_gw_doc_id = "GW-1".to_string();
        draft.content_gw_list = "drafts_page1".to_string();
        assert!(matches_inbox(&input(draft, INBOX_MY_DRAFT, "u1", false)));

        let mut circulate = document(DOC_STATUS_DRAFT);
        circulate.content_imported_from = "gw".to_string();
        circulate.content_gw_list = "reference".to_string();
        assert!(matches_inbox(&input(
            circulate,
            INBOX_CIRCULATE,
            "u1",
            false
        )));
    }

    #[test]
    fn blank_all_and_filter_ids_are_stable() {
        let document = document(DOC_STATUS_APPROVED);
        assert!(matches_inbox(&input(
            document.clone(),
            "",
            "requester-1",
            false
        )));
        assert!(matches_inbox(&input(
            document.clone(),
            INBOX_ALL,
            "requester-1",
            false
        )));
        assert_eq!(
            GW_INBOX_QUICK_TAB_IDS,
            ["all", "to_approve", "my_draft", "circulate"]
        );
        let ids = filter_inbox_ids(&document, "requester-1", false);
        assert!(ids.contains(&INBOX_COMPLETED.to_string()));
        assert!(ids.contains(&INBOX_ALL.to_string()));
    }

    #[test]
    fn supplied_string_fields_are_not_trimmed_before_matching() {
        let mut draft = document(DOC_STATUS_DRAFT);
        draft.requester_id = " requester-1 ".to_string();
        assert!(!matches_inbox(&input(
            draft,
            INBOX_MY_DRAFT,
            "requester-1",
            false,
        )));

        let mut gw_draft = document(DOC_STATUS_APPROVED);
        gw_draft.content_imported_from = " ".to_string();
        gw_draft.content_gw_list = "drafts".to_string();
        assert!(matches_inbox(&input(
            gw_draft,
            INBOX_MY_DRAFT,
            "requester-1",
            false,
        )));
    }
}
