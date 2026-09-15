ASPECT_DEFINITIONS = {
    "Kavuşum":    {"angle": 0,   "orb": 8,  "nature": "major"},
    "Karşıtlık":  {"angle": 180, "orb": 8,  "nature": "major"},
    "Üçgen":      {"angle": 120, "orb": 8,  "nature": "major"},
    "Kare":       {"angle": 90,  "orb": 7,  "nature": "major"},
    "Altıgen":    {"angle": 60,  "orb": 6,  "nature": "major"},
    "Yüzelli":    {"angle": 150, "orb": 3,  "nature": "minor"},
    "Otuzluk":    {"angle": 30,  "orb": 2,  "nature": "minor"},
    "Kırkbeşlik": {"angle": 45,  "orb": 2,  "nature": "minor"},
    "YüzOtuzBeş": {"angle": 135, "orb": 2,  "nature": "minor"},
    "Beştebirlik":{"angle": 72,  "orb": 2,  "nature": "minor"},
}

def angular_distance(lon1: float, lon2: float) -> float:
    """İki boylam arasındaki minimum açı mesafesi."""
    diff = abs(lon1 - lon2) % 360
    return min(diff, 360 - diff)

def calculate_aspects(planets: dict, include_minor: bool = True) -> list:
    """Tüm gezegen çiftleri arasındaki açıları hesaplar."""
    aspects = []
    planet_names = [name for name in planets if "longitude" in planets[name]]
    
    for i in range(len(planet_names)):
        for j in range(i + 1, len(planet_names)):
            p1_name = planet_names[i]
            p2_name = planet_names[j]
            
            lon1 = planets[p1_name]["longitude"]
            lon2 = planets[p2_name]["longitude"]
            distance = angular_distance(lon1, lon2)
            
            for aspect_name, aspect_def in ASPECT_DEFINITIONS.items():
                if not include_minor and aspect_def["nature"] == "minor":
                    continue
                
                target = aspect_def["angle"]
                orb = aspect_def["orb"]
                
                if abs(distance - target) <= orb:
                    actual_orb = round(abs(distance - target), 4)
                    applying = is_applying(
                        planets[p1_name]["speed"],
                        planets[p2_name]["speed"],
                        lon1, lon2, target
                    )
                    
                    aspects.append({
                        "planet1": p1_name,
                        "planet2": p2_name,
                        "aspect": aspect_name,
                        "angle": target,
                        "actual_angle": round(distance, 4),
                        "orb": actual_orb,
                        "nature": aspect_def["nature"],
                        "applying": applying,
                        "separating": not applying
                    })
                    break  # Bir çift için bir açı yeterli
    
    return aspects

def is_applying(speed1: float, speed2: float, 
                lon1: float, lon2: float, target_angle: float) -> bool:
    """Açının oluşmakta mı (applying) yoksa ayrılmakta mı (separating) olduğunu belirler."""
    current_diff = angular_distance(lon1, lon2)
    relative_speed = speed1 - speed2
    return abs(current_diff - target_angle) > 0 and relative_speed != 0