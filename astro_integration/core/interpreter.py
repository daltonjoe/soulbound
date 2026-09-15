# astro_integration/core/interpreter.py
"""
AstroInterpreter — calls Gemini with locale-aware system prompt.
REPLACES the previous hardcoded-Turkish version.

Changes from original:
  - generate_report() now accepts `locale` parameter (default "tr")
  - System prompt loaded from prompt_loader (JSON file)
  - Language enforcement injected into every Gemini call
"""
from __future__ import annotations

import json
import requests
from typing import Optional

from .prompt_loader import get_natal_system_prompt


class AstroInterpreter:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={self.api_key}"
        )

    def generate_report(
        self,
        chart_data: dict,
        locale: str = "tr",
    ) -> Optional[str]:
        """
        Generates an AI natal analysis report.

        Args:
            chart_data: Full chart dict from build_full_chart()
            locale:     "tr" (default) or "en"

        Returns:
            Report text string, or None on failure.
        """
        system_prompt = get_natal_system_prompt(locale)
        chart_json_str = json.dumps(chart_data, ensure_ascii=False, indent=2)
        combined_prompt = f"{system_prompt}\n\nANALYSIS DATA:\n{chart_json_str}"

        payload = {
            "contents": [{"parts": [{"text": combined_prompt}]}],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 12000,
                "topP": 0.95,
                "candidateCount": 1,
            },
        }

        try:
            response = requests.post(
                self.url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120,
            )
            if response.status_code != 200:
                print(f"[interpreter] Gemini error: {response.status_code} — {response.text[:200]}")
                return None

            result = response.json()
            if result.get("candidates"):
                return result["candidates"][0]["content"]["parts"][0]["text"]
            return None

        except requests.exceptions.RequestException as e:
            print(f"[interpreter] Connection error: {e}")
            return None
