#!/usr/bin/env python3
"""
SoulBound - import_snippets.py (Faz 2)

JSON Lines -> snippet_templates + snippet_translations (hepsi 'draft').

Kullanım (PowerShell, backend klasöründe):
  python import_snippets.py batch1.jsonl            # yalnızca DOĞRULAMA (ağ yok, DB'ye dokunmaz)
  python import_snippets.py batch1.jsonl --apply    # DB'ye yazar (SERVICE_ROLE_KEY gerekir)

Gerekli ortam değişkenleri / .env: SUPABASE_URL, SERVICE_ROLE_KEY
Bağımlılık yok (yalnızca standart kütüphane).
"""
import argparse, hashlib, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone

TRANSITS = ["Sun", "Moon", "Mercury", "Venus", "Mars"]
ASPECTS = ["conjunction", "sextile", "square", "trine", "opposition"]
NATALS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
VALENCES = ["power", "pressure", "trouble", "neutral"]
LOCALES = ["en", "tr", "de", "fr", "es", "pt", "it"]
MAX_BODY, MAX_NOTIF = 220, 80

# GEÇİCİ ÖNERİ - onayla ya da değiştir. content_themes.code değerleriyle eşleşmeli.
THEME_BY_NATAL = {
    "Sun": "identity", "Moon": "identity", "Mercury": "career", "Venus": "love",
     "Mars": "health", "Jupiter": "career", "Saturn": "career", "Uranus": "identity",
    "Neptune": "love", "Pluto": "identity",
}

EN_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
            "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
TR_PLANETS = {"Mercury": "Merkür", "Venus": "Venüs", "Mars": "Mars", "Jupiter": "Jüpiter",
              "Saturn": "Satürn", "Uranus": "Uranüs", "Neptune": "Neptün", "Pluto": "Plüton"}

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
FORBIDDEN_RE = re.compile(r"\b(you will|will die|pregnan\w*|lawsuit|diagnos\w*)\b|hamile|ölüm|dava açıl|kanser|teşhis", re.I)
HEDGE_RE = re.compile(r"\b(maybe|perhaps)\b|\bbelki\b", re.I)
BASE_INTENSITY = {"Moon": (1, 2), "Sun": (2, 3), "Mercury": (2, 3), "Venus": (2, 3), "Mars": (3, 4)}
BOOST_NATALS = {"Sun", "Moon", "Saturn", "Pluto"}


def expected_valence(t, a, n, intensity):
    if a in ("trine", "sextile"):
        return "power"
    if a in ("square", "opposition"):
        if t == "Mars" and n in BOOST_NATALS and intensity == 5:
            return "trouble"
        return "pressure"
    return {"Venus": "power", "Mars": "pressure"}.get(t, "neutral")


def validate(rows):
    errors, warnings = [], []
    seen = set()
    starts = {}
    for i, r in enumerate(rows, 1):
        tag = f"satır {i}"
        try:
            t, a, n, v = r["transit_body"], r["aspect"], r["natal_point"], int(r["variant_no"])
        except Exception as e:
            errors.append(f"{tag}: anahtar alanları eksik ({e})")
            continue
        tag = f"satır {i} ({t} {a} {n} v{v})"
        if t not in TRANSITS: errors.append(f"{tag}: transit_body geçersiz")
        if a not in ASPECTS: errors.append(f"{tag}: aspect geçersiz")
        if n not in NATALS: errors.append(f"{tag}: natal_point geçersiz")
        if (t, a, n, v) in seen: errors.append(f"{tag}: dosyada tekrar eden anahtar")
        seen.add((t, a, n, v))
        val, inten = r.get("valence"), r.get("intensity")
        if val not in VALENCES: errors.append(f"{tag}: valence geçersiz")
        if not isinstance(inten, int) or not 1 <= inten <= 5:
            errors.append(f"{tag}: intensity 1-5 tamsayı olmalı")
        else:
            if val in VALENCES and t in TRANSITS and a in ASPECTS and n in NATALS:
                exp = expected_valence(t, a, n, inten)
                if exp != val: warnings.append(f"{tag}: valence kurala göre '{exp}' olmalı, gelen '{val}'")
            lo, hi = BASE_INTENSITY.get(t, (1, 5))
            if n in BOOST_NATALS: lo, hi = lo + 1, hi + 1
            if val != "trouble": hi = min(hi, 4)
            if not lo <= inten <= hi: warnings.append(f"{tag}: intensity {inten}, beklenen aralık {lo}-{hi}")
            if inten == 5 and val != "trouble":
                errors.append(f"{tag}: intensity 5 yalnızca valence=trouble için (K1)")
            if val == "trouble" and not (t == "Mars" and a in ("square", "opposition") and n in BOOST_NATALS and inten == 5):
                errors.append(f"{tag}: trouble yalnızca Mars square/opposition x natal Sun/Moon/Saturn/Pluto ve intensity 5 için (K1)")
        kw = r.get("keywords")
        if not isinstance(kw, list) or not 3 <= len(kw) <= 6 or not all(isinstance(k, str) and k.strip() for k in kw):
            errors.append(f"{tag}: keywords 3-6 dolu metin olmalı")
        if not isinstance(r.get("gist"), str) or not r["gist"].strip():
            errors.append(f"{tag}: gist boş")
        locs = [l for l in LOCALES if l in r]
        if not locs: errors.append(f"{tag}: hiç dil bloğu yok")
        for l in locs:
            blk = r[l]
            body, notif = (blk or {}).get("body", ""), (blk or {}).get("notification", "")
            if not body.strip(): errors.append(f"{tag}/{l}: body boş"); continue
            if not notif.strip(): errors.append(f"{tag}/{l}: notification boş")
            if len(body) > MAX_BODY: errors.append(f"{tag}/{l}: body {len(body)} > {MAX_BODY}")
            if len(notif) > MAX_NOTIF: errors.append(f"{tag}/{l}: notification {len(notif)} > {MAX_NOTIF}")
            for field, txt in (("body", body), ("notification", notif)):
                if "!" in txt or EMOJI_RE.search(txt): errors.append(f"{tag}/{l}/{field}: ünlem veya emoji")
                if FORBIDDEN_RE.search(txt): errors.append(f"{tag}/{l}/{field}: yasaklı kalıp")
                if HEDGE_RE.search(txt): warnings.append(f"{tag}/{l}/{field}: kaçamak sözcük")
                allowed = {t, n}
                for p in set(NATALS) - allowed:
                    if re.search(rf"\b{p}\b", txt, re.I) and p not in ("Sun", "Moon"):
                        errors.append(f"{tag}/{l}/{field}: başka gezegen anılıyor ({p})")
                    elif re.search(rf"\b{p}\b", txt, re.I):
                        warnings.append(f"{tag}/{l}/{field}: '{p}' sözcüğü geçiyor")
                for s in EN_SIGNS:
                    if re.search(rf"\b{s}\b", txt, re.I): errors.append(f"{tag}/{l}/{field}: burç anılıyor ({s})")
                for p, trn in TR_PLANETS.items():
                    if p not in allowed and re.search(trn, txt, re.I):
                        errors.append(f"{tag}/{l}/{field}: başka gezegen anılıyor ({trn})")
            if notif and body.lower().startswith(notif.lower().rstrip(". ")):
                warnings.append(f"{tag}/{l}: notification body'nin ilk cümlesini tekrarlıyor")
            starts.setdefault(l, Counter())[" ".join(body.lower().split()[:2])] += 1
    for l, c in starts.items():
        for k, cnt in c.items():
            if cnt >= 3: warnings.append(f"[{l}] {cnt} metin aynı açılışla başlıyor: '{k} ...'")
    return errors, warnings


# ---------------- Supabase (PostgREST, yalnızca urllib) ----------------
def load_env():
    if os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class Api:
    def __init__(self, url, key):
        self.base, self.key = url.rstrip("/") + "/rest/v1/", key

    def call(self, method, path, body=None, prefer=None):
        h = {"apikey": self.key, "Content-Type": "application/json"}
        if not self.key.startswith("sb_secret_"):
            h["Authorization"] = f"Bearer {self.key}"
        if prefer: h["Prefer"] = prefer
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            sys.exit(f"HTTP {e.code} {method} {path}\n{e.read().decode('utf-8', 'replace')}")

    def get_all(self, path):
        out, off = [], 0
        while True:
            sep = "&" if "?" in path else "?"
            page = self.call("GET", f"{path}{sep}limit=1000&offset={off}")
            out += page
            if len(page) < 1000: return out
            off += 1000


def meaning_of(r):
    card = {"keywords": [k.strip() for k in r["keywords"]], "gist": r["gist"].strip()}
    raw = json.dumps(card, sort_keys=True, ensure_ascii=False) + f"|{r['valence']}|{r['intensity']}"
    return card, hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def apply(rows, prompt_version, model):
    load_env()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key: sys.exit("SUPABASE_URL ve SERVICE_ROLE_KEY (veya SUPABASE_SERVICE_ROLE_KEY) gerekli (.env veya ortam).")
    api = Api(url, key)
    bodies = {x["code"].lower(): x["id"] for x in api.get_all("celestial_bodies?select=id,code")}
    aspects = {x["code"].lower(): x["id"] for x in api.get_all("aspect_types?select=id,code")}
    themes = {x["code"].lower(): x["id"] for x in api.get_all("content_themes?select=id,code")}
    locales = {x["code"] for x in api.get_all("locales?select=code")}
    for n, d, names in (("celestial_bodies", bodies, TRANSITS + NATALS), ("aspect_types", aspects, ASPECTS)):
        miss = [c for c in set(names) if c.lower() not in d]
        if miss: sys.exit(f"{n} içinde kod bulunamadı: {miss}")
    for code in set(THEME_BY_NATAL.values()):
        if code not in themes: print(f"UYARI: content_themes içinde '{code}' yok -> theme_id NULL yazılacak")

    existing = {}
    for x in api.get_all("snippet_templates?select=id,transit_body_id,aspect_type_id,natal_body_id,variant_no,meaning_hash&kind=eq.transit_daily&house_id=is.null"):
        existing[(x["transit_body_id"], x["aspect_type_id"], x["natal_body_id"], x["variant_no"])] = x

    new_payload, new_rows, patch, tmpl_of = [], [], [], {}
    for r in rows:
        k = (bodies[r["transit_body"].lower()], aspects[r["aspect"].lower()], bodies[r["natal_point"].lower()], int(r["variant_no"]))
        card, h = meaning_of(r)
        common = {"valence": r["valence"], "intensity": r["intensity"], "meaning_card": card, "meaning_hash": h}
        if k in existing:
            tmpl_of[id(r)] = (existing[k]["id"], h)
            if existing[k]["meaning_hash"] != h:
                patch.append((existing[k]["id"], {**common, "status": "draft"}))
        else:
            new_payload.append({"kind": "transit_daily", "transit_body_id": k[0], "aspect_type_id": k[1],
                                "natal_body_id": k[2], "house_id": None,
                                "theme_id": themes.get(THEME_BY_NATAL[r["natal_point"]].lower()),
                                "variant_no": k[3], "status": "draft", **common})
            new_rows.append((r, k, h))

    for i in range(0, len(new_payload), 100):
        res = api.call("POST", "snippet_templates", new_payload[i:i + 100], prefer="return=representation")
        for x in res:
            kk = (x["transit_body_id"], x["aspect_type_id"], x["natal_body_id"], x["variant_no"])
            for r, k, h in new_rows:
                if k == kk: tmpl_of[id(r)] = (x["id"], h)
    for tid, body in patch:
        api.call("PATCH", f"snippet_templates?id=eq.{tid}", body, prefer="return=minimal")
    print(f"şablon: {len(new_payload)} yeni, {len(patch)} güncellendi (hash değişti -> draft), "
          f"{len(rows) - len(new_payload) - len(patch)} aynı")

    ids = sorted({v[0] for v in tmpl_of.values()})
    old_tr = {}
    for i in range(0, len(ids), 100):
        chunk = ",".join(map(str, ids[i:i + 100]))
        for x in api.get_all(f"snippet_translations?select=template_id,locale,body,status&template_id=in.({chunk})"):
            old_tr[(x["template_id"], x["locale"])] = x
    out, skipped = [], 0
    now = datetime.now(timezone.utc).isoformat()
    for r in rows:
        tid, h = tmpl_of[id(r)]
        for l in LOCALES:
            if l not in r: continue
            if l not in locales: print(f"UYARI: locales içinde '{l}' yok, atlandı"); continue
            o = old_tr.get((tid, l))
            if o and o["status"] == "approved":
                if o["body"] != r[l]["body"]:
                    print(f"UYARI: onaylı çeviri korunuyor, atlandı (template {tid}/{l})")
                skipped += 1; continue
            out.append({"template_id": tid, "locale": l, "body": r[l]["body"].strip(),
                        "notification": r[l]["notification"].strip(), "source_hash": h, "model": model,
                        "prompt_version": prompt_version, "status": "draft", "updated_at": now})
    for i in range(0, len(out), 200):
        api.call("POST", "snippet_translations?on_conflict=template_id,locale", out[i:i + 200],
                 prefer="resolution=merge-duplicates,return=minimal")
    print(f"çeviri: {len(out)} yazıldı, {skipped} atlandı")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--apply", action="store_true", help="DB'ye yaz (varsayılan: yalnızca doğrula)")
    ap.add_argument("--prompt-version", default="f2-v1")
    ap.add_argument("--model", default="claude")
    a = ap.parse_args()
    rows = []
    with open(a.file, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try: rows.append(json.loads(line))
                except json.JSONDecodeError as e: sys.exit(f"satır {n}: geçersiz JSON ({e})")
    errors, warnings = validate(rows)
    print(f"{len(rows)} satır okundu.")
    for w in warnings: print("UYARI:", w)
    for e in errors: print("HATA :", e)
    print(f"-> {len(errors)} hata, {len(warnings)} uyarı")
    if errors: sys.exit(1)
    if a.apply: apply(rows, a.prompt_version, a.model)
    else: print("Yalnızca doğrulama yapıldı. DB'ye yazmak için --apply ekle.")


if __name__ == "__main__":
    main()