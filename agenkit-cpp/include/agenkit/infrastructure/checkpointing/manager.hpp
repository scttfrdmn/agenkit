#pragma once

#include "agenkit/infrastructure/checkpointing/checkpoint.hpp"
#include "agenkit/infrastructure/checkpointing/storage.hpp"
#include "agenkit/core/result.hpp"
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace agenkit {
namespace infrastructure {
namespace checkpointing {

/// Manager error types
enum class ManagerError {
    StorageError,
    CheckpointNotFound,
    InvalidSession,
    Other,
};

/// Result type for manager operations
template<typename T>
using ManagerResult = core::Result<T, ManagerError>;

/// Checkpoint manager configuration
struct CheckpointConfig {
    /// Maximum checkpoints per session (0 = unlimited)
    size_t max_checkpoints_per_session = 0;

    /// Whether to automatically link parent checkpoints
    bool auto_parent_linking = true;

    /// Whether to enable pruning of old checkpoints
    bool enable_pruning = true;

    /// Create default configuration
    static CheckpointConfig default_config() {
        return CheckpointConfig{};
    }

    /// Create configuration with specified max checkpoints
    static CheckpointConfig with_max_checkpoints(size_t max) {
        CheckpointConfig config;
        config.max_checkpoints_per_session = max;
        return config;
    }
};

/// Checkpoint manager - High-level orchestration
///
/// Provides:
/// - Session state tracking
/// - Automatic parent linking
/// - Checkpoint pruning
/// - Replay/time-travel support
///
/// Thread-safe through underlying storage.
class CheckpointManager {
public:
    /// Create manager with specified storage and config
    ///
    /// @param storage Checkpoint storage backend
    /// @param config Manager configuration
    CheckpointManager(
        std::unique_ptr<CheckpointStorage> storage,
        CheckpointConfig config = CheckpointConfig::default_config()
    );

    /// Create a checkpoint for a session
    ///
    /// Automatically:
    /// - Generates UUID
    /// - Links to previous checkpoint if auto_parent_linking enabled
    /// - Prunes old checkpoints if needed
    ///
    /// @param session_id Session identifier
    /// @param agent_name Agent name
    /// @param step_number Step number
    /// @param state Agent state (JSON)
    /// @param messages Conversation history
    /// @param metadata Optional metadata
    /// @return Checkpoint ID or error
    ManagerResult<std::string> create_checkpoint(
        const std::string& session_id,
        const std::string& agent_name,
        size_t step_number,
        const nlohmann::json& state,
        const std::vector<core::Message>& messages,
        const std::optional<nlohmann::json>& metadata = std::nullopt
    );

    /// Load a checkpoint by ID
    ///
    /// @param checkpoint_id Checkpoint ID
    /// @return Checkpoint or None if not found
    ManagerResult<std::optional<Checkpoint>> load_checkpoint(
        const std::string& checkpoint_id
    );

    /// Get latest checkpoint for a session
    ///
    /// @param session_id Session ID
    /// @return Latest checkpoint or None if session has no checkpoints
    ManagerResult<std::optional<Checkpoint>> get_latest_checkpoint(
        const std::string& session_id
    );

    /// List checkpoints for a session
    ///
    /// @param session_id Session ID
    /// @param limit Optional limit (nullopt = all)
    /// @return Vector of checkpoints (most recent first)
    ManagerResult<std::vector<Checkpoint>> list_session_checkpoints(
        const std::string& session_id,
        std::optional<size_t> limit = std::nullopt
    );

    /// Delete a checkpoint
    ///
    /// @param checkpoint_id Checkpoint ID
    /// @return true if deleted, false if not found
    ManagerResult<bool> delete_checkpoint(const std::string& checkpoint_id);

    /// Delete all checkpoints for a session
    ///
    /// @param session_id Session ID
    /// @return Number of checkpoints deleted
    ManagerResult<size_t> delete_session(const std::string& session_id);

    /// Get checkpoint history (follow parent links)
    ///
    /// @param checkpoint_id Starting checkpoint ID
    /// @param max_depth Maximum depth to traverse
    /// @return Vector of checkpoints (newest to oldest)
    ManagerResult<std::vector<Checkpoint>> get_history(
        const std::string& checkpoint_id,
        size_t max_depth = 100
    );

    /// Replay from a checkpoint
    ///
    /// Returns the checkpoint and all its history for time-travel debugging.
    ///
    /// @param checkpoint_id Checkpoint to replay from
    /// @return Checkpoint and its history
    ManagerResult<std::vector<Checkpoint>> replay_from_checkpoint(
        const std::string& checkpoint_id
    );

    /// Prune old checkpoints for a session
    ///
    /// Keeps the N most recent checkpoints, deletes older ones.
    ///
    /// @param session_id Session ID
    /// @param keep_count Number of checkpoints to keep
    /// @return Number of checkpoints pruned
    ManagerResult<size_t> prune_session(
        const std::string& session_id,
        size_t keep_count
    );

    /// Get statistics across all sessions
    ///
    /// @return Map with checkpoint counts by category
    ManagerResult<std::map<std::string, size_t>> get_stats();

    /// Get current configuration
    const CheckpointConfig& config() const { return config_; }

private:
    std::unique_ptr<CheckpointStorage> storage_;
    CheckpointConfig config_;

    /// Prune session if needed based on max_checkpoints_per_session
    void auto_prune_if_needed(const std::string& session_id);
};

} // namespace checkpointing
} // namespace infrastructure
} // namespace agenkit
