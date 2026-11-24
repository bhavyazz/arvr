"""
audit_l1c_l2a_counts.py – Verifies the 2018 L1C vs L2A scene counts
over Sentinel-2 Tile 43PGQ for the dry season (2018-01-01 to 2018-03-31).
"""

import json
from datetime import datetime, timezone
import ee

ee.Initialize(project="psychic-droplet-419414")

study_area_path = "d:/ar_vr/urbanlens/data/study_area/study_area.geojson"
with open(study_area_path, "r", encoding="utf-8") as f:
    gj = json.load(f)
aoi = ee.Geometry(gj["features"][0]["geometry"])

# 1. Query L2A Surface Reflectance Harmonized
l2a_col = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(aoi)
    .filterDate("2018-01-01", "2018-03-31")
    .filter(ee.Filter.eq("MGRS_TILE", "43PGQ"))
)

# 2. Query L1C Top-of-Atmosphere Harmonized
l1c_col = (
    ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
    .filterBounds(aoi)
    .filterDate("2018-01-01", "2018-03-31")
    .filter(ee.Filter.eq("MGRS_TILE", "43PGQ"))
)

l2a_scenes = l2a_col.getInfo()["features"]
l1c_scenes = l1c_col.getInfo()["features"]

print(f"=================================================================")
print(f"  SENTINEL-2 TILE 43PGQ INVENTORY (2018-01-01 to 2018-03-31)")
print(f"=================================================================")
print(f"Total L1C (Top-of-Atmosphere) scenes in catalog: {len(l1c_scenes)}")
print(f"Total L2A (Surface Reflectance) scenes in catalog: {len(l2a_scenes)}")
print(f"=================================================================\n")

def get_scene_table(scenes):
    rows = []
    for s in scenes:
        p = s["properties"]
        ts = p.get("system:time_start", 0) / 1000.0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        craft = p.get("SPACECRAFT_NAME", "Unknown")
        cloud = p.get("CLOUDY_PIXEL_PERCENTAGE", -1.0)
        rows.append((dt, craft, cloud, s["id"]))
    return rows

l1c_table = get_scene_table(l1c_scenes)
l2a_table = get_scene_table(l2a_scenes)

l2a_dates = set(r[0][:10] for r in l2a_table)

print("--- All 17 L1C (TOA) Overpasses ---")
for dt, craft, cloud, sid in l1c_table:
    d_short = dt[:10]
    in_l2a = "Available in L2A catalog" if d_short in l2a_dates else "MISSING in L2A catalog (processing/availability difference)"
    print(f"  {dt} | {craft} | Cloud: {cloud:>6.2f}% | {in_l2a}")

print("\n--- All 7 L2A (SR) Overpasses ---")
for dt, craft, cloud, sid in l2a_table:
    print(f"  {dt} | {craft} | Cloud: {cloud:>6.2f}% | ID: {sid.split('/')[-1]}")

