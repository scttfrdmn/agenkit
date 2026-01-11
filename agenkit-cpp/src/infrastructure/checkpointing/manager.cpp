#include "agenkit/infrastructure/checkpointing/manager.hpp"
#include <algorithm>

namespace agenkit {
namespace infrastructure {
namespace checkpointing {

CheckpointManager::CheckpointManager(
    std::unique_ptr<CheckpointStorage> storage,
    CheckpointConfig config
) : storage_(std::move(storage)), config_(config) {
}

ManagerResult<std::string> CheckpointManager::create_checkpoint(
    const std::string& session_id,
    const std::string& agent_name,
    size_t step_number,
    const nlohmann::json& state,
    const std::vector<core::Message>& messages,
    const std::optional<nlohmann::json>& metadata
) {
    // Create checkpoint
    auto checkpoint = Checkpoint::create(
        session_id,
        agent_name,
        step_number,
        state,
        messages
    );

    // Add metadata if provided
    if (metadata.has_value()) {
        checkpoint.with_metadata(metadata.value());
    }

    // Auto-link to parent if enabled
    if (config_.auto_parent_linking) {
        auto latest_result = storage_->get_latest(session_id);
        if (latest_result.is_ok()) {
            auto latest = latest_result.unwrap();
            if (latest.has_value()) {
                checkpoint.with_parent(latest.value().checkpoint_id);
            }
        }
    }

    // Save checkpoint
    auto save_result = storage_->save(checkpoint);
    if (!save_result.is_ok()) {
        return core::Result<std::string, ManagerError>::err(ManagerError::StorageError);
    }

    // Auto-prune if enabled
    if (config_.enable_pruning && config_.max_checkpoints_per_session > 0) {
        auto_prune_if_needed(session_id);
    }

    return core::Result<std::string, ManagerError>::ok(checkpoint.checkpoint_id);
}

ManagerResult<std::optional<Checkpoint>> CheckpointManager::load_checkpoint(
    const std::string& checkpoint_id
) {
    auto result = storage_->load(checkpoint_id);
    if (!result.is_ok()) {
        return core::Result<std::optional<Checkpoint>, ManagerError>::err(
            ManagerError::StorageError
        );
    }

    return core::Result<std::optional<Checkpoint>, ManagerError>::ok(result.unwrap());
}

ManagerResult<std::optional<Checkpoint>> CheckpointManager::get_latest_checkpoint(
    const std::string& session_id
) {
    auto result = storage_->get_latest(session_id);
    if (!result.is_ok()) {
        return core::Result<std::optional<Checkpoint>, ManagerError>::err(
            ManagerError::StorageError
        );
    }

    return core::Result<std::optional<Checkpoint>, ManagerError>::ok(result.unwrap());
}

ManagerResult<std::vector<Checkpoint>> CheckpointManager::list_session_checkpoints(
    const std::string& session_id,
    std::optional<size_t> limit
) {
    auto result = storage_->list_checkpoints(session_id, limit);
    if (!result.is_ok()) {
        return core::Result<std::vector<Checkpoint>, ManagerError>::err(
            ManagerError::StorageError
        );
    }

    return core::Result<std::vector<Checkpoint>, ManagerError>::ok(result.unwrap());
}

ManagerResult<bool> CheckpointManager::delete_checkpoint(const std::string& checkpoint_id) {
    auto result = storage_->remove(checkpoint_id);
    if (!result.is_ok()) {
        return core::Result<bool, ManagerError>::err(ManagerError::StorageError);
    }

    return core::Result<bool, ManagerError>::ok(result.unwrap());
}

ManagerResult<size_t> CheckpointManager::delete_session(const std::string& session_id) {
    auto result = storage_->delete_session(session_id);
    if (!result.is_ok()) {
        return core::Result<size_t, ManagerError>::err(ManagerError::StorageError);
    }

    return core::Result<size_t, ManagerError>::ok(result.unwrap());
}

ManagerResult<std::vector<Checkpoint>> CheckpointManager::get_history(
    const std::string& checkpoint_id,
    size_t max_depth
) {
    auto result = storage_->get_checkpoint_history(checkpoint_id, max_depth);
    if (!result.is_ok()) {
        return core::Result<std::vector<Checkpoint>, ManagerError>::err(
            ManagerError::StorageError
        );
    }

    return core::Result<std::vector<Checkpoint>, ManagerError>::ok(result.unwrap());
}

ManagerResult<std::vector<Checkpoint>> CheckpointManager::replay_from_checkpoint(
    const std::string& checkpoint_id
) {
    // Get full history
    auto history_result = get_history(checkpoint_id);
    if (!history_result.is_ok()) {
        return history_result;
    }

    auto history = history_result.unwrap();
    if (history.empty()) {
        return core::Result<std::vector<Checkpoint>, ManagerError>::err(
            ManagerError::CheckpointNotFound
        );
    }

    // History is already newest-to-oldest from get_history
    // For replay, we want oldest-to-newest (chronological order)
    std::reverse(history.begin(), history.end());

    return core::Result<std::vector<Checkpoint>, ManagerError>::ok(std::move(history));
}

ManagerResult<size_t> CheckpointManager::prune_session(
    const std::string& session_id,
    size_t keep_count
) {
    // Get all checkpoints for session
    auto list_result = storage_->list_checkpoints(session_id, std::nullopt);
    if (!list_result.is_ok()) {
        return core::Result<size_t, ManagerError>::err(ManagerError::StorageError);
    }

    auto checkpoints = list_result.unwrap();
    if (checkpoints.size() <= keep_count) {
        return core::Result<size_t, ManagerError>::ok(0);
    }

    // Already sorted by timestamp (most recent first)
    // Delete everything after keep_count
    size_t pruned = 0;
    for (size_t i = keep_count; i < checkpoints.size(); i++) {
        auto delete_result = storage_->remove(checkpoints[i].checkpoint_id);
        if (delete_result.is_ok() && delete_result.unwrap()) {
            pruned++;
        }
    }

    return core::Result<size_t, ManagerError>::ok(pruned);
}

ManagerResult<std::map<std::string, size_t>> CheckpointManager::get_stats() {
    // Try to get stats from storage (InMemoryCheckpointStorage has this)
    // For FileCheckpointStorage, it returns Result so we need to handle it

    // Since CheckpointStorage interface doesn't declare get_stats(),
    // we'll need to handle this differently. Let's provide basic stats
    // by querying the storage.

    std::map<std::string, size_t> stats;

    // For now, we can try to cast to known implementations
    // This is not ideal but works for basic stats

    auto* in_memory = dynamic_cast<InMemoryCheckpointStorage*>(storage_.get());
    if (in_memory) {
        stats = in_memory->get_stats();
        return core::Result<std::map<std::string, size_t>, ManagerError>::ok(stats);
    }

    auto* file_storage = dynamic_cast<FileCheckpointStorage*>(storage_.get());
    if (file_storage) {
        auto result = file_storage->get_stats();
        if (result.is_ok()) {
            stats = result.unwrap();
            return core::Result<std::map<std::string, size_t>, ManagerError>::ok(stats);
        } else {
            return core::Result<std::map<std::string, size_t>, ManagerError>::err(
                ManagerError::StorageError
            );
        }
    }

    // Unknown storage type
    stats["checkpoints"] = 0;
    stats["sessions"] = 0;
    return core::Result<std::map<std::string, size_t>, ManagerError>::ok(stats);
}

void CheckpointManager::auto_prune_if_needed(const std::string& session_id) {
    if (config_.max_checkpoints_per_session == 0) {
        return;
    }

    auto list_result = storage_->list_checkpoints(session_id, std::nullopt);
    if (!list_result.is_ok()) {
        return;
    }

    auto checkpoints = list_result.unwrap();
    if (checkpoints.size() > config_.max_checkpoints_per_session) {
        // Prune excess checkpoints
        prune_session(session_id, config_.max_checkpoints_per_session);
    }
}

} // namespace checkpointing
} // namespace infrastructure
} // namespace agenkit
