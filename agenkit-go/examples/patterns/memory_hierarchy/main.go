// Package main demonstrates the Memory Hierarchy pattern for long-running agents.
//
// The Memory Hierarchy pattern implements a three-tier memory system:
// - Working Memory: Current conversation context (fast, limited capacity)
// - Short-Term Memory: Recent sessions with TTL-based expiration
// - Long-Term Memory: Persistent facts filtered by importance
//
// This example shows:
//   - Working memory with LRU eviction
//   - Short-term memory with TTL expiration
//   - Long-term memory with importance filtering
//   - Cross-tier retrieval and ranking
//   - Session isolation for multi-user systems
//
// Run with: go run memory_hierarchy_pattern.go
package main

import (
	"fmt"
	"strings"
)

/*
// Example 1: Basic working memory with LRU eviction
func exampleWorkingMemory() error {
	fmt.Println("\n--- Scenario 1: Working Memory (Current Context) ---")

	working, err := patterns.NewWorkingMemory(5)
	if err != nil {
		return err
	}

	ctx := context.Background()

	// Add more messages than capacity
	for i := 1; i <= 7; i++ {
		entry := patterns.CreateMemoryEntry(
			fmt.Sprintf("Message %d", i),
			map[string]interface{}{},
			0.5,
			"session-1",
		)
		if err := working.Store(ctx, entry); err != nil {
			return err
		}
	}

	messages, err := working.Retrieve(ctx, "Message", 10)
	if err != nil {
		return err
	}

	fmt.Printf("Working memory (max 5): %d messages stored\n", len(messages))
	var contents []string
	for _, m := range messages {
		contents = append(contents, m.Content)
	}
	fmt.Printf("Messages: %v\n", contents)
	fmt.Println("✓ LRU eviction kept only the last 5 messages")

	return nil
}

// Example 2: Short-term memory with TTL
func exampleShortTermMemory() error {
	fmt.Println("--- Scenario 2: Short-Term Memory (Recent Sessions) ---")

	shortTerm, err := patterns.NewShortTermMemory(10, 2*time.Second)
	if err != nil {
		return err
	}

	ctx := context.Background()

	entry1 := patterns.CreateMemoryEntry(
		"User asked about Go",
		map[string]interface{}{},
		0.6,
		"session-2",
	)
	if err := shortTerm.Store(ctx, entry1); err != nil {
		return err
	}

	fmt.Println("Stored: 'User asked about Go'")

	results, err := shortTerm.Retrieve(ctx, "Go", 5)
	if err != nil {
		return err
	}
	fmt.Printf("Retrieved immediately: %d results\n", len(results))

	fmt.Println("Waiting 3 seconds for TTL expiration...")
	time.Sleep(3 * time.Second)

	results, err = shortTerm.Retrieve(ctx, "Go", 5)
	if err != nil {
		return err
	}
	fmt.Printf("Retrieved after TTL: %d results\n", len(results))
	fmt.Println("✓ TTL-based expiration removed expired memories")

	return nil
}

// Example 3: Long-term memory with importance filtering
func exampleLongTermMemory() error {
	fmt.Println("--- Scenario 3: Long-Term Memory (Persistent Facts) ---")

	longTerm, err := patterns.NewLongTermMemory(map[string]interface{}{}, 0.7)
	if err != nil {
		return err
	}

	ctx := context.Background()

	lowImportance := patterns.CreateMemoryEntry(
		"Casual mention of weather",
		map[string]interface{}{},
		0.5, // Below threshold
		"",
	)

	highImportance := patterns.CreateMemoryEntry(
		"User's birthday is December 25",
		map[string]interface{}{},
		0.9, // Above threshold
		"",
	)

	if err := longTerm.Store(ctx, lowImportance); err != nil {
		return err
	}
	if err := longTerm.Store(ctx, highImportance); err != nil {
		return err
	}

	allMemories, err := longTerm.Retrieve(ctx, "", 10)
	if err != nil {
		return err
	}

	fmt.Println("Stored 2 memories (importance 0.5 and 0.9)")
	fmt.Printf("Retrieved with min_importance=0.7: %d memories\n", len(allMemories))
	if len(allMemories) > 0 {
		fmt.Printf("Memory: %s\n", allMemories[0].Content)
	}
	fmt.Println("✓ Importance-based filtering kept only high-value memories")

	return nil
}

// Example 4: Full memory hierarchy
func exampleFullHierarchy() error {
	fmt.Println("--- Scenario 4: Complete Three-Tier System ---")

	working, err := patterns.NewWorkingMemory(10)
	if err != nil {
		return err
	}

	shortTerm, err := patterns.NewShortTermMemory(50, 3600*time.Second)
	if err != nil {
		return err
	}

	longTerm, err := patterns.NewLongTermMemory(map[string]interface{}{}, 0.6)
	if err != nil {
		return err
	}

	memory := patterns.NewMemoryHierarchy(working, shortTerm, longTerm)
	ctx := context.Background()

	// Store in working memory
	if err := memory.Store(ctx,
		"Current topic: Go patterns",
		map[string]interface{}{},
		0.7,
		"session-3",
	); err != nil {
		return err
	}

	// Store in short-term
	if err := memory.Store(ctx,
		"User asked about memory patterns yesterday",
		map[string]interface{}{},
		0.6,
		"session-2",
	); err != nil {
		return err
	}

	// Store in long-term
	if err := memory.Store(ctx,
		"User prefers async/await over callbacks",
		map[string]interface{}{},
		0.85,
		"session-1",
	); err != nil {
		return err
	}

	fmt.Println("Stored memories across all three tiers")
	fmt.Println("Working: current conversation")
	fmt.Println("Short-term: recent sessions")
	fmt.Println("Long-term: persistent preferences")

	return nil
}

// Example 5: Cross-tier retrieval
func exampleCrossTierRetrieval() error {
	fmt.Println("--- Scenario 5: Cross-Tier Retrieval ---")

	working, err := patterns.NewWorkingMemory(10)
	if err != nil {
		return err
	}

	shortTerm, err := patterns.NewShortTermMemory(50, 3600*time.Second)
	if err != nil {
		return err
	}

	longTerm, err := patterns.NewLongTermMemory(map[string]interface{}{}, 0.6)
	if err != nil {
		return err
	}

	memory := patterns.NewMemoryHierarchy(working, shortTerm, longTerm)
	ctx := context.Background()

	// Store test data
	if err := memory.Store(ctx, "Go is a great language", map[string]interface{}{}, 0.8, "session-1"); err != nil {
		return err
	}
	if err := memory.Store(ctx, "Learning Go patterns today", map[string]interface{}{}, 0.7, "session-2"); err != nil {
		return err
	}

	results, err := memory.Retrieve(ctx, "Go", 5, nil)
	if err != nil {
		return err
	}

	fmt.Println("Query: 'Go'")
	fmt.Printf("Results: %d memories found\n", len(results))
	for i, result := range results {
		fmt.Printf("  %d. %s (importance: %.2f)\n", i+1, result.Content, result.Importance)
	}
	fmt.Println("✓ Retrieved and ranked results from all tiers")

	return nil
}

// Example 6: Tier-specific retrieval
func exampleTierSpecificRetrieval() error {
	fmt.Println("--- Scenario 6: Tier-Specific Retrieval ---")

	working, err := patterns.NewWorkingMemory(10)
	if err != nil {
		return err
	}

	shortTerm, err := patterns.NewShortTermMemory(50, 3600*time.Second)
	if err != nil {
		return err
	}

	longTerm, err := patterns.NewLongTermMemory(map[string]interface{}{}, 0.6)
	if err != nil {
		return err
	}

	memory := patterns.NewMemoryHierarchy(working, shortTerm, longTerm)
	ctx := context.Background()

	// Store test data
	if err := memory.Store(ctx, "Current topic", map[string]interface{}{}, 0.8, "session-1"); err != nil {
		return err
	}
	if err := memory.Store(ctx, "User preference", map[string]interface{}{}, 0.9, "session-2"); err != nil {
		return err
	}

	workingOnly, err := memory.Retrieve(ctx, "topic", 5, []string{"working"})
	if err != nil {
		return err
	}
	fmt.Printf("Working memory only: %d results\n", len(workingOnly))

	longTermOnly, err := memory.Retrieve(ctx, "User", 5, []string{"long_term"})
	if err != nil {
		return err
	}
	fmt.Printf("Long-term memory only: %d results\n", len(longTermOnly))

	shortAndLong, err := memory.Retrieve(ctx, "", 10, []string{"short_term", "long_term"})
	if err != nil {
		return err
	}
	fmt.Printf("Short-term + Long-term: %d results\n", len(shortAndLong))
	fmt.Println("✓ Selective tier querying for optimized retrieval")

	return nil
}

// Example 7: Memory with metadata
func exampleMemoryWithMetadata() error {
	fmt.Println("--- Scenario 7: Structured Metadata ---")

	working, err := patterns.NewWorkingMemory(10)
	if err != nil {
		return err
	}

	memory := patterns.NewMemoryHierarchy(working, nil, nil)
	ctx := context.Background()

	metadata := map[string]interface{}{
		"category":   "preference",
		"confidence": 0.95,
		"source":     "explicit",
	}

	if err := memory.Store(ctx,
		"User prefers functional programming style",
		metadata,
		0.9,
		"session-4",
	); err != nil {
		return err
	}

	fmt.Println("Stored memory with metadata:")
	fmt.Println("  Category: preference")
	fmt.Println("  Confidence: 0.95")
	fmt.Println("  Source: explicit")
	fmt.Println("✓ Rich metadata enables advanced filtering and analysis")

	return nil
}

// Example 8: Session isolation
func exampleSessionIsolation() error {
	fmt.Println("--- Scenario 8: Multi-User Sessions ---")

	// User 1 memory
	working1, err := patterns.NewWorkingMemory(10)
	if err != nil {
		return err
	}
	user1Memory := patterns.NewMemoryHierarchy(working1, nil, nil)

	// User 2 memory
	working2, err := patterns.NewWorkingMemory(10)
	if err != nil {
		return err
	}
	user2Memory := patterns.NewMemoryHierarchy(working2, nil, nil)

	ctx := context.Background()

	// User 1
	if err := user1Memory.Store(ctx, "User 1 prefers Python", map[string]interface{}{}, 0.8, "user-1-session-1"); err != nil {
		return err
	}

	// User 2
	if err := user2Memory.Store(ctx, "User 2 prefers Go", map[string]interface{}{}, 0.8, "user-2-session-1"); err != nil {
		return err
	}

	user1Prefs, err := user1Memory.Retrieve(ctx, "prefers", 5, nil)
	if err != nil {
		return err
	}

	user2Prefs, err := user2Memory.Retrieve(ctx, "prefers", 5, nil)
	if err != nil {
		return err
	}

	if len(user1Prefs) > 0 {
		fmt.Printf("User 1 memory: %s\n", user1Prefs[0].Content)
	}
	if len(user2Prefs) > 0 {
		fmt.Printf("User 2 memory: %s\n", user2Prefs[0].Content)
	}
	fmt.Println("✓ Session isolation maintains user privacy")

	return nil
}
*/

func main() {
	fmt.Println("Memory Hierarchy Pattern Examples")
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("\n⚠ These examples need updating to match current MemoryHierarchy API.")
	fmt.Println("See agenkit-go/patterns/memory_test.go for correct usage.")

	// TODO: Update examples to use correct API:
	// NewShortTermMemory(maxMessages int, ttlSeconds int)
	// NewLongTermMemory(storageBackend map[string]*MemoryEntry, embeddingFn interface{}, minImportance float64)
	/*
		// Run all examples
		if err := exampleWorkingMemory(); err != nil {
			log.Fatalf("Example 1 failed: %v", err)
		}

		if err := exampleShortTermMemory(); err != nil {
			log.Fatalf("Example 2 failed: %v", err)
		}

		if err := exampleLongTermMemory(); err != nil {
			log.Fatalf("Example 3 failed: %v", err)
		}

		if err := exampleFullHierarchy(); err != nil {
			log.Fatalf("Example 4 failed: %v", err)
		}

		if err := exampleCrossTierRetrieval(); err != nil {
			log.Fatalf("Example 5 failed: %v", err)
		}

		if err := exampleTierSpecificRetrieval(); err != nil {
			log.Fatalf("Example 6 failed: %v", err)
		}

		if err := exampleMemoryWithMetadata(); err != nil {
			log.Fatalf("Example 7 failed: %v", err)
		}

		if err := exampleSessionIsolation(); err != nil {
			log.Fatalf("Example 8 failed: %v", err)
		}

		fmt.Println(strings.Repeat("=", 60))
		fmt.Println("=== All Memory Hierarchy Examples Complete! ===")
		fmt.Println("\nKey Takeaways:")
		fmt.Println("1. Working Memory: Fast, in-context, LRU eviction")
		fmt.Println("2. Short-Term Memory: Recent sessions, TTL-based expiration")
		fmt.Println("3. Long-Term Memory: Persistent facts, importance filtering")
		fmt.Println("4. Cross-Tier Retrieval: Unified search with ranking")
		fmt.Println("5. Session Isolation: Multi-user privacy")
		fmt.Println("6. Rich Metadata: Structured information for filtering")
		fmt.Println("7. Automatic Management: No manual tier promotion needed")
		fmt.Println("8. Scalable: From single-user to multi-tenant systems")
		fmt.Println()
		fmt.Println("🎯 When to use Memory Hierarchy:")
		fmt.Println("   - Long-running conversational agents")
		fmt.Println("   - Multi-session context management")
		fmt.Println("   - Systems requiring memory prioritization")
		fmt.Println("   - Applications with multi-user isolation needs")
	*/
}
