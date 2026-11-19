import type {
  AuthResponse,
  Crew,
  ImportPreview,
  MeResponse,
  Member,
  OptimizeResponse,
  Role,
  Route,
  RouteGeometry,
  RouteStop,
  Stop,
  User,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type RequestOptions = {
  method?: string;
  token?: string | null;
  body?: unknown;
  formData?: FormData;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }
  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
  });

  if (!response.ok) {
    let message = "İşlem tamamlanamadı.";
    try {
      const payload = await response.json();
      message = payload.detail ?? message;
    } catch {
      // ignore non-JSON errors
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function requestBlob(path: string, token: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new ApiError("Dosya indirilemedi.", response.status);
  }
  return response.blob();
}

export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export const api = {
  login: (phone: string, password: string) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: { phone, password },
    }),

  signupDispatcher: (payload: {
    full_name: string;
    phone: string;
    password: string;
    crew_name: string;
    depot_name: string;
    depot_lat: number;
    depot_lon: number;
  }) =>
    request<AuthResponse>("/api/auth/signup-dispatcher", {
      method: "POST",
      body: payload,
    }),

  signupDriver: (payload: {
    full_name: string;
    phone: string;
    password: string;
    invite_code: string;
  }) =>
    request<AuthResponse>("/api/auth/signup-driver", {
      method: "POST",
      body: payload,
    }),

  me: (token: string) => request<MeResponse>("/api/auth/me", { token }),

  updateMe: (token: string, full_name: string) =>
    request<User>("/api/auth/me", {
      method: "PATCH",
      token,
      body: { full_name },
    }),

  changePassword: (token: string, current_password: string, new_password: string) =>
    request<void>("/api/auth/change-password", {
      method: "POST",
      token,
      body: { current_password, new_password },
    }),

  getCrew: (token: string) => request<Crew>("/api/crews/me", { token }),

  listMembers: (token: string) => request<Member[]>("/api/crews/members", { token }),

  updateCrew: (token: string, payload: Partial<Crew>) =>
    request<Crew>("/api/crews/settings", { method: "PATCH", token, body: payload }),

  rotateCode: (token: string) =>
    request<{ invite_code: string; invite_expires_at: string }>("/api/crews/rotate-code", {
      method: "POST",
      token,
    }),

  changeRole: (token: string, memberId: number, role: Role) =>
    request<Member>(`/api/crews/members/${memberId}/role`, {
      method: "PATCH",
      token,
      body: { role },
    }),

  removeMember: (token: string, memberId: number) =>
    request<{ message: string }>(`/api/crews/members/${memberId}`, {
      method: "DELETE",
      token,
    }),

  joinCrew: (token: string, invite_code: string) =>
    request<{ message: string }>("/api/crews/join", {
      method: "POST",
      token,
      body: { invite_code },
    }),

  leaveCrew: (token: string) =>
    request<{ message: string }>("/api/crews/leave", { method: "POST", token }),

  downloadTemplate: (token: string) => requestBlob("/api/imports/template", token),

  previewImport: (token: string, file: File, scheduled_date: string) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("scheduled_date", scheduled_date);
    return request<ImportPreview>("/api/imports/preview", {
      method: "POST",
      token,
      formData,
    });
  },

  commitImport: (token: string, importId: number) =>
    request<{ created_count: number; skipped_count: number }>(
      `/api/imports/${importId}/commit`,
      { method: "POST", token }
    ),

  downloadImportErrors: (token: string, importId: number) =>
    requestBlob(`/api/imports/${importId}/errors.csv`, token),

  listStops: (token: string, routeDate: string) =>
    request<Stop[]>(`/api/stops?route_date=${encodeURIComponent(routeDate)}`, { token }),

  createStop: (
    token: string,
    payload: {
      external_id?: string;
      recipient_name: string;
      phone: string;
      address: string;
      lat?: number | null;
      lon?: number | null;
      scheduled_date: string;
      time_window_start_min?: number | null;
      time_window_end_min?: number | null;
      weight_kg?: number | null;
      notes: string;
    }
  ) => request<Stop>("/api/stops", { method: "POST", token, body: payload }),

  updateStop: (token: string, stopId: number, payload: Partial<Stop>) =>
    request<Stop>(`/api/stops/${stopId}`, { method: "PATCH", token, body: payload }),

  deleteStop: (token: string, stopId: number) =>
    request<{ message: string }>(`/api/stops/${stopId}`, { method: "DELETE", token }),

  optimize: (token: string, route_date: string, driver_ids: number[]) =>
    request<OptimizeResponse>("/api/routes/optimize", {
      method: "POST",
      token,
      body: { route_date, driver_ids },
    }),

  listRoutes: (token: string, routeDate: string) =>
    request<Route[]>(`/api/routes?route_date=${encodeURIComponent(routeDate)}`, { token }),

  getRoute: (token: string, routeId: number) =>
    request<Route>(`/api/routes/${routeId}`, { token }),

  routeGeometry: (token: string, routeId: number) =>
    request<RouteGeometry>(`/api/routes/${routeId}/geometry`, { token }),

  reorderRoute: (token: string, routeId: number, routeStopIds: number[]) =>
    request<Route>(`/api/routes/${routeId}/reorder`, {
      method: "POST",
      token,
      body: { route_stop_ids: routeStopIds },
    }),

  addStopToRoute: (token: string, routeId: number, stopId: number) =>
    request<Route>(`/api/routes/${routeId}/stops`, {
      method: "POST",
      token,
      body: { stop_id: stopId },
    }),

  removeStopFromRoute: (token: string, routeId: number, routeStopId: number) =>
    request<Route>(`/api/routes/${routeId}/stops/${routeStopId}`, {
      method: "DELETE",
      token,
    }),

  publishRoute: (token: string, routeId: number) =>
    request<Route>(`/api/routes/${routeId}/publish`, { method: "POST", token }),

  unpublishRoute: (token: string, routeId: number) =>
    request<Route>(`/api/routes/${routeId}/unpublish`, { method: "POST", token }),

  deleteRoute: (token: string, routeId: number) =>
    request<{ message: string }>(`/api/routes/${routeId}/delete`, { method: "POST", token }),

  driverRoute: (token: string, routeDate: string) =>
    request<Route>(`/api/driver/route?route_date=${encodeURIComponent(routeDate)}`, { token }),

  updateDriverStop: (
    token: string,
    routeStopId: number,
    payload: { status: "delivered" | "failed" | "pending"; failure_reason?: string; driver_note?: string }
  ) =>
    request<RouteStop>(`/api/driver/route-stops/${routeStopId}`, {
      method: "PATCH",
      token,
      body: payload,
    }),
};
