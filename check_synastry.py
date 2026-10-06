import io, json, re, sys, glob, os, collections

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

GROUPS = {
 "sun": ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"],
 "moon": ["Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"],
 "venus": ["Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"],
 "mars": ["Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"],
 "mercury": ["Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"],
 "jupiter": ["Jupiter","Saturn","Uranus","Neptune","Pluto"],
 "saturn": ["Saturn","Uranus","Neptune","Pluto"],
 "outer": None,
}
OUTER_PAIRS = [("Uranus","Uranus"),("Uranus","Neptune"),("Uranus","Pluto"),
               ("Neptune","Neptune"),("Neptune","Pluto"),("Pluto","Pluto")]
ASPECTS = ["conjunction","sextile","square","trine","opposition"]
ORDER = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]
TR = {"Sun":"Güneş","Moon":"Ay","Mercury":"Merkür","Venus":"Venüs","Mars":"Mars",
      "Jupiter":"Jüpiter","Saturn":"Satürn","Uranus":"Uranüs","Neptune":"Neptün","Pluto":"Plüton"}
PERSONAL = {"Sun","Moon","Venus","Mars"}
OUTER3 = {"Uranus","Neptune","Pluto"}
FORBID = ["uyumlu","uyumsuz","ruh eşi","kader","karmik","toksik","kusursuz","mükemmel eşleşme",
          "felaket","lanet","soulmate","destiny","karmic","toxic","perfect match","doomed"]
SENSITIVE = [r"\bevlilik\b",r"\bboşan",r"\bsadakat",r"\bhamile",r"\bçocuk",r"\bpara\b",r"\bsağlık",
             r"\bölüm\b",r"\bhukuk",r"\baldat",r"\bmarriage",r"\bdivorce",r"\bcheat",r"\bpregnan",
             r"\bchild",r"\bmoney\b",r"\bhealth\b",r"\bdeath\b",r"\blegal\b"]
MAXB = 220

def pairs_for(group):
    if group == "outer":
        return OUTER_PAIRS
    return [(group.capitalize(), x) for x in GROUPS[group]]

def exp_valence(a, b, asp):
    if asp in ("sextile","trine"): return "power"
    if asp in ("square","opposition"): return "pressure"
    s = {a, b}
    if s == {"Venus","Mars"}: return "power"
    if s == {"Venus", "Neptune"}: return "neutral"
    if s == {"Mars", "Jupiter"}: return "power"
    if s & {"Mars","Saturn","Pluto","Uranus"}: return "pressure"
    if s & {"Venus","Jupiter"}: return "power"
    return "neutral"

def exp_intensity(a, b):
    """(lo, hi, hard)"""
    s = {a, b}
    if s <= OUTER3: return (1, 1, True)
    if s & PERSONAL: return (3, 4, True)
    if s & {"Jupiter","Saturn"} and s & OUTER3: return (1, 2, False)
    if s & {"Mercury","Jupiter","Saturn"}: return (2, 3, False)
    return (1, 4, False)

errors, warns = [], []
def E(m): errors.append(m)
def W(m): warns.append(m)

seen = {}
openers_tr = collections.Counter()
total = 0
files_ok = 0
for group in GROUPS:
    for asp in ASPECTS:
        path = os.path.join("data","synastry","syn_%s_%s.jsonl" % (group, asp))
        tag = os.path.basename(path)
        if not os.path.exists(path):
            E("%s: dosya YOK" % tag); continue
        raw = open(path, "rb").read()
        if raw.startswith(b"\xef\xbb\xbf"): E("%s: BOM var" % tag)
        text = raw.decode("utf-8-sig")
        lines = text.split("\n")
        if lines and lines[-1] == "": lines = lines[:-1]
        lines = [l.rstrip("\r") for l in lines]
        exp = pairs_for(group)
        if len(lines) != len(exp):
            E("%s: satır %d, beklenen %d" % (tag, len(lines), len(exp)))
        got_pairs = []
        local_open = collections.Counter()
        for i, line in enumerate(lines, 1):
            t = "%s#%d" % (tag, i)
            if line.strip().startswith("```") or not line.strip():
                E("%s: boş satır veya kod çiti" % t); continue
            try:
                r = json.loads(line)
            except Exception as ex:
                E("%s: JSON hatası %s" % (t, ex)); continue
            if not isinstance(r, dict):
                E("%s: nesne değil" % t); continue
            req = ["kind","body_a","body_b","aspect","variant_no","valence","intensity","keywords","gist","en","tr"]
            miss = [k for k in req if k not in r]
            if miss: E("%s: eksik alan %s" % (t, miss)); continue
            extra = set(r) - set(req)
            if extra: W("%s: fazla alan %s" % (t, sorted(extra)))
            if r["kind"] != "synastry": E("%s: kind=%r" % (t, r["kind"]))
            a, b = r["body_a"], r["body_b"]
            if a not in ORDER or b not in ORDER:
                E("%s: geçersiz gezegen %s-%s" % (t, a, b)); continue
            if ORDER.index(a) > ORDER.index(b): E("%s: ID sırası ters %s-%s" % (t, a, b))
            if r["aspect"] != asp: E("%s: aspect %r, dosya %r" % (t, r["aspect"], asp))
            if r["variant_no"] != 1: E("%s: variant_no %r" % (t, r["variant_no"]))
            got_pairs.append((a, b))
            key = (a, b, r["aspect"])
            if key in seen: E("%s: tekrar anahtar (önce %s)" % (t, seen[key]))
            seen[key] = t
            ev = exp_valence(a, b, asp)
            if r["valence"] == "trouble": E("%s: trouble yasak" % t)
            elif r["valence"] != ev: E("%s: valence %r, beklenen %r" % (t, r["valence"], ev))
            it = r["intensity"]
            if not isinstance(it, int) or it < 1 or it > 4:
                E("%s: intensity %r (1-4)" % (t, it))
            else:
                lo, hi, hard = exp_intensity(a, b)
                if not (lo <= it <= hi):
                    (E if hard else W)("%s: intensity %d, beklenen %d-%d" % (t, it, lo, hi))
                if a == b and a in PERSONAL and it != 3:
                    W("%s: aynı kişisel gezegen, intensity %d (öneri 3)" % (t, it))
            kw = r["keywords"]
            if not isinstance(kw, list) or not (3 <= len(kw) <= 6) or not all(isinstance(x, str) and x.strip() for x in kw):
                E("%s: keywords 3-6 olmalı" % t)
            if not isinstance(r["gist"], str) or not r["gist"].strip(): E("%s: gist boş" % t)
            for lang in ("en","tr"):
                blk = r[lang]
                if not isinstance(blk, dict) or not str(blk.get("body","")).strip():
                    E("%s/%s: body boş" % (t, lang)); continue
                if blk.get("notification"): E("%s/%s: notification dolu (olmamalı)" % (t, lang))
                body = blk["body"]
                if len(body) > MAXB: E("%s/%s: body %d > %d" % (t, lang, len(body), MAXB))
                low = body.lower()
                for f in FORBID:
                    if f in low: E("%s/%s: yasak ifade %r" % (t, lang, f))
                if "!" in body: E("%s/%s: ünlem" % (t, lang))
                if re.search(r"\d", body): W("%s/%s: rakam var" % (t, lang))
                if re.search(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", body): E("%s/%s: emoji" % (t, lang))
                for s in SENSITIVE:
                    if re.search(s, low): W("%s/%s: hassas kelime %s" % (t, lang, s))
                ns = len([x for x in re.split(r"(?<=[.?])\s+", body.strip()) if x])
                if ns > 3: W("%s/%s: %d cümle (>3)" % (t, lang, ns))
                other = [n for n in ORDER if n not in (a, b)]
                names = [TR[n] for n in other] if lang == "tr" else other
                for n in names:
                    if re.search(r"\b%s\b" % re.escape(n), body):
                        W("%s/%s: pair dışı gezegen adı %s" % (t, lang, n))
            words = r["tr"]["body"].split()[:2] if isinstance(r["tr"], dict) else []
            if len(words) == 2:
                o = " ".join(words).lower()
                local_open[o] += 1; openers_tr[o] += 1
        for o, c in local_open.items():
            if c > 1: W("%s: aynı açılış %r x%d" % (tag, o, c))
        if got_pairs and sorted(got_pairs) != sorted(exp):
            E("%s: çift listesi beklenenden farklı; eksik=%s fazla=%s" % (
                tag, sorted(set(exp) - set(got_pairs)), sorted(set(got_pairs) - set(exp))))
        elif got_pairs and got_pairs != exp:
            W("%s: çift sırası <pairs> sırasından farklı" % tag)
        total += len(lines); files_ok += 1

for o, c in openers_tr.most_common(8):
    if c >= 4: W("GLOBAL: tr açılış %r x%d" % (o, c))
if len(seen) != 275: E("benzersiz anahtar %d, beklenen 275" % len(seen))

print("dosya: %d/40 okundu, satır: %d (beklenen 275), benzersiz anahtar: %d" % (files_ok, total, len(seen)))
for m in errors: print("HATA  " + m)
for m in warns: print("UYARI " + m)
print("HATA %d, UYARI %d" % (len(errors), len(warns)))
sys.exit(1 if errors else 0)