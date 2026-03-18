package llm

// VllmLLM is an LLM adapter for a vLLM inference server.
// It wraps OpenAICompatibleLLM with vLLM-specific defaults and
// structured-output helpers.
//
// Default base URL: http://localhost:8000/v1
//
// Example:
//
//	adapter := llm.NewVllmLLM("meta-llama/Llama-3.1-8B-Instruct", "")
//	resp, err := adapter.Complete(ctx, messages,
//	    llm.WithVllmGuidedRegex(`[A-Za-z ,.'!?]+`),
//	)
type VllmLLM struct {
	*OpenAICompatibleLLM
}

// NewVllmLLM returns an LLM adapter for a vLLM server.
// Pass an empty baseURL to use the default "http://localhost:8000/v1".
//
// Example:
//
//	// Local vLLM server on default port
//	adapter := llm.NewVllmLLM("meta-llama/Llama-3.1-8B-Instruct", "")
//
//	// Remote deployment
//	adapter := llm.NewVllmLLM("meta-llama/Llama-3.1-8B-Instruct", "http://gpu-host:8000/v1")
func NewVllmLLM(model, baseURL string) *VllmLLM {
	if baseURL == "" {
		baseURL = "http://localhost:8000/v1"
	}
	return &VllmLLM{NewOpenAICompatibleLLM(baseURL, model, "vllm", "")}
}

// WithVllmGuidedJSON constrains output to conform to the given JSON schema.
// The schema can be any JSON-serialisable value (map, struct, etc.).
func WithVllmGuidedJSON(schema interface{}) CallOption { return WithExtra("guided_json", schema) }

// WithVllmGuidedRegex constrains output to strings matching the given regex.
func WithVllmGuidedRegex(pattern string) CallOption { return WithExtra("guided_regex", pattern) }

// WithVllmGuidedGrammar constrains output using a context-free grammar string.
func WithVllmGuidedGrammar(grammar string) CallOption { return WithExtra("guided_grammar", grammar) }

// WithVllmBestOf samples n completions server-side and returns the best one.
func WithVllmBestOf(n int) CallOption { return WithExtra("best_of", n) }

// WithVllmUseBeamSearch enables beam-search sampling.
func WithVllmUseBeamSearch(use bool) CallOption { return WithExtra("use_beam_search", use) }
