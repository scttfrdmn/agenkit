// Package strategies provides memory selection strategies for context management.
//
// Strategies determine which messages from memory should be included
// in the agent's context window, optimizing for relevance, recency,
// and context limits.
package strategies

import (
	"context"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/memory"
)

// MemoryStrategy defines the interface for intelligent memory management.
//
// Memory strategies decide which messages from memory to include
// in the agent's context, optimizing for:
//   - Relevance (most important information)
//   - Recency (recent conversation flow)
//   - Context limits (fit within token budgets)
//
// Example:
//
//	strategy := NewSlidingWindowStrategy(10)
//	messages, err := strategy.Select(ctx, memory, "session-123", 20)
type MemoryStrategy interface {
	// Select chooses which messages to include in context.
	//
	// Args:
	//   ctx: Context for cancellation
	//   mem: Memory instance to retrieve from
	//   sessionID: Session identifier
	//   contextLimit: Maximum number of messages to return
	//
	// Returns:
	//   List of messages to include in context
	//
	// Example:
	//   messages, err := strategy.Select(ctx, memory, "session-123", 10)
	Select(ctx context.Context, mem memory.Memory, sessionID string, contextLimit int) ([]agenkit.Message, error)
}
