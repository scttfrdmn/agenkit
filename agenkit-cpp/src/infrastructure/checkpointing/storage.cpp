#include "agenkit/infrastructure/checkpointing/storage.hpp"
#include <algorithm>
#include <fstream>
#include <stdexcept>

namespace agenkit {
namespace infrastructure {
namespace checkpointing {

// ============================================================================
// InMemoryCheckpointStorage Implementation
// ============================================================================

StorageResult<bool> InMemoryCheckpointStorage::save(const Checkpoint& checkpoint) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Store checkpoint
    checkpoints_[checkpoint.checkpoint_id] = checkpoint;

    // Add to session index
    auto& session_ids = session_checkpoints_[checkpoint.session_id];

    // Remove if already exists (update case)
    auto it = std::find(session_ids.begin(), session_ids.end(), checkpoint.checkpoint_id);
    if (it != session_ids.end()) {
        session_ids.erase(it);
    }

    // Add at end (will be sorted by timestamp later)
    session_ids.push_back(checkpoint.checkpoint_id);

    return core::Result<bool, StorageError>::ok(true);
}

StorageResult<std::optional<Checkpoint>> InMemoryCheckpointStorage::load(
    const std::string& checkpoint_id
) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto it = checkpoints_.find(checkpoint_id);
    if (it != checkpoints_.end()) {
        return core::Result<std::optional<Checkpoint>, StorageError>::ok(it->second);
    }

    return core::Result<std::optional<Checkpoint>, StorageError>::ok(std::nullopt);
}

StorageResult<std::vector<Checkpoint>> InMemoryCheckpointStorage::list_checkpoints(
    const std::string& session_id,
    std::optional<size_t> limit
) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto session_it = session_checkpoints_.find(session_id);
    if (session_it == session_checkpoints_.end()) {
        return core::Result<std::vector<Checkpoint>, StorageError>::ok(std::vector<Checkpoint>{});
    }

    // Collect checkpoints
    std::vector<Checkpoint> results;
    for (const auto& checkpoint_id : session_it->second) {
        auto it = checkpoints_.find(checkpoint_id);
        if (it != checkpoints_.end()) {
            results.push_back(it->second);
        }
    }

    // Sort by timestamp (most recent first)
    std::sort(results.begin(), results.end(),
        [](const Checkpoint& a, const Checkpoint& b) {
            return a.timestamp > b.timestamp;
        });

    // Apply limit
    if (limit.has_value() && results.size() > limit.value()) {
        results.resize(limit.value());
    }

    return core::Result<std::vector<Checkpoint>, StorageError>::ok(std::move(results));
}

StorageResult<std::optional<Checkpoint>> InMemoryCheckpointStorage::get_latest(
    const std::string& session_id
) {
    auto result = list_checkpoints(session_id, 1);
    if (result.is_ok()) {
        auto checkpoints = result.unwrap();
        if (!checkpoints.empty()) {
            return core::Result<std::optional<Checkpoint>, StorageError>::ok(checkpoints[0]);
        }
    }

    return core::Result<std::optional<Checkpoint>, StorageError>::ok(std::nullopt);
}

StorageResult<bool> InMemoryCheckpointStorage::del(const std::string& checkpoint_id) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto it = checkpoints_.find(checkpoint_id);
    if (it == checkpoints_.end()) {
        return core::Result<bool, StorageError>::ok(false);
    }

    std::string session_id = it->second.session_id;
    checkpoints_.erase(it);

    // Remove from session index
    auto& session_ids = session_checkpoints_[session_id];
    auto session_it = std::find(session_ids.begin(), session_ids.end(), checkpoint_id);
    if (session_it != session_ids.end()) {
        session_ids.erase(session_it);
    }

    // Clean up empty session
    if (session_ids.empty()) {
        session_checkpoints_.erase(session_id);
    }

    return core::Result<bool, StorageError>::ok(true);
}

StorageResult<size_t> InMemoryCheckpointStorage::delete_session(const std::string& session_id) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto session_it = session_checkpoints_.find(session_id);
    if (session_it == session_checkpoints_.end()) {
        return core::Result<size_t, StorageError>::ok(0);
    }

    size_t count = 0;
    for (const auto& checkpoint_id : session_it->second) {
        checkpoints_.erase(checkpoint_id);
        count++;
    }

    session_checkpoints_.erase(session_it);

    return core::Result<size_t, StorageError>::ok(count);
}

StorageResult<std::vector<Checkpoint>> InMemoryCheckpointStorage::get_checkpoint_history(
    const std::string& checkpoint_id,
    size_t max_depth
) {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<Checkpoint> history;
    std::string current_id = checkpoint_id;
    size_t depth = 0;

    while (depth < max_depth) {
        auto it = checkpoints_.find(current_id);
        if (it == checkpoints_.end()) {
            break;
        }

        history.push_back(it->second);

        // Follow parent link
        if (!it->second.parent_checkpoint_id.has_value()) {
            break;
        }

        current_id = it->second.parent_checkpoint_id.value();
        depth++;
    }

    return core::Result<std::vector<Checkpoint>, StorageError>::ok(std::move(history));
}

std::map<std::string, size_t> InMemoryCheckpointStorage::get_stats() const {
    std::lock_guard<std::mutex> lock(mutex_);

    std::map<std::string, size_t> stats;
    stats["checkpoints"] = checkpoints_.size();
    stats["sessions"] = session_checkpoints_.size();

    return stats;
}

// ============================================================================
// FileCheckpointStorage Implementation
// ============================================================================

FileCheckpointStorage::FileCheckpointStorage(const std::filesystem::path& checkpoint_dir)
    : checkpoint_dir_(checkpoint_dir) {

    // Create directory if it doesn't exist
    if (!std::filesystem::exists(checkpoint_dir_)) {
        std::filesystem::create_directories(checkpoint_dir_);
    }

    if (!std::filesystem::is_directory(checkpoint_dir_)) {
        throw std::runtime_error("Checkpoint path exists but is not a directory");
    }
}

std::filesystem::path FileCheckpointStorage::session_dir(const std::string& session_id) const {
    return checkpoint_dir_ / session_id;
}

std::filesystem::path FileCheckpointStorage::checkpoint_path(
    const std::string& session_id,
    const std::string& checkpoint_id
) const {
    return session_dir(session_id) / (checkpoint_id + ".json");
}

std::optional<std::filesystem::path> FileCheckpointStorage::find_checkpoint_file(
    const std::string& checkpoint_id
) const {
    // Search all session directories
    for (const auto& entry : std::filesystem::directory_iterator(checkpoint_dir_)) {
        if (entry.is_directory()) {
            auto path = entry.path() / (checkpoint_id + ".json");
            if (std::filesystem::exists(path)) {
                return path;
            }
        }
    }
    return std::nullopt;
}

StorageResult<bool> FileCheckpointStorage::save(const Checkpoint& checkpoint) {
    std::lock_guard<std::mutex> lock(mutex_);

    try {
        // Create session directory if needed
        auto session_path = session_dir(checkpoint.session_id);
        if (!std::filesystem::exists(session_path)) {
            std::filesystem::create_directories(session_path);
        }

        // Write checkpoint file
        auto file_path = checkpoint_path(checkpoint.session_id, checkpoint.checkpoint_id);
        std::ofstream file(file_path);
        if (!file.is_open()) {
            return core::Result<bool, StorageError>::err(StorageError::IoError);
        }

        file << checkpoint.to_json();
        file.close();

        return core::Result<bool, StorageError>::ok(true);
    } catch (const std::exception&) {
        return core::Result<bool, StorageError>::err(StorageError::IoError);
    }
}

StorageResult<std::optional<Checkpoint>> FileCheckpointStorage::load(
    const std::string& checkpoint_id
) {
    std::lock_guard<std::mutex> lock(mutex_);

    try {
        // Find checkpoint file across all sessions
        auto file_path = find_checkpoint_file(checkpoint_id);
        if (!file_path.has_value()) {
            return core::Result<std::optional<Checkpoint>, StorageError>::ok(std::nullopt);
        }

        // Read and parse
        std::ifstream file(file_path.value());
        if (!file.is_open()) {
            return core::Result<std::optional<Checkpoint>, StorageError>::err(StorageError::IoError);
        }

        std::string json_str((std::istreambuf_iterator<char>(file)),
                             std::istreambuf_iterator<char>());
        file.close();

        auto checkpoint = Checkpoint::from_json(json_str);
        return core::Result<std::optional<Checkpoint>, StorageError>::ok(checkpoint);
    } catch (const std::exception&) {
        return core::Result<std::optional<Checkpoint>, StorageError>::err(
            StorageError::SerializationError
        );
    }
}

StorageResult<std::vector<Checkpoint>> FileCheckpointStorage::list_checkpoints(
    const std::string& session_id,
    std::optional<size_t> limit
) {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<Checkpoint> results;

    try {
        auto session_path = session_dir(session_id);
        if (!std::filesystem::exists(session_path)) {
            return core::Result<std::vector<Checkpoint>, StorageError>::ok(results);
        }

        // Read all checkpoint files in session directory
        for (const auto& entry : std::filesystem::directory_iterator(session_path)) {
            if (entry.path().extension() == ".json") {
                std::ifstream file(entry.path());
                if (file.is_open()) {
                    std::string json_str((std::istreambuf_iterator<char>(file)),
                                         std::istreambuf_iterator<char>());
                    file.close();

                    try {
                        auto checkpoint = Checkpoint::from_json(json_str);
                        results.push_back(checkpoint);
                    } catch (...) {
                        // Skip malformed checkpoints
                    }
                }
            }
        }

        // Sort by timestamp (most recent first)
        std::sort(results.begin(), results.end(),
            [](const Checkpoint& a, const Checkpoint& b) {
                return a.timestamp > b.timestamp;
            });

        // Apply limit
        if (limit.has_value() && results.size() > limit.value()) {
            results.resize(limit.value());
        }

        return core::Result<std::vector<Checkpoint>, StorageError>::ok(std::move(results));
    } catch (const std::exception&) {
        return core::Result<std::vector<Checkpoint>, StorageError>::err(StorageError::IoError);
    }
}

StorageResult<std::optional<Checkpoint>> FileCheckpointStorage::get_latest(
    const std::string& session_id
) {
    auto result = list_checkpoints(session_id, 1);
    if (result.is_ok()) {
        auto checkpoints = result.unwrap();
        if (!checkpoints.empty()) {
            return core::Result<std::optional<Checkpoint>, StorageError>::ok(checkpoints[0]);
        }
    }

    return core::Result<std::optional<Checkpoint>, StorageError>::ok(std::nullopt);
}

StorageResult<bool> FileCheckpointStorage::del(const std::string& checkpoint_id) {
    std::lock_guard<std::mutex> lock(mutex_);

    try {
        auto file_path = find_checkpoint_file(checkpoint_id);
        if (!file_path.has_value()) {
            return core::Result<bool, StorageError>::ok(false);
        }

        std::filesystem::remove(file_path.value());
        return core::Result<bool, StorageError>::ok(true);
    } catch (const std::exception&) {
        return core::Result<bool, StorageError>::err(StorageError::IoError);
    }
}

StorageResult<size_t> FileCheckpointStorage::delete_session(const std::string& session_id) {
    std::lock_guard<std::mutex> lock(mutex_);

    try {
        auto session_path = session_dir(session_id);
        if (!std::filesystem::exists(session_path)) {
            return core::Result<size_t, StorageError>::ok(0);
        }

        size_t count = 0;
        for (const auto& entry : std::filesystem::directory_iterator(session_path)) {
            if (entry.path().extension() == ".json") {
                std::filesystem::remove(entry.path());
                count++;
            }
        }

        // Remove directory if empty
        if (std::filesystem::is_empty(session_path)) {
            std::filesystem::remove(session_path);
        }

        return core::Result<size_t, StorageError>::ok(count);
    } catch (const std::exception&) {
        return core::Result<size_t, StorageError>::err(StorageError::IoError);
    }
}

StorageResult<std::vector<Checkpoint>> FileCheckpointStorage::get_checkpoint_history(
    const std::string& checkpoint_id,
    size_t max_depth
) {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<Checkpoint> history;
    std::string current_id = checkpoint_id;
    size_t depth = 0;

    while (depth < max_depth) {
        auto result = load(current_id);
        if (!result.is_ok() || !result.unwrap().has_value()) {
            break;
        }

        auto checkpoint = result.unwrap().value();
        history.push_back(checkpoint);

        // Follow parent link
        if (!checkpoint.parent_checkpoint_id.has_value()) {
            break;
        }

        current_id = checkpoint.parent_checkpoint_id.value();
        depth++;
    }

    return core::Result<std::vector<Checkpoint>, StorageError>::ok(std::move(history));
}

StorageResult<std::map<std::string, size_t>> FileCheckpointStorage::get_stats() const {
    std::lock_guard<std::mutex> lock(mutex_);

    std::map<std::string, size_t> stats;
    size_t checkpoint_count = 0;
    size_t session_count = 0;

    try {
        for (const auto& entry : std::filesystem::directory_iterator(checkpoint_dir_)) {
            if (entry.is_directory()) {
                session_count++;
                for (const auto& file : std::filesystem::directory_iterator(entry.path())) {
                    if (file.path().extension() == ".json") {
                        checkpoint_count++;
                    }
                }
            }
        }

        stats["checkpoints"] = checkpoint_count;
        stats["sessions"] = session_count;

        return core::Result<std::map<std::string, size_t>, StorageError>::ok(stats);
    } catch (const std::exception&) {
        return core::Result<std::map<std::string, size_t>, StorageError>::err(
            StorageError::IoError
        );
    }
}

} // namespace checkpointing
} // namespace infrastructure
} // namespace agenkit
