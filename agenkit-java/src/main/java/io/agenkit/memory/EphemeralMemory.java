package io.agenkit.memory;

import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * In-memory storage that does not persist across sessions.
 */
public final class EphemeralMemory implements Memory {

    private final List<Message> messages = new ArrayList<>();
    private final int maxSize;

    public EphemeralMemory(int maxSize) {
        this.maxSize = maxSize;
    }

    public EphemeralMemory() {
        this(1000);
    }

    @Override
    public synchronized void store(Message message) {
        messages.add(message);
        if (messages.size() > maxSize) {
            messages.remove(0);
        }
    }

    @Override
    public synchronized List<Message> retrieve(String query, int topK) {
        // Simple recency-based retrieval
        int start = Math.max(0, messages.size() - topK);
        return Collections.unmodifiableList(new ArrayList<>(messages.subList(start, messages.size())));
    }

    @Override
    public synchronized int size() { return messages.size(); }

    @Override
    public synchronized void clear() { messages.clear(); }
}
