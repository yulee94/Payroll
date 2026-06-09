export type PlatformKind = 'android' | 'ios';
export type AttendanceEventType = 'clock_in' | 'clock_out';
export type BiometricKind = 'fingerprint' | 'face';
export type GeofenceTransition = 'enter' | 'exit' | 'heartbeat';
export type PayrollStatus = 'finalized' | 'estimate';
export type ConsentKind = 'privacy' | 'location' | 'biometric' | 'notifications' | 'payroll';

export interface MobileUser {
  user_id: string;
  tenant_id: string;
  username: string;
  display_name: string;
  role: string;
  employee_name: string;
}

export interface MobileAuthState {
  tenantId: string;
  token: string;
  user: MobileUser;
  branchId?: string;
  deviceUid?: string;
}

export interface SiteGeofence {
  id: string;
  site_name: string;
  latitude: number;
  longitude: number;
  radius_m: number;
  legal_entity: string;
  active: boolean;
  note: string;
}

export interface MobileBranch {
  company_id: string;
  branch_id: string;
  branch_name: string;
  site_name: string;
  active: boolean;
  legal_entity: string;
  geofence: SiteGeofence;
}

export interface MobileTask {
  id: string;
  task_type: string;
  title: string;
  status: string;
  branch_id: string;
  site_name: string;
  employee_name: string;
  detected_at: string;
  requires_action: boolean;
  api_version?: 'v2';
  priority?: string;
  assigned_manager_user_id?: string;
  device_id?: string;
  location?: {
    latitude: number;
    longitude: number;
  };
  permissions?: {
    acknowledge: boolean;
    resolve: boolean;
  };
}

export interface MobileVersionPolicy {
  minimum_supported_version: string;
  latest_version: string;
  force_update_required: boolean;
  maintenance_mode: boolean;
  notice_message: string;
}

export interface MobileAppConfig {
  version: string;
  version_policy: MobileVersionPolicy;
  push_notifications: {
    required: boolean;
    token_flow: string[];
    event_kinds: Record<string, string>;
    server_db_fields: string[];
  };
  offline_mode: {
    required: boolean;
    sync_flow: string[];
    server_idempotency_fields: string[];
    dedupe_rule: string;
  };
  review_metadata_required: string[];
}

export interface OfflineSyncRequest {
  request_id: string;
  sync_id: string;
  created_at: string;
  device_id: string;
  branch_id: string;
  request_type: string;
  payload: Record<string, unknown>;
}

export interface OfflineSyncResult {
  request_id: string;
  sync_id: string;
  duplicate: boolean;
  status: string;
  result: Record<string, unknown>;
}

export interface AttendanceEvent {
  id: string;
  employee_name: string;
  site_name: string;
  event_type: AttendanceEventType;
  event_at: string;
  latitude: number;
  longitude: number;
  status: 'pending' | 'verified' | 'rejected';
  geofence_ok: boolean;
  biometric_ok: boolean;
  note: string;
}

export interface PayrollSummary {
  period: string;
  status: PayrollStatus;
  employee_name: string;
  gross_pay: number;
  net_pay: number;
  total_deduction: number;
  tax: number;
  remaining_leave: number;
  work_hours: number;
  work_days?: number;
  leave_days?: number;
  source: string;
  estimate_notice?: string;
}

export interface GeofenceAlert {
  id: string;
  employee_name: string;
  site_name: string;
  transition: GeofenceTransition;
  detected_at: string;
  latitude: number;
  longitude: number;
  status: 'open' | 'acknowledged' | 'resolved';
  worker_warning_sent: boolean;
  manager_alert_sent: boolean;
  note: string;
}

export interface AttendanceRequestInput {
  title: string;
  attendance_type: '연차' | '오전 반차' | '오후 반차' | '병가' | '출장' | '외출' | '조퇴' | '기타';
  start_at: string;
  end_at: string;
  site_name: string;
  reason: string;
}

export interface ApiErrorBody {
  error?: string;
  message?: string;
  detail?: string;
}
