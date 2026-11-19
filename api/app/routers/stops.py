from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import Context, require_dispatcher
from app.models import Stop
from app.schemas import MessageResponse, StopCreate, StopOut, StopUpdate
from app.serializers import stop_out
from app.services.audit import log_event
from app.services.geocode import geocode_address

router = APIRouter(prefix="/stops", tags=["stops"])


@router.post("", response_model=StopOut, status_code=201)
def create_stop(
    payload: StopCreate,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    external_id = (payload.external_id or "").strip() or f"MAN-{uuid.uuid4().hex[:8].upper()}"
    existing = db.scalar(
        select(Stop).where(Stop.crew_id == context.crew.id, Stop.external_id == external_id)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Bu Menzil ID zaten kullanılıyor.")

    lat = payload.lat
    lon = payload.lon
    if (lat is None) ^ (lon is None):
        raise HTTPException(status_code=422, detail="Enlem ve boylam birlikte girilmelidir.")
    if lat is None and lon is None:
        resolved = geocode_address(payload.address)
        if resolved is None:
            raise HTTPException(
                status_code=422,
                detail="Adres koordinata çevrilemedi. Enlem/boylam girerek tekrar deneyin.",
            )
        lat, lon = resolved
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise HTTPException(status_code=422, detail="Enlem/boylam aralığı geçersiz.")
    if (payload.time_window_start_min is None) ^ (payload.time_window_end_min is None):
        raise HTTPException(status_code=422, detail="Başlangıç ve bitiş saati birlikte girilmeli.")
    if (
        payload.time_window_start_min is not None
        and payload.time_window_end_min is not None
        and payload.time_window_start_min >= payload.time_window_end_min
    ):
        raise HTTPException(status_code=422, detail="Başlangıç saati bitişten önce olmalı.")

    stop = Stop(
        crew_id=context.crew.id,
        external_id=external_id,
        recipient_name=payload.recipient_name.strip(),
        phone=payload.phone.strip(),
        address=payload.address.strip(),
        lat=float(lat),
        lon=float(lon),
        scheduled_date=payload.scheduled_date,
        time_window_start_min=payload.time_window_start_min,
        time_window_end_min=payload.time_window_end_min,
        weight_kg=payload.weight_kg,
        notes=payload.notes.strip(),
        status="unassigned",
    )
    db.add(stop)
    log_event(
        db,
        crew_id=context.crew.id,
        actor_id=context.user.id,
        action="stop.created",
        details=external_id,
    )
    db.commit()
    db.refresh(stop)
    return stop_out(stop)


@router.get("", response_model=list[StopOut])
def list_stops(
    route_date: date,
    status_filter: str | None = None,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    query = select(Stop).where(
        Stop.crew_id == context.crew.id,
        Stop.scheduled_date == route_date,
    )
    if status_filter:
        query = query.where(Stop.status == status_filter)
    stops = db.scalars(query.order_by(Stop.external_id.asc())).all()
    return [stop_out(stop) for stop in stops]


@router.patch("/{stop_id}", response_model=StopOut)
def update_stop(
    stop_id: int,
    payload: StopUpdate,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    stop = db.get(Stop, stop_id)
    if stop is None or stop.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="Menzil bulunamadı.")
    if stop.status != "unassigned":
        raise HTTPException(status_code=409, detail="Sevkiyata girmiş menzil düzenlenemez.")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(stop, key, value)
    if (stop.time_window_start_min is None) ^ (stop.time_window_end_min is None):
        raise HTTPException(status_code=422, detail="Başlangıç ve bitiş saati birlikte olmalı.")
    if (
        stop.time_window_start_min is not None
        and stop.time_window_end_min is not None
        and stop.time_window_start_min >= stop.time_window_end_min
    ):
        raise HTTPException(status_code=422, detail="Başlangıç saati bitişten önce olmalı.")
    log_event(db, crew_id=context.crew.id, actor_id=context.user.id, action="stop.updated", details=stop.external_id)
    db.commit()
    db.refresh(stop)
    return stop_out(stop)


@router.delete("/{stop_id}", response_model=MessageResponse)
def delete_stop(
    stop_id: int,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    stop = db.get(Stop, stop_id)
    if stop is None or stop.crew_id != context.crew.id:
        raise HTTPException(status_code=404, detail="Menzil bulunamadı.")
    if stop.status != "unassigned":
        raise HTTPException(status_code=409, detail="Sevkiyata girmiş menzil silinemez.")
    db.delete(stop)
    log_event(db, crew_id=context.crew.id, actor_id=context.user.id, action="stop.deleted", details=stop.external_id)
    db.commit()
    return MessageResponse(message="Menzil silindi.")
