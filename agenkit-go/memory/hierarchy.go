package memory

import (
	"context"
	"fmt"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// HierarchyMemory is a backward-compatible adapter wrapping MemoryHierarchy.
//
// Implements the session-based Memory interface while using the 3-tier
// hierarchy internally for improved performance and scalability.
//
// Benefits over InMemoryMemory:
//   - Automatic importance-based tier routing
//   - FIFO/LRU/TTL eviction strategies
//   - Better memory management for long sessions
//   - Semantic retrieval across tiers
//   - Proven architecture (used in Rust/C++/Zig/Python)
//
// Architecture:
//   - Working Memory: Current conversation (FIFO, 10-20 msgs)
//   - Short-Term Memory: Recent sessions (LRU+TTL, 100-1000 msgs)
//   - Long-Term Memory: Important facts (importance threshold, unlimited)
//
// Example:
//
//	memory, err := NewHierarchyMemory(HierarchyConfig{
//	    WorkingCapacity:        10,
//	    ShortTermCapacity:      100,
//	    ShortTermTTLSeconds:    3600,
//	    LongTermMinImportance:  0.7,
//	})
//	err = memory.Store(ctx, "session-123", message, nil)
//	limit := 10
//	messages, err := memory.Retrieve(ctx, "session-123", RetrieveOptions{Limit: &limit})
type HierarchyMemory struct {
	hierarchy *patterns.MemoryHierarchy
	config    HierarchyConfig
}

// HierarchyConfig contains configuration for HierarchyMemory.
type HierarchyConfig struct {
	// WorkingCapacity is the max messages in working memory (default: 10).
	// Increase for longer context windows.
	WorkingCapacity int

	// ShortTermCapacity is the max messages in short-term memory (default: 100).
	// Increase for longer session history.
	ShortTermCapacity int

	// ShortTermTTLSeconds is time-to-live for short-term entries (default: 3600 = 1 hour).
	// Increase to retain history longer.
	ShortTermTTLSeconds int

	// LongTermMinImportance is minimum importance for long-term storage (default: 0.7).
	// Lower to store more, higher for only critical info.
	LongTermMinImportance float64

	// EnableLongTerm enables long-term memory (default: true).
	// Disable for testing or simple use cases.
	EnableLongTerm bool
}

// DefaultHierarchyConfig returns the default hierarchy configuration.
func DefaultHierarchyConfig() HierarchyConfig {
	return HierarchyConfig{
		WorkingCapacity:       10,
		ShortTermCapacity:     100,
		ShortTermTTLSeconds:   3600,
		LongTermMinImportance: 0.7,
		EnableLongTerm:        true,
	}
}

// NewHierarchyMemory creates a new HierarchyMemory with the given configuration.
func NewHierarchyMemory(config HierarchyConfig) (*HierarchyMemory, error) {
	// Validate configuration
	if config.WorkingCapacity < 1 {
		return nil, fmt.Errorf("working capacity must be at least 1")
	}
	if config.ShortTermCapacity < 1 {
		return nil, fmt.Errorf("short-term capacity must be at least 1")
	}
	if config.ShortTermTTLSeconds < 1 {
		return nil, fmt.Errorf("short-term TTL must be at least 1 second")
	}
	if config.LongTermMinImportance < 0.0 || config.LongTermMinImportance > 1.0 {
		return nil, fmt.Errorf("long-term min importance must be between 0.0 and 1.0")
	}

	// Create hierarchy tiers
	working, err := patterns.NewWorkingMemory(config.WorkingCapacity)
	if err != nil {
		return nil, fmt.Errorf("failed to create working memory: %w", err)
	}

	shortTerm, err := patterns.NewShortTermMemory(
		config.ShortTermCapacity,
		config.ShortTermTTLSeconds,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create short-term memory: %w", err)
	}

	var longTerm *patterns.LongTermMemory
	if config.EnableLongTerm {
		longTerm, err = patterns.NewLongTermMemory(nil, nil, config.LongTermMinImportance)
		if err != nil {
			return nil, fmt.Errorf("failed to create long-term memory: %w", err)
		}
	}

	hierarchy := patterns.NewMemoryHierarchy(working, shortTerm, longTerm)

	return &HierarchyMemory{
		hierarchy: hierarchy,
		config:    config,
	}, nil
}

// NewDefaultHierarchyMemory creates a HierarchyMemory with default configuration.
func NewDefaultHierarchyMemory() (*HierarchyMemory, error) {
	return NewHierarchyMemory(DefaultHierarchyConfig())
}

// Store stores a message in the hierarchy with session association.
//
// Importance Routing:
//   - System messages: 0.3 (working + short-term only)
//   - User messages: 0.5 (working + short-term, possibly long-term)
//   - Assistant messages: 0.4 (working + short-term only)
//   - High importance (0.7+): Stored in long-term memory
//
// To control routing, pass importance in metadata:
//
//	metadata := map[string]interface{}{"importance": 0.9}
//	err := memory.Store(ctx, "session-123", message, metadata)
func (h *HierarchyMemory) Store(
	ctx context.Context,
	sessionID string,
	message agenkit.Message,
	metadata map[string]interface{},
) error {
	// Merge message metadata with provided metadata
	combinedMetadata := make(map[string]interface{})
	combinedMetadata["session_id"] = sessionID
	combinedMetadata["role"] = message.Role

	// Preserve original message timestamp
	combinedMetadata["message_timestamp"] = message.Timestamp.Format(time.RFC3339Nano)

	// Copy message metadata
	if message.Metadata != nil {
		for k, v := range message.Metadata {
			combinedMetadata[k] = v
		}
	}

	// Copy provided metadata (overrides message metadata)
	if metadata != nil {
		for k, v := range metadata {
			combinedMetadata[k] = v
		}
	}

	// Determine importance (use provided, or default by role)
	importance := h.defaultImportance(message)
	if importanceVal, ok := combinedMetadata["importance"].(float64); ok {
		importance = importanceVal
	}

	// Ensure importance is within valid range
	if importance < 0.0 {
		importance = 0.0
	}
	if importance > 1.0 {
		importance = 1.0
	}

	// Convert message content to string
	content := fmt.Sprintf("%v", message.Content)

	// Store in hierarchy
	_, err := h.hierarchy.Store(ctx, content, combinedMetadata, importance, sessionID)
	if err != nil {
		return fmt.Errorf("failed to store in hierarchy: %w", err)
	}

	return nil
}

// Retrieve retrieves messages from hierarchy filtered by session.
//
// Note:
// Unlike InMemoryMemory, this searches semantically across all tiers
// when query is provided. For chronological order, use query="".
func (h *HierarchyMemory) Retrieve(
	ctx context.Context,
	sessionID string,
	opts RetrieveOptions,
) ([]agenkit.Message, error) {
	// Set default limit
	limit := 10
	if opts.Limit != nil {
		limit = *opts.Limit
	}

	// Retrieve from hierarchy (get extra to account for filtering)
	// We multiply limit by 3 because:
	// - Multiple sessions may be in hierarchy
	// - Need enough results after session filtering
	// - Better to over-retrieve than under-retrieve
	entries, err := h.hierarchy.Retrieve(ctx, opts.Query, limit*3, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to retrieve from hierarchy: %w", err)
	}

	// Filter by session and convert to Messages
	messages := make([]agenkit.Message, 0, limit)
	for _, entry := range entries {
		if sessionIDVal, ok := entry.Metadata["session_id"].(string); ok && sessionIDVal == sessionID {
			// Apply additional filters
			if !h.matchesFilters(entry, opts) {
				continue
			}

			messages = append(messages, h.entryToMessage(entry))

			if len(messages) >= limit {
				break
			}
		}
	}

	return messages, nil
}

// Summarize creates a summary of conversation history for session.
//
// Note:
// This is a simple implementation using concatenation.
// Production use should use LLM-based summarization.
func (h *HierarchyMemory) Summarize(
	ctx context.Context,
	sessionID string,
	opts SummarizeOptions,
) (agenkit.Message, error) {
	// Retrieve all messages for session (up to reasonable limit)
	limit := 1000
	messages, err := h.Retrieve(ctx, sessionID, RetrieveOptions{Limit: &limit})
	if err != nil {
		return agenkit.Message{}, fmt.Errorf("failed to retrieve messages: %w", err)
	}

	if len(messages) == 0 {
		return agenkit.Message{
			Role:    "system",
			Content: "No messages in session.",
		}, nil
	}

	// Simple concatenation summary (last 10 messages)
	summaryParts := make([]string, 0)
	maxMessages := 10
	if len(messages) < maxMessages {
		maxMessages = len(messages)
	}

	for i := 0; i < maxMessages; i++ {
		msg := messages[i]
		preview := fmt.Sprintf("%v", msg.Content)
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

// Clear removes all messages for a session from all tiers.
//
// Note:
// Deletion is permanent and cannot be undone.
func (h *HierarchyMemory) Clear(ctx context.Context, sessionID string) error {
	// Retrieve all entries for session (across all tiers)
	entries, err := h.hierarchy.Retrieve(ctx, "", 9999, nil)
	if err != nil {
		return fmt.Errorf("failed to retrieve entries: %w", err)
	}

	// Delete entries matching session from all tiers
	for _, entry := range entries {
		if sessionIDVal, ok := entry.Metadata["session_id"].(string); ok && sessionIDVal == sessionID {
			// Delete from working memory
			if err := h.hierarchy.GetWorking().Delete(ctx, entry.ID); err != nil {
				return fmt.Errorf("failed to delete from working memory: %w", err)
			}

			// Delete from short-term memory if available
			if shortTerm := h.hierarchy.GetShortTerm(); shortTerm != nil {
				if err := shortTerm.Delete(ctx, entry.ID); err != nil {
					return fmt.Errorf("failed to delete from short-term memory: %w", err)
				}
			}

			// Delete from long-term memory if available
			if longTerm := h.hierarchy.GetLongTerm(); longTerm != nil {
				if err := longTerm.Delete(ctx, entry.ID); err != nil {
					return fmt.Errorf("failed to delete from long-term memory: %w", err)
				}
			}
		}
	}

	return nil
}

// Capabilities returns the memory capabilities.
func (h *HierarchyMemory) Capabilities() []string {
	return []string{
		"semantic_search",
		"importance_filtering",
		"tag_filtering",
		"time_filtering",
		"multi_tier",
		"auto_eviction",
	}
}

// GetStats returns memory usage statistics from hierarchy.
func (h *HierarchyMemory) GetStats() map[string]interface{} {
	return h.hierarchy.GetStats()
}

// defaultImportance calculates default importance score based on message role.
func (h *HierarchyMemory) defaultImportance(message agenkit.Message) float64 {
	roleImportance := map[string]float64{
		"system":    0.3,
		"user":      0.5,
		"assistant": 0.4,
		"tool":      0.3,
		"agent":     0.4,
	}

	if importance, ok := roleImportance[message.Role]; ok {
		return importance
	}
	return 0.5
}

// entryToMessage converts a MemoryEntry back to Message.
func (h *HierarchyMemory) entryToMessage(entry *patterns.MemoryEntry) agenkit.Message {
	// Extract role from metadata
	role := "assistant"
	if roleVal, ok := entry.Metadata["role"].(string); ok {
		role = roleVal
	}

	// Extract original message timestamp if preserved
	timestamp := entry.Timestamp
	if timestampStr, ok := entry.Metadata["message_timestamp"].(string); ok {
		if parsedTime, err := time.Parse(time.RFC3339Nano, timestampStr); err == nil {
			timestamp = parsedTime
		}
	}

	// Filter out internal metadata keys
	filteredMetadata := make(map[string]interface{})
	for k, v := range entry.Metadata {
		if k != "session_id" && k != "role" && k != "message_timestamp" {
			filteredMetadata[k] = v
		}
	}

	return agenkit.Message{
		Role:      role,
		Content:   entry.Content,
		Metadata:  filteredMetadata,
		Timestamp: timestamp,
	}
}

// matchesFilters checks if entry matches provided filters.
func (h *HierarchyMemory) matchesFilters(entry *patterns.MemoryEntry, opts RetrieveOptions) bool {
	// Importance threshold filter
	if opts.ImportanceThreshold != nil {
		if entry.Importance < *opts.ImportanceThreshold {
			return false
		}
	}

	// Tags filter (any tag matches)
	if len(opts.Tags) > 0 {
		entryTags := make(map[string]bool)
		if tagsVal, ok := entry.Metadata["tags"].([]interface{}); ok {
			for _, tag := range tagsVal {
				if tagStr, ok := tag.(string); ok {
					entryTags[tagStr] = true
				}
			}
		}

		hasMatch := false
		for _, requiredTag := range opts.Tags {
			if entryTags[requiredTag] {
				hasMatch = true
				break
			}
		}

		if !hasMatch {
			return false
		}
	}

	// Time range filter - use original message timestamp, not storage timestamp
	if opts.TimeRange != nil {
		startTime := time.Unix(opts.TimeRange.Start, 0)
		endTime := time.Unix(opts.TimeRange.End, 0)

		// Get message timestamp from metadata (preserved from original Message)
		messageTimestamp := entry.Timestamp // Default to storage timestamp
		if timestampStr, ok := entry.Metadata["message_timestamp"].(string); ok {
			if parsedTime, err := time.Parse(time.RFC3339Nano, timestampStr); err == nil {
				messageTimestamp = parsedTime
			}
		}

		if messageTimestamp.Before(startTime) || messageTimestamp.After(endTime) {
			return false
		}
	}

	return true
}
