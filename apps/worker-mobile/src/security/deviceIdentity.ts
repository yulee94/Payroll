import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import type { PlatformKind } from '../types';

const DEVICE_UID_KEY = 'bitween.worker.deviceUid.v1';

function randomId(): string {
  return `${Platform.OS}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export async function getOrCreateDeviceUid(): Promise<string> {
  const existing = await SecureStore.getItemAsync(DEVICE_UID_KEY);
  if (existing) return existing;
  const next = randomId();
  await SecureStore.setItemAsync(DEVICE_UID_KEY, next, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
  return next;
}

export function mobilePlatform(): PlatformKind {
  return Platform.OS === 'ios' ? 'ios' : 'android';
}
