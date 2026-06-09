import * as SecureStore from 'expo-secure-store';
import { syncOfflineRequests } from '../api/client';
import type { MobileAuthState, OfflineSyncRequest, OfflineSyncResult } from '../types';

const OFFLINE_QUEUE_KEY = 'bitween.worker.offlineQueue.v1';

function randomId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

async function saveQueue(rows: OfflineSyncRequest[]): Promise<void> {
  await SecureStore.setItemAsync(OFFLINE_QUEUE_KEY, JSON.stringify(rows), {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function loadOfflineQueue(): Promise<OfflineSyncRequest[]> {
  const raw = await SecureStore.getItemAsync(OFFLINE_QUEUE_KEY);
  if (!raw) return [];
  try {
    const rows = JSON.parse(raw) as OfflineSyncRequest[];
    return Array.isArray(rows) ? rows : [];
  } catch {
    await saveQueue([]);
    return [];
  }
}

export async function enqueueOfflineRequest(input: {
  deviceId: string;
  branchId: string;
  requestType: string;
  payload: Record<string, unknown>;
}): Promise<OfflineSyncRequest> {
  const row: OfflineSyncRequest = {
    request_id: randomId('req'),
    sync_id: randomId('sync'),
    created_at: new Date().toISOString(),
    device_id: input.deviceId,
    branch_id: input.branchId,
    request_type: input.requestType,
    payload: input.payload,
  };
  const queue = await loadOfflineQueue();
  await saveQueue([...queue, row]);
  return row;
}

export async function syncQueuedOfflineRequests(auth: MobileAuthState): Promise<{
  processed: number;
  duplicates: number;
  results: OfflineSyncResult[];
}> {
  const queue = await loadOfflineQueue();
  if (queue.length === 0) {
    return { processed: 0, duplicates: 0, results: [] };
  }
  const result = await syncOfflineRequests(auth, queue);
  const completed = new Set(result.results.map((row) => row.request_id));
  await saveQueue(queue.filter((row) => !completed.has(row.request_id)));
  return result;
}
