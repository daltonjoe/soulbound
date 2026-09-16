# astro_integration/core/forecast_service.py
"""
Forecast service — daily / weekly / monthly / yearly.
REPLACES the previous hardcoded-Turkish version.

Changes from original:
  - generate_forecast() accepts `locale` parameter (default "tr")
  - Prompts and period labels loaded from prompt_loader
  - Language enforcement is automatic
  - PERIOD_LABELS exported for backward compatibility with main.py
"""
from __future__ import annotations

from typing import Optional
import json
import requests
from datetime import datetime, date

from .prompt_loader import (
    get_forecast_prompt,
    get_period_label,
    get_prompts,
)


VALID_TYPES = {"daily", "weekly", "monthly", "yearly"}

# Backward-compat: main.py imports PERIOD_LABELS from here
# Now dynamically reads from the default locale (tr)
def _make_period_labels() -> dict:
    try:
        return get_prompts("tr")["period_labels"]
    except Exception:
        return {"daily": "Günlük", "weekly": "Haftalık", "monthly": "Aylık", "yearly": "Yıllık"}

PERIOD_LABELS = _make_period_labels()


# ── Period info builders ───────────────────────────────────────────────────

def _build_period_info(analysis_type: str) -> str:
    today = date.today()
    if analysis_type == "daily":
        return f"Date: {today.strftime('%d %B %Y, %A')}"
    if analysis_type == "weekly":
        from datetime import timedelta
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        return f"Week: {week_start.strftime('%d %B')} – {week_end.strftime('%d %B %Y')}"
    if analysis_type == "monthly":
        return f"Month: {today.strftime('%B %Y')}"
    if analysis_type == "yearly":
        return f"Year: {today.year}"
    return str(today)


# ── Chart data formatters ──────────────────────────────────────────────────

def _format_planets(planets: dict) -> str:
    lines = []
    for name, data in planets.items():
        retro = " (Retrograde)" if data.get("retrograde") else ""
        lines.append(
            f"  - {name}: {data.get('sign', '?')} "
            f"{data.get('degree_in_sign', 0):.1f}° "
            f"· House {data.get('house', '?')}{retro}"
        )
    return "\n".join(lines) if lines else "No data"


def _format_aspects(aspects: list) -> str:
    major = [a for a in aspects if a.get("is_major")]
    lines = [
        f"  - {a.get('planet1')} {a.get('aspect')} "
        f"{a.get('planet2')} (orb: {a.get('orb', 0):.1f}°)"
        for a in major[:12]
    ]
    return "\n".join(lines) if lines else "No significant aspects"


def _format_elements(element_dist: dict) -> str:
    total = sum(element_dist.values()) or 1
    lines = [
        f"  - {el}: {count} planets ({round(count/total*100)}%)"
        for el, count in sorted(element_dist.items(), key=lambda x: -x[1])
    ]
    dominant = max(element_dist, key=element_dist.get) if element_dist else "?"
    lines.append(f"  → Dominant element: {dominant}")
    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────

def generate_forecast(
    analysis_type: str,
    chart_data: dict,
    gemini_api_key: str,
    locale: str = "tr",
) -> Optional[str]:
    """
    Generates a forecast report via Gemini.

    Args:
        analysis_type: "daily" | "weekly" | "monthly" | "yearly"
        chart_data:    Full chart payload from Flutter (planets, aspects, summary)
        gemini_api_key: Gemini API key
        locale:        "tr" (default) or "en"
    """
    if analysis_type not in VALID_TYPES:
        return None

    planets_text = _format_planets(chart_data.get("planets", {}))
    aspects_text = _format_aspects(chart_data.get("aspects", []))
    elements_text = _format_elements(
        chart_data.get("summary", {}).get("element_distribution", {})
    )
    period_text = _build_period_info(analysis_type)

    prompt = get_forecast_prompt(
        analysis_type=analysis_type,
        planets=planets_text,
        aspects=aspects_text,
        elements=elements_text,
        period_info=period_text,
        locale=locale,
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.6-flash:generateContent?key={gemini_api_key}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 6000,
            "topP": 0.95,
        },
    }

    try:
        response = requests.post(
            url, json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=120,
        )
        if response.status_code != 200:
            print(f"[forecast] Gemini error: {response.status_code}")
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
                print(f"[forecast] ⚠️  {_rep} U+FFFD bulundu, onarım deneniyor...")
                try:
                    _text = _text.encode("latin-1").decode("utf-8")
                except Exception:
                    pass
            return _text
        return None
    except Exception as e:
        print(f"[forecast error] {e}")
        return None
