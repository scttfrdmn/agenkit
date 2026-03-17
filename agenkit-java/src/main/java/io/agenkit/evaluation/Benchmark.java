package io.agenkit.evaluation;

import io.agenkit.core.Agent;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * Benchmarks an agent's performance across multiple runs.
 */
public final class Benchmark {

    public record BenchmarkResult(
            String agentName,
            int runs,
            double avgLatencyMs,
            double p95LatencyMs,
            long successCount,
            long failureCount) {}

    private final Agent agent;
    private final int warmupRuns;

    public Benchmark(Agent agent, int warmupRuns) {
        this.agent = agent;
        this.warmupRuns = warmupRuns;
    }

    public Benchmark(Agent agent) {
        this(agent, 2);
    }

    public CompletableFuture<BenchmarkResult> run(List<Evaluator.EvalCase> cases, int runs) {
        return warmup(cases).thenCompose(v -> measure(cases, runs));
    }

    private CompletableFuture<Void> warmup(List<Evaluator.EvalCase> cases) {
        if (cases.isEmpty() || warmupRuns == 0) {
            return CompletableFuture.completedFuture(null);
        }
        List<CompletableFuture<Void>> warmups = new ArrayList<>();
        for (int i = 0; i < warmupRuns && i < cases.size(); i++) {
            Evaluator.EvalCase c = cases.get(i % cases.size());
            warmups.add(agent.process(c.input())
                    .thenApply(r -> (Void) null)
                    .exceptionally(ex -> null));
        }
        return CompletableFuture.allOf(warmups.toArray(new CompletableFuture[0]));
    }

    private CompletableFuture<BenchmarkResult> measure(List<Evaluator.EvalCase> cases, int runs) {
        List<Double> latencies = new ArrayList<>();
        long[] successCount = {0};
        long[] failureCount = {0};

        List<CompletableFuture<Void>> futures = new ArrayList<>();
        for (int i = 0; i < runs; i++) {
            Evaluator.EvalCase c = cases.get(i % Math.max(1, cases.size()));
            Instant start = Instant.now();
            futures.add(agent.process(c.input())
                    .thenAccept(r -> {
                        double ms = Duration.between(start, Instant.now()).toNanos() / 1e6;
                        synchronized (latencies) {
                            latencies.add(ms);
                            successCount[0]++;
                        }
                    })
                    .exceptionally(ex -> {
                        synchronized (latencies) { failureCount[0]++; }
                        return null;
                    }));
        }

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenApply(v -> {
                    latencies.sort(Double::compareTo);
                    double avg = latencies.stream().mapToDouble(d -> d).average().orElse(0.0);
                    double p95 = latencies.isEmpty() ? 0.0
                            : latencies.get((int) (latencies.size() * 0.95));
                    return new BenchmarkResult(
                            agent.getName(), runs, avg, p95,
                            successCount[0], failureCount[0]);
                });
    }
}
