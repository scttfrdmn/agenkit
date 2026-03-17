package io.agenkit.examples.middleware;

import io.agenkit.adapters.MockAdapter;
import io.agenkit.core.Agent;
import io.agenkit.core.Message;
import io.agenkit.middleware.AgentBuilder;
import io.agenkit.middleware.MetricsMiddleware;
import io.agenkit.middleware.RetryMiddleware;
import io.agenkit.patterns.ConversationalAgent;

import java.time.Duration;

/**
 * Middleware composition example.
 *
 * Shows how to compose agents with retry, timeout, caching, and metrics.
 * Run with: mvn exec:java
 */
public class Main {

    public static void main(String[] args) throws Exception {
        MockAdapter llm = new MockAdapter(messages ->
                "Echo: " + (messages.isEmpty() ? "" :
                        messages.get(messages.size() - 1).contentString()));

        ConversationalAgent base = new ConversationalAgent("base", llm);

        // Compose middleware using fluent builder
        MetricsMiddleware metricsLayer = new MetricsMiddleware(base);
        Agent agent = AgentBuilder.wrap(metricsLayer)
                .withRetry(RetryMiddleware.RetryConfig.builder()
                        .maxAttempts(3)
                        .initialDelay(Duration.ofMillis(10))
                        .build())
                .withTimeout(Duration.ofSeconds(10))
                .withCaching(50, Duration.ofMinutes(5))
                .withRateLimit(100)
                .build();

        System.out.println("=== Agenkit Middleware Example ===");
        System.out.println("Agent chain: " + agent.getName());
        System.out.println();

        // Send messages
        String[] messages = {"Hello!", "What can you do?", "Hello!"};  // last is duplicate -> cache hit
        for (String msg : messages) {
            System.out.println("Sending: " + msg);
            Message response = agent.process(Message.of("user", msg)).get();
            System.out.println("Response: " + response.contentString());
            if (response.getMetadata().containsKey("cache_hit")) {
                System.out.println("(cache hit!)");
            }
            if (response.getMetadata().containsKey("latency_ms")) {
                System.out.println("Latency: " + response.getMetadata().get("latency_ms") + "ms");
            }
            System.out.println();
        }

        System.out.println("=== Metrics ===");
        System.out.println("Total requests: " + metricsLayer.getRequestCount());
        System.out.println("Errors: " + metricsLayer.getErrorCount());
        System.out.printf("Avg latency: %.2fms%n", metricsLayer.getAverageLatencyMs());
    }
}
