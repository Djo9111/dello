from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.modules.users.exceptions import WrongPasswordError
from app.modules.users.models import User


def delete_account(db: Session, user: User, password: str) -> None:
    """
    Supprime définitivement le compte après confirmation du mot de passe.
    Les refresh tokens partent avec, par ON DELETE CASCADE.
    """
    is_valid, _ = verify_password(password, user.hashed_password)
    if not is_valid:
        raise WrongPasswordError()

    db.delete(user)
    db.commit()