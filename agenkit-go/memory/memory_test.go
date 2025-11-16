package memory

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

func TestInMemoryMemory(t *testing.T) {
	ctx := context.Background()
	memory := NewInMemoryMemory(100)

	// Test Store
	msg1 := agenkit.Message{Role: "user", Content: "Hello"}
	err := memory.Store(ctx, "session-1", msg1, nil)
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	msg2 := agenkit.Message{Role: "assistant", Content: "Hi there"}
	err = memory.Store(ctx, "session-1", msg2, map[string]interface{}{"importance": 0.8})
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// Test Retrieve
	messages, err := memory.Retrieve(ctx, "session-1", RetrieveOptions{Limit: 10})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	if len(messages) != 2 {
		t.Errorf("Expected 2 messages, got %d", len(messages))
	}

	// Should be most recent first
	if messages[0].Content != "Hi there" {
		t.Errorf("Expected 'Hi there', got '%s'", messages[0].Content)
	}

	// Test GetSessionCount
	count := memory.GetSessionCount("session-1")
	if count != 2 {
		t.Errorf("Expected count 2, got %d", count)
	}

	// Test Clear
	err = memory.Clear(ctx, "session-1")
	if err != nil {
		t.Fatalf("Clear failed: %v", err)
	}

	messages, err = memory.Retrieve(ctx, "session-1", RetrieveOptions{Limit: 10})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	if len(messages) != 0 {
		t.Errorf("Expected 0 messages after clear, got %d", len(messages))
	}
}

func TestInMemoryMemoryFiltering(t *testing.T) {
	ctx := context.Background()
	memory := NewInMemoryMemory(100)

	// Store messages with different importance
	msg1 := agenkit.Message{Role: "user", Content: "Low importance"}
	err := memory.Store(ctx, "session-1", msg1, map[string]interface{}{"importance": 0.3})
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	msg2 := agenkit.Message{Role: "user", Content: "High importance"}
	err = memory.Store(ctx, "session-1", msg2, map[string]interface{}{"importance": 0.9})
	if err != nil {
		t.Fatalf("Store failed: %v", err)
	}

	// Test importance threshold filter
	threshold := 0.5
	messages, err := memory.Retrieve(ctx, "session-1", RetrieveOptions{
		Limit:               10,
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

func TestInMemoryMemoryLRU(t *testing.T) {
	ctx := context.Background()
	memory := NewInMemoryMemory(3) // Max 3 messages

	// Store 5 messages
	for i := 1; i <= 5; i++ {
		msg := agenkit.Message{Role: "user", Content: fmt.Sprintf("Message %d", i)}
		err := memory.Store(ctx, "session-1", msg, nil)
		if err != nil {
			t.Fatalf("Store failed: %v", err)
		}
	}

	// Should only have 3 most recent messages (3, 4, 5)
	count := memory.GetSessionCount("session-1")
	if count != 3 {
		t.Errorf("Expected count 3 after LRU eviction, got %d", count)
	}

	messages, err := memory.Retrieve(ctx, "session-1", RetrieveOptions{Limit: 10})
	if err != nil {
		t.Fatalf("Retrieve failed: %v", err)
	}

	// Should have messages 3, 4, 5 (most recent first)
	if len(messages) != 3 {
		t.Fatalf("Expected 3 messages, got %d", len(messages))
	}

	// Most recent first
	if messages[0].Content != "Message 5" {
		t.Errorf("Expected 'Message 5', got '%s'", messages[0].Content)
	}
}

func TestInMemoryMemorySummarize(t *testing.T) {
	ctx := context.Background()
	memory := NewInMemoryMemory(100)

	// Store some messages
	for i := 1; i <= 5; i++ {
		msg := agenkit.Message{Role: "user", Content: fmt.Sprintf("Message %d", i)}
		err := memory.Store(ctx, "session-1", msg, nil)
		if err != nil {
			t.Fatalf("Store failed: %v", err)
		}
	}

	// Test summarize
	summary, err := memory.Summarize(ctx, "session-1", SummarizeOptions{})
	if err != nil {
		t.Fatalf("Summarize failed: %v", err)
	}

	if summary.Role != "system" {
		t.Errorf("Expected role 'system', got '%s'", summary.Role)
	}

	if !strings.Contains(summary.Content, "Session summary") {
		t.Errorf("Expected summary to contain 'Session summary', got: %s", summary.Content)
	}
}

func TestInMemoryMemoryCapabilities(t *testing.T) {
	memory := NewInMemoryMemory(100)

	caps := memory.Capabilities()
	expectedCaps := []string{
		"basic_retrieval",
		"time_filtering",
		"importance_filtering",
		"tag_filtering",
	}

	if len(caps) != len(expectedCaps) {
		t.Errorf("Expected %d capabilities, got %d", len(expectedCaps), len(caps))
	}

	for _, expected := range expectedCaps {
		found := false
		for _, cap := range caps {
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

func TestInMemoryMemoryGetMemoryUsage(t *testing.T) {
	ctx := context.Background()
	memory := NewInMemoryMemory(100)

	// Store messages in multiple sessions
	for i := 1; i <= 3; i++ {
		sessionID := fmt.Sprintf("session-%d", i)
		for j := 1; j <= 5; j++ {
			msg := agenkit.Message{Role: "user", Content: fmt.Sprintf("Message %d", j)}
			err := memory.Store(ctx, sessionID, msg, nil)
			if err != nil {
				t.Fatalf("Store failed: %v", err)
			}
		}
	}

	usage := memory.GetMemoryUsage()

	totalSessions, ok := usage["total_sessions"].(int)
	if !ok || totalSessions != 3 {
		t.Errorf("Expected 3 sessions, got %v", usage["total_sessions"])
	}

	totalMessages, ok := usage["total_messages"].(int)
	if !ok || totalMessages != 15 {
		t.Errorf("Expected 15 messages, got %v", usage["total_messages"])
	}
}

