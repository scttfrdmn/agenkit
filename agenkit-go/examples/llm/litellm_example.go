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
	// LiteLLM proxy URL - default is http://localhost:4000
	// Start LiteLLM with: litellm --model gpt-3.5-turbo
	baseURL := os.Getenv("LITELLM_BASE_URL")
	if baseURL == "" {
		baseURL = "http://localhost:4000"
	}

	// Optional: API key for LiteLLM proxy authentication
	apiKey := os.Getenv("LITELLM_API_KEY")

	// Create LiteLLM adapter
	var llmAdapter llm.LLM
	if apiKey != "" {
		llmAdapter = llm.NewLiteLLMLLMWithAuth(baseURL, "gpt-3.5-turbo", apiKey)
		fmt.Println("Using LiteLLM with authentication")
	} else {
		llmAdapter = llm.NewLiteLLMLLM(baseURL, "gpt-3.5-turbo")
		fmt.Println("Using LiteLLM without authentication")
	}

	fmt.Printf("LiteLLM Proxy URL: %s\n", baseURL)
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

	// Example 5: Multiple providers through LiteLLM
	fmt.Println("\n=== Example 5: Multiple Providers ===")
	multipleProviders(baseURL, apiKey)
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

	messages := []*agenkit.Message{
		agenkit.NewMessage("system", "You are a helpful coding assistant that explains concepts clearly."),
		agenkit.NewMessage("user", "What is a REST API in one sentence?"),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Printf("System: You are a helpful coding assistant that explains concepts clearly.\n")
	fmt.Printf("User: What is a REST API in one sentence?\n")
	fmt.Printf("Assistant: %s\n", response.Content)
}

// streamingResponse demonstrates streaming completions.
func streamingResponse(llmAdapter llm.LLM) {
	ctx := context.Background()

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Count from 1 to 5 slowly, one number per line."),
	}

	stream, err := llmAdapter.Stream(ctx, messages)
	if err != nil {
		log.Fatalf("Error starting stream: %v", err)
	}

	fmt.Printf("User: Count from 1 to 5 slowly, one number per line.\n")
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
		agenkit.NewMessage("user", "Explain HTTP in exactly one sentence."),
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

	fmt.Printf("User: Explain HTTP in exactly one sentence.\n")
	fmt.Printf("Assistant: %s\n", response.Content)
	fmt.Printf("\nParameters used:\n")
	fmt.Printf("  Temperature: 0.3 (precise)\n")
	fmt.Printf("  MaxTokens: 100\n")
	fmt.Printf("  TopP: 0.9\n")
}

// multipleProviders demonstrates using different LLM providers through LiteLLM.
func multipleProviders(baseURL, apiKey string) {
	ctx := context.Background()

	// LiteLLM supports 100+ providers through model prefixes
	// Examples (uncomment the one you want to try):

	providers := []struct {
		name  string
		model string
		note  string
	}{
		{"OpenAI", "gpt-3.5-turbo", "Default OpenAI model"},
		{"OpenAI GPT-4", "gpt-4", "More capable OpenAI model"},
		{"Anthropic", "claude-3-5-sonnet-20241022", "Claude Sonnet 3.5"},
		{"Anthropic Haiku", "claude-3-haiku-20240307", "Fast, cost-effective Claude"},
		{"AWS Bedrock", "bedrock/anthropic.claude-v2", "Claude on AWS Bedrock"},
		{"Google Gemini", "gemini/gemini-pro", "Google's Gemini Pro"},
		{"Azure OpenAI", "azure/gpt-35-turbo", "OpenAI on Azure"},
		{"Cohere", "command-r-plus", "Cohere's Command R+"},
		{"Ollama Local", "ollama/llama2", "Local Llama2 via Ollama"},
		{"Ollama Mistral", "ollama/mistral", "Local Mistral via Ollama"},
	}

	fmt.Println("LiteLLM supports 100+ providers through model prefixes:")
	fmt.Println("\nAvailable providers:")
	for i, p := range providers {
		fmt.Printf("  %d. %s: %s (%s)\n", i+1, p.name, p.model, p.note)
	}

	fmt.Println("\nTo use any provider, simply specify the model:")
	fmt.Println("  llm := llm.NewLiteLLMLLM(baseURL, \"gpt-4\")")
	fmt.Println("  llm := llm.NewLiteLLMLLM(baseURL, \"claude-3-5-sonnet-20241022\")")
	fmt.Println("  llm := llm.NewLiteLLMLLM(baseURL, \"ollama/llama2\")")

	fmt.Println("\nTrying a simple request with default model...")

	// Create adapter with default model
	var llmAdapter llm.LLM
	if apiKey != "" {
		llmAdapter = llm.NewLiteLLMLLMWithAuth(baseURL, "gpt-3.5-turbo", apiKey)
	} else {
		llmAdapter = llm.NewLiteLLMLLM(baseURL, "gpt-3.5-turbo")
	}

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Say 'Hello from LiteLLM!' in a creative way."),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Printf("Error (this is expected if LiteLLM is not running): %v", err)
		fmt.Println("\nTo start LiteLLM proxy:")
		fmt.Println("  pip install litellm")
		fmt.Println("  litellm --model gpt-3.5-turbo")
		fmt.Println("  # Or with config file: litellm --config litellm_config.yaml")
		return
	}

	fmt.Printf("\nResponse: %s\n", response.Content)
	fmt.Printf("Model used: %s\n", response.Metadata["model"])
}
