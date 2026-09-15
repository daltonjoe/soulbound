# SOULBOUND/main.py
"""
FastAPI app — run with: uvicorn main:app --reload --port 8000

CHANGES:
  - locale field added to NatalChartRequest, AstroReportRequest,
    PlanetReportRequest, ForecastRequest
  - locale passed through to all service/interpreter calls
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, FastAPI, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional, Any

from astro_integration.core.planet_interpreter import generate_planet_report
from astro_integration.core.forecast_service import generate_forecast, VALID_TYPES
from astro_integration.core.prompt_loader import get_period_label
from astro_integration.core.auth import verify_token, create_app_token

load_dotenv()

from astro_integration.core.service import generate_chart_service

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

def custom_rate_limit_handler(request: Request, exc: Any):
    detail = getattr(exc, "detail", str(exc))
    return JSONResponse(
        status_code=429,
        content={"error": f"Rate limit exceeded: {detail}"}
    )

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="SoulBound Astro API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @app.get("/")
    def root():
        return FileResponse(os.path.join(_STATIC_DIR, "index.html"))

    @app.get("/style.css")
    def style_css():
        return FileResponse(os.path.join(_STATIC_DIR, "style.css"),
                            media_type="text/css")

    @app.get("/app.js")
    def app_js():
        return FileResponse(os.path.join(_STATIC_DIR, "app.js"),
                            media_type="application/javascript")

    @app.get("/manifest.json")
    def manifest():
        return FileResponse(os.path.join(_STATIC_DIR, "manifest.json"))

    @app.get("/service-worker.js")
    def sw():
        return FileResponse(os.path.join(_STATIC_DIR, "service-worker.js"),
                            media_type="application/javascript")

    @app.get("/icon-{size}.png")
    def icon(size: int):
        path = os.path.join(_STATIC_DIR, f"icon-{size}.png")
        if os.path.isfile(path):
            return FileResponse(path)
        return FileResponse(os.path.join(_STATIC_DIR, "icon-192.png"))

VALID_PLANETS = {
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"
}


# ─── Request Schemas ─────────────────────────────────────────────────────────

class NatalChartRequest(BaseModel):
    birth_date: str
    birth_time: str
    city: str
    locale: str = "tr"            # ← new (was always "tr" before)
    include_report: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None


class AstroReportRequest(BaseModel):
    birth_date: str
    birth_time: str
    city: str
    locale: str = "tr"            # ← new
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None


class PlanetReportRequest(BaseModel):
    planet_name: str
    chart_data: dict
    locale: str = "tr"            # ← new


class ForecastRequest(BaseModel):
    analysis_type: str
    chart_data: dict
    locale: str = "tr"            # ← new


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "SoulBound Astro API"}


@app.get("/app-token")
def get_app_token():
    """
    Flutter uygulaması başlarken bu endpoint'i çağırır.
    Dönen token sonraki tüm isteklerde Authorization header'ında kullanılır.
    Bu endpoint'i production'da IP whitelist veya API key ile koruyun.
    """
    return {"token": create_app_token()}


# ─── Natal Chart ──────────────────────────────────────────────────────────────

@app.post("/generateNatalChart", dependencies=[Depends(verify_token)])
@limiter.limit("30/minute")
def generate_natal_chart(request: Request, payload: NatalChartRequest):
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    return generate_chart_service(
        birth_date=payload.birth_date,
        birth_time=payload.birth_time,
        city=payload.city,
        locale=payload.locale,         # ← passed through
        gemini_api_key=gemini_key,
        include_report=payload.include_report,
        latitude=payload.latitude,
        longitude=payload.longitude,
        timezone=payload.timezone,
    )


# ─── Astro Report ─────────────────────────────────────────────────────────────

@app.post("/generateAstroReport", dependencies=[Depends(verify_token)])
@limiter.limit("5/minute")
def generate_astro_report(request: Request, payload: AstroReportRequest):
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    return generate_chart_service(
        birth_date=payload.birth_date,
        birth_time=payload.birth_time,
        city=payload.city,
        locale=payload.locale,         # ← passed through
        latitude=payload.latitude,
        longitude=payload.longitude,
        timezone=payload.timezone,
        gemini_api_key=gemini_key,
        include_report=True,
    )


# ─── Planet Report ────────────────────────────────────────────────────────────

@app.post("/generatePlanetReport", dependencies=[Depends(verify_token)])
@limiter.limit("10/minute")
def generate_planet_report_endpoint(request: Request, payload: PlanetReportRequest):
    if payload.planet_name not in VALID_PLANETS:
        return {
            "status": "error",
            "error_code": "INVALID_PLANET",
            "message": f"Invalid planet: {payload.planet_name}",
        }
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        return {"status": "error", "error_code": "NO_API_KEY",
                "message": "Gemini API key not set."}

    report = generate_planet_report(
        planet_name=payload.planet_name,
        chart_data=payload.chart_data,
        gemini_api_key=gemini_key,
        locale=payload.locale,         # ← passed through
    )
    if not report:
        return {"status": "error", "error_code": "AI_ERROR",
                "message": "Report could not be generated."}

    return {
        "status": "success",
        "planet_name": payload.planet_name,
        "report": report,
    }


# ─── Forecast ─────────────────────────────────────────────────────────────────

@app.post("/forecast-analysis", dependencies=[Depends(verify_token)])
@limiter.limit("10/minute")
def forecast_analysis(request: Request, payload: ForecastRequest):
    if payload.analysis_type not in VALID_TYPES:
        return {
            "status": "error",
            "error_code": "INVALID_TYPE",
            "message": f"Invalid analysis type. Valid: {list(VALID_TYPES)}",
        }
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        return {"status": "error", "error_code": "NO_API_KEY",
                "message": "Gemini API key not set."}

    report = generate_forecast(
        analysis_type=payload.analysis_type,
        chart_data=payload.chart_data,
        gemini_api_key=gemini_key,
        locale=payload.locale,         # ← passed through
    )
    if not report:
        return {"status": "error", "error_code": "AI_ERROR",
                "message": "Forecast could not be generated."}

    return {
        "status": "success",
        "analysis_type": payload.analysis_type,
        "period_label": get_period_label(payload.analysis_type, payload.locale),
        "report": report,
    }
