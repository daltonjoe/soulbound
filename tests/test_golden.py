import json
import os
from datetime import datetime

import pytest

from module1_engine.engine import calculate_julian_day, calculate_planets

TOL_DEG = 0.01
GOLDEN = os.path.join(os.path.dirname(__file__), "golden_planets.json")


def angdiff(a, b):
    return abs((a - b + 180) % 360 - 180)


def _cases():
    with open(GOLDEN, encoding="utf-8") as f:
        return json.load(f)["cases"]


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["utc"])
def test_planet_positions_match_golden(case):
    dt = datetime.fromisoformat(case["utc"])
    got = calculate_planets(calculate_julian_day(dt))
    for name, exp in case["planets"].items():
        assert angdiff(got[name]["longitude"], exp["lon"]) < TOL_DEG, name
        assert got[name]["retrograde"] == exp["retro"], f"{name} retro"


def test_sun_at_j2000_anchor():
    # Mutlak capa: 2000-01-01 12:00 UT'de Gunes ~280.37 (Oglak 10.37)
    got = calculate_planets(calculate_julian_day(datetime(2000, 1, 1, 12, 0)))
    assert angdiff(got["Sun"]["longitude"], 280.37) < 0.02
    assert got["Sun"]["sign_index"] == 9