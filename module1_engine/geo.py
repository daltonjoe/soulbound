from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pytz
from datetime import datetime

def get_coordinates(city: str) -> dict:
    """Şehir adından lat/lon ve timezone döner."""
    geolocator = Nominatim(user_agent="astro_saas_v1")
    location = geolocator.geocode(city, language="en")
    
    if not location:
        raise ValueError(f"Şehir bulunamadı: {city}")
    
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lat=location.latitude, lng=location.longitude)
    
    if not tz_name:
        raise ValueError(f"Timezone bulunamadı: {city}")
    
    return {
        "city": city,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timezone": tz_name,
        "address": location.address
    }

def to_utc(year: int, month: int, day: int, 
           hour: int, minute: int, timezone: str) -> datetime:
    """Yerel saati UTC'ye çevirir."""
    tz = pytz.timezone(timezone)
    local_dt = tz.localize(datetime(year, month, day, hour, minute))
    return local_dt.astimezone(pytz.utc)