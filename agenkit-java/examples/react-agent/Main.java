package io.agenkit.examples.react;

import io.agenkit.adapters.MockAdapter;
import io.agenkit.core.Message;
import io.agenkit.core.ToolResult;
import io.agenkit.helpers.MockTool;
import io.agenkit.patterns.ReActAgent;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * ReAct (Reasoning + Acting) agent example.
 *
 * Demonstrates tool use with reasoning traces.
 * Run with: mvn exec:java
 */
public class Main {

    public static void main(String[] args) throws Exception {
        // Simulated tools
        MockTool calculator = new MockTool("calculator",
                "performs arithmetic calculations",
                params -> {
                    String input = String.valueOf(params.getOrDefault("input", ""));
                    // Simple mock: return a computed result
                    return ToolResult.ok("Result: " + input.replace("*", "×") + " = 42");
                });

        MockTool search = new MockTool("search",
                "searches for information on a topic",
                params -> {
                    String query = String.valueOf(params.getOrDefault("input", ""));
                    return ToolResult.ok("Search results for '" + query + "': Found 3 relevant articles.");
                });

        // Mock LLM that simulates ReAct behavior
        AtomicInteger step = new AtomicInteger(0);
        MockAdapter llm = new MockAdapter(messages -> {
            int n = step.incrementAndGet();
            return switch (n) {
                case 1 -> "Thought: I need to search for Java information.\nAction: search\nAction Input: Java programming language";
                case 2 -> "Thought: I have search results. Let me calculate something.\nAction: calculator\nAction Input: 6*7";
                default -> "Thought: I have all the information needed.\nFinal Answer: Java is a powerful language. 6\u00d77 = 42.";
            };
        });

        ReActAgent agent = new ReActAgent("react-demo", llm,
                List.of(calculator, search), 5, true);

        System.out.println("=== Agenkit ReAct Agent Example ===");
        System.out.println();

        Message response = agent.process(
                Message.of("user", "Tell me about Java and calculate 6*7")).get();

        System.out.println("Final Answer: " + response.contentString());
        System.out.println("Stop reason: " + response.getMetadata().get("stop_reason"));
        System.out.println("Steps taken: " + response.getMetadata().get("steps"));
        System.out.println();

        System.out.println("=== Reasoning Trace ===");
        for (int i = 0; i < agent.getSteps().size(); i++) {
            var s = agent.getSteps().get(i);
            System.out.printf("Step %d:%n", i + 1);
            System.out.println("  Thought: " + s.getThought());
            if (s.getAction() != null) {
                System.out.println("  Action: " + s.getAction());
                System.out.println("  Input: " + s.getActionInput());
                System.out.println("  Observation: " + s.getObservation());
            }
        }
    }
}
