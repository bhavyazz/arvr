# UrbanLens

**Interactive visualisation of urban environmental change in Pattanagere locality, Bengaluru.**
Final-year academic project, RV College of Engineering.

The study area is the **Pattanagere locality within BBMP Ward 35 (Hemmigepura)**, not the whole ward.
The current deliverable is a Unity 6 desktop visualisation. An AR mode is planned but not implemented.

Full documentation (architecture, methodology, controls, setup, limitations and demonstration steps)
is in [`urbanlens/README.md`](urbanlens/README.md).

## Repository structure

- [`urbanlens/`](urbanlens/) — Project directory
  - [`pipeline/`](urbanlens/pipeline/) — Sentinel-2 export, NDVI/NDBI/NDWI, Random Forest classification and change statistics
  - [`unity_inputs/`](urbanlens/unity_inputs/) — Per-class overlay masks and JSON metrics for the Unity visualisation
  - [`unity/UrbanLens/`](urbanlens/unity/UrbanLens/) — Unity 6 desktop visualisation
  - [`backend/`](urbanlens/backend/) — FastAPI backend
  - [`reports/`](urbanlens/reports/) — Metrics, figures and the methodology decisions log

## Current status

| Component | Status |
|---|---|
| Data pipeline and land-cover classification | Completed; outputs feed the Unity project |
| Unity desktop visualisation (year switching, layer and combined controls, statistics dashboard, camera) | Working; controls tested in Play Mode |
| Accuracy and validation reporting | Completed; 2018 unverified, 2025 cross-year only |
| AR mode (AR Foundation, ARCore, plane placement) | Not implemented |
| Physical Android device testing | Not performed |

## Quick start

Open `urbanlens/unity/UrbanLens/` in Unity 6000.6.10f1, open `Assets/Scenes/SampleScene.unity` and press Play.
See [`urbanlens/README.md`](urbanlens/README.md) for controls, data details and the demonstration sequence.

## Design decisions

Methodology decisions are logged in [`urbanlens/reports/decisions.md`](urbanlens/reports/decisions.md).
