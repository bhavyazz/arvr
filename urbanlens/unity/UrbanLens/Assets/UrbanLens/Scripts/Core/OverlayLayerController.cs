using UnityEngine;

namespace UrbanLens.Core
{
    /// <summary>
    /// Switches the study-area overlay between 2018 and 2025.
    /// Source textures are the classified land-cover PNGs from the Python pipeline
    /// (unity_inputs/). They are classification-derived, not continuous NDVI/NDBI/NDWI.
    /// </summary>
    public class OverlayLayerController : MonoBehaviour
    {
        public enum Year { Y2018, Y2025 }

        [Header("Target")]
        [SerializeField] private Renderer targetRenderer;

        [Header("Classified overlays (vegetation, built-up, water combined)")]
        [SerializeField] private Texture2D overlay2018;
        [SerializeField] private Texture2D overlay2025;

        [Header("State")]
        [SerializeField] private Year currentYear = Year.Y2025;

        private static readonly int BaseMapId = Shader.PropertyToID("_BaseMap");
        private static readonly int MainTexId = Shader.PropertyToID("_MainTex");

        public Year CurrentYear => currentYear;

        private void Start()
        {
            ApplyYear();
        }

        public void SetYear(Year year)
        {
            currentYear = year;
            ApplyYear();
        }

        private void ApplyYear()
        {
            if (targetRenderer == null)
            {
                Debug.LogError("[UrbanLens] OverlayLayerController: targetRenderer is not assigned.");
                return;
            }

            Texture2D tex = currentYear == Year.Y2018 ? overlay2018 : overlay2025;
            if (tex == null)
            {
                Debug.LogWarning($"[UrbanLens] Overlay texture for {currentYear} is not assigned.");
                return;
            }

            Material mat = targetRenderer.material;
            if (mat.HasProperty(BaseMapId)) mat.SetTexture(BaseMapId, tex);
            else if (mat.HasProperty(MainTexId)) mat.SetTexture(MainTexId, tex);
            else Debug.LogWarning("[UrbanLens] Target material has no base texture property.");
        }
    }
}
