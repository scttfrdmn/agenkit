package io.agenkit.patterns;

import io.agenkit.adapters.LlmClient;
import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import io.agenkit.core.Tool;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * An agent that interleaves step-by-step reasoning with tool invocations.
 */
public final class ReasoningWithToolsAgent implements Agent {

    private final String name;
    private final LlmClient llmClient;
    private final List<Tool> tools;
    private final int maxSteps;

    public ReasoningWithToolsAgent(String name, LlmClient llmClient, List<Tool> tools, int maxSteps) {
        this.name = name;
        this.llmClient = llmClient;
        this.tools = List.copyOf(tools);
        this.maxSteps = maxSteps;
    }

    public ReasoningWithToolsAgent(String name, LlmClient llmClient, List<Tool> tools) {
        this(name, llmClient, tools, 8);
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("reasoning", "tool_use", "chain_of_thought");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        return reason(message, new ArrayList<>(), 0);
    }

    private CompletableFuture<Message> reason(Message original, List<String> chain, int step) {
        if (step >= maxSteps) {
            return CompletableFuture.completedFuture(
                    Message.of("assistant", String.join("\n", chain))
                            .withMetadata("steps", step)
                            .withMetadata("stopped", "max_steps"));
        }

        StringBuilder toolsDesc = new StringBuilder();
        for (Tool tool : tools) {
            toolsDesc.append("- ").append(tool.getName())
                    .append(": ").append(tool.getDescription()).append("\n");
        }

        String context = "Question: " + original.contentString()
                + (chain.isEmpty() ? "" : "\n\nReasoning so far:\n" + String.join("\n", chain));

        return llmClient.complete(List.of(
                Message.of("system", "Reason step by step. Available tools:\n" + toolsDesc
                        + "\nFormat: THINK: reasoning\nUSE_TOOL: tool_name INPUT: input\nOR: ANSWER: final answer"),
                Message.of("user", context)))
                .thenCompose(response -> {
                    String text = response.contentString();

                    if (text.contains("ANSWER:")) {
                        String answer = text.substring(text.indexOf("ANSWER:") + 7).trim();
                        return CompletableFuture.completedFuture(
                                Message.of("assistant", answer)
                                        .withMetadata("steps", step + 1)
                                        .withMetadata("reasoning_chain", chain.size()));
                    }

                    if (text.contains("USE_TOOL:")) {
                        String toolPart = text.substring(text.indexOf("USE_TOOL:") + 9);
                        String toolName = toolPart.split("INPUT:")[0].trim();
                        String input = toolPart.contains("INPUT:")
                                ? toolPart.substring(toolPart.indexOf("INPUT:") + 6).trim() : "";

                        Tool tool = tools.stream()
                                .filter(t -> t.getName().equalsIgnoreCase(toolName))
                                .findFirst().orElse(null);

                        if (tool != null) {
                            Map<String, Object> params = new HashMap<>();
                            params.put("input", input);
                            return tool.execute(params).thenCompose(result -> {
                                List<String> newChain = new ArrayList<>(chain);
                                newChain.add(text);
                                newChain.add("Tool result: " + result.getData());
                                return reason(original, newChain, step + 1);
                            });
                        }
                    }

                    List<String> newChain = new ArrayList<>(chain);
                    newChain.add(text);
                    return reason(original, newChain, step + 1);
                });
    }

    @Override
    public IntrospectionResult introspect() {
        List<String> toolNames = tools.stream().map(Tool::getName).toList();
        Map<String, Object> state = new HashMap<>();
        state.put("maxSteps", maxSteps);
        return new IntrospectionResult(name, getCapabilities(), null, state, toolNames);
    }
}
