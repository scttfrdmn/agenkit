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
	ctx := context.Background()

	// Example 1: Using IAM role (default credential chain)
	fmt.Println("=== Example 1: Using IAM Role (Default Credentials) ===")
	iamRoleExample(ctx)

	// Example 2: Using AWS profile
	fmt.Println("\n=== Example 2: Using AWS Profile ===")
	profileExample(ctx)

	// Example 3: Using explicit credentials
	fmt.Println("\n=== Example 3: Using Explicit Credentials ===")
	explicitCredentialsExample(ctx)

	// Example 4: Streaming response
	fmt.Println("\n=== Example 4: Streaming Response ===")
	streamingExample(ctx)

	// Example 5: Custom parameters
	fmt.Println("\n=== Example 5: Custom Parameters ===")
	customParametersExample(ctx)

	// Example 6: Multi-turn conversation
	fmt.Println("\n=== Example 6: Multi-turn Conversation ===")
	conversationExample(ctx)
}

// iamRoleExample demonstrates using default credentials (IAM role, env vars, etc.)
func iamRoleExample(ctx context.Context) {
	// Create Bedrock LLM adapter with default credentials
	// This will use the AWS credential chain:
	// 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
	// 2. Shared credentials file (~/.aws/credentials)
	// 3. IAM role attached to EC2/ECS/EKS instance
	llmAdapter, err := llm.NewBedrockLLM(ctx, llm.BedrockConfig{
		ModelID: "anthropic.claude-3-5-sonnet-20241022-v2:0",
		Region:  "us-east-1",
	})
	if err != nil {
		log.Printf("Failed to create Bedrock LLM (skipping): %v", err)
		return
	}

	fmt.Printf("Using model: %s\n", llmAdapter.Model())

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "What is the capital of France?"),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Printf("Error: %v", err)
		return
	}

	fmt.Printf("User: What is the capital of France?\n")
	fmt.Printf("Assistant: %s\n", response.Content)

	// Print usage stats
	if usage, ok := response.Metadata["usage"].(map[string]interface{}); ok {
		fmt.Printf("\nTokens used: %v\n", usage)
	}
}

// profileExample demonstrates using an AWS profile
func profileExample(ctx context.Context) {
	// Get profile from environment or use default
	profile := os.Getenv("AWS_PROFILE")
	if profile == "" {
		profile = "default"
	}

	llmAdapter, err := llm.NewBedrockLLM(ctx, llm.BedrockConfig{
		ModelID: "anthropic.claude-3-5-sonnet-20241022-v2:0",
		Region:  "us-east-1",
		Profile: profile,
	})
	if err != nil {
		log.Printf("Failed to create Bedrock LLM with profile (skipping): %v", err)
		return
	}

	fmt.Printf("Using AWS profile: %s\n", profile)
	fmt.Printf("Using model: %s\n", llmAdapter.Model())

	messages := []*agenkit.Message{
		agenkit.NewMessage("system", "You are a helpful geography expert."),
		agenkit.NewMessage("user", "Name three countries in South America."),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Printf("Error: %v", err)
		return
	}

	fmt.Printf("User: Name three countries in South America.\n")
	fmt.Printf("Assistant: %s\n", response.Content)
}

// explicitCredentialsExample demonstrates using explicit credentials
func explicitCredentialsExample(ctx context.Context) {
	// Get credentials from environment
	accessKey := os.Getenv("AWS_ACCESS_KEY_ID")
	secretKey := os.Getenv("AWS_SECRET_ACCESS_KEY")
	sessionToken := os.Getenv("AWS_SESSION_TOKEN")

	if accessKey == "" || secretKey == "" {
		log.Println("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY not set (skipping)")
		return
	}

	llmAdapter, err := llm.NewBedrockLLM(ctx, llm.BedrockConfig{
		ModelID:         "anthropic.claude-3-5-sonnet-20241022-v2:0",
		Region:          "us-east-1",
		AccessKeyID:     accessKey,
		SecretAccessKey: secretKey,
		SessionToken:    sessionToken,
	})
	if err != nil {
		log.Printf("Failed to create Bedrock LLM with credentials (skipping): %v", err)
		return
	}

	fmt.Printf("Using explicit credentials\n")
	fmt.Printf("Using model: %s\n", llmAdapter.Model())

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "What is 7 * 8?"),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Printf("Error: %v", err)
		return
	}

	fmt.Printf("User: What is 7 * 8?\n")
	fmt.Printf("Assistant: %s\n", response.Content)
}

// streamingExample demonstrates streaming responses
func streamingExample(ctx context.Context) {
	llmAdapter, err := llm.NewBedrockLLM(ctx, llm.BedrockConfig{
		ModelID: "anthropic.claude-3-5-sonnet-20241022-v2:0",
		Region:  "us-east-1",
	})
	if err != nil {
		log.Printf("Failed to create Bedrock LLM (skipping): %v", err)
		return
	}

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Write a haiku about cloud computing."),
	}

	stream, err := llmAdapter.Stream(ctx, messages)
	if err != nil {
		log.Printf("Error starting stream: %v", err)
		return
	}

	fmt.Printf("User: Write a haiku about cloud computing.\n")
	fmt.Printf("Assistant (streaming): ")

	for chunk := range stream {
		// Check for errors in metadata
		if errMsg, ok := chunk.Metadata["error"].(string); ok {
			log.Printf("Stream error: %s", errMsg)
			return
		}

		fmt.Print(chunk.Content)
	}
	fmt.Println()
}

// customParametersExample demonstrates using custom parameters
func customParametersExample(ctx context.Context) {
	llmAdapter, err := llm.NewBedrockLLM(ctx, llm.BedrockConfig{
		ModelID: "anthropic.claude-3-5-sonnet-20241022-v2:0",
		Region:  "us-east-1",
	})
	if err != nil {
		log.Printf("Failed to create Bedrock LLM (skipping): %v", err)
		return
	}

	messages := []*agenkit.Message{
		agenkit.NewMessage("system", "You are a concise technical writer."),
		agenkit.NewMessage("user", "Explain what AWS Lambda is in one sentence."),
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
		log.Printf("Error: %v", err)
		return
	}

	fmt.Printf("User: Explain what AWS Lambda is in one sentence.\n")
	fmt.Printf("Assistant: %s\n", response.Content)
	fmt.Printf("\nParameters used:\n")
	fmt.Printf("  Temperature: 0.3 (precise)\n")
	fmt.Printf("  MaxTokens: 100\n")
	fmt.Printf("  TopP: 0.9\n")

	if usage, ok := response.Metadata["usage"].(map[string]interface{}); ok {
		fmt.Printf("  Tokens: %v\n", usage)
	}
}

// conversationExample demonstrates a multi-turn conversation
func conversationExample(ctx context.Context) {
	llmAdapter, err := llm.NewBedrockLLM(ctx, llm.BedrockConfig{
		ModelID: "anthropic.claude-3-5-sonnet-20241022-v2:0",
		Region:  "us-east-1",
	})
	if err != nil {
		log.Printf("Failed to create Bedrock LLM (skipping): %v", err)
		return
	}

	// Start with system message and first user message
	messages := []*agenkit.Message{
		agenkit.NewMessage("system", "You are a helpful coding assistant."),
		agenkit.NewMessage("user", "Write a Go function that adds two numbers."),
	}

	// First turn
	response1, err := llmAdapter.Complete(ctx, messages, llm.WithTemperature(0.2))
	if err != nil {
		log.Printf("Error: %v", err)
		return
	}

	fmt.Printf("User: Write a Go function that adds two numbers.\n")
	fmt.Printf("Assistant: %s\n\n", response1.Content)

	// Add assistant response to conversation
	messages = append(messages, response1)

	// Second turn - follow up question
	messages = append(messages, agenkit.NewMessage("user", "Now write a test for that function."))

	response2, err := llmAdapter.Complete(ctx, messages, llm.WithTemperature(0.2))
	if err != nil {
		log.Printf("Error: %v", err)
		return
	}

	fmt.Printf("User: Now write a test for that function.\n")
	fmt.Printf("Assistant: %s\n", response2.Content)
}
