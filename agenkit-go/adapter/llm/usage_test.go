package llm

import (
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

func msgWithUsage(usage map[string]interface{}) *agenkit.Message {
	m := agenkit.NewMessage("agent", "hi")
	if usage != nil {
		m.Metadata["usage"] = usage
	}
	return m
}

func TestUsageFromMessage(t *testing.T) {
	tests := []struct {
		name   string
		msg    *agenkit.Message
		wantOK bool
		want   Usage
	}{
		{
			name:   "nil message",
			msg:    nil,
			wantOK: false,
		},
		{
			name:   "no usage metadata",
			msg:    msgWithUsage(nil),
			wantOK: false,
		},
		{
			name: "openai-style prompt/completion, int",
			msg: msgWithUsage(map[string]interface{}{
				"prompt_tokens":     10,
				"completion_tokens": 5,
				"total_tokens":      15,
			}),
			wantOK: true,
			want:   Usage{PromptTokens: 10, CompletionTokens: 5, TotalTokens: 15},
		},
		{
			name: "bedrock-style int32",
			msg: msgWithUsage(map[string]interface{}{
				"prompt_tokens":     int32(100),
				"completion_tokens": int32(20),
				"total_tokens":      int32(120),
			}),
			wantOK: true,
			want:   Usage{PromptTokens: 100, CompletionTokens: 20, TotalTokens: 120},
		},
		{
			name: "anthropic-style input/output keys",
			msg: msgWithUsage(map[string]interface{}{
				"input_tokens":  30,
				"output_tokens": 7,
			}),
			wantOK: true,
			// total derived from prompt+completion when absent
			want: Usage{PromptTokens: 30, CompletionTokens: 7, TotalTokens: 37},
		},
		{
			name: "float64 values (JSON round-trip)",
			msg: msgWithUsage(map[string]interface{}{
				"prompt_tokens":     float64(8),
				"completion_tokens": float64(2),
			}),
			wantOK: true,
			want:   Usage{PromptTokens: 8, CompletionTokens: 2, TotalTokens: 10},
		},
		{
			name: "bedrock cache tokens (normalized keys)",
			msg: msgWithUsage(map[string]interface{}{
				"prompt_tokens":         int32(1000),
				"completion_tokens":     int32(50),
				"total_tokens":          int32(1050),
				"cache_read_tokens":     int32(900),
				"cache_creation_tokens": int32(100),
			}),
			wantOK: true,
			want: Usage{
				PromptTokens: 1000, CompletionTokens: 50, TotalTokens: 1050,
				CacheReadTokens: 900, CacheCreationTokens: 100,
			},
		},
		{
			name: "raw provider cache key aliases",
			msg: msgWithUsage(map[string]interface{}{
				"input_tokens":                20,
				"output_tokens":               4,
				"cache_read_input_tokens":     15,
				"cache_creation_input_tokens": 5,
			}),
			wantOK: true,
			want: Usage{
				PromptTokens: 20, CompletionTokens: 4, TotalTokens: 24,
				CacheReadTokens: 15, CacheCreationTokens: 5,
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := UsageFromMessage(tt.msg)
			if ok != tt.wantOK {
				t.Fatalf("ok = %v, want %v", ok, tt.wantOK)
			}
			if !tt.wantOK {
				return
			}
			if got != tt.want {
				t.Errorf("Usage = %+v, want %+v", got, tt.want)
			}
		})
	}
}
