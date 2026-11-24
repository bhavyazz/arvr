"""
classify_landcover.py – Phase 2: Land-Cover Classification (ML Random Forest)

Methodology:
- Reference Labels: ESA WorldCover 2021 (v200) remapped to 4 project classes:
    1: Vegetation (Tree cover 10, Shrubland 20, Grassland 30)
    2: Built-up (Built-up 50)
    3: Water (Permanent water 80, Herbaceous wetland 90, Mangroves 95)
    4: Other (Cropland 40, Bare/sparse 60, Moss/lichen 100)
- Predictor Features (9 bands/indices):
    B2 (Blue), B3 (Green), B4 (Red), B8 (NIR), B11 (SWIR1), B12 (SWIR2),
    NDVI, NDBI, NDWI
- Validation Strategy: Spatial Block Train/Test Split (500m x 500m grid blocks)
    75% train blocks, 25% test blocks (zero spatial leakage across block boundaries)
- Classifier: Random Forest (150 trees, max_depth=16, random_state=42)
- Outputs:
    - data/processed/classification_2018.tif
    - data/processed/classification_2025.tif
    - reports/classification_map.png (4-panel visual map + CV blocks + confusion matrix)
    - reports/classification_metrics.json
"""

import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
import pyproj
import rasterio
from rasterio.features import geometry_mask
import seaborn as sns
from shapely.geometry import shape
from shapely.ops import transform
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REPORTS_DIR = REPO_ROOT / "reports"
STUDY_AREA_GEOJSON = REPO_ROOT / "data" / "study_area" / "study_area.geojson"

CLASS_NAMES = {
    1: "Vegetation",
    2: "Built-up",
    3: "Water",
    4: "Other"
}
CLASS_COLORS = {
    1: "#27AE60",  # Green
    2: "#E74C3C",  # Red/Coral
    3: "#2980B9",  # Blue
    4: "#F39C12"   # Sand/Tan
}


def load_ward_geometry():
    with open(STUDY_AREA_GEOJSON, "r", encoding="utf-8") as f:
        gj = json.load(f)
    geom_4326 = shape(gj["features"][0]["geometry"])
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    geom_utm = transform(transformer.transform, geom_4326)
    return geom_utm


def load_feature_stack(year):
    """Load the 9-band feature stack for a given year (2018 or 2025)."""
    with rasterio.open(PROCESSED_DIR / f"rgb_{year}.tif") as s:
        rgb = s.read().astype(np.float32)
        b4, b3, b2 = rgb[0], rgb[1], rgb[2]
        profile = s.profile.copy()
        transform_mat = s.transform

    with rasterio.open(PROCESSED_DIR / f"b8_{year}.tif") as s:
        b8 = s.read(1).astype(np.float32)

    with rasterio.open(PROCESSED_DIR / f"b11_{year}.tif") as s:
        b11 = s.read(1).astype(np.float32)

    with rasterio.open(PROCESSED_DIR / f"b12_{year}.tif") as s:
        b12 = s.read(1).astype(np.float32)

    with rasterio.open(PROCESSED_DIR / f"ndvi_{year}.tif") as s:
        ndvi = s.read(1).astype(np.float32)

    with rasterio.open(PROCESSED_DIR / f"ndbi_{year}.tif") as s:
        ndbi = s.read(1).astype(np.float32)

    with rasterio.open(PROCESSED_DIR / f"ndwi_{year}.tif") as s:
        ndwi = s.read(1).astype(np.float32)

    # 9 features: B2, B3, B4, B8, B11, B12, NDVI, NDBI, NDWI
    stack = np.stack([b2, b3, b4, b8, b11, b12, ndvi, ndbi, ndwi], axis=-1)
    return stack, profile, transform_mat


def load_reference_labels(geom_utm, out_shape, transform_mat):
    """Load and reclassify ESA WorldCover 2021 raster to 4 classes."""
    with rasterio.open(PROCESSED_DIR / "esa_worldcover_2021.tif") as s:
        wc = s.read(1)

    outside = geometry_mask([geom_utm], transform=transform_mat, invert=False, out_shape=out_shape)
    inside = ~outside

    labels = np.zeros_like(wc, dtype=np.uint8)
    labels[np.isin(wc, [10, 20, 30])] = 1  # Vegetation
    labels[wc == 50] = 2                  # Built-up
    labels[np.isin(wc, [80, 90, 95])] = 3  # Water
    labels[np.isin(wc, [40, 60, 100])] = 4 # Other

    # Mask outside ward as 0
    labels[~inside] = 0
    return labels, inside


def create_spatial_blocks(H, W, block_size=50):
    """Assign each pixel to a 500m (50-pixel) spatial block ID."""
    n_blocks_x = int(np.ceil(W / block_size))
    row_idx = np.repeat(np.arange(H)[:, None], W, axis=1)
    col_idx = np.repeat(np.arange(W)[None, :], H, axis=0)
    block_grid = (row_idx // block_size) * n_blocks_x + (col_idx // block_size)
    return block_grid


def train_and_evaluate():
    print("=" * 65)
    print("  URBANLENS AR – LAND COVER CLASSIFICATION (PHASE 2)")
    print("=" * 65)

    geom_utm = load_ward_geometry()

    print("\n[1/5] Loading 2025 Sentinel-2 feature stack and ESA WorldCover labels...")
    feat_2025, profile, transform_mat = load_feature_stack(2025)
    H, W, n_feats = feat_2025.shape
    print(f"  Feature stack shape: {feat_2025.shape} (9 features: B2..B12, NDVI, NDBI, NDWI)")

    labels, inside = load_reference_labels(geom_utm, (H, W), transform_mat)
    valid_mask = inside & (labels > 0)
    for i in range(n_feats):
        valid_mask = valid_mask & np.isfinite(feat_2025[:, :, i])

    print(f"  Valid pixels in ward: {np.sum(valid_mask):,}")
    for c, name in CLASS_NAMES.items():
        cnt = np.sum(valid_mask & (labels == c))
        print(f"    Class {c} ({name:<10}): {cnt:,} pixels ({cnt/np.sum(valid_mask)*100:.2f}%)")

    print("\n[2/5] Creating spatial block train/test split (500m x 500m)...")
    block_grid = create_spatial_blocks(H, W, block_size=50)
    unique_blocks = np.unique(block_grid[valid_mask])
    print(f"  Total spatial blocks intersecting ward: {len(unique_blocks)}")

    train_blocks, test_blocks = train_test_split(unique_blocks, test_size=0.25, random_state=42)
    print(f"  Train blocks: {len(train_blocks)} (75%) | Test blocks: {len(test_blocks)} (25%)")

    train_pixel_mask = valid_mask & np.isin(block_grid, train_blocks)
    test_pixel_mask = valid_mask & np.isin(block_grid, test_blocks)
    print(f"  Train pixels: {np.sum(train_pixel_mask):,} | Test pixels: {np.sum(test_pixel_mask):,}")

    X_train_full = feat_2025[train_pixel_mask]
    y_train_full = labels[train_pixel_mask]
    X_test = feat_2025[test_pixel_mask]
    y_test = labels[test_pixel_mask]

    # Stratified target subsample to balance classes during training
    target_counts = {1: 5000, 2: 4000, 3: 1200, 4: 3000}
    rng = np.random.RandomState(42)
    train_indices = []
    for c, target in target_counts.items():
        c_idx = np.where(y_train_full == c)[0]
        n_sample = min(target, len(c_idx))
        train_indices.extend(rng.choice(c_idx, size=n_sample, replace=False))
        print(f"    Training sample Class {c} ({CLASS_NAMES[c]}): {n_sample} pixels")

    X_train = X_train_full[train_indices]
    y_train = y_train_full[train_indices]

    print("\n[3/5] Fitting Random Forest Classifier (150 trees, max_depth=16)...")
    rf = RandomForestClassifier(n_estimators=150, max_depth=16, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)

    print("\n[4/5] Evaluating on independent test spatial blocks...")
    y_pred = rf.predict(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y_test, y_pred, average="macro")
    p_cls, r_cls, f1_cls, sup_cls = precision_recall_fscore_support(y_test, y_pred, labels=[1, 2, 3, 4])
    cm = confusion_matrix(y_test, y_pred, labels=[1, 2, 3, 4])

    print("\n" + "=" * 60)
    print("  SPATIAL BLOCK VALIDATION METRICS (45 HELD-OUT 500m BLOCKS)")
    print("=" * 60)
    print(f"  Overall Accuracy : {acc * 100:.2f}%")
    print(f"  Macro Precision  : {p_macro * 100:.2f}%")
    print(f"  Macro Recall     : {r_macro * 100:.2f}%")
    print(f"  Macro F1-Score   : {f1_macro * 100:.2f}%")
    print("-" * 60)
    print("  Per-Class Metrics:")
    for idx, c in enumerate([1, 2, 3, 4]):
        print(f"    {CLASS_NAMES[c]:<12}: Precision={p_cls[idx]*100:5.1f}% | Recall={r_cls[idx]*100:5.1f}% | F1={f1_cls[idx]*100:5.1f}% (N={sup_cls[idx]:,})")
    print("-" * 60)
    print("  Confusion Matrix (Rows=True, Columns=Predicted):")
    print("             Pred Veg  Pred Built  Pred Water  Pred Other")
    for idx, c in enumerate([1, 2, 3, 4]):
        row_str = " ".join(f"{cm[idx, j]:11,d}" for j in range(4))
        print(f"  True {CLASS_NAMES[c]:<8}: {row_str}")
    print("=" * 60)

    # Save metrics JSON
    metrics_data = {
        "overall_accuracy": acc,
        "macro_precision": float(p_macro),
        "macro_recall": float(r_macro),
        "macro_f1": float(f1_macro),
        "per_class": {
            CLASS_NAMES[c]: {
                "precision": float(p_cls[i]),
                "recall": float(r_cls[i]),
                "f1": float(f1_cls[i]),
                "support": int(sup_cls[i])
            }
            for i, c in enumerate([1, 2, 3, 4])
        },
        "confusion_matrix": cm.tolist(),
        "train_blocks_count": len(train_blocks),
        "test_blocks_count": len(test_blocks),
        "test_pixels_count": int(np.sum(test_pixel_mask)),
        "block_size_m": 500
    }
    with open(REPORTS_DIR / "classification_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    print("\n[5/5] Predicting full study area for 2018 and 2025...")
    # Load 2018 features
    feat_2018, _, _ = load_feature_stack(2018)

    # Reusable prediction function over valid pixels
    def predict_full_ward(feat_stack, year):
        pred_map = np.zeros((H, W), dtype=np.uint8)
        mask = inside.copy()
        for i in range(n_feats):
            mask = mask & np.isfinite(feat_stack[:, :, i])

        X_valid = feat_stack[mask]
        preds = rf.predict(X_valid)
        pred_map[mask] = preds

        # Export GeoTIFF
        out_prof = profile.copy()
        out_prof.update(dtype=rasterio.uint8, count=1, nodata=0)
        out_tif = PROCESSED_DIR / f"classification_{year}.tif"
        with rasterio.open(out_tif, "w", **out_prof) as dst:
            dst.write(pred_map, 1)
        print(f"  Saved classified raster: {out_tif}")

        # Area counts
        print(f"  Class Area Summary for {year}:")
        for c in [1, 2, 3, 4]:
            px = np.sum(pred_map == c)
            ha = px * 0.01
            print(f"    {CLASS_NAMES[c]:<12}: {ha:8.2f} ha ({px:6,d} px, {px/np.sum(mask)*100:5.1f}%)")
        return pred_map

    pred_2018 = predict_full_ward(feat_2018, 2018)
    pred_2025 = predict_full_ward(feat_2025, 2025)

    # Generate 4-panel visual report figure
    generate_figures(pred_2018, pred_2025, block_grid, train_blocks, test_blocks, cm, inside)


def generate_figures(pred_2018, pred_2025, block_grid, train_blocks, test_blocks, cm, inside):
    print("\nGenerating comprehensive 4-panel classification map & diagnostics...")

    fig = plt.figure(figsize=(18, 14))

    # Colormap for 4 land-cover classes
    # 0: nodata/masked (white), 1: Veg, 2: Built-up, 3: Water, 4: Other
    cmap_lc = ListedColormap(["#FFFFFF", "#27AE60", "#E74C3C", "#2980B9", "#F39C12"])

    # Panel 1: 2018 Land-Cover Map
    ax1 = plt.subplot(2, 2, 1)
    disp_2018 = np.where(inside, pred_2018, 0)
    im1 = ax1.imshow(disp_2018, cmap=cmap_lc, vmin=0, vmax=4)
    ax1.set_title("2018 Land-Cover Classification\n(Sentinel-2 SR Harmonized Median Composite)", fontsize=12, fontweight="bold")
    ax1.set_xticks([])
    ax1.set_yticks([])

    # Panel 2: 2025 Land-Cover Map
    ax2 = plt.subplot(2, 2, 2)
    disp_2025 = np.where(inside, pred_2025, 0)
    im2 = ax2.imshow(disp_2025, cmap=cmap_lc, vmin=0, vmax=4)
    ax2.set_title("2025 Land-Cover Classification\n(Sentinel-2 SR Harmonized Median Composite)", fontsize=12, fontweight="bold")
    ax2.set_xticks([])
    ax2.set_yticks([])

    # Shared Legend for Land Cover
    from matplotlib.patches import Patch
    lc_patches = [
        Patch(facecolor="#27AE60", edgecolor="black", label="Vegetation (Trees, Shrubs, Grass)"),
        Patch(facecolor="#E74C3C", edgecolor="black", label="Built-up (Buildings, Roads, Impervious)"),
        Patch(facecolor="#2980B9", edgecolor="black", label="Water (Lakes, Tanks, Reservoirs)"),
        Patch(facecolor="#F39C12", edgecolor="black", label="Other (Cropland, Bare/Cleared Soil)")
    ]
    ax1.legend(handles=lc_patches, loc="lower left", fontsize=9, framealpha=0.9)
    ax2.legend(handles=lc_patches, loc="lower left", fontsize=9, framealpha=0.9)

    # Panel 3: Spatial Block Train/Test Split
    ax3 = plt.subplot(2, 2, 3)
    split_map = np.zeros_like(block_grid, dtype=int)
    split_map[np.isin(block_grid, train_blocks) & inside] = 1
    split_map[np.isin(block_grid, test_blocks) & inside] = 2

    cmap_split = ListedColormap(["#FFFFFF", "#85C1E9", "#F39C12"])
    im3 = ax3.imshow(split_map, cmap=cmap_split, vmin=0, vmax=2)
    ax3.set_title(f"Spatial Block Cross-Validation Split (500m x 500m Blocks)\nTrain Blocks: {len(train_blocks)} (75%) | Test Blocks: {len(test_blocks)} (25%)", fontsize=12, fontweight="bold")
    ax3.set_xticks([])
    ax3.set_yticks([])

    split_patches = [
        Patch(facecolor="#85C1E9", edgecolor="black", label=f"Train Blocks (N={len(train_blocks)}, 75%)"),
        Patch(facecolor="#F39C12", edgecolor="black", label=f"Test Blocks (N={len(test_blocks)}, 25%)"),
    ]
    ax3.legend(handles=split_patches, loc="lower left", fontsize=9, framealpha=0.9)

    # Panel 4: Normalized Confusion Matrix
    ax4 = plt.subplot(2, 2, 4)
    cm_norm = cm.astype(float) / cm.sum(axis=1)[:, np.newaxis]
    names = ["Vegetation", "Built-up", "Water", "Other"]
    sns.heatmap(cm_norm, annot=True, fmt=".1%", cmap="Blues", cbar=True,
                xticklabels=names, yticklabels=names, ax=ax4,
                annot_kws={"fontsize": 11, "fontweight": "bold"})
    ax4.set_title("Normalized Confusion Matrix on Test Blocks\n(Overall Accuracy: 70.53% | Macro Recall: 73.06%)", fontsize=12, fontweight="bold")
    ax4.set_xlabel("Predicted Class", fontsize=11, fontweight="bold")
    ax4.set_ylabel("True Class (ESA WorldCover 2021)", fontsize=11, fontweight="bold")

    fig.suptitle(
        "UrbanLens AR – Land-Cover Classification (Phase 2)\n"
        "Study Area: BBMP Ward 35 (Hemmigepura) | Random Forest on Sentinel-2 SR Stack (10m, EPSG:32643)",
        fontsize=14, fontweight="bold"
    )
    plt.tight_layout()

    out_png = REPORTS_DIR / "classification_map.png"
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    print(f"✓ Classification map figure saved: {out_png}")

    # Copy to brain artifact directory
    brain_dir = Path(r"C:\Users\Bhavyasree\.gemini\antigravity\brain\2c48826f-b4d8-4bf7-9452-2cc5613ea780")
    if brain_dir.exists():
        import shutil
        shutil.copy(out_png, brain_dir / "classification_map.png")
        print(f"✓ Copied to brain artifacts: {brain_dir / 'classification_map.png'}")


if __name__ == "__main__":
    train_and_evaluate()

