from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import Context, get_context, get_current_user, require_dispatcher
from app.models import Crew, Membership, Route, User
from app.schemas import (
    CrewDetail,
    CrewSettingsUpdate,
    JoinCrewRequest,
    MemberOut,
    MessageResponse,
    RoleUpdate,
    RotateCodeResponse,
)
from app.security import generate_invite_code, invite_expiry
from app.services.audit import log_event

router = APIRouter(prefix="/crews", tags=["crews"])


def _find_crew_by_code(db: Session, code: str) -> Crew | None:
    return db.scalar(select(Crew).where(Crew.invite_code == code.strip().upper()))


def _validate_invite(crew: Crew | None) -> Crew:
    now = datetime.now(timezone.utc)
    expires = crew.invite_expires_at if crew else None
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if crew is None or expires is None or expires < now:
        raise HTTPException(status_code=404, detail="Davet kodu geçersiz veya süresi dolmuş.")
    if crew.invite_uses >= crew.invite_max_uses:
        raise HTTPException(status_code=409, detail="Davet kodu kullanım limitine ulaştı.")
    return crew


def _has_active_route(db: Session, crew_id: int, user_id: int) -> bool:
    return (
        db.scalar(
            select(func.count(Route.id)).where(
                Route.crew_id == crew_id,
                Route.driver_id == user_id,
                Route.route_date == date.today(),
                Route.status.in_(["draft", "published"]),
            )
        )
        or 0
    ) > 0


def _crew_detail(db: Session, crew: Crew, user_id: int) -> CrewDetail:
    member_count = db.scalar(
        select(func.count(Membership.id)).where(
            Membership.crew_id == crew.id, Membership.status == "active"
        )
    )
    is_dispatcher = db.scalar(
        select(Membership).where(
            Membership.crew_id == crew.id,
            Membership.user_id == user_id,
            Membership.status == "active",
            Membership.role == "dispatcher",
        )
    )
    return CrewDetail(
        id=crew.id,
        name=crew.name,
        owner_id=crew.owner_id,
        depot_name=crew.depot_name,
        depot_lat=crew.depot_lat,
        depot_lon=crew.depot_lon,
        shift_start_min=crew.shift_start_min,
        shift_end_min=crew.shift_end_min,
        service_minutes=crew.service_minutes,
        max_stops_per_driver=crew.max_stops_per_driver,
        invite_code=crew.invite_code if is_dispatcher else None,
        invite_expires_at=crew.invite_expires_at if is_dispatcher else None,
        invite_uses=crew.invite_uses if is_dispatcher else 0,
        invite_max_uses=crew.invite_max_uses if is_dispatcher else 0,
        is_owner=crew.owner_id == user_id,
        member_count=member_count or 0,
    )


@router.get("/me", response_model=CrewDetail)
def get_my_crew(context: Context = Depends(get_context), db: Session = Depends(get_db)):
    return _crew_detail(db, context.crew, context.user.id)


@router.get("/members", response_model=list[MemberOut])
def list_members(context: Context = Depends(get_context), db: Session = Depends(get_db)):
    memberships = db.scalars(
        select(Membership)
        .options(joinedload(Membership.user))
        .where(Membership.crew_id == context.crew.id, Membership.status == "active")
        .order_by(Membership.created_at.asc())
    ).all()
    return [
        MemberOut(
            id=item.id,
            role=item.role,
            status=item.status,
            full_name=item.user.full_name,
            phone=item.user.phone if context.is_dispatcher else "",
            is_owner=item.user_id == context.crew.owner_id,
        )
        for item in memberships
    ]


@router.patch("/settings", response_model=CrewDetail)
def update_settings(
    payload: CrewSettingsUpdate,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    crew = context.crew
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if value is not None:
            setattr(crew, key, value)
    if crew.shift_start_min >= crew.shift_end_min:
        raise HTTPException(status_code=422, detail="Vardiya başlangıcı bitişten önce olmalı.")
    log_event(db, crew_id=crew.id, actor_id=context.user.id, action="crew.settings_updated")
    db.commit()
    db.refresh(crew)
    return _crew_detail(db, crew, context.user.id)


@router.post("/rotate-code", response_model=RotateCodeResponse)
def rotate_code(
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    crew = context.crew
    for _ in range(20):
        code = generate_invite_code()
        if db.scalar(select(Crew).where(Crew.invite_code == code, Crew.id != crew.id)) is None:
            break
    else:
        raise HTTPException(status_code=500, detail="Davet kodu üretilemedi.")
    crew.invite_code = code
    crew.invite_expires_at = invite_expiry(7)
    crew.invite_uses = 0
    log_event(db, crew_id=crew.id, actor_id=context.user.id, action="crew.code_rotated")
    db.commit()
    return RotateCodeResponse(invite_code=crew.invite_code, invite_expires_at=crew.invite_expires_at)


@router.patch("/members/{user_id}/role", response_model=MemberOut)
def change_role(
    user_id: int,
    payload: RoleUpdate,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    target = db.scalar(
        select(Membership)
        .options(joinedload(Membership.user))
        .where(
            Membership.crew_id == context.crew.id,
            Membership.user_id == user_id,
            Membership.status == "active",
        )
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Kafile üyesi bulunamadı.")

    if target.user_id == context.crew.owner_id and payload.role == "driver":
        other = db.scalar(
            select(Membership).where(
                Membership.crew_id == context.crew.id,
                Membership.status == "active",
                Membership.role == "dispatcher",
                Membership.user_id != target.user_id,
            )
        )
        if other is None:
            raise HTTPException(
                status_code=409,
                detail="Son kervanbaşı sâik yapılamaz. Önce başka birini kervanbaşı yapın.",
            )
        context.crew.owner_id = other.user_id

    target.role = payload.role
    log_event(
        db,
        crew_id=context.crew.id,
        actor_id=context.user.id,
        action="member.role_changed",
        details=f"{target.user.full_name}: {payload.role}",
    )
    db.commit()
    db.refresh(context.crew)
    return MemberOut(
        id=target.id,
        role=target.role,
        status=target.status,
        full_name=target.user.full_name,
        phone=target.user.phone,
        is_owner=target.user_id == context.crew.owner_id,
    )


@router.delete("/members/{user_id}", response_model=MessageResponse)
def remove_member(
    user_id: int,
    context: Context = Depends(require_dispatcher),
    db: Session = Depends(get_db),
):
    if user_id == context.crew.owner_id:
        raise HTTPException(status_code=409, detail="Kervan sahibi çıkarılamaz.")
    if user_id == context.user.id:
        raise HTTPException(status_code=409, detail="Kendinizi çıkaramazsınız.")
    target = db.scalar(
        select(Membership).where(
            Membership.crew_id == context.crew.id,
            Membership.user_id == user_id,
            Membership.status == "active",
        )
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Kafile üyesi bulunamadı.")
    if _has_active_route(db, context.crew.id, user_id):
        raise HTTPException(status_code=409, detail="Aktif güzergâhı olan sâik çıkarılamaz.")
    target.status = "removed"
    log_event(db, crew_id=context.crew.id, actor_id=context.user.id, action="member.removed")
    db.commit()
    return MessageResponse(message="Kafile üyesi çıkarıldı.")


@router.post("/join", response_model=MessageResponse)
def join_crew(
    payload: JoinCrewRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(Membership).where(Membership.user_id == user.id, Membership.status == "active")
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Zaten bir kervana katılmışsınız.")
    crew = _validate_invite(_find_crew_by_code(db, payload.invite_code))
    db.add(Membership(crew_id=crew.id, user_id=user.id, role="driver"))
    crew.invite_uses += 1
    log_event(db, crew_id=crew.id, actor_id=user.id, action="member.joined", details=user.full_name)
    db.commit()
    return MessageResponse(message=f"{crew.name} kervanına katıldınız.")


@router.post("/leave", response_model=MessageResponse)
def leave_crew(context: Context = Depends(get_context), db: Session = Depends(get_db)):
    if context.crew.owner_id == context.user.id:
        raise HTTPException(status_code=409, detail="Kervan sahibi kervandan ayrılamaz.")
    if _has_active_route(db, context.crew.id, context.user.id):
        raise HTTPException(status_code=409, detail="Aktif güzergâh varken kervandan ayrılamazsınız.")
    context.membership.status = "removed"
    log_event(db, crew_id=context.crew.id, actor_id=context.user.id, action="member.left")
    db.commit()
    return MessageResponse(message="Kervandan ayrıldınız.")
