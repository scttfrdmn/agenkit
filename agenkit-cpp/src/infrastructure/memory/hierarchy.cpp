#include "agenkit/infrastructure/memory/hierarchy.hpp"
#include <algorithm>
#include <unordered_set>

namespace agenkit {
namespace infrastructure {
namespace memory {

MemoryHierarchy::MemoryHierarchy(
    std::unique_ptr<WorkingMemory> working,
    std::unique_ptr<ShortTermMemory> short_term,
    std::unique_ptr<LongTermMemory> long_term
) : working_(std::move(working)),
    short_term_(std::move(short_term)),
    long_term_(std::move(long_term)) {
}

HierarchyResult<std::string> MemoryHierarchy::store(
    const std::string& content,
    const std::map<std::string, nlohmann::json>& metadata,
    double importance,
    const std::optional<std::string>& session_id
) {
    // Create entry
    auto entry = MemoryEntry::create(content, metadata, importance, session_id);
    std::string entry_id = entry.id;

    // Always store in working memory
    auto working_result = working_->store(entry);
    if (!working_result.is_ok()) {
        return core::Result<std::string, HierarchyError>::err(
            HierarchyError::WorkingMemoryError
        );
    }

    // Store in short-term if available
    if (short_term_) {
        auto st_result = short_term_->store(entry);
        if (!st_result.is_ok()) {
            return core::Result<std::string, HierarchyError>::err(
                HierarchyError::ShortTermMemoryError
            );
        }
    }

    // Store in long-term if available AND importance >= threshold
    if (long_term_) {
        if (importance >= long_term_->min_importance()) {
            auto lt_result = long_term_->store(entry);
            if (!lt_result.is_ok()) {
                return core::Result<std::string, HierarchyError>::err(
                    HierarchyError::LongTermMemoryError
                );
            }
        }
    }

    return core::Result<std::string, HierarchyError>::ok(entry_id);
}

LongTermMemoryResult<std::vector<MemoryEntry>> MemoryHierarchy::retrieve(
    const std::string& query,
    size_t limit,
    const std::vector<std::string>& search_tiers
) {
    std::vector<MemoryEntry> all_entries;
    std::unordered_set<std::string> seen_ids;

    // Helper to check if tier should be searched
    auto should_search = [&](const std::string& tier) {
        return std::find(search_tiers.begin(), search_tiers.end(), tier) != search_tiers.end();
    };

    // Query working memory
    if (should_search("working") && working_) {
        auto result = working_->retrieve(limit);
        if (result.is_ok()) {
            for (auto& entry : result.unwrap()) {
                if (seen_ids.insert(entry.id).second) {
                    all_entries.push_back(std::move(entry));
                }
            }
        }
    }

    // Query short-term memory
    if (should_search("short_term") && short_term_) {
        auto result = short_term_->retrieve(limit);
        if (result.is_ok()) {
            for (auto& entry : result.unwrap()) {
                if (seen_ids.insert(entry.id).second) {
                    all_entries.push_back(std::move(entry));
                }
            }
        }
    }

    // Query long-term memory
    if (should_search("long_term") && long_term_) {
        auto result = long_term_->retrieve(query, limit);
        if (result.is_ok()) {
            for (auto& entry : result.unwrap()) {
                if (seen_ids.insert(entry.id).second) {
                    all_entries.push_back(std::move(entry));
                }
            }
        }
    }

    // Sort by importance (descending), then timestamp (descending)
    std::sort(all_entries.begin(), all_entries.end(),
        [](const MemoryEntry& a, const MemoryEntry& b) {
            if (std::abs(a.importance - b.importance) > 0.001) {
                return a.importance > b.importance;
            }
            return a.timestamp > b.timestamp;
        });

    // Return top N
    if (all_entries.size() > limit) {
        all_entries.resize(limit);
    }

    return core::Result<std::vector<MemoryEntry>, LongTermMemoryError>::ok(std::move(all_entries));
}

HierarchyResult<bool> MemoryHierarchy::remove(const std::string& entry_id) {
    bool deleted_any = false;

    // Delete from working
    if (working_) {
        auto result = working_->remove(entry_id);
        if (result.is_ok() && result.unwrap()) {
            deleted_any = true;
        }
    }

    // Delete from short-term
    if (short_term_) {
        auto result = short_term_->remove(entry_id);
        if (result.is_ok() && result.unwrap()) {
            deleted_any = true;
        }
    }

    // Delete from long-term
    if (long_term_) {
        auto result = long_term_->remove(entry_id);
        if (result.is_ok() && result.unwrap()) {
            deleted_any = true;
        }
    }

    return core::Result<bool, HierarchyError>::ok(deleted_any);
}

void MemoryHierarchy::clear_working() {
    if (working_) {
        working_->clear();
    }
}

void MemoryHierarchy::clear_all() {
    if (working_) {
        working_->clear();
    }
    if (short_term_) {
        short_term_->clear();
    }
    if (long_term_) {
        long_term_->clear();
    }
}

std::map<std::string, size_t> MemoryHierarchy::get_stats() {
    std::map<std::string, size_t> stats;

    if (working_) {
        stats["working"] = working_->count();
    }
    if (short_term_) {
        stats["short_term"] = short_term_->count();
    }
    if (long_term_) {
        stats["long_term"] = long_term_->count();
    }

    return stats;
}

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
