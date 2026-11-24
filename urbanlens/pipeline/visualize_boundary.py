"""
visualize_boundary.py – Renders the Pattanagere study-area boundary
on an OpenStreetMap basemap for visual confirmation.

The source of the boundary (OSM Nominatim lookup) is printed on the figure.
No unverified landmark labels are drawn.

Run:
    python pipeline/visualize_boundary.py

Output:
    reports/boundary_preview.png
"""

import json
import math
import sys
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import contextily as ctx
    HAS_CONTEXTILY = True
except ImportError:
    HAS_CONTEXTILY = False

try:
    import geopandas as gpd
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

REPO_ROOT   = Path(__file__).resolve().parent.parent
GEOJSON_PATH = REPO_ROOT / "data" / "study_area" / "pattanagere_boundary.geojson"
OUTPUT_PATH  = REPO_ROOT / "reports" / "boundary_preview.png"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def haversine_area_km2(coords: list) -> float:
    """
    Approximate geodesic area of a lon/lat closed ring (spherical excess).
    Returns area in km².
    """
    R = 6371.0
    n = len(coords)
    total = 0.0
    for i in range(n):
        x1, y1 = math.radians(coords[i][0]),      math.radians(coords[i][1])
        x2, y2 = math.radians(coords[(i+1)%n][0]), math.radians(coords[(i+1)%n][1])
        total += (x2 - x1) * (2 + math.sin(y1) + math.sin(y2))
    return abs(total) * R**2 / 2


def load_geojson(path: Path) -> dict:
    """Load and return the parsed GeoJSON FeatureCollection."""
    with open(path) as f:
        return json.load(f)


def print_summary(props: dict, area_km2: float, coords: list) -> None:
    """Print key boundary statistics to stdout."""
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    print("\n" + "="*65)
    print("  PATTANAGERE BOUNDARY SUMMARY")
    print("="*65)
    print(f"  OSM type     : {props.get('osm_type','?')}  (locality/quarter)")
    print(f"  OSM node     : {props.get('osm_node_url','?')}")
    print(f"  Boundary     : {props.get('boundary_type','?')}")
    print(f"  Centroid     : {props.get('centroid_lat')}°N, {props.get('centroid_lon')}°E")
    print(f"  Lon range    : {min(lons):.4f}° – {max(lons):.4f}° E")
    print(f"  Lat range    : {min(lats):.4f}° – {max(lats):.4f}° N")
    print(f"  Area         : ~{area_km2:.2f} km²")
    print(f"  Source       : {props.get('source','?')}")
    print(f"  Retrieved    : {props.get('retrieval_date','?')}")
    print(f"  Landmarks    : {props.get('landmarks_cited','NONE')}")
    print("="*65 + "\n")


def plot_figure(gj: dict, feature: dict, area_km2: float) -> None:
    """
    Generate a two-panel figure:
      Left : WGS-84 lon/lat view — centroid marker, bbox corners labelled.
      Right: Web Mercator with OSM basemap (if contextily available).
    Source is named in the figure footer.
    """
    props = feature["properties"]
    ring  = feature["geometry"]["coordinates"][0]
    lons  = [c[0] for c in ring]
    lats  = [c[1] for c in ring]
    clon  = props["centroid_lon"]
    clat  = props["centroid_lat"]

    source_label = (
        f"Source: {props.get('source','OSM Nominatim')} | "
        f"OSM node/{props.get('osm_node_id','')} type={props.get('osm_type','')} | "
        f"Retrieved: {props.get('retrieval_date','')[:10]}\n"
        f"Licence: {props.get('source_licence','ODbL 1.0')}\n"
        f"⚠ APPROXIMATE SQUARE (centroid ±0.01°) — DO NOT USE FOR GEE. Awaiting polygon definition."
    )
    bbox_note = (
        f"APPROXIMATE SQUARE (Placeholder)\n"
        f"S={props['bbox_south']:.4f}° N={props['bbox_north']:.4f}°\n"
        f"W={props['bbox_west']:.4f}° E={props['bbox_east']:.4f}°\n"
        f"Area ≈ {area_km2:.2f} km²"
    )

    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    fig.suptitle(
        "Pattanagere — UrbanLens AR  |  APPROXIMATE SQUARE PLACEHOLDER  |  STOPPED FOR DECISION",
        fontsize=12, fontweight="bold", color="#C0392B"
    )

    # ---- Left panel: WGS-84 ----
    ax = axes[0]
    ax.fill(lons, lats, color="#E63946", alpha=0.15)
    ax.plot(lons, lats, color="#E63946", linewidth=2.5, linestyle="--", label="Approximate Square (Placeholder)")
    # Centroid marker
    ax.scatter([clon], [clat], s=80, color="#2C3E50", zorder=6,
               label=f"OSM centroid\n({clat:.4f}°N, {clon:.4f}°E)")
    # Corner labels (bbox corners only — no unverified landmark names)
    corners = [(lons[0], lats[0]), (lons[1], lats[1]),
               (lons[2], lats[2]), (lons[3], lats[3])]
    for lon, lat in corners:
        ax.annotate(f"({lon:.4f}°E\n{lat:.4f}°N)", (lon, lat),
                    textcoords="offset points", xytext=(4, 4),
                    fontsize=7, color="#1D3557")
    ax.scatter([c[0] for c in corners], [c[1] for c in corners],
               s=25, color="#1D3557", zorder=5)
    ax.set_title("WGS-84 (lon/lat)", fontsize=10)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.legend(fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.text(0.02, 0.98, bbox_note, transform=ax.transAxes, fontsize=8,
            va="top", bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.7))

    # ---- Right panel: Web Mercator + basemap ----
    ax2 = axes[1]
    if HAS_GEOPANDAS:
        import geopandas as gpd
        gdf = gpd.GeoDataFrame.from_features(gj["features"], crs="EPSG:4326")
        gdf_m = gdf.to_crs(epsg=3857)
        gdf_m.boundary.plot(ax=ax2, color="#E63946", linewidth=2.5)
        gdf_m.plot(ax=ax2, color="#E63946", alpha=0.15)
        # Centroid
        from shapely.geometry import Point
        c_gdf = gpd.GeoDataFrame(geometry=[Point(clon, clat)], crs="EPSG:4326").to_crs(3857)
        c_gdf.plot(ax=ax2, color="#2C3E50", markersize=60, zorder=6)
        if HAS_CONTEXTILY:
            try:
                import socket
                socket.setdefaulttimeout(10)
                ctx.add_basemap(ax2, source=ctx.providers.CartoDB.Positron, zoom=14)
                ax2.set_title("Web Mercator + Basemap", fontsize=10)
            except Exception as e:
                ax2.set_title("Web Mercator (basemap fetch skipped)", fontsize=10)
                ax2.set_facecolor("#eaeaea")
        else:
            ax2.set_title("Web Mercator (no contextily)", fontsize=10)
        ax2.set_xlabel("Easting (m)")
        ax2.set_ylabel("Northing (m)")
    else:
        ax2.text(0.5, 0.5, "GeoPandas not installed\n(install geopandas contextily)",
                 transform=ax2.transAxes, ha="center", va="center", fontsize=11)
        ax2.set_title("OSM basemap (unavailable)", fontsize=10)

    # Footer with full source citation
    fig.text(0.01, 0.01, source_label, fontsize=7.5, va="bottom",
             bbox=dict(boxstyle="round", facecolor="#FDFEFE", alpha=0.8))

    fig.tight_layout(rect=[0, 0.08, 1, 0.97])
    fig.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ Preview saved → {OUTPUT_PATH}")


def main() -> None:
    """Load OSM-sourced boundary, print stats, and save a visual preview."""
    gj = load_geojson(GEOJSON_PATH)
    feature = gj["features"][0]
    ring = feature["geometry"]["coordinates"][0]
    props = feature["properties"]
    area_km2 = haversine_area_km2(ring)

    print_summary(props, area_km2, ring)

    if not HAS_MATPLOTLIB:
        print("⚠  matplotlib not installed — skipping plot.")
        sys.exit(0)

    plot_figure(gj, feature, area_km2)


if __name__ == "__main__":
    main()
