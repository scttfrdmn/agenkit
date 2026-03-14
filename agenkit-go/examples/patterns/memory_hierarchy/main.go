// Package main demonstrates the Memory Hierarchy pattern for long-running agents.
//
// The Memory Hierarchy pattern implements a three-tier memory system:
//   - Working Memory: Current conversation context (fast, limited capacity)
//   - Short-Term Memory: Recent sessions with TTL-based expiration
//   - Long-Term Memory: Persistent facts filtered by importance
//
// This example shows:
//   - Creating a hierarchy with NewDefaultHierarchyMemory
//   - Storing messages to the hierarchy
//   - Retrieving messages by session
//   - Using a custom HierarchyConfig
//
// Run with: go run main.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/memory"
)

func main() {
	fmt.Println("Memory Hierarchy Pattern Example")
	fmt.Println(strings.Repeat("=", 60))

	if err := exampleDefaultHierarchy(); err != nil {
		log.Fatalf("example failed: %v", err)
	}

	if err := exampleCustomConfig(); err != nil {
		log.Fatalf("custom config example failed: %v", err)
	}

	fmt.Println("\n✓ Memory Hierarchy examples complete")
}

// exampleDefaultHierarchy shows basic usage with default configuration.
func exampleDefaultHierarchy() error {
	fmt.Println("\n--- Scenario 1: Default hierarchy (working + short-term + long-term) ---")

	h, err := memory.NewDefaultHierarchyMemory()
	if err != nil {
		return fmt.Errorf("create hierarchy: %w", err)
	}

	ctx := context.Background()
	sessionID := "session-demo"

	// Store a few messages
	messages := []struct {
		role    string
		content string
	}{
		{"user", "Hello, I need help planning a project."},
		{"assistant", "I'd be happy to help. What kind of project?"},
		{"user", "A Go microservice with LLM capabilities."},
		{"assistant", "Great choice. Let's start with the architecture."},
	}

	for _, m := range messages {
		msg := agenkit.NewMessage(m.role, m.content)
		if err := h.Store(ctx, sessionID, *msg, nil); err != nil {
			return fmt.Errorf("store message: %w", err)
		}
	}

	// Retrieve messages for the session
	limit := 10
	retrieved, err := h.Retrieve(ctx, sessionID, memory.RetrieveOptions{Limit: &limit})
	if err != nil {
		return fmt.Errorf("retrieve: %w", err)
	}

	fmt.Printf("Stored %d messages, retrieved %d\n", len(messages), len(retrieved))
	for i, entry := range retrieved {
		fmt.Printf("  [%d] %s: %s\n", i+1, entry.Role, truncate(entry.ContentString(), 60))
	}

	return nil
}

// exampleCustomConfig shows usage with a custom HierarchyConfig.
func exampleCustomConfig() error {
	fmt.Println("\n--- Scenario 2: Custom config (small working memory, 30s TTL) ---")

	h, err := memory.NewHierarchyMemory(memory.HierarchyConfig{
		WorkingCapacity:       3, // Only keep last 3 messages in working memory
		ShortTermCapacity:     50,
		ShortTermTTLSeconds:   30,
		LongTermMinImportance: 0.8,
		EnableLongTerm:        true,
	})
	if err != nil {
		return fmt.Errorf("create hierarchy: %w", err)
	}

	ctx := context.Background()
	sessionID := "session-custom"

	// Store 5 messages — only last 3 should be in working memory
	for i := 1; i <= 5; i++ {
		msg := agenkit.NewMessage("user", fmt.Sprintf("Message %d", i))
		if err := h.Store(ctx, sessionID, *msg, nil); err != nil {
			return fmt.Errorf("store: %w", err)
		}
	}

	limit := 10
	retrieved, err := h.Retrieve(ctx, sessionID, memory.RetrieveOptions{Limit: &limit})
	if err != nil {
		return fmt.Errorf("retrieve: %w", err)
	}

	fmt.Printf("Stored 5 messages, retrieved %d (working capacity=3)\n", len(retrieved))
	for _, entry := range retrieved {
		fmt.Printf("  %s\n", entry.ContentString())
	}

	return nil
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}
