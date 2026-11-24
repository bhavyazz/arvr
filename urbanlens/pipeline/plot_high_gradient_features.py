"""
plot_high_gradient_features.py – Visualizes high-gradient NDVI edges
to inspect for linear or straight-line seam artifacts versus real ground features.

Output:
    reports/ndvi_high_gradient_features.png
"""

from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage
import geopandas as gpd
from shapely.geometry import Point
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT     = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REPORTS_DIR   = REPO_ROOT / "reports"
STUDY_AREA    = REPO_ROOT / "data" / "study_area" / "study_area.geojson"
OUT_PNG       = REPORTS_DIR / "ndvi_high_gradient_features.png"


def analyze_year(year, ax, gdf_ward, c_gdf):
    tif_path = PROCESSED_DIR / f"ndvi_{year}.tif"
    with rasterio.open(tif_path) as src:
        arr = src.read(1)
        extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
        nodata = src.nodata

    valid_mask = (arr != nodata) & (~np.isnan(arr))
    # Erode the border by 2 pixels to avoid artificial step at the study area polygon boundary
    interior_mask = ndimage.binary_erosion(valid_mask, iterations=2)

    # Compute Sobel gradients
    gx = ndimage.sobel(arr, axis=1)
    gy = ndimage.sobel(arr, axis=0)
    grad_mag = np.hypot(gx, gy)
    grad_mag[~interior_mask] = 0

    # High-gradient threshold: 95th percentile of interior valid pixels
    threshold = np.percentile(grad_mag[interior_mask], 95)
    high_grad_mask = (grad_mag >= threshold) & interior_mask

    # Background grayscale NDVI
    ndvi_bg = np.where(valid_mask, arr, np.nan)
    ax.imshow(ndvi_bg, extent=extent, cmap="Greys_r", vmin=-0.1, vmax=0.7, origin="upper", alpha=0.6)

    # Highlight high-gradient pixels in bright red
    high_grad_plot = np.where(high_grad_mask, 1.0, np.nan)
    ax.imshow(high_grad_plot, extent=extent, cmap="autumn", origin="upper", vmin=0, vmax=1)

    gdf_ward.boundary.plot(ax=ax, color="blue", linewidth=1.2, label="Ward 35 Boundary")
    c_gdf.plot(ax=ax, color="darkgreen", marker="*", markersize=140, zorder=6, label="Pattanagere Centroid")

    c_pt = c_gdf.geometry.iloc[0]
    ax.annotate(
        "Pattanagere",
        xy=(c_pt.x, c_pt.y),
        xytext=(15, 10),
        textcoords="offset points",
        fontsize=9,
        fontweight="bold",
        color="darkgreen",
        arrowprops=dict(arrowstyle="->", color="darkgreen", lw=1.5)
    )

    ax.set_title(f"Year {year}: High-Gradient Pixels (≥ 95th percentile, |∇NDVI| ≥ {threshold:.2f})", fontsize=11, fontweight="bold")
    ax.set_xlabel("Easting (m, UTM 43N)")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower right", fontsize=8)


def main():
    gdf_ward = gpd.read_file(STUDY_AREA).to_crs(epsg=32643)
    clon = gdf_ward.iloc[0]["centroid_pattanagere"]["lon"]
    clat = gdf_ward.iloc[0]["centroid_pattanagere"]["lat"]
    c_gdf = gpd.GeoDataFrame(geometry=[Point(clon, clat)], crs="EPSG:4326").to_crs(epsg=32643)

    fig, axes = plt.subplots(1, 2, figsize=(18, 9))
    fig.suptitle(
        "Visual Inspection of High-Gradient NDVI Edges (Seam & Linear Feature Diagnostic)\n"
        "BBMP Ward 35 containing Pattanagere | EPSG:32643 (UTM 43N, 10m)",
        fontsize=12, fontweight="bold", color="#1B4F72"
    )

    analyze_year(2018, axes[0], gdf_ward, c_gdf)
    analyze_year(2025, axes[1], gdf_ward, c_gdf)

    axes[0].set_ylabel("Northing (m, UTM 43N)")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ Saved high gradient diagnostic map to: {OUT_PNG}")


if __name__ == "__main__":
    main()

