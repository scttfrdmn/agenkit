#pragma once

#include <chrono>
#include <map>
#include <optional>
#include <string>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace infrastructure {
namespace memory {

/// Memory entry representing a single stored message or fact
///
/// Each entry contains content, structured metadata, temporal information,
/// and access tracking for LRU and importance-based retrieval.
struct MemoryEntry {
    /// Unique identifier (UUID)
    std::string id;

    /// Text content of the memory
    std::string content;

    /// Structured metadata (arbitrary JSON values)
    std::map<std::string, nlohmann::json> metadata;

    /// Creation timestamp
    std::chrono::system_clock::time_point timestamp;

    /// Number of times this entry has been accessed
    size_t access_count;

    /// Last access timestamp (for LRU eviction)
    std::optional<std::chrono::system_clock::time_point> last_accessed;

    /// Importance score (0.0-1.0)
    double importance;

    /// Session identifier for grouping related memories
    std::optional<std::string> session_id;

    /// Create a new memory entry
    ///
    /// @param content Text content
    /// @param metadata Structured metadata
    /// @param importance Importance score (0.0-1.0)
    /// @param session_id Optional session identifier
    /// @return MemoryEntry with generated UUID and current timestamp
    static MemoryEntry create(
        const std::string& content,
        const std::map<std::string, nlohmann::json>& metadata = {},
        double importance = 0.5,
        const std::optional<std::string>& session_id = std::nullopt
    );

    /// Record an access to this entry (updates last_accessed and access_count)
    void record_access();

    /// Check if entry has expired based on TTL
    ///
    /// @param ttl_seconds Time-to-live in seconds
    /// @return true if age exceeds TTL
    bool is_expired(int64_t ttl_seconds) const;

    /// Calculate relevance score for a query
    ///
    /// Score components:
    /// - Keyword match: 0.5 if query found in lowercase content
    /// - Importance: importance * 0.3
    /// - Recency: (1.0 - age_days/365) * 0.2
    ///
    /// @param query Search query
    /// @return Relevance score (0.0-1.0)
    double calculate_relevance(const std::string& query) const;

    /// Get age of entry in seconds
    ///
    /// @return Age since creation in seconds
    int64_t age_seconds() const;

    /// Get age of entry in days
    ///
    /// @return Age since creation in days
    double age_days() const;

    /// Serialize to JSON
    nlohmann::json to_json() const;

    /// Deserialize from JSON
    ///
    /// @param j JSON object
    /// @return MemoryEntry
    static MemoryEntry from_json(const nlohmann::json& j);

private:
    /// Generate a UUID v4 string
    static std::string generate_uuid();

    /// Convert string to lowercase for case-insensitive matching
    static std::string to_lowercase(const std::string& str);
};

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
