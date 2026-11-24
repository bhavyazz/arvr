"""
overpass_retry.py – Query Overpass API for Pattanagere boundary relations/ways
with automatic retry on timeout or 5xx errors.

Tries multiple endpoint mirrors and multiple query strategies.
Prints all found elements and their geometry types.

Run:
    python pipeline/overpass_retry.py
"""

import json
import time
import urllib.request
import urllib.parse
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_META  = REPO_ROOT / "data" / "study_area" / "overpass_result.json"

# Overpass endpoint mirrors (try in order)
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

HEADERS = {
    "User-Agent": "UrbanLens-AR/1.0 (academic, RV College of Engineering)",
    "Content-Type": "application/x-www-form-urlencoded",
}

# --- Queries: from most specific to broadest ---
QUERIES = {
    "admin_boundary_relations": """
[out:json][timeout:40];
(
  relation["boundary"="administrative"]["name"~"[Pp]attanagere"]
    (12.85,77.45,12.95,77.56);
  relation["boundary"="administrative"]["name:en"~"[Pp]attanagere"]
    (12.85,77.45,12.95,77.56);
);
out body;
>;
out skel qt;
""",

    "place_quarter_relations": """
[out:json][timeout:40];
(
  relation["place"~"quarter|suburb|neighbourhood"]["name"~"[Pp]attanagere"]
    (12.85,77.45,12.95,77.56);
  way["place"~"quarter|suburb|neighbourhood"]["name"~"[Pp]attanagere"]
    (12.85,77.45,12.95,77.56);
);
out body;
>;
out skel qt;
""",

    "any_named_pattanagere_relations": """
[out:json][timeout:40];
(
  relation["name"~"[Pp]attanagere"]["type"~"boundary|multipolygon|public_transport"]
    (12.85,77.45,12.95,77.56);
  relation["name"~"[Pp]attanagere"]
    (12.85,77.45,12.95,77.56);
);
out body;
>;
out skel qt;
""",

    "bbmp_ward_admin_level": """
[out:json][timeout:40];
(
  relation["boundary"="administrative"]["admin_level"~"^(8|9|10|11)$"]
    (12.88,77.47,12.95,77.54);
);
out body;
""",
}

MAX_RETRIES = 4
RETRY_WAIT  = [5, 10, 20, 40]   # seconds between retries


def post_query(endpoint: str, ql: str, timeout: int = 50) -> dict:
    """
    POST an Overpass QL query to the given endpoint.
    Returns parsed JSON on success, raises on HTTP/network error.
    """
    data = urllib.parse.urlencode({"data": ql}).encode()
    req  = urllib.request.Request(endpoint, data=data, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def run_with_retry(ql_name: str, ql: str) -> dict | None:
    """
    Try each Overpass mirror with exponential backoff.
    Returns the first successful parsed JSON, or None.
    """
    for attempt, endpoint in enumerate(ENDPOINTS * 2):   # 2 passes through mirrors
        wait = RETRY_WAIT[min(attempt, len(RETRY_WAIT)-1)]
        print(f"  [{ql_name}] attempt {attempt+1}: {endpoint.split('/')[2]} ... ", end="", flush=True)
        try:
            result = post_query(endpoint, ql, timeout=55)
            print("OK")
            return result
        except Exception as exc:
            print(f"FAILED ({exc})")
            if attempt < MAX_RETRIES * len(ENDPOINTS) - 1:
                print(f"    Waiting {wait}s before retry ...")
                time.sleep(wait)
    return None


def summarise_elements(elements: list, label: str) -> None:
    """Print a human-readable summary of Overpass elements."""
    print(f"\n  Results for '{label}': {len(elements)} element(s)")
    for el in elements:
        t  = el.get("type", "?")
        eid = el.get("id", "?")
        tags = el.get("tags", {})
        # nodes inside a way/relation will have no tags — skip those
        if not tags and t in ("node", "way"):
            continue
        geom = "geometry" if "geometry" in el else ("members" if "members" in el else "none")
        print(f"    {t}/{eid} | name={tags.get('name','—')} | "
              f"boundary={tags.get('boundary','—')} | "
              f"admin_level={tags.get('admin_level','—')} | "
              f"place={tags.get('place','—')} | "
              f"geom={geom}")


def main():
    retrieval_ts = datetime.now(timezone.utc).isoformat()
    print("\n" + "="*65)
    print("  OVERPASS RETRY – Pattanagere boundary relations/ways")
    print(f"  Started: {retrieval_ts}")
    print("="*65)

    all_elements = []
    found_polygon_elements = []

    for name, ql in QUERIES.items():
        print(f"\n--- Query: {name} ---")
        result = run_with_retry(name, ql)
        if result is None:
            print(f"  All retries failed for '{name}'.")
            continue
        elements = result.get("elements", [])
        summarise_elements(elements, name)
        all_elements.extend(elements)

        # Check for elements that could carry polygon geometry
        for el in elements:
            tags = el.get("tags", {})
            if not tags:
                continue
            name_val = tags.get("name", "")
            if "pattanagere" in name_val.lower() or "pattanagere" in name_val.lower():
                found_polygon_elements.append(el)
        time.sleep(2)   # polite gap between queries

    print("\n" + "="*65)
    print(f"  Total elements across all queries : {len(all_elements)}")
    print(f"  Named 'Pattanagere' elements      : {len(found_polygon_elements)}")
    print("="*65)

    # Save raw results for inspection
    out = {
        "retrieval_date": retrieval_ts,
        "queries_run": list(QUERIES.keys()),
        "total_elements": len(all_elements),
        "pattanagere_named_elements": found_polygon_elements,
        "all_elements": all_elements,
    }
    OUT_META.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_META, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n✓ Raw results saved → {OUT_META}")


if __name__ == "__main__":
    main()

