//go:build ignore

// service_connectors demonstrates the named provider preset factory functions
// for production inference servers.
//
// Each factory function wraps NewOpenAICompatibleLLM with provider-specific
// default URLs, so you can connect to a known inference server type with a
// single call.
//
// Start the server for the provider you want to test, then run this example:
//
//	vLLM:
//	  python -m vllm.entrypoints.openai.api_server \
//	      --model meta-llama/Llama-3.1-8B-Instruct
//
//	SGLang:
//	  python -m sglang.launch_server \
//	      --model-path meta-llama/Llama-3.1-8B-Instruct --port 30000
//
//	TensorRT-LLM (Triton):
//	  docker run --gpus all -p 8000:8000 \
//	      nvcr.io/nvidia/tritonserver:24.12-trtllm-python-py3
//
//	DeepSpeed-MII:
//	  python -c "import mii; mii.serve('meta-llama/Llama-3.1-8B-Instruct')"
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ProviderConfig holds connection details for a production inference server.
type ProviderConfig struct {
	Name    string
	Model   string
	BaseURL string // empty = use connector default
}

// providers lists the four supported production inference servers.
var providers = []ProviderConfig{
	{
		Name:  "vLLM",
		Model: "meta-llama/Llama-3.1-8B-Instruct",
		// BaseURL: "" — VLLMConnector defaults to http://localhost:8000/v1
	},
	{
		Name:  "SGLang",
		Model: "meta-llama/Llama-3.1-8B-Instruct",
		// BaseURL: "" — SGLangConnector defaults to http://localhost:30000/v1
	},
	{
		Name:  "TensorRT-LLM",
		Model: "llama-3.1-8b-instruct",
		// BaseURL: "" — TensorRTLLMConnector defaults to http://localhost:8000/v1
	},
	{
		Name:  "DeepSpeed",
		Model: "meta-llama/Llama-3.1-8B-Instruct",
		// BaseURL: "" — DeepSpeedConnector defaults to http://localhost:8000/v1
	},
}

func main() {
	ctx := context.Background()

	fmt.Println("Service Connector Examples")
	fmt.Println("==========================")
	fmt.Println("Each connector below wraps OpenAICompatibleLLM with provider-specific defaults.")
	fmt.Println("Start the server for the provider you want to test, then run this example.")
	fmt.Println()

	for _, p := range providers {
		fmt.Printf("--- %s ---\n", p.Name)
		runExample(ctx, p)
		fmt.Println()
	}
}

// connectorFor creates the appropriate connector for the named provider.
func connectorFor(p ProviderConfig) *llm.OpenAICompatibleLLM {
	switch p.Name {
	case "vLLM":
		return llm.VLLMConnector(p.Model, p.BaseURL)
	case "SGLang":
		return llm.SGLangConnector(p.Model, p.BaseURL)
	case "TensorRT-LLM":
		return llm.TensorRTLLMConnector(p.Model, p.BaseURL)
	case "DeepSpeed":
		return llm.DeepSpeedConnector(p.Model, p.BaseURL)
	default:
		log.Fatalf("unknown provider: %s", p.Name)
		return nil
	}
}

// runExample connects to a single provider and sends a simple question.
// It prints a helpful message when the provider is not running.
func runExample(ctx context.Context, p ProviderConfig) {
	adapter := connectorFor(p)

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Reply with exactly one sentence: what are you?"),
	}

	resp, err := adapter.Complete(ctx, messages, llm.WithMaxTokens(80))
	if err != nil {
		log.Printf("  [%s] not available (is the server running?): %v", p.Name, err)
		return
	}

	fmt.Printf("  Model    : %s\n", adapter.Model())
	fmt.Printf("  Provider : %v\n", resp.Metadata["provider"])
	fmt.Printf("  Reply    : %s\n", resp.ContentString())
	if usage, ok := resp.Metadata["usage"].(map[string]interface{}); ok {
		if total, ok := usage["total_tokens"].(int); ok {
			fmt.Printf("  Tokens   : %d\n", total)
		}
	}
}
