import Constants from 'expo-constants';
import type {
  AttendanceEvent,
  AttendanceEventType,
  AttendanceRequestInput,
  ConsentKind,
  GeofenceAlert,
  GeofenceTransition,
  MobileBranch,
  MobileAppConfig,
  MobileAuthState,
  OfflineSyncRequest,
  OfflineSyncResult,
  MobileTask,
  PayrollSummary,
  PlatformKind,
  SiteGeofence,
} from '../types';

type MobileApiVersion = 'v1' | 'v2';

const extra = Constants.expoConfig?.extra as {
  apiBaseUrl?: string;
  mobileApiBaseUrl?: string;
  mobileApiVersion?: MobileApiVersion;
  appEnvironment?: 'development' | 'staging' | 'production';
  apiUrls?: Partial<Record<'development' | 'staging' | 'production', string>>;
} | undefined;
const DEFAULT_MOBILE_API_BASE_URL = 'https://mobile-api.bitween.example';
const DEFAULT_MOBILE_API_VERSION: MobileApiVersion = extra?.mobileApiVersion ?? 'v1';
const APP_ENVIRONMENT = extra?.appEnvironment ?? 'development';

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

function stripVersionedApiPath(value: string): string {
  return trimTrailingSlash(value).replace(/\/api\/v\d+$/i, '');
}

const MOBILE_API_BASE_URL = stripVersionedApiPath(
  extra?.mobileApiBaseUrl
    ?? extra?.apiUrls?.[APP_ENVIRONMENT]
    ?? extra?.apiBaseUrl
    ?? DEFAULT_MOBILE_API_BASE_URL,
);

function apiUrl(path: string, version: MobileApiVersion = DEFAULT_MOBILE_API_VERSION): string {
  const cleanPath = path.replace(/^\/+/, '');
  return `${MOBILE_API_BASE_URL}/api/${version}/${cleanPath}`;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth?: MobileAuthState,
  version: MobileApiVersion = DEFAULT_MOBILE_API_VERSION,
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };
  if (auth) {
    headers.Authorization = `Bearer ${auth.token}`;
    headers['X-Bitween-Tenant'] = auth.tenantId;
  }
  const response = await fetch(apiUrl(path, version), { ...options, headers });
  const text = await response.text();
  const body = text ? (JSON.parse(text) as unknown) : undefined;
  if (!response.ok) {
    const message =
      typeof body === 'object' && body !== null && 'message' in body
        ? String((body as { message?: unknown }).message)
        : `HTTP ${response.status}`;
    throw new ApiError(response.status, message);
  }
  return body as T;
}

export interface LoginResponse {
  token: string;
  token_type: 'Bearer';
  user: MobileAuthState['user'];
  required_consents: ConsentKind[];
  mfa_verified: boolean;
}

export async function getAppConfig(currentVersion: string): Promise<MobileAppConfig> {
  return request<MobileAppConfig>(`/config?current_version=${encodeURIComponent(currentVersion)}`);
}

export async function login(input: {
  tenantId: string;
  username: string;
  password: string;
  deviceUid: string;
  mfaOtp: string;
}): Promise<MobileAuthState> {
  const res = await request<LoginResponse>('/login', {
    method: 'POST',
    body: JSON.stringify({
      tenant_id: input.tenantId,
      username: input.username,
      password: input.password,
      device_uid: input.deviceUid,
      mfa_otp: input.mfaOtp,
    }),
  });
  return { tenantId: res.user.tenant_id, token: res.token, user: res.user };
}

export async function registerDevice(
  auth: MobileAuthState,
  input: {
    deviceUid: string;
    branchId: string;
    platform: PlatformKind;
    pushToken: string;
    appVersion: string;
    osVersion: string;
  },
): Promise<void> {
  await request('/devices/register', {
    method: 'POST',
    body: JSON.stringify({
      device_uid: input.deviceUid,
      branch_id: input.branchId,
      platform: input.platform,
      push_token: input.pushToken,
      app_version: input.appVersion,
      os_version: input.osVersion,
    }),
  }, auth);
}

export async function recordConsents(auth: MobileAuthState, deviceUid: string, kinds: ConsentKind[]): Promise<void> {
  await request('/consents', {
    method: 'POST',
    body: JSON.stringify({
      device_uid: deviceUid,
      locale: 'ko-KR',
      policy_version: '2026-06-04',
      consents: kinds.map((kind) => ({ kind, granted: true })),
    }),
  }, auth);
}

export async function getCurrentGeofence(auth: MobileAuthState): Promise<SiteGeofence | null> {
  const branches = await listBranches(auth);
  return branches.find((branch) => branch.active)?.geofence ?? null;
}

export async function listBranches(auth: MobileAuthState): Promise<MobileBranch[]> {
  const res = await request<{ branches: MobileBranch[] }>('/branches', {}, auth);
  return res.branches;
}

export async function listTasks(
  auth: MobileAuthState,
  version: MobileApiVersion = DEFAULT_MOBILE_API_VERSION,
): Promise<MobileTask[]> {
  const res = await request<{ tasks: MobileTask[] }>('/tasks', {}, auth, version);
  return res.tasks;
}

export async function checkAttendance(
  auth: MobileAuthState,
  input: {
    deviceUid: string;
    siteName: string;
    eventType: AttendanceEventType;
    latitude: number;
    longitude: number;
    biometricKind: 'fingerprint' | 'face';
    biometricRef: string;
  },
): Promise<AttendanceEvent> {
  const res = await request<{ ok: boolean; event: AttendanceEvent }>('/attendance/check', {
    method: 'POST',
    body: JSON.stringify({
      device_uid: input.deviceUid,
      site_name: input.siteName,
      event_type: input.eventType,
      event_at: new Date().toISOString(),
      latitude: input.latitude,
      longitude: input.longitude,
      biometric_kind: input.biometricKind,
      biometric_ref: input.biometricRef,
      biometric_ok: true,
    }),
  }, auth);
  return res.event;
}

export async function sendGeofenceEvent(
  auth: MobileAuthState,
  input: {
    deviceUid: string;
    siteName: string;
    transition: GeofenceTransition;
    latitude: number;
    longitude: number;
  },
): Promise<{ authorized: boolean; alert: GeofenceAlert | null }> {
  return request('/location/geofence-event', {
    method: 'POST',
    body: JSON.stringify({
      device_uid: input.deviceUid,
      site_name: input.siteName,
      transition: input.transition,
      detected_at: new Date().toISOString(),
      latitude: input.latitude,
      longitude: input.longitude,
    }),
  }, auth);
}

export async function getPayroll(auth: MobileAuthState, period: string): Promise<PayrollSummary> {
  return request<PayrollSummary>(`/payroll/${encodeURIComponent(period)}`, {}, auth);
}

export async function createAttendanceRequest(auth: MobileAuthState, input: AttendanceRequestInput): Promise<void> {
  await request('/requests', {
    method: 'POST',
    body: JSON.stringify(input),
  }, auth);
}

export async function listAlerts(auth: MobileAuthState): Promise<GeofenceAlert[]> {
  const res = await request<{ alerts: GeofenceAlert[] }>('/manager/alerts?status=open', {}, auth);
  return res.alerts;
}

export async function acknowledgeAlert(auth: MobileAuthState, alertId: string): Promise<void> {
  await request(`/manager/alerts/${encodeURIComponent(alertId)}/ack`, { method: 'POST' }, auth);
}

export async function syncOfflineRequests(
  auth: MobileAuthState,
  requests: OfflineSyncRequest[],
): Promise<{ processed: number; duplicates: number; results: OfflineSyncResult[] }> {
  return request('/sync/offline', {
    method: 'POST',
    body: JSON.stringify({ requests }),
  }, auth);
}
