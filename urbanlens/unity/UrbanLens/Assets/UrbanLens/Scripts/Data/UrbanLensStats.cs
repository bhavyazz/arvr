using System.Collections.Generic;
using UnityEngine;

namespace UrbanLens.Data
{
    /// <summary>
    /// Typed read-only view over unity_inputs/stats.json and ward_bounds.json (copied into
    /// Assets/UrbanLens/Data). Every number shown in the dashboard comes from these files.
    /// Nothing is hard-coded here.
    /// </summary>
    public class UrbanLensStats
    {
        private readonly Dictionary<string, object> stats;
        private readonly Dictionary<string, object> bounds;

        public string StudyArea => GetString(stats, "study_area");
        public string Crs => GetString(stats, "crs");
        public string ValidationLine => GetString(stats, "validation_line");

        public double WidthM => GetNum(bounds, "width_m");
        public double HeightM => GetNum(bounds, "height_m");
        public int GridRows => (int)GetNum((List<object>)bounds["grid_shape"], 0);
        public int GridCols => (int)GetNum((List<object>)bounds["grid_shape"], 1);

        private UrbanLensStats(Dictionary<string, object> stats, Dictionary<string, object> bounds)
        {
            this.stats = stats;
            this.bounds = bounds;
        }

        /// <summary>Parses the two data assets. Throws if either is missing.</summary>
        public static UrbanLensStats Load(TextAsset statsAsset, TextAsset boundsAsset)
        {
            if (statsAsset == null || boundsAsset == null)
                throw new System.ArgumentNullException("UrbanLens data assets are not assigned.");
            var s = (Dictionary<string, object>)UrbanLens.Data.MiniJson.Parse(statsAsset.text);
            var b = (Dictionary<string, object>)UrbanLens.Data.MiniJson.Parse(boundsAsset.text);
            return new UrbanLensStats(s, b);
        }

        /// <summary>Key used inside stats.json for each land-cover class.</summary>
        public static string ClassKey(Core.LandCoverClass c)
        {
            switch (c)
            {
                case Core.LandCoverClass.Vegetation: return "vegetation";
                case Core.LandCoverClass.BuiltUp: return "builtup";
                default: return "water";
            }
        }

        public double AreaHa(int year, Core.LandCoverClass c) =>
            GetNum(Dig("areas_ha", year.ToString()), ClassKey(c));

        public long PixelCount(int year, Core.LandCoverClass c) =>
            (long)GetNum(Dig("pixel_counts", year.ToString()), ClassKey(c));

        public double NdwiWaterHa(int year) =>
            GetNum((Dictionary<string, object>)stats["ndwi_water_ha"], year.ToString());

        public double NdwiNetChangeHa => GetNum(Dig("ndwi_water_ha"), "net_change_ha");
        public double NdwiChangePct => GetNum(Dig("ndwi_water_ha"), "change_pct");
        public double NdwiThreshold => GetNum(Dig("ndwi_water_ha"), "threshold");

        public double Accuracy2025Overall => GetNum(Dig("accuracy_2025"), "overall_accuracy");
        public double Accuracy2025MacroF1 => GetNum(Dig("accuracy_2025"), "macro_f1");

        /// <summary>Per-class metric from accuracy_2025. className is "Vegetation", "Built-up" or "Water".</summary>
        public double Accuracy2025Class(string className, string metric) =>
            GetNum(Dig("accuracy_2025", "per_class", className), metric);

        public double Accuracy2018Agreement => GetNum(Dig("accuracy_2018"), "overall_agreement");
        public double Accuracy2018MacroF1 => GetNum(Dig("accuracy_2018"), "macro_f1");
        public string Accuracy2018Status => GetString(Dig("accuracy_2018"), "status");

        // ----- helpers -----

        private Dictionary<string, object> Dig(params string[] path)
        {
            Dictionary<string, object> cur = stats;
            foreach (var key in path)
                cur = (Dictionary<string, object>)cur[key];
            return cur;
        }

        private static double GetNum(Dictionary<string, object> d, string key) =>
            System.Convert.ToDouble(d[key]);

        private static double GetNum(List<object> list, int index) =>
            System.Convert.ToDouble(list[index]);

        private static string GetString(Dictionary<string, object> d, string key) =>
            d.TryGetValue(key, out var v) ? v as string ?? "" : "";
    }
}
