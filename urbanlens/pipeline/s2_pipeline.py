"""
s2_pipeline.py – Phase 1 Step 2: Sentinel-2 Cloud-Masked Median Composites
and Index Computation (NDVI, NDBI, NDWI).

Study Area: BBMP Ward 35 (Hemmigepura), which contains Pattanagere.
Collection: COPERNICUS/S2_SR_HARMONIZED
Cloud Filter: CLOUDY_PIXEL_PERCENTAGE < 20
Cloud Masking: Scene Classification Layer (SCL)
Target CRS: EPSG:32643 (UTM Zone 43N)
Resolution: 10 metres
Periods:
  2018: 2018-01-01 to 2018-03-31 (dry season)
  2025: 2025-01-01 to 2025-03-31 (dry season)
"""

import io
import json
import os
import sys
import zipfile
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.warp import calculate_default_transform, reproject, Resampling
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure local pipeline modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

REPO_ROOT     = Path(__file__).resolve().parent.parent
STUDY_AREA    = REPO_ROOT / config.STUDY_AREA_GEOJSON
PROCESSED_DIR = REPO_ROOT / config.PROCESSED_DIR
REPORTS_DIR   = REPO_ROOT / "reports"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def init_ee():
    """Initialize Earth Engine with informative error if unauthenticated."""
    import ee
    project = getattr(config, "GEE_PROJECT", None) or os.environ.get("EE_PROJECT")
    try:
        if project:
            ee.Initialize(project=project)
            print(f"✓ Google Earth Engine initialized with project: {project}")
        else:
            ee.Initialize()
            print("✓ Google Earth Engine initialized successfully.")
    except Exception as exc:
        print("\n" + "!" * 65)
        print("  GEE AUTHENTICATION REQUIRED")
        print("!" * 65)
        print(f"Error: {exc}\n")
        print("Please authenticate GEE by running:")
        print("    python -c \"import ee; ee.Authenticate()\"")
        print("or in your shell:")
        print("    earthengine authenticate")
        print("!" * 65 + "\n")
        sys.exit(1)
    return ee


def load_study_area_geometry(ee):
    """Load study area polygon GeoJSON and return an ee.Geometry."""
    with open(STUDY_AREA, "r", encoding="utf-8") as f:
        gj = json.load(f)
    geom_dict = gj["features"][0]["geometry"]
    ee_geom = ee.Geometry(geom_dict)
    return ee_geom, gj["features"][0]["properties"]


def mask_s2_scl(image):
    """
    Mask Sentinel-2 SR using the Scene Classification Layer (SCL).
    Masked values per project configuration:
      3: Cloud shadows
      8: Cloud medium probability
      9: Cloud high probability
      10: Thin cirrus
      11: Snow / ice
    """
    scl = image.select("SCL")
    # Retain pixels where SCL is NOT in the mask classes
    mask = (scl.neq(3)
            .And(scl.neq(8))
            .And(scl.neq(9))
            .And(scl.neq(10))
            .And(scl.neq(11)))
    return image.updateMask(mask)


def add_indices(image):
    """
    Calculate NDVI, NDBI, and NDWI on surface reflectance bands:
      NDVI = (B8 - B4) / (B8 + B4)      [NIR - Red]
      NDBI = (B11 - B8) / (B11 + B8)    [SWIR1 - NIR]
      NDWI = (B3 - B8) / (B3 + B8)      [Green - NIR] (McFeeters)
    """
    # Convert DN to reflectance (divide by 10000) for standard calculations
    b3  = image.select("B3").divide(10000.0)
    b4  = image.select("B4").divide(10000.0)
    b8  = image.select("B8").divide(10000.0)
    b11 = image.select("B11").divide(10000.0)

    ndvi = (b8.subtract(b4)).divide(b8.add(b4)).rename("NDVI")
    ndbi = (b11.subtract(b8)).divide(b11.add(b8)).rename("NDBI")
    ndwi = (b3.subtract(b8)).divide(b3.add(b8)).rename("NDWI")

    return image.addBands([ndvi, ndbi, ndwi])


def build_composite_for_year(ee, aoi, year):
    """
    Query, filter, cloud-mask, and composite Sentinel-2 imagery for a given year.
    Returns: (composite_image, scene_count)
    """
    period = config.PERIODS[year]
    start_date = period["start"]
    end_date   = period["end"]

    collection = (
        ee.ImageCollection(config.S2_COLLECTION)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", config.CLOUDY_PIXEL_PERCENTAGE_MAX))
    )

    count = collection.size().getInfo()

    # Cloud masking with SCL
    masked_col = collection.map(mask_s2_scl)

    # Median reducer over the dry season
    composite = masked_col.median().clip(aoi)

    # Compute indices on composite
    composite_with_indices = add_indices(composite)

    return composite_with_indices, count


def download_geotiff(ee, image, band_name, aoi, output_tif, scale=config.EXPORT_SCALE, crs=config.EXPORT_CRS):
    """
    Download a single band GeoTIFF directly from GEE via download URL
    and save with the target CRS (EPSG:32643) at 10m resolution.
    Handles both direct GeoTIFF streams and zip-wrapped outputs.
    """
    single_band = image.select([band_name])
    url = single_band.getDownloadURL({
        "scale": scale,
        "crs": crs,
        "region": aoi,
        "format": "GEO_TIFF"
    })

    print(f"  Downloading {band_name} ({crs}, {scale}m)...")
    req = urllib.request.Request(url, headers={"User-Agent": "UrbanLens-Pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = resp.read()

    # Handle zip if GEE packages it
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            tif_names = [n for n in z.namelist() if n.lower().endswith(".tif")]
            if tif_names:
                with open(output_tif, "wb") as f:
                    f.write(z.read(tif_names[0]))
            else:
                raise RuntimeError("No .tif file found in downloaded zip archive.")
    else:
        with open(output_tif, "wb") as f:
            f.write(data)

    print(f"  Saved -> {output_tif} ({len(data)} bytes)")


def analyze_raster(tif_path):
    """Compute basic raster statistics using rasterio and numpy."""
    with rasterio.open(tif_path) as src:
        arr = src.read(1)
        nodata = src.nodata
        valid = arr[~np.isnan(arr)]
        if nodata is not None:
            valid = valid[valid != nodata]

        stats = {
            "min": float(np.min(valid)) if len(valid) else None,
            "max": float(np.max(valid)) if len(valid) else None,
            "mean": float(np.mean(valid)) if len(valid) else None,
            "std": float(np.std(valid)) if len(valid) else None,
            "crs": str(src.crs),
            "width": src.width,
            "height": src.height,
            "resolution": src.res,
            "bounds": [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top],
            "valid_pixels": int(len(valid))
        }
    return stats, valid


def generate_ndvi_histogram(valid_2018, valid_2025):
    """Plot NDVI histograms for 2018 and 2025 dry season composites."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(
        f"Sentinel-2 NDVI Distribution: {config.STUDY_AREA_NAME}\n"
        f"Dry Season (Jan–Mar) 2018 vs 2025 (CRS: {config.EXPORT_CRS}, 10m)",
        fontsize=12, fontweight="bold"
    )

    for ax, data, year, color in [
        (axes[0], valid_2018, 2018, "#27AE60"),
        (axes[1], valid_2025, 2025, "#E67E22"),
    ]:
        ax.hist(data, bins=60, range=(-0.2, 0.9), color=color, alpha=0.75, edgecolor="black", linewidth=0.5)
        ax.axvline(np.mean(data), color="red", linestyle="--", linewidth=1.5,
                   label=f"Mean: {np.mean(data):.3f}")
        ax.axvline(0.3, color="gray", linestyle=":", linewidth=1.2, label="Veg Threshold (~0.3)")
        ax.set_title(f"{year} Dry Season NDVI (N={len(data):,})", fontsize=11)
        ax.set_xlabel("NDVI Value")
        ax.set_ylabel("Pixel Count")
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.legend()

    hist_out = REPORTS_DIR / "ndvi_histogram.png"
    fig.tight_layout()
    fig.savefig(hist_out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ NDVI histogram saved to: {hist_out}")
    return hist_out


def main():
    print("=" * 65)
    print("  URBANLENS AR – SATELLITE PIPELINE (PHASE 1 STEP 2)")
    print(f"  Study Area: {config.STUDY_AREA_NAME}")
    print(f"  Collection: {config.S2_COLLECTION}")
    print(f"  Cloud Filter: CLOUDY_PIXEL_PERCENTAGE < {config.CLOUDY_PIXEL_PERCENTAGE_MAX}")
    print(f"  Target CRS: {config.EXPORT_CRS} (10m)")
    print("=" * 65)

    ee = init_ee()
    aoi, area_props = load_study_area_geometry(ee)
    print(f"Loaded AOI from: {config.STUDY_AREA_GEOJSON}")
    print(f"Ward: {area_props.get('ward_number')} - {area_props.get('ward_name')} ({area_props.get('area_km2')} km²)\n")

    results_meta = {
        "study_area": config.STUDY_AREA_NAME,
        "ward_number": area_props.get("ward_number"),
        "ward_name": area_props.get("ward_name"),
        "years": {}
    }

    ndvi_arrays = {}

    for year in [2018, 2025]:
        print(f"\n--- Processing Year {year} (Jan to Mar) ---")
        composite, scene_count = build_composite_for_year(ee, aoi, year)
        print(f"  Scenes meeting cloud threshold (<20%): {scene_count}")

        year_stats = {"scene_count": scene_count, "indices": {}}

        for index_name in config.INDEX_NAMES:
            out_tif = PROCESSED_DIR / f"{index_name.lower()}_{year}.tif"
            download_geotiff(ee, composite, index_name, aoi, str(out_tif))

            stats, valid_pixels = analyze_raster(out_tif)
            year_stats["indices"][index_name] = stats
            print(f"  {index_name} Stats: min={stats['min']:.3f}, max={stats['max']:.3f}, "
                  f"mean={stats['mean']:.3f}, std={stats['std']:.3f}, CRS={stats['crs']}")

            if index_name == "NDVI":
                ndvi_arrays[year] = valid_pixels

        results_meta["years"][year] = year_stats

    # Generate histogram
    if 2018 in ndvi_arrays and 2025 in ndvi_arrays:
        generate_ndvi_histogram(ndvi_arrays[2018], ndvi_arrays[2025])

    # Save summary metadata
    meta_path = REPORTS_DIR / "phase1_step2_stats.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(results_meta, f, indent=2)
    print(f"\n✓ Metrics saved to: {meta_path}")
    print("=" * 65)


if __name__ == "__main__":
    main()
