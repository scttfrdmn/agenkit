//go:build ignore
// +build ignore

package main

import (
	"context"
	"fmt"
	"log"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

func main() {
	fmt.Println("╔" + repeatString("=", 78) + "╗")
	fmt.Println("║" + center("OpenAI-Compatible LLM Adapter Examples", 78) + "║")
	fmt.Println("╚" + repeatString("=", 78) + "╝")
	fmt.Println()

	fmt.Println("This example demonstrates using Agenkit with OpenAI-compatible")
	fmt.Println("inference services like vLLM, llama.cpp, SGLang, and TensorRT-LLM.")
	fmt.Println()
	fmt.Println("Note: These examples require a running inference service.")
	fmt.Println("See the examples below for setup instructions.")
	fmt.Println()

	// Example 1: vLLM local deployment
	fmt.Println(repeatString("=", 80))
	fmt.Println("Example 1: vLLM Local Deployment")
	fmt.Println(repeatString("=", 80))
	fmt.Println()
	vllmExample()

	// Example 2: llama.cpp server
	fmt.Println("\n" + repeatString("=", 80))
	fmt.Println("Example 2: llama.cpp Server")
	fmt.Println(repeatString("=", 80))
	fmt.Println()
	llamacppExample()

	// Example 3: Streaming response
	fmt.Println("\n" + repeatString("=", 80))
	fmt.Println("Example 3: Streaming Response")
	fmt.Println(repeatString("=", 80))
	fmt.Println()
	streamingExample()

	// Example 4: Multi-service comparison
	fmt.Println("\n" + repeatString("=", 80))
	fmt.Println("Example 4: Multi-Service Comparison")
	fmt.Println(repeatString("=", 80))
	fmt.Println()
	multiServiceExample()

	// Print setup instructions
	fmt.Println("\n" + repeatString("=", 80))
	fmt.Println("Setup Instructions")
	fmt.Println(repeatString("=", 80))
	printSetupInstructions()
}

// vllmExample demonstrates using vLLM inference service.
func vllmExample() {
	fmt.Println("Setup: docker run --gpus all -p 8000:8000 vllm/vllm-openai \\")
	fmt.Println("         --model meta-llama/Llama-2-7b-chat-hf")
	fmt.Println()

	// Create vLLM adapter
	llmAdapter := llm.NewOpenAICompatibleLLM(
		"http://localhost:8000/v1",
		"meta-llama/Llama-2-7b-chat-hf",
		"vllm",
		"", // No API key needed for local deployment
	)

	fmt.Printf("✓ Connected to vLLM service\n")
	fmt.Printf("  Model: %s\n", llmAdapter.Model())
	fmt.Println()

	ctx := context.Background()

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "What is machine learning in one sentence?"),
	}

	fmt.Println("📤 User: What is machine learning in one sentence?")

	response, err := llmAdapter.Complete(ctx, messages)
	if err != nil {
		log.Printf("❌ Error (service may not be running): %v", err)
		return
	}

	fmt.Printf("📥 Assistant: %s\n", response.Content)

	// Print metadata
	if provider, ok := response.Metadata["provider"].(string); ok {
		fmt.Printf("\n📊 Metadata:\n")
		fmt.Printf("  Provider: %s\n", provider)
		fmt.Printf("  Base URL: %s\n", response.Metadata["base_url"])
		if usage, ok := response.Metadata["usage"].(map[string]interface{}); ok {
			if totalTokens, ok := usage["total_tokens"].(int); ok {
				fmt.Printf("  Tokens: %d\n", totalTokens)
			}
		}
	}
}

// llamacppExample demonstrates using llama.cpp server.
func llamacppExample() {
	fmt.Println("Setup: ./llama.cpp/server -m models/llama-2-7b-chat.gguf \\")
	fmt.Println("         -c 2048 --port 8080")
	fmt.Println()

	// Create llama.cpp adapter
	llmAdapter := llm.NewOpenAICompatibleLLM(
		"http://localhost:8080/v1",
		"llama-2-7b-chat",
		"llamacpp",
		"",
	)

	fmt.Printf("✓ Connected to llama.cpp server\n")
	fmt.Printf("  Model: %s\n", llmAdapter.Model())
	fmt.Println()

	ctx := context.Background()

	messages := []*agenkit.Message{
		agenkit.NewMessage("system", "You are a helpful assistant."),
		agenkit.NewMessage("user", "Write a haiku about coding."),
	}

	fmt.Println("📤 User: Write a haiku about coding.")

	response, err := llmAdapter.Complete(
		ctx,
		messages,
		llm.WithTemperature(0.7),
		llm.WithMaxTokens(100),
	)
	if err != nil {
		log.Printf("❌ Error (service may not be running): %v", err)
		return
	}

	fmt.Printf("📥 Assistant:\n%s\n", response.Content)
}

// streamingExample demonstrates streaming responses.
func streamingExample() {
	fmt.Println("This example streams responses in real-time from vLLM.")
	fmt.Println()

	// Create adapter
	llmAdapter := llm.NewOpenAICompatibleLLM(
		"http://localhost:8000/v1",
		"meta-llama/Llama-2-7b-chat-hf",
		"vllm",
		"",
	)

	ctx := context.Background()

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Count from 1 to 10 slowly."),
	}

	fmt.Println("📤 User: Count from 1 to 10 slowly.")
	fmt.Print("📥 Assistant (streaming): ")

	stream, err := llmAdapter.Stream(ctx, messages)
	if err != nil {
		log.Printf("❌ Error (service may not be running): %v", err)
		return
	}

	// Stream chunks as they arrive
	for chunk := range stream {
		// Check for errors in metadata
		if errMsg, ok := chunk.Metadata["error"].(string); ok {
			log.Printf("\n❌ Stream error: %s", errMsg)
			return
		}

		fmt.Print(chunk.Content)
	}
	fmt.Println()
}

// multiServiceExample demonstrates comparing multiple services.
func multiServiceExample() {
	fmt.Println("This example shows how the same code works with different services.")
	fmt.Println()

	services := []struct {
		name     string
		baseURL  string
		model    string
		provider string
	}{
		{
			name:     "vLLM",
			baseURL:  "http://localhost:8000/v1",
			model:    "meta-llama/Llama-2-7b-chat-hf",
			provider: "vllm",
		},
		{
			name:     "llama.cpp",
			baseURL:  "http://localhost:8080/v1",
			model:    "llama-2-7b-chat",
			provider: "llamacpp",
		},
		{
			name:     "SGLang",
			baseURL:  "http://localhost:30000/v1",
			model:    "meta-llama/Llama-2-7b-chat-hf",
			provider: "sglang",
		},
	}

	ctx := context.Background()
	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "What is a GPU in one sentence?"),
	}

	for _, svc := range services {
		fmt.Printf("Testing %s...\n", svc.name)

		llmAdapter := llm.NewOpenAICompatibleLLM(
			svc.baseURL,
			svc.model,
			svc.provider,
			"",
		)

		response, err := llmAdapter.Complete(ctx, messages, llm.WithMaxTokens(100))
		if err != nil {
			fmt.Printf("  ❌ %s not available: %v\n\n", svc.name, err)
			continue
		}

		fmt.Printf("  ✅ %s responded:\n", svc.name)
		fmt.Printf("     %s\n", truncate(response.Content, 80))
		if provider, ok := response.Metadata["provider"].(string); ok {
			fmt.Printf("     Provider: %s\n", provider)
		}
		fmt.Println()
	}

	fmt.Println("💡 Key Point: The same Agenkit code works with all services!")
}

// printSetupInstructions prints detailed setup instructions.
func printSetupInstructions() {
	fmt.Println("\n1️⃣  vLLM:")
	fmt.Println("   docker run --gpus all -p 8000:8000 vllm/vllm-openai \\")
	fmt.Println("       --model meta-llama/Llama-2-7b-chat-hf")
	fmt.Println()

	fmt.Println("2️⃣  llama.cpp:")
	fmt.Println("   git clone https://github.com/ggerganov/llama.cpp")
	fmt.Println("   cd llama.cpp && make")
	fmt.Println("   ./server -m models/llama-2-7b-chat.gguf -c 2048 --port 8080")
	fmt.Println()

	fmt.Println("3️⃣  SGLang:")
	fmt.Println("   pip install sglang")
	fmt.Println("   python -m sglang.launch_server \\")
	fmt.Println("       --model-path meta-llama/Llama-2-7b-chat-hf \\")
	fmt.Println("       --port 30000")
	fmt.Println()

	fmt.Println("4️⃣  TensorRT-LLM:")
	fmt.Println("   docker run --gpus all -p 8001:8001 \\")
	fmt.Println("       nvcr.io/nvidia/tritonserver:23.10-trtllm-python-py3 \\")
	fmt.Println("       tritonserver --model-repository=/models")
	fmt.Println()

	fmt.Println("📚 For detailed setup guides, see:")
	fmt.Println("   examples/adapters/openai_compatible/README.md")
	fmt.Println()

	fmt.Println("💡 Benefits:")
	fmt.Println("   • Run LLMs locally (no cloud API costs)")
	fmt.Println("   • Keep data private (on-premises)")
	fmt.Println("   • Same code works with all services")
	fmt.Println("   • Easy migration between providers")
	fmt.Println()

	fmt.Println("✅ Example Complete!")
	fmt.Println()
	fmt.Println("Next steps:")
	fmt.Println("  • Start a local inference service")
	fmt.Println("  • Run: go run examples/llm/openai_compatible_example.go")
	fmt.Println("  • Try different services and models")
}

// Helper functions

func repeatString(s string, count int) string {
	result := ""
	for i := 0; i < count; i++ {
		result += s
	}
	return result
}

func center(s string, width int) string {
	if len(s) >= width {
		return s
	}
	padding := (width - len(s)) / 2
	return repeatString(" ", padding) + s + repeatString(" ", width-len(s)-padding)
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}
