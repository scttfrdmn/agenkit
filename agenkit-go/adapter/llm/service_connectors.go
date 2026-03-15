package llm

// VLLMConnector returns an LLM adapter pre-configured for a vLLM inference server.
//
// vLLM is a high-throughput inference engine optimised for GPU clusters.
// It exposes an OpenAI-compatible /v1/chat/completions endpoint.
//
// If baseURL is empty the default "http://localhost:8000/v1" is used.
// Pass a non-empty baseURL to connect to a remote deployment.
//
// Example:
//
//	// Local vLLM server on default port
//	adapter := llm.VLLMConnector("meta-llama/Llama-3.1-8B-Instruct", "")
//	resp, err := adapter.Complete(ctx, messages)
//
//	// Remote deployment
//	adapter := llm.VLLMConnector("meta-llama/Llama-3.1-8B-Instruct", "http://gpu-host:8000/v1")
func VLLMConnector(model, baseURL string) *OpenAICompatibleLLM {
	if baseURL == "" {
		baseURL = "http://localhost:8000/v1"
	}
	return NewOpenAICompatibleLLM(baseURL, model, "vllm", "")
}

// SGLangConnector returns an LLM adapter pre-configured for an SGLang inference server.
//
// SGLang (Structured Generation Language) is optimised for complex prompts,
// structured output, and multi-turn conversations.  It can be 29–64% faster
// than vLLM for certain workloads.
//
// If baseURL is empty the default "http://localhost:30000/v1" is used.
//
// Example:
//
//	adapter := llm.SGLangConnector("meta-llama/Llama-3.1-8B-Instruct", "")
//	resp, err := adapter.Complete(ctx, messages)
func SGLangConnector(model, baseURL string) *OpenAICompatibleLLM {
	if baseURL == "" {
		baseURL = "http://localhost:30000/v1"
	}
	return NewOpenAICompatibleLLM(baseURL, model, "sglang", "")
}

// TensorRTLLMConnector returns an LLM adapter pre-configured for a TensorRT-LLM
// inference server.
//
// TensorRT-LLM is NVIDIA's inference framework that compiles models to optimised
// TensorRT engines.  It is typically served via Triton Inference Server with an
// OpenAI-compatible frontend.
//
// If baseURL is empty the default "http://localhost:8000/v1" is used.
//
// Example:
//
//	adapter := llm.TensorRTLLMConnector("llama-3.1-8b-instruct", "")
//	resp, err := adapter.Complete(ctx, messages)
func TensorRTLLMConnector(model, baseURL string) *OpenAICompatibleLLM {
	if baseURL == "" {
		baseURL = "http://localhost:8000/v1"
	}
	return NewOpenAICompatibleLLM(baseURL, model, "tensorrt-llm", "")
}

// DeepSpeedConnector returns an LLM adapter pre-configured for a DeepSpeed-MII
// inference server.
//
// DeepSpeed-MII (Model Implementations for Inference) provides highly optimised
// inference for large transformer models using DeepSpeed's inference kernels,
// including tensor parallelism and kernel fusion.
//
// If baseURL is empty the default "http://localhost:8000/v1" is used.
//
// Example:
//
//	adapter := llm.DeepSpeedConnector("meta-llama/Llama-3.1-8B-Instruct", "")
//	resp, err := adapter.Complete(ctx, messages)
func DeepSpeedConnector(model, baseURL string) *OpenAICompatibleLLM {
	if baseURL == "" {
		baseURL = "http://localhost:8000/v1"
	}
	return NewOpenAICompatibleLLM(baseURL, model, "deepspeed", "")
}
