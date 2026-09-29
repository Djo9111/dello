from app.core.config import settings

from tests.helpers import create_account

API = settings.API_V1_PREFIX
PASSWORD = "Tamarin-Soleil-9"
NUMBER = "1234567890123"
ANSWER = "12 juin 1995"


def _account(client, phone, name) -> dict:
    return create_account(client, phone, name)


def _finder(client):
    return _account(client, "78 111 22 33", "Moussa Fall")


def _owner(client):
    return _account(client, "77 123 45 67", "Awa Diop")


def _found_report(client, headers, *, with_question=True, with_gps=False) -> dict:
    payload = {
        "kind": "found",
        "document_type": "cni",
        "document_number": NUMBER,
        "owner_name": "Modienne GUISSE",
        "region": "Dakar",
        "commune": "Keur Massar",
    }
    if with_question:
        payload["verification_question"] = "Date de naissance sur la carte ?"
        payload["verification_answer"] = ANSWER
    if with_gps:
        payload["latitude"] = 14.7645
        payload["longitude"] = -17.3660

    return client.post(f"{API}/reports", json=payload, headers=headers).json()


# ---------------------------------------------------------------------------
# Position et question à la déclaration
# ---------------------------------------------------------------------------


def test_gps_is_saved_for_a_found_document(client):
    headers = _finder(client)

    report = _found_report(client, headers, with_gps=True)

    assert report["latitude"] == 14.7645
    assert report["longitude"] == -17.3660


def test_gps_is_refused_for_a_lost_document(client):
    headers = _finder(client)

    response = client.post(
        f"{API}/reports",
        json={
            "kind": "lost",
            "document_type": "cni",
            "region": "Dakar",
            "latitude": 14.7645,
            "longitude": -17.3660,
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_gps_is_never_public(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder, with_gps=True)["id"]

    body = client.get(f"{API}/reports/{report_id}", headers=owner).json()

    assert "latitude" not in body
    assert "longitude" not in body


def test_question_is_public_but_not_the_answer(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder)["id"]

    response = client.get(f"{API}/reports/{report_id}", headers=owner)

    assert response.json()["verification_question"] == "Date de naissance sur la carte ?"
    assert ANSWER not in response.text
    assert "verification_answer_hash" not in response.text


# ---------------------------------------------------------------------------
# Revendication
# ---------------------------------------------------------------------------


def test_right_answer_gives_contact_immediately(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder)["id"]

    claim = client.post(
        f"{API}/reports/{report_id}/claims",
        json={"answer": "12 JUIN 1995"},
        headers=owner,
    ).json()

    assert claim["status"] == "verified"

    contact = client.get(f"{API}/claims/{claim['id']}/contact", headers=owner).json()
    assert contact["phone_number"] == "+221781112233"
    assert contact["full_name"] == "Moussa Fall"


def test_contact_is_locked_until_approval(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder, with_question=False)["id"]

    claim = client.post(
        f"{API}/reports/{report_id}/claims",
        json={"message": "C'est ma carte"},
        headers=owner,
    ).json()

    assert claim["status"] == "pending"
    assert client.get(f"{API}/claims/{claim['id']}/contact", headers=owner).status_code == 404

    client.post(f"{API}/claims/{claim['id']}/approve", headers=finder)

    assert client.get(f"{API}/claims/{claim['id']}/contact", headers=owner).status_code == 200


def test_wrong_answer_then_retry(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder)["id"]

    claim = client.post(
        f"{API}/reports/{report_id}/claims", json={"answer": "faux"}, headers=owner
    ).json()
    assert claim["status"] == "pending"

    retry = client.post(
        f"{API}/claims/{claim['id']}/answer", json={"answer": ANSWER}, headers=owner
    )

    assert retry.status_code == 200
    assert retry.json()["status"] == "verified"


def test_answer_route_is_claimant_only(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder)["id"]
    claim = client.post(
        f"{API}/reports/{report_id}/claims", json={"answer": "faux"}, headers=owner
    ).json()

    response = client.post(
        f"{API}/claims/{claim['id']}/answer", json={"answer": ANSWER}, headers=finder
    )

    assert response.status_code == 404


def test_claimant_cannot_approve_own_claim(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder, with_question=False)["id"]
    claim = client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner).json()

    assert client.post(f"{API}/claims/{claim['id']}/approve", headers=owner).status_code == 404


def test_cannot_claim_own_report(client):
    finder = _finder(client)
    report_id = _found_report(client, finder)["id"]

    response = client.post(
        f"{API}/reports/{report_id}/claims", json={"answer": ANSWER}, headers=finder
    )

    assert response.status_code == 403


def test_duplicate_claim_is_refused(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder, with_question=False)["id"]
    client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner)

    response = client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner)

    assert response.status_code == 409


def test_rejection_keeps_the_contact_hidden(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder, with_question=False)["id"]
    claim = client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner).json()

    client.post(f"{API}/claims/{claim['id']}/reject", headers=finder)

    assert client.get(f"{API}/claims/{claim['id']}/contact", headers=owner).status_code == 404


def test_withdrawal_cuts_the_contact(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder)["id"]
    claim = client.post(
        f"{API}/reports/{report_id}/claims", json={"answer": ANSWER}, headers=owner
    ).json()

    client.post(f"{API}/claims/{claim['id']}/withdraw", headers=owner)

    assert client.get(f"{API}/claims/{claim['id']}/contact", headers=finder).status_code == 404


# ---------------------------------------------------------------------------
# Listes et clôture
# ---------------------------------------------------------------------------


def test_lists_are_separated(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder, with_question=False)["id"]
    claim_id = client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner).json()["id"]

    mine = client.get(f"{API}/claims/mine", headers=owner).json()
    received = client.get(f"{API}/claims/received", headers=finder).json()

    assert [item["id"] for item in mine] == [claim_id]
    assert [item["id"] for item in received] == [claim_id]
    assert client.get(f"{API}/claims/mine", headers=finder).json() == []
    assert client.get(f"{API}/claims/received", headers=owner).json() == []


def test_claim_carries_the_report_summary(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder, with_question=False)["id"]
    claim = client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner).json()

    assert claim["report"]["id"] == report_id
    assert claim["report"]["owner_name_masked"] == "Mod... G..."
    assert "place_detail" not in claim["report"]


def test_closing_a_report_rejects_pending_claims(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder, with_question=False)["id"]
    claim_id = client.post(f"{API}/reports/{report_id}/claims", json={}, headers=owner).json()["id"]

    closed = client.post(f"{API}/reports/{report_id}/close", headers=finder)

    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert client.get(f"{API}/claims/{claim_id}", headers=owner).json()["status"] == "rejected"
    assert client.get(f"{API}/reports/{report_id}", headers=owner).status_code == 404


def test_close_is_owner_only(client):
    finder = _finder(client)
    owner = _owner(client)
    report_id = _found_report(client, finder)["id"]

    assert client.post(f"{API}/reports/{report_id}/close", headers=owner).status_code == 404