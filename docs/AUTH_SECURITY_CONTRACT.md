# Bitween Auth and Session Security Contract

Status: active production contract seed, 2026-06-09.

## Best-practice evidence basis

- IETF RFC 7519 defines registered JWT claims including `iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, and `jti`; a verifier that is not in the `aud` claim must reject the token when `aud` is present: https://datatracker.ietf.org/doc/html/rfc7519
- OpenID Connect Discovery 1.0 defines provider metadata discovery, including issuer and endpoint metadata used by relying parties: https://openid.net/specs/openid-connect-discovery-1_0.html
- IETF RFC 7517 defines JSON Web Key and JWK Set data structures used for JWKS key material: https://datatracker.ietf.org/doc/html/rfc7517
- IETF RFC 8725 is the JWT Best Current Practices document and reinforces explicit validation to prevent common JWT implementation weaknesses: https://www.rfc-editor.org/rfc/rfc8725.html
- OWASP JWT guidance requires explicit expected algorithm validation and calls out token storage/revocation caveats; JWT is not a universal session-store replacement: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
- W3C WebAuthn Level 3 defines relying-party authentication/registration ceremonies, authenticator selection, user-verification requirements, and client capability signals: https://www.w3.org/TR/webauthn-3/
- FIDO passkey guidance positions passkeys as phishing-resistant, public-key credentials with no shared password secret to steal: https://fidoalliance.org/passkeys/
- NIST SP 800-63B recognizes WebAuthn/FIDO2 as phishing resistant through verifier-name binding and rejects manually entered OTP-style outputs as phishing resistant: https://pages.nist.gov/800-63-4/sp800-63b.html
- NIST SP 800-162 defines ABAC as authorization based on subject, object, operation, and environment attributes evaluated against policy/rules/relationships: https://csrc.nist.gov/pubs/sp/800/162/upd2/final
- NIST RBAC material covers access based on organizational roles and the privileges associated with those roles: https://csrc.nist.gov/projects/role-based-access-control
- NIST defines policy-based access control as combining business roles with policies to determine access privileges: https://csrc.nist.gov/glossary/term/policy_based_access_control
- OWASP authorization guidance emphasizes deny-by-default, least privilege, and authorization logic appropriate to business context: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html

## Product stance

1. Browser code never authenticates itself. It can only start configured identity/onboarding routes and render authenticated application screens after the Rust live session reports a verified session.
2. Sign-in, access request, onboarding, and sign-out are real route contracts:
   - `GET /api/auth/v1/routes` reports configured/missing route status for the signed-out UI.
   - `GET /api/auth/v1/signin`
   - `GET /api/auth/v1/signup`
   - `GET /api/onboarding/v1/start`
   - `POST /api/auth/v1/signout`
3. Action routes fail closed with `auth_route_unconfigured` unless the environment provides configured identity/onboarding URLs. Identity URLs are HTTPS-only, must not contain embedded credentials or fragments, and when `BITWEEN_AUTH_EXPECTED_ISSUER`, `BITWEEN_AUTH_ALLOWED_ORIGINS`, or `BITWEEN_ONBOARDING_ALLOWED_ORIGINS` is configured, the route origin must match that allow-list. The browser preflights route status and disables unavailable actions instead of showing a dead-end missing-address toast. These routes do not create local browser sessions.
4. Sign-out always clears the host-only `__Host-bitween_session` cookie with `Max-Age=0`, `Path=/`, `HttpOnly`, `SameSite=Lax`, and `Secure` before returning configured upstream route metadata or a fail-closed route error.
5. Authenticated shell access requires all of the following server-side facts in the Rust live payload:
   - production auth provider configured,
   - JWT/session verification completed by the identity gateway,
   - registered claim facts present: issuer, audience, subject, and bounded expiration,
   - WebAuthn/passkey user verification completed,
   - a controlled authentication-context level (`routine`, `elevated`, `sensitive`, or `critical`) with a non-future event timestamp,
   - tenant/workplace scope remains available for downstream RBAC/ABAC checks.
6. JWT possession is never authorization. Backend Rust services must still enforce tenant, legal entity, workplace, role, action, document sensitivity, and workflow state on every write/read decision.
7. Authorization uses **ABAC + RBAC + PBAC** together, not a single coarse role check:
   - RBAC: controlled role families such as payroll operator, payroll manager, HR operator, HR manager, approval signer, IT/security admin, platform owner, and support/SRE.
   - ABAC: tenant, legal entity/workplace scope, resource scope, and data classification must match before reads/writes proceed.
   - PBAC: a stable Rust policy id and workflow-state policy decide whether the operation is valid at this point in the payroll/approval lifecycle.
   - Every sensitive decision is deny-by-default and returns only controlled denial reasons (`policy_version_untrusted`, `acr_missing`, `step_up_required`, `role_missing`, `rbac_denied`, `abac_scope_denied`, `abac_data_denied`, `pbac_workflow_denied`) without leaking employee/JWT claims.
8. Sensitive operations require step-up decisions in Rust, not frontend labels:
   - routine: read workspace and user preference update
   - elevated: HR employee read/write and archive read/upload
   - sensitive: archive review/issue resolution, archive canonical admission, archive rollback/recovery, archive source-file synchronization, payroll run/export, payroll policy change, workflow step execution, approval signing
   - critical: tenant-destructive change
9. Payroll lifecycle PBAC gates are enforced server-side: payroll run requires closed source inputs; payroll export requires approved/archived state; approval signing requires calculated or approval-pending state.
10. Live local-review routes that read or mutate sensitive business state must call the Rust authorization decision target before storage/object side effects:
   - HR employee list/read: `hr_employee_read`
   - HR employee create/update/remove: `hr_employee_write`
   - 자료함 list/read: `archive_read`
   - 자료함 upload/intake: `archive_upload`
   - 자료함 review/issue resolution: `archive_review`
   - 자료함 reviewed-row admission into canonical HR/payroll tables: `archive_admit`
   - 자료함 recovery rollback from canonical HR/payroll tables: `archive_rollback`
   - 자료함 source-file synchronization into a derived RustFS workbook version: `archive_sync`
   - Workflow template/canvas read: `workflow_template_read`
   - Workflow template/canvas add/edit/delete/publish preparation: `workflow_template_write`
   - Workflow step execution/runtime action: `workflow_step_execute`
   - Settings preference read: `read_workspace`
   - Settings preference update: `user_preference_update`
   - A denied decision returns `authorization_required` with a controlled reason and must happen before PostgreSQL/local-review store writes or RustFS object PUTs.

## Runtime environment contract

Preview/local review identity routes:

```text
BITWEEN_AUTH_SIGNIN_URL=https://auth.example.com/signin
BITWEEN_AUTH_SIGNUP_URL=https://auth.example.com/request-access
BITWEEN_AUTH_SIGNOUT_URL=https://auth.example.com/signout
BITWEEN_ONBOARDING_START_URL=https://onboarding.example.com/start
BITWEEN_AUTH_ALLOWED_ORIGINS=https://auth.example.com
BITWEEN_ONBOARDING_ALLOWED_ORIGINS=https://onboarding.example.com
```

Rust live session facts supplied by the identity gateway after verification:

```text
BITWEEN_AUTH_CONFIGURED=true
BITWEEN_SESSION_JWT_VERIFIED=true
BITWEEN_SESSION_JWT_ISSUER=https://auth.example.com
BITWEEN_SESSION_JWT_AUDIENCE=bitween-platform
BITWEEN_SESSION_JWT_SUBJECT=<stable-user-subject>
BITWEEN_SESSION_JWT_EXPIRES_AT_UNIX=<future-unix-seconds>
BITWEEN_WEBAUTHN_USER_VERIFIED=true
BITWEEN_SESSION_ACR_LEVEL=elevated
BITWEEN_SESSION_ACR_EVENT_AT_UNIX=<acr-grant-unix-seconds>
BITWEEN_SESSION_ROLE=<role-family>
BITWEEN_SESSION_AUTHZ_POLICY_ID=bitween.authz.rbac-abac-pbac.v1
BITWEEN_SESSION_AUTHZ_TENANT_ID=<authorized-tenant-id>
BITWEEN_SESSION_AUTHZ_LEGAL_ENTITY=<authorized-legal-entity>
BITWEEN_SESSION_AUTHZ_WORKPLACE=<authorized-workplace>
```

Rust JWT/JWKS verifier slice:

```text
BITWEEN_SESSION_JWT=<server-side bearer token, never browser-local storage>
BITWEEN_AUTH_JWKS_JSON=<provider JWKS document or mounted configuration>
BITWEEN_AUTH_OIDC_CONFIGURATION_JSON=<provider .well-known/openid-configuration JSON>
BITWEEN_AUTH_EXPECTED_ISSUER=https://auth.example.com
BITWEEN_AUTH_EXPECTED_AUDIENCE=bitween-platform
BITWEEN_AUTH_EXPECTED_JWKS_URI=https://auth.example.com/.well-known/jwks.json
BITWEEN_SESSION_NOW_UNIX=<optional hermetic test clock>
```

`//crates/payroll-api:auth_session_validate` is the current Rust verification
boundary for local review and service integration. When
`BITWEEN_AUTH_OIDC_CONFIGURATION_JSON` is present, it first validates server-side
OpenID Provider metadata: `issuer` must match `BITWEEN_AUTH_EXPECTED_ISSUER`,
`jwks_uri` must be HTTPS and match `BITWEEN_AUTH_EXPECTED_JWKS_URI` when pinned,
and `id_token_signing_alg_values_supported` must include `RS256`. It then
validates RS256 JWT signatures against RSA JWKS key material, rejects untrusted
`alg` values before
signature verification, enforces `iss`, `aud`, `sub`, `exp`, optional
`nbf`/`iat`, and non-empty `jti`, requires WebAuthn/passkey evidence through
`amr` or an explicit user-verification claim, requires controlled ACR and
tenant/legal-entity/workplace authorization scope claims, and emits sanitized
session facts for downstream Rust targets. It hashes JWT IDs before output and
exits non-zero on verification failure. Preview routing only derives
`BITWEEN_SESSION_*` facts from this verifier when JWT/JWKS config is present;
invalid tokens force unauthenticated Rust target facts instead of falling back
to browser state or stale environment flags.

Rust WebAuthn assertion verification slice:

```text
BITWEEN_WEBAUTHN_ASSERTION_JSON=<server-side WebAuthn assertion evidence JSON>
BITWEEN_WEBAUTHN_RP_ID=bitween.example.com
BITWEEN_WEBAUTHN_EXPECTED_ORIGIN=https://bitween.example.com
BITWEEN_WEBAUTHN_CHALLENGE=<base64url challenge issued by the Rust/session boundary>
BITWEEN_WEBAUTHN_CHALLENGE_ISSUED_AT_UNIX=<challenge-issued unix seconds>
BITWEEN_WEBAUTHN_PREVIOUS_SIGN_COUNT=<previous stored authenticator counter>
BITWEEN_WEBAUTHN_CREDENTIAL_PUBLIC_KEY_X=<base64url P-256 public key x coordinate>
BITWEEN_WEBAUTHN_CREDENTIAL_PUBLIC_KEY_Y=<base64url P-256 public key y coordinate>
```

When `BITWEEN_WEBAUTHN_ASSERTION_JSON` is present,
`auth_session_validate` enforces the server-side relying-party assertion
boundary after JWT/OIDC verification and before the session is accepted. The
assertion verifier exposes schema `bitween.auth-webauthn-assertion.v1`, accepts
only `webauthn.get` client data, requires a fresh matching challenge, binds the
origin to `BITWEEN_WEBAUTHN_EXPECTED_ORIGIN`, binds authenticator data to the
configured RP ID hash, requires user-present and user-verified flags, rejects
replayed nonzero signature counters with `webauthn_sign_count_replayed`, and
verifies the authenticator ES256 signature with the stored P-256 credential
public key. Controlled failure reasons include challenge mismatch, origin
mismatch, RP ID hash mismatch, missing user verification, replayed signature
counter, invalid public key, and invalid signature. Raw authenticator assertions
are transient verification input only; persistence belongs to credential
metadata, public keys, sign counters, audit evidence, and revocation lifecycle
tables, not bearer-token or credential-secret storage.

Rust PostgreSQL session security-store slice:

```text
BITWEEN_AUTH_SESSION_SECURITY_MODE=postgres
BITWEEN_POSTGRES_DSN=postgresql://...
BITWEEN_POSTGRES_TLS_POLICY=verify-full
```

When `BITWEEN_AUTH_SESSION_SECURITY_MODE=postgres` is set,
`auth_session_validate` treats PostgreSQL revocation and audit as part of the
session verification boundary. It applies the controlled
`007_auth_session_security.sql` migration, looks up the verified
`jwt_id_sha256` in `bitween_auth.jwt_revocation`, rejects active revocations
with `jwt_revoked`, and writes `bitween_auth.session_event_audit` evidence
before returning a verified session. Missing or unavailable PostgreSQL
security-store configuration fails closed (`auth_session_security_store_required`
or `auth_session_security_store_unavailable`). The schema stores hashed JWT IDs
and hashed subject IDs only; raw bearer tokens, access tokens, passwords, and
WebAuthn credential secrets must never be stored in these tables.

Expo/native frontend route variables:

```text
EXPO_PUBLIC_BITWEEN_AUTH_SIGNIN_URL=https://auth.example.com/signin
EXPO_PUBLIC_BITWEEN_AUTH_SIGNUP_URL=https://auth.example.com/request-access
EXPO_PUBLIC_BITWEEN_AUTH_SIGNOUT_URL=https://auth.example.com/signout
EXPO_PUBLIC_BITWEEN_ONBOARDING_START_URL=https://onboarding.example.com/start
```

## Implementation guardrails

- Do not add username/password forms to the product shell unless they are backed by the production identity provider and WebAuthn ceremony.
- Do not set `authed` in browser state except from the Rust live payload field `session.authenticated`.
- Do not treat `BITWEEN_AUTH_CONFIGURED=true` as authentication.
- Do not treat a verified JWT as sufficient unless WebAuthn user verification and bounded registered-claim facts are also present.
- Do not treat WebAuthn user verification as enough for sensitive work unless the Rust ACR/step-up policy allows the requested operation.
- Do not treat RBAC alone as authorization. Every Rust write/read gate for sensitive business operations must also evaluate ABAC resource scope and PBAC workflow/policy state.
- Do not let preview/local-review endpoints write HR records, settings, archive metadata, or RustFS objects before `//crates/payroll-api:authz_decision` returns an allowed Rust decision.
- Do not omit legal-entity scope from ABAC. The Rust decision request must compare tenant, legal entity, and workplace where the operation requires workplace scope.
- Do not place employee numbers, JWT claims, auth mode names, or build/runtime implementation details in the operator top bar.
- Use short-lived JWT/API claims, server-side revocation/replay policy, and ABAC + RBAC + PBAC authorization before enabling sensitive writes.

## Remaining Rust backend slices

The current local preview route contract now has a Rust OIDC discovery metadata
validation slice, a Rust RS256 JWT/JWKS validation slice, and a
PostgreSQL-backed revocation/audit slice, but the production Rust API service
still needs dependency-reviewed identity depth for:

- networked OIDC discovery retrieval, JWKS cache refresh, and key rotation,
- distributed revocation/replay controls across service instances,
- session-event retention/export policy and security operations dashboards,
- WebAuthn/passkey registration options, credential enrollment lifecycle,
  recovery/offboarding flows, and browser ceremony adapters around the verified
  server-side assertion boundary,
- step-up verification for payroll export, policy change, privileged HR edits, and approval signing,
- recovery/offboarding flows that preserve audit evidence and least privilege.

## Deferred authorization decisions (recorded 2026-06-10)

- WebAuthn/OIDC re-verification layers are env-gated (`auth_session_validate`);
  when unconfigured, step-up trust rests on IdP-asserted JWT claims. Production
  deployments MUST wire the WebAuthn/OIDC env for sensitive/critical ACR
  operations.

- Tenant scope uses session-scoped `set_config(..., false)` with one connection
  per process invocation; connection pooling across tenants is NOT supported
  until the repository moves to transaction-local scope.

- Sessions carry a single role; multi-role sessions are deferred.

- `AuthzRequest` carries no actor identity, so separation-of-duties (payroll
  runner ≠ approver) is not yet expressible; `platform_owner` bypasses RBAC by
  design and must be treated as an audited break-glass role.

- ABAC scope attributes are display strings (legal entity, workplace) compared
  by exact match; migration to opaque IDs is deferred.

- Payroll workflow state is derived from deployment env flags as a monotonic
  prefix chain (hardened to fail closed); persisting per-period workflow state
  with validated transitions in Postgres is the durable end state.

- RLS (including FORCE) is bypassed for superuser roles — the application DSN
  must use a non-superuser role.

## Data-driven authorization policy (recorded 2026-06-10)

The RBAC/ABAC/PBAC matrix is configurable, not compiled-in. The Rust
authorization layer loads an `AuthzPolicy` at decision time:

- Default: when `BITWEEN_AUTHZ_POLICY_JSON` is unset or blank, the built-in
  policy (`policy_id` `bitween.authz.rbac-abac-pbac.v1`) is used. The built-in
  matrix is byte-for-byte identical to the prior compile-time matrix.
- Override: when `BITWEEN_AUTHZ_POLICY_JSON` is set, its JSON document is parsed
  and validated. Operations remain a closed code-owned set (operation ids are
  touchpoints); roles are open strings (legacy aliases such as `payroll_ops`,
  `tenant_admin`, `approver` are normalized to their canonical role id before
  lookup).
- Fail closed: any parse or validation error makes every decision deny with
  reason `authz_policy_invalid` and `allowed=false`. The layer never silently
  falls back to the built-in policy when the variable is set but invalid.
  This includes the case where `BITWEEN_AUTHZ_POLICY_JSON` is set to a
  non-unicode value (`VarError::NotUnicode`): a configured-but-unreadable
  variable is treated as invalid and fails closed, not as if it were unset.
  Only an unset or blank variable falls back to the built-in policy.

Load-time validation rejects: empty `policy_id`, empty `roles`, unknown
operation id (in `operations` or any grant; `"*"` is the wildcard grant),
unknown ACR / data-class / workflow-state strings, and any role whose
`max_data_class` is below a granted operation's `required_data_class` (dead
grants are configuration errors).

Additional load-time validation hardening:

- Duplicate role keys are rejected. Two JSON role keys that normalize to the
  same canonical role id (for example `it_security_admin` and its alias
  `tenant_admin`, or `payroll_ops` and `payroll_operator`) are a configuration
  error rather than a silent overwrite, so a privileged definition can never
  shadow a restricted one.
- Duplicate operation keys are rejected for the same reason. Operation ids fold
  case, whitespace, and `-`/`_` variants onto one canonical id (for example
  `payroll-export` and `payroll_export`), so colliding keys are a configuration
  error rather than a silent overwrite where a looser workflow window could
  swallow a tighter one.
- The wildcard ceiling rule applies to `"*"`. A role granting `"*"` must have a
  `max_data_class` at least as high as the maximum `required_data_class` across
  all operations (using the policy's per-operation overrides where present and
  the built-in requirement otherwise). A wildcard whose ceiling is below that
  maximum is rejected as a dead grant, exactly like a named operation grant.

Decision behavior for unknown roles: an unknown (non-blank) role still denies
with reason `rbac_denied` (semantically correct under configurable policies),
but the decision's `role` field is `null` for any role that does not resolve to
an entry in the policy's role map. The layer never echoes an arbitrary
caller-supplied role string back into the decision; only roles that exist in the
policy are reflected.

Per-operation workflow-window fallback: when a custom policy omits an operation
from its `operations` map, the operation's workflow window falls back to the
built-in window (the same fallback used for `required_acr`,
`required_data_class`, and `requires_workplace_scope`). The PBAC gate therefore
fails closed for operations that have a built-in window, instead of treating a
missing entry as "all states allowed".

The `inconsistent` workflow state: payroll workflow state is derived from
deployment lifecycle env flags that must form a clean prefix chain (each stage
requires every earlier flag). When the flags do not form a prefix chain — for
example `BITWEEN_PAYROLL_APPROVAL_REQUESTED=true` without
`BITWEEN_PAYROLL_CALCULATED=true`, or `BITWEEN_PAYOUT_PREPARED=true` set alone —
the derived state is `inconsistent` rather than a demotion to the last
consistent prefix. `inconsistent` denies every operation that declares an
explicit workflow window (the built-in gated operations `payroll_run`,
`payroll_export`, `approval_signing`, `workflow_step_execute`,
`payroll_policy_change`, and `workflow_template_write`) with
`pbac_workflow_denied`. Operations with no window (`allowed_workflow_states` of
`null`/omitted) remain allowed in `inconsistent`; that asymmetry is intended.
`inconsistent` is a fail-closed sentinel only: it serializes as the string
`"inconsistent"` but is never accepted by the workflow-state parser, so no
custom policy can declare a window that opens on it.

JSON shape (one custom role granted one operation):

```json
{
  "policy_id": "bitween.authz.rbac-abac-pbac.v1",
  "operations": {
    "payroll_run": {
      "required_acr": "sensitive",
      "required_data_class": "payroll_confidential",
      "requires_workplace_scope": true,
      "allowed_workflow_states": ["inputs_closed", "calculated"]
    }
  },
  "roles": {
    "finance_runner": {
      "max_data_class": "payroll_confidential",
      "grants": ["payroll_run"]
    }
  }
}
```

An `allowed_workflow_states` of `null` or omitted means the operation is
permitted in every workflow state; a `grants` entry of `"*"` grants every
operation (still bounded by the role's `max_data_class` ceiling and the
per-operation ACR/scope/workflow gates).
