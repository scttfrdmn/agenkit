/*
Retry Middleware Example

This example demonstrates WHY and HOW to use retry middleware for handling
transient failures in agent communication.

WHY USE RETRY MIDDLEWARE?
-------------------------
- API rate limits: External services may temporarily reject requests
- Network instability: Transient network issues are common
- Service restarts: Backends briefly unavailable during deployments
- Cost efficiency: Retrying is cheaper than manual intervention

WHEN TO USE:
- External API calls (LLM providers, databases, web services)
- Network-based agent communication
- Operations with transient failure modes

WHEN NOT TO USE:
- Permanent errors (authentication failures, invalid input)
- Non-idempotent operations without safeguards
- Real-time systems where latency is critical

TRADE-OFFS:
- Latency: Retries add delay (exponential backoff minimizes this)
- Resource usage: Failed attempts consume resources
- Complexity: Must distinguish transient vs permanent failures

Run with: go run agenkit-go/examples/middleware/retry_example.go
*/

package main

import (
	"context"
	"fmt"
	"math/rand"
	"strings"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/middleware"
)

// UnreliableAgent simulates an agent that fails intermittently (like a real API)
type UnreliableAgent struct {
	name         string
	attemptCount int
	failUntil    int // Fail this many times before succeeding
}

func NewUnreliableAgent(name string, failUntil int) *UnreliableAgent {
	return &UnreliableAgent{
		name:      name,
		failUntil: failUntil,
	}
}

func (a *UnreliableAgent) Name() string {
	return a.name
}

func (a *UnreliableAgent) Capabilities() []string {
	return []string{"translation"}
}

func (a *UnreliableAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	a.attemptCount++
	fmt.Printf("  Attempt %d: ", a.attemptCount)

	// Simulate transient failure
	if a.attemptCount <= a.failUntil {
		fmt.Println("❌ Failed (transient error)")
		return nil, fmt.Errorf("transient error: service temporarily unavailable")
	}

	// Success
	fmt.Println("✓ Success")
	return agenkit.NewMessage("assistant", fmt.Sprintf("Translated: %s", message.Content)), nil
}


// Example 1: Basic Retry
func example1BasicRetry() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 1: Basic Retry")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nWHY: Network requests fail temporarily. Retry middleware handles this automatically.")

	// Create agent that fails twice before succeeding
	baseAgent := NewUnreliableAgent("api", 2)

	// Wrap with retry middleware
	retryConfig := middleware.RetryConfig{
		MaxAttempts:       5,
		InitialBackoff:    100 * time.Millisecond,
		MaxBackoff:        2 * time.Second,
		BackoffMultiplier: 2.0,
	}
	agent := middleware.NewRetryDecorator(baseAgent, retryConfig)

	// Send message
	fmt.Println("\nSending message (will fail 2 times, then succeed):")
	ctx := context.Background()
	message := agenkit.NewMessage("user", "Hello, world!")

	start := time.Now()
	result, err := agent.Process(ctx, message)
	elapsed := time.Since(start)

	if err != nil {
		fmt.Printf("\n❌ Final failure after retries: %v\n", err)
	} else {
		fmt.Printf("\n✓ Success: %s\n", result.Content)
		fmt.Printf("  Total time: %dms\n", elapsed.Milliseconds())
		fmt.Printf("  Total attempts: %d\n", baseAgent.attemptCount)
	}

	fmt.Println("\n💡 KEY INSIGHT:")
	fmt.Println("   Retry middleware handled 2 transient failures automatically.")
	fmt.Println("   Exponential backoff: 100ms → 200ms → success")
	fmt.Println("   Without retry: User would see error and have to retry manually.")
}

// Example 2: Max Retries Exceeded
func example2MaxRetriesExceeded() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 2: Max Retries Exceeded")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nWHY: Some failures are persistent. Retry middleware gives up after max attempts.")

	// Create agent that always fails
	baseAgent := NewUnreliableAgent("broken-api", 99) // Will never succeed

	// Wrap with retry middleware (3 attempts)
	retryConfig := middleware.RetryConfig{
		MaxAttempts:       3,
		InitialBackoff:    50 * time.Millisecond,
		MaxBackoff:        1 * time.Second,
		BackoffMultiplier: 2.0,
	}
	agent := middleware.NewRetryDecorator(baseAgent, retryConfig)

	// Send message
	fmt.Println("\nSending message (will fail all attempts):")
	ctx := context.Background()
	message := agenkit.NewMessage("user", "Hello, world!")

	start := time.Now()
	_, err := agent.Process(ctx, message)
	elapsed := time.Since(start)

	fmt.Printf("\n❌ Final failure after %d attempts: %v\n", baseAgent.attemptCount, err)
	fmt.Printf("  Total time: %dms\n", elapsed.Milliseconds())

	fmt.Println("\n💡 KEY INSIGHT:")
	fmt.Println("   Retry middleware stops after max attempts to avoid infinite loops.")
	fmt.Println("   Backoff delays: 50ms → 100ms → 200ms")
	fmt.Println("   Total time: ~350ms (sum of delays)")
}

// Example 3: Rate Limit Handling
func example3RateLimitHandling() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 3: Rate Limit Handling")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nWHY: LLM APIs (OpenAI, Anthropic) have rate limits. Retry handles this gracefully.")

	// Simulate rate-limited API
	type RateLimitedAgent struct {
		*UnreliableAgent
	}

	rateLimitAgent := &RateLimitedAgent{
		UnreliableAgent: NewUnreliableAgent("rate-limited-api", 1),
	}

	// Retry with longer delays (respecting rate limits)
	retryConfig := middleware.RetryConfig{
		MaxAttempts:       4,
		InitialBackoff:    500 * time.Millisecond, // Longer initial delay
		MaxBackoff:        5 * time.Second,
		BackoffMultiplier: 2.0,
	}
	agent := middleware.NewRetryDecorator(rateLimitAgent, retryConfig)

	fmt.Println("\nSending message (simulating rate limit):")
	ctx := context.Background()
	message := agenkit.NewMessage("user", "Summarize this document")

	start := time.Now()
	result, err := agent.Process(ctx, message)
	elapsed := time.Since(start)

	if err != nil {
		fmt.Printf("\n❌ Failed: %v\n", err)
	} else {
		fmt.Printf("\n✓ Success after rate limit: %s\n", result.Content)
		fmt.Printf("  Total time: %dms\n", elapsed.Milliseconds())
	}

	fmt.Println("\n💡 KEY INSIGHT:")
	fmt.Println("   Longer initial delay (500ms) respects API rate limits.")
	fmt.Println("   Real-world: OpenAI returns 429 status, retry after delay.")
	fmt.Println("   Alternative: Use RateLimitMiddleware for proactive limiting.")
}

func main() {
	// Seed random for demonstration
	rand.Seed(time.Now().UnixNano())

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("RETRY MIDDLEWARE EXAMPLES FOR AGENKIT-GO")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nThese examples demonstrate WHY and HOW to use retry middleware.")
	fmt.Println("Each example includes real-world scenarios and trade-offs.")

	// Run examples
	example1BasicRetry()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example2MaxRetriesExceeded()

	fmt.Print("\nPress Enter to continue...")
	fmt.Scanln()

	example3RateLimitHandling()

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("KEY TAKEAWAYS")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println(`
1. WHEN TO USE RETRY MIDDLEWARE:
   - External API calls (LLM providers: OpenAI, Anthropic, Cohere)
   - Network requests that may fail transiently
   - Database connections during brief outages
   - Service-to-service communication

2. CONFIGURATION:
   - MaxAttempts: How many times to retry (3-5 typical)
   - InitialDelay: First retry delay (100-500ms typical)
   - BackoffMultiplier: How fast to increase delay (2.0 typical)
   - MaxDelay: Cap on retry delay (2-10s typical)

3. EXPONENTIAL BACKOFF:
   - Delays: 100ms → 200ms → 400ms → 800ms
   - Prevents overwhelming failing service
   - Gives service time to recover
   - Standard practice for distributed systems

4. REAL-WORLD SCENARIOS:
   - LLM API rate limits (429 status codes)
   - Network timeouts and connection errors
   - Service restarts during deployments
   - Database connection pool exhaustion

5. TRADE-OFFS:
   - Latency: Retries add delay (but better than manual retry)
   - Resources: Failed attempts cost money/compute
   - Complexity: Need to identify transient vs permanent errors
   - User experience: Automatic retry vs immediate error

6. BEST PRACTICES:
   - Use with idempotent operations (safe to retry)
   - Set reasonable max attempts (3-5, not infinite)
   - Log retry attempts for debugging
   - Consider circuit breaker for repeated failures
   - Combine with timeout middleware

Next steps:
- See metrics_example.go for observability
- See composition examples for multi-agent patterns
- See MIDDLEWARE.md for design patterns
	`)
}
