# SOULBOUND/test_service.py

import json
from astro_integration.core.service import generate_chart_service

def test(label, birth_date, birth_time, city):
    print(f"\n{'='*55}")
    print(f"TEST: {label}")
    print(f"{'='*55}")
    result = generate_chart_service(birth_date, birth_time, city)
    
    # Sadece kritik alanları göster
    print(f"STATUS      : {result.get('status')}")
    print(f"ERROR_CODE  : {result.get('error_code', '-')}")
    
    if result.get('status') == 'success':
        loc = result.get('location', {})
        print(f"CITY QUERY  : {loc.get('city_query')}")
        print(f"CITY RESOLVED: {loc.get('city_resolved')}")
        print(f"LATITUDE    : {loc.get('latitude')}")
        print(f"LONGITUDE   : {loc.get('longitude')}")
        print(f"TIMEZONE    : {loc.get('timezone')}")
        print(f"UTC OFFSET  : {loc.get('utc_offset')}")
        print(f"BIRTH UTC   : {result.get('input', {}).get('birth_time_utc')}")
        
        summary = result.get('summary', {})
        print(f"SUN SIGN    : {summary.get('sun_sign')}")
        print(f"MOON SIGN   : {summary.get('moon_sign')}")
        print(f"ASCENDANT   : {summary.get('ascendant_sign')}")
    else:
        print(f"MESSAGE     : {result.get('message')}")
        print(f"SUGGESTION  : {result.get('suggestion', '-')}")

if __name__ == "__main__":
    test("Konya doğum",   "1998-11-23", "08:30", "Konya, Turkey")
    test("Yanlış şehir",  "1998-11-23", "08:30", "Xyzabc12345")
    test("Gelecek tarih", "2099-01-01", "08:30", "Istanbul, Turkey")
    test("Hatalı saat",   "1998-11-23", "8:3",   "Istanbul, Turkey")
    test("Istanbul",      "1990-06-15", "14:30",  "Istanbul, Turkey")