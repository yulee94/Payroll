# Bitween Worker Mobile

Cross-platform Expo React Native worker app for Android and iOS.

## Runtime

- Expo SDK 56 / React Native 0.85
- Node.js 22.13.x or newer for SDK 56
- Private employee distribution first via EAS internal builds, TestFlight, Play Internal/Closed Testing, or MDM

## Core device capabilities

- `expo-location`: check-in/out GPS and shift-bounded geofence/background events
- `expo-local-authentication`: device-only fingerprint/Face ID/Touch ID pass/fail
- `expo-secure-store`: mobile bearer token, branch/device scope, and encrypted offline queue
- `expo-notifications`: native FCM/APNs device token registration and push delivery surface

## Mobile API routing

The app talks only to the separated **Mobile App API** surface, not the web/admin API.

- API host root: `expo.extra.mobileApiBaseUrl`
- Default app API version: `expo.extra.mobileApiVersion`
- v1 examples: `/api/v1/login`, `/api/v1/branches`, `/api/v1/tasks`
- v2 expansion example: `/api/v2/tasks`

Environment routing is dynamic in `app.config.js`:

| Build | Env | API variable |
| --- | --- | --- |
| Development App | `APP_ENV=development` | `DEV_API_URL` |
| Staging App | `APP_ENV=staging` | `STAGING_API_URL` |
| Production App | `APP_ENV=production` | `PROD_API_URL` |

Development and staging builds use separate app schemes and bundle/package IDs (`.dev`, `.staging`) so they can be installed beside the production app.

## Login and app-use order

Company account login → OTP/MFA → native push token + device registration → branch/permission check → consent capture → app use.

The app must not store raw passwords, resident-registration numbers, card numbers, plaintext sensitive data, or long-lived admin tokens. Required local values use iOS Keychain/Android Keystore through SecureStore.

## Offline queue

`src/offline/localQueue.ts` stores offline-created requests with `request_id`, `sync_id`, `created_at`, and `device_id`, then calls `/api/v1/sync/offline` when the app comes back online. The server dedupes duplicate offline submissions by device/request/sync/payload hash.

## Release commands

```bash
npm run typecheck
npm run verify:release-config
npm run build:development
npm run build:staging
npm run build:production
npm run submit:production
```

`review-assets/app-review-checklist.json` must be filled with real review account, privacy URL, terms URL, support contact, permission reasons, and test branch data before submission.
