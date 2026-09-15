#!/usr/bin/env python3
"""
Test scripti: Konya'da doğan örnek bir kişi için natal chart hesaplar.
Çalıştır: python -m module1_engine.test_engine
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from module1_engine import calculate_natal_chart, build_full_chart, to_json

def test_basic_chart():
    print("=" * 60)
    print("TEST 1: Temel natal chart hesaplama")
    print("=" * 60)
    
    chart = calculate_natal_chart(
        year=1998, month=11, day=23,
        hour=8, minute=30,
        city="Konya, Turkey"
    )
    
    print(f"✓ Doğum tarihi: {chart['input']['birth_date']}")
    print(f"✓ UTC saat: {chart['input']['utc_time']}")
    print(f"✓ Julian Day: {chart['input']['julian_day']}")
    print(f"✓ Koordinat: {chart['location']['latitude']}, {chart['location']['longitude']}")
    print()
    
    print("GEZEGENLER:")
    for planet, data in chart['planets'].items():
        if 'sign' in data:
            retro = " ℞" if data.get('retrograde') else ""
            print(f"  {planet:10} → {data['sign']:15} {data['degree_in_sign']:.2f}°  Ev:{data.get('house','?')}{retro}")
    
    print()
    print(f"ASC: {chart['angles']['ascendant']['sign']} {chart['angles']['ascendant']['degree_in_sign']:.2f}°")
    print(f" MC: {chart['angles']['midheaven']['sign']} {chart['angles']['midheaven']['degree_in_sign']:.2f}°")
    
    return chart

def test_aspects(chart):
    print()
    print("=" * 60)
    print("TEST 2: Aspect hesaplama")
    print("=" * 60)
    
    full_chart = build_full_chart(chart)
    
    major = [a for a in full_chart['aspects'] if a['nature'] == 'major']
    print(f"✓ Toplam aspect: {len(full_chart['aspects'])}")
    print(f"✓ Major aspect: {len(major)}")
    print()
    print("MAJOR ASPECTS:")
    for a in major:
        print(f"  {a['planet1']:10} {a['aspect']:15} {a['planet2']:10}  orb: {a['orb']:.2f}°")
    
    return full_chart

def test_summary(full_chart):
    print()
    print("=" * 60)
    print("TEST 3: Özet")
    print("=" * 60)
    
    s = full_chart['summary']
    print(f"Güneş Burcu:  {s['sun_sign']}")
    print(f"Ay Burcu:     {s['moon_sign']}")
    print(f"Yükselen:     {s['ascendant_sign']}")
    print(f"Elementler:   {s['element_distribution']}")
    print(f"Retrogradlar: {s['retrograde_planets']}")

def test_json_output(full_chart):
    print()
    print("=" * 60)
    print("TEST 4: JSON output")
    print("=" * 60)
    
    json_str = to_json(full_chart)
    
    # Dosyaya yaz
    output_path = "test_output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json_str)
    
    size = len(json_str)
    print(f"✓ JSON üretildi: {output_path} ({size} karakter)")
    
    # Parse edilebildiğini doğrula
    parsed = json.loads(json_str)
    assert "planets" in parsed
    assert "aspects" in parsed
    assert "summary" in parsed
    print("✓ JSON parse testi geçti")

def test_different_cities():
    print()
    print("=" * 60)
    print("TEST 5: Farklı şehirler")
    print("=" * 60)
    
    cities = [
        ("New York, USA", 1985, 3, 21, 8, 0),
        ("London, UK", 1992, 12, 1, 18, 45),
        ("Tokyo, Japan", 2000, 7, 4, 0, 0),
    ]
    
    for city, y, mo, d, h, mi in cities:
        try:
            chart = calculate_natal_chart(y, mo, d, h, mi, city)
            sun = chart['planets']['Sun']
            print(f"✓ {city:20} → Güneş: {sun['sign']:15} (UTC: {chart['input']['utc_time'][:19]})")
        except Exception as e:
            print(f"✗ {city}: {e}")

if __name__ == "__main__":
    try:
        chart = test_basic_chart()
        full_chart = test_aspects(chart)
        test_summary(full_chart)
        test_json_output(full_chart)
        test_different_cities()
        print()
        print("=" * 60)
        print("✅ TÜM TESTLER TAMAMLANDI")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ HATA: {e}")
        import traceback
        traceback.print_exc()


  
