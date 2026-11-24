"""
classify_3class.py – 3-class Random Forest land-cover classifier for UrbanLens AR.

Classes:
  1 = Vegetation   (ESA WorldCover: Tree cover, Shrubland, Grassland)
  2 = Built-up     (ESA WorldCover: Built-up)
  3 = Water        (ESA WorldCover: Permanent water body)

Dropped (excluded from training AND evaluation — not merged):
  ESA 40  = Cropland
  ESA 60  = Bare/sparse vegetation
  ESA 100 = Moss/lichen

Dynamic World class mapping for 2018 proxy validation:
  DW 0  = Water   -> 3
  DW 1  = Trees   -> 1
  DW 2  = Grass   -> 1
  DW 5  = Built   -> 2
  DW 3  = Flooded -> 3  (map to Water for consistency)
  DW 4  = Crops   -> DROPPED
  DW 7  = Bare    -> DROPPED
  DW 6  = Scrub   -> 1  (Vegetation)
  (DW uses label_mode from GEE; 8=Snow/ice not expected in Bengaluru)

Accuracy notes:
  - 2025 accuracy is evaluated against WorldCover 2021 on held-out spatial blocks.
  - 2018 accuracy is UNVERIFIED. No authoritative ground truth exists for 2018
    over Ward 35. Dynamic World 2018 is used as a proxy reference only —
    it is an automated ML model output, not field-surveyed ground truth, and
    over-predicts built-up surfaces on dry peri-urban soils.
"""

import os
import sys
import json
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import rowcol
import geopandas as gpd
from shapely.ops import transform as shp_transform
import pyproj
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
RPT_DIR  = os.path.join(BASE_DIR, "reports")
os.makedirs(RPT_DIR, exist_ok=True)

WORLDCOVER_PATH = os.path.join(PROC_DIR, "esa_worldcover_2021.tif")
DW_2018_PATH    = os.path.join(PROC_DIR, "dynamic_world_2018.tif")
STUDY_AREA_PATH = os.path.join(BASE_DIR, "data", "study_area", "study_area.geojson")

BAND_FILES_2025 = {
    "B2":   os.path.join(PROC_DIR, "rgb_2025.tif"),        # band 1 of RGB
    "B3":   os.path.join(PROC_DIR, "rgb_2025.tif"),        # band 2
    "B4":   os.path.join(PROC_DIR, "rgb_2025.tif"),        # band 3
    "B8":   os.path.join(PROC_DIR, "b8_2025.tif"),
    "B11":  os.path.join(PROC_DIR, "b11_2025.tif"),
    "B12":  os.path.join(PROC_DIR, "b12_2025.tif"),
    "NDVI": os.path.join(PROC_DIR, "ndvi_2025.tif"),
    "NDBI": os.path.join(PROC_DIR, "ndbi_2025.tif"),
    "NDWI": os.path.join(PROC_DIR, "ndwi_2025.tif"),
}

BAND_FILES_2018 = {
    "B2":   os.path.join(PROC_DIR, "rgb_2018.tif"),
    "B3":   os.path.join(PROC_DIR, "rgb_2018.tif"),
    "B4":   os.path.join(PROC_DIR, "rgb_2018.tif"),
    "B8":   os.path.join(PROC_DIR, "b8_2018.tif"),
    "B11":  os.path.join(PROC_DIR, "b11_2018.tif"),
    "B12":  os.path.join(PROC_DIR, "b12_2018.tif"),
    "NDVI": os.path.join(PROC_DIR, "ndvi_2018.tif"),
    "NDBI": os.path.join(PROC_DIR, "ndbi_2018.tif"),
    "NDWI": os.path.join(PROC_DIR, "ndwi_2018.tif"),
}

OUT_CLASS_2018 = os.path.join(PROC_DIR, "classification_2018_3c.tif")
OUT_CLASS_2025 = os.path.join(PROC_DIR, "classification_2025_3c.tif")
OUT_MAP_FIG    = os.path.join(RPT_DIR,  "classification_map_3c.png")
OUT_METRICS    = os.path.join(RPT_DIR,  "classification_metrics_3c.json")

# ---------------------------------------------------------------------------
# ESA WorldCover -> 3-class mapping  (None = DROPPED)
# ---------------------------------------------------------------------------
ESA_MAP = {
    10: 1,    # Tree cover     -> Vegetation
    20: 1,    # Shrubland      -> Vegetation
    30: 1,    # Grassland      -> Vegetation
    40: None, # Cropland       -> DROPPED
    50: 2,    # Built-up       -> Built-up
    60: None, # Bare/sparse    -> DROPPED
    80: 3,    # Permanent H2O  -> Water
    90: 3,    # Herbaceous wet -> Water  (UNUSED IN BENGALURU)
    95: 3,    # Mangroves      -> Water  (UNUSED IN BENGALURU)
   100: None, # Moss/lichen    -> DROPPED
}

# Dynamic World -> 3-class mapping  (None = DROPPED)
DW_MAP = {
    0: 3,    # Water          -> Water
    1: 1,    # Trees          -> Vegetation
    2: 1,    # Grass          -> Vegetation
    3: 3,    # Flooded veg    -> Water
    4: None, # Crops          -> DROPPED
    5: 2,    # Built-up       -> Built-up
    6: 1,    # Bare/scrub     -> Vegetation
    7: None, # Bare ground    -> DROPPED
    8: None, # Snow/ice       -> DROPPED (not present in Bengaluru)
}

CLASS_NAMES = {1: "Vegetation", 2: "Built-up", 3: "Water"}
CLASS_COLORS = {1: "#2d7a2d", 2: "#c0392b", 3: "#2980b9"}


# ---------------------------------------------------------------------------
# Utility: load ward mask
# ---------------------------------------------------------------------------
def load_ward_mask(profile):
    """Return boolean array True inside ward boundary."""
    gdf = gpd.read_file(STUDY_AREA_PATH).to_crs("EPSG:4326")
    proj_crs = pyproj.CRS.from_epsg(32643)
    wgs84    = pyproj.CRS.from_epsg(4326)
    proj_fn  = pyproj.Transformer.from_crs(wgs84, proj_crs, always_xy=True).transform
    geoms_proj = [shp_transform(proj_fn, geom) for geom in gdf.geometry]
    h, w = profile["height"], profile["width"]
    mask = geometry_mask(
        geoms_proj, out_shape=(h, w),
        transform=profile["transform"], invert=True
    )
    return mask


# ---------------------------------------------------------------------------
# Utility: read feature stack
# ---------------------------------------------------------------------------
def read_feature_stack(band_files):
    """Return (n_pixels, 9) feature array and reference profile."""
    bands = []
    profile = None
    keys = ["B2", "B3", "B4", "B8", "B11", "B12", "NDVI", "NDBI", "NDWI"]
    rgb_loaded = False
    rgb_data   = None

    for key in keys:
        path = band_files[key]
        if key in ("B2", "B3", "B4"):
            if not rgb_loaded:
                with rasterio.open(path) as src:
                    rgb_data = src.read()          # shape (3, H, W)
                    if profile is None:
                        profile = src.profile.copy()
                rgb_loaded = True
            band_idx = ["B2", "B3", "B4"].index(key)
            bands.append(rgb_data[band_idx].astype(np.float32))
        else:
            with rasterio.open(path) as src:
                arr = src.read(1).astype(np.float32)
                if profile is None:
                    profile = src.profile.copy()
            bands.append(arr)

    stack = np.stack(bands, axis=0)   # (9, H, W)
    return stack, profile


# ---------------------------------------------------------------------------
# Utility: map ESA raster to 3-class labels
# ---------------------------------------------------------------------------
def map_esa_labels(esa_arr, mapping=ESA_MAP):
    """
    Map ESA WorldCover DN values to project class IDs.
    Returns array with:
      1/2/3 for kept classes
      0     for DROPPED pixels (excluded from training and evaluation)
    """
    out = np.zeros(esa_arr.shape, dtype=np.uint8)
    for esa_val, cls in mapping.items():
        if cls is not None:
            out[esa_arr == esa_val] = cls
        # cls is None -> stays 0 (dropped)
    return out


# ---------------------------------------------------------------------------
# Utility: map Dynamic World raster to 3-class labels
# ---------------------------------------------------------------------------
def map_dw_labels(dw_arr, mapping=DW_MAP):
    out = np.zeros(dw_arr.shape, dtype=np.uint8)
    for dw_val, cls in mapping.items():
        if cls is not None:
            out[dw_arr == dw_val] = cls
    return out


# ---------------------------------------------------------------------------
# Spatial block split
# ---------------------------------------------------------------------------
def make_spatial_blocks(profile, block_size_m=500, seed=42, test_frac=0.25):
    """
    Divide the raster into square spatial blocks of block_size_m x block_size_m.
    Returns block_id array (H, W) with block IDs; and test_block_ids set.
    """
    pixel_size = abs(profile["transform"].a)
    block_px   = max(1, int(block_size_m / pixel_size))
    H, W       = profile["height"], profile["width"]

    rows = np.arange(H)
    cols = np.arange(W)
    block_row = rows // block_px
    block_col = cols // block_px
    n_block_cols = int(np.ceil(W / block_px))

    block_id = np.outer(block_row, np.ones(W, dtype=int)) * n_block_cols + \
               np.outer(np.ones(H, dtype=int), block_col.astype(int))
    block_id = block_id.astype(np.int32)

    unique_blocks = np.unique(block_id)
    rng = np.random.default_rng(seed)
    n_test = max(1, int(len(unique_blocks) * test_frac))
    test_ids = set(rng.choice(unique_blocks, size=n_test, replace=False).tolist())

    return block_id, test_ids


# ---------------------------------------------------------------------------
# Stratified subsample
# ---------------------------------------------------------------------------
def stratified_subsample(X, y, n_per_class, seed=42):
    rng = np.random.default_rng(seed)
    idx_all = []
    for cls, n in n_per_class.items():
        idx = np.where(y == cls)[0]
        if len(idx) == 0:
            print(f"  WARNING: class {cls} has 0 training pixels")
            continue
        chosen = rng.choice(idx, size=min(n, len(idx)), replace=False)
        idx_all.append(chosen)
    idx_all = np.concatenate(idx_all)
    rng.shuffle(idx_all)
    return X[idx_all], y[idx_all]


# ---------------------------------------------------------------------------
# Save classification raster
# ---------------------------------------------------------------------------
def save_classification(arr, profile, path):
    out_profile = profile.copy()
    out_profile.update({"dtype": "uint8", "count": 1, "nodata": 0})
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(arr.astype(np.uint8), 1)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("UrbanLens Phase 2 — 3-class Random Forest Classifier")
    print("=" * 70)

    # --- 1. Load 2025 feature stack and ward mask ---
    print("\n[1/8] Loading 2025 feature stack …")
    stack_2025, profile_2025 = read_feature_stack(BAND_FILES_2025)
    ward_mask = load_ward_mask(profile_2025)
    H, W = profile_2025["height"], profile_2025["width"]
    print(f"  Raster shape: {H} x {W}  |  Ward pixels: {ward_mask.sum():,}")

    # --- 2. Load ESA WorldCover labels ---
    print("\n[2/8] Loading ESA WorldCover 2021 labels …")
    with rasterio.open(WORLDCOVER_PATH) as src:
        esa_raw = src.read(1)
    labels_wc = map_esa_labels(esa_raw)

    unique_esa, counts_esa = np.unique(esa_raw[ward_mask], return_counts=True)
    print("  ESA WorldCover class distribution inside ward:")
    for val, cnt in zip(unique_esa, counts_esa):
        mapped = ESA_MAP.get(int(val), "UNKNOWN")
        name = CLASS_NAMES.get(mapped, "DROPPED" if mapped is None else str(mapped))
        print(f"    ESA {val:3d} -> class {str(mapped):4s} ({name:12s}): {cnt:7,} px")

    kept_mask = (labels_wc > 0) & ward_mask
    print(f"\n  Pixels kept (3 valid classes inside ward): {kept_mask.sum():,}")
    dropped_pct = 100.0 * (ward_mask.sum() - kept_mask.sum()) / ward_mask.sum()
    print(f"  Pixels dropped (ESA 40/60/100):            {ward_mask.sum() - kept_mask.sum():,} ({dropped_pct:.1f}%)")

    # --- 3. Spatial block split ---
    print("\n[3/8] Creating spatial block split (500 m, 75% train / 25% test, seed=42) …")
    block_id, test_ids = make_spatial_blocks(profile_2025, block_size_m=500,
                                              seed=42, test_frac=0.25)
    train_mask = kept_mask & ~np.isin(block_id, list(test_ids))
    test_mask  = kept_mask &  np.isin(block_id, list(test_ids))
    print(f"  Total blocks: {len(np.unique(block_id)):,}  |  Test blocks: {len(test_ids):,}")
    print(f"  Train pixels: {train_mask.sum():,}  |  Test pixels: {test_mask.sum():,}")

    # --- 4. Build train / test arrays ---
    print("\n[4/8] Building feature arrays …")
    X_flat = stack_2025.reshape(9, -1).T    # (H*W, 9)
    y_flat = labels_wc.ravel()

    X_train_all = X_flat[train_mask.ravel()]
    y_train_all = y_flat[train_mask.ravel()]
    X_test  = X_flat[test_mask.ravel()]
    y_test  = y_flat[test_mask.ravel()]

    # Stratified subsample
    n_per_class = {1: 5000, 2: 4500, 3: 1500}
    X_train, y_train = stratified_subsample(X_train_all, y_train_all, n_per_class, seed=42)
    print(f"  Training subsample: {len(y_train):,} pixels  |  Test: {len(y_test):,} pixels")
    for cls in [1, 2, 3]:
        print(f"    Class {cls} ({CLASS_NAMES[cls]}): "
              f"train={np.sum(y_train==cls):,}, test={np.sum(y_test==cls):,}")

    # --- 5. Train classifier ---
    print("\n[5/8] Training Random Forest (n_estimators=150, max_depth=16, seed=42) …")
    rf = RandomForestClassifier(
        n_estimators=150,
        max_depth=16,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced"
    )
    rf.fit(X_train, y_train)
    print("  Training complete.")

    # --- 6. Evaluate against WorldCover 2021 (2025 imagery) ---
    print("\n[6/8] Evaluating on held-out spatial test blocks (vs WorldCover 2021) …")
    y_pred_test = rf.predict(X_test)
    labels_list = [1, 2, 3]
    label_names  = ["Vegetation", "Built-up", "Water"]

    oa_wc = accuracy_score(y_test, y_pred_test)
    mac_p = precision_score(y_test, y_pred_test, labels=labels_list,
                            average="macro", zero_division=0)
    mac_r = recall_score(y_test, y_pred_test, labels=labels_list,
                         average="macro", zero_division=0)
    mac_f1 = f1_score(y_test, y_pred_test, labels=labels_list,
                      average="macro", zero_division=0)
    cm_wc = confusion_matrix(y_test, y_pred_test, labels=labels_list)

    print(f"\n  === 2025 Classification Accuracy (vs WorldCover 2021) ===")
    print(f"  Overall Accuracy : {oa_wc*100:.2f}%")
    print(f"  Macro Precision  : {mac_p*100:.2f}%")
    print(f"  Macro Recall     : {mac_r*100:.2f}%")
    print(f"  Macro F1         : {mac_f1*100:.2f}%")
    print(f"\n  Confusion Matrix (rows=true, cols=pred):")
    print(f"  {'':14s} " + "  ".join(f"{n:>10s}" for n in label_names))
    for i, true_name in enumerate(label_names):
        row_str = "  ".join(f"{cm_wc[i, j]:>10,}" for j in range(3))
        print(f"  {true_name:14s} {row_str}")

    per_class_wc = {}
    for i, cls in enumerate(labels_list):
        p = precision_score(y_test, y_pred_test, labels=[cls],
                            average="micro", zero_division=0)
        r = recall_score(y_test, y_pred_test, labels=[cls],
                         average="micro", zero_division=0)
        f = f1_score(y_test, y_pred_test, labels=[cls],
                     average="micro", zero_division=0)
        per_class_wc[CLASS_NAMES[cls]] = {
            "precision": round(float(p), 4),
            "recall":    round(float(r), 4),
            "f1":        round(float(f), 4),
            "n_test":    int(np.sum(y_test == cls)),
        }
        print(f"  {CLASS_NAMES[cls]:14s}  P={p*100:.1f}%  R={r*100:.1f}%  F1={f*100:.1f}%"
              f"  (n={np.sum(y_test==cls):,})")

    # --- 7. Predict full ward — 2025 and 2018 ---
    print("\n[7/8] Predicting full ward …")

    # 2025
    print("  Predicting 2025 …")
    X_all_2025 = X_flat.copy()
    y_pred_2025_flat = np.zeros(H * W, dtype=np.uint8)
    ward_idx = np.where(ward_mask.ravel())[0]
    y_pred_2025_flat[ward_idx] = rf.predict(X_all_2025[ward_idx]).astype(np.uint8)
    pred_2025 = y_pred_2025_flat.reshape(H, W)
    save_classification(pred_2025, profile_2025, OUT_CLASS_2025)

    # 2018
    print("  Loading 2018 feature stack …")
    stack_2018, profile_2018 = read_feature_stack(BAND_FILES_2018)
    X_all_2018 = stack_2018.reshape(9, -1).T
    y_pred_2018_flat = np.zeros(H * W, dtype=np.uint8)
    y_pred_2018_flat[ward_idx] = rf.predict(X_all_2018[ward_idx]).astype(np.uint8)
    pred_2018 = y_pred_2018_flat.reshape(H, W)
    save_classification(pred_2018, profile_2018, OUT_CLASS_2018)

    # --- 7b. Evaluate 2018 against Dynamic World 2018 ---
    print("\n  Evaluating 2018 classification against Dynamic World 2018 (proxy reference) …")
    print("  NOTE: Dynamic World 2018 is an automated ML output — not ground truth.")
    print("  2018 accuracy is UNVERIFIED against field surveys.")
    with rasterio.open(DW_2018_PATH) as src:
        dw_raw = src.read(1)
    labels_dw_2018 = map_dw_labels(dw_raw)

    # Mask: inside ward, DW label is valid (not 0=dropped)
    dw_valid_mask = (labels_dw_2018 > 0) & ward_mask
    y_dw_true  = labels_dw_2018[dw_valid_mask]
    y_dw_pred  = pred_2018[dw_valid_mask]

    oa_dw = accuracy_score(y_dw_true, y_dw_pred)
    mac_f1_dw = f1_score(y_dw_true, y_dw_pred, labels=labels_list,
                         average="macro", zero_division=0)
    cm_dw = confusion_matrix(y_dw_true, y_dw_pred, labels=labels_list)

    print(f"\n  === 2018 Classification Proxy Accuracy (vs Dynamic World 2018) ===")
    print(f"  Overall Agreement: {oa_dw*100:.2f}%  [proxy only — not ground truth]")
    print(f"  Macro F1         : {mac_f1_dw*100:.2f}%  [proxy only]")
    print(f"\n  Confusion Matrix (rows=DW-true, cols=our-pred):")
    print(f"  {'':14s} " + "  ".join(f"{n:>10s}" for n in label_names))
    for i, true_name in enumerate(label_names):
        row_str = "  ".join(f"{cm_dw[i, j]:>10,}" for j in range(3))
        print(f"  {true_name:14s} {row_str}")

    per_class_dw = {}
    for i, cls in enumerate(labels_list):
        p = precision_score(y_dw_true, y_dw_pred, labels=[cls],
                            average="micro", zero_division=0)
        r = recall_score(y_dw_true, y_dw_pred, labels=[cls],
                         average="micro", zero_division=0)
        f = f1_score(y_dw_true, y_dw_pred, labels=[cls],
                     average="micro", zero_division=0)
        per_class_dw[CLASS_NAMES[cls]] = {
            "precision": round(float(p), 4),
            "recall":    round(float(r), 4),
            "f1":        round(float(f), 4),
        }
        print(f"  {CLASS_NAMES[cls]:14s}  P={p*100:.1f}%  R={r*100:.1f}%  F1={f*100:.1f}%")

    # --- 8. Figures ---
    print("\n[8/8] Generating classification map figure …")

    # Prepare RGB display of classification
    def cls_to_rgb(arr):
        rgb = np.zeros((*arr.shape, 3), dtype=np.uint8)
        for cls, hex_col in CLASS_COLORS.items():
            r, g, b = int(hex_col[1:3], 16), int(hex_col[3:5], 16), int(hex_col[5:7], 16)
            rgb[arr == cls] = [r, g, b]
        return rgb

    # RGB for display
    def load_rgb(year):
        path = os.path.join(PROC_DIR, f"rgb_{year}.tif")
        with rasterio.open(path) as src:
            r = src.read(1).astype(np.float32)
            g = src.read(2).astype(np.float32)
            b = src.read(3).astype(np.float32)
        def norm(x):
            lo, hi = np.nanpercentile(x[ward_mask], [2, 98])
            return np.clip((x - lo) / (hi - lo + 1e-6), 0, 1)
        return np.stack([norm(r), norm(g), norm(b)], axis=-1)

    rgb_2018_disp = load_rgb(2018)
    rgb_2025_disp = load_rgb(2025)
    cls_2018_rgb  = cls_to_rgb(pred_2018)
    cls_2025_rgb  = cls_to_rgb(pred_2025)

    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    fig.suptitle("UrbanLens Phase 2 — 3-Class Land Cover Classification\n"
                 "BBMP Ward 35 (Hemmigepura), Bengaluru", fontsize=14, fontweight="bold")

    titles = ["2018 — RGB True Colour", "2018 — Classification (3-class)",
              "2025 — RGB True Colour", "2025 — Classification (3-class)"]
    images = [rgb_2018_disp, cls_2018_rgb, rgb_2025_disp, cls_2025_rgb]

    for ax, title, img in zip(axes.flat, titles, images):
        ax.imshow(img)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.axis("off")

    # Legend
    patches = [mpatches.Patch(color=CLASS_COLORS[c], label=CLASS_NAMES[c])
               for c in [1, 2, 3]]
    patches.append(mpatches.Patch(color="black", label="Outside ward / Dropped"))
    fig.legend(handles=patches, loc="lower center", ncol=4,
               fontsize=10, frameon=True, bbox_to_anchor=(0.5, 0.01))

    # Accuracy annotation
    fig.text(0.02, 0.5,
             f"2025 vs WorldCover 2021:\n"
             f"  OA = {oa_wc*100:.1f}%  |  Macro F1 = {mac_f1*100:.1f}%\n"
             f"  Veg F1={per_class_wc['Vegetation']['f1']*100:.1f}%  "
             f"Built F1={per_class_wc['Built-up']['f1']*100:.1f}%  "
             f"Water F1={per_class_wc['Water']['f1']*100:.1f}%\n\n"
             f"2018 vs Dynamic World 2018 (PROXY — not ground truth):\n"
             f"  Agreement = {oa_dw*100:.1f}%  |  Macro F1 = {mac_f1_dw*100:.1f}%",
             fontsize=8.5, va="center", ha="left",
             bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))

    plt.tight_layout(rect=[0.0, 0.07, 1.0, 0.96])
    plt.savefig(OUT_MAP_FIG, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Figure saved: {OUT_MAP_FIG}")

    # --- Save metrics JSON ---
    metrics = {
        "model": {
            "type": "RandomForestClassifier",
            "n_estimators": 150,
            "max_depth": 16,
            "random_state": 42,
            "n_classes": 3,
            "class_weights": "balanced",
            "features": ["B2", "B3", "B4", "B8", "B11", "B12", "NDVI", "NDBI", "NDWI"],
            "dropped_esa_classes": "40 (Cropland), 60 (Bare/sparse), 100 (Moss/lichen) — excluded from training and evaluation, not merged",
        },
        "accuracy_2025_vs_worldcover2021": {
            "reference": "ESA WorldCover 2021 (held-out 25% spatial blocks, 500m)",
            "overall_accuracy": round(float(oa_wc), 4),
            "macro_precision": round(float(mac_p), 4),
            "macro_recall": round(float(mac_r), 4),
            "macro_f1": round(float(mac_f1), 4),
            "per_class": per_class_wc,
            "confusion_matrix": cm_wc.tolist(),
            "confusion_matrix_labels": label_names,
        },
        "accuracy_2018_vs_dynamic_world_2018": {
            "reference": "Google Dynamic World 2018 (dry-season label_mode, 15 scenes) — PROXY ONLY, not ground truth",
            "caveat": (
                "2018 classification accuracy is UNVERIFIED. No authoritative in-situ ground truth "
                "exists for 2018 over Ward 35. Dynamic World 2018 is an automated deep-learning model "
                "output that over-predicts built-up surfaces on dry peri-urban soils. "
                "Agreement with DW is a proxy measure, not validation accuracy."
            ),
            "overall_agreement": round(float(oa_dw), 4),
            "macro_f1": round(float(mac_f1_dw), 4),
            "per_class": per_class_dw,
            "confusion_matrix": cm_dw.tolist(),
            "confusion_matrix_labels": label_names,
        },
        "shadow_claim": (
            "Topographic shadowing from quarry faces was identified as a candidate cause of "
            "water false positives, based on spectral similarity to water (suppressed NIR). "
            "No quantitative shadow mask test was performed. The '47%' figure previously stated "
            "has been REMOVED as unverified."
        ),
        "label_noise_note": (
            "Label noise from temporal mismatch (WorldCover 2021 applied to 2018 and 2025 imagery) "
            "is of unquantified extent. The '5-8% label noise' estimate stated in earlier drafts "
            "was an unverified guess and has been REMOVED."
        ),
    }

    with open(OUT_METRICS, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Metrics saved: {OUT_METRICS}")

    print("\n" + "=" * 70)
    print("Phase 2 (3-class) complete. Waiting for user 'confirmed'.")
    print("Change statistics (class-to-class transitions) withheld until approval.")
    print("=" * 70)

    return metrics, oa_wc, mac_f1, oa_dw, mac_f1_dw


if __name__ == "__main__":
    main()

