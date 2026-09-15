import swisseph as swe
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pytz

print("pyswisseph OK:", swe.__version__)
print("geopy OK")
print("timezonefinder OK")
print("pytz OK:", pytz.__version__)

tf = TimezoneFinder()
tz = tf.timezone_at(lat=41.0082, lng=28.9784)
print("Istanbul timezone:", tz)