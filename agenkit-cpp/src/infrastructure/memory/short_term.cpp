#include "agenkit/infrastructure/memory/short_term.hpp"
#include "agenkit/utils/simd.hpp"
#include <algorithm>
#include <stdexcept>

#if AGENKIT_HAS_AVX2
#include <immintrin.h>
#endif

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
    if (messages_.empty()) {
        return;
    }

    // Get current time once (not N times)
    auto now = std::chrono::system_clock::now();

#if AGENKIT_HAS_AVX2
    // SIMD-optimized expiration checking (process 4 entries at a time)
    auto now_ticks = now.time_since_epoch().count();
    int64_t ttl_ticks = ttl_seconds_ * 1000000000LL;  // Convert to nanoseconds

    std::vector<MemoryEntry> valid_entries;
    valid_entries.reserve(messages_.size());

    size_t i = 0;
    const size_t batch_size = 4;

    // Process in batches of 4 using AVX2
    __m256i now_vec = _mm256_set1_epi64x(now_ticks);
    __m256i ttl_vec = _mm256_set1_epi64x(ttl_ticks);

    for (; i + batch_size <= messages_.size(); i += batch_size) {
        // Load 4 timestamps
        int64_t timestamps[4];
        for (size_t j = 0; j < batch_size; j++) {
            timestamps[j] = messages_[i + j].timestamp.time_since_epoch().count();
        }

        __m256i ts_vec = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(timestamps));

        // Calculate ages: now - timestamp
        __m256i age_vec = _mm256_sub_epi64(now_vec, ts_vec);

        // Check if age > ttl (entry is expired)
        __m256i expired_mask = _mm256_cmpgt_epi64(age_vec, ttl_vec);

        // Extract mask (1 bit per 64-bit element)
        // We need to check which entries are NOT expired
        int64_t expired[4];
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(expired), expired_mask);

        // Keep non-expired entries
        for (size_t j = 0; j < batch_size; j++) {
            if (expired[j] == 0) {  // Not expired (mask is 0)
                valid_entries.push_back(std::move(messages_[i + j]));
            }
        }
    }

    // Handle remaining entries (scalar)
    for (; i < messages_.size(); i++) {
        if (!messages_[i].is_expired(ttl_seconds_)) {
            valid_entries.push_back(std::move(messages_[i]));
        }
    }

    messages_ = std::move(valid_entries);
#else
    // Scalar fallback (still optimized to get time once)
    // Use chrono duration for correct unit handling
    auto threshold = now - std::chrono::seconds(ttl_seconds_);

    messages_.erase(
        std::remove_if(messages_.begin(), messages_.end(),
            [threshold](const MemoryEntry& entry) {
                return entry.timestamp < threshold;
            }),
        messages_.end()
    );
#endif
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
    results.reserve(std::min(limit, messages_.size()));  // Pre-allocate for efficiency

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

ShortTermMemoryResult<bool> ShortTermMemory::del(const std::string& entry_id) {
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
