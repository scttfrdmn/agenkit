package io.agenkit.budget;

import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Tracks cumulative LLM usage costs.
 */
public final class CostTracker {

    private final AtomicLong totalInputTokens = new AtomicLong(0);
    private final AtomicLong totalOutputTokens = new AtomicLong(0);
    private final AtomicReference<Double> totalCostUsd = new AtomicReference<>(0.0);
    private final String model;

    public CostTracker(String model) {
        this.model = model;
    }

    public void record(int inputTokens, int outputTokens) {
        totalInputTokens.addAndGet(inputTokens);
        totalOutputTokens.addAndGet(outputTokens);
        double cost = ModelPricing.calculateCost(model, inputTokens, outputTokens);
        totalCostUsd.updateAndGet(prev -> prev + cost);
    }

    public long getTotalInputTokens() { return totalInputTokens.get(); }
    public long getTotalOutputTokens() { return totalOutputTokens.get(); }
    public double getTotalCostUsd() { return totalCostUsd.get(); }

    public void reset() {
        totalInputTokens.set(0);
        totalOutputTokens.set(0);
        totalCostUsd.set(0.0);
    }
}
