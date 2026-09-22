from fastapi import APIRouter, Request, status

from app.core.config import settings
from app.core.rate_limit import limiter
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.users import service
from app.modules.users.schemas import DeleteAccountRequest, UserRead

router = APIRouter(prefix="/users", tags=["Utilisateurs"])


@router.get("/me", response_model=UserRead)
def read_me(current_user: CurrentUser):
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def delete_me(
    request: Request,
    data: DeleteAccountRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    service.delete_account(db, current_user, data.password.get_secret_value())