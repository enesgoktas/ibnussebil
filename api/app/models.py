from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Crew(Base):
    __tablename__ = "crews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    invite_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invite_max_uses: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    invite_uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    depot_name: Mapped[str] = mapped_column(String(160), default="Depo", nullable=False)
    depot_lat: Mapped[float] = mapped_column(Float, default=41.0082, nullable=False)
    depot_lon: Mapped[float] = mapped_column(Float, default=28.9784, nullable=False)
    shift_start_min: Mapped[int] = mapped_column(Integer, default=9 * 60, nullable=False)
    shift_end_min: Mapped[int] = mapped_column(Integer, default=18 * 60, nullable=False)
    service_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_stops_per_driver: Mapped[int] = mapped_column(Integer, default=40, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped[User] = relationship(foreign_keys=[owner_id])
    memberships: Mapped[list[Membership]] = relationship(
        back_populates="crew", cascade="all, delete-orphan"
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("crew_id", "user_id", name="uq_membership_crew_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crew_id: Mapped[int] = mapped_column(ForeignKey("crews.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="driver")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    crew: Mapped[Crew] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crew_id: Mapped[int] = mapped_column(ForeignKey("crews.id"), nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="preview", nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    rows_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Stop(Base):
    __tablename__ = "stops"
    __table_args__ = (UniqueConstraint("crew_id", "external_id", name="uq_stop_crew_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crew_id: Mapped[int] = mapped_column(ForeignKey("crews.id"), nullable=False, index=True)
    import_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    external_id: Mapped[str] = mapped_column(String(80), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time_window_start_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_window_end_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unassigned", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crew_id: Mapped[int] = mapped_column(ForeignKey("crews.id"), nullable=False, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    route_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    total_distance_m: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_duration_s: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    driver: Mapped[User] = relationship(foreign_keys=[driver_id])
    stops: Mapped[list[RouteStop]] = relationship(
        back_populates="route", cascade="all, delete-orphan", order_by="RouteStop.sequence"
    )


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False, index=True)
    stop_id: Mapped[int] = mapped_column(ForeignKey("stops.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_arrival_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    driver_note: Mapped[str] = mapped_column(Text, default="", nullable=False)

    route: Mapped[Route] = relationship(back_populates="stops")
    stop: Mapped[Stop] = relationship()


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crew_id: Mapped[int] = mapped_column(ForeignKey("crews.id"), nullable=False, index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
