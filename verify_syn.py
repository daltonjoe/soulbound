import io, glob, json, os, re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
D = sys.argv[1] if len(sys.argv) > 1 else "data/synastry"
P = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]
ID = {n: i + 1 for i, n in enumerate(P)}
GROUPS = ["sun","moon","mercury","venus","mars","jupiter","saturn","outer"]
ASP = ["conjunction","sextile","square","trine","opposition"]
def pairs_for(g):
    if g == "outer": a = ["Uranus","Neptune","Pluto"]
    else: a = [g.capitalize()]
    return [(x, y) for x in a for y in P if ID[y] >= ID[x]]
FORB_EN = re.compile(r"\b(today|doomed|soulmate|toxic|ruined|perfect match)\b", re.I)
FORB_TR = re.compile(r"(bugün|ruh eşi|toksik)", re.I)
NAMES_EN = re.compile(r"\b(Sun|Moon|Mercury|Venus|Mars|Jupiter|Saturn|Uranus|Neptune|Pluto)\b")
NAMES_TR = re.compile(r"(Güneş|Merkür|Venüs|Mars|Jüpiter|Satürn|Uranüs|Neptün|Plüton)")
BADOPEN = ("Kimlik ile","Sıcaklık ile","Yenilik ve","Değişim ve","İkiniz de")
err = []; warn = []; keys = set(); opens = {}; total = 0
def E(m): err.append(m)
for g in GROUPS:
    exp = pairs_for(g)
    for a in ASP:
        fn = "%s/syn_%s_%s.jsonl" % (D, g, a)
        if not os.path.exists(fn): E(fn + ": YOK"); continue
        raw = io.open(fn, "rb").read()
        if raw.startswith(b"\xef\xbb\xbf"): E(fn + ": BOM var")
        lines = [l for l in raw.decode("utf-8-sig").split("\n") if l.strip()]
        if len(lines) != len(exp): E("%s: satir %d, beklenen %d" % (fn, len(lines), len(exp)))
        got = []
        for i, l in enumerate(lines, 1):
            t = "%s#%d" % (os.path.basename(fn), i)
            try: d = json.loads(l)
            except Exception as e: E(t + ": JSON " + str(e)); continue
            total += 1
            if d.get("kind") != "synastry": E(t + ": kind")
            if d.get("aspect") != a: E(t + ": aspect dosya ile uyusmuyor")
            ba, bb = d.get("body_a"), d.get("body_b")
            if ba not in ID or bb not in ID: E(t + ": bilinmeyen govde"); continue
            if ID[ba] > ID[bb]: E(t + ": ID sirasi ters %s>%s" % (ba, bb))
            got.append((ba, bb)); k = (ba, bb, a)
            if k in keys: E(t + ": yinelenen anahtar")
            keys.add(k)
            if d.get("variant_no") != 1: E(t + ": variant_no")
            if "notification" in d or "notification" in d.get("en", {}) or "notification" in d.get("tr", {}): E(t + ": notification var")
            v = d.get("valence")
            if v not in ("power","pressure","neutral"): E(t + ": valence " + str(v))
            it = d.get("intensity")
            if not isinstance(it, int) or not 1 <= it <= 4: E(t + ": intensity " + str(it))
            if {ba, bb} == {"Venus","Mars"} and a == "conjunction" and v != "power": E(t + ": Venus-Mars conj power olmali")
            if ba in P[7:] and bb in P[7:] and it != 1: E(t + ": kusak cifti intensity 1 olmali")
            kw = d.get("keywords", [])
            if not 3 <= len(kw) <= 6: E(t + ": keywords sayisi")
            if not d.get("gist"): E(t + ": gist yok")
            for loc in ("en", "tr"):
                b = d.get(loc, {}).get("body", "")
                if not b: E(t + ": %s body yok" % loc); continue
                if len(b) > 220: E("%s: %s body %d karakter" % (t, loc, len(b)))
                if "!" in b: E(t + ": unlem " + loc)
                if "\u0307" in b or unicodedata.normalize("NFC", b) != b: E(t + ": NFC degil " + loc)
                if re.search(r"[a-zçğıöşü][A-ZÇĞİÖŞÜ]", b): warn.append(t + ": yapisik soz? " + loc)
                if re.search(r"[a-z]{4,}(?:before|meets|for|to|and|the)[a-z]{4,}", b) and False: pass
            for kwd in kw:
                if re.search(r"[a-z][A-Z]", kwd): E(t + ": keywords yapisik")
            en = d.get("en", {}).get("body", ""); tr = d.get("tr", {}).get("body", "")
            if FORB_EN.search(en) or NAMES_EN.search(en): E(t + ": en yasakli/gezegen adi")
            if FORB_TR.search(tr) or NAMES_TR.search(tr): E(t + ": tr yasakli/gezegen adi")
            if tr.startswith(BADOPEN):
                if g in ("moon","mercury","venus","mars"): E(t + ": tr yasakli acilis")
                else: warn.append(t + ": tr acilis (eski dosya)")
            o = " ".join(tr.split()[:2]); opens.setdefault(o, []).append(t)
        if sorted(got) != sorted(exp): E("%s: cift listesi beklenenle uyusmuyor" % fn)
if total != 275: E("toplam satir %d, beklenen 275" % total)
if len(keys) != 275: E("benzersiz anahtar %d, beklenen 275" % len(keys))
for o, ts in opens.items():
    if len(ts) > 3: warn.append("tr acilis '%s' x%d" % (o, len(ts)))
for m in err: print("HATA", m)
for m in warn[:40]: print("UYARI", m)
print("SONUC: HATA %d, UYARI %d, satir %d, anahtar %d" % (len(err), len(warn), total, len(keys)))
sys.exit(1 if err else 0)