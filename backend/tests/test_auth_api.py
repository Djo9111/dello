from app.core.config import settings

API = settings.API_V1_PREFIX
PHONE = "77 123 45 67"
PASSWORD = "Tamarin-Soleil-9"


def _register(client, phone=PHONE, password=PASSWORD):
    return client.post(
        f"{API}/auth/register",
        json={"phone_number": phone, "full_name": "Awa Diop", "password": password},
    )


def _login(client, phone=PHONE, password=PASSWORD):
    return client.post(
        f"{API}/auth/login",
        json={"phone_number": phone, "password": password},
    )


def _auth_header(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


# ---------------------------------------------------------------------------
# Inscription
# ---------------------------------------------------------------------------


def test_register_returns_only_public_fields(client):
    response = _register(client)

    assert response.status_code == 201
    assert set(response.json()) == {
        "id",
        "phone_number",
        "full_name",
        "is_phone_verified",
        "created_at",
    }
    assert response.json()["phone_number"] == "+221771234567"


def test_register_duplicate_returns_409(client):
    _register(client)

    response = _register(client, phone="+221771234567")

    assert response.status_code == 409


def test_validation_error_does_not_echo_password(client):
    weak_password = "azertyuiop"

    response = _register(client, password=weak_password)

    assert response.status_code == 422
    assert weak_password not in response.text
    assert response.json()["detail"][0]["message"] == "Ce mot de passe est trop courant"


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
    _register(client)

    response = _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_errors_are_identical(client):
    _register(client)

    wrong_password = _login(client, password="mauvais-mot-de-passe")
    unknown_phone = _login(client, phone="781112233")

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


def test_me_returns_current_user(client):
    _register(client)
    tokens = _login(client).json()

    response = client.get(f"{API}/users/me", headers=_auth_header(tokens["access_token"]))

    assert response.status_code == 200
    assert response.json()["phone_number"] == "+221771234567"


def test_deactivated_user_loses_access_immediately(client, db_session):
    from app.modules.users.models import User

    _register(client)
    tokens = _login(client).json()

    user = db_session.query(User).one()
    user.is_active = False
    db_session.commit()

    response = client.get(f"{API}/users/me", headers=_auth_header(tokens["access_token"]))

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Rafraîchissement et déconnexion
# ---------------------------------------------------------------------------


def test_refresh_and_reuse_detection(client):
    _register(client)
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
    _register(client)
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
    _register(client)
    session_1 = _login(client).json()
    session_2 = _login(client).json()

    response = client.post(
        f"{API}/auth/logout-all", headers=_auth_header(session_1["access_token"])
    )

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