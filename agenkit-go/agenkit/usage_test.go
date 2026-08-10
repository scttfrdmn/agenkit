package agenkit

import "testing"

// These round-trip the two shapes #664 was filed about: Bedrock's usage map
// stores token counts as int32 (via aws.ToInt32), while Ollama's derived
// usage map (agenkit-go/adapter/llm/ollama.go) stores plain int. Usage lives
// here in the core package (moved from adapter/llm in #782 so observability
// can depend on it without the AWS SDK); this test is the negative-verification
// case for that move — it must still normalize both provider shapes correctly
// after the move, not just compile.

func TestUsageFromMessage_BedrockInt32Shape(t *testing.T) {
	msg := NewMessage("agent", "hi")
	msg.Metadata["usage"] = map[string]interface{}{
		"prompt_tokens":         int32(1000),
		"completion_tokens":     int32(50),
		"total_tokens":          int32(1050),
		"cache_read_tokens":     int32(900),
		"cache_creation_tokens": int32(100),
	}

	got, ok := UsageFromMessage(msg)
	if !ok {
		t.Fatal("UsageFromMessage returned ok=false for a message with usage metadata")
	}

	want := Usage{
		PromptTokens:        1000,
		CompletionTokens:    50,
		TotalTokens:         1050,
		CacheReadTokens:     900,
		CacheCreationTokens: 100,
	}
	if got != want {
		t.Errorf("Usage = %+v, want %+v", got, want)
	}
}

func TestUsageFromMessage_OllamaIntShape(t *testing.T) {
	msg := NewMessage("agent", "hi")
	// Ollama's adapter derives this from plain Go ints
	// (PromptEvalCount/EvalCount), no total_tokens key, so it must be derived.
	msg.Metadata["usage"] = map[string]interface{}{
		"prompt_tokens":     42,
		"completion_tokens": 8,
		"total_tokens":      50,
	}

	got, ok := UsageFromMessage(msg)
	if !ok {
		t.Fatal("UsageFromMessage returned ok=false for a message with usage metadata")
	}

	want := Usage{PromptTokens: 42, CompletionTokens: 8, TotalTokens: 50}
	if got != want {
		t.Errorf("Usage = %+v, want %+v", got, want)
	}
}

func TestUsageFromMessage_NoUsageMetadata(t *testing.T) {
	msg := NewMessage("agent", "hi")
	if _, ok := UsageFromMessage(msg); ok {
		t.Error("expected ok=false for a message with no usage metadata")
	}
	if _, ok := UsageFromMessage(nil); ok {
		t.Error("expected ok=false for a nil message")
	}
}
