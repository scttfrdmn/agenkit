// Package main demonstrates the Parallel pattern for concurrent execution.
//
// The Parallel pattern runs multiple agents concurrently and aggregates
// their results. This is ideal for ensemble methods, multi-perspective
// analysis, or independent parallel tasks.
//
// This example shows:
//   - Running multiple agents concurrently
//   - Different aggregation strategies (voting, concatenation)
//   - Handling partial failures in parallel execution
//   - Observing parallel execution metadata
//
// Run with: go run parallel_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// SentimentAgent analyzes sentiment
type SentimentAgent struct{}

func (s *SentimentAgent) Name() string {
	return "SentimentAnalyzer"
}

func (s *SentimentAgent) Capabilities() []string {
	return []string{"sentiment", "analysis"}
}

func (s *SentimentAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    s.Name(),
		Capabilities: s.Capabilities(),
	}
}

func (s *SentimentAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   💭 Sentiment analysis running...")
	time.Sleep(100 * time.Millisecond) // Simulate processing

	// Simple sentiment detection
	content := strings.ToLower(message.Content)
	sentiment := "neutral"
	if strings.Contains(content, "great") || strings.Contains(content, "excellent") {
		sentiment = "positive"
	} else if strings.Contains(content, "bad") || strings.Contains(content, "poor") {
		sentiment = "negative"
	}

	result := agenkit.NewMessage("agent", fmt.Sprintf("Sentiment: %s", sentiment))
	result.WithMetadata("analysis_type", "sentiment")
	return result, nil
}

// EntityAgent extracts entities
type EntityAgent struct{}

func (e *EntityAgent) Name() string {
	return "EntityExtractor"
}

func (e *EntityAgent) Capabilities() []string {
	return []string{"entities", "extraction"}
}

func (e *EntityAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    e.Name(),
		Capabilities: e.Capabilities(),
	}
}

func (e *EntityAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   🏷️  Entity extraction running...")
	time.Sleep(150 * time.Millisecond) // Simulate processing

	// Simple entity extraction (capital words)
	words := strings.Fields(message.Content)
	entities := []string{}
	for _, word := range words {
		if len(word) > 0 && word[0] >= 'A' && word[0] <= 'Z' {
			entities = append(entities, word)
		}
	}

	entitiesStr := strings.Join(entities, ", ")
	if entitiesStr == "" {
		entitiesStr = "none"
	}

	result := agenkit.NewMessage("agent", fmt.Sprintf("Entities: %s", entitiesStr))
	result.WithMetadata("analysis_type", "entities")
	return result, nil
}

// TopicAgent identifies topics
type TopicAgent struct{}

func (t *TopicAgent) Name() string {
	return "TopicClassifier"
}

func (t *TopicAgent) Capabilities() []string {
	return []string{"topics", "classification"}
}

func (t *TopicAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    t.Name(),
		Capabilities: t.Capabilities(),
	}
}

func (t *TopicAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   📚 Topic classification running...")
	time.Sleep(120 * time.Millisecond) // Simulate processing

	// Simple topic detection
	content := strings.ToLower(message.Content)
	topic := "general"
	if strings.Contains(content, "product") || strings.Contains(content, "service") {
		topic = "business"
	} else if strings.Contains(content, "technology") || strings.Contains(content, "software") {
		topic = "technology"
	}

	result := agenkit.NewMessage("agent", fmt.Sprintf("Topic: %s", topic))
	result.WithMetadata("analysis_type", "topic")
	return result, nil
}

// ClassifierAgent provides classification
type ClassifierAgent struct {
	name   string
	result string
}

func (c *ClassifierAgent) Name() string {
	return c.name
}

func (c *ClassifierAgent) Capabilities() []string {
	return []string{"classification"}
}

func (c *ClassifierAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    c.Name(),
		Capabilities: c.Capabilities(),
	}
}

func (c *ClassifierAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(50 * time.Millisecond) // Simulate processing
	return agenkit.NewMessage("agent", c.result), nil
}

func main() {
	fmt.Println("=== Parallel Pattern Demo ===")
	fmt.Println("Demonstrating concurrent agent execution")

	// Example 1: Multi-perspective analysis with concatenation
	fmt.Println("📊 Example 1: Multi-Perspective Analysis")
	fmt.Println(strings.Repeat("-", 50))

	sentiment := &SentimentAgent{}
	entities := &EntityAgent{}
	topics := &TopicAgent{}

	// Create parallel agent with concatenation
	analyzer, err := patterns.NewParallelAgent(
		[]agenkit.Agent{sentiment, entities, topics},
		patterns.DefaultAggregators.Concatenate,
	)
	if err != nil {
		log.Fatalf("Failed to create analyzer: %v", err)
	}

	text := agenkit.NewMessage("user", "This is a great product with excellent features. The Service team was very helpful.")

	fmt.Printf("\n📥 Input: %s\n\n", text.Content)
	fmt.Println("Running 3 analyzers in parallel...")

	ctx := context.Background()
	start := time.Now()
	result, err := analyzer.Process(ctx, text)
	if err != nil {
		log.Fatalf("Analysis failed: %v", err)
	}
	elapsed := time.Since(start)

	fmt.Printf("\n📤 Analysis Results:\n%s\n", result.Content)
	fmt.Printf("\n⏱️  Completed in %v (parallel execution)\n", elapsed)

	if parallelAgents, ok := result.Metadata["parallel_agents"].(int); ok {
		fmt.Printf("   Agents: %d\n", parallelAgents)
	}
	if successful, ok := result.Metadata["successful_agents"].(int); ok {
		fmt.Printf("   Successful: %d\n", successful)
	}

	// Example 2: Majority voting for classification
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 2: Majority Voting Ensemble")
	fmt.Println(strings.Repeat("-", 50))

	classifiers := []agenkit.Agent{
		&ClassifierAgent{name: "Classifier1", result: "spam"},
		&ClassifierAgent{name: "Classifier2", result: "spam"},
		&ClassifierAgent{name: "Classifier3", result: "ham"},
		&ClassifierAgent{name: "Classifier4", result: "spam"},
		&ClassifierAgent{name: "Classifier5", result: "ham"},
	}

	// Create parallel agent with voting
	ensemble, err := patterns.NewParallelAgent(
		classifiers,
		patterns.DefaultAggregators.MajorityVote,
	)
	if err != nil {
		log.Fatalf("Failed to create ensemble: %v", err)
	}

	message := agenkit.NewMessage("user", "Check this out!")

	fmt.Printf("\n📥 Input: %s\n", message.Content)
	fmt.Println("\nRunning 5-classifier ensemble...")

	result, err = ensemble.Process(ctx, message)
	if err != nil {
		log.Fatalf("Ensemble failed: %v", err)
	}

	fmt.Printf("\n📤 Ensemble Result: %s\n", result.Content)
	if votes, ok := result.Metadata["votes"].(int); ok {
		if total, ok := result.Metadata["total_agents"].(int); ok {
			fmt.Printf("   Votes: %d/%d\n", votes, total)
		}
	}

	// Example 3: Handling partial failures
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 3: Fault Tolerance")
	fmt.Println(strings.Repeat("-", 50))

	mixedAgents := []agenkit.Agent{
		sentiment,
		&FailingAgent{},
		topics,
	}

	// Create parallel agent that continues despite failures
	faultTolerant, err := patterns.NewParallelAgent(
		mixedAgents,
		patterns.DefaultAggregators.Concatenate,
	)
	if err != nil {
		log.Fatalf("Failed to create fault-tolerant agent: %v", err)
	}

	fmt.Println("\nRunning with 1 failing agent...")

	result, err = faultTolerant.Process(ctx, text)
	if err != nil {
		log.Fatalf("Should not fail entirely: %v", err)
	}

	fmt.Printf("\n📤 Results (from successful agents):\n%s\n", result.Content)

	if errors, ok := result.Metadata["errors"].([]map[string]interface{}); ok {
		fmt.Printf("\n⚠️  Errors encountered: %d\n", len(errors))
		for _, errInfo := range errors {
			if agent, ok := errInfo["agent"].(string); ok {
				if errMsg, ok := errInfo["error"].(string); ok {
					fmt.Printf("   - %s: %s\n", agent, errMsg)
				}
			}
		}
	}

	// Example 4: Custom aggregation
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 4: Custom Aggregation")
	fmt.Println(strings.Repeat("-", 50))

	// Custom aggregator that creates a summary
	customAggregator := func(messages []*agenkit.Message) *agenkit.Message {
		var summary strings.Builder
		summary.WriteString("Combined Analysis:\n")
		summary.WriteString(fmt.Sprintf("- Received %d analyses\n", len(messages)))

		for i, msg := range messages {
			summary.WriteString(fmt.Sprintf("- Analysis %d: %s\n", i+1, msg.Content))
		}

		return agenkit.NewMessage("agent", summary.String())
	}

	customAnalyzer, err := patterns.NewParallelAgent(
		[]agenkit.Agent{sentiment, entities, topics},
		customAggregator,
	)
	if err != nil {
		log.Fatalf("Failed to create custom analyzer: %v", err)
	}

	result, err = customAnalyzer.Process(ctx, text)
	if err != nil {
		log.Fatalf("Custom analysis failed: %v", err)
	}

	fmt.Printf("\n📤 Custom Aggregation Result:\n%s\n", result.Content)

	fmt.Println("\n✅ Parallel pattern demo complete!")
}

// FailingAgent simulates an agent that fails
type FailingAgent struct{}

func (f *FailingAgent) Name() string {
	return "FailingAgent"
}

func (f *FailingAgent) Capabilities() []string {
	return []string{"failure"}
}

func (f *FailingAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    f.Name(),
		Capabilities: f.Capabilities(),
	}
}

func (f *FailingAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	time.Sleep(80 * time.Millisecond)
	return nil, fmt.Errorf("simulated failure")
}
