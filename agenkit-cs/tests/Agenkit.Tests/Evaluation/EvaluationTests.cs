using Agenkit.Core;
using Agenkit.Evaluation;
using Agenkit.Tests.Helpers;

namespace Agenkit.Tests.Evaluation;

public class MetricTests
{
    [Fact]
    public void Metric_StoresFields()
    {
        var m = new Metric("accuracy", 0.95, "%");
        m.Name.Should().Be("accuracy");
        m.Value.Should().Be(0.95);
        m.Unit.Should().Be("%");
    }

    [Fact]
    public void Metric_ToString_IncludesNameAndValue()
    {
        var m = new Metric("latency", 42.5, "ms");
        m.ToString().Should().Contain("latency");
        m.ToString().Should().Contain("42.5");
    }

    [Fact]
    public void Metric_WithoutUnit_ToStringSkipsUnit()
    {
        var m = new Metric("score", 1.0);
        m.ToString().Should().NotContain("ms");
    }
}

public class EvaluatorTests
{
    [Fact]
    public async Task RunAsync_SingleCase_ReturnsMetric()
    {
        var agent = new MockAgent("yes");
        var evaluator = new Evaluator(agent);
        evaluator.AddCase("test", Message.NewMessage("user", "q"),
            m => new Metric("contains_yes", m.ContentString().Contains("yes") ? 1.0 : 0.0));

        var results = await evaluator.RunAsync();
        results.Should().HaveCount(1);
        results[0].Value.Should().Be(1.0);
    }

    [Fact]
    public async Task RunAsync_MultipleCases_ReturnsAll()
    {
        var agent = new MockAgent("response");
        var evaluator = new Evaluator(agent);
        evaluator.AddCase("c1", Message.NewMessage("user", "q1"), _ => new Metric("m1", 1.0));
        evaluator.AddCase("c2", Message.NewMessage("user", "q2"), _ => new Metric("m2", 2.0));

        var results = await evaluator.RunAsync();
        results.Should().HaveCount(2);
    }
}

public class BenchmarkTests
{
    [Fact]
    public async Task RunAsync_ReturnsResults()
    {
        var agent = new MockAgent("ok");
        var bench = new Benchmark(agent);
        var result = await bench.RunAsync("test", Message.NewMessage("user", "test"), iterations: 5);
        result.Name.Should().Be("test");
        result.Iterations.Should().Be(5);
        result.Errors.Should().Be(0);
    }

    [Fact]
    public async Task RunAsync_CountsErrors()
    {
        var agent = new MockAgent(exception: new Exception("fail"));
        var bench = new Benchmark(agent);
        var result = await bench.RunAsync("test", Message.NewMessage("user", "test"), iterations: 3);
        result.Errors.Should().Be(3);
    }

    [Fact]
    public async Task RunAsync_AverageTime_IsPositive()
    {
        var agent = new MockAgent("ok");
        var bench = new Benchmark(agent);
        var result = await bench.RunAsync("test", Message.NewMessage("user", "test"), iterations: 3);
        result.AverageTime.Should().BeGreaterThan(TimeSpan.Zero);
    }
}
