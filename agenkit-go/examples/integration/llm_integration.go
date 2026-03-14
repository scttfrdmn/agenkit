// LLM Integration Example - OpenAI, Anthropic, and Ollama
//
// Demonstrates how to integrate real LLM providers:
// - OpenAI (GPT-4, GPT-3.5)
// - Anthropic (Claude)
// - Ollama (Local models)
// - Middleware for production resilience
//
// Setup:
//   export OPENAI_API_KEY="your-key"
//   export ANTHROPIC_API_KEY="your-key"
//   # For Ollama: ollama pull llama2
//
// Run: go run examples/integration/llm_integration.go

//go:build ignore

package main

import (
	"context"
	"fmt"
	"os"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/middleware"
)

func printSeparator(title string) {
	fmt.Println()
	fmt.Println("======================================================================")
	if title != "" {
		fmt.Println(title)
		fmt.Println("======================================================================")
	}
	fmt.Println()
}

// Example 1: OpenAI Integration
func exampleOpenAI() {
	printSeparator("Example 1: OpenAI Integration")
	fmt.Println("  GPT-4 and GPT-3.5 Turbo support")

	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		fmt.Println("  ⚠️  OPENAI_API_KEY not set, skipping...")
		return
	}

	llmAdapter := llm.NewOpenAILLM(apiKey, "gpt-3.5-turbo")

	fmt.Println("  Asking OpenAI: \"What is agenkit?\"")
	ctx := context.Background()

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "What is agenkit? Answer in one sentence."),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		fmt.Printf("  ❌ Error: %v\n\n", err)
		return
	}

	fmt.Printf("  🤖 OpenAI: %s\n\n", response.ContentString())
}

// Example 2: Anthropic Integration (Claude)
func exampleAnthropic() {
	printSeparator("Example 2: Anthropic Integration")
	fmt.Println("  Claude 3 (Opus, Sonnet, Haiku) support")

	apiKey := os.Getenv("ANTHROPIC_API_KEY")
	if apiKey == "" {
		fmt.Println("  ⚠️  ANTHROPIC_API_KEY not set, skipping...")
		return
	}

	llmAdapter := llm.NewAnthropicLLM(apiKey, "claude-3-5-sonnet-20241022")

	fmt.Println("  Asking Claude: \"What makes a good AI agent framework?\"")
	ctx := context.Background()

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "What makes a good AI agent framework? One sentence."),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		fmt.Printf("  ❌ Error: %v\n\n", err)
		return
	}

	fmt.Printf("  🤖 Claude: %s\n\n", response.ContentString())
}

// Example 3: Ollama Integration (Local models)
func exampleOllama() {
	printSeparator("Example 3: Ollama Integration")
	fmt.Println("  Local LLM inference (Llama 2, Mistral, etc.)")

	llmAdapter := llm.NewOllamaLLM("llama2", "http://localhost:11434")

	fmt.Println("  Asking Ollama: \"What are AI agents?\"")
	ctx := context.Background()

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "What are AI agents? One sentence."),
	}

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		fmt.Printf("  ❌ Error: %v\n", err)
		fmt.Println("  💡 Make sure Ollama is running: ollama serve")
		fmt.Println("  💡 And model is downloaded: ollama pull llama2")
		return
	}

	fmt.Printf("  🤖 Ollama: %s\n\n", response.ContentString())
}

// Example 4: Production-Ready LLM with Middleware
func exampleProductionMiddleware() {
	printSeparator("Example 4: Production-Ready LLM with Middleware")
	fmt.Println("  Add resilience: Retry + Timeout + Circuit Breaker")

	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		fmt.Println("  ⚠️  OPENAI_API_KEY not set, skipping...")
		return
	}

	// Create base LLM
	baseLLM := llm.NewOpenAILLM(apiKey, "gpt-3.5-turbo")

	// Wrap with production middleware
	productionLLM := middleware.WithCircuitBreaker(
		middleware.WithTimeout(
			middleware.WithRetry(
				baseLLM,
				&middleware.RetryConfig{
					MaxRetries:        3,
					InitialDelay:      1.0,
					RetryMultiplier: 2.0,
				},
			),
			&middleware.TimeoutConfig{
				Timeout: 30.0,
			},
		),
		&middleware.CircuitBreakerConfig{
			FailureThreshold: 5,
			RecoveryTimeout:  60.0,
		},
	)

	fmt.Println("  Middleware stack: Circuit Breaker → Timeout → Retry → OpenAI")
	fmt.Println("  Processing request...")

	ctx := context.Background()
	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Explain middleware in one sentence."),
	}

	response, err := productionLLM.Complete(ctx, messages)
	if err != nil {
		fmt.Printf("  ❌ Failed: %v\n\n", err)
		return
	}

	fmt.Printf("  ✅ Success: %s\n\n", response.ContentString())
}

// Example 5: Streaming LLM Responses
func exampleStreaming() {
	printSeparator("Example 5: Streaming LLM Responses")
	fmt.Println("  Real-time token-by-token output")

	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		fmt.Println("  ⚠️  OPENAI_API_KEY not set, skipping...")
		return
	}

	llmAdapter := llm.NewOpenAILLM(apiKey, "gpt-3.5-turbo")

	fmt.Println("  Streaming response: \"Tell me a haiku about code\"")
	fmt.Print("  🤖 ")

	ctx := context.Background()
	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Tell me a haiku about code."),
	}

	stream, err := llmAdapter.Stream(ctx, messages)
	if err != nil {
		fmt.Printf("\n  ❌ Error: %v\n\n", err)
		return
	}

	for chunk := range stream {
		if chunk.Error != nil {
			fmt.Printf("\n  ❌ Stream error: %v\n\n", chunk.Error)
			return
		}
		fmt.Print(chunk.Message.ContentString())
	}
	fmt.Println("")
}

// Print LLM configuration best practices
func printBestPractices() {
	printSeparator("🎯 LLM Configuration Best Practices")

	fmt.Println("  Model Selection:")
	fmt.Println("    • GPT-4: Most capable, slower, $$$")
	fmt.Println("    • GPT-3.5-turbo: Fast, cheap, good for most tasks")
	fmt.Println("    • Claude Opus: Highest capability")
	fmt.Println("    • Claude Sonnet: Balanced performance/cost")
	fmt.Println("    • Claude Haiku: Fastest, cheapest")
	fmt.Println("    • Ollama (local): Free, private, offline")

	fmt.Println("  Temperature Settings:")
	fmt.Println("    • 0.0-0.3: Deterministic, factual (code, facts)")
	fmt.Println("    • 0.4-0.7: Balanced (most applications)")
	fmt.Println("    • 0.8-1.0: Creative (writing, brainstorming)")

	fmt.Println("  Production Checklist:")
	fmt.Println("    ✓ Add retry middleware (handle rate limits)")
	fmt.Println("    ✓ Add timeout middleware (prevent hangs)")
	fmt.Println("    ✓ Add circuit breaker (handle outages)")
	fmt.Println("    ✓ Monitor token usage (cost control)")
	fmt.Println("    ✓ Cache responses (reduce API calls)")
	fmt.Println("    ✓ Use streaming for UX (show progress)")
}

// Print cost optimization tips
func printCostOptimization() {
	printSeparator("💰 Cost Optimization Tips")

	fmt.Println("  1. Use appropriate models:")
	fmt.Println("     • Don't use GPT-4 for simple tasks")
	fmt.Println("     • Start with GPT-3.5, upgrade if needed")

	fmt.Println("  2. Limit max_tokens:")
	fmt.Println("     • Set reasonable limits (e.g., 150 for short answers)")
	fmt.Println("     • Prevents runaway costs")

	fmt.Println("  3. Cache responses:")
	fmt.Println("     • Use caching middleware for repeated queries")
	fmt.Println("     • Especially effective for FAQ-style apps")

	fmt.Println("  4. Batch requests:")
	fmt.Println("     • Use batching middleware when possible")
	fmt.Println("     • OpenAI Batch API: 50% cheaper!")

	fmt.Println("  5. Use local models (Ollama):")
	fmt.Println("     • Free for development and testing")
	fmt.Println("     • No API costs or rate limits")
	fmt.Println("     • Privacy-preserving (data stays local)")

	fmt.Println("✨ Pro Tip: Monitor your API usage in production!")
	fmt.Println("   Set up alerts for unexpected cost spikes.")
}

func main() {
	fmt.Println("\n🤖 Agenkit LLM Integration Examples")

	exampleOpenAI()
	exampleAnthropic()
	exampleOllama()
	exampleProductionMiddleware()
	exampleStreaming()

	printBestPractices()
	printCostOptimization()

	printSeparator("✅ ALL EXAMPLES COMPLETED")
}
