package io.agenkit.adapters;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.agenkit.core.Message;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

/**
 * LLM client for the Anthropic Messages API.
 */
public final class AnthropicAdapter implements LlmClient {

    private static final Logger log = LoggerFactory.getLogger(AnthropicAdapter.class);
    private static final String API_URL = "https://api.anthropic.com/v1/messages";
    private static final String ANTHROPIC_VERSION = "2023-06-01";

    private final String apiKey;
    private final String model;
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    public AnthropicAdapter(String apiKey, String model) {
        this.apiKey = apiKey;
        this.model = model;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(30))
                .build();
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public CompletableFuture<Message> complete(List<Message> messages) {
        try {
            // Separate system messages from conversation
            String systemPrompt = messages.stream()
                    .filter(m -> "system".equals(m.getRole()))
                    .map(Message::contentString)
                    .collect(Collectors.joining("\n"));

            List<Message> conversation = messages.stream()
                    .filter(m -> !"system".equals(m.getRole()))
                    .collect(Collectors.toList());

            ObjectNode body = objectMapper.createObjectNode();
            body.put("model", model);
            body.put("max_tokens", 4096);
            if (!systemPrompt.isEmpty()) {
                body.put("system", systemPrompt);
            }

            ArrayNode messagesNode = body.putArray("messages");
            for (Message msg : conversation) {
                ObjectNode msgNode = messagesNode.addObject();
                msgNode.put("role", msg.getRole());
                msgNode.put("content", msg.contentString());
            }

            String requestBody = objectMapper.writeValueAsString(body);
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(API_URL))
                    .header("Content-Type", "application/json")
                    .header("x-api-key", apiKey)
                    .header("anthropic-version", ANTHROPIC_VERSION)
                    .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                    .timeout(Duration.ofSeconds(60))
                    .build();

            return httpClient.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                    .thenApply(response -> {
                        try {
                            JsonNode root = objectMapper.readTree(response.body());
                            String content = root.at("/content/0/text").asText("");
                            return Message.of("assistant", content);
                        } catch (Exception e) {
                            log.error("failed to parse Anthropic response: {}", e.getMessage());
                            return Message.of("assistant", "Error: failed to parse response");
                        }
                    });
        } catch (Exception e) {
            return CompletableFuture.failedFuture(e);
        }
    }

    @Override
    public String getModel() { return model; }
}
