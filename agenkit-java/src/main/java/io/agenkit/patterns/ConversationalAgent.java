package io.agenkit.patterns;

import io.agenkit.adapters.LlmClient;
import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * An agent that maintains conversation history.
 */
public final class ConversationalAgent implements Agent {

    private static final int DEFAULT_MAX_HISTORY = 10;

    private final String name;
    private final LlmClient llmClient;
    private final String systemPrompt;
    private int maxHistory;
    private final List<Message> history = new ArrayList<>();

    public ConversationalAgent(String name, LlmClient llmClient, String systemPrompt, int maxHistory) {
        this.name = name;
        this.llmClient = llmClient;
        this.systemPrompt = systemPrompt;
        this.maxHistory = maxHistory;
    }

    public ConversationalAgent(String name, LlmClient llmClient) {
        this(name, llmClient, "You are a helpful assistant.", DEFAULT_MAX_HISTORY);
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("conversation", "history");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        history.add(message);
        List<Message> messages = buildMessages();
        return llmClient.complete(messages).thenApply(response -> {
            history.add(response);
            pruneHistory();
            return response;
        });
    }

    @Override
    public IntrospectionResult introspect() {
        Map<String, Object> state = new HashMap<>();
        state.put("historySize", history.size());
        state.put("maxHistory", maxHistory);
        return new IntrospectionResult(name, getCapabilities(), null, state, null);
    }

    public List<Message> getHistory() { return Collections.unmodifiableList(history); }

    public void clearHistory(boolean keepSystem) {
        history.clear();
    }

    public void setMaxHistory(int maxHistory) {
        this.maxHistory = maxHistory;
        pruneHistory();
    }

    private List<Message> buildMessages() {
        List<Message> messages = new ArrayList<>();
        if (systemPrompt != null && !systemPrompt.isEmpty()) {
            messages.add(Message.of("system", systemPrompt));
        }
        messages.addAll(history);
        return messages;
    }

    private void pruneHistory() {
        while (history.size() > maxHistory * 2) {
            history.remove(0);
            if (!history.isEmpty()) {
                history.remove(0);
            }
        }
    }
}
