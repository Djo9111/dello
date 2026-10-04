import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.notifications import service
from app.modules.notifications.schemas import (
    DeviceRegisterRequest,
    DeviceUnregisterRequest,
    NotificationRead,
    UnreadCount,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _to_read(entry) -> NotificationRead:
    title, body = service.MESSAGES[entry.event]
    return NotificationRead.from_entry(entry, title, body)


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(30, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """Boîte de réception, de la plus récente à la plus ancienne."""
    entries = service.list_notifications(db, current_user, limit=limit, offset=offset)
    return [_to_read(entry) for entry in entries]


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(current_user: CurrentUser, db: DbSession):
    """Alimente la pastille de l'application."""
    return UnreadCount(unread=service.count_unread(db, current_user))


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_as_read(
    notification_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    if not service.mark_as_read(db, current_user, notification_id):
        # Inexistante ou appartenant a quelqu'un d'autre : meme reponse
        raise HTTPException(status_code=404, detail="Notification introuvable")


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_as_read(current_user: CurrentUser, db: DbSession) -> None:
    service.mark_all_as_read(db, current_user)


devices_router = APIRouter(prefix="/devices", tags=["Notifications"])


@devices_router.post("", status_code=status.HTTP_204_NO_CONTENT)
def register_device(
    data: DeviceRegisterRequest, current_user: CurrentUser, db: DbSession
) -> None:
    """Inscrit l'appareil aux notifications push."""
    service.register_device(db, current_user, data.token, data.platform)


@devices_router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def unregister_device(
    data: DeviceUnregisterRequest, current_user: CurrentUser, db: DbSession
) -> None:
    """À appeler à la déconnexion, sinon l'appareil continuerait de
    recevoir les notifications du compte précédent."""
    service.unregister_device(db, current_user, data.token)