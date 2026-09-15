import json
from .aspects import calculate_aspects

def build_full_chart(natal_data: dict, include_minor_aspects: bool = True) -> dict:
    """Natal chart verisine aspect'leri ekleyip tam JSON oluşturur."""
    aspects = calculate_aspects(natal_data["planets"], include_minor_aspects)
    
    return {
        **natal_data,
        "aspects": aspects,
        "summary": build_summary(natal_data, aspects)
    }

def build_summary(natal_data: dict, aspects: list) -> dict:
    """Hızlı erişim için özet veriler."""
    planets = natal_data["planets"]
    
    # Burç dağılımı
    sign_count = {}
    element_map = {
    "Koç": "Ateş", "Aslan": "Ateş", "Yay": "Ateş",
    "Boğa": "Toprak", "Başak": "Toprak", "Oğlak": "Toprak",
    "İkizler": "Hava", "Terazi": "Hava", "Kova": "Hava",
    "Yengeç": "Su", "Akrep": "Su", "Balık": "Su"
    }
    element_count = {"Ateş": 0, "Toprak": 0, "Hava": 0, "Su": 0}
    
    for planet, data in planets.items():
        if "sign" in data:
            sign = data["sign"]
            sign_count[sign] = sign_count.get(sign, 0) + 1
            element_count[element_map.get(sign, "Unknown")] += 1
    
    # Retrograd gezegenler
    retrogrades = [name for name, data in planets.items() 
                   if data.get("retrograde", False)]
    
    # Major aspect sayıları
    major_aspects = [a for a in aspects if a["nature"] == "major"]
    
    return {
        "sun_sign": planets.get("Sun", {}).get("sign", "Unknown"),
        "moon_sign": planets.get("Moon", {}).get("sign", "Unknown"),
        "ascendant_sign": natal_data["angles"]["ascendant"].get("sign", "Unknown"),
        "element_distribution": element_count,
        "sign_distribution": sign_count,
        "retrograde_planets": retrogrades,
        "total_aspects": len(aspects),
        "major_aspects_count": len(major_aspects)
    }

def to_json(chart_data: dict, indent: int = 2) -> str:
    return json.dumps(chart_data, ensure_ascii=False, indent=indent)