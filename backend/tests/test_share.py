from app.core.config import settings

from tests.helpers import create_account

API = settings.API_V1_PREFIX
NUMBER = "1234567890123"


def _account(client, phone="77 123 45 67", name="Awa Diop"):
    return create_account(client, phone, name)


def _declare(client, headers, **overrides):
    payload = {
        "kind": "lost",
        "circumstance": "stolen",
        "documents": [
            {"document_type": "cni", "document_number": NUMBER},
            {"document_type": "permis"},
        ],
        "owner_name": "Modienne GUISSE",
        "region": "Dakar",
        "commune": "Keur Massar",
        "place_detail": "pres du marche",
    }
    payload.update(overrides)
    return client.post(f"{API}/reports", json=payload, headers=headers).json()


# ---------------------------------------------------------------------------
# Texte proposé au partage
# ---------------------------------------------------------------------------


def test_share_text_contains_no_phone_number(client):
    """Toute la raison d'être du partage Dello : publier sans exposer
    son numéro, contrairement à un post sur un réseau social."""
    headers = _account(client)
    report_id = _declare(client, headers)["id"]

    body = client.get(f"{API}/reports/me/{report_id}/share", headers=headers).json()

    assert "+221" not in body["text"]
    assert "77" not in body["text"].replace(report_id, "")
    assert report_id in body["url"]


def test_share_text_describes_the_documents(client):
    headers = _account(client)
    report_id = _declare(client, headers)["id"]

    text = client.get(f"{API}/reports/me/{report_id}/share", headers=headers).json()["text"]

    assert "Carte d'identité" in text
    assert "Permis de conduire" in text
    assert "Keur Massar" in text


def test_share_is_owner_only(client):
    awa = _account(client)
    moussa = _account(client, phone="78 111 22 33", name="Moussa Fall")
    report_id = _declare(client, awa)["id"]

    assert client.get(f"{API}/reports/me/{report_id}/share", headers=moussa).status_code == 404


# ---------------------------------------------------------------------------
# Page publique
# ---------------------------------------------------------------------------


def test_public_page_needs_no_account(client):
    headers = _account(client)
    report_id = _declare(client, headers)["id"]

    response = client.get(f"/r/{report_id}")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_public_page_shows_masked_information_only(client):
    headers = _account(client)
    report_id = _declare(client, headers)["id"]

    page = client.get(f"/r/{report_id}").text

    assert "Mod... G..." in page
    assert "Keur Massar" in page
    assert "Carte d'identité" in page
    # Ni le nom complet, ni le lieu précis, ni le numéro du document
    assert "Modienne" not in page
    assert "GUISSE" not in page
    assert "pres du marche" not in page
    assert NUMBER not in page


def test_public_page_shows_no_contact(client):
    headers = _account(client)
    report_id = _declare(client, headers)["id"]

    page = client.get(f"/r/{report_id}").text

    assert "+221" not in page
    assert "771234567" not in page


def test_public_page_is_hidden_from_search_engines(client):
    """Un signalement de pièce d'identité n'a rien à faire dans Google."""
    headers = _account(client)
    report_id = _declare(client, headers)["id"]

    response = client.get(f"/r/{report_id}")

    assert "noindex" in response.headers["x-robots-tag"]
    assert "noindex" in response.text


def test_unpublished_report_has_no_public_page(client):
    headers = _account(client)
    report_id = _declare(client, headers)["id"]
    client.patch(f"{API}/reports/{report_id}", json={"is_published": False}, headers=headers)

    response = client.get(f"/r/{report_id}")

    assert response.status_code == 404
    assert "plus disponible" in response.text


def test_closed_report_has_no_public_page(client):
    headers = _account(client)
    report_id = _declare(client, headers)["id"]
    client.post(f"{API}/reports/{report_id}/close", headers=headers)

    assert client.get(f"/r/{report_id}").status_code == 404


def test_unknown_report_returns_a_readable_page(client):
    response = client.get("/r/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert "DELLO" in response.text


def test_malformed_identifier_is_rejected(client):
    assert client.get("/r/pas-un-uuid").status_code == 422