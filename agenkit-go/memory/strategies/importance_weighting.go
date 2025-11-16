package strategies

import (
	"context"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/memory"
)

// ImportanceWeightingStrategy prioritizes messages by importance score.
//
// Selects messages based on:
//   - Importance metadata (if available)
//   - Recency (recent messages get bonus)
//   - Relevance (optional custom scoring)
//
// Scoring:
//   - Base score = importance (0.0-1.0)
//   - Recency bonus = recency_weight * (1 - normalized_age)
//   - Final score = base_score + recency_bonus
//
// Use cases:
//   - When some messages more important than others
//   - Long conversations with key decisions
//   - Tracking action items or commitments
//
// Example:
//
//	strategy := NewImportanceWeightingStrategy(0.5, 0.3, 3)
//	messages, err := strategy.Select(ctx, memory, "session-123", 10)
type ImportanceWeightingStrategy struct {
	importanceThreshold float64
	recencyWeight       float64
	minRecent           int
}

// NewImportanceWeightingStrategy creates a new importance weighting strategy.
//
// Args:
//
//	importanceThreshold: Minimum importance to consider (0.0-1.0)
//	recencyWeight: Weight for recency bonus (0.0-1.0)
//	minRecent: Always include N most recent messages
//
// Example:
//
//	strategy := NewImportanceWeightingStrategy(0.5, 0.3, 3)
func NewImportanceWeightingStrategy(importanceThreshold, recencyWeight float64, minRecent int) *ImportanceWeightingStrategy {
	if minRecent <= 0 {
		minRecent = 3
	}
	return &ImportanceWeightingStrategy{
		importanceThreshold: importanceThreshold,
		recencyWeight:       recencyWeight,
		minRecent:           minRecent,
	}
}

// scoredMessage represents a message with its calculated score.
type scoredMessage struct {
	message agenkit.Message
	score   float64
}

// Select chooses messages by importance score.
//
// Args:
//
//	ctx: Context for cancellation
//	mem: Memory instance
//	sessionID: Session identifier
//	contextLimit: Maximum messages
//
// Returns:
//
//	Messages sorted by importance (most important first)
func (s *ImportanceWeightingStrategy) Select(ctx context.Context, mem memory.Memory, sessionID string, contextLimit int) ([]agenkit.Message, error) {
	// Get more messages than needed for scoring
	allMessages, err := mem.Retrieve(ctx, sessionID, memory.RetrieveOptions{Limit: contextLimit * 3})
	if err != nil {
		return nil, err
	}

	if len(allMessages) == 0 {
		return []agenkit.Message{}, nil
	}

	// Always include most recent messages
	recentCount := s.minRecent
	if recentCount > len(allMessages) {
		recentCount = len(allMessages)
	}
	recent := allMessages[:recentCount]

	// Score remaining messages
	scored := make([]scoredMessage, 0)
	for i := recentCount; i < len(allMessages); i++ {
		msg := allMessages[i]

		// Get base importance (default 0.5 if not set)
		importance := s.calculateImportance(msg)

		// Skip if below threshold
		if importance < s.importanceThreshold {
			continue
		}

		// Add recency bonus (more recent = higher bonus)
		// Normalize by position in list
		recencyBonus := s.recencyWeight * (1.0 - float64(i)/float64(len(allMessages)))
		finalScore := importance + recencyBonus

		scored = append(scored, scoredMessage{
			message: msg,
			score:   finalScore,
		})
	}

	// Sort by score (descending)
	// Simple bubble sort for clarity (Go doesn't have built-in sort for custom structs easily)
	for i := 0; i < len(scored); i++ {
		for j := i + 1; j < len(scored); j++ {
			if scored[j].score > scored[i].score {
				scored[i], scored[j] = scored[j], scored[i]
			}
		}
	}

	// Take top messages (minus what we already included)
	remainingBudget := contextLimit - len(recent)
	if remainingBudget < 0 {
		remainingBudget = 0
	}
	if remainingBudget > len(scored) {
		remainingBudget = len(scored)
	}

	selected := make([]agenkit.Message, 0, remainingBudget)
	for i := 0; i < remainingBudget; i++ {
		selected = append(selected, scored[i].message)
	}

	// Combine important + recent (keeping recent at the end for context flow)
	result := append(selected, recent...)
	return result, nil
}

// calculateImportance calculates the importance score for a message.
//
// Args:
//
//	message: Message to score
//
// Returns:
//
//	Importance score (0.0-1.0)
func (s *ImportanceWeightingStrategy) calculateImportance(message agenkit.Message) float64 {
	// Try to get importance from metadata
	if message.Metadata != nil {
		if importance, ok := message.Metadata["importance"]; ok {
			if f, ok := importance.(float64); ok {
				return f
			}
		}
	}

	// Default importance
	return 0.5
}
