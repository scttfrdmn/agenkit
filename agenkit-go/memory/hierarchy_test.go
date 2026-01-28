package memory

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

func TestHierarchyMemoryBasic(t *testing.T) {
	ctx := context.Background()
	memory, err := NewDefaultHierarchyMemory()
	if err != nil {
		t.Fatalf("Failed to create memory: %v", err)
	}

	// Test Store
	msg1 := agenkit.Message{Role: "user", Content: "Hello"}
	err = memory.Store(ctx, "session-1", msg1, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	msg2 := agenkit.Message{Role: "assistant", Content: "Hi there"}
	err = memory.Store(ctx, "session-1", msg2, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// Test Retrieve
	limit := 10
	messages, err := memory.Retrieve(ctx, "session-1", RetrieveOptions{Limit: &limit})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	if len(messages) != 2 {
		t.Errorf("Expected 2 messages, got %d", len(messages))
	}

	// Check both messages are present
	foundHello := false
	foundHi := false
	for _, msg := range messages {
		if msg.Content == "Hello" {
			foundHello = true
		}
		if msg.Content == "Hi there" {
			foundHi = true
		}
	}

	if !foundHello || !foundHi {
		t.Errorf("Not all messages retrieved correctly")
	}
}

func TestHierarchyMemorySessionIsolation(t *testing.T) {
	ctx := context.Background()
	memory, err := NewDefaultHierarchyMemory()
	if err != nil {
		t.Fatalf("Failed to create memory: %v", err)
	}

	// Store in different sessions
	msg1 := agenkit.Message{Role: "user", Content: "Session 1 message"}
	err = memory.Store(ctx, "session-1", msg1, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	msg2 := agenkit.Message{Role: "user", Content: "Session 2 message"}
	err = memory.Store(ctx, "session-2", msg2, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// Retrieve session 1
	limit := 10
	messages1, err := memory.Retrieve(ctx, "session-1", RetrieveOptions{Limit: &limit})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	if len(messages1) != 1 {
		t.Errorf("Expected 1 message in session-1, got %d", len(messages1))
	}

	if messages1[0].Content != "Session 1 message" {
		t.Errorf("Expected 'Session 1 message', got '%s'", messages1[0].Content)
	}

	// Retrieve session 2
	limit = 10
	messages2, err := memory.Retrieve(ctx, "session-2", RetrieveOptions{Limit: &limit})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	if len(messages2) != 1 {
		t.Errorf("Expected 1 message in session-2, got %d", len(messages2))
	}

	if messages2[0].Content != "Session 2 message" {
		t.Errorf("Expected 'Session 2 message', got '%s'", messages2[0].Content)
	}
}

func TestHierarchyMemoryImportanceRouting(t *testing.T) {
	ctx := context.Background()
	config := HierarchyConfig{
		WorkingCapacity:       5,
		ShortTermCapacity:     10,
		ShortTermTTLSeconds:   3600,
		LongTermMinImportance: 0.7,
		EnableLongTerm:        true,
	}
	memory, err := NewHierarchyMemory(config)
	if err != nil {
		t.Fatalf("Failed to create memory: %v", err)
	}

	// Store low importance (working + short-term only)
	msg1 := agenkit.Message{Role: "system", Content: "Low importance"}
	err = memory.Store(ctx, "session-1", msg1, map[string]interface{}{"importance": 0.3})
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// Store medium importance (working + short-term only)
	msg2 := agenkit.Message{Role: "user", Content: "Medium importance"}
	err = memory.Store(ctx, "session-1", msg2, map[string]interface{}{"importance": 0.5})
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// Store high importance (all tiers including long-term)
	msg3 := agenkit.Message{Role: "user", Content: "High importance"}
	err = memory.Store(ctx, "session-1", msg3, map[string]interface{}{"importance": 0.9})
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// All should be retrievable
	limit := 10
	messages, err := memory.Retrieve(ctx, "session-1", RetrieveOptions{Limit: &limit})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	if len(messages) != 3 {
		t.Errorf("Expected 3 messages, got %d", len(messages))
	}

	// Check stats to verify tier distribution
	stats := memory.GetStats()
	workingStats, _ := stats["working"].(map[string]interface{})
	shortTermStats, _ := stats["short_term"].(map[string]interface{})
	longTermStats, _ := stats["long_term"].(map[string]interface{})

	if workingStats["size"].(int) != 3 {
		t.Errorf("Expected 3 entries in working memory, got %d", workingStats["size"])
	}

	if shortTermStats["size"].(int) != 3 {
		t.Errorf("Expected 3 entries in short-term memory, got %d", shortTermStats["size"])
	}

	if longTermStats["size"].(int) != 1 {
		t.Errorf("Expected 1 entry in long-term memory, got %d", longTermStats["size"])
	}
}

func TestHierarchyMemoryDefaultImportance(t *testing.T) {
	ctx := context.Background()
	config := HierarchyConfig{
		WorkingCapacity:       10,
		ShortTermCapacity:     100,
		ShortTermTTLSeconds:   3600,
		LongTermMinImportance: 0.7,
		EnableLongTerm:        true,
	}
	memory, err := NewHierarchyMemory(config)
	if err != nil {
		t.Fatalf("Failed to create memory: %v", err)
	}

	// System: 0.3 (not in long-term)
	msg1 := agenkit.Message{Role: "system", Content: "System message"}
	err = memory.Store(ctx, "session-1", msg1, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// User: 0.5 (not in long-term)
	msg2 := agenkit.Message{Role: "user", Content: "User message"}
	err = memory.Store(ctx, "session-1", msg2, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// Assistant: 0.4 (not in long-term)
	msg3 := agenkit.Message{Role: "assistant", Content: "Assistant message"}
	err = memory.Store(ctx, "session-1", msg3, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// None should reach long-term (threshold is 0.7)
	stats := memory.GetStats()
	longTermStats, _ := stats["long_term"].(map[string]interface{})

	if longTermStats["size"].(int) != 0 {
		t.Errorf("Expected 0 entries in long-term memory, got %d", longTermStats["size"])
	}
}

func TestHierarchyMemoryClear(t *testing.T) {
	ctx := context.Background()
	memory, err := NewDefaultHierarchyMemory()
	if err != nil {
		t.Fatalf("Failed to create memory: %v", err)
	}

	// Store messages in two sessions
	msg1 := agenkit.Message{Role: "user", Content: "Session 1 msg 1"}
	err = memory.Store(ctx, "session-1", msg1, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	msg2 := agenkit.Message{Role: "user", Content: "Session 1 msg 2"}
	err = memory.Store(ctx, "session-1", msg2, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	msg3 := agenkit.Message{Role: "user", Content: "Session 2 msg 1"}
	err = memory.Store(ctx, "session-2", msg3, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// Clear session 1
	err = memory.Clear(ctx, "session-1")
	if err != nil {
		t.Fatalf("Clear failed: %v", err)
	}

	// Session 1 should be empty
	limit := 10
	messages1, err := memory.Retrieve(ctx, "session-1", RetrieveOptions{Limit: &limit})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	if len(messages1) != 0 {
		t.Errorf("Expected 0 messages in session-1 after clear, got %d", len(messages1))
	}

	// Session 2 should still have messages
	limit = 10
	messages2, err := memory.Retrieve(ctx, "session-2", RetrieveOptions{Limit: &limit})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	if len(messages2) != 1 {
		t.Errorf("Expected 1 message in session-2, got %d", len(messages2))
	}
}

func TestHierarchyMemoryImportanceFilter(t *testing.T) {
	ctx := context.Background()
	memory, err := NewDefaultHierarchyMemory()
	if err != nil {
		t.Fatalf("Failed to create memory: %v", err)
	}

	// Store messages with different importance
	msg1 := agenkit.Message{Role: "user", Content: "Low importance"}
	err = memory.Store(ctx, "session-1", msg1, map[string]interface{}{"importance": 0.3})
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	msg2 := agenkit.Message{Role: "user", Content: "High importance"}
	err = memory.Store(ctx, "session-1", msg2, map[string]interface{}{"importance": 0.9})
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// Filter by importance
	threshold := 0.5
	limit := 10
	messages, err := memory.Retrieve(ctx, "session-1", RetrieveOptions{
		Limit:               &limit,
		ImportanceThreshold: &threshold,
	})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	if len(messages) != 1 {
		t.Errorf("Expected 1 message with importance >= 0.5, got %d", len(messages))
	}

	if messages[0].Content != "High importance" {
		t.Errorf("Expected 'High importance', got '%s'", messages[0].Content)
	}
}

func TestHierarchyMemoryTagsFilter(t *testing.T) {
	ctx := context.Background()
	memory, err := NewDefaultHierarchyMemory()
	if err != nil {
		t.Fatalf("Failed to create memory: %v", err)
	}

	// Store messages with different tags
	msg1 := agenkit.Message{Role: "user", Content: "Tagged message"}
	err = memory.Store(ctx, "session-1", msg1, map[string]interface{}{
		"tags": []interface{}{"important", "urgent"},
	})
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	msg2 := agenkit.Message{Role: "user", Content: "Untagged message"}
	err = memory.Store(ctx, "session-1", msg2, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// Filter by tags
	limit := 10
	messages, err := memory.Retrieve(ctx, "session-1", RetrieveOptions{
		Limit: &limit,
		Tags:  []string{"important"},
	})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	if len(messages) != 1 {
		t.Errorf("Expected 1 message with tag 'important', got %d", len(messages))
	}

	if messages[0].Content != "Tagged message" {
		t.Errorf("Expected 'Tagged message', got '%s'", messages[0].Content)
	}
}

func TestHierarchyMemoryTimeRangeFilter(t *testing.T) {
	ctx := context.Background()
	memory, err := NewDefaultHierarchyMemory()
	if err != nil {
		t.Fatalf("Failed to create memory: %v", err)
	}

	// Store messages with specific timestamps
	now := time.Now()
	past := now.Add(-2 * time.Hour)

	msg1 := agenkit.Message{Role: "user", Content: "Old message", Timestamp: past}
	err = memory.Store(ctx, "session-1", msg1, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	msg2 := agenkit.Message{Role: "user", Content: "Recent message", Timestamp: now}
	err = memory.Store(ctx, "session-1", msg2, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// Filter by time range
	startTime := now.Add(-1 * time.Hour).Unix()
	endTime := now.Add(1 * time.Hour).Unix()

	limit := 10
	messages, err := memory.Retrieve(ctx, "session-1", RetrieveOptions{
		Limit: &limit,
		TimeRange: &TimeRange{
			Start: startTime,
			End:   endTime,
		},
	})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	// Should only get recent message
	if len(messages) != 1 {
		t.Errorf("Expected 1 message in time range, got %d", len(messages))
	}

	if len(messages) > 0 && messages[0].Content != "Recent message" {
		t.Errorf("Expected 'Recent message', got '%s'", messages[0].Content)
	}
}

func TestHierarchyMemorySummarize(t *testing.T) {
	ctx := context.Background()
	memory, err := NewDefaultHierarchyMemory()
	if err != nil {
		t.Fatalf("Failed to create memory: %v", err)
	}

	// Store several messages
	msg1 := agenkit.Message{Role: "user", Content: "Hello"}
	memory.Store(ctx, "session-1", msg1, nil)

	msg2 := agenkit.Message{Role: "assistant", Content: "Hi there!"}
	memory.Store(ctx, "session-1", msg2, nil)

	msg3 := agenkit.Message{Role: "user", Content: "How are you?"}
	memory.Store(ctx, "session-1", msg3, nil)

	// Get summary
	summary, err := memory.Summarize(ctx, "session-1", SummarizeOptions{})
	if err != nil {
		t.Fatalf("Summarize failed: %v", err)
	}

	if summary.Role != "system" {
		t.Errorf("Expected role 'system', got '%s'", summary.Role)
	}

	// Content is already a string in Go agenkit.Message
	summaryStr := summary.Content

	if !strings.Contains(strings.ToLower(summaryStr), "summary") {
		t.Errorf("Expected summary to contain 'summary', got: %s", summaryStr)
	}

	if !strings.Contains(summaryStr, "3 messages") {
		t.Errorf("Expected summary to mention 3 messages, got: %s", summaryStr)
	}
}

func TestHierarchyMemoryCapabilities(t *testing.T) {
	memory, err := NewDefaultHierarchyMemory()
	if err != nil {
		t.Fatalf("Failed to create memory: %v", err)
	}

	capabilities := memory.Capabilities()

	expectedCapabilities := []string{
		"semantic_search",
		"importance_filtering",
		"tag_filtering",
		"time_filtering",
		"multi_tier",
		"auto_eviction",
	}

	for _, expected := range expectedCapabilities {
		found := false
		for _, cap := range capabilities {
			if cap == expected {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Expected capability '%s' not found", expected)
		}
	}
}

func TestHierarchyMemoryInvalidConfig(t *testing.T) {
	tests := []struct {
		name   string
		config HierarchyConfig
	}{
		{
			name: "InvalidWorkingCapacity",
			config: HierarchyConfig{
				WorkingCapacity:       0,
				ShortTermCapacity:     100,
				ShortTermTTLSeconds:   3600,
				LongTermMinImportance: 0.7,
			},
		},
		{
			name: "InvalidShortTermCapacity",
			config: HierarchyConfig{
				WorkingCapacity:       10,
				ShortTermCapacity:     0,
				ShortTermTTLSeconds:   3600,
				LongTermMinImportance: 0.7,
			},
		},
		{
			name: "InvalidTTL",
			config: HierarchyConfig{
				WorkingCapacity:       10,
				ShortTermCapacity:     100,
				ShortTermTTLSeconds:   0,
				LongTermMinImportance: 0.7,
			},
		},
		{
			name: "InvalidImportance",
			config: HierarchyConfig{
				WorkingCapacity:       10,
				ShortTermCapacity:     100,
				ShortTermTTLSeconds:   3600,
				LongTermMinImportance: 1.5,
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := NewHierarchyMemory(tt.config)
			if err == nil {
				t.Errorf("Expected error for %s, got nil", tt.name)
			}
		})
	}
}

func TestHierarchyMemoryInterface(t *testing.T) {
	// Verify HierarchyMemory implements Memory interface
	var _ Memory = (*HierarchyMemory)(nil)
}
