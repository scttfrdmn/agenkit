namespace Agenkit.Evaluation;

/// <summary>
/// A single evaluation metric with name, value, and unit.
/// </summary>
public record Metric(string Name, double Value, string Unit = "")
{
    /// <summary>Returns a human-readable representation.</summary>
    public override string ToString() =>
        string.IsNullOrEmpty(Unit) ? $"{Name}: {Value}" : $"{Name}: {Value} {Unit}";
}
