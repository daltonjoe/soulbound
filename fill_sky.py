"""sky_daily_positions + sky_events doldurma scripti (tekrar çalıştırılabilir).

Kullanim:
  python fill_sky.py --dry-run
  python fill_sky.py                 # bugunden itibaren 24 ay
  python fill_sky.py --months 6 --start 2026-10-01
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

import swisseph as swe

from module1_engine.engine import PLANETS
from module1_engine.transit_engine import BODY_ID, transit_jd

SUN, MOON = "Sun", "Moon"
BATCH = 500


def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def lon_speed(jd, name):
    pos, _ = swe.calc_ut(jd, PLANETS[name])
    return pos[0], pos[3]


def sign_idx(lon):
    return int(lon // 30) % 12


def bisect(f, a, b, iters=40):
    fa = f(a)
    for _ in range(iters):
        m = (a + b) / 2
        fm = f(m)
        if (fa <= 0) == (fm <= 0):
            a, fa = m, fm
        else:
            b = m
    return (a + b) / 2


def jd_iso(jd):
    y, m, d, h = swe.revjul(jd)
    dt = datetime(y, m, d, tzinfo=timezone.utc) + timedelta(seconds=round(h * 3600))
    return dt.isoformat()


def build(start, n_days):
    days = [start + timedelta(n) for n in range(n_days + 1)]  # +1: son aralik icin
    jds = [transit_jd(d) for d in days]
    data = {name: [lon_speed(jd, name) for jd in jds] for name in PLANETS}

    pos_rows = []
    for i in range(n_days):
        for name in PLANETS:
            lon, spd = data[name][i]
            pos_rows.append({
                "day": days[i].isoformat(),
                "body_id": BODY_ID[name],
                "longitude_degree": round(lon, 6) % 360,
                "speed_deg_per_day": round(spd, 6),
                "sign_id": sign_idx(lon) + 1,
                "retrograde": spd < 0,
            })

    events = {}

    def add(etype, name, jd, sign_lon):
        row = {
            "event_type": etype,
            "body_id": BODY_ID[name],
            "sign_id": sign_idx(sign_lon) + 1,
            "exact_at": jd_iso(jd),
        }
        events[(row["event_type"], row["body_id"], row["exact_at"])] = row

    for i in range(n_days):
        a, b = jds[i], jds[i + 1]
        for name in PLANETS:
            la, sa = data[name][i]
            lb, sb = data[name][i + 1]
            ia, ib = sign_idx(la), sign_idx(lb)

            # Burc gecisi (retro donuslerde geri giris dahil)
            if ia != ib:
                if ib == (ia + 1) % 12:
                    boundary = ib * 30
                elif ia == (ib + 1) % 12:
                    boundary = ia * 30
                else:
                    boundary = None
                if boundary is not None:
                    f = lambda jd, nm=name, bd=boundary: \
                        ((lon_speed(jd, nm)[0] - bd + 180) % 360) - 180
                    t = bisect(f, a, b)
                    add("ingress", name, t, ib * 30 + 15)   

            # Istasyon (hiz isaret degistirir); Gunes/Ay icin yok
            if name not in (SUN, MOON) and sa * sb < 0:
                t = bisect(lambda jd, nm=name: lon_speed(jd, nm)[1], a, b)
                etype = "station_retrograde" if sa > 0 else "station_direct"
                add(etype, name, t, lon_speed(t, name)[0])

        # Yeni ay / dolunay
        ea = (data[MOON][i][0] - data[SUN][i][0]) % 360
        eb = (data[MOON][i + 1][0] - data[SUN][i + 1][0]) % 360
        na, nb = ((ea + 180) % 360) - 180, ((eb + 180) % 360) - 180
        if na < 0 <= nb and nb - na < 90:
            f = lambda jd: (((lon_speed(jd, MOON)[0] - lon_speed(jd, SUN)[0]) % 360 + 180) % 360) - 180
            t = bisect(f, a, b)
            add("new_moon", MOON, t, lon_speed(t, MOON)[0])
        fa, fb = ea - 180, eb - 180
        if fa < 0 <= fb and fb - fa < 90:
            f = lambda jd: ((lon_speed(jd, MOON)[0] - lon_speed(jd, SUN)[0]) % 360) - 180
            t = bisect(f, a, b)
            add("full_moon", MOON, t, lon_speed(t, MOON)[0])

    # Tutulmalar: Swiss Ephemeris bir sonraki tutulmayi dogrudan verir.
    # tret[0] = maksimum an (JD, UT). Pencere: jds[0] .. jds[-1].
    t = jds[0]
    while True:
        _, tret = swe.sol_eclipse_when_glob(t)
        tmax = tret[0]
        if tmax > jds[-1]:
            break
        add("solar_eclipse", SUN, tmax, lon_speed(tmax, SUN)[0])
        t = tmax + 1  # ayni tutulmayi tekrar bulmasin

    t = jds[0]
    while True:
        _, tret = swe.lun_eclipse_when(t)
        tmax = tret[0]
        if tmax > jds[-1]:
            break
        add("lunar_eclipse", MOON, tmax, lon_speed(tmax, MOON)[0])
        t = tmax + 1

    return pos_rows, sorted(events.values(), key=lambda r: r["exact_at"])


def upsert(table, rows, conflict):
    url = f"{os.environ['SUPABASE_URL']}/rest/v1/{table}?on_conflict={conflict}"
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    if key.startswith("eyJ"):  # eski JWT tipi service_role anahtari
        headers["Authorization"] = f"Bearer {key}"
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        req = urllib.request.Request(
            url, data=json.dumps(chunk).encode(), headers=headers, method="POST")
        try:
            urllib.request.urlopen(req, timeout=60)
        except urllib.error.HTTPError as e:
            sys.exit(f"{table} hata {e.code}: {e.read().decode()}")
        print(f"  {table}: {min(i + BATCH, len(rows))}/{len(rows)}")


def main():
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--start", default=date.today().isoformat())
    p.add_argument("--months", type=int, default=24)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if not args.dry_run:
        for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
            if not os.environ.get(k):
                sys.exit(f".env icinde {k} eksik")

    start = date.fromisoformat(args.start)
    n_days = round(args.months * 30.4375)
    pos_rows, ev_rows = build(start, n_days)

    counts = {}
    for r in ev_rows:
        counts[r["event_type"]] = counts.get(r["event_type"], 0) + 1
    print(f"{start} -> +{n_days} gun | positions={len(pos_rows)} events={len(ev_rows)}")
    print("event dagilimi:", counts)

    if args.dry_run:
        for r in ev_rows[:5]:
            print(r)
        return
    upsert("sky_daily_positions", pos_rows, "day,body_id")
    upsert("sky_events", ev_rows, "event_type,body_id,exact_at")
    print("tamam")


if __name__ == "__main__":
    main()