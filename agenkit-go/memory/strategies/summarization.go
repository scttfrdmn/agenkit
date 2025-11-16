package strategies

import (
	"context"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/memory"
)

// SummarizationStrategy summarizes old messages and keeps recent ones verbatim.
//
// Strategy:
//   - Keep last N messages verbatim (for immediate context)
//   - Summarize older messages (for historical context)
//   - Reduces token usage while preserving key information
//
// Use cases:
//   - Long conversations
//   - Token budget constraints
//   - When history matters but details don't
//
// Example:
//
//	strategy := NewSummarizationStrategy(5, true)
//	messages, err := strategy.Select(ctx, memory, "session-123", 10)
//	// Returns: [summary_message, msg1, msg2, msg3, msg4, msg5]
type SummarizationStrategy struct {
	recentCount     int
	summarizeOlder bool
}

// NewSummarizationStrategy creates a new summarization strategy.
//
// Args:
//
//	recentCount: Number of recent messages to keep verbatim
//	summarizeOlder: Whether to include summary of older messages
//
// Example:
//
//	strategy := NewSummarizationStrategy(10, true)
func NewSummarizationStrategy(recentCount int, summarizeOlder bool) *SummarizationStrategy {
	if recentCount <= 0 {
		recentCount = 10
	}
	return &SummarizationStrategy{
		recentCount:     recentCount,
		summarizeOlder: summarizeOlder,
	}
}

// Select chooses messages with summarization.
//
// Args:
//
//	ctx: Context for cancellation
//	mem: Memory instance
//	sessionID: Session identifier
//	contextLimit: Maximum messages (including summary)
//
// Returns:
//
//	[summary_message (if enabled), recent_message_1, ..., recent_message_N]
//
// Note:
//   - Summary counts as 1 message in context_limit
//   - Recent messages ordered from oldest to newest
func (s *SummarizationStrategy) Select(ctx context.Context, mem memory.Memory, sessionID string, contextLimit int) ([]agenkit.Message, error) {
	// Get recent messages
	recent, err := mem.Retrieve(ctx, sessionID, memory.RetrieveOptions{Limit: s.recentCount})
	if err != nil {
		return nil, err
	}

	if !s.summarizeOlder || len(recent) == 0 {
		// No summarization, just return recent
		// Reverse to get oldest-to-newest order for context flow
		if len(recent) > contextLimit {
			recent = recent[:contextLimit]
		}
		return reverseMessages(recent), nil
	}

	// Get summary of older messages
	summary, err := mem.Summarize(ctx, sessionID, memory.SummarizeOptions{})
	if err != nil {
		// If summarization fails, just return recent messages
		if len(recent) > contextLimit {
			recent = recent[:contextLimit]
		}
		return reverseMessages(recent), nil
	}

	// Check if summary indicates no older messages
	if strings.Contains(summary.Content, "No messages") {
		// No older messages to summarize
		if len(recent) > contextLimit {
			recent = recent[:contextLimit]
		}
		return reverseMessages(recent), nil
	}

	// Combine summary + recent (summary first, then chronological recent)
	// Reserve 1 slot for summary
	recentBudget := contextLimit - 1
	if recentBudget < 0 {
		recentBudget = 0
	}
	if recentBudget > len(recent) {
		recentBudget = len(recent)
	}

	result := make([]agenkit.Message, 0, recentBudget+1)
	result = append(result, summary)
	result = append(result, reverseMessages(recent[:recentBudget])...)

	return result, nil
}

// reverseMessages reverses a slice of messages (to get oldest-to-newest order).
func reverseMessages(messages []agenkit.Message) []agenkit.Message {
	result := make([]agenkit.Message, len(messages))
	for i, msg := range messages {
		result[len(messages)-1-i] = msg
	}
	return result
}
