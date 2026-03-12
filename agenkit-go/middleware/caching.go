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

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// CacheStore is the interface for pluggable cache backends used by CachingDecorator.
type CacheStore interface {
	// Get returns the cached response for key, and whether it was found.
	Get(key string) (*agenkit.Message, bool)
	// Set stores a response under key with the given TTL.
	Set(key string, value *agenkit.Message, ttl time.Duration)
	// Delete removes the entry for key (no-op if absent).
	Delete(key string)
	// Flush removes all entries.
	Flush()
	// Size returns the number of currently cached entries.
	Size() int
}

// MemoryCacheStore implements CacheStore with an in-process LRU cache and TTL expiry.
//
// This is the default store used by CachingDecorator when no custom store is provided.
type MemoryCacheStore struct {
	mu             sync.RWMutex
	cache          map[string]*list.Element
	lruList        *list.List
	maxSize        int
	cleanupCounter int64
	onEvict        func() // optional: called by Set when an entry is evicted due to capacity
}

// NewMemoryCacheStore creates an in-process LRU cache store with the given capacity.
func NewMemoryCacheStore(maxSize int) *MemoryCacheStore {
	return &MemoryCacheStore{
		cache:   make(map[string]*list.Element),
		lruList: list.New(),
		maxSize: maxSize,
	}
}

// Get returns the cached message for key. Expired entries are treated as misses.
func (s *MemoryCacheStore) Get(key string) (*agenkit.Message, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	elem, ok := s.cache[key]
	if !ok {
		return nil, false
	}
	item := elem.Value.(*lruItem)
	if item.entry.isExpired() {
		return nil, false
	}
	return item.entry.Response, true
}

// Set stores value under key with the given TTL, evicting the LRU entry if the cache is full.
func (s *MemoryCacheStore) Set(key string, value *agenkit.Message, ttl time.Duration) {
	s.mu.Lock()
	defer s.mu.Unlock()

	// Remove stale entry for this key if present.
	if elem, ok := s.cache[key]; ok {
		s.lruList.Remove(elem)
		delete(s.cache, key)
	}

	// Periodic cleanup of expired entries (every 100 writes).
	s.cleanupCounter++
	if s.cleanupCounter%100 == 0 {
		s.cleanupExpiredLocked()
	}

	// Evict LRU entry when at capacity.
	if s.lruList.Len() >= s.maxSize {
		oldest := s.lruList.Back()
		if oldest != nil {
			evictedItem := oldest.Value.(*lruItem)
			s.lruList.Remove(oldest)
			delete(s.cache, evictedItem.key)
			if s.onEvict != nil {
				s.onEvict()
			}
		}
	}

	entry := &cacheEntry{
		Response:  value,
		ExpiresAt: time.Now().Add(ttl),
		CreatedAt: time.Now(),
	}
	item := &lruItem{key: key, entry: entry}
	elem := s.lruList.PushFront(item)
	s.cache[key] = elem
}

// Delete removes the entry for key.
func (s *MemoryCacheStore) Delete(key string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if elem, ok := s.cache[key]; ok {
		s.lruList.Remove(elem)
		delete(s.cache, key)
	}
}

// Flush removes all entries.
func (s *MemoryCacheStore) Flush() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.cache = make(map[string]*list.Element)
	s.lruList = list.New()
}

// Size returns the number of cached entries.
func (s *MemoryCacheStore) Size() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.cache)
}

// cleanupExpiredLocked removes expired entries; must be called with write lock held.
func (s *MemoryCacheStore) cleanupExpiredLocked() {
	var expired []string
	for key, elem := range s.cache {
		if elem.Value.(*lruItem).entry.isExpired() {
			expired = append(expired, key)
		}
	}
	for _, key := range expired {
		if elem, ok := s.cache[key]; ok {
			s.lruList.Remove(elem)
			delete(s.cache, key)
		}
	}
}

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

	// Store is an optional custom cache backend.
	// If nil, NewCachingDecorator creates a MemoryCacheStore.
	Store CacheStore
}

// DefaultCachingConfig returns a caching config with sensible defaults.
func DefaultCachingConfig() CachingConfig {
	return CachingConfig{
		MaxCacheSize: 1000,
		DefaultTTL:   5 * time.Minute,
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

// WithCacheStore returns a functional option that sets a custom cache store on a CachingConfig.
//
// Example:
//
//	cfg := middleware.DefaultCachingConfig()
//	middleware.WithCacheStore(redisStore)(&cfg)
//	decorator, _ := middleware.NewCachingDecorator(agent, cfg)
func WithCacheStore(store CacheStore) func(*CachingConfig) {
	return func(c *CachingConfig) { c.Store = store }
}

// CachingMetrics tracks caching middleware metrics.
type CachingMetrics struct {
	mu            sync.RWMutex
	TotalRequests int64
	CacheHits     int64
	CacheMisses   int64
	Evictions     int64
	Invalidations int64
	CurrentSize   int64
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
// - Pluggable cache backends via CacheStore (default: MemoryCacheStore with LRU + TTL)
// - Cache invalidation (specific entries or entire cache)
// - Configurable cache keys with custom key generator support
// - Thread-safe operations
// - Comprehensive metrics (hits, misses, hit rate, evictions, invalidations)
//
// Example:
//
//	agent := &MyAgent{}
//	cachingAgent, _ := middleware.NewCachingDecorator(
//		agent,
//		middleware.CachingConfig{
//			MaxCacheSize: 1000,
//			DefaultTTL:   5 * time.Minute,
//		},
//	)
//
//	result, err := cachingAgent.Process(ctx, message)
//
//	// Check cache metrics
//	fmt.Printf("Hit rate: %.2f%%\n", cachingAgent.Metrics().HitRate() * 100)
type CachingDecorator struct {
	agent   agenkit.Agent
	config  CachingConfig
	metrics *CachingMetrics
	store   CacheStore
}

// Verify that CachingDecorator implements Agent interface.
var _ agenkit.Agent = (*CachingDecorator)(nil)

// NewCachingDecorator creates a new caching decorator.
func NewCachingDecorator(agent agenkit.Agent, config CachingConfig) (*CachingDecorator, error) {
	// Apply defaults.
	if config.MaxCacheSize <= 0 {
		config.MaxCacheSize = 1000
	}
	if config.DefaultTTL <= 0 {
		config.DefaultTTL = 5 * time.Minute
	}

	if err := config.Validate(); err != nil {
		return nil, err
	}

	d := &CachingDecorator{
		agent:   agent,
		config:  config,
		metrics: NewCachingMetrics(),
	}

	// Use provided store or fall back to an in-process LRU store.
	if config.Store != nil {
		d.store = config.Store
	} else {
		ms := NewMemoryCacheStore(config.MaxCacheSize)
		ms.onEvict = func() { d.metrics.RecordEviction() }
		d.store = ms
	}

	return d, nil
}

// Name returns the name of the underlying agent.
func (c *CachingDecorator) Name() string {
	return c.agent.Name()
}

// Capabilities returns the capabilities of the underlying agent.
func (c *CachingDecorator) Capabilities() []string {
	return c.agent.Capabilities()
}

// Introspect returns the introspection result of the underlying agent.
func (c *CachingDecorator) Introspect() *agenkit.IntrospectionResult {
	return c.agent.Introspect()
}

// Metrics returns the caching metrics.
func (c *CachingDecorator) Metrics() *CachingMetrics {
	return c.metrics
}

// generateCacheKey generates a cache key from a message.
func (c *CachingDecorator) generateCacheKey(message *agenkit.Message) string {
	if c.config.KeyGenerator != nil {
		return c.config.KeyGenerator(message)
	}

	keyData := map[string]interface{}{
		"role":     message.Role,
		"content":  message.Content,
		"metadata": message.Metadata,
	}

	jsonBytes, err := json.Marshal(keyData)
	if err != nil {
		return fmt.Sprintf("%s:%s", message.Role, message.Content)
	}

	hash := sha256.Sum256(jsonBytes)
	return fmt.Sprintf("%x", hash)
}

// Process implements the Agent interface with caching.
func (c *CachingDecorator) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	cacheKey := c.generateCacheKey(message)

	if cached, ok := c.store.Get(cacheKey); ok {
		c.metrics.RecordHit()
		return cached, nil
	}
	c.metrics.RecordMiss()

	response, err := c.agent.Process(ctx, message)
	if err != nil {
		return nil, err
	}

	c.store.Set(cacheKey, response, c.config.DefaultTTL)
	c.metrics.UpdateSize(int64(c.store.Size()))

	return response, nil
}

// Invalidate invalidates cache entries.
//
// If message is provided, invalidates only that message's cache entry.
// If message is nil, invalidates the entire cache.
func (c *CachingDecorator) Invalidate(message *agenkit.Message) {
	if message != nil {
		cacheKey := c.generateCacheKey(message)
		c.store.Delete(cacheKey)
		c.metrics.RecordInvalidation()
	} else {
		count := c.store.Size()
		c.store.Flush()
		for i := 0; i < count; i++ {
			c.metrics.RecordInvalidation()
		}
	}
	c.metrics.UpdateSize(int64(c.store.Size()))
}

// GetCacheSize returns the current cache size.
func (c *CachingDecorator) GetCacheSize() int {
	return c.store.Size()
}

// GetCacheInfo returns detailed cache information.
func (c *CachingDecorator) GetCacheInfo() map[string]interface{} {
	return map[string]interface{}{
		"size":        c.store.Size(),
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
