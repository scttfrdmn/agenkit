// Self-Consistency Reasoning Example
//
// This example demonstrates the Self-Consistency reasoning technique,
// which improves reliability by generating multiple independent reasoning
// paths and using voting to select the most consistent answer.
//
// Reference: "Self-Consistency Improves Chain of Thought Reasoning in Language Models"
// Wang et al., 2022 - https://arxiv.org/abs/2203.11171

package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/techniques/reasoning"
)

// SimpleAgent is a mock agent that simulates varying responses
type SimpleAgent struct {
	responses []string
	index     int
}

func NewSimpleAgent(responses []string) *SimpleAgent {
	return &SimpleAgent{
		responses: responses,
		index:     0,
	}
}

func (a *SimpleAgent) Name() string {
	return "simple_agent"
}

func (a *SimpleAgent) Capabilities() []string {
	return []string{"reasoning"}
}

// Introspect satisfies agenkit.Agent. Omitting it is what made this file stop
// compiling: Introspect() was added to the interface without conformance
// assertions, so agent-shaped types silently stopped satisfying it (#847). Nothing
// noticed here because the file was in no Go module at all (#857).
func (a *SimpleAgent) Introspect() *agenkit.IntrospectionResult {
	result, err := agenkit.NewIntrospectionResult(
		a.Name(),
		a.Capabilities(),
		nil,
		map[string]interface{}{"response_index": a.index},
		nil,
	)
	if err != nil {
		return nil
	}
	return result
}

func (a *SimpleAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	response := a.responses[a.index%len(a.responses)]
	a.index++
	return agenkit.NewMessage("assistant", response), nil
}

func main() {
	fmt.Print("=== Self-Consistency Reasoning Examples ===\n\n")

	// Example 1: Basic Self-Consistency with Majority Voting
	example1()

	// Example 2: Weighted Voting Strategy
	example2()

	// Example 3: Custom Answer Extractor
	example3()

	// Example 4: High vs Low Consistency
	example4()
}

// Example 1: Basic Self-Consistency with Majority Voting
func example1() {
	fmt.Println("Example 1: Basic Self-Consistency with Majority Voting")
	fmt.Println(strings.Repeat("-", 60))

	// Create a base agent that provides varying answers
	baseAgent := NewSimpleAgent([]string{
		"After calculation, the answer is 42.",
		"Let me think... I believe it's 43.",
		"The answer is 42.",
		"Definitely 42.",
		"I think the answer is 42.",
	})

	// Wrap with Self-Consistency using majority voting
	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(5),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is 6 * 7?")

	response, err := sc.Process(ctx, message)
	if err != nil {
		log.Fatalf("Process failed: %v", err)
	}

	fmt.Printf("Question: %s\n", message.Content)
	fmt.Printf("Consensus Answer: %s\n", response.Content)
	fmt.Printf("Consistency Score: %.2f\n", response.Metadata["consistency_score"])
	fmt.Printf("Number of Samples: %d\n", response.Metadata["num_samples"])

	// Show individual samples
	samples := response.Metadata["samples"].([]string)
	fmt.Println("\nIndividual Samples:")
	for i, sample := range samples {
		fmt.Printf("  %d. %s\n", i+1, sample)
	}

	// Show extracted answers
	extractedAnswers := response.Metadata["extracted_answers"].([]string)
	fmt.Println("\nExtracted Answers:")
	for i, answer := range extractedAnswers {
		fmt.Printf("  %d. %s\n", i+1, answer)
	}

	fmt.Println()
}

// Example 2: Weighted Voting Strategy
func example2() {
	fmt.Println("Example 2: Weighted Voting Strategy")
	fmt.Println(strings.Repeat("-", 60))

	// Create agent with responses of varying lengths
	baseAgent := NewSimpleAgent([]string{
		"Paris.",
		"Paris.",
		"Paris.",
		"After extensive analysis of historical data, geographical considerations, and political significance, I can confidently conclude that the capital of France is London.",
	})

	// Use weighted voting (longer responses get more weight)
	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(4),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyWeighted),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is the capital of France?")

	response, err := sc.Process(ctx, message)
	if err != nil {
		log.Fatalf("Process failed: %v", err)
	}

	fmt.Printf("Question: %s\n", message.Content)
	fmt.Printf("Weighted Consensus: %s\n", response.Content)
	fmt.Printf("Consistency Score: %.2f\n", response.Metadata["consistency_score"])

	fmt.Println("\nNote: Weighted voting can favor more detailed responses,")
	fmt.Println("which may not always be correct. In this case, the longer")
	fmt.Println("response outweighs three shorter correct answers.")

	fmt.Println()
}

// Example 3: Custom Answer Extractor
func example3() {
	fmt.Println("Example 3: Custom Answer Extractor")
	fmt.Println(strings.Repeat("-", 60))

	// Create agent with structured output format
	baseAgent := NewSimpleAgent([]string{
		"Analysis: Step 1, Step 2. FINAL_ANSWER: 42",
		"Let me calculate... FINAL_ANSWER: 42",
		"After thinking through this... FINAL_ANSWER: 43",
		"My conclusion is FINAL_ANSWER: 42",
		"The result is FINAL_ANSWER: 42",
	})

	// Custom extractor for "FINAL_ANSWER: X" pattern
	customExtractor := func(text string) string {
		marker := "FINAL_ANSWER: "
		start := strings.Index(text, marker)
		if start == -1 {
			return text
		}
		start += len(marker)
		end := strings.IndexAny(text[start:], "\n.")
		if end == -1 {
			return strings.TrimSpace(text[start:])
		}
		return strings.TrimSpace(text[start : start+end])
	}

	sc := reasoning.NewSelfConsistency(
		baseAgent,
		reasoning.WithNumSamples(5),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
		reasoning.WithAnswerExtractor(customExtractor),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Calculate 6 * 7")

	response, err := sc.Process(ctx, message)
	if err != nil {
		log.Fatalf("Process failed: %v", err)
	}

	fmt.Printf("Question: %s\n", message.Content)
	fmt.Printf("Consensus Answer: %s\n", response.Content)
	fmt.Printf("Consistency Score: %.2f (4/5 agreed on '42')\n",
		response.Metadata["consistency_score"])

	extractedAnswers := response.Metadata["extracted_answers"].([]string)
	fmt.Println("\nExtracted Answers:")
	for i, answer := range extractedAnswers {
		fmt.Printf("  %d. %s\n", i+1, answer)
	}

	fmt.Println()
}

// Example 4: High vs Low Consistency
func example4() {
	fmt.Println("Example 4: High vs Low Consistency Comparison")
	fmt.Println(strings.Repeat("-", 60))

	// High consistency case
	fmt.Println("Case A: High Consistency")
	highConsAgent := NewSimpleAgent([]string{
		"The answer is 42.",
		"The answer is 42.",
		"The answer is 42.",
		"The answer is 42.",
		"The answer is 42.",
	})

	scHigh := reasoning.NewSelfConsistency(
		highConsAgent,
		reasoning.WithNumSamples(5),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
	)

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is the answer?")

	responseHigh, err := scHigh.Process(ctx, message)
	if err != nil {
		log.Fatalf("Process failed: %v", err)
	}

	fmt.Printf("Consensus Answer: %s\n", responseHigh.Content)
	fmt.Printf("Consistency Score: %.2f (perfect agreement)\n",
		responseHigh.Metadata["consistency_score"])

	// Low consistency case
	fmt.Println("\nCase B: Low Consistency")
	lowConsAgent := NewSimpleAgent([]string{
		"The answer is 40.",
		"The answer is 41.",
		"The answer is 42.",
		"The answer is 43.",
		"The answer is 44.",
	})

	scLow := reasoning.NewSelfConsistency(
		lowConsAgent,
		reasoning.WithNumSamples(5),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
	)

	responseLow, err := scLow.Process(ctx, message)
	if err != nil {
		log.Fatalf("Process failed: %v", err)
	}

	fmt.Printf("Consensus Answer: %s\n", responseLow.Content)
	fmt.Printf("Consistency Score: %.2f (no agreement)\n",
		responseLow.Metadata["consistency_score"])

	fmt.Println("\nInterpretation:")
	fmt.Println("- High consistency (>0.7): Strong confidence in the answer")
	fmt.Println("- Medium consistency (0.4-0.7): Some agreement, moderate confidence")
	fmt.Println("- Low consistency (<0.4): Little agreement, low confidence")
	fmt.Println("\nLow consistency scores may indicate:")
	fmt.Println("  - Ambiguous or underspecified questions")
	fmt.Println("  - Multiple valid interpretations")
	fmt.Println("  - Need for more samples or better prompting")

	fmt.Println()
}
