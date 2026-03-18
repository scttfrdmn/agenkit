package llm

import (
	"testing"
)

// TestSGLangLLMInterface verifies that SGLangLLM implements the LLM interface.
func TestSGLangLLMInterface(t *testing.T) {
	var _ LLM = &SGLangLLM{}
}

// TestNewSGLangLLM_DefaultBaseURL tests that an empty baseURL uses the SGLang default.
func TestNewSGLangLLM_DefaultBaseURL(t *testing.T) {
	l := NewSGLangLLM("test-model", "")
	if l.baseURL != "http://localhost:30000/v1" {
		t.Errorf("expected default baseURL %q, got %q", "http://localhost:30000/v1", l.baseURL)
	}
}

// TestNewSGLangLLM_CustomBaseURL tests that a custom baseURL is preserved.
func TestNewSGLangLLM_CustomBaseURL(t *testing.T) {
	custom := "http://gpu-host:30000/v1"
	l := NewSGLangLLM("test-model", custom)
	if l.baseURL != custom {
		t.Errorf("expected baseURL %q, got %q", custom, l.baseURL)
	}
}

// TestNewSGLangLLM_Model tests that the model name is stored correctly.
func TestNewSGLangLLM_Model(t *testing.T) {
	l := NewSGLangLLM("test-model", "")
	if l.Model() != "test-model" {
		t.Errorf("expected model %q, got %q", "test-model", l.Model())
	}
}

// TestNewSGLangLLM_ProviderName tests that the provider is set to "sglang".
func TestNewSGLangLLM_ProviderName(t *testing.T) {
	l := NewSGLangLLM("test-model", "")
	if l.provider != "sglang" {
		t.Errorf("expected provider %q, got %q", "sglang", l.provider)
	}
}

// TestNewSGLangLLM_Unwrap tests that Unwrap returns a non-nil client.
func TestNewSGLangLLM_Unwrap(t *testing.T) {
	l := NewSGLangLLM("test-model", "")
	if l.Unwrap() == nil {
		t.Error("Unwrap() should not return nil")
	}
}

// TestWithSGLangJSONSchema tests that the json_schema option is set correctly.
func TestWithSGLangJSONSchema(t *testing.T) {
	schema := `{"type":"object","properties":{"answer":{"type":"string"}}}`
	opts := BuildCallOptions(WithSGLangJSONSchema(schema))
	got, ok := opts.Extra["json_schema"].(string)
	if !ok {
		t.Fatalf("json_schema should be string, got %T", opts.Extra["json_schema"])
	}
	if got != schema {
		t.Errorf("expected schema %q, got %q", schema, got)
	}
}

// TestWithSGLangRegex tests that the regex option is set correctly.
func TestWithSGLangRegex(t *testing.T) {
	pattern := `[A-Za-z ,.'!?]+`
	opts := BuildCallOptions(WithSGLangRegex(pattern))
	got, ok := opts.Extra["regex"].(string)
	if !ok {
		t.Fatalf("regex should be string, got %T", opts.Extra["regex"])
	}
	if got != pattern {
		t.Errorf("expected pattern %q, got %q", pattern, got)
	}
}
