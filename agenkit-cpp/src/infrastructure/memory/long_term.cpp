#include "agenkit/infrastructure/memory/long_term.hpp"
#include <algorithm>
#include <stdexcept>

namespace agenkit {
namespace infrastructure {
namespace memory {

LongTermMemory::LongTermMemory(double min_importance)
    : min_importance_(min_importance) {
    if (min_importance < 0.0 || min_importance > 1.0) {
        throw std::invalid_argument("min_importance must be between 0.0 and 1.0");
    }
}

LongTermMemoryResult<std::optional<std::string>> LongTermMemory::store(const MemoryEntry& entry) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Filter by importance threshold
    if (entry.importance < min_importance_) {
        return core::Result<std::optional<std::string>, LongTermMemoryError>::ok(std::nullopt);
    }

    storage_[entry.id] = entry;

    return core::Result<std::optional<std::string>, LongTermMemoryError>::ok(entry.id);
}

LongTermMemoryResult<std::vector<MemoryEntry>> LongTermMemory::retrieve(
    const std::string& query,
    size_t limit
) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Calculate relevance for all entries
    std::vector<std::pair<double, MemoryEntry>> scored_entries;
    scored_entries.reserve(storage_.size());

    for (auto& [id, entry] : storage_) {
        double relevance = entry.calculate_relevance(query);
        // Record access
        const_cast<MemoryEntry&>(entry).record_access();
        scored_entries.emplace_back(relevance, entry);
    }

    // Sort by relevance (descending)
    std::sort(scored_entries.begin(), scored_entries.end(),
        [](const auto& a, const auto& b) {
            return a.first > b.first;
        });

    // Extract top N entries
    std::vector<MemoryEntry> results;
    results.reserve(std::min(limit, scored_entries.size()));

    for (size_t i = 0; i < std::min(limit, scored_entries.size()); ++i) {
        results.push_back(std::move(scored_entries[i].second));
    }

    return core::Result<std::vector<MemoryEntry>, LongTermMemoryError>::ok(std::move(results));
}

LongTermMemoryResult<bool> LongTermMemory::del(const std::string& entry_id) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto it = storage_.find(entry_id);
    if (it != storage_.end()) {
        storage_.erase(it);
        return core::Result<bool, LongTermMemoryError>::ok(true);
    }

    return core::Result<bool, LongTermMemoryError>::ok(false);
}

LongTermMemoryResult<std::vector<MemoryEntry>> LongTermMemory::get_all() {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<MemoryEntry> results;
    results.reserve(storage_.size());

    for (const auto& [id, entry] : storage_) {
        results.push_back(entry);
    }

    return core::Result<std::vector<MemoryEntry>, LongTermMemoryError>::ok(std::move(results));
}

void LongTermMemory::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    storage_.clear();
}

size_t LongTermMemory::count() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return storage_.size();
}

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
