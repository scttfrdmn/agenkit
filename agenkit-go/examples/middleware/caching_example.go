/*
Caching Middleware Example

This example demonstrates WHY and HOW to use caching middleware for improving
performance and reducing costs in agent applications.

WHY USE CACHING MIDDLEWARE?
---------------------------
- Latency reduction: Cache hits return instantly (0ms vs 500ms+ for LLM calls)
- Cost savings: Avoid redundant API calls to expensive LLM services
- Throughput improvement: Handle more requests with same resources
- Graceful degradation: Serve stale data during service outages

WHEN TO USE:
- Repeated requests: Same questions asked multiple times
- Deterministic responses: Agent output is predictable for given input
- Cost-sensitive applications: LLM API costs are significant
- Locality patterns: Similar requests in short time windows

WHEN NOT TO USE:
- Fresh data required: Real-time data that changes frequently
- Unique requests: Every request is different (no cache benefit)
- Memory constrained: Large cache requires significant memory
- Non-deterministic agents: Random/time-dependent responses

TRADE-OFFS:
- Memory usage: Cache stores responses in RAM (configurable size)
- Stale data: Cached responses may be outdated (TTL mitigates this)
- Complexity: Must handle cache invalidation and key generation
- Cold start: Initial requests are slower (cache miss penalty)

KEY FEATURES DEMONSTRATED:
1. Basic caching - Cache hits vs misses, dramatic latency reduction
2. TTL expiration - Automatic expiration of stale entries
3. LRU eviction - When cache is full, evict least recently used
4. Cache invalidation - Manual invalidation of specific entries or entire cache
5. Custom key generators - Control what makes requests "same"
6. Comprehensive metrics - Hit rate, miss rate, evictions, invalidations

Run with: go run examples/middleware/caching_example.go
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

// SlowAgent simulates an agent with expensive processing (like an LLM API call)
type SlowAgent struct {
	name string
}

// NewSlowAgent creates a new slow agent
func NewSlowAgent(name string) *SlowAgent {
	return &SlowAgent{name: name}
}

func (a *SlowAgent) Name() string {
	return a.name
}

func (a *SlowAgent) Capabilities() []string {
	return []string{"processing"}
}

func (a *SlowAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate expensive operation (e.g., LLM API call, database query)
	time.Sleep(500 * time.Millisecond)

	response := agenkit.NewMessage("agent", fmt.Sprintf("Processed: %s", message.Content))
	response.WithMetadata("processing_time", 0.5)
	return response, nil
}

// scenario1BasicCaching demonstrates basic caching with cache hits and misses
func scenario1BasicCaching() {
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("SCENARIO 1: Basic Caching")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println()

	// Create agent with caching
	agent := NewSlowAgent("slow_agent")
	config := middleware.CachingConfig{
		MaxCacheSize: 1000,
		DefaultTTL:   5 * time.Minute,
	}
	cachedAgent, err := middleware.NewCachingDecorator(agent, config)
	if err != nil {
		fmt.Printf("Error creating cached agent: %v\n", err)
		return
	}

	ctx := context.Background()
	message := agenkit.NewMessage("user", "What is AI?")

	// First request - cache miss
	fmt.Println("Request 1 (cache miss - should take ~500ms):")
	start := time.Now()
	response, err := cachedAgent.Process(ctx, message)
	elapsed := time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Response: %s\n", response.Content)
	fmt.Printf("  Time: %dms\n", elapsed.Milliseconds())
	fmt.Println()

	// Second request - cache hit
	fmt.Println("Request 2 (cache hit - should be instant):")
	start = time.Now()
	response, err = cachedAgent.Process(ctx, message)
	elapsed = time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Response: %s\n", response.Content)
	fmt.Printf("  Time: %dms\n", elapsed.Milliseconds())
	fmt.Println()

	// Show metrics
	metrics := cachedAgent.Metrics()
	fmt.Println("Cache Metrics:")
	fmt.Printf("  Total requests: %d\n", metrics.TotalRequests)
	fmt.Printf("  Cache hits: %d\n", metrics.CacheHits)
	fmt.Printf("  Cache misses: %d\n", metrics.CacheMisses)
	fmt.Printf("  Hit rate: %.1f%%\n", metrics.HitRate()*100)
	fmt.Println()
}

// scenario2TTLExpiration demonstrates TTL-based cache expiration
func scenario2TTLExpiration() {
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("SCENARIO 2: TTL-Based Expiration")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println()

	// Create agent with short TTL
	agent := NewSlowAgent("slow_agent")
	config := middleware.CachingConfig{
		MaxCacheSize: 1000,
		DefaultTTL:   1 * time.Second, // 1 second TTL
	}
	cachedAgent, err := middleware.NewCachingDecorator(agent, config)
	if err != nil {
		fmt.Printf("Error creating cached agent: %v\n", err)
		return
	}

	ctx := context.Background()
	message := agenkit.NewMessage("user", "Tell me a joke")

	// First request
	fmt.Println("Request 1:")
	start := time.Now()
	_, err = cachedAgent.Process(ctx, message)
	elapsed := time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Time: %dms (cache miss)\n", elapsed.Milliseconds())
	fmt.Println()

	// Second request (within TTL)
	fmt.Println("Request 2 (within 1s TTL):")
	start = time.Now()
	_, err = cachedAgent.Process(ctx, message)
	elapsed = time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Time: %dms (cache hit)\n", elapsed.Milliseconds())
	fmt.Println()

	// Wait for expiration
	fmt.Println("Waiting for TTL expiration (1.5s)...")
	time.Sleep(1500 * time.Millisecond)
	fmt.Println()

	// Third request (after TTL)
	fmt.Println("Request 3 (after TTL expiration):")
	start = time.Now()
	_, err = cachedAgent.Process(ctx, message)
	elapsed = time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Time: %dms (cache miss - expired)\n", elapsed.Milliseconds())
	fmt.Println()
}

// scenario3LRUEviction demonstrates LRU eviction when cache is full
func scenario3LRUEviction() {
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("SCENARIO 3: LRU Eviction")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println()

	// Create agent with small cache
	agent := NewSlowAgent("slow_agent")
	config := middleware.CachingConfig{
		MaxCacheSize: 3, // Only 3 entries
		DefaultTTL:   5 * time.Minute,
	}
	cachedAgent, err := middleware.NewCachingDecorator(agent, config)
	if err != nil {
		fmt.Printf("Error creating cached agent: %v\n", err)
		return
	}

	ctx := context.Background()

	// Fill cache
	fmt.Println("Filling cache with 3 entries:")
	for i := 0; i < 3; i++ {
		msg := agenkit.NewMessage("user", fmt.Sprintf("Question %d", i))
		_, err := cachedAgent.Process(ctx, msg)
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			return
		}
		fmt.Printf("  Added: Question %d\n", i)
	}

	fmt.Printf("\nCache size: %d\n", cachedAgent.GetCacheSize())
	fmt.Println()

	// Access first entry to make it recently used
	fmt.Println("Accessing Question 0 (mark as recently used):")
	msg0 := agenkit.NewMessage("user", "Question 0")
	start := time.Now()
	_, err = cachedAgent.Process(ctx, msg0)
	elapsed := time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Time: %dms (cache hit)\n", elapsed.Milliseconds())
	fmt.Println()

	// Add new entry - should evict Question 1 (LRU)
	fmt.Println("Adding Question 3 (should evict Question 1):")
	msg3 := agenkit.NewMessage("user", "Question 3")
	_, err = cachedAgent.Process(ctx, msg3)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	metrics := cachedAgent.Metrics()
	fmt.Printf("  Evictions: %d\n", metrics.Evictions)
	fmt.Println()

	// Verify Question 0 is still cached
	fmt.Println("Verifying Question 0 is still cached:")
	start = time.Now()
	_, err = cachedAgent.Process(ctx, msg0)
	elapsed = time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Time: %dms (cache hit)\n", elapsed.Milliseconds())
	fmt.Println()

	// Verify Question 1 was evicted
	fmt.Println("Verifying Question 1 was evicted:")
	msg1 := agenkit.NewMessage("user", "Question 1")
	start = time.Now()
	_, err = cachedAgent.Process(ctx, msg1)
	elapsed = time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Time: %dms (cache miss - evicted)\n", elapsed.Milliseconds())
	fmt.Println()
}

// scenario4CacheInvalidation demonstrates manual cache invalidation
func scenario4CacheInvalidation() {
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("SCENARIO 4: Cache Invalidation")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println()

	agent := NewSlowAgent("slow_agent")
	config := middleware.DefaultCachingConfig()
	cachedAgent, err := middleware.NewCachingDecorator(agent, config)
	if err != nil {
		fmt.Printf("Error creating cached agent: %v\n", err)
		return
	}

	ctx := context.Background()

	// Cache some responses
	msg1 := agenkit.NewMessage("user", "Weather today")
	msg2 := agenkit.NewMessage("user", "Stock price")

	fmt.Println("Caching two messages:")
	_, err = cachedAgent.Process(ctx, msg1)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	_, err = cachedAgent.Process(ctx, msg2)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Cache size: %d\n", cachedAgent.GetCacheSize())
	fmt.Println()

	// Invalidate specific entry
	fmt.Println("Invalidating 'Weather today':")
	cachedAgent.Invalidate(msg1)
	fmt.Printf("  Cache size: %d\n", cachedAgent.GetCacheSize())
	fmt.Println()

	// Verify msg1 is invalidated (miss) but msg2 is still cached (hit)
	fmt.Println("Testing cache after invalidation:")
	start := time.Now()
	_, err = cachedAgent.Process(ctx, msg1)
	elapsed1 := time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Weather today: %dms (cache miss)\n", elapsed1.Milliseconds())

	start = time.Now()
	_, err = cachedAgent.Process(ctx, msg2)
	elapsed2 := time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Stock price: %dms (cache hit)\n", elapsed2.Milliseconds())
	fmt.Println()

	// Invalidate entire cache
	fmt.Println("Invalidating entire cache:")
	cachedAgent.Invalidate(nil)
	fmt.Printf("  Cache size: %d\n", cachedAgent.GetCacheSize())
	metrics := cachedAgent.Metrics()
	fmt.Printf("  Total invalidations: %d\n", metrics.Invalidations)
	fmt.Println()
}

// scenario5CustomKeyGenerator demonstrates custom cache key generation
func scenario5CustomKeyGenerator() {
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("SCENARIO 5: Custom Key Generator")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println()

	// Key generator that ignores metadata
	contentOnlyKey := func(message *agenkit.Message) string {
		return fmt.Sprintf("key:%s", message.Content)
	}

	agent := NewSlowAgent("slow_agent")
	config := middleware.CachingConfig{
		MaxCacheSize: 1000,
		DefaultTTL:   5 * time.Minute,
		KeyGenerator: contentOnlyKey,
	}
	cachedAgent, err := middleware.NewCachingDecorator(agent, config)
	if err != nil {
		fmt.Printf("Error creating cached agent: %v\n", err)
		return
	}

	ctx := context.Background()

	// Same content, different metadata
	msg1 := agenkit.NewMessage("user", "Translate: Hello")
	msg1.WithMetadata("lang", "es")

	msg2 := agenkit.NewMessage("user", "Translate: Hello")
	msg2.WithMetadata("lang", "fr")

	fmt.Println("Request 1 (Spanish):")
	start := time.Now()
	_, err = cachedAgent.Process(ctx, msg1)
	elapsed := time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Time: %dms (cache miss)\n", elapsed.Milliseconds())
	fmt.Println()

	fmt.Println("Request 2 (French - same content, different metadata):")
	start = time.Now()
	_, err = cachedAgent.Process(ctx, msg2)
	elapsed = time.Since(start)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("  Time: %dms (cache hit - key ignores metadata)\n", elapsed.Milliseconds())
	fmt.Println()

	fmt.Println("Note: Custom key generator treats these as same request")
	fmt.Println()
}

// scenario6CacheMetrics demonstrates comprehensive cache metrics
func scenario6CacheMetrics() {
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("SCENARIO 6: Cache Metrics")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println()

	agent := NewSlowAgent("slow_agent")
	config := middleware.CachingConfig{
		MaxCacheSize: 100,
		DefaultTTL:   5 * time.Minute,
	}
	cachedAgent, err := middleware.NewCachingDecorator(agent, config)
	if err != nil {
		fmt.Printf("Error creating cached agent: %v\n", err)
		return
	}

	ctx := context.Background()

	// Make various requests
	fmt.Println("Making 10 requests (5 unique, 5 repeated):")
	for i := 0; i < 10; i++ {
		// First 5 are unique, next 5 repeat
		msgID := i % 5
		msg := agenkit.NewMessage("user", fmt.Sprintf("Question %d", msgID))
		_, err := cachedAgent.Process(ctx, msg)
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			return
		}
	}

	fmt.Println()

	// Get detailed cache info
	info := cachedAgent.GetCacheInfo()

	fmt.Println("Cache Configuration:")
	fmt.Printf("  Max size: %v\n", info["max_size"])
	fmt.Printf("  TTL: %.0fs\n", info["default_ttl"])
	fmt.Println()

	fmt.Println("Cache Statistics:")
	metricsMap := info["metrics"].(map[string]interface{})
	fmt.Printf("  Current size: %v\n", info["size"])
	fmt.Printf("  Total requests: %v\n", metricsMap["total_requests"])
	fmt.Printf("  Cache hits: %v\n", metricsMap["cache_hits"])
	fmt.Printf("  Cache misses: %v\n", metricsMap["cache_misses"])
	fmt.Printf("  Hit rate: %.1f%%\n", metricsMap["hit_rate"].(float64)*100)
	fmt.Printf("  Miss rate: %.1f%%\n", metricsMap["miss_rate"].(float64)*100)
	fmt.Printf("  Evictions: %v\n", metricsMap["evictions"])
	fmt.Printf("  Invalidations: %v\n", metricsMap["invalidations"])
	fmt.Println()
}

func main() {
	fmt.Println()
	fmt.Println("╔" + strings.Repeat("═", 68) + "╗")
	fmt.Println("║" + strings.Repeat(" ", 20) + "Caching Middleware Demo" + strings.Repeat(" ", 25) + "║")
	fmt.Println("╚" + strings.Repeat("═", 68) + "╝")
	fmt.Println()

	scenario1BasicCaching()
	time.Sleep(500 * time.Millisecond)

	scenario2TTLExpiration()
	time.Sleep(500 * time.Millisecond)

	scenario3LRUEviction()
	time.Sleep(500 * time.Millisecond)

	scenario4CacheInvalidation()
	time.Sleep(500 * time.Millisecond)

	scenario5CustomKeyGenerator()
	time.Sleep(500 * time.Millisecond)

	scenario6CacheMetrics()

	// Summary
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("SUMMARY")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println()
	fmt.Println("Caching Benefits:")
	fmt.Println("  ✓ Reduces latency for repeated requests")
	fmt.Println("  ✓ Reduces cost (fewer LLM API calls)")
	fmt.Println("  ✓ Improves throughput")
	fmt.Println("  ✓ Configurable TTL and LRU eviction")
	fmt.Println("  ✓ Cache invalidation support")
	fmt.Println("  ✓ Comprehensive metrics")
	fmt.Println()
	fmt.Println("Use caching when:")
	fmt.Println("  • Requests are frequently repeated")
	fmt.Println("  • Responses are deterministic or acceptable to be stale")
	fmt.Println("  • Cost/latency reduction is more important than freshness")
	fmt.Println("  • Traffic patterns have locality (similar requests)")
	fmt.Println()
	fmt.Println("Avoid caching when:")
	fmt.Println("  • Responses must always be fresh")
	fmt.Println("  • Requests are always unique")
	fmt.Println("  • Memory is constrained")
	fmt.Println()
}
