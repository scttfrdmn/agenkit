#pragma once

#include "agenkit/infrastructure/memory/entry.hpp"
#include "agenkit/infrastructure/memory/working.hpp"
#include "agenkit/infrastructure/memory/short_term.hpp"
#include "agenkit/infrastructure/memory/long_term.hpp"
#include "agenkit/core/result.hpp"
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <vector>

namespace agenkit {
namespace infrastructure {
namespace memory {

/// Error types for MemoryHierarchy
enum class HierarchyError {
    WorkingMemoryError,
    ShortTermMemoryError,
    LongTermMemoryError,
    InvalidTier,
};

/// Result type for MemoryHierarchy operations
template<typename T>
using HierarchyResult = core::Result<T, HierarchyError>;

/// Three-tier memory hierarchy orchestrator
///
/// Routes messages to appropriate tiers based on importance:
/// - Always stored in working memory
/// - Always stored in short-term if available
/// - Conditionally stored in long-term if importance >= threshold
///
/// Retrieval deduplicates across tiers and ranks by importance/recency.
class MemoryHierarchy {
public:
    /// Create a memory hierarchy
    ///
    /// @param working Working memory tier (required)
    /// @param short_term Optional short-term memory tier
    /// @param long_term Optional long-term memory tier
    MemoryHierarchy(
        std::unique_ptr<WorkingMemory> working,
        std::unique_ptr<ShortTermMemory> short_term = nullptr,
        std::unique_ptr<LongTermMemory> long_term = nullptr
    );

    /// Store a memory across appropriate tiers
    ///
    /// Routing:
    /// - Always stored in working memory
    /// - Stored in short-term if available
    /// - Stored in long-term if available AND importance >= threshold
    ///
    /// @param content Text content
    /// @param metadata Structured metadata
    /// @param importance Importance score (0.0-1.0)
    /// @param session_id Optional session identifier
    /// @return Entry ID
    HierarchyResult<std::string> store(
        const std::string& content,
        const std::map<std::string, nlohmann::json>& metadata = {},
        double importance = 0.5,
        const std::optional<std::string>& session_id = std::nullopt
    );

    /// Retrieve entries across tiers
    ///
    /// Searches selected tiers, deduplicates by ID, and ranks by:
    /// 1. Importance (descending)
    /// 2. Timestamp (descending)
    ///
    /// @param query Search query
    /// @param limit Maximum number of entries to retrieve
    /// @param search_tiers Tiers to search (empty = all tiers)
    /// @return Vector of deduplicated entries (highest ranked first)
    LongTermMemoryResult<std::vector<MemoryEntry>> retrieve(
        const std::string& query,
        size_t limit,
        const std::vector<std::string>& search_tiers = {"working", "short_term", "long_term"}
    );

    /// Delete an entry from all tiers
    ///
    /// @param entry_id Entry ID to delete
    /// @return true if deleted from any tier
    HierarchyResult<bool> remove(const std::string& entry_id);

    /// Clear working memory only
    void clear_working();

    /// Clear all tiers
    void clear_all();

    /// Get statistics for all tiers
    ///
    /// @return Map of tier name to entry count
    std::map<std::string, size_t> get_stats();

private:
    std::unique_ptr<WorkingMemory> working_;
    std::unique_ptr<ShortTermMemory> short_term_;
    std::unique_ptr<LongTermMemory> long_term_;
};

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
