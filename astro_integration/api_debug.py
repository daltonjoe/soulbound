"""
api_debug.py — FreeAstrologyAPI auth sorununu çöz

Çalıştır:
    python api_debug.py
"""
import httpx
import json

API_KEY = "Jky6DTfaPF8VnwjoO7L4K2zf1MqQedFDNANtH7la"
BASE    = "https://json.freeastrologyapi.com"

# Test body (minimal, gerçek değerler)
BODY = {
    "year": 1998, "month": 11, "date": 23,
    "hours": 6, "minutes": 30, "seconds": 0,
    "latitude": 37.87, "longitude": 32.49,
    "timezone": 3.0,
    "config": {
        "observation_point": "topocentric",
        "ayanamsha": "tropical",
    },
}

ENDPOINT = "/western-astrology/planets"

# AWS API Gateway "Missing Authentication Token" genellikle şu 3 şeyden biri:
#   1. Header adı yanlış  → x-api-key  (doğru)  vs  Authorization  (yanlış)
#   2. Key query string'de bekleniyor → ?x-api-key=...
#   3. Base URL yanlış (AWS path yok)

ATTEMPTS = [
    # (açıklama, headers, params)
    (
        "x-api-key header (standart AWS)",
        {"Content-Type": "application/json", "x-api-key": API_KEY},
        {},
    ),
    (
        "x-api-key header (küçük harf)",
        {"content-type": "application/json", "x-api-key": API_KEY},
        {},
    ),
    (
        "Authorization: Bearer",
        {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
        {},
    ),
    (
        "Authorization: Api-Key",
        {"Content-Type": "application/json", "Authorization": f"Api-Key {API_KEY}"},
        {},
    ),
    (
        "Query string: ?x-api-key=",
        {"Content-Type": "application/json"},
        {"x-api-key": API_KEY},
    ),
    (
        "Query string: ?key=",
        {"Content-Type": "application/json"},
        {"key": API_KEY},
    ),
    (
        "Body içinde api_key",
        {"Content-Type": "application/json"},
        {},
        # body'ye eklenecek
    ),
]


def test():
    print("=" * 60)
    print("FreeAstrologyAPI Auth Debug")
    print("=" * 60)

    with httpx.Client(timeout=10) as client:

        # Deneme 1-6: farklı header/param kombinasyonları
        for i, attempt in enumerate(ATTEMPTS[:6], 1):
            desc, headers, params = attempt
            url = f"{BASE}{ENDPOINT}"

            try:
                r = client.post(url, headers=headers, params=params, json=BODY)
                status = r.status_code
                body_preview = r.text[:120].replace("\n", " ")
                print(f"\n[{i}] {desc}")
                print(f"    Status: {status}")
                print(f"    Body  : {body_preview}")

                if status == 200:
                    print(f"    ✅ BAŞARILI! Bu header/param kombinasyonu çalışıyor.")
                    print(f"\n    Tam response:")
                    print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:500])
                    return headers, params
                elif status == 403:
                    print(f"    ✗ 403 — auth reddedildi")
                elif status == 401:
                    print(f"    ✗ 401 — geçersiz key")
                elif status == 404:
                    print(f"    ✗ 404 — endpoint yanlış olabilir")
                else:
                    print(f"    ? {status}")

            except Exception as e:
                print(f"\n[{i}] {desc}")
                print(f"    ✗ Hata: {e}")

        # Deneme 7: api_key body içinde
        print(f"\n[7] api_key body içinde gönder")
        body_with_key = {**BODY, "api_key": API_KEY}
        try:
            r = client.post(
                f"{BASE}{ENDPOINT}",
                headers={"Content-Type": "application/json"},
                json=body_with_key,
            )
            print(f"    Status: {r.status_code} — {r.text[:120]}")
            if r.status_code == 200:
                print("    ✅ BAŞARILI! api_key body içinde çalışıyor.")
        except Exception as e:
            print(f"    ✗ {e}")

        # Endpoint'leri de dene — belki URL farklı
        print(f"\n─── Alternatif endpoint'leri test et ───")
        alt_endpoints = [
            "/v1/western-astrology/planets",
            "/western/planets",
            "/natal/planets",
        ]
        headers_std = {"Content-Type": "application/json", "x-api-key": API_KEY}
        for ep in alt_endpoints:
            try:
                r = client.post(f"{BASE}{ep}", headers=headers_std, json=BODY)
                print(f"  {ep} → {r.status_code}: {r.text[:80]}")
            except Exception as e:
                print(f"  {ep} → ✗ {e}")

    print("\n─── Sonuç ───────────────────────────────────────────────")
    print("Hiçbir kombinasyon çalışmadıysa:")
    print("  1. API key'ini freeastrologyapi.com/login'den kontrol et")
    print("  2. Hesabının aktif olduğunu doğrula (email onayı gerekebilir)")
    print("  3. Western API'nin ayrı bir key gerektirip gerektirmediğine bak")


if __name__ == "__main__":
    test()