namespace Agenkit.Core;

/// <summary>
/// Represents the result of a tool execution.
/// </summary>
public record ToolResult(
    bool Success,
    object? Data,
    string? Error = null,
    IReadOnlyDictionary<string, object>? Metadata = null)
{
    /// <summary>Creates a successful tool result with the given data.</summary>
    public static ToolResult Ok(object? data) => new(true, data);

    /// <summary>Creates a failed tool result with the given error message.</summary>
    public static ToolResult Fail(string error) => new(false, null, error);

    /// <summary>Returns a new ToolResult with additional metadata.</summary>
    public ToolResult WithMetadata(string key, object value)
    {
        var meta = Metadata is not null
            ? new Dictionary<string, object>(Metadata) { [key] = value }
            : new Dictionary<string, object> { [key] = value };
        return this with { Metadata = meta };
    }
}
