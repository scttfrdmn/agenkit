package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/agenkit/agenkit-go/adapter/llm"
	"github.com/agenkit/agenkit-go/agenkit"
)

func main() {
	// Get API key from environment
	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		log.Fatal("OPENAI_API_KEY environment variable not set")
	}

	// Create OpenAI LLM adapter
	llmAdapter := llm.NewOpenAILLM(apiKey, "gpt-4o-mini")

	fmt.Printf("Using model: %s\n\n", llmAdapter.Model())

	// Example 1: Simple completion
	fmt.Println("=== Example 1: Simple Completion ===")
	simpleCompletion(llmAdapter)

	// Example 2: Conversation with history
	fmt.Println("\n=== Example 2: Conversation with History ===")
	conversationWithHistory(llmAdapter)

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
		agenkit.NewMessage("system", "You are a helpful assistant."),
		agenkit.NewMessage("user", "What is 2+2?"),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("User: What is 2+2?\n")
	fmt.Printf("Assistant: %s\n", response.Content)

	// Print usage stats
	if usage, ok := response.Metadata["usage"].(map[string]interface{}); ok {
		fmt.Printf("\nTokens used: %v\n", usage)
	}
}

// conversationWithHistory demonstrates a multi-turn conversation.
func conversationWithHistory(llmAdapter llm.LLM) {
	ctx := context.Background()

	// Build conversation history
	messages := []*agenkit.Message{
		agenkit.NewMessage("system", "You are a helpful math tutor."),
		agenkit.NewMessage("user", "Can you help me with algebra?"),
		agenkit.NewMessage("agent", "Of course! I'd be happy to help you with algebra. What specific topic would you like to work on?"),
		agenkit.NewMessage("user", "How do I solve x + 5 = 10?"),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("Conversation:\n")
	for _, msg := range messages {
		fmt.Printf("%s: %s\n", msg.Role, msg.Content)
	}
	fmt.Printf("agent: %s\n", response.Content)
}

// streamingResponse demonstrates streaming completions.
func streamingResponse(llmAdapter llm.LLM) {
	ctx := context.Background()

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Count from 1 to 5, one number per line."),
	}

	stream, err := llmAdapter.Stream(ctx, messages)
	if err != nil {
		log.Fatalf("Error starting stream: %v", err)
	}

	fmt.Printf("User: Count from 1 to 5, one number per line.\n")
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
		agenkit.NewMessage("system", "You are a creative writing assistant."),
		agenkit.NewMessage("user", "Write a short poem about coding."),
	}

	// Use custom parameters for more creative output
	response, err := llmAdapter.Complete(
		ctx,
		messages,
		llm.WithTemperature(0.9),        // Higher temperature for creativity
		llm.WithMaxTokens(200),           // Limit response length
		llm.WithTopP(0.95),               // Nucleus sampling
		llm.WithExtra("presence_penalty", 0.6), // Encourage topic diversity
	)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("User: Write a short poem about coding.\n")
	fmt.Printf("Assistant: %s\n", response.Content)
	fmt.Printf("\nParameters used:\n")
	fmt.Printf("  Temperature: 0.9\n")
	fmt.Printf("  MaxTokens: 200\n")
	fmt.Printf("  TopP: 0.95\n")
	fmt.Printf("  PresencePenalty: 0.6\n")
}
