"""
config.py – Central configuration for the UrbanLens AR pipeline.

All tunable parameters live here. Any change to these values must also be
recorded in reports/decisions.md with a rationale.
"""

# ---------------------------------------------------------------------------
# Study area
# ---------------------------------------------------------------------------
# Study Area: "BBMP Ward 35 (Hemmigepura), which contains Pattanagere"
# Sourced from DataMeet 243-ward delimitation (2022 draft/KGIS, UDD 66 BBS 2022).
# Limitation: Ward 35 (~32.91 km²) is an administrative municipal ward that contains
# the Pattanagere locality in its northern section, but extends further south.
# Furthermore, the 243-ward setup was subject to subsequent legal restructuring
# toward a 225-ward framework.
STUDY_AREA_NAME = "BBMP Ward 35 (Hemmigepura), which contains Pattanagere"
STUDY_AREA_GEOJSON = "data/study_area/study_area.geojson"
WARD_SET_STATUS = "243-ward draft delimitation (July 2022 / KGIS)"
WARD_SET_LIMITATION = (
    "The 243-ward boundary was a draft delimitation notified in 2022 under "
    "UDD 66 BBS 2022 that was subsequently contested in courts and revised towards "
    "a 225-ward structure in late 2023. It is used here as the highest-resolution "
    "publicly available open-data GIS ward polygon containing the Pattanagere centroid."
)

# ---------------------------------------------------------------------------
# GEE image collection and cloud masking
# ---------------------------------------------------------------------------
GEE_PROJECT = "psychic-droplet-419414"          # Google Cloud project ID (verified academic/community tier)
S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"   # Sentinel-2 L2A Harmonized
CLOUDY_PIXEL_PERCENTAGE_MAX = 20                # % scene-level metadata filter
CLOUD_MASK_METHOD = "SCL"                       # Scene Classification Layer (SCL)
# SCL values to mask out:
# 3: Cloud shadow, 8: Cloud medium prob, 9: Cloud high prob, 10: Thin cirrus, 11: Snow
SCL_MASK_CLASSES = [3, 8, 9, 10, 11]

# Dry-season periods (Jan to Mar for both years as specified)
PERIODS = {
    2018: {"start": "2018-01-01", "end": "2018-03-31"},
    2025: {"start": "2025-01-01", "end": "2025-03-31"},
}

# Exact scene counts used in ImageCollection filters (<20% cloud):
# 2018: 7 scenes queried (SCL cloud-shadow masking leaves 6-7 valid observations per pixel)
# 2025: 14 scenes queried (SCL cloud-shadow/cloud probability masking leaves 10-14 valid observations)
S2_SCENE_COUNTS = {
    2018: 7,
    2025: 14
}

COMPOSITE_REDUCER = "median"                    # Median composite over valid pixels

# ---------------------------------------------------------------------------
# Water Threshold & Limitations (Phase 1 Approved)
# ---------------------------------------------------------------------------
WATER_NDWI_THRESHOLD = 0.3                      # Default threshold for water mask
WATER_SENSITIVITY_THRESHOLDS = [0.2, 0.4]       # Sensitivity testing thresholds
# Sensitivity Note:
# NDWI > 0.2: 2018 = 18.52 ha, 2025 = 17.19 ha (Change: -1.33 ha)
# NDWI > 0.3: 2018 = 13.40 ha, 2025 = 7.73 ha (Change: -5.67 ha) [DEFAULT]
# NDWI > 0.4: 2018 = 9.59 ha, 2025 = 1.44 ha (Change: -8.15 ha)
ZERO_NIR_EXPLANATION = (
    "Consistent-with-data explanation: Over deep clear water, pure water molecules "
    "absorb incident near-infrared radiation almost completely. Sen2Cor atmospheric "
    "correction subtracts path radiance and bottom-clips zero/negative surface "
    "reflectance to 0 DN. This explanation is consistent with SCL=6 (Water) and "
    "QA60=0, but is not a laboratory-proven causal proof in the absence of in-situ sampling."
)

# ---------------------------------------------------------------------------
# Sentinel-2 bands and resolutions
# ---------------------------------------------------------------------------
# B2: Blue, B3: Green, B4: Red, B8: NIR, B11: SWIR1, B12: SWIR2, SCL: Scene Class
S2_BANDS = ["B2", "B3", "B4", "B8", "B11", "B12", "SCL"]
S2_SCALE = 10                                   # metres per pixel

# ---------------------------------------------------------------------------
# Indices
# ---------------------------------------------------------------------------
# NDVI  = (B8 - B4) / (B8 + B4)      -> Vegetation
# NDBI  = (B11 - B8) / (B11 + B8)    -> Built-up
# NDWI  = (B3 - B8) / (B3 + B8)      -> Water
INDEX_NAMES = ["NDVI", "NDBI", "NDWI"]

# ---------------------------------------------------------------------------
# Export settings
# ---------------------------------------------------------------------------
EXPORT_SCALE = 10                               # metres (Sentinel-2 10m native)
EXPORT_CRS = "EPSG:32643"                       # UTM Zone 43N (projected CRS for Bengaluru)
PROCESSED_DIR = "data/processed"

# ---------------------------------------------------------------------------
# Land-cover classes (Phase 2 reference)
# ---------------------------------------------------------------------------
LAND_COVER_CLASSES = {
    1: "Vegetation",
    2: "Built-up",
    3: "Water",
    # NOTE: Class 4 (Other) has been DROPPED from the 3-class model.
    # Pixels with ESA WorldCover classes 40, 60, 100 are excluded from
    # training and evaluation (not merged into another class).
}

ESA_TO_PROJECT_CLASS = {
    10: 1,    # Tree cover     -> Vegetation
    20: 1,    # Shrubland      -> Vegetation
    30: 1,    # Grassland      -> Vegetation
    40: None, # Cropland       -> DROPPED (excluded from 3-class model; not merged)
    50: 2,    # Built-up       -> Built-up
    60: None, # Bare/sparse    -> DROPPED (excluded from 3-class model; not merged)
    80: 3,    # Permanent H2O  -> Water
    90: 3,    # Herbaceous wet -> Water  # UNUSED IN BENGALURU — 0 pixels in ward
    95: 3,    # Mangroves      -> Water  # UNUSED IN BENGALURU — 0 pixels in ward, coastal only
    100: None,# Moss/lichen    -> DROPPED (excluded from 3-class model; not merged)
}

# ---------------------------------------------------------------------------
# Classification Parameters (Phase 2 — 3-class model)
# ---------------------------------------------------------------------------
N_ESTIMATORS = 150          # trees (3-class rerun; was 200 in 4-class draft)
MAX_DEPTH = 16
RANDOM_STATE = 42
SPATIAL_BLOCK_SIZE = 500    # metres — spatial block size for train/test split
TEST_BLOCK_FRACTION = 0.25
# Stratified training sample per class (3-class model):
SAMPLE_PER_CLASS = {
    1: 5000,   # Vegetation
    2: 4500,   # Built-up
    3: 1500,   # Water (fewer reference pixels available)
}

# ---------------------------------------------------------------------------
# Blender Configuration
# ---------------------------------------------------------------------------
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"

LANDSAT_COLLECTION = "LANDSAT/LC08/C02/T1_L2"
LANDSAT9_COLLECTION = "LANDSAT/LC09/C02/T1_L2"
LST_SCALE_FACTOR = 0.00341802
LST_OFFSET = 149.0
KELVIN_TO_CELSIUS = -273.15
