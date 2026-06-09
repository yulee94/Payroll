# Bitween Worker Mobile App

Implemented vertical slice for an Android + iOS worker phone app linked to Bitween payroll, workflow, and attendance data.

## Runtime target

- App stack: Expo SDK 56, React Native 0.85, strict TypeScript.
- Phone targets: Android and iPhone from one React Native codebase.
- Distribution default: private employee-only builds first; customer-facing apps can later move to public App Store + Google Play release.
- Android target: Expo SDK 56 uses target/compile SDK 36, satisfying current Android 15/API 35+ Play submission requirements.

## Login, device, and local-storage contract

Mobile app use follows this order and is locked in `core.mobile.app_api.mobile_security_contract()`:

1. Company account login.
2. OTP/MFA proof.
3. Device registration.
4. Branch/role permission check.
5. App use.

The app must not store these values in local plaintext: raw password, resident-registration number, card number, plaintext sensitive data, or long-lived admin token. When data must remain on-device, use encrypted storage only: iOS Keychain, Android Keystore, or Expo SecureStore/Secure Storage.

## Backend service layer

Framework-neutral handlers live in `core.mobile.app_api` so an HTTP or Rust wrapper can call the same behavior.

The phone app API is separated from the web/admin APIs at the gateway/service surface:

| Surface | Exposure | Path rule |
| --- | --- | --- |
| Web Admin API | Admin web only | `admin-api` / `/api/admin/v1/*` |
| Mobile App API | React Native iOS/Android employee app only | `mobile-api` / `/api/v{n}/*` |
| Public Customer API | External customer/partner integrations | `public-api` / `/api/public/v1/*` |
| Internal Admin API | Private subnet operations/batch/security only | `internal-api` / `/api/internal/v1/*` |

Mobile App API paths must be versioned. Current examples are `/api/v1/login`, `/api/v1/branches`, `/api/v1/tasks`; future task shape changes use `/api/v2/tasks`.

| Endpoint | Handler | Purpose |
| --- | --- | --- |
| `GET /api/v1/config` | `get_mobile_app_config` | Server-controlled app version policy, push/offline contract, review metadata requirements |
| `POST /api/v1/login` | `mobile_login` | Bitween login + OTP/MFA gate + mobile token issue |
| `GET /api/v1/branches` | `list_mobile_branches` | App-visible branch/worksite list with `branch_id` |
| `GET /api/v1/tasks` | `list_mobile_tasks_v1` | App action tasks, stable v1 shape |
| `GET /api/v2/tasks` | `list_mobile_tasks_v2` | Forward-compatible task shape for future app releases |
| `POST /api/v1/devices/register` | `register_mobile_device` | Android/iOS device and FCM/APNs push token registration |
| `POST /api/v1/consents` | `record_mobile_consents` | Location, biometric, notification, payroll, privacy consent capture |
| `GET /api/v1/me` | `get_mobile_me` | Current worker and latest consent state |
| `GET /api/v1/geofence/current` | `get_current_geofence` | Assigned/current work area geofence |
| `POST /api/v1/attendance/check` | `mobile_check_attendance` | Biometric + GPS check-in/out |
| `POST /api/v1/location/geofence-event` | `mobile_geofence_event` | Shift geofence enter/exit/heartbeat |
| `POST /api/v1/push/send` | `send_mobile_push_notification` | Queue FCM/APNs notifications by user/branch/device |
| `POST /api/v1/sync/offline` | `sync_mobile_offline_requests` | Idempotent sync for offline-created requests |
| `GET /api/v1/payroll/{period}` | `get_mobile_payroll_summary` | Own finalized payroll or current estimate |
| `POST /api/v1/requests` | `create_mobile_attendance_request` | 연차/병가/출장/외출/조퇴 workflow request |
| `POST /api/v1/absence-windows/sync` | `sync_mobile_absence_windows` | Approved workflow docs → authorized absence windows |
| `GET /api/v1/manager/alerts` | `list_mobile_manager_alerts` | Manager/department open geofence alerts |
| `POST /api/v1/manager/alerts/{id}/ack` | `ack_mobile_alert` | Manager alert acknowledgement |

## Push notifications

Required notification kinds:

- 작업 배정 알림
- 승인 요청 알림
- 공지사항
- 장애 알림
- 입고/출고 알림
- 예약 알림
- 결제/정산 알림

Flow: app install → FCM/APNs device token issue → server saves device token → business event occurs → push is queued/sent.

Server-side device token records include `user_id`, `branch_id`, `device_id`, `push_token`, `platform`, `app_version`, and `last_active_at`. The compatibility store keeps queued notification evidence in `mobile.push_notifications`; production delivery should connect this queue to FCM and APNs workers.

## Offline mode and duplicate prevention

The app contains an encrypted local offline queue (`src/offline/localQueue.ts`) for requests created while the network is unavailable. The production app may swap this adapter to SQLite/local DB, but the server contract is already fixed:

1. Local app queue stores the offline request.
2. Internet returns.
3. App calls `/api/v1/sync/offline`.
4. Server creates the central workflow document only once.

Every offline request must include `request_id`, `sync_id`, `created_at`, and `device_id`. The server dedupes by `device_id + request_id`, `device_id + sync_id`, or `device_id + payload_hash`, so three identical purchase requests from the same offline device will create one workflow document and two duplicate responses.

## Server-controlled app version policy

`GET /api/v1/config?current_version=x.y.z` returns:

- `minimum_supported_version`
- `latest_version`
- `force_update_required`
- `maintenance_mode`
- `notice_message`

Example locked in tests: current app `1.0.0`, server minimum `1.1.0` means the app must show an update notice before normal use.

## App environments and build automation

Build profiles and API routing are defined in `apps/worker-mobile/eas.json` and `apps/worker-mobile/app.config.js`:

| App | Env | API |
| --- | --- | --- |
| Development App | `APP_ENV=development` | `DEV_API_URL` |
| Staging App | `APP_ENV=staging` | `STAGING_API_URL` |
| Production App | `APP_ENV=production` | `PROD_API_URL` |

Development and staging builds use separate app schemes and bundle/package IDs (`.dev`, `.staging`) so they can be installed beside the production app.

Automation route:

1. Git push.
2. Mobile API and app checks run in GitHub Actions.
3. Docker/API deployment remains separate from app build.
4. Optional EAS internal build creates iOS/Android builds when `ENABLE_EAS_INTERNAL_BUILD=true` and `EXPO_TOKEN` is configured.
5. TestFlight / Play Internal Testing review.
6. Store/private release after approval.

Supported tools by lane: GitHub Actions or GitLab CI for checks, Fastlane/EAS for app distribution automation, FCM + APNs for push, Firebase Crashlytics or Sentry for crashes, Firebase Analytics/Amplitude for analytics, and Firebase Remote Config or `/api/v1/config` for remote policy.

## Release-review readiness

Assets and review templates are under `apps/worker-mobile/review-assets/`:

- `app-review-checklist.json`: test account/template, test branch data, privacy/terms URLs, support contact, app description, permission reasons.
- `screenshots/ios/*.png` and `screenshots/android/*.png`: login, attendance, payroll preview screenshots.
- `assets/icon.png`, `assets/adaptive-icon.png`, `assets/splash.png`: app icon/splash inputs.

Before launch, replace placeholder URLs/accounts and confirm:

- Login/test account is provided to reviewers.
- Test branch data exists and contains visible attendance/payroll/request flows.
- Privacy policy URL, terms URL, support contact, app description, screenshots, icon, and permission reasons are final.
- Location/notification/biometric permission text matches actual usage.
- App opens without a blank screen when config API is unavailable.
- Customer-facing payment flows, if later added, comply with store payment policies.

## Attendance behavior

1. Worker logs in with MFA and grants required consents.
2. App registers the current Android/iOS device and FCM/APNs token.
3. Check-in prompts biometric auth, captures current GPS, validates geofence, and stores a verified event.
4. While checked in, the app starts a single assigned-site geofence task.
5. Unauthorized exit creates a worker warning and manager/department alert.
6. Approved Bitween attendance workflow windows suppress exit violations.
7. Check-out prompts biometric auth, stores verified event, and stops shift geofencing.

## Verification

Targeted backend tests:

```bash
python3 -m unittest tests.test_api_surfaces tests.test_mobile_app_api tests.test_mobile_attendance -v
```

Mobile TypeScript and release metadata verification:

```bash
cd apps/worker-mobile
npm install
npm run typecheck
npm run verify:release-config
```
