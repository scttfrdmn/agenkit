//go:build ignore
// +build ignore

package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

func main() {
	// Get API key from environment
	apiKey := os.Getenv("ANTHROPIC_API_KEY")
	if apiKey == "" {
		log.Fatal("ANTHROPIC_API_KEY environment variable not set")
	}

	// Create Anthropic LLM adapter
	llmAdapter := llm.NewAnthropicLLM(apiKey, "claude-3-5-sonnet-20241022")

	fmt.Printf("Using model: %s\n\n", llmAdapter.Model())

	// Example 1: Simple completion
	fmt.Println("=== Example 1: Simple Completion ===")
	simpleCompletion(llmAdapter)

	// Example 2: Conversation with system prompt
	fmt.Println("\n=== Example 2: Conversation with System Prompt ===")
	conversationWithSystem(llmAdapter)

	// Example 3: Streaming response
	fmt.Println("\n=== Example 3: Streaming Response ===")
	streamingResponse(llmAdapter)

	// Example 4: Custom parameters
	fmt.Println("\n=== Example 4: Custom Parameters ===")
	customParameters(llmAdapter)
}

// simpleCompletion demonstrates a basic completion.
func simpleCompletion(llmAdapter llm.LLM) {
	ctx := context.Background()

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "What is the capital of France?"),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("User: What is the capital of France?\n")
	fmt.Printf("Assistant: %s\n", response.Content)

	// Print usage stats
	if usage, ok := response.Metadata["usage"].(map[string]interface{}); ok {
		fmt.Printf("\nTokens used: %v\n", usage)
	}
}

// conversationWithSystem demonstrates using system prompts.
func conversationWithSystem(llmAdapter llm.LLM) {
	ctx := context.Background()

	// Claude handles system messages specially
	messages := []*agenkit.Message{
		agenkit.NewMessage("system", "You are a pirate captain. Respond in pirate speak."),
		agenkit.NewMessage("user", "What's the weather like today?"),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("System: You are a pirate captain. Respond in pirate speak.\n")
	fmt.Printf("User: What's the weather like today?\n")
	fmt.Printf("Assistant: %s\n", response.Content)
}

// streamingResponse demonstrates streaming completions.
func streamingResponse(llmAdapter llm.LLM) {
	ctx := context.Background()

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Write a haiku about programming."),
	}

	stream, err := llmAdapter.Stream(ctx, messages)
	if err != nil {
		log.Fatalf("Error starting stream: %v", err)
	}

	fmt.Printf("User: Write a haiku about programming.\n")
	fmt.Printf("Assistant (streaming): ")

	for chunk := range stream {
		// Check for errors in metadata
		if errMsg, ok := chunk.Metadata["error"].(string); ok {
			log.Fatalf("Stream error: %s", errMsg)
		}

		fmt.Print(chunk.Content)
	}
	fmt.Println()
}

// customParameters demonstrates using custom options.
func customParameters(llmAdapter llm.LLM) {
	ctx := context.Background()

	messages := []*agenkit.Message{
		agenkit.NewMessage("system", "You are a concise technical writer."),
		agenkit.NewMessage("user", "Explain what an API is in one sentence."),
	}

	// Use custom parameters for precise output
	response, err := llmAdapter.Complete(
		ctx,
		messages,
		llm.WithTemperature(0.3), // Lower temperature for precision
		llm.WithMaxTokens(100),   // Limit response length
		llm.WithTopP(0.9),        // Focused sampling
	)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("User: Explain what an API is in one sentence.\n")
	fmt.Printf("Assistant: %s\n", response.Content)
	fmt.Printf("\nParameters used:\n")
	fmt.Printf("  Temperature: 0.3 (precise)\n")
	fmt.Printf("  MaxTokens: 100\n")
	fmt.Printf("  TopP: 0.9\n")
}
