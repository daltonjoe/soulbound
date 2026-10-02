"""meaning_card: şablon anlamının dil-bağımsız tek kaynağı (kural 11)."""
from __future__ import annotations

import hashlib
import json
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

Body = Literal["Sun", "Moon", "Mercury", "Venus", "Mars",
               "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
Aspect = Literal["conjunction", "sextile", "square", "trine", "opposition"]
Theme = Literal["love", "career", "identity", "health"]
Valence = Literal["power", "pressure", "trouble", "neutral"]

# DB ID eşlemeleri (RefIds ve content_themes ile birebir, SQL ile doğrulandı)
BODY_IDS = {"Sun": 1, "Moon": 2, "Mercury": 3, "Venus": 4, "Mars": 5,
            "Jupiter": 6, "Saturn": 7, "Uranus": 8, "Neptune": 9, "Pluto": 10}
ASPECT_IDS = {"conjunction": 1, "sextile": 2, "square": 3,
              "trine": 4, "opposition": 5}
THEME_IDS = {"love": 1, "career": 2, "identity": 3, "health": 4}


class Facts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transit_body: Body
    aspect: Aspect
    natal_point: Body


class MeaningCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    kind: Literal["transit_daily"] = "transit_daily"
    facts: Facts
    theme: Theme
    valence: Valence
    intensity: int = Field(ge=1, le=5)
    keywords: List[str] = Field(min_length=3, max_length=6)
    feels_like: str = Field(min_length=10, max_length=200)
    wants: str = Field(min_length=10, max_length=200)
    suggests: str = Field(min_length=10, max_length=200)
    avoid: List[str] = Field(default_factory=list, max_length=4)


def canonical_json(card: MeaningCard) -> str:
    data = card.model_dump(mode="json")
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def meaning_hash(card: MeaningCard) -> str:
    return hashlib.sha256(canonical_json(card).encode("utf-8")).hexdigest()


def to_row(card: MeaningCard, variant_no: int = 1) -> dict:
    """snippet_templates insert satırı. house_id bu aşamada her zaman None."""
    return {
        "kind": card.kind,
        "transit_body_id": BODY_IDS[card.facts.transit_body],
        "aspect_type_id": ASPECT_IDS[card.facts.aspect],
        "natal_body_id": BODY_IDS[card.facts.natal_point],
        "house_id": None,
        "theme_id": THEME_IDS[card.theme],
        "valence": card.valence,
        "intensity": card.intensity,
        "variant_no": variant_no,
        "meaning_card": card.model_dump(mode="json"),
        "meaning_hash": meaning_hash(card),
        "status": "draft",
    }