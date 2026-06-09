import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';
import * as TaskManager from 'expo-task-manager';
import type { MobileAuthState, SiteGeofence } from '../types';
import { sendGeofenceEvent } from '../api/client';

export const GEOFENCE_TASK = 'bitween-worker-geofence-task';

interface GeofenceTaskData {
  eventType: Location.GeofencingEventType;
  region: Location.LocationRegion;
}

let taskAuth: MobileAuthState | null = null;
let taskDeviceUid = '';

TaskManager.defineTask(GEOFENCE_TASK, async ({ data, error }) => {
  if (error || !taskAuth) return;
  const event = data as GeofenceTaskData;
  const transition = event.eventType === Location.GeofencingEventType.Exit ? 'exit' : 'enter';
  const region = event.region;
  const result = await sendGeofenceEvent(taskAuth, {
    deviceUid: taskDeviceUid,
    siteName: region.identifier ?? 'assigned-site',
    transition,
    latitude: region.latitude,
    longitude: region.longitude,
  });
  if (!result.authorized && result.alert) {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: '근무지 이탈 경고',
        body: '승인 없이 근무지를 벗어났습니다. 복귀하거나 담당자에게 문의하세요.',
      },
      trigger: null,
    });
  }
});

export async function requestWorkerPermissions(): Promise<{ ok: boolean; reason?: string }> {
  const foreground = await Location.requestForegroundPermissionsAsync();
  if (foreground.status !== 'granted') {
    return { ok: false, reason: 'location_foreground_denied' };
  }
  const background = await Location.requestBackgroundPermissionsAsync();
  if (background.status !== 'granted') {
    return { ok: false, reason: 'location_background_denied' };
  }
  const notifications = await Notifications.requestPermissionsAsync();
  if (!notifications.granted) {
    return { ok: false, reason: 'notifications_denied' };
  }
  return { ok: true };
}

export async function getCurrentCoordinates(): Promise<{ latitude: number; longitude: number }> {
  const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
  return { latitude: loc.coords.latitude, longitude: loc.coords.longitude };
}

export async function startShiftGeofence(
  auth: MobileAuthState,
  deviceUid: string,
  geofence: SiteGeofence,
): Promise<void> {
  taskAuth = auth;
  taskDeviceUid = deviceUid;
  const started = await Location.hasStartedGeofencingAsync(GEOFENCE_TASK);
  if (started) {
    await Location.stopGeofencingAsync(GEOFENCE_TASK);
  }
  await Location.startGeofencingAsync(GEOFENCE_TASK, [
    {
      identifier: geofence.site_name,
      latitude: geofence.latitude,
      longitude: geofence.longitude,
      radius: geofence.radius_m,
      notifyOnEnter: true,
      notifyOnExit: true,
    },
  ]);
}

export async function stopShiftGeofence(): Promise<void> {
  const started = await Location.hasStartedGeofencingAsync(GEOFENCE_TASK);
  if (started) {
    await Location.stopGeofencingAsync(GEOFENCE_TASK);
  }
}
