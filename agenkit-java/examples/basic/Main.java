package io.agenkit.examples.basic;

import io.agenkit.adapters.MockAdapter;
import io.agenkit.core.Message;
import io.agenkit.patterns.ConversationalAgent;

/**
 * Basic example: a simple conversational agent.
 *
 * Run with: mvn exec:java
 */
public class Main {

    public static void main(String[] args) throws Exception {
        // Use MockAdapter for demonstration (replace with OpenAiAdapter for real use)
        MockAdapter llm = new MockAdapter(messages -> {
            String lastMsg = messages.isEmpty() ? "" :
                    messages.get(messages.size() - 1).contentString();
            return "I received your message: '" + lastMsg + "'. How can I help you further?";
        });

        ConversationalAgent agent = new ConversationalAgent(
                "assistant",
                llm,
                "You are a helpful, friendly assistant.",
                10);

        System.out.println("=== Agenkit Basic Example ===");
        System.out.println("Agent: " + agent.getName());
        System.out.println("Capabilities: " + agent.getCapabilities());
        System.out.println();

        // Simulate a conversation
        String[] userMessages = {
                "Hello! Can you help me?",
                "What can you do?",
                "Tell me about Java agents."
        };

        for (String userMsg : userMessages) {
            System.out.println("User: " + userMsg);
            Message response = agent.process(Message.of("user", userMsg)).get();
            System.out.println("Agent: " + response.contentString());
            System.out.println();
        }

        // Show introspection
        var state = agent.introspect();
        System.out.println("=== Agent State ===");
        System.out.println("History size: " + state.getState().get("historySize"));
    }
}
