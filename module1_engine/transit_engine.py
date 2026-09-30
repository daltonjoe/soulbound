"""Language-independent transit x natal event engine."""
import math
from datetime import date, datetime, time, timezone

from .engine import PLANETS, calculate_julian_day, calculate_planets

ENGINE_VERSION = "transit-v1"
BODY_ID = {name: i + 1 for i, name in enumerate(PLANETS)}
ASPECT_ANGLE = {1: 0, 2: 60, 3: 90, 4: 120, 5: 180}
TRANSIT_ORB = {
    1: 3.0, 2: 1.5, 3: 3.0, 4: 3.0, 5: 3.0,
    6: 2.5, 7: 2.5, 8: 2.0, 9: 2.0, 10: 2.0,
}
ORB_SCALE = 0.41
W_TRANSIT = {1: 1.0, 2: 0.8, 3: 0.7, 4: 0.7, 5: 0.8,
             6: 0.9, 7: 1.0, 8: 1.0, 9: 0.9, 10: 1.0}
W_NATAL = {1: 1.0, 2: 1.0, 3: 0.7, 4: 0.7, 5: 0.7,
           6: 0.6, 7: 0.7, 8: 0.5, 9: 0.5, 10: 0.5}
W_ASPECT = {1: 1.0, 2: 0.6, 3: 0.9, 4: 0.7, 5: 1.0}
APPLYING_BONUS = 1.15


def signed_deviation(transit_lon: float, natal_lon: float, angle: float) -> float:
    diff = (transit_lon - natal_lon) % 360
    candidates = []
    for target in (angle % 360, (360 - angle) % 360):
        candidates.append((diff - target + 180) % 360 - 180)
    return min(candidates, key=abs)


def is_applying(deviation: float, transit_speed: float) -> bool:
    return deviation * transit_speed < 0


def transit_jd(day: date, tz_name: str = "UTC") -> float:
    utc_noon = datetime.combine(day, time(12, 0), tzinfo=timezone.utc)
    return calculate_julian_day(utc_noon)


def compute_daily_events(natal_lons: dict, day: date, tz_name: str = "UTC",
                         top_n: int = 5) -> list:
    transit = calculate_planets(transit_jd(day, tz_name))
    events = []
    for t_name, transit_body in transit.items():
        if "longitude" not in transit_body:
            continue
        transit_id = BODY_ID[t_name]
        sigma_orb = TRANSIT_ORB[transit_id] * ORB_SCALE
        for natal_id, natal_lon in natal_lons.items():
            for aspect_id, angle in ASPECT_ANGLE.items():
                deviation = signed_deviation(
                    transit_body["longitude"], natal_lon, angle
                )
                if abs(deviation) > sigma_orb:
                    continue
                sigma = sigma_orb / 2
                applying = is_applying(deviation, transit_body["speed"])
                score = (
                    W_TRANSIT[transit_id]
                    * W_NATAL[natal_id]
                    * W_ASPECT[aspect_id]
                    * math.exp(-(deviation ** 2) / (2 * sigma ** 2))
                    * (APPLYING_BONUS if applying else 1.0)
                )
                events.append({
                    "transit_body_id": transit_id,
                    "aspect_type_id": aspect_id,
                    "natal_body_id": natal_id,
                    "orb": round(abs(deviation), 4),
                    "applying": applying,
                    "score": round(score, 4),
                })
    events.sort(key=lambda event: event["score"], reverse=True)
    for rank, event in enumerate(events[:top_n], 1):
        event["rank"] = rank
    return events[:top_n]
