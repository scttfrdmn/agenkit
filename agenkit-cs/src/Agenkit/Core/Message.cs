namespace Agenkit.Core;

/// <summary>
/// Represents a message exchanged between agents or with users.
/// </summary>
public record Message(
    string Role,
    object? Content,
    IReadOnlyDictionary<string, object>? Metadata = null,
    DateTimeOffset? Timestamp = null)
{
    private static readonly HashSet<string> AllowedRoles = new(StringComparer.Ordinal)
    {
        "user", "assistant", "system", "tool", "agent"
    };

    private const int MaxContentBytes = 16 * 1024 * 1024; // 16MB
    private const int MaxMetadataKeys = 100;
    private const int MaxKeyLength = 50;
    private const int MaxRoleLength = 20;

    /// <summary>
    /// Returns the message content as a string.
    /// </summary>
    public string ContentString() => Content switch
    {
        string s => s,
        null => "",
        _ => Content.ToString() ?? ""
    };

    /// <summary>
    /// Creates a new message with the given role and content.
    /// </summary>
    public static Message NewMessage(string role, string content) =>
        new(role, content, new Dictionary<string, object>(), DateTimeOffset.UtcNow);

    /// <summary>
    /// Validates the message and returns it. Throws ArgumentException if invalid.
    /// </summary>
    public Message Validate()
    {
        if (string.IsNullOrEmpty(Role))
            throw new ArgumentException("message role cannot be empty");

        if (Role.Length > MaxRoleLength)
            throw new ArgumentException(
                $"message role exceeds maximum length of {MaxRoleLength} characters (got {Role.Length})");

        if (!AllowedRoles.Contains(Role))
            throw new ArgumentException(
                $"invalid message role: {Role}. Must be one of: user, assistant, system, tool, agent");

        // Content size validation
        var contentSize = Content switch
        {
            string s => System.Text.Encoding.UTF8.GetByteCount(s),
            null => 0,
            _ => System.Text.Encoding.UTF8.GetByteCount(Content.ToString() ?? "")
        };

        if (contentSize > MaxContentBytes)
            throw new ArgumentException(
                $"message content exceeds maximum size of {MaxContentBytes} bytes (got {contentSize} bytes)");

        if (Metadata is not null)
        {
            if (Metadata.Count > MaxMetadataKeys)
                throw new ArgumentException(
                    $"message metadata exceeds maximum of {MaxMetadataKeys} keys (got {Metadata.Count})");

            foreach (var (key, value) in Metadata)
            {
                if (key.Length > MaxKeyLength)
                    throw new ArgumentException(
                        $"metadata key '{key[..Math.Min(20, key.Length)]}...' exceeds maximum length of {MaxKeyLength} characters (got {key.Length})");

                var valueStr = value?.ToString() ?? "";
                var valueSize = System.Text.Encoding.UTF8.GetByteCount(valueStr);
                if (valueSize > MaxContentBytes)
                    throw new ArgumentException(
                        $"metadata value for key '{key}' exceeds maximum size of {MaxContentBytes} bytes (got {valueSize} bytes)");
            }
        }

        return this;
    }

    /// <summary>
    /// Returns a new message with additional metadata.
    /// </summary>
    public Message WithMetadata(string key, object value)
    {
        var meta = Metadata is not null
            ? new Dictionary<string, object>(Metadata) { [key] = value }
            : new Dictionary<string, object> { [key] = value };
        return this with { Metadata = meta };
    }
}
