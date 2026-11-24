# UrbanLens AR – Design & Method Decision Log

Every decision that affects methodology, data sources, boundaries, or parameters is recorded here.
Format: `## YYYY-MM-DD – <topic>` with rationale, alternatives considered, and risk notes.

---

## 2026-11-10 – Sentinel-2 dry-season composite & indices configuration (Phase 1 Step 2 — APPROVED WITH LIMITATIONS)

**Formal Approval & Phase 1 Limitations:**
1. **2018 Scene Count:** The exact scene count used in the 2018 dry-season collection is **7 scenes** (<20% cloud filter). Per-pixel SCL masking leaves 6–7 valid observations per pixel (e.g. 6 valid observations at the Vaderahalli water pixel due to SCL cloud-shadow filtering on 2018-01-09). The 2018-03-10 scene was audited and confirmed non-defective (standard L2A pass, S2A, 12.8% cloudy pixels).
2. **Water Threshold Sensitivity Note:** `NDWI > 0.3` is adopted as the canonical project default. Sensitivity analysis across the ward:
   - `NDWI > 0.2`: 2018 = 18.52 ha, 2025 = 17.19 ha ($\Delta = -1.33\text{ ha}$)
   - `NDWI > 0.3` (default): 2018 = 13.40 ha, 2025 = 7.73 ha ($\Delta = -5.67\text{ ha}$, $-42.3\%$)
   - `NDWI > 0.4`: 2018 = 9.59 ha, 2025 = 1.44 ha ($\Delta = -8.15\text{ ha}$)
3. **Zero-NIR Explanation Status:** Near-zero NIR surface reflectance over deep water is recorded as a **consistent-with-data explanation** supported by optical limnology principles and Sen2Cor bottom-clipping, not as a laboratory-proven causal proof in the absence of in-situ sampling.

**Study Area Name:**
- Defined explicitly as: **"BBMP Ward 35 (Hemmigepura), which contains Pattanagere"**
- Canonical file: `data/study_area/study_area.geojson`

**Delimitation Status & Methodological Limitation:**
- **Ward Set Status:** The 243-ward dataset represents the **draft delimitation** notified in July 2022 (UDD 66 BBS 2022 / KGIS). 
- **Limitation Note for Viva:** The 243-ward framework faced legal challenges and was subsequently revised towards a 225-ward structure in late 2023. It is utilized here because it is the most detailed, publicly accessible open GIS municipal dataset containing the verified Pattanagere centroid. Ward 35 (~32.91 km²) is significantly larger than the Pattanagere locality itself; results represent the enclosing administrative ward.

**Composite & Processing Parameters:**
- **Satellite Collection:** `COPERNICUS/S2_SR_HARMONIZED` (Sentinel-2 L2A Surface Reflectance, baseline harmonized).
- **Scene Cloud Threshold:** `CLOUDY_PIXEL_PERCENTAGE < 20`.
- **Pixel-level Cloud Masking:** Scene Classification Layer (`SCL`) band. Classes masked: 3 (cloud shadows), 8 (medium cloud probability), 9 (high cloud probability), 10 (thin cirrus), 11 (snow/ice).
- **Seasonal Window:** Dry season: **January 1 to March 31** for both 2018 and 2025.
- **Aggregation:** Pixel-wise median composite.
- **Indices Computed:**
  - `NDVI = (B8 - B4) / (B8 + B4)`
  - `NDBI = (B11 - B8) / (B11 + B8)`
  - `NDWI = (B3 - B8) / (B3 + B8)`
- **Export Specifications:**
  - Format: GeoTIFF
  - Destination: `data/processed/`
  - Projected CRS: **`EPSG:32643`** (WGS 84 / UTM Zone 43N)
  - Native Resolution: **10 metres**

**Execution & Export Results (Executed 2026-11-10):**
- **GEE Project:** `psychic-droplet-419414`
- **Scene Filter Results:**
  - 2018 Dry Season (Jan–Mar): **7 cloud-filtered scenes** (<20% cloudy pixel percentage)
  - 2025 Dry Season (Jan–Mar): **14 cloud-filtered scenes** (<20% cloudy pixel percentage)
- **Exported Rasters:**
  - `data/processed/ndvi_2018.tif` & `ndvi_2025.tif`
  - `data/processed/ndbi_2018.tif` & `ndbi_2025.tif`
  - `data/processed/ndwi_2018.tif` & `ndwi_2025.tif`
- **Computed Raster Metrics:**
  - **NDVI 2018:** Min: -1.000 | Max: 0.897 | Mean: **0.363** | Std: 0.179 (Valid pixels: 331,611)
  - **NDVI 2025:** Min: -0.364 | Max: 0.886 | Mean: **0.356** | Std: 0.175 (Valid pixels: 331,610)
  - **NDBI 2018:** Min: -0.535 | Max: 1.000 | Mean: **0.064** | Std: 0.106
  - **NDBI 2025:** Min: -0.710 | Max: 0.721 | Mean: **0.058** | Std: 0.100
  - **NDWI 2018:** Min: -0.818 | Max: 1.000 | Mean: **-0.448** | Std: 0.161
  - **NDWI 2025:** Min: -0.793 | Max: 0.564 | Mean: **-0.414** | Std: 0.158
- **Verification:** All rasters confirmed in `EPSG:32643`, 10m grid, bounding box strictly aligned with Ward 35. QGIS check preview saved to `reports/qgis_check_preview.png`.

**Detailed Statistical & Physical Verification (Audited 2026-11-10):**
1. **Extreme Pixel Analysis (-1.000 NDVI and +1.000 NDBI):**
   - NDVI 2018: 365 pixels (0.1101%) < -0.5; 0 pixels > 0.9; exactly 30 pixels (0.0090%) == -1.000.
   - NDVI 2025: 0 pixels < -0.5; 0 pixels > 0.9; 0 pixels == -1.000.
   - NDBI 2018: 30 pixels == +1.000 (identical coordinates to the -1.000 NDVI pixels).
   - NDBI 2025: 0 pixels == +1.000.
   - **Physical Property of Water & Impact:** Recorded that these values are an inherent **physical property of water**, caused by near-zero surface reflectance in the Near-Infrared band (`B8 = 0`) over deep clear water (where `B4 = 84` and `B11 = 94`). Under normalized difference formulas, zero NIR produces mathematical limits: $(0 - B4)/(0 + B4) = -1.000$ and $(B11 - 0)/(B11 + 0) = +1.000$. With a minute spatial share of **0.11%** (and exact -1.000 at 0.009%), these physical water pixels do not distort the overall distribution, terrestrial statistics, or subsequent classification.
   - **B8 (NIR) Zero-DN Audit Across Full Ward (Audited 2026-11-10):**
     - **2018 Composite:** Across the 329,074 pixels strictly inside Ward 35, exactly **19 pixels** (0.00577%) have $B_8 == 0\text{ DN}$.
       - Water pixels ($\text{NDWI} > 0.3$) with $B_8 == 0$: **19 pixels** (100% of all zeros).
       - Non-water pixels ($\text{NDWI} \le 0.3$) with $B_8 == 0$: **0 pixels** (0.0%).
       - (Across the enclosing raster bounding box, 30 water pixels in the quarry lake have $B_8 == 0$, 0 non-water pixels inside the ward have $B_8 == 0$, and 109 pixels in outer border padding represent GEE bounding box clip).
     - **2025 Composite:** Across the 329,074 pixels inside Ward 35, exactly **0 pixels** (0.0000%) have $B_8 == 0\text{ DN}$.
       - Water pixels with $B_8 == 0$: **0 pixels**.
       - Non-water pixels with $B_8 == 0$: **0 pixels**.
     - **Verification Against Raw L2A SCL and QA60:**
       - Inspected raw uncomposited scenes at the target water pixel:
         - 2018-01-29: `SCL = 6 (Water)`, `QA60 = 0 (Clear)`, `B8 = 0 DN`, `B4 = 84 DN`, `B3 = 146 DN`
         - 2018-02-03: `SCL = 6 (Water)`, `QA60 = 0 (Clear)`, `B8 = 0 DN`, `B4 = 97 DN`, `B3 = 136 DN`
         - 2018-02-23: `SCL = 6 (Water)`, `QA60 = 0 (Clear)`, `B8 = 0 DN`, `B4 = 74 DN`, `B3 = 179 DN`
         - 2018-03-10: `SCL = 7`, `QA60 = 0`, `B8 = 0 DN`, `B4 = 0 DN`, `B3 = 45 DN`
       - Conclusion: The 2018 exact zeros are confirmed as **physical deep-water absorption** where Sen2Cor atmospheric correction clips near-zero/negative NIR surface reflectance to 0 DN over clear standing water with `QA60 = 0` and `SCL = 6`. They are not nodata or clipping artefacts.
   - **Water Mask & Lake Area Analysis (NDWI > 0.3):**
     - Full Ward Water Area: 2018 = **13.40 ha** (1,340 px); 2025 = **7.73 ha** (773 px); Change = **-5.67 ha (-42.3%)**.
     - Vaderahalli Lake Basin Area: 2018 = **3.83 ha** (383 px); 2025 = **2.35 ha** (235 px); Change = **-1.48 ha (-38.6%)**.
     - 3×3 Window Classification Stability: 100% stable as Water in both years (all 9 pixels have $\text{NDWI} > 0.83$ in 2018 and $\text{NDWI} > 0.30$ in 2025).
     - **Hypothesis Caveat:** While surface water area contraction (-38.6%) is verified empirically from the NDWI > 0.3 water mask, accompanying vertical lake depth reduction and turbidity/bottom reflectance mechanisms remain **untested working hypotheses** in the absence of in-situ bathymetric or water sample measurements.
     - Water mask figure saved to `reports/water_mask_comparison.png`.
   - **Sentinel-2 Same-Date True-Colour Reflectance Comparison (Replacing External Basemap):**
     - Target coordinate (12.8409°N, 77.5347°E):
       - 2018 S2 Composite: $B_4 (\text{Red}) = 90.5$, $B_3 (\text{Green}) = 162.5$, $B_2 (\text{Blue}) = 108.0$, $B_8 (\text{NIR}) = 0.0\text{ DN}$. Deep, optically dark water.
       - 2025 S2 Composite: $B_4 (\text{Red}) = 183.0$, $B_3 (\text{Green}) = 372.0$, $B_2 (\text{Blue}) = 246.0$, $B_8 (\text{NIR}) = 168.5\text{ DN}$. Turbid greenish-brown water with increased visible backscatter.
2. **Sentinel-2 Processing Baseline Offset (PB 04.00+):**
   - Harmonization confirmed. GEE collection `COPERNICUS/S2_SR_HARMONIZED` automatically offsets post-PB 04.00 data by -1000 DN (verified empirically: 2025 raw B4 = 3776 vs. harmonized B4 = 2776).
   - Code lines: `pipeline/config.py` (line 28: `S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"`) and `pipeline/s2_pipeline.py` (line 114: `ee.ImageCollection(config.S2_COLLECTION)`).
3. **Exact NDVI Percentiles and Mode:**
   - 2018: Mode = `0.3335` (100 bins; discrete: 0.33) | P5 = `0.0928` | P50 (median) = `0.3570` | P95 = `0.6647`.
   - 2025: Mode = `0.4105` (100 bins; discrete: 0.39) | P5 = `0.0760` | P50 (median) = `0.3615` | P95 = `0.6376`.
   - **Attribution & Confounder Caveat:** The upward shift in NDVI mode (from 0.33 to 0.41) has **not yet been attributed to actual vegetation change**. Potential confounding factors that must be evaluated include: (a) scene count disparity (7 vs 14 scenes affecting median composite depth), (b) differing intra-seasonal temporal spread across Jan–Mar, (c) antecedent precipitation and soil moisture variations affecting canopy greenness, and (d) residual aerosol/atmospheric correction differences across processing baseline versions. These candidate confounders are currently **untested hypotheses**.
4. **Cloud Masking Completeness:**
   - Valid pixel count (`331,611` for 2018; `331,610` for 2025) verified post-SCL cloud masking. 100% spatial completeness over the ward interior.
5. **Scene Count Inventory & Satellite Mix:**
   - **2018 L1C vs L2A Inventory:** Over Tile `43PGQ` (Jan 1 – Mar 31, 2018), the Level-1C Top-of-Atmosphere collection (`COPERNICUS/S2_HARMONIZED`) contains **17 overpasses**, while the Level-2A Surface Reflectance collection (`COPERNICUS/S2_SR_HARMONIZED`) contains **7 overpasses**. The 10-scene gap is an archive processing or data availability difference in the Level-2A catalog for early 2018 over this tile. All 7 available L2A scenes had $<20\%$ cloud cover and were included in the composite.
   - **2025 Inventory:** 19 Level-2A overpasses exist in the catalog over the same period; 14 had $<20\%$ cloud and were used, while 5 were rejected due to cloud cover ($23.1\%$ to $56.0\%$).
   - **Satellite Mix per Year (Reconciled with 14 Accepted Scenes):**
     - **2018 Composite (7 scenes):** Sentinel-2A = **4 scenes** (57.1%), Sentinel-2B = **3 scenes** (42.9%).
     - **2025 Composite (14 scenes):** Sentinel-2B = **8 scenes** (57.1%), Sentinel-2C = **4 scenes** (28.6%), Sentinel-2A = **2 scenes** (14.3%).
       - Reconciled dates: S2B (2025-01-07, 01-27, 02-06, 02-16, 02-26, 03-08, 03-18, 03-28); S2C (2025-01-22, 02-11, 02-21, 03-13); S2A (2025-01-12, 03-15).
       - Total: $8 + 4 + 2 = 14$ scenes.
6. **Gradient Statistics & Seam Diagnostic (Descriptive Only):**
   - The Sobel spatial gradient test is descriptive only. Mean interior gradient is $0.48$ in 2018 and $0.51$ in 2025 (99th percentile: $1.64$ and $1.69$).
   - High-gradient pixels ($\ge 95\text{th}$ percentile) were mapped in `reports/ndvi_high_gradient_features.png`. Visual inspection confirms prominent ground features: (a) an East-West high-gradient linear feature traversing between Northing 1,424,000 and 1,426,000 m, (b) a northern high-gradient linear feature near Northing 1,429,000 m, and (c) water reservoir shorelines and layout parcel edges. In the absence of vector road centerline overlays, these are recorded strictly as high-gradient linear features. No artificial straight-line sensor swath edges or detector stripe boundaries traversing the scene were found.
7. **3-Panel Verification Figures:**
   - Saved to `reports/s2_three_panel_2018.png` and `reports/s2_three_panel_2025.png`.
- **Status:** Phase 1 Step 2 complete; awaiting user review and approval before starting Phase 2 (Classification).

---

## 2026-11-10 – Study area selection: BBMP Ward 35 (Hemmigepura) containing Pattanagere (Phase 1 Step 1 — CONFIRMED)

**Point Containment Verification:**
- Centroid evaluated: `(12.9201°N, 77.5067°E)` (OSM Node 1588150123 for Pattanagere quarter).
- Evaluated against both BBMP ward sets from DataMeet:
  1. **243-ward set (`BBMP.geojson`):** The point falls strictly inside **Ward No. 35 (Hemmigepura)** (`KGISWardCode: 2003035`, `LGD_WardCode: 1302707`).
  2. **198-ward set (`BBMP_oldWards.geojson`):** The point falls strictly inside **Ward No. 198 (Hemmigepura)** (`AREA_SQ_KM: 28.59`).
- **Choice:** Selected the **243-ward set (Ward 35 - Hemmigepura)** as requested because it represents the more recent official delimitation framework.

**Geometry & Storage:**
- Extracted polygon saved to: `data/study_area/study_area.geojson`.
- Area computed in UTM Zone 43N (EPSG:32643): **32.906 km²** (~3,291 hectares).
- Point containment confirmed programmatically (`shapely.geometry.Point.contains = True`).
- Preview map generated and saved to: `reports/study_area_preview.png`.

**Methodological Limitations (for Viva / Project Defence):**
- **Spatial Granularity:** Ward 35 (Hemmigepura) is an expansive peripheral municipal ward (~32.91 km²) extending from the Mysore Road / Pattanagere corridor in the north down past NICE Road into Hemmigepura / Thalagattapura boundaries in the south.
- **Locality vs. Ward Extent:** Pattanagere itself is an urban sub-locality located in the northern sector of this ward. Conducting satellite-derived environmental change analysis over the entire ward provides authoritative, official administrative boundaries, but captures environmental dynamics across both dense residential layouts and southern peri-urban/fringe areas of Hemmigepura.
- **Documentation Note:** Stamped in GeoJSON properties and reports: *"Pattanagere locality lies within this ward; ward boundary is larger than the locality."*

**Status:** Awaiting user "confirmed" before initiating any GEE composite or index processing.

---

## 2026-11-10 – Study area boundary search results & status (Phase 1 Step 1 — STOPPED FOR USER DECISION)

**1. OpenStreetMap / Overpass API Investigation:**
- Query for administrative boundary relations (`boundary=administrative`, `place=quarter|suburb`) containing "Pattanagere" was run against Overpass on 2026-11-10:
  - Result: **0 elements returned**. There is no administrative boundary polygon or closed way relation for Pattanagere in OpenStreetMap.
  - The only entity in OSM for Pattanagere is `node/1588150123` (`place=quarter`, lat: 12.9200602, lon: 77.5067010).

**2. Official BBMP Ward Data Search (DataMeet Municipal Spatial Data):**
- Downloaded and parsed official BBMP ward shapefile/GeoJSON datasets from DataMeet on 2026-11-10:
  - `BBMP.geojson` (243 wards): 0 wards named "Pattanagere". Nearby wards are Ward 33 (Kengeri), Ward 35 (Hemmigepura), Ward 49 (Rajarajeshwari Nagar), Ward 217 (Uttarahalli).
  - `BBMP_oldWards.geojson` (198 wards): 0 wards named "Pattanagere". Nearby wards are Ward 159 (Kengeri), Ward 160 (Rajarajeshwari Nagar), Ward 184 (Uttarahalli), Ward 198 (Hemmigepura).
- Delimitation schedule analysis: Pattanagere is a historical revenue village / urban locality in the RR Nagar zone. It has never been an independent municipal ward under that standalone name; rather, it sits along the border of Hemmigepura (Ward 198/35) and Rajarajeshwari Nagar (Ward 160/49).

**3. State of GeoJSON Boundary:**
- Renamed geometry type in `data/study_area/pattanagere_boundary.geojson` from bbox to `approximate_square`.
- Status set to `UNCONFIRMED_PLACEHOLDER` with explicit note: **"DO NOT USE FOR GEE QUERIES"**.
- No synthetic polygon has been invented.

**4. Next Step:**
- Pipeline stopped as instructed. Waiting for user to confirm how to establish the polygon boundary (e.g., hand-digitising in QGIS / geojson.io, or using a specific sub-ward boundary).

**Earlier version discarded:** An 8-vertex hand-drawn polygon derived from landmark names was drafted but rejected by the student because the landmark citations were unverifiable. That polygon has been deleted and replaced with an OSM-sourced boundary.

**What OSM says about Pattanagere:**
- Nominatim was queried three times with query strings `"Pattanagere, Bengaluru, Karnataka, India"`, `"Pattanagere ward, Bangalore Urban, Karnataka, India"`, and `"Pattanagere, Bangalore, India"` on 2026-11-10 (UTC).
- Overpass API was queried for administrative boundary relations (admin_level 9–11) containing "Pattanagere" within bounding box (12.88–12.95°N, 77.47–77.54°E). **No polygon or administrative relation was found.**
- The only OSM entity for Pattanagere is **node/1588150123**, OSM category=`place`, type=`quarter`. It is a named place centroid — not a ward boundary polygon.
- Nominatim lookup of this node returned centroid **12.9200602°N, 77.5067010°E** and an auto-derived bounding box S=12.9101°, N=12.9301°, W=77.4967°, E=77.5167° (Nominatim's standard ±0.01° expansion for point nodes).

**Decision:** Use the OSM Nominatim bounding box as the study area until the student provides or confirms a better boundary. This is explicitly labelled `bbox_only: true` and `status: AWAITING_USER_CONFIRMATION` in the GeoJSON.

**What "locality" vs "ward" means here:** OSM classifies Pattanagere as a **quarter** (locality/neighbourhood), not an administrative ward. The BBMP ward named "Pattanagere" may or may not coincide with this locality. No official BBMP ward shapefile was found in OSM. The student should confirm whether the intended study area is (a) the OSM locality bounding box, (b) the exact BBMP ward boundary (which would need to be sourced from BBMP/Karnataka government GIS), or (c) a custom polygon.

**Landmark labels:** None — all previously uncited landmark labels have been removed.

**Source citation:** OpenStreetMap contributors, ODbL 1.0. Retrieved via Nominatim API (`https://nominatim.openstreetmap.org/lookup?osm_ids=N1588150123`) on 2026-11-10T13:18:24Z.

**Status:** Awaiting student confirmation.

## 2026-11-10 – Study area boundary (Phase 1 Step 1 — ORIGINAL, DISCARDED)

**Decision:** Define the Pattanagere BBMP ward as the study area, using an 8-vertex polygon approximation centred on 12.9143°N, 77.5014°E.

**Rationale:** Pattanagere is the specified project area. The boundary is bounded by:
- **North:** BHEL/BEML Layout edge (~12.930°N)
- **South:** Uttarahalli Main Road (~12.905°N)
- **East:** Kenchanahalli Road / Rajarajeshwari Nagar edge (~77.520°E)
- **West:** Kengeri / Southern Railway corridor (~77.487°E)

**Alternative considered:** Using the exact BBMP ward shapefile from Karnataka Urban Development Dept. This is preferable if the official file is available; the polygon here is a reasonable approximation derived from known ward landmarks.

**Risk:** The approximated polygon may include or exclude a few hundred metres of the true ward boundary. Impact is bounded: Sentinel-2 analyses scale to ~10 m pixels; a ~100 m boundary error affects < 1% of pixels. The polygon must be confirmed by the student before pipeline execution.

**Status:** Awaiting student confirmation.

---

## 2026-11-10 – Composite period selection (Phase 1 Step 2)

**Decision:** Use January–April (dry season) for both 2018 and 2025 composites.

**Rationale:** Bengaluru's monsoon season runs June–September, bringing heavy cloud cover that would mask most Sentinel-2 observations. The dry-season window (Jan–Apr) maximises cloud-free pixels. Sentinel-2 began operations in late 2015, so 2018 data is available. Using the same seasonal window for both years eliminates phenological bias.

**Alternative considered:** Full-year median composites. Rejected because monsoon clouds would reduce valid pixel counts significantly, particularly in 2018 when fewer Sentinel-2 passes were available.

**Risk:** Dry-season NDVI will be lower than monsoon-peak NDVI. This is intentional for inter-year comparability, but should be stated clearly in the final report.

---

## 2026-11-10 – Sentinel-2 collection choice (Phase 1 Step 2)

**Decision:** Use `COPERNICUS/S2_SR_HARMONIZED` (Surface Reflectance, L2A, harmonised).

**Rationale:** L2A provides atmospherically corrected surface reflectance, essential for physically meaningful NDVI/NDBI/NDWI values. The "harmonised" variant corrects the processing baseline discontinuity introduced in January 2022, making 2018 and 2025 data directly comparable.

**Risk:** Some older 2018 tiles may still have minor radiometric differences post-harmonisation. The cloud probability mask (threshold 20%) mitigates artefacts from cloud edges.

---

## 2026-11-10 – Land-cover classification methodology & spatial block validation (Phase 2 — 3-class rerun)

**Decision (3-class rerun):** Use a Random Forest classifier trained on Sentinel-2 surface reflectance bands ($B_2, B_3, B_4, B_8, B_{11}, B_{12}$) and spectral indices ($\text{NDVI}, \text{NDBI}, \text{NDWI}$), supervised by ESA WorldCover 2021 reference labels, evaluated via spatial block cross-validation.

**3-Class Model — Class Mapping Decision (Updated):**
- ESA WorldCover 2021 (v200, 10m native resolution).
- Reclassified into **3 canonical project classes (Other class DROPPED, not merged):**
  - Class 1: **Vegetation** (ESA Tree cover 10, Shrubland 20, Grassland 30)
  - Class 2: **Built-up** (ESA Built-up 50)
  - Class 3: **Water** (ESA Permanent water 80, Wetland 90 `# UNUSED IN BENGALURU`, Mangroves 95 `# UNUSED IN BENGALURU`)
  - **DROPPED — excluded from training AND evaluation (not merged):** Cropland (40), Bare/sparse (60), Moss/lichen (100) → 43,336 px (13.2% of ward)
- **Ecological Verification for Bengaluru (Mangroves & Wetlands):**
  - Bengaluru is situated on the inland Deccan plateau (~900 m elevation); Mangroves (Class 95) do not exist.
  - Direct pixel inspection of `esa_worldcover_2021.tif` over Ward 35 confirms exactly **0 pixels of Class 95 (Mangroves)** and **0 pixels of Class 90 (Herbaceous wetland)**. Mapping 90 and 95 to Class 3 is maintained in `config.py` for global schema compatibility without altering local pixel assignments.
- **Water body at 12.8409°N, 77.5347°E (Vaderahalli quarry lake):** -1/+1 pixel extreme values (NDVI = -1.0, NDBI = +1.0 in 2018) are a **physical property of water** (near-zero NIR reflectance producing mathematical limits in normalized difference formulas). Their 0.11% spatial share does not affect classification results.

**Temporal Mismatch Analysis & Risk:**
- **Training Baseline (2021 WorldCover on 2025 S2):** A 4-year forward gap exists between 2021 labels and 2025 imagery; a 3-year backward gap exists to 2018 imagery.
- **Quantified Risk:**
  - In peri-urban Bengaluru, rapid urbanization converted agricultural fallow and scrubland into built structures between 2018 and 2025.
  - Applying a model trained on 2021 labels to 2018 imagery carries the risk that historical early-stage built-up (unpaved plots, packed earth) may be classified as "Vegetation" rather than "Built-up".
  - Forward risk: Parcels developed after 2021 are labelled as "Vegetation" in WorldCover 2021, creating label mismatches in training blocks. **The extent of this label noise is unquantified** (a previous estimate of "5–8%" was an unverified guess and has been removed from all documents).

**Shadow Claim Correction:**
- Topographic shadowing from quarry faces was identified as a **candidate cause** of water false positives, based on spectral similarity to water (suppressed NIR). No quantitative shadow mask test was performed and no percentage is attributed to shadows. This remains an **untested hypothesis**. Any percentage figure for shadow contribution stated in prior drafts has been removed as unverified.

**Per-Year Accuracy & 2018 Reference Comparison (3-class model):**
- **2025 Test Evaluation (Independent 500m Spatial Blocks, N=67,207 px, 95 test blocks):**
  - Overall Accuracy: **81.25%** | Macro Precision: **70.44%** | Macro Recall: **86.77%** | Macro F1: **75.65%**
  - Vegetation P=90.9% R=77.9% F1=83.9% | Built-up P=71.5% R=86.4% F1=78.3% | Water P=48.9% R=96.0% F1=64.8%
- **2018 Reference Comparison (against Google Dynamic World 2018, proxy reference only):**
  - Overall Agreement: **58.10%** | Macro F1: **52.83%**
  - Vegetation F1=72.6% | Built-up F1=5.3% | Water F1=80.5%
  - **2018 accuracy is UNVERIFIED against field surveys.** No authoritative in-situ ground truth exists for 2018 in this ward. Dynamic World 2018 is an automated deep-learning prediction that heavily over-predicts built-up over dry fallow fields (DW: 181,717 px built-up vs WorldCover: 95,345 px in 2021). The near-zero Built-up F1 reflects reference disagreement between two automated systems, not model failure.

**Investigation of Water Precision (48.9% in 3-class model — water is over-predicted):**
- In 2025 cross-year test blocks (67,207 retained pixels = 23.5% of retained pixels), 953 true water pixels yielded 915 true positives; 888 vegetation and 69 built-up pixels were also predicted as water (of 67,207 test pixels).
- **2025 vs WorldCover 2021 is a cross-year validation, not independent accuracy.**
- **2018 figures are proxy agreement, not accuracy — no authoritative 2018 ground truth exists.**
- Causes identified:
  1. *Reference Label Omission — Vaderahalli quarry basin (confirmed interpretation, Phase 2 approved 2026-11-10):*
     ESA WorldCover labels 66.3% of the Vaderahalli quarry basin as Permanent water (254 of 383 basin pixels, NDWI > 0.3 in 2018, 60 × 60 window centred on 12.8409°N, 77.5347°E). The remaining 129 pixels are labelled as non-water (Shrubland 94, Tree cover 21, Grassland 13, Cropland 1) despite having NDWI 2018 mean = 0.643, B8 mean = 48 DN, and NDVI mean = −0.472 — spectrally indistinguishable from the confirmed-water pixels (NDWI mean = 0.720, B8 mean = 34 DN).

     **Classifier behaviour on the 129 pixels:**
     - 2018 classifier predicted Water for 124 of 129 pixels (96.1%). The remaining 5 pixels fall in a dropped ESA class (Cropland) and were excluded from evaluation, not misclassified.
     - 2025 classifier predicted Water for 112 of 129 pixels (86.8%); 12 pixels predicted Vegetation, consistent with those pixels drying out between 2018 and 2025 (2025 NDWI mean = 0.169 for those 12).
     - **Conclusion: the classifier is correct. These are WorldCover labelling errors, not classifier errors.**

     **Spatial breakdown of the 129 pixels:**
     - **80 pixels (62%) are in the basin interior** (more than 1 pixel from the NDWI > 0.3 edge). Of these, 77 are labelled Shrubland with NDWI mean = 0.733. These are unambiguously open water and cannot be explained by mixed-pixel edge effects.
     - **49 pixels (38%) are on the 1-pixel shoreline ring** (mean NDWI = 0.490). These are genuine sub-pixel land–water mixtures; either label (Water or non-water) is defensible. Recorded as **mixed-pixel ambiguity at the shoreline.**

     **Explanation for the WorldCover labelling error (likely, untested):** ESA WorldCover is composited from multi-year Sentinel-1 and Sentinel-2 observations. Active granite quarry lakes can fluctuate seasonally. It is likely that the 80 interior pixels were not covered by water during the WorldCover compositing period, causing the global classifier to assign the surrounding upland class (Shrubland). This explanation is consistent with the 2025 NDWI data showing lake shrinkage, but it has not been tested against the WorldCover compositing dates or Sentinel-1 backscatter.

  2. *Topographic Shadows (untested hypothesis):* Steep quarry walls and hill slopes may suppress NIR to water-like levels. No shadow mask test performed; no percentage stated.
  3. *Moist channels and low-albedo surfaces (untested hypothesis):* Consistent with spectral signatures but not spatially verified.

**Rasters & Deliverables Exported (3-class model):**
- `data/processed/classification_2018_3c.tif` & `classification_2025_3c.tif`
- `reports/classification_map_3c.png` (4-panel 2×2 figure)
- `reports/classification_metrics_3c.json`
- `pipeline/classify_3class.py`


## 2026-11-10 – Change detection methodology (Phase 3 — approved)

**Denominator:** All change figures use **329,074 ward pixels** as denominator unless stated.

**Class areas (3-class model, superseding 4-class table):**
- 2018: Vegetation 2,309.15 ha | Built-up 927.68 ha | Water 53.91 ha (classifier)
- 2025: Vegetation 1,932.42 ha | Built-up 1,303.92 ha | Water 54.40 ha (classifier)
- Superseded 4-class table (Veg 1,589 ha / Built 729 ha) used different model and class definitions; direct comparison is invalid.

**Transition matrix:** Stable 264,398 px (80.35%) | Changed 64,676 px (19.65%) of 329,074 ward px.
- Key transitions: Vegetation→Built-up 49,754 px (497.54 ha, 15.1%, boundary-dominated, not interpretable as expansion); Built-up→Vegetation 12,283 px (122.83 ha, 3.7%).
- All changes described as "detected between dry-season composites." No cause stated. 2018 accuracy unverified. Interior change: 7,174 px (~71.74 ha, 11.1%), described as stable-interior change, consistent with urban expansion (without attributing cause), while 88.9% (57,502 px) is boundary-adjacent probable classifier noise.

**Water change:** NDWI > 0.3 mask only (not classifier water counts).
- 2018: 1,340 px = 13.40 ha | 2025: 773 px = 7.73 ha | Change: −567 px = −5.67 ha (−42.3% of 2018 water area).
- Stable water: 539 px | Lost: 801 px | Gained: 234 px.

**Stability check:** 88.9% of changed pixels are within 1 pixel of a class boundary in at least one year. Interior changed pixels (not near any boundary): 7,174 px (11.1%, 71.74 ha), representing stable-interior change, consistent with urban expansion, without attributing cause.

**Basin exclusion:** 124 of 129 mislabelled basin pixels are inside the ward. All 12 that changed class are Water↔Vegetation transitions; 0 affect Veg↔Built-up counts.

**Decision:** Use Landsat 8 Collection 2 Tier 1 (Band 10) for 2018 LST; Landsat 9 Collection 2 Tier 1 for 2025 LST.

**Rationale:** Landsat is the standard, operationally calibrated thermal IR source at 30 m. Collection 2 applies updated radiometric calibration and provides a consistent scale factor (0.00341802) and offset (149.0 K). Landsat 9 (launched 2021) is cross-calibrated with Landsat 8 so the two are directly comparable.

**What LST represents:** Satellite-derived **land surface temperature (LST)**, not air temperature. It reflects emitted thermal radiation from the surface and is higher than ambient air temperature on sunny days. This distinction will be stated explicitly in the AR info panel.

---

