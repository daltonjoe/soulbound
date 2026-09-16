# astro_integration/core/planet_interpreter.py
"""
Per-planet Gemini report generator.
REPLACES the previous hardcoded-Turkish version.

Changes from original:
  - generate_planet_report() accepts `locale` parameter
  - Prompt built via prompt_loader.get_planet_prompt()
  - Language enforcement is automatic
"""
from __future__ import annotations

import json
import requests
from typing import Optional

from .prompt_loader import get_planet_prompt


PLANET_TR = {
    "Sun": "Güneş", "Moon": "Ay", "Mercury": "Merkür",
    "Venus": "Venüs", "Mars": "Mars", "Jupiter": "Jüpiter",
    "Saturn": "Satürn", "Uranus": "Uranüs",
    "Neptune": "Neptün", "Pluto": "Plüton",
}

# English names are already in the key — used when locale="en"
PLANET_EN = {k: k for k in PLANET_TR}


def _planet_display_name(planet_name: str, locale: str) -> str:
    if locale == "tr":
        return PLANET_TR.get(planet_name, planet_name)
    return planet_name  # English: keep original name


def _format_aspects(planet_name: str, aspects: list, locale: str) -> str:
    planet_aspects = [
        a for a in aspects
        if a.get("planet1") == planet_name or a.get("planet2") == planet_name
    ]
    lines = []
    for a in planet_aspects:
        other = a["planet2"] if a["planet1"] == planet_name else a["planet1"]
        other_display = _planet_display_name(other, locale)
        this_display = _planet_display_name(planet_name, locale)
        lines.append(
            f"  - {this_display} {a['aspect']} "
            f"{other_display} (orb: {a['orb']:.2f}°, "
            f"{'major' if a['is_major'] else 'minor'})"
        )
    return "\n".join(lines) if lines else "  - No significant aspects"


def _format_elements(element_dist: dict) -> tuple[str, str]:
    total = sum(element_dist.values()) or 1
    lines = [
        f"  - {el}: {count} planets ({round(count/total*100)}%)"
        for el, count in sorted(element_dist.items(), key=lambda x: -x[1])
    ]
    dominant = max(element_dist, key=element_dist.get) if element_dist else "?"
    return "\n".join(lines), dominant


def build_planet_prompt(
    planet_name: str,
    chart_data: dict,
    locale: str = "tr",
) -> str:
    planets = chart_data.get("planets", {})
    aspects = chart_data.get("aspects", [])
    summary = chart_data.get("summary", {})
    element_dist = summary.get("element_distribution", {})

    planet_data = planets.get(planet_name, {})
    sign = planet_data.get("sign", "?")
    house = planet_data.get("house", "?")
    retrograde = planet_data.get("retrograde", False)
    degree = float(planet_data.get("degree_in_sign", 0))

    planet_display = _planet_display_name(planet_name, locale)
    aspects_text = _format_aspects(planet_name, aspects, locale)
    element_lines, dominant_element = _format_elements(element_dist)

    other_planets_json = json.dumps(
        {k: {"sign": v.get("sign"), "house": v.get("house")}
         for k, v in planets.items() if k != planet_name},
        ensure_ascii=False, indent=2
    )

    return get_planet_prompt(
        planet_name=planet_name,
        planet_tr=planet_display,
        sign=sign,
        house=house,
        degree=degree,
        retrograde=retrograde,
        aspects_text=aspects_text,
        element_lines=element_lines,
        dominant_element=dominant_element,
        other_planets_json=other_planets_json,
        locale=locale,
    )


def generate_planet_report(
    planet_name: str,
    chart_data: dict,
    gemini_api_key: str,
    locale: str = "tr",
) -> Optional[str]:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.6-flash:generateContent?key={gemini_api_key}"
    )

    prompt = build_planet_prompt(planet_name, chart_data, locale)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.75,
            "maxOutputTokens": 4000,
            "topP": 0.95,
        },
    }

    try:
        response = requests.post(
            url, json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=90,
        )
        if response.status_code != 200:
            print(f"[planet_interpreter] Gemini error: {response.status_code}")
            return None
        response.encoding = "utf-8"
        try:
            result = json.loads(response.content.decode("utf-8"))
        except Exception:
            result = response.json()
        candidates = result.get("candidates", [])
        if candidates:
            _text = candidates[0]["content"]["parts"][0]["text"]
            _rep = _text.count("\ufffd")
            if _rep:
                print(f"[planet_interpreter] ⚠️  {_rep} U+FFFD bulundu, onarım deneniyor...")
                try:
                    _text = _text.encode("latin-1").decode("utf-8")
                except Exception:
                    pass
            return _text
        return None
    except Exception as e:
        print(f"[planet_interpreter error] {e}")
        return None
