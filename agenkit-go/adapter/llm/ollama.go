package llm

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// OllamaLLM is an adapter for Ollama's local LLM API.
//
// Wraps the Ollama API to provide a consistent Agenkit interface
// for local models like Llama, Mistral, CodeLlama, etc.
// Supports both completion and streaming.
//
// Example:
//
//	llm := NewOllamaLLM("llama2", "http://localhost:11434")
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
//	)
type OllamaLLM struct {
	model   string
	baseURL string
	client  *http.Client
}

// ollamaMessage represents a message in Ollama format
type ollamaMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ollamaChatRequest represents the Ollama chat API request
type ollamaChatRequest struct {
	Model    string          `json:"model"`
	Messages []ollamaMessage `json:"messages"`
	Stream   bool            `json:"stream"`
	Options  *ollamaOptions  `json:"options,omitempty"`
}

// ollamaOptions represents Ollama-specific options
type ollamaOptions struct {
	Temperature float64 `json:"temperature,omitempty"`
	NumPredict  int     `json:"num_predict,omitempty"` // max tokens
}

// ollamaChatResponse represents the Ollama chat API response
type ollamaChatResponse struct {
	Model     string        `json:"model"`
	CreatedAt string        `json:"created_at"`
	Message   ollamaMessage `json:"message"`
	Done      bool          `json:"done"`
	// Metrics
	TotalDuration      int64 `json:"total_duration,omitempty"`
	LoadDuration       int64 `json:"load_duration,omitempty"`
	PromptEvalCount    int   `json:"prompt_eval_count,omitempty"`
	PromptEvalDuration int64 `json:"prompt_eval_duration,omitempty"`
	EvalCount          int   `json:"eval_count,omitempty"`
	EvalDuration       int64 `json:"eval_duration,omitempty"`
}

// NewOllamaLLM creates a new Ollama LLM adapter.
//
// Parameters:
//   - model: Model identifier (e.g., "llama2", "mistral", "codellama")
//   - baseURL: Ollama API base URL (e.g., "http://localhost:11434")
//
// Example:
//
//	llm := NewOllamaLLM("llama2", "http://localhost:11434")
func NewOllamaLLM(model, baseURL string) *OllamaLLM {
	if model == "" {
		model = "llama2"
	}
	if baseURL == "" {
		baseURL = "http://localhost:11434"
	}
	return &OllamaLLM{
		model:   model,
		baseURL: baseURL,
		client: &http.Client{
			Timeout: 120 * time.Second,
		},
	}
}

// Model returns the model identifier.
func (o *OllamaLLM) Model() string {
	return o.model
}

// Complete generates a completion from Ollama.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Response as Agenkit Message with metadata including:
//   - model: Model used
//   - usage: Token counts (prompt, completion, total)
//   - total_duration_ns: Total duration in nanoseconds
//
// Example:
//
//	messages := []*agenkit.Message{
//	    agenkit.NewMessage("user", "What is 2+2?"),
//	}
//	response, err := llm.Complete(ctx, messages, WithTemperature(0.7))
func (o *OllamaLLM) Complete(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (*agenkit.Message, error) {
	options := &CallOptions{}
	for _, opt := range opts {
		opt(options)
	}

	// Convert messages to Ollama format
	ollamaMessages := make([]ollamaMessage, len(messages))
	for i, msg := range messages {
		ollamaMessages[i] = ollamaMessage{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}

	// Build request
	reqBody := ollamaChatRequest{
		Model:    o.model,
		Messages: ollamaMessages,
		Stream:   false,
	}

	// Add options if specified
	if options.Temperature != nil || options.MaxTokens != nil {
		reqBody.Options = &ollamaOptions{}
		if options.Temperature != nil {
			reqBody.Options.Temperature = *options.Temperature
		}
		if options.MaxTokens != nil {
			reqBody.Options.NumPredict = *options.MaxTokens
		}
	}

	reqJSON, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Make request
	req, err := http.NewRequestWithContext(ctx, "POST", o.baseURL+"/api/chat", bytes.NewBuffer(reqJSON))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := o.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to make request: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("ollama API error (%d): %s", resp.StatusCode, string(body))
	}

	// Parse response
	var ollamaResp ollamaChatResponse
	if err := json.NewDecoder(resp.Body).Decode(&ollamaResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	// Convert to Agenkit message
	response := agenkit.NewMessage(ollamaResp.Message.Role, ollamaResp.Message.Content)

	// Add metadata
	response.Metadata["model"] = ollamaResp.Model
	if ollamaResp.TotalDuration > 0 {
		response.Metadata["total_duration_ns"] = ollamaResp.TotalDuration
	}

	// Add usage information
	if ollamaResp.PromptEvalCount > 0 || ollamaResp.EvalCount > 0 {
		response.Metadata["usage"] = map[string]interface{}{
			"prompt_tokens":     ollamaResp.PromptEvalCount,
			"completion_tokens": ollamaResp.EvalCount,
			"total_tokens":      ollamaResp.PromptEvalCount + ollamaResp.EvalCount,
		}
	}

	return response, nil
}

// Stream generates a streaming completion from Ollama.
//
// Parameters:
//   - ctx: Context for cancellation
//   - messages: Conversation history
//   - opts: Options like temperature
//
// Returns:
//   - Channel of Message chunks
//   - Error channel for async errors
//
// Example:
//
//	stream, errChan := llm.Stream(ctx, messages)
//	for chunk := range stream {
//	    fmt.Print(chunk.Content)
//	}
//	if err := <-errChan; err != nil {
//	    log.Fatal(err)
//	}
func (o *OllamaLLM) Stream(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (<-chan *agenkit.Message, <-chan error) {
	msgChan := make(chan *agenkit.Message)
	errChan := make(chan error, 1)

	go func() {
		defer close(msgChan)
		defer close(errChan)

		options := &CallOptions{}
		for _, opt := range opts {
			opt(options)
		}

		// Convert messages to Ollama format
		ollamaMessages := make([]ollamaMessage, len(messages))
		for i, msg := range messages {
			ollamaMessages[i] = ollamaMessage{
				Role:    msg.Role,
				Content: msg.Content,
			}
		}

		// Build request
		reqBody := ollamaChatRequest{
			Model:    o.model,
			Messages: ollamaMessages,
			Stream:   true,
		}

		// Add options if specified
		if options.Temperature != nil || options.MaxTokens != nil {
			reqBody.Options = &ollamaOptions{}
			if options.Temperature != nil {
				reqBody.Options.Temperature = *options.Temperature
			}
			if options.MaxTokens != nil {
				reqBody.Options.NumPredict = *options.MaxTokens
			}
		}

		reqJSON, err := json.Marshal(reqBody)
		if err != nil {
			errChan <- fmt.Errorf("failed to marshal request: %w", err)
			return
		}

		// Make request
		req, err := http.NewRequestWithContext(ctx, "POST", o.baseURL+"/api/chat", bytes.NewBuffer(reqJSON))
		if err != nil {
			errChan <- fmt.Errorf("failed to create request: %w", err)
			return
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := o.client.Do(req)
		if err != nil {
			errChan <- fmt.Errorf("failed to make request: %w", err)
			return
		}
		defer func() { _ = resp.Body.Close() }()

		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			errChan <- fmt.Errorf("ollama API error (%d): %s", resp.StatusCode, string(body))
			return
		}

		// Parse streaming response
		decoder := json.NewDecoder(resp.Body)
		for {
			var chunk ollamaChatResponse
			if err := decoder.Decode(&chunk); err != nil {
				if errors.Is(err, io.EOF) {
					break
				}
				errChan <- fmt.Errorf("failed to decode chunk: %w", err)
				return
			}

			// Send chunk
			msg := agenkit.NewMessage(chunk.Message.Role, chunk.Message.Content)
			msg.Metadata["model"] = chunk.Model
			if chunk.Done {
				msg.Metadata["done"] = true
			}

			select {
			case msgChan <- msg:
			case <-ctx.Done():
				errChan <- ctx.Err()
				return
			}

			if chunk.Done {
				break
			}
		}

		errChan <- nil
	}()

	return msgChan, errChan
}
