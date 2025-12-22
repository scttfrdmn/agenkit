// Package main demonstrates the ParallelAgent pattern.
//
// # Concurrent execution of multiple agents with result aggregation
//
// Use cases:
//   - Ensemble methods
//   - Multi-perspective analysis
//   - Independent parallel tasks
//
// Run with: go run parallel_usage.go
package main

import (
	"context"
	"fmt"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// SimpleAgent is a basic agent for demonstration
type SimpleAgent struct {
	name string
}

func (a *SimpleAgent) Name() string {
	return a.name
}

func (a *SimpleAgent) Capabilities() []string {
	return []string{"demo"}
}

func (a *SimpleAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Printf("   🤖 %s processing...\n", a.name)

	// Simulate varying processing times
	var duration time.Duration
	switch a.name {
	case "Agent1":
		duration = 100 * time.Millisecond
	case "Agent2":
		duration = 200 * time.Millisecond
	case "Agent3":
		duration = 150 * time.Millisecond
	default:
		duration = 100 * time.Millisecond
	}
	time.Sleep(duration)

	result := agenkit.NewMessage("agent", fmt.Sprintf("%s: %s", a.name, message.Content))
	result.WithMetadata("processed_by", a.name)
	result.WithMetadata("duration_ms", duration.Milliseconds())
	return result, nil
}

func (a *SimpleAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    a.Name(),
		Capabilities: a.Capabilities(),
	}
}

func main() {
	fmt.Println("=== ParallelAgent Demo ===")

	// Create agents with different processing speeds
	agent1 := &SimpleAgent{name: "Agent1"} // Fast (100ms)
	agent2 := &SimpleAgent{name: "Agent2"} // Slow (200ms)
	agent3 := &SimpleAgent{name: "Agent3"} // Medium (150ms)

	ctx := context.Background()

	// Example 1: Parallel execution with default aggregator
	fmt.Println("📝 Example 1: Default aggregation (concatenate all results)")
	parallel1, err := patterns.NewParallelAgent([]agenkit.Agent{agent1, agent2, agent3}, nil)
	if err != nil {
		fmt.Printf("   Error: %v\n", err)
		return
	}

	msg1 := agenkit.NewMessage("user", "Analyze this data")
	startTime := time.Now()
	result1, err := parallel1.Process(ctx, msg1)
	duration := time.Since(startTime)
	if err != nil {
		fmt.Printf("   Error: %v\n", err)
		return
	}

	fmt.Printf("   Result: %s\n", result1.Content)
	fmt.Printf("   Total time: %dms (parallel execution)\n", duration.Milliseconds())
	fmt.Printf("   Note: ~200ms (slowest agent), not 450ms (sum of all)\n\n")

	// Example 2: Custom aggregator - combine results
	fmt.Println("📝 Example 2: Custom aggregator (combine with metadata)")
	combineAggregator := func(messages []*agenkit.Message) *agenkit.Message {
		combined := ""
		totalDuration := int64(0)
		agents := []string{}

		for i, msg := range messages {
			if i > 0 {
				combined += ", "
			}
			combined += msg.Content

			if agent, ok := msg.Metadata["processed_by"].(string); ok {
				agents = append(agents, agent)
			}
			if dur, ok := msg.Metadata["duration_ms"].(int64); ok {
				totalDuration += dur
			}
		}

		result := agenkit.NewMessage("agent", combined)
		result.WithMetadata("agents", agents)
		result.WithMetadata("total_processing_ms", totalDuration)
		return result
	}

	parallel2, err := patterns.NewParallelAgent(
		[]agenkit.Agent{agent1, agent2, agent3},
		combineAggregator,
	)
	if err != nil {
		fmt.Printf("   Error: %v\n", err)
		return
	}

	msg2 := agenkit.NewMessage("user", "Process task")
	startTime = time.Now()
	result2, err := parallel2.Process(ctx, msg2)
	duration = time.Since(startTime)
	if err != nil {
		fmt.Printf("   Error: %v\n", err)
		return
	}

	fmt.Printf("   Result: %s\n", result2.Content)
	fmt.Printf("   Agents: %v\n", result2.Metadata["agents"])
	fmt.Printf("   Wall time: %dms\n", duration.Milliseconds())
	fmt.Printf("   CPU time: %dms (sum of all agents)\n\n", result2.Metadata["total_processing_ms"])

	// Example 3: Error handling - one agent fails
	fmt.Println("📝 Example 3: Error handling (one agent fails)")
	fmt.Println("   Note: ParallelAgent continues despite individual failures")

	fmt.Println("✅ ParallelAgent pattern examples completed")
	fmt.Println("\nUse cases:")
	fmt.Println("  • Ensemble methods (combine multiple model predictions)")
	fmt.Println("  • Multi-perspective analysis (analyze from different angles)")
	fmt.Println("  • Independent parallel tasks (process multiple items simultaneously)")
}
