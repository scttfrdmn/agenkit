/**
 * @file caching.cpp
 * @brief Caching middleware implementation
 */

#include "agenkit/middleware/caching.hpp"

namespace agenkit {
namespace middleware {

std::optional<core::Message> CachingMiddleware::get_cached(const std::string& key) {
    std::shared_lock<std::shared_mutex> lock(mutex_);

    auto it = cache_.find(key);
    if (it == cache_.end()) {
        return std::nullopt;
    }

    // Check if expired
    if (it->second.first.is_expired()) {
        // Need to upgrade to unique lock for modification
        lock.unlock();
        std::unique_lock<std::shared_mutex> write_lock(mutex_);

        // Check again after acquiring write lock
        it = cache_.find(key);
        if (it != cache_.end() && it->second.first.is_expired()) {
            lru_list_.erase(it->second.second);
            cache_.erase(it);
            metrics_.expired_entries++;
        }

        return std::nullopt;
    }

    // Cache hit - need write access to update LRU
    lock.unlock();
    std::unique_lock<std::shared_mutex> write_lock(mutex_);

    // Re-check after acquiring write lock
    it = cache_.find(key);
    if (it == cache_.end() || it->second.first.is_expired()) {
        return std::nullopt;
    }

    // Update LRU order
    lru_list_.erase(it->second.second);
    lru_list_.push_front(key);
    it->second.second = lru_list_.begin();

    return it->second.first.response;
}

void CachingMiddleware::store_in_cache(
    const std::string& key,
    const core::Message& response
) {
    std::unique_lock<std::shared_mutex> lock(mutex_);

    // Check if we need to evict
    while (cache_.size() >= config_.max_cache_size) {
        evict_lru();
    }

    // Calculate expiry
    auto expiry = std::chrono::steady_clock::now() + config_.default_ttl;

    // Add to front of LRU list
    lru_list_.push_front(key);

    // Store in cache using insert_or_assign to avoid default construction
    cache_.insert_or_assign(key, std::make_pair(
        CacheEntry{response, expiry},
        lru_list_.begin()
    ));
}

void CachingMiddleware::evict_lru() {
    if (lru_list_.empty()) {
        return;
    }

    // Remove least recently used (back of list)
    auto lru_key = lru_list_.back();
    lru_list_.pop_back();
    cache_.erase(lru_key);
    metrics_.cache_evictions++;
}

std::future<core::Result<core::Message, core::AgentError>>
CachingMiddleware::process(core::Message message) {
    metrics_.total_requests++;

    // Generate cache key
    auto key = config_.key_generator(message);

    // Try to get from cache
    auto cached = get_cached(key);
    if (cached.has_value()) {
        // Cache hit
        metrics_.cache_hits++;
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(cached.value())
        );
    }

    // Cache miss - process request
    metrics_.cache_misses++;
    auto future = agent_->process(message);
    auto result = future.get();

    // Store in cache if successful (or if caching errors is enabled)
    if (result.is_ok()) {
        store_in_cache(key, result.unwrap());
    } else if (config_.cache_errors) {
        // For error responses, we don't cache them by default
        // But if cache_errors is enabled, we could cache them here
        // For now, we skip caching errors
    }

    return core::make_ready_future(std::move(result));
}

} // namespace middleware
} // namespace agenkit
