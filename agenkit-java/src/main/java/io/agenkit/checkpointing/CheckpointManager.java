package io.agenkit.checkpointing;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Manages agent checkpoints for durability and recovery.
 */
public final class CheckpointManager {

    private static final Logger log = LoggerFactory.getLogger(CheckpointManager.class);

    private final Map<String, Object> inMemoryStore = new ConcurrentHashMap<>();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Path checkpointDir;

    public CheckpointManager(Path checkpointDir) {
        this.checkpointDir = checkpointDir;
        try {
            Files.createDirectories(checkpointDir);
        } catch (IOException e) {
            log.warn("failed to create checkpoint directory: {}", e.getMessage());
        }
    }

    public CheckpointManager() {
        this(Path.of(System.getProperty("java.io.tmpdir"), "agenkit-checkpoints"));
    }

    public void save(String agentId, Object state) {
        inMemoryStore.put(agentId, state);
        try {
            Path file = checkpointDir.resolve(agentId + ".json");
            objectMapper.writeValue(file.toFile(), state);
            log.debug("checkpoint saved for agent={}", agentId);
        } catch (IOException e) {
            log.warn("failed to persist checkpoint for agent={}: {}", agentId, e.getMessage());
        }
    }

    public Optional<Object> load(String agentId) {
        Object cached = inMemoryStore.get(agentId);
        if (cached != null) return Optional.of(cached);

        Path file = checkpointDir.resolve(agentId + ".json");
        if (!Files.exists(file)) return Optional.empty();

        try {
            Object state = objectMapper.readValue(file.toFile(), Object.class);
            inMemoryStore.put(agentId, state);
            return Optional.of(state);
        } catch (IOException e) {
            log.warn("failed to load checkpoint for agent={}: {}", agentId, e.getMessage());
            return Optional.empty();
        }
    }

    public void delete(String agentId) {
        inMemoryStore.remove(agentId);
        try {
            Files.deleteIfExists(checkpointDir.resolve(agentId + ".json"));
        } catch (IOException e) {
            log.warn("failed to delete checkpoint for agent={}: {}", agentId, e.getMessage());
        }
    }

    public boolean exists(String agentId) {
        return inMemoryStore.containsKey(agentId)
                || Files.exists(checkpointDir.resolve(agentId + ".json"));
    }
}
