# UrbanLens AR

**An Android AR application visualising urban environmental change in Pattanagere, Bengaluru.**  
Final-year academic project, RV College of Engineering.

---

## Repository Structure

- [`urbanlens/`](urbanlens/) — Core project directory
  - [`pipeline/`](urbanlens/pipeline/) — Sentinel-2 data ingestion, index computation (NDVI/NDBI/NDWI), 3-class Random Forest land-cover classification, and change detection
  - [`reports/`](urbanlens/reports/) — Metrics, generated figures, methodology decisions log (`decisions.md`), and final summary (`results_summary.md`)
  - [`data/study_area/`](urbanlens/data/study_area/) — BBMP Ward 35 (Hemmigepura) and Pattanagere GeoJSON study area boundaries
  - [`unity_inputs/`](urbanlens/unity_inputs/) — Generated overlay textures and JSON metrics for the AR application
  - [`backend/`](urbanlens/backend/) — FastAPI backend
  - [`unity/`](urbanlens/unity/) — Unity 6 LTS AR project

For complete project documentation, installation instructions, and design decisions, please refer to [`urbanlens/README.md`](urbanlens/README.md).
