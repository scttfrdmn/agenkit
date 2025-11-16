package strategies

import (
	"context"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/memory"
)

// SlidingWindowStrategy keeps the most recent N messages.
//
// This is the simplest and most common strategy:
//   - Always includes most recent messages
//   - Maintains conversation flow
//   - Fixed memory usage
//   - No complex logic
//
// Use cases:
//   - General chatbots
//   - Simple agents
//   - When recent context is most important
//
// Example:
//
//	strategy := NewSlidingWindowStrategy(10)
//	messages, err := strategy.Select(ctx, memory, "session-123", 10)
type SlidingWindowStrategy struct {
	windowSize int
}

// NewSlidingWindowStrategy creates a new sliding window strategy.
//
// Args:
//
//	windowSize: Number of recent messages to keep (default: 10)
//
// Example:
//
//	strategy := NewSlidingWindowStrategy(10)
func NewSlidingWindowStrategy(windowSize int) *SlidingWindowStrategy {
	if windowSize <= 0 {
		windowSize = 10
	}
	return &SlidingWindowStrategy{
		windowSize: windowSize,
	}
}

// Select returns the most recent messages.
//
// Args:
//
//	ctx: Context for cancellation
//	mem: Memory instance
//	sessionID: Session identifier
//	contextLimit: Maximum messages (takes min of contextLimit and windowSize)
//
// Returns:
//
//	Most recent messages (up to limit)
func (s *SlidingWindowStrategy) Select(ctx context.Context, mem memory.Memory, sessionID string, contextLimit int) ([]agenkit.Message, error) {
	limit := contextLimit
	if s.windowSize < limit {
		limit = s.windowSize
	}

	return mem.Retrieve(ctx, sessionID, memory.RetrieveOptions{Limit: limit})
}
