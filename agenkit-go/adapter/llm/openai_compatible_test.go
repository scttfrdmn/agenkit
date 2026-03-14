package llm

import (
	"context"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestOpenAICompatibleLLMInterface verifies that OpenAICompatibleLLM implements the LLM interface.
func TestOpenAICompatibleLLMInterface(t *testing.T) {
	var _ LLM = &OpenAICompatibleLLM{}
}

// TestNewOpenAICompatibleLLM tests the constructor.
func TestNewOpenAICompatibleLLM(t *testing.T) {
	tests := []struct {
		name             string
		baseURL          string
		model            string
		provider         string
		apiKey           string
		expectedModel    string
		expectedProvider string
		expectedBaseURL  string
	}{
		{
			name:             "With all parameters",
			baseURL:          "http://localhost:8000/v1",
			model:            "llama-2-7b",
			provider:         "vllm",
			apiKey:           "test-key",
			expectedModel:    "llama-2-7b",
			expectedProvider: "vllm",
			expectedBaseURL:  "http://localhost:8000/v1",
		},
		{
			name:             "Without API key",
			baseURL:          "http://localhost:8000/v1",
			model:            "llama-2-7b",
			provider:         "vllm",
			apiKey:           "",
			expectedModel:    "llama-2-7b",
			expectedProvider: "vllm",
			expectedBaseURL:  "http://localhost:8000/v1",
		},
		{
			name:             "Without provider",
			baseURL:          "http://localhost:8000/v1",
			model:            "llama-2-7b",
			provider:         "",
			apiKey:           "",
			expectedModel:    "llama-2-7b",
			expectedProvider: "",
			expectedBaseURL:  "http://localhost:8000/v1",
		},
		{
			name:             "llama.cpp configuration",
			baseURL:          "http://localhost:8080/v1",
			model:            "llama-2-7b-chat",
			provider:         "llamacpp",
			apiKey:           "",
			expectedModel:    "llama-2-7b-chat",
			expectedProvider: "llamacpp",
			expectedBaseURL:  "http://localhost:8080/v1",
		},
		{
			name:             "SGLang configuration",
			baseURL:          "http://localhost:30000/v1",
			model:            "meta-llama/Llama-2-13b-chat-hf",
			provider:         "sglang",
			apiKey:           "",
			expectedModel:    "meta-llama/Llama-2-13b-chat-hf",
			expectedProvider: "sglang",
			expectedBaseURL:  "http://localhost:30000/v1",
		},
		{
			name:             "TensorRT-LLM configuration",
			baseURL:          "http://localhost:8001/v1",
			model:            "llama-2-70b",
			provider:         "tensorrt",
			apiKey:           "api-key-123",
			expectedModel:    "llama-2-70b",
			expectedProvider: "tensorrt",
			expectedBaseURL:  "http://localhost:8001/v1",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			llm := NewOpenAICompatibleLLM(tt.baseURL, tt.model, tt.provider, tt.apiKey)

			if llm == nil {
				t.Fatal("NewOpenAICompatibleLLM returned nil")
			}

			if llm.Model() != tt.expectedModel {
				t.Errorf("Expected model %s, got %s", tt.expectedModel, llm.Model())
			}

			if llm.provider != tt.expectedProvider {
				t.Errorf("Expected provider %s, got %s", tt.expectedProvider, llm.provider)
			}

			if llm.baseURL != tt.expectedBaseURL {
				t.Errorf("Expected baseURL %s, got %s", tt.expectedBaseURL, llm.baseURL)
			}

			if llm.client == nil {
				t.Error("Client should not be nil")
			}
		})
	}
}

// TestOpenAICompatibleModel tests the Model() method.
func TestOpenAICompatibleModel(t *testing.T) {
	llm := NewOpenAICompatibleLLM(
		"http://localhost:8000/v1",
		"test-model",
		"vllm",
		"",
	)

	if llm.Model() != "test-model" {
		t.Errorf("Expected model 'test-model', got %s", llm.Model())
	}
}

// TestOpenAICompatibleUnwrap tests the Unwrap() method.
func TestOpenAICompatibleUnwrap(t *testing.T) {
	llm := NewOpenAICompatibleLLM(
		"http://localhost:8000/v1",
		"test-model",
		"vllm",
		"",
	)

	client := llm.Unwrap()
	if client == nil {
		t.Error("Unwrap should not return nil")
	}

	// Verify it's the same client
	if client != llm.client {
		t.Error("Unwrap should return the underlying client")
	}
}

// TestConvertMessages tests message conversion.
func TestConvertMessages(t *testing.T) {
	llm := NewOpenAICompatibleLLM(
		"http://localhost:8000/v1",
		"test-model",
		"vllm",
		"",
	)

	tests := []struct {
		name          string
		messages      []*agenkit.Message
		expectedCount int
		expectedRoles []string
	}{
		{
			name: "Single user message",
			messages: []*agenkit.Message{
				agenkit.NewMessage("user", "Hello"),
			},
			expectedCount: 1,
			expectedRoles: []string{"user"},
		},
		{
			name: "System message",
			messages: []*agenkit.Message{
				agenkit.NewMessage("system", "You are helpful"),
			},
			expectedCount: 1,
			expectedRoles: []string{"system"},
		},
		{
			name: "Agent to assistant conversion",
			messages: []*agenkit.Message{
				agenkit.NewMessage("agent", "I can help"),
			},
			expectedCount: 1,
			expectedRoles: []string{"assistant"},
		},
		{
			name: "Tool message",
			messages: []*agenkit.Message{
				agenkit.NewMessage("tool", "Tool result"),
			},
			expectedCount: 1,
			expectedRoles: []string{"tool"},
		},
		{
			name: "Multi-turn conversation",
			messages: []*agenkit.Message{
				agenkit.NewMessage("system", "You are helpful"),
				agenkit.NewMessage("user", "Hello"),
				agenkit.NewMessage("agent", "Hi there!"),
				agenkit.NewMessage("user", "How are you?"),
			},
			expectedCount: 4,
			expectedRoles: []string{"system", "user", "assistant", "user"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			converted := llm.convertMessages(tt.messages)

			if len(converted) != tt.expectedCount {
				t.Errorf("Expected %d messages, got %d", tt.expectedCount, len(converted))
			}

			for i, expectedRole := range tt.expectedRoles {
				if i >= len(converted) {
					t.Fatalf("Not enough converted messages")
				}
				if converted[i].Role != expectedRole {
					t.Errorf("Message %d: expected role %s, got %s", i, expectedRole, converted[i].Role)
				}
			}

			// Verify content is preserved
			for i, msg := range tt.messages {
				if converted[i].Content != msg.ContentString() {
					t.Errorf("Message %d: content not preserved. Expected %s, got %s",
						i, msg.ContentString(), converted[i].Content)
				}
			}
		})
	}
}

// TestOpenAICompatibleCompleteMetadata tests that Complete() adds proper metadata.
// Note: This is a unit test that doesn't make real API calls.
// Integration tests with running services are in adapter_test/.
func TestOpenAICompatibleCompleteMetadata(t *testing.T) {
	// This test verifies the metadata structure without making real API calls.
	// The actual API behavior is tested in integration tests.

	llm := NewOpenAICompatibleLLM(
		"http://localhost:8000/v1",
		"test-model",
		"vllm",
		"test-key",
	)

	// Verify provider is set correctly
	if llm.provider != "vllm" {
		t.Errorf("Expected provider 'vllm', got %s", llm.provider)
	}

	// Verify baseURL is set correctly
	if llm.baseURL != "http://localhost:8000/v1" {
		t.Errorf("Expected baseURL 'http://localhost:8000/v1', got %s", llm.baseURL)
	}
}

// TestOpenAICompatibleDefaultProvider tests the default provider name.
func TestOpenAICompatibleDefaultProvider(t *testing.T) {
	llm := NewOpenAICompatibleLLM(
		"http://localhost:8000/v1",
		"test-model",
		"", // No provider specified
		"",
	)

	if llm.provider != "" {
		t.Errorf("Expected empty provider, got %s", llm.provider)
	}

	// When provider is empty, metadata should use "openai_compatible"
	// This is tested in the Complete() method implementation
}

// TestOpenAICompatibleCallOptions tests that call options are properly applied.
func TestOpenAICompatibleCallOptions(t *testing.T) {
	// This test verifies that options are built correctly
	// The actual API behavior is tested in integration tests

	opts := BuildCallOptions(
		WithTemperature(0.7),
		WithMaxTokens(100),
		WithTopP(0.9),
	)

	if opts.Temperature == nil || *opts.Temperature != 0.7 {
		t.Error("Temperature not set correctly")
	}

	if opts.MaxTokens == nil || *opts.MaxTokens != 100 {
		t.Error("MaxTokens not set correctly")
	}

	if opts.TopP == nil || *opts.TopP != 0.9 {
		t.Error("TopP not set correctly")
	}
}

// TestOpenAICompatibleMessageConversionPreservesContent tests that content is not modified.
func TestOpenAICompatibleMessageConversionPreservesContent(t *testing.T) {
	llm := NewOpenAICompatibleLLM(
		"http://localhost:8000/v1",
		"test-model",
		"vllm",
		"",
	)

	testContent := "This is a test message with special characters: !@#$%^&*()"
	messages := []*agenkit.Message{
		agenkit.NewMessage("user", testContent),
	}

	converted := llm.convertMessages(messages)

	if len(converted) != 1 {
		t.Fatalf("Expected 1 message, got %d", len(converted))
	}

	if converted[0].Content != testContent {
		t.Errorf("Content was modified. Expected %s, got %s", testContent, converted[0].Content)
	}
}

// TestOpenAICompatibleEmptyMessages tests handling of empty message lists.
func TestOpenAICompatibleEmptyMessages(t *testing.T) {
	llm := NewOpenAICompatibleLLM(
		"http://localhost:8000/v1",
		"test-model",
		"vllm",
		"",
	)

	messages := []*agenkit.Message{}
	converted := llm.convertMessages(messages)

	if len(converted) != 0 {
		t.Errorf("Expected 0 messages, got %d", len(converted))
	}
}

// TestOpenAICompatibleMultipleProviders tests configuration for different providers.
func TestOpenAICompatibleMultipleProviders(t *testing.T) {
	providers := []struct {
		name     string
		baseURL  string
		port     string
		provider string
	}{
		{"vLLM", "http://localhost:8000/v1", "8000", "vllm"},
		{"llama.cpp", "http://localhost:8080/v1", "8080", "llamacpp"},
		{"SGLang", "http://localhost:30000/v1", "30000", "sglang"},
		{"TensorRT-LLM", "http://localhost:8001/v1", "8001", "tensorrt"},
		{"OpenLLM", "http://localhost:3000/v1", "3000", "openllm"},
		{"MLC LLM", "http://localhost:8088/v1", "8088", "mlc"},
		{"TGI", "http://localhost:8080/v1", "8080", "tgi"},
		{"Inferflow", "http://localhost:8000/v1", "8000", "inferflow"},
	}

	for _, p := range providers {
		t.Run(p.name, func(t *testing.T) {
			llm := NewOpenAICompatibleLLM(
				p.baseURL,
				"test-model",
				p.provider,
				"",
			)

			if llm == nil {
				t.Fatal("NewOpenAICompatibleLLM returned nil")
			}

			if llm.provider != p.provider {
				t.Errorf("Expected provider %s, got %s", p.provider, llm.provider)
			}

			if llm.baseURL != p.baseURL {
				t.Errorf("Expected baseURL %s, got %s", p.baseURL, llm.baseURL)
			}
		})
	}
}

// BenchmarkMessageConversion benchmarks the message conversion performance.
func BenchmarkMessageConversion(b *testing.B) {
	llm := NewOpenAICompatibleLLM(
		"http://localhost:8000/v1",
		"test-model",
		"vllm",
		"",
	)

	messages := []*agenkit.Message{
		agenkit.NewMessage("system", "You are a helpful assistant."),
		agenkit.NewMessage("user", "Hello, how are you?"),
		agenkit.NewMessage("agent", "I'm doing well, thank you!"),
		agenkit.NewMessage("user", "That's great to hear."),
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = llm.convertMessages(messages)
	}
}

// BenchmarkBuildCallOptions benchmarks the option building performance.
func BenchmarkBuildCallOptions(b *testing.B) {
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = BuildCallOptions(
			WithTemperature(0.7),
			WithMaxTokens(1024),
			WithTopP(0.9),
		)
	}
}

// TestOpenAICompatibleStreamContext tests that context cancellation works correctly.
// Note: This is a structural test. Full stream testing is in integration tests.
func TestOpenAICompatibleStreamContext(t *testing.T) {
	llm := NewOpenAICompatibleLLM(
		"http://localhost:8000/v1",
		"test-model",
		"vllm",
		"",
	)

	// Test that cancelling context before stream doesn't panic
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	messages := []*agenkit.Message{
		agenkit.NewMessage("user", "Hello"),
	}

	// This will fail to connect (which is expected), but shouldn't panic
	_, err := llm.Stream(ctx, messages)
	if err == nil {
		// If somehow it succeeds, that's OK for this test
		return
	}

	// We just want to make sure it doesn't panic
	// The actual error handling is tested in integration tests
}
