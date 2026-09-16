# astro_integration/core/service.py
"""
Core service layer: city input → coordinates → timezone → natal chart → AI report.
Called by main.py FastAPI endpoints.

Changes from original:
  - locale flows into generate_chart_service and to AstroInterpreter
  - Error messages loaded from prompt_loader (locale-aware)
  - All other logic is identical
"""
from __future__ import annotations

from typing import Optional
import uuid
import pytz
import json
import redis
import hashlib
import json as json_lib
from datetime import datetime, date
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from module1_engine import calculate_natal_chart, build_full_chart, to_json
from astro_integration.core.interpreter import AstroInterpreter
from astro_integration.core.prompt_loader import get_error_message, get_error_suggestion


# ── Redis Cache ───────────────────────────────────────────────────────────────

def _get_redis():
    """Redis bağlantısı — bağlanamazsa None döner, uygulama çalışmaya devam eder."""
    try:
        r = redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            socket_connect_timeout=2,
            decode_responses=True,
        )
        r.ping()
        return r
    except Exception:
        print("[cache] Redis bağlantısı kurulamadı, cache devre dışı.")
        return None


def _chart_cache_key(birth_date: str, birth_time: str, city: str) -> str:
    raw = f"{birth_date}|{birth_time}|{city.lower().strip()}"
    return f"chart:{hashlib.md5(raw.encode()).hexdigest()}"


# ─── City / Timezone Resolution ─────────────────────────────────────────────

def resolve_city(city_query: str) -> Optional[dict]:
    try:
        geolocator = Nominatim(user_agent="soulbound_astro_v1", timeout=10)
        location = geolocator.geocode(city_query, language="tr")
        if not location:
            return None
        return {
            "city_query": city_query,
            "city_resolved": location.address,
            "latitude": round(location.latitude, 6),
            "longitude": round(location.longitude, 6),
        }
    except Exception as e:
        print(f"[geo error] {e}")
        return None


def resolve_timezone(lat: float, lng: float) -> Optional[dict]:
    try:
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lat=lat, lng=lng)
        if not tz_name:
            return None
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)
        utc_offset_raw = now.strftime("%z")
        utc_offset_fmt = f"{utc_offset_raw[:3]}:{utc_offset_raw[3:]}"
        return {"timezone": tz_name, "utc_offset": utc_offset_fmt}
    except Exception as e:
        print(f"[tz error] {e}")
        return None


# ─── Input Validation ────────────────────────────────────────────────────────

def validate_input(birth_date: str, birth_time: str, city: str) -> Optional[str]:
    import re
    try:
        d = datetime.strptime(birth_date, "%Y-%m-%d").date()
    except ValueError:
        return "INVALID_DATE_FORMAT"
    if d > date.today():
        return "FUTURE_DATE"
    if d.year < 1800 or d.year > date.today().year:
        return "INVALID_DATE_RANGE"
    if not re.match(r"^\d{2}:\d{2}$", birth_time):
        return "INVALID_TIME_FORMAT"
    hour, minute = int(birth_time[:2]), int(birth_time[3:])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return "INVALID_TIME_VALUE"
    if len(city.strip()) < 2:
        return "CITY_TOO_SHORT"
    return None


# ─── Main Service ─────────────────────────────────────────────────────────────

def generate_chart_service(
    birth_date: str,
    birth_time: str,
    city: str,
    locale: str = "tr",
    gemini_api_key: str = None,
    include_report: bool = False,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    timezone: Optional[str] = None,
) -> dict:
    _redis = _get_redis()
    request_id = f"req_{uuid.uuid4().hex[:8]}"

    # ── 1. Validate ──────────────────────────────────────────────────────────
    error_code = validate_input(birth_date, birth_time, city)
    if error_code:
        return {
            "status": "error",
            "error_code": error_code,
            "message": get_error_message(error_code, locale),
            "request_id": request_id,
        }

    # ── Cache kontrolü ───────────────────────────────────────────────────────
    _cache_key = _chart_cache_key(birth_date, birth_time, city)
    if _redis and not include_report:
        cached = _redis.get(_cache_key)
        if cached:
            print(f"[cache] HIT — {_cache_key}")
            return json_lib.loads(cached)
        print(f"[cache] MISS — {_cache_key}")

    # ── 2. Coordinates + Timezone ────────────────────────────────────────────
    if latitude is not None and longitude is not None and timezone:
        geo = {
            "city_query": city,
            "city_resolved": city,
            "latitude": latitude,
            "longitude": longitude,
        }
        tz_info = {"timezone": timezone, "utc_offset": ""}
    else:
        geo = resolve_city(city)
        if not geo:
            return {
                "status": "error",
                "error_code": "CITY_NOT_FOUND",
                "message": get_error_message("CITY_NOT_FOUND", locale),
                "suggestion": get_error_suggestion("CITY_NOT_FOUND", locale),
                "request_id": request_id,
            }
        tz_info = resolve_timezone(geo["latitude"], geo["longitude"])
        if not tz_info:
            return {
                "status": "error",
                "error_code": "TIMEZONE_ERROR",
                "message": get_error_message("TIMEZONE_ERROR", locale),
                "suggestion": get_error_suggestion("TIMEZONE_ERROR", locale),
                "request_id": request_id,
            }

    # ── 3. UTC offset ────────────────────────────────────────────────────────
    try:
        local_tz_obj = pytz.timezone(tz_info["timezone"])
        local_dt = local_tz_obj.localize(
            datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
        )
        utc_dt = local_dt.astimezone(pytz.utc)
        utc_offset_raw = local_dt.strftime("%z")
        tz_info["utc_offset"] = f"{utc_offset_raw[:3]}:{utc_offset_raw[3:]}"
    except Exception as e:
        return {
            "status": "error",
            "error_code": "TIMEZONE_PARSE_ERROR",
            "message": f"Timezone conversion error: {str(e)}",
            "request_id": request_id,
        }

    # ── 4. Natal chart ───────────────────────────────────────────────────────
    try:
        chart = calculate_natal_chart(
            year=local_dt.year, month=local_dt.month, day=local_dt.day,
            hour=local_dt.hour, minute=local_dt.minute, city=city,
        )
        full_chart = build_full_chart(chart)
    except Exception as e:
        return {
            "status": "error",
            "error_code": "EPHEM_ERROR",
            "message": get_error_message("EPHEM_ERROR", locale),
            "detail": str(e),
            "request_id": request_id,
        }

    # ── 5. AI report (optional) ──────────────────────────────────────────────
    ai_report = None
    ai_error = None
    if include_report and gemini_api_key:
        try:
            interpreter = AstroInterpreter(gemini_api_key)
            ai_report = interpreter.generate_report(full_chart, locale=locale)
            if not ai_report:
                ai_error = "AI report could not be generated. Check API key or quota."
        except Exception as _err:
            print(f"[service] AI report error: {type(_err).__name__}: {_err}")
            ai_error = f"{type(_err).__name__}: {_err}"

    # ── 6. Response ──────────────────────────────────────────────────────────
    result = {
        "status": "success",
        "request_id": request_id,
        "input": {
            "birth_date": birth_date,
            "birth_time_local": birth_time,
            "birth_time_utc": utc_dt.isoformat(),
            "julian_day": full_chart["input"]["julian_day"],
        },
        "location": {**geo, **tz_info},
        "summary": full_chart["summary"],
        "planets": full_chart["planets"],
        "aspects": full_chart["aspects"],
        "angles": full_chart["angles"],
        "ai_report": ai_report,
    }
    if ai_error:
        result["ai_error"] = ai_error

    # Sadece chart verisi cache'lenir (AI raporu hariç, include_report=False ise)
    if _redis and not include_report:
        try:
            _redis.setex(_cache_key, 86400, json_lib.dumps(result))
            print(f"[cache] SET — {_cache_key} (24 saat)")
        except Exception as e:
            print(f"[cache] SET hatası: {e}")

    return result
