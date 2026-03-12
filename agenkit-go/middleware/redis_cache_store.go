package middleware

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// RedisCacheStore implements CacheStore backed by Redis.
//
// Cache entries are stored as JSON-serialised agenkit.Message values with
// the provided TTL applied on every Set. Key collisions across deployments
// can be avoided with a non-empty keyPrefix.
//
// Example:
//
//	store, err := NewRedisCacheStore("redis://localhost:6379", "myagent:")
//	if err != nil {
//	    log.Fatal(err)
//	}
//	cfg := middleware.DefaultCachingConfig()
//	middleware.WithCacheStore(store)(&cfg)
//	decorator, _ := middleware.NewCachingDecorator(agent, cfg)
type RedisCacheStore struct {
	client    *redis.Client
	keyPrefix string
}

// NewRedisCacheStore creates a RedisCacheStore that connects to the given Redis URL.
//
// Args:
//
//	redisURL:  Redis connection URL (e.g. "redis://localhost:6379").
//	keyPrefix: Optional prefix prepended to every cache key.
func NewRedisCacheStore(redisURL string, keyPrefix string) (*RedisCacheStore, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("invalid redis URL: %w", err)
	}
	client := redis.NewClient(opts)

	// Verify connectivity.
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to redis: %w", err)
	}

	return &RedisCacheStore{
		client:    client,
		keyPrefix: keyPrefix,
	}, nil
}

func (s *RedisCacheStore) fullKey(key string) string {
	return s.keyPrefix + key
}

// Get returns the cached message for key, and whether it was found.
func (s *RedisCacheStore) Get(key string) (*agenkit.Message, bool) {
	ctx := context.Background()
	data, err := s.client.Get(ctx, s.fullKey(key)).Bytes()
	if err != nil {
		return nil, false
	}

	var msg agenkit.Message
	if err := json.Unmarshal(data, &msg); err != nil {
		return nil, false
	}
	return &msg, true
}

// Set stores value under key with the given TTL.
func (s *RedisCacheStore) Set(key string, value *agenkit.Message, ttl time.Duration) {
	ctx := context.Background()
	data, err := json.Marshal(value)
	if err != nil {
		return
	}
	if err := s.client.Set(ctx, s.fullKey(key), data, ttl).Err(); err != nil {
		// Best-effort; cache misses are non-fatal.
		_ = err
	}
}

// Delete removes the entry for key.
func (s *RedisCacheStore) Delete(key string) {
	ctx := context.Background()
	_ = s.client.Del(ctx, s.fullKey(key)).Err()
}

// Flush removes all keys matching this store's prefix.
//
// Note: uses SCAN + DEL which is O(N) in the number of prefixed keys.
// Avoid calling Flush on large caches in latency-sensitive paths.
func (s *RedisCacheStore) Flush() {
	ctx := context.Background()
	pattern := s.keyPrefix + "*"
	var cursor uint64
	for {
		keys, next, err := s.client.Scan(ctx, cursor, pattern, 100).Result()
		if err != nil {
			return
		}
		if len(keys) > 0 {
			_ = s.client.Del(ctx, keys...).Err()
		}
		cursor = next
		if cursor == 0 {
			break
		}
	}
}

// Size returns the approximate number of keys matching this store's prefix.
//
// Uses SCAN, so the result may be slightly stale under concurrent writes.
func (s *RedisCacheStore) Size() int {
	ctx := context.Background()
	pattern := s.keyPrefix + "*"
	var count int
	var cursor uint64
	for {
		keys, next, err := s.client.Scan(ctx, cursor, pattern, 100).Result()
		if err != nil {
			return count
		}
		count += len(keys)
		cursor = next
		if cursor == 0 {
			break
		}
	}
	return count
}

// Close closes the underlying Redis client.
func (s *RedisCacheStore) Close() error {
	return s.client.Close()
}
