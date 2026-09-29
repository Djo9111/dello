from app.core.config import settings

from tests.helpers import allow_new_code, create_account
from tests.sms_outbox import OUTBOX

API = settings.API_V1_PREFIX
PHONE = "77 123 45 67"
NORMALIZED = "+221771234567"
PASSWORD = "Tamarin-Soleil-9"


def _start_registration(client, phone=PHONE, password=PASSWORD, name="Awa Diop"):
    return client.post(
        f"{API}/auth/register",
        json={"phone_number": phone, "full_name": name, "password": password},
    )


def _verify(client, phone=NORMALIZED, code=None):
    return client.post(
        f"{API}/auth/verify",
        json={"phone_number": phone, "code": code or OUTBOX.last_code()},
    )


def _login(client, phone=PHONE, password=PASSWORD):
    return client.post(
        f"{API}/auth/login", json={"phone_number": phone, "password": password}
    )


def _auth_header(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


# ---------------------------------------------------------------------------
# Inscription en deux temps
# ---------------------------------------------------------------------------


def test_registration_does_not_create_the_account_yet(client):
    response = _start_registration(client)

    assert response.status_code == 202
    assert _login(client).status_code == 401


def test_code_is_sent_by_sms(client):
    _start_registration(client)

    assert len(OUTBOX.messages) == 1
    assert OUTBOX.messages[0][0] == NORMALIZED
    assert OUTBOX.last_code().isdigit()


def test_verification_creates_the_account_and_logs_in(client):
    _start_registration(client)

    response = _verify(client)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]

    me = client.get(f"{API}/users/me", headers=_auth_header(body["access_token"]))
    assert me.json()["phone_number"] == NORMALIZED
    assert me.json()["is_phone_verified"] is True


def test_wrong_code_is_rejected(client):
    _start_registration(client)

    assert _verify(client, code="000000").status_code == 400
    assert _login(client).status_code == 401


def test_code_cannot_be_used_twice(client):
    _start_registration(client)
    code = OUTBOX.last_code()

    assert _verify(client, code=code).status_code == 200
    assert _verify(client, code=code).status_code == 400


def test_existing_account_gets_the_same_response(client, db_session):
    """Réponse identique que le numéro soit libre ou déjà inscrit :
    l'inscription ne doit pas révéler qui a un compte sur Dello."""
    first = _start_registration(client)
    _verify(client)
    allow_new_code(db_session)

    second = _start_registration(client, name="Usurpateur")

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()


def test_code_sent_to_an_existing_account_leads_nowhere(client, db_session):
    create_account(client, PHONE)
    allow_new_code(db_session)
    _start_registration(client, name="Usurpateur")

    assert _verify(client).status_code == 400


def test_resend_is_throttled(client):
    _start_registration(client)

    response = client.post(f"{API}/auth/resend-code", json={"phone_number": PHONE})

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_resend_gives_a_new_usable_code(client, db_session):
    _start_registration(client)
    first_code = OUTBOX.last_code()
    allow_new_code(db_session)

    client.post(f"{API}/auth/resend-code", json={"phone_number": PHONE})
    second_code = OUTBOX.last_code()

    assert first_code != second_code
    assert _verify(client, code=first_code).status_code == 400
    assert _verify(client, code=second_code).status_code == 200


def test_resend_for_an_unknown_number_says_the_same_thing(client):
    response = client.post(f"{API}/auth/resend-code", json={"phone_number": "78 111 22 33"})

    assert response.status_code == 202
    assert OUTBOX.messages == []


def test_validation_error_does_not_echo_password(client):
    weak_password = "azertyuiop"

    response = _start_registration(client, password=weak_password)

    assert response.status_code == 422
    assert weak_password not in response.text


def test_extra_field_is_rejected(client):
    response = client.post(
        f"{API}/auth/register",
        json={
            "phone_number": PHONE,
            "full_name": "Awa Diop",
            "password": PASSWORD,
            "role": "admin",
        },
    )

    assert response.status_code == 422
    assert "admin" not in response.text


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------


def test_login_returns_tokens(client):
    create_account(client, PHONE)

    response = _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_errors_are_identical(client):
    create_account(client, PHONE)

    wrong_password = _login(client, password="mauvais-mot-de-passe")
    unknown_phone = _login(client, phone="78 111 22 33")

    assert wrong_password.status_code == unknown_phone.status_code == 401
    assert wrong_password.json() == unknown_phone.json()


# ---------------------------------------------------------------------------
# Accès protégé
# ---------------------------------------------------------------------------


def test_me_requires_authentication(client):
    assert client.get(f"{API}/users/me").status_code == 401


def test_me_rejects_garbage_token(client):
    response = client.get(f"{API}/users/me", headers=_auth_header("pas-un-token"))

    assert response.status_code == 401


def test_deactivated_user_loses_access_immediately(client, db_session):
    from app.modules.users.models import User

    headers = create_account(client, PHONE)

    user = db_session.query(User).one()
    user.is_active = False
    db_session.commit()

    assert client.get(f"{API}/users/me", headers=headers).status_code == 401


# ---------------------------------------------------------------------------
# Rafraîchissement et déconnexion
# ---------------------------------------------------------------------------


def test_refresh_and_reuse_detection(client):
    create_account(client, PHONE)
    first = _login(client).json()

    rotated = client.post(
        f"{API}/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )
    reused = client.post(
        f"{API}/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )

    assert rotated.status_code == 200
    assert reused.status_code == 401


def test_logout_then_refresh_fails(client):
    create_account(client, PHONE)
    tokens = _login(client).json()

    logout = client.post(
        f"{API}/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    refresh = client.post(
        f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert logout.status_code == 204
    assert refresh.status_code == 401


def test_logout_all_requires_authentication(client):
    assert client.post(f"{API}/auth/logout-all").status_code == 401


def test_logout_all_revokes_every_session(client):
    headers = create_account(client, PHONE)
    session_1 = _login(client).json()
    session_2 = _login(client).json()

    response = client.post(f"{API}/auth/logout-all", headers=headers)

    assert response.status_code == 204
    for session in (session_1, session_2):
        refresh = client.post(
            f"{API}/auth/refresh", json={"refresh_token": session["refresh_token"]}
        )
        assert refresh.status_code == 401


# ---------------------------------------------------------------------------
# Protections transverses
# ---------------------------------------------------------------------------


def test_login_is_rate_limited(rate_limited_client):
    responses = [
        _login(rate_limited_client, password="mauvais-mot-de-passe") for _ in range(6)
    ]

    assert [r.status_code for r in responses[:5]] == [401] * 5
    assert responses[5].status_code == 429


def test_security_headers_are_present(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"