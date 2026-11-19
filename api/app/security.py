from __future__ import annotations

import re
import secrets
import string
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.config import settings

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Şifre en az 8 karakter olmalıdır.",
        )


def normalize_phone(phone: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if len(cleaned.lstrip("+")) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Geçerli bir telefon numarası girin.",
        )
    return cleaned


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum geçersiz veya süresi dolmuş.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def generate_invite_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


def invite_expiry(days: int = 7) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)
