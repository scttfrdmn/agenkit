// Package middleware provides reusable middleware for agents.
package middleware

import (
	"container/list"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// CachingConfig configures caching behavior.
type CachingConfig struct {
	// MaxCacheSize is the maximum number of entries in the cache.
	// Default: 1000
	MaxCacheSize int

	// DefaultTTL is the time-to-live for cache entries.
	// Default: 5 minutes
	DefaultTTL time.Duration

	// KeyGenerator is an optional custom function to generate cache keys.
	// If nil, a default SHA256-based key generator is used.
	KeyGenerator func(*agenkit.Message) string
}

// DefaultCachingConfig returns a caching config with sensible defaults.
func DefaultCachingConfig() CachingConfig {
	return CachingConfig{
		MaxCacheSize: 1000,
		DefaultTTL:   5 * time.Minute,
		KeyGenerator: nil,
	}
}

// Validate validates the caching configuration.
func (c *CachingConfig) Validate() error {
	if c.MaxCacheSize < 1 {
		return fmt.Errorf("max_cache_size must be at least 1, got %d", c.MaxCacheSize)
	}
	if c.DefaultTTL <= 0 {
		return fmt.Errorf("default_ttl must be positive, got %v", c.DefaultTTL)
	}
	return nil
}

// CachingMetrics tracks caching middleware metrics.
type CachingMetrics struct {
	mu              sync.RWMutex
	TotalRequests   int64
	CacheHits       int64
	CacheMisses     int64
	Evictions       int64
	Invalidations   int64
	CurrentSize     int64
}

// NewCachingMetrics creates a new metrics instance.
func NewCachingMetrics() *CachingMetrics {
	return &CachingMetrics{}
}

// RecordHit records a cache hit.
func (m *CachingMetrics) RecordHit() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.TotalRequests++
	m.CacheHits++
}

// RecordMiss records a cache miss.
func (m *CachingMetrics) RecordMiss() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.TotalRequests++
	m.CacheMisses++
}

// RecordEviction records a cache eviction.
func (m *CachingMetrics) RecordEviction() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.Evictions++
}

// RecordInvalidation records a cache invalidation.
func (m *CachingMetrics) RecordInvalidation() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.Invalidations++
}

// UpdateSize updates the current cache size.
func (m *CachingMetrics) UpdateSize(size int64) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.CurrentSize = size
}

// HitRate returns the cache hit rate.
func (m *CachingMetrics) HitRate() float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if m.TotalRequests == 0 {
		return 0.0
	}
	return float64(m.CacheHits) / float64(m.TotalRequests)
}

// MissRate returns the cache miss rate.
func (m *CachingMetrics) MissRate() float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if m.TotalRequests == 0 {
		return 0.0
	}
	return float64(m.CacheMisses) / float64(m.TotalRequests)
}

// GetStats returns a snapshot of all metrics.
func (m *CachingMetrics) GetStats() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	return map[string]interface{}{
		"total_requests": m.TotalRequests,
		"cache_hits":     m.CacheHits,
		"cache_misses":   m.CacheMisses,
		"hit_rate":       float64(m.CacheHits) / float64(max(m.TotalRequests, 1)),
		"miss_rate":      float64(m.CacheMisses) / float64(max(m.TotalRequests, 1)),
		"evictions":      m.Evictions,
		"invalidations":  m.Invalidations,
	}
}

// cacheEntry represents an entry in the cache with expiration.
type cacheEntry struct {
	Response  *agenkit.Message
	ExpiresAt time.Time
	CreatedAt time.Time
}

// isExpired checks if the entry is expired.
func (e *cacheEntry) isExpired() bool {
	return time.Now().After(e.ExpiresAt)
}

// lruItem represents an item in the LRU list.
type lruItem struct {
	key   string
	entry *cacheEntry
}

// CachingDecorator wraps an agent with caching.
//
// The caching middleware reduces latency and cost by caching agent responses.
// It implements:
//
// - LRU (Least Recently Used) eviction when cache is full
// - TTL (Time To Live) based expiration with automatic cleanup
// - Cache invalidation (specific entries or entire cache)
// - Configurable cache keys with custom key generator support
// - Thread-safe operations with sync.Mutex
// - Comprehensive metrics (hits, misses, hit rate, evictions, invalidations)
//
// Example:
//
//	agent := &MyAgent{}
//	cachingAgent := middleware.NewCachingDecorator(
//		agent,
//		middleware.CachingConfig{
//			MaxCacheSize: 1000,
//			DefaultTTL:   5 * time.Minute,
//		},
//	)
//
//	ctx := context.Background()
//	result, err := cachingAgent.Process(ctx, message)
//	if err != nil {
//		log.Fatal(err)
//	}
//
//	// Check cache metrics
//	fmt.Printf("Hit rate: %.2f%%\n", cachingAgent.Metrics().HitRate() * 100)
type CachingDecorator struct {
	agent   agenkit.Agent
	config  CachingConfig
	metrics *CachingMetrics

	mu       sync.Mutex
	cache    map[string]*list.Element // key -> list element
	lruList  *list.List                // doubly linked list for LRU
	cleanupCounter int64
}

// Verify that CachingDecorator implements Agent interface.
var _ agenkit.Agent = (*CachingDecorator)(nil)

// NewCachingDecorator creates a new caching decorator.
func NewCachingDecorator(agent agenkit.Agent, config CachingConfig) (*CachingDecorator, error) {
	// Apply defaults
	if config.MaxCacheSize <= 0 {
		config.MaxCacheSize = 1000
	}
	if config.DefaultTTL <= 0 {
		config.DefaultTTL = 5 * time.Minute
	}

	// Validate config
	if err := config.Validate(); err != nil {
		return nil, err
	}

	return &CachingDecorator{
		agent:   agent,
		config:  config,
		metrics: NewCachingMetrics(),
		cache:   make(map[string]*list.Element),
		lruList: list.New(),
	}, nil
}

// Name returns the name of the underlying agent.
func (c *CachingDecorator) Name() string {
	return c.agent.Name()
}

// Capabilities returns the capabilities of the underlying agent.
func (c *CachingDecorator) Capabilities() []string {
	return c.agent.Capabilities()
}

// Metrics returns the caching metrics.
func (c *CachingDecorator) Metrics() *CachingMetrics {
	return c.metrics
}

// generateCacheKey generates a cache key from a message.
func (c *CachingDecorator) generateCacheKey(message *agenkit.Message) string {
	// Use custom key generator if provided
	if c.config.KeyGenerator != nil {
		return c.config.KeyGenerator(message)
	}

	// Default key generation: hash of role + content + metadata
	keyData := map[string]interface{}{
		"role":     message.Role,
		"content":  message.Content,
		"metadata": message.Metadata,
	}

	jsonBytes, err := json.Marshal(keyData)
	if err != nil {
		// Fallback to simple string concatenation
		return fmt.Sprintf("%s:%s", message.Role, message.Content)
	}

	hash := sha256.Sum256(jsonBytes)
	return fmt.Sprintf("%x", hash)
}

// evictLRU evicts the least recently used entry if cache is full.
func (c *CachingDecorator) evictLRU() {
	if c.lruList.Len() >= c.config.MaxCacheSize {
		// Remove oldest (least recently used) entry
		oldest := c.lruList.Back()
		if oldest != nil {
			item := oldest.Value.(*lruItem)
			c.lruList.Remove(oldest)
			delete(c.cache, item.key)
			c.metrics.RecordEviction()
			c.metrics.UpdateSize(int64(len(c.cache)))
		}
	}
}

// cleanupExpired removes expired entries from cache.
func (c *CachingDecorator) cleanupExpired() {
	var expiredKeys []string

	// Find expired entries
	for key, elem := range c.cache {
		item := elem.Value.(*lruItem)
		if item.entry.isExpired() {
			expiredKeys = append(expiredKeys, key)
		}
	}

	// Remove expired entries
	for _, key := range expiredKeys {
		if elem, ok := c.cache[key]; ok {
			c.lruList.Remove(elem)
			delete(c.cache, key)
			c.metrics.RecordEviction()
		}
	}

	if len(expiredKeys) > 0 {
		c.metrics.UpdateSize(int64(len(c.cache)))
	}
}

// Process implements the Agent interface with caching.
func (c *CachingDecorator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	c.mu.Lock()

	// Generate cache key
	cacheKey := c.generateCacheKey(message)

	// Check cache
	if elem, ok := c.cache[cacheKey]; ok {
		item := elem.Value.(*lruItem)

		// Check if expired
		if !item.entry.isExpired() {
			// Move to front (mark as recently used)
			c.lruList.MoveToFront(elem)
			c.metrics.RecordHit()
			response := item.entry.Response
			c.mu.Unlock()
			return response, nil
		}

		// Remove expired entry
		c.lruList.Remove(elem)
		delete(c.cache, cacheKey)
		c.metrics.RecordEviction()
		c.metrics.UpdateSize(int64(len(c.cache)))
	}

	// Cache miss
	c.metrics.RecordMiss()

	// Periodic cleanup (every 100 requests)
	c.cleanupCounter++
	if c.cleanupCounter%100 == 0 {
		c.cleanupExpired()
	}

	c.mu.Unlock()

	// Process message (outside lock to avoid blocking cache reads)
	response, err := c.agent.Process(ctx, message)
	if err != nil {
		return nil, err
	}

	// Cache response
	c.mu.Lock()
	defer c.mu.Unlock()

	// Evict LRU if needed
	c.evictLRU()

	// Add to cache
	entry := &cacheEntry{
		Response:  response,
		ExpiresAt: time.Now().Add(c.config.DefaultTTL),
		CreatedAt: time.Now(),
	}

	item := &lruItem{
		key:   cacheKey,
		entry: entry,
	}

	elem := c.lruList.PushFront(item)
	c.cache[cacheKey] = elem
	c.metrics.UpdateSize(int64(len(c.cache)))

	return response, nil
}

// Invalidate invalidates cache entries.
//
// If message is provided, invalidates only that message's cache entry.
// If message is nil, invalidates the entire cache.
func (c *CachingDecorator) Invalidate(message *agenkit.Message) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if message != nil {
		// Invalidate specific entry
		cacheKey := c.generateCacheKey(message)
		if elem, ok := c.cache[cacheKey]; ok {
			c.lruList.Remove(elem)
			delete(c.cache, cacheKey)
			c.metrics.RecordInvalidation()
			c.metrics.UpdateSize(int64(len(c.cache)))
		}
	} else {
		// Invalidate entire cache
		count := len(c.cache)
		c.cache = make(map[string]*list.Element)
		c.lruList = list.New()
		for i := 0; i < count; i++ {
			c.metrics.RecordInvalidation()
		}
		c.metrics.UpdateSize(0)
	}
}

// GetCacheSize returns the current cache size.
func (c *CachingDecorator) GetCacheSize() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return len(c.cache)
}

// GetCacheInfo returns detailed cache information.
func (c *CachingDecorator) GetCacheInfo() map[string]interface{} {
	c.mu.Lock()
	size := len(c.cache)
	c.mu.Unlock()

	return map[string]interface{}{
		"size":        size,
		"max_size":    c.config.MaxCacheSize,
		"default_ttl": c.config.DefaultTTL.Seconds(),
		"metrics":     c.metrics.GetStats(),
	}
}

// Helper function for max
func max(a, b int64) int64 {
	if a > b {
		return a
	}
	return b
}
