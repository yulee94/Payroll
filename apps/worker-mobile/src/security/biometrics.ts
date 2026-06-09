import * as LocalAuthentication from 'expo-local-authentication';
import type { BiometricKind } from '../types';

export interface BiometricResult {
  ok: boolean;
  kind: BiometricKind | 'none';
  ref: string;
}

export async function requireBiometric(reason: string, platform: 'android' | 'ios'): Promise<BiometricResult> {
  const hasHardware = await LocalAuthentication.hasHardwareAsync();
  const enrolled = await LocalAuthentication.isEnrolledAsync();
  if (!hasHardware || !enrolled) {
    return { ok: false, kind: 'none', ref: '' };
  }
  const types = await LocalAuthentication.supportedAuthenticationTypesAsync();
  const kind: BiometricKind = types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)
    ? 'face'
    : 'fingerprint';
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: reason,
    cancelLabel: '취소',
    disableDeviceFallback: false,
    biometricsSecurityLevel: 'strong',
  });
  return {
    ok: result.success,
    kind: result.success ? kind : 'none',
    ref: result.success ? `device://local-auth/${platform}/${Date.now()}` : '',
  };
}
