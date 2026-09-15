"""
dataset_builder.py — Ephemeris çıktısını fine-tune dataset'ine dönüştürür.

module1_engine çıktı formatı:
  planets: {"Sun": {"sign": "Yay", "longitude": 240.75, "house": 11, ...}, ...}
  aspects: [{"planet1": "Sun", "aspect": "Kavuşum", "planet2": "Venus", "orb": 6.01}, ...]
  summary: {"sun_sign": "Yay", "moon_sign": "Oğlak", "rising": "Yay", "elements": {...}}

Çalıştır:
    python dataset_builder.py --mode validate --file test_output.json
    python dataset_builder.py --mode finetune --file test_output.json --output dataset.jsonl
    python dataset_builder.py --mode enrich   --file test_output.json --api api_result.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════════
# FORMAT NORMALIZE
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_planets(raw) -> list[dict]:
    """
    module1_engine formatı (dict of dicts) → list of dicts

    Girdi:
        {
          "Sun":  {"sign": "Yay", "degree_in_sign": 0.75, "house": 11, "retrograde": False, ...},
          "Moon": {"sign": "Oğlak", "degree_in_sign": 16.30, "house": 1, ...},
          ...
        }

    Çıktı:
        [
          {"name": "Sun",  "sign": "Yay",   "degree": 0.75,  "house": 11, "retrograde": False},
          {"name": "Moon", "sign": "Oğlak", "degree": 16.30, "house": 1,  "retrograde": False},
          ...
        ]
    """
    if not raw:
        return []

    # Format A: zaten list of dicts
    if isinstance(raw, list):
        result = []
        for p in raw:
            if isinstance(p, dict):
                result.append({
                    "name":       p.get("name", "?"),
                    "sign":       p.get("sign", "?"),
                    "degree":     float(p.get("degree_in_sign", p.get("degree", 0))),
                    "longitude":  float(p.get("longitude", 0)),
                    "house":      int(p.get("house", 0)),
                    "retrograde": bool(p.get("retrograde", False)),
                    "speed":      float(p.get("speed", 0)),
                })
        return result

    # Format B: dict of dicts (module1_engine)
    if isinstance(raw, dict):
        result = []
        for name, data in raw.items():
            if not isinstance(data, dict):
                continue
            result.append({
                "name":       name,
                "sign":       data.get("sign", "?"),
                "degree":     float(data.get("degree_in_sign", data.get("degree", 0))),
                "longitude":  float(data.get("longitude", 0)),
                "house":      int(data.get("house", 0)),
                "retrograde": bool(data.get("retrograde", False)),
                "speed":      float(data.get("speed", 0)),
                "dms":        data.get("dms", {}),
            })
        return result

    return []


def normalize_aspects(raw) -> list[dict]:
    """
    aspects alanını normalize et — 'aspect' veya 'type' key'ini destekle.
    """
    if not raw:
        return []

    if isinstance(raw, dict):
        result = []
        for key, data in raw.items():
            if isinstance(data, dict):
                entry = dict(data)
                if "_" in key and "planet1" not in entry:
                    parts = key.split("_")
                    entry["planet1"] = parts[0]
                    entry["planet2"] = parts[1] if len(parts) > 1 else ""
                result.append(entry)
        return result

    if isinstance(raw, list):
        result = []
        for a in raw:
            if not isinstance(a, dict):
                continue
            entry = dict(a)
            # "type" ve "aspect" her ikisini de destekle
            if "aspect" not in entry and "type" in entry:
                entry["aspect"] = entry["type"]
            if "type" not in entry and "aspect" in entry:
                entry["type"] = entry["aspect"]
            result.append(entry)
        return result

    return []


def normalize_summary(ephemeris: dict, planets: list[dict]) -> dict:
    """
    summary/meta alanını normalize et.
    Yoksa gezegen listesinden türet.
    """
    summary = ephemeris.get("summary", {})

    if not summary.get("sun_sign"):
        summary = ephemeris.get("meta", {})

    if not summary.get("sun_sign") and planets:
        sun  = next((p for p in planets if p["name"] == "Sun"),  {})
        moon = next((p for p in planets if p["name"] == "Moon"), {})
        asc  = ephemeris.get("angles", {}).get("asc_sign", "?")
        summary = {
            "sun_sign":  summary.get("sun_sign")  or sun.get("sign",  "?"),
            "moon_sign": summary.get("moon_sign") or moon.get("sign", "?"),
            "rising":    summary.get("rising")    or asc,
            "elements":  summary.get("elements",  {}),
        }

    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# A) VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_ephemeris_vs_api(ephemeris_path: str, api_result_path: str | None = None):
    with open(ephemeris_path, encoding="utf-8") as f:
        ephemeris = json.load(f)

    planets = normalize_planets(ephemeris.get("planets", {}))
    aspects = normalize_aspects(ephemeris.get("aspects", []))
    summary = normalize_summary(ephemeris, planets)

    retrogrades = [p["name"] for p in planets if p.get("retrograde")]

    print("─── EPHEMERİS DOĞRULAMA ────────────────────────────────────")
    print(f"Güneş Burcu   : {summary.get('sun_sign', '?')}")
    print(f"Ay Burcu      : {summary.get('moon_sign', '?')}")
    print(f"Yükselen      : {summary.get('rising', '?')}")
    print(f"Elementler    : {summary.get('elements', {})}")
    print(f"Retrograde    : {retrogrades if retrogrades else 'Yok'}")
    print()

    print("GEZEGEN POZİSYONLARI (Kesin Değerler):")
    for p in planets:
        retro = " ℞" if p.get("retrograde") else ""
        print(f"  {p['name']:<10} {p['sign']:<10} {p['degree']:>6.2f}°  Ev:{p['house']}{retro}")

    major = [a for a in aspects if a.get("is_major", True)]
    print(f"\nASPEKTLER: {len(aspects)} toplam, {len(major)} major")
    for a in major:
        p1  = a.get("planet1", "?")
        asp = a.get("aspect", a.get("type", "?"))
        p2  = a.get("planet2", "?")
        orb = float(a.get("orb", 0))
        print(f"  {p1:<10} {asp:<12} {p2:<10} orb:{orb:.2f}°")

    if api_result_path and Path(api_result_path).exists():
        with open(api_result_path, encoding="utf-8") as f:
            api = json.load(f)
        _cross_check(summary, api.get("meta", {}))

    return ephemeris


def _cross_check(eph_meta: dict, api_meta: dict):
    print("\n─── CROSS-CHECK: Ephemeris vs API ──────────────────────────")
    fields = [("sun_sign", "Güneş"), ("moon_sign", "Ay"), ("rising", "Yükselen")]
    all_ok = True
    for key, label in fields:
        e = str(eph_meta.get(key, "")).strip()
        a = str(api_meta.get(key, "")).strip()
        ok = (e == a) or not a
        status = "✅" if ok else "❌ UYUŞMAZLIK"
        print(f"  {label:<10}: Ephemeris={e!r:<14} API={a!r:<14} {status}")
        if not ok:
            all_ok = False
    print("Sonuç:", "✅ Tüm değerler uyuşuyor" if all_ok else "❌ Timezone veya koordinat hatası")


# ═══════════════════════════════════════════════════════════════════════════════
# B) FINE-TUNE DATASET
# ═══════════════════════════════════════════════════════════════════════════════

_ASTRO_SYSTEM_PROMPT = (
    "Sen uzman bir astrologsun. Verilen doğum haritası bilgilerini kullanarak "
    "kişiye özel, derinlikli ve psikolojik açıdan anlamlı Türkçe yorumlar üretiyorsun. "
    "Yorumların özgün, klişeden uzak ve gerçekçi olmalı."
)
_PLACEHOLDER = "[Bu alana gerçek bir astrolog yorumu eklenecek]"


def _make_record(system, user, assistant):
    return {"messages": [
        {"role": "system",    "content": system},
        {"role": "user",      "content": user},
        {"role": "assistant", "content": assistant},
    ]}


def build_finetune_dataset(
    ephemeris_path: str,
    output_path: str = "dataset.jsonl",
    interpretation: dict | None = None,
):
    with open(ephemeris_path, encoding="utf-8") as f:
        ephemeris = json.load(f)

    planets = normalize_planets(ephemeris.get("planets", {}))
    aspects = normalize_aspects(ephemeris.get("aspects", []))
    summary = normalize_summary(ephemeris, planets)

    interp       = interpretation or {}
    interp_inner = interp.get("interpretation", {})

    records = [
        _make_record(
            _ASTRO_SYSTEM_PROMPT,
            _q_character(summary, planets, aspects),
            interp.get("summary", _PLACEHOLDER),
        ),
        _make_record(
            _ASTRO_SYSTEM_PROMPT,
            _q_planet(planets, "Sun"),
            interp_inner.get("sun", {}).get("description", _PLACEHOLDER),
        ),
        _make_record(
            _ASTRO_SYSTEM_PROMPT,
            _q_planet(planets, "Moon"),
            interp_inner.get("moon", {}).get("description", _PLACEHOLDER),
        ),
        _make_record(
            _ASTRO_SYSTEM_PROMPT,
            _q_aspects(aspects),
            _a_aspects(aspects, interp_inner),
        ),
        _make_record(
            _ASTRO_SYSTEM_PROMPT,
            _q_elements(summary),
            _a_elements(summary, interp_inner),
        ),
    ]

    out = Path(output_path)
    with open(out, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"─── FINE-TUNE DATASET ──────────────────────────────────────")
    print(f"✅ {len(records)} kayıt üretildi → {out}")
    print(f"Format: OpenAI / Anthropic / HuggingFace chat fine-tune")
    print("\nSonraki adımlar:")
    print("  1. Daha fazla doğum haritası topla (50+ kayıt hedefle)")
    print("  2. 'assistant' alanlarını gerçek yorumlarla doldur")
    print("  3. openai fine_tuning.jobs.create() veya Unsloth ile eğit")
    return records


# ── Soru üreticiler ───────────────────────────────────────────────────────────

def _q_character(summary, planets, aspects) -> str:
    retros = [p["name"] for p in planets if p.get("retrograde")]
    lines = [
        "Aşağıdaki doğum haritasına sahip kişinin genel karakter profilini yorumla:",
        "",
        f"Güneş Burcu : {summary.get('sun_sign', '?')}",
        f"Ay Burcu    : {summary.get('moon_sign', '?')}",
        f"Yükselen    : {summary.get('rising', '?')}",
        f"Elementler  : {summary.get('elements', {})}",
        f"Retrograde  : {retros if retros else 'Yok'}",
        "",
        "Gezegenler:",
    ]
    for p in planets:
        r = " ℞" if p.get("retrograde") else ""
        lines.append(f"  {p['name']}: {p['sign']} {p['degree']:.1f}° | {p['house']}. ev{r}")
    return "\n".join(lines)


def _q_planet(planets, planet_name) -> str:
    label = {
        "Sun": "Güneş", "Moon": "Ay", "Mercury": "Merkür",
        "Venus": "Venüs", "Mars": "Mars", "Jupiter": "Jüpiter",
        "Saturn": "Satürn", "Uranus": "Uranüs", "Neptune": "Neptün",
        "Pluto": "Plüton",
    }.get(planet_name, planet_name)
    p = next((x for x in planets if x["name"] == planet_name), {})
    if not p:
        return f"{label} burcu yorumu yap."
    retro = " (retrograde)" if p.get("retrograde") else ""
    return (
        f"{p['sign']} burcundaki {label}{retro}, "
        f"{p['house']}. evde {p['degree']:.2f}° derecede "
        f"(longitude: {p.get('longitude', 0):.2f}°). "
        f"Bu yerleşimin kişi üzerindeki etkisini yorumla."
    )


def _q_aspects(aspects) -> str:
    major = [a for a in aspects if a.get("is_major", True)][:6]
    lines = ["Bu doğum haritasındaki önemli aspektleri yorumla:", ""]
    for a in major:
        asp = a.get("aspect", a.get("type", "?"))
        lines.append(
            f"  {a.get('planet1','?')} {asp} {a.get('planet2','?')} "
            f"(orb: {float(a.get('orb', 0)):.2f}°)"
        )
    return "\n".join(lines)


def _a_aspects(aspects, interp_inner) -> str:
    saved = interp_inner.get("aspects", [])
    if saved:
        return "\n".join(
            f"{a.get('planets', '')}: {a.get('meaning', '')}"
            for a in saved if a.get("meaning")
        )
    return _PLACEHOLDER


def _q_elements(summary) -> str:
    elements = summary.get("elements", {})
    return (
        f"Bu doğum haritasındaki element dağılımını yorumla: {elements}\n"
        f"Hangi element baskın, bu kişinin yaşam yaklaşımını nasıl etkiler?"
    )


def _a_elements(summary, interp_inner) -> str:
    elements = summary.get("elements", {})
    if not elements:
        return _PLACEHOLDER
    dominant = max(elements, key=lambda k: elements[k])
    desc_map = {
        "Ateş":   "girişken, tutkulu ve liderlik odaklı",
        "Toprak": "pratik, sabırlı ve maddi güvenliğe önem veren",
        "Hava":   "analitik, sosyal ve iletişim odaklı",
        "Su":     "sezgisel, empatik ve duygusal derinliğe sahip",
    }
    desc = desc_map.get(dominant, "güçlü bir karaktere sahip")
    others = ", ".join(f"{k}:{v}" for k, v in elements.items() if k != dominant)
    return (
        f"Bu haritada {dominant} elementi {elements[dominant]} gezegenle baskındır. "
        f"Kişi doğası gereği {desc} bir yapıya sahiptir. "
        f"Diğer elementlerin dağılımı — {others} — bu temel karakteri dengeler veya tamamlar."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# C) ENRICH
# ═══════════════════════════════════════════════════════════════════════════════

def enrich_with_interpretation(
    ephemeris_path: str,
    interpretation: dict,
    output_path: str = "enriched_chart.json",
):
    with open(ephemeris_path, encoding="utf-8") as f:
        ephemeris = json.load(f)

    planets = normalize_planets(ephemeris.get("planets", {}))
    summary = normalize_summary(ephemeris, planets)

    enriched = {
        "ephemeris":      ephemeris,
        "interpretation": interpretation,
        "meta": {
            "ephemeris_source":      "swiss_ephemeris / module1_engine",
            "interpretation_source": interpretation.get("raw_api", {}).get("provider", "unknown"),
            "birth_date": ephemeris.get("meta", {}).get("birth_date", ""),
            "sun_sign":   summary.get("sun_sign", ""),
            "moon_sign":  summary.get("moon_sign", ""),
            "rising":     summary.get("rising", ""),
        }
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    print(f"✅ Zenginleştirilmiş chart kaydedildi: {output_path}")
    return enriched


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ephemeris Dataset Builder")
    parser.add_argument("--mode",   choices=["validate", "finetune", "enrich"], default="validate")
    parser.add_argument("--file",   default="test_output.json", help="Ephemeris JSON dosyası")
    parser.add_argument("--api",    default=None,               help="API sonuç JSON (cross-check için)")
    parser.add_argument("--output", default="dataset.jsonl",    help="Çıktı dosyası")
    args = parser.parse_args()

    if args.mode == "validate":
        validate_ephemeris_vs_api(args.file, args.api)

    elif args.mode == "finetune":
        interpretation = None
        if args.api and Path(args.api).exists():
            with open(args.api, encoding="utf-8") as f:
                interpretation = json.load(f)
        build_finetune_dataset(args.file, args.output, interpretation)

    elif args.mode == "enrich":
        if not args.api or not Path(args.api).exists():
            print("HATA: --api parametresi gerekli (API sonuç JSON dosyası)")
            sys.exit(1)
        with open(args.api, encoding="utf-8") as f:
            interpretation = json.load(f)
        enrich_with_interpretation(
            args.file, interpretation,
            args.output.replace(".jsonl", ".json")
        )