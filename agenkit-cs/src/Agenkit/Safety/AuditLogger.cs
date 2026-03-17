using Agenkit.Core;
using Microsoft.Extensions.Logging;

namespace Agenkit.Safety;

/// <summary>
/// Logs all agent interactions for audit purposes.
/// </summary>
public class AuditLogger
{
    private readonly ILogger _logger;
    private readonly List<AuditEntry> _entries = new();

    /// <summary>Creates an AuditLogger using the provided ILogger.</summary>
    public AuditLogger(ILogger logger) => _logger = logger;

    /// <summary>Creates an AuditLogger that stores entries only in memory.</summary>
    public AuditLogger() : this(Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance) { }

    /// <summary>Logs an agent interaction.</summary>
    public void Log(string agentName, Message input, Message output, TimeSpan latency)
    {
        var entry = new AuditEntry(agentName, input, output, latency, DateTimeOffset.UtcNow);
        lock (_entries) _entries.Add(entry);
        _logger.LogInformation(
            "Agent {AgentName} processed message in {LatencyMs}ms",
            agentName, latency.TotalMilliseconds);
    }

    /// <summary>Returns a snapshot of all audit entries.</summary>
    public IReadOnlyList<AuditEntry> GetEntries()
    {
        lock (_entries) return _entries.ToList();
    }
}

/// <summary>A single audit log entry.</summary>
public record AuditEntry(
    string AgentName,
    Message Input,
    Message Output,
    TimeSpan Latency,
    DateTimeOffset Timestamp);
