"""
visualize_study_area.py – Renders the extracted study area ward polygon
with the Pattanagere centroid marked.

Output:
    reports/study_area_preview.png
"""

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point

try:
    import contextily as ctx
    HAS_CONTEXTILY = True
except ImportError:
    HAS_CONTEXTILY = False

REPO_ROOT     = Path(__file__).resolve().parent.parent
GEOJSON_PATH  = REPO_ROOT / "data" / "study_area" / "study_area.geojson"
OUTPUT_PATH   = REPO_ROOT / "reports" / "study_area_preview.png"


def main():
    gdf = gpd.read_file(GEOJSON_PATH)
    props = gdf.iloc[0]

    centroid_pt = Point(props["centroid_pattanagere"]["lon"], props["centroid_pattanagere"]["lat"])
    c_gdf = gpd.GeoDataFrame(geometry=[centroid_pt], crs="EPSG:4326")

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle(
        f"Study Area: BBMP Ward {props['ward_number']} – {props['ward_name']} ({props['ward_set']})\n"
        f"Containing Pattanagere Centroid | Area: {props['area_km2']:.2f} km²",
        fontsize=12, fontweight="bold", color="#1B4F72"
    )

    # 1. Left Panel: WGS-84 coordinates
    ax1 = axes[0]
    gdf.boundary.plot(ax=ax1, color="#2E86C1", linewidth=2.0, label=f"Ward {props['ward_number']} Boundary")
    gdf.plot(ax=ax1, color="#2E86C1", alpha=0.15)
    c_gdf.plot(ax=ax1, color="#C0392B", markersize=90, marker="*", label="Pattanagere Centroid (OSM)")

    clon = props["centroid_pattanagere"]["lon"]
    clat = props["centroid_pattanagere"]["lat"]
    ax1.annotate(
        f"Pattanagere Centroid\n({clat:.4f}°N, {clon:.4f}°E)",
        xy=(clon, clat),
        xytext=(15, 15),
        textcoords="offset points",
        fontsize=9,
        fontweight="bold",
        color="#922B21",
        arrowprops=dict(arrowstyle="->", color="#922B21", lw=1.5)
    )

    ax1.set_title("WGS-84 Coordinate View", fontsize=11)
    ax1.set_xlabel("Longitude (°E)")
    ax1.set_ylabel("Latitude (°N)")
    ax1.legend(loc="lower right")
    ax1.grid(True, linestyle="--", alpha=0.4)

    # 2. Right Panel: Web Mercator with Basemap
    ax2 = axes[1]
    gdf_m = gdf.to_crs(epsg=3857)
    c_gdf_m = c_gdf.to_crs(epsg=3857)

    gdf_m.boundary.plot(ax=ax2, color="#1B4F72", linewidth=2.2, label=f"Ward {props['ward_number']} ({props['ward_name']})")
    gdf_m.plot(ax=ax2, color="#2E86C1", alpha=0.12)
    c_gdf_m.plot(ax=ax2, color="#C0392B", markersize=120, marker="*", zorder=5, label="Pattanagere Centroid")

    if HAS_CONTEXTILY:
        try:
            import socket
            socket.setdefaulttimeout(15)
            ctx.add_basemap(ax2, source=ctx.providers.OpenStreetMap.Mapnik, zoom=13)
            ax2.set_title("Web Mercator + OSM Basemap", fontsize=11)
        except Exception:
            ax2.set_title("Web Mercator Projection", fontsize=11)
            ax2.set_facecolor("#f5f5f5")
    else:
        ax2.set_title("Web Mercator Projection", fontsize=11)

    ax2.set_xlabel("Easting (m)")
    ax2.set_ylabel("Northing (m)")
    ax2.legend(loc="lower right")

    # Add explanatory note in footer
    footer_text = (
        f"Ward: No. {props['ward_number']} - {props['ward_name']} | Set: {props['ward_set']} | Area: {props['area_km2']:.2f} km²\n"
        f"Note: {props['note']}\n"
        f"Source: {props['source']} | Retrieval Date: {props['retrieval_date']}"
    )
    fig.text(
        0.02, 0.02, footer_text, fontsize=8, va="bottom",
        bbox=dict(boxstyle="round", facecolor="#EBF5FB", edgecolor="#AED6F1", alpha=0.9)
    )

    fig.tight_layout(rect=[0, 0.08, 1, 0.95])
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Preview saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

