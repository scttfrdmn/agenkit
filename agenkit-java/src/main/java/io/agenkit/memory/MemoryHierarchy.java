package io.agenkit.memory;

import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.List;

/**
 * Three-tier memory hierarchy: working (short-term), episodic (medium-term), semantic (long-term).
 */
public final class MemoryHierarchy implements Memory {

    private final Memory working;    // short-term, small capacity
    private final Memory episodic;   // medium-term
    private final Memory semantic;   // long-term, larger capacity
    private final int workingThreshold;

    public MemoryHierarchy(Memory working, Memory episodic, Memory semantic, int workingThreshold) {
        this.working = working;
        this.episodic = episodic;
        this.semantic = semantic;
        this.workingThreshold = workingThreshold;
    }

    public MemoryHierarchy() {
        this(new EphemeralMemory(20), new EphemeralMemory(200), new EphemeralMemory(2000), 20);
    }

    @Override
    public void store(Message message) {
        working.store(message);
        episodic.store(message);
        semantic.store(message);

        // Consolidate working memory if full
        if (working.size() >= workingThreshold) {
            working.clear();
        }
    }

    @Override
    public List<Message> retrieve(String query, int topK) {
        List<Message> results = new ArrayList<>();
        // Prioritize working memory, then episodic, then semantic
        results.addAll(working.retrieve(query, Math.min(topK, 2)));
        if (results.size() < topK) {
            results.addAll(episodic.retrieve(query, topK - results.size()));
        }
        if (results.size() < topK) {
            results.addAll(semantic.retrieve(query, topK - results.size()));
        }
        return results.subList(0, Math.min(topK, results.size()));
    }

    @Override
    public int size() { return semantic.size(); }

    @Override
    public void clear() {
        working.clear();
        episodic.clear();
        semantic.clear();
    }

    public Memory getWorking() { return working; }
    public Memory getEpisodic() { return episodic; }
    public Memory getSemantic() { return semantic; }
}
