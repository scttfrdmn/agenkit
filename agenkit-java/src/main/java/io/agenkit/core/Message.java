package io.agenkit.core;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/**
 * Immutable message exchanged between agents and users.
 */
public final class Message {

    private static final Set<String> ALLOWED_ROLES = Set.of(
            "user", "assistant", "system", "tool", "agent");
    private static final int MAX_CONTENT_BYTES = 16 * 1024 * 1024; // 16 MB
    private static final int MAX_METADATA_KEYS = 100;
    private static final int MAX_KEY_LENGTH = 50;
    private static final int MAX_ROLE_LENGTH = 20;

    private final String role;
    private final Object content;
    private final Map<String, Object> metadata;
    private final Instant timestamp;

    public Message(String role, Object content, Map<String, Object> metadata, Instant timestamp) {
        this.role = role;
        this.content = content;
        this.metadata = metadata != null
                ? Collections.unmodifiableMap(new HashMap<>(metadata))
                : Collections.emptyMap();
        this.timestamp = timestamp != null ? timestamp : Instant.now();
    }

    /** Factory: create a simple user/assistant message. */
    public static Message of(String role, String content) {
        return new Message(role, content, Collections.emptyMap(), Instant.now());
    }

    /** Returns content as a String, or empty string if null. */
    public String contentString() {
        if (content == null) return "";
        if (content instanceof String s) return s;
        return content.toString();
    }

    /** Returns a copy of this message with an additional metadata entry. */
    public Message withMetadata(String key, Object value) {
        Map<String, Object> newMeta = new HashMap<>(this.metadata);
        newMeta.put(key, value);
        return new Message(role, content, newMeta, timestamp);
    }

    /** Validates this message and returns it; throws IllegalArgumentException on failure. */
    public Message validate() {
        if (role == null || role.isEmpty()) {
            throw new IllegalArgumentException("message role cannot be empty");
        }
        if (role.length() > MAX_ROLE_LENGTH) {
            throw new IllegalArgumentException(
                    "message role exceeds maximum length of " + MAX_ROLE_LENGTH
                            + " characters (got " + role.length() + ")");
        }
        if (!ALLOWED_ROLES.contains(role)) {
            throw new IllegalArgumentException(
                    "invalid message role: " + role
                            + ". Must be one of: user, assistant, system, tool, agent");
        }

        String contentStr = contentString();
        int contentSize = contentStr.getBytes(StandardCharsets.UTF_8).length;
        if (contentSize > MAX_CONTENT_BYTES) {
            throw new IllegalArgumentException(
                    "message content exceeds maximum size of " + MAX_CONTENT_BYTES
                            + " bytes (got " + contentSize + " bytes)");
        }

        if (metadata.size() > MAX_METADATA_KEYS) {
            throw new IllegalArgumentException(
                    "message metadata exceeds maximum of " + MAX_METADATA_KEYS
                            + " keys (got " + metadata.size() + ")");
        }
        for (Map.Entry<String, Object> entry : metadata.entrySet()) {
            String key = entry.getKey();
            if (key.length() > MAX_KEY_LENGTH) {
                throw new IllegalArgumentException(
                        "metadata key '" + key.substring(0, Math.min(20, key.length()))
                                + "...' exceeds maximum length of " + MAX_KEY_LENGTH
                                + " characters (got " + key.length() + ")");
            }
        }
        return this;
    }

    public String getRole() { return role; }
    public Object getContent() { return content; }
    public Map<String, Object> getMetadata() { return metadata; }
    public Instant getTimestamp() { return timestamp; }

    @Override
    public String toString() {
        return "Message{role='" + role + "', content='" + contentString() + "'}";
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Message m)) return false;
        return role.equals(m.role)
                && java.util.Objects.equals(content, m.content)
                && metadata.equals(m.metadata)
                && timestamp.equals(m.timestamp);
    }

    @Override
    public int hashCode() {
        return java.util.Objects.hash(role, content, metadata, timestamp);
    }
}
