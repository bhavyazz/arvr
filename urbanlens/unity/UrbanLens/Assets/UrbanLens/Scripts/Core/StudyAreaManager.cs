using System;
using UnityEngine;
using UnityEngine.InputSystem;
using UrbanLens.Data;

namespace UrbanLens.Core
{
    /// <summary>
    /// Owns the study-area state: selected year, per-class visibility and opacity, and the
    /// combined overlay. Applies changes to every layer and raises StateChanged for the UI.
    /// Scene units: 1 unit = 100 m, so the 9.8 km x 9.2 km ward is 98 x 92 units.
    ///
    /// Keyboard (Input System):  1 = 2018   2 = 2025   V = vegetation   B = built-up
    ///                           W = water   C = combined overlay   R = reset camera
    /// </summary>
    public class StudyAreaManager : MonoBehaviour
    {
        [Header("Data assets (Assets/UrbanLens/Data)")]
        [SerializeField] private TextAsset statsJson;
        [SerializeField] private TextAsset boundsJson;

        [Header("Independent land-cover layers")]
        [SerializeField] private LandCoverLayer vegetationLayer;
        [SerializeField] private LandCoverLayer builtUpLayer;
        [SerializeField] private LandCoverLayer waterLayer;

        [Header("Combined overlay (all classes in one image)")]
        [SerializeField] private OverlayLayerController combinedOverlay;
        [SerializeField] private GameObject combinedObject;

        [Header("Optional")]
        [SerializeField] private ElevationRelief elevation;
        [SerializeField] private UrbanLens.Camera.OrbitCamera orbitCamera;

        [Header("State")]
        [SerializeField] private OverlayLayerController.Year year = OverlayLayerController.Year.Y2025;
        [SerializeField] private bool combinedVisible;

        public event Action StateChanged;

        // Individual-layer visibility saved while the combined overlay is shown.
        private readonly bool[] savedLayerVisible = new bool[3];

        public UrbanLensStats Stats { get; private set; }
        public OverlayLayerController.Year Year => year;
        public bool CombinedVisible => combinedVisible;
        public ElevationRelief Elevation => elevation;

        private void Awake()
        {
            if (statsJson != null && boundsJson != null)
            {
                Stats = UrbanLensStats.Load(statsJson, boundsJson);
                if (elevation != null) elevation.Configure((float)Stats.WidthM, (float)Stats.HeightM);
            }
            else
            {
                Debug.LogError("[UrbanLens] StudyAreaManager: stats.json / ward_bounds.json not assigned.");
            }
        }

        private void Start()
        {
            // Capture each layer's own visibility before the combined overlay can hide it.
            bool startCombined = combinedVisible;
            combinedVisible = false;
            foreach (LandCoverClass c in Enum.GetValues(typeof(LandCoverClass)))
                savedLayerVisible[(int)c] = GetLayer(c).IsVisible;

            if (startCombined) SetCombinedVisible(true);
            else ApplyAll();
        }

        public LandCoverLayer GetLayer(LandCoverClass c)
        {
            switch (c)
            {
                case LandCoverClass.Vegetation: return vegetationLayer;
                case LandCoverClass.BuiltUp: return builtUpLayer;
                default: return waterLayer;
            }
        }

        public void SetYear(OverlayLayerController.Year newYear)
        {
            year = newYear;
            ApplyAll();
        }

        public void SetLayerVisible(LandCoverClass c, bool visible)
        {
            // Individual layers and the combined overlay are mutually exclusive.
            // Showing an individual layer while the combined overlay is on exits combined mode first,
            // restoring the saved layer states.
            if (combinedVisible && visible) SetCombinedVisible(false);
            if (combinedVisible) return; // layers stay hidden while the combined overlay is shown

            GetLayer(c).SetVisible(visible);
            savedLayerVisible[(int)c] = visible;
            StateChanged?.Invoke();
        }

        public void SetLayerOpacity(LandCoverClass c, float opacity)
        {
            GetLayer(c).SetOpacity(opacity);
            StateChanged?.Invoke();
        }

        public void SetCombinedVisible(bool visible)
        {
            if (visible == combinedVisible)
            {
                ApplyAll();
                return;
            }

            if (visible)
            {
                // Save the individual states, then hide all three layers.
                foreach (LandCoverClass c in Enum.GetValues(typeof(LandCoverClass)))
                {
                    var layer = GetLayer(c);
                    savedLayerVisible[(int)c] = layer.IsVisible;
                    layer.SetVisible(false);
                }
            }
            else
            {
                // Restore the individual states that were active before the combined overlay.
                foreach (LandCoverClass c in Enum.GetValues(typeof(LandCoverClass)))
                    GetLayer(c).SetVisible(savedLayerVisible[(int)c]);
            }

            combinedVisible = visible;
            ApplyAll();
        }

        public void ResetCamera()
        {
            if (orbitCamera != null) orbitCamera.ResetCamera();
        }

        private void Update()
        {
            var kb = Keyboard.current;
            if (kb == null) return;

            if (kb.digit1Key.wasPressedThisFrame) SetYear(OverlayLayerController.Year.Y2018);
            if (kb.digit2Key.wasPressedThisFrame) SetYear(OverlayLayerController.Year.Y2025);
            if (kb.vKey.wasPressedThisFrame) SetLayerVisible(LandCoverClass.Vegetation, !vegetationLayer.IsVisible);
            if (kb.bKey.wasPressedThisFrame) SetLayerVisible(LandCoverClass.BuiltUp, !builtUpLayer.IsVisible);
            if (kb.wKey.wasPressedThisFrame) SetLayerVisible(LandCoverClass.Water, !waterLayer.IsVisible);
            if (kb.cKey.wasPressedThisFrame) SetCombinedVisible(!combinedVisible);
            if (kb.rKey.wasPressedThisFrame) ResetCamera();
        }

        private void ApplyAll()
        {
            vegetationLayer?.SetYear(year);
            builtUpLayer?.SetYear(year);
            waterLayer?.SetYear(year);

            if (combinedOverlay != null) combinedOverlay.SetYear(year);
            if (combinedObject != null) combinedObject.SetActive(combinedVisible);

            StateChanged?.Invoke();
        }
    }
}
