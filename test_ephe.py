import swisseph as swe
import os

swe.set_ephe_path(os.path.join(os.getcwd(), "ephemeris"))

jd = swe.julday(1990, 6, 15, 14.5)
pos, ret = swe.calc_ut(jd, swe.SUN)
print("Julian Day:", round(jd, 4))
print("Gunes longitude:", round(pos[0], 4))
print("Beklenen: ~84 derece (Ikizler burcu)")
print("Ephemeris OK!")