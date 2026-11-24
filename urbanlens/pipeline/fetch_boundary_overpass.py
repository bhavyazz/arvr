"""
fetch_boundary_overpass.py – Secondary boundary fetch using the
Overpass API to search for administrative ward/boundary relations
that contain "Pattanagere" in the Bengaluru area.

Also retrieves the OSM node centroid for the Pattanagere quarter
and builds a bbox from its surroundings.

Run:
    python pipeline/fetch_boundary_overpass.py
"""

import json
import math
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "data" / "study_area" / "pattanagere_boundary.geojson"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
META_PATH = OUT_PATH.with_suffix(".fetch_meta.json")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {
    "User-Agent": "UrbanLens-AR/1.0 (academic project, RV College of Engineering)",
    "Content-Type": "application/x-www-form-urlencoded",
}

# OSM node ID for Pattanagere quarter (from Nominatim result)
PATTANAGERE_NODE_ID = 1588150123

# Overpass queries to try
QUERIES = {
    "node_coords": f"""
[out:json][timeout:25];
node({PATTANAGERE_NODE_ID});
out body;
""",
    "admin_relations_near": """
[out:json][timeout:30];
(
  relation["boundary"="administrative"]["name"~"Pattanagere",i]
    (12.88,77.47,12.95,77.54);
  relation["place"]["name"~"Pattanagere",i]
    (12.88,77.47,12.95,77.54);
  relation["boundary"="administrative"]["name"~"Pattanagere",i];
);
out body;
""",
    "bbmp_ward_relations": """
[out:json][timeout:30];
(
  relation["boundary"="administrative"]["admin_level"~"9|10|11"]
    ["name"~"Pattanagere",i]
    (12.88,77.47,12.95,77.54);
);
out body;
""",
}


def overpass_query(ql: str) -> dict:
    """
    POST a query to the Overpass API and return parsed JSON.

    Args:
        ql: Overpass QL query string.
    Returns:
        Parsed JSON response dict.
    """
    data = urllib.parse.urlencode({"data": ql}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=35) as resp:
        return json.loads(resp.read().decode())


def haversine_area_km2(coords: list) -> float:
    """
    Approximate geodesic area of a lon/lat closed ring using spherical excess.
    """
    R = 6371.0
    n = len(coords)
    total = 0.0
    for i in range(n):
        x1, y1 = math.radians(coords[i][0]), math.radians(coords[i][1])
        x2, y2 = math.radians(coords[(i+1)%n][0]), math.radians(coords[(i+1)%n][1])
        total += (x2 - x1) * (2 + math.sin(y1) + math.sin(y2))
    return abs(total) * R**2 / 2


def main():
    """Fetch Pattanagere boundary via Overpass; fall back to centroid+bbox."""
    retrieval_ts = datetime.now(timezone.utc).isoformat()

    print("\n" + "=" * 65)
    print("  OVERPASS API BOUNDARY FETCH – Pattanagere, Bengaluru")
    print("=" * 65)

    # ------------------------------------------------------------------
    # Step 1: Get the OSM node coordinates (the named Pattanagere quarter)
    # ------------------------------------------------------------------
    print("\n[1] Fetching OSM node coords for node/1588150123 ...")
    centroid_lon, centroid_lat = None, None
    node_tags = {}
    try:
        r = overpass_query(QUERIES["node_coords"])
        time.sleep(1)
        elements = r.get("elements", [])
        if elements:
            el = elements[0]
            centroid_lat = el.get("lat")
            centroid_lon = el.get("lon")
            node_tags = el.get("tags", {})
            print(f"    Node lat={centroid_lat}, lon={centroid_lon}")
            print(f"    Tags: {node_tags}")
        else:
            print("    No element returned.")
    except Exception as exc:
        print(f"    ✗ Failed: {exc}")

    # ------------------------------------------------------------------
    # Step 2: Look for admin relations near Pattanagere
    # ------------------------------------------------------------------
    print("\n[2] Searching for administrative boundary relations ...")
    found_relation = None
    for qname in ("admin_relations_near", "bbmp_ward_relations"):
        try:
            r = overpass_query(QUERIES[qname])
            time.sleep(1)
            elements = r.get("elements", [])
            print(f"    Query '{qname}': {len(elements)} element(s)")
            for el in elements:
                tags = el.get("tags", {})
                print(f"      type={el.get('type')} id={el.get('id')} "
                      f"name={tags.get('name','?')} "
                      f"admin_level={tags.get('admin_level','?')} "
                      f"place={tags.get('place','?')}")
                if found_relation is None:
                    found_relation = el
        except Exception as exc:
            print(f"    ✗ Query '{qname}' failed: {exc}")

    # ------------------------------------------------------------------
    # Step 3: Decide geometry source
    # ------------------------------------------------------------------
    bbox_only = True
    boundary_description = ""
    boundary_type = ""
    geom = None

    if found_relation:
        print(f"\n★ Found OSM relation for Pattanagere: {found_relation}")
        # Relations from Overpass body output don't include geometry;
        # we'd need a second 'out geom;' call. Flag for user.
        boundary_description = (
            "OSM administrative relation found — geometry not auto-fetched. "
            "See OSM relation ID in source_url."
        )
        boundary_type = "OSM administrative relation (geometry pending manual fetch)"
        bbox_only = True  # still need manual step
    else:
        print("\n  No administrative polygon found in OSM/Overpass for Pattanagere.")
        print("  → Pattanagere is mapped in OSM as a named place node (type=quarter),")
        print("    not as an administrative ward boundary polygon.")
        boundary_type = (
            "OSM-centred bounding box — Pattanagere is a named locality node "
            "(OSM type=quarter) with no polygon in OSM. "
            "Bounding box is derived from the node centroid ±~1.5 km, "
            "sized to encompass the known residential extent of the locality."
        )
        boundary_description = (
            "No polygon exists in OSM for Pattanagere. This boundary is a "
            "rectangular bounding box centred on the OSM node for Pattanagere "
            "(node/1588150123, type=quarter, lat={}, lon={}). "
            "It is an approximation and must be confirmed against local knowledge."
        ).format(centroid_lat, centroid_lon)

    # Build the bounding box geometry from centroid if no polygon found
    if centroid_lat and centroid_lon and not found_relation:
        # ~1.4 km radius box, appropriate for a dense urban locality in Bengaluru
        # 0.013 deg lat ≈ 1.44 km; 0.016 deg lon ≈ 1.56 km at 12.9°N
        d_lat = 0.013
        d_lon = 0.016
        lat, lon = centroid_lat, centroid_lon
        ring = [
            [lon - d_lon, lat - d_lat],
            [lon + d_lon, lat - d_lat],
            [lon + d_lon, lat + d_lat],
            [lon - d_lon, lat + d_lat],
            [lon - d_lon, lat - d_lat],
        ]
        geom = {"type": "Polygon", "coordinates": [ring]}
        area_km2 = haversine_area_km2(ring)
        bbox_only = True
    else:
        # Last resort: known rough location if node fetch also failed
        centroid_lat = centroid_lat or 12.9165
        centroid_lon = centroid_lon or 12.9141
        d_lat, d_lon = 0.013, 0.016
        lat, lon = centroid_lat, centroid_lon
        ring = [
            [lon - d_lon, lat - d_lat],
            [lon + d_lon, lat - d_lat],
            [lon + d_lon, lat + d_lat],
            [lon - d_lon, lat + d_lat],
            [lon - d_lon, lat - d_lat],
        ]
        geom = {"type": "Polygon", "coordinates": [ring]}
        area_km2 = haversine_area_km2(ring)

    # ------------------------------------------------------------------
    # Step 4: Assemble and save GeoJSON
    # ------------------------------------------------------------------
    feature = {
        "type": "Feature",
        "properties": {
            "name": "Pattanagere",
            "osm_node_id": PATTANAGERE_NODE_ID,
            "osm_node_type": node_tags.get("place", "quarter"),
            "osm_node_lat": centroid_lat,
            "osm_node_lon": centroid_lon,
            "osm_node_name": node_tags.get("name", "Pattanagere"),
            "osm_node_name_kn": node_tags.get("name:kn", ""),
            "boundary_type": boundary_type,
            "bbox_only": bbox_only,
            "area_approx_km2": round(area_km2, 3) if geom else None,
            "source": "OpenStreetMap via Overpass API + Nominatim",
            "osm_node_url": f"https://www.openstreetmap.org/node/{PATTANAGERE_NODE_ID}",
            "overpass_query_url": "https://overpass-api.de/api/interpreter",
            "retrieval_date": retrieval_ts,
            "note": boundary_description,
            "landmarks_cited": "NONE — no unverified landmark labels added",
            "status": "AWAITING_USER_CONFIRMATION",
        },
        "geometry": geom,
    }

    fc = {
        "type": "FeatureCollection",
        "name": "pattanagere_boundary",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": [feature],
    }

    with open(OUT_PATH, "w") as f:
        json.dump(fc, f, indent=2)

    # Save metadata sidecar
    meta = {
        "osm_node_id": PATTANAGERE_NODE_ID,
        "centroid_lat": centroid_lat,
        "centroid_lon": centroid_lon,
        "node_tags": node_tags,
        "admin_relation_found": found_relation is not None,
        "bbox_only": bbox_only,
        "boundary_type": boundary_type,
        "area_km2": round(area_km2, 3) if geom else None,
        "retrieval_date": retrieval_ts,
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n  Bbox only  : {bbox_only}")
    print(f"  Area       : ~{area_km2:.2f} km²" if geom else "")
    print(f"\n✓ Saved → {OUT_PATH}")
    print(f"  Metadata  → {META_PATH}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()

