from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.modules.reports.models import Report, ReportKind
from app.modules.users.exceptions import WrongPasswordError
from app.modules.users.models import User


def delete_account(db: Session, user: User, password: str) -> None:
    """
    Supprime définitivement le compte après confirmation du mot de passe.

    Les signalements de documents PERDUS partent avec le compte : sans leur
    auteur, personne ne peut etre recontacte. Ceux de documents TROUVES sont
    conserves mais anonymises : une piece retrouvee doit pouvoir etre rendue
    a son proprietaire meme si celui qui l'a signalee quitte Dello.
    """
    is_valid, _ = verify_password(password, user.hashed_password)
    if not is_valid:
        raise WrongPasswordError()

    db.execute(
        delete(Report).where(Report.user_id == user.id, Report.kind == ReportKind.LOST)
    )
    db.execute(
        update(Report)
        .where(Report.user_id == user.id, Report.kind == ReportKind.FOUND)
        .values(user_id=None)
    )

    db.delete(user)
    db.commit()