import uuid

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.rate_limit import limiter
from app.modules.auth.dependencies import DbSession
from app.modules.reports import service, share
from app.modules.reports.exceptions import ReportNotFoundError

# Hors du prefixe API : ces liens sont destines a etre colles dans un SMS
# ou sur un reseau social, donc ils doivent rester courts.
router = APIRouter(tags=["Partage"])

SHARE_RATE_LIMIT = "60/minute"


@router.get("/r/{report_id}", response_class=HTMLResponse, include_in_schema=False)
@limiter.limit(SHARE_RATE_LIMIT)
def public_report_page(request: Request, report_id: uuid.UUID, db: DbSession):
    """Page publique d'un signalement, sans authentification.

    Seul contenu : ce qu'un utilisateur connecté voit déjà, moins le lieu
    précis. Aucune coordonnée, et la page est exclue des moteurs de
    recherche : un signalement de pièce d'identité n'a rien à y faire.
    """
    headers = {"X-Robots-Tag": "noindex, nofollow, noarchive"}

    try:
        report = service.get_public_report(db, report_id)
    except ReportNotFoundError:
        return HTMLResponse(share.render_not_found(), status_code=404, headers=headers)

    return HTMLResponse(share.render_page(report), headers=headers)