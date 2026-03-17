package io.agenkit.patterns;

import io.agenkit.adapters.LlmClient;
import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Function;

/**
 * An agent that requests human approval before executing actions.
 */
public final class HumanInLoopAgent implements Agent {

    private final String name;
    private final LlmClient llmClient;
    private final Function<String, CompletableFuture<Boolean>> approvalHandler;

    public HumanInLoopAgent(
            String name,
            LlmClient llmClient,
            Function<String, CompletableFuture<Boolean>> approvalHandler) {
        this.name = name;
        this.llmClient = llmClient;
        this.approvalHandler = approvalHandler;
    }

    /** Creates an agent that auto-approves all actions (useful for testing). */
    public static HumanInLoopAgent autoApprove(String name, LlmClient llmClient) {
        return new HumanInLoopAgent(name, llmClient,
                action -> CompletableFuture.completedFuture(true));
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("human_in_loop", "approval_gate");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        return llmClient.complete(List.of(
                Message.of("system", "Propose an action to handle the request. Start with 'Action: '"),
                message))
                .thenCompose(proposal -> {
                    String proposedAction = proposal.contentString();
                    return approvalHandler.apply(proposedAction)
                            .thenCompose(approved -> {
                                if (!approved) {
                                    return CompletableFuture.completedFuture(
                                            Message.of("assistant", "Action rejected by human review: "
                                                    + proposedAction)
                                                    .withMetadata("approved", false));
                                }
                                return llmClient.complete(List.of(
                                        Message.of("system", "The human approved your action. Execute it and report results."),
                                        message,
                                        Message.of("assistant", proposedAction),
                                        Message.of("user", "Approved. Please proceed.")))
                                        .thenApply(result -> result.withMetadata("approved", true));
                            });
                });
    }

    @Override
    public IntrospectionResult introspect() {
        return new IntrospectionResult(name, getCapabilities(), null, null, null);
    }
}
