from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str


class CrewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    depot_name: str
    depot_lat: float
    depot_lon: float
    shift_start_min: int
    shift_end_min: int
    service_minutes: int
    max_stops_per_driver: int


class CrewWithCode(CrewOut):
    invite_code: str
    invite_expires_at: datetime
    invite_uses: int
    invite_max_uses: int


class MembershipOut(BaseModel):
    id: int
    role: str
    status: str
    user: UserOut


class MemberOut(BaseModel):
    id: int
    role: str
    status: str
    full_name: str
    phone: str
    is_owner: bool = False


class CrewDetail(CrewOut):
    invite_code: str | None = None
    invite_expires_at: datetime | None = None
    invite_uses: int = 0
    invite_max_uses: int = 0
    is_owner: bool = False
    member_count: int = 0


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    role: str | None = None
    crew: CrewOut | None = None


class MeResponse(BaseModel):
    user: UserOut
    role: str | None = None
    crew: CrewOut | None = None
    invite_code: str | None = None


class LoginRequest(BaseModel):
    phone: str
    password: str


class SignupDispatcherRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str
    password: str
    crew_name: str = Field(min_length=2, max_length=120)
    depot_name: str = "Depo"
    depot_lat: float = 41.0082
    depot_lon: float = 28.9784


class SignupDriverRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str
    password: str
    invite_code: str = Field(min_length=4, max_length=16)


class JoinCrewRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=16)


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CrewSettingsUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    depot_name: str | None = Field(default=None, min_length=2, max_length=160)
    depot_lat: float | None = None
    depot_lon: float | None = None
    shift_start_min: int | None = Field(default=None, ge=0, le=1439)
    shift_end_min: int | None = Field(default=None, ge=1, le=1440)
    service_minutes: int | None = Field(default=None, ge=0, le=120)
    max_stops_per_driver: int | None = Field(default=None, ge=1, le=200)


class RoleUpdate(BaseModel):
    role: Literal["driver", "dispatcher"]


class RotateCodeResponse(BaseModel):
    invite_code: str
    invite_expires_at: datetime


class StopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    recipient_name: str
    phone: str
    address: str
    lat: float
    lon: float
    scheduled_date: date
    time_window_start_min: int | None
    time_window_end_min: int | None
    weight_kg: float | None
    notes: str
    status: str


class StopCreate(BaseModel):
    external_id: str | None = Field(default=None, max_length=80)
    recipient_name: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=32)
    address: str = Field(min_length=3, max_length=500)
    lat: float | None = None
    lon: float | None = None
    scheduled_date: date
    time_window_start_min: int | None = Field(default=None, ge=0, le=1439)
    time_window_end_min: int | None = Field(default=None, ge=1, le=1440)
    weight_kg: float | None = Field(default=None, ge=0)
    notes: str = ""


class RouteReorderRequest(BaseModel):
    route_stop_ids: list[int] = Field(min_length=1)


class RouteAddStopRequest(BaseModel):
    stop_id: int


class StopUpdate(BaseModel):
    recipient_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    lat: float | None = None
    lon: float | None = None
    time_window_start_min: int | None = Field(default=None, ge=0, le=1439)
    time_window_end_min: int | None = Field(default=None, ge=1, le=1440)
    weight_kg: float | None = Field(default=None, ge=0)
    notes: str | None = None


class ImportPreviewRow(BaseModel):
    row_number: int
    external_id: str = ""
    recipient_name: str = ""
    address: str = ""
    lat: float | None = None
    lon: float | None = None
    status: Literal["valid", "invalid"]
    errors: list[str] = Field(default_factory=list)


class ImportPreviewResponse(BaseModel):
    import_id: int
    filename: str
    scheduled_date: date
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[ImportPreviewRow]


class ImportCommitResponse(BaseModel):
    created_count: int
    skipped_count: int


class OptimizeRequest(BaseModel):
    route_date: date
    driver_ids: list[int] = Field(min_length=1)
    stop_ids: list[int] | None = None


class RouteStopOut(BaseModel):
    id: int
    sequence: int
    planned_arrival_min: int | None
    status: str
    failure_reason: str
    driver_note: str
    stop: StopOut


class RouteOut(BaseModel):
    id: int
    driver_id: int
    driver_name: str
    route_date: date
    status: str
    total_distance_m: int
    total_duration_s: int
    published_at: datetime | None
    stop_count: int
    completed_count: int
    stops: list[RouteStopOut]


class RouteGeometryResponse(BaseModel):
    route_id: int
    coordinates: list[tuple[float, float]]
    source: str


class OptimizeResponse(BaseModel):
    routes: list[RouteOut]
    unassigned_stop_ids: list[int]
    matrix_source: str
    total_distance_m: int
    total_duration_s: int


class UpdateStopStatusRequest(BaseModel):
    status: Literal["delivered", "failed", "pending"]
    failure_reason: str | None = None
    driver_note: str | None = None


class MessageResponse(BaseModel):
    message: str
