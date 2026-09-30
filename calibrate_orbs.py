"""Monte Carlo orb kalibrasyonu.
Kullanım (backend kökünden):  python calibrate_orbs.py --charts 3000 --target 4.5
Çıktı: günlük ortalama olay/harita + önerilen ORB_SCALE + skor yüzdelikleri.
"""
import argparse
import numpy as np
import swisseph as swe

from module1_engine import transit_engine as te
from module1_engine.engine import PLANETS


def positions(jd_start, n_days):
    out = np.zeros((n_days, 10))
    for d in range(n_days):
        for i, pid in enumerate(PLANETS.values()):
            out[d, i] = swe.calc_ut(jd_start + d + 0.0, pid)[0][0]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--charts", type=int, default=3000)
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--target", type=float, default=4.5)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    jd_2026 = swe.julday(2026, 1, 1, 12.0)
    trans = positions(jd_2026, a.days)                       # (D,10)
    jd_1940 = swe.julday(1940, 1, 1, 12.0)
    pool = positions(jd_1940, 365 * 70)                      # doğum günü havuzu
    natal = pool[rng.integers(0, len(pool), a.charts)]       # (N,10)

    orb = np.array([te.TRANSIT_ORB[i + 1] for i in range(10)])  # transit başına
    total_hits, scores = 0, []
    for s in range(0, a.charts, 200):
        nat = natal[s:s + 200]
        diff = (trans[None, :, :, None] - nat[:, None, None, :]) % 360  # N,D,10(t),10(n)
        for aid, ang in te.ASPECT_ANGLE.items():
            dev = np.minimum(np.abs(diff - ang), np.abs(diff - (360 - ang) % 360))
            dev = np.minimum(dev, 360 - dev)
            hit = dev <= orb[None, None, :, None]
            total_hits += hit.sum()
            sigma = (orb / 2)[None, None, :, None]
            sc = np.exp(-(dev ** 2) / (2 * sigma ** 2))[hit] * te.W_ASPECT[aid]
            scores.append(sc[:200000])

    mean_events = total_hits / (a.charts * a.days)
    scale = a.target / mean_events
    sc_all = np.concatenate(scores)
    print(f"Günlük ortalama olay/harita (orb scale=1): {mean_events:.2f}")
    print(f"Hedef {a.target} -> önerilen ORB_SCALE ≈ {scale:.2f}")
    print("Skor yüzdelikleri (p30/p50/p70/p90):",
          np.percentile(sc_all, [30, 50, 70, 90]).round(3).tolist())


if __name__ == "__main__":
    main()
