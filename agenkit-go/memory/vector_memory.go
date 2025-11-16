package memory

import (
	"context"
	"fmt"
	"math"
	"sort"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// EmbeddingProvider is the interface for embedding providers.
type EmbeddingProvider interface {
	// Embed generates an embedding for text.
	Embed(ctx context.Context, text string) ([]float64, error)

	// Dimension returns the embedding dimension.
	Dimension() int
}

// VectorStore is the interface for vector stores.
type VectorStore interface {
	// Add adds a message with embedding to the store.
	Add(ctx context.Context, sessionID, messageID string, embedding []float64, message agenkit.Message, metadata map[string]interface{}, timestamp float64) error

	// Search searches for similar messages.
	// Returns list of (message, metadata, score) tuples.
	Search(ctx context.Context, sessionID string, queryEmbedding []float64, limit int, opts RetrieveOptions) ([]MessageSearchResult, error)

	// GetRecent gets recent messages without search.
	GetRecent(ctx context.Context, sessionID string, limit int, opts RetrieveOptions) ([]MessageWithMetadata, error)

	// Clear clears all messages for a session.
	Clear(ctx context.Context, sessionID string) error
}

// MessageSearchResult represents a search result with score.
type MessageSearchResult struct {
	Message  agenkit.Message
	Metadata map[string]interface{}
	Score    float64
}

// InMemoryVectorStore is a simple in-memory vector store using cosine similarity.
//
// Good for testing and small datasets. For production, use
// specialized vector databases (Pinecone, Weaviate, Qdrant, etc.).
type InMemoryVectorStore struct {
	mu sync.RWMutex
	// sessionID -> list of (messageID, embedding, message, metadata, timestamp)
	storage   map[string][]vectorEntry
	idCounter int
}

type vectorEntry struct {
	messageID string
	embedding []float64
	message   agenkit.Message
	metadata  map[string]interface{}
	timestamp float64
}

// NewInMemoryVectorStore creates a new in-memory vector store.
func NewInMemoryVectorStore() *InMemoryVectorStore {
	return &InMemoryVectorStore{
		storage:   make(map[string][]vectorEntry),
		idCounter: 0,
	}
}

// cosineSimilarity calculates cosine similarity between two vectors.
func (s *InMemoryVectorStore) cosineSimilarity(a, b []float64) float64 {
	if len(a) != len(b) {
		return 0.0
	}

	dotProduct := 0.0
	magnitudeA := 0.0
	magnitudeB := 0.0

	for i := range a {
		dotProduct += a[i] * b[i]
		magnitudeA += a[i] * a[i]
		magnitudeB += b[i] * b[i]
	}

	magnitudeA = math.Sqrt(magnitudeA)
	magnitudeB = math.Sqrt(magnitudeB)

	if magnitudeA == 0 || magnitudeB == 0 {
		return 0.0
	}

	return dotProduct / (magnitudeA * magnitudeB)
}

// Add adds a message with embedding to the store.
func (s *InMemoryVectorStore) Add(ctx context.Context, sessionID, messageID string, embedding []float64, message agenkit.Message, metadata map[string]interface{}, timestamp float64) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.storage[sessionID]; !exists {
		s.storage[sessionID] = make([]vectorEntry, 0)
	}

	s.storage[sessionID] = append(s.storage[sessionID], vectorEntry{
		messageID: messageID,
		embedding: embedding,
		message:   message,
		metadata:  metadata,
		timestamp: timestamp,
	})

	return nil
}

// Search searches for similar messages using cosine similarity.
func (s *InMemoryVectorStore) Search(ctx context.Context, sessionID string, queryEmbedding []float64, limit int, opts RetrieveOptions) ([]MessageSearchResult, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	entries, exists := s.storage[sessionID]
	if !exists {
		return []MessageSearchResult{}, nil
	}

	// Calculate similarity for all messages
	type scoredResult struct {
		message   agenkit.Message
		metadata  map[string]interface{}
		score     float64
		timestamp float64
	}

	results := make([]scoredResult, 0)
	for _, entry := range entries {
		score := s.cosineSimilarity(queryEmbedding, entry.embedding)
		results = append(results, scoredResult{
			message:   entry.message,
			metadata:  entry.metadata,
			score:     score,
			timestamp: entry.timestamp,
		})
	}

	// Sort by score (descending)
	sort.Slice(results, func(i, j int) bool {
		return results[i].score > results[j].score
	})

	// Apply filters
	filtered := make([]MessageSearchResult, 0)
	for _, result := range results {
		// Time range filter
		if opts.TimeRange != nil {
			msgTime := int64(result.timestamp)
			if msgTime < opts.TimeRange.Start || msgTime > opts.TimeRange.End {
				continue
			}
		}

		// Importance threshold filter
		if opts.ImportanceThreshold != nil {
			importance := 0.0
			if val, ok := result.metadata["importance"]; ok {
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
			if val, ok := result.metadata["tags"]; ok {
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

			// Check if any required tag exists
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

		filtered = append(filtered, MessageSearchResult{
			Message:  result.message,
			Metadata: result.metadata,
			Score:    result.score,
		})

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

// GetRecent gets recent messages without search.
func (s *InMemoryVectorStore) GetRecent(ctx context.Context, sessionID string, limit int, opts RetrieveOptions) ([]MessageWithMetadata, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	entries, exists := s.storage[sessionID]
	if !exists {
		return []MessageWithMetadata{}, nil
	}

	// Sort by timestamp (most recent first)
	sorted := make([]vectorEntry, len(entries))
	copy(sorted, entries)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].timestamp > sorted[j].timestamp
	})

	// Apply filters
	filtered := make([]MessageWithMetadata, 0)
	for _, entry := range sorted {
		// Time range filter
		if opts.TimeRange != nil {
			msgTime := int64(entry.timestamp)
			if msgTime < opts.TimeRange.Start || msgTime > opts.TimeRange.End {
				continue
			}
		}

		// Importance threshold filter
		if opts.ImportanceThreshold != nil {
			importance := 0.0
			if val, ok := entry.metadata["importance"]; ok {
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
			if val, ok := entry.metadata["tags"]; ok {
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

			// Check if any required tag exists
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

		filtered = append(filtered, MessageWithMetadata{
			Timestamp: entry.timestamp,
			Message:   entry.message,
			Metadata:  entry.metadata,
		})

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

// Clear clears all messages for a session.
func (s *InMemoryVectorStore) Clear(ctx context.Context, sessionID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	delete(s.storage, sessionID)
	return nil
}

// VectorMemory provides vector database for semantic retrieval.
//
// Features:
//   - Semantic search via embeddings
//   - Relevance-based retrieval
//   - Pluggable embedding providers
//   - Pluggable vector stores
//
// Use cases:
//   - RAG (Retrieval-Augmented Generation)
//   - Semantic memory
//   - Large knowledge bases
//   - Context-aware agents
//
// Example:
//
//	embeddings := NewOpenAIEmbeddings(client)
//	memory := NewVectorMemory(embeddings, nil)
//	err := memory.Store(ctx, "session-123", message, nil)
//	messages, err := memory.Retrieve(ctx, "session-123",
//	    RetrieveOptions{Query: "What did we discuss about pricing?", Limit: 5})
type VectorMemory struct {
	embeddings  EmbeddingProvider
	vectorStore VectorStore
	idCounter   int
	mu          sync.Mutex
}

// NewVectorMemory creates a new vector memory instance.
//
// Args:
//
//	embeddingProvider: Provider for generating embeddings
//	vectorStore: Vector storage backend (defaults to in-memory)
//
// Example:
//
//	embeddings := NewOpenAIEmbeddings(client)
//	memory := NewVectorMemory(embeddings, nil)
func NewVectorMemory(embeddingProvider EmbeddingProvider, vectorStore VectorStore) *VectorMemory {
	if vectorStore == nil {
		vectorStore = NewInMemoryVectorStore()
	}

	return &VectorMemory{
		embeddings:  embeddingProvider,
		vectorStore: vectorStore,
		idCounter:   0,
	}
}

// generateID generates a unique message ID.
func (v *VectorMemory) generateID() string {
	v.mu.Lock()
	defer v.mu.Unlock()
	v.idCounter++
	return fmt.Sprintf("msg-%d", v.idCounter)
}

// Store saves a message with embedding in vector store.
func (v *VectorMemory) Store(ctx context.Context, sessionID string, message agenkit.Message, metadata map[string]interface{}) error {
	// Generate embedding
	embedding, err := v.embeddings.Embed(ctx, message.Content)
	if err != nil {
		return fmt.Errorf("failed to generate embedding: %w", err)
	}

	// Store
	timestamp := float64(time.Now().UnixNano()) / 1e9
	messageID := v.generateID()

	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	return v.vectorStore.Add(ctx, sessionID, messageID, embedding, message, metadata, timestamp)
}

// Retrieve fetches messages with semantic search.
//
// If query provided, performs semantic search.
// Otherwise, returns most recent messages.
//
// Supports filtering by:
//   - TimeRange: Filter by time range
//   - ImportanceThreshold: Filter by importance score
//   - Tags: Filter by tags
func (v *VectorMemory) Retrieve(ctx context.Context, sessionID string, opts RetrieveOptions) ([]agenkit.Message, error) {
	// Set default limit
	limit := opts.Limit
	if limit <= 0 {
		limit = 10
	}

	if opts.Query != "" {
		// Semantic search
		queryEmbedding, err := v.embeddings.Embed(ctx, opts.Query)
		if err != nil {
			return nil, fmt.Errorf("failed to generate query embedding: %w", err)
		}

		results, err := v.vectorStore.Search(ctx, sessionID, queryEmbedding, limit, opts)
		if err != nil {
			return nil, err
		}

		// Return just messages (drop metadata and scores)
		messages := make([]agenkit.Message, len(results))
		for i, result := range results {
			messages[i] = result.Message
		}
		return messages, nil
	}

	// Recent messages (no search)
	results, err := v.vectorStore.GetRecent(ctx, sessionID, limit, opts)
	if err != nil {
		return nil, err
	}

	messages := make([]agenkit.Message, len(results))
	for i, result := range results {
		messages[i] = result.Message
	}
	return messages, nil
}

// RetrieveWithScores retrieves messages with similarity scores.
//
// Returns:
//
//	List of (message, score) tuples
func (v *VectorMemory) RetrieveWithScores(ctx context.Context, sessionID string, query string, limit int) ([]MessageSearchResult, error) {
	if limit <= 0 {
		limit = 10
	}

	queryEmbedding, err := v.embeddings.Embed(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("failed to generate query embedding: %w", err)
	}

	return v.vectorStore.Search(ctx, sessionID, queryEmbedding, limit, RetrieveOptions{})
}

// Summarize creates a summary of conversation history.
//
// For vector memory, we can use semantic search to find
// key messages and summarize those.
func (v *VectorMemory) Summarize(ctx context.Context, sessionID string, opts SummarizeOptions) (agenkit.Message, error) {
	messages, err := v.Retrieve(ctx, sessionID, RetrieveOptions{Limit: 100})
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

	summaryContent := fmt.Sprintf("Session summary (%d messages):\n", len(messages))
	for _, part := range summaryParts {
		summaryContent += part + "\n"
	}

	return agenkit.Message{
		Role:    "system",
		Content: summaryContent,
	}, nil
}

// Clear removes all memory for a session.
func (v *VectorMemory) Clear(ctx context.Context, sessionID string) error {
	return v.vectorStore.Clear(ctx, sessionID)
}

// Capabilities returns the memory capabilities.
func (v *VectorMemory) Capabilities() []string {
	return []string{
		"basic_retrieval",
		"semantic_search",
		"similarity_retrieval",
		"time_filtering",
		"importance_filtering",
		"tag_filtering",
	}
}
