"""
autofill_pipeline.py
=====================
Tam pipeline:
  1. 20 farklı doğum haritası profili üret (çeşitli burçlar, şehirler)
  2. Her biri için FreeAstrologyAPI → Western planets/houses/aspects çek
  3. Ephemeris verisiyle birleştir → Claude'a gönder → Türkçe yorum al
  4. dataset.jsonl dosyasına Llama/Mistral fine-tune formatında yaz

Çalıştır:
    python autofill_pipeline.py
    python autofill_pipeline.py --count 10 --out dataset.jsonl

Gereksinimler:
    pip install httpx anthropic python-dotenv
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── API Anahtarları ──────────────────────────────────────────────────────────
FREE_ASTRO_KEY  = os.getenv("FREE_ASTRO_API_KEY",  "Jky6DTfaPF8VnwjoO7L4K2zf1MqQedFDNANtH7la")
ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY",   "")
FREE_ASTRO_BASE = "https://json.freeastrologyapi.com"

# ── Burç → İngilizce map (FreeAstrologyAPI İngilizce döndürür) ──────────────
SIGN_TR = {
    "Aries":"Koç","Taurus":"Boğa","Gemini":"İkizler","Cancer":"Yengeç",
    "Leo":"Aslan","Virgo":"Başak","Libra":"Terazi","Scorpio":"Akrep",
    "Sagittarius":"Yay","Capricorn":"Oğlak","Aquarius":"Kova","Pisces":"Balık",
}
PLANET_TR = {
    "Sun":"Güneş","Moon":"Ay","Mercury":"Merkür","Venus":"Venüs","Mars":"Mars",
    "Jupiter":"Jüpiter","Saturn":"Satürn","Uranus":"Uranüs","Neptune":"Neptün",
    "Pluto":"Plüton","Ascendant":"Yükselen","Midheaven":"MC",
}
ASPECT_TR = {
    "Conjunction":"Kavuşum","Sextile":"Altıgen","Square":"Kare",
    "Trine":"Üçgen","Opposition":"Karşıt","Quincunx":"Yüz-elli",
}

# ── 20 Çeşitli Doğum Profili ─────────────────────────────────────────────────
# Farklı burçlar, şehirler, saatler → modelin genelleme yapabilmesi için çeşitlilik şart
BIRTH_PROFILES = [
    # (isim_kodu, yıl, ay, gün, saat, dakika, lat,    lon,   timezone)
    ("profile_01", 1998, 11, 23,  6, 30,  37.87,  32.49,  3.0),   # Konya — Yay
    ("profile_02", 1990,  3, 21, 12,  0,  41.01,  28.97,  3.0),   # İstanbul — Koç
    ("profile_03", 1985,  6, 15,  8, 45,  39.92,  32.85,  3.0),   # Ankara — İkizler
    ("profile_04", 1995,  9,  5, 23, 15,  38.42,  27.14,  3.0),   # İzmir — Başak
    ("profile_05", 2000,  1, 10, 15, 30,  40.76,  29.92,  3.0),   # Bursa — Oğlak
    ("profile_06", 1978, 12,  3,  4, 20,  36.89,  30.71,  3.0),   # Antalya — Yay
    ("profile_07", 1992,  4, 19, 18, 55,  37.00,  35.32,  3.0),   # Adana — Koç
    ("profile_08", 1988,  7, 22,  7, 10,  41.67,  26.56,  3.0),   # Edirne — Yengeç
    ("profile_09", 2002, 10, 28, 21,  0,  39.73,  37.02,  3.0),   # Sivas — Akrep
    ("profile_10", 1975,  2, 14,  9, 40,  40.19,  29.06,  3.0),   # Bursa — Kova
    ("profile_11", 1983,  8,  7, 16, 25,  37.96,  40.22,  3.0),   # Diyarbakır — Aslan
    ("profile_12", 1997,  5, 20, 11,  5,  41.30,  36.36,  3.0),   # Samsun — Boğa
    ("profile_13", 1970,  3,  1,  2, 30,  40.18,  44.51,  4.0),   # Erzurum — Balık
    ("profile_14", 2005, 11, 22,  5, 55,  37.87,  32.49,  3.0),   # Konya — Akrep/Yay
    ("profile_15", 1993, 12, 21, 13, 15,  41.01,  28.97,  3.0),   # İstanbul — Oğlak
    ("profile_16", 1980,  6,  4, 20, 10,  38.42,  27.14,  3.0),   # İzmir — İkizler
    ("profile_17", 1965,  9, 23,  0, 45,  37.96,  40.22,  3.0),   # Diyarbakır — Terazi
    ("profile_18", 2003,  1, 20,  8, 20,  39.92,  32.85,  3.0),   # Ankara — Oğlak/Kova
    ("profile_19", 1987,  4,  5, 17, 35,  36.89,  30.71,  3.0),   # Antalya — Koç
    ("profile_20", 1999,  7, 23, 22,  0,  40.76,  29.92,  3.0),   # Bursa — Yengeç/Aslan
]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FreeAstrologyAPI — Western Natal Chart
# ═══════════════════════════════════════════════════════════════════════════════

async def fetch_western_chart(
    client: httpx.AsyncClient,
    year: int, month: int, day: int,
    hour: int, minute: int,
    lat: float, lon: float, tz: float,
) -> dict:
    """
    3 Western endpoint'i paralel çağır → birleştir.

    FreeAstrologyAPI request body:
      year, month, date, hours, minutes, seconds,
      latitude, longitude, timezone,
      config: {observation_point, ayanamsha}

    Önemli: ayanamsha = "tropical" → Western astroloji (Vedic için "lahiri")
    """
    body = {
        "year": year, "month": month, "date": day,
        "hours": hour, "minutes": minute, "seconds": 0,
        "latitude": lat, "longitude": lon,
        "timezone": tz,
        "config": {
            "observation_point": "topocentric",
            "ayanamsha": "tropical",
        },
    }

    try:
        planets_r, houses_r, aspects_r = await asyncio.gather(
            _post(client, "/western-astrology/planets",  body),
            _post(client, "/western-astrology/houses",   body),
            _post(client, "/western-astrology/aspects",  body),
        )
        return _merge_western(planets_r, houses_r, aspects_r)

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 401:
            raise RuntimeError("FREE_ASTRO_API_KEY geçersiz!")
        if status == 429:
            raise RuntimeError("Günlük 50 istek limiti doldu!")
        log.error(f"HTTP {status}: {e.response.text[:200]}")
        raise
    except Exception as e:
        log.error(f"FreeAstrologyAPI hatası: {e}")
        raise


async def _post(client: httpx.AsyncClient, endpoint: str, body: dict) -> dict:
    r = await client.post(endpoint, json=body)
    r.raise_for_status()
    return r.json()


def _merge_western(planets_r: dict, houses_r: dict, aspects_r: dict) -> dict:
    """
    3 endpoint cevabını birleştir.

    FreeAstrologyAPI Western response yapısı:
    planets: {"output": [{"name":"Sun","full_degree":240.7,"norm_degree":0.7,
                          "speed":1.01,"is_retro":"false","sign":"Sagittarius",
                          "house":11}, ...]}
    houses:  {"output": [{"house":1,"sign":"Sagittarius","degree":23.1}, ...]}
    aspects: {"output": [{"planet1":"Sun","planet2":"Venus",
                          "type":"Conjunction","orb":6.01,"is_major":true}, ...]}
    """
    def _list(r, key="output"):
        val = r.get(key, r.get("data", []))
        return val if isinstance(val, list) else []

    planets_list = _list(planets_r)
    houses_list  = _list(houses_r)
    aspects_list = _list(aspects_r)

    # Gezegenleri parse et
    planets = []
    sun_sign = moon_sign = rising = ""

    for p in planets_list:
        name    = p.get("name", "")
        sign_en = p.get("sign", "")
        sign_tr = SIGN_TR.get(sign_en, sign_en)
        is_retro = str(p.get("is_retro", "false")).lower() == "true"
        house   = int(p.get("house", 0))

        planets.append({
            "name": name, "name_tr": PLANET_TR.get(name, name),
            "sign": sign_tr, "sign_en": sign_en,
            "degree": round(float(p.get("norm_degree", p.get("degree", 0))), 2),
            "full_degree": round(float(p.get("full_degree", 0)), 2),
            "house": house,
            "retrograde": is_retro,
            "speed": round(float(p.get("speed", 0)), 4),
        })

        if name == "Sun":   sun_sign = sign_tr
        if name == "Moon":  moon_sign = sign_tr

    # Yükselen: planets listesinde "Ascendant" olabilir veya house 1'den
    for p in planets_list:
        if p.get("name") in ("Ascendant", "ASC"):
            rising = SIGN_TR.get(p.get("sign", ""), p.get("sign", ""))
            break
    if not rising and houses_list:
        for h in houses_list:
            if int(h.get("house", h.get("id", 0))) == 1:
                rising = SIGN_TR.get(h.get("sign", ""), h.get("sign", ""))
                break

    # Aspektleri parse et
    aspects = []
    for a in aspects_list:
        p1_en  = a.get("planet1", a.get("body1", ""))
        p2_en  = a.get("planet2", a.get("body2", ""))
        asp_en = a.get("type",    a.get("aspect", ""))
        aspects.append({
            "planet1": p1_en,  "planet1_tr": PLANET_TR.get(p1_en, p1_en),
            "planet2": p2_en,  "planet2_tr": PLANET_TR.get(p2_en, p2_en),
            "type": ASPECT_TR.get(asp_en, asp_en), "type_en": asp_en,
            "orb": round(float(a.get("orb", 0)), 2),
            "is_major": bool(a.get("is_major", True)),
        })

    # Element sayımı (Ateş=Koç,Aslan,Yay | Toprak=Boğa,Başak,Oğlak | ...)
    fire  = ["Koç","Aslan","Yay"]
    earth = ["Boğa","Başak","Oğlak"]
    air   = ["İkizler","Terazi","Kova"]
    water = ["Yengeç","Akrep","Balık"]
    elements = {"Ateş": 0, "Toprak": 0, "Hava": 0, "Su": 0}
    for p in planets:
        s = p["sign"]
        if s in fire:   elements["Ateş"]   += 1
        elif s in earth: elements["Toprak"] += 1
        elif s in air:   elements["Hava"]   += 1
        elif s in water: elements["Su"]     += 1

    retrogrades = [p["name"] for p in planets if p["retrograde"]]

    return {
        "sun_sign": sun_sign, "moon_sign": moon_sign, "rising": rising,
        "planets": planets, "houses": houses_list, "aspects": aspects,
        "elements": elements, "retrogrades": retrogrades,
        "_raw": {"planets": planets_r, "houses": houses_r, "aspects": aspects_r},
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Claude — Türkçe Yorum Üret
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Sen deneyimli bir astrologsun. Doğum haritası verilerini alıp
kişiye özel, derinlikli ve psikolojik açıdan anlamlı Türkçe yorumlar üretiyorsun.

ÇIKTI KURALLARI:
1. YALNIZCA geçerli JSON döndür — başka hiçbir şey yazma, markdown yok.
2. Türkçe yorum yaz. Her yorum 2-4 cümle olsun.
3. Gerçekçi ve özgün ol — "enerjik ve hırslı" gibi klişelerden kaçın.

JSON ŞEMASI:
{
  "sun": {"description": "..."},
  "moon": {"description": "..."},
  "rising": {"description": "..."},
  "aspects": [{"planets": "Gezegen1 - Gezegen2", "meaning": "..."}],
  "elements": {"dominant": "...", "comment": "..."},
  "retrogrades": "...",
  "summary": "..."
}"""


def _build_prompt(chart: dict, birth_meta: dict) -> str:
    year, month, day = birth_meta["year"], birth_meta["month"], birth_meta["day"]
    hour, minute     = birth_meta["hour"], birth_meta["minute"]
    lat, lon         = birth_meta["lat"], birth_meta["lon"]

    planet_lines = "\n".join(
        f"  {p['name']:<10} {p['sign']:<10} {p['degree']:>5.1f}°  "
        f"Ev:{p['house']}{'  ℞' if p['retrograde'] else ''}"
        for p in chart["planets"]
    )
    aspect_lines = "\n".join(
        f"  {a['planet1_tr']} {a['type']} {a['planet2_tr']} (orb:{a['orb']:.1f}°)"
        for a in chart["aspects"] if a["is_major"]
    )
    retro = ", ".join(chart["retrogrades"]) or "Yok"
    elem  = chart["elements"]

    return f"""Doğum: {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d} UTC
Koordinat: {lat:.2f}°K, {lon:.2f}°D

Güneş: {chart['sun_sign']} | Ay: {chart['moon_sign']} | Yükselen: {chart['rising']}
Elementler: Ateş:{elem['Ateş']} Toprak:{elem['Toprak']} Hava:{elem['Hava']} Su:{elem['Su']}
Retrograde: {retro}

GEZEGENLER:
{planet_lines}

MAJOR ASPEKTLER:
{aspect_lines}

Bu haritayı yorumla."""


async def get_claude_interpretation(prompt: str) -> dict:
    """
    Claude API'ye gönder → JSON parse et.
    Not: Bu fonksiyon anthropic SDK yoksa httpx ile doğrudan çağırır.
    """
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_KEY)
        msg = await client.messages.create(
            model="claude-haiku-4-5-20251001",   # hızlı + ucuz, dataset üretimi için ideal
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        await client.close()
        raw_text = msg.content[0].text.strip()

    except ImportError:
        # anthropic SDK yoksa httpx ile direkt çağır
        async with httpx.AsyncClient(timeout=60) as hclient:
            r = await hclient.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1500,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            raw_text = r.json()["content"][0]["text"].strip()

    # JSON parse
    clean = raw_text
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(clean)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Dataset Kaydı Üret
# ═══════════════════════════════════════════════════════════════════════════════

def build_records(chart: dict, interp: dict, birth_meta: dict) -> list[dict]:
    """
    Bir natal chart → 5 (user, assistant) çifti → Llama/Mistral fine-tune formatı.

    Llama 3 chat template:
    <|begin_of_text|>
    <|start_header_id|>system<|end_header_id|>...<|eot_id|>
    <|start_header_id|>user<|end_header_id|>...<|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>...<|eot_id|>

    Ama JSONL formatında {"messages": [...]} şeklinde saklıyoruz.
    Unsloth/Axolotl bu formatı direkt okur.
    """
    system = "Sen uzman bir astrologsun. Kişiye özel, derinlikli Türkçe yorumlar üretiyorsun."
    sun_sign  = chart["sun_sign"]
    moon_sign = chart["moon_sign"]
    rising    = chart["rising"]
    elements  = chart["elements"]
    retros    = chart["retrogrades"]

    def rec(user, assistant):
        return {"messages": [
            {"role": "system",    "content": system},
            {"role": "user",      "content": user},
            {"role": "assistant", "content": assistant},
        ]}

    # Gezegen listesini string'e çevir
    planet_str = " | ".join(
        f"{p['name']}:{p['sign']}{' ℞' if p['retrograde'] else ''}"
        for p in chart["planets"]
    )
    major_aspects = [a for a in chart["aspects"] if a["is_major"]]
    aspect_str = ", ".join(
        f"{a['planet1_tr']} {a['type']} {a['planet2_tr']}"
        for a in major_aspects[:5]
    )

    records = [
        # 1. Genel karakter profili
        rec(
            f"{sun_sign} Güneş, {moon_sign} Ay, {rising} Yükselen. "
            f"Elementler: Ateş:{elements['Ateş']} Toprak:{elements['Toprak']} "
            f"Hava:{elements['Hava']} Su:{elements['Su']}. "
            f"Bu kişinin genel karakter profilini yorumla.",
            interp.get("summary", ""),
        ),
        # 2. Güneş burcu
        rec(
            f"{sun_sign} burcundaki Güneş'in kişilik üzerindeki etkisini yorumla. "
            f"Gezegenler: {planet_str}",
            interp.get("sun", {}).get("description", ""),
        ),
        # 3. Ay burcu
        rec(
            f"{moon_sign} burcundaki Ay'ın duygusal dünya ve içgüdüler üzerindeki "
            f"etkisini yorumla.",
            interp.get("moon", {}).get("description", ""),
        ),
        # 4. Aspektler
        rec(
            f"Bu doğum haritasındaki major aspektleri yorumla: {aspect_str}. "
            f"Güneş Burcu: {sun_sign}, Ay Burcu: {moon_sign}.",
            " ".join(
                a.get("meaning", "") for a in interp.get("aspects", [])
                if a.get("meaning")
            ) or interp.get("summary", ""),
        ),
        # 5. Element analizi
        rec(
            f"Element dağılımı — Ateş:{elements['Ateş']} Toprak:{elements['Toprak']} "
            f"Hava:{elements['Hava']} Su:{elements['Su']}. "
            f"Bu dağılımın kişilik üzerindeki etkisini açıkla.",
            f"{interp.get('elements', {}).get('comment', '')} {interp.get('summary', '')}".strip(),
        ),
    ]

    # Boş assistant içeriklerini filtrele
    return [r for r in records if r["messages"][2]["content"].strip()]


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Ana Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

async def run_pipeline(count: int, output_path: str):
    profiles = BIRTH_PROFILES[:count]
    all_records = []
    failed = []

    print(f"\n{'='*60}")
    print(f"  SoulBound Astroloji Dataset Pipeline")
    print(f"  {count} profil işlenecek → {output_path}")
    print(f"{'='*60}\n")

    # Günlük limit: 50 istek / gün, her profil 3 istek = max 16 profil/gün
    # Güvenli limit: 15 profil = 45 istek
    if count > 15:
        print(f"⚠️  FreeAstrologyAPI günlük limit: 50 istek.")
        print(f"   Her profil 3 istek = {count*3} istek gerekir.")
        print(f"   Bugün için max 15 profil (45 istek) önerilir.\n")

    async with httpx.AsyncClient(
        base_url=FREE_ASTRO_BASE,
        headers={"Content-Type": "application/json", "x-api-key": FREE_ASTRO_KEY},
        timeout=httpx.Timeout(30.0),
    ) as http_client:

        for i, (code, yr, mo, dy, hr, mn, lat, lon, tz) in enumerate(profiles, 1):
            print(f"[{i:02d}/{count}] {code} — {yr}-{mo:02d}-{dy:02d} "
                  f"{hr:02d}:{mn:02d} ({lat:.1f}, {lon:.1f})")

            # ── Step 1: FreeAstrologyAPI ──────────────────────────────────
            try:
                t0 = time.perf_counter()
                chart = await fetch_western_chart(
                    http_client, yr, mo, dy, hr, mn, lat, lon, tz
                )
                t1 = time.perf_counter()
                print(f"   ✓ FreeAstrology: Güneş={chart['sun_sign']} "
                      f"Ay={chart['moon_sign']} Yükselen={chart['rising']} "
                      f"({(t1-t0)*1000:.0f}ms)")
            except Exception as e:
                print(f"   ✗ FreeAstrology hatası: {e}")
                failed.append((code, str(e)))
                continue

            # ── Step 2: Claude Yorum ──────────────────────────────────────
            if not ANTHROPIC_KEY:
                print("   ⚠ ANTHROPIC_API_KEY yok — yorum atlandı")
                # Key yoksa placeholder ile devam et
                interp = {
                    "summary": f"{chart['sun_sign']} Güneş, {chart['moon_sign']} Ay kombinasyonu.",
                    "sun": {"description": f"{chart['sun_sign']} burcunda Güneş."},
                    "moon": {"description": f"{chart['moon_sign']} burcunda Ay."},
                    "aspects": [],
                    "elements": {"comment": ""},
                }
            else:
                try:
                    birth_meta = {"year":yr,"month":mo,"day":dy,
                                  "hour":hr,"minute":mn,"lat":lat,"lon":lon}
                    prompt = _build_prompt(chart, birth_meta)
                    t0 = time.perf_counter()
                    interp = await get_claude_interpretation(prompt)
                    t1 = time.perf_counter()
                    print(f"   ✓ Claude yorum: {len(interp.get('summary',''))} karakter "
                          f"({(t1-t0)*1000:.0f}ms)")
                except Exception as e:
                    print(f"   ✗ Claude hatası: {e}")
                    failed.append((code, f"Claude: {e}"))
                    continue

            # ── Step 3: Dataset kayıtları üret ───────────────────────────
            birth_meta = {"year":yr,"month":mo,"day":dy,
                          "hour":hr,"minute":mn,"lat":lat,"lon":lon}
            records = build_records(chart, interp, birth_meta)
            all_records.extend(records)
            print(f"   ✓ {len(records)} JSONL kaydı eklendi "
                  f"(toplam: {len(all_records)})")

            # Rate limit: istekler arası 1.5sn bekle
            if i < count:
                await asyncio.sleep(1.5)

    # ── Kaydet ────────────────────────────────────────────────────────────────
    out = Path(output_path)
    with open(out, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n{'='*60}")
    print(f"  ✅ TAMAMLANDI")
    print(f"  Toplam kayıt : {len(all_records)}")
    print(f"  Profil sayısı: {count - len(failed)}/{count}")
    print(f"  Çıktı dosyası: {out}")
    if failed:
        print(f"\n  ❌ Başarısız ({len(failed)}):")
        for code, err in failed:
            print(f"     {code}: {err}")
    print(f"\n  Sonraki adım (Llama fine-tune):")
    print(f"  → pip install unsloth")
    print(f"  → python finetune_llama.py --data {out}")
    print(f"{'='*60}\n")

    return all_records


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Astroloji Dataset Pipeline")
    parser.add_argument("--count", type=int, default=5,
                        help="İşlenecek profil sayısı (max 15 önerilir, günlük limit)")
    parser.add_argument("--out",   default="dataset.jsonl",
                        help="Çıktı JSONL dosyası")
    parser.add_argument("--dry-run", action="store_true",
                        help="API çağrısı yapmadan yapıyı test et")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — ilk 2 profilin prompt'unu göster:")
        for code, yr, mo, dy, hr, mn, lat, lon, tz in BIRTH_PROFILES[:2]:
            mock_chart = {
                "sun_sign": "Yay", "moon_sign": "Oğlak", "rising": "Yay",
                "planets": [], "aspects": [], "elements": {"Ateş":5,"Toprak":3,"Hava":1,"Su":1},
                "retrogrades": ["Mercury"],
            }
            bm = {"year":yr,"month":mo,"day":dy,"hour":hr,"minute":mn,"lat":lat,"lon":lon}
            print(f"\n--- {code} ---")
            print(_build_prompt(mock_chart, bm))
    else:
        asyncio.run(run_pipeline(args.count, args.out))