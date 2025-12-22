// Package memory provides memory systems for agent conversation history.
//
// This package defines interfaces and implementations for storing and retrieving
// agent conversation history, enabling context management beyond raw message lists.
//
// Design principles:
//   - Minimal: Only essential methods
//   - Flexible: Support multiple storage backends
//   - Composable: Combine with strategies
//   - Production-ready: Built for real-world use
//
// Implementations:
//   - InMemoryMemory: Simple in-memory storage with LRU eviction
//   - RedisMemory: Redis-backed with TTL and pub/sub
//   - VectorMemory: Vector database for semantic retrieval
//   - EndlessMemory: Integration with endless project for infinite context
package memory

import (
	"context"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// Memory is the minimal interface for agent memory systems.
//
// Memory systems store and retrieve agent conversation history,
// enabling context management beyond raw message lists. Different
// implementations support various storage backends and retrieval
// strategies.
//
// Example:
//
//	memory := NewInMemoryMemory(1000)
//	err := memory.Store(ctx, "session-123", message, nil)
//	messages, err := memory.Retrieve(ctx, "session-123", RetrieveOptions{Limit: 10})
type Memory interface {
	// Store saves a message to memory with optional metadata.
	//
	// Args:
	//   ctx: Context for cancellation
	//   sessionID: Unique session identifier
	//   message: Message to store
	//   metadata: Optional metadata (importance score, tags, etc.)
	//
	// Example:
	//   err := memory.Store(ctx, "session-123",
	//       Message{Role: "user", Content: "Hello"},
	//       map[string]interface{}{"importance": 0.8, "tags": []string{"greeting"}})
	Store(ctx context.Context, sessionID string, message agenkit.Message, metadata map[string]interface{}) error

	// Retrieve fetches messages from memory.
	//
	// Args:
	//   ctx: Context for cancellation
	//   sessionID: Session identifier
	//   opts: Retrieval options (query, limit, filters)
	//
	// Returns:
	//   List of messages (most recent first by default)
	//
	// Example:
	//   // Basic retrieval (most recent)
	//   messages, err := memory.Retrieve(ctx, "session-123", RetrieveOptions{Limit: 10})
	//
	//   // Semantic retrieval (if supported)
	//   messages, err := memory.Retrieve(ctx, "session-123",
	//       RetrieveOptions{Query: "What did we discuss about pricing?", Limit: 5})
	//
	//   // Time-filtered retrieval
	//   messages, err := memory.Retrieve(ctx, "session-123",
	//       RetrieveOptions{TimeRange: &TimeRange{Start: start, End: end}, Limit: 20})
	Retrieve(ctx context.Context, sessionID string, opts RetrieveOptions) ([]agenkit.Message, error)

	// Summarize creates a summary of conversation history.
	//
	// Args:
	//   ctx: Context for cancellation
	//   sessionID: Session identifier
	//   opts: Summarization options
	//
	// Returns:
	//   Message containing summary
	//
	// Example:
	//   summary, err := memory.Summarize(ctx, "session-123", SummarizeOptions{})
	//   fmt.Println(summary.Content) // "Discussed pricing strategy, decided on $50/month tier..."
	Summarize(ctx context.Context, sessionID string, opts SummarizeOptions) (agenkit.Message, error)

	// Clear removes all memory for a session.
	//
	// Args:
	//   ctx: Context for cancellation
	//   sessionID: Session identifier
	//
	// Example:
	//   err := memory.Clear(ctx, "session-123")
	Clear(ctx context.Context, sessionID string) error

	// Capabilities returns the memory capabilities.
	//
	// Possible capabilities:
	//   - "basic_retrieval": Supports simple Retrieve()
	//   - "semantic_search": Supports query-based retrieval
	//   - "summarization": Supports Summarize()
	//   - "persistence": Data survives restarts
	//   - "ttl": Supports automatic expiry
	//   - "importance_weighting": Supports importance-based retrieval
	//   - "time_travel": Supports point-in-time queries
	//
	// Example:
	//   caps := memory.Capabilities()
	//   // []string{"basic_retrieval", "persistence", "ttl"}
	Capabilities() []string
}

// RetrieveOptions specifies options for retrieving messages.
type RetrieveOptions struct {
	// Query is an optional semantic query for retrieval (if supported)
	Query string

	// Limit is the maximum number of messages to return (default: 10)
	Limit int

	// TimeRange filters messages by time (optional)
	TimeRange *TimeRange

	// ImportanceThreshold filters messages by importance score (optional)
	ImportanceThreshold *float64

	// Tags filters messages that have any of these tags (optional)
	Tags []string
}

// TimeRange represents a time range filter.
type TimeRange struct {
	Start int64 // Unix timestamp in seconds
	End   int64 // Unix timestamp in seconds
}

// SummarizeOptions specifies options for summarization.
type SummarizeOptions struct {
	// MaxLength is the maximum length of the summary (optional)
	MaxLength int

	// Style is the summary style: "brief" or "detailed" (optional)
	Style string
}

// MessageWithMetadata wraps a message with its timestamp and metadata.
type MessageWithMetadata struct {
	Timestamp float64                // Unix timestamp with microsecond precision
	Message   agenkit.Message        // The message
	Metadata  map[string]interface{} // Associated metadata
}
