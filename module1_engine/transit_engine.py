"""Transit x natal olay motoru. Dil-bağımsız: sadece ID ve sayı döner.
ID'ler DB ile aynı: planet 1..10 (Sun..Pluto), aspect 1..5 (major).
"""
import math
from datetime import date, datetime, time
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from .engine import PLANETS, calculate_julian_day, calculate_planets

ENGINE_VERSION = "transit-v1"

BODY_ID = {name: i + 1 for i, name in enumerate(PLANETS)}  # Sun=1..Pluto=10
ID_BODY = {v: k for k, v in BODY_ID.items()}

# aspect_types.id -> açı (DB ile aynı)
ASPECT_ANGLE = {1: 0, 2: 60, 3: 90, 4: 120, 5: 180}

# Transit orb (derece, tam genişlik). Monte Carlo ile ORB_SCALE kalibre edilir.
TRANSIT_ORB = {1: 3.0, 2: 1.5, 3: 3.0, 4: 3.0, 5: 3.0,
               6: 2.5, 7: 2.5, 8: 2.0, 9: 2.0, 10: 2.0}
ORB_SCALE = 0.41  # calibrate_orbs.py çıktısıyla güncelle

# Ağırlıklar (başlangıç; kalibrasyonla ayarlanır)
W_TRANSIT = {1: 1.0, 2: 0.8, 3: 0.7, 4: 0.7, 5: 0.8,
             6: 0.9, 7: 1.0, 8: 1.0, 9: 0.9, 10: 1.0}
W_NATAL = {1: 1.0, 2: 1.0, 3: 0.7, 4: 0.7, 5: 0.7,
           6: 0.6, 7: 0.7, 8: 0.5, 9: 0.5, 10: 0.5}
W_ASPECT = {1: 1.0, 2: 0.6, 3: 0.9, 4: 0.7, 5: 1.0}
APPLYING_BONUS = 1.15


def signed_deviation(transit_lon: float, natal_lon: float, angle: float) -> float:
    """Tam aspektten işaretli sapma (derece). >0: aspekt geçilmiş."""
    diff = (transit_lon - natal_lon) % 360
    best = None
    for target in {angle % 360, (360 - angle) % 360}:
        d = (diff - target + 180) % 360 - 180
        if best is None or abs(d) < abs(best):
            best = d
    return best


def is_applying(deviation: float, transit_speed: float) -> bool:
    """Natal nokta sabit. Sapma ile hız ters işaretliyse tam aspekte yaklaşıyor."""
    return deviation * transit_speed < 0


def transit_jd(day: date, tz_name: str = "UTC") -> float:
    """Kullanıcının yerel gününün öğlesi (Ay 13°/gün hareket eder)."""
    local = datetime.combine(day, time(12, 0), tzinfo=ZoneInfo(tz_name))
    return calculate_julian_day(local.astimezone(ZoneInfo("UTC")))


def compute_daily_events(natal_lons: dict, day: date, tz_name: str = "UTC",
                         top_n: int = 6) -> list:
    """natal_lons: {planet_id(int): ekliptik boylam}  (user_chart_placements.longitude_degree)"""
    transit = calculate_planets(transit_jd(day, tz_name))
    events = []
    for t_name, t in transit.items():
        if "longitude" not in t:
            continue
        t_id = BODY_ID[t_name]
        sigma_orb = TRANSIT_ORB[t_id] * ORB_SCALE
        for n_id, n_lon in natal_lons.items():
            for a_id, angle in ASPECT_ANGLE.items():
                dev = signed_deviation(t["longitude"], n_lon, angle)
                if abs(dev) > sigma_orb:
                    continue
                sigma = sigma_orb / 2
                applying = is_applying(dev, t["speed"])
                score = (W_TRANSIT[t_id] * W_NATAL[n_id] * W_ASPECT[a_id]
                         * math.exp(-(dev ** 2) / (2 * sigma ** 2))
                         * (APPLYING_BONUS if applying else 1.0))
                events.append({
                    "transit_body_id": t_id, "aspect_type_id": a_id,
                    "natal_body_id": n_id, "orb": round(abs(dev), 4),
                    "applying": applying, "score": round(score, 4),
                })
    events.sort(key=lambda e: e["score"], reverse=True)
    for rank, e in enumerate(events[:top_n], 1):
        e["rank"] = rank
    return events[:top_n]
