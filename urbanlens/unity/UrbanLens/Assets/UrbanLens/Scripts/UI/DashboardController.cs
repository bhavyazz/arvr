using System;
using System.Globalization;
using System.Text;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;
using UrbanLens.Core;
using Year = UrbanLens.Core.OverlayLayerController.Year;

namespace UrbanLens.UI
{
    /// <summary>
    /// Academic dashboard built at runtime with uGUI: year selector, independent layer
    /// controls, legend, statistics from stats.json, accuracy and validation status,
    /// methodology, limitations, terrain exaggeration (gated on real data) and camera controls.
    /// Uses InputSystemUIInputModule (Input System package), not the legacy StandaloneInputModule.
    /// </summary>
    public class DashboardController : MonoBehaviour
    {
        [SerializeField] private StudyAreaManager study;

        private static readonly Color VegColor = new Color(0.18f, 0.80f, 0.44f);
        private static readonly Color BuiltColor = new Color(0.91f, 0.30f, 0.24f);
        private static readonly Color WaterColor = new Color(0.20f, 0.60f, 0.86f);
        private static readonly Color AccentColor = new Color(0.30f, 0.45f, 0.62f);
        private static readonly Color SelectedColor = new Color(0.20f, 0.62f, 0.95f);
        private static readonly Color PanelColor = new Color(0.05f, 0.06f, 0.08f, 0.92f);
        private static readonly Color DimText = new Color(0.75f, 0.78f, 0.82f);

        private Font font;
        private Transform content;
        private Button btn2018, btn2025;
        private readonly System.Collections.Generic.Dictionary<LandCoverClass, Toggle> layerToggles
            = new System.Collections.Generic.Dictionary<LandCoverClass, Toggle>();
        private readonly System.Collections.Generic.Dictionary<LandCoverClass, Slider> opacitySliders
            = new System.Collections.Generic.Dictionary<LandCoverClass, Slider>();
        private Toggle combinedToggle;
        private Slider exaggerationSlider;
        private Text terrainNote;
        private Text yearStatus;

        private void Start()
        {
            if (study == null) study = FindAnyObjectByType<StudyAreaManager>();
            if (study == null || study.Stats == null)
            {
                Debug.LogError("[UrbanLens] DashboardController: StudyAreaManager or stats data missing.");
                return;
            }

            EnsureEventSystem();
            BuildCanvas();
            study.StateChanged += Refresh;
            Refresh();
        }

        private void OnDestroy()
        {
            if (study != null) study.StateChanged -= Refresh;
        }

        // ------------------------------------------------------------------ setup

        private void EnsureEventSystem()
        {
            var es = FindAnyObjectByType<EventSystem>();
            if (es == null)
            {
                new GameObject("EventSystem", typeof(EventSystem), typeof(InputSystemUIInputModule));
                return;
            }
            var legacy = es.GetComponent<StandaloneInputModule>();
            if (legacy != null) Destroy(legacy);
            if (es.GetComponent<InputSystemUIInputModule>() == null)
                es.gameObject.AddComponent<InputSystemUIInputModule>();
        }

        private void BuildCanvas()
        {
            font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

            // The saved scene may already contain a canvas from an earlier session; replace it so only one dashboard exists.
            var existing = GameObject.Find("UrbanLensCanvas");
            if (existing != null) Destroy(existing);

            var canvasGo = new GameObject("UrbanLensCanvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            var canvas = canvasGo.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvasGo.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1280, 720); // text scales up for typical screens
            scaler.matchWidthOrHeight = 0.5f;

            var panel = new GameObject("Panel", typeof(RectTransform), typeof(Image));
            panel.transform.SetParent(canvasGo.transform, false);
            panel.GetComponent<Image>().color = PanelColor;
            var prt = panel.GetComponent<RectTransform>();
            prt.anchorMin = new Vector2(0, 0);
            prt.anchorMax = new Vector2(0, 1);
            prt.pivot = new Vector2(0, 0.5f);
            prt.sizeDelta = new Vector2(420, 0);
            prt.anchoredPosition = Vector2.zero;

            var scrollGo = new GameObject("Scroll", typeof(RectTransform), typeof(Image), typeof(Mask), typeof(ScrollRect));
            scrollGo.transform.SetParent(panel.transform, false);
            scrollGo.GetComponent<Image>().color = new Color(0, 0, 0, 0.01f);
            scrollGo.GetComponent<Mask>().showMaskGraphic = false;
            StretchFull(scrollGo.GetComponent<RectTransform>());

            var contentGo = new GameObject("Content", typeof(RectTransform), typeof(VerticalLayoutGroup), typeof(ContentSizeFitter));
            contentGo.transform.SetParent(scrollGo.transform, false);
            var crt = contentGo.GetComponent<RectTransform>();
            crt.anchorMin = new Vector2(0, 1);
            crt.anchorMax = new Vector2(1, 1);
            crt.pivot = new Vector2(0.5f, 1);
            crt.sizeDelta = Vector2.zero; // new RectTransforms default to 100x100; stretched width must be exact
            var vlg = contentGo.GetComponent<VerticalLayoutGroup>();
            vlg.padding = new RectOffset(18, 18, 18, 18);
            vlg.spacing = 8;
            vlg.childControlWidth = true;
            vlg.childControlHeight = true;
            vlg.childForceExpandWidth = true;
            vlg.childForceExpandHeight = false;
            var fit = contentGo.GetComponent<ContentSizeFitter>();
            fit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            fit.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;

            var scroll = scrollGo.GetComponent<ScrollRect>();
            scroll.viewport = scrollGo.GetComponent<RectTransform>();
            scroll.content = crt;
            scroll.horizontal = false;
            scroll.vertical = true;

            content = contentGo.transform;
            BuildSections();
        }

        // ------------------------------------------------------------------ sections

        private void BuildSections()
        {
            var s = study.Stats;

            AddText("UrbanLens: land-cover change", 22, FontStyle.Bold);
            AddText(s.StudyArea + ", Bengaluru, Karnataka, India", 15, FontStyle.Bold, DimText);
            AddText(
                "Grid " + s.GridCols + " x " + s.GridRows + " px at 10 m, " + s.Crs +
                ". Bounding box " + Fmt(s.WidthM / 1000.0, "F2") + " km x " + Fmt(s.HeightM / 1000.0, "F2") +
                " km. Scene units: 1 unit = 100 m.", 13, FontStyle.Normal, DimText);

            AddSectionTitle("Year");
            var yearRow = AddRow();
            btn2018 = AddButton(yearRow, "2018", () => study.SetYear(Year.Y2018), AccentColor);
            btn2025 = AddButton(yearRow, "2025", () => study.SetYear(Year.Y2025), AccentColor);
            yearStatus = AddText("", 14, FontStyle.Italic, DimText);
            AddText("Keyboard: 1 = 2018, 2 = 2025", 13, FontStyle.Normal, DimText);

            AddSectionTitle("Layers (independent)");
            AddLayerControl(LandCoverClass.Vegetation, "Vegetation", VegColor);
            AddLayerControl(LandCoverClass.BuiltUp, "Built-up", BuiltColor);
            AddLayerControl(LandCoverClass.Water, "Water", WaterColor);
            combinedToggle = AddToggle("Combined overlay (all classes in one image)", false,
                v => study.SetCombinedVisible(v), Color.white);
            AddText("Keyboard: V = vegetation, B = built-up, W = water, C = combined, R = reset view",
                13, FontStyle.Normal, DimText);

            AddSectionTitle("Legend");
            AddLegend(VegColor, "Vegetation (classifier mask)");
            AddLegend(BuiltColor, "Built-up (classifier mask)");
            AddLegend(WaterColor, "Water (classifier mask)");
            AddText("Transparent areas: outside the study mask. Masks are classification-derived, not continuous NDVI/NDBI/NDWI.",
                13, FontStyle.Normal, DimText);

            AddSectionTitle("Area statistics (hectares, classifier)");
            AddText(BuildAreaStats(), 14);

            AddSectionTitle("Surface water (NDWI mask, canonical change measure)");
            AddText(BuildWaterStats(), 14);
            AddText("Classifier water and NDWI water are different measurements and are reported separately. Change is reported from the NDWI mask.",
                13, FontStyle.Normal, DimText);

            AddSectionTitle("Accuracy and validation");
            AddText(BuildAccuracy(), 14);

            AddSectionTitle("Methodology");
            AddText(Methodology, 14);

            AddSectionTitle("Limitations");
            AddText(Limitations, 14);

            AddSectionTitle("Terrain");
            var elev = study.Elevation;
            exaggerationSlider = AddSlider(1f, 5f, elev != null ? elev.Exaggeration : 1f,
                v => { if (elev != null) elev.SetExaggeration(v); });
            terrainNote = AddText("", 13, FontStyle.Normal, DimText);

            AddSectionTitle("Camera controls");
            AddText("Right-drag: orbit   Middle-drag: pan   Scroll: zoom", 14);
            AddButton(AddRow(), "Reset view", () => study.ResetCamera(), AccentColor);
        }

        private void AddLayerControl(LandCoverClass c, string label, Color color)
        {
            layerToggles[c] = AddToggle(label, true, v => study.SetLayerVisible(c, v), color);
            opacitySliders[c] = AddSlider(0f, 1f, 0.85f, v => study.SetLayerOpacity(c, v));
        }

        private void AddLegend(Color color, string label)
        {
            var row = AddRow();
            var sw = new GameObject("Swatch", typeof(RectTransform), typeof(Image), typeof(LayoutElement));
            sw.transform.SetParent(row, false);
            sw.GetComponent<Image>().color = color;
            sw.GetComponent<LayoutElement>().preferredWidth = 18;
            sw.GetComponent<LayoutElement>().preferredHeight = 18;
            AddText(label, 14, FontStyle.Normal, Color.white, row, false);
        }

        // ------------------------------------------------------------------ text content

        private string BuildAreaStats()
        {
            var s = study.Stats;
            var sb = new StringBuilder();
            long total18 = 0, total25 = 0;
            foreach (LandCoverClass c in Enum.GetValues(typeof(LandCoverClass)))
            {
                double a18 = s.AreaHa(2018, c), a25 = s.AreaHa(2025, c);
                double d = a25 - a18;
                double pct = a18 != 0 ? d / a18 * 100.0 : 0;
                total18 += s.PixelCount(2018, c);
                total25 += s.PixelCount(2025, c);
                sb.AppendLine(ClassName(c) + ": 2018 " + Fmt(a18, "F2") + " ha, 2025 " + Fmt(a25, "F2") + " ha");
                sb.AppendLine("   change " + Signed(d, "F2") + " ha (" + Signed(pct, "F1") + "%)");
            }
            sb.AppendLine("Classified pixels: 2018 " + total18.ToString("N0", CultureInfo.InvariantCulture) +
                ", 2025 " + total25.ToString("N0", CultureInfo.InvariantCulture));
            sb.Append("Change between classifications is not interpreted as verified expansion. See Limitations.");
            return sb.ToString();
        }

        private string BuildWaterStats()
        {
            var s = study.Stats;
            double w18 = s.NdwiWaterHa(2018), w25 = s.NdwiWaterHa(2025);
            return "NDWI > " + Fmt(s.NdwiThreshold, "F1") + " mask: 2018 " + Fmt(w18, "F2") + " ha, 2025 " +
                   Fmt(w25, "F2") + " ha.\nNet change " + Signed(s.NdwiNetChangeHa, "F2") + " ha (" +
                   Signed(s.NdwiChangePct, "F1") + "%).";
        }

        private string BuildAccuracy()
        {
            var s = study.Stats;
            return "2025 vs ESA WorldCover 2021: cross-year validation, not independent accuracy.\n" +
                   "Overall accuracy " + Fmt(s.Accuracy2025Overall * 100, "F2") + "%, macro F1 " +
                   Fmt(s.Accuracy2025MacroF1, "F3") + ".\n" +
                   "Vegetation F1 " + Fmt(s.Accuracy2025Class("Vegetation", "f1"), "F3") + ".  " +
                   "Built-up F1 " + Fmt(s.Accuracy2025Class("Built-up", "f1"), "F3") + ".  " +
                   "Water F1 " + Fmt(s.Accuracy2025Class("Water", "f1"), "F3") + " (precision " +
                   Fmt(s.Accuracy2025Class("Water", "precision"), "F3") + ", recall " +
                   Fmt(s.Accuracy2025Class("Water", "recall"), "F3") + ").\n\n" +
                   "2018: " + s.Accuracy2018Status.ToUpperInvariant() + ". No authoritative 2018 ground truth exists. " +
                   "Agreement with the Dynamic World 2018 proxy is " + Fmt(s.Accuracy2018Agreement * 100, "F2") +
                   "% (macro F1 " + Fmt(s.Accuracy2018MacroF1, "F3") + "). Proxy agreement is not accuracy.";
        }

        private const string Methodology =
            "Source: Copernicus Sentinel-2 L2A surface reflectance. Dry-season composites per year, cloud-masked.\n" +
            "Indices: NDVI, NDBI and NDWI. Classification: supervised classifier on spectral bands and indices, " +
            "exported as per-class masks for 2018 and 2025.\n" +
            "Reference labels: ESA WorldCover 2021, mapped to Vegetation, Built-up and Water. " +
            "Exact model parameters and sampling are documented in the processing pipeline, not repeated here.";

        private const string Limitations =
            "- 2025 accuracy is cross-year validation against 2021 labels, not independent accuracy.\n" +
            "- 2018 accuracy is unverified. The 58.1% figure is agreement with a Dynamic World proxy, not ground-truth accuracy.\n" +
            "- 88.9% of changed pixels lie at or next to a class boundary. Vegetation to built-up totals are boundary-dominated and are not interpreted as verified expansion.\n" +
            "- Causes of change are not attributed.\n" +
            "- Water precision is 0.489 against WorldCover, so many predicted water pixels disagree with the reference. Treat water classifier totals with caution.\n" +
            "- No elevation data is included. No terrain relief is shown and none has been estimated.";

        private string BuildTerrainNote()
        {
            var elev = study.Elevation;
            if (elev == null || !elev.HasElevationData)
                return "Terrain exaggeration is unavailable: no elevation raster with a known metre range is assigned. " +
                       "Nothing has been estimated or generated.";
            return "Vertical exaggeration x" + Fmt(elev.Exaggeration, "F1") + " using the assigned elevation raster.";
        }

        // ------------------------------------------------------------------ refresh

        private void Refresh()
        {
            if (study == null || study.Stats == null) return;

            var year = study.Year;
            SetButtonColor(btn2018, year == Year.Y2018);
            SetButtonColor(btn2025, year == Year.Y2025);
            yearStatus.text = "Showing " + (year == Year.Y2018 ? "2018" : "2025") +
                " classification. Classes at 2018 and 2025 are separate models; see Accuracy.";

            foreach (var kv in layerToggles)
            {
                kv.Value.SetIsOnWithoutNotify(study.GetLayer(kv.Key).IsVisible);
                opacitySliders[kv.Key].SetValueWithoutNotify(study.GetLayer(kv.Key).Opacity);
            }
            combinedToggle.SetIsOnWithoutNotify(study.CombinedVisible);

            bool hasElev = study.Elevation != null && study.Elevation.HasElevationData;
            exaggerationSlider.interactable = hasElev;
            if (study.Elevation != null)
                exaggerationSlider.SetValueWithoutNotify(study.Elevation.Exaggeration);
            terrainNote.text = BuildTerrainNote();
        }

        private void SetButtonColor(Button b, bool selected)
        {
            if (b != null) b.GetComponent<Image>().color = selected ? SelectedColor : AccentColor;
        }

        // ------------------------------------------------------------------ widget helpers

        private void AddSectionTitle(string title)
        {
            var spacer = new GameObject("Spacer", typeof(RectTransform), typeof(LayoutElement));
            spacer.transform.SetParent(content, false);
            spacer.GetComponent<LayoutElement>().preferredHeight = 10;
            AddText(title.ToUpperInvariant(), 15, FontStyle.Bold, SelectedColor);
        }

        private Text AddText(string s, int size, FontStyle style = FontStyle.Normal, Color? color = null,
            Transform parent = null, bool autoHeight = true)
        {
            var go = new GameObject("Text", typeof(RectTransform), typeof(Text));
            go.transform.SetParent(parent != null ? parent : content, false);
            var t = go.GetComponent<Text>();
            t.font = font;
            t.fontSize = size;
            t.fontStyle = style;
            t.color = color ?? Color.white;
            t.text = s;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            if (autoHeight)
            {
                var fit = go.AddComponent<ContentSizeFitter>();
                fit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            }
            return t;
        }

        private RectTransform AddRow()
        {
            var go = new GameObject("Row", typeof(RectTransform), typeof(HorizontalLayoutGroup));
            go.transform.SetParent(content, false);
            var h = go.GetComponent<HorizontalLayoutGroup>();
            h.spacing = 8;
            h.childControlWidth = true;
            h.childControlHeight = true;
            h.childForceExpandWidth = true;
            h.childForceExpandHeight = false;
            return go.GetComponent<RectTransform>();
        }

        private Button AddButton(Transform parent, string label, UnityAction onClick, Color bg)
        {
            var go = new GameObject("Button", typeof(RectTransform), typeof(Image), typeof(Button), typeof(LayoutElement));
            go.transform.SetParent(parent, false);
            go.GetComponent<LayoutElement>().preferredHeight = 36;
            go.GetComponent<LayoutElement>().flexibleWidth = 1;
            var img = go.GetComponent<Image>();
            img.color = bg;
            var btn = go.GetComponent<Button>();
            btn.targetGraphic = img;
            btn.onClick.AddListener(onClick);
            var t = AddText(label, 16, FontStyle.Bold, Color.white, go.transform, false);
            StretchFull(t.rectTransform);
            t.alignment = TextAnchor.MiddleCenter;
            return btn;
        }

        private Toggle AddToggle(string label, bool on, UnityAction<bool> onChange, Color labelColor)
        {
            var go = new GameObject("Toggle", typeof(RectTransform), typeof(Image), typeof(Toggle), typeof(LayoutElement));
            go.transform.SetParent(content, false);
            go.GetComponent<LayoutElement>().preferredHeight = 28;
            go.GetComponent<Image>().color = new Color(0, 0, 0, 0);

            var bg = new GameObject("Background", typeof(RectTransform), typeof(Image));
            bg.transform.SetParent(go.transform, false);
            bg.GetComponent<Image>().color = new Color(0.15f, 0.15f, 0.18f);
            var bgRt = bg.GetComponent<RectTransform>();
            bgRt.anchorMin = new Vector2(0, 0.5f);
            bgRt.anchorMax = new Vector2(0, 0.5f);
            bgRt.sizeDelta = new Vector2(22, 22);
            bgRt.anchoredPosition = new Vector2(11, 0);

            var check = new GameObject("Checkmark", typeof(RectTransform), typeof(Image));
            check.transform.SetParent(bg.transform, false);
            check.GetComponent<Image>().color = labelColor;
            StretchFull(check.GetComponent<RectTransform>());
            check.GetComponent<RectTransform>().offsetMin = new Vector2(4, 4);
            check.GetComponent<RectTransform>().offsetMax = new Vector2(-4, -4);

            var t = AddText(label, 15, FontStyle.Bold, labelColor, go.transform, false);
            var tr = t.rectTransform;
            tr.anchorMin = Vector2.zero;
            tr.anchorMax = Vector2.one;
            tr.offsetMin = new Vector2(34, 0);
            tr.offsetMax = Vector2.zero;

            var toggle = go.GetComponent<Toggle>();
            toggle.targetGraphic = bg.GetComponent<Image>();
            toggle.graphic = check.GetComponent<Image>();
            toggle.isOn = on;
            toggle.onValueChanged.AddListener(onChange);
            return toggle;
        }

        private Slider AddSlider(float min, float max, float value, UnityAction<float> onChange)
        {
            var go = new GameObject("Slider", typeof(RectTransform), typeof(Slider), typeof(LayoutElement));
            go.transform.SetParent(content, false);
            go.GetComponent<LayoutElement>().preferredHeight = 22;
            var sl = go.GetComponent<Slider>();
            sl.minValue = min;
            sl.maxValue = max;
            sl.direction = Slider.Direction.LeftToRight;

            var bg = new GameObject("Background", typeof(RectTransform), typeof(Image));
            bg.transform.SetParent(go.transform, false);
            bg.GetComponent<Image>().color = new Color(0.2f, 0.2f, 0.24f);
            StretchFull(bg.GetComponent<RectTransform>());

            var fillArea = new GameObject("Fill Area", typeof(RectTransform));
            fillArea.transform.SetParent(go.transform, false);
            StretchFull(fillArea.GetComponent<RectTransform>());
            fillArea.GetComponent<RectTransform>().offsetMin = new Vector2(6, 0);
            fillArea.GetComponent<RectTransform>().offsetMax = new Vector2(-6, 0);
            var fill = new GameObject("Fill", typeof(RectTransform), typeof(Image));
            fill.transform.SetParent(fillArea.transform, false);
            fill.GetComponent<Image>().color = new Color(0.30f, 0.60f, 0.90f);
            StretchFull(fill.GetComponent<RectTransform>());

            var handleArea = new GameObject("Handle Slide Area", typeof(RectTransform));
            handleArea.transform.SetParent(go.transform, false);
            StretchFull(handleArea.GetComponent<RectTransform>());
            handleArea.GetComponent<RectTransform>().offsetMin = new Vector2(6, 0);
            handleArea.GetComponent<RectTransform>().offsetMax = new Vector2(-6, 0);
            var handle = new GameObject("Handle", typeof(RectTransform), typeof(Image));
            handle.transform.SetParent(handleArea.transform, false);
            handle.GetComponent<Image>().color = Color.white;
            var hr = handle.GetComponent<RectTransform>();
            hr.anchorMin = new Vector2(0, 0);
            hr.anchorMax = new Vector2(0, 1);
            hr.sizeDelta = new Vector2(14, 0);

            sl.fillRect = fill.GetComponent<RectTransform>();
            sl.handleRect = hr;
            sl.targetGraphic = handle.GetComponent<Image>();
            sl.SetValueWithoutNotify(value);
            sl.onValueChanged.AddListener(onChange);
            return sl;
        }

        private static void StretchFull(RectTransform rt)
        {
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
        }

        private static string ClassName(LandCoverClass c)
        {
            switch (c)
            {
                case LandCoverClass.Vegetation: return "Vegetation";
                case LandCoverClass.BuiltUp: return "Built-up";
                default: return "Water (classifier)";
            }
        }

        private static string Fmt(double v, string format) =>
            v.ToString(format, CultureInfo.InvariantCulture);

        private static string Signed(double v, string format) =>
            (v >= 0 ? "+" : "") + v.ToString(format, CultureInfo.InvariantCulture);
    }
}
