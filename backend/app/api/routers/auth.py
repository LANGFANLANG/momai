from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import AuthCredentials, AuthSession, CaptchaChallenge, UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]


def _session_for(user: User) -> AuthSession:
    return AuthSession(token=AuthService.create_session(user), user=user)


@router.post("/register", response_model=AuthSession)
def register(payload: AuthCredentials, db: DbSession) -> AuthSession:
    AuthService.verify_captcha(payload.captcha_id, payload.captcha_answer)
    return _session_for(AuthService.register(db, payload.username, payload.password))


@router.post("/login", response_model=AuthSession)
def login(payload: AuthCredentials, db: DbSession) -> AuthSession:
    AuthService.verify_captcha(payload.captcha_id, payload.captcha_answer)
    return _session_for(AuthService.authenticate(db, payload.username, payload.password))


@router.get("/captcha", response_model=CaptchaChallenge)
def captcha() -> CaptchaChallenge:
    captcha_id, code = AuthService.create_captcha()
    return CaptchaChallenge(id=captcha_id, code=code)


@router.get("/me", response_model=UserRead)
def me(user: Annotated[User, Depends(current_user)]) -> User:
    return user
