from datetime import date

import pytest

from app.core.security import hash_password
from app.modules.reports import service
from app.modules.reports.models import ReportKind
from app.modules.reports.schemas import ReportCreate
from app.modules.users.models import User

NUMBER = "1234567890123"


def _user(db, phone="+221771234567") -> User:
    user = User(
        phone_number=phone,
        full_name="Awa Diop",
        hashed_password=hash_password("Tamarin-Soleil-9"),
    )
    db.add(user)
    db.commit()
    return user


def _create(db, user, **overrides):
    document_type = overrides.pop("document_type", "cni")
    document_number = overrides.pop("document_number", NUMBER)

    data = {
        "kind": "found",
        "documents": [
            {"document_type": document_type, "document_number": document_number}
        ],
        "owner_name": "Modienne GUISSE",
        "region": "Dakar",
        "commune": "Keur Massar",
        "occurred_on": date(2026, 9, 20),
    }
    data.update(overrides)
    return service.create_report(db, user, ReportCreate(**data))


def _search(db, text):
    return [report.id for report in service.list_public_reports(db, search=text)]


def test_search_by_document_number(db_session):
    user = _user(db_session)
    target = _create(db_session, user)
    _create(db_session, user, document_number="9999999999999", commune="Pikine")

    assert _search(db_session, NUMBER) == [target.id]


def test_search_by_document_number_ignores_formatting(db_session):
    user = _user(db_session)
    target = _create(db_session, user)

    assert _search(db_session, "1 234-567 890 123") == [target.id]


def test_search_finds_other_document_types(db_session):
    user = _user(db_session)
    permis = _create(db_session, user, document_type="permis", commune="Mbour")

    assert permis.id in _search(db_session, NUMBER)


def test_search_by_commune(db_session):
    user = _user(db_session)
    target = _create(db_session, user, commune="Keur Massar")
    _create(db_session, user, commune="Pikine", document_number="8888888888888")

    assert _search(db_session, "keur") == [target.id]


def test_search_by_region(db_session):
    user = _user(db_session)
    _create(db_session, user, region="Dakar")
    thies = _create(db_session, user, region="Thies", document_number="7777777777777")

    assert _search(db_session, "thies") == [thies.id]


def test_search_by_masked_name(db_session):
    user = _user(db_session)
    target = _create(db_session, user, owner_name="Modienne GUISSE")
    _create(db_session, user, owner_name="Awa Diop", document_number="6666666666666")

    assert _search(db_session, "Mod") == [target.id]


def test_search_is_case_insensitive(db_session):
    user = _user(db_session)
    target = _create(db_session, user, commune="Keur Massar")

    assert _search(db_session, "KEUR MASSAR") == [target.id]


# Un seul caractere est sous la longueur minimale, donc ignore : on teste
# les jokers a partir de deux caracteres.
@pytest.mark.parametrize("wildcard", ["%%", "__", "%%%", "ke%ur", "Keur_Massar"])
def test_sql_wildcards_are_neutralized(db_session, wildcard):
    user = _user(db_session)
    _create(db_session, user, commune="Keur Massar")

    assert _search(db_session, wildcard) == []


def test_too_short_search_is_ignored(db_session):
    user = _user(db_session)
    report = _create(db_session, user)

    assert _search(db_session, "a") == [report.id]


def test_search_combines_with_filters(db_session):
    user = _user(db_session)
    found = _create(db_session, user, kind="found", commune="Keur Massar")
    _create(db_session, user, kind="lost", commune="Keur Massar", document_number="5555555555555")

    results = service.list_public_reports(
        db_session, search="keur", kind=ReportKind.FOUND
    )

    assert [report.id for report in results] == [found.id]


def test_search_ignores_unpublished_reports(db_session):
    user = _user(db_session)
    report = _create(db_session, user, commune="Keur Massar")
    report.is_published = False
    db_session.commit()

    assert _search(db_session, "keur") == []