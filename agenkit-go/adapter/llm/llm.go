// Package llm provides minimal LLM interfaces for Agenkit.
//
// This package defines the minimal contract that all LLM adapters must implement.
// The interface is intentionally small to maximize flexibility while ensuring
// consistency across providers.
package llm

import (
	"context"
	"fmt"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// LLM is the minimal interface for agent-LLM interaction.
//
// This interface provides a consistent way to interact with any LLM provider,
// whether commercial (Anthropic, OpenAI, etc.) or local (Ollama, llama.cpp).
//
// Design principles:
//   - Minimal: Only 2 required methods (Complete, Stream)
//   - Flexible: Accepts CallOptions for provider-specific options
//   - Consistent: Works with Agenkit Message interface
//   - Swappable: Change providers without changing agent code
//   - Escape hatch: Unwrap() for advanced provider features
//
// The interface is intentionally NOT a full-featured LLM client. It focuses
// on the minimal contract needed for agent-LLM interaction, leaving advanced
// features to provider-specific implementations accessible via Unwrap().
//
// Example:
//
//	llm := NewOpenAILLM("sk-...")
//	messages := []*agenkit.Message{
//	    agenkit.NewMessage("system", "You are helpful."),
//	    agenkit.NewMessage("user", "Hello!"),
//	}
//	response, err := llm.Complete(ctx, messages, WithTemperature(0.7))
//	if err != nil {
//	    log.Fatal(err)
//	}
//	fmt.Println(response.ContentString())
//
// Swapping providers:
//
//	// Same code, different provider
//	llm := NewAnthropicLLM("sk-ant-...")
//	response, err := llm.Complete(ctx, messages, WithTemperature(0.7))
//
// Streaming:
//
//	stream, err := llm.Stream(ctx, messages)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	for chunk := range stream {
//	    fmt.Print(chunk.ContentString())
//	}
type LLM interface {
	// Complete generates a single completion from the LLM.
	//
	// This method sends a list of messages to the LLM and returns a single
	// response message. The conversation history is passed as a list of
	// Agenkit Messages, which the adapter converts to the provider's format.
	//
	// Parameters:
	//   - ctx: Context for cancellation and deadlines
	//   - messages: Conversation history as Agenkit Messages
	//   - opts: Provider-specific options (temperature, max_tokens, etc.)
	//
	// Returns:
	//   - Response from the LLM as an Agenkit Message with:
	//     * Role: "agent"
	//     * Content: The generated text
	//     * Metadata: Provider-specific data (usage stats, model name, etc.)
	//
	// Errors:
	//   - Provider-specific errors for API failures (auth, rate limits, etc.)
	//
	// Example:
	//
	//	messages := []*agenkit.Message{
	//	    agenkit.NewMessage("system", "You are a coding assistant."),
	//	    agenkit.NewMessage("user", "Write a Go hello world."),
	//	}
	//	response, err := llm.Complete(
	//	    ctx,
	//	    messages,
	//	    WithTemperature(0.2), // Lower temp for code
	//	    WithMaxTokens(1024),
	//	)
	Complete(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (*agenkit.Message, error)

	// Stream generates completion chunks from the LLM.
	//
	// This method sends messages to the LLM and streams back response chunks
	// as they're generated. Each chunk is sent through the returned channel.
	//
	// Parameters:
	//   - ctx: Context for cancellation and deadlines
	//   - messages: Conversation history as Agenkit Messages
	//   - opts: Provider-specific options
	//
	// Returns:
	//   - Channel of Message chunks as they arrive from the LLM. Each chunk contains:
	//     * Role: "agent"
	//     * Content: Partial text (may be a single token or character)
	//     * Metadata: {"streaming": true, ...}
	//   - The channel will be closed when streaming completes or on error
	//
	// Errors:
	//   - Provider-specific errors for API failures
	//   - Error causes channel to close; check for error after channel closes
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
	// Note:
	//   If streaming is not supported, return error immediately.
	Stream(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (<-chan *agenkit.Message, error)

	// Model returns the model identifier for this LLM instance.
	//
	// Returns:
	//   Model name/identifier (e.g., "claude-3-5-sonnet-20241022", "gpt-4-turbo")
	//
	// Example:
	//
	//	llm := NewAnthropicLLM("sk-ant-...", "claude-3-5-sonnet-20241022")
	//	fmt.Println(llm.Model()) // "claude-3-5-sonnet-20241022"
	Model() string

	// Unwrap returns the underlying provider client for advanced features.
	//
	// This is an escape hatch that allows access to provider-specific features
	// not exposed by the minimal LLM interface. Use this when you need
	// capabilities beyond Complete() and Stream().
	//
	// Returns:
	//   The native provider client (interface{} that must be type-asserted)
	//
	// Example:
	//
	//	llm := NewAnthropicLLM(...)
	//	client := llm.Unwrap().(*anthropic.Client)
	//	// Now use Anthropic-specific features
	//	response, err := client.Messages.Create(...)
	//
	// Warning:
	//   Using Unwrap() breaks provider portability. Code that uses Unwrap()
	//   will need changes when switching providers.
	Unwrap() interface{}
}

// CallOptions holds provider-specific options for LLM calls.
type CallOptions struct {
	// Common options
	Temperature *float64
	MaxTokens   *int
	TopP        *float64

	// Provider-specific options
	Extra map[string]interface{}
}

// CallOption is a functional option for configuring LLM calls.
type CallOption func(*CallOptions)

// WithTemperature sets the sampling temperature (0.0-2.0).
// Panics if temperature is outside the valid range.
func WithTemperature(temperature float64) CallOption {
	if temperature < 0.0 || temperature > 2.0 {
		panic(fmt.Sprintf("temperature must be between 0 and 2, got %v", temperature))
	}
	return func(opts *CallOptions) {
		opts.Temperature = &temperature
	}
}

// WithMaxTokens sets the maximum number of tokens to generate.
// Panics if maxTokens is not positive.
func WithMaxTokens(maxTokens int) CallOption {
	if maxTokens <= 0 {
		panic(fmt.Sprintf("max_tokens must be positive, got %d", maxTokens))
	}
	return func(opts *CallOptions) {
		opts.MaxTokens = &maxTokens
	}
}

// WithTopP sets the nucleus sampling parameter (0.0-1.0).
// Panics if topP is outside the valid range.
func WithTopP(topP float64) CallOption {
	if topP < 0.0 || topP > 1.0 {
		panic(fmt.Sprintf("top_p must be between 0 and 1, got %v", topP))
	}
	return func(opts *CallOptions) {
		opts.TopP = &topP
	}
}

// WithFrequencyPenalty sets the frequency penalty (-2.0 to 2.0).
// Panics if frequencyPenalty is outside the valid range.
func WithFrequencyPenalty(frequencyPenalty float64) CallOption {
	if frequencyPenalty < -2.0 || frequencyPenalty > 2.0 {
		panic(fmt.Sprintf("frequency_penalty must be between -2 and 2, got %v", frequencyPenalty))
	}
	return func(opts *CallOptions) {
		if opts.Extra == nil {
			opts.Extra = make(map[string]interface{})
		}
		opts.Extra["frequency_penalty"] = frequencyPenalty
	}
}

// WithPresencePenalty sets the presence penalty (-2.0 to 2.0).
// Panics if presencePenalty is outside the valid range.
func WithPresencePenalty(presencePenalty float64) CallOption {
	if presencePenalty < -2.0 || presencePenalty > 2.0 {
		panic(fmt.Sprintf("presence_penalty must be between -2 and 2, got %v", presencePenalty))
	}
	return func(opts *CallOptions) {
		if opts.Extra == nil {
			opts.Extra = make(map[string]interface{})
		}
		opts.Extra["presence_penalty"] = presencePenalty
	}
}

// WithExtra adds a provider-specific option.
func WithExtra(key string, value interface{}) CallOption {
	return func(opts *CallOptions) {
		if opts.Extra == nil {
			opts.Extra = make(map[string]interface{})
		}
		opts.Extra[key] = value
	}
}

// BuildCallOptions creates CallOptions from functional options.
func BuildCallOptions(opts ...CallOption) *CallOptions {
	options := &CallOptions{
		Extra: make(map[string]interface{}),
	}
	for _, opt := range opts {
		opt(options)
	}
	return options
}
