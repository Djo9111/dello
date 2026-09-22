from sqlalchemy import select

from app.core.config import settings
from app.modules.auth.models import RefreshToken
from app.modules.users.models import User

API = settings.API_V1_PREFIX
PHONE = "77 123 45 67"
PASSWORD = "Tamarin-Soleil-9"


def _register(client, phone=PHONE):
    return client.post(
        f"{API}/auth/register",
        json={"phone_number": phone, "full_name": "Awa Diop", "password": PASSWORD},
    )


def _login(client, phone=PHONE):
    return client.post(
        f"{API}/auth/login", json={"phone_number": phone, "password": PASSWORD}
    ).json()


def _auth_header(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def _delete(client, tokens, password=PASSWORD):
    return client.request(
        "DELETE",
        f"{API}/users/me",
        headers=_auth_header(tokens["access_token"]),
        json={"password": password},
    )


def test_delete_requires_authentication(client):
    response = client.request("DELETE", f"{API}/users/me", json={"password": PASSWORD})

    assert response.status_code == 401


def test_delete_requires_correct_password(client, db_session):
    _register(client)
    tokens = _login(client)

    response = _delete(client, tokens, password="mauvais-mot-de-passe")

    assert response.status_code == 403
    assert db_session.scalars(select(User)).all() != []


def test_delete_removes_account_and_sessions(client, db_session):
    _register(client)
    tokens = _login(client)

    response = _delete(client, tokens)

    assert response.status_code == 204
    assert db_session.scalars(select(User)).all() == []
    assert db_session.scalars(select(RefreshToken)).all() == []


def test_deleted_user_cannot_use_tokens(client):
    _register(client)
    tokens = _login(client)
    _delete(client, tokens)

    me = client.get(f"{API}/users/me", headers=_auth_header(tokens["access_token"]))
    refresh = client.post(
        f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert me.status_code == 401
    assert refresh.status_code == 401


def test_delete_only_affects_that_user(client, db_session):
    _register(client)
    _register(client, phone="781112233")
    tokens = _login(client)

    _delete(client, tokens)

    remaining = db_session.scalars(select(User)).all()
    assert [user.phone_number for user in remaining] == ["+221781112233"]


def test_phone_can_be_reused_after_deletion(client):
    _register(client)
    tokens = _login(client)
    _delete(client, tokens)

    assert _register(client).status_code == 201