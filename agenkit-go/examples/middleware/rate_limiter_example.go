/*
Rate Limiter Middleware Example

This example demonstrates WHY and HOW to use rate limiting middleware to protect
your services and control costs when working with rate-limited APIs.

WHY USE RATE LIMITING?
----------------------
1. API Quota Protection: LLM providers have strict rate limits (OpenAI: 3500 RPM, Anthropic: 50 RPM)
2. Cost Control: Prevent runaway costs from unbounded API usage
3. Fair Resource Allocation: Ensure equitable access in multi-tenant systems
4. Service Protection: Prevent downstream services from being overwhelmed
5. Graceful Degradation: Handle traffic spikes without cascading failures

WHEN TO USE:
- Calling third-party APIs with rate limits (OpenAI, Anthropic, Google)
- Multi-tenant SaaS applications (different tiers: free, pro, enterprise)
- Cost-sensitive operations (expensive LLM calls, data processing)
- Protecting your own services from overload
- Implementing usage quotas per user/organization

WHEN NOT TO USE:
- Internal services with unlimited capacity
- Single-user applications with no cost concerns
- Batch processing where throughput > latency
- Already rate-limited by upstream proxy/gateway

TRADE-OFFS:
- Latency: Requests may wait for available tokens (predictable delay)
- Complexity: Need to tune rate limits based on usage patterns
- Fairness: Simple rate limiting doesn't account for request complexity
- Solution: Use weighted rate limiting (multiple tokens per request)

REAL-WORLD SCENARIOS:
- OpenAI GPT-4: 3,500 RPM limit → Rate: 58.33 RPS, Burst: 100
- Anthropic Claude: 50 RPM limit → Rate: 0.83 RPS, Burst: 10
- Cost control: $0.03/request → Max $100/hour = 3,333 requests/hour (0.93 RPS)
- Multi-tenant: Free tier (10 RPM), Pro (100 RPM), Enterprise (1000 RPM)

Run with: go run agenkit-go/examples/middleware/rate_limiter_example.go
*/

package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/middleware"
)

// MockLLMAgent simulates an LLM API with realistic behavior
type MockLLMAgent struct {
	name    string
	latency time.Duration
}

func NewMockLLMAgent(name string, latency time.Duration) *MockLLMAgent {
	return &MockLLMAgent{
		name:    name,
		latency: latency,
	}
}

func (a *MockLLMAgent) Name() string {
	return a.name
}

func (a *MockLLMAgent) Capabilities() []string {
	return []string{"text_generation"}
}

func (a *MockLLMAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate API processing time
	time.Sleep(a.latency)
	return agenkit.NewMessage("assistant", fmt.Sprintf("Response from %s", a.name)), nil
}

// Example 1: Basic Rate Limiting - Protecting API Quotas
func example1BasicRateLimiting() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 1: Basic Rate Limiting - Protecting API Quotas")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\n📋 SCENARIO: OpenAI API with 3,500 RPM limit")
	fmt.Println("   Real limit: 3,500 RPM = 58.33 RPS")
	fmt.Println("   Our limit: 10 RPS (conservative buffer for safety)")
	fmt.Println("   Burst capacity: 20 requests (handle short spikes)")

	// Create mock OpenAI agent
	baseAgent := NewMockLLMAgent("openai-gpt4", 50*time.Millisecond)

	// Configure rate limiter: 10 requests/second, burst capacity of 20
	config := middleware.RateLimiterConfig{
		Rate:             10.0, // 10 tokens per second
		Capacity:         20,   // Max 20 tokens in bucket (burst capacity)
		TokensPerRequest: 1,    // Each request consumes 1 token
	}
	rateLimitedAgent := middleware.NewRateLimiterDecorator(baseAgent, config)

	fmt.Println("\n🚀 Sending 25 requests rapidly (exceeds burst capacity)...")
	ctx := context.Background()
	start := time.Now()

	successCount := 0
	for i := 0; i < 25; i++ {
		reqStart := time.Now()
		_, err := rateLimitedAgent.Process(ctx, agenkit.NewMessage("user", fmt.Sprintf("Request %d", i+1)))
		elapsed := time.Since(reqStart)

		if err != nil {
			fmt.Printf("  Request %2d: ❌ Failed - %v\n", i+1, err)
		} else {
			successCount++
			if elapsed > 100*time.Millisecond {
				fmt.Printf("  Request %2d: ⏱️  Waited %dms (rate limited)\n", i+1, elapsed.Milliseconds())
			} else {
				fmt.Printf("  Request %2d: ✅ Instant (burst capacity)\n", i+1)
			}
		}
	}

	totalTime := time.Since(start)
	metrics := rateLimitedAgent.Metrics()

	fmt.Printf("\n📊 RESULTS:")
	fmt.Printf("\n  Total time: %v", totalTime.Round(time.Millisecond))
	fmt.Printf("\n  Successful: %d/%d requests", successCount, 25)
	fmt.Printf("\n  Allowed: %d | Rejected: %d", metrics.AllowedRequests, metrics.RejectedRequests)
	fmt.Printf("\n  Tokens remaining: %.1f/%d", metrics.CurrentTokens, config.Capacity)

	fmt.Println("\n\n💡 KEY INSIGHTS:")
	fmt.Println("   ✓ First 20 requests used burst capacity (instant)")
	fmt.Println("   ✓ Remaining 5 requests waited for token refill")
	fmt.Println("   ✓ Rate limiter prevented exceeding API quota")
	fmt.Println("   ✓ Smooth handling of traffic spikes")
}

// Example 2: Burst Handling - Temporary Traffic Spikes
func example2BurstHandling() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 2: Burst Handling - Temporary Traffic Spikes")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\n📋 SCENARIO: Anthropic Claude API with 50 RPM limit")
	fmt.Println("   Real limit: 50 RPM = 0.83 RPS")
	fmt.Println("   Our config: 1 RPS with burst of 10")
	fmt.Println("   Use case: Handle occasional traffic spikes gracefully")

	baseAgent := NewMockLLMAgent("anthropic-claude", 30*time.Millisecond)

	// Conservative rate limit for Anthropic's strict limits
	config := middleware.RateLimiterConfig{
		Rate:             1.0, // 1 request per second (60 RPM)
		Capacity:         10,  // Burst of 10 requests
		TokensPerRequest: 1,
	}
	rateLimitedAgent := middleware.NewRateLimiterDecorator(baseAgent, config)

	fmt.Println("\n🚀 Simulating burst traffic pattern:")
	fmt.Println("   Phase 1: 5 requests (burst)")
	fmt.Println("   Phase 2: Wait 2 seconds (tokens refill)")
	fmt.Println("   Phase 3: 5 more requests (should be instant)")

	ctx := context.Background()

	// Phase 1: Initial burst
	fmt.Println("\n📤 Phase 1: Sending 5 requests...")
	for i := 0; i < 5; i++ {
		start := time.Now()
		_, _ = rateLimitedAgent.Process(ctx, agenkit.NewMessage("user", "Quick question"))
		fmt.Printf("  Request %d: ✅ Completed in %dms\n", i+1, time.Since(start).Milliseconds())
	}

	metrics := rateLimitedAgent.Metrics()
	fmt.Printf("  Tokens remaining: %.1f/%d\n", metrics.CurrentTokens, config.Capacity)

	// Phase 2: Wait for refill
	fmt.Println("\n⏸️  Phase 2: Waiting 2 seconds for token refill...")
	time.Sleep(2 * time.Second)

	// Phase 3: After refill
	fmt.Println("\n📤 Phase 3: Sending 5 more requests...")
	for i := 0; i < 5; i++ {
		start := time.Now()
		_, _ = rateLimitedAgent.Process(ctx, agenkit.NewMessage("user", "Another question"))
		fmt.Printf("  Request %d: ✅ Completed in %dms\n", i+1, time.Since(start).Milliseconds())
	}

	metrics = rateLimitedAgent.Metrics()
	fmt.Printf("  Tokens remaining: %.1f/%d\n", metrics.CurrentTokens, config.Capacity)

	fmt.Println("\n💡 KEY INSIGHTS:")
	fmt.Println("   ✓ Burst capacity handled traffic spikes instantly")
	fmt.Println("   ✓ Tokens refilled during idle periods (1 token/second)")
	fmt.Println("   ✓ System remains responsive during normal load")
	fmt.Println("   ✓ No requests rejected - all gracefully handled")
}

// Example 3: Weighted Rate Limiting - Multiple Tokens Per Request
func example3WeightedRateLimiting() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 3: Weighted Rate Limiting - Variable Request Costs")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\n📋 SCENARIO: Different LLM models have different costs")
	fmt.Println("   GPT-4: Heavy model (5 tokens per request)")
	fmt.Println("   GPT-3.5: Light model (1 token per request)")
	fmt.Println("   Rate: 10 tokens/second, Capacity: 50 tokens")

	// Create agents for different model tiers
	gpt4Agent := NewMockLLMAgent("gpt-4", 100*time.Millisecond)
	gpt35Agent := NewMockLLMAgent("gpt-3.5-turbo", 30*time.Millisecond)

	// Weighted rate limiting: expensive requests consume more tokens
	heavyConfig := middleware.RateLimiterConfig{
		Rate:             10.0, // 10 tokens/second
		Capacity:         50,   // Large burst capacity
		TokensPerRequest: 5,    // GPT-4 consumes 5 tokens
	}
	lightConfig := middleware.RateLimiterConfig{
		Rate:             10.0,
		Capacity:         50,
		TokensPerRequest: 1, // GPT-3.5 consumes 1 token
	}

	gpt4Limited := middleware.NewRateLimiterDecorator(gpt4Agent, heavyConfig)
	gpt35Limited := middleware.NewRateLimiterDecorator(gpt35Agent, lightConfig)

	ctx := context.Background()

	fmt.Println("\n🚀 Test 1: GPT-4 requests (5 tokens each)")
	start := time.Now()
	for i := 0; i < 5; i++ {
		reqStart := time.Now()
		_, _ = gpt4Limited.Process(ctx, agenkit.NewMessage("user", "Complex task"))
		elapsed := time.Since(reqStart)
		fmt.Printf("  GPT-4 Request %d: Completed in %dms (5 tokens)\n", i+1, elapsed.Milliseconds())
	}
	fmt.Printf("  Total: %d requests, %v\n", 5, time.Since(start).Round(time.Millisecond))

	fmt.Println("\n🚀 Test 2: GPT-3.5 requests (1 token each)")
	start = time.Now()
	for i := 0; i < 15; i++ {
		reqStart := time.Now()
		_, _ = gpt35Limited.Process(ctx, agenkit.NewMessage("user", "Simple task"))
		elapsed := time.Since(reqStart)
		if i < 3 || i >= 12 {
			fmt.Printf("  GPT-3.5 Request %d: Completed in %dms (1 token)\n", i+1, elapsed.Milliseconds())
		} else if i == 3 {
			fmt.Println("  ... (requests 4-13) ...")
		}
	}
	fmt.Printf("  Total: %d requests, %v\n", 15, time.Since(start).Round(time.Millisecond))

	gpt4Metrics := gpt4Limited.Metrics()
	gpt35Metrics := gpt35Limited.Metrics()

	fmt.Println("\n📊 COMPARISON:")
	fmt.Printf("  GPT-4:   %d requests × 5 tokens = %d tokens consumed\n",
		gpt4Metrics.AllowedRequests, gpt4Metrics.AllowedRequests*5)
	fmt.Printf("  GPT-3.5: %d requests × 1 token = %d tokens consumed\n",
		gpt35Metrics.AllowedRequests, gpt35Metrics.AllowedRequests)

	fmt.Println("\n💡 KEY INSIGHTS:")
	fmt.Println("   ✓ Expensive operations consume more tokens (fair resource allocation)")
	fmt.Println("   ✓ 5 GPT-4 requests = 25 tokens (rate limited)")
	fmt.Println("   ✓ 15 GPT-3.5 requests = 15 tokens (faster)")
	fmt.Println("   ✓ Weighted limiting prevents abuse of expensive resources")
}

// Example 4: Multi-Tenant SaaS - Different User Tiers
func example4MultiTenantTiers() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 4: Multi-Tenant SaaS - Cost Optimization")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\n📋 SCENARIO: SaaS with tiered pricing")
	fmt.Println("   Free Tier:       10 requests/minute  (burst: 5)")
	fmt.Println("   Pro Tier:       100 requests/minute  (burst: 20)")
	fmt.Println("   Enterprise:   1,000 requests/minute  (burst: 100)")

	baseAgent := NewMockLLMAgent("shared-api", 20*time.Millisecond)

	// Configure different tiers
	tiers := map[string]middleware.RateLimiterConfig{
		"free": {
			Rate:             10.0 / 60.0, // 10 per minute = 0.167 per second
			Capacity:         5,
			TokensPerRequest: 1,
		},
		"pro": {
			Rate:             100.0 / 60.0, // 100 per minute = 1.67 per second
			Capacity:         20,
			TokensPerRequest: 1,
		},
		"enterprise": {
			Rate:             1000.0 / 60.0, // 1000 per minute = 16.67 per second
			Capacity:         100,
			TokensPerRequest: 1,
		},
	}

	// Create rate-limited agents for each tier
	agents := make(map[string]*middleware.RateLimiterDecorator)
	for tier, config := range tiers {
		agents[tier] = middleware.NewRateLimiterDecorator(baseAgent, config)
	}

	ctx := context.Background()

	fmt.Println("\n🧪 Simulating concurrent user traffic:")

	// Simulate each tier sending requests
	for _, tierName := range []string{"free", "pro", "enterprise"} {
		agent := agents[tierName]
		config := tiers[tierName]
		requestCount := int(config.Capacity) + 2 // Slightly exceed burst capacity

		fmt.Printf("\n%s Tier: Sending %d requests...\n", strings.ToUpper(tierName), requestCount)
		start := time.Now()

		instantCount := 0
		waitedCount := 0

		for i := 0; i < requestCount; i++ {
			reqStart := time.Now()
			_, err := agent.Process(ctx, agenkit.NewMessage("user", fmt.Sprintf("Request %d", i+1)))
			elapsed := time.Since(reqStart)

			if err == nil {
				if elapsed < 50*time.Millisecond {
					instantCount++
				} else {
					waitedCount++
				}
			}
		}

		totalTime := time.Since(start)
		metrics := agent.Metrics()

		fmt.Printf("  ✅ Instant: %d requests (burst capacity)\n", instantCount)
		fmt.Printf("  ⏱️  Waited: %d requests (rate limited)\n", waitedCount)
		fmt.Printf("  ⏰ Total time: %v\n", totalTime.Round(time.Millisecond))
		fmt.Printf("  📊 Tokens remaining: %.2f/%d\n", metrics.CurrentTokens, config.Capacity)
	}

	fmt.Println("\n💡 KEY INSIGHTS:")
	fmt.Println("   ✓ Free tier: Limited burst, frequent rate limiting")
	fmt.Println("   ✓ Pro tier: Better burst capacity, occasional limiting")
	fmt.Println("   ✓ Enterprise: Large burst, minimal rate limiting")
	fmt.Println("   ✓ Fair resource allocation across customer tiers")
	fmt.Println("   ✓ Prevents free tier abuse while maintaining service quality")

	fmt.Println("\n💰 COST ANALYSIS:")
	fmt.Println("   Assuming $0.03 per API call:")
	fmt.Printf("   Free:       10/min × $0.03 = $0.30/min = $432/day (sustainable)\n")
	fmt.Printf("   Pro:       100/min × $0.03 = $3.00/min = $4,320/day (paid tier)\n")
	fmt.Printf("   Enterprise: 1000/min × $0.03 = $30/min = $43,200/day (premium)\n")
}

func main() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("RATE LIMITER MIDDLEWARE EXAMPLES FOR AGENKIT-GO")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nRate limiting is essential for:")
	fmt.Println("  1. Protecting against API quota exhaustion")
	fmt.Println("  2. Controlling costs in production systems")
	fmt.Println("  3. Fair resource allocation in multi-tenant systems")
	fmt.Println("  4. Graceful handling of traffic spikes")

	// Run examples
	example1BasicRateLimiting()

	fmt.Print("\n\nPress Enter to continue...")
	fmt.Scanln()

	example2BurstHandling()

	fmt.Print("\n\nPress Enter to continue...")
	fmt.Scanln()

	example3WeightedRateLimiting()

	fmt.Print("\n\nPress Enter to continue...")
	fmt.Scanln()

	example4MultiTenantTiers()

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("KEY TAKEAWAYS")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println(`
1. TOKEN BUCKET ALGORITHM:
   - Tokens refill at constant rate (e.g., 10/second)
   - Each request consumes tokens (default: 1)
   - Burst capacity allows temporary spikes
   - Requests wait if insufficient tokens available

2. CONFIGURATION GUIDELINES:

   OpenAI GPT-4 (3,500 RPM limit):
     Rate: 50.0             // Conservative: 3,000 RPM = 50 RPS
     Capacity: 100          // Handle 2-second burst
     TokensPerRequest: 1

   Anthropic Claude (50 RPM limit):
     Rate: 0.8              // Conservative: 48 RPM = 0.8 RPS
     Capacity: 10           // Handle 12-second burst
     TokensPerRequest: 1

   Cost Control ($100/hour budget, $0.03/call):
     Rate: 0.93             // 3,333 requests/hour = 0.93 RPS
     Capacity: 50           // Handle ~1 minute burst
     TokensPerRequest: 1

3. WEIGHTED RATE LIMITING:
   - Assign costs based on resource usage
   - GPT-4: 5 tokens (expensive)
   - GPT-3.5: 1 token (cheap)
   - Prevents abuse of expensive operations

4. MULTI-TENANT PATTERNS:
   - Free tier: Low rate, small burst (10 RPM, burst: 5)
   - Pro tier: Medium rate, medium burst (100 RPM, burst: 20)
   - Enterprise: High rate, large burst (1,000 RPM, burst: 100)

5. REAL-WORLD BEST PRACTICES:
   - Always set rate slightly BELOW API limits (safety buffer)
   - Use burst capacity = rate × expected spike duration
   - Monitor metrics: AllowedRequests, RejectedRequests, TotalWaitTime
   - Combine with retry middleware for rate limit errors
   - Log rate limit events for capacity planning

6. TRADE-OFFS:
   - Latency: Requests wait for tokens (predictable delay)
   - Fairness: Simple token bucket treats all requests equally
   - Solution: Use weighted limiting for variable-cost operations
   - Monitoring: Track token usage and wait times

7. WHEN TO USE RETRY + RATE LIMITING TOGETHER:
   - Rate limiter: Proactive (prevent exceeding limits)
   - Retry: Reactive (handle 429 errors from API)
   - Use both: Rate limiter as first line of defense
              Retry handles unexpected rate limit responses

Next steps:
- Combine with retry_example.go for robust error handling
- See metrics_example.go for observability
- Implement per-user rate limiting in production
- Consider circuit breaker for repeated failures
`)
}
