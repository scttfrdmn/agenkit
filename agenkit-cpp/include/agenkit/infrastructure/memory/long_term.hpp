#pragma once

#include "agenkit/infrastructure/memory/entry.hpp"
#include "agenkit/core/result.hpp"
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

namespace agenkit {
namespace infrastructure {
namespace memory {

/// Error types for LongTermMemory
enum class LongTermMemoryError {
    InvalidThreshold,
    EntryNotFound,
};

/// Result type for LongTermMemory operations
template<typename T>
using LongTermMemoryResult = core::Result<T, LongTermMemoryError>;

/// Long-term memory - persistent facts with importance filtering
///
/// Characteristics:
/// - Storage: HashMap (ID -> Entry)
/// - Filtering: Importance threshold (rejects low-importance entries)
/// - Capacity: Unbounded (or backed by persistent storage)
/// - Retrieval: Keyword search with relevance scoring
/// - Thread-safe: mutex-protected
class LongTermMemory {
public:
    /// Create a new long-term memory with importance threshold
    ///
    /// @param min_importance Minimum importance score to store (0.0-1.0, typically 0.6-0.9)
    /// @throws std::invalid_argument if min_importance not in [0.0, 1.0]
    explicit LongTermMemory(double min_importance = 0.7);

    /// Store a memory entry if importance >= threshold
    ///
    /// @param entry Memory entry to store
    /// @return Entry ID if stored, nullopt if below threshold
    LongTermMemoryResult<std::optional<std::string>> store(const MemoryEntry& entry);

    /// Retrieve entries matching query
    ///
    /// Performs keyword search and ranks by relevance score:
    /// - Keyword match: 0.5 if query found in content
    /// - Importance: importance * 0.3
    /// - Recency: (1.0 - age_days/365) * 0.2
    ///
    /// @param query Search query
    /// @param limit Maximum number of entries to retrieve
    /// @return Vector of entries (highest relevance first)
    LongTermMemoryResult<std::vector<MemoryEntry>> retrieve(
        const std::string& query,
        size_t limit
    );

    /// Delete an entry by ID
    ///
    /// @param entry_id Entry ID to delete
    /// @return true if deleted, false if not found
    LongTermMemoryResult<bool> remove(const std::string& entry_id);

    /// Get all entries
    ///
    /// @return Vector of all entries (unsorted)
    LongTermMemoryResult<std::vector<MemoryEntry>> get_all();

    /// Clear all entries
    void clear();

    /// Get current entry count
    ///
    /// @return Number of entries stored
    size_t count() const;

    /// Get minimum importance threshold
    ///
    /// @return Minimum importance value
    double min_importance() const { return min_importance_; }

private:
    double min_importance_;
    mutable std::mutex mutex_;
    std::map<std::string, MemoryEntry> storage_;
};

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
