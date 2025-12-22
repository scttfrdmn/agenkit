//go:build ignore

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
	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		apiKey = os.Getenv("GOOGLE_API_KEY")
	}
	if apiKey == "" {
		log.Fatal("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set")
	}

	// Create Gemini LLM adapter
	llmAdapter, err := llm.NewGeminiLLM(apiKey, "gemini-2.0-flash-exp")
	if err != nil {
		log.Fatalf("Failed to create Gemini LLM: %v", err)
	}
	defer func() {
		if err := llmAdapter.Close(); err != nil {
			log.Printf("Error closing Gemini client: %v", err)
		}
	}()

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

	// Example 5: Multi-turn conversation
	fmt.Println("\n=== Example 5: Multi-turn Conversation ===")
	multiTurnConversation(llmAdapter)
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

	// Gemini converts system messages to user messages
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
		llm.WithTemperature(0.3),   // Lower temperature for precision
		llm.WithMaxTokens(100),     // Limit response length
		llm.WithTopP(0.9),          // Focused sampling
		llm.WithExtra("top_k", 40), // Gemini-specific: top-k sampling
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
	fmt.Printf("  TopK: 40\n")

	// Print usage stats
	if usage, ok := response.Metadata["usage"].(map[string]interface{}); ok {
		fmt.Printf("\nTokens used: %v\n", usage)
	}
}

// multiTurnConversation demonstrates a multi-turn conversation.
func multiTurnConversation(llmAdapter llm.LLM) {
	ctx := context.Background()

	// Build up conversation history
	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "My favorite color is blue."),
		agenkit.NewMessage("agent", "That's nice! Blue is a calming color."),
		agenkit.NewMessage("user", "What was my favorite color again?"),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("Turn 1:\n")
	fmt.Printf("User: My favorite color is blue.\n")
	fmt.Printf("Assistant: That's nice! Blue is a calming color.\n\n")
	fmt.Printf("Turn 2:\n")
	fmt.Printf("User: What was my favorite color again?\n")
	fmt.Printf("Assistant: %s\n", response.Content)
}
