package io.agenkit.checkpointing;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;

class CheckpointManagerTest {

    @Test
    void saveAndLoadInMemory(@TempDir Path tempDir) {
        CheckpointManager manager = new CheckpointManager(tempDir);
        manager.save("agent-1", Map.of("status", "active"));

        Optional<Object> loaded = manager.load("agent-1");
        assertThat(loaded).isPresent();
    }

    @Test
    void loadMissingReturnsEmpty(@TempDir Path tempDir) {
        CheckpointManager manager = new CheckpointManager(tempDir);
        Optional<Object> result = manager.load("nonexistent-agent");
        assertThat(result).isEmpty();
    }

    @Test
    void existsReturnsTrueAfterSave(@TempDir Path tempDir) {
        CheckpointManager manager = new CheckpointManager(tempDir);
        manager.save("my-agent", "state-data");
        assertThat(manager.exists("my-agent")).isTrue();
    }

    @Test
    void existsReturnsFalseForUnknown(@TempDir Path tempDir) {
        CheckpointManager manager = new CheckpointManager(tempDir);
        assertThat(manager.exists("unknown")).isFalse();
    }

    @Test
    void deleteRemovesCheckpoint(@TempDir Path tempDir) {
        CheckpointManager manager = new CheckpointManager(tempDir);
        manager.save("to-delete", "state");
        assertThat(manager.exists("to-delete")).isTrue();
        manager.delete("to-delete");
        assertThat(manager.exists("to-delete")).isFalse();
    }

    @Test
    void durableAgentCheckpointsInteractions(@TempDir Path tempDir) throws Exception {
        MockAgent inner = new MockAgent("inner", "reply");
        CheckpointManager mgr = new CheckpointManager(tempDir);
        DurableAgent durable = new DurableAgent(inner, mgr);

        durable.process(Message.of("user", "hello")).get();

        assertThat(durable.getInteractionLog()).hasSize(1);
        assertThat(durable.getInteractionLog().get(0)).contains("hello").contains("reply");
    }

    @Test
    void durableAgentNameIncludesDurableSuffix(@TempDir Path tempDir) {
        MockAgent inner = new MockAgent("base-agent", "ok");
        CheckpointManager mgr = new CheckpointManager(tempDir);
        DurableAgent durable = new DurableAgent(inner, mgr);
        assertThat(durable.getName()).contains("base-agent").contains("durable");
    }

    @Test
    void durableAgentResponseHasCheckpointMetadata(@TempDir Path tempDir) throws Exception {
        MockAgent inner = new MockAgent("inner", "result");
        CheckpointManager mgr = new CheckpointManager(tempDir);
        DurableAgent durable = new DurableAgent(inner, mgr);

        Message response = durable.process(Message.of("user", "test")).get();
        assertThat(response.getMetadata()).containsKey("checkpoint_id");
        assertThat(response.getMetadata()).containsKey("interaction_count");
    }

    @Test
    void durableAgentMultipleInteractionsLogged(@TempDir Path tempDir) throws Exception {
        MockAgent inner = new MockAgent("inner", msg -> "response-" + msg.contentString());
        CheckpointManager mgr = new CheckpointManager(tempDir);
        DurableAgent durable = new DurableAgent(inner, mgr);

        durable.process(Message.of("user", "a")).get();
        durable.process(Message.of("user", "b")).get();
        durable.process(Message.of("user", "c")).get();

        assertThat(durable.getInteractionLog()).hasSize(3);
    }

    @Test
    void defaultConstructorUsesSystemTmp() {
        CheckpointManager manager = new CheckpointManager();
        manager.save("test-id", "data");
        assertThat(manager.exists("test-id")).isTrue();
        manager.delete("test-id");
    }
}
