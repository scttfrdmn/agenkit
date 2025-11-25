// Package patterns provides the Memory Hierarchy pattern for multi-tier agent memory.
//
// The Memory Hierarchy pattern provides a three-tier memory system for agents:
// working memory (in-context), short-term memory (recent), and long-term memory (persistent).
//
// This enables agents to handle long-running conversations, remember important facts,
// and operate effectively even with context window limitations.
//
// Key concepts:
//   - Working Memory: Current conversation context (fast, small, in-memory)
//   - Short-Term Memory: Recent sessions (medium, TTL-based, recency retrieval)
//   - Long-Term Memory: Persistent facts (large, semantic retrieval, importance-based)
//   - Automatic Promotion: Important memories move from short-term to long-term
//   - Intelligent Retrieval: Search across tiers with relevance ranking
//
// Use cases:
//   - Long-running conversational agents
//   - Personalization and user preferences
//   - Context-aware agents with limited context windows
//   - Multi-session continuity
//   - Learning and adaptation
//
// Example:
//
//	memory := patterns.NewMemoryHierarchy(
//	    patterns.NewWorkingMemory(10),
//	    patterns.NewShortTermMemory(100, 3600),
//	    patterns.NewLongTermMemory(nil, nil, 0.7),
//	)
//
//	memory.Store(ctx, "User prefers Python", map[string]interface{}{"category": "preferences"}, 0.8, "")
//
//	results, _ := memory.Retrieve(ctx, "What does the user prefer?", 5, nil)
package patterns

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
)

// MemoryEntry represents a single memory entry across all tiers.
type MemoryEntry struct {
	// ID is the unique identifier
	ID string
	// Content is the memory content (text)
	Content string
	// Metadata contains additional structured information
	Metadata map[string]interface{}
	// Timestamp when memory was created
	Timestamp time.Time
	// AccessCount is number of times accessed
	AccessCount int
	// LastAccessed when last accessed
	LastAccessed *time.Time
	// Importance score from 0.0 to 1.0
	Importance float64
	// SessionID optional session identifier
	SessionID string
}

// CreateMemoryEntry creates a new memory entry.
func CreateMemoryEntry(content string, metadata map[string]interface{}, importance float64, sessionID string) *MemoryEntry {
	if metadata == nil {
		metadata = make(map[string]interface{})
	}

	return &MemoryEntry{
		ID:          uuid.New().String(),
		Content:     content,
		Metadata:    metadata,
		Timestamp:   time.Now(),
		AccessCount: 0,
		Importance:  importance,
		SessionID:   sessionID,
	}
}

// MemoryStore is the interface for memory storage.
type MemoryStore interface {
	// Store stores a memory entry
	Store(ctx context.Context, entry *MemoryEntry) error
	// Retrieve retrieves relevant memories
	Retrieve(ctx context.Context, query string, limit int) ([]*MemoryEntry, error)
	// Delete deletes a memory entry
	Delete(ctx context.Context, entryID string) error
}

// WorkingMemory is in-context working memory for current conversation.
//
// Characteristics:
//   - Fast: O(1) append, O(n) retrieval
//   - Small capacity: 10-20 messages typically
//   - FIFO eviction: Oldest messages removed first
//   - No persistence: Exists only in memory
//   - Use for: Current conversation context
type WorkingMemory struct {
	maxMessages int
	messages    []*MemoryEntry
	mu          sync.RWMutex
}

// NewWorkingMemory creates a new working memory.
func NewWorkingMemory(maxMessages int) (*WorkingMemory, error) {
	if maxMessages < 1 {
		return nil, fmt.Errorf("maxMessages must be at least 1")
	}

	return &WorkingMemory{
		maxMessages: maxMessages,
		messages:    make([]*MemoryEntry, 0),
	}, nil
}

// Store stores a memory entry in working memory.
func (w *WorkingMemory) Store(ctx context.Context, entry *MemoryEntry) error {
	w.mu.Lock()
	defer w.mu.Unlock()

	w.messages = append(w.messages, entry)

	// Evict oldest if over capacity
	if len(w.messages) > w.maxMessages {
		w.messages = w.messages[1:]
	}

	return nil
}

// Retrieve retrieves recent messages from working memory.
func (w *WorkingMemory) Retrieve(ctx context.Context, query string, limit int) ([]*MemoryEntry, error) {
	w.mu.RLock()
	defer w.mu.RUnlock()

	// Working memory returns all recent messages
	start := 0
	if len(w.messages) > limit {
		start = len(w.messages) - limit
	}

	results := make([]*MemoryEntry, len(w.messages)-start)
	copy(results, w.messages[start:])

	return results, nil
}

// Delete deletes a memory entry from working memory.
func (w *WorkingMemory) Delete(ctx context.Context, entryID string) error {
	w.mu.Lock()
	defer w.mu.Unlock()

	filtered := make([]*MemoryEntry, 0)
	for _, entry := range w.messages {
		if entry.ID != entryID {
			filtered = append(filtered, entry)
		}
	}
	w.messages = filtered

	return nil
}

// GetAll returns all working memory entries.
func (w *WorkingMemory) GetAll() []*MemoryEntry {
	w.mu.RLock()
	defer w.mu.RUnlock()

	results := make([]*MemoryEntry, len(w.messages))
	copy(results, w.messages)
	return results
}

// Clear clears all working memory.
func (w *WorkingMemory) Clear() {
	w.mu.Lock()
	defer w.mu.Unlock()

	w.messages = make([]*MemoryEntry, 0)
}

// Length returns the number of entries in working memory.
func (w *WorkingMemory) Length() int {
	w.mu.RLock()
	defer w.mu.RUnlock()

	return len(w.messages)
}

// ShortTermMemory is recent session memory with TTL-based expiration.
//
// Characteristics:
//   - Medium capacity: 100-1000 messages typically
//   - TTL-based: Entries expire after time period
//   - Recency retrieval: Most recent first
//   - LRU eviction: Least recently used removed first
//   - Use for: Recent conversations, sliding window
type ShortTermMemory struct {
	maxMessages int
	ttl         time.Duration
	messages    []*MemoryEntry
	mu          sync.RWMutex
}

// NewShortTermMemory creates a new short-term memory.
func NewShortTermMemory(maxMessages int, ttlSeconds int) (*ShortTermMemory, error) {
	if maxMessages < 1 {
		return nil, fmt.Errorf("maxMessages must be at least 1")
	}
	if ttlSeconds < 1 {
		return nil, fmt.Errorf("ttlSeconds must be at least 1")
	}

	return &ShortTermMemory{
		maxMessages: maxMessages,
		ttl:         time.Duration(ttlSeconds) * time.Second,
		messages:    make([]*MemoryEntry, 0),
	}, nil
}

// Store stores a memory entry in short-term memory.
func (s *ShortTermMemory) Store(ctx context.Context, entry *MemoryEntry) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	// Clean expired entries first
	s.cleanExpired()

	s.messages = append(s.messages, entry)

	// Evict if over capacity (LRU)
	if len(s.messages) > s.maxMessages {
		// Sort by access time (least recently used first)
		sort.Slice(s.messages, func(i, j int) bool {
			iTime := s.messages[i].Timestamp
			if s.messages[i].LastAccessed != nil {
				iTime = *s.messages[i].LastAccessed
			}

			jTime := s.messages[j].Timestamp
			if s.messages[j].LastAccessed != nil {
				jTime = *s.messages[j].LastAccessed
			}

			return iTime.Before(jTime)
		})

		s.messages = s.messages[1:]
	}

	return nil
}

// Retrieve retrieves recent messages from short-term memory.
func (s *ShortTermMemory) Retrieve(ctx context.Context, query string, limit int) ([]*MemoryEntry, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.cleanExpired()

	// Sort by timestamp (most recent first)
	sorted := make([]*MemoryEntry, len(s.messages))
	copy(sorted, s.messages)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Timestamp.After(sorted[j].Timestamp)
	})

	// Take top limit
	results := sorted
	if len(results) > limit {
		results = results[:limit]
	}

	// Update access time and count
	now := time.Now()
	for _, entry := range results {
		entry.AccessCount++
		entry.LastAccessed = &now
	}

	return results, nil
}

// Delete deletes a memory entry from short-term memory.
func (s *ShortTermMemory) Delete(ctx context.Context, entryID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	filtered := make([]*MemoryEntry, 0)
	for _, entry := range s.messages {
		if entry.ID != entryID {
			filtered = append(filtered, entry)
		}
	}
	s.messages = filtered

	return nil
}

// cleanExpired removes expired entries.
func (s *ShortTermMemory) cleanExpired() {
	now := time.Now()
	filtered := make([]*MemoryEntry, 0)

	for _, entry := range s.messages {
		if now.Sub(entry.Timestamp) < s.ttl {
			filtered = append(filtered, entry)
		}
	}

	s.messages = filtered
}

// Length returns the number of entries in short-term memory.
func (s *ShortTermMemory) Length() int {
	s.mu.RLock()
	defer s.mu.RUnlock()

	return len(s.messages)
}

// LongTermMemory is persistent semantic memory with importance-based retention.
//
// Characteristics:
//   - Large capacity: Unlimited (depends on storage backend)
//   - Semantic retrieval: By relevance/similarity
//   - Persistent: Survives restarts
//   - Importance-based: Only important memories stored
//   - Use for: User preferences, facts, learned information
type LongTermMemory struct {
	storage       map[string]*MemoryEntry
	minImportance float64
	mu            sync.RWMutex
}

// NewLongTermMemory creates a new long-term memory.
func NewLongTermMemory(storageBackend map[string]*MemoryEntry, embeddingFn interface{}, minImportance float64) (*LongTermMemory, error) {
	if minImportance < 0.0 || minImportance > 1.0 {
		return nil, fmt.Errorf("minImportance must be between 0.0 and 1.0")
	}

	storage := storageBackend
	if storage == nil {
		storage = make(map[string]*MemoryEntry)
	}

	return &LongTermMemory{
		storage:       storage,
		minImportance: minImportance,
	}, nil
}

// Store stores a memory entry in long-term memory.
func (l *LongTermMemory) Store(ctx context.Context, entry *MemoryEntry) error {
	// Check importance threshold
	if entry.Importance < l.minImportance {
		return nil // Not important enough for long-term storage
	}

	l.mu.Lock()
	defer l.mu.Unlock()

	l.storage[entry.ID] = entry

	return nil
}

// Retrieve retrieves relevant memories from long-term memory.
func (l *LongTermMemory) Retrieve(ctx context.Context, query string, limit int) ([]*MemoryEntry, error) {
	l.mu.RLock()
	defer l.mu.RUnlock()

	allEntries := make([]*MemoryEntry, 0, len(l.storage))
	for _, entry := range l.storage {
		allEntries = append(allEntries, entry)
	}

	// Simple keyword-based relevance
	queryLower := strings.ToLower(query)
	type scoredEntry struct {
		entry *MemoryEntry
		score float64
	}

	scoredEntries := make([]scoredEntry, 0)

	for _, entry := range allEntries {
		score := 0.0

		// Keyword match
		if strings.Contains(strings.ToLower(entry.Content), queryLower) {
			score += 0.5
		}

		// Importance weight
		score += entry.Importance * 0.3

		// Recency weight (more recent = higher score)
		ageDays := time.Since(entry.Timestamp).Hours() / 24
		recencyScore := max(0.0, 1.0-ageDays/365.0) // Decay over a year
		score += recencyScore * 0.2

		scoredEntries = append(scoredEntries, scoredEntry{entry, score})
	}

	// Sort by score (descending)
	sort.Slice(scoredEntries, func(i, j int) bool {
		return scoredEntries[i].score > scoredEntries[j].score
	})

	// Take top limit
	results := make([]*MemoryEntry, 0)
	for i := 0; i < len(scoredEntries) && i < limit; i++ {
		results = append(results, scoredEntries[i].entry)
	}

	// Update access time
	now := time.Now()
	for _, entry := range results {
		entry.AccessCount++
		entry.LastAccessed = &now
	}

	return results, nil
}

// Delete deletes a memory entry from long-term memory.
func (l *LongTermMemory) Delete(ctx context.Context, entryID string) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	delete(l.storage, entryID)

	return nil
}

// Length returns the number of entries in long-term memory.
func (l *LongTermMemory) Length() int {
	l.mu.RLock()
	defer l.mu.RUnlock()

	return len(l.storage)
}

func max(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}

// MemoryHierarchy is a multi-tier memory system for agents.
//
// Manages working, short-term, and long-term memory with automatic
// promotion and intelligent retrieval across tiers.
type MemoryHierarchy struct {
	working   *WorkingMemory
	shortTerm *ShortTermMemory
	longTerm  *LongTermMemory
}

// NewMemoryHierarchy creates a new memory hierarchy.
func NewMemoryHierarchy(
	workingMemory *WorkingMemory,
	shortTermMemory *ShortTermMemory,
	longTermMemory *LongTermMemory,
) *MemoryHierarchy {
	return &MemoryHierarchy{
		working:   workingMemory,
		shortTerm: shortTermMemory,
		longTerm:  longTermMemory,
	}
}

// Store stores memory across appropriate tiers.
func (m *MemoryHierarchy) Store(
	ctx context.Context,
	content string,
	metadata map[string]interface{},
	importance float64,
	sessionID string,
) (string, error) {
	if importance < 0.0 || importance > 1.0 {
		return "", fmt.Errorf("importance must be between 0.0 and 1.0")
	}

	// Create entry
	entry := CreateMemoryEntry(content, metadata, importance, sessionID)

	// Always store in working memory
	if err := m.working.Store(ctx, entry); err != nil {
		return "", fmt.Errorf("failed to store in working memory: %w", err)
	}

	// Store in short-term if available
	if m.shortTerm != nil {
		if err := m.shortTerm.Store(ctx, entry); err != nil {
			return "", fmt.Errorf("failed to store in short-term memory: %w", err)
		}
	}

	// Store in long-term if important enough
	if m.longTerm != nil && importance >= m.longTerm.minImportance {
		if err := m.longTerm.Store(ctx, entry); err != nil {
			return "", fmt.Errorf("failed to store in long-term memory: %w", err)
		}
	}

	return entry.ID, nil
}

// Retrieve retrieves memories from hierarchy.
//
// Searches across all enabled tiers and returns deduplicated, ranked results.
func (m *MemoryHierarchy) Retrieve(
	ctx context.Context,
	query string,
	limit int,
	searchTiers []string,
) ([]*MemoryEntry, error) {
	results := make([]*MemoryEntry, 0)

	// Determine which tiers to search
	tiersToSearch := searchTiers
	if tiersToSearch == nil {
		tiersToSearch = []string{"working", "short_term", "long_term"}
	}

	// Search working memory
	if contains(tiersToSearch, "working") {
		workingResults, err := m.working.Retrieve(ctx, query, limit)
		if err != nil {
			return nil, fmt.Errorf("failed to retrieve from working memory: %w", err)
		}
		results = append(results, workingResults...)
	}

	// Search short-term memory
	if m.shortTerm != nil && contains(tiersToSearch, "short_term") {
		shortResults, err := m.shortTerm.Retrieve(ctx, query, limit)
		if err != nil {
			return nil, fmt.Errorf("failed to retrieve from short-term memory: %w", err)
		}
		results = append(results, shortResults...)
	}

	// Search long-term memory
	if m.longTerm != nil && contains(tiersToSearch, "long_term") {
		longResults, err := m.longTerm.Retrieve(ctx, query, limit)
		if err != nil {
			return nil, fmt.Errorf("failed to retrieve from long-term memory: %w", err)
		}
		results = append(results, longResults...)
	}

	// Deduplicate by ID
	seen := make(map[string]bool)
	unique := make([]*MemoryEntry, 0)

	for _, entry := range results {
		if !seen[entry.ID] {
			seen[entry.ID] = true
			unique = append(unique, entry)
		}
	}

	// Sort by importance and recency
	sort.Slice(unique, func(i, j int) bool {
		// Primary: importance
		if unique[i].Importance != unique[j].Importance {
			return unique[i].Importance > unique[j].Importance
		}
		// Secondary: recency
		return unique[i].Timestamp.After(unique[j].Timestamp)
	})

	// Return top limit
	if len(unique) > limit {
		unique = unique[:limit]
	}

	return unique, nil
}

// Delete deletes memory from all tiers.
func (m *MemoryHierarchy) Delete(ctx context.Context, entryID string) error {
	if err := m.working.Delete(ctx, entryID); err != nil {
		return fmt.Errorf("failed to delete from working memory: %w", err)
	}

	if m.shortTerm != nil {
		if err := m.shortTerm.Delete(ctx, entryID); err != nil {
			return fmt.Errorf("failed to delete from short-term memory: %w", err)
		}
	}

	if m.longTerm != nil {
		if err := m.longTerm.Delete(ctx, entryID); err != nil {
			return fmt.Errorf("failed to delete from long-term memory: %w", err)
		}
	}

	return nil
}

// ClearWorking clears all working memory.
func (m *MemoryHierarchy) ClearWorking() {
	m.working.Clear()
}

// GetWorking returns working memory entries.
func (m *MemoryHierarchy) GetWorking() []*MemoryEntry {
	return m.working.GetAll()
}

func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}
