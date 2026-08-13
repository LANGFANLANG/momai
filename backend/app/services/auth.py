from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User

DEFAULT_ADMIN_ID = "admin"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"
_ITERATIONS = 210_000
_TOKEN_BYTES = 32
_sessions: dict[str, str] = {}
_CAPTCHA_TTL_SECONDS = 300
_captcha_challenges: dict[str, tuple[str, datetime]] = {}


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        _ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, digest = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = _hash_password(password, base64.b64decode(salt))
        return hmac.compare_digest(expected, password_hash)
    except (ValueError, TypeError):
        return False


def ensure_default_admin(db: Session) -> User:
    user = db.get(User, DEFAULT_ADMIN_ID)
    if user is not None:
        return user
    user = User(
        id=DEFAULT_ADMIN_ID,
        username=DEFAULT_ADMIN_USERNAME,
        password_hash=_hash_password(DEFAULT_ADMIN_PASSWORD),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def normalize_username(username: str) -> str:
    return username.strip().lower()


class AuthService:
    @staticmethod
    def create_captcha() -> tuple[str, str]:
        alphabet = string.ascii_uppercase + string.digits
        code = "".join(secrets.choice(alphabet) for _ in range(4))
        captcha_id = secrets.token_urlsafe(16)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=_CAPTCHA_TTL_SECONDS)
        _captcha_challenges[captcha_id] = (code, expires_at)
        return captcha_id, code

    @staticmethod
    def verify_captcha(captcha_id: str, answer: str) -> None:
        challenge = _captcha_challenges.pop(captcha_id, None)
        if challenge is None:
            raise HTTPException(status_code=400, detail="验证码已失效，请刷新后重试")
        code, expires_at = challenge
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="验证码已过期，请刷新后重试")
        if not hmac.compare_digest(code.lower(), answer.strip().lower()):
            raise HTTPException(status_code=400, detail="验证码错误")

    @staticmethod
    def register(db: Session, username: str, password: str) -> User:
        username = normalize_username(username)
        if not username:
            raise HTTPException(status_code=422, detail="Username is required")
        ensure_default_admin(db)
        existing = db.scalar(select(User).where(User.username == username))
        if existing is not None:
            raise HTTPException(status_code=409, detail="Username already exists")
        user = User(username=username, password_hash=_hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, username: str, password: str) -> User:
        ensure_default_admin(db)
        user = db.scalar(select(User).where(User.username == normalize_username(username)))
        if user is None or not _verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        return user

    @staticmethod
    def create_session(user: User) -> str:
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        _sessions[token] = user.id
        return token

    @staticmethod
    def user_for_token(db: Session, token: str) -> User | None:
        user_id = _sessions.get(token)
        if not user_id:
            return None
        return db.get(User, user_id)
