#!/usr/bin/env python3
"""
SoulBound - check_data.py: data/*.jsonl kapsam + doğrulama raporu (ağ yok, DB'ye dokunmaz).
Backend klasöründe, import_snippets.py ile aynı yerde:
  python check_data.py          # özet rapor
  python check_data.py --dump   # + satır başına kısa döküm (keywords, gist, bildirimler)
"""
import glob, json, os, sys
from collections import Counter
import import_snippets as S

DUMP = "--dump" in sys.argv
rows, files, problems = [], {}, []
for fp in sorted(glob.glob(os.path.join("data", "*.jsonl"))):
    name = os.path.basename(fp)
    with open(fp, "rb") as fb:
        if fb.read(3) == b"\xef\xbb\xbf":
            problems.append(f"{name}: BOM var (importer okuyamaz, BOM'suz kaydet)")
    with open(fp, encoding="utf-8-sig") as f:
        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError as e:
                problems.append(f"{name}:{ln}: geçersiz JSON ({e})")
                continue
            r["_f"] = name
            rows.append(r)
            files.setdefault(name, []).append(r)

print(f"== KAPSAM: {len(files)} dosya, {len(rows)} satır (hedef 25 dosya, 250 satır) ==")
expected = {f"{t.lower()}_{a}.jsonl" for t in S.TRANSITS for a in S.ASPECTS}
missing = []
for t in S.TRANSITS:
    cells = []
    for a in S.ASPECTS:
        name = f"{t.lower()}_{a}.jsonl"
        rs = files.get(name)
        if rs is None:
            missing.append(name)
            cells.append(f"{a[:4]}=YOK")
            continue
        nats = Counter(r.get("natal_point") for r in rs)
        miss = [n for n in S.NATALS if n not in nats]
        dup = [n for n, c in nats.items() if c > 1]
        wrong = [r.get("natal_point") for r in rs if (r.get("transit_body"), r.get("aspect")) != (t, a)]
        noloc = sum(1 for r in rs if not all(l in r for l in ("en", "tr")))
        ok = not (miss or dup or wrong or noloc)
        cells.append(f"{a[:4]}={len(rs)}" + ("" if ok else f"!(eksik={miss} tekrar={dup} yanlis={wrong} dilsiz={noloc})"))
    print(f"{t}: " + " ".join(cells))
print("YOK:", ", ".join(missing) if missing else "-")
extra = sorted(set(files) - expected)
if extra:
    print("BEKLENMEYEN DOSYA:", ", ".join(extra))

for p in problems:
    print("DOSYA:", p)

errors, warnings = S.validate(rows)
print(f"== DOĞRULAMA (tüm dosyalar birlikte): {len(errors)} hata, {len(warnings)} uyarı ==")
for e in errors[:40]:
    print("HATA :", e)
for w in warnings[:40]:
    print("UYARI:", w)
if len(errors) > 40 or len(warnings) > 40:
    print("(liste kısaltıldı)")

print("== DAĞILIM ==")
print("valence  :", dict(Counter(r.get("valence") for r in rows)))
print("intensity:", dict(sorted(Counter(r.get("intensity") for r in rows).items(), key=lambda x: str(x[0]))))
print("intensity 5:", [(r["_f"][:-6], r.get("natal_point"), r.get("valence")) for r in rows if r.get("intensity") == 5])

if DUMP:
    print("== DÖKÜM (dosya|natal|valence|int|keywords|gist|EN bildirim|TR bildirim) ==")
    for r in rows:
        print("|".join([
            r["_f"][:-6], str(r.get("natal_point")), str(r.get("valence")), str(r.get("intensity")),
            ",".join(r.get("keywords", [])), str(r.get("gist")),
            "EN:" + str(r.get("en", {}).get("notification")), "TR:" + str(r.get("tr", {}).get("notification")),
        ]))