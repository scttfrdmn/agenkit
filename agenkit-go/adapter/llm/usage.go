package llm

import "github.com/scttfrdmn/agenkit/agenkit-go/agenkit"

// Usage is a normalized, typed view of the token usage an LLM adapter records
// on a response. It exists so cost-metering, budgeting, and routing layers can
// consume a single struct instead of re-parsing the per-provider
// Metadata["usage"] map (which varies in both key names and value types across
// providers).
//
// Aliased from the core agenkit package (#782), where the type now lives so
// that observability.TracingMiddleware can promote usage onto GenAI span
// attributes without importing adapter/llm — which transitively pulls in the
// AWS SDK via the Bedrock adapter (#805, the same reasoning that moved
// CallOptions). This is a true alias, not a conversion: llm.Usage and
// agenkit.Usage are the same type, so existing code using llm.Usage /
// llm.UsageFromMessage is unaffected.
//
// Fields are zero when the provider does not report them. The cache fields are
// provider-dependent (e.g. Anthropic prompt caching, including via Bedrock) and
// are zero when caching is inactive or unsupported.
type Usage = agenkit.Usage

// UsageReporter is an optional interface an LLM adapter may implement to let
// consumers detect typed-usage support at compile time. The core LLM interface
// deliberately stays minimal (Complete/Stream/Model/Unwrap); adapters that can
// report usage do so additively.
//
// Adapters in this package report usage via response Metadata rather than this
// interface; UsageFromMessage is the primary accessor. UsageReporter is
// provided for consumers that wrap an LLM and want to expose aggregate usage.
type UsageReporter = agenkit.UsageReporter

// UsageFromMessage extracts normalized token usage from an adapter response.
//
// It reads the Metadata["usage"] map populated by the adapters in this package,
// normalizing the two naming conventions in use today:
//   - prompt_tokens / completion_tokens (OpenAI, Bedrock, Gemini, Ollama, LiteLLM, ...)
//   - input_tokens / output_tokens      (Anthropic native)
//
// and the value types in use (int and int32). cache_read_tokens /
// cache_creation_tokens are read when present.
//
// ok is false when the message is nil or carries no usage metadata. When
// total_tokens is absent it is derived as prompt+completion.
var UsageFromMessage = agenkit.UsageFromMessage
