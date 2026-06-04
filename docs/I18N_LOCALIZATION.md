# I18n and localization baseline

## Status

Required baseline for Bitween's production React Native, web, and Tauri desktop UI.

## Goal

Bitween must support a fully single-language user experience in Korean, English, Chinese, and Japanese. "Fully single-language" means one active locale owns all navigation, labels, buttons, statuses, errors, onboarding/help text, dashboard copy, policy explanations, desktop shell copy, and auth/security messages for the current user session. Production screens must not mix Korean/English/Chinese/Japanese fallback strings because a translation key is missing.

## Source-backed references

- Expo localization guide for app metadata, locale settings, units, and `Intl` usage: https://docs.expo.dev/guides/localization/
- Expo `expo-localization` API for `getLocales()` / `getCalendars()` behavior: https://docs.expo.dev/versions/latest/sdk/localization/
- MDN JavaScript internationalization guide for `Intl` formatting, collation, plural rules, segmentation, and display names: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Internationalization
- React Native `I18nManager` for layout-direction support if future RTL locales are added: https://reactnative.dev/docs/0.80/i18nmanager
- IETF RFC 5646 / BCP 47 language tags: https://datatracker.ietf.org/doc/rfc5646/
- W3C language-tag guidance for BCP 47 usage: https://www.w3.org/International/articles/language-tags/

## Supported language policy

| Product language | Initial BCP 47 locale tag | Notes |
| --- | --- | --- |
| Korean | `ko-KR` | Default product language and source-of-truth language for Korean labor-law policy copy. |
| English | `en-US` | International business/admin language. |
| Chinese | `zh-Hans-CN` | Initial Chinese target is Simplified Chinese. Add `zh-Hant` only as an explicit future scope. |
| Japanese | `ja-JP` | Japanese business/admin language. |

Language selection precedence:

1. User profile language, if set.
2. Tenant/admin language policy, if enforced.
3. Explicit in-app language switcher.
4. Device/browser locale from Expo/device APIs, mapped to a supported locale.
5. `ko-KR` default.

If an unsupported locale is requested, map to the nearest supported locale and render the entire UI in that chosen locale.

## Full single-language rules

- No user-facing string literals in components, Tauri commands, preview fixtures, or frontend adapters unless the string is a translation key, a test id, or user-provided data.
- All user-facing copy must be pulled from a catalog array. Add copy as `{ key, values }` rows with one value for each supported locale, then reference the key from UI code.
- Every translation key must exist for `ko-KR`, `en-US`, `zh-Hans-CN`, and `ja-JP` before production release.
- Runtime fallback across product languages is not acceptable for production UI. Fallback is allowed only in development/test and must be visible as a failure condition.
- Backend APIs return stable error/status codes and structured parameters. Frontend/desktop localizes the message for the active locale.
- Domain state is stored as stable codes, not translated display text.
- Audit logs store event codes, actor/resource metadata, and optionally the locale used for displayed copy; they do not rely on translated prose as the source of truth.
- Korean legal and policy source names may be retained as data where required, but the surrounding UI copy must be localized into the active language.

## Formatting and content rules

- Use `Intl` for dates, times, numbers, currency, relative time, sorting/collation, list formatting, and plural rules wherever the runtime supports it.
- Use KRW as the payroll/accounting currency unless the domain explicitly supports another currency; localize formatting, not the underlying value.
- Use active-locale calendars/time zones from a documented policy. Payroll/legal deadlines should be tied to the Korean business/legal calendar unless a tenant policy states otherwise.
- CJK layouts must support longer translated labels, line breaking, search, IME composition, and dense tables without clipping.
- Legal/policy explanations must have an official source URL, source language, effective date, last reviewed date, and reviewer/owner before production use.
- Machine translation may draft copy, but payroll, labor-law, WebAuthn/JWT/security, audit, and policy text needs human or domain-owner review before release.

## Catalog-array contract

The initial catalog lives under `apps/bitween-platform-ui/src/i18n/catalog.json` and is verified by `npm run verify:i18n --prefix apps/bitween-platform-ui`.

Required shape:

```json
{
  "supportedLocales": ["ko-KR", "en-US", "zh-Hans-CN", "ja-JP"],
  "messages": [
    {
      "key": "domain.screen.element",
      "values": {
        "ko-KR": "...",
        "en-US": "...",
        "zh-Hans-CN": "...",
        "ja-JP": "..."
      }
    }
  ],
  "languageDisplayNames": [
    {
      "locale": "ko-KR",
      "values": {
        "ko-KR": "한국어",
        "en-US": "Korean",
        "zh-Hans-CN": "韩语",
        "ja-JP": "韓国語"
      }
    }
  ]
}
```

Do not scatter copy across multiple files just because a component is small. Components should import a translator/formatter and pull from the catalog. Domain lists can still be arrays, but their display labels should be message keys or complete localized values, not inline prose.

## Implementation architecture

Current React Native baseline:

1. `apps/bitween-platform-ui/src/i18n/` owns locale configuration, catalog-array loading, translation lookup, locale normalization, and language option helpers.
2. `apps/bitween-platform-ui/src/i18n/catalog.json` stores current navigation, dashboard, table, form, auth, permission, action, toast, and preview copy as catalog-array rows.
3. `apps/bitween-platform-ui/scripts/verify-i18n-catalog.mjs` fails when any locale is missing a catalog value or when localized CJK/Korean/Japanese/Chinese copy appears outside `catalog.json` in the React Native/static preview source.
4. Source arrays in `src/data.ts`, `src/screens.tsx`, `src/theme.ts`, `src/viewModel.ts`, and `preview/app.js` hold stable ids, tones, targets, dates, and sample data; display text is pulled from the catalog.

Future implementation PRs should expand:

1. Compile-time key typing and test coverage around the catalog.
2. Profile/tenant persistence for the active language selection.
3. Localized API error rendering through stable backend error codes.
4. Tauri desktop metadata/localized shell copy that follows the React Native source of truth.
5. Snapshot/visual checks for Korean, English, Chinese, and Japanese on dense dashboards and forms.

No new localization dependency should be added until the implementation PR compares it against the current Expo/React Native/TypeScript constraints and records the decision in an ADR or implementation note.

## QA matrix

Each production UI slice must be reviewed in all four language modes:

| Area | Required check |
| --- | --- |
| Navigation and launcher | All labels, module names, badges, and empty states render in the selected language only. |
| Payroll/HR/workflow/trip/KPI | Statuses, due dates, legal/policy helper text, validation errors, and audit actions are localized. |
| Manager dashboards | Ongoing/completed/overdue/escalation views remain readable with translated labels and dense data. |
| Auth/security | WebAuthn/passkey prompts, JWT/session errors, step-up verification copy, and recovery/offboarding states are localized. |
| Compliance cockpit | Korean labor-law, social-insurance, NTS/e-tax, wage, leave, and working-time readiness messages have source/effective-date metadata. |
| Desktop/Tauri | Window/app metadata, native dialogs, desktop command errors, and capability-denied states match the active language. |
| Accessibility | Screen-reader labels, keyboard flow, focus announcements, and non-color status indicators are localized. |
| Performance | Locale loading does not regress Core Web Vitals or desktop startup budgets. |

## Non-goals

- Do not add a second desktop-only localization system.
- Do not translate user-entered names, attachments, imported files, or official document identifiers unless the domain explicitly stores a translation.
- Do not encode legal thresholds as translated strings.
- Do not add `zh-Hant`/Traditional Chinese, RTL languages, or additional jurisdictions until explicitly scoped.
