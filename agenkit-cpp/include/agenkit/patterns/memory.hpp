/**
 * @file memory.hpp
 * @brief Memory hierarchy pattern for multi-tier memory management
 *
 * Provides a three-tier memory system: working memory (in-context),
 * short-term memory (recent), and long-term memory (persistent).
 */

#ifndef AGENKIT_PATTERNS_MEMORY_HPP
#define AGENKIT_PATTERNS_MEMORY_HPP

#include "agenkit/core/message.hpp"
#include <string>
#include <vector>
#include <deque>
#include <memory>
#include <chrono>
#include <optional>
#include <map>

namespace agenkit {
namespace patterns {

/**
 * @brief Single memory entry
 */
struct MemoryEntry {
    std::string id;
    std::string content;
    std::map<std::string, std::string> metadata;
    std::chrono::system_clock::time_point timestamp;
    int access_count{0};
    std::optional<std::chrono::system_clock::time_point> last_accessed;
    double importance{0.0};  ///< 0.0 to 1.0
    std::optional<std::string> session_id;

    MemoryEntry();
    MemoryEntry(const std::string& content_str, double imp = 0.0);
};

/**
 * @brief Abstract base class for memory storage
 */
class MemoryStore {
public:
    virtual ~MemoryStore() = default;

    /**
     * @brief Store a memory entry
     * @param entry Entry to store
     */
    virtual void store(const MemoryEntry& entry) = 0;

    /**
     * @brief Retrieve relevant memories
     * @param query Search query
     * @param limit Maximum results
     * @return Vector of relevant entries
     */
    virtual std::vector<MemoryEntry> retrieve(
        const std::string& query,
        int limit = 10
    ) = 0;

    /**
     * @brief Delete a memory entry
     * @param entry_id ID of entry to delete
     */
    virtual void del(const std::string& entry_id) = 0;

    /**
     * @brief Delete a memory entry (deprecated, use del)
     * @param entry_id ID of entry to delete
     * @deprecated Use del() for consistency with other languages
     */
    [[deprecated("Use del() for consistency with other languages")]]
    void deleteEntry(const std::string& entry_id) { del(entry_id); }

    /**
     * @brief Delete a memory entry (deprecated, use del)
     * @param entry_id ID of entry to delete
     * @deprecated Use del() for consistency with other languages
     */
    [[deprecated("Use del() for consistency with other languages")]]
    void remove(const std::string& entry_id) { del(entry_id); }

    /**
     * @brief Get all entries
     * @return All stored entries
     */
    virtual std::vector<MemoryEntry> get_all() const = 0;

    /**
     * @brief Get number of entries
     * @return Entry count
     */
    virtual size_t size() const = 0;
};

/**
 * @brief In-context working memory for current conversation
 *
 * Characteristics:
 * - Fast: O(1) append, O(n) retrieval
 * - Small capacity: 10-20 messages typically
 * - FIFO eviction: Oldest messages removed first
 * - No persistence: Exists only in memory
 * - Use for: Current conversation context
 */
class WorkingMemory : public MemoryStore {
public:
    /**
     * @brief Construct working memory
     * @param max_messages Maximum messages to keep (default: 10)
     */
    explicit WorkingMemory(int max_messages = 10);

    void store(const MemoryEntry& entry) override;

    std::vector<MemoryEntry> retrieve(
        const std::string& query,
        int limit = 10
    ) override;

    void del(const std::string& entry_id) override;

    std::vector<MemoryEntry> get_all() const override;

    size_t size() const override;

    /**
     * @brief Clear all memories
     */
    void clear();

private:
    int max_messages_;
    std::deque<MemoryEntry> messages_;  // Deque for O(1) pop_front
};

/**
 * @brief Short-term memory for recent sessions
 *
 * Characteristics:
 * - Medium capacity: 100-1000 messages
 * - Recency-based retrieval
 * - Optional TTL (time-to-live)
 * - In-memory storage
 * - Use for: Recent conversation history
 */
class ShortTermMemory : public MemoryStore {
public:
    /**
     * @brief Construct short-term memory
     * @param max_messages Maximum messages to keep (default: 100)
     * @param ttl_seconds Time-to-live in seconds (0 = no expiry, default: 3600)
     */
    explicit ShortTermMemory(
        int max_messages = 100,
        int ttl_seconds = 3600
    );

    void store(const MemoryEntry& entry) override;

    std::vector<MemoryEntry> retrieve(
        const std::string& query,
        int limit = 10
    ) override;

    void del(const std::string& entry_id) override;

    std::vector<MemoryEntry> get_all() const override;

    size_t size() const override;

    /**
     * @brief Remove expired entries
     * @return Number of entries removed
     */
    int cleanup_expired();

private:
    int max_messages_;
    std::chrono::seconds ttl_;
    std::deque<MemoryEntry> messages_;  // Deque for O(1) pop_front

    /**
     * @brief Check if entry is expired
     * @param entry Entry to check
     * @return True if expired
     */
    bool is_expired(const MemoryEntry& entry) const;
};

/**
 * @brief Long-term memory for persistent facts
 *
 * Characteristics:
 * - Large capacity: Unlimited
 * - Importance-based retrieval
 * - In-memory storage (could be extended to persistent)
 * - Use for: Important facts, preferences, knowledge
 */
class LongTermMemory : public MemoryStore {
public:
    /**
     * @brief Construct long-term memory
     * @param importance_threshold Minimum importance to store (default: 0.5)
     */
    explicit LongTermMemory(double importance_threshold = 0.5);

    void store(const MemoryEntry& entry) override;

    std::vector<MemoryEntry> retrieve(
        const std::string& query,
        int limit = 10
    ) override;

    void del(const std::string& entry_id) override;

    std::vector<MemoryEntry> get_all() const override;

    size_t size() const override;

private:
    double importance_threshold_;
    std::vector<MemoryEntry> memories_;
};

/**
 * @brief Three-tier memory hierarchy
 *
 * Combines working, short-term, and long-term memory into a unified system
 * with automatic promotion and intelligent retrieval across tiers.
 */
class MemoryHierarchy {
public:
    /**
     * @brief Construct memory hierarchy
     * @param working_max Working memory size (default: 10)
     * @param short_term_max Short-term memory size (default: 100)
     * @param ttl_seconds Short-term TTL (default: 3600)
     * @param importance_threshold Long-term importance threshold (default: 0.5)
     */
    explicit MemoryHierarchy(
        int working_max = 10,
        int short_term_max = 100,
        int ttl_seconds = 3600,
        double importance_threshold = 0.5
    );

    /**
     * @brief Store memory in appropriate tier
     * @param content Memory content
     * @param importance Importance score (0.0-1.0)
     * @param metadata Optional metadata
     */
    void store(
        const std::string& content,
        double importance = 0.0,
        const std::map<std::string, std::string>& metadata = {}
    );

    /**
     * @brief Retrieve relevant memories across all tiers
     * @param query Search query
     * @param limit Maximum results
     * @return Vector of relevant memories
     */
    std::vector<MemoryEntry> retrieve(
        const std::string& query,
        int limit = 10
    );

    /**
     * @brief Get working memory
     * @return Working memory instance
     */
    WorkingMemory& get_working_memory();

    /**
     * @brief Get short-term memory
     * @return Short-term memory instance
     */
    ShortTermMemory& get_short_term_memory();

    /**
     * @brief Get long-term memory
     * @return Long-term memory instance
     */
    LongTermMemory& get_long_term_memory();

    /**
     * @brief Get total memories across all tiers
     * @return Total memory count
     */
    size_t total_size() const;

private:
    WorkingMemory working_memory_;
    ShortTermMemory short_term_memory_;
    LongTermMemory long_term_memory_;
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_MEMORY_HPP
