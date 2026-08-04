/**
 * @file test_ab_testing.cpp
 * @brief Unit tests for A/B testing framework
 */

#include <gtest/gtest.h>
#include "agenkit/evaluation/ab_testing.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <chrono>
#include <cmath>
#include <random>
#include <string>
#include <thread>

using namespace agenkit::evaluation;
using namespace agenkit::core;
using namespace agenkit::adapters;

// Answers each test case correctly a fixed proportion of the time.
//
// This replaces a MockMetricAgent that returned a fixed response body and reported its
// own score via `response.with_metadata("accuracy", value)`. That mock is why the bug in
// #829 survived: ABTest::collect_measurements read the score straight out of response
// metadata, so the suite only ever exercised an agent grading itself. Against any
// ordinary agent every measurement was 0.0, for both arms.
//
// The test cases here carry a real `expected` fragment, and scoring goes through
// AccuracyMetric, so `accuracy_` is now the rate at which the agent actually earns its
// score rather than the number it claims.
class PartiallyCorrectAgent : public Agent {
public:
    // seed is fixed per agent so the accuracy rate is deterministic across runs.
    PartiallyCorrectAgent(double accuracy, unsigned seed)
        : accuracy_(accuracy), gen_(seed) {}

    ~PartiallyCorrectAgent() override = default;

    std::string name() const override {
        return "partially_correct_agent";
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        // Draw before going async: the generator is shared mutable state, and the
        // thread pool runs both arms' test cases through here.
        bool correct;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            correct = dist_(gen_) < accuracy_;
        }

        return std::async(std::launch::async,
                          [correct, msg = std::move(message)]() -> Result<Message, AgentError> {
            // The expected fragment for every case below is "42". Answering in prose is
            // deliberate: `expected` is a fragment, not the whole output
            // (docs/DEFAULTS.md), so a verbose correct answer must score 1.0.
            Message response("assistant",
                             correct ? "After working through it, the answer is 42."
                                     : "After working through it, the answer is 7.");
            return Result<Message, AgentError>::ok(response);
        });
    }

private:
    double accuracy_;
    std::mt19937 gen_;
    std::uniform_real_distribution<> dist_{0.0, 1.0};
    std::mutex mutex_;
};

// Always answers correctly, in prose.
class CorrectButVerboseAgent : public Agent {
public:
    ~CorrectButVerboseAgent() override = default;

    std::string name() const override { return "correct_but_verbose"; }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async,
                          [msg = std::move(message)]() -> Result<Message, AgentError> {
            return Result<Message, AgentError>::ok(
                Message("assistant", "Let me think. Carrying the one, the answer is 42."));
        });
    }
};

// Always answers wrongly.
class AlwaysWrongAgent : public Agent {
public:
    ~AlwaysWrongAgent() override = default;

    std::string name() const override { return "always_wrong"; }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async,
                          [msg = std::move(message)]() -> Result<Message, AgentError> {
            return Result<Message, AgentError>::ok(
                Message("assistant", "I believe the answer is 7."));
        });
    }
};

// Fails on every call.
class FailingAgent : public Agent {
public:
    ~FailingAgent() override = default;

    std::string name() const override { return "failing_agent"; }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async,
                          [msg = std::move(message)]() -> Result<Message, AgentError> {
            return Result<Message, AgentError>::err(
                AgentError(AgentErrorType::Transport, "upstream is down"));
        });
    }
};

// Sleeps before answering, so "latency" has something to measure.
class SlowAgent : public Agent {
public:
    explicit SlowAgent(std::chrono::milliseconds delay) : delay_(delay) {}

    ~SlowAgent() override = default;

    std::string name() const override { return "slow_agent"; }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async,
                          [delay = delay_, msg = std::move(message)]()
                              -> Result<Message, AgentError> {
            std::this_thread::sleep_for(delay);
            return Result<Message, AgentError>::ok(Message("assistant", "The answer is 42."));
        });
    }

private:
    std::chrono::milliseconds delay_;
};

// Builds `count` cases whose expected fragment is "42".
static std::vector<TestCase> make_test_cases(int count) {
    std::vector<TestCase> test_cases;
    test_cases.reserve(static_cast<size_t>(count));
    for (int i = 0; i < count; ++i) {
        test_cases.push_back(TestCase("Question " + std::to_string(i) + ": what is 6*7?", "42"));
    }
    return test_cases;
}

// ABVariant Tests

TEST(ABVariantTest, AddSample) {
    ABVariant variant("test");
    variant.add_sample(0.5);
    variant.add_sample(0.7);
    variant.add_sample(0.6);

    EXPECT_EQ(variant.samples.size(), 3);
    EXPECT_DOUBLE_EQ(variant.samples[0], 0.5);
    EXPECT_DOUBLE_EQ(variant.samples[1], 0.7);
    EXPECT_DOUBLE_EQ(variant.samples[2], 0.6);
}

TEST(ABVariantTest, CalculateStatistics) {
    ABVariant variant("test");
    variant.add_sample(1.0);
    variant.add_sample(2.0);
    variant.add_sample(3.0);
    variant.add_sample(4.0);
    variant.add_sample(5.0);

    variant.calculate_statistics();

    EXPECT_EQ(variant.sample_size, 5);
    EXPECT_DOUBLE_EQ(variant.mean, 3.0);
    EXPECT_GT(variant.std_dev, 0.0);
}

TEST(ABVariantTest, CalculateStatisticsEmptySamples) {
    ABVariant variant("test");
    variant.calculate_statistics();

    EXPECT_EQ(variant.sample_size, 0);
    EXPECT_DOUBLE_EQ(variant.mean, 0.0);
    EXPECT_DOUBLE_EQ(variant.std_dev, 0.0);
}

TEST(ABVariantTest, ToJsonFromJson) {
    ABVariant variant("control");
    variant.add_sample(0.7);
    variant.add_sample(0.8);
    variant.calculate_statistics();

    // Serialize
    auto json = variant.to_json();

    // Deserialize
    auto variant2 = ABVariant::from_json(json);

    EXPECT_EQ(variant2.name, "control");
    EXPECT_EQ(variant2.sample_size, 2);
    EXPECT_DOUBLE_EQ(variant2.mean, variant.mean);
    EXPECT_DOUBLE_EQ(variant2.std_dev, variant.std_dev);
    EXPECT_EQ(variant2.samples.size(), 2);
}

// ABResult Tests

TEST(ABResultTest, DefaultConstructor) {
    ABResult result;

    EXPECT_DOUBLE_EQ(result.p_value, 1.0);
    EXPECT_DOUBLE_EQ(result.effect_size, 0.0);
    EXPECT_FALSE(result.is_significant);
    EXPECT_EQ(result.winner, "inconclusive");
}

TEST(ABResultTest, ToJsonFromJson) {
    ABResult result;
    result.control = ABVariant("control");
    result.control.add_sample(0.7);
    result.control.calculate_statistics();

    result.treatment = ABVariant("treatment");
    result.treatment.add_sample(0.8);
    result.treatment.calculate_statistics();

    result.p_value = 0.03;
    result.effect_size = 0.65;
    result.confidence_interval = {0.05, 0.15};
    result.is_significant = true;
    result.winner = "treatment";
    result.test_type = StatisticalTestType::T_TEST;
    result.alpha = SignificanceLevel::P_0_05;

    // Serialize
    auto json = result.to_json();

    // Deserialize
    auto result2 = ABResult::from_json(json);

    EXPECT_DOUBLE_EQ(result2.p_value, 0.03);
    EXPECT_DOUBLE_EQ(result2.effect_size, 0.65);
    EXPECT_TRUE(result2.is_significant);
    EXPECT_EQ(result2.winner, "treatment");
    EXPECT_EQ(result2.test_type, StatisticalTestType::T_TEST);
}

// ABTest Tests

TEST(ABTestTest, ConstructorDefaults) {
    ABTest test;
    // Should not crash, just verify construction works
    EXPECT_NO_THROW({
        ABTest t(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);
    });
}

TEST(ABTestTest, RunWithSignificantDifference) {
    // Create test with t-test
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    // Agents that are correct 30% vs 90% of the time, scored against `expected`
    std::shared_ptr<Agent> control(new PartiallyCorrectAgent(0.30, 11));
    std::shared_ptr<Agent> treatment(new PartiallyCorrectAgent(0.90, 22));

    auto test_cases = make_test_cases(30);

    // Run test
    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    EXPECT_EQ(result.control.sample_size, 30);
    EXPECT_EQ(result.treatment.sample_size, 30);

    // Control should be around 0.30, treatment around 0.90
    EXPECT_GT(result.treatment.mean, result.control.mean);

    // With a 60-point difference, should be significant
    EXPECT_TRUE(result.is_significant);
    EXPECT_EQ(result.winner, "treatment");
    EXPECT_LT(result.p_value, 0.05);
}

TEST(ABTestTest, RunWithNoSignificantDifference) {
    // Create test
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    // Agents with the same accuracy rate
    std::shared_ptr<Agent> control(new PartiallyCorrectAgent(0.50, 33));
    std::shared_ptr<Agent> treatment(new PartiallyCorrectAgent(0.50, 44));

    auto test_cases = make_test_cases(20);

    // Run test
    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    // With no real difference, should not be significant
    EXPECT_GE(result.p_value, 0.01);  // Very lenient threshold
}

TEST(ABTestTest, RunWithMannWhitney) {
    // Create test with Mann-Whitney
    ABTest test(StatisticalTestType::MANN_WHITNEY, SignificanceLevel::P_0_05);

    std::shared_ptr<Agent> control(new AlwaysWrongAgent());
    std::shared_ptr<Agent> treatment(new CorrectButVerboseAgent());

    auto test_cases = make_test_cases(25);

    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    EXPECT_TRUE(result.is_significant);
    EXPECT_EQ(result.test_type, StatisticalTestType::MANN_WHITNEY);
}

TEST(ABTestTest, RunWithBootstrap) {
    // Create test with bootstrap
    ABTest test(StatisticalTestType::BOOTSTRAP, SignificanceLevel::P_0_05);

    std::shared_ptr<Agent> control(new PartiallyCorrectAgent(0.25, 55));
    std::shared_ptr<Agent> treatment(new PartiallyCorrectAgent(0.95, 66));

    auto test_cases = make_test_cases(20);

    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    EXPECT_TRUE(result.is_significant);
    EXPECT_EQ(result.test_type, StatisticalTestType::BOOTSTRAP);

    // Confidence interval should not contain 0
    EXPECT_GT(result.confidence_interval.first, 0.0);
}

TEST(ABTestTest, EffectSizeCalculation) {
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    std::shared_ptr<Agent> control(new PartiallyCorrectAgent(0.30, 77));
    std::shared_ptr<Agent> treatment(new PartiallyCorrectAgent(0.90, 88));

    auto test_cases = make_test_cases(30);

    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    // Should have large effect size given the 60-point difference
    EXPECT_GT(std::abs(result.effect_size), 0.5);
}

TEST(ABTestTest, GetSummary) {
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    // Create result manually
    ABResult result;
    result.control = ABVariant("control");
    result.control.add_sample(0.70);
    result.control.add_sample(0.72);
    result.control.calculate_statistics();

    result.treatment = ABVariant("treatment");
    result.treatment.add_sample(0.80);
    result.treatment.add_sample(0.82);
    result.treatment.calculate_statistics();

    result.p_value = 0.03;
    result.effect_size = 0.65;
    result.confidence_interval = {0.05, 0.15};
    result.is_significant = true;
    result.winner = "treatment";
    result.test_type = StatisticalTestType::T_TEST;
    result.alpha = SignificanceLevel::P_0_05;

    // Get summary
    std::string summary = test.get_summary(result);

    // Verify key information is in summary
    EXPECT_NE(summary.find("t-test"), std::string::npos);
    EXPECT_NE(summary.find("0.03"), std::string::npos);  // p-value
    EXPECT_NE(summary.find("0.65"), std::string::npos);  // effect size
    EXPECT_NE(summary.find("treatment"), std::string::npos);
    EXPECT_NE(summary.find("significant"), std::string::npos);
}

TEST(ABTestTest, GetSummaryNotSignificant) {
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    ABResult result;
    result.control = ABVariant("control");
    result.treatment = ABVariant("treatment");
    result.p_value = 0.15;
    result.is_significant = false;
    result.winner = "inconclusive";
    result.test_type = StatisticalTestType::T_TEST;

    std::string summary = test.get_summary(result);

    EXPECT_NE(summary.find("No significant difference"), std::string::npos);
    EXPECT_NE(summary.find("inconclusive"), std::string::npos);
}

TEST(ABTestTest, CalculateSampleSize) {
    // Calculate sample size to detect 10% improvement
    size_t n = ABTest::calculate_sample_size(
        0.75,   // baseline mean
        0.10,   // detect 10% improvement
        0.05,   // 95% confidence
        0.80,   // 80% power
        0.12    // std dev
    );

    // Should return a reasonable sample size
    EXPECT_GT(n, 0);
    EXPECT_LT(n, 10000);  // Sanity check
}

TEST(ABTestTest, CalculateSampleSizeLargerEffect) {
    // Larger effect size should require smaller sample
    size_t n_small_effect = ABTest::calculate_sample_size(0.75, 0.05, 0.05, 0.80, 0.12);
    size_t n_large_effect = ABTest::calculate_sample_size(0.75, 0.20, 0.05, 0.80, 0.12);

    EXPECT_GT(n_small_effect, n_large_effect);
}

TEST(ABTestTest, SignificanceLevels) {
    // Test different significance levels
    ABTest test_001(StatisticalTestType::T_TEST, SignificanceLevel::P_0_001);
    ABTest test_01(StatisticalTestType::T_TEST, SignificanceLevel::P_0_01);
    ABTest test_05(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);
    ABTest test_10(StatisticalTestType::T_TEST, SignificanceLevel::P_0_10);

    // Just verify they construct correctly and run.
    //
    // Partially-correct agents rather than an all-right/all-wrong pair: the latter gives
    // both arms zero variance, which trips the t-test's `se < 1e-10` guard and reports
    // p = 1.0 regardless of significance level (#835).
    EXPECT_NO_THROW({
        std::shared_ptr<Agent> control(new PartiallyCorrectAgent(0.25, 313));
        std::shared_ptr<Agent> treatment(new PartiallyCorrectAgent(0.90, 414));
        auto test_cases = make_test_cases(30);

        auto result = test_05.run(control, treatment, test_cases, "accuracy").get();
        // A 65-point difference over 30 samples must be significant
        EXPECT_TRUE(result.is_significant);
    });
}

TEST(ABTestTest, ControlWinnerWhenHigherMean) {
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    // Control better than treatment
    std::shared_ptr<Agent> control(new PartiallyCorrectAgent(0.95, 99));
    std::shared_ptr<Agent> treatment(new PartiallyCorrectAgent(0.35, 111));

    auto test_cases = make_test_cases(30);

    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    EXPECT_TRUE(result.is_significant);
    EXPECT_EQ(result.winner, "control");
    EXPECT_GT(result.control.mean, result.treatment.mean);
}

TEST(ABTestTest, ConfidenceIntervalContainsZeroWhenNoEffect) {
    ABTest test(StatisticalTestType::BOOTSTRAP, SignificanceLevel::P_0_05);

    // Same accuracy rate for both arms
    std::shared_ptr<Agent> control(new PartiallyCorrectAgent(0.50, 123));
    std::shared_ptr<Agent> treatment(new PartiallyCorrectAgent(0.50, 234));

    auto test_cases = make_test_cases(30);

    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    // CI should contain 0 (same underlying rate)
    EXPECT_LE(result.confidence_interval.first, 0.0);
    EXPECT_GE(result.confidence_interval.second, 0.0);
}

// #829 regression tests
//
// These pin the behaviour the old collect_measurements could not have: it read the score
// from the agent's own response metadata and never touched TestCase::expected, so for
// every agent below each measurement was 0.0 in both arms and the result was a
// plausible-looking "inconclusive".

// The headline case from #829: a correct agent answering in prose must score, and must
// beat a wrong one. Under the old code both arms scored 0.0.
TEST(ABTestTest, ScoresACorrectButVerboseAgentAboveAWrongOne) {
    // Mann-Whitney rather than the t-test deliberately. With every case scoring 1.0 in
    // one arm and 0.0 in the other, both variances are zero, so Welch's standard error
    // is zero and t_test()'s `se < 1e-10` guard returns p = 1.0 — the maximum-effect
    // case reported as no effect. That guard is a separate pre-existing bug (#835),
    // shared with Go and Rust, and this test must not depend on it either way.
    ABTest test(StatisticalTestType::MANN_WHITNEY, SignificanceLevel::P_0_05);

    std::shared_ptr<Agent> correct(new CorrectButVerboseAgent());
    std::shared_ptr<Agent> wrong(new AlwaysWrongAgent());

    auto test_cases = make_test_cases(20);

    auto result = test.run(wrong, correct, test_cases, "accuracy").get();

    // `expected` is the fragment "42" and the answer is "...the answer is 42.", so a
    // substring match scores 1.0 — this is the docs/DEFAULTS.md contract. These two
    // assertions are the heart of #829: before the fix both were 0.0.
    EXPECT_DOUBLE_EQ(result.treatment.mean, 1.0)
        << "a correct agent must score 1.0; 0.0 means expected is still not being read";
    EXPECT_DOUBLE_EQ(result.control.mean, 0.0);
    EXPECT_EQ(result.winner, "treatment");
    EXPECT_TRUE(result.is_significant);
}

// Scoring must agree with what AccuracyMetric would report for the same interaction —
// there must not be a second implementation of the comparison inside ABTest.
TEST(ABTestTest, ScoringAgreesWithTheAccuracyMetric) {
    TestCase test_case("Question 0: what is 6*7?", "42");
    Message input("user", test_case.input);
    Message output("assistant", "Let me think. Carrying the one, the answer is 42.");

    AccuracyMetric metric;
    nlohmann::json ctx = nlohmann::json::object();
    ctx["expected"] = "42";
    std::shared_ptr<Agent> agent(new CorrectButVerboseAgent());
    double via_metric = metric.measure(agent, input, output, ctx);

    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);
    std::vector<TestCase> test_cases{test_case};
    auto result = test.run(agent, agent, test_cases, "accuracy").get();

    EXPECT_DOUBLE_EQ(result.control.mean, via_metric);
}

// Case-insensitivity comes from the shared contract, not from ABTest.
TEST(ABTestTest, ScoringIsCaseInsensitive) {
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    // Expected is upper-case; the agent answers lower-case.
    std::vector<TestCase> test_cases;
    for (int i = 0; i < 5; ++i) {
        test_cases.push_back(TestCase("Capital of France?", "PARIS"));
    }

    class LowerCaseParisAgent : public Agent {
    public:
        std::string name() const override { return "lower_case_paris"; }
        std::future<Result<Message, AgentError>> process(Message message) override {
            return std::async(std::launch::async,
                              [msg = std::move(message)]() -> Result<Message, AgentError> {
                return Result<Message, AgentError>::ok(
                    Message("assistant", "it is paris, i think"));
            });
        }
    };

    std::shared_ptr<Agent> agent(new LowerCaseParisAgent());
    auto result = test.run(agent, agent, test_cases, "accuracy").get();

    EXPECT_DOUBLE_EQ(result.control.mean, 1.0);
}

// The validator-function variant of `expected` must be honoured too. It cannot cross a
// JSON ctx, so this is the path that delegates to TestCase::validate.
TEST(ABTestTest, ScoresTheValidatorFunctionVariant) {
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    std::vector<TestCase> test_cases;
    for (int i = 0; i < 10; ++i) {
        // Deliberately case-sensitive, which the string variant would not be — proving
        // the validator actually ran rather than falling through to a substring match.
        test_cases.push_back(TestCase("Question: what is 6*7?",
                                      std::function<bool(const std::string&)>{
                                          [](const std::string& out) {
                                              return out.find("42") != std::string::npos;
                                          }}));
    }

    std::shared_ptr<Agent> correct(new CorrectButVerboseAgent());
    std::shared_ptr<Agent> wrong(new AlwaysWrongAgent());

    auto result = test.run(wrong, correct, test_cases, "accuracy").get();

    EXPECT_DOUBLE_EQ(result.treatment.mean, 1.0);
    EXPECT_DOUBLE_EQ(result.control.mean, 0.0);
}

// metric_name used to be a metadata key, so it selected nothing. It must now select the
// metric: "latency" measures elapsed milliseconds, not accuracy's 0.0/1.0.
TEST(ABTestTest, MetricNameSelectsTheMetric) {
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    std::shared_ptr<Agent> fast(new CorrectButVerboseAgent());
    std::shared_ptr<Agent> slow(new SlowAgent(std::chrono::milliseconds(25)));

    auto test_cases = make_test_cases(5);

    auto latency = test.run(fast, slow, test_cases, "latency").get();

    // Both agents answer correctly, so accuracy would be 1.0 for both arms. Latency
    // must instead report milliseconds and rank the slow agent higher.
    EXPECT_GT(latency.treatment.mean, 20.0)
        << "the slow agent sleeps 25ms per case; a mean near 1.0 means accuracy was "
           "measured instead of latency";
    EXPECT_GT(latency.treatment.mean, latency.control.mean);

    auto accuracy = test.run(fast, slow, test_cases, "accuracy").get();
    EXPECT_DOUBLE_EQ(accuracy.control.mean, 1.0);
    EXPECT_DOUBLE_EQ(accuracy.treatment.mean, 1.0);
}

// An unrecognised metric must be an error, not a silent fallback to accuracy.
TEST(ABTestTest, UnknownMetricIsAnErrorNotASilentFallback) {
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    std::shared_ptr<Agent> agent(new CorrectButVerboseAgent());
    auto test_cases = make_test_cases(5);

    auto future = test.run(agent, agent, test_cases, "no_such_metric");
    EXPECT_THROW(future.get(), AgentError);
}

// An agent that fails is not an agent that scored zero. This used to be swallowed into a
// 0.0 sample, making a broken arm indistinguishable from a wrong one.
TEST(ABTestTest, FailingAgentPropagatesRatherThanScoringZero) {
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    std::shared_ptr<Agent> ok(new CorrectButVerboseAgent());
    std::shared_ptr<Agent> broken(new FailingAgent());

    auto test_cases = make_test_cases(5);

    auto future = test.run(ok, broken, test_cases, "accuracy");
    EXPECT_THROW(future.get(), AgentError);
}

// metric_for is the registry; nullptr is how an unknown name is signalled.
TEST(ABTestTest, MetricForResolvesTheDocumentedNames) {
    EXPECT_NE(ABTest::metric_for("accuracy"), nullptr);
    EXPECT_NE(ABTest::metric_for("quality"), nullptr);
    EXPECT_NE(ABTest::metric_for("latency"), nullptr);
    EXPECT_NE(ABTest::metric_for("context_length"), nullptr);
    EXPECT_EQ(ABTest::metric_for("no_such_metric"), nullptr);
    EXPECT_EQ(ABTest::metric_for(""), nullptr);

    // The resolved metric must be the one named.
    EXPECT_EQ(ABTest::metric_for("accuracy")->name(), "accuracy");
    EXPECT_EQ(ABTest::metric_for("latency")->name(), "latency");
}
