package io.agenkit.memory;

import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

/**
 * Simple vector-like memory using keyword overlap as similarity.
 * In production, replace the similarity function with real embeddings.
 */
public final class VectorMemory implements Memory {

    private final List<Message> messages = new ArrayList<>();
    private final int maxSize;

    public VectorMemory(int maxSize) {
        this.maxSize = maxSize;
    }

    public VectorMemory() {
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
        String[] queryTokens = query.toLowerCase().split("\\s+");
        return messages.stream()
                .map(m -> new ScoredMessage(m, similarity(queryTokens, m.contentString())))
                .sorted(Comparator.comparingDouble(ScoredMessage::score).reversed())
                .limit(topK)
                .map(ScoredMessage::message)
                .toList();
    }

    private double similarity(String[] queryTokens, String text) {
        String lower = text.toLowerCase();
        long matches = 0;
        for (String token : queryTokens) {
            if (lower.contains(token)) matches++;
        }
        return queryTokens.length == 0 ? 0.0 : (double) matches / queryTokens.length;
    }

    @Override
    public synchronized int size() { return messages.size(); }

    @Override
    public synchronized void clear() { messages.clear(); }

    private record ScoredMessage(Message message, double score) {}
}
