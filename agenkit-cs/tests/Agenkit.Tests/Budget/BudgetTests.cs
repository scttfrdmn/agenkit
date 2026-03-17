using Agenkit.Budget;
using Agenkit.Core;
using Agenkit.Tests.Helpers;

namespace Agenkit.Tests.Budget;

public class ModelPricingTests
{
    [Fact]
    public void CalculateCost_KnownModel_ReturnsPositiveCost()
    {
        var cost = ModelPricing.CalculateCost("gpt-4o", 1000, 500);
        cost.Should().BeGreaterThan(0);
    }

    [Fact]
    public void CalculateCost_UnknownModel_ReturnsZero()
    {
        var cost = ModelPricing.CalculateCost("unknown-model", 1000, 500);
        cost.Should().Be(0m);
    }

    [Fact]
    public void KnownModels_ContainsExpectedModels()
    {
        ModelPricing.KnownModels.Should().Contain("gpt-4o");
        ModelPricing.KnownModels.Should().Contain("claude-3-5-sonnet-20241022");
    }
}

public class CostTrackerTests
{
    [Fact]
    public void Record_UpdatesTotals()
    {
        var tracker = new CostTracker("gpt-4o");
        tracker.Record(100, 50);
        tracker.TotalInputTokens.Should().Be(100);
        tracker.TotalOutputTokens.Should().Be(50);
        tracker.TotalCostUsd.Should().BeGreaterThan(0);
    }

    [Fact]
    public void Reset_ClearsAllCounters()
    {
        var tracker = new CostTracker("gpt-4o");
        tracker.Record(100, 50);
        tracker.Reset();
        tracker.TotalInputTokens.Should().Be(0);
        tracker.TotalCostUsd.Should().Be(0m);
    }

    [Fact]
    public void Record_MultipleRequests_Accumulates()
    {
        var tracker = new CostTracker("gpt-4o");
        tracker.Record(100, 50);
        tracker.Record(200, 100);
        tracker.TotalInputTokens.Should().Be(300);
    }
}

public class BudgetLimiterTests
{
    [Fact]
    public async Task ProcessAsync_WithinBudget_Succeeds()
    {
        var tracker = new CostTracker("gpt-4o");
        var limiter = new BudgetLimiter(new MockAgent("ok"), tracker, 10.00m);
        var response = await limiter.ProcessAsync(Message.NewMessage("user", "test"));
        response.ContentString().Should().Be("ok");
    }

    [Fact]
    public async Task ProcessAsync_BudgetExhausted_Throws()
    {
        var tracker = new CostTracker("gpt-4o");
        // Start with a near-zero budget
        tracker.Record(100000, 100000); // exhaust budget
        var limiter = new BudgetLimiter(new MockAgent("ok"), tracker, 0.001m);

        await limiter.Invoking(l => l.ProcessAsync(Message.NewMessage("user", "test")))
            .Should().ThrowAsync<InvalidOperationException>()
            .WithMessage("*budget*");
    }

    [Fact]
    public void Constructor_NegativeBudget_Throws()
    {
        var act = () => new BudgetLimiter(new MockAgent(), new CostTracker("gpt-4o"), -1m);
        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public void Introspect_ReturnsRemainingBudget()
    {
        var limiter = new BudgetLimiter(new MockAgent(), new CostTracker("gpt-4o"), 5.0m);
        var result = limiter.Introspect();
        result.State.Should().ContainKey("remaining_usd");
    }
}
