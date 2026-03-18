package io.agenkit.budget;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

class BudgetManagerTest {

    @Test
    void processSucceedsWithinBudget() throws Exception {
        MockAgent inner = new MockAgent("agent", "response");
        BudgetLimiter limiter = new BudgetLimiter(inner, 1.0, "gpt-4o-mini");

        Message response = limiter.process(Message.of("user", "hello")).get();
        assertThat(response.contentString()).isEqualTo("response");
    }

    @Test
    void responseIncludesCostMetadata() throws Exception {
        MockAgent inner = new MockAgent("agent", "result");
        BudgetLimiter limiter = new BudgetLimiter(inner, 1.0, "gpt-4o-mini");

        Message response = limiter.process(Message.of("user", "test input")).get();
        assertThat(response.getMetadata()).containsKey("cost_usd");
        assertThat(response.getMetadata()).containsKey("budget_remaining");
    }

    @Test
    void getNameIncludesBudgetSuffix() {
        MockAgent inner = new MockAgent("my-agent");
        BudgetLimiter limiter = new BudgetLimiter(inner, 0.5, "gpt-4o-mini");
        assertThat(limiter.getName()).contains("budget");
    }

    @Test
    void remainingBudgetStartsAtMax() {
        MockAgent inner = new MockAgent("agent", "ok");
        BudgetLimiter limiter = new BudgetLimiter(inner, 2.0, "gpt-4o-mini");
        assertThat(limiter.getRemainingBudget()).isEqualTo(2.0);
    }

    @Test
    void remainingBudgetDecreasesAfterCall() throws Exception {
        MockAgent inner = new MockAgent("agent", "ok");
        BudgetLimiter limiter = new BudgetLimiter(inner, 1.0, "gpt-4o-mini");

        limiter.process(Message.of("user", "hello world")).get();

        assertThat(limiter.getRemainingBudget()).isLessThan(1.0);
    }

    @Test
    void exceedingBudgetThrowsException() throws Exception {
        MockAgent inner = new MockAgent("agent", "costly");
        // Extremely small budget
        BudgetLimiter limiter = new BudgetLimiter(inner, 0.0, "gpt-4o");

        assertThatThrownBy(() -> limiter.process(Message.of("user", "query")).get())
                .hasCauseInstanceOf(RuntimeException.class)
                .hasMessageContaining("budget");
    }

    @Test
    void introspectIncludesBudgetState() {
        MockAgent inner = new MockAgent("agent", "ok");
        BudgetLimiter limiter = new BudgetLimiter(inner, 5.0, "gpt-4o-mini");
        var state = limiter.introspect().getState();
        assertThat(state).containsKey("maxBudgetUsd");
        assertThat(state).containsKey("spentUsd");
        assertThat(state).containsKey("remainingUsd");
    }

    @Test
    void costTrackerStartsAtZero() {
        CostTracker tracker = new CostTracker("gpt-4o-mini");
        assertThat(tracker.getTotalCostUsd()).isEqualTo(0.0);
        assertThat(tracker.getTotalInputTokens()).isEqualTo(0L);
        assertThat(tracker.getTotalOutputTokens()).isEqualTo(0L);
    }

    @Test
    void costTrackerRecordsTokens() {
        CostTracker tracker = new CostTracker("gpt-4o-mini");
        tracker.record(1000, 500);
        assertThat(tracker.getTotalInputTokens()).isEqualTo(1000L);
        assertThat(tracker.getTotalOutputTokens()).isEqualTo(500L);
        assertThat(tracker.getTotalCostUsd()).isGreaterThan(0.0);
    }

    @Test
    void costTrackerResetClearsAllCounters() {
        CostTracker tracker = new CostTracker("gpt-4o-mini");
        tracker.record(2000, 1000);
        tracker.reset();
        assertThat(tracker.getTotalCostUsd()).isEqualTo(0.0);
        assertThat(tracker.getTotalInputTokens()).isEqualTo(0L);
        assertThat(tracker.getTotalOutputTokens()).isEqualTo(0L);
    }
}
