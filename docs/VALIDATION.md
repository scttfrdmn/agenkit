# Parameter Validation in Agenkit

This document describes the parameter validation approach used across all Agenkit language implementations.

## Philosophy

**Validate early, fail fast**: All LLM parameter validation happens at construction/configuration time, not at API call time. This ensures invalid configurations are caught immediately rather than after expensive API calls.

## Validation Standards

All LLM adapters validate the following parameters:

| Parameter | Valid Range | Description |
|-----------|-------------|-------------|
| `temperature` | 0.0 - 2.0 | Sampling temperature (0 = deterministic, 2 = most random) |
| `max_tokens` | > 0 | Maximum tokens to generate (must be positive integer) |
| `top_p` | 0.0 - 1.0 | Nucleus sampling parameter |
| `frequency_penalty` | -2.0 to 2.0 | Penalty for token frequency (OpenAI/Anthropic) |
| `presence_penalty` | -2.0 to 2.0 | Penalty for token presence (OpenAI/Anthropic) |

**Note**: Not all providers support all parameters. For example:
- Anthropic uses temperature 0-1 (but we standardize on 0-2)
- Gemini has different penalty mechanisms
- Zig's CallOptions supports first 3 parameters directly; others via `extra` field

## Error Messages

All validation errors follow a consistent format:

```
"{parameter} must be {constraint}, got {value}"
```

Examples:
- `"temperature must be between 0 and 2, got 3.5"`
- `"max_tokens must be positive, got -100"`
- `"top_p must be between 0 and 1, got 1.5"`
- `"frequency_penalty must be between -2 and 2, got 2.5"`

## Implementation by Language

### Python

Validation centralized in `agenkit.adapters.llm.base.LLM._validate_llm_params()`:

```python
def _validate_llm_params(
    self,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
) -> None:
    """Validate common LLM parameters."""
    if temperature is not None:
        if not isinstance(temperature, (int, float)):
            raise ValueError("temperature must be a number")
        if not 0 <= temperature <= 2:
            raise ValueError(f"temperature must be between 0 and 2, got {temperature}")

    if max_tokens is not None:
        if not isinstance(max_tokens, int):
            raise ValueError("max_tokens must be an integer")
        if max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {max_tokens}")

    # ... similar validation for other parameters
```

**Error handling**: Raises `ValueError` with descriptive message

**Testing**: See `agenkit/tests/test_llm_validation.py` for comprehensive test suite

### Go

Validation in functional options using panic (idiomatic for builder pattern):

```go
// WithTemperature sets the sampling temperature (0.0-2.0).
func WithTemperature(temperature float64) CallOption {
    if temperature < 0.0 || temperature > 2.0 {
        panic(fmt.Sprintf("temperature must be between 0 and 2, got %v", temperature))
    }
    return func(opts *CallOptions) {
        opts.Temperature = &temperature
    }
}

// WithMaxTokens sets the maximum number of tokens to generate.
func WithMaxTokens(maxTokens int) CallOption {
    if maxTokens <= 0 {
        panic(fmt.Sprintf("max_tokens must be positive, got %d", maxTokens))
    }
    return func(opts *CallOptions) {
        opts.MaxTokens = &maxTokens
    }
}
```

**Error handling**: Uses `panic()` for invalid parameters (fails fast at construction time)

**Location**: `agenkit-go/adapter/llm/llm.go` (lines 179-238)

### TypeScript

Shared validation utility in `agenkit-ts/src/llm/validation.ts`:

```typescript
export interface LLMParams {
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
}

export function validateLLMParams(params: LLMParams): void {
  if (params.temperature !== undefined) {
    if (typeof params.temperature !== 'number' ||
        params.temperature < 0 ||
        params.temperature > 2) {
      throw new Error(
        `temperature must be between 0 and 2, got ${params.temperature}`
      );
    }
  }

  if (params.max_tokens !== undefined) {
    if (typeof params.max_tokens !== 'number' || params.max_tokens <= 0) {
      throw new Error(`max_tokens must be positive, got ${params.max_tokens}`);
    }
  }

  // ... similar validation for other parameters
}
```

**Error handling**: Throws `Error` with descriptive message

**Usage**: All adapters import and use `validateLLMParams()` in constructor

### Rust

Validation at adapter construction (panic or Result-based):

```rust
// Panic-based validation (OpenAI, Anthropic, OpenAICompatible)
pub fn new(config: OpenAIConfig) -> Self {
    // Validate temperature (0-2)
    if !(0.0..=2.0).contains(&config.temperature) {
        panic!(
            "temperature must be between 0 and 2, got {}",
            config.temperature
        );
    }

    // Validate max_tokens (must be positive)
    if config.max_tokens <= 0 {
        panic!("max_tokens must be positive, got {}", config.max_tokens);
    }

    // ... similar validation for other parameters
}

// Result-based validation (Gemini)
pub fn new(config: GeminiConfig) -> Result<Self, AgentError> {
    if let Some(temp) = config.temperature {
        if !(0.0..=2.0).contains(&temp) {
            return Err(AgentError::InvalidInput(
                format!("temperature must be between 0 and 2, got {}", temp)
            ));
        }
    }
    // ... similar validation for other parameters
}
```

**Error handling**:
- `panic!()` for must-succeed constructors (OpenAI, Anthropic, OpenAICompatible)
- `Result<Self, AgentError>` for fallible constructors (Gemini)

**Location**: Individual adapter files in `agenkit-rust/src/adapters/`

### C++

Shared validation utility in `agenkit-cpp/include/agenkit/adapters/validation.hpp`:

```cpp
class LLMParameterValidator {
public:
    static void validate_temperature(double temperature) {
        if (temperature < 0.0 || temperature > 2.0) {
            throw std::invalid_argument(
                "temperature must be between 0 and 2, got " +
                std::to_string(temperature)
            );
        }
    }

    static void validate_max_tokens(int max_tokens) {
        if (max_tokens <= 0) {
            throw std::invalid_argument(
                "max_tokens must be positive, got " +
                std::to_string(max_tokens)
            );
        }
    }

    static void validate_all(
        double temperature,
        int max_tokens,
        double top_p,
        double frequency_penalty = 0.0,
        double presence_penalty = 0.0
    ) {
        validate_temperature(temperature);
        validate_max_tokens(max_tokens);
        validate_top_p(top_p);
        validate_frequency_penalty(frequency_penalty);
        validate_presence_penalty(presence_penalty);
    }
};
```

**Error handling**: Throws `std::invalid_argument` with descriptive message

**Usage**: All adapters use `LLMParameterValidator::validate_all()` in constructor

### Zig

Validation in CallOptions setter methods:

```zig
pub const CallOptions = struct {
    temperature: ?f64 = null,
    max_tokens: ?usize = null,
    top_p: ?f64 = null,
    extra: std.StringHashMap([]const u8),

    /// Set temperature (must be between 0 and 2)
    pub fn withTemperature(self: *CallOptions, temperature: f64) !void {
        if (temperature < 0.0 or temperature > 2.0) {
            return error.InvalidTemperature;
        }
        self.temperature = temperature;
    }

    /// Set max tokens (must be positive)
    pub fn withMaxTokens(self: *CallOptions, max_tokens: usize) !void {
        if (max_tokens == 0) {
            return error.InvalidMaxTokens;
        }
        self.max_tokens = max_tokens;
    }

    /// Set top_p (must be between 0 and 1)
    pub fn withTopP(self: *CallOptions, top_p: f64) !void {
        if (top_p < 0.0 or top_p > 1.0) {
            return error.InvalidTopP;
        }
        self.top_p = top_p;
    }
};
```

**Error handling**: Returns error union (e.g., `error.InvalidTemperature`)

**Location**: `agenkit-zig/src/adapter/llm.zig` (lines 154-175)

## When to Validate

### Construction Time (Recommended)

Validate parameters when the adapter/config is created:

```python
# Python
llm = OpenAILLM(api_key="...", temperature=3.0)  # Raises ValueError immediately

# Go
llm := NewOpenAILLM("sk-...", WithTemperature(3.0))  # Panics immediately

# TypeScript
const llm = new OpenAIAgent({ temperature: 3.0 })  // Throws Error immediately

# Rust
let llm = OpenAIAgent::new(config);  // Panics immediately

# C++
OpenAIAgent gpt(config);  // Throws std::invalid_argument immediately

# Zig
try options.withTemperature(3.0);  // Returns error.InvalidTemperature
```

**Benefits**:
- Fail fast (catch errors before API calls)
- Clear error messages with context
- No wasted API calls or tokens

### Call Time (Not Recommended)

Validating at API call time is **not recommended** because:
- Errors discovered after potentially expensive setup
- May waste API quota on invalid requests
- Less clear error context (which config value was wrong?)

## Testing Validation

### Python Example

See `agenkit/tests/test_llm_validation.py`:

```python
def test_temperature_validation(self):
    """Temperature must be between 0 and 2."""
    llm = MockLLM()

    # Valid temperatures
    llm._validate_llm_params(temperature=0.0)
    llm._validate_llm_params(temperature=2.0)

    # Invalid: too low
    with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
        llm._validate_llm_params(temperature=-0.1)

    # Invalid: too high
    with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
        llm._validate_llm_params(temperature=2.1)
```

### General Testing Pattern

For each language, test:
1. **Valid boundary values**: 0, 1, 2 for temperature; 1, 100, 4096 for max_tokens; 0.0, 0.5, 1.0 for top_p
2. **Invalid low values**: -0.1, -100, -2.1
3. **Invalid high values**: 2.1, 1.1, 2.5
4. **Invalid types** (where applicable): strings, null, undefined
5. **Multiple parameters**: Ensure validation works when setting multiple parameters

## Migration Guide

If you have existing code that sets invalid parameters:

### Before (would fail at API call time)
```python
# May succeed construction but fail later
llm = OpenAILLM(api_key="...", temperature=3.0)
response = llm.complete(messages)  # Fails here (wasted time)
```

### After (fails immediately)
```python
# Fix: Use valid temperature
llm = OpenAILLM(api_key="...", temperature=1.0)  # Succeeds
response = llm.complete(messages)  # Also succeeds
```

## Related Documentation

- **Issue**: #514 - Standardize type validation approach
- **Cross-language Testing**: `tests/cross_language/README.md`
- **API Alignment**: ROADMAP.md - Phase 2B/2C

## Summary

All Agenkit language implementations now enforce consistent parameter validation:
- ✅ Validation happens at construction time (fail fast)
- ✅ Error messages follow consistent format
- ✅ All parameters use standardized ranges
- ✅ Each language uses idiomatic error handling
- ✅ Comprehensive test coverage (Python; recommended for other languages)

This ensures users get immediate, clear feedback when configuring LLM adapters incorrectly.
