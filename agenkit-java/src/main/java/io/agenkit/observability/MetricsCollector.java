package io.agenkit.observability;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Collects agent metrics for monitoring.
 */
public final class MetricsCollector {

    private final Map<String, AtomicLong> counters = new ConcurrentHashMap<>();
    private final Map<String, List<Double>> histograms = new ConcurrentHashMap<>();

    public void increment(String metric) {
        counters.computeIfAbsent(metric, k -> new AtomicLong(0)).incrementAndGet();
    }

    public void increment(String metric, long amount) {
        counters.computeIfAbsent(metric, k -> new AtomicLong(0)).addAndGet(amount);
    }

    public void record(String metric, double value) {
        histograms.computeIfAbsent(metric, k ->
                Collections.synchronizedList(new ArrayList<>())).add(value);
    }

    public long getCount(String metric) {
        AtomicLong counter = counters.get(metric);
        return counter != null ? counter.get() : 0;
    }

    public double getAverage(String metric) {
        List<Double> values = histograms.get(metric);
        if (values == null || values.isEmpty()) return 0.0;
        synchronized (values) {
            return values.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
        }
    }

    public Map<String, Long> getAllCounters() {
        Map<String, Long> result = new ConcurrentHashMap<>();
        counters.forEach((k, v) -> result.put(k, v.get()));
        return Collections.unmodifiableMap(result);
    }
}
