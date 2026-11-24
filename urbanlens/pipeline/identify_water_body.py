"""
identify_water_body.py – Queries Nominatim and Overpass to identify the exact
water body / feature at Lat 12.8409°N, Lon 77.5347°E.
"""

import json
import urllib.request
import urllib.parse

lat = 12.8409
lon = 77.5347

# 1. Reverse geocode via Nominatim
nom_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=jsonv2&zoom=18&addressdetails=1"
req = urllib.request.Request(nom_url, headers={"User-Agent": "UrbanLens/1.0 academic"})
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    print("=== Nominatim Reverse Geocode Result ===")
    print("  Display name:", data.get("display_name"))
    print("  Category / Type:", data.get("category"), "/", data.get("type"))
    print("  Address:", data.get("address"))
except Exception as e:
    print("Nominatim error:", e)

# 2. Overpass query around 500m bbox
endpoint = "https://overpass-api.de/api/interpreter"
ql = f"""[out:json][timeout:25];
(
  way["natural"="water"]({lat-0.005},{lon-0.005},{lat+0.005},{lon+0.005});
  way["landuse"="quarry"]({lat-0.005},{lon-0.005},{lat+0.005},{lon+0.005});
  way["water"]({lat-0.005},{lon-0.005},{lat+0.005},{lon+0.005});
  node["natural"="water"]({lat-0.005},{lon-0.005},{lat+0.005},{lon+0.005});
);
out tags center;
"""
data = urllib.parse.urlencode({"data": ql}).encode()
req = urllib.request.Request(endpoint, data=data, headers={"User-Agent": "UrbanLens/1.0 academic", "Content-Type": "application/x-www-form-urlencoded"})
try:
    with urllib.request.urlopen(req, timeout=25) as resp:
        ores = json.loads(resp.read().decode())
    print("\n=== Overpass OSM Features ===")
    for el in ores.get("elements", []):
        print(" ", el.get("type"), el.get("id"), el.get("tags"), "center:", el.get("center"))
except Exception as e:
    print("Overpass error:", e)

