"""
fetch_boundary.py – Retrieves the Pattanagere boundary from the
OpenStreetMap Nominatim API and saves it as GeoJSON.

Usage:
    python pipeline/fetch_boundary.py

What it does:
1. Queries Nominatim for "Pattanagere, Bengaluru, Karnataka, India"
   with polygon_geojson=1 so OSM returns the actual polygon (if one exists).
2. Prints every candidate result so we can inspect OSM type/class.
3. Saves the best match (admin boundary or locality polygon) to
   data/study_area/pattanagere_boundary.geojson, annotated with
   the OSM place_id, type, class, and retrieval timestamp.
4. If OSM only returns a bounding box (no polygon ring), it saves that
   as a rectangular polygon and flags it as "bbox_only" in properties.

Sources tried (in order):
  a. Nominatim polygon   – preferred; exact OSM boundary
  b. Nominatim bounding box – fallback; rectangular approximation
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

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# OSM usage policy: identify your application in User-Agent
HEADERS = {
    "User-Agent": "UrbanLens-AR/1.0 (academic project, RV College of Engineering)",
    "Accept-Language": "en",
}

QUERIES = [
    "Pattanagere, Bengaluru, Karnataka, India",
    "Pattanagere ward, Bangalore Urban, Karnataka, India",
    "Pattanagere, Bangalore, India",
]


def nominatim_search(query: str, polygon: bool = True) -> list:
    """
    Call Nominatim search endpoint and return parsed JSON list.

    Args:
        query:   Free-text place query.
        polygon: If True, request polygon_geojson=1.
    Returns:
        List of result dicts from Nominatim.
    """
    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "extratags": 1,
        "limit": 10,
    }
    if polygon:
        params["polygon_geojson"] = 1

    url = NOMINATIM_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def bbox_to_polygon(boundingbox: list) -> dict:
    """
    Convert Nominatim bounding box [S, N, W, E] to a GeoJSON Polygon ring.

    Args:
        boundingbox: [south_lat, north_lat, west_lon, east_lon] as strings.
    Returns:
        GeoJSON Polygon geometry dict.
    """
    s, n, w, e = [float(x) for x in boundingbox]
    return {
        "type": "Polygon",
        "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
    }


def haversine_area_km2(coords: list) -> float:
    """
    Approximate geodesic area of a lon/lat polygon using spherical excess.

    Args:
        coords: List of [lon, lat] pairs forming a closed ring.
    Returns:
        Area in km².
    """
    R = 6371.0
    n = len(coords)
    total = 0.0
    for i in range(n):
        x1 = math.radians(coords[i][0])
        y1 = math.radians(coords[i][1])
        x2 = math.radians(coords[(i + 1) % n][0])
        y2 = math.radians(coords[(i + 1) % n][1])
        total += (x2 - x1) * (2 + math.sin(y1) + math.sin(y2))
    return abs(total) * R ** 2 / 2


def pick_best_result(results: list) -> dict | None:
    """
    Score results and return the best match for Pattanagere.

    Preference order:
      1. osm_type=relation + place class = suburb/neighbourhood/quarter/ward
      2. osm_type=way   + same classes
      3. osm_type=node  (point only — least useful, but we record it)

    Args:
        results: Raw Nominatim result list.
    Returns:
        Best result dict, or None.
    """
    priority = {"relation": 0, "way": 1, "node": 2}
    good_classes = {"suburb", "neighbourhood", "quarter", "residential",
                    "administrative", "place", "boundary"}

    def score(r):
        type_score = priority.get(r.get("osm_type", "node"), 3)
        class_score = 0 if r.get("type") in good_classes else 1
        # Prefer results whose display name mentions Pattanagere
        name_score = 0 if "pattanagere" in r.get("display_name", "").lower() else 1
        return (name_score, class_score, type_score)

    scored = sorted(results, key=score)
    return scored[0] if scored else None


def main() -> None:
    """Fetch, evaluate, and save the Pattanagere OSM boundary."""
    all_results = []
    retrieval_ts = datetime.now(timezone.utc).isoformat()

    print("\n" + "=" * 65)
    print("  NOMINATIM BOUNDARY FETCH – Pattanagere, Bengaluru")
    print("=" * 65)

    for query in QUERIES:
        print(f"\n→ Querying: {query!r}")
        try:
            results = nominatim_search(query, polygon=True)
            time.sleep(1)  # OSM rate-limit: ≤ 1 req/s
        except Exception as exc:
            print(f"  ✗ Request failed: {exc}")
            continue

        print(f"  Got {len(results)} result(s):")
        for r in results:
            geom_type = r.get("geojson", {}).get("type", "none")
            print(
                f"    OSM {r.get('osm_type','?')}/{r.get('osm_id','?')} | "
                f"class={r.get('class','?')} type={r.get('type','?')} | "
                f"geom={geom_type} | {r.get('display_name','')[:70]}"
            )
        all_results.extend(results)

    if not all_results:
        print("\n✗ No results from Nominatim. Check network connectivity.")
        sys.exit(1)

    best = pick_best_result(all_results)
    if best is None:
        print("\n✗ Could not select a best result.")
        sys.exit(1)

    print(f"\n★ Selected: OSM {best.get('osm_type')}/{best.get('osm_id')}")
    print(f"  Display name : {best.get('display_name')}")
    print(f"  class/type   : {best.get('class')} / {best.get('type')}")

    # -----------------------------------------------------------------
    # Build geometry
    # -----------------------------------------------------------------
    geom = best.get("geojson")
    bbox_only = False

    if geom and geom.get("type") in ("Polygon", "MultiPolygon"):
        print(f"  Geometry     : {geom['type']} from OSM polygon_geojson ✓")
        boundary_type = "OSM polygon"
    else:
        print("  ⚠ No polygon geometry — falling back to bounding box.")
        geom = bbox_to_polygon(best["boundingbox"])
        bbox_only = True
        boundary_type = "OSM bounding box (rectangular approximation)"

    # Compute area from the outer ring
    if geom["type"] == "Polygon":
        ring = geom["coordinates"][0]
    else:  # MultiPolygon — use the largest ring
        ring = max(geom["coordinates"], key=lambda p: haversine_area_km2(p[0]))[0]

    area_km2 = haversine_area_km2(ring)

    # -----------------------------------------------------------------
    # Assemble GeoJSON FeatureCollection
    # -----------------------------------------------------------------
    addr = best.get("address", {})
    feature = {
        "type": "Feature",
        "properties": {
            "name": best.get("name", "Pattanagere"),
            "display_name": best.get("display_name", ""),
            "osm_type": best.get("osm_type"),
            "osm_id": best.get("osm_id"),
            "osm_class": best.get("class"),
            "osm_place_type": best.get("type"),
            "boundary_type": boundary_type,
            "bbox_only": bbox_only,
            "area_approx_km2": round(area_km2, 3),
            "city": addr.get("city") or addr.get("town") or addr.get("village", ""),
            "state": addr.get("state", ""),
            "country": addr.get("country", ""),
            "source": "OpenStreetMap via Nominatim API",
            "source_url": (
                f"https://www.openstreetmap.org/"
                f"{best.get('osm_type','')}/{best.get('osm_id','')}"
            ),
            "retrieval_date": retrieval_ts,
            "retrieved_by": "UrbanLens pipeline – fetch_boundary.py Phase 1 Step 1 (revised)",
            "note": (
                "Boundary sourced directly from OpenStreetMap via Nominatim. "
                "No landmark labels have been added. "
                "OSM place type determines whether this is a locality, "
                "suburb, ward, or bounding-box approximation — see boundary_type field."
            ),
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

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------
    bb = best.get("boundingbox", [])
    print(f"\n  Boundary type: {boundary_type}")
    print(f"  OSM bbox     : S={bb[0]} N={bb[1]} W={bb[2]} E={bb[3]}")
    print(f"  Area         : ~{area_km2:.2f} km²  (~{area_km2*100:.0f} ha)")
    print(f"\n✓ Saved → {OUT_PATH}")
    print("=" * 65 + "\n")

    # Write summary to a small sidecar for decisions.md update
    sidecar = OUT_PATH.with_suffix(".fetch_meta.json")
    with open(sidecar, "w") as f:
        json.dump({
            "osm_type": best.get("osm_type"),
            "osm_id": best.get("osm_id"),
            "osm_class": best.get("class"),
            "osm_place_type": best.get("type"),
            "display_name": best.get("display_name"),
            "boundary_type": boundary_type,
            "bbox_only": bbox_only,
            "area_km2": round(area_km2, 3),
            "retrieval_date": retrieval_ts,
        }, f, indent=2)
    print(f"  Metadata sidecar → {sidecar}")


if __name__ == "__main__":
    main()

