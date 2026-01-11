#include "agenkit/infrastructure/memory/short_term.hpp"
#include <algorithm>
#include <stdexcept>

namespace agenkit {
namespace infrastructure {
namespace memory {

ShortTermMemory::ShortTermMemory(size_t max_messages, int64_t ttl_seconds)
    : max_messages_(max_messages), ttl_seconds_(ttl_seconds) {
    if (max_messages == 0) {
        throw std::invalid_argument("max_messages must be greater than 0");
    }
    if (ttl_seconds <= 0) {
        throw std::invalid_argument("ttl_seconds must be greater than 0");
    }
}

void ShortTermMemory::clean_expired() {
    // Remove entries where age > TTL
    messages_.erase(
        std::remove_if(messages_.begin(), messages_.end(),
            [this](const MemoryEntry& entry) {
                return entry.is_expired(ttl_seconds_);
            }),
        messages_.end()
    );
}

void ShortTermMemory::evict_lru() {
    if (messages_.empty()) {
        return;
    }

    // Sort by last_accessed (oldest first)
    // Never-accessed entries are considered oldest
    std::sort(messages_.begin(), messages_.end(),
        [](const MemoryEntry& a, const MemoryEntry& b) {
            // If neither has been accessed, sort by timestamp
            if (!a.last_accessed.has_value() && !b.last_accessed.has_value()) {
                return a.timestamp < b.timestamp;
            }
            // Never-accessed is oldest
            if (!a.last_accessed.has_value()) return true;
            if (!b.last_accessed.has_value()) return false;
            // Compare last_accessed times
            return a.last_accessed.value() < b.last_accessed.value();
        });

    // Remove the least recently used (first element after sort)
    messages_.erase(messages_.begin());
}

ShortTermMemoryResult<std::string> ShortTermMemory::store(const MemoryEntry& entry) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Clean expired entries
    clean_expired();

    // Evict LRU if at capacity
    if (messages_.size() >= max_messages_) {
        evict_lru();
    }

    messages_.push_back(entry);

    return core::Result<std::string, ShortTermMemoryError>::ok(entry.id);
}

ShortTermMemoryResult<std::vector<MemoryEntry>> ShortTermMemory::retrieve(size_t limit) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Clean expired entries
    clean_expired();

    std::vector<MemoryEntry> results;

    // Get most recent non-expired entries
    size_t start_index = messages_.size() > limit ? messages_.size() - limit : 0;

    for (size_t i = start_index; i < messages_.size(); ++i) {
        auto& entry = messages_[i];
        // Record access
        const_cast<MemoryEntry&>(entry).record_access();
        results.push_back(entry);
    }

    // Reverse to get most recent first
    std::reverse(results.begin(), results.end());

    return core::Result<std::vector<MemoryEntry>, ShortTermMemoryError>::ok(std::move(results));
}

ShortTermMemoryResult<bool> ShortTermMemory::remove(const std::string& entry_id) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto it = std::find_if(messages_.begin(), messages_.end(),
        [&entry_id](const MemoryEntry& entry) {
            return entry.id == entry_id;
        });

    if (it != messages_.end()) {
        messages_.erase(it);
        return core::Result<bool, ShortTermMemoryError>::ok(true);
    }

    return core::Result<bool, ShortTermMemoryError>::ok(false);
}

ShortTermMemoryResult<std::vector<MemoryEntry>> ShortTermMemory::get_all() {
    std::lock_guard<std::mutex> lock(mutex_);

    // Clean expired entries
    clean_expired();

    // Return copy with most recent first
    std::vector<MemoryEntry> results(messages_.rbegin(), messages_.rend());

    return core::Result<std::vector<MemoryEntry>, ShortTermMemoryError>::ok(std::move(results));
}

void ShortTermMemory::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    messages_.clear();
}

size_t ShortTermMemory::count() {
    std::lock_guard<std::mutex> lock(mutex_);
    // Clean expired before counting
    clean_expired();
    return messages_.size();
}

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
