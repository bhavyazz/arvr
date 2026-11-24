"""Print nearby ward names and polygons from DataMeet files."""
import json
from pathlib import Path

data = Path(r"d:/ar_vr/urbanlens/data/study_area")
NEARBY = ["pattana","kengeri","rr ","rajaraje","uttara","mylas","hemmi","beml","bhel","mylasandra"]

for fname, label in [
    ("datameet_BBMP_new.geojson", "NEW 243-ward"),
    ("datameet_BBMP_old.geojson", "OLD 198-ward"),
]:
    gj = json.loads((data / fname).read_text(encoding="utf-8", errors="replace"))
    feats = gj["features"]
    print(f"\n--- {label} ({len(feats)} wards) ---")
    for f in feats:
        p    = f.get("properties") or {}
        name = str(p.get("KGISWardName") or p.get("WARD_NAME") or "")
        no   = str(p.get("KGISWardNo")   or p.get("WARD_NO")   or "")
        if any(s in name.lower() for s in NEARBY):
            geom  = f.get("geometry") or {}
            gtype = geom.get("type", "?")
            ring  = geom.get("coordinates", [[]])[0] if gtype == "Polygon" else []
            area  = p.get("AREA_SQ_KM", "?")
            lat   = p.get("LAT", "?")
            lon   = p.get("LON", "?")
            print(f"  Ward {no:>4}: {name!r}  geom={gtype}  verts={len(ring)}  area={area} km2  cen=({lat},{lon})")

