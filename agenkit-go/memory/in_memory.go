package memory

import (
	"context"
	"fmt"
	"sort"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// InMemoryMemory provides simple in-memory storage with LRU eviction.
//
// Features:
//   - Fast access (no I/O)
//   - LRU eviction when max_size reached
//   - Per-session storage
//   - Optional metadata support
//
// Limitations:
//   - No persistence (data lost on restart)
//   - No semantic search
//   - Memory limited
//
// Use cases:
//   - Testing
//   - Simple applications
//   - Prototypes
//   - When persistence not needed
//
// Example:
//
//	memory := NewInMemoryMemory(1000)
//	err := memory.Store(ctx, "session-123", message, nil)
//	messages, err := memory.Retrieve(ctx, "session-123", RetrieveOptions{Limit: 10})
type InMemoryMemory struct {
	maxSize int
	mu      sync.RWMutex
	// sessionID -> list of messages with metadata
	storage map[string][]MessageWithMetadata
	// Counter to ensure unique ordering even for same-timestamp messages
	counter int64
}

// NewInMemoryMemory creates a new in-memory memory instance.
//
// Args:
//
//	maxSize: Maximum number of messages to store per session before LRU eviction
//
// Example:
//
//	memory := NewInMemoryMemory(1000)
func NewInMemoryMemory(maxSize int) *InMemoryMemory {
	return &InMemoryMemory{
		maxSize: maxSize,
		storage: make(map[string][]MessageWithMetadata),
		counter: 0,
	}
}

// Store saves a message to memory with optional metadata.
func (m *InMemoryMemory) Store(ctx context.Context, sessionID string, message agenkit.Message, metadata map[string]interface{}) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	// Initialize session storage if needed
	if _, exists := m.storage[sessionID]; !exists {
		m.storage[sessionID] = make([]MessageWithMetadata, 0)
	}

	// Add message with timestamp (use counter to ensure unique ordering)
	timestamp := float64(time.Now().UnixNano()) / 1e9
	timestamp += float64(m.counter) * 0.000001
	m.counter++

	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	m.storage[sessionID] = append(m.storage[sessionID], MessageWithMetadata{
		Timestamp: timestamp,
		Message:   message,
		Metadata:  metadata,
	})

	// LRU eviction if over limit
	if len(m.storage[sessionID]) > m.maxSize {
		// Remove oldest (first item in slice)
		m.storage[sessionID] = m.storage[sessionID][1:]
	}

	return nil
}

// Retrieve fetches messages from memory.
//
// Supports filtering by:
//   - TimeRange: Filter by time range
//   - ImportanceThreshold: Filter by importance score (requires metadata with "importance")
//   - Tags: Filter by tags (requires metadata with "tags")
func (m *InMemoryMemory) Retrieve(ctx context.Context, sessionID string, opts RetrieveOptions) ([]agenkit.Message, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	sessionStorage, exists := m.storage[sessionID]
	if !exists {
		return []agenkit.Message{}, nil
	}

	// Set default limit
	limit := opts.Limit
	if limit <= 0 {
		limit = 10
	}

	// Get all messages (most recent first)
	messagesWithMetadata := make([]MessageWithMetadata, len(sessionStorage))
	copy(messagesWithMetadata, sessionStorage)

	// Reverse to get most recent first
	for i, j := 0, len(messagesWithMetadata)-1; i < j; i, j = i+1, j-1 {
		messagesWithMetadata[i], messagesWithMetadata[j] = messagesWithMetadata[j], messagesWithMetadata[i]
	}

	// Apply filters
	filtered := make([]agenkit.Message, 0)
	for _, item := range messagesWithMetadata {
		// Time range filter
		if opts.TimeRange != nil {
			msgTime := int64(item.Timestamp)
			if msgTime < opts.TimeRange.Start || msgTime > opts.TimeRange.End {
				continue
			}
		}

		// Importance threshold filter
		if opts.ImportanceThreshold != nil {
			importance := 0.0
			if val, ok := item.Metadata["importance"]; ok {
				if f, ok := val.(float64); ok {
					importance = f
				}
			}
			if importance < *opts.ImportanceThreshold {
				continue
			}
		}

		// Tags filter
		if len(opts.Tags) > 0 {
			requiredTags := make(map[string]bool)
			for _, tag := range opts.Tags {
				requiredTags[tag] = true
			}

			messageTags := make(map[string]bool)
			if val, ok := item.Metadata["tags"]; ok {
				if tags, ok := val.([]string); ok {
					for _, tag := range tags {
						messageTags[tag] = true
					}
				} else if tags, ok := val.([]interface{}); ok {
					for _, tag := range tags {
						if str, ok := tag.(string); ok {
							messageTags[str] = true
						}
					}
				}
			}

			// Check if any required tag exists in message tags
			hasTag := false
			for tag := range requiredTags {
				if messageTags[tag] {
					hasTag = true
					break
				}
			}
			if !hasTag {
				continue
			}
		}

		filtered = append(filtered, item.Message)

		// Stop if we have enough
		if len(filtered) >= limit {
			break
		}
	}

	// Return up to limit
	if len(filtered) > limit {
		filtered = filtered[:limit]
	}

	return filtered, nil
}

// Summarize creates a summary of conversation history.
//
// Simple implementation: Returns a message with concatenated content.
// Production use should use LLM-based summarization.
func (m *InMemoryMemory) Summarize(ctx context.Context, sessionID string, opts SummarizeOptions) (agenkit.Message, error) {
	messages, err := m.Retrieve(ctx, sessionID, RetrieveOptions{Limit: 100})
	if err != nil {
		return agenkit.Message{}, err
	}

	if len(messages) == 0 {
		return agenkit.Message{
			Role:    "system",
			Content: "No messages in session.",
		}, nil
	}

	// Simple concatenation summary
	summaryParts := make([]string, 0)
	maxMessages := 10
	if len(messages) < maxMessages {
		maxMessages = len(messages)
	}

	for i := 0; i < maxMessages; i++ {
		msg := messages[i]
		preview := msg.Content
		if len(preview) > 100 {
			preview = preview[:100] + "..."
		}
		summaryParts = append(summaryParts, fmt.Sprintf("%d. [%s] %s", i+1, msg.Role, preview))
	}

	summaryContent := fmt.Sprintf("Session summary (%d messages):\n", len(messages))
	for _, part := range summaryParts {
		summaryContent += part + "\n"
	}

	return agenkit.Message{
		Role:    "system",
		Content: summaryContent,
	}, nil
}

// Clear removes all memory for a session.
func (m *InMemoryMemory) Clear(ctx context.Context, sessionID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	delete(m.storage, sessionID)
	return nil
}

// Capabilities returns the memory capabilities.
func (m *InMemoryMemory) Capabilities() []string {
	return []string{
		"basic_retrieval",
		"time_filtering",
		"importance_filtering",
		"tag_filtering",
	}
}

// Additional utility methods

// GetSessionCount returns the number of messages stored for a session.
func (m *InMemoryMemory) GetSessionCount(sessionID string) int {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if storage, exists := m.storage[sessionID]; exists {
		return len(storage)
	}
	return 0
}

// GetAllSessions returns a list of all session IDs.
func (m *InMemoryMemory) GetAllSessions() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	sessions := make([]string, 0, len(m.storage))
	for sessionID := range m.storage {
		sessions = append(sessions, sessionID)
	}
	sort.Strings(sessions)
	return sessions
}

// GetMemoryUsage returns memory usage statistics.
func (m *InMemoryMemory) GetMemoryUsage() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	totalMessages := 0
	for _, storage := range m.storage {
		totalMessages += len(storage)
	}

	return map[string]interface{}{
		"total_sessions":        len(m.storage),
		"total_messages":        totalMessages,
		"max_size_per_session": m.maxSize,
	}
}
