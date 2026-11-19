export type Role = "dispatcher" | "driver";

export interface User {
  id: number;
  full_name: string;
  phone: string;
}

export interface Crew {
  id: number;
  name: string;
  owner_id: number;
  depot_name: string;
  depot_lat: number;
  depot_lon: number;
  shift_start_min: number;
  shift_end_min: number;
  service_minutes: number;
  max_stops_per_driver: number;
  invite_code?: string | null;
  invite_expires_at?: string | null;
  invite_uses?: number;
  invite_max_uses?: number;
  is_owner?: boolean;
  member_count?: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  role: Role | null;
  crew: Crew | null;
}

export interface MeResponse {
  user: User;
  role: Role | null;
  crew: Crew | null;
  invite_code: string | null;
}

export interface Member {
  id: number;
  role: Role;
  status: string;
  full_name: string;
  phone: string;
  is_owner: boolean;
}

export interface Stop {
  id: number;
  external_id: string;
  recipient_name: string;
  phone: string;
  address: string;
  lat: number;
  lon: number;
  scheduled_date: string;
  time_window_start_min: number | null;
  time_window_end_min: number | null;
  weight_kg: number | null;
  notes: string;
  status: "unassigned" | "assigned" | "delivered" | "failed";
}

export interface RouteStop {
  id: number;
  sequence: number;
  planned_arrival_min: number | null;
  status: "pending" | "delivered" | "failed";
  failure_reason: string;
  driver_note: string;
  stop: Stop;
}

export interface Route {
  id: number;
  driver_id: number;
  driver_name: string;
  route_date: string;
  status: "draft" | "published" | "completed";
  total_distance_m: number;
  total_duration_s: number;
  published_at: string | null;
  stop_count: number;
  completed_count: number;
  stops: RouteStop[];
}

export interface ImportPreviewRow {
  row_number: number;
  external_id: string;
  recipient_name: string;
  address: string;
  lat: number | null;
  lon: number | null;
  status: "valid" | "invalid";
  errors: string[];
}

export interface ImportPreview {
  import_id: number;
  filename: string;
  scheduled_date: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  rows: ImportPreviewRow[];
}

export interface RouteGeometry {
  route_id: number;
  coordinates: Array<[number, number]>;
  source: string;
}


export interface OptimizeResponse {
  routes: Route[];
  unassigned_stop_ids: number[];
  matrix_source: string;
  total_distance_m: number;
  total_duration_s: number;
}
