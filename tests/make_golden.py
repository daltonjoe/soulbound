"""Golden dosyasini uretir. Sadece bilerek calistir (motor/ephemeris degistiginde)."""
import json
import os
from datetime import datetime

import swisseph as swe

from module1_engine.engine import calculate_julian_day, calculate_planets

# UTC anlari: farkli yillar, retro/direkt donemler, yil sonu/basi sinirlari
CASES = [
    "1950-03-21T06:30:00", "1963-11-22T18:30:00", "1969-07-20T20:17:00",
    "1975-01-01T00:00:00", "1980-06-15T09:45:00", "1984-02-29T12:00:00",
    "1987-08-17T03:10:00", "1990-12-31T23:59:00", "1992-05-05T14:20:00",
    "1995-09-09T21:05:00", "1999-08-11T10:03:00", "2000-01-01T12:00:00",
    "2003-04-18T07:40:00", "2008-10-08T16:25:00", "2012-12-21T11:11:00",
    "2016-03-08T01:30:00", "2019-07-04T13:00:00", "2023-11-05T19:45:00",
    "2026-10-03T07:16:00", "2030-01-15T08:00:00",
]


def main():
    out = {"swe_version": getattr(swe, "version", "unknown"), "cases": []}
    for iso in CASES:
        dt = datetime.fromisoformat(iso)
        planets = calculate_planets(calculate_julian_day(dt))
        out["cases"].append({
            "utc": iso,
            "planets": {
                name: {"lon": round(p["longitude"], 6), "retro": p["retrograde"]}
                for name, p in planets.items()
            },
        })
    path = os.path.join(os.path.dirname(__file__), "golden_planets.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"{len(CASES)} vaka yazildi: {path}")


if __name__ == "__main__":
    main()