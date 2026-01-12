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

/// Error types for WorkingMemory
enum class WorkingMemoryError {
    InvalidCapacity,
    EntryNotFound,
};

/// Result type for WorkingMemory operations
template<typename T>
using WorkingMemoryResult = core::Result<T, WorkingMemoryError>;

/// Working memory - current context with FIFO eviction
///
/// Characteristics:
/// - Storage: Vector of entries
/// - Eviction: FIFO (First-In-First-Out)
/// - Capacity: Fixed (typically 5-20 messages)
/// - Retrieval: Most recent first
/// - Thread-safe: mutex-protected
class WorkingMemory {
public:
    /// Create a new working memory with specified capacity
    ///
    /// @param max_messages Maximum number of messages to store
    /// @throws std::invalid_argument if max_messages is 0
    explicit WorkingMemory(size_t max_messages);

    /// Store a memory entry
    ///
    /// If at capacity, removes oldest entry (FIFO)
    ///
    /// @param entry Memory entry to store
    /// @return Entry ID on success
    WorkingMemoryResult<std::string> store(const MemoryEntry& entry);

    /// Retrieve recent entries
    ///
    /// Returns most recent entries up to limit, updating access tracking
    ///
    /// @param limit Maximum number of entries to retrieve
    /// @return Vector of entries (most recent first)
    WorkingMemoryResult<std::vector<MemoryEntry>> retrieve(size_t limit);

    /// Delete an entry by ID
    ///
    /// @param entry_id Entry ID to delete
    /// @return true if deleted, false if not found
    WorkingMemoryResult<bool> del(const std::string& entry_id);

    /// Delete an entry by ID (deprecated, use del)
    ///
    /// @param entry_id Entry ID to delete
    /// @return true if deleted, false if not found
    /// @deprecated Use del() for consistency with other languages
    [[deprecated("Use del() for consistency with other languages")]]
    WorkingMemoryResult<bool> deleteEntry(const std::string& entry_id) { return del(entry_id); }

    /// Delete an entry by ID (deprecated, use del)
    ///
    /// @param entry_id Entry ID to delete
    /// @return true if deleted, false if not found
    /// @deprecated Use del() for consistency with other languages
    [[deprecated("Use del() for consistency with other languages")]]
    WorkingMemoryResult<bool> remove(const std::string& entry_id) { return del(entry_id); }

    /// Get all entries
    ///
    /// @return Vector of all entries (most recent first)
    WorkingMemoryResult<std::vector<MemoryEntry>> get_all();

    /// Clear all entries
    void clear();

    /// Get current entry count
    ///
    /// @return Number of entries stored
    size_t count() const;

    /// Get maximum capacity
    ///
    /// @return Maximum number of entries
    size_t capacity() const { return max_messages_; }

private:
    size_t max_messages_;
    mutable std::mutex mutex_;
    std::vector<MemoryEntry> messages_;

    /// Evict oldest entry if at capacity (FIFO)
    void evict_if_needed();
};

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
