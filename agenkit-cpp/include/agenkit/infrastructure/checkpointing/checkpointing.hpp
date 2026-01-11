#pragma once

/// @file checkpointing.hpp
/// @brief Checkpointing system for durable agent execution
///
/// The checkpointing system provides:
///
/// 1. **Durable Execution** - Resume after crashes/restarts
/// 2. **Time-Travel Debugging** - Replay from any checkpoint
/// 3. **State Persistence** - Save/load complete agent state
/// 4. **History Tracking** - Parent links form checkpoint chain
///
/// # Architecture
///
/// The system has three layers:
///
/// - **Checkpoint**: Core data structure (state + messages + metadata)
/// - **Storage**: Pluggable backends (InMemory, File, Database)
/// - **Manager**: High-level orchestration (auto-parent, pruning, replay)
///
/// # Basic Usage
///
/// ```cpp
/// #include <agenkit/infrastructure/checkpointing/checkpointing.hpp>
///
/// // 1. Create storage backend
/// auto storage = std::make_unique<InMemoryCheckpointStorage>();
///
/// // 2. Create manager
/// auto config = CheckpointConfig::with_max_checkpoints(10);
/// auto manager = std::make_unique<CheckpointManager>(std::move(storage), config);
///
/// // 3. Create checkpoint
/// auto checkpoint_id = manager->create_checkpoint(
///     "session-123",
///     "my-agent",
///     1,
///     state_json,
///     messages
/// ).unwrap();
///
/// // 4. Load checkpoint later
/// auto checkpoint = manager->load_checkpoint(checkpoint_id).unwrap();
/// ```
///
/// # Durable Agent Wrapper
///
/// For automatic checkpointing after each step:
///
/// ```cpp
/// auto agent = std::make_unique<MyAgent>();
/// auto durable = DurableAgent<MyAgent>(
///     std::move(agent),
///     std::make_shared<CheckpointManager>(storage, config),
///     "session-123"
/// );
///
/// // Automatically checkpoints after run()
/// auto result = durable.run(input);
///
/// // Restore from crash
/// durable.restore_latest();
/// ```
///
/// # Storage Backends
///
/// ## InMemoryCheckpointStorage
///
/// Fast, thread-safe in-memory storage. Good for testing and short-lived sessions.
///
/// ```cpp
/// auto storage = std::make_unique<InMemoryCheckpointStorage>();
/// ```
///
/// ## FileCheckpointStorage
///
/// Persistent file-based storage. Organizes checkpoints as:
///
/// ```
/// checkpoints/
///   session-1/
///     checkpoint-uuid-1.json
///     checkpoint-uuid-2.json
/// ```
///
/// ```cpp
/// auto storage = std::make_unique<FileCheckpointStorage>("./checkpoints");
/// ```
///
/// # Configuration
///
/// ```cpp
/// CheckpointConfig config;
/// config.max_checkpoints_per_session = 10;  // Keep last 10 checkpoints
/// config.auto_parent_linking = true;        // Automatic history chain
/// config.enable_pruning = true;             // Auto-prune old checkpoints
/// ```
///
/// # Time-Travel Debugging
///
/// ```cpp
/// // Get checkpoint history
/// auto history = manager->get_history(checkpoint_id, 100).unwrap();
///
/// // Replay from specific point (oldest to newest)
/// auto replay = manager->replay_from_checkpoint(checkpoint_id).unwrap();
/// for (const auto& cp : replay) {
///     std::cout << "Step " << cp.step_number << ": " << cp.checkpoint_id << "\n";
/// }
/// ```
///
/// # Thread Safety
///
/// All storage implementations are thread-safe using std::mutex.
/// Multiple threads can safely:
/// - Create checkpoints concurrently
/// - Load checkpoints concurrently
/// - Mix reads and writes
///
/// # Error Handling
///
/// All operations return Result<T, Error> for explicit error handling:
///
/// ```cpp
/// auto result = manager->create_checkpoint(...);
/// if (result.is_ok()) {
///     std::string checkpoint_id = result.unwrap();
/// } else {
///     ManagerError err = result.unwrap_err();
///     // Handle error
/// }
/// ```
///
/// # Performance Characteristics
///
/// | Operation           | InMemory | File      |
/// |---------------------|----------|-----------|
/// | Save                | O(1)     | O(size)   |
/// | Load by ID          | O(1)     | O(sessions) |
/// | List session        | O(n)     | O(n)      |
/// | History traversal   | O(depth) | O(depth)  |
///
/// Where:
/// - n = checkpoints in session
/// - depth = parent chain length
/// - size = serialized checkpoint size
///
/// # Best Practices
///
/// 1. **Choose storage based on durability needs**:
///    - Testing: InMemory
///    - Production: File or Database
///
/// 2. **Set max_checkpoints_per_session** to prevent unbounded growth
///
/// 3. **Include cost metadata** in checkpoints for budget tracking:
/// ```cpp
/// nlohmann::json metadata;
/// metadata["tokens"] = 1500;
/// metadata["cost"] = 0.03;
/// manager->create_checkpoint(..., metadata);
/// ```
///
/// 4. **Use DurableAgent wrapper** for automatic checkpointing
///
/// 5. **Enable parent linking** for time-travel debugging
///
/// # Integration with Other Infrastructure
///
/// Checkpointing integrates with:
///
/// - **Memory Systems**: Checkpoint memory state alongside agent state
/// - **Budget Tracking**: Store cost metadata in checkpoints
/// - **Observability**: Log checkpoint creation in traces
/// - **Middleware**: Checkpoint before/after retry attempts

#include "agenkit/infrastructure/checkpointing/checkpoint.hpp"
#include "agenkit/infrastructure/checkpointing/storage.hpp"
#include "agenkit/infrastructure/checkpointing/manager.hpp"
#include "agenkit/infrastructure/checkpointing/durable_agent.hpp"
