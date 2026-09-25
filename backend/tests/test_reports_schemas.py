from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.modules.reports.masking import mask_owner_name
from app.modules.reports.models import DocumentType, ReportKind
from app.modules.reports.schemas import ReportCreate, ReportUpdate


def _create(**overrides) -> ReportCreate:
    data = {
        "kind": "lost",
        "document_type": "cni",
        "document_number": "1234567890123",
        "owner_name": "Modienne GUISSE",
        "region": "Dakar",
        "commune": "Keur Massar",
    }
    data.update(overrides)
    return ReportCreate(**data)


# ---------------------------------------------------------------------------
# Masquage du nom
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("full_name", "expected"),
    [
        ("Modienne GUISSE", "Mod... G..."),
        ("Awa Diop", "Awa... D..."),
        ("Fatou Bintou Ndiaye", "Fat... B... N..."),
    ],
)
def test_owner_name_is_masked(full_name, expected):
    assert mask_owner_name(full_name) == expected


def test_masked_name_hides_most_of_the_identity():
    masked = mask_owner_name("Modienne GUISSE")

    assert "Modienne" not in masked
    assert "GUISSE" not in masked


# ---------------------------------------------------------------------------
# Création
# ---------------------------------------------------------------------------


def test_valid_report_is_normalized():
    report = _create(region="  dakar ", commune="  Keur   Massar  ", place_detail="  pres du marche  ")

    assert report.kind is ReportKind.LOST
    assert report.document_type is DocumentType.CNI
    assert report.region == "Dakar"
    assert report.commune == "Keur Massar"
    assert report.place_detail == "pres du marche"


def test_document_number_is_never_exposed_in_repr():
    report = _create(document_number="1234567890123")

    assert "1234567890123" not in repr(report)
    assert report.document_number.get_secret_value() == "1234567890123"


def test_document_number_is_optional():
    report = _create(document_number=None)

    assert report.document_number is None


def test_blank_document_number_becomes_none():
    assert _create(document_number="   ").document_number is None


@pytest.mark.parametrize("number", ["12", "A" * 31])
def test_invalid_document_number_length_is_rejected(number):
    with pytest.raises(ValidationError):
        _create(document_number=number)


def test_formatted_document_number_is_accepted():
    report = _create(document_number="1 234-567.890 12")

    assert report.document_number.get_secret_value() == "1 234-567.890 12"


def test_unknown_region_is_rejected():
    with pytest.raises(ValidationError):
        _create(region="Bamako")


def test_future_date_is_rejected():
    tomorrow = datetime.now(UTC).date() + timedelta(days=1)

    with pytest.raises(ValidationError):
        _create(occurred_on=tomorrow)


def test_today_is_accepted():
    today = datetime.now(UTC).date()

    assert _create(occurred_on=today).occurred_on == today


def test_very_old_date_is_rejected():
    with pytest.raises(ValidationError):
        _create(occurred_on=date(2015, 1, 1))


def test_invalid_kind_is_rejected():
    with pytest.raises(ValidationError):
        _create(kind="peut-etre")


def test_extra_fields_are_forbidden():
    with pytest.raises(ValidationError):
        _create(status="closed")

    with pytest.raises(ValidationError):
        _create(user_id="00000000-0000-0000-0000-000000000000")


def test_owner_name_with_digits_is_rejected():
    with pytest.raises(ValidationError):
        _create(owner_name="Awa 2024")


# ---------------------------------------------------------------------------
# Modification
# ---------------------------------------------------------------------------


def test_update_accepts_only_editable_fields():
    update = ReportUpdate(commune="Pikine", is_published=False)

    assert update.commune == "Pikine"
    assert update.is_published is False


@pytest.mark.parametrize("field", ["document_type", "kind", "status", "document_number"])
def test_update_rejects_identity_fields(field):
    with pytest.raises(ValidationError):
        ReportUpdate(**{field: "cni"})