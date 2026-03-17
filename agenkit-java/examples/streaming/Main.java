package io.agenkit.examples.streaming;

import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;
import io.agenkit.core.StreamingAgent;

import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Flow;
import java.util.concurrent.SubmissionPublisher;

/**
 * Streaming agent example.
 *
 * Demonstrates the StreamingAgent interface with a simulated token stream.
 * Run with: mvn exec:java
 */
public class Main {

    public static void main(String[] args) throws Exception {
        // Create a streaming agent that simulates token-by-token output
        StreamingAgent agent = new SimulatedStreamingAgent();

        System.out.println("=== Agenkit Streaming Example ===");
        System.out.println();
        System.out.print("Streaming response: ");

        CountDownLatch latch = new CountDownLatch(1);
        StringBuilder fullResponse = new StringBuilder();

        // Subscribe to the stream
        Flow.Publisher<Message> publisher = agent.stream(Message.of("user", "Tell me about agents"));
        publisher.subscribe(new Flow.Subscriber<>() {
            private Flow.Subscription subscription;

            @Override
            public void onSubscribe(Flow.Subscription s) {
                this.subscription = s;
                s.request(Long.MAX_VALUE);
            }

            @Override
            public void onNext(Message chunk) {
                String token = chunk.contentString();
                System.out.print(token);
                System.out.flush();
                fullResponse.append(token);
            }

            @Override
            public void onError(Throwable t) {
                System.err.println("\nStream error: " + t.getMessage());
                latch.countDown();
            }

            @Override
            public void onComplete() {
                System.out.println();
                System.out.println();
                System.out.println("=== Stream Complete ===");
                System.out.println("Full response (" + fullResponse.length() + " chars): "
                        + fullResponse);
                latch.countDown();
            }
        });

        latch.await();
    }

    /** A simulated streaming agent that emits tokens with delays. */
    static class SimulatedStreamingAgent implements StreamingAgent {

        private static final String[] TOKENS = {
                "Agents ", "are ", "autonomous ", "programs ", "that ",
                "perceive ", "their ", "environment ", "and ", "take ", "actions."
        };

        @Override
        public String getName() { return "streaming-demo"; }

        @Override
        public List<String> getCapabilities() { return List.of("streaming"); }

        @Override
        public CompletableFuture<Message> process(Message message) {
            return CompletableFuture.completedFuture(
                    Message.of("assistant", String.join("", TOKENS)));
        }

        @Override
        public Flow.Publisher<Message> stream(Message message) {
            SubmissionPublisher<Message> publisher = new SubmissionPublisher<>();
            CompletableFuture.runAsync(() -> {
                try {
                    for (String token : TOKENS) {
                        publisher.submit(Message.of("assistant", token));
                        Thread.sleep(80);
                    }
                    publisher.close();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    publisher.closeExceptionally(e);
                }
            });
            return publisher;
        }

        @Override
        public IntrospectionResult introspect() {
            return new IntrospectionResult(getName(), getCapabilities(), null, null, null);
        }
    }
}
