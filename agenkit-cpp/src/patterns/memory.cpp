/**
 * @file memory.cpp
 * @brief Implementation of Memory hierarchy pattern
 */

#include "agenkit/patterns/memory.hpp"
#include <algorithm>
#include <sstream>
#include <random>

namespace agenkit {
namespace patterns {

// ============================================================================
// MemoryEntry
// ============================================================================

static std::string generate_memory_id() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<uint64_t> dis;

    std::ostringstream oss;
    oss << "mem_" << std::hex << dis(gen);
    return oss.str();
}

MemoryEntry::MemoryEntry()
    : id(generate_memory_id()),
      timestamp(std::chrono::system_clock::now()),
      access_count(0),
      importance(0.0) {}

MemoryEntry::MemoryEntry(const std::string& content_str, double imp)
    : id(generate_memory_id()),
      content(content_str),
      timestamp(std::chrono::system_clock::now()),
      access_count(0),
      importance(imp) {}

// ============================================================================
// WorkingMemory
// ============================================================================

WorkingMemory::WorkingMemory(int max_messages)
    : max_messages_(max_messages) {}

void WorkingMemory::store(const MemoryEntry& entry) {
    messages_.push_back(entry);

    // FIFO eviction: Remove oldest if over capacity (O(1) with deque)
    while (static_cast<int>(messages_.size()) > max_messages_) {
        messages_.pop_front();
    }
}

std::vector<MemoryEntry> WorkingMemory::retrieve(
    const std::string& query,
    int limit
) {
    std::vector<MemoryEntry> results;
    results.reserve(std::min(static_cast<size_t>(limit), messages_.size()));

    // Simple substring search in reverse order (most recent first)
    for (auto it = messages_.rbegin(); it != messages_.rend(); ++it) {
        if (it->content.find(query) != std::string::npos) {
            // Update access tracking on the original entry
            size_t index = std::distance(it, messages_.rend()) - 1;
            messages_[index].access_count++;
            messages_[index].last_accessed = std::chrono::system_clock::now();

            // Add updated entry to results
            results.push_back(messages_[index]);

            if (static_cast<int>(results.size()) >= limit) {
                break;
            }
        }
    }

    return results;
}

void WorkingMemory::del(const std::string& entry_id) {
    messages_.erase(
        std::remove_if(messages_.begin(), messages_.end(),
            [&entry_id](const MemoryEntry& e) { return e.id == entry_id; }),
        messages_.end()
    );
}

std::vector<MemoryEntry> WorkingMemory::get_all() const {
    return std::vector<MemoryEntry>(messages_.begin(), messages_.end());
}

size_t WorkingMemory::size() const {
    return messages_.size();
}

void WorkingMemory::clear() {
    messages_.clear();
}

// ============================================================================
// ShortTermMemory
// ============================================================================

ShortTermMemory::ShortTermMemory(
    int max_messages,
    int ttl_seconds
) : max_messages_(max_messages),
    ttl_(ttl_seconds) {}

void ShortTermMemory::store(const MemoryEntry& entry) {
    // Remove expired entries before adding
    cleanup_expired();

    messages_.push_back(entry);

    // Remove oldest if over capacity (O(1) with deque)
    while (static_cast<int>(messages_.size()) > max_messages_) {
        messages_.pop_front();
    }
}

std::vector<MemoryEntry> ShortTermMemory::retrieve(
    const std::string& query,
    int limit
) {
    // Remove expired entries first
    cleanup_expired();

    std::vector<MemoryEntry> results;
    results.reserve(std::min(static_cast<size_t>(limit), messages_.size()));

    // Search in reverse order (most recent first)
    for (auto it = messages_.rbegin(); it != messages_.rend(); ++it) {
        if (it->content.find(query) != std::string::npos) {
            // Update access tracking on the original entry
            size_t index = std::distance(it, messages_.rend()) - 1;
            messages_[index].access_count++;
            messages_[index].last_accessed = std::chrono::system_clock::now();

            // Add updated entry to results
            results.push_back(messages_[index]);

            if (static_cast<int>(results.size()) >= limit) {
                break;
            }
        }
    }

    return results;
}

void ShortTermMemory::del(const std::string& entry_id) {
    messages_.erase(
        std::remove_if(messages_.begin(), messages_.end(),
            [&entry_id](const MemoryEntry& e) { return e.id == entry_id; }),
        messages_.end()
    );
}

std::vector<MemoryEntry> ShortTermMemory::get_all() const {
    return std::vector<MemoryEntry>(messages_.begin(), messages_.end());
}

size_t ShortTermMemory::size() const {
    return messages_.size();
}

int ShortTermMemory::cleanup_expired() {
    if (ttl_.count() == 0) {
        return 0;  // No expiry
    }

    size_t original_size = messages_.size();

    messages_.erase(
        std::remove_if(messages_.begin(), messages_.end(),
            [this](const MemoryEntry& e) { return is_expired(e); }),
        messages_.end()
    );

    return static_cast<int>(original_size - messages_.size());
}

bool ShortTermMemory::is_expired(const MemoryEntry& entry) const {
    if (ttl_.count() == 0) {
        return false;
    }

    auto now = std::chrono::system_clock::now();
    auto age = std::chrono::duration_cast<std::chrono::seconds>(
        now - entry.timestamp
    );

    return age > ttl_;
}

// ============================================================================
// LongTermMemory
// ============================================================================

LongTermMemory::LongTermMemory(double importance_threshold)
    : importance_threshold_(importance_threshold) {}

void LongTermMemory::store(const MemoryEntry& entry) {
    // Only store if importance meets threshold
    if (entry.importance >= importance_threshold_) {
        memories_.push_back(entry);
    }
}

std::vector<MemoryEntry> LongTermMemory::retrieve(
    const std::string& query,
    int limit
) {
    std::vector<size_t> matching_indices;

    // Search and collect matching indices
    for (size_t i = 0; i < memories_.size(); ++i) {
        if (memories_[i].content.find(query) != std::string::npos) {
            matching_indices.push_back(i);

            // Update access tracking
            memories_[i].access_count++;
            memories_[i].last_accessed = std::chrono::system_clock::now();
        }
    }

    // Sort indices by importance (highest first)
    std::sort(matching_indices.begin(), matching_indices.end(),
        [this](size_t a, size_t b) {
            return memories_[a].importance > memories_[b].importance;
        }
    );

    // Build results from sorted indices
    std::vector<MemoryEntry> results;
    results.reserve(std::min(matching_indices.size(), static_cast<size_t>(limit)));
    for (size_t i = 0; i < matching_indices.size() && static_cast<int>(i) < limit; ++i) {
        results.push_back(memories_[matching_indices[i]]);
    }

    return results;
}

void LongTermMemory::del(const std::string& entry_id) {
    memories_.erase(
        std::remove_if(memories_.begin(), memories_.end(),
            [&entry_id](const MemoryEntry& e) { return e.id == entry_id; }),
        memories_.end()
    );
}

std::vector<MemoryEntry> LongTermMemory::get_all() const {
    return memories_;
}

size_t LongTermMemory::size() const {
    return memories_.size();
}

// ============================================================================
// MemoryHierarchy
// ============================================================================

MemoryHierarchy::MemoryHierarchy(
    int working_max,
    int short_term_max,
    int ttl_seconds,
    double importance_threshold
) : working_memory_(working_max),
    short_term_memory_(short_term_max, ttl_seconds),
    long_term_memory_(importance_threshold) {}

void MemoryHierarchy::store(
    const std::string& content,
    double importance,
    const std::map<std::string, std::string>& metadata
) {
    MemoryEntry entry(content, importance);
    entry.metadata = metadata;

    // Store in working memory (always)
    working_memory_.store(entry);

    // Store in short-term memory (for recent access)
    short_term_memory_.store(entry);

    // Store in long-term memory (if important enough)
    // Use the long-term memory's threshold
    long_term_memory_.store(entry);
}

std::vector<MemoryEntry> MemoryHierarchy::retrieve(
    const std::string& query,
    int limit
) {
    std::vector<MemoryEntry> all_results;
    std::map<std::string, MemoryEntry> unique_results;

    // Search working memory first (most relevant)
    auto working_results = working_memory_.retrieve(query, limit);
    for (const auto& entry : working_results) {
        unique_results.insert({entry.id, entry});
    }

    // Then short-term memory (recent context)
    if (static_cast<int>(unique_results.size()) < limit) {
        auto short_term_results = short_term_memory_.retrieve(
            query,
            limit - static_cast<int>(unique_results.size())
        );
        for (const auto& entry : short_term_results) {
            unique_results.insert({entry.id, entry});
        }
    }

    // Finally long-term memory (important facts)
    if (static_cast<int>(unique_results.size()) < limit) {
        auto long_term_results = long_term_memory_.retrieve(
            query,
            limit - static_cast<int>(unique_results.size())
        );
        for (const auto& entry : long_term_results) {
            unique_results.insert({entry.id, entry});
        }
    }

    // Convert map to vector
    for (const auto& pair : unique_results) {
        all_results.push_back(pair.second);
    }

    // Sort by recency (most recent first)
    std::sort(all_results.begin(), all_results.end(),
        [](const MemoryEntry& a, const MemoryEntry& b) {
            return a.timestamp > b.timestamp;
        }
    );

    // Limit results
    if (static_cast<int>(all_results.size()) > limit) {
        all_results.resize(limit);
    }

    return all_results;
}

WorkingMemory& MemoryHierarchy::get_working_memory() {
    return working_memory_;
}

ShortTermMemory& MemoryHierarchy::get_short_term_memory() {
    return short_term_memory_;
}

LongTermMemory& MemoryHierarchy::get_long_term_memory() {
    return long_term_memory_;
}

size_t MemoryHierarchy::total_size() const {
    return working_memory_.size() +
           short_term_memory_.size() +
           long_term_memory_.size();
}

} // namespace patterns
} // namespace agenkit
