using System.Diagnostics;
using Agenkit.Core;

namespace Agenkit.Evaluation;

/// <summary>
/// Benchmark result for a single run.
/// </summary>
public record BenchmarkResult(
    string Name,
    int Iterations,
    TimeSpan TotalTime,
    TimeSpan AverageTime,
    TimeSpan MinTime,
    TimeSpan MaxTime,
    int Errors);

/// <summary>
/// Runs benchmark suites against agents.
/// </summary>
public class Benchmark
{
    private readonly IAgent _agent;

    /// <summary>Creates a new Benchmark for the given agent.</summary>
    public Benchmark(IAgent agent) => _agent = agent;

    /// <summary>
    /// Runs a benchmark by sending the given message repeatedly.
    /// </summary>
    /// <param name="name">Benchmark name.</param>
    /// <param name="message">Message to send each iteration.</param>
    /// <param name="iterations">Number of iterations.</param>
    /// <param name="ct">Cancellation token.</param>
    public async Task<BenchmarkResult> RunAsync(
        string name,
        Message message,
        int iterations = 10,
        CancellationToken ct = default)
    {
        var times = new List<TimeSpan>(iterations);
        int errors = 0;

        for (int i = 0; i < iterations; i++)
        {
            ct.ThrowIfCancellationRequested();
            var sw = Stopwatch.StartNew();
            try
            {
                await _agent.ProcessAsync(message, ct).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                throw;
            }
            catch
            {
                errors++;
            }
            finally
            {
                sw.Stop();
                times.Add(sw.Elapsed);
            }
        }

        var total = TimeSpan.FromTicks(times.Sum(t => t.Ticks));
        var avg = TimeSpan.FromTicks(total.Ticks / iterations);
        var min = times.Min();
        var max = times.Max();

        return new BenchmarkResult(name, iterations, total, avg, min, max, errors);
    }
}
