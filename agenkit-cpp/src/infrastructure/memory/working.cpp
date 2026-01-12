#include "agenkit/infrastructure/memory/working.hpp"
#include <algorithm>
#include <stdexcept>

namespace agenkit {
namespace infrastructure {
namespace memory {

WorkingMemory::WorkingMemory(size_t max_messages)
    : max_messages_(max_messages) {
    if (max_messages == 0) {
        throw std::invalid_argument("max_messages must be greater than 0");
    }
}

void WorkingMemory::evict_if_needed() {
    if (messages_.size() >= max_messages_) {
        // FIFO: remove oldest (first) entry
        messages_.erase(messages_.begin());
    }
}

WorkingMemoryResult<std::string> WorkingMemory::store(const MemoryEntry& entry) {
    std::lock_guard<std::mutex> lock(mutex_);

    evict_if_needed();
    messages_.push_back(entry);

    return core::Result<std::string, WorkingMemoryError>::ok(entry.id);
}

WorkingMemoryResult<std::vector<MemoryEntry>> WorkingMemory::retrieve(size_t limit) {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<MemoryEntry> results;

    // Return most recent entries (from end of vector)
    size_t start_index = messages_.size() > limit ? messages_.size() - limit : 0;

    for (size_t i = start_index; i < messages_.size(); ++i) {
        auto& entry = messages_[i];
        // Record access (need to modify the entry)
        const_cast<MemoryEntry&>(entry).record_access();
        results.push_back(entry);
    }

    // Reverse to get most recent first
    std::reverse(results.begin(), results.end());

    return core::Result<std::vector<MemoryEntry>, WorkingMemoryError>::ok(std::move(results));
}

WorkingMemoryResult<bool> WorkingMemory::del(const std::string& entry_id) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto it = std::find_if(messages_.begin(), messages_.end(),
        [&entry_id](const MemoryEntry& entry) {
            return entry.id == entry_id;
        });

    if (it != messages_.end()) {
        messages_.erase(it);
        return core::Result<bool, WorkingMemoryError>::ok(true);
    }

    return core::Result<bool, WorkingMemoryError>::ok(false);
}

WorkingMemoryResult<std::vector<MemoryEntry>> WorkingMemory::get_all() {
    std::lock_guard<std::mutex> lock(mutex_);

    // Return copy with most recent first
    std::vector<MemoryEntry> results(messages_.rbegin(), messages_.rend());

    return core::Result<std::vector<MemoryEntry>, WorkingMemoryError>::ok(std::move(results));
}

void WorkingMemory::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    messages_.clear();
}

size_t WorkingMemory::count() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return messages_.size();
}

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
