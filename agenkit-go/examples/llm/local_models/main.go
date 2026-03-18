//go:build ignore

// local_models demonstrates using Agenkit with local inference servers.
//
// All four providers (Ollama, vLLM, llama.cpp, LM Studio) expose the same
// OpenAI-compatible /v1/chat/completions endpoint, so the same adapter works
// for all of them. No API keys are required.
//
// Quick-start for each provider:
//
//	Ollama:    ollama serve && ollama pull llama3.2
//	vLLM:      docker run --gpus all -p 8000:8000 vllm/vllm-openai --model meta-llama/Llama-3.2-3B-Instruct
//	llama.cpp: ./llama-server -m models/llama-3.2-3b-instruct.Q4_K_M.gguf --port 8080
//	LM Studio: launch the app, load a model, start the local server (port 1234)
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ProviderConfig holds connection details for a local inference server.
type ProviderConfig struct {
	Name    string
	BaseURL string
	Model   string
	APIKey  string // empty = "not-needed" (most local servers skip auth)
}

// providers lists the four target local inference servers.
var providers = []ProviderConfig{
	{
		Name:    "Ollama",
		BaseURL: "http://localhost:11434/v1",
		Model:   "llama3.2",
	},
	{
		Name:    "vLLM",
		BaseURL: "http://localhost:8000/v1",
		Model:   "meta-llama/Llama-3.2-3B-Instruct",
	},
	{
		Name:    "llama.cpp",
		BaseURL: "http://localhost:8080/v1",
		Model:   "llama-3.2-3b-instruct",
	},
	{
		Name:    "LM Studio",
		BaseURL: "http://localhost:1234/v1",
		Model:   "lmstudio-community/Meta-Llama-3.2-3B-Instruct-GGUF",
	},
}

func main() {
	ctx := context.Background()

	fmt.Println("Local Model Provider Examples")
	fmt.Println("==============================")
	fmt.Println("Each provider below exposes an OpenAI-compatible endpoint.")
	fmt.Println("Start the server for the provider you want to test, then run this example.")
	fmt.Println()

	for _, p := range providers {
		fmt.Printf("--- %s (%s) ---\n", p.Name, p.BaseURL)
		runExample(ctx, p)
		fmt.Println()
	}

	fmt.Println("Provider Swap Demo")
	fmt.Println("==================")
	fmt.Println("Because all providers use the same interface, you can swap them")
	fmt.Println("by changing only the BaseURL and Model — zero other code changes.")
	providerSwapDemo(ctx)

	fmt.Println()
	fmt.Println("vLLM Named Type Demo")
	fmt.Println("=====================")
	vllmNamedTypeDemo(ctx)

	fmt.Println()
	fmt.Println("SGLang Named Type Demo")
	fmt.Println("=======================")
	sglangNamedTypeDemo(ctx)
}

// runExample connects to a single provider and asks a simple question.
// It prints a helpful error message when the provider is not running.
func runExample(ctx context.Context, p ProviderConfig) {
	adapter := llm.NewOpenAICompatibleLLM(p.BaseURL, p.Model, p.Name, p.APIKey)

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Reply with exactly one sentence: what are you?"),
	}

	resp, err := adapter.Complete(ctx, messages, llm.WithMaxTokens(80))
	if err != nil {
		log.Printf("  [%s] not available (is the server running?): %v", p.Name, err)
		return
	}

	fmt.Printf("  Model  : %s\n", adapter.Model())
	fmt.Printf("  Reply  : %s\n", resp.ContentString())
	if usage, ok := resp.Metadata["usage"].(map[string]interface{}); ok {
		if total, ok := usage["total_tokens"].(int); ok {
			fmt.Printf("  Tokens : %d\n", total)
		}
	}
}

// vllmNamedTypeDemo demonstrates the VllmLLM named type with structured-output helpers.
func vllmNamedTypeDemo(ctx context.Context) {
	adapter := llm.NewVllmLLM("meta-llama/Llama-3.1-8B-Instruct", "")
	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Reply in one sentence: what are you?"),
	}
	resp, err := adapter.Complete(ctx, messages,
		llm.WithMaxTokens(80),
		llm.WithVllmGuidedRegex(`[A-Za-z ,.'!?]+`),
	)
	if err != nil {
		log.Printf("  [vLLM] not available (is the server running?): %v", err)
		return
	}
	fmt.Printf("  Model : %s\n", adapter.Model())
	fmt.Printf("  Reply : %s\n", resp.ContentString())
}

// sglangNamedTypeDemo demonstrates the SGLangLLM named type with JSON-schema constrained output.
func sglangNamedTypeDemo(ctx context.Context) {
	adapter := llm.NewSGLangLLM("meta-llama/Llama-3.1-8B-Instruct", "")
	schema := `{"type":"object","properties":{"answer":{"type":"string"}}}`
	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "What is 2+2? Respond as JSON."),
	}
	resp, err := adapter.Complete(ctx, messages,
		llm.WithMaxTokens(50),
		llm.WithSGLangJSONSchema(schema),
	)
	if err != nil {
		log.Printf("  [SGLang] not available (is the server running?): %v", err)
		return
	}
	fmt.Printf("  Model : %s\n", adapter.Model())
	fmt.Printf("  Reply : %s\n", resp.ContentString())
}

// providerSwapDemo shows that the identical request works against any provider.
func providerSwapDemo(ctx context.Context) {
	messages := []*agenkit.Message{
		agenkit.NewMessage("system", "You are a concise assistant."),
		agenkit.NewMessage("user", "What is 2+2?"),
	}

	tried := 0
	for _, p := range providers {
		adapter := llm.NewOpenAICompatibleLLM(p.BaseURL, p.Model, p.Name, p.APIKey)
		resp, err := adapter.Complete(ctx, messages, llm.WithMaxTokens(20))
		if err != nil {
			continue // provider not running, skip silently
		}
		tried++
		fmt.Printf("  [%s] %s\n", p.Name, resp.ContentString())
	}
	if tried == 0 {
		fmt.Println("  (no local providers reachable — start one of the servers above)")
	}
}
