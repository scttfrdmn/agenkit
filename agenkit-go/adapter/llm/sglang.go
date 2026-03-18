package llm

// SGLangLLM is an LLM adapter for an SGLang inference server.
// It wraps OpenAICompatibleLLM with SGLang-specific defaults and
// native structured-generation helpers.
//
// Default base URL: http://localhost:30000/v1
//
// Example:
//
//	adapter := llm.NewSGLangLLM("meta-llama/Llama-3.1-8B-Instruct", "")
//	schema := `{"type":"object","properties":{"answer":{"type":"string"}}}`
//	resp, err := adapter.Complete(ctx, messages,
//	    llm.WithSGLangJSONSchema(schema),
//	)
type SGLangLLM struct {
	*OpenAICompatibleLLM
}

// NewSGLangLLM returns an LLM adapter for an SGLang server.
// Pass an empty baseURL to use the default "http://localhost:30000/v1".
//
// Example:
//
//	// Local SGLang server on default port
//	adapter := llm.NewSGLangLLM("meta-llama/Llama-3.1-8B-Instruct", "")
//
//	// Remote deployment
//	adapter := llm.NewSGLangLLM("meta-llama/Llama-3.1-8B-Instruct", "http://gpu-host:30000/v1")
func NewSGLangLLM(model, baseURL string) *SGLangLLM {
	if baseURL == "" {
		baseURL = "http://localhost:30000/v1"
	}
	return &SGLangLLM{NewOpenAICompatibleLLM(baseURL, model, "sglang", "")}
}

// WithSGLangJSONSchema constrains output to conform to the given JSON schema string.
func WithSGLangJSONSchema(schema string) CallOption { return WithExtra("json_schema", schema) }

// WithSGLangRegex constrains output to strings matching the given regex.
func WithSGLangRegex(pattern string) CallOption { return WithExtra("regex", pattern) }

// WithSGLangEBNF constrains output using an EBNF grammar string.
func WithSGLangEBNF(grammar string) CallOption { return WithExtra("ebnf", grammar) }

// WithSGLangReturnLogprob enables log-probability output in the response.
func WithSGLangReturnLogprob(enabled bool) CallOption { return WithExtra("return_logprob", enabled) }
