package io.agenkit.safety;

import io.agenkit.core.Message;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Detects anomalous usage patterns (e.g., rapid repeated calls).
 */
public final class AnomalyDetector {

    private static final Logger log = LoggerFactory.getLogger(AnomalyDetector.class);

    private final int maxRequestsPerWindow;
    private final Duration window;
    private final Map<String, List<Instant>> requestHistory = new ConcurrentHashMap<>();
    private final AtomicInteger anomalyCount = new AtomicInteger(0);

    public AnomalyDetector(int maxRequestsPerWindow, Duration window) {
        this.maxRequestsPerWindow = maxRequestsPerWindow;
        this.window = window;
    }

    public AnomalyDetector() {
        this(100, Duration.ofMinutes(1));
    }

    public boolean isAnomaly(Message message) {
        String userId = (String) message.getMetadata().getOrDefault("user_id", "anonymous");
        Instant now = Instant.now();

        List<Instant> history = requestHistory.computeIfAbsent(userId, k -> new ArrayList<>());
        synchronized (history) {
            history.removeIf(t -> t.isBefore(now.minus(window)));
            history.add(now);

            if (history.size() > maxRequestsPerWindow) {
                anomalyCount.incrementAndGet();
                log.warn("anomaly detected for user={}: {} requests in window", userId, history.size());
                return true;
            }
        }
        return false;
    }

    public int getAnomalyCount() { return anomalyCount.get(); }
}
