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

// AnthropicLLM is an adapter for Anthropic's Claude models.
//
// Implements the Agenkit LLM interface for Claude models.
// Supports both completion and streaming.
//
// Example:
//
//	llm := NewAnthropicLLM("sk-ant-...", "claude-3-5-sonnet-20241022")
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
//	    WithExtra("stop_sequences", []string{"Human:", "Assistant:"}),
//	)
type AnthropicLLM struct {
	apiKey     string
	model      string
	baseURL    string
	httpClient *http.Client
}

// NewAnthropicLLM creates a new Anthropic LLM adapter.
//
// Parameters:
//   - apiKey: Anthropic API key
//   - model: Model identifier (e.g., "claude-3-5-sonnet-20241022")
//
// Example:
//
//	llm := NewAnthropicLLM("sk-ant-...", "claude-3-5-sonnet-20241022")
func NewAnthropicLLM(apiKey, model string) *AnthropicLLM {
	if model == "" {
		model = "claude-3-haiku-20240307"
	}
	return &AnthropicLLM{
		apiKey:     apiKey,
		model:      model,
		baseURL:    "https://api.anthropic.com/v1",
		httpClient: &http.Client{},
	}
}

// Model returns the model identifier.
func (a *AnthropicLLM) Model() string {
	return a.model
}

// anthropicRequest is the request structure for Anthropic's Messages API.
type anthropicRequest struct {
	Model       string                   `json:"model"`
	Messages    []anthropicMessage       `json:"messages"`
	MaxTokens   int                      `json:"max_tokens"`
	Temperature *float64                 `json:"temperature,omitempty"`
	TopP        *float64                 `json:"top_p,omitempty"`
	System      string                   `json:"system,omitempty"`
	Stream      bool                     `json:"stream,omitempty"`
	Extra       map[string]interface{}   `json:"-"` // Not serialized directly
}

// anthropicMessage is a message in Anthropic's format.
type anthropicMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// anthropicResponse is the response structure from Anthropic's Messages API.
type anthropicResponse struct {
	ID           string                   `json:"id"`
	Type         string                   `json:"type"`
	Role         string                   `json:"role"`
	Content      []anthropicContentBlock  `json:"content"`
	Model        string                   `json:"model"`
	StopReason   string                   `json:"stop_reason"`
	StopSequence *string                  `json:"stop_sequence,omitempty"`
	Usage        anthropicUsage           `json:"usage"`
}

// anthropicContentBlock represents a content block in the response.
type anthropicContentBlock struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

// anthropicUsage contains token usage information.
type anthropicUsage struct {
	InputTokens  int `json:"input_tokens"`
	OutputTokens int `json:"output_tokens"`
}

// anthropicStreamEvent represents a server-sent event in the stream.
type anthropicStreamEvent struct {
	Type         string                  `json:"type"`
	Message      *anthropicResponse      `json:"message,omitempty"`
	Index        int                     `json:"index,omitempty"`
	ContentBlock *anthropicContentBlock  `json:"content_block,omitempty"`
	Delta        *anthropicDelta         `json:"delta,omitempty"`
	Usage        *anthropicUsage         `json:"usage,omitempty"`
}

// anthropicDelta represents a streaming delta.
type anthropicDelta struct {
	Type       string `json:"type"`
	Text       string `json:"text,omitempty"`
	StopReason string `json:"stop_reason,omitempty"`
}

// Complete generates a completion from Claude.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Response as Agenkit Message with metadata including:
//   - model: Model used
//   - usage: Input and output token counts
//   - stop_reason: Why generation stopped
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
func (a *AnthropicLLM) Complete(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (*agenkit.Message, error) {
	// Build options
	options := BuildCallOptions(opts...)

	// Convert messages and extract system message
	anthropicMessages, systemMessage := a.convertMessages(messages)

	// Build request
	req := anthropicRequest{
		Model:     a.model,
		Messages:  anthropicMessages,
		MaxTokens: 4096, // Default
		System:    systemMessage,
	}

	// Apply options
	if options.Temperature != nil {
		req.Temperature = options.Temperature
	}
	if options.MaxTokens != nil {
		req.MaxTokens = *options.MaxTokens
	}
	if options.TopP != nil {
		req.TopP = options.TopP
	}

	// Make HTTP request
	resp, err := a.makeRequest(ctx, req)
	if err != nil {
		return nil, err
	}

	// Parse response
	var anthropicResp anthropicResponse
	if err := json.NewDecoder(resp.Body).Decode(&anthropicResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	resp.Body.Close()

	// Extract text content
	var content string
	if len(anthropicResp.Content) > 0 {
		content = anthropicResp.Content[0].Text
	}

	// Convert to Agenkit Message
	response := agenkit.NewMessage("agent", content)
	response.Metadata["model"] = a.model
	response.Metadata["usage"] = map[string]interface{}{
		"input_tokens":  anthropicResp.Usage.InputTokens,
		"output_tokens": anthropicResp.Usage.OutputTokens,
	}
	response.Metadata["stop_reason"] = anthropicResp.StopReason
	response.Metadata["id"] = anthropicResp.ID

	return response, nil
}

// Stream generates completion chunks from Claude.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Channel of Message chunks as they arrive from Claude
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
func (a *AnthropicLLM) Stream(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (<-chan *agenkit.Message, error) {
	// Build options
	options := BuildCallOptions(opts...)

	// Convert messages
	anthropicMessages, systemMessage := a.convertMessages(messages)

	// Build request
	req := anthropicRequest{
		Model:     a.model,
		Messages:  anthropicMessages,
		MaxTokens: 4096, // Default
		System:    systemMessage,
		Stream:    true,
	}

	// Apply options
	if options.Temperature != nil {
		req.Temperature = options.Temperature
	}
	if options.MaxTokens != nil {
		req.MaxTokens = *options.MaxTokens
	}
	if options.TopP != nil {
		req.TopP = options.TopP
	}

	// Make HTTP request
	resp, err := a.makeRequest(ctx, req)
	if err != nil {
		return nil, err
	}

	// Create channel for messages
	messageChan := make(chan *agenkit.Message)

	// Start goroutine to read stream
	go func() {
		defer close(messageChan)
		defer resp.Body.Close()

		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			line := scanner.Text()

			// SSE format: "data: {...}"
			if !strings.HasPrefix(line, "data: ") {
				continue
			}

			// Remove "data: " prefix
			data := strings.TrimPrefix(line, "data: ")

			// Parse event
			var event anthropicStreamEvent
			if err := json.Unmarshal([]byte(data), &event); err != nil {
				continue
			}

			// Handle content_block_delta events
			if event.Type == "content_block_delta" && event.Delta != nil && event.Delta.Text != "" {
				chunk := agenkit.NewMessage("agent", event.Delta.Text)
				chunk.Metadata["streaming"] = true
				chunk.Metadata["model"] = a.model
				messageChan <- chunk
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

// convertMessages converts Agenkit Messages to Anthropic format.
//
// Anthropic expects:
//   - role: "user" or "assistant"
//   - content: string
//
// System messages are handled separately via the system parameter.
func (a *AnthropicLLM) convertMessages(messages []*agenkit.Message) ([]anthropicMessage, string) {
	var anthropicMessages []anthropicMessage
	var systemMessage string

	for _, msg := range messages {
		// Extract system message
		if msg.Role == "system" {
			systemMessage = msg.Content
			continue
		}

		// Map roles
		var role string
		if msg.Role == "user" {
			role = "user"
		} else {
			role = "assistant"
		}

		anthropicMessages = append(anthropicMessages, anthropicMessage{
			Role:    role,
			Content: msg.Content,
		})
	}

	return anthropicMessages, systemMessage
}

// makeRequest makes an HTTP request to the Anthropic API.
func (a *AnthropicLLM) makeRequest(ctx context.Context, req anthropicRequest) (*http.Response, error) {
	// Marshal request body
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Create HTTP request
	httpReq, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		fmt.Sprintf("%s/messages", a.baseURL),
		bytes.NewReader(body),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("x-api-key", a.apiKey)
	httpReq.Header.Set("anthropic-version", "2023-06-01")

	// Make request
	resp, err := a.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("anthropic api error: %w", err)
	}

	// Check status code
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, fmt.Errorf("anthropic api error (status %d): %s", resp.StatusCode, string(body))
	}

	return resp, nil
}

// Unwrap returns the underlying HTTP client.
//
// Returns:
//   The *http.Client for direct API access
//
// Example:
//
//	llm := NewAnthropicLLM("sk-ant-...", "claude-3-5-sonnet-20241022")
//	client := llm.Unwrap().(*http.Client)
//	// Use for custom requests
func (a *AnthropicLLM) Unwrap() interface{} {
	return a.httpClient
}
