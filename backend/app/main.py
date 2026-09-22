import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import check_database_connection
from app.core.rate_limit import limiter
from app.modules.auth.exceptions import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    PhoneAlreadyRegisteredError,
)
from app.modules.auth.router import router as auth_router
from app.modules.users.exceptions import WrongPasswordError
from app.modules.users.router import router as users_router

logger = logging.getLogger("dello")

app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.state.limiter = limiter

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


# ---------------------------------------------------------------------------
# En-têtes de sécurité
# ---------------------------------------------------------------------------


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # Les réponses contiennent des tokens et des données personnelles :
    # aucun cache (proxy, navigateur) ne doit les garder
    response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------------------
# Gestion des erreurs
# ---------------------------------------------------------------------------


def _error(status_code: int, detail, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Remplace la réponse 422 par défaut de FastAPI, qui renvoie les valeurs
    saisies en clair (mots de passe compris). On ne garde que le champ et le message.
    """
    errors = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ()) if part != "body"]
        message = str(error.get("msg", "Valeur invalide")).removeprefix("Value error, ")
        errors.append({"field": ".".join(location) or None, "message": message})

    return _error(422, errors)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return _error(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Trop de tentatives. Réessayez dans une minute.",
    )


@app.exception_handler(PhoneAlreadyRegisteredError)
async def phone_already_registered_handler(request: Request, exc: PhoneAlreadyRegisteredError):
    return _error(status.HTTP_409_CONFLICT, "Ce numéro est déjà associé à un compte")


@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):
    return _error(
        status.HTTP_401_UNAUTHORIZED,
        "Numéro ou mot de passe incorrect",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(InvalidRefreshTokenError)
async def invalid_refresh_token_handler(request: Request, exc: InvalidRefreshTokenError):
    return _error(
        status.HTTP_401_UNAUTHORIZED,
        "Session expirée, veuillez vous reconnecter",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(WrongPasswordError)
async def wrong_password_handler(request: Request, exc: WrongPasswordError):
    return _error(status.HTTP_403_FORBIDDEN, "Mot de passe incorrect")


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """Toute erreur imprévue : trace complète dans les logs, message neutre au client."""
    logger.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
    return _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erreur interne")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Supervision"])
def health():
    try:
        check_database_connection()
    except Exception:
        logger.exception("Base de données injoignable")
        return _error(status.HTTP_503_SERVICE_UNAVAILABLE, "Service indisponible")
    return {"status": "ok"}


app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)