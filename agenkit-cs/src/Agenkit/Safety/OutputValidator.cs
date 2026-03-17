using Agenkit.Core;

namespace Agenkit.Safety;

/// <summary>
/// Validates output messages from agents.
/// </summary>
public class OutputValidator
{
    private readonly List<Func<Message, ValidationResult>> _rules = new();

    /// <summary>Adds a custom validation rule.</summary>
    public OutputValidator AddRule(Func<Message, ValidationResult> rule)
    {
        _rules.Add(rule);
        return this;
    }

    /// <summary>Validates an output message against all registered rules.</summary>
    public ValidationResult Validate(Message message)
    {
        foreach (var rule in _rules)
        {
            var result = rule(message);
            if (!result.IsValid) return result;
        }
        return ValidationResult.Ok;
    }

    /// <summary>Returns a validator that rejects empty responses.</summary>
    public static OutputValidator RequireNonEmpty()
    {
        var v = new OutputValidator();
        v.AddRule(m => string.IsNullOrWhiteSpace(m.ContentString())
            ? ValidationResult.Fail("output content must not be empty")
            : ValidationResult.Ok);
        return v;
    }

    /// <summary>Returns a validator that enforces role is "assistant".</summary>
    public static OutputValidator RequireAssistantRole()
    {
        var v = new OutputValidator();
        v.AddRule(m => m.Role == "assistant"
            ? ValidationResult.Ok
            : ValidationResult.Fail($"expected assistant role but got '{m.Role}'"));
        return v;
    }
}
