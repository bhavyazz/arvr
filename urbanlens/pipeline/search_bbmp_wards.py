"""
search_bbmp_wards.py – Search the DataMeet BBMP ward GeoJSON files for Pattanagere.

Prints matching ward features, extracts the polygon, and saves it as the
canonical study-area boundary if found.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data" / "study_area"
OUT_PATH  = DATA_DIR / "pattanagere_boundary.geojson"

SOURCES = [
    ("datameet_BBMP_new.geojson",  "DataMeet/BBMP.geojson (new ward delimitation)"),
    ("datameet_BBMP_old.geojson",  "DataMeet/BBMP_oldWards.geojson (pre-2022 wards)"),
]


def search_file(fname: str, label: str):
    """
    Load a BBMP GeoJSON file, print all property keys, and
    return any features whose properties contain 'pattanagere'.
    """
    path = DATA_DIR / fname
    gj   = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    features = gj.get("features", [])
    print(f"\n=== {label} ===")
    print(f"  Features total : {len(features)}")
    if features:
        keys = list(features[0].get("properties", {}).keys())
        print(f"  Property keys  : {keys}")

    hits = []
    for feat in features:
        props = feat.get("properties") or {}
        combined = " ".join(str(v) for v in props.values()).lower()
        if "pattanagere" in combined:
            hits.append(feat)

    print(f"  Pattanagere hits: {len(hits)}")
    for h in hits:
        print(f"    props: {h.get('properties')}")
        geom = h.get("geometry", {})
        gtype = geom.get("type", "none")
        ncoords = len(geom.get("coordinates", [[]])[0]) if gtype == "Polygon" else "?"
        print(f"    geom : {gtype} ({ncoords} vertices in outer ring)")
    return hits, gj.get("type"), features


def main():
    retrieval_ts = datetime.now(timezone.utc).isoformat()
    all_hits = []
    best_feature = None
    best_source  = None

    for fname, label in SOURCES:
        hits, fc_type, all_feats = search_file(fname, label)
        if hits and best_feature is None:
            best_feature = hits[0]
            best_source  = label

    print("\n" + "="*65)
    if best_feature:
        props = best_feature.get("properties", {})
        geom  = best_feature.get("geometry", {})
        gtype = geom.get("type", "?")
        print(f"FOUND: {gtype} in {best_source}")
        print(f"  Properties: {props}")
        print(f"  Geometry type: {gtype}")

        # Build the output GeoJSON
        # Annotate with provenance
        props["source"]           = "DataMeet Municipal Spatial Data GitHub repository"
        props["source_url"]       = "https://github.com/datameet/Municipal_Spatial_Data/tree/master/Bangalore"
        props["source_file"]      = best_source
        props["source_licence"]   = "Open data; original BBMP data"
        props["retrieval_date"]   = retrieval_ts
        props["retrieved_by"]     = "UrbanLens pipeline – search_bbmp_wards.py Phase 1 Step 1"
        props["boundary_type"]    = f"BBMP ward polygon from DataMeet ({best_source})"
        props["bbox_only"]        = False
        props["landmarks_cited"]  = "NONE"
        props["status"]           = "AWAITING_USER_CONFIRMATION"

        fc = {
            "type": "FeatureCollection",
            "name": "pattanagere_boundary",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "features": [best_feature],
        }
        with open(OUT_PATH, "w") as f:
            json.dump(fc, f, indent=2)
        print(f"\n✓ Saved polygon → {OUT_PATH}")
    else:
        print("NOT FOUND in either BBMP ward file.")
        print("Pattanagere may be named differently in the ward list.")
        print("Printing all ward names for manual inspection ...")

        # Print all ward names from the new file for manual inspection
        path = DATA_DIR / "datameet_BBMP_new.geojson"
        gj   = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        features = gj.get("features", [])
        all_names = set()
        for feat in features:
            props = feat.get("properties") or {}
            for k, v in props.items():
                if isinstance(v, str) and len(v) > 1:
                    all_names.add(v.strip())
        # Print names that contain common substrings from the area
        nearby = [n for n in sorted(all_names)
                  if any(sub in n.lower() for sub in
                         ["pattana", "kengeri", "rr nagar", "rajarajeshwari",
                          "uttarahalli", "mylas", "hemmige"])]
        print("\n  Nearby ward names:")
        for n in nearby:
            print(f"    {n!r}")


if __name__ == "__main__":
    main()

