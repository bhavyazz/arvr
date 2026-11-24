"""
get_scene_metadata.py – Extracts exact acquisition dates, spacecraft, MGRS tile,
and CLOUDY_PIXEL_PERCENTAGE for all Sentinel-2 scenes in the dry-season window
(Jan 1 to Mar 31) for 2018 and 2025 over the study area.
"""

import json
from pathlib import Path
import ee

ee.Initialize(project="psychic-droplet-419414")

study_area_path = Path(r"d:\ar_vr\urbanlens\data\study_area\study_area.geojson")
with open(study_area_path, "r", encoding="utf-8") as f:
    gj = json.load(f)
aoi = ee.Geometry(gj["features"][0]["geometry"])

results = {}

for year in [2018, 2025]:
    start = f"{year}-01-01"
    end   = f"{year}-03-31"

    all_col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(start, end)
    )

    scenes = all_col.getInfo()["features"]
    scene_list = []
    for s in scenes:
        p = s["properties"]
        idx = s["id"]
        from datetime import datetime, timezone
        ts = p.get("system:time_start", 0) / 1000.0
        acq_date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        cloud = p.get("CLOUDY_PIXEL_PERCENTAGE")
        craft = p.get("SPACECRAFT_NAME")
        mgrs = p.get("MGRS_TILE")
        passed = cloud < 20.0
        scene_list.append({
            "id": idx,
            "acquisition_date": acq_date,
            "spacecraft": craft,
            "mgrs_tile": mgrs,
            "cloudy_pixel_percentage": round(cloud, 2),
            "passed_filter": passed
        })

    results[year] = scene_list

out_path = Path(r"d:\ar_vr\urbanlens\reports\scene_metadata_audit.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"Audit results saved to: {out_path}\n")

for year, slist in results.items():
    passed_count = sum(1 for s in slist if s["passed_filter"])
    print(f"=== YEAR {year}: Total passes in catalog = {len(slist)}, Passed (<20%) = {passed_count} ===")
    for s in slist:
        status = "USED IN COMPOSITE" if s["passed_filter"] else f"REJECTED (>20% cloud)"
        print(f"  {s['acquisition_date'][:10]} | {s['spacecraft']} | Tile: {s['mgrs_tile']} | Cloud: {s['cloudy_pixel_percentage']:>5.2f}% | {status}")
    print()
