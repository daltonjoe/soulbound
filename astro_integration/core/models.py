"""
Core data models — Swiss Ephemeris çıktısı için Pydantic modelleri.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class AspectType(str, Enum):
    CONJUNCTION = "Kavuşum"
    SEXTILE = "Altıgen"
    SQUARE = "Kare"
    TRINE = "Üçgen"
    OPPOSITION = "Karşıt"
    QUINCUNX = "Yüz-elli"


class Element(str, Enum):
    FIRE = "Ateş"
    EARTH = "Toprak"
    AIR = "Hava"
    WATER = "Su"


@dataclass
class Planet:
    name: str                    # "Sun", "Moon", etc.
    sign: str                    # "Yay", "Koç", etc.
    degree: float                # 0.76
    house: int                   # 11
    retrograde: bool = False

    def to_api_dict(self) -> dict:
        return {
            "planet": self.name,
            "sign": self.sign,
            "degree": round(self.degree, 2),
            "house": self.house,
            "retrograde": self.retrograde,
        }


@dataclass
class Aspect:
    planet1: str
    aspect_type: str
    planet2: str
    orb: float
    is_major: bool = True

    def to_api_dict(self) -> dict:
        return {
            "planet1": self.planet1,
            "aspect": self.aspect_type,
            "planet2": self.planet2,
            "orb": round(self.orb, 2),
            "is_major": self.is_major,
        }


@dataclass
class NatalChart:
    """Swiss Ephemeris'ten gelen ham natal chart verisi."""
    birth_date: str              # "1998-11-23"
    birth_time_utc: str          # "1998-11-23T06:30:00+00:00"
    julian_day: float
    latitude: float
    longitude: float
    planets: list[Planet] = field(default_factory=list)
    aspects: list[Aspect] = field(default_factory=list)
    ascendant_sign: str = ""
    ascendant_degree: float = 0.0
    mc_sign: str = ""
    mc_degree: float = 0.0
    sun_sign: str = ""
    moon_sign: str = ""
    rising_sign: str = ""
    elements: dict[str, int] = field(default_factory=dict)
    retrogrades: list[str] = field(default_factory=list)