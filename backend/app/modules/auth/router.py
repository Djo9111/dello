from fastapi import APIRouter, Request, status

from app.core.config import settings
from app.core.rate_limit import limiter
from app.modules.auth import service
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.auth.schemas import (
    LoginRequest,
    PendingVerificationResponse,
    RefreshRequest,
    RegisterRequest,
    ResendCodeRequest,
    TokenResponse,
    VerifyPhoneRequest,
)


from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["Authentification"])


from app.modules.auth.schemas import (
    LoginRequest,
    PendingVerificationResponse,
    RefreshRequest,
    RegisterRequest,
    ResendCodeRequest,
    TokenResponse,
    VerifyPhoneRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post(
    "/register",
    response_model=PendingVerificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def register(request: Request, data: RegisterRequest, db: DbSession):
    """Première étape. Aucun compte n'est créé tant que le numéro n'est
    pas vérifié, et la réponse ne dit pas si ce numéro est déjà inscrit."""
    service.start_registration(db, data)
    return PendingVerificationResponse()


@router.post("/verify", response_model=TokenResponse)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def verify_phone(request: Request, data: VerifyPhoneRequest, db: DbSession):
    """Seconde étape : le compte est créé et l'utilisateur est connecté."""
    return service.complete_registration(db, data.phone_number, data.code)


@router.post(
    "/resend-code",
    response_model=PendingVerificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def resend_code(request: Request, data: ResendCodeRequest, db: DbSession):
    service.resend_registration_code(db, data.phone_number)
    return PendingVerificationResponse()


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