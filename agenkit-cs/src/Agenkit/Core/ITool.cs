namespace Agenkit.Core;

/// <summary>
/// Represents an executable capability that agents can use.
/// </summary>
public interface ITool
{
    /// <summary>Returns the unique name of this tool.</summary>
    string Name { get; }

    /// <summary>Returns a human-readable description of what this tool does.</summary>
    string Description { get; }

    /// <summary>Executes the tool with the given parameters and returns a result.</summary>
    Task<ToolResult> ExecuteAsync(IDictionary<string, object> parameters, CancellationToken ct = default);
}
