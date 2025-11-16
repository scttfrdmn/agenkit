package llm

import (
	"context"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestCallOptions tests the functional options pattern.
func TestCallOptions(t *testing.T) {
	tests := []struct {
		name     string
		opts     []CallOption
		validate func(*testing.T, *CallOptions)
	}{
		{
			name: "WithTemperature",
			opts: []CallOption{WithTemperature(0.7)},
			validate: func(t *testing.T, opts *CallOptions) {
				if opts.Temperature == nil {
					t.Fatal("Temperature should not be nil")
				}
				if *opts.Temperature != 0.7 {
					t.Errorf("Expected temperature 0.7, got %f", *opts.Temperature)
				}
			},
		},
		{
			name: "WithMaxTokens",
			opts: []CallOption{WithMaxTokens(1024)},
			validate: func(t *testing.T, opts *CallOptions) {
				if opts.MaxTokens == nil {
					t.Fatal("MaxTokens should not be nil")
				}
				if *opts.MaxTokens != 1024 {
					t.Errorf("Expected max_tokens 1024, got %d", *opts.MaxTokens)
				}
			},
		},
		{
			name: "WithTopP",
			opts: []CallOption{WithTopP(0.9)},
			validate: func(t *testing.T, opts *CallOptions) {
				if opts.TopP == nil {
					t.Fatal("TopP should not be nil")
				}
				if *opts.TopP != 0.9 {
					t.Errorf("Expected top_p 0.9, got %f", *opts.TopP)
				}
			},
		},
		{
			name: "WithExtra",
			opts: []CallOption{WithExtra("custom", "value")},
			validate: func(t *testing.T, opts *CallOptions) {
				if opts.Extra == nil {
					t.Fatal("Extra should not be nil")
				}
				val, ok := opts.Extra["custom"]
				if !ok {
					t.Fatal("Extra should contain 'custom' key")
				}
				if val != "value" {
					t.Errorf("Expected extra value 'value', got %v", val)
				}
			},
		},
		{
			name: "Multiple options",
			opts: []CallOption{
				WithTemperature(0.5),
				WithMaxTokens(2048),
				WithTopP(0.95),
				WithExtra("stop", []string{"END"}),
			},
			validate: func(t *testing.T, opts *CallOptions) {
				if opts.Temperature == nil || *opts.Temperature != 0.5 {
					t.Error("Temperature not set correctly")
				}
				if opts.MaxTokens == nil || *opts.MaxTokens != 2048 {
					t.Error("MaxTokens not set correctly")
				}
				if opts.TopP == nil || *opts.TopP != 0.95 {
					t.Error("TopP not set correctly")
				}
				if opts.Extra["stop"] == nil {
					t.Error("Extra 'stop' not set")
				}
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			opts := BuildCallOptions(tt.opts...)
			tt.validate(t, opts)
		})
	}
}

// MockLLM is a mock implementation for testing.
type MockLLM struct {
	model             string
	completeFunc      func(context.Context, []*agenkit.Message, ...CallOption) (*agenkit.Message, error)
	streamFunc        func(context.Context, []*agenkit.Message, ...CallOption) (<-chan *agenkit.Message, error)
}

func (m *MockLLM) Complete(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (*agenkit.Message, error) {
	if m.completeFunc != nil {
		return m.completeFunc(ctx, messages, opts...)
	}
	return agenkit.NewMessage("agent", "mock response"), nil
}

func (m *MockLLM) Stream(ctx context.Context, messages []*agenkit.Message, opts ...CallOption) (<-chan *agenkit.Message, error) {
	if m.streamFunc != nil {
		return m.streamFunc(ctx, messages, opts...)
	}
	ch := make(chan *agenkit.Message)
	go func() {
		defer close(ch)
		ch <- agenkit.NewMessage("agent", "mock")
		ch <- agenkit.NewMessage("agent", " response")
	}()
	return ch, nil
}

func (m *MockLLM) Model() string {
	return m.model
}

func (m *MockLLM) Unwrap() interface{} {
	return m
}

// TestMockLLM tests the mock implementation.
func TestMockLLM(t *testing.T) {
	mock := &MockLLM{model: "mock-model"}
	ctx := context.Background()

	t.Run("Complete", func(t *testing.T) {
		messages := []*agenkit.Message{
			agenkit.NewMessage("user", "test"),
		}
		response, err := mock.Complete(ctx, messages)
		if err != nil {
			t.Fatalf("Unexpected error: %v", err)
		}
		if response.Content != "mock response" {
			t.Errorf("Expected 'mock response', got %s", response.Content)
		}
	})

	t.Run("Stream", func(t *testing.T) {
		messages := []*agenkit.Message{
			agenkit.NewMessage("user", "test"),
		}
		stream, err := mock.Stream(ctx, messages)
		if err != nil {
			t.Fatalf("Unexpected error: %v", err)
		}

		var content string
		for chunk := range stream {
			content += chunk.Content
		}

		if content != "mock response" {
			t.Errorf("Expected 'mock response', got %s", content)
		}
	})

	t.Run("Model", func(t *testing.T) {
		if mock.Model() != "mock-model" {
			t.Errorf("Expected 'mock-model', got %s", mock.Model())
		}
	})

	t.Run("Unwrap", func(t *testing.T) {
		unwrapped := mock.Unwrap()
		if unwrapped != mock {
			t.Error("Unwrap should return the mock itself")
		}
	})
}

// TestLLMInterface verifies that concrete implementations satisfy the interface.
func TestLLMInterface(t *testing.T) {
	// This test ensures that our types implement the LLM interface
	var _ LLM = &MockLLM{}
	var _ LLM = &OpenAILLM{}
	var _ LLM = &AnthropicLLM{}
}
