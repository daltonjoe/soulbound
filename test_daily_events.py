import json
from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import main
from astro_integration.core import auth
from module1_engine import transit_engine


def make_request(token="user-token"):
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/daily-events",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "query_string": b"",
        "server": ("test", 80),
        "client": ("test", 80),
        "scheme": "http",
    })


def test_daily_events_schema_and_limit(monkeypatch):
    profile_id = uuid4()
    rows = {
        "user_profiles": [{
            "id": str(profile_id), "user_id": "user-1", "birth_time_known": False
        }],
        "user_chart_placements": [
            {"planet_id": 1, "longitude_degree": 0},
            {"planet_id": 2, "longitude_degree": 10},
        ],
    }
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setattr(main, "_supabase_get", lambda table, params, access_token: rows.get(table, []))
    monkeypatch.setattr(
        main, "compute_daily_events",
        lambda natal_lons, event_date, tz_name, top_n: [
            {"rank": rank, "transit_body_id": 1, "aspect_type_id": 1,
             "natal_body_id": 1, "orb": 0.8, "applying": True, "score": 0.71}
            for rank in range(1, 6)
        ],
    )

    response = main.daily_events(
        make_request(), main.DailyEventsRequest(
            profile_id=profile_id, date="2026-10-01"
        ), "user-1"
    )
    body = json.loads(response.body)
    assert body["date"] == "2026-10-01"
    assert body["engine_version"] == "transit-v1"
    assert len(body["events"]) == 5
    assert body["events"][0]["rank"] == 1


def test_daily_events_rejects_foreign_profile(monkeypatch):
    profile_id = uuid4()
    monkeypatch.setattr(
        main, "_supabase_get",
        lambda table, params, access_token: [{
            "id": str(profile_id), "user_id": "different-user",
            "birth_time_known": True
        }],
    )

    with pytest.raises(HTTPException) as error:
        main.daily_events(
            make_request(), main.DailyEventsRequest(
                profile_id=profile_id, date="2026-10-01"
            ), "user-1"
        )
    assert error.value.status_code == 403


def test_transit_engine_uses_utc_noon_and_orb_scale(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        transit_engine, "calculate_planets",
        lambda jd: (
            captured.setdefault("jd", jd),
            {"Sun": {"longitude": 0, "speed": 1}},
        )[1],
    )
    events = transit_engine.compute_daily_events({1: 0}, date(2026, 10, 1))
    assert transit_engine.ORB_SCALE == 0.41
    assert events
    assert captured["jd"] == transit_engine.transit_jd(date(2026, 10, 1), "UTC")


def test_get_user_id_uses_supabase_jwks_and_refreshes_unknown_kid(monkeypatch):
    auth._JWKS_CACHE = None
    jwks_calls = []
    responses = []

    class Response:
        def __init__(self, kid):
            self.kid = kid

        def raise_for_status(self):
            return None

        def json(self):
            return {"keys": [{"kid": self.kid, "kty": "EC"}]}

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    responses.extend([Response("old-kid"), Response("new-kid")])
    monkeypatch.setattr(
        auth.requests,
        "get",
        lambda url, timeout: (
            jwks_calls.append(url),
            responses.pop(0),
        )[1],
    )
    monkeypatch.setattr(
        auth.jwt,
        "get_unverified_header",
        lambda token: {"alg": "ES256", "kid": "new-kid"},
    )
    decoded = {}

    def decode(token, key, **kwargs):
        decoded.update(key=key, kwargs=kwargs)
        return {"sub": "user-1"}

    monkeypatch.setattr(auth.jwt, "decode", decode)

    user_id = auth.get_user_id(
        auth.HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="supabase-token"
        )
    )

    assert user_id == "user-1"
    assert jwks_calls == [
        "https://example.supabase.co/auth/v1/.well-known/jwks.json",
        "https://example.supabase.co/auth/v1/.well-known/jwks.json",
    ]
    assert decoded["key"]["kid"] == "new-kid"
    assert decoded["kwargs"] == {
        "algorithms": ["ES256"],
        "audience": "authenticated",
        "issuer": "https://example.supabase.co/auth/v1",
    }
