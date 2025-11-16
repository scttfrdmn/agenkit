package llm

import (
	"context"
	"errors"
	"fmt"
	"io"

	"github.com/sashabaranov/go-openai"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// OpenAILLM is an adapter for OpenAI's GPT models.
//
// Wraps the go-openai SDK to provide a consistent Agenkit interface
// for GPT models. Supports both completion and streaming.
//
// Example:
//
//	llm := NewOpenAILLM("sk-...", "gpt-4-turbo")
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
//	    WithExtra("frequency_penalty", 0.5),
//	    WithExtra("presence_penalty", 0.5),
//	)
type OpenAILLM struct {
	client *openai.Client
	model  string
}

// NewOpenAILLM creates a new OpenAI LLM adapter.
//
// Parameters:
//   - apiKey: OpenAI API key. If empty, will use OPENAI_API_KEY env var
//   - model: Model identifier (e.g., "gpt-4-turbo", "gpt-4o")
//
// Example:
//
//	llm := NewOpenAILLM("sk-...", "gpt-4-turbo")
func NewOpenAILLM(apiKey, model string) *OpenAILLM {
	client := openai.NewClient(apiKey)
	if model == "" {
		model = "gpt-4-turbo"
	}
	return &OpenAILLM{
		client: client,
		model:  model,
	}
}

// Model returns the model identifier.
func (o *OpenAILLM) Model() string {
	return o.model
}

// Complete generates a completion from GPT.
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
//   - finish_reason: Why generation stopped
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
func (o *OpenAILLM) Complete(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (*agenkit.Message, error) {
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

	// Call OpenAI API
	resp, err := o.client.CreateChatCompletion(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("openai api error: %w", err)
	}

	// Check for valid response
	if len(resp.Choices) == 0 {
		return nil, errors.New("openai returned no choices")
	}

	// Convert response to Agenkit Message
	response := agenkit.NewMessage("agent", resp.Choices[0].Message.Content)
	response.Metadata["model"] = resp.Model
	response.Metadata["usage"] = map[string]interface{}{
		"prompt_tokens":     resp.Usage.PromptTokens,
		"completion_tokens": resp.Usage.CompletionTokens,
		"total_tokens":      resp.Usage.TotalTokens,
	}
	response.Metadata["finish_reason"] = resp.Choices[0].FinishReason
	response.Metadata["id"] = resp.ID

	return response, nil
}

// Stream generates completion chunks from GPT.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Channel of Message chunks as they arrive from GPT
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
func (o *OpenAILLM) Stream(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (<-chan *agenkit.Message, error) {
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
		return nil, fmt.Errorf("openai stream error: %w", err)
	}

	// Create channel for messages
	messageChan := make(chan *agenkit.Message)

	// Start goroutine to read stream
	go func() {
		defer close(messageChan)
		defer stream.Close()

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
					messageChan <- chunk
				}
			}
		}
	}()

	return messageChan, nil
}

// convertMessages converts Agenkit Messages to OpenAI format.
//
// OpenAI expects:
//   - role: "system", "user", "assistant", or "tool"
//   - content: string
func (o *OpenAILLM) convertMessages(messages []*agenkit.Message) []openai.ChatCompletionMessage {
	openaiMessages := make([]openai.ChatCompletionMessage, 0, len(messages))

	for _, msg := range messages {
		// Map roles
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
			Content: msg.Content,
		})
	}

	return openaiMessages
}

// Unwrap returns the underlying OpenAI client.
//
// Returns:
//   The *openai.Client for direct API access
//
// Example:
//
//	llm := NewOpenAILLM("sk-...", "gpt-4-turbo")
//	client := llm.Unwrap().(*openai.Client)
//	// Use OpenAI-specific features
//	resp, err := client.CreateChatCompletion(...)
func (o *OpenAILLM) Unwrap() interface{} {
	return o.client
}
