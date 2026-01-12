#pragma once

#include "agenkit/infrastructure/memory/entry.hpp"
#include "agenkit/core/result.hpp"
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace agenkit {
namespace infrastructure {
namespace memory {

/// Error types for ShortTermMemory
enum class ShortTermMemoryError {
    InvalidCapacity,
    InvalidTTL,
    EntryNotFound,
};

/// Result type for ShortTermMemory operations
template<typename T>
using ShortTermMemoryResult = core::Result<T, ShortTermMemoryError>;

/// Short-term memory - recent sessions with TTL and LRU eviction
///
/// Characteristics:
/// - Storage: Vector with TTL tracking
/// - Eviction: LRU (Least Recently Used) + TTL-based
/// - Capacity: Medium (typically 100-1000 messages)
/// - TTL: Age-based expiration (1 second to 24 hours typical)
/// - Retrieval: Most recent first
/// - Thread-safe: mutex-protected
/// - Cleanup: Automatic expired entry removal on operations
class ShortTermMemory {
public:
    /// Create a new short-term memory with capacity and TTL
    ///
    /// @param max_messages Maximum number of messages to store
    /// @param ttl_seconds Time-to-live in seconds
    /// @throws std::invalid_argument if max_messages is 0 or ttl_seconds <= 0
    ShortTermMemory(size_t max_messages, int64_t ttl_seconds);

    /// Store a memory entry
    ///
    /// Automatically removes expired entries and evicts LRU if at capacity
    ///
    /// @param entry Memory entry to store
    /// @return Entry ID on success
    ShortTermMemoryResult<std::string> store(const MemoryEntry& entry);

    /// Retrieve recent entries
    ///
    /// Returns non-expired entries up to limit, updating access tracking
    ///
    /// @param limit Maximum number of entries to retrieve
    /// @return Vector of entries (most recent first)
    ShortTermMemoryResult<std::vector<MemoryEntry>> retrieve(size_t limit);

    /// Delete an entry by ID
    ///
    /// @param entry_id Entry ID to delete
    /// @return true if deleted, false if not found
    ShortTermMemoryResult<bool> del(const std::string& entry_id);

    /// Delete an entry by ID (deprecated, use del)
    ///
    /// @param entry_id Entry ID to delete
    /// @return true if deleted, false if not found
    /// @deprecated Use del() for consistency with other languages
    [[deprecated("Use del() for consistency with other languages")]]
    ShortTermMemoryResult<bool> deleteEntry(const std::string& entry_id) { return del(entry_id); }

    /// Delete an entry by ID (deprecated, use del)
    ///
    /// @param entry_id Entry ID to delete
    /// @return true if deleted, false if not found
    /// @deprecated Use del() for consistency with other languages
    [[deprecated("Use del() for consistency with other languages")]]
    ShortTermMemoryResult<bool> remove(const std::string& entry_id) { return del(entry_id); }

    /// Get all non-expired entries
    ///
    /// @return Vector of all entries (most recent first)
    ShortTermMemoryResult<std::vector<MemoryEntry>> get_all();

    /// Clear all entries
    void clear();

    /// Get current entry count (including expired)
    ///
    /// @return Number of entries stored
    size_t count();

    /// Get maximum capacity
    ///
    /// @return Maximum number of entries
    size_t capacity() const { return max_messages_; }

    /// Get TTL in seconds
    ///
    /// @return TTL value
    int64_t ttl() const { return ttl_seconds_; }

private:
    size_t max_messages_;
    int64_t ttl_seconds_;
    mutable std::mutex mutex_;
    std::vector<MemoryEntry> messages_;

    /// Remove expired entries (age > TTL)
    void clean_expired();

    /// Evict least recently used entry
    void evict_lru();
};

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
