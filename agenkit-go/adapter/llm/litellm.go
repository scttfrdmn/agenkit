package llm

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// LiteLLMLLM is an adapter for LiteLLM proxy.
//
// LiteLLM is a universal LLM gateway that provides an OpenAI-compatible API
// for 100+ LLM providers. This adapter communicates with a LiteLLM proxy server
// using HTTP requests in OpenAI format.
//
// Supported providers through LiteLLM include:
//   - OpenAI (gpt-4, gpt-3.5-turbo)
//   - Anthropic (claude-3-5-sonnet-20241022)
//   - AWS Bedrock (bedrock/anthropic.claude-v2)
//   - Google Gemini (gemini/gemini-pro)
//   - Azure OpenAI (azure/gpt-4)
//   - Cohere (command-r-plus)
//   - Local models (ollama/llama2, ollama/mistral)
//   - And 100+ more!
//
// Example:
//
//	llm := NewLiteLLMLLM("http://localhost:4000", "gpt-4")
//	messages := []*agenkit.Message{
//	    agenkit.NewMessage("user", "Hello!"),
//	}
//	response, err := llm.Complete(ctx, messages)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	fmt.Println(response.Content)
//
// Streaming example:
//
//	stream, err := llm.Stream(ctx, messages)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	for chunk := range stream {
//	    fmt.Print(chunk.Content)
//	}
//
// Provider-specific options:
//
//	response, err := llm.Complete(
//	    ctx,
//	    messages,
//	    WithTemperature(0.7),
//	    WithMaxTokens(1024),
//	    WithTopP(0.9),
//	)
type LiteLLMLLM struct {
	baseURL    string
	model      string
	httpClient *http.Client
	apiKey     string // Optional API key for LiteLLM proxy auth
}

// NewLiteLLMLLM creates a new LiteLLM adapter.
//
// Parameters:
//   - baseURL: LiteLLM proxy URL (e.g., "http://localhost:4000")
//   - model: Model identifier in LiteLLM format
//
// Example:
//
//	// OpenAI through LiteLLM
//	llm := NewLiteLLMLLM("http://localhost:4000", "gpt-4")
//
//	// Anthropic through LiteLLM
//	llm := NewLiteLLMLLM("http://localhost:4000", "claude-3-5-sonnet-20241022")
//
//	// AWS Bedrock through LiteLLM
//	llm := NewLiteLLMLLM("http://localhost:4000", "bedrock/anthropic.claude-v2")
//
//	// Local Ollama through LiteLLM
//	llm := NewLiteLLMLLM("http://localhost:4000", "ollama/llama2")
func NewLiteLLMLLM(baseURL, model string) *LiteLLMLLM {
	if baseURL == "" {
		baseURL = "http://localhost:4000"
	}
	if model == "" {
		model = "gpt-3.5-turbo"
	}
	return &LiteLLMLLM{
		baseURL:    baseURL,
		model:      model,
		httpClient: &http.Client{},
	}
}

// NewLiteLLMLLMWithAuth creates a new LiteLLM adapter with API key authentication.
//
// Parameters:
//   - baseURL: LiteLLM proxy URL
//   - model: Model identifier
//   - apiKey: API key for LiteLLM proxy authentication
//
// Example:
//
//	llm := NewLiteLLMLLMWithAuth("http://localhost:4000", "gpt-4", "sk-litellm-...")
func NewLiteLLMLLMWithAuth(baseURL, model, apiKey string) *LiteLLMLLM {
	llm := NewLiteLLMLLM(baseURL, model)
	llm.apiKey = apiKey
	return llm
}

// Model returns the model identifier.
func (l *LiteLLMLLM) Model() string {
	return l.model
}

// litellmRequest is the request structure for LiteLLM's OpenAI-compatible API.
type litellmRequest struct {
	Model       string           `json:"model"`
	Messages    []litellmMessage `json:"messages"`
	Temperature *float64         `json:"temperature,omitempty"`
	MaxTokens   *int             `json:"max_tokens,omitempty"`
	TopP        *float64         `json:"top_p,omitempty"`
	Stream      bool             `json:"stream,omitempty"`
}

// litellmMessage is a message in OpenAI/LiteLLM format.
type litellmMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// litellmResponse is the response structure from LiteLLM's API.
type litellmResponse struct {
	ID      string          `json:"id"`
	Object  string          `json:"object"`
	Created int64           `json:"created"`
	Model   string          `json:"model"`
	Choices []litellmChoice `json:"choices"`
	Usage   litellmUsage    `json:"usage"`
}

// litellmChoice represents a completion choice.
type litellmChoice struct {
	Index        int            `json:"index"`
	Message      litellmMessage `json:"message"`
	FinishReason string         `json:"finish_reason"`
}

// litellmUsage contains token usage information.
type litellmUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// litellmStreamChunk represents a streaming response chunk.
type litellmStreamChunk struct {
	ID      string                `json:"id"`
	Object  string                `json:"object"`
	Created int64                 `json:"created"`
	Model   string                `json:"model"`
	Choices []litellmStreamChoice `json:"choices"`
}

// litellmStreamChoice represents a streaming choice.
type litellmStreamChoice struct {
	Index        int          `json:"index"`
	Delta        litellmDelta `json:"delta"`
	FinishReason *string      `json:"finish_reason"`
}

// litellmDelta represents a streaming delta.
type litellmDelta struct {
	Role    string `json:"role,omitempty"`
	Content string `json:"content,omitempty"`
}

// Complete generates a completion via LiteLLM proxy.
//
// LiteLLM automatically routes to the correct provider based on the
// model string and handles the provider-specific API calls.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Response as Agenkit Message with metadata including:
//   - model: Model used (may differ from requested)
//   - usage: Token counts (if provided by provider)
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
//	fmt.Println(response.Content)
//	fmt.Printf("Usage: %+v\n", response.Metadata["usage"])
func (l *LiteLLMLLM) Complete(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (*agenkit.Message, error) {
	// Build options
	options := BuildCallOptions(opts...)

	// Convert messages to OpenAI format
	litellmMessages := l.convertMessages(messages)

	// Build request
	req := litellmRequest{
		Model:    l.model,
		Messages: litellmMessages,
	}

	// Apply options
	if options.Temperature != nil {
		req.Temperature = options.Temperature
	}
	if options.MaxTokens != nil {
		req.MaxTokens = options.MaxTokens
	}
	if options.TopP != nil {
		req.TopP = options.TopP
	}

	// Make HTTP request
	resp, err := l.makeRequest(ctx, req)
	if err != nil {
		return nil, err
	}
	defer func() { _ = resp.Body.Close() }()

	// Parse response
	var litellmResp litellmResponse
	if err := json.NewDecoder(resp.Body).Decode(&litellmResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	// Check for valid response
	if len(litellmResp.Choices) == 0 {
		return nil, fmt.Errorf("litellm returned no choices")
	}

	// Convert to Agenkit Message
	response := agenkit.NewMessage("agent", litellmResp.Choices[0].Message.Content)
	response.Metadata["model"] = litellmResp.Model
	response.Metadata["usage"] = map[string]interface{}{
		"prompt_tokens":     litellmResp.Usage.PromptTokens,
		"completion_tokens": litellmResp.Usage.CompletionTokens,
		"total_tokens":      litellmResp.Usage.TotalTokens,
	}
	response.Metadata["finish_reason"] = litellmResp.Choices[0].FinishReason
	response.Metadata["id"] = litellmResp.ID

	return response, nil
}

// Stream generates completion chunks via LiteLLM proxy.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Channel of Message chunks as they arrive
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
//	    fmt.Print(chunk.Content)
//	}
func (l *LiteLLMLLM) Stream(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (<-chan *agenkit.Message, error) {
	// Build options
	options := BuildCallOptions(opts...)

	// Convert messages
	litellmMessages := l.convertMessages(messages)

	// Build request
	req := litellmRequest{
		Model:    l.model,
		Messages: litellmMessages,
		Stream:   true,
	}

	// Apply options
	if options.Temperature != nil {
		req.Temperature = options.Temperature
	}
	if options.MaxTokens != nil {
		req.MaxTokens = options.MaxTokens
	}
	if options.TopP != nil {
		req.TopP = options.TopP
	}

	// Make HTTP request
	resp, err := l.makeRequest(ctx, req)
	if err != nil {
		return nil, err
	}

	// Create channel for messages
	messageChan := make(chan *agenkit.Message)

	// Start goroutine to read stream
	go func() {
		defer close(messageChan)
		defer func() { _ = resp.Body.Close() }()

		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			line := scanner.Text()

			// SSE format: "data: {...}"
			if !strings.HasPrefix(line, "data: ") {
				continue
			}

			// Remove "data: " prefix
			data := strings.TrimPrefix(line, "data: ")

			// Check for [DONE] marker
			if strings.TrimSpace(data) == "[DONE]" {
				return
			}

			// Parse chunk
			var chunk litellmStreamChunk
			if err := json.Unmarshal([]byte(data), &chunk); err != nil {
				continue
			}

			// Extract content from delta
			if len(chunk.Choices) > 0 && chunk.Choices[0].Delta.Content != "" {
				msg := agenkit.NewMessage("agent", chunk.Choices[0].Delta.Content)
				msg.Metadata["streaming"] = true
				msg.Metadata["model"] = l.model
				messageChan <- msg
			}
		}

		if err := scanner.Err(); err != nil {
			// Send error message
			errorMsg := agenkit.NewMessage("agent", "")
			errorMsg.Metadata["error"] = err.Error()
			errorMsg.Metadata["streaming"] = true
			messageChan <- errorMsg
		}
	}()

	return messageChan, nil
}

// convertMessages converts Agenkit Messages to OpenAI/LiteLLM format.
//
// LiteLLM uses OpenAI-style message format:
//   - role: "system", "user", "assistant"
//   - content: string
func (l *LiteLLMLLM) convertMessages(messages []*agenkit.Message) []litellmMessage {
	litellmMessages := make([]litellmMessage, 0, len(messages))

	for _, msg := range messages {
		// Map roles to OpenAI-style
		var role string
		switch msg.Role {
		case "system", "user":
			role = msg.Role
		default:
			// Map "agent" and others to "assistant"
			role = "assistant"
		}

		litellmMessages = append(litellmMessages, litellmMessage{
			Role:    role,
			Content: msg.Content,
		})
	}

	return litellmMessages
}

// makeRequest makes an HTTP request to the LiteLLM proxy.
func (l *LiteLLMLLM) makeRequest(ctx context.Context, req litellmRequest) (*http.Response, error) {
	// Marshal request body
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Create HTTP request
	httpReq, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		fmt.Sprintf("%s/chat/completions", l.baseURL),
		bytes.NewReader(body),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	httpReq.Header.Set("Content-Type", "application/json")
	if l.apiKey != "" {
		httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", l.apiKey))
	}

	// Make request
	resp, err := l.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("litellm api error: %w", err)
	}

	// Check status code
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		return nil, fmt.Errorf("litellm api error (status %d): %s", resp.StatusCode, string(body))
	}

	return resp, nil
}

// Unwrap returns the underlying HTTP client.
//
// Returns:
//
//	The *http.Client for direct API access
//
// Example:
//
//	llm := NewLiteLLMLLM("http://localhost:4000", "gpt-4")
//	client := llm.Unwrap().(*http.Client)
//	// Use for custom requests
func (l *LiteLLMLLM) Unwrap() interface{} {
	return l.httpClient
}
