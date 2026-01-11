/**
 * @file test_checkpointing.cpp
 * @brief Comprehensive tests for checkpointing infrastructure
 */

#include <gtest/gtest.h>
#include "agenkit/infrastructure/checkpointing.hpp"
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
    EXPECT_TRUE(save_result.value());

    auto load_result = storage.load(checkpoint.checkpoint_id);
    ASSERT_TRUE(load_result.is_ok());
    ASSERT_TRUE(load_result.value().has_value());

    auto loaded = load_result.value().value();
    EXPECT_EQ(loaded.checkpoint_id, checkpoint.checkpoint_id);
}

TEST(InMemoryStorageTest, LoadNonExistentCheckpoint) {
    InMemoryCheckpointStorage storage;

    auto result = storage.load("non-existent-id");
    ASSERT_TRUE(result.is_ok());
    EXPECT_FALSE(result.value().has_value());
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
    EXPECT_EQ(result.value().size(), 2);
}

TEST(InMemoryStorageTest, GetLatestCheckpoint) {
    InMemoryCheckpointStorage storage;

    // Add checkpoints with delays to ensure different timestamps
    auto cp1 = Checkpoint::create("session-1", "agent-1", 1, {}, {});
    storage.save(cp1);

    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    auto cp2 = Checkpoint::create("session-1", "agent-1", 2, {}, {});
    storage.save(cp2);

    auto result = storage.get_latest("session-1", "agent-1");
    ASSERT_TRUE(result.is_ok());
    ASSERT_TRUE(result.value().has_value());

    auto latest = result.value().value();
    EXPECT_EQ(latest.step_number, 2);
}

TEST(InMemoryStorageTest, RemoveCheckpoint) {
    InMemoryCheckpointStorage storage;

    auto checkpoint = Checkpoint::create("session-1", "agent-1", 1, {}, {});
    storage.save(checkpoint);

    auto remove_result = storage.remove(checkpoint.checkpoint_id);
    ASSERT_TRUE(remove_result.is_ok());
    EXPECT_TRUE(remove_result.value());

    auto load_result = storage.load(checkpoint.checkpoint_id);
    ASSERT_TRUE(load_result.is_ok());
    EXPECT_FALSE(load_result.value().has_value());
}

TEST(InMemoryStorageTest, DeleteSession) {
    InMemoryCheckpointStorage storage;

    storage.save(Checkpoint::create("session-1", "agent-1", 1, {}, {}));
    storage.save(Checkpoint::create("session-1", "agent-1", 2, {}, {}));
    storage.save(Checkpoint::create("session-2", "agent-1", 1, {}, {}));

    auto result = storage.delete_session("session-1");
    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.value(), 2);

    auto list_result = storage.list_checkpoints("session-1");
    ASSERT_TRUE(list_result.is_ok());
    EXPECT_EQ(list_result.value().size(), 0);
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

    auto result = storage.get_checkpoint_history("session-1", "agent-1");
    ASSERT_TRUE(result.is_ok());

    auto history = result.value();
    EXPECT_EQ(history.size(), 3);
    EXPECT_EQ(history[0].step_number, 1);
    EXPECT_EQ(history[1].step_number, 2);
    EXPECT_EQ(history[2].step_number, 3);
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
    ASSERT_TRUE(load_result.value().has_value());

    auto loaded = load_result.value().value();
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
    EXPECT_EQ(result.value().size(), 2);
}

TEST_F(FileStorageTest, DeleteSessionFiles) {
    FileCheckpointStorage storage(test_dir.string());

    storage.save(Checkpoint::create("session-1", "agent-1", 1, {}, {}));
    storage.save(Checkpoint::create("session-1", "agent-1", 2, {}, {}));

    auto result = storage.delete_session("session-1");
    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.value(), 2);

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

    auto checkpoint_id = result.value();
    EXPECT_FALSE(checkpoint_id.empty());

    auto restore_result = manager.restore_checkpoint(checkpoint_id);
    ASSERT_TRUE(restore_result.is_ok());
    ASSERT_TRUE(restore_result.value().has_value());
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

    auto restore_result = manager.restore_checkpoint(result2.value());
    ASSERT_TRUE(restore_result.is_ok());

    auto checkpoint = restore_result.value().value();
    ASSERT_TRUE(checkpoint.parent_checkpoint_id.has_value());
    EXPECT_EQ(checkpoint.parent_checkpoint_id.value(), result1.value());
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
    EXPECT_EQ(list_result.value().size(), 3);
}

TEST(CheckpointManagerTest, GetLatestCheckpoint) {
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    CheckpointManager manager(std::move(storage));

    manager.create_checkpoint("session-1", "agent-1", 1, {{"step", 1}}, {});
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    manager.create_checkpoint("session-1", "agent-1", 2, {{"step", 2}}, {});

    auto result = manager.get_latest("session-1", "agent-1");
    ASSERT_TRUE(result.is_ok());
    ASSERT_TRUE(result.value().has_value());

    auto checkpoint = result.value().value();
    EXPECT_EQ(checkpoint.step_number, 2);
}

TEST(CheckpointManagerTest, DeleteCheckpoint) {
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    CheckpointManager manager(std::move(storage));

    auto result = manager.create_checkpoint("session-1", "agent-1", 1, {}, {});
    ASSERT_TRUE(result.is_ok());
    auto checkpoint_id = result.value();

    auto delete_result = manager.delete_checkpoint(checkpoint_id);
    ASSERT_TRUE(delete_result.is_ok());
    EXPECT_TRUE(delete_result.value());

    auto restore_result = manager.restore_checkpoint(checkpoint_id);
    ASSERT_TRUE(restore_result.is_ok());
    EXPECT_FALSE(restore_result.value().has_value());
}

TEST(CheckpointManagerTest, GetStatistics) {
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    CheckpointManager manager(std::move(storage));

    manager.create_checkpoint("session-1", "agent-1", 1, {}, {});
    manager.create_checkpoint("session-1", "agent-1", 2, {}, {});
    manager.create_checkpoint("session-2", "agent-2", 1, {}, {});

    auto stats = manager.get_statistics();
    EXPECT_EQ(stats.total_checkpoints, 3);
    EXPECT_EQ(stats.sessions.size(), 2);
    EXPECT_EQ(stats.checkpoints_by_session["session-1"], 2);
    EXPECT_EQ(stats.checkpoints_by_session["session-2"], 1);
}

// ============================================================================
// DurableAgent Tests
// ============================================================================

TEST(DurableAgentTest, BasicCheckpointing) {
    auto agent = std::make_shared<MockAgent>("test-agent");
    auto storage = std::make_unique<InMemoryCheckpointStorage>();

    CheckpointConfig config;
    config.auto_parent_linking = true;

    auto durable = DurableAgent<MockAgent>::create(
        agent,
        std::move(storage),
        "session-1",
        config
    );

    // Process messages - should auto-checkpoint
    auto message = Message::with_text("user", "Hello");
    auto result = durable.run(message);
    ASSERT_TRUE(result.is_ok());

    // Check that checkpoint was created
    auto checkpoints = durable.list_checkpoints();
    EXPECT_GE(checkpoints.size(), 1);
}

TEST(DurableAgentTest, RestoreFromCheckpoint) {
    auto agent = std::make_shared<MockAgent>("test-agent");
    auto storage = std::make_unique<InMemoryCheckpointStorage>();
    auto storage_ptr = storage.get();

    CheckpointConfig config;
    auto durable = DurableAgent<MockAgent>::create(
        agent,
        std::move(storage),
        "session-1",
        config
    );

    // Create a checkpoint manually
    nlohmann::json state = {{"restored", true}};
    auto checkpoint = Checkpoint::create("session-1", "test-agent", 1, state, {});
    storage_ptr->save(checkpoint);

    // Restore from checkpoint
    EXPECT_TRUE(durable.restore(checkpoint.checkpoint_id));

    auto restored_state = durable.get_state();
    EXPECT_TRUE(restored_state["restored"]);
}

TEST(DurableAgentTest, DisableAutoCheckpoint) {
    auto agent = std::make_shared<MockAgent>("test-agent");
    auto storage = std::make_unique<InMemoryCheckpointStorage>();

    CheckpointConfig config;
    auto durable = DurableAgent<MockAgent>::create(
        agent,
        std::move(storage),
        "session-1",
        config
    );

    // Disable auto-checkpoint
    durable.set_auto_checkpoint(false);

    auto message = Message::with_text("user", "Hello");
    durable.run(message);

    // Should not auto-checkpoint
    auto checkpoints = durable.list_checkpoints();
    EXPECT_EQ(checkpoints.size(), 0);

    // Manual checkpoint should still work
    durable.checkpoint();
    checkpoints = durable.list_checkpoints();
    EXPECT_EQ(checkpoints.size(), 1);
}

TEST(DurableAgentTest, StateManagement) {
    auto agent = std::make_shared<MockAgent>("test-agent");
    auto storage = std::make_unique<InMemoryCheckpointStorage>();

    auto durable = DurableAgent<MockAgent>::create(
        agent,
        std::move(storage),
        "session-1"
    );

    // Set state
    nlohmann::json state = {{"key", "value"}, {"count", 42}};
    durable.set_state(state);

    // Get state
    auto retrieved = durable.get_state();
    EXPECT_EQ(retrieved["key"], "value");
    EXPECT_EQ(retrieved["count"], 42);
}
