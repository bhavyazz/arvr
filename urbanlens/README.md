# UrbanLens: Interactive Visualisation of Urban Environmental Change

**Research prototype:** a Unity 6 desktop visualisation of classified land-cover change for
Pattanagere locality within BBMP Ward 35 (Hemmigepura), Bengaluru, Karnataka, India.
Final-year academic project, RV College of Engineering.

**Status:** the desktop visualisation runs and its controls have been tested in Unity Play Mode.
The AR mode is **not implemented** (see [AR status](#ar-status)).

---

## Research objective

Show how land-cover classes (vegetation, built-up and water) differ between a 2018 and a 2025
classification of the same study area, and make the limits of those classifications explicit.
The application is a visualisation and evaluation aid. It does not establish causes of change.

## Study area

- **Locality:** Pattanagere, within BBMP Ward 35 (Hemmigepura), Bengaluru.
- **Coordinate system:** EPSG:32643 (WGS 84 / UTM zone 43N).
- **Bounding box:** 9.8 km x 9.2 km (`ward_bounds.json`).
- **Raster grid:** 980 x 920 pixels at 10 m.
- **Scene scale:** 1 Unity unit = 100 m, so the bounding box is 98 x 92 units.

## Architecture

```
urbanlens/
  pipeline/          Python: Sentinel-2 export, indices, Random Forest classification, change statistics
  unity_inputs/      Generated per-class PNG masks (2018, 2025) and JSON metrics
  unity/UrbanLens/   Unity 6 project (desktop visualisation)
    Assets/UrbanLens/Scripts/
      Core/          StudyAreaManager, LandCoverLayer, OverlayLayerController, ElevationRelief
      Data/          UrbanLensStats (typed read of stats.json and ward_bounds.json), MiniJson
      UI/            DashboardController (runtime uGUI dashboard)
      Camera/        OrbitCamera (orbit, pan, zoom, reset)
      Editor/        RenderQueueEnforcer (editor-time material render queues)
    Assets/Scenes/SampleScene.unity   Main scene (the UrbanLens scene)
  backend/           FastAPI (not used by the desktop visualisation)
  reports/           Metrics, figures and the methodology decisions log
```

### Runtime flow

1. `StudyAreaManager` loads `stats.json` and `ward_bounds.json` (text assets) into `UrbanLensStats`.
2. Each land-cover class is a `LandCoverLayer` on its own quad. Each layer holds 2018 and 2025
   masks and writes textures through a `MaterialPropertyBlock`, so shared material assets are not changed at runtime.
3. `OverlayLayerController` drives the combined overlay, which shows all classes in one image.
4. `DashboardController` builds the UI at runtime from the same manager and refreshes on every state change.
5. `OrbitCamera` handles camera input and ignores drags or scrolls that start over the dashboard.

### Render order

Vegetation draws at queue 3001, built-up at 3002, water at 3003, and the combined overlay at 3000.
`LandCoverLayer.RenderQueueFor` is the single source of truth. `RenderQueueEnforcer` (editor menu item
`UrbanLens/Enforce Layer Render Queues`) writes the values to the material assets, and
`LandCoverLayer` re-checks them at runtime, so the order holds even if the saved asset value drifts.

## Data processing methodology

Summarised here. Exact parameters live in the pipeline configuration and `reports/decisions.md`.

- **Source imagery:** Copernicus Sentinel-2 L2A surface reflectance, dry-season composites for each year, with cloud masking.
- **Indices:** NDVI, NDBI and NDWI, with per-pixel composites.
- **Classification:** supervised Random Forest on spectral bands and indices, producing vegetation, built-up and water classes.
- **Reference labels for 2025 validation:** ESA WorldCover 2021.
- **Outputs:** per-class PNG masks and `stats.json` (areas, pixel counts, accuracy, NDWI water statistics).

The Unity overlays are classification masks. They are **not** continuous NDVI, NDBI or NDWI rasters.

## Results shown in the application

All figures come from `Assets/UrbanLens/Data/stats.json`.

| Measure | 2018 | 2025 |
|---|---|---|
| Vegetation (classifier), ha | 2309.15 | 1932.42 |
| Built-up (classifier), ha | 927.68 | 1303.92 |
| Water (classifier), ha | 53.91 | 54.40 |
| Water (NDWI > 0.3 mask), ha | 13.40 | 7.73 |

NDWI water change: -5.67 ha (-42.3%). Classifier water and NDWI water are different measurements
and are reported separately.

## Accuracy and validation

- **2025 vs ESA WorldCover 2021:** overall accuracy 81.25%, macro F1 0.757.
  Per-class F1: Vegetation 0.839, Built-up 0.783, Water 0.648 (water precision 0.489, recall 0.960).
  This is **cross-year comparison**, not independent ground-truth accuracy.
- **2018:** status *unverified*. There is no authoritative 2018 ground truth. Agreement with a
  Dynamic World 2018 proxy is 58.1% (macro F1 0.528). This is proxy agreement, not accuracy.

## Limitations

- 2025 accuracy is validated against 2021 labels, so it is cross-year and not independent.
- 2018 accuracy is unverified.
- 88.9% of changed pixels lie at or next to a class boundary. Vegetation-to-built-up change is
  boundary-dominated and must not be presented as verified urban expansion.
- Causes of change are not attributed.
- Water precision is 0.489. Many predicted water pixels disagree with the reference.
- No verified elevation (DEM) data is included. Terrain relief is disabled and nothing has been estimated.
- The Unity masks are classification-derived. Continuous indices are not visualised.

## Features and controls

**Year:** 2018 and 2025 buttons, or keys `1` and `2`. All layers and the combined overlay update together.

**Layers:** independent Vegetation, Built-up and Water toggles, each with an opacity slider.
Keys `V`, `B`, `W`.

**Combined overlay:** shows all classes in one image and hides the individual layers.
Turning it off restores the individual layer visibility that was active before. Key `C`.
While the combined overlay is on, individual toggles do not show layers; turning a layer on exits combined mode first.

**Camera:**
- Right-drag: orbit
- Middle-drag: pan
- Scroll: zoom
- Reset view button, or key `R`

Drags and scrolls that start over the dashboard do not move the camera.

**Dashboard:** year status, layer controls, legend, area statistics, NDWI water statistics,
accuracy and validation, methodology, limitations, and terrain status.

**Terrain:** the exaggeration slider is disabled unless a real elevation raster with a known
metre range is assigned to `ElevationRelief`.

## Setup

**Requirements:** Unity 6000.6.10f1 (Universal Render Pipeline 17.6.0, Input System 1.20.1).

1. Open Unity Hub and add `urbanlens/unity/UrbanLens`.
2. Open `Assets/Scenes/SampleScene.unity`.
3. Press Play.

To regenerate the data, run the pipeline in `urbanlens/pipeline/`. Its requirements are listed in
the pipeline configuration. Google Earth Engine authentication is required for the export step.

## Demonstration

1. Open `SampleScene` and press Play. The dashboard appears on the left and the study area is centred.
2. Confirm the title reads "BBMP Ward 35 (Hemmigepura)" and the grid and bounding box are shown.
3. Click **2018**, then **2025**. The layers change and the year status line updates.
4. Turn off Built-up and Water. Turn on the **Combined overlay**. The three individual layers disappear.
5. Turn the combined overlay off. The previous layer visibility returns.
6. Drag with the right mouse button to orbit, the middle button to pan, and scroll to zoom. Press **Reset view**.
7. Scroll the dashboard. Check the statistics and the accuracy caveats.

## AR status

**Not implemented.** The project does not yet include AR Foundation or the ARCore XR plugin
(`Packages/manifest.json` contains neither). Implementing AR requires:

- Adding AR Foundation and the ARCore XR plugin with versions compatible with Unity 6000.6.10f1.
- Configuring the Android build target and XR plug-in management.
- A separate AR scene with an XR origin, an AR session and plane detection.
- Testing on a physical ARCore-supported Android device. Plane detection, placement and performance
  cannot be verified without one.

## Git

Unity generated folders (`Library/`, `Temp/`, `Obj/`, `Build/`, `Logs/`, `UserSettings/` and
Visual Studio/Rider project files) are listed in the repository `.gitignore`. If any were committed
earlier, remove them from the index without deleting local files:

```bash
git rm -r --cached urbanlens/unity/UrbanLens/Library urbanlens/unity/UrbanLens/Temp
```

## Future work

- AR mode with plane detection and study-area placement on Android.
- Elevation data, once a verified DEM is available for the study area.
- Independent ground-truth validation for 2018 and 2025.
- Continuous index visualisation, if continuous NDVI, NDBI and NDWI rasters are produced.
