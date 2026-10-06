#!/usr/bin/env python3
"""
SoulBound - import_synastry.py
data\synastry\*.jsonl -> snippet_templates(kind='synastry') + snippet_translations (draft)

  python import_synastry.py data\synastry            # yalnızca DOĞRULAMA
  python import_synastry.py data\synastry --apply    # DB'ye yazar (SERVICE_ROLE_KEY)
Dosya veya klasör verilebilir. import_snippets.py'ye dokunmaz.
"""
import argparse, glob, hashlib, json, os, re, sys
from collections import Counter
from datetime import datetime, timezone

from import_snippets import Api, load_env, LOCALES, MAX_BODY, EMOJI_RE, FORBIDDEN_RE, HEDGE_RE

BODIES = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
ASPECTS = ["conjunction", "sextile", "square", "trine", "opposition"]
VALENCES = ["power", "pressure", "neutral"]
EXPECTED = 275
GLUE_EN = re.compile(
    r"\b(?:You|Your|They|We|The|It|And|But|Both|Each)(?:both|which|that|when|with|and|each|can|may|are|have|will|want|feel|but)\b"
    r"|\b(?:weigh|sit|keep|hold|need|take|both|each|which|that|with)(?:which|that|when|with|both|each)\b")


def pair_key(r):
    a, b = BODIES.index(r["body_a"]), BODIES.index(r["body_b"])
    return (min(a, b), max(a, b), r["aspect"])


def validate(rows):
    errors, warnings, seen = [], [], {}
    for i, r in enumerate(rows, 1):
        tag = f"satır {i}"
        try:
            if r["kind"] != "synastry": errors.append(f"{tag}: kind synastry değil")
            if r["body_a"] not in BODIES or r["body_b"] not in BODIES or r["aspect"] not in ASPECTS:
                errors.append(f"{tag}: body_a/body_b/aspect geçersiz"); continue
            k = pair_key(r)
            vn = int(r["variant_no"])
        except Exception as e:
            errors.append(f"{tag}: alanlar eksik ({e})"); continue
        tag = f"satır {i} ({r['body_a']}-{r['body_b']} {r['aspect']})"
        if vn != 1: errors.append(f"{tag}: variant_no 1 olmalı")
        if k in seen: errors.append(f"{tag}: tekrar eden anahtar (satır {seen[k]})")
        seen[k] = i
        if r.get("valence") not in VALENCES: errors.append(f"{tag}: valence geçersiz")
        it = r.get("intensity")
        if not isinstance(it, int) or not 1 <= it <= 4: errors.append(f"{tag}: intensity 1-4 olmalı")
        kw = r.get("keywords")
        if not isinstance(kw, list) or not 3 <= len(kw) <= 6 or not all(isinstance(x, str) and x.strip() for x in kw):
            errors.append(f"{tag}: keywords 3-6 dolu metin olmalı")
        if not isinstance(r.get("gist"), str) or not r["gist"].strip(): errors.append(f"{tag}: gist boş")
        for l in ("en", "tr"):
            if l not in r: errors.append(f"{tag}: '{l}' bloğu yok")
        for l in LOCALES:
            if l not in r: continue
            blk = r[l] or {}
            body = blk.get("body", "")
            if not isinstance(body, str) or not body.strip(): errors.append(f"{tag}/{l}: body boş"); continue
            if len(body) > MAX_BODY: errors.append(f"{tag}/{l}: body {len(body)} > {MAX_BODY}")
            if "!" in body or EMOJI_RE.search(body): errors.append(f"{tag}/{l}: ünlem veya emoji")
            if "%" in body: errors.append(f"{tag}/{l}: yüzde işareti (yüzde yok kararı)")
            if FORBIDDEN_RE.search(body): errors.append(f"{tag}/{l}: yasaklı kalıp")
            if HEDGE_RE.search(body): warnings.append(f"{tag}/{l}: kaçamak sözcük")
            if "  " in body: warnings.append(f"{tag}/{l}: çift boşluk")
            if l == "en" and GLUE_EN.search(body): errors.append(f"{tag}/en: bitişik sözcük şüphesi")
            if blk.get("notification"): warnings.append(f"{tag}/{l}: notification yok sayılır (NULL yazılır)")
    allk = {(a, b, asp) for a in range(10) for b in range(a, 10) for asp in ASPECTS}
    missing = sorted(allk - set(seen))
    if missing:
        warnings.append(f"{len(missing)} anahtar eksik (beklenen {EXPECTED}); ilk 5: " +
                        ", ".join(f"{BODIES[a]}-{BODIES[b]} {asp}" for a, b, asp in missing[:5]))
    return errors, warnings


def meaning_of(r):
    card = {"keywords": [k.strip() for k in r["keywords"]], "gist": r["gist"].strip()}
    raw = json.dumps(card, sort_keys=True, ensure_ascii=False) + f"|{r['valence']}|{r['intensity']}"
    return card, hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def apply(rows, prompt_version, model):
    load_env()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key: sys.exit("SUPABASE_URL ve SERVICE_ROLE_KEY gerekli (.env veya ortam).")
    api = Api(url, key)
    bodies = {x["code"].lower(): x["id"] for x in api.get_all("celestial_bodies?select=id,code")}
    aspects = {x["code"].lower(): x["id"] for x in api.get_all("aspect_types?select=id,code")}
    locales = {x["code"] for x in api.get_all("locales?select=code")}
    for n, d, names in (("celestial_bodies", bodies, BODIES), ("aspect_types", aspects, ASPECTS)):
        miss = [c for c in names if c.lower() not in d]
        if miss: sys.exit(f"{n} içinde kod bulunamadı: {miss}")

    def key_of(r):
        a, b = bodies[r["body_a"].lower()], bodies[r["body_b"].lower()]
        return (min(a, b), aspects[r["aspect"].lower()], max(a, b), 1)

    existing = {}
    for x in api.get_all("snippet_templates?select=id,transit_body_id,aspect_type_id,natal_body_id,variant_no,meaning_hash"
                         "&kind=eq.synastry&house_id=is.null&theme_id=is.null"):
        existing[(x["transit_body_id"], x["aspect_type_id"], x["natal_body_id"], x["variant_no"])] = x

    new_payload, patch, tmpl_of, new_idx = [], [], {}, {}
    for i, r in enumerate(rows):
        k = key_of(r)
        card, h = meaning_of(r)
        common = {"valence": r["valence"], "intensity": r["intensity"], "meaning_card": card, "meaning_hash": h}
        if k in existing:
            tmpl_of[i] = (existing[k]["id"], h)
            if existing[k]["meaning_hash"] != h:
                patch.append((existing[k]["id"], {**common, "status": "draft"}))
        else:
            new_payload.append({"kind": "synastry", "transit_body_id": k[0], "aspect_type_id": k[1],
                                "natal_body_id": k[2], "house_id": None, "theme_id": None,
                                "variant_no": 1, "status": "draft", **common})
            new_idx[k] = (i, h)
    for j in range(0, len(new_payload), 100):
        res = api.call("POST", "snippet_templates", new_payload[j:j + 100], prefer="return=representation")
        for x in res:
            kk = (x["transit_body_id"], x["aspect_type_id"], x["natal_body_id"], x["variant_no"])
            i, h = new_idx[kk]
            tmpl_of[i] = (x["id"], h)
    for tid, body in patch:
        api.call("PATCH", f"snippet_templates?id=eq.{tid}", body, prefer="return=minimal")
    print(f"şablon: {len(new_payload)} yeni, {len(patch)} güncellendi (hash değişti -> draft), "
          f"{len(rows) - len(new_payload) - len(patch)} aynı")

    ids = sorted({v[0] for v in tmpl_of.values()})
    old_tr = {}
    for j in range(0, len(ids), 100):
        chunk = ",".join(map(str, ids[j:j + 100]))
        for x in api.get_all(f"snippet_translations?select=template_id,locale,body,status&template_id=in.({chunk})"):
            old_tr[(x["template_id"], x["locale"])] = x
    out, skipped = [], 0
    now = datetime.now(timezone.utc).isoformat()
    for i, r in enumerate(rows):
        tid, h = tmpl_of[i]
        for l in LOCALES:
            if l not in r: continue
            if l not in locales: print(f"UYARI: locales içinde '{l}' yok, atlandı"); continue
            o = old_tr.get((tid, l))
            if o and o["status"] == "approved":
                if o["body"] != r[l]["body"]:
                    print(f"UYARI: onaylı çeviri korunuyor, atlandı (template {tid}/{l})")
                skipped += 1; continue
            out.append({"template_id": tid, "locale": l, "body": r[l]["body"].strip(), "notification": None,
                        "source_hash": h, "model": model, "prompt_version": prompt_version,
                        "status": "draft", "updated_at": now})
    for j in range(0, len(out), 200):
        api.call("POST", "snippet_translations?on_conflict=template_id,locale", out[j:j + 200],
                 prefer="resolution=merge-duplicates,return=minimal")
    print(f"çeviri: {len(out)} yazıldı, {skipped} atlandı")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="JSONL dosyası veya klasör")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--prompt-version", default="syn-v1")
    ap.add_argument("--model", default="claude")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.path, "*.jsonl"))) if os.path.isdir(a.path) else [a.path]
    if not files: sys.exit("JSONL bulunamadı")
    rows = []
    for fp in files:
        with open(fp, encoding="utf-8-sig") as f:
            for n, line in enumerate(f, 1):
                if line.strip():
                    try: rows.append(json.loads(line))
                    except json.JSONDecodeError as e: sys.exit(f"{fp} satır {n}: geçersiz JSON ({e})")
    errors, warnings = validate(rows)
    print(f"{len(files)} dosya, {len(rows)} satır okundu.")
    for w in warnings: print("UYARI:", w)
    for e in errors: print("HATA :", e)
    print(f"-> {len(errors)} hata, {len(warnings)} uyarı")
    if errors: sys.exit(1)
    if a.apply: apply(rows, a.prompt_version, a.model)
    else: print("Yalnızca doğrulama yapıldı. DB'ye yazmak için --apply ekle.")


if __name__ == "__main__":
    main()
    