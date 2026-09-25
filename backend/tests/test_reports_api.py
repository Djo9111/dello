from app.core.config import settings

API = settings.API_V1_PREFIX
PASSWORD = "Tamarin-Soleil-9"
NUMBER = "1234567890123"


def _account(client, phone="77 123 45 67", name="Awa Diop") -> dict:
    client.post(
        f"{API}/auth/register",
        json={"phone_number": phone, "full_name": name, "password": PASSWORD},
    )
    tokens = client.post(
        f"{API}/auth/login", json={"phone_number": phone, "password": PASSWORD}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _payload(**overrides) -> dict:
    data = {
        "kind": "lost",
        "document_type": "cni",
        "document_number": NUMBER,
        "owner_name": "Modienne GUISSE",
        "region": "Dakar",
        "commune": "Keur Massar",
        "place_detail": "pres du marche",
        "occurred_on": "2026-09-20",
    }
    data.update(overrides)
    return data


def _create(client, headers, **overrides):
    return client.post(f"{API}/reports", json=_payload(**overrides), headers=headers)


# ---------------------------------------------------------------------------
# Création
# ---------------------------------------------------------------------------


def test_create_requires_authentication(client):
    assert client.post(f"{API}/reports", json=_payload()).status_code == 401


def test_create_returns_masked_report_without_the_number(client):
    headers = _account(client)

    response = _create(client, headers)

    assert response.status_code == 201
    body = response.json()
    assert body["owner_name_masked"] == "Mod... G..."
    assert body["has_document_number"] is True
    assert NUMBER not in response.text
    assert "document_number_hmac" not in body


def test_invalid_region_is_rejected(client):
    headers = _account(client)

    response = _create(client, headers, region="Bamako")

    assert response.status_code == 422


def test_status_cannot_be_forced_at_creation(client):
    headers = _account(client)

    response = client.post(
        f"{API}/reports", json=_payload() | {"status": "closed"}, headers=headers
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------


def test_public_detail_hides_precise_location(client):
    headers = _account(client)
    report_id = _create(client, headers).json()["id"]

    body = client.get(f"{API}/reports/{report_id}", headers=headers).json()

    assert "place_detail" not in body
    assert "has_document_number" not in body
    assert body["region"] == "Dakar"


def test_owner_view_shows_precise_location(client):
    headers = _account(client)
    report_id = _create(client, headers).json()["id"]

    body = client.get(f"{API}/reports/me/{report_id}", headers=headers).json()

    assert body["place_detail"] == "pres du marche"
    assert body["is_published"] is True


def test_other_user_cannot_use_the_owner_view(client):
    awa = _account(client)
    moussa = _account(client, phone="78 111 22 33", name="Moussa Fall")
    report_id = _create(client, awa).json()["id"]

    assert client.get(f"{API}/reports/me/{report_id}", headers=moussa).status_code == 404


def test_list_is_filtered(client):
    headers = _account(client)
    _create(client, headers, kind="lost", document_type="cni")
    found_id = _create(
        client, headers, kind="found", document_type="permis", region="Thies"
    ).json()["id"]

    listed = client.get(f"{API}/reports", params={"kind": "found"}, headers=headers).json()

    assert [item["id"] for item in listed] == [found_id]


def test_list_requires_authentication(client):
    assert client.get(f"{API}/reports").status_code == 401


def test_unpublished_report_is_hidden_from_others(client):
    awa = _account(client)
    moussa = _account(client, phone="78 111 22 33", name="Moussa Fall")
    report_id = _create(client, awa).json()["id"]

    client.patch(f"{API}/reports/{report_id}", json={"is_published": False}, headers=awa)

    assert client.get(f"{API}/reports/{report_id}", headers=moussa).status_code == 404
    assert client.get(f"{API}/reports/me/{report_id}", headers=awa).status_code == 200


# ---------------------------------------------------------------------------
# Rapprochement
# ---------------------------------------------------------------------------


def test_matches_are_found_across_users(client):
    awa = _account(client)
    moussa = _account(client, phone="78 111 22 33", name="Moussa Fall")

    lost_id = _create(client, awa, kind="lost").json()["id"]
    found_id = _create(client, moussa, kind="found", document_number="1 234 567 890 123").json()["id"]

    matches = client.get(f"{API}/reports/me/{lost_id}/matches", headers=awa).json()

    assert [item["id"] for item in matches] == [found_id]


def test_matches_are_owner_only(client):
    awa = _account(client)
    moussa = _account(client, phone="78 111 22 33", name="Moussa Fall")
    lost_id = _create(client, awa).json()["id"]

    assert client.get(f"{API}/reports/me/{lost_id}/matches", headers=moussa).status_code == 404


# ---------------------------------------------------------------------------
# Modification et suppression
# ---------------------------------------------------------------------------


def test_update_only_touches_sent_fields(client):
    headers = _account(client)
    report_id = _create(client, headers).json()["id"]

    body = client.patch(
        f"{API}/reports/{report_id}", json={"commune": "Pikine"}, headers=headers
    ).json()

    assert body["commune"] == "Pikine"
    assert body["place_detail"] == "pres du marche"


def test_update_rejects_protected_fields(client):
    headers = _account(client)
    report_id = _create(client, headers).json()["id"]

    response = client.patch(
        f"{API}/reports/{report_id}", json={"document_type": "permis"}, headers=headers
    )

    assert response.status_code == 422


def test_other_user_cannot_update_or_delete(client):
    awa = _account(client)
    moussa = _account(client, phone="78 111 22 33", name="Moussa Fall")
    report_id = _create(client, awa).json()["id"]

    assert client.patch(
        f"{API}/reports/{report_id}", json={"commune": "Pikine"}, headers=moussa
    ).status_code == 404
    assert client.delete(f"{API}/reports/{report_id}", headers=moussa).status_code == 404


def test_delete_removes_the_report(client):
    headers = _account(client)
    report_id = _create(client, headers).json()["id"]

    assert client.delete(f"{API}/reports/{report_id}", headers=headers).status_code == 204
    assert client.get(f"{API}/reports/me/{report_id}", headers=headers).status_code == 404