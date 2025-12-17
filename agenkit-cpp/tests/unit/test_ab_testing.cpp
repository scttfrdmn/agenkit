/**
 * @file test_ab_testing.cpp
 * @brief Unit tests for A/B testing framework
 */

#include <gtest/gtest.h>
#include "agenkit/evaluation/ab_testing.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <cmath>
#include <random>

using namespace agenkit::evaluation;
using namespace agenkit::core;
using namespace agenkit::adapters;

// Mock agent for testing - returns metric in metadata
class MockMetricAgent : public Agent {
public:
    explicit MockMetricAgent(double base_metric, double variance = 0.0)
        : base_metric_(base_metric), variance_(variance) {}

    ~MockMetricAgent() override = default;

    std::string name() const override {
        return "mock_metric_agent";
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async, [this, msg = std::move(message)]() -> Result<Message, AgentError> {
            // Add some random variance if specified
            double metric_value = base_metric_;
            if (variance_ > 0.0) {
                std::random_device rd;
                std::mt19937 gen(rd());
                std::normal_distribution<> dist(0.0, variance_);
                metric_value += dist(gen);
            }

            // Create response with metric in metadata
            Message response("assistant", "Response");
            response.with_metadata("accuracy", metric_value);

            return Result<Message, AgentError>::ok(response);
        });
    }

private:
    double base_metric_;
    double variance_;
};

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

    // Create agents with different metrics
    std::shared_ptr<Agent> control(new MockMetricAgent(0.60, 0.05));
    std::shared_ptr<Agent> treatment(new MockMetricAgent(0.80, 0.05));

    // Create test cases
    std::vector<TestCase> test_cases;
    for (int i = 0; i < 30; ++i) {
        test_cases.push_back(TestCase("input" + std::to_string(i), "output"));
    }

    // Run test
    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    EXPECT_EQ(result.control.sample_size, 30);
    EXPECT_EQ(result.treatment.sample_size, 30);

    // Control should be around 0.60, treatment around 0.80
    EXPECT_GT(result.treatment.mean, result.control.mean);

    // With 20% difference, should be significant
    EXPECT_TRUE(result.is_significant);
    EXPECT_EQ(result.winner, "treatment");
    EXPECT_LT(result.p_value, 0.05);
}

TEST(ABTestTest, RunWithNoSignificantDifference) {
    // Create test
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    // Create agents with same metrics
    std::shared_ptr<Agent> control(new MockMetricAgent(0.70, 0.1));
    std::shared_ptr<Agent> treatment(new MockMetricAgent(0.71, 0.1));  // Very small difference

    // Create test cases
    std::vector<TestCase> test_cases;
    for (int i = 0; i < 20; ++i) {
        test_cases.push_back(TestCase("input" + std::to_string(i), "output"));
    }

    // Run test
    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    // With minimal difference, likely not significant
    // (probabilistic test - may occasionally fail)
    EXPECT_GE(result.p_value, 0.01);  // Very lenient threshold
}

TEST(ABTestTest, RunWithMannWhitney) {
    // Create test with Mann-Whitney
    ABTest test(StatisticalTestType::MANN_WHITNEY, SignificanceLevel::P_0_05);

    std::shared_ptr<Agent> control(new MockMetricAgent(0.60, 0.05));
    std::shared_ptr<Agent> treatment(new MockMetricAgent(0.80, 0.05));

    std::vector<TestCase> test_cases;
    for (int i = 0; i < 25; ++i) {
        test_cases.push_back(TestCase("input" + std::to_string(i), "output"));
    }

    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    EXPECT_TRUE(result.is_significant);
    EXPECT_EQ(result.test_type, StatisticalTestType::MANN_WHITNEY);
}

TEST(ABTestTest, RunWithBootstrap) {
    // Create test with bootstrap
    ABTest test(StatisticalTestType::BOOTSTRAP, SignificanceLevel::P_0_05);

    std::shared_ptr<Agent> control(new MockMetricAgent(0.60, 0.05));
    std::shared_ptr<Agent> treatment(new MockMetricAgent(0.80, 0.05));

    std::vector<TestCase> test_cases;
    for (int i = 0; i < 20; ++i) {
        test_cases.push_back(TestCase("input" + std::to_string(i), "output"));
    }

    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    EXPECT_TRUE(result.is_significant);
    EXPECT_EQ(result.test_type, StatisticalTestType::BOOTSTRAP);

    // Confidence interval should not contain 0
    EXPECT_GT(result.confidence_interval.first, 0.0);
}

TEST(ABTestTest, EffectSizeCalculation) {
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    std::shared_ptr<Agent> control(new MockMetricAgent(0.60, 0.05));
    std::shared_ptr<Agent> treatment(new MockMetricAgent(0.80, 0.05));

    std::vector<TestCase> test_cases;
    for (int i = 0; i < 30; ++i) {
        test_cases.push_back(TestCase("input" + std::to_string(i), "output"));
    }

    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    // Should have large effect size given 20% difference
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

    // Just verify they construct correctly and run
    EXPECT_NO_THROW({
        std::shared_ptr<Agent> control(new MockMetricAgent(0.60, 0.05));
        std::shared_ptr<Agent> treatment(new MockMetricAgent(0.80, 0.05));
        std::vector<TestCase> test_cases(30, TestCase("input", "output"));

        auto result = test_05.run(control, treatment, test_cases, "accuracy").get();
        // With 20% difference and 30 samples, should be significant
        EXPECT_TRUE(result.is_significant);
    });
}

TEST(ABTestTest, ControlWinnerWhenHigherMean) {
    ABTest test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);

    // Control better than treatment
    std::shared_ptr<Agent> control(new MockMetricAgent(0.90, 0.02));
    std::shared_ptr<Agent> treatment(new MockMetricAgent(0.70, 0.02));

    std::vector<TestCase> test_cases;
    for (int i = 0; i < 30; ++i) {
        test_cases.push_back(TestCase("input" + std::to_string(i), "output"));
    }

    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    EXPECT_TRUE(result.is_significant);
    EXPECT_EQ(result.winner, "control");
    EXPECT_GT(result.control.mean, result.treatment.mean);
}

TEST(ABTestTest, ConfidenceIntervalContainsZeroWhenNoEffect) {
    ABTest test(StatisticalTestType::BOOTSTRAP, SignificanceLevel::P_0_05);

    // Same metric for both with minimal variance
    std::shared_ptr<Agent> control(new MockMetricAgent(0.75, 0.02));
    std::shared_ptr<Agent> treatment(new MockMetricAgent(0.75, 0.02));

    std::vector<TestCase> test_cases;
    for (int i = 0; i < 30; ++i) {
        test_cases.push_back(TestCase("input" + std::to_string(i), "output"));
    }

    auto result = test.run(control, treatment, test_cases, "accuracy").get();

    // CI should contain 0 (with minimal variance and same means)
    EXPECT_LE(result.confidence_interval.first, 0.0);
    EXPECT_GE(result.confidence_interval.second, 0.0);
}
