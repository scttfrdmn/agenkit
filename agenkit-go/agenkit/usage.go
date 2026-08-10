package agenkit

// Usage is a normalized, typed view of the token usage an LLM adapter records
// on a response. It exists so cost-metering, budgeting, and routing layers can
// consume a single struct instead of re-parsing the per-provider
// Metadata["usage"] map (which varies in both key names and value types across
// providers).
//
// This type lives in the core package rather than adapter/llm so that
// observability (TracingMiddleware, which promotes usage onto GenAI span
// attributes per #782) can depend on it without transitively pulling in the AWS
// SDK that adapter/llm carries for the Bedrock adapter (~20 packages) — the same
// reasoning that moved CallOptions here in #805. adapter/llm keeps a type alias
// (llm.Usage) and a forwarding UsageFromMessage so existing code is unaffected.
//
// Fields are zero when the provider does not report them. The cache fields are
// provider-dependent (e.g. Anthropic prompt caching, including via Bedrock) and
// are zero when caching is inactive or unsupported.
type Usage struct {
	PromptTokens     int
	CompletionTokens int
	TotalTokens      int

	// CacheReadTokens is the number of prompt tokens served from a provider
	// prompt cache. These are typically billed at a fraction of normal input
	// token cost. Zero when unknown or caching is inactive.
	CacheReadTokens int

	// CacheCreationTokens is the number of prompt tokens written to a provider
	// prompt cache on this request. Zero when unknown or caching is inactive.
	CacheCreationTokens int
}

// UsageReporter is an optional interface an LLM adapter may implement to let
// consumers detect typed-usage support at compile time. The core LLM interface
// deliberately stays minimal (Complete/Stream/Model/Unwrap); adapters that can
// report usage do so additively.
//
// Adapters in adapter/llm report usage via response Metadata rather than this
// interface; UsageFromMessage is the primary accessor. UsageReporter is
// provided for consumers that wrap an LLM and want to expose aggregate usage.
type UsageReporter interface {
	// Usage returns the most recent token usage and true if available.
	Usage() (Usage, bool)
}

// UsageFromMessage extracts normalized token usage from an adapter response.
//
// It reads the Metadata["usage"] map populated by the adapters in adapter/llm,
// normalizing the two naming conventions in use today:
//   - prompt_tokens / completion_tokens (OpenAI, Bedrock, Gemini, Ollama, LiteLLM, ...)
//   - input_tokens / output_tokens      (Anthropic native)
//
// and the value types in use (int and int32). cache_read_tokens /
// cache_creation_tokens are read when present.
//
// ok is false when the message is nil or carries no usage metadata. When
// total_tokens is absent it is derived as prompt+completion.
func UsageFromMessage(m *Message) (Usage, bool) {
	if m == nil || m.Metadata == nil {
		return Usage{}, false
	}

	raw, ok := m.Metadata["usage"].(map[string]interface{})
	if !ok {
		return Usage{}, false
	}

	// pick returns the first present key, coerced to int.
	pick := func(keys ...string) int {
		for _, k := range keys {
			if v, present := raw[k]; present {
				return toInt(v)
			}
		}
		return 0
	}

	u := Usage{
		PromptTokens:        pick("prompt_tokens", "input_tokens"),
		CompletionTokens:    pick("completion_tokens", "output_tokens"),
		TotalTokens:         pick("total_tokens"),
		CacheReadTokens:     pick("cache_read_tokens", "cache_read_input_tokens"),
		CacheCreationTokens: pick("cache_creation_tokens", "cache_creation_input_tokens", "cache_write_tokens"),
	}

	if u.TotalTokens == 0 {
		u.TotalTokens = u.PromptTokens + u.CompletionTokens
	}

	return u, true
}

// toInt coerces the numeric types adapters store in usage metadata (int, int32,
// int64, and the float64 produced by JSON round-trips) to int. Unknown types
// yield 0.
func toInt(v interface{}) int {
	switch n := v.(type) {
	case int:
		return n
	case int32:
		return int(n)
	case int64:
		return int(n)
	case float64:
		return int(n)
	default:
		return 0
	}
}
