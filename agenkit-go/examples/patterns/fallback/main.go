// Package main demonstrates the Fallback pattern for resilience.
//
// The Fallback pattern tries agents sequentially until one succeeds,
// providing automatic failover and graceful degradation. This is ideal
// for high-availability systems and multi-provider setups.
//
// This example shows:
//   - Primary/backup agent configuration
//   - Automatic failover on errors
//   - Graceful degradation strategies
//   - Recovery functions for error handling
//
// Run with: go run fallback_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"math/rand"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// PrimaryAgent represents a primary service (may fail)
type PrimaryAgent struct {
	failureRate float64
}

func (p *PrimaryAgent) Name() string {
	return "PrimaryService"
}

func (p *PrimaryAgent) Capabilities() []string {
	return []string{"primary", "high-quality"}
}

func (p *PrimaryAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    p.Name(),
		Capabilities: p.Capabilities(),
	}
}

func (p *PrimaryAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   🔵 Primary service attempting...")
	time.Sleep(100 * time.Millisecond)

	// Simulate random failures
	if rand.Float64() < p.failureRate {
		return nil, fmt.Errorf("primary service unavailable")
	}

	result := agenkit.NewMessage("agent", "Response from primary service (high quality)")
	result.WithMetadata("service", "primary").WithMetadata("quality", "high")
	fmt.Println("   ✓ Primary service succeeded")
	return result, nil
}

// BackupAgent represents a backup service
type BackupAgent struct{}

func (b *BackupAgent) Name() string {
	return "BackupService"
}

func (b *BackupAgent) Capabilities() []string {
	return []string{"backup", "reliable"}
}

func (b *BackupAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    b.Name(),
		Capabilities: b.Capabilities(),
	}
}

func (b *BackupAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   🟡 Backup service attempting...")
	time.Sleep(80 * time.Millisecond)

	result := agenkit.NewMessage("agent", "Response from backup service (reliable)")
	result.WithMetadata("service", "backup").WithMetadata("quality", "medium")
	fmt.Println("   ✓ Backup service succeeded")
	return result, nil
}

// CacheAgent represents a fast cache fallback
type CacheAgent struct{}

func (c *CacheAgent) Name() string {
	return "CacheService"
}

func (c *CacheAgent) Capabilities() []string {
	return []string{"cache", "fast"}
}

func (c *CacheAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    c.Name(),
		Capabilities: c.Capabilities(),
	}
}

func (c *CacheAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Println("   🟢 Cache service attempting...")
	time.Sleep(20 * time.Millisecond)

	result := agenkit.NewMessage("agent", "Response from cache (fast, may be stale)")
	result.WithMetadata("service", "cache").WithMetadata("quality", "low")
	fmt.Println("   ✓ Cache service succeeded")
	return result, nil
}

// UnreliableAgent fails randomly
type UnreliableAgent struct {
	name        string
	failureRate float64
}

func (u *UnreliableAgent) Name() string {
	return u.name
}

func (u *UnreliableAgent) Capabilities() []string {
	return []string{"unreliable"}
}

func (u *UnreliableAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    u.Name(),
		Capabilities: u.Capabilities(),
	}
}

func (u *UnreliableAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if rand.Float64() < u.failureRate {
		return nil, fmt.Errorf("%s failed", u.name)
	}
	return agenkit.NewMessage("agent", fmt.Sprintf("Response from %s", u.name)), nil
}

func main() {
	fmt.Println("=== Fallback Pattern Demo ===")
	fmt.Println("Demonstrating high-availability agent patterns")

	ctx := context.Background()

	// Example 1: Basic fallback with primary/backup
	fmt.Println("📊 Example 1: Primary/Backup Failover")
	fmt.Println(strings.Repeat("-", 50))

	primary := &PrimaryAgent{failureRate: 0.7} // 70% failure rate
	backup := &BackupAgent{}
	cache := &CacheAgent{}

	fallback, err := patterns.NewFallbackAgent([]agenkit.Agent{
		primary,
		backup,
		cache,
	})
	if err != nil {
		log.Fatalf("Failed to create fallback agent: %v", err)
	}

	message := agenkit.NewMessage("user", "Request data")

	fmt.Println("\nAttempting request with fallback chain:")
	fmt.Println("Primary -> Backup -> Cache")

	result, err := fallback.Process(ctx, message)
	if err != nil {
		log.Fatalf("All services failed: %v", err)
	}

	fmt.Printf("\n📤 Result: %s\n", result.Content)

	if service, ok := result.Metadata["service"].(string); ok {
		fmt.Printf("   Service: %s\n", service)
	}
	if attempts, ok := result.Metadata["fallback_attempts"].(int); ok {
		fmt.Printf("   Attempts: %d\n", attempts)
	}
	if successAgent, ok := result.Metadata["fallback_success_agent"].(string); ok {
		fmt.Printf("   Success: %s\n", successAgent)
	}

	// Example 2: Multiple attempts showing different outcomes
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 2: Multiple Requests")
	fmt.Println(strings.Repeat("-", 50))

	fmt.Println("\nMaking 5 requests to see fallback behavior:")

	for i := 0; i < 5; i++ {
		fmt.Printf("Request %d:\n", i+1)

		result, err := fallback.Process(ctx, message)
		if err != nil {
			fmt.Printf("   ✗ All services failed\n\n")
			continue
		}

		if service, ok := result.Metadata["service"].(string); ok {
			if attempts, ok := result.Metadata["fallback_attempts"].(int); ok {
				fmt.Printf("   ✓ %s (after %d attempts)\n\n", service, attempts)
			}
		}

		time.Sleep(50 * time.Millisecond)
	}

	// Example 3: All agents fail
	fmt.Println(strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 3: Complete Failure Scenario")
	fmt.Println(strings.Repeat("-", 50))

	failing, err := patterns.NewFallbackAgent([]agenkit.Agent{
		&UnreliableAgent{name: "Agent1", failureRate: 1.0},
		&UnreliableAgent{name: "Agent2", failureRate: 1.0},
		&UnreliableAgent{name: "Agent3", failureRate: 1.0},
	})
	if err != nil {
		log.Fatalf("Failed to create failing agent: %v", err)
	}

	fmt.Println("\nAttempting with all unreliable agents...")

	_, err = failing.Process(ctx, message)
	if err != nil {
		fmt.Printf("✓ Correctly reported failure:\n%v\n", err)
	}

	// Example 4: Using recovery functions
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 4: Recovery Functions")
	fmt.Println(strings.Repeat("-", 50))

	unreliable := &UnreliableAgent{name: "UnreliableService", failureRate: 0.9}

	// Create recovery agent with static message fallback
	recoveryFunc := patterns.DefaultRecovery.StaticMessage(
		"Service temporarily unavailable. Please try again later.")

	recovered := patterns.WithRecovery(unreliable, recoveryFunc)

	fmt.Println("\nAttempting request with recovery...")

	result, err = recovered.Process(ctx, message)
	if err != nil {
		log.Fatalf("Recovery should have handled error: %v", err)
	}

	fmt.Printf("📤 Result: %s\n", result.Content)

	if used, ok := result.Metadata["recovery_used"].(bool); ok && used {
		fmt.Println("   ℹ️  Recovery was triggered")
		if origError, ok := result.Metadata["original_error"].(string); ok {
			fmt.Printf("   Original error: %s\n", origError)
		}
	}

	// Example 5: Custom recovery with context
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 5: Context-Aware Recovery")
	fmt.Println(strings.Repeat("-", 50))

	customRecovery := func(ctx context.Context, msg *agenkit.Message, originalError error) (*agenkit.Message, error) {
		fmt.Println("   🔄 Custom recovery executing...")

		// Create context-aware fallback response
		recovery := fmt.Sprintf("Unable to process request: '%s'. Error: %v\n\nSuggestion: Please try again or contact support.",
			msg.Content, originalError)

		result := agenkit.NewMessage("agent", recovery)
		result.WithMetadata("recovery_type", "custom")
		return result, nil
	}

	customRecovered := patterns.WithRecovery(unreliable, customRecovery)

	fmt.Println("\nAttempting request with custom recovery...")

	result, err = customRecovered.Process(ctx, message)
	if err != nil {
		log.Fatalf("Custom recovery should have handled error: %v", err)
	}

	fmt.Printf("📤 Result:\n%s\n", result.Content)

	// Example 6: Demonstrating first-success optimization
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 6: First-Success Optimization")
	fmt.Println(strings.Repeat("-", 50))

	quickWin, err := patterns.NewFallbackAgent([]agenkit.Agent{
		cache,   // Fast cache
		backup,  // Slower backup
		primary, // Slowest primary
	})
	if err != nil {
		log.Fatalf("Failed to create quick-win agent: %v", err)
	}

	fmt.Println("\nOptimized for speed (Cache -> Backup -> Primary):")

	start := time.Now()
	result, err = quickWin.Process(ctx, message)
	elapsed := time.Since(start)

	if err != nil {
		log.Fatalf("Should have succeeded: %v", err)
	}

	fmt.Printf("📤 Result: %s\n", result.Content)
	fmt.Printf("⏱️  Completed in %v\n", elapsed)

	if service, ok := result.Metadata["service"].(string); ok {
		fmt.Printf("   Service: %s (first to succeed)\n", service)
	}

	fmt.Println("\n✅ Fallback pattern demo complete!")
}
