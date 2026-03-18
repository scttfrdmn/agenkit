package llm

import (
	"testing"
)

// TestVllmLLMInterface verifies that VllmLLM implements the LLM interface.
func TestVllmLLMInterface(t *testing.T) {
	var _ LLM = &VllmLLM{}
}

// TestNewVllmLLM_DefaultBaseURL tests that an empty baseURL uses the vLLM default.
func TestNewVllmLLM_DefaultBaseURL(t *testing.T) {
	l := NewVllmLLM("test-model", "")
	if l.baseURL != "http://localhost:8000/v1" {
		t.Errorf("expected default baseURL %q, got %q", "http://localhost:8000/v1", l.baseURL)
	}
}

// TestNewVllmLLM_CustomBaseURL tests that a custom baseURL is preserved.
func TestNewVllmLLM_CustomBaseURL(t *testing.T) {
	custom := "http://gpu-host:8000/v1"
	l := NewVllmLLM("test-model", custom)
	if l.baseURL != custom {
		t.Errorf("expected baseURL %q, got %q", custom, l.baseURL)
	}
}

// TestNewVllmLLM_Model tests that the model name is stored correctly.
func TestNewVllmLLM_Model(t *testing.T) {
	l := NewVllmLLM("test-model", "")
	if l.Model() != "test-model" {
		t.Errorf("expected model %q, got %q", "test-model", l.Model())
	}
}

// TestNewVllmLLM_ProviderName tests that the provider is set to "vllm".
func TestNewVllmLLM_ProviderName(t *testing.T) {
	l := NewVllmLLM("test-model", "")
	if l.provider != "vllm" {
		t.Errorf("expected provider %q, got %q", "vllm", l.provider)
	}
}

// TestNewVllmLLM_Unwrap tests that Unwrap returns a non-nil client.
func TestNewVllmLLM_Unwrap(t *testing.T) {
	l := NewVllmLLM("test-model", "")
	if l.Unwrap() == nil {
		t.Error("Unwrap() should not return nil")
	}
}

// TestWithVllmGuidedJSON tests that the guided_json option is set correctly.
func TestWithVllmGuidedJSON(t *testing.T) {
	schema := map[string]interface{}{"type": "object"}
	opts := BuildCallOptions(WithVllmGuidedJSON(schema))
	if opts.Extra["guided_json"] == nil {
		t.Fatal("guided_json should be set")
	}
	got, ok := opts.Extra["guided_json"].(map[string]interface{})
	if !ok {
		t.Fatalf("guided_json should be map[string]interface{}, got %T", opts.Extra["guided_json"])
	}
	if got["type"] != "object" {
		t.Errorf("expected type %q, got %q", "object", got["type"])
	}
}

// TestWithVllmGuidedRegex tests that the guided_regex option is set correctly.
func TestWithVllmGuidedRegex(t *testing.T) {
	pattern := `[A-Za-z ,.'!?]+`
	opts := BuildCallOptions(WithVllmGuidedRegex(pattern))
	got, ok := opts.Extra["guided_regex"].(string)
	if !ok {
		t.Fatalf("guided_regex should be string, got %T", opts.Extra["guided_regex"])
	}
	if got != pattern {
		t.Errorf("expected pattern %q, got %q", pattern, got)
	}
}
