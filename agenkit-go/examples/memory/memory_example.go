//go:build ignore
// +build ignore

package main

import (
	"context"
	"fmt"
	"log"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/memory"
	"github.com/scttfrdmn/agenkit/agenkit-go/memory/strategies"
)

func main() {
	ctx := context.Background()

	// Example 1: In-Memory Storage
	fmt.Println("=== Example 1: In-Memory Storage ===")
	inMemory := memory.NewInMemoryMemory(1000)

	// Store messages
	msg1 := interfaces.Message{Role: "user", Content: "What is the weather today?"}
	err := inMemory.Store(ctx, "session-123", msg1, map[string]interface{}{
		"importance": 0.5,
		"tags":       []string{"weather", "query"},
	})
	if err != nil {
		log.Fatal(err)
	}

	msg2 := interfaces.Message{Role: "assistant", Content: "It's sunny and 72°F."}
	err = inMemory.Store(ctx, "session-123", msg2, map[string]interface{}{
		"importance": 0.7,
	})
	if err != nil {
		log.Fatal(err)
	}

	msg3 := interfaces.Message{Role: "user", Content: "Should I bring an umbrella?"}
	err = inMemory.Store(ctx, "session-123", msg3, map[string]interface{}{
		"importance": 0.6,
	})
	if err != nil {
		log.Fatal(err)
	}

	// Retrieve messages
	messages, err := inMemory.Retrieve(ctx, "session-123", memory.RetrieveOptions{Limit: 10})
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Retrieved %d messages:\n", len(messages))
	for i, msg := range messages {
		fmt.Printf("  %d. [%s] %s\n", i+1, msg.Role, msg.Content)
	}

	// Get summary
	summary, err := inMemory.Summarize(ctx, "session-123", memory.SummarizeOptions{})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("\nSummary:\n%s\n\n", summary.Content)

	// Example 2: Importance-Based Filtering
	fmt.Println("=== Example 2: Importance-Based Filtering ===")
	threshold := 0.6
	importantMessages, err := inMemory.Retrieve(ctx, "session-123", memory.RetrieveOptions{
		Limit:               10,
		ImportanceThreshold: &threshold,
	})
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Messages with importance >= %.1f:\n", threshold)
	for i, msg := range importantMessages {
		fmt.Printf("  %d. [%s] %s\n", i+1, msg.Role, msg.Content)
	}
	fmt.Println()

	// Example 3: Sliding Window Strategy
	fmt.Println("=== Example 3: Sliding Window Strategy ===")
	// Create a new memory with more messages
	mem := memory.NewInMemoryMemory(1000)
	for i := 1; i <= 20; i++ {
		msg := interfaces.Message{
			Role:    "user",
			Content: fmt.Sprintf("Message %d", i),
		}
		err := mem.Store(ctx, "session-456", msg, nil)
		if err != nil {
			log.Fatal(err)
		}
	}

	// Use sliding window strategy to get only recent 5 messages
	strategy := strategies.NewSlidingWindowStrategy(5)
	recentMessages, err := strategy.Select(ctx, mem, "session-456", 10)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Sliding window (5 most recent):\n")
	for i, msg := range recentMessages {
		fmt.Printf("  %d. %s\n", i+1, msg.Content)
	}
	fmt.Println()

	// Example 4: Importance Weighting Strategy
	fmt.Println("=== Example 4: Importance Weighting Strategy ===")
	// Create memory with varied importance
	impMem := memory.NewInMemoryMemory(1000)
	importanceScores := []float64{0.3, 0.8, 0.5, 0.9, 0.4, 0.7, 0.2, 0.6}
	for i, score := range importanceScores {
		msg := interfaces.Message{
			Role:    "user",
			Content: fmt.Sprintf("Message %d (importance: %.1f)", i+1, score),
			Metadata: map[string]interface{}{
				"importance": score,
			},
		}
		err := impMem.Store(ctx, "session-789", msg, map[string]interface{}{
			"importance": score,
		})
		if err != nil {
			log.Fatal(err)
		}
	}

	// Use importance weighting strategy
	impStrategy := strategies.NewImportanceWeightingStrategy(0.5, 0.3, 2)
	importantMsgs, err := impStrategy.Select(ctx, impMem, "session-789", 5)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Top important messages (threshold: 0.5):\n")
	for i, msg := range importantMsgs {
		fmt.Printf("  %d. %s\n", i+1, msg.Content)
	}
	fmt.Println()

	// Example 5: Memory Usage Statistics
	fmt.Println("=== Example 5: Memory Usage Statistics ===")
	usage := mem.GetMemoryUsage()
	fmt.Printf("Total sessions: %v\n", usage["total_sessions"])
	fmt.Printf("Total messages: %v\n", usage["total_messages"])
	fmt.Printf("Max size per session: %v\n", usage["max_size_per_session"])
	fmt.Println()

	// Example 6: Capabilities
	fmt.Println("=== Example 6: Memory Capabilities ===")
	caps := inMemory.Capabilities()
	fmt.Printf("InMemoryMemory capabilities:\n")
	for _, cap := range caps {
		fmt.Printf("  - %s\n", cap)
	}
	fmt.Println()

	fmt.Println("All examples completed successfully!")
}
