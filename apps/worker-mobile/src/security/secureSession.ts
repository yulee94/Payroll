import * as SecureStore from 'expo-secure-store';
import type { MobileAuthState } from '../types';

const AUTH_KEY = 'bitween.worker.auth.v1';

export async function saveAuthState(auth: MobileAuthState): Promise<void> {
  await SecureStore.setItemAsync(AUTH_KEY, JSON.stringify(auth), {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function loadAuthState(): Promise<MobileAuthState | null> {
  const raw = await SecureStore.getItemAsync(AUTH_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as MobileAuthState;
  } catch {
    await clearAuthState();
    return null;
  }
}

export async function clearAuthState(): Promise<void> {
  await SecureStore.deleteItemAsync(AUTH_KEY);
}
