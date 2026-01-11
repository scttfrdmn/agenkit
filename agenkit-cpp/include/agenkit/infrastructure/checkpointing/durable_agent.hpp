#pragma once

#include "agenkit/infrastructure/checkpointing/manager.hpp"
#include "agenkit/core/result.hpp"
#include <memory>
#include <optional>
#include <string>
#include <utility>

namespace agenkit {
namespace infrastructure {
namespace checkpointing {

/// Durable agent wrapper - Adds auto-checkpointing to any agent
///
/// Usage:
/// ```cpp
/// auto manager = std::make_shared<CheckpointManager>(storage, config);
/// auto agent = std::make_unique<MyAgent>();
/// auto durable = DurableAgent<MyAgent>(
///     std::move(agent),
///     manager,
///     "session-123"
/// );
///
/// // Automatically checkpoints after each step
/// auto result = durable.run(input);
/// ```
///
/// Template parameter TAgent must have:
/// - run() method that returns Result<Response, Error>
/// - get_state() method that returns nlohmann::json
/// - set_state(json) method to restore state
/// - get_messages() method that returns vector<Message>
///
template<typename TAgent>
class DurableAgent {
public:
    /// Create durable agent wrapper
    ///
    /// @param agent Agent to wrap (takes ownership)
    /// @param manager Checkpoint manager
    /// @param session_id Session identifier
    /// @param auto_checkpoint Enable automatic checkpointing after each step
    DurableAgent(
        std::unique_ptr<TAgent> agent,
        std::shared_ptr<CheckpointManager> manager,
        const std::string& session_id,
        bool auto_checkpoint = true
    ) : agent_(std::move(agent)),
        manager_(manager),
        session_id_(session_id),
        auto_checkpoint_(auto_checkpoint),
        step_number_(0) {
    }

    /// Get underlying agent (const)
    const TAgent& agent() const { return *agent_; }

    /// Get underlying agent (mutable)
    TAgent& agent() { return *agent_; }

    /// Get current session ID
    const std::string& session_id() const { return session_id_; }

    /// Get current step number
    size_t step_number() const { return step_number_; }

    /// Create a checkpoint of current state
    ///
    /// @param metadata Optional metadata
    /// @return Checkpoint ID or error
    ManagerResult<std::string> checkpoint(
        const std::optional<nlohmann::json>& metadata = std::nullopt
    ) {
        auto state = agent_->get_state();
        auto messages = agent_->get_messages();

        return manager_->create_checkpoint(
            session_id_,
            agent_->name(),
            step_number_,
            state,
            messages,
            metadata
        );
    }

    /// Restore from a checkpoint
    ///
    /// @param checkpoint_id Checkpoint ID to restore from
    /// @return Ok(void) or Err
    ManagerResult<bool> restore(const std::string& checkpoint_id) {
        auto load_result = manager_->load_checkpoint(checkpoint_id);
        if (!load_result.is_ok()) {
            return core::Result<bool, ManagerError>::err(load_result.unwrap_err());
        }

        auto checkpoint_opt = load_result.unwrap();
        if (!checkpoint_opt.has_value()) {
            return core::Result<bool, ManagerError>::err(ManagerError::CheckpointNotFound);
        }

        auto checkpoint = checkpoint_opt.value();

        // Restore agent state
        agent_->set_state(checkpoint.state);
        agent_->set_messages(checkpoint.messages);

        // Update step number
        step_number_ = checkpoint.step_number;

        return core::Result<bool, ManagerError>::ok(true);
    }

    /// Restore from latest checkpoint in session
    ///
    /// @return Ok(true) if restored, Ok(false) if no checkpoints exist
    ManagerResult<bool> restore_latest() {
        auto latest_result = manager_->get_latest_checkpoint(session_id_);
        if (!latest_result.is_ok()) {
            return core::Result<bool, ManagerError>::err(latest_result.unwrap_err());
        }

        auto checkpoint_opt = latest_result.unwrap();
        if (!checkpoint_opt.has_value()) {
            return core::Result<bool, ManagerError>::ok(false);
        }

        return restore(checkpoint_opt.value().checkpoint_id);
    }

    /// Execute agent step with optional auto-checkpointing
    ///
    /// @param input Input to agent
    /// @return Agent response or error
    template<typename TInput>
    auto run(const TInput& input) -> decltype(std::declval<TAgent>().run(std::declval<TInput>())) {
        // Execute agent step
        auto result = agent_->run(input);

        // Increment step number
        step_number_++;

        // Auto-checkpoint if enabled and step succeeded
        if (auto_checkpoint_ && result.is_ok()) {
            checkpoint();
        }

        return result;
    }

    /// Get checkpoint history for this session
    ///
    /// @return Vector of checkpoints (newest to oldest)
    ManagerResult<std::vector<Checkpoint>> get_history() {
        if (last_checkpoint_id_.empty()) {
            // No checkpoints yet, list session checkpoints
            return manager_->list_session_checkpoints(session_id_);
        }

        return manager_->get_history(last_checkpoint_id_);
    }

    /// Replay from a specific checkpoint
    ///
    /// Returns history in chronological order (oldest to newest)
    ///
    /// @param checkpoint_id Checkpoint to replay from
    /// @return Vector of checkpoints for replay
    ManagerResult<std::vector<Checkpoint>> replay_from(const std::string& checkpoint_id) {
        return manager_->replay_from_checkpoint(checkpoint_id);
    }

private:
    std::unique_ptr<TAgent> agent_;
    std::shared_ptr<CheckpointManager> manager_;
    std::string session_id_;
    bool auto_checkpoint_;
    size_t step_number_;
    std::string last_checkpoint_id_;
};

} // namespace checkpointing
} // namespace infrastructure
} // namespace agenkit
