package io.agenkit.safety;

import io.agenkit.core.Message;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Audit logger that records all agent interactions.
 */
public final class AuditLogger {

    private static final Logger log = LoggerFactory.getLogger(AuditLogger.class);

    public record AuditEntry(
            Instant timestamp,
            String agentName,
            String userId,
            String inputContent,
            String outputContent,
            boolean success) {}

    private final List<AuditEntry> entries = new ArrayList<>();
    private final int maxEntries;

    public AuditLogger(int maxEntries) {
        this.maxEntries = maxEntries;
    }

    public AuditLogger() {
        this(10000);
    }

    public synchronized void log(String agentName, Message input, Message output, boolean success) {
        String userId = (String) input.getMetadata().getOrDefault("user_id", "anonymous");
        AuditEntry entry = new AuditEntry(
                Instant.now(), agentName, userId,
                input.contentString(), output != null ? output.contentString() : "",
                success);

        if (entries.size() >= maxEntries) {
            entries.remove(0);
        }
        entries.add(entry);

        log.info("audit: agent={} user={} success={}", agentName, userId, success);
    }

    public synchronized List<AuditEntry> getEntries() {
        return Collections.unmodifiableList(new ArrayList<>(entries));
    }

    public synchronized List<AuditEntry> getEntriesForAgent(String agentName) {
        return entries.stream()
                .filter(e -> e.agentName().equals(agentName))
                .toList();
    }
}
