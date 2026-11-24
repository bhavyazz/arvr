using UnityEngine;

namespace UrbanLens.Core
{
    /// <summary>
    /// Optional terrain relief with vertical exaggeration.
    /// IMPORTANT: this only works with REAL elevation data. It is disabled unless an elevation
    /// raster AND its true min/max elevation in metres are assigned. Nothing is fabricated:
    /// no elevation values are generated when the data is missing.
    /// Scene units: 1 unit = 100 m (see StudyAreaManager), so 1 m of height = 0.01 units.
    /// </summary>
    public class ElevationRelief : MonoBehaviour
    {
        [Header("Real elevation data (required)")]
        [Tooltip("Single-channel elevation raster, read from the R channel. Must be Read/Write enabled.")]
        [SerializeField] private Texture2D elevationRaster;
        [Tooltip("True minimum elevation in metres, from the source DEM metadata.")]
        [SerializeField] private float minElevationM;
        [Tooltip("True maximum elevation in metres, from the source DEM metadata.")]
        [SerializeField] private float maxElevationM;

        [Header("Display")]
        [SerializeField, Range(1f, 5f)] private float exaggeration = 1f;
        [SerializeField] private int maxGridResolution = 256;

        [Header("Scene objects")]
        [SerializeField] private GameObject flatGround;

        private const float UnitsPerMetre = 0.01f;
        private GameObject reliefObject;
        private float widthUnits = 98f;
        private float heightUnits = 92f;

        public bool HasElevationData =>
            elevationRaster != null && maxElevationM > minElevationM;

        public float Exaggeration => exaggeration;

        /// <summary>Sets the footprint in scene units (from ward_bounds.json width_m / height_m).</summary>
        public void Configure(float widthMetres, float heightMetres)
        {
            widthUnits = widthMetres * UnitsPerMetre;
            heightUnits = heightMetres * UnitsPerMetre;
        }

        public void SetExaggeration(float value)
        {
            exaggeration = Mathf.Clamp(value, 1f, 5f);
            if (HasElevationData) Rebuild();
        }

        private void Start()
        {
            Rebuild();
        }

        /// <summary>Builds the relief mesh only when real elevation data is present.</summary>
        public void Rebuild()
        {
            if (!HasElevationData)
            {
                if (reliefObject != null) reliefObject.SetActive(false);
                if (flatGround != null) flatGround.SetActive(true);
                return;
            }

            if (reliefObject == null) CreateReliefObject();
            reliefObject.SetActive(true);
            if (flatGround != null) flatGround.SetActive(false);

            int res = Mathf.Clamp(Mathf.Min(elevationRaster.width, elevationRaster.height), 2, maxGridResolution);
            var vertices = new Vector3[res * res];
            var uvs = new Vector2[res * res];

            for (int z = 0; z < res; z++)
            {
                for (int x = 0; x < res; x++)
                {
                    float u = x / (float)(res - 1);
                    float v = z / (float)(res - 1);
                    float norm = elevationRaster.GetPixelBilinear(u, v).r;
                    float elevM = minElevationM + norm * (maxElevationM - minElevationM);
                    int idx = z * res + x;
                    vertices[idx] = new Vector3((u - 0.5f) * widthUnits, elevM * exaggeration * UnitsPerMetre, (v - 0.5f) * heightUnits);
                    uvs[idx] = new Vector2(u, v);
                }
            }

            var tris = new int[(res - 1) * (res - 1) * 6];
            int t = 0;
            for (int z = 0; z < res - 1; z++)
            {
                for (int x = 0; x < res - 1; x++)
                {
                    int i = z * res + x;
                    tris[t++] = i; tris[t++] = i + res; tris[t++] = i + 1;
                    tris[t++] = i + 1; tris[t++] = i + res; tris[t++] = i + res + 1;
                }
            }

            var mesh = reliefObject.GetComponent<MeshFilter>().sharedMesh;
            if (mesh == null)
            {
                mesh = new Mesh { name = "UrbanLensRelief" };
                reliefObject.GetComponent<MeshFilter>().sharedMesh = mesh;
            }
            mesh.Clear();
            mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            mesh.vertices = vertices;
            mesh.uv = uvs;
            mesh.triangles = tris;
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
        }

        private void CreateReliefObject()
        {
            reliefObject = new GameObject("TerrainRelief");
            reliefObject.transform.SetParent(transform, false);
            reliefObject.AddComponent<MeshFilter>();
            var mr = reliefObject.AddComponent<MeshRenderer>();
            mr.sharedMaterial = flatGround != null && flatGround.GetComponent<Renderer>() != null
                ? flatGround.GetComponent<Renderer>().sharedMaterial
                : null;
        }
    }
}
