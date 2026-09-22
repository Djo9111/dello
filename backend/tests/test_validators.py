import pytest

from app.shared.validators import normalize_full_name, normalize_senegal_mobile


@pytest.mark.parametrize(
    "raw",
    [
        "77 123 45 67",
        "+221771234567",
        "00221 77-123-45-67",
        "221771234567",
        "(77) 123.45.67",
    ],
)
def test_senegal_mobile_formats_are_normalized(raw):
    assert normalize_senegal_mobile(raw) == "+221771234567"


@pytest.mark.parametrize(
    "raw",
    [
        "33 821 00 00",  # fixe, pas de SMS possible
        "7712345",  # trop court
        "+2217712345678",  # trop long
        "+33612345678",  # étranger
        "٧٧١٢٣٤٥٦٧",  # chiffres arabes orientaux
        "",
    ],
)
def test_invalid_numbers_are_rejected(raw):
    with pytest.raises(ValueError):
        normalize_senegal_mobile(raw)


def test_full_name_is_cleaned():
    assert normalize_full_name("  Awa   N'Diaye-Sène ") == "Awa N'Diaye-Sène"


@pytest.mark.parametrize(
    "raw",
    [
        "A",  # trop court
        "Awa1",  # chiffre
        "<script>",  # balises
        "Awa; DROP TABLE",  # ponctuation
        "- '",  # aucune lettre
        "a" * 101,  # trop long
    ],
)
def test_invalid_full_names_are_rejected(raw):
    with pytest.raises(ValueError):
        normalize_full_name(raw)