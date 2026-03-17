package io.agenkit.checkpointing;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Agent wrapper that automatically checkpoints state after each interaction.
 */
public final class DurableAgent implements Agent {

    private static final Logger log = LoggerFactory.getLogger(DurableAgent.class);

    private final Agent inner;
    private final CheckpointManager checkpointManager;
    private final String agentId;
    private final List<String> interactionLog = new ArrayList<>();

    public DurableAgent(Agent inner, CheckpointManager checkpointManager) {
        this.inner = inner;
        this.checkpointManager = checkpointManager;
        this.agentId = inner.getName() + "-" + System.currentTimeMillis();

        // Restore from checkpoint if available
        checkpointManager.load(agentId).ifPresent(state -> {
            if (state instanceof List<?> list) {
                list.forEach(item -> interactionLog.add(String.valueOf(item)));
                log.info("restored {} interactions from checkpoint", interactionLog.size());
            }
        });
    }

    @Override
    public String getName() { return inner.getName() + "[durable]"; }

    @Override
    public List<String> getCapabilities() { return inner.getCapabilities(); }

    @Override
    public CompletableFuture<Message> process(Message message) {
        return inner.process(message).thenApply(response -> {
            interactionLog.add(message.contentString() + " -> " + response.contentString());
            checkpointManager.save(agentId, new ArrayList<>(interactionLog));
            log.debug("checkpointed interaction #{}", interactionLog.size());
            return response.withMetadata("checkpoint_id", agentId)
                    .withMetadata("interaction_count", interactionLog.size());
        });
    }

    public List<String> getInteractionLog() { return List.copyOf(interactionLog); }

    @Override
    public IntrospectionResult introspect() {
        Map<String, Object> state = new HashMap<>();
        state.put("agentId", agentId);
        state.put("interactions", interactionLog.size());
        return new IntrospectionResult(getName(), getCapabilities(), null, state, null);
    }
}
