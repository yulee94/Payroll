# Backend Contract Requests

Initial React Native migration does not require backend changes. The current app uses empty live-data states so frontend layout, navigation, responsive behavior, and screen copy can be reviewed without touching payroll logic or fabricating business records.

Future frontend integration should map backend/API-ready outputs into the read-only `PlatformViewModel` shape in `apps/bitween-platform-ui/src/viewModel.ts`.

Future frontend integration will need stable read-only endpoints or adapters for:

- Current tenant/session display info
- Platform navigation permissions by user role
- Payroll readiness cards or snapshot
- Payroll setup policy display values
- Recent payroll periods and archive file summaries
- Workflow inbox counts and document state summaries
- HR summary counts for roster, attendance, and certificate requests
- Archive folder/category summaries
- AI recommendation availability by screen
- Admin user/role summary counts
- User appearance and notification preferences

These should be exposed through existing API-ready/service contracts where possible.

Frontend should consume these as read-only view models. If the backend shape is not available yet, keep the UI in empty-state mode and document the missing field here instead of adding local fake data or editing backend services.
