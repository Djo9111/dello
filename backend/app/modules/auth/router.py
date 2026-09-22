from fastapi import APIRouter, Request, status

from app.core.config import settings
from app.core.rate_limit import limiter
from app.modules.auth import service
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def register(request: Request, data: RegisterRequest, db: DbSession):
    return service.register(db, data)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def login(request: Request, data: LoginRequest, db: DbSession):
    return service.login(db, data)


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: DbSession):
    return service.refresh_tokens(db, data.refresh_token.get_secret_value())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: RefreshRequest, db: DbSession) -> None:
    service.logout(db, data.refresh_token.get_secret_value())


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(current_user: CurrentUser, db: DbSession) -> None:
    service.logout_all(db, current_user.id)