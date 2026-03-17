package io.agenkit.patterns;

import io.agenkit.adapters.LlmClient;
import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * An agent that reaches consensus by polling multiple peers.
 */
public final class CollaborativeAgent implements Agent {

    private final String name;
    private final LlmClient llmClient;
    private final List<Agent> peers;
    private final int minConsensus;

    public CollaborativeAgent(String name, LlmClient llmClient, List<Agent> peers) {
        this.name = name;
        this.llmClient = llmClient;
        this.peers = List.copyOf(peers);
        this.minConsensus = (peers.size() / 2) + 1;
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("collaboration", "consensus");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        List<CompletableFuture<Message>> peerResponses = peers.stream()
                .map(peer -> peer.process(message))
                .toList();

        return CompletableFuture.allOf(peerResponses.toArray(new CompletableFuture[0]))
                .thenCompose(v -> {
                    List<String> opinions = peerResponses.stream()
                            .map(f -> f.join().contentString())
                            .toList();

                    String synthesisPrompt = "Synthesize these responses into a consensus:\n"
                            + String.join("\n---\n", opinions);
                    return llmClient.complete(List.of(
                            Message.of("system", "Synthesize peer responses into a final consensus answer."),
                            Message.of("user", synthesisPrompt)))
                            .thenApply(response -> response
                                    .withMetadata("peer_count", peers.size())
                                    .withMetadata("consensus_threshold", minConsensus));
                });
    }

    @Override
    public IntrospectionResult introspect() {
        List<String> peerNames = peers.stream().map(Agent::getName).toList();
        Map<String, Object> state = new HashMap<>();
        state.put("peerCount", peers.size());
        state.put("minConsensus", minConsensus);
        return new IntrospectionResult(name, getCapabilities(), null, state, peerNames);
    }
}
