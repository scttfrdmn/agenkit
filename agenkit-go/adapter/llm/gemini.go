package llm

import (
	"context"
	"errors"
	"fmt"
	"os"

	"github.com/google/generative-ai-go/genai"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"google.golang.org/api/iterator"
	"google.golang.org/api/option"
)

// GeminiLLM is an adapter for Google's Gemini models.
//
// Wraps the Google GenAI SDK to provide a consistent Agenkit interface
// for Gemini models. Supports both completion and streaming.
//
// Example:
//
//	llm := NewGeminiLLM("your-api-key", "gemini-2.0-flash-exp")
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
//	    WithExtra("top_k", 40),
//	)
type GeminiLLM struct {
	client *genai.Client
	model  string
}

// NewGeminiLLM creates a new Gemini LLM adapter.
//
// Parameters:
//   - apiKey: Google API key. If empty, will use GEMINI_API_KEY or GOOGLE_API_KEY env var
//   - model: Model identifier (e.g., "gemini-2.0-flash-exp", "gemini-1.5-pro")
//
// Example:
//
//	llm := NewGeminiLLM("your-api-key", "gemini-2.0-flash-exp")
func NewGeminiLLM(apiKey, model string) (*GeminiLLM, error) {
	// Use environment variable if API key not provided
	if apiKey == "" {
		apiKey = os.Getenv("GEMINI_API_KEY")
		if apiKey == "" {
			apiKey = os.Getenv("GOOGLE_API_KEY")
		}
		if apiKey == "" {
			return nil, errors.New("gemini api key required: provide apiKey parameter or set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
		}
	}

	// Default model
	if model == "" {
		model = "gemini-2.0-flash-exp"
	}

	// Create client
	ctx := context.Background()
	client, err := genai.NewClient(ctx, option.WithAPIKey(apiKey))
	if err != nil {
		return nil, fmt.Errorf("failed to create gemini client: %w", err)
	}

	return &GeminiLLM{
		client: client,
		model:  model,
	}, nil
}

// Model returns the model identifier.
func (g *GeminiLLM) Model() string {
	return g.model
}

// Complete generates a completion from Gemini.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Response as Agenkit Message with metadata including:
//   - model: Model used
//   - usage: Token counts if available
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
func (g *GeminiLLM) Complete(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (*agenkit.Message, error) {
	// Build options
	options := BuildCallOptions(opts...)

	// Get model
	model := g.client.GenerativeModel(g.model)

	// Configure model
	g.configureModel(model, options)

	// Convert messages to Gemini format
	history, lastMessage := g.convertMessages(messages)

	// Start chat session
	session := model.StartChat()
	session.History = history

	// Send message
	resp, err := session.SendMessage(ctx, lastMessage...)
	if err != nil {
		return nil, fmt.Errorf("gemini api error: %w", err)
	}

	// Extract content
	content := g.extractContent(resp)

	// Build response message
	response := agenkit.NewMessage("agent", content)
	response.Metadata["model"] = g.model

	// Add usage metadata if available
	if resp.UsageMetadata != nil {
		response.Metadata["usage"] = map[string]interface{}{
			"prompt_tokens":     resp.UsageMetadata.PromptTokenCount,
			"completion_tokens": resp.UsageMetadata.CandidatesTokenCount,
			"total_tokens":      resp.UsageMetadata.TotalTokenCount,
		}
	}

	// Add finish reason if available
	if len(resp.Candidates) > 0 && resp.Candidates[0].FinishReason != 0 {
		response.Metadata["finish_reason"] = resp.Candidates[0].FinishReason.String()
	}

	return response, nil
}

// Stream generates completion chunks from Gemini.
//
// Parameters:
//   - ctx: Context for cancellation and deadlines
//   - messages: Conversation history as Agenkit Messages
//   - opts: Options like temperature, max_tokens, etc.
//
// Returns:
//   - Channel of Message chunks as they arrive from Gemini
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
func (g *GeminiLLM) Stream(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (<-chan *agenkit.Message, error) {
	// Build options
	options := BuildCallOptions(opts...)

	// Get model
	model := g.client.GenerativeModel(g.model)

	// Configure model
	g.configureModel(model, options)

	// Convert messages to Gemini format
	history, lastMessage := g.convertMessages(messages)

	// Start chat session
	session := model.StartChat()
	session.History = history

	// Start stream
	iter := session.SendMessageStream(ctx, lastMessage...)

	// Create channel for messages
	messageChan := make(chan *agenkit.Message)

	// Start goroutine to read stream
	go func() {
		defer close(messageChan)

		for {
			resp, err := iter.Next()
			if errors.Is(err, iterator.Done) {
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

			// Extract content from chunk
			content := g.extractContent(resp)
			if content != "" {
				chunk := agenkit.NewMessage("agent", content)
				chunk.Metadata["streaming"] = true
				chunk.Metadata["model"] = g.model
				messageChan <- chunk
			}
		}
	}()

	return messageChan, nil
}

// convertMessages converts Agenkit Messages to Gemini format.
//
// Gemini expects:
//   - role: "user" or "model"
//   - parts: list of content parts
//
// System messages are prepended as user messages.
// Returns the conversation history and the last message to send.
func (g *GeminiLLM) convertMessages(messages []*agenkit.Message) ([]*genai.Content, []genai.Part) {
	if len(messages) == 0 {
		return nil, nil
	}

	var history []*genai.Content

	// Process all messages except the last one
	for i := 0; i < len(messages)-1; i++ {
		msg := messages[i]

		// Map role
		role := g.mapRole(msg.Role)

		// Create content
		content := &genai.Content{
			Role: role,
			Parts: []genai.Part{
				genai.Text(msg.Content),
			},
		}

		history = append(history, content)
	}

	// The last message is what we're sending
	lastMsg := messages[len(messages)-1]
	lastParts := []genai.Part{
		genai.Text(lastMsg.Content),
	}

	return history, lastParts
}

// mapRole maps Agenkit role to Gemini role.
func (g *GeminiLLM) mapRole(role string) string {
	switch role {
	case "user", "system":
		return "user"
	default:
		// Map "agent", "assistant", and others to "model"
		return "model"
	}
}

// configureModel applies configuration options to the model.
func (g *GeminiLLM) configureModel(model *genai.GenerativeModel, options *CallOptions) {
	// Set temperature
	if options.Temperature != nil {
		temp := float32(*options.Temperature)
		model.Temperature = &temp
	}

	// Set max tokens
	if options.MaxTokens != nil {
		maxTokens := int32(*options.MaxTokens)
		model.MaxOutputTokens = &maxTokens
	}

	// Set top P
	if options.TopP != nil {
		topP := float32(*options.TopP)
		model.TopP = &topP
	}

	// Set top K from extra options
	if topK, ok := options.Extra["top_k"].(int); ok {
		topKInt := int32(topK)
		model.TopK = &topKInt
	}

	// Set candidate count from extra options
	if candidateCount, ok := options.Extra["candidate_count"].(int); ok {
		count := int32(candidateCount)
		model.CandidateCount = &count
	}

	// Set stop sequences from extra options
	if stopSequences, ok := options.Extra["stop_sequences"].([]string); ok {
		model.StopSequences = stopSequences
	}
}

// extractContent extracts text content from a Gemini response.
func (g *GeminiLLM) extractContent(resp *genai.GenerateContentResponse) string {
	if resp == nil || len(resp.Candidates) == 0 {
		return ""
	}

	candidate := resp.Candidates[0]
	if candidate.Content == nil || len(candidate.Content.Parts) == 0 {
		return ""
	}

	// Concatenate all text parts
	var content string
	for _, part := range candidate.Content.Parts {
		if txt, ok := part.(genai.Text); ok {
			content += string(txt)
		}
	}

	return content
}

// Close closes the Gemini client.
func (g *GeminiLLM) Close() error {
	if g.client != nil {
		return g.client.Close()
	}
	return nil
}

// Unwrap returns the underlying Gemini client.
//
// Returns:
//
//	The *genai.Client for direct API access
//
// Example:
//
//	llm, err := NewGeminiLLM("your-api-key", "gemini-2.0-flash-exp")
//	if err != nil {
//	    log.Fatal(err)
//	}
//	client := llm.Unwrap().(*genai.Client)
//	// Use Gemini-specific features
//	model := client.GenerativeModel("gemini-1.5-pro")
//	resp, err := model.GenerateContent(...)
func (g *GeminiLLM) Unwrap() interface{} {
	return g.client
}
