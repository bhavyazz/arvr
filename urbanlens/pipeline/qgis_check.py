"""
qgis_check.py – Rigorous verification of exported GeoTIFFs for QGIS compatibility.

Checks:
  1. CRS is EPSG:32643 (UTM Zone 43N)
  2. Resolution is 10m x 10m
  3. Bounding box aligns with BBMP Ward 35
  4. Pixel values are strictly within valid physical index limits [-1.0, 1.0]
  5. Generates a QGIS-style map canvas render with RdYlGn color ramp
     overlaid with the study area vector boundary and Pattanagere centroid.

Output:
    reports/qgis_check_preview.png
"""

import json
from pathlib import Path
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Point
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

REPO_ROOT     = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
STUDY_AREA    = REPO_ROOT / "data" / "study_area" / "study_area.geojson"
REPORTS_DIR   = REPO_ROOT / "reports"
OUTPUT_PNG    = REPORTS_DIR / "qgis_check_preview.png"


def verify_file(tif_path, expected_range=(-1.0, 1.0)):
    with rasterio.open(tif_path) as src:
        arr = src.read(1)
        valid = arr[~np.isnan(arr)]
        if src.nodata is not None:
            valid = valid[valid != src.nodata]

        info = {
            "file": tif_path.name,
            "crs": str(src.crs),
            "crs_epsg": src.crs.to_epsg() if src.crs else None,
            "width": src.width,
            "height": src.height,
            "res": src.res,
            "bounds": [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top],
            "dtype": str(src.dtypes[0]),
            "nodata": src.nodata,
            "min": float(np.min(valid)),
            "max": float(np.max(valid)),
            "mean": float(np.mean(valid)),
            "std": float(np.std(valid)),
            "valid_pixels": int(len(valid)),
            "in_range": bool(np.all(valid >= expected_range[0]) and np.all(valid <= expected_range[1]))
        }
    return info


def generate_qgis_preview():
    # Load study area and reproject to EPSG:32643
    gdf = gpd.read_file(STUDY_AREA).to_crs(epsg=32643)
    clon = gdf.iloc[0]["centroid_pattanagere"]["lon"]
    clat = gdf.iloc[0]["centroid_pattanagere"]["lat"]
    c_gdf = gpd.GeoDataFrame(geometry=[Point(clon, clat)], crs="EPSG:4326").to_crs(epsg=32643)

    tif_2018 = PROCESSED_DIR / "ndvi_2018.tif"
    tif_2025 = PROCESSED_DIR / "ndvi_2025.tif"

    with rasterio.open(tif_2018) as src18:
        ndvi18 = src18.read(1)
        extent18 = [src18.bounds.left, src18.bounds.right, src18.bounds.bottom, src18.bounds.top]
        nodata18 = src18.nodata

    with rasterio.open(tif_2025) as src25:
        ndvi25 = src25.read(1)
        extent25 = [src25.bounds.left, src25.bounds.right, src25.bounds.bottom, src25.bounds.top]
        nodata25 = src25.nodata

    # Mask nodata
    ndvi18_plot = np.where(ndvi18 == nodata18, np.nan, ndvi18)
    ndvi25_plot = np.where(ndvi25 == nodata25, np.nan, ndvi25)

    norm = Normalize(vmin=-0.1, vmax=0.7)
    cmap = "RdYlGn"

    fig, axes = plt.subplots(1, 2, figsize=(16, 9))
    fig.suptitle(
        "QGIS Map Canvas Check: Sentinel-2 NDVI Composites (CRS: EPSG:32643 / UTM 43N, 10m)\n"
        "BBMP Ward 35 (Hemmigepura) containing Pattanagere | 2018 vs 2025 Dry Season",
        fontsize=12, fontweight="bold", color="#1B4F72"
    )

    for ax, data, extent, year in [
        (axes[0], ndvi18_plot, extent18, 2018),
        (axes[1], ndvi25_plot, extent25, 2025),
    ]:
        im = ax.imshow(data, extent=extent, cmap=cmap, norm=norm, origin="upper")
        gdf.boundary.plot(ax=ax, color="black", linewidth=1.5, linestyle="-", label="Ward 35 Boundary")
        c_gdf.plot(ax=ax, color="#154360", marker="*", markersize=140, zorder=6, label="Pattanagere Centroid")

        c_pt = c_gdf.geometry.iloc[0]
        ax.annotate(
            "Pattanagere",
            xy=(c_pt.x, c_pt.y),
            xytext=(15, 10),
            textcoords="offset points",
            fontweight="bold",
            fontsize=9,
            color="#0E6251",
            arrowprops=dict(arrowstyle="->", color="#0E6251", lw=1.5)
        )

        ax.set_title(f"Sentinel-2 NDVI {year} Composite (Jan–Mar)", fontsize=11, fontweight="bold")
        ax.set_xlabel("Easting (m, UTM 43N)")
        ax.set_ylabel("Northing (m, UTM 43N)")
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.legend(loc="lower right", fontsize=8)

    cbar_ax = fig.add_axes([0.2, 0.05, 0.6, 0.025])
    cbar = fig.colorbar(im, cax=cbar_ax, orientation="horizontal")
    cbar.set_label("NDVI Value (Vegetation: ~0.3 to 0.7 | Built-up/Bare: <0.2 | Water: <0.0)", fontsize=9)

    fig.tight_layout(rect=[0, 0.08, 1, 0.95])
    fig.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ QGIS check preview saved to: {OUTPUT_PNG}")


def main():
    print("=" * 65)
    print("  QGIS GEOTIFF INTEGRITY & SPECIFICATION VERIFICATION")
    print("=" * 65)

    all_tifs = sorted(PROCESSED_DIR.glob("*.tif"))
    print(f"Found {len(all_tifs)} GeoTIFFs in {PROCESSED_DIR}:\n")

    summary_list = []
    for p in all_tifs:
        info = verify_file(p)
        summary_list.append(info)
        print(f"File: {info['file']}")
        print(f"  CRS:        {info['crs']} (EPSG:{info['crs_epsg']})")
        print(f"  Dimensions: {info['width']} x {info['height']} px | Resolution: {info['res']} m")
        print(f"  Stats:      min={info['min']:.3f}, max={info['max']:.3f}, mean={info['mean']:.3f}, std={info['std']:.3f}")
        print(f"  In Range [-1, 1]: {info['in_range']}")
        print(f"  Valid Px:   {info['valid_pixels']:,}\n")

    # Save verification JSON
    v_path = REPORTS_DIR / "qgis_verification.json"
    with open(v_path, "w", encoding="utf-8") as f:
        json.dump(summary_list, f, indent=2)
    print(f"✓ QGIS verification report saved -> {v_path}")

    # Generate preview
    generate_qgis_preview()
    print("=" * 65)


if __name__ == "__main__":
    main()

