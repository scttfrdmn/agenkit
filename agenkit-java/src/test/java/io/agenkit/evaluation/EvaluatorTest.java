package io.agenkit.evaluation;

import io.agenkit.core.Message;
import io.agenkit.helpers.MockAgent;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.*;

class EvaluatorTest {

    @Test
    void exactMatchPassesWhenEqual() throws Exception {
        MockAgent agent = new MockAgent("agent", "hello world");
        Evaluator evaluator = new Evaluator().withExactMatch();

        Evaluator.EvalCase testCase = new Evaluator.EvalCase(
                "case1", Message.of("user", "say hello"), "hello world");
        Evaluator.EvalResult result = evaluator.evaluate(agent, testCase).get();

        assertThat(result.passed()).isTrue();
        assertThat(result.caseName()).isEqualTo("case1");
    }

    @Test
    void exactMatchFailsWhenDifferent() throws Exception {
        MockAgent agent = new MockAgent("agent", "wrong answer");
        Evaluator evaluator = new Evaluator().withExactMatch();

        Evaluator.EvalCase testCase = new Evaluator.EvalCase(
                "case2", Message.of("user", "q"), "expected answer");
        Evaluator.EvalResult result = evaluator.evaluate(agent, testCase).get();

        assertThat(result.passed()).isFalse();
    }

    @Test
    void keywordCoverageAllKeywordsPresent() throws Exception {
        MockAgent agent = new MockAgent("agent", "the sky is blue and water is wet");
        Evaluator evaluator = new Evaluator().withKeywordCoverage("sky", "blue", "water");

        Evaluator.EvalCase testCase = new Evaluator.EvalCase(
                "kw", Message.of("user", "describe"), "sky blue water");
        Evaluator.EvalResult result = evaluator.evaluate(agent, testCase).get();

        assertThat(result.passed()).isTrue();
        assertThat(result.metrics()).hasSize(1);
        assertThat(result.metrics().get(0).score()).isEqualTo(1.0);
    }

    @Test
    void keywordCoveragePartialKeywords() throws Exception {
        MockAgent agent = new MockAgent("agent", "only sky here");
        Evaluator evaluator = new Evaluator().withKeywordCoverage("sky", "blue", "green");

        Evaluator.EvalCase testCase = new Evaluator.EvalCase(
                "partial", Message.of("user", "q"), "");
        Evaluator.EvalResult result = evaluator.evaluate(agent, testCase).get();

        // 1 of 3 keywords = 0.333 score < 0.5 threshold
        assertThat(result.passed()).isFalse();
        assertThat(result.metrics().get(0).score()).isCloseTo(1.0 / 3.0, within(0.01));
    }

    @Test
    void metricPassesThreshold() {
        Metric m = new Metric("accuracy", 0.8);
        assertThat(m.passes(0.5)).isTrue();
        assertThat(m.passes(0.9)).isFalse();
    }

    @Test
    void metricToStringIncludesNameAndScore() {
        Metric m = new Metric("precision", 0.75, "test metric");
        assertThat(m.toString()).contains("precision").contains("0.750");
    }

    @Test
    void evaluateAllRunsMultipleCases() throws Exception {
        MockAgent agent = new MockAgent("agent", "correct");
        Evaluator evaluator = new Evaluator().withExactMatch();

        List<Evaluator.EvalCase> cases = List.of(
                new Evaluator.EvalCase("c1", Message.of("user", "q1"), "correct"),
                new Evaluator.EvalCase("c2", Message.of("user", "q2"), "correct"),
                new Evaluator.EvalCase("c3", Message.of("user", "q3"), "wrong")
        );

        List<Evaluator.EvalResult> results = evaluator.evaluateAll(agent, cases).get();
        assertThat(results).hasSize(3);
        long passed = results.stream().filter(Evaluator.EvalResult::passed).count();
        assertThat(passed).isEqualTo(2);
    }

    @Test
    void evaluatorWithNoMetricsPassesByDefault() throws Exception {
        MockAgent agent = new MockAgent("agent", "any response");
        Evaluator evaluator = new Evaluator(); // no metrics added

        Evaluator.EvalCase testCase = new Evaluator.EvalCase(
                "empty", Message.of("user", "q"), "expected");
        Evaluator.EvalResult result = evaluator.evaluate(agent, testCase).get();

        assertThat(result.metrics()).isEmpty();
        assertThat(result.passed()).isTrue(); // allMatch on empty stream is true
    }

    @Test
    void customMetricFunction() throws Exception {
        MockAgent agent = new MockAgent("agent", "the answer is 42");
        Evaluator evaluator = new Evaluator().addMetric((actual, expected) ->
                new Metric("length_ok", actual.length() > 5 ? 1.0 : 0.0));

        Evaluator.EvalCase testCase = new Evaluator.EvalCase(
                "custom", Message.of("user", "q"), "anything");
        Evaluator.EvalResult result = evaluator.evaluate(agent, testCase).get();

        assertThat(result.passed()).isTrue();
        assertThat(result.metrics().get(0).name()).isEqualTo("length_ok");
    }
}
