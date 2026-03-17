using Agenkit.Core;

namespace Agenkit.Safety;

/// <summary>Validation result.</summary>
public record ValidationResult(bool IsValid, string? Error = null)
{
    /// <summary>A passing validation result.</summary>
    public static readonly ValidationResult Ok = new(true);

    /// <summary>Creates a failing result with the given error.</summary>
    public static ValidationResult Fail(string error) => new(false, error);
}

/// <summary>
/// Validates input messages before they reach an agent.
/// </summary>
public class InputValidator
{
    private readonly List<Func<Message, ValidationResult>> _rules = new();

    /// <summary>Adds a custom validation rule.</summary>
    public InputValidator AddRule(Func<Message, ValidationResult> rule)
    {
        _rules.Add(rule);
        return this;
    }

    /// <summary>Validates a message against all registered rules.</summary>
    public ValidationResult Validate(Message message)
    {
        foreach (var rule in _rules)
        {
            var result = rule(message);
            if (!result.IsValid) return result;
        }
        return ValidationResult.Ok;
    }

    /// <summary>Returns a validator that enforces max content length.</summary>
    public static InputValidator WithMaxLength(int maxLength)
    {
        var v = new InputValidator();
        v.AddRule(m =>
        {
            var len = m.ContentString().Length;
            return len <= maxLength
                ? ValidationResult.Ok
                : ValidationResult.Fail($"content length {len} exceeds maximum {maxLength}");
        });
        return v;
    }

    /// <summary>Returns a validator that blocks messages containing forbidden patterns.</summary>
    public static InputValidator WithBlocklist(IReadOnlyList<string> blocklist)
    {
        var v = new InputValidator();
        v.AddRule(m =>
        {
            var content = m.ContentString().ToLowerInvariant();
            foreach (var term in blocklist)
            {
                if (content.Contains(term, StringComparison.OrdinalIgnoreCase))
                    return ValidationResult.Fail($"content contains blocked term: '{term}'");
            }
            return ValidationResult.Ok;
        });
        return v;
    }
}
