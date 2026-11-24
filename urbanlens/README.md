# UrbanLens AR

**An Android AR application visualising urban environmental change in Pattanagere, Bengaluru.**
Final-year academic project, RV College of Engineering.

---

## Repository Structure

```
urbanlens/
  pipeline/      # GEE export, NDVI, classification, change detection, stats
  backend/       # FastAPI REST API
  unity/         # Unity 6 LTS AR project (C#)
  data/          # Raw and processed outputs (gitignored)
    study_area/  # GeoJSON boundary
    raw/         # GEE-exported GeoTIFFs
    processed/   # Classified rasters, change maps
  reports/       # Metrics, figures, change maps, decisions log
  README.md
```

## Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Pipeline core (GEE, Sentinel-2, NDVI/NDBI/NDWI) | 🔄 In Progress |
| 2 | Land-cover classification (ML, Random Forest) | ⏳ Pending |
| 3 | Change detection and statistics | ⏳ Pending |
| 4 | FastAPI backend | ⏳ Pending |
| 5 | Leaflet web preview | ⏳ Pending |
| 6 | Unity AR app | ⏳ Pending |

## Configuration

All tunable parameters are in [`pipeline/config.py`](pipeline/config.py):
- Study area path, GEE collections, cloud threshold
- Composite date ranges (2018 and 2025)
- Band names, export scale, CRS
- Classification parameters, LST scale factors

## Study Area

Pattanagere BBMP ward, Bengaluru West Zone, Karnataka, India.
Centre: 12.9143°N, 77.5014°E | Approx. area: ~7.7 km²

## Stack

- **Data processing:** Python 3.12, Google Earth Engine API, Rasterio, GeoPandas, scikit-learn
- **Backend:** FastAPI
- **AR App:** Unity 6 LTS, AR Foundation, ARCore, Android

## Setup

```bash
# Clone and set up Python environment
pip install earthengine-api rasterio geopandas scikit-learn fastapi uvicorn

# Authenticate with GEE
earthengine authenticate

# Run boundary visualisation (Phase 1 Step 1)
python pipeline/visualize_boundary.py
```

## Design Decisions

All methodology decisions are logged in [`reports/decisions.md`](reports/decisions.md).

