# astro_integration/core/prompt_loader.py
"""
Central prompt loader.
- Reads prompts/tr.json or prompts/en.json based on `locale`
- Default: "tr"
- Falls back to "tr" if locale file is missing
- Injects strict language enforcement into every Gemini prompt

Place this file at:  astro_integration/core/prompt_loader.py
Place JSON files at: SOULBOUND/prompts/tr.json and en.json
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Optional

# Resolve the prompts/ directory relative to this file:
# astro_integration/core/ → ../../prompts/
_PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "prompts",
)

SUPPORTED_LOCALES = {"tr", "en","ar","de","es","fr","pt"}
DEFAULT_LOCALE = "tr"


@lru_cache(maxsize=8)
def _load_raw(locale: str) -> dict:
    """
    Load and cache the JSON file for `locale`.
    Falls back to DEFAULT_LOCALE if the requested file doesn't exist.
    """
    path = os.path.join(_PROMPTS_DIR, f"{locale}.json")
    if not os.path.exists(path):
        if locale != DEFAULT_LOCALE:
            return _load_raw(DEFAULT_LOCALE)
        raise FileNotFoundError(
            f"Default prompt file not found: {path}\n"
            f"Make sure prompts/tr.json exists at {_PROMPTS_DIR}"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_prompts(locale: Optional[str] = None) -> dict:
    """
    Public accessor.  Returns the full prompt dict for the given locale.
    """
    safe_locale = (locale or DEFAULT_LOCALE).lower().strip()
    if safe_locale not in SUPPORTED_LOCALES:
        safe_locale = DEFAULT_LOCALE
    return _load_raw(safe_locale)


# ── Convenience helpers ────────────────────────────────────────────────────


def get_natal_system_prompt(locale: Optional[str] = None) -> str:
    """
    Returns the natal chart system prompt with language enforcement appended.
    """
    p = get_prompts(locale)
    base = p["natal_system_prompt"]
    enforce = p["language_enforce"]
    return f"{base}\n\n---\n{enforce}"


def get_planet_prompt(
    planet_name: str,
    planet_tr: str,
    sign: str,
    house: int | str,
    degree: float,
    retrograde: bool,
    aspects_text: str,
    element_lines: str,
    dominant_element: str,
    other_planets_json: str,
    locale: Optional[str] = None,
) -> str:
    """
    Builds the per-planet Gemini prompt.
    Template variables are filled from the JSON file.
    """
    p = get_prompts(locale)
    retro_text = " (Retrograde)" if retrograde else ""
    template = p["planet_prompt_template"]
    enforce = p["language_enforce"]

    filled = template.format(
        planet_tr=planet_tr,
        retro_text=retro_text,
        sign=sign,
        degree=degree,
        house=house,
        aspects_text=aspects_text,
        element_lines=element_lines,
        dominant_element=dominant_element,
        other_planets_json=other_planets_json,
    )
    return f"{filled}\n\n---\n{enforce}"


def get_forecast_prompt(
    analysis_type: str,
    planets: str,
    aspects: str,
    elements: str,
    period_info: str,
    locale: Optional[str] = None,
) -> str:
    """
    Builds the forecast Gemini prompt for daily/weekly/monthly/yearly.
    """
    p = get_prompts(locale)
    template = p["forecast"].get(analysis_type)
    if not template:
        raise ValueError(f"Unknown analysis_type: {analysis_type}")
    enforce = p["language_enforce"]

    filled = template.format(
        planets=planets,
        aspects=aspects,
        elements=elements,
        period_info=period_info,
    )
    return f"{filled}\n\n---\n{enforce}"


def get_period_label(analysis_type: str, locale: Optional[str] = None) -> str:
    p = get_prompts(locale)
    return p["period_labels"].get(analysis_type, analysis_type)


def get_error_message(error_code: str, locale: Optional[str] = None) -> str:
    p = get_prompts(locale)
    return p["error_messages"].get(error_code, p["error_messages"]["GENERIC_ERROR"])


def get_error_suggestion(error_code: str, locale: Optional[str] = None) -> Optional[str]:
    p = get_prompts(locale)
    suggestion_key = f"{error_code}_SUGGESTION"
    return p["error_messages"].get(suggestion_key)
