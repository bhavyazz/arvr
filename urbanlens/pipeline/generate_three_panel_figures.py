"""
generate_three_panel_figures.py – Generates 3-panel visual check figures
for both 2018 and 2025:
  Panel 1: Sentinel-2 NDVI (Vegetation index, RdYlGn)
  Panel 2: Sentinel-2 NDBI (Built-up index, Coolwarm/PuOr)
  Panel 3: Sentinel-2 True Colour RGB (B4-Red, B3-Green, B2-Blue)

Output:
  reports/s2_three_panel_2018.png
  reports/s2_three_panel_2025.png
"""

import json
import urllib.request
import zipfile
import io
import sys
from pathlib import Path
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Point
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

REPO_ROOT     = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / config.PROCESSED_DIR
REPORTS_DIR   = REPO_ROOT / "reports"
STUDY_AREA    = REPO_ROOT / config.STUDY_AREA_GEOJSON


def download_rgb_composite(ee, aoi, year):
    """Fetch 3-band RGB (B4, B3, B2) median composite from GEE."""
    out_rgb = PROCESSED_DIR / f"rgb_{year}.tif"
    if out_rgb.exists() and out_rgb.stat().st_size > 100000:
        print(f"RGB {year} already exists at {out_rgb}")
        return out_rgb

    print(f"Fetching Sentinel-2 RGB (B4, B3, B2) for {year} from GEE...")
    period = config.PERIODS[year]
    col = (
        ee.ImageCollection(config.S2_COLLECTION)
        .filterBounds(aoi)
        .filterDate(period["start"], period["end"])
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", config.CLOUDY_PIXEL_PERCENTAGE_MAX))
    )

    # Cloud masking with SCL
    def mask_scl(img):
        scl = img.select("SCL")
        mask = (scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11)))
        return img.updateMask(mask)

    comp = col.map(mask_scl).median().clip(aoi)
    rgb = comp.select(["B4", "B3", "B2"])  # Red, Green, Blue

    url = rgb.getDownloadURL({
        "scale": config.EXPORT_SCALE,
        "crs": config.EXPORT_CRS,
        "region": aoi,
        "format": "GEO_TIFF"
    })

    req = urllib.request.Request(url, headers={"User-Agent": "UrbanLens/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()

    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            tif_names = [n for n in z.namelist() if n.lower().endswith(".tif")]
            with open(out_rgb, "wb") as f:
                f.write(z.read(tif_names[0]))
    else:
        with open(out_rgb, "wb") as f:
            f.write(data)

    print(f"Saved RGB {year} -> {out_rgb} ({out_rgb.stat().st_size:,} bytes)")
    return out_rgb


def make_three_panel(year, gdf_ward, c_gdf):
    ndvi_path = PROCESSED_DIR / f"ndvi_{year}.tif"
    ndbi_path = PROCESSED_DIR / f"ndbi_{year}.tif"
    rgb_path  = PROCESSED_DIR / f"rgb_{year}.tif"

    with rasterio.open(ndvi_path) as src:
        ndvi = src.read(1)
        extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
        nodata = src.nodata
    ndvi_masked = np.where(ndvi == nodata, np.nan, ndvi)

    with rasterio.open(ndbi_path) as src:
        ndbi = src.read(1)
    ndbi_masked = np.where(ndbi == nodata, np.nan, ndbi)

    with rasterio.open(rgb_path) as src:
        r = src.read(1) / 10000.0  # B4
        g = src.read(2) / 10000.0  # B3
        b = src.read(3) / 10000.0  # B2

    # Linear 2-98% percentile stretch for true colour RGB
    valid_mask = ~np.isnan(r) & (r > 0)
    rgb_stack = np.dstack([r, g, b])
    p2, p98 = np.percentile(rgb_stack[valid_mask], (2, 98))
    rgb_stretched = np.clip((rgb_stack - p2) / (p98 - p2), 0, 1)

    fig, axes = plt.subplots(1, 3, figsize=(21, 8))
    fig.suptitle(
        f"Sentinel-2 Environmental Assessment: {year} Dry Season (Jan–Mar)\n"
        f"BBMP Ward 35 (Hemmigepura) containing Pattanagere | EPSG:32643 (UTM 43N, 10m)",
        fontsize=13, fontweight="bold", color="#1B4F72"
    )

    # 1. NDVI Panel
    ax1 = axes[0]
    im1 = ax1.imshow(ndvi_masked, extent=extent, cmap="RdYlGn", vmin=-0.1, vmax=0.75, origin="upper")
    gdf_ward.boundary.plot(ax=ax1, color="black", linewidth=1.2)
    c_gdf.plot(ax=ax1, color="#154360", marker="*", markersize=140, zorder=6, label="Pattanagere Centroid")
    ax1.set_title(f"(a) NDVI – Vegetation ({year})", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Easting (m, UTM 43N)")
    ax1.set_ylabel("Northing (m, UTM 43N)")
    ax1.grid(True, linestyle=":", alpha=0.5)
    plt.colorbar(im1, ax=ax1, orientation="horizontal", pad=0.08, shrink=0.85, label="NDVI")

    # 2. NDBI Panel
    ax2 = axes[1]
    im2 = ax2.imshow(ndbi_masked, extent=extent, cmap="PuOr_r", vmin=-0.35, vmax=0.35, origin="upper")
    gdf_ward.boundary.plot(ax=ax2, color="black", linewidth=1.2)
    c_gdf.plot(ax=ax2, color="#154360", marker="*", markersize=140, zorder=6)
    ax2.set_title(f"(b) NDBI – Built-Up / Impervious ({year})", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Easting (m, UTM 43N)")
    ax2.grid(True, linestyle=":", alpha=0.5)
    plt.colorbar(im2, ax=ax2, orientation="horizontal", pad=0.08, shrink=0.85, label="NDBI")

    # 3. RGB True Colour Panel
    ax3 = axes[2]
    ax3.imshow(rgb_stretched, extent=extent, origin="upper")
    gdf_ward.boundary.plot(ax=ax3, color="yellow", linewidth=1.2)
    c_gdf.plot(ax=ax3, color="cyan", marker="*", markersize=140, zorder=6, label="Pattanagere Centroid")
    ax3.set_title(f"(c) True Colour RGB (B4-B3-B2) ({year})", fontsize=11, fontweight="bold")
    ax3.set_xlabel("Easting (m, UTM 43N)")
    ax3.grid(True, linestyle=":", alpha=0.5)

    c_pt = c_gdf.geometry.iloc[0]
    for ax, color in [(ax1, "black"), (ax2, "black"), (ax3, "yellow")]:
        ax.annotate(
            "Pattanagere",
            xy=(c_pt.x, c_pt.y),
            xytext=(15, 10),
            textcoords="offset points",
            fontweight="bold",
            fontsize=9,
            color=color,
            arrowprops=dict(arrowstyle="->", color=color, lw=1.5)
        )

    out_fig = REPORTS_DIR / f"s2_three_panel_{year}.png"
    fig.tight_layout()
    fig.savefig(out_fig, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ Saved 3-panel figure -> {out_fig}")
    return out_fig


def main():
    import ee
    ee.Initialize(project=config.GEE_PROJECT)

    with open(STUDY_AREA) as f:
        gj = json.load(f)
    aoi = ee.Geometry(gj["features"][0]["geometry"])

    gdf_ward = gpd.read_file(STUDY_AREA).to_crs(epsg=32643)
    clon = gdf_ward.iloc[0]["centroid_pattanagere"]["lon"]
    clat = gdf_ward.iloc[0]["centroid_pattanagere"]["lat"]
    c_gdf = gpd.GeoDataFrame(geometry=[Point(clon, clat)], crs="EPSG:4326").to_crs(epsg=32643)

    for year in [2018, 2025]:
        download_rgb_composite(ee, aoi, year)
        make_three_panel(year, gdf_ward, c_gdf)

    print("\n✓ Both 3-panel figures successfully generated in reports/!")


if __name__ == "__main__":
    main()

