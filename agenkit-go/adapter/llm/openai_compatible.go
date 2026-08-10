package llm

import (
	"context"
	"errors"
	"fmt"
	"io"

	"github.com/sashabaranov/go-openai"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// OpenAICompatibleLLM is a generic adapter for OpenAI-compatible inference services.
//
// This adapter enables Agenkit to work with any service implementing the
// OpenAI Chat Completions API by configuring the go-openai SDK with a custom
// base URL. This provides a consistent interface across different local and
// self-hosted inference engines.
//
// Supported services include:
//   - vLLM: High-throughput batch inference
//   - llama.cpp: Lightweight C++ implementation (CPU-friendly)
//   - SGLang: Optimized for complex prompts
//   - TensorRT-LLM: NVIDIA GPU optimized
//   - OpenLLM: Multi-model serving platform
//   - MLC LLM: Mobile and edge deployment
//   - Text Generation Inference (TGI): HuggingFace inference server
//   - Inferflow: High-performance inference
//
// Example - vLLM local deployment:
//
//	llm := NewOpenAICompatibleLLM(
//	    "http://localhost:8000/v1",
//	    "meta-llama/Llama-2-7b-chat-hf",
//	    "vllm",
//	    "",
//	)
//	messages := []*agenkit.Message{
//	    agenkit.NewMessage("user", "Hello!"),
//	}
//	response, err := llm.Complete(ctx, messages)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	fmt.Println(response.ContentString())
//
// Example - llama.cpp server:
//
//	llm := NewOpenAICompatibleLLM(
//	    "http://localhost:8080/v1",
//	    "llama-2-7b-chat",
//	    "llamacpp",
//	    "",
//	)
//
// Example - Streaming:
//
//	stream, err := llm.Stream(ctx, messages)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	for chunk := range stream {
//	    fmt.Print(chunk.ContentString())
//	}
type OpenAICompatibleLLM struct {
	client   *openai.Client
	model    string
	provider string
	baseURL  string
}

// NewOpenAICompatibleLLM creates a new OpenAI-compatible LLM adapter.
//
// Parameters:
//   - baseURL: Base URL of the inference service (e.g., "http://localhost:8000/v1").
//     Must include the /v1 suffix for most services.
//   - model: Model name/identifier used by the inference service. Format varies
//     by service (e.g., "meta-llama/Llama-2-7b-chat-hf" for vLLM,
//     "llama-2-7b-chat" for llama.cpp).
//   - provider: Optional provider name for metadata and debugging (e.g., "vllm",
//     "llamacpp", "sglang"). Helps identify which service is being used.
//   - apiKey: Optional API key. Most local services don't require authentication,
//     so this can be empty. If empty, defaults to "not-needed".
//
// Example - vLLM:
//
//	llm := NewOpenAICompatibleLLM(
//	    "http://localhost:8000/v1",
//	    "meta-llama/Llama-2-7b-chat-hf",
//	    "vllm",
//	    "",
//	)
//
// Example - llama.cpp:
//
//	llm := NewOpenAICompatibleLLM(
//	    "http://localhost:8080/v1",
//	    "llama-2-7b-chat",
//	    "llamacpp",
//	    "",
//	)
//
// Example - SGLang with API key:
//
//	llm := NewOpenAICompatibleLLM(
//	    "http://localhost:30000/v1",
//	    "meta-llama/Llama-2-13b-chat-hf",
//	    "sglang",
//	    "your-api-key",
//	)
func NewOpenAICompatibleLLM(baseURL, model, provider, apiKey string) *OpenAICompatibleLLM {
	// Many local services don't require authentication
	if apiKey == "" {
		apiKey = "not-needed"
	}

	// Configure client with custom base URL
	config := openai.DefaultConfig(apiKey)
	config.BaseURL = baseURL

	client := openai.NewClientWithConfig(config)

	return &OpenAICompatibleLLM{
		client:   client,
		model:    model,
		provider: provider,
		baseURL:  baseURL,
	}
}

// Model returns the model identifier.
func (o *OpenAICompatibleLLM) Model() string {
	return o.model
}

// Complete generates a completion from the OpenAI-compatible service.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Response as Agenkit Message with metadata including:
//   - model: Model identifier used
//   - usage: Token counts (prompt_tokens, completion_tokens, total_tokens)
//   - finish_reason: Why generation stopped (stop, length, etc.)
//   - provider: Provider name if specified during initialization
//   - base_url: Service URL for debugging
//   - id: Response ID from the service
//
// Example:
//
//	messages := []*agenkit.Message{
//	    agenkit.NewMessage("system", "You are a helpful assistant."),
//	    agenkit.NewMessage("user", "What is 2+2?"),
//	}
//	response, err := llm.Complete(ctx, messages, WithTemperature(0.2))
//	if err != nil {
//	    log.Fatal(err)
//	}
//	fmt.Println(response.ContentString())
//	fmt.Printf("Provider: %s\n", response.Metadata["provider"])
//	fmt.Printf("Tokens: %v\n", response.Metadata["usage"])
func (o *OpenAICompatibleLLM) Complete(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (*agenkit.Message, error) {
	// Build options
	options := BuildCallOptions(opts...)

	// Convert Agenkit Messages to OpenAI format
	openaiMessages := o.convertMessages(messages)

	// Build request
	req := openai.ChatCompletionRequest{
		Model:    o.model,
		Messages: openaiMessages,
	}

	// Apply options
	if options.Temperature != nil {
		temp := float32(*options.Temperature)
		req.Temperature = temp
	}
	if options.MaxTokens != nil {
		req.MaxTokens = *options.MaxTokens
	}
	if options.TopP != nil {
		topP := float32(*options.TopP)
		req.TopP = topP
	}

	// Apply extra options
	if fp, ok := options.Extra["frequency_penalty"].(float64); ok {
		fpFloat := float32(fp)
		req.FrequencyPenalty = fpFloat
	}
	if pp, ok := options.Extra["presence_penalty"].(float64); ok {
		ppFloat := float32(pp)
		req.PresencePenalty = ppFloat
	}
	if stop, ok := options.Extra["stop"].([]string); ok {
		req.Stop = stop
	}

	// Call OpenAI-compatible API
	resp, err := o.client.CreateChatCompletion(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("openai-compatible api error: %w", err)
	}

	// Check for valid response
	if len(resp.Choices) == 0 {
		return nil, errors.New("service returned no choices")
	}

	// Convert response to Agenkit Message with provider metadata
	response := agenkit.NewMessage("agent", resp.Choices[0].Message.Content)
	response.Metadata["model"] = resp.Model
	response.Metadata["usage"] = map[string]interface{}{
		"prompt_tokens":     resp.Usage.PromptTokens,
		"completion_tokens": resp.Usage.CompletionTokens,
		"total_tokens":      resp.Usage.TotalTokens,
	}
	response.Metadata["finish_reason"] = resp.Choices[0].FinishReason
	response.Metadata["id"] = resp.ID

	// Add provider metadata for debugging and monitoring
	genAISystem := "openai_compatible"
	if o.provider != "" {
		response.Metadata["provider"] = o.provider
		genAISystem = o.provider
	} else {
		response.Metadata["provider"] = "openai_compatible"
	}
	response.Metadata["base_url"] = o.baseURL

	// GenAI semconv promotion (#782). gen_ai.system uses the configured
	// provider name (e.g. "vllm", "sglang") rather than a fixed semconv enum
	// value, since these are self-hosted/local services the semconv list does
	// not cover — see docs/OTEL_CONVENTION.md's note that a custom system
	// should use a custom friendly name.
	response.Metadata[agenkit.MetadataKeyGenAISystem] = genAISystem
	response.Metadata[agenkit.MetadataKeyRequestModel] = o.model
	response.Metadata[agenkit.MetadataKeyResponseModel] = resp.Model

	return response, nil
}

// Stream generates completion chunks from the OpenAI-compatible service.
//
// This method streams response chunks as they're generated by the service,
// enabling real-time display and lower perceived latency for users.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Channel of Message chunks as they arrive from the service
//   - Error if streaming cannot be initiated
//
// Example:
//
//	messages := []*agenkit.Message{
//	    agenkit.NewMessage("user", "Count to 10"),
//	}
//	stream, err := llm.Stream(ctx, messages)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	for chunk := range stream {
//	    fmt.Print(chunk.ContentString())
//	}
//
// Example - accumulate full response:
//
//	var fullResponse string
//	for chunk := range stream {
//	    fullResponse += chunk.ContentString()
//	}
//	fmt.Println(fullResponse)
//
// Note:
//
//	Not all OpenAI-compatible services support streaming. If the service
//	doesn't support it, you'll get an error from the underlying service.
func (o *OpenAICompatibleLLM) Stream(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (<-chan *agenkit.Message, error) {
	// Build options
	options := BuildCallOptions(opts...)

	// Convert messages
	openaiMessages := o.convertMessages(messages)

	// Build request
	req := openai.ChatCompletionRequest{
		Model:    o.model,
		Messages: openaiMessages,
		Stream:   true,
	}

	// Apply options
	if options.Temperature != nil {
		temp := float32(*options.Temperature)
		req.Temperature = temp
	}
	if options.MaxTokens != nil {
		req.MaxTokens = *options.MaxTokens
	}
	if options.TopP != nil {
		topP := float32(*options.TopP)
		req.TopP = topP
	}

	// Create stream
	stream, err := o.client.CreateChatCompletionStream(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("openai-compatible stream error: %w", err)
	}

	// Create channel for messages
	messageChan := make(chan *agenkit.Message)

	// Start goroutine to read stream
	go func() {
		defer close(messageChan)
		defer func() { _ = stream.Close() }()

		for {
			response, err := stream.Recv()
			if errors.Is(err, io.EOF) {
				return
			}
			if err != nil {
				// On error, send an error message and return
				errorMsg := agenkit.NewMessage("agent", "")
				errorMsg.Metadata["error"] = err.Error()
				errorMsg.Metadata["streaming"] = true
				messageChan <- errorMsg
				return
			}

			// Extract content from delta
			if len(response.Choices) > 0 {
				delta := response.Choices[0].Delta
				if delta.Content != "" {
					chunk := agenkit.NewMessage("agent", delta.Content)
					chunk.Metadata["streaming"] = true
					chunk.Metadata["model"] = o.model
					if o.provider != "" {
						chunk.Metadata["provider"] = o.provider
					} else {
						chunk.Metadata["provider"] = "openai_compatible"
					}
					messageChan <- chunk
				}
			}
		}
	}()

	return messageChan, nil
}

// convertMessages converts Agenkit Messages to OpenAI format.
//
// OpenAI-compatible services expect messages in the format:
//   - role: "system", "user", or "assistant"
//   - content: string
//
// Agenkit uses "agent" role which gets mapped to "assistant" for compatibility.
func (o *OpenAICompatibleLLM) convertMessages(messages []*agenkit.Message) []openai.ChatCompletionMessage {
	openaiMessages := make([]openai.ChatCompletionMessage, 0, len(messages))

	for _, msg := range messages {
		// Map roles for OpenAI compatibility
		var role string
		switch msg.Role {
		case "system", "user", "tool":
			role = msg.Role
		default:
			// Map "agent" and others to "assistant"
			role = "assistant"
		}

		openaiMessages = append(openaiMessages, openai.ChatCompletionMessage{
			Role:    role,
			Content: msg.ContentString(),
		})
	}

	return openaiMessages
}

// Unwrap returns the underlying OpenAI client.
//
// This provides an escape hatch for accessing OpenAI SDK features
// not exposed by the minimal LLM interface. Useful for advanced use cases
// like custom request handling or service-specific features.
//
// Returns:
//
//	The *openai.Client configured with custom base URL
//
// Example:
//
//	llm := NewOpenAICompatibleLLM(
//	    "http://localhost:8000/v1",
//	    "llama-2-7b",
//	    "vllm",
//	    "",
//	)
//	client := llm.Unwrap().(*openai.Client)
//	// Use OpenAI SDK features directly
//	resp, err := client.CreateChatCompletion(...)
//
// Warning:
//
//	Using Unwrap() breaks provider portability. Code that uses Unwrap()
//	will need changes when switching between services or providers.
func (o *OpenAICompatibleLLM) Unwrap() interface{} {
	return o.client
}
