"""
extract_ward_study_area.py – Extracts the BBMP 243-ward polygon containing
the Pattanagere centroid, computes its area, and saves it as
data/study_area/study_area.geojson.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from shapely.geometry import shape, Point
import geopandas as gpd

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PATH   = REPO_ROOT / "data" / "study_area" / "datameet_BBMP_new.geojson"
OUT_PATH  = REPO_ROOT / "data" / "study_area" / "study_area.geojson"

CENTROID_LON = 77.5067010
CENTROID_LAT = 12.9200602
pt = Point(CENTROID_LON, CENTROID_LAT)


def main():
    retrieval_date = "2026-11-10T12:55:41+00:00"
    gj = json.loads(IN_PATH.read_text(encoding="utf-8", errors="replace"))

    target_feature = None
    for feat in gj["features"]:
        geom = shape(feat["geometry"])
        if geom.contains(pt):
            target_feature = feat
            break

    if not target_feature:
        raise RuntimeError("No ward in 243-ward dataset contains the centroid!")

    orig_props = target_feature["properties"]
    print("Found containing ward in 243-ward set:")
    print(" ", orig_props)

    # Use GeoPandas to compute projected area in km² (EPSG:7755 - India South or EPSG:3857/UTM 43N)
    # UTM 43N (EPSG:32643) is standard for Bengaluru
    gdf = gpd.GeoDataFrame.from_features([target_feature], crs="EPSG:4326")
    gdf_utm = gdf.to_crs(epsg=32643)
    area_sq_m = gdf_utm.geometry.area.iloc[0]
    area_km2 = round(area_sq_m / 1e6, 3)

    # Verify containment
    contains_check = gdf.geometry.iloc[0].contains(pt)
    print(f"Area in UTM 43N: {area_km2:.3f} km²")
    print(f"Point containment verified: {contains_check}")

    new_properties = {
        "ward_number": str(orig_props.get("KGISWardNo", "35")),
        "ward_name": orig_props.get("KGISWardName", "Hemmigepura"),
        "ward_set": "243-ward BBMP Delimitation (2022 draft/KGIS)",
        "kgis_ward_id": orig_props.get("KGISWardID"),
        "kgis_ward_code": orig_props.get("KGISWardCode"),
        "lgd_ward_code": orig_props.get("LGD_WardCode"),
        "area_km2": area_km2,
        "centroid_pattanagere": {
            "lat": CENTROID_LAT,
            "lon": CENTROID_LON,
            "contains_verified": bool(contains_check)
        },
        "source": "DataMeet Municipal Spatial Data (Bangalore/BBMP.geojson)",
        "source_url": "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Bangalore/BBMP.geojson",
        "retrieval_date": retrieval_date,
        "note": "Pattanagere locality lies within this ward; ward boundary is larger than the locality."
    }

    out_fc = {
        "type": "FeatureCollection",
        "name": "study_area_hemmigepura_ward35",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": [
            {
                "type": "Feature",
                "properties": new_properties,
                "geometry": target_feature["geometry"]
            }
        ]
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out_fc, f, indent=2)

    print(f"Saved to: {OUT_PATH}")


if __name__ == "__main__":
    main()

