package io.agenkit.composition;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Predicate;

/**
 * Routes messages to different agents based on predicates.
 */
public final class ConditionalAgent implements Agent {

    private final String name;
    private final List<Branch> branches;
    private final Agent fallback;

    public ConditionalAgent(String name, List<Branch> branches, Agent fallback) {
        this.name = name;
        this.branches = List.copyOf(branches);
        this.fallback = fallback;
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("conditional_routing", "predicate_dispatch");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        for (Branch branch : branches) {
            if (branch.predicate().test(message)) {
                return branch.agent().process(message)
                        .thenApply(r -> r.withMetadata("matched_branch", branch.label()));
            }
        }
        if (fallback != null) {
            return fallback.process(message)
                    .thenApply(r -> r.withMetadata("matched_branch", "fallback"));
        }
        return CompletableFuture.completedFuture(
                Message.of("assistant", "No branch matched for: " + message.contentString())
                        .withMetadata("matched_branch", "none"));
    }

    @Override
    public IntrospectionResult introspect() {
        List<String> branchLabels = branches.stream().map(Branch::label).toList();
        Map<String, Object> state = new HashMap<>();
        state.put("branchCount", branches.size());
        state.put("hasFallback", fallback != null);
        return new IntrospectionResult(name, getCapabilities(), null, state, branchLabels);
    }

    public record Branch(String label, Predicate<Message> predicate, Agent agent) {}
}
