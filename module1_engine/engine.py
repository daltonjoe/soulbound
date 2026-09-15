import swisseph as swe
import os
from datetime import datetime
from .geo import get_coordinates, to_utc

EPHE_PATH = os.getenv("SE_EPHE_PATH", os.path.join(os.path.dirname(__file__), "../ephemeris"))
swe.set_ephe_path(EPHE_PATH)

PLANETS = {
    "Sun":     swe.SUN,
    "Moon":    swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus":   swe.VENUS,
    "Mars":    swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn":  swe.SATURN,
    "Uranus":  swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto":   swe.PLUTO,
}

SIGNS = [
    "Koç", "Boğa", "İkizler", "Yengeç",
    "Aslan", "Başak", "Terazi", "Akrep",
    "Yay", "Oğlak", "Kova", "Balık"
]

def decimal_to_dms(decimal: float) -> dict:
    d = int(decimal)
    m = int((decimal - d) * 60)
    s = round(((decimal - d) * 60 - m) * 60, 2)
    return {"degrees": d, "minutes": m, "seconds": s}

def get_sign_and_degree(longitude: float) -> dict:
    sign_index = int(longitude / 30) % 12
    degree_in_sign = longitude % 30
    return {
        "sign": SIGNS[sign_index],
        "sign_index": sign_index,
        "longitude": round(longitude, 6),
        "degree_in_sign": round(degree_in_sign, 4),
        "dms": decimal_to_dms(degree_in_sign)
    }

def calculate_julian_day(utc_dt: datetime) -> float:
    return swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
    )

def calculate_planets(jd: float) -> dict:
    results = {}
    for name, planet_id in PLANETS.items():
        try:
            pos, ret = swe.calc_ut(jd, planet_id)
            longitude = pos[0]
            speed = pos[3]
            planet_data = get_sign_and_degree(longitude)
            planet_data["speed"] = round(speed, 6)
            planet_data["retrograde"] = speed < 0
            planet_data["latitude"] = round(pos[1], 6)
            results[name] = planet_data
        except Exception as e:
            results[name] = {"error": str(e)}
    return results

def calculate_houses(jd: float, lat: float, lon: float, house_system: str = "P") -> dict:
    try:
        cusps, ascmc = swe.houses(jd, lat, lon, bytes(house_system, 'ascii'))
        
        
        houses = {}
        for i in range(12):  # 0-11 arası, cusps[0] = ev 1
            longitude = cusps[i]
            house_data = get_sign_and_degree(longitude)
            house_data["house_number"] = i + 1
            houses[f"house_{i+1}"] = house_data

        ascendant = get_sign_and_degree(ascmc[0])
        ascendant["type"] = "Ascendant"
        mc = get_sign_and_degree(ascmc[1])
        mc["type"] = "Midheaven"

        return {
            "houses": houses,
            "ascendant": ascendant,
            "midheaven": mc,
            "house_system": house_system
        }
    except Exception as e:
        print("HOUSES HATA:", str(e))
        return {"error": str(e)}

def get_house_placement(planet_longitude: float, cusps: list) -> int:
    planet = planet_longitude % 360
    for i in range(12):
        start = cusps[i] % 360
        end = cusps[(i + 1) % 12] % 360
        if start < end:
            if start <= planet < end:
                return i + 1
        else:  # Koç noktasını geçen ev
            if planet >= start or planet < end:
                return i + 1
    return 12

def calculate_natal_chart(
    year: int, month: int, day: int,
    hour: int, minute: int,
    city: str,
    house_system: str = "P"
) -> dict:

    geo = get_coordinates(city)
    utc_dt = to_utc(year, month, day, hour, minute, geo["timezone"])
    jd = calculate_julian_day(utc_dt)
    planets = calculate_planets(jd)
    house_data = calculate_houses(jd, geo["latitude"], geo["longitude"], house_system)

    if "houses" in house_data:
        cusps_raw, _ = swe.houses(jd, geo["latitude"], geo["longitude"], bytes(house_system, 'ascii'))
        cusps_list = list(cusps_raw)
        for planet_name, planet_info in planets.items():
            if "longitude" in planet_info:
                house_num = get_house_placement(planet_info["longitude"], cusps_list)
                planets[planet_name]["house"] = house_num

    return {
        "input": {
            "birth_date": f"{year}-{month:02d}-{day:02d}",
            "birth_time": f"{hour:02d}:{minute:02d}",
            "city": city,
            "timezone": geo["timezone"],
            "utc_time": utc_dt.isoformat(),
            "julian_day": round(jd, 6)
        },
        "location": {
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
            "address": geo["address"]
        },
        "planets": planets,
        "houses": house_data["houses"],
        "angles": {
            "ascendant": house_data["ascendant"],
            "midheaven": house_data["midheaven"]
        },
        "house_system": house_system
    }