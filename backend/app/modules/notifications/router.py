from fastapi import APIRouter, status

from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.notifications import service
from app.modules.notifications.schemas import (
    DeviceRegisterRequest,
    DeviceUnregisterRequest,
)

router = APIRouter(prefix="/devices", tags=["Notifications"])


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
def register_device(
    data: DeviceRegisterRequest, current_user: CurrentUser, db: DbSession
) -> None:
    """Inscrit l'appareil aux notifications push."""
    service.register_device(db, current_user, data.token, data.platform)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def unregister_device(
    data: DeviceUnregisterRequest, current_user: CurrentUser, db: DbSession
) -> None:
    """À appeler à la déconnexion, sinon l'appareil continuerait de
    recevoir les notifications du compte précédent."""
    service.unregister_device(db, current_user, data.token)