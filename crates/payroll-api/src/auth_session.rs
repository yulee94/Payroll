use ring::signature::{
    ECDSA_P256_SHA256_ASN1, RSA_PKCS1_2048_8192_SHA256, RsaPublicKeyComponents,
    UnparsedPublicKey,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::auth_policy::{AUTHZ_POLICY_ID, AuthAcrLevel};

pub const AUTH_SESSION_SCHEMA: &str = "bitween.auth-session.v1";
pub const AUTH_OIDC_DISCOVERY_SCHEMA: &str = "bitween.auth-oidc-discovery.v1";
pub const AUTH_WEBAUTHN_ASSERTION_SCHEMA: &str = "bitween.auth-webauthn-assertion.v1";
pub const AUTH_ROUTES_SCHEMA: &str = "bitween.auth-routes.v1";
pub const AUTH_ROUTE_ACTION_SCHEMA: &str = "bitween.auth-route-action.v1";
pub const AUTH_SESSION_ALLOWED_ALGORITHM: &str = "RS256";
pub const AUTH_WEBAUTHN_CHALLENGE_TTL_SECONDS: u64 = 300;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AuthSessionVerifierConfig {
    pub expected_issuer: String,
    pub expected_audience: String,
    pub now_unix: u64,
}

impl AuthSessionVerifierConfig {
    pub fn new(
        expected_issuer: impl Into<String>,
        expected_audience: impl Into<String>,
        now_unix: u64,
    ) -> Self {
        Self {
            expected_issuer: clean(expected_issuer.into()),
            expected_audience: clean(expected_audience.into()),
            now_unix,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OidcDiscoveryVerifierConfig {
    pub expected_issuer: String,
    pub expected_jwks_uri: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct WebAuthnAssertionVerifierConfig {
    pub rp_id: String,
    pub expected_origin: String,
    pub challenge: String,
    pub challenge_issued_at_unix: u64,
    pub now_unix: u64,
    pub previous_sign_count: u32,
    pub credential_public_key_x_base64url: String,
    pub credential_public_key_y_base64url: String,
}

impl WebAuthnAssertionVerifierConfig {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        rp_id: impl Into<String>,
        expected_origin: impl Into<String>,
        challenge: impl Into<String>,
        challenge_issued_at_unix: u64,
        now_unix: u64,
        previous_sign_count: u32,
        credential_public_key_x_base64url: impl Into<String>,
        credential_public_key_y_base64url: impl Into<String>,
    ) -> Self {
        Self {
            rp_id: clean(rp_id.into()),
            expected_origin: clean_uri(expected_origin.into()),
            challenge: clean(challenge.into()),
            challenge_issued_at_unix,
            now_unix,
            previous_sign_count,
            credential_public_key_x_base64url: clean(credential_public_key_x_base64url.into()),
            credential_public_key_y_base64url: clean(credential_public_key_y_base64url.into()),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq)]
pub struct WebAuthnAssertionInput {
    pub client_data_json_base64url: String,
    pub authenticator_data_base64url: String,
    pub signature_der_base64url: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct WebAuthnAssertionVerification {
    pub schema: &'static str,
    pub ok: bool,
    pub verified: bool,
    pub reason: &'static str,
    pub user_present: bool,
    pub user_verified: bool,
    pub sign_count: u32,
    pub rp_id_hash_sha256: String,
    pub challenge_sha256: String,
}

impl WebAuthnAssertionVerification {
    pub fn denied(reason: &'static str) -> Self {
        Self {
            schema: AUTH_WEBAUTHN_ASSERTION_SCHEMA,
            ok: false,
            verified: false,
            reason,
            user_present: false,
            user_verified: false,
            sign_count: 0,
            rp_id_hash_sha256: String::new(),
            challenge_sha256: String::new(),
        }
    }
}

impl OidcDiscoveryVerifierConfig {
    pub fn new(
        expected_issuer: impl Into<String>,
        expected_jwks_uri: Option<impl Into<String>>,
    ) -> Self {
        Self {
            expected_issuer: clean(expected_issuer.into()),
            expected_jwks_uri: expected_jwks_uri
                .map(|value| clean_uri(value.into()))
                .filter(|value| !value.is_empty()),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct OidcDiscoveryValidation {
    pub schema: &'static str,
    pub ok: bool,
    pub verified: bool,
    pub reason: &'static str,
    pub issuer: String,
    pub jwks_uri: String,
    pub response_types_supported: Vec<String>,
    pub subject_types_supported: Vec<String>,
    pub signing_algorithms: Vec<String>,
}

impl OidcDiscoveryValidation {
    pub fn denied(reason: &'static str) -> Self {
        Self {
            schema: AUTH_OIDC_DISCOVERY_SCHEMA,
            ok: false,
            verified: false,
            reason,
            issuer: String::new(),
            jwks_uri: String::new(),
            response_types_supported: Vec::new(),
            subject_types_supported: Vec::new(),
            signing_algorithms: Vec::new(),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct AuthSessionVerification {
    pub schema: &'static str,
    pub ok: bool,
    pub verified: bool,
    pub reason: &'static str,
    pub algorithm: String,
    pub key_id: String,
    pub issuer: String,
    pub audience: String,
    pub subject: String,
    pub expires_at_unix: u64,
    pub not_before_unix: Option<u64>,
    pub issued_at_unix: Option<u64>,
    pub jwt_id_sha256: String,
    pub webauthn_user_verified: bool,
    pub acr_level: String,
    pub acr_event_at_unix: u64,
    pub role: String,
    pub authz_policy_id: String,
    pub authorized_tenant_id: String,
    pub authorized_legal_entity: String,
    pub authorized_workplace: String,
}

impl AuthSessionVerification {
    pub fn denied(reason: &'static str) -> Self {
        Self {
            schema: AUTH_SESSION_SCHEMA,
            ok: false,
            verified: false,
            reason,
            algorithm: String::new(),
            key_id: String::new(),
            issuer: String::new(),
            audience: String::new(),
            subject: String::new(),
            expires_at_unix: 0,
            not_before_unix: None,
            issued_at_unix: None,
            jwt_id_sha256: String::new(),
            webauthn_user_verified: false,
            acr_level: String::new(),
            acr_event_at_unix: 0,
            role: String::new(),
            authz_policy_id: String::new(),
            authorized_tenant_id: String::new(),
            authorized_legal_entity: String::new(),
            authorized_workplace: String::new(),
        }
    }
}

#[derive(Debug, Deserialize)]
struct JwtHeader {
    alg: String,
    kid: Option<String>,
    typ: Option<String>,
}

#[derive(Debug, Deserialize)]
struct JwtClaims {
    iss: String,
    sub: String,
    aud: JwtAudience,
    exp: u64,
    nbf: Option<u64>,
    iat: Option<u64>,
    jti: Option<String>,
    acr: Option<String>,
    auth_time: Option<u64>,
    amr: Option<Vec<String>>,
    webauthn_user_verified: Option<bool>,
    bitween_role: Option<String>,
    bitween_tenant_id: Option<String>,
    bitween_legal_entity: Option<String>,
    bitween_workplace: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(untagged)]
enum JwtAudience {
    Single(String),
    Multiple(Vec<String>),
}

impl JwtAudience {
    fn contains(&self, expected: &str) -> bool {
        match self {
            Self::Single(value) => value == expected,
            Self::Multiple(values) => values.iter().any(|value| value == expected),
        }
    }

    fn display_for(&self, expected: &str) -> String {
        if self.contains(expected) {
            expected.to_owned()
        } else {
            match self {
                Self::Single(value) => value.clone(),
                Self::Multiple(values) => values.join(","),
            }
        }
    }
}

#[derive(Debug, Deserialize)]
struct JwksDocument {
    keys: Vec<JwkKey>,
}

#[derive(Debug, Deserialize)]
struct JwkKey {
    kty: String,
    kid: Option<String>,
    alg: Option<String>,
    #[serde(rename = "use")]
    use_: Option<String>,
    n: Option<String>,
    e: Option<String>,
}

#[derive(Debug, Deserialize)]
struct OidcProviderConfiguration {
    issuer: String,
    jwks_uri: String,
    response_types_supported: Vec<String>,
    subject_types_supported: Vec<String>,
    id_token_signing_alg_values_supported: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct WebAuthnClientData {
    #[serde(rename = "type")]
    ceremony_type: String,
    challenge: String,
    origin: String,
}

pub fn validate_oidc_discovery(
    discovery_json: &str,
    config: &OidcDiscoveryVerifierConfig,
) -> OidcDiscoveryValidation {
    if discovery_json.trim().is_empty() {
        return OidcDiscoveryValidation::denied("oidc_discovery_missing");
    }
    if config.expected_issuer.is_empty() {
        return OidcDiscoveryValidation::denied("oidc_config_missing");
    }
    let discovery = match serde_json::from_str::<OidcProviderConfiguration>(discovery_json) {
        Ok(value) => value,
        Err(_) => return OidcDiscoveryValidation::denied("oidc_discovery_invalid"),
    };
    let issuer = clean_uri(discovery.issuer);
    if issuer != config.expected_issuer {
        return OidcDiscoveryValidation::denied("oidc_issuer_mismatch");
    }
    let jwks_uri = clean_uri(discovery.jwks_uri);
    if !is_trusted_https_url(&jwks_uri) {
        return OidcDiscoveryValidation::denied("oidc_jwks_uri_untrusted");
    }
    if config
        .expected_jwks_uri
        .as_ref()
        .is_some_and(|expected| expected != &jwks_uri)
    {
        return OidcDiscoveryValidation::denied("oidc_jwks_uri_mismatch");
    }
    let signing_algorithms = clean_values(discovery.id_token_signing_alg_values_supported);
    if !signing_algorithms
        .iter()
        .any(|algorithm| algorithm == AUTH_SESSION_ALLOWED_ALGORITHM)
    {
        return OidcDiscoveryValidation::denied("oidc_rs256_unsupported");
    }
    let response_types_supported = clean_values(discovery.response_types_supported);
    if response_types_supported.is_empty() {
        return OidcDiscoveryValidation::denied("oidc_response_types_missing");
    }
    let subject_types_supported = clean_values(discovery.subject_types_supported);
    if subject_types_supported.is_empty() {
        return OidcDiscoveryValidation::denied("oidc_subject_types_missing");
    }

    OidcDiscoveryValidation {
        schema: AUTH_OIDC_DISCOVERY_SCHEMA,
        ok: true,
        verified: true,
        reason: "verified",
        issuer,
        jwks_uri,
        response_types_supported,
        subject_types_supported,
        signing_algorithms,
    }
}

pub fn verify_webauthn_assertion(
    assertion: &WebAuthnAssertionInput,
    config: &WebAuthnAssertionVerifierConfig,
) -> WebAuthnAssertionVerification {
    if config.rp_id.is_empty()
        || config.expected_origin.is_empty()
        || config.challenge.is_empty()
        || config.credential_public_key_x_base64url.is_empty()
        || config.credential_public_key_y_base64url.is_empty()
    {
        return WebAuthnAssertionVerification::denied("webauthn_config_missing");
    }
    if !is_trusted_https_url(&config.expected_origin) {
        return WebAuthnAssertionVerification::denied("webauthn_origin_untrusted");
    }
    if config.challenge_issued_at_unix == 0
        || config.challenge_issued_at_unix > config.now_unix
        || config.now_unix - config.challenge_issued_at_unix > AUTH_WEBAUTHN_CHALLENGE_TTL_SECONDS
    {
        return WebAuthnAssertionVerification::denied("webauthn_challenge_expired");
    }

    let client_data_bytes = match decode_base64url(&assertion.client_data_json_base64url) {
        Ok(value) => value,
        Err(_) => return WebAuthnAssertionVerification::denied("webauthn_client_data_invalid"),
    };
    let client_data = match serde_json::from_slice::<WebAuthnClientData>(&client_data_bytes) {
        Ok(value) => value,
        Err(_) => return WebAuthnAssertionVerification::denied("webauthn_client_data_invalid"),
    };
    if client_data.ceremony_type != "webauthn.get" {
        return WebAuthnAssertionVerification::denied("webauthn_type_invalid");
    }
    if clean(client_data.challenge) != config.challenge {
        return WebAuthnAssertionVerification::denied("webauthn_challenge_mismatch");
    }
    if clean_uri(client_data.origin) != config.expected_origin {
        return WebAuthnAssertionVerification::denied("webauthn_origin_mismatch");
    }

    let authenticator_data = match decode_base64url(&assertion.authenticator_data_base64url) {
        Ok(value) => value,
        Err(_) => {
            return WebAuthnAssertionVerification::denied("webauthn_authenticator_data_invalid");
        }
    };
    if authenticator_data.len() < 37 {
        return WebAuthnAssertionVerification::denied("webauthn_authenticator_data_invalid");
    }
    let expected_rp_id_hash = Sha256::digest(config.rp_id.as_bytes());
    let rp_id_hash = &authenticator_data[..32];
    if rp_id_hash != expected_rp_id_hash.as_slice() {
        return WebAuthnAssertionVerification::denied("webauthn_rp_id_hash_mismatch");
    }
    let flags = authenticator_data[32];
    let user_present = flags & 0x01 == 0x01;
    let user_verified = flags & 0x04 == 0x04;
    if !user_present {
        return WebAuthnAssertionVerification::denied("webauthn_user_not_present");
    }
    if !user_verified {
        return WebAuthnAssertionVerification::denied("webauthn_user_not_verified");
    }
    let sign_count = u32::from_be_bytes([
        authenticator_data[33],
        authenticator_data[34],
        authenticator_data[35],
        authenticator_data[36],
    ]);
    if config.previous_sign_count > 0
        && sign_count > 0
        && sign_count <= config.previous_sign_count
    {
        return WebAuthnAssertionVerification::denied("webauthn_sign_count_replayed");
    }

    let public_key = match webauthn_public_key_from_xy(config) {
        Ok(value) => value,
        Err(reason) => return WebAuthnAssertionVerification::denied(reason),
    };
    let signature = match decode_base64url(&assertion.signature_der_base64url) {
        Ok(value) => value,
        Err(_) => return WebAuthnAssertionVerification::denied("webauthn_signature_invalid"),
    };
    let mut signed_data = authenticator_data.clone();
    signed_data.extend_from_slice(&Sha256::digest(&client_data_bytes));
    if UnparsedPublicKey::new(&ECDSA_P256_SHA256_ASN1, public_key)
        .verify(&signed_data, &signature)
        .is_err()
    {
        return WebAuthnAssertionVerification::denied("webauthn_signature_invalid");
    }

    WebAuthnAssertionVerification {
        schema: AUTH_WEBAUTHN_ASSERTION_SCHEMA,
        ok: true,
        verified: true,
        reason: "verified",
        user_present,
        user_verified,
        sign_count,
        rp_id_hash_sha256: hex_bytes(rp_id_hash),
        challenge_sha256: hex_sha256(&config.challenge),
    }
}

fn webauthn_public_key_from_xy(
    config: &WebAuthnAssertionVerifierConfig,
) -> Result<Vec<u8>, &'static str> {
    let x = decode_base64url(&config.credential_public_key_x_base64url)
        .map_err(|_| "webauthn_public_key_invalid")?;
    let y = decode_base64url(&config.credential_public_key_y_base64url)
        .map_err(|_| "webauthn_public_key_invalid")?;
    if x.len() != 32 || y.len() != 32 {
        return Err("webauthn_public_key_invalid");
    }
    let mut public_key = Vec::with_capacity(65);
    public_key.push(0x04);
    public_key.extend_from_slice(&x);
    public_key.extend_from_slice(&y);
    Ok(public_key)
}

pub fn verify_jwt_session(
    token: &str,
    jwks_json: &str,
    config: &AuthSessionVerifierConfig,
) -> AuthSessionVerification {
    if token.trim().is_empty() {
        return AuthSessionVerification::denied("token_missing");
    }
    if config.expected_issuer.is_empty() || config.expected_audience.is_empty() {
        return AuthSessionVerification::denied("verifier_config_missing");
    }

    let mut parts = token.split('.');
    let Some(header_part) = parts.next() else {
        return AuthSessionVerification::denied("jwt_format_invalid");
    };
    let Some(payload_part) = parts.next() else {
        return AuthSessionVerification::denied("jwt_format_invalid");
    };
    let Some(signature_part) = parts.next() else {
        return AuthSessionVerification::denied("jwt_format_invalid");
    };
    if parts.next().is_some() || header_part.is_empty() || payload_part.is_empty() || signature_part.is_empty() {
        return AuthSessionVerification::denied("jwt_format_invalid");
    }

    let header = match decode_json_part::<JwtHeader>(header_part) {
        Ok(value) => value,
        Err(reason) => return AuthSessionVerification::denied(reason),
    };
    if header.alg != AUTH_SESSION_ALLOWED_ALGORITHM {
        return AuthSessionVerification::denied("jwt_alg_untrusted");
    }
    if let Some(typ) = &header.typ {
        if typ != "JWT" {
            return AuthSessionVerification::denied("jwt_type_invalid");
        }
    }
    let key_id = clean(header.kid.unwrap_or_default());
    if key_id.is_empty() {
        return AuthSessionVerification::denied("jwt_kid_missing");
    }

    let claims = match decode_json_part::<JwtClaims>(payload_part) {
        Ok(value) => value,
        Err(_) => return AuthSessionVerification::denied("jwt_payload_invalid"),
    };

    let jwks = match serde_json::from_str::<JwksDocument>(jwks_json) {
        Ok(value) => value,
        Err(_) => return AuthSessionVerification::denied("jwks_invalid"),
    };
    let Some(jwk) = jwks.keys.iter().find(|key| key.kid.as_deref() == Some(key_id.as_str())) else {
        return AuthSessionVerification::denied("jwks_key_missing");
    };
    if !jwk.trusts_rs256_signature() {
        return AuthSessionVerification::denied("jwks_key_untrusted");
    }
    let Some(n) = jwk.n.as_deref().and_then(|value| decode_base64url(value).ok()) else {
        return AuthSessionVerification::denied("jwks_key_invalid");
    };
    let Some(e) = jwk.e.as_deref().and_then(|value| decode_base64url(value).ok()) else {
        return AuthSessionVerification::denied("jwks_key_invalid");
    };
    let signature = match decode_base64url(signature_part) {
        Ok(value) => value,
        Err(_) => return AuthSessionVerification::denied("jwt_signature_invalid"),
    };
    let signing_input = format!("{header_part}.{payload_part}");
    if (RsaPublicKeyComponents { n: &n, e: &e })
        .verify(
            &RSA_PKCS1_2048_8192_SHA256,
            signing_input.as_bytes(),
            &signature,
        )
        .is_err()
    {
        return AuthSessionVerification::denied("jwt_signature_invalid");
    }

    validate_claims(header.alg, key_id, claims, config)
}

impl JwkKey {
    fn trusts_rs256_signature(&self) -> bool {
        self.kty == "RSA"
            && self.alg.as_deref().is_none_or(|alg| alg == AUTH_SESSION_ALLOWED_ALGORITHM)
            && self.use_.as_deref().is_none_or(|use_| use_ == "sig")
    }
}

fn validate_claims(
    algorithm: String,
    key_id: String,
    claims: JwtClaims,
    config: &AuthSessionVerifierConfig,
) -> AuthSessionVerification {
    if claims.iss != config.expected_issuer {
        return AuthSessionVerification::denied("jwt_issuer_mismatch");
    }
    if !claims.aud.contains(&config.expected_audience) {
        return AuthSessionVerification::denied("jwt_audience_mismatch");
    }
    let subject = clean(claims.sub);
    if subject.is_empty() {
        return AuthSessionVerification::denied("jwt_subject_missing");
    }
    if claims.exp <= config.now_unix {
        return AuthSessionVerification::denied("jwt_expired");
    }
    if claims.nbf.is_some_and(|nbf| nbf > config.now_unix) {
        return AuthSessionVerification::denied("jwt_not_yet_valid");
    }
    if claims.iat.is_some_and(|iat| iat > config.now_unix + 60) {
        return AuthSessionVerification::denied("jwt_issued_in_future");
    }
    let jwt_id = clean(claims.jti.unwrap_or_default());
    if jwt_id.is_empty() {
        return AuthSessionVerification::denied("jwt_id_missing");
    }
    let webauthn_user_verified = claims.webauthn_user_verified.unwrap_or(false)
        || claims.amr.as_ref().is_some_and(|values| {
            values.iter().any(|value| {
                let normalized = value.trim().to_ascii_lowercase();
                matches!(normalized.as_str(), "webauthn" | "passkey" | "fido2")
            })
        });
    if !webauthn_user_verified {
        return AuthSessionVerification::denied("webauthn_user_verification_missing");
    }
    let acr_level = clean(claims.acr.unwrap_or_default());
    if AuthAcrLevel::parse(&acr_level).is_none() {
        return AuthSessionVerification::denied("acr_missing");
    }
    let acr_event_at_unix = claims.auth_time.unwrap_or_default();
    if acr_event_at_unix == 0 || acr_event_at_unix > config.now_unix {
        return AuthSessionVerification::denied("acr_event_invalid");
    }
    let role = clean(claims.bitween_role.unwrap_or_default());
    if role.is_empty() {
        return AuthSessionVerification::denied("role_missing");
    }
    let authorized_tenant_id = clean(claims.bitween_tenant_id.unwrap_or_default());
    let authorized_legal_entity = clean(claims.bitween_legal_entity.unwrap_or_default());
    let authorized_workplace = clean(claims.bitween_workplace.unwrap_or_default());
    if authorized_tenant_id.is_empty()
        || authorized_legal_entity.is_empty()
        || authorized_workplace.is_empty()
    {
        return AuthSessionVerification::denied("tenant_scope_missing");
    }

    AuthSessionVerification {
        schema: AUTH_SESSION_SCHEMA,
        ok: true,
        verified: true,
        reason: "verified",
        algorithm,
        key_id,
        issuer: claims.iss,
        audience: claims.aud.display_for(&config.expected_audience),
        subject,
        expires_at_unix: claims.exp,
        not_before_unix: claims.nbf,
        issued_at_unix: claims.iat,
        jwt_id_sha256: hex_sha256(&jwt_id),
        webauthn_user_verified,
        acr_level,
        acr_event_at_unix,
        role,
        authz_policy_id: AUTHZ_POLICY_ID.to_owned(),
        authorized_tenant_id,
        authorized_legal_entity,
        authorized_workplace,
    }
}

fn decode_json_part<T: for<'de> Deserialize<'de>>(part: &str) -> Result<T, &'static str> {
    let bytes = decode_base64url(part).map_err(|_| "jwt_header_invalid")?;
    serde_json::from_slice::<T>(&bytes).map_err(|_| "jwt_header_invalid")
}

fn decode_base64url(input: &str) -> Result<Vec<u8>, ()> {
    if input.contains('=') {
        return Err(());
    }
    let mut output = Vec::with_capacity(input.len() * 3 / 4);
    let mut buffer: u32 = 0;
    let mut bits: u8 = 0;
    for byte in input.bytes() {
        let value = match byte {
            b'A'..=b'Z' => byte - b'A',
            b'a'..=b'z' => byte - b'a' + 26,
            b'0'..=b'9' => byte - b'0' + 52,
            b'-' => 62,
            b'_' => 63,
            _ => return Err(()),
        } as u32;
        buffer = (buffer << 6) | value;
        bits += 6;
        while bits >= 8 {
            bits -= 8;
            output.push(((buffer >> bits) & 0xff) as u8);
        }
    }
    if bits > 0 && (buffer & ((1 << bits) - 1)) != 0 {
        return Err(());
    }
    Ok(output)
}

fn hex_sha256(value: &str) -> String {
    let digest = Sha256::digest(value.as_bytes());
    hex_bytes(&digest)
}

fn hex_bytes(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn clean(value: String) -> String {
    value.trim().chars().take(256).collect()
}

fn clean_uri(value: String) -> String {
    value.trim().chars().take(512).collect()
}

fn clean_values(values: Vec<String>) -> Vec<String> {
    values
        .into_iter()
        .map(clean)
        .filter(|value| !value.is_empty())
        .take(32)
        .collect()
}

fn is_trusted_https_url(value: &str) -> bool {
    value.starts_with("https://")
        && !value.contains(char::is_whitespace)
        && !value.contains('#')
        && !value.contains('?')
        && value.len() <= 512
}

#[cfg(test)]
mod tests {
    use super::*;
    use ring::rand::SystemRandom;
    use ring::signature::{ECDSA_P256_SHA256_ASN1_SIGNING, EcdsaKeyPair, KeyPair};

    const TEST_TOKEN: &str = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InRlc3Qta2V5LTEifQ.eyJpc3MiOiJodHRwczovL2F1dGguYWNtZS5leGFtcGxlIiwic3ViIjoidXNlci1saXZlLW9wcyIsImF1ZCI6ImJpdHdlZW4tcGxhdGZvcm0iLCJleHAiOjQxMDI0NDQ4MDAsIm5iZiI6MTcwMDAwMDAwMCwiaWF0IjoxNzAwMDAwMDAwLCJqdGkiOiJzZXNzaW9uLXRva2VuLTAwMSIsImFjciI6InNlbnNpdGl2ZSIsImF1dGhfdGltZSI6MTcwMDAwMDAwMCwiYW1yIjpbInB3ZCIsIndlYmF1dGhuIl0sImJpdHdlZW5fcm9sZSI6InBheXJvbGxfbWFuYWdlciIsImJpdHdlZW5fdGVuYW50X2lkIjoidGVuYW50LWFjbWUiLCJiaXR3ZWVuX2xlZ2FsX2VudGl0eSI6IkFjbWUiLCJiaXR3ZWVuX3dvcmtwbGFjZSI6IlNlb3VsIn0.C5cBG8-5NUAfjf2zzua4IvNtYSLs11eHTF96G1kwSSDxfsBNCBw731oJAbxGmnlzZi9RVZTH0bjC2sf5ldqIb5T0g2z3KyH7V1DeMg0uZERm7J4evWaJ3VnHh5RYEgO06mM7zD9XBU7hS4-_32Ol1wQ4KPuoH9wfTc9798YKTlIIm_hYgH42IUoB_Snws2GgdVJ-CwnCKwZubIJ_bdPj8c6UXREaxlz6Up5Z8Xfgfbtrt5ENnAmCe4NX6Uy605ukwzVUSK7pep7wD-u6UAB0k2SbSAEz-oL_6CiYJcHLx5CVHl4BceaB_coaGL4mdOw-nflOelaL8GPDN-jhS5NiJw";
    const TEST_JWKS: &str = r#"{"keys":[{"kty":"RSA","n":"mwaczqZWd1GkBo8DQtJAEjFd4v4XGkBQt1KI7Flawe0lW9omwfolE6dut3Rrff4qhI3ncSjIOlf8NZ4EMmkH5wL6ktdRj0MWpDvSj7ZPAi1RvdKL6KrUGxpMtQymivPn2dd37KtaxZB4vbXYMU8vPJki3tjpI3bGNePRvmd8eYP2h5QmDXZFcqZJZ3oBIzKxH7NFjgZUetysXNvZLKqvLdnez_uCD83KoqV81l97IMJCHFBmoTnO3wyD0QXnBvNbyW7Sat8ekgx9PHuv8AhWjze9di4dy7n-Im2fN7Mry0afvFCpxmqj-vqVru8igUw13ngqq9vxjQ047zs5SWMMgQ","e":"AQAB","kid":"test-key-1","alg":"RS256","use":"sig"}]}"#;
    const TEST_OIDC_DISCOVERY: &str = r#"{"issuer":"https://auth.acme.example","jwks_uri":"https://auth.acme.example/.well-known/jwks.json","response_types_supported":["code"],"subject_types_supported":["public"],"id_token_signing_alg_values_supported":["RS256"]}"#;

    fn config(now_unix: u64) -> AuthSessionVerifierConfig {
        AuthSessionVerifierConfig::new(
            "https://auth.acme.example",
            "bitween-platform",
            now_unix,
        )
    }

    fn base64url_encode(bytes: &[u8]) -> String {
        const TABLE: &[u8; 64] =
            b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
        let mut output = String::with_capacity(bytes.len().div_ceil(3) * 4);
        let mut index = 0;
        while index + 3 <= bytes.len() {
            let chunk = ((bytes[index] as u32) << 16)
                | ((bytes[index + 1] as u32) << 8)
                | bytes[index + 2] as u32;
            output.push(TABLE[((chunk >> 18) & 0x3f) as usize] as char);
            output.push(TABLE[((chunk >> 12) & 0x3f) as usize] as char);
            output.push(TABLE[((chunk >> 6) & 0x3f) as usize] as char);
            output.push(TABLE[(chunk & 0x3f) as usize] as char);
            index += 3;
        }
        match bytes.len() - index {
            1 => {
                let chunk = (bytes[index] as u32) << 16;
                output.push(TABLE[((chunk >> 18) & 0x3f) as usize] as char);
                output.push(TABLE[((chunk >> 12) & 0x3f) as usize] as char);
            }
            2 => {
                let chunk = ((bytes[index] as u32) << 16) | ((bytes[index + 1] as u32) << 8);
                output.push(TABLE[((chunk >> 18) & 0x3f) as usize] as char);
                output.push(TABLE[((chunk >> 12) & 0x3f) as usize] as char);
                output.push(TABLE[((chunk >> 6) & 0x3f) as usize] as char);
            }
            _ => {}
        }
        output
    }

    fn webauthn_assertion_fixture(
        flags: u8,
        sign_count: u32,
    ) -> (WebAuthnAssertionInput, WebAuthnAssertionVerifierConfig) {
        let rng = SystemRandom::new();
        let pkcs8 =
            EcdsaKeyPair::generate_pkcs8(&ECDSA_P256_SHA256_ASN1_SIGNING, &rng).unwrap();
        let key_pair =
            EcdsaKeyPair::from_pkcs8(&ECDSA_P256_SHA256_ASN1_SIGNING, pkcs8.as_ref(), &rng)
                .unwrap();
        let public_key = key_pair.public_key().as_ref();
        assert_eq!(public_key.len(), 65);
        assert_eq!(public_key[0], 0x04);

        let rp_id = "acme.example";
        let origin = "https://acme.example";
        let challenge = "challenge-token-001";
        let client_data_json = format!(
            r#"{{"type":"webauthn.get","challenge":"{challenge}","origin":"{origin}"}}"#
        );
        let mut authenticator_data = Vec::new();
        authenticator_data.extend_from_slice(&Sha256::digest(rp_id.as_bytes()));
        authenticator_data.push(flags);
        authenticator_data.extend_from_slice(&sign_count.to_be_bytes());

        let mut signed_data = authenticator_data.clone();
        signed_data.extend_from_slice(&Sha256::digest(client_data_json.as_bytes()));
        let signature = key_pair.sign(&rng, &signed_data).unwrap();

        (
            WebAuthnAssertionInput {
                client_data_json_base64url: base64url_encode(client_data_json.as_bytes()),
                authenticator_data_base64url: base64url_encode(&authenticator_data),
                signature_der_base64url: base64url_encode(signature.as_ref()),
            },
            WebAuthnAssertionVerifierConfig::new(
                rp_id,
                origin,
                challenge,
                1_800_000_000,
                1_800_000_030,
                41,
                base64url_encode(&public_key[1..33]),
                base64url_encode(&public_key[33..65]),
            ),
        )
    }

    #[test]
    fn verifies_rs256_jwt_against_jwks_and_registered_claims() {
        let decision = verify_jwt_session(TEST_TOKEN, TEST_JWKS, &config(1_800_000_000));

        assert!(decision.verified);
        assert_eq!(decision.reason, "verified");
        assert_eq!(decision.algorithm, "RS256");
        assert_eq!(decision.key_id, "test-key-1");
        assert_eq!(decision.issuer, "https://auth.acme.example");
        assert_eq!(decision.audience, "bitween-platform");
        assert_eq!(decision.subject, "user-live-ops");
        assert_eq!(decision.role, "payroll_manager");
        assert_eq!(decision.acr_level, "sensitive");
        assert!(decision.webauthn_user_verified);
        assert_eq!(decision.authorized_tenant_id, "tenant-acme");
        assert_eq!(decision.authorized_legal_entity, "Acme");
        assert_eq!(decision.authorized_workplace, "Seoul");
        assert_eq!(decision.authz_policy_id, AUTHZ_POLICY_ID);
        assert_eq!(decision.jwt_id_sha256.len(), 64);
    }

    #[test]
    fn rejects_tampered_signature_without_leaking_claim_values() {
        let mut token = TEST_TOKEN.to_owned();
        token.pop();
        token.push('A');

        let decision = verify_jwt_session(&token, TEST_JWKS, &config(1_800_000_000));

        assert!(!decision.verified);
        assert_eq!(decision.reason, "jwt_signature_invalid");
        assert!(decision.subject.is_empty());
        assert!(decision.jwt_id_sha256.is_empty());
    }

    #[test]
    fn rejects_untrusted_algorithm_before_signature_verification() {
        let parts: Vec<&str> = TEST_TOKEN.split('.').collect();
        let token = format!("eyJhbGciOiJub25lIiwia2lkIjoidGVzdC1rZXktMSJ9.{}.{}", parts[1], parts[2]);

        let decision = verify_jwt_session(&token, TEST_JWKS, &config(1_800_000_000));

        assert_eq!(decision.reason, "jwt_alg_untrusted");
    }

    #[test]
    fn rejects_expired_token() {
        let decision = verify_jwt_session(TEST_TOKEN, TEST_JWKS, &config(4_102_444_801));

        assert_eq!(decision.reason, "jwt_expired");
    }

    #[test]
    fn rejects_wrong_audience() {
        let decision = verify_jwt_session(
            TEST_TOKEN,
            TEST_JWKS,
            &AuthSessionVerifierConfig::new(
                "https://auth.acme.example",
                "different-audience",
                1_800_000_000,
            ),
        );

        assert_eq!(decision.reason, "jwt_audience_mismatch");
    }

    #[test]
    fn verifies_webauthn_assertion_origin_challenge_rp_hash_and_signature() {
        let (assertion, config) = webauthn_assertion_fixture(0x05, 42);

        let verification = verify_webauthn_assertion(&assertion, &config);

        assert!(verification.verified);
        assert_eq!(verification.schema, AUTH_WEBAUTHN_ASSERTION_SCHEMA);
        assert_eq!(verification.reason, "verified");
        assert!(verification.user_present);
        assert!(verification.user_verified);
        assert_eq!(verification.sign_count, 42);
        assert_eq!(verification.rp_id_hash_sha256.len(), 64);
        assert_eq!(verification.challenge_sha256.len(), 64);
    }

    #[test]
    fn rejects_webauthn_assertion_origin_challenge_and_uv_failures() {
        let (assertion, mut config) = webauthn_assertion_fixture(0x05, 42);
        config.challenge = "different-challenge".to_owned();
        assert_eq!(
            verify_webauthn_assertion(&assertion, &config).reason,
            "webauthn_challenge_mismatch"
        );

        let (assertion, mut config) = webauthn_assertion_fixture(0x05, 42);
        config.expected_origin = "https://evil.example".to_owned();
        assert_eq!(
            verify_webauthn_assertion(&assertion, &config).reason,
            "webauthn_origin_mismatch"
        );

        let (assertion, config) = webauthn_assertion_fixture(0x01, 42);
        assert_eq!(
            verify_webauthn_assertion(&assertion, &config).reason,
            "webauthn_user_not_verified"
        );
    }

    #[test]
    fn rejects_webauthn_replayed_nonzero_signature_counter() {
        let (assertion, mut config) = webauthn_assertion_fixture(0x05, 42);
        config.previous_sign_count = 42;

        let verification = verify_webauthn_assertion(&assertion, &config);

        assert_eq!(verification.reason, "webauthn_sign_count_replayed");
        assert!(!verification.verified);
    }

    #[test]
    fn validates_oidc_discovery_metadata_for_rs256_jwks_rotation() {
        let validation = validate_oidc_discovery(
            TEST_OIDC_DISCOVERY,
            &OidcDiscoveryVerifierConfig::new(
                "https://auth.acme.example",
                Some("https://auth.acme.example/.well-known/jwks.json"),
            ),
        );

        assert!(validation.verified);
        assert_eq!(validation.reason, "verified");
        assert_eq!(validation.issuer, "https://auth.acme.example");
        assert_eq!(validation.jwks_uri, "https://auth.acme.example/.well-known/jwks.json");
        assert!(validation.signing_algorithms.contains(&"RS256".to_owned()));
    }

    #[test]
    fn rejects_oidc_discovery_issuer_mismatch() {
        let validation = validate_oidc_discovery(
            TEST_OIDC_DISCOVERY,
            &OidcDiscoveryVerifierConfig::new(
                "https://different-issuer.example",
                Some("https://auth.acme.example/.well-known/jwks.json"),
            ),
        );

        assert_eq!(validation.reason, "oidc_issuer_mismatch");
    }

    #[test]
    fn rejects_oidc_discovery_without_rs256_support() {
        let validation = validate_oidc_discovery(
            r#"{"issuer":"https://auth.acme.example","jwks_uri":"https://auth.acme.example/.well-known/jwks.json","response_types_supported":["code"],"subject_types_supported":["public"],"id_token_signing_alg_values_supported":["ES256"]}"#,
            &OidcDiscoveryVerifierConfig::new(
                "https://auth.acme.example",
                Some("https://auth.acme.example/.well-known/jwks.json"),
            ),
        );

        assert_eq!(validation.reason, "oidc_rs256_unsupported");
    }

    #[test]
    fn rejects_oidc_discovery_non_https_jwks_uri() {
        let validation = validate_oidc_discovery(
            r#"{"issuer":"https://auth.acme.example","jwks_uri":"http://auth.acme.example/.well-known/jwks.json","response_types_supported":["code"],"subject_types_supported":["public"],"id_token_signing_alg_values_supported":["RS256"]}"#,
            &OidcDiscoveryVerifierConfig::new("https://auth.acme.example", None::<String>),
        );

        assert_eq!(validation.reason, "oidc_jwks_uri_untrusted");
    }
}
