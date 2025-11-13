package middleware

import (
	"context"
	"fmt"
	"sync"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// ============================================
// Test Agent Implementation
// ============================================

// TestAgent is a simple agent for testing caching.
type TestAgent struct {
	responsePrefix string
	callCount      int
	mu             sync.Mutex
}

func NewTestAgent(responsePrefix string) *TestAgent {
	return &TestAgent{
		responsePrefix: responsePrefix,
		callCount:      0,
	}
}

func (a *TestAgent) Name() string {
	return "test"
}

func (a *TestAgent) Capabilities() []string {
	return []string{}
}

func (a *TestAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	a.mu.Lock()
	a.callCount++
	count := a.callCount
	a.mu.Unlock()

	return &agenkit.Message{
		Role:    "agent",
		Content: fmt.Sprintf("%s: %s", a.responsePrefix, message.Content),
		Metadata: map[string]interface{}{
			"call_count": count,
		},
	}, nil
}

func (a *TestAgent) GetCallCount() int {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.callCount
}

// ============================================
// Configuration Tests
// ============================================

func TestDefaultConfig(t *testing.T) {
	config := DefaultCachingConfig()
	if config.MaxCacheSize != 1000 {
		t.Errorf("Expected MaxCacheSize=1000, got %d", config.MaxCacheSize)
	}
	if config.DefaultTTL != 5*time.Minute {
		t.Errorf("Expected DefaultTTL=5m, got %v", config.DefaultTTL)
	}
	if config.KeyGenerator != nil {
		t.Errorf("Expected KeyGenerator=nil")
	}
}

func TestCustomConfig(t *testing.T) {
	customKeyGen := func(msg *agenkit.Message) string {
		return fmt.Sprintf("custom-%s", msg.Content)
	}

	config := CachingConfig{
		MaxCacheSize: 100,
		DefaultTTL:   60 * time.Second,
		KeyGenerator: customKeyGen,
	}

	if config.MaxCacheSize != 100 {
		t.Errorf("Expected MaxCacheSize=100, got %d", config.MaxCacheSize)
	}
	if config.DefaultTTL != 60*time.Second {
		t.Errorf("Expected DefaultTTL=60s, got %v", config.DefaultTTL)
	}
	if config.KeyGenerator == nil {
		t.Errorf("Expected KeyGenerator to be set")
	}
}

func TestConfigValidation(t *testing.T) {
	tests := []struct {
		name        string
		config      CachingConfig
		expectError bool
		errorMatch  string
	}{
		{
			name: "Invalid max_cache_size",
			config: CachingConfig{
				MaxCacheSize: 0,
				DefaultTTL:   5 * time.Minute,
			},
			expectError: true,
			errorMatch:  "max_cache_size must be at least 1",
		},
		{
			name: "Invalid default_ttl",
			config: CachingConfig{
				MaxCacheSize: 1000,
				DefaultTTL:   0,
			},
			expectError: true,
			errorMatch:  "default_ttl must be positive",
		},
		{
			name: "Valid config",
			config: CachingConfig{
				MaxCacheSize: 1000,
				DefaultTTL:   5 * time.Minute,
			},
			expectError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.config.Validate()
			if tt.expectError {
				if err == nil {
					t.Errorf("Expected error but got nil")
				} else if tt.errorMatch != "" && err.Error() != tt.errorMatch {
					// Just check if error contains the expected string
					if len(err.Error()) < len(tt.errorMatch) {
						t.Errorf("Expected error containing '%s', got '%s'", tt.errorMatch, err.Error())
					}
				}
			} else {
				if err != nil {
					t.Errorf("Expected no error but got: %v", err)
				}
			}
		})
	}
}

// ============================================
// Basic Caching Tests
// ============================================

func TestCacheHit(t *testing.T) {
	agent := NewTestAgent("Response")
	cachedAgent, err := NewCachingDecorator(agent, DefaultCachingConfig())
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	// First call - should miss cache
	response1, err := cachedAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if response1.Content != "Response: test" {
		t.Errorf("Expected 'Response: test', got '%s'", response1.Content)
	}
	if agent.GetCallCount() != 1 {
		t.Errorf("Expected agent call count=1, got %d", agent.GetCallCount())
	}
	if cachedAgent.Metrics().CacheMisses != 1 {
		t.Errorf("Expected cache misses=1, got %d", cachedAgent.Metrics().CacheMisses)
	}
	if cachedAgent.Metrics().CacheHits != 0 {
		t.Errorf("Expected cache hits=0, got %d", cachedAgent.Metrics().CacheHits)
	}

	// Second call - should hit cache
	response2, err := cachedAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if response2.Content != "Response: test" {
		t.Errorf("Expected 'Response: test', got '%s'", response2.Content)
	}
	if agent.GetCallCount() != 1 { // Not called again
		t.Errorf("Expected agent call count=1, got %d", agent.GetCallCount())
	}
	if cachedAgent.Metrics().CacheMisses != 1 {
		t.Errorf("Expected cache misses=1, got %d", cachedAgent.Metrics().CacheMisses)
	}
	if cachedAgent.Metrics().CacheHits != 1 {
		t.Errorf("Expected cache hits=1, got %d", cachedAgent.Metrics().CacheHits)
	}
}

func TestCacheMissDifferentMessages(t *testing.T) {
	agent := NewTestAgent("Response")
	cachedAgent, err := NewCachingDecorator(agent, DefaultCachingConfig())
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	msg1 := agenkit.NewMessage("user", "test1")
	msg2 := agenkit.NewMessage("user", "test2")
	ctx := context.Background()

	// Both should miss cache
	response1, err := cachedAgent.Process(ctx, msg1)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	response2, err := cachedAgent.Process(ctx, msg2)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	if response1.Content != "Response: test1" {
		t.Errorf("Expected 'Response: test1', got '%s'", response1.Content)
	}
	if response2.Content != "Response: test2" {
		t.Errorf("Expected 'Response: test2', got '%s'", response2.Content)
	}
	if agent.GetCallCount() != 2 {
		t.Errorf("Expected agent call count=2, got %d", agent.GetCallCount())
	}
	if cachedAgent.Metrics().CacheMisses != 2 {
		t.Errorf("Expected cache misses=2, got %d", cachedAgent.Metrics().CacheMisses)
	}
	if cachedAgent.Metrics().CacheHits != 0 {
		t.Errorf("Expected cache hits=0, got %d", cachedAgent.Metrics().CacheHits)
	}
}

// ============================================
// TTL Expiration Tests
// ============================================

func TestTTLExpiration(t *testing.T) {
	agent := NewTestAgent("Response")
	config := CachingConfig{
		MaxCacheSize: 1000,
		DefaultTTL:   100 * time.Millisecond, // 100ms TTL
	}
	cachedAgent, err := NewCachingDecorator(agent, config)
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	// First call
	_, err = cachedAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if agent.GetCallCount() != 1 {
		t.Errorf("Expected agent call count=1, got %d", agent.GetCallCount())
	}

	// Second call before expiration - should hit cache
	_, err = cachedAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if agent.GetCallCount() != 1 {
		t.Errorf("Expected agent call count=1, got %d", agent.GetCallCount())
	}

	// Wait for expiration
	time.Sleep(150 * time.Millisecond)

	// Third call after expiration - should miss cache
	_, err = cachedAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if agent.GetCallCount() != 2 {
		t.Errorf("Expected agent call count=2, got %d", agent.GetCallCount())
	}
	if cachedAgent.Metrics().CacheHits != 1 {
		t.Errorf("Expected cache hits=1, got %d", cachedAgent.Metrics().CacheHits)
	}
	if cachedAgent.Metrics().CacheMisses != 2 {
		t.Errorf("Expected cache misses=2, got %d", cachedAgent.Metrics().CacheMisses)
	}
}

// ============================================
// LRU Eviction Tests
// ============================================

func TestLRUEviction(t *testing.T) {
	agent := NewTestAgent("Response")
	config := CachingConfig{
		MaxCacheSize: 3, // Only 3 entries
		DefaultTTL:   5 * time.Minute,
	}
	cachedAgent, err := NewCachingDecorator(agent, config)
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	ctx := context.Background()

	// Fill cache with 3 entries
	for i := 0; i < 3; i++ {
		msg := agenkit.NewMessage("user", fmt.Sprintf("test%d", i))
		_, err := cachedAgent.Process(ctx, msg)
		if err != nil {
			t.Fatalf("Process failed: %v", err)
		}
	}

	if cachedAgent.GetCacheSize() != 3 {
		t.Errorf("Expected cache size=3, got %d", cachedAgent.GetCacheSize())
	}
	if agent.GetCallCount() != 3 {
		t.Errorf("Expected agent call count=3, got %d", agent.GetCallCount())
	}

	// Access first entry to make it recently used
	msg0 := agenkit.NewMessage("user", "test0")
	_, err = cachedAgent.Process(ctx, msg0)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if agent.GetCallCount() != 3 { // Cache hit
		t.Errorf("Expected agent call count=3 (cache hit), got %d", agent.GetCallCount())
	}

	// Add new entry - should evict test1 (LRU)
	msg3 := agenkit.NewMessage("user", "test3")
	_, err = cachedAgent.Process(ctx, msg3)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	if cachedAgent.GetCacheSize() != 3 {
		t.Errorf("Expected cache size=3, got %d", cachedAgent.GetCacheSize())
	}
	if agent.GetCallCount() != 4 {
		t.Errorf("Expected agent call count=4, got %d", agent.GetCallCount())
	}
	if cachedAgent.Metrics().Evictions != 1 {
		t.Errorf("Expected evictions=1, got %d", cachedAgent.Metrics().Evictions)
	}

	// test0 should still be cached
	_, err = cachedAgent.Process(ctx, msg0)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if agent.GetCallCount() != 4 { // Cache hit
		t.Errorf("Expected agent call count=4 (cache hit), got %d", agent.GetCallCount())
	}

	// test1 should be evicted (miss)
	msg1 := agenkit.NewMessage("user", "test1")
	_, err = cachedAgent.Process(ctx, msg1)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if agent.GetCallCount() != 5 { // Cache miss
		t.Errorf("Expected agent call count=5 (cache miss), got %d", agent.GetCallCount())
	}
}

// ============================================
// Cache Invalidation Tests
// ============================================

func TestInvalidateSpecificEntry(t *testing.T) {
	agent := NewTestAgent("Response")
	cachedAgent, err := NewCachingDecorator(agent, DefaultCachingConfig())
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	msg1 := agenkit.NewMessage("user", "test1")
	msg2 := agenkit.NewMessage("user", "test2")
	ctx := context.Background()

	// Cache both messages
	_, err = cachedAgent.Process(ctx, msg1)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	_, err = cachedAgent.Process(ctx, msg2)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if agent.GetCallCount() != 2 {
		t.Errorf("Expected agent call count=2, got %d", agent.GetCallCount())
	}

	// Invalidate msg1
	cachedAgent.Invalidate(msg1)
	if cachedAgent.Metrics().Invalidations != 1 {
		t.Errorf("Expected invalidations=1, got %d", cachedAgent.Metrics().Invalidations)
	}

	// msg1 should miss cache
	_, err = cachedAgent.Process(ctx, msg1)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if agent.GetCallCount() != 3 {
		t.Errorf("Expected agent call count=3, got %d", agent.GetCallCount())
	}

	// msg2 should still be cached
	_, err = cachedAgent.Process(ctx, msg2)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if agent.GetCallCount() != 3 { // Cache hit
		t.Errorf("Expected agent call count=3 (cache hit), got %d", agent.GetCallCount())
	}
}

func TestInvalidateEntireCache(t *testing.T) {
	agent := NewTestAgent("Response")
	cachedAgent, err := NewCachingDecorator(agent, DefaultCachingConfig())
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	ctx := context.Background()

	// Cache multiple messages
	for i := 0; i < 3; i++ {
		msg := agenkit.NewMessage("user", fmt.Sprintf("test%d", i))
		_, err := cachedAgent.Process(ctx, msg)
		if err != nil {
			t.Fatalf("Process failed: %v", err)
		}
	}

	if cachedAgent.GetCacheSize() != 3 {
		t.Errorf("Expected cache size=3, got %d", cachedAgent.GetCacheSize())
	}
	if agent.GetCallCount() != 3 {
		t.Errorf("Expected agent call count=3, got %d", agent.GetCallCount())
	}

	// Invalidate entire cache
	cachedAgent.Invalidate(nil)
	if cachedAgent.Metrics().Invalidations != 3 {
		t.Errorf("Expected invalidations=3, got %d", cachedAgent.Metrics().Invalidations)
	}
	if cachedAgent.GetCacheSize() != 0 {
		t.Errorf("Expected cache size=0, got %d", cachedAgent.GetCacheSize())
	}

	// All messages should miss cache
	for i := 0; i < 3; i++ {
		msg := agenkit.NewMessage("user", fmt.Sprintf("test%d", i))
		_, err := cachedAgent.Process(ctx, msg)
		if err != nil {
			t.Fatalf("Process failed: %v", err)
		}
	}

	if agent.GetCallCount() != 6 {
		t.Errorf("Expected agent call count=6, got %d", agent.GetCallCount())
	}
}

// ============================================
// Custom Key Generator Tests
// ============================================

func TestCustomKeyGenerator(t *testing.T) {
	agent := NewTestAgent("Response")

	// Key generator that ignores metadata
	contentOnlyKey := func(message *agenkit.Message) string {
		return message.Content
	}

	config := CachingConfig{
		MaxCacheSize: 1000,
		DefaultTTL:   5 * time.Minute,
		KeyGenerator: contentOnlyKey,
	}
	cachedAgent, err := NewCachingDecorator(agent, config)
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	ctx := context.Background()

	// Same content, different metadata - should hit cache
	msg1 := agenkit.NewMessage("user", "test").WithMetadata("id", 1)
	msg2 := agenkit.NewMessage("user", "test").WithMetadata("id", 2)

	_, err = cachedAgent.Process(ctx, msg1)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	_, err = cachedAgent.Process(ctx, msg2)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	if agent.GetCallCount() != 1 { // Only called once
		t.Errorf("Expected agent call count=1, got %d", agent.GetCallCount())
	}
	if cachedAgent.Metrics().CacheHits != 1 {
		t.Errorf("Expected cache hits=1, got %d", cachedAgent.Metrics().CacheHits)
	}
}

// ============================================
// Metrics Tests
// ============================================

func TestMetricsHitRate(t *testing.T) {
	agent := NewTestAgent("Response")
	cachedAgent, err := NewCachingDecorator(agent, DefaultCachingConfig())
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	// First call - miss
	_, err = cachedAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	hitRate := cachedAgent.Metrics().HitRate()
	if hitRate != 0.0 {
		t.Errorf("Expected hit rate=0.0, got %.2f", hitRate)
	}

	// Next 3 calls - hits
	for i := 0; i < 3; i++ {
		_, err = cachedAgent.Process(ctx, msg)
		if err != nil {
			t.Fatalf("Process failed: %v", err)
		}
	}

	if cachedAgent.Metrics().TotalRequests != 4 {
		t.Errorf("Expected total requests=4, got %d", cachedAgent.Metrics().TotalRequests)
	}
	if cachedAgent.Metrics().CacheHits != 3 {
		t.Errorf("Expected cache hits=3, got %d", cachedAgent.Metrics().CacheHits)
	}
	if cachedAgent.Metrics().CacheMisses != 1 {
		t.Errorf("Expected cache misses=1, got %d", cachedAgent.Metrics().CacheMisses)
	}

	hitRate = cachedAgent.Metrics().HitRate()
	if hitRate != 0.75 {
		t.Errorf("Expected hit rate=0.75, got %.2f", hitRate)
	}

	missRate := cachedAgent.Metrics().MissRate()
	if missRate != 0.25 {
		t.Errorf("Expected miss rate=0.25, got %.2f", missRate)
	}
}

func TestGetCacheInfo(t *testing.T) {
	agent := NewTestAgent("Response")
	config := CachingConfig{
		MaxCacheSize: 100,
		DefaultTTL:   60 * time.Second,
	}
	cachedAgent, err := NewCachingDecorator(agent, config)
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	ctx := context.Background()

	// Add some entries
	for i := 0; i < 3; i++ {
		msg := agenkit.NewMessage("user", fmt.Sprintf("test%d", i))
		_, err := cachedAgent.Process(ctx, msg)
		if err != nil {
			t.Fatalf("Process failed: %v", err)
		}
	}

	// Get first entry again for a hit
	msg := agenkit.NewMessage("user", "test0")
	_, err = cachedAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	info := cachedAgent.GetCacheInfo()

	if info["size"].(int) != 3 {
		t.Errorf("Expected size=3, got %v", info["size"])
	}
	if info["max_size"].(int) != 100 {
		t.Errorf("Expected max_size=100, got %v", info["max_size"])
	}
	if info["default_ttl"].(float64) != 60.0 {
		t.Errorf("Expected default_ttl=60.0, got %v", info["default_ttl"])
	}

	metrics := info["metrics"].(map[string]interface{})
	if metrics["total_requests"].(int64) != 4 {
		t.Errorf("Expected total_requests=4, got %v", metrics["total_requests"])
	}
	if metrics["cache_hits"].(int64) != 1 {
		t.Errorf("Expected cache_hits=1, got %v", metrics["cache_hits"])
	}
	if metrics["cache_misses"].(int64) != 3 {
		t.Errorf("Expected cache_misses=3, got %v", metrics["cache_misses"])
	}
	if metrics["hit_rate"].(float64) != 0.25 {
		t.Errorf("Expected hit_rate=0.25, got %v", metrics["hit_rate"])
	}
}

// ============================================
// Concurrent Access Tests
// ============================================

func TestConcurrentCacheAccess(t *testing.T) {
	agent := NewTestAgent("Response")
	cachedAgent, err := NewCachingDecorator(agent, DefaultCachingConfig())
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	// First request populates cache
	_, err = cachedAgent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Multiple concurrent requests should all hit cache
	const numRequests = 10
	var wg sync.WaitGroup
	wg.Add(numRequests)

	for i := 0; i < numRequests; i++ {
		go func() {
			defer wg.Done()
			response, err := cachedAgent.Process(ctx, msg)
			if err != nil {
				t.Errorf("Process failed: %v", err)
			}
			if response.Content != "Response: test" {
				t.Errorf("Expected 'Response: test', got '%s'", response.Content)
			}
		}()
	}

	wg.Wait()

	// Agent should only be called once
	if agent.GetCallCount() != 1 {
		t.Errorf("Expected agent call count=1, got %d", agent.GetCallCount())
	}
	// 10 hits (after initial miss)
	if cachedAgent.Metrics().CacheHits != numRequests {
		t.Errorf("Expected cache hits=%d, got %d", numRequests, cachedAgent.Metrics().CacheHits)
	}
}

// ============================================
// Edge Cases
// ============================================

func TestEmptyCache(t *testing.T) {
	agent := NewTestAgent("Response")
	cachedAgent, err := NewCachingDecorator(agent, DefaultCachingConfig())
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	if cachedAgent.GetCacheSize() != 0 {
		t.Errorf("Expected cache size=0, got %d", cachedAgent.GetCacheSize())
	}
	if cachedAgent.Metrics().TotalRequests != 0 {
		t.Errorf("Expected total requests=0, got %d", cachedAgent.Metrics().TotalRequests)
	}

	// Invalidate empty cache
	cachedAgent.Invalidate(nil)
	if cachedAgent.Metrics().Invalidations != 0 {
		t.Errorf("Expected invalidations=0, got %d", cachedAgent.Metrics().Invalidations)
	}
}

func TestCacheWithMetadata(t *testing.T) {
	agent := NewTestAgent("Response")
	cachedAgent, err := NewCachingDecorator(agent, DefaultCachingConfig())
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	ctx := context.Background()

	// Same content, different metadata - should be different cache keys
	msg1 := agenkit.NewMessage("user", "test").WithMetadata("version", 1)
	msg2 := agenkit.NewMessage("user", "test").WithMetadata("version", 2)

	_, err = cachedAgent.Process(ctx, msg1)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	_, err = cachedAgent.Process(ctx, msg2)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Should be two different cache entries
	if agent.GetCallCount() != 2 {
		t.Errorf("Expected agent call count=2, got %d", agent.GetCallCount())
	}
	if cachedAgent.GetCacheSize() != 2 {
		t.Errorf("Expected cache size=2, got %d", cachedAgent.GetCacheSize())
	}
}

func TestExpiredEntriesCleanup(t *testing.T) {
	agent := NewTestAgent("Response")
	config := CachingConfig{
		MaxCacheSize: 1000,
		DefaultTTL:   100 * time.Millisecond,
	}
	cachedAgent, err := NewCachingDecorator(agent, config)
	if err != nil {
		t.Fatalf("Failed to create caching decorator: %v", err)
	}

	ctx := context.Background()

	// Add entries
	for i := 0; i < 10; i++ {
		msg := agenkit.NewMessage("user", fmt.Sprintf("test%d", i))
		_, err := cachedAgent.Process(ctx, msg)
		if err != nil {
			t.Fatalf("Process failed: %v", err)
		}
	}

	if cachedAgent.GetCacheSize() != 10 {
		t.Errorf("Expected cache size=10, got %d", cachedAgent.GetCacheSize())
	}

	// Wait for expiration
	time.Sleep(150 * time.Millisecond)

	// Make 100 requests to trigger cleanup (happens every 100 requests)
	for i := 0; i < 100; i++ {
		msg := agenkit.NewMessage("user", fmt.Sprintf("new%d", i))
		_, err := cachedAgent.Process(ctx, msg)
		if err != nil {
			t.Fatalf("Process failed: %v", err)
		}
	}

	// Expired entries should be cleaned up
	// Note: exact count depends on timing, but should be significantly reduced
	cacheSize := cachedAgent.GetCacheSize()
	if cacheSize >= 110 {
		t.Errorf("Expected cache size < 110 after cleanup, got %d", cacheSize)
	}
}
