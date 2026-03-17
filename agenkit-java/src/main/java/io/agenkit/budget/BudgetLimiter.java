package io.agenkit.budget;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Agent wrapper that enforces a USD cost budget.
 */
public final class BudgetLimiter implements Agent {

    private final Agent inner;
    private final double maxBudgetUsd;
    private final CostTracker costTracker;

    public BudgetLimiter(Agent inner, double maxBudgetUsd, String model) {
        this.inner = inner;
        this.maxBudgetUsd = maxBudgetUsd;
        this.costTracker = new CostTracker(model);
    }

    @Override
    public String getName() { return inner.getName() + "[budget]"; }

    @Override
    public List<String> getCapabilities() { return inner.getCapabilities(); }

    @Override
    public CompletableFuture<Message> process(Message message) {
        if (costTracker.getTotalCostUsd() >= maxBudgetUsd) {
            return CompletableFuture.failedFuture(
                    new RuntimeException("budget exceeded: $" + String.format("%.4f", maxBudgetUsd)
                            + " limit, spent $" + String.format("%.4f", costTracker.getTotalCostUsd())));
        }

        int estimatedInputTokens = message.contentString().length() / 4;
        return inner.process(message).thenApply(response -> {
            int estimatedOutputTokens = response.contentString().length() / 4;
            costTracker.record(estimatedInputTokens, estimatedOutputTokens);
            return response
                    .withMetadata("cost_usd", costTracker.getTotalCostUsd())
                    .withMetadata("budget_remaining",
                            maxBudgetUsd - costTracker.getTotalCostUsd());
        });
    }

    public double getRemainingBudget() {
        return maxBudgetUsd - costTracker.getTotalCostUsd();
    }

    @Override
    public IntrospectionResult introspect() {
        Map<String, Object> state = new HashMap<>();
        state.put("maxBudgetUsd", maxBudgetUsd);
        state.put("spentUsd", costTracker.getTotalCostUsd());
        state.put("remainingUsd", getRemainingBudget());
        return new IntrospectionResult(getName(), getCapabilities(), null, state, null);
    }
}
