package memory

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/redis/go-redis/v9"
)

// RedisMemory provides Redis-backed memory with TTL and pub/sub.
//
// Features:
//   - Persistent storage (survives restarts)
//   - TTL support (automatic expiry)
//   - Multi-instance agents (shared memory)
//   - Fast access (in-memory Redis)
//   - Scalable (Redis cluster support)
//
// Use cases:
//   - Production deployments
//   - Multi-instance agents
//   - When persistence needed
//   - Shared memory across agents
//
// Example:
//
//	memory := NewRedisMemory("redis://localhost:6379", 86400, "agenkit:memory")
//	err := memory.Store(ctx, "session-123", message, nil)
//	messages, err := memory.Retrieve(ctx, "session-123", RetrieveOptions{Limit: 10})
//
// Redis Data Structure:
//   - Key: "agenkit:memory:{session_id}:messages"
//   - Type: Sorted Set (ZSET)
//   - Score: Timestamp (for ordering)
//   - Value: JSON(message, metadata)
type RedisMemory struct {
	redisURL  string
	ttl       time.Duration
	keyPrefix string
	client    *redis.Client
}

// NewRedisMemory creates a new Redis-backed memory instance.
//
// Args:
//
//	redisURL: Redis connection URL
//	ttlSeconds: Time-to-live in seconds (0 = no expiry)
//	keyPrefix: Prefix for Redis keys
//
// Example:
//
//	memory := NewRedisMemory("redis://localhost:6379", 86400, "agenkit:memory")
func NewRedisMemory(redisURL string, ttlSeconds int, keyPrefix string) (*RedisMemory, error) {
	// Parse Redis URL
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("invalid Redis URL: %w", err)
	}

	client := redis.NewClient(opts)

	return &RedisMemory{
		redisURL:  redisURL,
		ttl:       time.Duration(ttlSeconds) * time.Second,
		keyPrefix: keyPrefix,
		client:    client,
	}, nil
}

// sessionKey returns the Redis key for a session.
func (r *RedisMemory) sessionKey(sessionID string) string {
	return fmt.Sprintf("%s:%s:messages", r.keyPrefix, sessionID)
}

// serializeMessage serializes a message and metadata to JSON.
func (r *RedisMemory) serializeMessage(message agenkit.Message, metadata map[string]interface{}) (string, error) {
	data := map[string]interface{}{
		"role":     message.Role,
		"content":  message.Content,
		"metadata": metadata,
	}
	bytes, err := json.Marshal(data)
	if err != nil {
		return "", fmt.Errorf("failed to serialize message: %w", err)
	}
	return string(bytes), nil
}

// deserializeMessage deserializes JSON to message and metadata.
func (r *RedisMemory) deserializeMessage(data string) (agenkit.Message, map[string]interface{}, error) {
	var parsed map[string]interface{}
	if err := json.Unmarshal([]byte(data), &parsed); err != nil {
		return agenkit.Message{}, nil, fmt.Errorf("failed to deserialize message: %w", err)
	}

	role, _ := parsed["role"].(string)
	content, _ := parsed["content"].(string)
	metadata, _ := parsed["metadata"].(map[string]interface{})
	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	message := agenkit.Message{
		Role:    role,
		Content: content,
	}

	return message, metadata, nil
}

// Store saves a message to Redis with optional metadata.
func (r *RedisMemory) Store(ctx context.Context, sessionID string, message agenkit.Message, metadata map[string]interface{}) error {
	// Serialize
	timestamp := float64(time.Now().UnixNano()) / 1e9
	if metadata == nil {
		metadata = make(map[string]interface{})
	}
	value, err := r.serializeMessage(message, metadata)
	if err != nil {
		return err
	}

	// Store in sorted set (score = timestamp)
	key := r.sessionKey(sessionID)
	if err := r.client.ZAdd(ctx, key, redis.Z{
		Score:  timestamp,
		Member: value,
	}).Err(); err != nil {
		return fmt.Errorf("failed to store message: %w", err)
	}

	// Set TTL if configured
	if r.ttl > 0 {
		if err := r.client.Expire(ctx, key, r.ttl).Err(); err != nil {
			return fmt.Errorf("failed to set TTL: %w", err)
		}
	}

	return nil
}

// Retrieve fetches messages from Redis.
//
// Supports filtering by:
//   - TimeRange: Filter by time range
//   - ImportanceThreshold: Filter by importance score
//   - Tags: Filter by tags
func (r *RedisMemory) Retrieve(ctx context.Context, sessionID string, opts RetrieveOptions) ([]agenkit.Message, error) {
	key := r.sessionKey(sessionID)

	// Set default limit
	limit := opts.Limit
	if limit <= 0 {
		limit = 10
	}

	// Get messages (most recent first)
	// ZREVRANGE returns highest scores first
	values, err := r.client.ZRevRangeWithScores(ctx, key, 0, -1).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to retrieve messages: %w", err)
	}

	if len(values) == 0 {
		return []agenkit.Message{}, nil
	}

	// Deserialize and filter
	filtered := make([]agenkit.Message, 0)
	for _, value := range values {
		data, ok := value.Member.(string)
		if !ok {
			continue
		}

		message, metadata, err := r.deserializeMessage(data)
		if err != nil {
			continue // Skip malformed messages
		}

		timestamp := int64(value.Score)

		// Time range filter
		if opts.TimeRange != nil {
			if timestamp < opts.TimeRange.Start || timestamp > opts.TimeRange.End {
				continue
			}
		}

		// Importance threshold filter
		if opts.ImportanceThreshold != nil {
			importance := 0.0
			if val, ok := metadata["importance"]; ok {
				if f, ok := val.(float64); ok {
					importance = f
				}
			}
			if importance < *opts.ImportanceThreshold {
				continue
			}
		}

		// Tags filter
		if len(opts.Tags) > 0 {
			requiredTags := make(map[string]bool)
			for _, tag := range opts.Tags {
				requiredTags[tag] = true
			}

			messageTags := make(map[string]bool)
			if val, ok := metadata["tags"]; ok {
				if tags, ok := val.([]interface{}); ok {
					for _, tag := range tags {
						if str, ok := tag.(string); ok {
							messageTags[str] = true
						}
					}
				} else if tags, ok := val.([]string); ok {
					for _, tag := range tags {
						messageTags[tag] = true
					}
				}
			}

			// Check if any required tag exists in message tags
			hasTag := false
			for tag := range requiredTags {
				if messageTags[tag] {
					hasTag = true
					break
				}
			}
			if !hasTag {
				continue
			}
		}

		filtered = append(filtered, message)

		if len(filtered) >= limit {
			break
		}
	}

	// Return up to limit
	if len(filtered) > limit {
		filtered = filtered[:limit]
	}

	return filtered, nil
}

// Summarize creates a summary of conversation history.
//
// Simple implementation: Returns a message with concatenated content.
// Production use should use LLM-based summarization.
func (r *RedisMemory) Summarize(ctx context.Context, sessionID string, opts SummarizeOptions) (agenkit.Message, error) {
	messages, err := r.Retrieve(ctx, sessionID, RetrieveOptions{Limit: 100})
	if err != nil {
		return agenkit.Message{}, err
	}

	if len(messages) == 0 {
		return agenkit.Message{
			Role:    "system",
			Content: "No messages in session.",
		}, nil
	}

	// Simple concatenation summary
	summaryParts := make([]string, 0)
	maxMessages := 10
	if len(messages) < maxMessages {
		maxMessages = len(messages)
	}

	for i := 0; i < maxMessages; i++ {
		msg := messages[i]
		preview := msg.Content
		if len(preview) > 100 {
			preview = preview[:100] + "..."
		}
		summaryParts = append(summaryParts, fmt.Sprintf("%d. [%s] %s", i+1, msg.Role, preview))
	}

	summaryContent := fmt.Sprintf("Session summary (%d messages):\n%s", len(messages), strings.Join(summaryParts, "\n"))

	return agenkit.Message{
		Role:    "system",
		Content: summaryContent,
	}, nil
}

// Clear removes all memory for a session.
func (r *RedisMemory) Clear(ctx context.Context, sessionID string) error {
	key := r.sessionKey(sessionID)
	if err := r.client.Del(ctx, key).Err(); err != nil {
		return fmt.Errorf("failed to clear session: %w", err)
	}
	return nil
}

// Capabilities returns the memory capabilities.
func (r *RedisMemory) Capabilities() []string {
	return []string{
		"basic_retrieval",
		"persistence",
		"ttl",
		"time_filtering",
		"importance_filtering",
		"tag_filtering",
	}
}

// Additional utility methods

// GetSessionCount returns the number of messages stored for a session.
func (r *RedisMemory) GetSessionCount(ctx context.Context, sessionID string) (int64, error) {
	key := r.sessionKey(sessionID)
	count, err := r.client.ZCard(ctx, key).Result()
	if err != nil {
		return 0, fmt.Errorf("failed to get session count: %w", err)
	}
	return count, nil
}

// GetAllSessions returns a list of all session IDs.
func (r *RedisMemory) GetAllSessions(ctx context.Context) ([]string, error) {
	pattern := fmt.Sprintf("%s:*:messages", r.keyPrefix)
	sessions := make([]string, 0)

	iter := r.client.Scan(ctx, 0, pattern, 0).Iterator()
	for iter.Next(ctx) {
		key := iter.Val()
		// Extract session_id from key
		// Format: "agenkit:memory:{session_id}:messages"
		parts := strings.Split(key, ":")
		if len(parts) >= 3 {
			sessionID := parts[len(parts)-2] // Second to last part
			sessions = append(sessions, sessionID)
		}
	}

	if err := iter.Err(); err != nil {
		return nil, fmt.Errorf("failed to scan sessions: %w", err)
	}

	return sessions, nil
}

// GetMemoryUsage returns memory usage statistics.
func (r *RedisMemory) GetMemoryUsage(ctx context.Context) (map[string]interface{}, error) {
	sessions, err := r.GetAllSessions(ctx)
	if err != nil {
		return nil, err
	}

	totalMessages := int64(0)
	for _, sessionID := range sessions {
		count, err := r.GetSessionCount(ctx, sessionID)
		if err != nil {
			continue
		}
		totalMessages += count
	}

	return map[string]interface{}{
		"total_sessions": len(sessions),
		"total_messages": totalMessages,
		"ttl":            int(r.ttl.Seconds()),
	}, nil
}

// Close closes the Redis connection.
func (r *RedisMemory) Close() error {
	if r.client != nil {
		return r.client.Close()
	}
	return nil
}
