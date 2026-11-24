using UnityEngine;
using UnityEngine.Rendering;

namespace UrbanLens.Core
{
    public enum LandCoverClass { Vegetation, BuiltUp, Water }

    /// <summary>
    /// One independent land-cover layer (vegetation, built-up or water) for one study area.
    /// Each layer has its own quad, 2018 and 2025 mask textures, visibility and opacity.
    /// Textures and opacity are written through a MaterialPropertyBlock, so the shared
    /// material asset (one per layer, created with ConfigureUnlitTransparent) is not mutated.
    /// Masks are the per-class PNGs from the pipeline (unity_inputs/{class}_{year}.png):
    /// classification-derived, not continuous indices.
    /// </summary>
    [RequireComponent(typeof(Renderer))]
    public class LandCoverLayer : MonoBehaviour
    {
        private static readonly int BaseMapId = Shader.PropertyToID("_BaseMap");
        private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");

        [SerializeField] private LandCoverClass layerClass = LandCoverClass.Vegetation;
        [SerializeField] private Texture2D texture2018;
        [SerializeField] private Texture2D texture2025;
        [SerializeField] private Color tint = Color.white;
        [SerializeField, Range(0f, 1f)] private float opacity = 0.85f;
        [SerializeField] private bool visible = true;
        [SerializeField] private OverlayLayerController.Year year = OverlayLayerController.Year.Y2025;

        private MaterialPropertyBlock block;

        public LandCoverClass LayerClass => layerClass;
        public OverlayLayerController.Year CurrentYear => year;
        public bool IsVisible => visible;
        public float Opacity => opacity;

        public void Initialize(LandCoverClass cls, Texture2D tex2018, Texture2D tex2025)
        {
            layerClass = cls;
            texture2018 = tex2018;
            texture2025 = tex2025;
            Apply();
        }

        /// <summary>
        /// Required render queue for each independent layer. Vegetation 3001, built-up 3002, water 3003
        /// so the stack draws in a fixed order. The combined overlay uses its own material (3000).
        /// </summary>
        public static int RenderQueueFor(LandCoverClass c)
        {
            switch (c)
            {
                case LandCoverClass.Vegetation: return 3001;
                case LandCoverClass.BuiltUp: return 3002;
                default: return 3003;
            }
        }

        private void Awake()
        {
            EnforceRenderQueue();
            Apply();
        }

        /// <summary>
        /// Guarantees this layer renders at its required queue. If the shared material has drifted
        /// (for example a new material assigned in the Inspector at 3000), a per-renderer instance is
        /// created with the correct queue. The shared asset is never mutated at runtime.
        /// </summary>
        private void EnforceRenderQueue()
        {
            var r = GetComponent<Renderer>();
            if (r == null || r.sharedMaterial == null) return;
            int want = RenderQueueFor(layerClass);
            if (r.sharedMaterial.renderQueue == want) return;
            int before = r.sharedMaterial.renderQueue; // read before the change so the log reports the old value
            r.material.renderQueue = want;
            Debug.LogWarning($"[UrbanLens] '{name}' render queue was {before}; set to {want} at runtime.");
        }

#if UNITY_EDITOR
        private void OnValidate()
        {
            var r = GetComponent<Renderer>();
            if (r == null || r.sharedMaterial == null) return;
            if (r.sharedMaterial.renderQueue != RenderQueueFor(layerClass))
                Debug.LogWarning($"[UrbanLens] '{name}' material '{r.sharedMaterial.name}' has render queue {r.sharedMaterial.renderQueue}; expected {RenderQueueFor(layerClass)}.");
        }
#endif

        public void SetYear(OverlayLayerController.Year newYear)
        {
            year = newYear;
            Apply();
        }

        public void SetVisible(bool value)
        {
            visible = value;
            Apply();
        }

        public void SetOpacity(float value)
        {
            opacity = Mathf.Clamp01(value);
            Apply();
        }

        private void Apply()
        {
            var r = GetComponent<Renderer>();
            if (r == null) return;

            // Runtime fallback: Apply runs on Start, year change and visibility change, so the required
            // queue is re-checked even if Awake did not run or the asset value drifted.
            EnforceRenderQueue();

            if (block == null) block = new MaterialPropertyBlock();
            Texture2D tex = year == OverlayLayerController.Year.Y2018 ? texture2018 : texture2025;
            if (tex == null)
                Debug.LogWarning($"[UrbanLens] No {layerClass} mask assigned for {year} on '{name}'.");

            Color c = tint;
            c.a = opacity;
            r.GetPropertyBlock(block);
            block.SetTexture(BaseMapId, tex);
            block.SetColor(BaseColorId, c);
            r.SetPropertyBlock(block);
            r.enabled = visible;
        }

        /// <summary>
        /// Makes a URP Unlit material alpha-blended and double sided, so the transparent
        /// background of each mask is respected. Call on material assets at creation time.
        /// </summary>
        public static void ConfigureUnlitTransparent(Material m, int renderQueue)
        {
            var unlit = Shader.Find("Universal Render Pipeline/Unlit");
            if (unlit != null && m.shader != unlit) m.shader = unlit;
            m.SetFloat("_Surface", 1f);
            m.SetFloat("_Blend", 0f);
            m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
            m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            m.SetFloat("_ZWrite", 0f);
            m.SetFloat("_Cull", 0f);
            m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            m.renderQueue = renderQueue;
        }
    }
}
