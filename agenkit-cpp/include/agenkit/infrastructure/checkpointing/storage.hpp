#pragma once

#include "agenkit/infrastructure/checkpointing/checkpoint.hpp"
#include "agenkit/core/result.hpp"
#include <filesystem>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace agenkit {
namespace infrastructure {
namespace checkpointing {

/// Storage error types
enum class StorageError {
    NotFound,
    IoError,
    SerializationError,
    Other,
};

/// Result type for storage operations
template<typename T>
using StorageResult = core::Result<T, StorageError>;

/// Abstract checkpoint storage interface
///
/// Implementations must be thread-safe.
class CheckpointStorage {
public:
    virtual ~CheckpointStorage() = default;

    /// Save a checkpoint
    ///
    /// @param checkpoint Checkpoint to save
    /// @return Ok(void) or Err(StorageError)
    virtual StorageResult<bool> save(const Checkpoint& checkpoint) = 0;

    /// Load a checkpoint by ID
    ///
    /// @param checkpoint_id Checkpoint ID
    /// @return Ok(Some(Checkpoint)) or Ok(None) if not found
    virtual StorageResult<std::optional<Checkpoint>> load(
        const std::string& checkpoint_id
    ) = 0;

    /// List checkpoints for a session
    ///
    /// @param session_id Session ID
    /// @param limit Optional limit (nullopt = all)
    /// @return Vector of checkpoints (most recent first)
    virtual StorageResult<std::vector<Checkpoint>> list_checkpoints(
        const std::string& session_id,
        std::optional<size_t> limit = std::nullopt
    ) = 0;

    /// Get latest checkpoint for a session
    ///
    /// @param session_id Session ID
    /// @return Ok(Some(Checkpoint)) or Ok(None) if no checkpoints exist
    virtual StorageResult<std::optional<Checkpoint>> get_latest(
        const std::string& session_id
    ) = 0;

    /// Delete a checkpoint
    ///
    /// @param checkpoint_id Checkpoint ID
    /// @return true if deleted, false if not found
    virtual StorageResult<bool> remove(const std::string& checkpoint_id) = 0;

    /// Delete all checkpoints for a session
    ///
    /// @param session_id Session ID
    /// @return Number of checkpoints deleted
    virtual StorageResult<size_t> delete_session(const std::string& session_id) = 0;

    /// Get checkpoint history (follow parent links backward)
    ///
    /// @param checkpoint_id Starting checkpoint ID
    /// @param max_depth Maximum depth to traverse
    /// @return Vector of checkpoints (newest to oldest)
    virtual StorageResult<std::vector<Checkpoint>> get_checkpoint_history(
        const std::string& checkpoint_id,
        size_t max_depth = 100
    ) = 0;
};

/// In-memory checkpoint storage (for testing)
///
/// Thread-safe implementation using std::mutex.
class InMemoryCheckpointStorage : public CheckpointStorage {
public:
    InMemoryCheckpointStorage() = default;

    StorageResult<bool> save(const Checkpoint& checkpoint) override;

    StorageResult<std::optional<Checkpoint>> load(
        const std::string& checkpoint_id
    ) override;

    StorageResult<std::vector<Checkpoint>> list_checkpoints(
        const std::string& session_id,
        std::optional<size_t> limit = std::nullopt
    ) override;

    StorageResult<std::optional<Checkpoint>> get_latest(
        const std::string& session_id
    ) override;

    StorageResult<bool> remove(const std::string& checkpoint_id) override;

    StorageResult<size_t> delete_session(const std::string& session_id) override;

    StorageResult<std::vector<Checkpoint>> get_checkpoint_history(
        const std::string& checkpoint_id,
        size_t max_depth = 100
    ) override;

    /// Get storage statistics
    ///
    /// @return Map with "checkpoints" and "sessions" counts
    std::map<std::string, size_t> get_stats() const;

private:
    mutable std::mutex mutex_;
    std::map<std::string, Checkpoint> checkpoints_;  // checkpoint_id -> Checkpoint
    std::map<std::string, std::vector<std::string>> session_checkpoints_;  // session_id -> [checkpoint_ids]
};

/// File-based checkpoint storage
///
/// Organizes checkpoints as:
/// checkpoints/
///   session-1/
///     checkpoint-uuid-1.json
///     checkpoint-uuid-2.json
///   session-2/
///     checkpoint-uuid-3.json
///
/// Thread-safe implementation using std::mutex.
class FileCheckpointStorage : public CheckpointStorage {
public:
    /// Create file storage with specified directory
    ///
    /// Creates directory if it doesn't exist.
    ///
    /// @param checkpoint_dir Directory for checkpoints
    /// @throws std::runtime_error if directory creation fails
    explicit FileCheckpointStorage(const std::filesystem::path& checkpoint_dir);

    StorageResult<bool> save(const Checkpoint& checkpoint) override;

    StorageResult<std::optional<Checkpoint>> load(
        const std::string& checkpoint_id
    ) override;

    StorageResult<std::vector<Checkpoint>> list_checkpoints(
        const std::string& session_id,
        std::optional<size_t> limit = std::nullopt
    ) override;

    StorageResult<std::optional<Checkpoint>> get_latest(
        const std::string& session_id
    ) override;

    StorageResult<bool> remove(const std::string& checkpoint_id) override;

    StorageResult<size_t> delete_session(const std::string& session_id) override;

    StorageResult<std::vector<Checkpoint>> get_checkpoint_history(
        const std::string& checkpoint_id,
        size_t max_depth = 100
    ) override;

    /// Get storage statistics
    ///
    /// @return Map with "checkpoints" and "sessions" counts
    StorageResult<std::map<std::string, size_t>> get_stats() const;

private:
    std::filesystem::path checkpoint_dir_;
    mutable std::mutex mutex_;

    /// Get session directory path
    std::filesystem::path session_dir(const std::string& session_id) const;

    /// Get checkpoint file path
    std::filesystem::path checkpoint_path(
        const std::string& session_id,
        const std::string& checkpoint_id
    ) const;

    /// Find checkpoint file across all sessions
    std::optional<std::filesystem::path> find_checkpoint_file(
        const std::string& checkpoint_id
    ) const;
};

} // namespace checkpointing
} // namespace infrastructure
} // namespace agenkit
