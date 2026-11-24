using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace UrbanLens.Data
{
    /// <summary>
    /// Minimal JSON parser. Returns Dictionary&lt;string, object&gt;, List&lt;object&gt;, string,
    /// double, bool or null. Used because Unity's JsonUtility cannot read year-keyed objects
    /// such as stats.json ("areas_ha": { "2018": {...} }).
    /// </summary>
    public static class MiniJson
    {
        public static object Parse(string json)
        {
            int i = 0;
            return ParseValue(json, ref i);
        }

        private static void Skip(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }

        private static object ParseValue(string s, ref int i)
        {
            Skip(s, ref i);
            if (i >= s.Length) throw new FormatException("Unexpected end of JSON.");
            char c = s[i];
            switch (c)
            {
                case '{': return ParseObject(s, ref i);
                case '[': return ParseArray(s, ref i);
                case '"': return ParseString(s, ref i);
                case 't': i += 4; return true;
                case 'f': i += 5; return false;
                case 'n': i += 4; return null;
                default: return ParseNumber(s, ref i);
            }
        }

        private static Dictionary<string, object> ParseObject(string s, ref int i)
        {
            var dict = new Dictionary<string, object>();
            i++; // {
            Skip(s, ref i);
            if (s[i] == '}') { i++; return dict; }
            while (true)
            {
                Skip(s, ref i);
                string key = ParseString(s, ref i);
                Skip(s, ref i);
                i++; // :
                dict[key] = ParseValue(s, ref i);
                Skip(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == '}') { i++; break; }
                throw new FormatException("Malformed JSON object at " + i);
            }
            return dict;
        }

        private static List<object> ParseArray(string s, ref int i)
        {
            var list = new List<object>();
            i++; // [
            Skip(s, ref i);
            if (s[i] == ']') { i++; return list; }
            while (true)
            {
                list.Add(ParseValue(s, ref i));
                Skip(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == ']') { i++; break; }
                throw new FormatException("Malformed JSON array at " + i);
            }
            return list;
        }

        private static string ParseString(string s, ref int i)
        {
            var sb = new StringBuilder();
            i++; // opening quote
            while (s[i] != '"')
            {
                if (s[i] == '\\')
                {
                    i++;
                    switch (s[i])
                    {
                        case 'n': sb.Append('\n'); break;
                        case 't': sb.Append('\t'); break;
                        case 'r': sb.Append('\r'); break;
                        case 'u':
                            sb.Append((char)Convert.ToInt32(s.Substring(i + 1, 4), 16));
                            i += 4;
                            break;
                        default: sb.Append(s[i]); break;
                    }
                }
                else sb.Append(s[i]);
                i++;
            }
            i++; // closing quote
            return sb.ToString();
        }

        private static double ParseNumber(string s, ref int i)
        {
            int start = i;
            while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            return double.Parse(s.Substring(start, i - start), CultureInfo.InvariantCulture);
        }
    }
}
