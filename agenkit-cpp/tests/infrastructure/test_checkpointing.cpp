/**
 * @file test_checkpointing.cpp
 * @brief Comprehensive tests for checkpointing infrastructure
 */

#include <gtest/gtest.h>
#include "agenkit/infrastructure/checkpointing/checkpointing.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <filesystem>
#include <fstream>

using namespace agenkit::infrastructure::checkpointing;
using namespace agenkit::core;

// ============================================================================
// Test Helper: MockAgent
// ============================================================================

class MockAgent : public Agent {
private:
    std::string name_;
    int call_count_ = 0;

public:
    explicit MockAgent(std::string name) : name_(std::move(name)) {}

    std::string name() const override { return name_; }

    std::future<Result<Message, AgentError>> process(Message message) override {
        call_count_++;
        return make_ready_future(
            Result<Message, AgentError>::ok(
                Message::with_text("assistant", "Response " + std::to_string(call_count_))
            )
        );
    }

    int call_count() const { return call_count_; }
};

// ============================================================================
// Checkpoint Tests
// ============================================================================

TEST(CheckpointTest, CreateBasicCheckpoint) {
    nlohmann::json state = {{"counter", 42}};
    std::vector<Message> messages = {
        Message::with_text("user", "Hello")
    };

    auto checkpoint = Checkpoint::create("session-1", "agent-1", 1, state, messages);

    EXPECT_EQ(checkpoint.session_id, "session-1");
    EXPECT_EQ(checkpoint.agent_name, "agent-1");
    EXPECT_EQ(checkpoint.step_number, 1);
    EXPECT_EQ(checkpoint.state["counter"], 42);
    EXPECT_EQ(checkpoint.messages.size(), 1);
    EXPECT_FALSE(checkpoint.checkpoint_id.empty());
}

TEST(CheckpointTest, CheckpointWithMetadata) {
    auto checkpoint = Checkpoint::create("session-1", "agent-1", 1, {}, {});

    nlohmann::json metadata = {{"reason", "test"}, {"priority", "high"}};
    checkpoint.with_metadata(metadata);

    ASSERT_TRUE(checkpoint.metadata.has_value());
    EXPECT_EQ(checkpoint.metadata.value()["reason"], "test");
}

TEST(CheckpointTest, CheckpointWithParent) {
    auto checkpoint = Checkpoint::create("session-1", "agent-1", 1, {}, {});
    checkpoint.with_parent("parent-checkpoint-id");

    ASSERT_TRUE(checkpoint.parent_checkpoint_id.has_value());
    EXPECT_EQ(checkpoint.parent_checkpoint_id.value(), "parent-checkpoint-id");
}

TEST(CheckpointTest, SerializeAndDeserialize) {
    nlohmann::json state = {{"key", "value"}};
    std::vector<Message> messages = {
        Message::with_text("user", "Test message")
    };

    auto original = Checkpoint::create("session-1", "agent-1", 1, state, messages);
    original.with_metadata(nlohmann::json{{"test", true}});
    original.with_parent("parent-id");

    // Serialize
    std::string json_str = original.to_json();
    EXPECT_FALSE(json_str.empty());

    // Deserialize
    auto deserialized = Checkpoint::from_json(json_str);

    EXPECT_EQ(deserialized.checkpoint_id, original.checkpoint_id);
    EXPECT_EQ(deserialized.session_id, original.session_id);
    EXPECT_EQ(deserialized.agent_name, original.agent_name);
    EXPECT_EQ(deserialized.step_number, original.step_number);
    EXPECT_EQ(deserialized.state, original.state);
    EXPECT_EQ(deserialized.messages.size(), original.messages.size());
}

// ============================================================================
// InMemoryCheckpointStorage Tests
// ============================================================================

TEST(InMemoryStorageTest, SaveAndLoadCheckpoint) {
    InMemoryCheckpointStorage storage;

    auto checkpoint = Checkpoint::create("session-1", "agent-1", 1, {}, {});

    auto save_result = storage.save(checkpoint);
    ASSERT_TRUE(save_result.is_ok());
    EXPECT_TRUE(save_result.unwrap());

    auto load_result = storage.load(checkpoint.checkpoint_id);
    ASSERT_TRUE(load_result.is_ok());
    ASSERT_TRUE(load_result.unwrap().has_value());

    auto loaded = load_result.unwrap().value();
    EXPECT_EQ(loaded.checkpoint_id, checkpoint.checkpoint_id);
}

TEST(InMemoryStorageTest, LoadNonExistentCheckpoint) {
    InMemoryCheckpointStorage storage;

    auto result = storage.load("non-existent-id");
    ASSERT_TRUE(result.is_ok());
    EXPECT_FALSE(result.unwrap().has_value());
}

TEST(InMemoryStorageTest, ListCheckpointsBySession) {
    InMemoryCheckpointStorage storage;

    auto cp1 = Checkpoint::create("session-1", "agent-1", 1, {}, {});
    auto cp2 = Checkpoint::create("session-1", "agent-1", 2, {}, {});
    auto cp3 = Checkpoint::create("session-2", "agent-1", 1, {}, {});

    storage.save(cp1);
    storage.save(cp2);
    storage.save(cp3);

    auto result = storage.list_checkpoints("session-1");
    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.unwrap().size(), 2);
}

TEST(InMemoryStorageTest, GetLatestCheckpoint) {
    InMemoryCheckpointStorage storage;

    // Add checkpoints with delays to ensure different timestamps
    auto cp1 = Checkpoint::create("session-1", "agent-1", 1, {}, {});
    storage.save(cp1);

    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    auto cp2 = Checkpoint::create("session-1", "agent-1", 2, {}, {});
    storage.save(cp2);

    auto result = storage.get_latest("session-1");
    ASSERT_TRUE(result.is_ok());
    ASSERT_TRUE(result.unwrap().has_value());

    auto latest = result.unwrap().value();
    EXPECT_EQ(latest.step_number, 2);
}

TEST(InMemoryStorageTest, RemoveCheckpoint) {
    InMemoryCheckpointStorage storage;

    auto checkpoint = Checkpoint::create("session-1", "agent-1", 1, {}, {});
    storage.save(checkpoint);

    auto remove_result = storage.deleteCheckpoint(checkpoint.checkpoint_id);
    ASSERT_TRUE(remove_result.is_ok());
    EXPECT_TRUE(remove_result.unwrap());

    auto load_result = storage.load(checkpoint.checkpoint_id);
    ASSERT_TRUE(load_result.is_ok());
    EXPECT_FALSE(load_result.unwrap().has_value());
}

TEST(InMemoryStorageTest, DeleteSession) {
    InMemoryCheckpointStorage storage;

    storage.save(Checkpoint::create("session-1", "agent-1", 1, {}, {}));
    storage.save(Checkpoint::create("session-1", "agent-1", 2, {}, {}));
    storage.save(Checkpoint::create("session-2", "agent-1", 1, {}, {}));

    auto result = storage.delete_session("session-1");
    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.unwrap(), 2);

    auto list_result = storage.list_checkpoints("session-1");
    ASSERT_TRUE(list_result.is_ok());
    EXPECT_EQ(list_result.unwrap().size(), 0);
}

TEST(InMemoryStorageTest, GetCheckpointHistory) {
    InMemoryCheckpointStorage storage;

    auto cp1 = Checkpoint::create("session-1", "agent-1", 1, {}, {});
    storage.save(cp1);

    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    auto cp2 = Checkpoint::create("session-1", "agent-1", 2, {}, {});
    cp2.with_parent(cp1.checkpoint_id);
    storage.save(cp2);

    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    auto cp3 = Checkpoint::create("session-1", "agent-1", 3, {}, {});
    cp3.with_parent(cp2.checkpoint_id);
    storage.save(cp3);

    auto result = storage.get_checkpoint_history(cp3.checkpoint_id);
    ASSERT_TRUE(result.is_ok());

    auto history = result.unwrap();
    EXPECT_EQ(history.size(), 3);
    // get_checkpoint_history follows parent links newest-to-oldest
    EXPECT_EQ(history[0].step_number, 3);
    EXPECT_EQ(history[1].step_number, 2);
    EXPECT_EQ(history[2].step_number, 1);
}

// ============================================================================
// FileCheckpointStorage Tests
// ============================================================================

class FileStorageTest : public ::testing::Test {
protected:
    std::filesystem::path test_dir = std::filesystem::temp_directory_path() / "checkpoint_test";

    void SetUp() override {
        std::filesystem::create_directories(test_dir);
    }

    void TearDown() override {
        if (std::filesystem::exists(test_dir)) {
            std::filesystem::remove_all(test_dir);
        }
    }
};

TEST_F(FileStorageTest, SaveAndLoadCheckpoint) {
    FileCheckpointStorage storage(test_dir.string());

    auto checkpoint = Checkpoint::create("session-1", "agent-1", 1, {{"key", "value"}}, {});

    auto save_result = storage.save(checkpoint);
    ASSERT_TRUE(save_result.is_ok());

    auto load_result = storage.load(checkpoint.checkpoint_id);
    ASSERT_TRUE(load_result.is_ok());
    ASSERT_TRUE(load_result.unwrap().has_value());

    auto loaded = load_result.unwrap().value();
    EXPECT_EQ(loaded.checkpoint_id, checkpoint.checkpoint_id);
    EXPECT_EQ(loaded.state["key"], "value");
}

TEST_F(FileStorageTest, FileStructure) {
    FileCheckpointStorage storage(test_dir.string());

    auto checkpoint = Checkpoint::create("session-1", "agent-1", 1, {}, {});
    storage.save(checkpoint);

    // Check file exists in correct location
    auto session_dir = test_dir / "session-1";
    EXPECT_TRUE(std::filesystem::exists(session_dir));
    EXPECT_TRUE(std::filesystem::is_directory(session_dir));

    auto checkpoint_file = session_dir / (checkpoint.checkpoint_id + ".json");
    EXPECT_TRUE(std::filesystem::exists(checkpoint_file));
}

TEST_F(FileStorageTest, ListCheckpointsFromDisk) {
    FileCheckpointStorage storage(test_dir.string());

    storage.save(Checkpoint::create("session-1", "agent-1", 1, {}, {}));
    storage.save(Checkpoint::create("session-1", "agent-1", 2, {}, {}));
    storage.save(Checkpoint::create("session-2", "agent-1", 1, {}, {}));

    auto result = storage.list_checkpoints("session-1");
    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.unwrap().size(), 2);
}

TEST_F(FileStorageTest, DeleteSessionFiles) {
    FileCheckpointStorage storage(test_dir.string());

    storage.save(Checkpoint::create("session-1", "agent-1", 1, {}, {}));
    storage.save(Checkpoint::create("session-1", "agent-1", 2, {}, {}));

    auto result = storage.delete_session("session-1");
    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.unwrap(), 2);

    auto session_dir = test_dir / "session-1";
    EXPECT_FALSE(std::filesystem::exists(session_dir));
}

// ============================================================================
// CheckpointManager Tests
// ============================================================================

TEST(CheckpointManagerTest, CreateCheckpointWithDefaults) {
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    CheckpointManager manager(std::move(storage));

    nlohmann::json state = {{"counter", 1}};
    std::vector<Message> messages = {Message::with_text("user", "Hello")};

    auto result = manager.create_checkpoint("session-1", "agent-1", 1, state, messages);
    ASSERT_TRUE(result.is_ok());

    auto checkpoint_id = result.unwrap();
    EXPECT_FALSE(checkpoint_id.empty());

    auto restore_result = manager.load_checkpoint(checkpoint_id);
    ASSERT_TRUE(restore_result.is_ok());
    ASSERT_TRUE(restore_result.unwrap().has_value());
}

TEST(CheckpointManagerTest, AutoParentLinking) {
    CheckpointConfig config;
    config.auto_parent_linking = true;

    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    CheckpointManager manager(std::move(storage), config);

    // Create first checkpoint
    auto result1 = manager.create_checkpoint("session-1", "agent-1", 1, {}, {});
    ASSERT_TRUE(result1.is_ok());

    // Create second checkpoint - should auto-link to first
    auto result2 = manager.create_checkpoint("session-1", "agent-1", 2, {}, {});
    ASSERT_TRUE(result2.is_ok());

    auto restore_result = manager.load_checkpoint(result2.unwrap());
    ASSERT_TRUE(restore_result.is_ok());

    auto checkpoint = restore_result.unwrap().value();
    ASSERT_TRUE(checkpoint.parent_checkpoint_id.has_value());
    EXPECT_EQ(checkpoint.parent_checkpoint_id.value(), result1.unwrap());
}

TEST(CheckpointManagerTest, AutoPruning) {
    CheckpointConfig config;
    config.enable_pruning = true;
    config.max_checkpoints_per_session = 3;

    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    CheckpointManager manager(std::move(storage), config);

    // Create 5 checkpoints (should keep only last 3)
    for (int i = 1; i <= 5; i++) {
        auto result = manager.create_checkpoint("session-1", "agent-1", i, {}, {});
        ASSERT_TRUE(result.is_ok());
    }

    auto list_result = manager.list_session_checkpoints("session-1");
    ASSERT_TRUE(list_result.is_ok());
    EXPECT_EQ(list_result.unwrap().size(), 3);
}

TEST(CheckpointManagerTest, GetLatestCheckpoint) {
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    CheckpointManager manager(std::move(storage));

    manager.create_checkpoint("session-1", "agent-1", 1, {{"step", 1}}, {});
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    manager.create_checkpoint("session-1", "agent-1", 2, {{"step", 2}}, {});

    auto result = manager.get_latest_checkpoint("session-1");
    ASSERT_TRUE(result.is_ok());
    ASSERT_TRUE(result.unwrap().has_value());

    auto checkpoint = result.unwrap().value();
    EXPECT_EQ(checkpoint.step_number, 2);
}

TEST(CheckpointManagerTest, DeleteCheckpoint) {
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    CheckpointManager manager(std::move(storage));

    auto result = manager.create_checkpoint("session-1", "agent-1", 1, {}, {});
    ASSERT_TRUE(result.is_ok());
    auto checkpoint_id = result.unwrap();

    auto delete_result = manager.delete_checkpoint(checkpoint_id);
    ASSERT_TRUE(delete_result.is_ok());
    EXPECT_TRUE(delete_result.unwrap());

    auto restore_result = manager.load_checkpoint(checkpoint_id);
    ASSERT_TRUE(restore_result.is_ok());
    EXPECT_FALSE(restore_result.unwrap().has_value());
}

TEST(CheckpointManagerTest, GetStatistics) {
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    CheckpointManager manager(std::move(storage));

    manager.create_checkpoint("session-1", "agent-1", 1, {}, {});
    manager.create_checkpoint("session-1", "agent-1", 2, {}, {});
    manager.create_checkpoint("session-2", "agent-2", 1, {}, {});

    auto stats_result = manager.get_stats();
    ASSERT_TRUE(stats_result.is_ok());
    auto stats = stats_result.unwrap();
    EXPECT_EQ(stats.at("checkpoints"), 3);
    EXPECT_EQ(stats.at("sessions"), 2);
}

// ============================================================================
// DurableAgent Helper: implements the run/get_state/set_state interface
// ============================================================================

class DurableAgentMock {
    nlohmann::json state_;
    std::vector<Message> messages_;
    int run_count_ = 0;

public:
    std::string name() const { return "durable-mock"; }

    Result<Message, AgentError> run(const Message& input) {
        run_count_++;
        messages_.push_back(input);
        return Result<Message, AgentError>::ok(
            Message::with_text("assistant", "response " + std::to_string(run_count_))
        );
    }

    nlohmann::json get_state() const { return state_; }
    void set_state(const nlohmann::json& s) { state_ = s; }
    std::vector<Message> get_messages() const { return messages_; }
    void set_messages(const std::vector<Message>& msgs) { messages_ = msgs; }
    int run_count() const { return run_count_; }
};

// ============================================================================
// DurableAgent Tests
// ============================================================================

TEST(DurableAgentTest, BasicCheckpointing) {
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    auto manager = std::make_shared<CheckpointManager>(std::move(storage));

    DurableAgent<DurableAgentMock> durable(
        std::make_unique<DurableAgentMock>(),
        manager,
        "session-1"
    );

    // Process a message - should auto-checkpoint
    auto message = Message::with_text("user", "Hello");
    auto result = durable.run(message);
    ASSERT_TRUE(result.is_ok());

    // Check that checkpoint was created
    auto history_result = durable.get_history();
    ASSERT_TRUE(history_result.is_ok());
    EXPECT_GE(history_result.unwrap().size(), 1);
}

TEST(DurableAgentTest, RestoreFromCheckpoint) {
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    auto manager = std::make_shared<CheckpointManager>(std::move(storage));

    DurableAgent<DurableAgentMock> durable(
        std::make_unique<DurableAgentMock>(),
        manager,
        "session-1"
    );

    // Create a checkpoint manually
    auto cp_result = durable.checkpoint();
    ASSERT_TRUE(cp_result.is_ok());
    auto checkpoint_id = cp_result.unwrap();

    // Restore from checkpoint
    auto restore_result = durable.restore(checkpoint_id);
    ASSERT_TRUE(restore_result.is_ok());
    EXPECT_TRUE(restore_result.unwrap());
}

TEST(DurableAgentTest, DisableAutoCheckpoint) {
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    auto manager = std::make_shared<CheckpointManager>(std::move(storage));

    // Construct with auto_checkpoint=false
    DurableAgent<DurableAgentMock> durable(
        std::make_unique<DurableAgentMock>(),
        manager,
        "session-1",
        false  // auto_checkpoint disabled
    );

    auto message = Message::with_text("user", "Hello");
    durable.run(message);

    // No auto-checkpoint: history should be empty
    auto history_result = durable.get_history();
    ASSERT_TRUE(history_result.is_ok());
    EXPECT_EQ(history_result.unwrap().size(), 0);

    // Manual checkpoint should still work
    auto cp_result = durable.checkpoint();
    ASSERT_TRUE(cp_result.is_ok());

    history_result = durable.get_history();
    ASSERT_TRUE(history_result.is_ok());
    EXPECT_EQ(history_result.unwrap().size(), 1);
}

TEST(DurableAgentTest, StateManagement) {
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    auto manager = std::make_shared<CheckpointManager>(std::move(storage));

    DurableAgent<DurableAgentMock> durable(
        std::make_unique<DurableAgentMock>(),
        manager,
        "session-1"
    );

    // Session ID should be preserved
    EXPECT_EQ(durable.session_id(), "session-1");

    // Step number starts at 0
    EXPECT_EQ(durable.step_number(), 0);
}
