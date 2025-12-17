"use strict";
/**
 * Memory Hierarchy Pattern - Multi-Tier Memory for Agents
 *
 * The Memory Hierarchy pattern provides a three-tier memory system for agents:
 * working memory (in-context), short-term memory (recent), and long-term memory (persistent).
 *
 * This enables agents to handle long-running conversations, remember important facts,
 * and operate effectively even with context window limitations.
 *
 * Key Concepts:
 * - Working Memory: Current conversation context (fast, small, in-memory)
 * - Short-Term Memory: Recent sessions (medium, TTL-based, recency retrieval)
 * - Long-Term Memory: Persistent facts (large, semantic retrieval, importance-based)
 * - Automatic Promotion: Important memories move from short-term to long-term
 * - Intelligent Retrieval: Search across tiers with relevance ranking
 *
 * Use Cases:
 * - Long-running conversational agents
 * - Personalization and user preferences
 * - Context-aware agents with limited context windows
 * - Multi-session continuity
 * - Learning and adaptation
 *
 * Example:
 * ```typescript
 * const memory = new MemoryHierarchy(
 *   new WorkingMemory(10),
 *   new ShortTermMemory(100, 3600),
 *   new LongTermMemory({}, undefined, 0.7)
 * );
 *
 * await memory.store(
 *   'User prefers Python over JavaScript',
 *   { category: 'preferences' },
 *   0.8
 * );
 *
 * const results = await memory.retrieve(
 *   'What programming languages does the user prefer?',
 *   5
 * );
 * ```
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.MemoryHierarchy = exports.LongTermMemory = exports.ShortTermMemory = exports.WorkingMemory = void 0;
exports.createMemoryEntry = createMemoryEntry;
/**
 * Create a new memory entry.
 */
function createMemoryEntry(content, metadata = {}, importance = 0.5, sessionId) {
    return {
        id: crypto.randomUUID(),
        content,
        metadata,
        timestamp: new Date(),
        accessCount: 0,
        importance,
        sessionId,
    };
}
/**
 * In-context working memory for current conversation.
 *
 * Characteristics:
 * - Fast: O(1) append, O(n) retrieval
 * - Small capacity: 10-20 messages typically
 * - FIFO eviction: Oldest messages removed first
 * - No persistence: Exists only in memory
 * - Use for: Current conversation context
 */
class WorkingMemory {
    constructor(maxMessages = 10) {
        if (maxMessages < 1) {
            throw new Error('maxMessages must be at least 1');
        }
        this.maxMessages = maxMessages;
        this.messages = [];
    }
    async store(entry) {
        this.messages.push(entry);
        // Evict oldest if over capacity
        if (this.messages.length > this.maxMessages) {
            this.messages.shift();
        }
    }
    async retrieve(query, limit = 10) {
        // Working memory returns all recent messages
        return this.messages.slice(-limit);
    }
    async delete(entryId) {
        this.messages = this.messages.filter(e => e.id !== entryId);
    }
    /**
     * Get all working memory entries.
     */
    getAll() {
        return [...this.messages];
    }
    /**
     * Clear all working memory.
     */
    clear() {
        this.messages = [];
    }
    /**
     * Number of entries in working memory.
     */
    get length() {
        return this.messages.length;
    }
}
exports.WorkingMemory = WorkingMemory;
/**
 * Recent session memory with TTL-based expiration.
 *
 * Characteristics:
 * - Medium capacity: 100-1000 messages typically
 * - TTL-based: Entries expire after time period
 * - Recency retrieval: Most recent first
 * - LRU eviction: Least recently used removed first
 * - Use for: Recent conversations, sliding window
 */
class ShortTermMemory {
    constructor(maxMessages = 100, ttlSeconds = 3600) {
        if (maxMessages < 1) {
            throw new Error('maxMessages must be at least 1');
        }
        if (ttlSeconds < 1) {
            throw new Error('ttlSeconds must be at least 1');
        }
        this.maxMessages = maxMessages;
        this.ttlMs = ttlSeconds * 1000;
        this.messages = [];
    }
    async store(entry) {
        // Clean expired entries first
        await this.cleanExpired();
        this.messages.push(entry);
        // Evict if over capacity (LRU)
        if (this.messages.length > this.maxMessages) {
            // Sort by access time (least recently used first)
            this.messages.sort((a, b) => {
                const aTime = a.lastAccessed || a.timestamp;
                const bTime = b.lastAccessed || b.timestamp;
                return aTime.getTime() - bTime.getTime();
            });
            this.messages.shift();
        }
    }
    async retrieve(query, limit = 10) {
        await this.cleanExpired();
        // Sort by timestamp (most recent first)
        const sorted = [...this.messages].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
        const results = sorted.slice(0, limit);
        // Update access time and count
        const now = new Date();
        for (const entry of results) {
            entry.accessCount++;
            entry.lastAccessed = now;
        }
        return results;
    }
    async delete(entryId) {
        this.messages = this.messages.filter(e => e.id !== entryId);
    }
    async cleanExpired() {
        const now = new Date();
        this.messages = this.messages.filter(e => now.getTime() - e.timestamp.getTime() < this.ttlMs);
    }
    /**
     * Number of entries in short-term memory.
     */
    get length() {
        return this.messages.length;
    }
}
exports.ShortTermMemory = ShortTermMemory;
/**
 * Persistent semantic memory with importance-based retention.
 *
 * Characteristics:
 * - Large capacity: Unlimited (depends on storage backend)
 * - Semantic retrieval: By relevance/similarity (embeddings)
 * - Persistent: Survives restarts
 * - Importance-based: Only important memories stored
 * - Use for: User preferences, facts, learned information
 */
class LongTermMemory {
    constructor(storageBackend, embeddingFn, minImportance = 0.5) {
        if (minImportance < 0.0 || minImportance > 1.0) {
            throw new Error('minImportance must be between 0.0 and 1.0');
        }
        if (storageBackend instanceof Map) {
            this.storage = storageBackend;
        }
        else if (storageBackend) {
            this.storage = new Map(Object.entries(storageBackend));
        }
        else {
            this.storage = new Map();
        }
        this.embeddingFn = embeddingFn;
        this.minImportance = minImportance;
    }
    async store(entry) {
        // Check importance threshold
        if (entry.importance < this.minImportance) {
            return; // Not important enough for long-term storage
        }
        // Store in backend
        this.storage.set(entry.id, entry);
    }
    async retrieve(query, limit = 10) {
        const allEntries = Array.from(this.storage.values());
        // Simple keyword-based relevance (replace with semantic search in production)
        const queryLower = query.toLowerCase();
        const scoredEntries = [];
        for (const entry of allEntries) {
            let score = 0.0;
            // Keyword match
            if (entry.content.toLowerCase().includes(queryLower)) {
                score += 0.5;
            }
            // Importance weight
            score += entry.importance * 0.3;
            // Recency weight (more recent = higher score)
            const ageDays = (Date.now() - entry.timestamp.getTime()) / (1000 * 60 * 60 * 24);
            const recencyScore = Math.max(0.0, 1.0 - ageDays / 365.0); // Decay over a year
            score += recencyScore * 0.2;
            scoredEntries.push([entry, score]);
        }
        // Sort by score (descending)
        scoredEntries.sort((a, b) => b[1] - a[1]);
        // Return top-k
        const results = scoredEntries.slice(0, limit).map(([entry]) => entry);
        // Update access time
        const now = new Date();
        for (const entry of results) {
            entry.accessCount++;
            entry.lastAccessed = now;
        }
        return results;
    }
    async delete(entryId) {
        this.storage.delete(entryId);
    }
    /**
     * Number of entries in long-term memory.
     */
    get length() {
        return this.storage.size;
    }
}
exports.LongTermMemory = LongTermMemory;
/**
 * Multi-tier memory system for agents.
 *
 * Manages working, short-term, and long-term memory with automatic
 * promotion and intelligent retrieval across tiers.
 */
class MemoryHierarchy {
    constructor(workingMemory, shortTermMemory, longTermMemory) {
        this.working = workingMemory;
        this.shortTerm = shortTermMemory;
        this.longTerm = longTermMemory;
    }
    /**
     * Store memory across appropriate tiers.
     */
    async store(content, metadata = {}, importance = 0.5, sessionId) {
        if (importance < 0.0 || importance > 1.0) {
            throw new Error('importance must be between 0.0 and 1.0');
        }
        // Create entry
        const entry = createMemoryEntry(content, metadata, importance, sessionId);
        // Always store in working memory
        await this.working.store(entry);
        // Store in short-term if available
        if (this.shortTerm) {
            await this.shortTerm.store(entry);
        }
        // Store in long-term if important enough
        if (this.longTerm && importance >= this.longTerm['minImportance']) {
            await this.longTerm.store(entry);
        }
        return entry.id;
    }
    /**
     * Retrieve memories from hierarchy.
     *
     * Searches across all enabled tiers and returns deduplicated,
     * ranked results.
     */
    async retrieve(query, limit = 10, searchTiers) {
        const results = [];
        // Determine which tiers to search
        const tiersToSearch = searchTiers || ['working', 'short_term', 'long_term'];
        // Search working memory
        if (tiersToSearch.includes('working')) {
            const workingResults = await this.working.retrieve(query, limit);
            results.push(...workingResults);
        }
        // Search short-term memory
        if (this.shortTerm && tiersToSearch.includes('short_term')) {
            const shortResults = await this.shortTerm.retrieve(query, limit);
            results.push(...shortResults);
        }
        // Search long-term memory
        if (this.longTerm && tiersToSearch.includes('long_term')) {
            const longResults = await this.longTerm.retrieve(query, limit);
            results.push(...longResults);
        }
        // Deduplicate by ID
        const seen = new Set();
        const unique = [];
        for (const entry of results) {
            if (!seen.has(entry.id)) {
                seen.add(entry.id);
                unique.push(entry);
            }
        }
        // Sort by importance and recency
        unique.sort((a, b) => {
            // Primary: importance
            if (a.importance !== b.importance) {
                return b.importance - a.importance;
            }
            // Secondary: recency
            return b.timestamp.getTime() - a.timestamp.getTime();
        });
        return unique.slice(0, limit);
    }
    /**
     * Delete memory from all tiers.
     */
    async delete(entryId) {
        await this.working.delete(entryId);
        if (this.shortTerm) {
            await this.shortTerm.delete(entryId);
        }
        if (this.longTerm) {
            await this.longTerm.delete(entryId);
        }
    }
    /**
     * Clear all working memory.
     */
    clearWorking() {
        this.working.clear();
    }
    /**
     * Get working memory entries.
     */
    getWorking() {
        return this.working.getAll();
    }
}
exports.MemoryHierarchy = MemoryHierarchy;
