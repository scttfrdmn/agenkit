using Agenkit.Core;

namespace Agenkit.Adapters;

/// <summary>
/// Abstraction over LLM backends (OpenAI, Anthropic, etc.).
/// </summary>
public interface ILlmClient
{
    /// <summary>Sends a conversation to the LLM and returns the next assistant message.</summary>
    Task<Message> ChatAsync(IList<Message> messages, CancellationToken ct = default);
}
