// Package reasoning provides reasoning techniques like Self-Consistency, Chain-of-Thought, etc.
package reasoning

import (
	"context"
	"fmt"
	"regexp"
	"strings"
	"sync"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// VotingStrategy defines how to aggregate multiple answers.
type VotingStrategy string

const (
	// VotingStrategyMajority selects the most common answer.
	VotingStrategyMajority VotingStrategy = "majority"
	// VotingStrategyWeighted weights answers by response length (proxy for detail/confidence).
	VotingStrategyWeighted VotingStrategy = "weighted"
	// VotingStrategyFirst uses the first answer (no voting, for debugging).
	VotingStrategyFirst VotingStrategy = "first"
)

// AnswerExtractor is a function that extracts the final answer from a response.
type AnswerExtractor func(text string) string

// SelfConsistency implements the Self-Consistency reasoning technique.
// It generates multiple independent reasoning paths and selects the most consistent
// answer through voting or aggregation strategies.
//
// Reference: "Self-Consistency Improves Chain of Thought Reasoning in Language Models"
// Wang et al., 2022 - https://arxiv.org/abs/2203.11171
type SelfConsistency struct {
	agent           agenkit.Agent
	numSamples      int
	votingStrategy  VotingStrategy
	temperature     *float64
	answerExtractor AnswerExtractor
}

// SelfConsistencyOption is a functional option for configuring SelfConsistency.
type SelfConsistencyOption func(*SelfConsistency)

// WithNumSamples sets the number of independent samples to generate.
func WithNumSamples(n int) SelfConsistencyOption {
	return func(sc *SelfConsistency) {
		sc.numSamples = n
	}
}

// WithVotingStrategy sets the voting strategy for answer aggregation.
func WithVotingStrategy(strategy VotingStrategy) SelfConsistencyOption {
	return func(sc *SelfConsistency) {
		sc.votingStrategy = strategy
	}
}

// WithTemperature sets the sampling temperature for diversity.
func WithTemperature(temp float64) SelfConsistencyOption {
	return func(sc *SelfConsistency) {
		sc.temperature = &temp
	}
}

// WithAnswerExtractor sets a custom answer extraction function.
func WithAnswerExtractor(extractor AnswerExtractor) SelfConsistencyOption {
	return func(sc *SelfConsistency) {
		sc.answerExtractor = extractor
	}
}

// NewSelfConsistency creates a new SelfConsistency agent.
//
// The agent wraps a base agent and samples it multiple times to generate
// diverse reasoning paths. It then uses voting to determine the most
// consistent answer, improving reliability.
//
// Example:
//
//	sc := reasoning.NewSelfConsistency(
//	    baseAgent,
//	    reasoning.WithNumSamples(5),
//	    reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
//	)
func NewSelfConsistency(agent agenkit.Agent, options ...SelfConsistencyOption) *SelfConsistency {
	sc := &SelfConsistency{
		agent:           agent,
		numSamples:      5, // Default
		votingStrategy:  VotingStrategyMajority,
		answerExtractor: defaultAnswerExtractor,
	}

	for _, option := range options {
		option(sc)
	}

	return sc
}

// Name returns the agent name.
func (sc *SelfConsistency) Name() string {
	return "self_consistency"
}

// Capabilities returns the agent capabilities.
func (sc *SelfConsistency) Capabilities() []string {
	return []string{
		"reasoning",
		"self_consistency",
		"majority_voting",
		"reliability",
		"consensus",
	}
}

// defaultAnswerExtractor extracts the final answer from response text.
// It looks for common answer patterns:
//   - "Therefore, X" / "Thus, X" / "So, X"
//   - "The answer is X"
//   - "= X" (for math)
//   - "Conclusion: X" / "Result: X"
//   - Last non-empty line (fallback)
func defaultAnswerExtractor(text string) string {
	// Try explicit answer markers
	patterns := []string{
		`(?i)(?:therefore|thus|so),?\s+(?:the answer is\s+)?(.+?)(?:\.|$)`,
		`(?i)(?:the answer is|answer:)\s+(.+?)(?:\.|$)`,
		`=\s*(.+?)(?:\n|$)`,
		`(?i)(?:conclusion|result):\s*(.+?)(?:\.|$)`,
	}

	for _, pattern := range patterns {
		re := regexp.MustCompile(pattern)
		if match := re.FindStringSubmatch(text); match != nil {
			return strings.TrimSpace(match[1])
		}
	}

	// Fallback: use last non-empty line
	lines := strings.Split(text, "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if line != "" {
			return line
		}
	}

	return strings.TrimSpace(text)
}

// sample represents one sampling result.
type sample struct {
	fullResponse    string
	extractedAnswer string
	err             error
}

// sampleOnce generates one sample from the base agent.
func (sc *SelfConsistency) sampleOnce(ctx context.Context, message *agenkit.Message) (string, string, error) {
	// TODO: If temperature supported, pass it to agent
	response, err := sc.agent.Process(ctx, message)
	if err != nil {
		return "", "", err
	}

	fullResponse := response.Content
	answer := sc.answerExtractor(fullResponse)
	return fullResponse, answer, nil
}

// generateSamples generates multiple samples in parallel.
func (sc *SelfConsistency) generateSamples(ctx context.Context, message *agenkit.Message) ([]string, []string, error) {
	var wg sync.WaitGroup
	samples := make([]sample, sc.numSamples)

	for i := 0; i < sc.numSamples; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			fullResp, answer, err := sc.sampleOnce(ctx, message)
			samples[idx] = sample{
				fullResponse:    fullResp,
				extractedAnswer: answer,
				err:             err,
			}
		}(i)
	}

	wg.Wait()

	// Collect results and check for errors
	fullResponses := make([]string, 0, sc.numSamples)
	extractedAnswers := make([]string, 0, sc.numSamples)

	for _, s := range samples {
		if s.err != nil {
			return nil, nil, fmt.Errorf("sampling failed: %w", s.err)
		}
		fullResponses = append(fullResponses, s.fullResponse)
		extractedAnswers = append(extractedAnswers, s.extractedAnswer)
	}

	return fullResponses, extractedAnswers, nil
}

// voteMajority selects the most common answer.
func (sc *SelfConsistency) voteMajority(answers []string) (string, float64) {
	if len(answers) == 0 {
		return "", 0.0
	}

	// Count answer occurrences (case-insensitive)
	counts := make(map[string]int)
	originalCase := make(map[string]string)

	for _, answer := range answers {
		normalized := strings.ToLower(strings.TrimSpace(answer))
		counts[normalized]++
		if _, exists := originalCase[normalized]; !exists {
			originalCase[normalized] = answer
		}
	}

	// Find most common
	var winningAnswer string
	var maxCount int

	for normalized, count := range counts {
		if count > maxCount {
			maxCount = count
			winningAnswer = normalized
		}
	}

	// Get original case version
	winner := originalCase[winningAnswer]
	consistencyScore := float64(maxCount) / float64(len(answers))

	return winner, consistencyScore
}

// voteWeighted weights answers by response length (proxy for detail/confidence).
func (sc *SelfConsistency) voteWeighted(answers []string, responses []string) (string, float64) {
	if len(answers) == 0 {
		return "", 0.0
	}

	// Group answers by normalized form
	type answerGroup struct {
		original string
		weight   int
		count    int
	}

	groups := make(map[string]*answerGroup)

	for i, answer := range answers {
		normalized := strings.ToLower(strings.TrimSpace(answer))
		if group, exists := groups[normalized]; exists {
			group.weight += len(responses[i])
			group.count++
		} else {
			groups[normalized] = &answerGroup{
				original: answer,
				weight:   len(responses[i]),
				count:    1,
			}
		}
	}

	// Find highest weighted answer
	var winningAnswer string
	var maxWeight int
	var totalWeight int

	for _, group := range groups {
		totalWeight += group.weight
		if group.weight > maxWeight {
			maxWeight = group.weight
			winningAnswer = group.original
		}
	}

	consistencyScore := 0.0
	if totalWeight > 0 {
		consistencyScore = float64(maxWeight) / float64(totalWeight)
	}

	return winningAnswer, consistencyScore
}

// voteFirst uses the first answer (no voting).
func (sc *SelfConsistency) voteFirst(answers []string) (string, float64) {
	if len(answers) == 0 {
		return "", 0.0
	}
	return answers[0], 1.0
}

// Process processes the message with Self-Consistency.
//
// It generates multiple independent samples, extracts answers, and uses
// voting to determine the most consistent answer.
func (sc *SelfConsistency) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Generate multiple samples
	fullResponses, extractedAnswers, err := sc.generateSamples(ctx, message)
	if err != nil {
		return nil, err
	}

	// Vote for consensus answer
	var consensusAnswer string
	var consistencyScore float64

	switch sc.votingStrategy {
	case VotingStrategyMajority:
		consensusAnswer, consistencyScore = sc.voteMajority(extractedAnswers)
	case VotingStrategyWeighted:
		consensusAnswer, consistencyScore = sc.voteWeighted(extractedAnswers, fullResponses)
	case VotingStrategyFirst:
		consensusAnswer, consistencyScore = sc.voteFirst(extractedAnswers)
	default:
		return nil, fmt.Errorf("invalid voting strategy: %s", sc.votingStrategy)
	}

	// Count answer occurrences for metadata
	answerCounts := make(map[string]int)
	for _, answer := range extractedAnswers {
		normalized := strings.ToLower(strings.TrimSpace(answer))
		answerCounts[normalized]++
	}

	// Build response
	response := agenkit.NewMessage("assistant", consensusAnswer)
	response.Metadata["technique"] = "self_consistency"
	response.Metadata["num_samples"] = sc.numSamples
	response.Metadata["voting_strategy"] = string(sc.votingStrategy)
	response.Metadata["consistency_score"] = consistencyScore
	response.Metadata["samples"] = fullResponses
	response.Metadata["extracted_answers"] = extractedAnswers
	response.Metadata["answer_counts"] = answerCounts
	response.Metadata["base_agent"] = sc.agent.Name()

	return response, nil
}
