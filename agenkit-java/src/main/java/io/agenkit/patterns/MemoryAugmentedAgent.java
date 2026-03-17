package io.agenkit.patterns;

import io.agenkit.adapters.LlmClient;
import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import io.agenkit.memory.Memory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * An agent augmented with pluggable memory.
 */
public final class MemoryAugmentedAgent implements Agent {

    private final String name;
    private final LlmClient llmClient;
    private final Memory memory;
    private final int topK;

    public MemoryAugmentedAgent(String name, LlmClient llmClient, Memory memory, int topK) {
        this.name = name;
        this.llmClient = llmClient;
        this.memory = memory;
        this.topK = topK;
    }

    public MemoryAugmentedAgent(String name, LlmClient llmClient, Memory memory) {
        this(name, llmClient, memory, 3);
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("memory", "context_retrieval");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        List<Message> relevant = memory.retrieve(message.contentString(), topK);

        List<Message> messages = new ArrayList<>();
        messages.add(Message.of("system", "You have access to relevant memory context."));
        if (!relevant.isEmpty()) {
            StringBuilder ctx = new StringBuilder("Relevant memory:\n");
            for (Message mem : relevant) {
                ctx.append("- ").append(mem.contentString()).append("\n");
            }
            messages.add(Message.of("system", ctx.toString()));
        }
        messages.add(message);

        return llmClient.complete(messages).thenApply(response -> {
            memory.store(message);
            memory.store(response);
            return response.withMetadata("memory_hits", relevant.size());
        });
    }

    @Override
    public IntrospectionResult introspect() {
        Map<String, Object> memoryState = new HashMap<>();
        memoryState.put("size", memory.size());
        memoryState.put("topK", topK);
        return new IntrospectionResult(name, getCapabilities(), memoryState, null, null);
    }
}
