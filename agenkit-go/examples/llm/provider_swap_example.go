package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// This example demonstrates how easy it is to swap between LLM providers
// thanks to Agenkit's minimal LLM interface. The same code works with
// any provider - just change the initialization!

func main() {
	// Choose provider based on environment variable
	provider := os.Getenv("LLM_PROVIDER")
	if provider == "" {
		provider = "openai" // default
	}

	fmt.Printf("Using provider: %s\n\n", provider)

	// Create LLM adapter based on provider
	var llmAdapter llm.LLM
	switch provider {
	case "openai":
		apiKey := os.Getenv("OPENAI_API_KEY")
		if apiKey == "" {
			log.Fatal("OPENAI_API_KEY environment variable not set")
		}
		llmAdapter = llm.NewOpenAILLM(apiKey, "gpt-4o-mini")

	case "anthropic":
		apiKey := os.Getenv("ANTHROPIC_API_KEY")
		if apiKey == "" {
			log.Fatal("ANTHROPIC_API_KEY environment variable not set")
		}
		llmAdapter = llm.NewAnthropicLLM(apiKey, "claude-3-5-sonnet-20241022")

	default:
		log.Fatalf("Unknown provider: %s", provider)
	}

	fmt.Printf("Model: %s\n\n", llmAdapter.Model())

	// The rest of the code is IDENTICAL regardless of provider!
	// This is the power of Agenkit's minimal interface.

	runExamples(llmAdapter)
}

// runExamples demonstrates various LLM operations.
// This function is completely provider-agnostic!
func runExamples(llmAdapter llm.LLM) {
	ctx := context.Background()

	// Example 1: Simple question
	fmt.Println("=== Example 1: Simple Question ===")
	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "What is the meaning of life?"),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("User: What is the meaning of life?\n")
	fmt.Printf("Assistant: %s\n", response.Content)

	// Example 2: Streaming
	fmt.Println("\n=== Example 2: Streaming Response ===")
	messages = []*agenkit.Message{
		agenkit.NewMessage("user", "Count from 1 to 3."),
	}

	stream, err := llmAdapter.Stream(ctx, messages)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("User: Count from 1 to 3.\n")
	fmt.Printf("Assistant: ")

	for chunk := range stream {
		if errMsg, ok := chunk.Metadata["error"].(string); ok {
			log.Fatalf("Stream error: %s", errMsg)
		}
		fmt.Print(chunk.Content)
	}
	fmt.Println()

	// Example 3: With options
	fmt.Println("\n=== Example 3: With Custom Options ===")
	messages = []*agenkit.Message{
		agenkit.NewMessage("system", "You are a helpful assistant."),
		agenkit.NewMessage("user", "Explain quantum computing in one sentence."),
	}

	response, err = llmAdapter.Complete(
		ctx,
		messages,
		llm.WithTemperature(0.5),
		llm.WithMaxTokens(100),
	)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("User: Explain quantum computing in one sentence.\n")
	fmt.Printf("Assistant: %s\n", response.Content)

	// Example 4: Accessing provider-specific features via Unwrap()
	fmt.Println("\n=== Example 4: Provider-Specific Features ===")
	fmt.Printf("Provider type: %T\n", llmAdapter)

	// You can use Unwrap() to access provider-specific features
	// This breaks portability, but sometimes you need it!
	switch adapter := llmAdapter.(type) {
	case *llm.OpenAILLM:
		fmt.Println("OpenAI-specific features available via Unwrap()")
		// client := adapter.Unwrap().(*openai.Client)
		// Use OpenAI-specific features...

	case *llm.AnthropicLLM:
		fmt.Println("Anthropic-specific features available via Unwrap()")
		// httpClient := adapter.Unwrap().(*http.Client)
		// Use for custom Anthropic API calls...

	default:
		fmt.Printf("Unknown adapter type: %T\n", adapter)
	}
}

// Best practices for provider-agnostic code:
//
// 1. Always code against the llm.LLM interface, not concrete types
// 2. Use CallOptions (WithTemperature, etc.) for common parameters
// 3. Only use Unwrap() when absolutely necessary for provider-specific features
// 4. Test your code with multiple providers to ensure portability
// 5. Handle errors consistently across providers
//
// Provider differences to be aware of:
//
// - OpenAI uses "assistant" role, Anthropic uses "assistant" but handles "system" specially
// - Token limits vary by model
// - Streaming behavior may differ slightly
// - Error messages and status codes differ between providers
// - Rate limits and pricing vary
//
// But with Agenkit's interface, these differences are abstracted away!
