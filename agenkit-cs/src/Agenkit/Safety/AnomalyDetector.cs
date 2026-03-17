using Agenkit.Core;

namespace Agenkit.Safety;

/// <summary>
/// Detects anomalous patterns in input messages.
/// </summary>
public class AnomalyDetector
{
    private readonly int _maxContentLength;
    private readonly int _maxRepetitionRatio;
    private readonly IReadOnlyList<string> _suspiciousPatterns;

    /// <summary>Creates an AnomalyDetector with the given thresholds.</summary>
    /// <param name="maxContentLength">Maximum allowed content length.</param>
    /// <param name="maxRepetitionRatio">Maximum ratio (0–100) of repeated characters.</param>
    /// <param name="suspiciousPatterns">List of suspicious string patterns to detect.</param>
    public AnomalyDetector(
        int maxContentLength = 10_000,
        int maxRepetitionRatio = 80,
        IReadOnlyList<string>? suspiciousPatterns = null)
    {
        _maxContentLength = maxContentLength;
        _maxRepetitionRatio = maxRepetitionRatio;
        _suspiciousPatterns = suspiciousPatterns ?? Array.Empty<string>();
    }

    /// <summary>Analyzes a message and returns a list of detected anomalies.</summary>
    public IReadOnlyList<string> Analyze(Message message)
    {
        var anomalies = new List<string>();
        var content = message.ContentString();

        if (content.Length > _maxContentLength)
            anomalies.Add($"content length {content.Length} exceeds threshold {_maxContentLength}");

        if (content.Length > 0)
        {
            var maxChar = content.GroupBy(c => c).Max(g => g.Count());
            var ratio = maxChar * 100 / content.Length;
            if (ratio > _maxRepetitionRatio)
                anomalies.Add($"high character repetition ratio: {ratio}%");
        }

        foreach (var pattern in _suspiciousPatterns)
        {
            if (content.Contains(pattern, StringComparison.OrdinalIgnoreCase))
                anomalies.Add($"suspicious pattern detected: '{pattern}'");
        }

        return anomalies;
    }

    /// <summary>Returns true if the message contains any detected anomalies.</summary>
    public bool IsAnomalous(Message message) => Analyze(message).Count > 0;
}
