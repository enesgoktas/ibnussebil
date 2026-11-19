from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Crew, Membership, User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


@dataclass
class Context:
    user: User
    membership: Membership
    crew: Crew

    @property
    def role(self) -> str:
        return self.membership.role

    @property
    def is_dispatcher(self) -> bool:
        return self.membership.role == "dispatcher"


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Giriş yapmalısınız.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı.")
    return user


def get_context(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Context:
    membership = (
        db.query(Membership)
        .filter(Membership.user_id == user.id, Membership.status == "active")
        .order_by(Membership.created_at.asc())
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Henüz bir kervana katılmadınız.",
        )
    crew = db.get(Crew, membership.crew_id)
    if crew is None:
        raise HTTPException(status_code=403, detail="Kervan bulunamadı.")
    return Context(user=user, membership=membership, crew=crew)


def require_dispatcher(context: Context = Depends(get_context)) -> Context:
    if not context.is_dispatcher:
        raise HTTPException(status_code=403, detail="Bu işlem için kervanbaşı yetkisi gerekir.")
    return context


def require_driver(context: Context = Depends(get_context)) -> Context:
    if context.role != "driver":
        raise HTTPException(status_code=403, detail="Bu işlem için sâik yetkisi gerekir.")
    return context
