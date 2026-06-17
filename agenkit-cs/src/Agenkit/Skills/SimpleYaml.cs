namespace Agenkit.Skills;

/// <summary>
/// Minimal YAML mapping parser for skill frontmatter. Supports a flat set of
/// <c>key: value</c> pairs plus a single level of nested mapping (e.g. a
/// <c>metadata:</c> block whose child keys are indented). This deliberately
/// covers only the subset of YAML used by SKILL.md frontmatter and avoids a
/// third-party dependency.
/// </summary>
internal static class SimpleYaml
{
    /// <summary>
    /// Parses frontmatter text into a string-keyed mapping. Nested blocks are
    /// represented as <see cref="IReadOnlyDictionary{TKey,TValue}"/> values.
    /// </summary>
    public static IReadOnlyDictionary<string, object> ParseMapping(string text)
    {
        var result = new Dictionary<string, object>();
        var lines = text.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');

        for (var i = 0; i < lines.Length; i++)
        {
            var line = lines[i];
            if (IsBlankOrComment(line))
                continue;

            // Top-level entries have no leading whitespace.
            if (char.IsWhiteSpace(line[0]))
                continue; // nested lines are consumed by their parent below

            var colon = line.IndexOf(':');
            if (colon < 0)
                continue;

            var key = line[..colon].Trim();
            var valuePart = line[(colon + 1)..].Trim();

            if (valuePart.Length == 0)
            {
                // Possible nested mapping: collect following indented lines.
                var nested = new Dictionary<string, object>();
                while (i + 1 < lines.Length)
                {
                    var next = lines[i + 1];
                    if (IsBlankOrComment(next))
                    {
                        i++;
                        continue;
                    }

                    if (!char.IsWhiteSpace(next[0]))
                        break; // back to top level

                    var nColon = next.IndexOf(':');
                    if (nColon >= 0)
                    {
                        var nKey = next[..nColon].Trim();
                        var nVal = next[(nColon + 1)..].Trim();
                        if (nKey.Length > 0)
                            nested[nKey] = Unquote(nVal);
                    }

                    i++;
                }

                result[key] = nested;
            }
            else
            {
                result[key] = Unquote(valuePart);
            }
        }

        return result;
    }

    private static bool IsBlankOrComment(string line)
    {
        var trimmed = line.Trim();
        return trimmed.Length == 0 || trimmed[0] == '#';
    }

    private static string Unquote(string value)
    {
        // Strip a trailing inline comment only when the value is unquoted.
        if (value.Length >= 2 &&
            ((value[0] == '\'' && value[^1] == '\'') ||
             (value[0] == '"' && value[^1] == '"')))
        {
            return value[1..^1];
        }

        return value;
    }
}
