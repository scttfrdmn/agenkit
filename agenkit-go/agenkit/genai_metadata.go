package agenkit

// Well-known Message.Metadata keys used to plumb GenAI attributes from an LLM
// adapter response through to observability.TracingMiddleware, which promotes
// them onto span attributes per docs/OTEL_CONVENTION.md's GenAI attributes
// table (#782).
//
// adapter/llm adapters populate these alongside the pre-existing "model" and
// "usage" keys on the response Message they return from Complete/Stream.
// Patterns that pass an LLM response through unchanged as their own
// Agent.Process response (the common case — see e.g. ConversationalAgent) carry
// these keys to the outer response with no extra plumbing, so
// TracingMiddleware sees them without needing to know about adapter/llm at
// all (observability does not import adapter/llm, which transitively pulls in
// the AWS SDK; see the Usage type doc for why that boundary matters).
//
// These live in the core package, next to Usage, so both adapter/llm and
// observability agree on the exact strings without either importing the
// other.
const (
	// MetadataKeyGenAISystem is the provider name, e.g. "anthropic",
	// "aws.bedrock", "openai". Promoted to the gen_ai.system span attribute.
	MetadataKeyGenAISystem = "gen_ai_system"

	// MetadataKeyRequestModel is the model id as requested — may be an alias.
	// Promoted to gen_ai.request.model.
	MetadataKeyRequestModel = "request_model"

	// MetadataKeyResponseModel is the model id as served, resolved to an
	// explicit version when the provider reports one. Adapters whose provider
	// API does not resolve a distinct value (e.g. Bedrock's Converse response)
	// set this equal to the requested model — deliberately: docs/OTEL_CONVENTION.md
	// requires both gen_ai.request.model and gen_ai.response.model to be emitted
	// even when equal, since that is what lets a consumer detect a mismatch
	// instead of assuming the invariant holds. Promoted to gen_ai.response.model.
	MetadataKeyResponseModel = "response_model"

	// MetadataKeyCostMicroUnits is the cost of this call in integer micro-units
	// of currency (1,000,000 micro-units = 1 unit), never a float — float
	// currency accumulates rounding error across a large span tree. The
	// currency itself is out of band. Promoted to agenkit.cost.micro_units.
	MetadataKeyCostMicroUnits = "cost_micro_units"

	// MetadataKeyRetryCount is the number of transport retries for this call —
	// a call failed and was reissued. Distinct from MetadataKeyVerifyRetries:
	// summing the two would conflate "unreliable dependency" with "model not
	// meeting the bar." Promoted to agenkit.retry.count.
	MetadataKeyRetryCount = "retry_count"

	// MetadataKeyVerifyRetries is the number of quality retries for this call —
	// a call succeeded, its output was rejected by a verifier, and it was
	// reissued. Promoted to agenkit.verify.retries.
	MetadataKeyVerifyRetries = "verify_retries"
)
