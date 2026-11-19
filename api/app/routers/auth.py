from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Crew, Membership, User
from app.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    MeResponse,
    SignupDispatcherRequest,
    SignupDriverRequest,
    UpdateProfileRequest,
    UserOut,
)
from app.security import (
    create_access_token,
    generate_invite_code,
    hash_password,
    invite_expiry,
    normalize_phone,
    validate_password,
    verify_password,
)
from app.serializers import crew_out, user_out
from app.services.audit import log_event

router = APIRouter(prefix="/auth", tags=["auth"])


def _active_membership(db: Session, user_id: int) -> Membership | None:
    return db.scalar(
        select(Membership)
        .where(Membership.user_id == user_id, Membership.status == "active")
        .order_by(Membership.created_at.asc())
    )


def _auth_response(user: User, membership: Membership | None) -> AuthResponse:
    crew = membership.crew if membership else None
    return AuthResponse(
        access_token=create_access_token(user.id),
        user=user_out(user),
        role=membership.role if membership else None,
        crew=crew_out(crew) if crew else None,
    )


def _unique_code(db: Session) -> str:
    for _ in range(20):
        code = generate_invite_code()
        if db.scalar(select(Crew).where(Crew.invite_code == code)) is None:
            return code
    raise HTTPException(status_code=500, detail="Davet kodu üretilemedi.")


@router.post("/signup-dispatcher", response_model=AuthResponse, status_code=201)
def signup_dispatcher(payload: SignupDispatcherRequest, db: Session = Depends(get_db)):
    validate_password(payload.password)
    phone = normalize_phone(payload.phone)
    if db.scalar(select(User).where(User.phone == phone)):
        raise HTTPException(status_code=409, detail="Bu telefon numarası zaten kayıtlı.")

    user = User(
        full_name=payload.full_name.strip(),
        phone=phone,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()

    crew = Crew(
        name=payload.crew_name.strip(),
        owner_id=user.id,
        invite_code=_unique_code(db),
        invite_expires_at=invite_expiry(7),
        invite_max_uses=100,
        invite_uses=0,
        depot_name=payload.depot_name.strip() or "Depo",
        depot_lat=payload.depot_lat,
        depot_lon=payload.depot_lon,
    )
    db.add(crew)
    db.flush()

    membership = Membership(crew_id=crew.id, user_id=user.id, role="dispatcher")
    db.add(membership)
    log_event(db, crew_id=crew.id, actor_id=user.id, action="crew.created", details=crew.name)
    db.commit()
    db.refresh(membership)
    return _auth_response(user, membership)


@router.post("/signup-driver", response_model=AuthResponse, status_code=201)
def signup_driver(payload: SignupDriverRequest, db: Session = Depends(get_db)):
    validate_password(payload.password)
    phone = normalize_phone(payload.phone)
    if db.scalar(select(User).where(User.phone == phone)):
        raise HTTPException(status_code=409, detail="Bu telefon numarası zaten kayıtlı. Giriş yapıp kervana katılın.")

    code = payload.invite_code.strip().upper()
    crew = db.scalar(select(Crew).where(Crew.invite_code == code))
    now = datetime.now(timezone.utc)
    expires = crew.invite_expires_at if crew else None
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if crew is None or expires is None or expires < now:
        raise HTTPException(status_code=404, detail="Davet kodu geçersiz veya süresi dolmuş.")
    if crew.invite_uses >= crew.invite_max_uses:
        raise HTTPException(status_code=409, detail="Davet kodu kullanım limitine ulaştı.")

    user = User(
        full_name=payload.full_name.strip(),
        phone=phone,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    membership = Membership(crew_id=crew.id, user_id=user.id, role="driver")
    db.add(membership)
    crew.invite_uses += 1
    log_event(db, crew_id=crew.id, actor_id=user.id, action="member.joined", details=user.full_name)
    db.commit()
    db.refresh(membership)
    return _auth_response(user, membership)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    phone = normalize_phone(payload.phone)
    user = db.scalar(select(User).where(User.phone == phone))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Telefon veya şifre hatalı.")
    return _auth_response(user, _active_membership(db, user.id))


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = _active_membership(db, user.id)
    crew = membership.crew if membership else None
    return MeResponse(
        user=user_out(user),
        role=membership.role if membership else None,
        crew=crew_out(crew) if crew else None,
        invite_code=crew.invite_code if crew and membership and membership.role == "dispatcher" else None,
    )


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.full_name = payload.full_name.strip()
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mevcut şifre hatalı.")
    validate_password(payload.new_password)
    user.password_hash = hash_password(payload.new_password)
    db.commit()
