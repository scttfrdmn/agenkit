/**
 * @file basic_checkpointing.cpp
 * @brief Demonstrates checkpointing system for durable agent execution
 *
 * This example shows:
 * 1. Creating checkpoints with InMemory and File storage
 * 2. Loading and restoring from checkpoints
 * 3. Time-travel debugging with checkpoint history
 * 4. Automatic pruning of old checkpoints
 * 5. DurableAgent wrapper for auto-checkpointing
 */

#include <agenkit/infrastructure/checkpointing/checkpointing.hpp>
#include <agenkit/core/message.hpp>
#include <iostream>
#include <memory>

using namespace agenkit::infrastructure::checkpointing;
using namespace agenkit::core;

/// Simple agent for demonstration
class SimpleAgent {
public:
    SimpleAgent(std::string name) : name_(name), counter_(0) {}

    std::string name() const { return name_; }

    nlohmann::json get_state() const {
        nlohmann::json state;
        state["counter"] = counter_;
        state["name"] = name_;
        return state;
    }

    void set_state(const nlohmann::json& state) {
        counter_ = state["counter"].get<int>();
        name_ = state["name"].get<std::string>();
    }

    std::vector<Message> get_messages() const {
        return messages_;
    }

    void set_messages(const std::vector<Message>& messages) {
        messages_ = messages;
    }

    struct Response {
        std::string text;
        bool success;
    };

    agenkit::core::Result<Response, std::string> run(const std::string& input) {
        counter_++;
        messages_.push_back(Message::with_text("user", input));

        std::string response = "Processed: " + input + " (count=" + std::to_string(counter_) + ")";
        messages_.push_back(Message::with_text("assistant", response));

        return agenkit::core::Result<Response, std::string>::ok(Response{response, true});
    }

private:
    std::string name_;
    int counter_;
    std::vector<Message> messages_;
};

void example_basic_checkpointing() {
    std::cout << "\n=== Basic Checkpointing Example ===\n\n";

    // 1. Create InMemory storage
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    auto config = CheckpointConfig::with_max_checkpoints(5);
    auto manager = std::make_unique<CheckpointManager>(std::move(storage), config);

    // 2. Create checkpoints
    std::vector<Message> messages;
    messages.push_back(Message::with_text("user", "Hello"));
    messages.push_back(Message::with_text("assistant", "Hi there!"));

    nlohmann::json state;
    state["counter"] = 1;
    state["name"] = "demo-agent";

    std::cout << "Creating checkpoint 1...\n";
    auto result1 = manager->create_checkpoint(
        "session-123",
        "demo-agent",
        1,
        state,
        messages
    );

    if (result1.is_ok()) {
        std::cout << "✓ Checkpoint created: " << result1.unwrap() << "\n";
    }

    // 3. Create second checkpoint (will auto-link to first)
    messages.push_back(Message::with_text("user", "How are you?"));
    messages.push_back(Message::with_text("assistant", "I'm doing well!"));
    state["counter"] = 2;

    std::cout << "\nCreating checkpoint 2...\n";
    auto result2 = manager->create_checkpoint(
        "session-123",
        "demo-agent",
        2,
        state,
        messages
    );

    if (result2.is_ok()) {
        std::cout << "✓ Checkpoint created: " << result2.unwrap() << "\n";
    }

    // 4. Load latest checkpoint
    std::cout << "\nLoading latest checkpoint...\n";
    auto latest_result = manager->get_latest_checkpoint("session-123");
    if (latest_result.is_ok() && latest_result.unwrap().has_value()) {
        auto checkpoint = latest_result.unwrap().value();
        std::cout << "✓ Latest checkpoint: " << checkpoint.checkpoint_id << "\n";
        std::cout << "  Step: " << checkpoint.step_number << "\n";
        std::cout << "  Messages: " << checkpoint.messages.size() << "\n";
        std::cout << "  State counter: " << checkpoint.state["counter"] << "\n";
    }

    // 5. List all checkpoints
    std::cout << "\nListing all checkpoints...\n";
    auto list_result = manager->list_session_checkpoints("session-123");
    if (list_result.is_ok()) {
        auto checkpoints = list_result.unwrap();
        std::cout << "✓ Found " << checkpoints.size() << " checkpoints:\n";
        for (const auto& cp : checkpoints) {
            std::cout << "  - " << cp.checkpoint_id << " (step " << cp.step_number << ")\n";
        }
    }

    // 6. Get checkpoint history
    if (result2.is_ok()) {
        std::cout << "\nGetting checkpoint history...\n";
        auto history_result = manager->get_history(result2.unwrap());
        if (history_result.is_ok()) {
            auto history = history_result.unwrap();
            std::cout << "✓ History chain (" << history.size() << " checkpoints):\n";
            for (const auto& cp : history) {
                std::cout << "  - Step " << cp.step_number;
                if (cp.parent_checkpoint_id.has_value()) {
                    std::cout << " → parent: " << cp.parent_checkpoint_id.value().substr(0, 8) << "...\n";
                } else {
                    std::cout << " (root)\n";
                }
            }
        }
    }

    // 7. Get statistics
    auto stats_result = manager->get_stats();
    if (stats_result.is_ok()) {
        auto stats = stats_result.unwrap();
        std::cout << "\nStatistics:\n";
        std::cout << "  Checkpoints: " << stats["checkpoints"] << "\n";
        std::cout << "  Sessions: " << stats["sessions"] << "\n";
    }
}

void example_file_storage() {
    std::cout << "\n=== File Storage Example ===\n\n";

    // Use temporary directory
    auto storage = std::make_unique<FileCheckpointStorage>("/tmp/agenkit-checkpoints");
    auto manager = std::make_unique<CheckpointManager>(std::move(storage));

    std::vector<Message> messages;
    messages.push_back(Message::with_text("user", "Test file storage"));

    nlohmann::json state;
    state["test"] = true;

    std::cout << "Creating checkpoint with file storage...\n";
    auto result = manager->create_checkpoint(
        "file-session",
        "file-agent",
        1,
        state,
        messages
    );

    if (result.is_ok()) {
        std::cout << "✓ Checkpoint saved to disk: " << result.unwrap() << "\n";
        std::cout << "  Location: /tmp/agenkit-checkpoints/file-session/\n";

        // Load it back
        auto load_result = manager->load_checkpoint(result.unwrap());
        if (load_result.is_ok() && load_result.unwrap().has_value()) {
            std::cout << "✓ Successfully loaded from disk\n";
        }
    }
}

void example_time_travel() {
    std::cout << "\n=== Time-Travel Debugging Example ===\n\n";

    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    auto manager = std::make_unique<CheckpointManager>(std::move(storage));

    // Create a series of checkpoints
    std::vector<std::string> checkpoint_ids;
    std::vector<Message> messages;

    for (int i = 1; i <= 5; i++) {
        messages.push_back(Message::with_text("user", "Step " + std::to_string(i)));
        nlohmann::json state;
        state["step"] = i;

        auto result = manager->create_checkpoint(
            "time-travel-session",
            "agent",
            i,
            state,
            messages
        );

        if (result.is_ok()) {
            checkpoint_ids.push_back(result.unwrap());
            std::cout << "Created checkpoint " << i << "\n";
        }
    }

    // Replay from checkpoint 3
    std::cout << "\nReplaying from checkpoint 3...\n";
    auto replay_result = manager->replay_from_checkpoint(checkpoint_ids[2]);
    if (replay_result.is_ok()) {
        auto replay = replay_result.unwrap();
        std::cout << "✓ Replay sequence (" << replay.size() << " steps):\n";
        for (const auto& cp : replay) {
            std::cout << "  Step " << cp.step_number << ": " << cp.state["step"] << "\n";
        }
    }
}

void example_pruning() {
    std::cout << "\n=== Auto-Pruning Example ===\n\n";

    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    auto config = CheckpointConfig::with_max_checkpoints(3);
    auto manager = std::make_unique<CheckpointManager>(std::move(storage), config);

    // Create 5 checkpoints (should auto-prune to keep only 3)
    std::vector<Message> messages;
    for (int i = 1; i <= 5; i++) {
        nlohmann::json state;
        state["step"] = i;

        auto result = manager->create_checkpoint(
            "prune-session",
            "agent",
            i,
            state,
            messages
        );

        if (result.is_ok()) {
            std::cout << "Created checkpoint " << i << "\n";
        }
    }

    // Check how many remain
    auto list_result = manager->list_session_checkpoints("prune-session");
    if (list_result.is_ok()) {
        auto checkpoints = list_result.unwrap();
        std::cout << "\n✓ After auto-pruning: " << checkpoints.size() << " checkpoints remain\n";
        std::cout << "  (configured max: 3)\n";
    }
}

void example_durable_agent() {
    std::cout << "\n=== DurableAgent Wrapper Example ===\n\n";

    // Create manager
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    auto manager = std::make_shared<CheckpointManager>(std::move(storage));

    // Wrap agent with DurableAgent
    auto agent = std::make_unique<SimpleAgent>("durable-agent");
    auto durable = DurableAgent<SimpleAgent>(
        std::move(agent),
        manager,
        "durable-session",
        true  // auto-checkpoint enabled
    );

    std::cout << "Running agent steps (auto-checkpointing enabled)...\n";

    // Run 3 steps - each automatically creates a checkpoint
    durable.run(std::string("First input"));
    std::cout << "✓ Step 1 completed (auto-checkpointed)\n";

    durable.run(std::string("Second input"));
    std::cout << "✓ Step 2 completed (auto-checkpointed)\n";

    durable.run(std::string("Third input"));
    std::cout << "✓ Step 3 completed (auto-checkpointed)\n";

    // Check checkpoint history
    auto history_result = durable.get_history();
    if (history_result.is_ok()) {
        auto history = history_result.unwrap();
        std::cout << "\n✓ Created " << history.size() << " automatic checkpoints\n";
    }

    std::cout << "\nSimulating crash and restore...\n";

    // Restore from latest
    auto restore_result = durable.restore_latest();
    if (restore_result.is_ok() && restore_result.unwrap()) {
        std::cout << "✓ Agent restored from checkpoint\n";
        std::cout << "  Current step: " << durable.step_number() << "\n";
    }
}

int main() {
    std::cout << "Agenkit C++ Checkpointing Examples\n";
    std::cout << "===================================\n";

    try {
        example_basic_checkpointing();
        example_file_storage();
        example_time_travel();
        example_pruning();
        example_durable_agent();

        std::cout << "\n=== All Examples Completed ===\n\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
}
