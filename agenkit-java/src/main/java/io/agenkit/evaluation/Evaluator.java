package io.agenkit.evaluation;

import io.agenkit.core.Agent;
import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiFunction;

/**
 * Evaluates an agent's responses using configurable metrics.
 */
public final class Evaluator {

    public record EvalCase(String name, Message input, String expectedOutput) {}

    public record EvalResult(String caseName, List<Metric> metrics, boolean passed) {}

    private final List<BiFunction<String, String, Metric>> metricFunctions = new ArrayList<>();

    /** Add a metric that scores output vs expected on a 0.0-1.0 scale. */
    public Evaluator addMetric(BiFunction<String, String, Metric> metricFn) {
        metricFunctions.add(metricFn);
        return this;
    }

    /** Add a keyword coverage metric. */
    public Evaluator withKeywordCoverage(String... keywords) {
        return addMetric((actual, expected) -> {
            long matched = 0;
            String lower = actual.toLowerCase();
            for (String kw : keywords) {
                if (lower.contains(kw.toLowerCase())) matched++;
            }
            double score = keywords.length == 0 ? 1.0 : (double) matched / keywords.length;
            return new Metric("keyword_coverage", score,
                    matched + "/" + keywords.length + " keywords found");
        });
    }

    /** Add an exact match metric. */
    public Evaluator withExactMatch() {
        return addMetric((actual, expected) ->
                new Metric("exact_match",
                        actual.trim().equalsIgnoreCase(expected.trim()) ? 1.0 : 0.0));
    }

    public CompletableFuture<EvalResult> evaluate(Agent agent, EvalCase evalCase) {
        return agent.process(evalCase.input()).thenApply(response -> {
            String actual = response.contentString();
            List<Metric> metrics = metricFunctions.stream()
                    .map(fn -> fn.apply(actual, evalCase.expectedOutput()))
                    .toList();
            boolean passed = metrics.stream().allMatch(m -> m.passes(0.5));
            return new EvalResult(evalCase.name(), metrics, passed);
        });
    }

    public CompletableFuture<List<EvalResult>> evaluateAll(Agent agent, List<EvalCase> cases) {
        List<CompletableFuture<EvalResult>> futures = cases.stream()
                .map(c -> evaluate(agent, c))
                .toList();
        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenApply(v -> futures.stream().map(CompletableFuture::join).toList());
    }
}
