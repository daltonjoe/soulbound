"""
Swiss Ephemeris JSON çıktısını internal NatalChart modeline dönüştürür.
"""
from __future__ import annotations
import json
from pathlib import Path
from core.models import NatalChart, Planet, Aspect


PLANET_NAME_MAP = {
    "Sun": "Sun", "Moon": "Moon", "Mercury": "Mercury",
    "Venus": "Venus", "Mars": "Mars", "Jupiter": "Jupiter",
    "Saturn": "Saturn", "Uranus": "Uranus", "Neptune": "Neptune",
    "Pluto": "Pluto",
}


def parse_swiss_ephemeris_json(raw: dict) -> NatalChart:
    """
    Swiss Ephemeris JSON çıktısını NatalChart'a dönüştürür.
    raw dict yapısı test_output.json'dan gelir.
    """
    meta = raw.get("meta", {})
    summary = raw.get("summary", {})
    planets_raw = raw.get("planets", [])
    aspects_raw = raw.get("aspects", [])
    angles = raw.get("angles", {})

    planets = []
    retrogrades = []
    for p in planets_raw:
        is_retro = p.get("retrograde", False)
        planet = Planet(
            name=p["name"],
            sign=p["sign"],
            degree=float(p["degree"]),
            house=int(p["house"]),
            retrograde=is_retro,
        )
        planets.append(planet)
        if is_retro:
            retrogrades.append(p["name"])

    aspects = []
    for a in aspects_raw:
        aspects.append(Aspect(
            planet1=a["planet1"],
            aspect_type=a["aspect"],
            planet2=a["planet2"],
            orb=float(a["orb"]),
            is_major=a.get("is_major", True),
        ))

    return NatalChart(
        birth_date=meta.get("birth_date", ""),
        birth_time_utc=meta.get("birth_time_utc", ""),
        julian_day=float(meta.get("julian_day", 0)),
        latitude=float(meta.get("latitude", 0)),
        longitude=float(meta.get("longitude", 0)),
        planets=planets,
        aspects=aspects,
        ascendant_sign=angles.get("asc_sign", summary.get("rising", "")),
        ascendant_degree=float(angles.get("asc_degree", 0)),
        mc_sign=angles.get("mc_sign", ""),
        mc_degree=float(angles.get("mc_degree", 0)),
        sun_sign=summary.get("sun_sign", ""),
        moon_sign=summary.get("moon_sign", ""),
        rising_sign=summary.get("rising", ""),
        elements=summary.get("elements", {}),
        retrogrades=retrogrades,
    )


def load_from_file(path: str | Path) -> NatalChart:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return parse_swiss_ephemeris_json(raw)