import pytest
from pydantic import ValidationError

from content.meaning_card import MeaningCard, meaning_hash, to_row

VALID = {
    "facts": {"transit_body": "Saturn", "aspect": "square", "natal_point": "Moon"},
    "theme": "identity",
    "valence": "pressure",
    "intensity": 4,
    "keywords": ["restriction", "duty", "emotional reserve"],
    "feels_like": "Emotional needs meet a wall of responsibility.",
    "wants": "Structure around feelings, not suppression of them.",
    "suggests": "Name one need and protect time for it today.",
}


def test_hash_is_stable():
    assert meaning_hash(MeaningCard(**VALID)) == meaning_hash(MeaningCard(**VALID))


def test_hash_changes_on_edit():
    other = {**VALID, "intensity": 3}
    assert meaning_hash(MeaningCard(**VALID)) != meaning_hash(MeaningCard(**other))


def test_unknown_body_rejected():
    bad = {**VALID, "facts": {**VALID["facts"], "natal_point": "Chiron"}}
    with pytest.raises(ValidationError):
        MeaningCard(**bad)


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        MeaningCard(**{**VALID, "extra_planet": "Mars"})


def test_to_row_ids():
    row = to_row(MeaningCard(**VALID))
    assert (row["transit_body_id"], row["aspect_type_id"],
            row["natal_body_id"], row["theme_id"]) == (7, 3, 2, 3)
    assert row["house_id"] is None and row["status"] == "draft"