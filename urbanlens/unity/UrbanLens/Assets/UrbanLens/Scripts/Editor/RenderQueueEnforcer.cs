using UnityEditor;
using UnityEngine;
using UrbanLens.Core;

namespace UrbanLens.EditorTools
{
    /// <summary>
    /// Keeps the independent land-cover materials at their required render queues.
    /// Unity does not reliably keep an edited m_CustomRenderQueue in memory across reimports,
    /// so this re-applies the values after every domain reload and on demand.
    /// The mapping is LandCoverLayer.RenderQueueFor (single source of truth).
    /// </summary>
    public static class RenderQueueEnforcer
    {
        private const string MaterialFolder = "Assets/UrbanLens/Materials";

        // Runs after every domain reload (scripts recompiled, Play Mode entered, editor restarted).
        [InitializeOnLoadMethod]
        private static void OnEditorLoad()
        {
            EditorApplication.delayCall += () =>
            {
                Debug.Log("[UrbanLens] Render queue enforcer: running after editor load.");
                EnforceAll();
            };
        }

        [MenuItem("UrbanLens/Enforce Layer Render Queues")]
        public static void EnforceAll()
        {
            if (!AssetDatabase.IsValidFolder(MaterialFolder)) return;

            bool changed = false;
            foreach (string guid in AssetDatabase.FindAssets("t:Material", new[] { MaterialFolder }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (mat == null) continue;

                int? want = QueueForMaterialName(mat.name);
                if (want == null || mat.renderQueue == want.Value) continue;

                mat.renderQueue = want.Value;
                EditorUtility.SetDirty(mat);
                changed = true;
                Debug.Log($"[UrbanLens] Set render queue of '{mat.name}' to {want.Value}.");
            }

            if (changed) AssetDatabase.SaveAssets();
        }

        private static int? QueueForMaterialName(string name)
        {
            if (name == "LandCover_Vegetation") return LandCoverLayer.RenderQueueFor(LandCoverClass.Vegetation);
            if (name == "LandCover_BuiltUp") return LandCoverLayer.RenderQueueFor(LandCoverClass.BuiltUp);
            if (name == "LandCover_Water") return LandCoverLayer.RenderQueueFor(LandCoverClass.Water);
            return null; // Combined overlay and Ground are not part of the independent stack
        }
    }
}
