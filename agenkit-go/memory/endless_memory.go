package memory

import (
	"context"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// EndlessClient is the interface for endless project clients.
//
// Users must provide a client implementing this interface.
// See: https://github.com/jxnl/endless (user installs separately)
type EndlessClient interface {
	// StoreContext stores messages in endless compressed context.
	StoreContext(ctx context.Context, sessionID string, messages []map[string]interface{}, metadata map[string]interface{}) error

	// RetrieveContext retrieves compressed context from endless.
	RetrieveContext(ctx context.Context, sessionID string, query string, limit int) ([]map[string]interface{}, error)

	// SummarizeContext gets summary of compressed context.
	SummarizeContext(ctx context.Context, sessionID string) (string, error)

	// ClearContext clears context for session.
	ClearContext(ctx context.Context, sessionID string) error
}

// EndlessMemory provides integration with endless project for infinite context.
//
// Features:
//   - Infinite context through compression
//   - Semantic retrieval from compressed context
//   - Automatic context management
//   - Cross-session knowledge accumulation
//
// Limitations:
//   - Requires endless client (user provides)
//   - Compression may lose some details
//   - Additional latency for compression/decompression
//
// Use cases:
//   - Very long conversations (> 200K tokens)
//   - Knowledge accumulation over time
//   - Multi-session knowledge sharing
//   - 30-hour autonomous agents
//
// Example:
//
//	// User installs endless separately
//	import "github.com/jxnl/endless"
//
//	endlessClient := endless.NewClient("api-key")
//	memory := NewEndlessMemory(endlessClient)
//	err := memory.Store(ctx, "session-123", message, nil)
//	messages, err := memory.Retrieve(ctx, "session-123",
//	    RetrieveOptions{Query: "pricing discussion"})
type EndlessMemory struct {
	client EndlessClient
}

// NewEndlessMemory creates a new EndlessMemory instance.
//
// Args:
//
//	endlessClient: Client implementing EndlessClient interface
//	              (user installs endless separately)
//
// Example:
//
//	import "github.com/jxnl/endless"
//	client := endless.NewClient("sk-...")
//	memory := NewEndlessMemory(client)
func NewEndlessMemory(endlessClient EndlessClient) *EndlessMemory {
	return &EndlessMemory{
		client: endlessClient,
	}
}

// messageToMap converts a Message to map for endless storage.
func (e *EndlessMemory) messageToMap(message agenkit.Message) map[string]interface{} {
	return map[string]interface{}{
		"role":    message.Role,
		"content": message.Content,
	}
}

// mapToMessage converts a map from endless to Message.
func (e *EndlessMemory) mapToMessage(data map[string]interface{}) agenkit.Message {
	role, _ := data["role"].(string)
	content, _ := data["content"].(string)

	return agenkit.Message{
		Role:    role,
		Content: content,
	}
}

// Store saves a message in endless compressed context.
//
// Args:
//
//	ctx: Context for cancellation
//	sessionID: Session identifier
//	message: Message to store
//	metadata: Optional metadata (importance, tags, etc.)
func (e *EndlessMemory) Store(ctx context.Context, sessionID string, message agenkit.Message, metadata map[string]interface{}) error {
	msgMap := e.messageToMap(message)
	if metadata != nil {
		msgMap["metadata"] = metadata
	}

	// Store in endless (compression happens automatically)
	return e.client.StoreContext(ctx, sessionID, []map[string]interface{}{msgMap}, metadata)
}

// Retrieve fetches messages from endless compressed context.
//
// Supports semantic retrieval via query parameter.
//
// Args:
//
//	ctx: Context for cancellation
//	sessionID: Session identifier
//	opts: Retrieval options
//
// Returns:
//
//	List of messages from compressed context
func (e *EndlessMemory) Retrieve(ctx context.Context, sessionID string, opts RetrieveOptions) ([]agenkit.Message, error) {
	// Set default limit
	limit := opts.Limit
	if limit <= 0 {
		limit = 10
	}

	// Retrieve from endless
	results, err := e.client.RetrieveContext(ctx, sessionID, opts.Query, limit)
	if err != nil {
		return nil, err
	}

	// Convert to Messages
	messages := make([]agenkit.Message, 0, len(results))
	for _, data := range results {
		messages = append(messages, e.mapToMessage(data))
	}

	return messages, nil
}

// Summarize gets summary of compressed context from endless.
//
// Args:
//
//	ctx: Context for cancellation
//	sessionID: Session identifier
//	opts: Summarization options
//
// Returns:
//
//	Message containing summary
func (e *EndlessMemory) Summarize(ctx context.Context, sessionID string, opts SummarizeOptions) (agenkit.Message, error) {
	summaryText, err := e.client.SummarizeContext(ctx, sessionID)
	if err != nil {
		return agenkit.Message{}, err
	}

	return agenkit.Message{
		Role:    "system",
		Content: summaryText,
	}, nil
}

// Clear removes endless context for session.
//
// Args:
//
//	ctx: Context for cancellation
//	sessionID: Session identifier
func (e *EndlessMemory) Clear(ctx context.Context, sessionID string) error {
	return e.client.ClearContext(ctx, sessionID)
}

// Capabilities returns the memory capabilities.
func (e *EndlessMemory) Capabilities() []string {
	return []string{
		"infinite_context",
		"compression",
		"semantic_search",
		"cross_session_knowledge",
		"automatic_summarization",
	}
}
