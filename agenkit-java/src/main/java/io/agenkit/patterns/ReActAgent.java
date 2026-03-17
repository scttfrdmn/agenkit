package io.agenkit.patterns;

import io.agenkit.adapters.LlmClient;
import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import io.agenkit.core.Tool;
import io.agenkit.core.ToolResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * ReAct (Reasoning + Acting) agent that interleaves reasoning and tool use.
 */
public final class ReActAgent implements Agent {

    private static final Logger log = LoggerFactory.getLogger(ReActAgent.class);

    private final String name;
    private final LlmClient llmClient;
    private final List<Tool> tools;
    private final int maxSteps;
    private final boolean verbose;
    private final List<ReActStep> steps = new ArrayList<>();

    public ReActAgent(String name, LlmClient llmClient, List<Tool> tools, int maxSteps, boolean verbose) {
        this.name = name;
        this.llmClient = llmClient;
        this.tools = List.copyOf(tools);
        this.maxSteps = maxSteps;
        this.verbose = verbose;
    }

    public ReActAgent(String name, LlmClient llmClient, List<Tool> tools) {
        this(name, llmClient, tools, 10, false);
    }

    @Override
    public String getName() { return name; }

    @Override
    public List<String> getCapabilities() {
        return List.of("reasoning", "tool_use");
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        steps.clear();
        return runLoop(message, new ArrayList<>(), 0);
    }

    private CompletableFuture<Message> runLoop(Message original, List<Message> history, int step) {
        if (step >= maxSteps) {
            String finalAnswer = "Reached maximum steps (" + maxSteps + "). Last reasoning complete.";
            return CompletableFuture.completedFuture(
                    Message.of("assistant", finalAnswer)
                            .withMetadata("stop_reason", "max_steps")
                            .withMetadata("steps", step));
        }

        List<Message> messages = new ArrayList<>();
        messages.add(Message.of("system", buildSystemPrompt()));
        messages.add(original);
        messages.addAll(history);

        return llmClient.complete(messages).thenCompose(response -> {
            String text = response.contentString();
            if (verbose) {
                log.info("[ReActAgent] step={} response={}", step, text);
            }

            ParsedResponse parsed = parseResponse(text);

            if (parsed.isFinalAnswer()) {
                steps.add(new ReActStep(parsed.thought, null, null, null, true));
                return CompletableFuture.completedFuture(
                        Message.of("assistant", parsed.finalAnswer)
                                .withMetadata("stop_reason", "final_answer")
                                .withMetadata("steps", step + 1));
            }

            // Execute tool
            steps.add(new ReActStep(parsed.thought, parsed.action, parsed.actionInput, null, false));
            Tool tool = findTool(parsed.action);
            if (tool == null) {
                String observation = "Error: tool '" + parsed.action + "' not found";
                steps.get(steps.size() - 1).setObservation(observation);
                List<Message> newHistory = new ArrayList<>(history);
                newHistory.add(response);
                newHistory.add(Message.of("user", "Observation: " + observation));
                return runLoop(original, newHistory, step + 1);
            }

            Map<String, Object> params = new HashMap<>();
            params.put("input", parsed.actionInput);

            return tool.execute(params).thenCompose(toolResult -> {
                String observation = toolResult.isSuccess()
                        ? String.valueOf(toolResult.getData())
                        : "Error: " + toolResult.getError();
                steps.get(steps.size() - 1).setObservation(observation);

                List<Message> newHistory = new ArrayList<>(history);
                newHistory.add(response);
                newHistory.add(Message.of("user", "Observation: " + observation));
                return runLoop(original, newHistory, step + 1);
            });
        });
    }

    private String buildSystemPrompt() {
        StringBuilder sb = new StringBuilder();
        sb.append("You are a helpful assistant with access to tools.\n\n");
        sb.append("Available tools:\n");
        for (Tool tool : tools) {
            sb.append("- ").append(tool.getName()).append(": ").append(tool.getDescription()).append("\n");
        }
        sb.append("\nUse this format:\n");
        sb.append("Thought: reason about what to do\n");
        sb.append("Action: tool_name\n");
        sb.append("Action Input: input for the tool\n");
        sb.append("OR if you have the final answer:\n");
        sb.append("Thought: I have the answer\n");
        sb.append("Final Answer: your answer here\n");
        return sb.toString();
    }

    private ParsedResponse parseResponse(String text) {
        String thought = "";
        String action = null;
        String actionInput = null;
        String finalAnswer = null;

        for (String line : text.split("\n")) {
            String trimmed = line.trim();
            if (trimmed.startsWith("Thought:")) {
                thought = trimmed.substring("Thought:".length()).trim();
            } else if (trimmed.startsWith("Action:")) {
                action = trimmed.substring("Action:".length()).trim();
            } else if (trimmed.startsWith("Action Input:")) {
                actionInput = trimmed.substring("Action Input:".length()).trim();
            } else if (trimmed.startsWith("Final Answer:")) {
                finalAnswer = trimmed.substring("Final Answer:".length()).trim();
            }
        }

        return new ParsedResponse(thought, action, actionInput, finalAnswer);
    }

    private Tool findTool(String name) {
        if (name == null) return null;
        return tools.stream()
                .filter(t -> t.getName().equalsIgnoreCase(name))
                .findFirst()
                .orElse(null);
    }

    public List<ReActStep> getSteps() { return Collections.unmodifiableList(steps); }

    @Override
    public IntrospectionResult introspect() {
        List<String> toolNames = tools.stream().map(Tool::getName).toList();
        Map<String, Object> state = new HashMap<>();
        state.put("maxSteps", maxSteps);
        state.put("stepsTaken", steps.size());
        return new IntrospectionResult(name, getCapabilities(), null, state, toolNames);
    }

    public static final class ReActStep {
        private final String thought;
        private final String action;
        private final String actionInput;
        private String observation;
        private final boolean isFinal;

        public ReActStep(String thought, String action, String actionInput,
                         String observation, boolean isFinal) {
            this.thought = thought;
            this.action = action;
            this.actionInput = actionInput;
            this.observation = observation;
            this.isFinal = isFinal;
        }

        public void setObservation(String observation) { this.observation = observation; }

        public String getThought() { return thought; }
        public String getAction() { return action; }
        public String getActionInput() { return actionInput; }
        public String getObservation() { return observation; }
        public boolean isFinal() { return isFinal; }
    }

    private static final class ParsedResponse {
        final String thought;
        final String action;
        final String actionInput;
        final String finalAnswer;

        ParsedResponse(String thought, String action, String actionInput, String finalAnswer) {
            this.thought = thought;
            this.action = action;
            this.actionInput = actionInput;
            this.finalAnswer = finalAnswer;
        }

        boolean isFinalAnswer() { return finalAnswer != null; }
    }
}
