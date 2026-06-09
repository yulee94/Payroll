# Backend Contract Requests

Initial React Native migration does not require backend changes. The default app runtime renders empty non-demo view models until an approved adapter is wired. Typed mock data is isolated to explicit demo mode and the dependency-free demo preview so frontend layout, navigation, responsive behavior, empty states, and screen copy can be reviewed without touching payroll logic.

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

Frontend should consume these as read-only view models. If the backend shape is not available yet, keep the default app state empty, keep mock data local to `apps/bitween-platform-ui/src/data.ts` behind the explicit demo-data gate, and document the missing field here instead of editing backend services.
