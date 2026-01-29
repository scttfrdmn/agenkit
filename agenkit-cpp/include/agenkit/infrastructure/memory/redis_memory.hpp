#pragma once

#include <chrono>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace infrastructure {
namespace memory {

/// Message returned from Redis
struct RedisMessage {
    std::string role;
    std::string content;
};

/// Redis-backed memory with TTL and persistence support
///
/// Features:
/// - Persistent storage (survives restarts)
/// - TTL support (automatic expiry)
/// - Multi-instance agents (shared memory)
/// - Fast access (in-memory Redis)
/// - Scalable (Redis cluster support)
///
/// Use cases:
/// - Production deployments
/// - Multi-instance agents
/// - When persistence needed
/// - Shared memory across agents
///
/// Example:
/// ```cpp
/// using namespace agenkit::infrastructure::memory;
///
/// // Create Redis memory with 24-hour TTL
/// auto memory = std::make_unique<RedisMemory>(
///     "localhost",
///     6379,
///     86400,  // 24 hours
///     "agenkit:memory"
/// );
///
/// // Store message with metadata
/// std::map<std::string, nlohmann::json> metadata;
/// metadata["importance"] = 0.8;
/// metadata["tags"] = nlohmann::json::array({"question", "technical"});
/// memory->store("session-123", "user", "Hello", metadata);
///
/// // Retrieve messages
/// auto messages = memory->retrieve("session-123", 10);
///
/// // Clear session
/// memory->clear("session-123");
/// ```
///
/// Redis Data Structure:
///   Key: "agenkit:memory:{session_id}:messages"
///   Type: Sorted Set (ZSET)
///   Score: Timestamp (for ordering)
///   Value: JSON(message, metadata)
class RedisMemory {
public:
    /// Create a new Redis memory instance
    ///
    /// @param host Redis host (default: localhost)
    /// @param port Redis port (default: 6379)
    /// @param ttl Time-to-live in seconds (0 = no expiry)
    /// @param key_prefix Prefix for Redis keys
    RedisMemory(
        const std::string& host = "localhost",
        int port = 6379,
        int64_t ttl = 86400,
        const std::string& key_prefix = "agenkit:memory"
    );

    /// Destructor
    ~RedisMemory();

    /// Store a message in Redis with optional metadata
    ///
    /// @param session_id Session identifier
    /// @param role Message role (user, assistant, system)
    /// @param content Message content
    /// @param metadata Optional metadata
    void store(
        const std::string& session_id,
        const std::string& role,
        const std::string& content,
        const std::map<std::string, nlohmann::json>& metadata = {}
    );

    /// Retrieve messages from Redis with filtering
    ///
    /// @param session_id Session identifier
    /// @param limit Maximum messages to return (default: 10)
    /// @param time_range Optional (start, end) time range in seconds
    /// @param importance_threshold Optional minimum importance score
    /// @param tags Optional list of tags to filter by
    /// @return Vector of messages (most recent first)
    std::vector<RedisMessage> retrieve(
        const std::string& session_id,
        size_t limit = 10,
        const std::optional<std::pair<double, double>>& time_range = std::nullopt,
        const std::optional<double>& importance_threshold = std::nullopt,
        const std::optional<std::vector<std::string>>& tags = std::nullopt
    );

    /// Create a summary of conversation history
    ///
    /// Simple implementation: Returns a message with concatenated content.
    /// Production use should use LLM-based summarization.
    ///
    /// @param session_id Session identifier
    /// @return Summary message
    RedisMessage summarize(const std::string& session_id);

    /// Clear all memory for a session
    ///
    /// @param session_id Session identifier
    void clear(const std::string& session_id);

    /// Get the number of messages stored for a session
    ///
    /// @param session_id Session identifier
    /// @return Number of messages
    size_t get_session_count(const std::string& session_id);

    /// Get all session IDs
    ///
    /// @return Vector of session IDs
    std::vector<std::string> get_all_sessions();

    /// Get memory usage statistics
    ///
    /// @return (total_sessions, total_messages, ttl)
    std::tuple<size_t, size_t, int64_t> get_memory_usage();

    /// Get memory capabilities
    ///
    /// @return Vector of capability strings
    static std::vector<std::string> capabilities();

private:
    /// Stored message format in Redis
    struct StoredMessage {
        std::string role;
        std::string content;
        std::map<std::string, nlohmann::json> metadata;
    };

    /// Get Redis key for a session
    std::string session_key(const std::string& session_id) const;

    /// Serialize message and metadata to JSON string
    std::string serialize_message(
        const std::string& role,
        const std::string& content,
        const std::map<std::string, nlohmann::json>& metadata
    ) const;

    /// Deserialize JSON string to message and metadata
    std::pair<RedisMessage, std::map<std::string, nlohmann::json>>
    deserialize_message(const std::string& data) const;

    /// Get current timestamp in seconds since epoch
    static double get_timestamp();

    std::string host_;
    [[maybe_unused]] int port_;
    int64_t ttl_;
    std::string key_prefix_;

    // Forward declaration for Redis connection (pimpl idiom)
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
