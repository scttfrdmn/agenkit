// Package patterns provides reusable agent composition patterns.
//
// Collaborative pattern implements peer-to-peer agent collaboration with
// iterative refinement. Multiple agents work together, each contributing
// their perspective and refining the collective output through rounds.
//
// Key concepts:
//   - Peer-to-peer collaboration (no hierarchy)
//   - Iterative refinement through rounds
//   - Consensus detection or max rounds limit
//   - Each agent sees all previous responses
//
// Performance characteristics:
//   - Time: O(rounds * n agents) worst case
//   - Memory: O(rounds * n agents * message size)
//   - Early termination on consensus
package patterns

import (
	"context"
	"fmt"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ConsensusFunc determines if agents have reached consensus.
//
// The function receives all agent responses from a round and returns true
// if consensus is achieved. Common strategies include:
//   - Content similarity threshold
//   - Voting on same answer
//   - Agreement indicators in responses
//   - Convergence metrics
type ConsensusFunc func([]*agenkit.Message) bool

// MergeFunc combines multiple agent responses into a single result.
//
// The function receives all responses and produces a merged output.
// Common strategies include:
//   - Voting/majority rule
//   - Weighted combination
//   - Concatenation with synthesis
//   - Best response selection
type MergeFunc func([]*agenkit.Message) *agenkit.Message

// CollaborativeAgent enables peer collaboration with iterative refinement.
//
// Agents work together in rounds, each seeing previous responses and
// contributing refinements. The process continues until consensus is
// reached or maximum rounds are exhausted.
//
// Example use cases:
//   - Code review: multiple reviewers provide feedback
//   - Document editing: iterative improvements from editors
//   - Decision making: collaborative analysis and consensus
//   - Creative writing: multiple perspectives and refinement
//   - Research: peer review and iteration
//
// The collaborative pattern is ideal when multiple perspectives improve
// output quality through discussion and refinement.
type CollaborativeAgent struct {
	name          string
	agents        []agenkit.Agent
	maxRounds     int
	consensusFunc ConsensusFunc
	mergeFunc     MergeFunc
}

// CollaborativeConfig configures a CollaborativeAgent.
type CollaborativeConfig struct {
	// Agents participating in collaboration
	Agents []agenkit.Agent
	// MaxRounds limits iteration (default: 3)
	MaxRounds int
	// ConsensusFunc detects agreement (optional)
	ConsensusFunc ConsensusFunc
	// MergeFunc combines responses (required)
	MergeFunc MergeFunc
}

// NewCollaborativeAgent creates a new collaborative agent.
//
// Parameters:
//   - config: Configuration with agents and collaboration settings
//
// If no consensus function is provided, collaboration continues for all rounds.
// The merge function is required and determines how responses are combined.
func NewCollaborativeAgent(config *CollaborativeConfig) (*CollaborativeAgent, error) {
	if config == nil {
		return nil, fmt.Errorf("config is required")
	}
	if len(config.Agents) < 2 {
		return nil, fmt.Errorf("at least two agents are required for collaboration")
	}
	if config.MergeFunc == nil {
		return nil, fmt.Errorf("merge function is required")
	}

	maxRounds := config.MaxRounds
	if maxRounds == 0 {
		maxRounds = 3
	}

	return &CollaborativeAgent{
		name:          "CollaborativeAgent",
		agents:        config.Agents,
		maxRounds:     maxRounds,
		consensusFunc: config.ConsensusFunc,
		mergeFunc:     config.MergeFunc,
	}, nil
}

// Name returns the agent's identifier.
func (c *CollaborativeAgent) Name() string {
	return c.name
}

// Capabilities returns the combined capabilities of all agents.
func (c *CollaborativeAgent) Capabilities() []string {
	capMap := make(map[string]bool)

	for _, agent := range c.agents {
		for _, cap := range agent.Capabilities() {
			capMap[cap] = true
		}
	}

	capabilities := make([]string, 0, len(capMap))
	for cap := range capMap {
		capabilities = append(capabilities, cap)
	}
	capabilities = append(capabilities, "collaborative", "iterative", "consensus")

	return capabilities
}

// roundResult holds responses from a single collaboration round.
type roundResult struct {
	round     int
	responses []*agenkit.Message
	consensus bool
}

// Process executes collaborative refinement through multiple rounds.
//
// The process follows these steps for each round:
//  1. Each agent processes the current context (original + previous responses)
//  2. All responses are collected
//  3. Consensus is checked (if function provided)
//  4. If consensus or max rounds, merge and return
//  5. Otherwise, prepare next round with all responses as context
//
// The final message includes metadata about rounds, consensus, and participation.
func (c *CollaborativeAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if message == nil {
		return nil, fmt.Errorf("message cannot be nil")
	}

	rounds := make([]roundResult, 0, c.maxRounds)
	currentContext := []*agenkit.Message{message}

	for round := 0; round < c.maxRounds; round++ {
		// Check for context cancellation
		select {
		case <-ctx.Done():
			return nil, fmt.Errorf("collaboration cancelled at round %d: %w", round, ctx.Err())
		default:
		}

		// Collect responses from all agents
		responses := make([]*agenkit.Message, 0, len(c.agents))

		for _, agent := range c.agents {
			// Build context message with conversation history
			contextMsg := c.buildContextMessage(currentContext, round, agent.Name())

			// Get agent response
			response, err := agent.Process(ctx, contextMsg)
			if err != nil {
				return nil, fmt.Errorf("agent %s failed in round %d: %w",
					agent.Name(), round, err)
			}

			responses = append(responses, response)
		}

		// Check for consensus
		hasConsensus := false
		if c.consensusFunc != nil {
			hasConsensus = c.consensusFunc(responses)
		}

		// Record round
		rounds = append(rounds, roundResult{
			round:     round,
			responses: responses,
			consensus: hasConsensus,
		})

		// Stop if consensus reached
		if hasConsensus {
			return c.buildFinalResult(rounds, "consensus"), nil
		}

		// Prepare next round context
		currentContext = append(currentContext, responses...)
	}

	// Max rounds reached
	return c.buildFinalResult(rounds, "max_rounds"), nil
}

// buildContextMessage creates a message with full conversation context.
func (c *CollaborativeAgent) buildContextMessage(context []*agenkit.Message, round int, agentName string) *agenkit.Message {
	var content strings.Builder

	// Add round information
	content.WriteString(fmt.Sprintf("=== Collaboration Round %d ===\n", round))
	content.WriteString(fmt.Sprintf("Agent: %s\n\n", agentName))

	// Add conversation history
	if round == 0 {
		content.WriteString("Original Request:\n")
		content.WriteString(context[0].Content)
	} else {
		content.WriteString("Original Request:\n")
		content.WriteString(context[0].Content)
		content.WriteString("\n\n--- Previous Responses ---\n\n")

		for i, msg := range context[1:] {
			content.WriteString(fmt.Sprintf("Response %d:\n%s\n\n", i+1, msg.Content))
		}

		content.WriteString("--- Your Turn ---\n")
		content.WriteString("Please review the above responses and provide your refined contribution.\n")
	}

	return agenkit.NewMessage("user", content.String())
}

// buildFinalResult merges all responses and adds metadata.
func (c *CollaborativeAgent) buildFinalResult(rounds []roundResult, stopReason string) *agenkit.Message {
	// Collect all responses from final round
	finalRound := rounds[len(rounds)-1]
	merged := c.mergeFunc(finalRound.responses)

	// Add collaboration metadata
	if merged.Metadata == nil {
		merged.Metadata = make(map[string]interface{})
	}

	merged.Metadata["collaboration_rounds"] = len(rounds)
	merged.Metadata["collaboration_agents"] = len(c.agents)
	merged.Metadata["stop_reason"] = stopReason

	// Add round details
	roundDetails := make([]map[string]interface{}, len(rounds))
	for i, r := range rounds {
		roundDetails[i] = map[string]interface{}{
			"round":     r.round,
			"responses": len(r.responses),
			"consensus": r.consensus,
		}
	}
	merged.Metadata["rounds"] = roundDetails

	return merged
}

// DefaultConsensusFunc provides common consensus detection strategies.
var DefaultConsensusFunc = struct {
	// ExactMatch requires all responses to be identical
	ExactMatch ConsensusFunc

	// SimilarityThreshold requires responses to be similar (simple string comparison)
	SimilarityThreshold func(threshold float64) ConsensusFunc

	// MajorityAgreement requires majority of responses to match
	MajorityAgreement ConsensusFunc
}{
	ExactMatch: func(messages []*agenkit.Message) bool {
		if len(messages) <= 1 {
			return true
		}

		first := messages[0].Content
		for _, msg := range messages[1:] {
			if msg.Content != first {
				return false
			}
		}
		return true
	},

	SimilarityThreshold: func(threshold float64) ConsensusFunc {
		return func(messages []*agenkit.Message) bool {
			if len(messages) <= 1 {
				return true
			}

			// Simple similarity: compare common words
			// In production, use proper similarity metrics
			first := strings.ToLower(messages[0].Content)
			for _, msg := range messages[1:] {
				current := strings.ToLower(msg.Content)
				if !strings.Contains(first, current[:min(len(current), 20)]) {
					return false
				}
			}
			return true
		}
	},

	MajorityAgreement: func(messages []*agenkit.Message) bool {
		if len(messages) <= 1 {
			return true
		}

		// Count identical responses
		contentCount := make(map[string]int)
		for _, msg := range messages {
			contentCount[msg.Content]++
		}

		// Check if any content has majority
		majority := (len(messages) / 2) + 1
		for _, count := range contentCount {
			if count >= majority {
				return true
			}
		}

		return false
	},
}

// DefaultMergeFunc provides common merge strategies.
var DefaultMergeFunc = struct {
	// Concatenate combines all responses with separators
	Concatenate MergeFunc

	// Vote returns most common response
	Vote MergeFunc

	// First returns first response
	First MergeFunc

	// Last returns last response
	Last MergeFunc
}{
	Concatenate: func(messages []*agenkit.Message) *agenkit.Message {
		if len(messages) == 0 {
			return agenkit.NewMessage("assistant", "No responses to merge")
		}

		var combined strings.Builder
		for i, msg := range messages {
			if i > 0 {
				combined.WriteString("\n\n---\n\n")
			}
			combined.WriteString(msg.Content)
		}

		return agenkit.NewMessage("assistant", combined.String())
	},

	Vote: func(messages []*agenkit.Message) *agenkit.Message {
		if len(messages) == 0 {
			return agenkit.NewMessage("assistant", "No responses to merge")
		}

		// Count votes
		votes := make(map[string]int)
		msgByContent := make(map[string]*agenkit.Message)

		for _, msg := range messages {
			votes[msg.Content]++
			msgByContent[msg.Content] = msg
		}

		// Find winner
		var maxVotes int
		var winner string
		for content, count := range votes {
			if count > maxVotes {
				maxVotes = count
				winner = content
			}
		}

		result := msgByContent[winner]
		result.WithMetadata("votes", maxVotes).
			WithMetadata("total", len(messages))

		return result
	},

	First: func(messages []*agenkit.Message) *agenkit.Message {
		if len(messages) == 0 {
			return agenkit.NewMessage("assistant", "No responses to merge")
		}
		return messages[0]
	},

	Last: func(messages []*agenkit.Message) *agenkit.Message {
		if len(messages) == 0 {
			return agenkit.NewMessage("assistant", "No responses to merge")
		}
		return messages[len(messages)-1]
	},
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
