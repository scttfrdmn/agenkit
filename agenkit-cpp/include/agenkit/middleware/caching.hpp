/**
 * @file caching.hpp
 * @brief Caching middleware with LRU eviction and TTL expiration
 *
 * Implements response caching with:
 * - LRU (Least Recently Used) eviction policy
 * - TTL (Time To Live) expiration
 * - Custom key generation
 * - Cache invalidation
 * - Thread-safe operations
 *
 * Features:
 * - Configurable cache size and TTL
 * - Custom key generation from messages
 * - Hit/miss metrics
 * - Manual invalidation support
 * - Thread-safe with shared_mutex (multiple readers, single writer)
 *
 * @example
 * @code
 * auto config = CachingConfig::builder()
 *     .max_cache_size(1000)
 *     .default_ttl(std::chrono::minutes(5))
 *     .build();
 *
 * auto cached_agent = std::make_shared<CachingMiddleware>(agent, config);
 * auto result = cached_agent->process(message).get();
 * @endcode
 */

#pragma once

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/core/errors.hpp"
#include <chrono>
#include <memory>
#include <atomic>
#include <mutex>
#include <shared_mutex>
#include <unordered_map>
#include <list>
#include <functional>
#include <optional>

namespace agenkit {
namespace middleware {

/// Cache entry with TTL
struct CacheEntry {
    core::Message response;
    std::chrono::steady_clock::time_point expiry;

    bool is_expired() const {
        return std::chrono::steady_clock::now() >= expiry;
    }
};

/// Caching configuration
struct CachingConfig {
    /// Maximum cache size (number of entries)
    size_t max_cache_size = 1000;

    /// Default TTL for cache entries
    std::chrono::milliseconds default_ttl{300000};  // 5 minutes

    /// Custom key generator (defaults to message content hash)
    std::function<std::string(const core::Message&)> key_generator = nullptr;

    /// Whether to cache error responses
    bool cache_errors = false;

    /// Validate configuration
    void validate() const {
        if (max_cache_size < 1) {
            throw std::invalid_argument("max_cache_size must be >= 1");
        }
        if (default_ttl.count() <= 0) {
            throw std::invalid_argument("default_ttl must be positive");
        }
    }

    /// Builder for fluent configuration
    class Builder;

    static Builder builder();
};

/// Builder implementation for CachingConfig
class CachingConfig::Builder {
public:
    Builder() = default;

    Builder& max_cache_size(size_t n) {
        config_.max_cache_size = n;
        return *this;
    }

    Builder& default_ttl(std::chrono::milliseconds duration) {
        config_.default_ttl = duration;
        return *this;
    }

    Builder& key_generator(std::function<std::string(const core::Message&)> gen) {
        config_.key_generator = std::move(gen);
        return *this;
    }

    Builder& cache_errors(bool cache) {
        config_.cache_errors = cache;
        return *this;
    }

    CachingConfig build() {
        config_.validate();
        return config_;
    }

private:
    CachingConfig config_;
};

inline CachingConfig::Builder CachingConfig::builder() {
    return Builder();
}

/// Caching metrics
struct CachingMetrics {
    std::atomic<uint64_t> total_requests{0};
    std::atomic<uint64_t> cache_hits{0};
    std::atomic<uint64_t> cache_misses{0};
    std::atomic<uint64_t> cache_evictions{0};
    std::atomic<uint64_t> cache_invalidations{0};
    std::atomic<uint64_t> expired_entries{0};

    /// Get snapshot of current metrics
    struct Snapshot {
        uint64_t total_requests;
        uint64_t cache_hits;
        uint64_t cache_misses;
        uint64_t cache_evictions;
        uint64_t cache_invalidations;
        uint64_t expired_entries;
        size_t current_cache_size;
        double hit_rate;
        double miss_rate;
    };

    Snapshot snapshot(size_t current_cache_size) const {
        auto total = total_requests.load();
        auto hits = cache_hits.load();
        auto misses = cache_misses.load();

        return Snapshot{
            total,
            hits,
            misses,
            cache_evictions.load(),
            cache_invalidations.load(),
            expired_entries.load(),
            current_cache_size,
            total > 0 ? static_cast<double>(hits) / total : 0.0,
            total > 0 ? static_cast<double>(misses) / total : 0.0
        };
    }
};

/// Caching middleware - wraps an agent with LRU cache
class CachingMiddleware : public core::Agent {
public:
    /// Create caching middleware
    ///
    /// @param agent Underlying agent to wrap
    /// @param config Caching configuration
    CachingMiddleware(
        std::shared_ptr<core::Agent> agent,
        CachingConfig config = CachingConfig()
    ) : agent_(std::move(agent)), config_(std::move(config)) {
        config_.validate();

        // Use default key generator if none provided
        if (!config_.key_generator) {
            config_.key_generator = [](const core::Message& msg) {
                return std::to_string(std::hash<std::string>{}(msg.content_as_str()));
            };
        }
    }

    std::string name() const override {
        return "caching(" + agent_->name() + ")";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /// Get current metrics
    const CachingMetrics& metrics() const {
        return metrics_;
    }

    /// Get configuration
    const CachingConfig& config() const {
        return config_;
    }

    /// Get current cache size
    size_t cache_size() const {
        std::shared_lock<std::shared_mutex> lock(mutex_);
        return cache_.size();
    }

    /// Clear all cache entries
    void clear_cache() {
        std::unique_lock<std::shared_mutex> lock(mutex_);
        cache_.clear();
        lru_list_.clear();
    }

    /// Invalidate a specific cache entry
    ///
    /// @param message Message to generate key from
    /// @return true if entry was found and removed
    bool invalidate(const core::Message& message) {
        std::unique_lock<std::shared_mutex> lock(mutex_);
        auto key = config_.key_generator(message);
        auto it = cache_.find(key);
        if (it != cache_.end()) {
            lru_list_.erase(it->second.second);
            cache_.erase(it);
            metrics_.cache_invalidations++;
            return true;
        }
        return false;
    }

private:
    std::shared_ptr<core::Agent> agent_;
    CachingConfig config_;
    mutable CachingMetrics metrics_;

    // Cache storage (protected by shared_mutex)
    mutable std::shared_mutex mutex_;
    std::unordered_map<
        std::string,
        std::pair<CacheEntry, std::list<std::string>::iterator>
    > cache_;
    std::list<std::string> lru_list_;  // Most recently used at front

    /// Get cached response if available
    std::optional<core::Message> get_cached(const std::string& key);

    /// Store response in cache
    void store_in_cache(const std::string& key, const core::Message& response);

    /// Evict least recently used entry
    void evict_lru();

    /// Move key to front of LRU list (most recently used)
    void touch_lru(const std::string& key);
};

} // namespace middleware
} // namespace agenkit
