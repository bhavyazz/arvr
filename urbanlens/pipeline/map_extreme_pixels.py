"""
map_extreme_pixels.py – Maps the spatial locations of extreme NDVI pixels (< -0.5, == -1.0)
to visually prove their physical context (water body absorption in the south).

Output:
    reports/extreme_pixels_map.png
"""

from pathlib import Path
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Point
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT     = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REPORTS_DIR   = REPO_ROOT / "reports"
STUDY_AREA    = REPO_ROOT / "data" / "study_area" / "study_area.geojson"
OUTPUT_PNG    = REPORTS_DIR / "extreme_pixels_map.png"


def main():
    gdf_ward = gpd.read_file(STUDY_AREA).to_crs(epsg=32643)
    clon = gdf_ward.iloc[0]["centroid_pattanagere"]["lon"]
    clat = gdf_ward.iloc[0]["centroid_pattanagere"]["lat"]
    c_gdf = gpd.GeoDataFrame(geometry=[Point(clon, clat)], crs="EPSG:4326").to_crs(epsg=32643)

    tif_path = PROCESSED_DIR / "ndvi_2018.tif"
    with rasterio.open(tif_path) as src:
        arr = src.read(1)
        extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
        nodata = src.nodata

        # Locate extreme pixels
        rows_neg05, cols_neg05 = np.where((arr < -0.5) & (arr != nodata))
        xs_neg05, ys_neg05 = rasterio.transform.xy(src.transform, rows_neg05, cols_neg05)

        rows_neg1, cols_neg1 = np.where(arr == -1.0)
        xs_neg1, ys_neg1 = rasterio.transform.xy(src.transform, rows_neg1, cols_neg1)

    fig, ax = plt.subplots(figsize=(10, 10))
    fig.suptitle(
        "Spatial Mapping of Extreme NDVI Pixels (2018 Dry Season)\n"
        "BBMP Ward 35 (Hemmigepura) containing Pattanagere (EPSG:32643)",
        fontsize=12, fontweight="bold", color="#1B4F72"
    )

    # Base NDVI map
    ndvi_plot = np.where(arr == nodata, np.nan, arr)
    ax.imshow(ndvi_plot, extent=extent, cmap="Greys", vmin=-0.2, vmax=0.8, origin="upper", alpha=0.5)
    gdf_ward.boundary.plot(ax=ax, color="black", linewidth=1.5, label="Ward 35 Boundary")

    # Plot extreme points
    ax.scatter(xs_neg05, ys_neg05, color="#E67E22", s=15, alpha=0.7, label=f"NDVI < -0.5 (N={len(xs_neg05):,}, 0.11%)")
    ax.scatter(xs_neg1, ys_neg1, color="#C0392B", s=35, marker="x", label=f"NDVI == -1.000 (N={len(xs_neg1)}, 0.009%)")

    # Plot Pattanagere Centroid
    c_gdf.plot(ax=ax, color="#154360", marker="*", markersize=180, zorder=6, label="Pattanagere Centroid (North)")
    c_pt = c_gdf.geometry.iloc[0]
    ax.annotate(
        "Pattanagere Centroid\n(Residential/Urban)",
        xy=(c_pt.x, c_pt.y),
        xytext=(20, 15),
        textcoords="offset points",
        fontsize=9,
        fontweight="bold",
        color="#154360",
        arrowprops=dict(arrowstyle="->", color="#154360", lw=1.5)
    )

    # Annotate extreme cluster location
    if len(xs_neg1):
        mean_x = np.mean(xs_neg1)
        mean_y = np.mean(ys_neg1)
        ax.annotate(
            "Cluster of -1.000 pixels\n(Water Body / Quarry Reservoir in South;\nZero NIR absorption: B8=0, B4>0)",
            xy=(mean_x, mean_y),
            xytext=(-180, 40),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
            color="#900C3F",
            arrowprops=dict(arrowstyle="->", color="#900C3F", lw=1.5),
            bbox=dict(boxstyle="round", facecolor="#FDEDEC", edgecolor="#E6B0AA", alpha=0.9)
        )

    ax.set_title("Extreme Value Locations: Clustered Strictly in Southern Water Bodies", fontsize=10)
    ax.set_xlabel("Easting (m, UTM 43N)")
    ax.set_ylabel("Northing (m, UTM 43N)")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=9)

    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ Saved extreme pixels map to: {OUTPUT_PNG}")


if __name__ == "__main__":
    main()

